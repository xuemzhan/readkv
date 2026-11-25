"""阶段 0：合并修正评测器与 identity 控制，产出统一底座。

默认 mock 后端可在 CPU 上跑完整管线；GPU 后端需先实现 models/hooks.py。
"""

from __future__ import annotations

import argparse
import json

from readkv.config import load_config, validate_gates
from readkv.evaluate.pipeline import PipelineConfig, run_pipeline
from readkv.runtime import RunContext

from experiments._common import add_backend_args, build_mock, require_gpu_backend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_args(parser, default_stage="stage0")
    parser.add_argument("--dry-run", action="store_true", help="只校验配置与门限")
    args = parser.parse_args()

    gates = load_config("gates")
    validate_gates(gates)
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": gates["version"]}, indent=2))
        return
    require_gpu_backend(args)

    backend, pipeline = build_mock(args)
    pipeline.controls = ("wrong_document", "random_gaussian", "zero", "shuffle_k", "shuffle_v")
    ctx = RunContext(args.run_id, {"stage": 0, "backend": args.backend, "gates": gates["version"]})
    metrics = run_pipeline(ctx, backend, pipeline)
    print(json.dumps({"run_id": ctx.run_id, "H1": metrics["H1"], "arms": list(metrics["arms"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
