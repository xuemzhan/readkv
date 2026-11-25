"""G3 FORMAL E5 cell runner (authoritative; thin instrument around P1_gpu.py).

Runs ONE G3 formal cell by calling the frozen ``experiments.P1_gpu.main()`` with
the caller's exact argv (no entry-script edits, no data/test changes).  Before
``RunContext.finalize()`` it writes ``g3_runtime_audit.json`` into the same run
directory so the entry's own manifest hashes the supplement too.

Usage (one cell, run serially)::

    .venv/bin/python scripts/g3_run_e5_cell.py \
      --run-id v3_E5_affine_s0 --teacher <sha-named-4B> --student <sha-named-1.7B> \
      --model-pair qwen3-4b-to-1.7b --mapper affine --seed 0 \
      --dtype bfloat16 --kernel sdpa --device cuda

Hard rules enforced here: no bare master alias, no --n-train/--n-val, no test
split, no overwrite of an existing run directory.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.g3_audit_common import (  # noqa: E402
    cf_data_fingerprint, code_record, env_record, model_record,
    variants_manifest_record,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import torch

    from readkv.runtime.context import RunContext
    from experiments.P1_gpu import main as p1_main

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw_argv)
    out_dir = ROOT / "reports" / "runs" / args.run_id
    if out_dir.exists():
        raise SystemExit(f"REFUSE overwrite: {out_dir} already exists")

    for label, path in (("teacher", args.teacher), ("student", args.student)):
        parts = {x.lower() for x in Path(path).parts}
        if parts & {"master", "main", "latest"}:
            raise SystemExit(f"REFUSE bare alias for {label}: {path}")
    if any(a in raw_argv for a in ("--n-train", "--n-val")):
        raise SystemExit("REFUSE --n-train/--n-val in a formal G3 cell")

    # Full frozen protocol sizes (the entry reads configs/protocol.yaml itself).
    from readkv.config import load_config
    sizes = dict(load_config("protocol")["data_sizes"])
    provenance = {
        "g3_formal_cell": True,
        "authoritative": True,
        "pilot_only": False,
        "sealed_test_read": False,
        "run_id": args.run_id,
        "stage": "E5",
        "package": "GPU_followup_v3.0",
        "backend": "gpu",
        "criteria_source": "configs/prereg/gpu_followup_v3.0.yaml",
        "release_source": "docs/decisions/v3_g2_release.md",
        "entry_point": "experiments.P1_gpu.main",
        "entry_wrapper": "scripts/g3_run_e5_cell.py",
        "argv": raw_argv,
        "seed": args.seed,
        "dtype": args.dtype,
        "kernel": args.kernel,
        "device": args.device,
        "mapper": args.mapper,
        "model_pair": args.model_pair,
        "n_resamples": args.n_resamples,
        "sizes": sizes,
        "environment": env_record(),
        "code_sha256": code_record({
            "scripts/g3_run_e5_cell.py": "self",
        }),
        "model_provenance": model_record(teacher=args.teacher, student=args.student),
        "data_variants_manifest": variants_manifest_record(),
        "generated_pair_fingerprint_default_pair": cf_data_fingerprint(
            seed=args.seed, sizes=sizes),
        "generated_pair_fingerprint_explicit_pair": cf_data_fingerprint(
            seed=args.seed, sizes=sizes, model_pair=args.model_pair),
        "model_pair_effect": "metadata-only; text/split/label/candidate order unchanged (build_cf_pairs.py:474)",
        "note": "Authoritative G3 formal cell for the NEW v3 study, NOT the current TMLR manuscript.",
    }
    # Self-hash of the wrapper (filled after we know our own bytes).
    provenance["code_sha256"]["scripts/g3_run_e5_cell.py"] = __import__(
        "hashlib").sha256(Path(__file__).read_bytes()).hexdigest()

    orig_finalize = RunContext.finalize
    state: dict[str, object] = {"t0": 0.0}

    def finalize_with_audit(self: RunContext) -> Path:  # type: ignore[valid-type]
        metrics_path = self.out_dir / "metrics.json"
        entry_metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {}
        audit = dict(provenance)
        audit["entry_metrics_snapshot"] = {
            "elapsed_sec": entry_metrics.get("elapsed_sec"),
            "n_captures": entry_metrics.get("n_captures"),
            "n_injections": entry_metrics.get("n_injections"),
            "joint_E_CF_mean": (entry_metrics.get("arms", {}).get("joint", {}).get("E_CF") or {}).get("mean"),
            "identity_E_CF_mean": (entry_metrics.get("arms", {}).get("identity", {}).get("E_CF") or {}).get("mean"),
            "joint_dual_correct": entry_metrics.get("arms", {}).get("joint", {}).get("dual_correct"),
            "self_dual_correct": entry_metrics.get("arms", {}).get("self", {}).get("dual_correct"),
            "decision": entry_metrics.get("decision"),
            "data_quality_gate": (entry_metrics.get("data_quality") or {}).get("quality_gate"),
        }
        audit["cuda_peak_allocated_bytes"] = int(torch.cuda.max_memory_allocated())
        audit["cuda_peak_reserved_bytes"] = int(torch.cuda.max_memory_reserved())
        audit["cuda_peak_allocated_mib"] = round(audit["cuda_peak_allocated_bytes"] / 1024 ** 2, 1)
        audit["cuda_peak_reserved_mib"] = round(audit["cuda_peak_reserved_bytes"] / 1024 ** 2, 1)
        # Wall clock is sampled at finalize time (inside p1_main), because the
        # audit file is written there. The post-main sample below is kept for
        # the runner stdout only.
        audit["wrapper_wall_sec_at_finalize"] = round(
            time.time() - float(state["t0"]), 1)
        (self.out_dir / "g3_runtime_audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        return orig_finalize(self)

    RunContext.finalize = finalize_with_audit  # type: ignore[assignment]
    sys.argv = [sys.argv[0]] + raw_argv
    state["t0"] = time.time()
    p1_main()
    print(json.dumps({"run_id": args.run_id, "status": "G3_FORMAL_COMPLETE",
                      "run_dir": str(out_dir),
                      "wrapper_wall_sec_at_return": round(time.time() - float(state["t0"]), 1)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
