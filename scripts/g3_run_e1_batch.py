"""G3 E1 batch runner: serial, hash-bound, stop-on-failure.

Runs the 30 GPU cells of v3.0 §3 (Panel A/B x 5 variants x seeds 0/1/2).
degenerate_only is a label-only defect and is NOT a GPU cell (CPU replay handled separately).
All model references use SHA-named symlinks so the frozen entry never sees a bare `master` alias.

Non-authoritative driver script: does not edit configs/prereg, papers, data, or frozen decisions.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/readkv")
PY = ROOT / ".venv/bin/python"
VARIANTS = (
    "legacy_bundle", "dedup_only", "entity_disjoint_only",
    "template_disjoint_only", "fully_repaired",
)
CLEAN = "fully_repaired"
SEEDS = (0, 1, 2)
PANELS = ("A", "B")
LINKS = ROOT / "reports/_non_authoritative/v3_env/pinned_links"
LOGS = ROOT / "reports/_non_authoritative/v3_g3_e1_logs"
SUMMARY = ROOT / "reports/review/v3_g3_e1_batch_summary.json"
MODELS = ROOT / "reports/_non_authoritative/v3_env/model_manifest.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pinned_link(model_id: str) -> Path:
    data = json.loads(MODELS.read_text(encoding="utf-8"))["models"][model_id]
    snap = Path(data["local_dir"])
    tag = data["files"]["config.json"]["sha256"][:12]
    link = LINKS / f"{model_id.split('/')[-1]}-{tag}"
    if not link.exists():
        link.symlink_to(snap, target_is_directory=True)
    return link


def main() -> int:
    LINKS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    teacher = pinned_link("Qwen/Qwen3-1.7B")
    student = pinned_link("Qwen/Qwen3-0.6B")
    manifest = ROOT / "data/variants_v3/manifest.json"
    manifest_hash = sha(manifest)
    results: list[dict] = []
    total = len(PANELS) * len(VARIANTS) * len(SEEDS)
    idx = 0
    for panel in PANELS:
        for variant in VARIANTS:
            for seed in SEEDS:
                idx += 1
                if panel == "A":
                    train_v, val_v = variant, CLEAN
                else:
                    train_v, val_v = CLEAN, variant
                train = ROOT / f"data/variants_v3/{train_v}/train_seed{seed}.jsonl"
                val = ROOT / f"data/variants_v3/{val_v}/val_seed{seed}.jsonl"
                # prereg §3: Panel B entity/template variants change val text -> explicit
                # authorization required, recorded by the entry as data_task_change=true.
                needs_flag = panel == "B" and variant in {
                    "entity_disjoint_only", "template_disjoint_only",
                }
                run_id = f"v3_E1_{panel}_{variant}_s{seed}" + ("_r2" if needs_flag else "")
                out = ROOT / "reports/runs" / run_id
                if (out / "scores.jsonl").exists():
                    print(f"[{idx}/{total}] SKIP (already has scores.jsonl): {run_id}", flush=True)
                    results.append({
                        "run_id": run_id, "panel": panel, "variant": variant, "seed": seed,
                        "returncode": 0, "status": "resumed_skip", "log": None,
                        "train": str(train.relative_to(ROOT)), "val": str(val.relative_to(ROOT)),
                    })
                    continue
                log = LOGS / f"{run_id}.log"
                cmd = [
                    str(PY), "-m", "experiments.e1_variant_gpu",
                    "--run-id", run_id,
                    "--variant", variant, "--panel", panel,
                    "--train-path", str(train), "--train-sha256", sha(train),
                    "--val-path", str(val), "--val-sha256", sha(val),
                    "--manifest-path", str(manifest), "--manifest-sha256", manifest_hash,
                    "--seed", str(seed),
                    "--model-pair", "qwen3-1.7b-to-0.6b",
                    "--teacher", str(teacher), "--student", str(student),
                    "--mapper", "affine", "--ridge-lambda", "1e-3",
                    "--dtype", "bfloat16", "--kernel", "sdpa", "--device", "cuda",
                    "--n-resamples", "10000",
                ]
                if needs_flag:
                    cmd.append("--allow-input-change-gpu-forward")
                print(f"[{idx}/{total}] {run_id}", flush=True)
                with log.open("w", encoding="utf-8") as fh:
                    rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
                results.append({
                    "run_id": run_id, "panel": panel, "variant": variant, "seed": seed,
                    "returncode": rc, "log": str(log.relative_to(ROOT)),
                    "train": str(train.relative_to(ROOT)), "val": str(val.relative_to(ROOT)),
                })
                SUMMARY.parent.mkdir(parents=True, exist_ok=True)
                SUMMARY.write_text(json.dumps({
                    "completed": len(results), "total": total, "results": results,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                if rc != 0:
                    print(f"STOP: {run_id} failed (rc={rc}), see {log}", flush=True)
                    return 1
    print(f"DONE: {total} cells", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
