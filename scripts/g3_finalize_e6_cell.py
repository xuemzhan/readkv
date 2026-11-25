"""G3 FORMAL E6 cell verification + provenance supplement (authoritative).

Reads the artifacts already written by the frozen ``experiments/v3_e6_control_gpu.py``
for one formal cell, verifies the frozen E6 contract (params, bias, shape, epochs,
lr, 120 train pairs, KL objective, zero-re-prefill, Self/Identity, finite loss),
and writes ``g3_runtime_audit.json`` into the same run directory as a
post-finalize supplement.

The entry script hard-codes ``authoritative=false / pilot=true`` in metrics (G2
pilot boilerplate).  Per ``docs/decisions/v3_g2_release.md`` §4 these run-ids ARE
authoritative G3 formal cells; this supplement records that discrepancy openly
and does NOT edit the entry artifacts.

Usage::

    .venv/bin/python scripts/g3_finalize_e6_cell.py --run-id v3_E6_BM-MLP-KD_s0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.g3_audit_common import (  # noqa: E402
    code_record, env_record, model_record, sha256_file, variants_manifest_record,
)

EXPECTED_PARAMS = 7_340_032


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--wall-sec", type=float, default=None,
                   help="external wall-clock seconds for the cell process")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    out_dir = ROOT / "reports" / "runs" / a.run_id
    if not out_dir.is_dir():
        raise SystemExit(f"run directory does not exist: {out_dir}")
    out = out_dir / "g3_runtime_audit.json"
    if out.exists():
        raise SystemExit(f"REFUSE overwrite: {out}")
    cfg = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    met = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    man = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    scores = [json.loads(x) for x in (out_dir / "scores.jsonl").read_text(
        encoding="utf-8").splitlines() if x.strip()]

    if cfg.get("run_id") != a.run_id or met.get("run_id") != a.run_id:
        raise SystemExit("run_id mismatch across artifacts")
    if man.get("run_id") != a.run_id:
        raise SystemExit("manifest run_id mismatch")
    for name in ("config.json", "metrics.json", "scores.jsonl"):
        rec = next((f for f in man["files"] if f["name"] == name), None)
        if rec is None or rec["sha256"] != sha256_file(out_dir / name):
            raise SystemExit(f"manifest hash mismatch for {name}")
    exp = cfg["experiment_config"]
    checks = {
        "run_id_match": True,
        "manifest_hashes_verified": True,
        "params_exact": int(met["trainable_params"]) == EXPECTED_PARAMS == int(exp["trainable_params"]),
        "bias_zero": int(met["train_audit"]["parameter_structure"]["bias_params"]) == 0,
        "shape_exact": met["train_audit"]["parameter_structure"]["W_K"] == [28, 8, 128, 128]
        and met["train_audit"]["parameter_structure"]["W_V"] == [28, 8, 128, 128],
        "epochs_8": int(exp["epochs"]) == 8,
        "lr_1e3": float(exp["lr"]) == 1e-3,
        "n_train_120": int(met["n_train"]) == 120,
        "n_val_60": int(met["n_val"]) == 60,
        "mapper_v3_BM_MLP_KD": met["mapper"] == "v3-BM-MLP-KD"
        and exp["experiment"] == "v3-BM-MLP-KD",
        "zero_re_prefill": met["zero_re_prefill"] is True and cfg["zero_re_prefill"] is True,
        "self_identity_zero": abs(float(met["self_identity_max_abs_diff"])) <= 1e-4,
        "loss_finite": bool(met["train_audit"]["loss_finite"]),
        "joint_forward_audit_no_doc_tokens": bool(
            met["joint_audit_example"]["forward_audit"]["doc_tokens_fed_to_student"] == 0),
        "joint_cache_shapes_28x8x25x128": bool(
            met["joint_audit_example"]["n_cache_layers"] == 28
            and all(v == [8, 25, 128] for v in met["joint_audit_example"]["cache_shapes"].values())),
        "no_smoke": exp["smoke"] is False,
        "no_test_read": met["sealed_test_read"] is False and cfg["metadata"]["sealed_test_read"] is False,
        "scores_nonempty": len(scores) > 0,
        "all_scores_val": all(r.get("split") == "val" for r in scores),
    }
    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise SystemExit(f"G3 E6 formal cell contract FAILED: {failed}")

    provenance = {
        "g3_formal_cell": True,
        "authoritative": True,
        "pilot_only": False,
        "sealed_test_read": False,
        "run_id": a.run_id,
        "stage": "E6",
        "package": "GPU_followup_v3.0",
        "backend": "gpu",
        "criteria_source": "configs/prereg/gpu_followup_v3.0.yaml",
        "spec_source": "docs/decisions/v3_baseline_spec.md",
        "release_source": "docs/decisions/v3_g2_release.md",
        "entry_point": "experiments.v3_e6_control_gpu.main",
        "seed": int(cfg["seed"]),
        "dtype": cfg["dtype"],
        "kernel": cfg["kernel"],
        "device": cfg["device"],
        "seeds_frozen": [0, 1, 2],
        "model_pair": exp["model_pair"],
        "layer_map": {"kind": "identity", "n_student_layers": 28, "n_teacher_layers": 28},
        "environment": env_record(),
        "code_sha256": code_record({
            "scripts/g3_finalize_e6_cell.py": sha256_file(Path(__file__)),
        }),
        "model_provenance": model_record(teacher=exp["teacher"], student=exp["student"]),
        "data_variants_manifest": variants_manifest_record(),
        "input_sha256": exp["input_sha256"],
        "split_registration": exp["split_registration"],
        "contract_checks": checks,
        "frozen_contract": {
            "trainable_params": EXPECTED_PARAMS,
            "parameter_structure": met["train_audit"]["parameter_structure"],
            "loss_formula": met["train_audit"]["loss_formula"],
            "hyperparameters": met["train_audit"]["hyperparameters"],
            "n_optimizer_steps": met["train_audit"]["n_optimizer_steps"],
            "n_student_forwards_train": met["train_audit"]["n_student_forwards_train"],
            "n_student_forwards_eval": met["n_student_forwards_eval"],
            "n_captures_eval": met["n_captures_eval"],
            "n_scores": met["n_scores"],
            "memory": met["memory"],
            "train_sec": met["train_sec"],
            "entry_elapsed_sec": met["elapsed_sec"],
            "wall_sec_external": a.wall_sec,
            "loss_first": met["train_audit"]["loss_first"],
            "loss_last": met["train_audit"]["loss_last"],
            "loss_log": met["train_audit"]["loss_log"],
        },
        "entry_flag_discrepancy": {
            "metrics_authoritative_field": met.get("authoritative"),
            "metrics_pilot_field": met.get("pilot"),
            "metrics_note": met.get("note"),
            "explanation": (
                "experiments/v3_e6_control_gpu.py hard-codes authoritative=false / pilot=true "
                "and a G2-pilot note in metrics.json for every run. These are stale G2 boilerplate, "
                "not a property of this run. Per docs/decisions/v3_g2_release.md §4 this run-id is "
                "an AUTHORITATIVE G3 formal cell for the NEW v3 study. The entry artifacts are "
                "preserved byte-for-byte; no frozen file or entry script was edited."
            ),
        },
        "note": "Authoritative G3 formal cell for the NEW study, NOT the current TMLR manuscript.",
    }
    out.write_text(json.dumps(provenance, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps({"run_id": a.run_id, "status": "G3_E6_VERIFIED",
                      "out": str(out), "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
