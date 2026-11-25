"""阶段 4（选做）：路由引导选择性重算、hidden-state 探针、统计功效。

mock 后端可跑探针与成本核算；hidden-state 映射在 mock 下退化为 affine hidden
代理，真实实现需先捕获教师/学生 hidden states。
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from readkv.cache.cache import KVCache, estimate_bytes_per_token
from readkv.config import load_config
from readkv.evaluate.diagnostics import mapper_cost
from readkv.evaluate.pipeline import make_items, run_pipeline
from readkv.evaluate.probes import estimate_recompute_cost, selective_recompute_plan
from readkv.runtime import RunContext

from experiments._common import add_backend_args, build_mock, clone_pipeline, require_gpu_backend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_args(parser, default_stage="stage4")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        models = load_config("models")["models"]
        print(json.dumps({
            "status": "dry-run-ok",
            "recompute_cost_demo": estimate_recompute_cost(2, 6),
            "mapper_cost_demo": mapper_cost(models["1.7B"], bytes_per_token=estimate_bytes_per_token(models["1.7B"])),
        }, indent=2))
        return
    require_gpu_backend(args)

    backend, base_pipeline = build_mock(args)
    pipeline = clone_pipeline(base_pipeline, probes=("fraction_0.5", "top_third", "octant_3"))
    ctx = RunContext(f"{args.run_id}_probes", {"stage": 4, "backend": args.backend, "kind": "probes"})
    metrics = run_pipeline(ctx, backend, pipeline)

    items = make_items(backend, base_pipeline.n_docs, base_pipeline.seed)
    cal = items[: base_pipeline.n_calibration]
    first = backend.student_cache(cal[0])
    plan = selective_recompute_plan([0.1, 0.3, 0.2, 0.4, 0.05, 0.25], [0.9, 0.7, 0.8, 0.6, 0.95, 0.75], 2)
    cost = estimate_recompute_cost(len(plan), first.n_layers)

    summary = {
        "stage": 4,
        "backend": args.backend,
        "recompute_plan": plan,
        "recompute_cost": cost,
        "H3": metrics["H3"],
        "note": "mock 结果仅用于探针/成本核算接线验证；hidden-state 路线需 GPU 机器实现",
    }
    ctx = RunContext(f"{args.run_id}_summary", {"stage": 4})
    ctx.write_metrics("summary.json", summary)
    ctx.finalize()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
