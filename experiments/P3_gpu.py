"""P3 方法层（真实 GPU）入口：kd / cf_lite / cf_mech。

沿用 train/cf_rct.py 训练骨架与 evaluate.cf_pipeline 评测口径；主终点 = 封存 test 上
cf 方法相对 primary_baseline=kd_only 的**成对 E_CF 差异**（paired 簇级 bootstrap，
CI 上界<0 才算改善）——与 P1/P2 的「相对 Self」口径严格区分。

配置来自冻结判据：δ=0.5（v2.2）、τ=1.0、self_threshold=0.1、λ_KD=1.0；
train120/val60/test300，8 epoch，bf16/sdpa，n_resamples=10000，≥3 seed。
封存 test 仅最终评测读取；烟测（--smoke）只用 val、不读 test、non-authoritative。

用法（烟测）：
  .venv/bin/python -m experiments.P3_gpu --run-id p3_smoke_cflite_seed0 \\
      --teacher <1.7B> --student <0.6B> --method cf_lite --seed 0 --smoke
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import torch

from readkv.config import load_config
from readkv.evaluate.cf_pipeline import CFPipelineConfig, run_cf_pipeline
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap
from readkv.models.loader import freeze_model
from readkv.runtime import v2_context
from readkv.train.cf_rct import train_cf_rct

P3_ROOT = Path("/root/readkv/reports/_non_authoritative")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--teacher", required=True)
    p.add_argument("--student", required=True)
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b")
    p.add_argument("--method", default="cf_lite", choices=["kd", "cf_lite", "cf_mech"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--rank", type=int, default=0)
    p.add_argument("--lam-kd", type=float, default=1.0)
    p.add_argument("--lam-cf", type=float, default=1.0)
    p.add_argument("--lam-local", type=float, default=0.0)
    p.add_argument("--lam-reg", type=float, default=1e-4)
    p.add_argument("--huber-delta", type=float, default=0.5, help="v2.2 冻结值，不从 CLI 改")
    p.add_argument("--n-train", type=int, default=120)
    p.add_argument("--n-val", type=int, default=60)
    p.add_argument("--n-test", type=int, default=300)
    p.add_argument("--n-resamples", type=int, default=10000)
    p.add_argument("--baseline-mapper-path", default=None,
                   help="同 seed 的 kd_only mapper 路径；用于 cf 方法的主终点配对（正式 run 必填）")
    p.add_argument("--save-mapper-path", default=None, help="保存本 run mapper 的 .pt 路径")
    p.add_argument("--smoke", action="store_true", help="烟测：val-only、小规模、non-authoritative")
    return p.parse_args()


def load(path, dtype, kernel, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                             attn_implementation=kernel).to(device)
    freeze_model(m)  # 学生/教师主权重全部冻结
    m.eval(); m.config.use_cache = True
    return m, tok


def verify_gradient_flow(backend: GPUBackend, module: Any, sample_pair: dict, device) -> dict:
    """可微 readout 梯度验证：mapper 有非零梯度、学生权重梯度为 None/0。"""
    for p in module.parameters():
        p.grad = None
    for p in backend.student.parameters():
        p.grad = None
    t = backend.pair_side_cache(sample_pair, "A", "teacher")
    mapped = module.map_cache(t)
    qdoc = {"query": sample_pair["query"], "text": sample_pair["query"]}
    cands = (sample_pair["candidate_A"], sample_pair["candidate_B"])
    logits = backend.torch_candidate_logits(mapped, qdoc, cands)
    loss = logits.sum()
    loss.backward()
    mapper_grads = [p.grad for p in module.parameters() if p.grad is not None]
    mapper_norm = float(sum(g.norm().item() for g in mapper_grads))
    nonzero_mapper = sum(1 for g in mapper_grads if float(g.abs().sum()) > 0)
    student_grads = [p.grad for p in backend.student.parameters() if p.grad is not None]
    student_norm = float(sum(g.norm().item() for g in student_grads))
    return {
        "mapper_grad_norm": mapper_norm,
        "mapper_params_with_nonzero_grad": nonzero_mapper,
        "mapper_params_total": sum(1 for _ in module.parameters()),
        "student_grad_tensors": len(student_grads),
        "student_grad_norm": student_norm,
        "mapper_backprop_ok": bool(mapper_norm > 0 and nonzero_mapper > 0),
        "student_frozen_ok": bool(student_norm == 0.0 and len(student_grads) == 0),
        "loss_value": float(loss.detach()),
    }


def main() -> None:
    args = parse_args()
    t0 = time.time()
    ev_cfg = load_config("eval")
    proto = load_config("protocol")
    sizes = {"train": args.n_train, "val": args.n_val, "test": args.n_test, "probe": 0, "real": 0}
    if args.smoke:  # 烟测：只用 train/val，不读 test 标签
        sizes = {"train": args.n_train, "val": args.n_val, "test": 0, "probe": 0, "real": 0}

    tm, tt = load(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers); n_t = int(tm.config.num_hidden_layers)
    lmap = LayerMap(n_s, n_t, kind="identity" if n_s == n_t else "proportional")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)

    from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
    pairs = build_cf_pairs(sizes=sizes, seed=args.seed, model_pair=args.model_pair)
    trains = split_pairs(pairs, "train")

    # 学生 Forward 计数（训练 + 评测），预算配平证据
    counter = {"n": 0}
    def _count_forward(module, a, k):
        counter["n"] += 1
    fh = sm.register_forward_pre_hook(_count_forward, with_kwargs=True)

    grad_check = None
    # 训练（真实可微 readout 经 torch_candidate_logits 回传到 mapper）
    train_start = time.time()
    mapper = train_cf_rct(
        backend, trains, method=args.method, epochs=args.epochs, lr=args.lr,
        lam_kd=args.lam_kd, lam_cf=args.lam_cf if args.method != "kd" else 0.0,
        lam_local=args.lam_local if args.method == "cf_mech" else 0.0,
        lam_reg=args.lam_reg, huber_delta=args.huber_delta,
        tau=float(ev_cfg["tau"]), rank=args.rank, seed=args.seed,
    )
    train_sec = time.time() - train_start

    if args.smoke:
        grad_check = verify_gradient_flow(backend, mapper.module, trains[0].as_record(), args.device)

    # 主终点配对基线：cf 方法用同 seed 的 kd mapper；kd 方法自比（endpoint=0）
    baseline_mapper = mapper
    baseline_source = "self (kd_only is primary baseline)" if args.method == "kd" else "self (smoke, no external baseline)"
    if not args.smoke and args.method != "kd" and args.baseline_mapper_path:
        baseline_mapper = type(mapper).load(args.baseline_mapper_path)
        baseline_source = args.baseline_mapper_path

    rules = load_config("prereg/phase3_method_decision")["rules"]
    eval_splits = ("val",) if args.smoke else ("val", "test")
    cfg = CFPipelineConfig(
        sizes=sizes, seed=args.seed, n_resamples=args.n_resamples,
        tau=float(ev_cfg["tau"]), self_threshold=float(ev_cfg["self_threshold"]),
        method=args.method, mapper_kind=args.method,
        eval_splits=eval_splits, decision_rules=rules,
    )
    report_root = P3_ROOT if args.smoke else None
    ctx = v2_context(
        args.run_id,
        {
            "stage": "P3", "gate": "method", "backend": "gpu", "method": args.method,
            "teacher": args.teacher, "student": args.student, "model_pair": args.model_pair,
            "layer_map": lmap.to_dict(), "seed": args.seed, "bootstrap_seed": args.seed,
            "dtype": args.dtype, "kernel": args.kernel, "device": args.device,
            "epochs": args.epochs, "lr": args.lr, "rank": args.rank,
            "huber_delta": args.huber_delta, "tau": ev_cfg["tau"],
            "self_threshold": ev_cfg["self_threshold"], "lambda": {
                "KD": args.lam_kd, "CF": args.lam_cf if args.method != "kd" else 0.0,
                "local": args.lam_local if args.method == "cf_mech" else 0.0,
                "reg": args.lam_reg},
            "budget": {
                "epochs": args.epochs, "lr": args.lr, "rank": args.rank,
                "trainable_params": sum(p.numel() for p in mapper.module.parameters()),
                "student_forward_calls": counter["n"],
                "train_sec": round(train_sec, 1),
                "seed": args.seed,
            },
            "primary_endpoint_definition": (
                "sealed test paired E_CF difference (cf method vs primary_baseline=kd_only), "
                "cluster paired bootstrap, 95% CI upper < 0; distinct from P1/P2 relative-Self E_CF"
            ),
            "baseline_mapper_source": baseline_source,
            "eval_splits": list(eval_splits),
            "n_resamples": args.n_resamples,
            "zero_re_prefill": True,
            "smoke": args.smoke,
            "prereg": "configs/prereg/phase3_method_decision.yaml + phase3_loss_config_v2.2.yaml (frozen)",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True, reports_root=report_root,
        metadata={"stage": "P3", "backend": "gpu", "method": args.method,
                  "non_authoritative": args.smoke, "protocol_version": "2.0"},
    )
    fh.remove()
    metrics = run_cf_pipeline(ctx, backend, cfg, baseline_mapper=baseline_mapper, new_mapper=mapper)
    metrics["budget"] = {
        "epochs": args.epochs, "lr": args.lr, "rank": args.rank,
        "trainable_params": sum(p.numel() for p in mapper.module.parameters()),
        "student_forward_calls": counter["n"], "train_sec": round(train_sec, 1),
    }
    metrics["gradient_check"] = grad_check
    metrics["method"] = args.method
    metrics["primary_endpoint_definition"] = "sealed-test paired E_CF difference vs kd_only (CI upper<0)"
    metrics["elapsed_sec"] = round(time.time() - t0, 1)
    if args.save_mapper_path:
        mapper.save(args.save_mapper_path)
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps({
        "run_id": args.run_id, "non_authoritative": args.smoke,
        "method": args.method, "decision": metrics.get("decision"),
        "primary_endpoint": metrics.get("primary_endpoint"),
        "gradient_check": grad_check, "budget": metrics["budget"],
        "elapsed_sec": metrics["elapsed_sec"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
