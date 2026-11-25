"""阶段 1：对称 key 目标 A–E；判据见 configs/prereg/stage1_decision.yaml。

mock 后端把 E（注意力 KL 的梯度版）近似为 attention-weighted score 回归；
GPU 机器上应以可微学生 attention 的 KL 目标替换。
"""

from __future__ import annotations

import argparse
import json

from readkv.config import load_config
from readkv.evaluate.decision import match_decision
from readkv.evaluate.pipeline import fit_mapper, make_items, run_pipeline
from readkv.runtime import RunContext

from experiments._common import add_backend_args, build_mock, clone_pipeline, require_gpu_backend

VARIANTS = {
    "A": "affine_k",
    "B": "score_weighted",
    "C": "score",
    "D": "score_shuffled",
    "E": "score_weighted",   # mock 近似；真实应替换为 KL/SGD 目标
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_args(parser, default_stage="stage1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "variants": VARIANTS}, indent=2))
        return
    require_gpu_backend(args)

    backend, base_pipeline = build_mock(args)
    base_pipeline.value_mapper = "affine"
    items = make_items(backend, base_pipeline.n_docs, base_pipeline.seed)
    cal = items[: base_pipeline.n_calibration]

    results: dict[str, dict] = {}
    for name, kind in VARIANTS.items():
        pipeline = clone_pipeline(base_pipeline)
        mapper = fit_mapper(backend, cal, kind, seed=base_pipeline.seed)
        ctx = RunContext(f"{args.run_id}_{name}", {"stage": 1, "arm": name, "mapper": kind, "backend": args.backend})
        results[name] = run_pipeline(ctx, backend, pipeline, key_mapper_obj=mapper)

    c = results["C"]["arms"]["k_only"]["corrected_em"]["mean"]
    a = results["A"]["arms"]["k_only"]["corrected_em"]["mean"]
    b = results["B"]["arms"]["k_only"]["corrected_em"]["mean"]
    d = results["D"]["arms"]["k_only"]["corrected_em"]["mean"]
    c_tv = results["C"]["arms"]["k_only"]["routing_tv_mean"]
    a_tv = results["A"]["arms"]["k_only"]["routing_tv_mean"]
    facts = {
        "C_k_only_em_high": c >= 0.15,
        "C_beats_baselines": c > a and c > b,
        "D_not_better": d <= c,
        "routing_improved": c_tv < a_tv,
    }
    rules = load_config("prereg/stage1_decision")["rules"]
    decision = match_decision(rules, facts)

    summary = {
        "stage": 1,
        "backend": args.backend,
        "em": {name: r["arms"]["k_only"]["corrected_em"]["mean"] for name, r in results.items()},
        "routing_tv": {name: r["arms"]["k_only"]["routing_tv_mean"] for name, r in results.items()},
        "facts": facts,
        "decision": decision,
        "note": "mock 结果仅用于判据接线验证，不是科学结论",
    }
    ctx = RunContext(f"{args.run_id}_summary", {"stage": 1, "variants": VARIANTS})
    ctx.write_metrics("summary.json", summary)
    ctx.finalize()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
