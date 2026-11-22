"""阶段 2：consumer-space mapper 过 H1/H2/H3 三道门。

mock 后端中 WO-aware 用 consumer-space 近似（见 fit_mapper 文档），
GPU 机器上必须按论文 1 的 W_O,q 目标替换。
"""

from __future__ import annotations

import argparse
import json

from readkv.config import load_config
from readkv.evaluate.decision import match_decision
from readkv.evaluate.pipeline import make_items, run_pipeline
from readkv.runtime import RunContext

from experiments._common import add_backend_args, build_mock, clone_pipeline, require_gpu_backend

ARMS = {
    "affine": "affine",
    "attention_output_aware": "consumer",
    "wo_aware": "wo_aware",             # mock 近似
    "shuffled_target": "consumer_shuffled",
    "stage1_best_key": "score",         # 阶段 1 的 C
}

CONTROLS = ("wrong_document", "random_gaussian", "zero", "shuffle_k", "shuffle_v")
PROBES = ("fraction_0.5", "top_third", "octant_3")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_args(parser, default_stage="stage2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        cfg = load_config("stage2_audit")
        print(json.dumps({"status": "dry-run-ok", "mapper_arms": cfg["mapper_arms"]}, indent=2))
        return
    require_gpu_backend(args)

    backend, base_pipeline = build_mock(args)
    base_pipeline.key_mapper = "affine"
    items = make_items(backend, base_pipeline.n_docs, base_pipeline.seed)
    cal = items[: base_pipeline.n_calibration]

    results: dict[str, dict] = {}
    for name, kind in ARMS.items():
        pipeline = clone_pipeline(
            base_pipeline,
            value_mapper=kind,
            controls=CONTROLS,
            probes=PROBES,
        )
        key_mapper = None
        if name == "stage1_best_key":
            from readkv.evaluate.pipeline import fit_mapper

            key_mapper = fit_mapper(backend, cal, kind, seed=base_pipeline.seed)
            pipeline = clone_pipeline(pipeline, value_mapper="affine")
        ctx = RunContext(f"{args.run_id}_{name}", {"stage": 2, "arm": name, "mapper": kind, "backend": args.backend})
        results[name] = run_pipeline(ctx, backend, pipeline, key_mapper_obj=key_mapper)

    h2_any = any(
        (r["arms"].get(a, {}).get("h2", {}).get("passed", False))
        for r in results.values()
        for a in ("v_only", "joint")
    )
    chg_any = any(
        r["arms"].get(a, {}).get("h2", {}).get("point", 0.0) > 0
        for r in results.values()
        for a in ("v_only", "joint")
    )
    facts = {"h2_pass_any": h2_any, "any_positive_chg": chg_any}
    decision = match_decision(load_config("prereg/stage2_decision")["rules"], facts)

    summary = {
        "stage": 2,
        "backend": args.backend,
        "arms": {
            name: {
                "H1": r["H1"],
                "v_only_h2": r["arms"]["v_only"]["h2"],
                "joint_h2": r["arms"]["joint"]["h2"],
                "CSG": r["CSG"],
                "H3": r["H3"],
            }
            for name, r in results.items()
        },
        "facts": facts,
        "decision": decision,
        "note": "mock 结果仅用于三道门与决策树接线验证，不是科学结论",
    }
    ctx = RunContext(f"{args.run_id}_summary", {"stage": 2, "arms": ARMS})
    ctx.write_metrics("summary.json", summary)
    ctx.finalize()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
