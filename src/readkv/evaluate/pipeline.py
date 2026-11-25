"""端到端 mock 管线：缓存 → mapper → 四臂/对照/探针 → 逐样本分数 → 门限。

同一套编排可供 GPU 后端复用：只需把 MockBackend 替换成实现 models/hooks.py
契约的后端对象。所有科学判定仍只由 reports/<run_id>/scores.jsonl 重算。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from readkv.cache.cache import KVCache
from readkv.evaluate.controls import build_control
from readkv.evaluate.decision import match_decision
from readkv.evaluate.diagnostics import routing_tv, top1_agreement
from readkv.evaluate.evaluator import answer_probability
from readkv.evaluate.gates import evaluate_h2, evaluate_h3
from readkv.evaluate.probes import fraction_probe, octant_probe, window_probe
from readkv.evaluate.validator import check_identity, logit_cosine
from readkv.mapper.consumer import ConsumerSpaceMapper
from readkv.mapper.key_objectives import ScoreRegressionKeyMapper
from readkv.mapper.representation import AffineMapper
from readkv.models.mock_backend import MockBackend
from readkv.runtime import RunContext
from readkv.stats.bootstrap import cluster_bootstrap


@dataclass
class PipelineConfig:
    n_docs: int = 16
    n_calibration: int = 8
    n_eval: int = 16
    seed: int = 0
    epsilon: float = 0.02
    n_resamples: int = 1000
    arms: tuple[str, ...] = ("self", "k_only", "v_only", "joint")
    controls: tuple[str, ...] = ()
    probes: tuple[str, ...] = ()
    include_identity: bool = True
    value_mapper: str = "affine"
    key_mapper: str = "affine"
    decision_rules: list[Mapping[str, Any]] = field(default_factory=list)


def make_items(backend: MockBackend, n_docs: int, seed: int = 0) -> list[dict[str, Any]]:
    """四选一合成文档：gold letter 由 mock 后端的内容向量确定。"""
    items = []
    for i in range(n_docs):
        doc = {"doc_id": f"D{i:03d}", "text": f"project-{seed}-{i}", "cluster": f"C{i // 2:02d}"}
        items.append(
            {
                **doc,
                "question": f"What is the status of {doc['doc_id']}?",
                "choices": ("A", "B", "C", "D"),
                "gold_letter": "ABCD"[backend.gold_letter(doc)],
            }
        )
    return items


def stack_caches(backend: MockBackend, docs: Sequence[Mapping[str, Any]], role: str) -> KVCache:
    caches = [backend.cache(d, role) for d in docs]
    layers = caches[0].layers
    keys = {l: np.concatenate([c.keys[l] for c in caches], axis=1) for l in layers}
    values = {l: np.concatenate([c.values[l] for c in caches], axis=1) for l in layers}
    return KVCache(keys, values, {"stacked": True, "n_docs": len(docs)})


def stacked_attention(backend: MockBackend, docs: Sequence[Mapping[str, Any]]) -> dict[tuple[int, int], np.ndarray]:
    per_doc = [backend.attention_matrices(backend.cache(d, "student"), d) for d in docs]
    t = backend.spec.tokens_per_doc
    size = t * len(docs)
    out: dict[tuple[int, int], np.ndarray] = {}
    for key in per_doc[0]:
        block = np.zeros((size, size), dtype=float)
        for i, matrices in enumerate(per_doc):
            block[i * t : (i + 1) * t, i * t : (i + 1) * t] = matrices[key]
        out[key] = block
    return out


def stacked_queries(backend: MockBackend, docs: Sequence[Mapping[str, Any]]) -> dict[tuple[int, int], np.ndarray]:
    out: dict[tuple[int, int], np.ndarray] = {}
    for key in backend.attention_matrices(backend.cache(docs[0], "student"), docs[0]):
        layer, head = key
        out[key] = np.concatenate([backend.query_states(layer, head, d) for d in docs], axis=0)
    return out


def fit_mapper(
    backend: MockBackend, docs: Sequence[Mapping[str, Any]], kind: str, *, seed: int = 0
) -> Any:
    """统一 mapper 工厂；mock 下 WO-aware 用 consumer-space 近似，并在文档中标明。"""
    teacher = stack_caches(backend, docs, "teacher")
    student = stack_caches(backend, docs, "student")
    if kind in ("affine", "affine_k", "affine_v", "affine_shuffled"):
        channel = {"affine": "both", "affine_k": "K", "affine_v": "V", "affine_shuffled": "both"}[kind]
        target = student
        if kind == "affine_shuffled":
            rolled = list(docs[1:]) + [docs[0]]
            target = stack_caches(backend, rolled, "student")
        return AffineMapper(channel=channel).fit(teacher, target)
    if kind in ("consumer", "wo_aware", "consumer_shuffled"):
        target = student
        if kind == "consumer_shuffled":
            rolled = list(docs[1:]) + [docs[0]]
            target = stack_caches(backend, rolled, "student")
        attn = stacked_attention(backend, docs)
        if kind == "consumer_shuffled":
            attn = stacked_attention(backend, list(docs[1:]) + [docs[0]])
        return ConsumerSpaceMapper(alpha=1.0, channel="V").fit(teacher, target, attention_matrices=attn)
    if kind in ("score", "score_weighted", "score_shuffled"):
        target = student
        kwargs: dict[str, Any] = {"query_states": stacked_queries(backend, docs)}
        if kind == "score_weighted":
            attn = stacked_attention(backend, docs)
            weights = {}
            for key, mat in attn.items():
                weights[key] = mat.sum(axis=1)
            kwargs["attention_weights"] = weights
        if kind == "score_shuffled":
            rolled = list(docs[1:]) + [docs[0]]
            target = stack_caches(backend, rolled, "student")
            kwargs["query_states"] = stacked_queries(backend, rolled)
        return ScoreRegressionKeyMapper(attention_weighted=(kind == "score_weighted")).fit(teacher, target, **kwargs)
    raise ValueError(f"unknown mapper kind: {kind}")


def combine(kcache: KVCache, vcache: KVCache) -> KVCache:
    keys = {l: a.copy() for l, a in kcache.keys.items()}
    values = {l: a.copy() for l, a in vcache.values.items()}
    return KVCache(keys, values, {"combined": True})


def _routing(backend: MockBackend, cache: KVCache, doc: Mapping[str, Any], native: KVCache) -> tuple[float, float]:
    tvs, tops = [], []
    for key, p in backend.attention_matrices(native, doc).items():
        q = backend.attention_matrices(cache, doc)[key]
        tvs.append(routing_tv(p, q))
        tops.append(top1_agreement(p, q))
    return float(np.mean(tvs)), float(np.mean(tops))


def run_pipeline(
    ctx: RunContext,
    backend: MockBackend,
    cfg: PipelineConfig,
    *,
    value_mapper_obj: Any | None = None,
    key_mapper_obj: Any | None = None,
) -> dict[str, Any]:
    """执行完整管线并写入 reports/<run_id>/；返回可用于 decision rule 的事实。"""
    items = make_items(backend, cfg.n_docs, cfg.seed)
    cal = items[: cfg.n_calibration]
    ev = items[cfg.n_calibration : cfg.n_calibration + cfg.n_eval]
    if len(cal) < 2 or len(ev) < 2:
        raise ValueError("need at least 2 calibration and 2 evaluation items")

    value_mapper = value_mapper_obj or fit_mapper(backend, cal, cfg.value_mapper, seed=cfg.seed)
    key_mapper = key_mapper_obj or fit_mapper(backend, cal, cfg.key_mapper, seed=cfg.seed)
    prepared = []
    for item in ev:
        t = backend.teacher_cache(item)
        s = backend.student_cache(item)
        mapped_k = key_mapper.transform(t)
        mapped_v = value_mapper.transform(t)
        prepared.append((item, s, combine(mapped_k, mapped_v)))

    rows: list[dict[str, Any]] = []
    for idx, (item, s, joint) in enumerate(prepared):
        gold = "ABCD".index(item["gold_letter"])
        self_logits = backend.answer_logits(s, item, arm="self")
        self_prob = float(answer_probability(self_logits)[gold])
        self_ll = backend.logprob(self_logits, arm="self")
        self_tv, self_top1 = _routing(backend, s, item, s)

        caches: dict[str, KVCache] = {"self": s, "k_only": combine(joint, s), "v_only": combine(s, joint), "joint": joint}
        if cfg.include_identity:
            caches["identity"] = backend.inject(s)
        for kind in cfg.controls:
            other = prepared[(idx + 1) % len(prepared)][2] if kind == "wrong_document" else None
            caches[f"control:{kind}"] = build_control(joint, kind, seed=cfg.seed + idx, other=other)
        if "fraction_0.5" in cfg.probes:
            caches["probe:fraction_0.5"] = fraction_probe(s, joint, 0.5)
        if "top_third" in cfg.probes:
            caches["probe:top_third"] = window_probe(s, joint, "top_third")
        if "octant_3" in cfg.probes:
            caches["probe:octant_3"] = octant_probe(s, joint, 3)

        for arm, cache in caches.items():
            logits = backend.answer_logits(cache, item, arm=arm)
            prob = float(answer_probability(logits)[gold])
            tv, top1 = (0.0, 1.0) if arm in ("self", "identity") else _routing(backend, cache, item, s)
            row: dict[str, Any] = {
                "item_id": item["doc_id"],
                "doc_id": item["doc_id"],
                "cluster": item["cluster"],
                "arm": arm,
                "gold_prob": prob,
                "gold_prob_self": self_prob,
                "corrected_em": float(backend.answer_text(logits) == item["gold_letter"]),
                "delta_ll": backend.logprob(logits, arm=arm) - self_ll,
                "routing_tv": tv,
                "top1_agreement": top1,
                "self_routing_tv": self_tv,
                "self_top1_agreement": self_top1,
            }
            if arm == "identity":
                row["logit_cosine"] = logit_cosine(logits, self_logits)
            rows.append(row)

    ctx.write_scores(rows)

    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)

    arm_metrics: dict[str, Any] = {}
    for arm, arm_rows in by_arm.items():
        deltas = [r["gold_prob"] - r["gold_prob_self"] for r in arm_rows]
        h2 = evaluate_h2(deltas, epsilon=cfg.epsilon, n_resamples=cfg.n_resamples, seed=cfg.seed)
        ems = [r["corrected_em"] for r in arm_rows]
        em_point, em_low, em_high = cluster_bootstrap(
            ems, [r["doc_id"] for r in arm_rows], n_resamples=cfg.n_resamples, seed=cfg.seed
        )
        arm_metrics[arm] = {
            "h2": h2.as_dict(),
            "corrected_em": {"point": em_point, "ci": [em_low, em_high], "mean": float(np.mean(ems))},
            "delta_ll_mean": float(np.mean([r["delta_ll"] for r in arm_rows])),
            "routing_tv_mean": float(np.mean([r["routing_tv"] for r in arm_rows])),
            "top1_agreement_mean": float(np.mean([r["top1_agreement"] for r in arm_rows])),
        }

    identity = None
    if cfg.include_identity:
        identity = check_identity(
            [r["logit_cosine"] for r in by_arm["identity"]],
            threshold=0.9998,
        ).as_dict()

    probe_deltas = [
        [r["gold_prob"] - r["gold_prob_self"] for r in arm_rows]
        for arm, arm_rows in by_arm.items()
        if arm.startswith("probe:")
    ]
    h3 = evaluate_h3(probe_deltas, n_resamples=cfg.n_resamples, seed=cfg.seed) if probe_deltas else None

    joint = arm_metrics.get("joint", {})
    wrong = arm_metrics.get("control:wrong_document", {})
    csg = (
        joint.get("h2", {}).get("point", 0.0) - wrong.get("h2", {}).get("point", 0.0)
        if wrong
        else None
    )

    metrics = {
        "run_id": ctx.run_id,
        "backend": "mock",
        "n_calibration": len(cal),
        "n_eval": len(ev),
        "arms": arm_metrics,
        "H1": identity,
        "H3": h3.as_dict() if h3 else None,
        "CSG": csg,
        "protocol_version": ctx.protocol_version,
    }
    ctx.write_metrics("metrics.json", metrics)

    decision = match_decision(cfg.decision_rules, decision_facts(metrics)) if cfg.decision_rules else None
    metrics["decision"] = decision
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    return metrics


def decision_facts(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """把观测指标映射成 prereg 规则的机器可读事实。"""
    arms = metrics.get("arms", {})
    k = arms.get("k_only", {}).get("corrected_em", {}).get("mean", 0.0)
    a = arms.get("control:affine_k", {}).get("corrected_em", {}).get("mean", 0.0)
    d = arms.get("control:score_shuffled", {}).get("corrected_em", {}).get("mean", 0.0)
    h2_any = any(v.get("h2", {}).get("passed") for name, v in arms.items() if name in ("v_only", "joint"))
    chg_any = any(v.get("h2", {}).get("point", 0.0) > 0 for v in arms.values())
    h1_pass = bool((metrics.get("H1") or {}).get("passed", False))
    key_tv = arms.get("k_only", {}).get("routing_tv_mean", 0.0)
    self_tv = arms.get("self", {}).get("routing_tv_mean", 0.0)
    return {
        "C_k_only_em_high": k >= 0.15,
        "C_beats_baselines": k > a and k > d,
        "D_not_better": d <= k,
        "routing_improved": key_tv < self_tv,
        "h2_pass_any": h2_any,
        "any_positive_chg": chg_any,
        "h1_pass": h1_pass,
    }
