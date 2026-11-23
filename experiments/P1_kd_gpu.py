"""P1 强行为基线 kd_only（及 cf_lite 消融）真实 GPU run。

kd_only = configs/eval.yaml 的 primary_baseline：在 train split 上以 L_KD 训练
KV Mapper（冻结学生，零 re-prefill），仅在 val/（或显式指定 split）评测。
沿用冻结的 phase1_benchmark_decision.yaml 判据，不新设规则、不触碰封存 test
（除非显式 --eval-splits test，且 δ 已锁定）。

用法：
  .venv/bin/python -m experiments.P1_kd_gpu --run-id p1_gpu_kdonly_mvp_seed0 \
      --teacher <1.7B> --student <0.6B> --seed 0
"""
from __future__ import annotations

import argparse
import json
import time

import torch

from readkv.config import load_config
from readkv.evaluate.cf_pipeline import CFPipelineConfig, run_cf_pipeline
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap
from readkv.runtime import v2_context
from readkv.train.kd_gpu import train_kd_gpu


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
    p.add_argument("--method", default="kd", choices=["kd", "cf_lite"])
    p.add_argument("--huber-delta", type=float, default=1.0, help="仅 cf_lite 使用；验证集网格锁定")
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--n-train", type=int, default=None)
    p.add_argument("--n-val", type=int, default=None)
    p.add_argument("--n-resamples", type=int, default=10000)
    p.add_argument("--eval-splits", default="val")
    p.add_argument("--skip-pipeline", action="store_true", help="只训练并保存 mapper 摘要（δ 网格用）")
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
    protocol = load_config("protocol"); ev = load_config("eval")
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

    from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
    trains = split_pairs(build_cf_pairs(sizes=sizes, seed=args.seed,
                                        model_pair=args.model_pair), "train")
    mapper = train_kd_gpu(
        backend, trains, method=args.method, epochs=args.epochs, lr=args.lr,
        lam_kd=1.0, lam_cf=1.0 if args.method == "cf_lite" else 0.0,
        lam_reg=1e-4, huber_delta=args.huber_delta,
        self_threshold=float(ev["self_threshold"]), seed=args.seed,
    )
    train_info = {
        "method": args.method, "epochs": args.epochs, "lr": args.lr,
        "huber_delta": args.huber_delta if args.method == "cf_lite" else None,
        "n_train_pairs": len(trains),
        "trainable_params": sum(p.numel() for p in mapper.module.parameters()),
        "train_sec": round(time.time() - t0, 1),
    }
    print(json.dumps({"run_id": args.run_id, "training": train_info}, ensure_ascii=False), flush=True)

    if args.skip_pipeline:
        return

    rules = load_config("prereg/phase1_benchmark_decision")["rules"]
    splits = tuple(args.eval_splits.split(","))
    cfg = CFPipelineConfig(
        sizes=sizes, seed=args.seed, n_resamples=args.n_resamples,
        tau=float(ev["tau"]), self_threshold=float(ev["self_threshold"]),
        method=args.method, mapper_kind=args.method,
        eval_splits=splits, decision_rules=rules,
    )
    ctx = v2_context(
        args.run_id,
        {
            "stage": "P1", "gate": "counterfactual_benchmark", "backend": "gpu",
            "teacher": args.teacher, "student": args.student,
            "model_pair": args.model_pair, "mapper": args.method,
            "layer_map": lmap.to_dict(),
            "primary_baseline": ev["primary_baseline"],
            "seeds": ev["seeds"], "seed": args.seed,
            "bootstrap_seed": args.seed,
            "dtype": args.dtype, "kernel": args.kernel,
            "n_resamples": args.n_resamples, "tau": ev["tau"],
            "self_threshold": ev["self_threshold"], "sizes": sizes,
            "eval_splits": list(splits), "training": train_info,
            "prereg": "configs/prereg/phase1_benchmark_decision.yaml (frozen protocol-v2.0)",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        metadata={"stage": "P1", "backend": "gpu", "method": args.method,
                  "protocol_version": "2.0"},
    )
    metrics = run_cf_pipeline(ctx, backend, cfg, baseline_mapper=mapper)
    metrics["training"] = train_info
    metrics["bootstrap_seed"] = args.seed
    metrics["elapsed_sec"] = round(time.time() - t0, 1)
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    j = metrics["arms"]["joint"]
    print(json.dumps({
        "run_id": args.run_id, "decision": metrics.get("decision"),
        "transfer_broken": metrics.get("transfer_broken"),
        "joint_E_CF": j["E_CF"], "identity_E_CF": metrics["arms"]["identity"]["E_CF"],
        "dual_correct": j["dual_correct"], "flip_consistency": j["flip_consistency"],
        "coverage": j["coverage"], "info_attribution": metrics["info_attribution"],
        "training": train_info,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
