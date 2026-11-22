"""P4 泛化：非等深 pair、未见模板/真实文档，最终封存测试。

报告跨设置稳定性、CI、失败边界与不利结果；不按测试结果调超参。
"""

from __future__ import annotations

import argparse
import json

from readkv.data.build_cf_pairs import build_cf_pairs
from readkv.evaluate.cf_pipeline import run_cf_pipeline

from experiments._common_v2 import add_v2_args, build_v2_mock, clone_cf, new_ctx, require_gpu


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P4")
    parser.add_argument("--pair", choices=["mvp", "main", "stress"], default="main")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": "2.0", "pair": args.pair}, indent=2))
        return
    require_gpu(args)

    backend, cfg = build_v2_mock(args)
    pairs = build_cf_pairs(sizes=cfg.sizes, seed=cfg.seed)
    # 按源文档/模板簇分组，报告分组 E_CF 与置信区间
    groups: dict[str, list[str]] = {}
    for p in pairs:
        groups.setdefault(p.template_family, []).append(p.pair_id)

    ctx = new_ctx(args, "P4", {"pair": args.pair})
    cfg2 = clone_cf(cfg, eval_splits=("test",), method="generalization")
    metrics = run_cf_pipeline(ctx, backend, cfg2)
    report = {
        "pair": args.pair,
        "template_groups": len(groups),
        "primary_endpoint": metrics["primary_endpoint"],
        "arms": {k: v.get("E_CF") for k, v in metrics["arms"].items()},
        "info_attribution": metrics["info_attribution"],
        "data_quality": metrics["data_quality"],
        "note": "mock 数字不是科学证据；真实结论需 GPU 后端与封存测试",
    }
    ctx.write_metrics("generalization.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
