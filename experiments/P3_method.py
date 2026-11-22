"""P3 方法：KD-only / CF-lite / CF-mech 严格配平预算并做消融。

放行条件：新方法相对最强基线有非偶然改进；否则停止扩大模型。
公平比较：同成对数据、同 Forward 次数、同可训练参数、同超参搜索预算。
"""

from __future__ import annotations

import argparse
import json

from readkv.config import load_config
from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
from readkv.evaluate.cf_pipeline import run_cf_pipeline
from readkv.train.cf_rct import train_cf_rct

from experiments._common_v2 import add_v2_args, build_v2_mock, clone_cf, new_ctx, require_gpu


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P3")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": "2.0",
                          "methods": ["kd", "cf_lite", "cf_mech"]}, indent=2))
        return
    require_gpu(args)

    backend, base_cfg = build_v2_mock(args)
    pairs = build_cf_pairs(sizes=base_cfg.sizes, seed=base_cfg.seed)
    cal = split_pairs(pairs, "train")
    rules = load_config("prereg/phase3_method_decision")["rules"]

    # 配平预算：三法共用 epochs/lr/rank
    budget = {"epochs": 4, "lr": 1e-3, "rank": 0, "seed": base_cfg.seed,
              "huber_delta": 1.0, "tau": base_cfg.tau}
    methods = ("kd", "cf_lite", "cf_mech")
    results = {}
    for method in methods:
        mapper = train_cf_rct(backend, cal, method=method, **budget)
        cfg = clone_cf(
            base_cfg, method=method, decision_rules=rules,
            mapper_kind="affine", cf_distortion=0.0,
        )
        import copy
        method_args = copy.copy(args)
        method_args.run_id = f"{args.run_id}_{method}"
        ctx = new_ctx(method_args, "P3", {"method": method, "budget": budget})
        metrics = run_cf_pipeline(ctx, backend, cfg, baseline_mapper=None, new_mapper=mapper)
        results[method] = metrics

    summary = {
        "stage": "P3",
        "budget": budget,
        "per_method": {
            m: {
                "joint_ecf": r["arms"].get("joint", {}).get("E_CF"),
                "new_ecf": r["arms"].get("new_joint", {}).get("E_CF"),
                "endpoint": r["primary_endpoint"],
                "decision": r["decision"],
            }
            for m, r in results.items()
        },
        "note": "mock 结果仅用于训练/对照接线验证，不是科学结论",
    }
    ctx = new_ctx(args, "P3", {"kind": "summary"})
    ctx.write_metrics("summary.json", summary)
    ctx.finalize()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
