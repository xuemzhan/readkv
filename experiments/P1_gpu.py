"""P1 基准（真实 GPU）：强基线（affine KV mapper）是否存在未被消除的反事实失真。

复用 evaluate/cf_pipeline.run_cf_pipeline 保证 score schema 与 mock 接线完全一致；
仅把 MockBackend 换成 GPUBackend（真实 Qwen3 前向）。判据来自冻结的
configs/prereg/phase1_benchmark_decision.yaml；tau/self_threshold/统计参数来自
configs/protocol.yaml 与 configs/eval.yaml，运行期不改。

只跑 val split（P1 基准），封存 test 留给 P3 封存测试。
"""
from __future__ import annotations

import argparse
import json
import time

import torch

from readkv.cache.cache import KVCache

from readkv.config import load_config
from readkv.evaluate.cf_pipeline import CFPipelineConfig, run_cf_pipeline
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap
from readkv.runtime import v2_context


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--teacher", required=True)
    p.add_argument("--student", required=True)
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--mapper", default="affine", choices=["affine", "ridge"])
    p.add_argument("--n-resamples", type=int, default=10000)
    p.add_argument("--n-train", type=int, default=None, help="调试用缩小校准集；默认用协议冻结规模")
    p.add_argument("--n-val", type=int, default=None, help="调试用缩小验证集")
    return p.parse_args()


def load(path, dtype, kernel, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                             attn_implementation=kernel).to(device)
    m.eval(); m.config.use_cache = True
    return m, tok


def main() -> None:
    args = parse_args()
    t0 = time.time()
    protocol = load_config("protocol")
    ev = load_config("eval")
    sizes = dict(protocol["data_sizes"])
    if args.n_train is not None:
        sizes["train"] = args.n_train
    if args.n_val is not None:
        sizes["val"] = args.n_val

    tm, tt = load(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers); n_t = int(tm.config.num_hidden_layers)
    lmap = LayerMap(n_s, n_t, kind="identity" if n_s == n_t else "proportional")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)

    # 校准：只用 train split 拟合 affine KV mapper（教师→学生，内容空间）
    from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
    trains = split_pairs(build_cf_pairs(sizes=sizes, seed=args.seed,
                                        model_pair=args.model_pair), "train")
    cal_docs = [{"doc_id": f"{p.pair_id}-{s}", "text": getattr(p, f"context_{s}")}
                for p in trains for s in ("A", "B")]
    tstack = stack_caches(backend, cal_docs, "teacher")
    sstack = stack_caches(backend, cal_docs, "student")
    mapper_cls = AffineMapper if args.mapper == "affine" else __import__(
        "readkv.mapper.representation", fromlist=["RidgeMapper"]).RidgeMapper
    mapper = mapper_cls(lam=1e-3, channel="both").fit(tstack, sstack, layer_map=lmap)

    class LayerMappedMapper:
        """非等深对：按 layer_map 先选教师层，再交给 per-student-layer mapper。"""

        def __init__(self, inner, layer_map):
            self.inner, self.layer_map = inner, layer_map

        def transform(self, teacher_cache):
            pairs = {s: teacher_cache.layer(int(self.layer_map(s)))
                     for s in range(int(self.layer_map.ns))}
            remapped = KVCache(
                {s: kv[0] for s, kv in pairs.items()},
                {s: kv[1] for s, kv in pairs.items()},
                dict(teacher_cache.metadata),
            )
            return self.inner.transform(remapped)

    mapper = LayerMappedMapper(mapper, lmap)

    rules = load_config("prereg/phase1_benchmark_decision")["rules"]
    cfg = CFPipelineConfig(
        sizes=sizes, seed=args.seed, n_resamples=args.n_resamples,
        tau=float(ev["tau"]), self_threshold=float(ev["self_threshold"]),
        method="none", mapper_kind=args.mapper,
        eval_splits=("val",), decision_rules=rules,
    )
    ctx = v2_context(
        args.run_id,
        {
            "stage": "P1", "gate": "counterfactual_benchmark", "backend": "gpu",
            "teacher": args.teacher, "student": args.student,
            "model_pair": args.model_pair, "mapper": args.mapper,
            "layer_map": lmap.to_dict(), "seeds": ev["seeds"],
            "seed": args.seed, "bootstrap_seed": args.seed,
            "dtype": args.dtype, "kernel": args.kernel,
            "n_resamples": args.n_resamples, "tau": ev["tau"],
            "self_threshold": ev["self_threshold"],
            "sizes": sizes, "eval_splits": ["val"],
            "primary_baseline": ev["primary_baseline"],
            "mapper_trainable_params": 0,
            "prereg": "configs/prereg/phase1_benchmark_decision.yaml (frozen protocol-v2.0)",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        metadata={"stage": "P1", "backend": "gpu", "protocol_version": "2.0"},
    )
    metrics = run_cf_pipeline(ctx, backend, cfg, baseline_mapper=mapper)
    metrics["n_captures"] = backend.n_captures
    metrics["n_injections"] = backend.n_injections
    metrics["elapsed_sec"] = round(time.time() - t0, 1)
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps({
        "run_id": args.run_id, "decision": metrics.get("decision"),
        "joint_E_CF": metrics["arms"].get("joint", {}).get("E_CF"),
        "identity_E_CF": metrics["arms"].get("identity", {}).get("E_CF"),
        "dual_correct": metrics["arms"].get("joint", {}).get("dual_correct"),
        "flip_consistency": metrics["arms"].get("joint", {}).get("flip_consistency"),
        "coverage": metrics["arms"].get("joint", {}).get("coverage"),
        "info_attribution": metrics["info_attribution"],
        "decision_facts": metrics.get("decision_facts"),
        "elapsed_sec": metrics["elapsed_sec"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
