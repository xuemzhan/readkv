"""P1 基准：建立反事实数据与强基线，判断是否存在未被消除的失真。

放行条件：确认存在未被强基线消除的反事实失真；否则按决策树转向边界研究。
"""

from __future__ import annotations

import argparse
import json

from readkv.config import load_config
from readkv.evaluate.cf_pipeline import run_cf_pipeline

from experiments._common_v2 import add_v2_args, build_v2_mock, clone_cf, new_ctx, require_gpu


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P1")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": "2.0", "gate": "counterfactual_benchmark"}, indent=2))
        return
    require_gpu(args)

    backend, cfg = build_v2_mock(args)
    rules = load_config("prereg/phase1_benchmark_decision")["rules"]
    ctx = new_ctx(args, "P1")
    metrics = run_cf_pipeline(ctx, backend, clone_cf(cfg, decision_rules=rules))
    print(json.dumps({
        "run_id": ctx.run_id,
        "decision": metrics["decision"],
        "joint_E_CF": metrics["arms"].get("joint", {}).get("E_CF"),
        "identity_E_CF": metrics["arms"].get("identity", {}).get("E_CF"),
        "info_attribution": metrics["info_attribution"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
