"""2×2 校准版本 × 验证版本独立审计入口（protocol-v2.7，task 2）。

严格独立：**显式接收两份 train 与两份 val 的 JSONL 路径**，只从这些文件读取
CFPair 记录；绝不调用 P1_gpu.py（其 run_cf_pipeline 会自动重建数据 + 质量门）。
固定 bf16/sdpa、等深 28→28、逐层逐头 K/V affine、ridge λ=0.001、首 token 评分。

单格语义：A{cal_version}{val_version}，用对应 train 拟合一个 affine mapper，在对应 val
上评测四臂（self/identity/k_only/v_only/joint）+ 控制，逐对分数 + 样本指纹 + 审计告警 +
耗时写 reports/runs/<run_id>/（冒烟 --smoke 写 reports/_non_authoritative/，non-authoritative）。

用法（冒烟 seed0，A00 示例）：
  .venv/bin/python -m experiments.audit_2x2_gpu \
      --run-id audit_2x2_A00_s0_smoke \
      --train-old data/audit_2x2/legacy/train_seed0.jsonl \
      --val-old   data/audit_2x2/legacy/val_seed0.jsonl \
      --train-fixed data/audit_2x2/fixed/train_seed0.jsonl \
      --val-fixed   data/audit_2x2/fixed/val_seed0.jsonl \
      --cell A00 --seed 0 --cal-version legacy --val-version legacy --smoke
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from readkv.cache.cache import KVCache
from readkv.config import load_config
from readkv.data.build_cf_pairs import CFPair
from readkv.evaluate.controls import build_control
from readkv.evaluate.counterfactual import PairCFRecord, summarize_cf
from readkv.evaluate.pipeline import combine, stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.hooks import inject_and_generate, verify_zero_re_prefill
from readkv.models.layer_map import LayerMap
from readkv.runtime import v2_context

RIDGE_LAM = 0.001
CELLS = {
    "A00": ("legacy", "legacy"), "A01": ("legacy", "fixed"),
    "A10": ("fixed", "legacy"), "A11": ("fixed", "fixed"),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--train-old", required=True)
    p.add_argument("--val-old", required=True)
    p.add_argument("--train-fixed", required=True)
    p.add_argument("--val-fixed", required=True)
    p.add_argument("--cell", required=True, choices=list(CELLS))
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--cal-version", choices=["legacy", "fixed"], default=None)
    p.add_argument("--val-version", choices=["legacy", "fixed"], default=None)
    p.add_argument("--teacher", default="/root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master")
    p.add_argument("--student", default="/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master")
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--smoke", action="store_true", help="冒烟门：val 取小子集，产物 non-authoritative")
    p.add_argument("--smoke-n-val", type=int, default=6)
    p.add_argument("--n-resamples", type=int, default=10000)
    return p.parse_args()


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_pairs(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """从显式 JSONL 读 CFPair 记录（不重建、不过质量门）。"""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit is not None:
        rows = rows[:limit]
    return rows


def load_model(path, dtype, kernel, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                             attn_implementation=kernel).to(device)
    m.eval(); m.config.use_cache = True
    for p in m.parameters():
        p.requires_grad_(False)
    return m, tok


def pair_doc(pair: Mapping[str, Any], side: str) -> dict[str, Any]:
    return {"doc_id": f"{pair['pair_id']}-{side}",
            "text": pair["context_A"] if side == "A" else pair["context_B"],
            "context": pair["context_A"] if side == "A" else pair["context_B"],
            "query": pair["query"], "cluster": pair.get("cluster", "")}


def candidate_logits(backend: GPUBackend, cache: KVCache, pair: Mapping[str, Any]) -> np.ndarray:
    qdoc = {"doc_id": f"{pair['pair_id']}-query", "text": pair["query"], "query": pair["query"]}
    return np.asarray(backend.candidate_logits(cache, qdoc,
                       candidates=(pair["candidate_A"], pair["candidate_B"])), dtype=float)


def correct_index(pair: Mapping[str, Any], side: str) -> int | None:
    label = str(pair["correct_A"] if side == "A" else pair["correct_B"]).strip().upper()
    if label.startswith("A") and label.startswith("B"):
        return None
    return 0 if label.startswith("A") else 1


def arm_caches(backend: GPUBackend, mapper: AffineMapper, pair: Mapping[str, Any],
               mismatch_pair: Mapping[str, Any] | None) -> dict[str, tuple[KVCache, KVCache]]:
    """四臂 + 控制，缓存按 pair 两侧独立 prefill；mismatch 来自显式另一对。"""
    out: dict[str, tuple[KVCache, KVCache]] = {}
    self_a = backend.pair_side_cache(pair, "A", "student")
    self_b = backend.pair_side_cache(pair, "B", "student")
    t_a = backend.pair_side_cache(pair, "A", "teacher")
    t_b = backend.pair_side_cache(pair, "B", "teacher")
    m_a, m_b = mapper.transform(t_a), mapper.transform(t_b)
    out["self"] = (self_a, self_b)
    out["identity"] = (backend.inject(self_a), backend.inject(self_b))
    out["joint"] = (m_a, m_b)
    out["k_only"] = (combine(m_a, self_a), combine(m_b, self_b))
    out["v_only"] = (combine(self_a, m_a), combine(self_b, m_b))
    out["control:random"] = (
        build_control(m_a, "random_gaussian", seed=0), build_control(m_b, "random_gaussian", seed=1))
    out["control:zero"] = (build_control(m_a, "zero", seed=0), build_control(m_b, "zero", seed=1))
    if mismatch_pair is not None:
        mo_a = mapper.transform(backend.pair_side_cache(mismatch_pair, "A", "teacher"))
        mo_b = mapper.transform(backend.pair_side_cache(mismatch_pair, "B", "teacher"))
        out["control:mismatch"] = (mo_a, mo_b)
    return out


def main() -> None:
    args = parse_args()
    t0 = time.time()
    cal_v, val_v = CELLS[args.cell]
    if args.cal_version and args.cal_version != cal_v:
        raise ValueError(f"--cal-version {args.cal_version} conflicts with cell {args.cell}")
    if args.val_version and args.val_version != val_v:
        raise ValueError(f"--val-version {args.val_version} conflicts with cell {args.cell}")
    paths = {
        "train-old": args.train_old, "val-old": args.val_old,
        "train-fixed": args.train_fixed, "val-fixed": args.val_fixed,
    }
    sha = {k: sha256_file(v) for k, v in paths.items()}
    # 版本名 -> paths 键（legacy=旧生成器对应 old 文件；fixed 同名）
    def path_key(which: str, ver: str) -> str:
        tag = "old" if ver == "legacy" else "fixed"
        return f"{which}-{tag}"
    cal_ver = args.cal_version or cal_v
    val_ver = args.val_version or val_v
    train_path = paths[path_key("train", cal_ver)]
    val_path = paths[path_key("val", val_ver)]

    trains = load_pairs(train_path)
    val_limit = args.smoke_n_val if args.smoke else None
    vals = load_pairs(val_path, limit=val_limit)

    # 旧数据历史缺陷登记（按格，legacy 版本）
    defect_warnings: list[str] = []
    if cal_v == "legacy" or val_v == "legacy":
        all_legacy = trains + vals
        dup = sum(1 for r in all_legacy if r.get("candidate_A") == r.get("candidate_B") and r.get("must_flip"))
        texts = [r.get("context_A", "") for r in all_legacy]
        dup_text = len(texts) - len(set(texts))
        defect_warnings.append(f"legacy_defects: degenerate_must_flip={dup}, dup_context_A={dup_text}")

    # 模型 + GPU 后端（固定 bf16/sdpa、等深 identity）
    tm, tt = load_model(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load_model(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers); n_t = int(tm.config.num_hidden_layers)
    if n_s != n_t:
        raise ValueError(f"audit entry requires equal depth, got teacher {n_t} vs student {n_s}")
    lmap = LayerMap(n_s, n_t, kind="identity")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)

    # 拟合 affine（唯一 mapper，逐层逐头 K/V，ridge λ=0.001）
    cal_docs = [{"doc_id": f"{p['pair_id']}-{s}", "text": p[f"context_{s}"]}
                for p in trains for s in ("A", "B")]
    ts = stack_caches(backend, cal_docs, "teacher")
    ss = stack_caches(backend, cal_docs, "student")
    mapper = AffineMapper(lam=RIDGE_LAM, channel="both").fit(ts, ss, layer_map=lmap)

    # 缓存恒等性 + Joint 输入审计（zero re-prefill），取 val 首对
    identity_ok = True
    joint_zero_ok = True
    sample = vals[0]
    doc_ids = torch.tensor(tt(sample["context_A"], add_special_tokens=False).input_ids,
                           device=args.device, dtype=torch.long)
    cache1 = backend.pair_side_cache(sample, "A", "teacher")
    cache2 = backend.pair_side_cache(sample, "A", "teacher")
    for layer in cache1.layers:
        identity_ok &= bool(np.array_equal(cache1.keys[layer], cache2.keys[layer]) and
                            np.array_equal(cache1.values[layer], cache2.values[layer]))
    q_ids = torch.tensor(st(sample["query"], add_special_tokens=False).input_ids,
                         device=args.device, dtype=torch.long)
    res = inject_and_generate(sm, mapper.transform(cache1), q_ids, attn_implementation=args.kernel)
    joint_zero_ok = bool(verify_zero_re_prefill(res, strict=False))
    if not identity_ok:
        defect_warnings.append("cache_identity_check=FAILED")
    if not joint_zero_ok:
        defect_warnings.append("joint_zero_re_prefill=FAILED")

    # 逐对四臂 + 控制打分
    rows: list[dict[str, Any]] = []
    for i, pair in enumerate(vals):
        mismatch = vals[(i + 1) % len(vals)] if len(vals) > 1 else None
        arms = arm_caches(backend, mapper, pair, mismatch)
        self_a, self_b = arms["self"]
        la_s = candidate_logits(backend, self_a, pair)
        lb_s = candidate_logits(backend, self_b, pair)
        for arm, (ca, cb) in arms.items():
            la = candidate_logits(backend, ca, pair)
            lb = candidate_logits(backend, cb, pair)
            rec = PairCFRecord(
                pair_id=pair["pair_id"], split=pair.get("split", "val"),
                slice_id=pair.get("slice_id", "F1"), cluster=pair.get("cluster", ""),
                self_logits_A=la_s, self_logits_B=lb_s,
                transfer_logits_A=la, transfer_logits_B=lb,
                correct_A=pair["correct_A"], correct_B=pair["correct_B"],
                must_flip=bool(pair.get("must_flip", True)),
                tau=1.0, self_threshold=0.1,
            ).compute()
            rows.append({
                "pair_id": pair["pair_id"], "sample_id": pair.get("sample_id", ""),
                "sample_hash": pair.get("sample_hash", ""), "version_tag": pair.get("version_tag", ""),
                "cluster": pair.get("cluster", ""), "slice_id": pair.get("slice_id", "F1"),
                "split": pair.get("split", "val"), "arm": arm,
                "E_CF": float(rec["E_CF"]), "dual_correct": float(rec["dual_correct"]),
                "flip_consistency": rec["flip_consistency"], "evaluable": rec["evaluable"],
                "D_self": float(rec["D_self"]), "D_trans": float(rec["D_trans"]),
            })

    from collections import defaultdict
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    summaries = {}
    for arm, ar in by_arm.items():
        dual = float(np.mean([r["dual_correct"] for r in ar]))
        summaries[arm] = {
            "n": len(ar), "dual_correct": dual,
            "E_CF_mean": float(np.mean([r["E_CF"] for r in ar])),
        }
    L = summaries["self"]["dual_correct"] - summaries["joint"]["dual_correct"]

    ctx = v2_context(
        args.run_id,
        {
            "stage": "audit_2x2", "gate": "GPU_followup_v2.7", "backend": "gpu",
            "cell": args.cell, "calibration_version": cal_v, "validation_version": val_v,
            "seed": args.seed, "bootstrap_seed": args.seed,
            "train_old": args.train_old, "val_old": args.val_old,
            "train_fixed": args.train_fixed, "val_fixed": args.val_fixed,
            "input_sha256": sha, "train_source": train_path, "val_source": val_path,
            "dtype": args.dtype, "kernel": args.kernel, "layer_map": lmap.to_dict(),
            "mapper": "affine_per_layer_head", "ridge_lambda": RIDGE_LAM, "scoring": "first_token",
            "n_train": len(trains), "n_val": len(vals),
            "identity_check": identity_ok, "joint_zero_re_prefill": joint_zero_ok,
            "defect_warnings": defect_warnings,
            "n_resamples": args.n_resamples, "tau": 1.0, "self_threshold": 0.1,
            "smoke": args.smoke, "zero_re_prefill": True,
            "criteria_source": "configs/prereg/gpu_followup_v2.7.yaml (frozen)",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        reports_root=(Path("/root/readkv/reports/_non_authoritative") if args.smoke else None),
        metadata={"stage": "audit_2x2", "backend": "gpu", "cell": args.cell,
                  "non_authoritative": args.smoke, "protocol_version": "2.7"},
    )
    ctx.write_scores(rows)
    metrics = {
        "run_id": args.run_id, "backend": "gpu", "protocol_version": "2.7",
        "cell": args.cell, "calibration_version": cal_v, "validation_version": val_v,
        "seed": args.seed, "dtype": args.dtype, "kernel": args.kernel,
        "zero_re_prefill": True, "input_sha256": sha,
        "n_train": len(trains), "n_val": len(vals),
        "identity_check": identity_ok, "joint_zero_re_prefill": joint_zero_ok,
        "defect_warnings": defect_warnings,
        "arms": summaries, "L_self_minus_joint": L,
        "n_scores": len(rows), "elapsed_sec": round(time.time() - t0, 1),
        "note": "2×2 审计格；冒烟标 non-authoritative；不重算冻结 CI、不恢复贡献、不碰封存 test。",
    }
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
