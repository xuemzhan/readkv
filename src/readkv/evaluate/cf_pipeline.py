"""V2 反事实保真端到端管线（方案 §9.2）。

编排：成对构造 → 双文档独立离线缓存 → mapper → 四臂 + 控制 →
逐对 g / D / E_CF 记录 → 主终点（成对 E_CF 差异）→ 决策树 → 报告落盘。

所有科学判定只由 reports/runs/<run_id>/scores.jsonl 重算；mock 数字不是证据。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from readkv.cache.cache import KVCache
from readkv.data.build_cf_pairs import (
    DEFAULT_SIZES,
    CFPair,
    build_cf_pairs,
    quality_report,
    split_pairs,
    stable_hash,
)
from readkv.evaluate.counterfactual import (
    PairCFRecord,
    paired_ecf_difference,
    summarize_cf,
)
from readkv.evaluate.controls import build_control
from readkv.evaluate.decision import match_decision
from readkv.evaluate.pipeline import combine, fit_mapper
from readkv.runtime import RunContext


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

@dataclass
class CFPipelineConfig:
    sizes: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_SIZES))
    seed: int = 0
    n_resamples: int = 2000
    tau: float = 1.0
    self_threshold: float = 0.1
    method: str = "kd"            # kd / cf_lite / cf_mech / none
    mapper_kind: str = "affine"   # affine / consumer / score
    include_controls: bool = True
    include_four_arms: bool = True
    decision_rules: list[Mapping[str, Any]] = field(default_factory=list)
    cf_distortion: float = 0.0    # 仅 mock 接线测试用
    eval_splits: tuple[str, ...] = ("val", "test")


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _pair_doc(pair: CFPair | Mapping[str, Any], side: str) -> dict[str, Any]:
    pair = _pair_dict(pair)
    return {
        "doc_id": f"{pair['pair_id']}-{side}",
        "pair_id": pair["pair_id"],
        "side": side,
        "text": pair["context_A"] if side == "A" else pair["context_B"],
        "context": pair["context_A"] if side == "A" else pair["context_B"],
        "query": pair["query"],
        "cluster": pair["cluster"],
    }


def _query_doc(pair: CFPair | Mapping[str, Any]) -> dict[str, Any]:
    pair = _pair_dict(pair)
    return {"doc_id": f"{pair['pair_id']}-query", "text": pair["query"], "query": pair["query"]}


def _correct_index(pair: CFPair | Mapping[str, Any], side: str) -> int | None:
    pair = _pair_dict(pair)
    label = pair["correct_A"] if side == "A" else pair["correct_B"]
    label = label.strip().upper()
    if label.startswith("A") and label.startswith("B"):
        return None  # F5: 两个候选都正确
    return 0 if label.startswith("A") else 1


def _pair_dict(pair: CFPair | Mapping[str, Any]) -> dict[str, Any]:
    from dataclasses import asdict
    return dict(pair) if isinstance(pair, Mapping) else asdict(pair)


def _arm_caches(backend: Any, pair: CFPair, cfg: CFPipelineConfig,
                mapper: Any, mismatch_pairs: Sequence[CFPair]) -> dict[str, tuple[KVCache, KVCache]]:
    """为每个 arm 产出 (cache_A, cache_B)。"""
    pair = _pair_dict(pair)
    self_a = backend.pair_side_cache(pair, "A", "student")
    self_b = backend.pair_side_cache(pair, "B", "student")
    teacher_a = backend.pair_side_cache(pair, "A", "teacher")
    teacher_b = backend.pair_side_cache(pair, "B", "teacher")

    mapped_a = mapper.transform(teacher_a)
    mapped_b = mapper.transform(teacher_b)
    if cfg.cf_distortion:
        mapped_a = backend.inject_counterfactual_distortion(mapped_a, strength=cfg.cf_distortion, upstream_bias=1.0)
        mapped_b = backend.inject_counterfactual_distortion(mapped_b, strength=cfg.cf_distortion, upstream_bias=-1.0)

    arms: dict[str, tuple[KVCache, KVCache]] = {
        "self": (self_a, self_b),
        "identity": (backend.inject(self_a), backend.inject(self_b)),
        "joint": (mapped_a, mapped_b),
    }
    if cfg.include_four_arms:
        arms["k_only"] = (combine(mapped_a, self_a), combine(mapped_b, self_b))
        arms["v_only"] = (combine(self_a, mapped_a), combine(self_b, mapped_b))

    if cfg.include_controls:
        # mismatch: 形状/长度匹配的 derangement（不允许混入正确文档）
        if mismatch_pairs:
            other = _pair_dict(mismatch_pairs[0])
            other_t_a = backend.pair_side_cache(other, "A", "teacher")
            other_t_b = backend.pair_side_cache(other, "B", "teacher")
            mismatch_a = mapper.transform(other_t_a)
            mismatch_b = mapper.transform(other_t_b)
            arms["control:mismatch"] = (mismatch_a, mismatch_b)
        arms["control:random"] = (
            build_control(mapped_a, "random_gaussian", seed=cfg.seed),
            build_control(mapped_b, "random_gaussian", seed=cfg.seed + 1),
        )
        arms["control:zero"] = (
            build_control(mapped_a, "zero", seed=cfg.seed),
            build_control(mapped_b, "zero", seed=cfg.seed + 1),
        )
        arms["control:correct"] = (mapped_a, mapped_b)
    return arms


def _logits_for(backend: Any, cache: KVCache, pair: CFPair | Mapping[str, Any], side: str) -> np.ndarray:
    pair = _pair_dict(pair)
    candidates = (pair["candidate_A"], pair["candidate_B"])
    return np.asarray(backend.candidate_logits(
        cache, _query_doc(pair),
        candidates=candidates,
        correct_index=_correct_index(pair, side),
    ), dtype=float)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_cf_pipeline(
    ctx: RunContext,
    backend: Any,
    cfg: CFPipelineConfig,
    *,
    baseline_mapper: Any | None = None,
    new_mapper: Any | None = None,
) -> dict[str, Any]:
    """执行完整反事实管线并写报告。返回供决策规则匹配的事实字典。"""
    pairs = build_cf_pairs(sizes=cfg.sizes, seed=cfg.seed)
    cal = split_pairs(pairs, "train")
    ev = [p for s in cfg.eval_splits for p in split_pairs(pairs, s)]
    if len(cal) < 2 or len(ev) < 2:
        raise ValueError("need at least 2 calibration and 2 evaluation pairs")

    quality = quality_report(pairs)
    if quality["quality_gate"] != "pass":
        raise ValueError(f"data quality gate failed: {quality}")

    # mapper 拟合：校准集只用 train split（实体/模板隔离已在 build_cf_pairs 完成）
    cal_docs = [_pair_doc(p, side) for p in cal for side in ("A", "B")]
    if baseline_mapper is None:
        baseline_mapper = fit_mapper(backend, cal_docs, cfg.mapper_kind, seed=cfg.seed)
    if new_mapper is None:
        new_mapper = baseline_mapper  # 默认同 mapper；WIRING 检查靠 cf_distortion 触发失真

    # 逐对计算
    rows: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    for idx, pair in enumerate(ev):
        mismatch = [p for p in ev if p.pair_id != pair.pair_id][:1]
        arms = _arm_caches(backend, pair, cfg, baseline_mapper, mismatch)

        per_arm_records: dict[str, dict[str, Any]] = {}
        for arm, (cache_a, cache_b) in arms.items():
            logits_a = _logits_for(backend, cache_a, pair, "A")
            logits_b = _logits_for(backend, cache_b, pair, "B")
            # 控制臂的 E_CF 也以 Self 为参照
            record = PairCFRecord(
                pair_id=pair.pair_id,
                split=pair.split,
                slice_id=pair.slice_id,
                cluster=pair.cluster,
                self_logits_A=_logits_for(backend, arms["self"][0], pair, "A"),
                self_logits_B=_logits_for(backend, arms["self"][1], pair, "B"),
                transfer_logits_A=logits_a,
                transfer_logits_B=logits_b,
                correct_A=pair.correct_A,
                correct_B=pair.correct_B,
                must_flip=pair.must_flip,
                tau=cfg.tau,
                self_threshold=cfg.self_threshold,
            ).compute()
            per_arm_records[arm] = record

            row = {
                "pair_id": pair.pair_id,
                "split": pair.split,
                "slice_id": pair.slice_id,
                "template_family": pair.template_family,
                "cluster": pair.cluster,
                "arm": arm,
                "must_flip": pair.must_flip,
                "length_matched": pair.length_matched,
                "cache_hash": stable_hash(pair),
                "candidate_A": pair.candidate_A,
                "candidate_B": pair.candidate_B,
                "correct_A": pair.correct_A,
                "correct_B": pair.correct_B,
                **{k: v for k, v in record.items() if k != "control_logits"},
            }
            rows.append(row)

        baseline_records.append(per_arm_records["joint"])

        # 新方法的 joint 臂（可与 baseline 不同 mapper）
        if new_mapper is not baseline_mapper:
            new_teacher_a = backend.pair_side_cache(_pair_dict(pair), "A", "teacher")
            new_teacher_b = backend.pair_side_cache(_pair_dict(pair), "B", "teacher")
            new_a, new_b = new_mapper.transform(new_teacher_a), new_mapper.transform(new_teacher_b)
            if cfg.cf_distortion:
                new_a = backend.inject_counterfactual_distortion(new_a, strength=cfg.cf_distortion, upstream_bias=1.0)
                new_b = backend.inject_counterfactual_distortion(new_b, strength=cfg.cf_distortion, upstream_bias=-1.0)
        else:
            new_a, new_b = arms["joint"]
        new_record = PairCFRecord(
            pair_id=pair.pair_id, split=pair.split, slice_id=pair.slice_id,
            cluster=pair.cluster,
            self_logits_A=_logits_for(backend, arms["self"][0], pair, "A"),
            self_logits_B=_logits_for(backend, arms["self"][1], pair, "B"),
            transfer_logits_A=_logits_for(backend, new_a, pair, "A"),
            transfer_logits_B=_logits_for(backend, new_b, pair, "B"),
            correct_A=pair.correct_A, correct_B=pair.correct_B,
            must_flip=pair.must_flip, tau=cfg.tau, self_threshold=cfg.self_threshold,
        ).compute()
        rows.append({
            "pair_id": pair.pair_id, "split": pair.split, "slice_id": pair.slice_id,
            "cluster": pair.cluster, "arm": "new_joint", "must_flip": pair.must_flip,
            "length_matched": pair.length_matched, "cache_hash": stable_hash(pair),
            **{k: v for k, v in new_record.items() if k != "control_logits"},
        })

    ctx.write_scores(rows)

    # 分组聚合
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)

    summaries = {
        arm: summarize_cf(arm_rows, tau=cfg.tau, n_resamples=cfg.n_resamples,
                          seed=cfg.seed).as_dict()
        for arm, arm_rows in by_arm.items()
    }

    # 主终点：新方法与最强基线的成对 E_CF 差异
    new_records = by_arm.get("new_joint", by_arm.get("joint", []))
    endpoint = paired_ecf_difference(new_records, baseline_records,
                                     n_resamples=cfg.n_resamples, seed=cfg.seed)

    # 信息归因：正确 vs 控制缓存的 E_CF 差
    info_attribution: dict[str, float] = {}
    joint_summary = summaries.get("joint", {})
    for ctrl in ("control:mismatch", "control:random", "control:zero"):
        ctrl_summary = summaries.get(ctrl)
        if ctrl_summary:
            info_attribution[ctrl] = float(ctrl_summary.get("E_CF", {}).get("mean", 0.0)) - float(
                joint_summary.get("E_CF", {}).get("mean", 0.0)
            )

    metrics = {
        "run_id": ctx.run_id,
        "backend": "mock",
        "protocol_version": ctx.protocol_version,
        "method": cfg.method,
        "n_calibration": len(cal),
        "n_eval": len(ev),
        "tau": cfg.tau,
        "data_quality": quality,
        "arms": summaries,
        "primary_endpoint": endpoint,
        "info_attribution": info_attribution,
    }
    ctx.write_metrics("metrics.json", metrics)

    facts = decision_facts(metrics)
    decision = match_decision(cfg.decision_rules, facts) if cfg.decision_rules else None
    metrics["decision"] = decision
    metrics["decision_facts"] = facts
    ctx.write_metrics("metrics.json", metrics)
    ctx.write_ledger("ecf_ledger.jsonl", rows)
    ctx.finalize()
    return metrics


def decision_facts(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """把观测指标映射成 V2 预注册规则的机器可读事实。"""
    endpoint = metrics.get("primary_endpoint", {})
    arms = metrics.get("arms", {})
    joint = arms.get("joint", {})
    ident = arms.get("identity", {})
    return {
        "ecf_improved": bool(endpoint.get("improved", False)),
        "ecf_point": float(endpoint.get("point", 0.0)),
        "ci_upper": float(endpoint.get("ci", [0, 0])[1]),
        "distortion_present": bool(joint.get("E_CF", {}).get("mean", 0.0) >
                                   ident.get("E_CF", {}).get("mean", 0.0)),
        "joint_ecf_mean": float(joint.get("E_CF", {}).get("mean", 0.0)),
        "identity_ecf_mean": float(ident.get("E_CF", {}).get("mean", 0.0)),
        "flip_consistency": float(joint.get("flip_consistency", 0.0)),
        "coverage": float(joint.get("coverage", 0.0)),
        "dual_correct": float(joint.get("dual_correct", 0.0)),
        "quality_pass": metrics.get("data_quality", {}).get("quality_gate") == "pass",
    }
