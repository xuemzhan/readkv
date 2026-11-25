"""G3 batch-1 provenance helper (engineer instrument; NOT a frozen entry).

Purpose: record, for every authoritative G3 formal cell, the full run config
provenance required by configs/prereg/gpu_followup_v3.0.yaml §2 `fixed_before_run`:
data hashes, snapshot directories + per-file SHA, code-entry SHA, environment
versions, seeds, dtype/kernel/layer map.  This module is read-only with respect to
all frozen files and writes nothing by itself.

It is used by ``scripts/g3_run_e5_cell.py``, ``scripts/g3_injection_audit.py`` and
``scripts/g3_finalize_e6_cell.py``.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
MODEL_MANIFEST = "reports/_non_authoritative/v3_env/model_manifest.json"
VARIANTS_MANIFEST = "data/variants_v3/manifest.json"

CODE_PATHS = (
    "experiments/P1_gpu.py",
    "experiments/v3_e6_control_gpu.py",
    "src/readkv/data/build_cf_pairs.py",
    "src/readkv/evaluate/cf_pipeline.py",
    "src/readkv/models/hooks.py",
    "src/readkv/models/gpu_backend.py",
    "src/readkv/models/layer_map.py",
    "src/readkv/mapper/representation.py",
    "src/readkv/mapper/mlp_kd.py",
    "src/readkv/runtime/context.py",
    "configs/protocol.yaml",
    "configs/eval.yaml",
    "configs/prereg/gpu_followup_v3.0.yaml",
    "docs/decisions/v3_baseline_spec.md",
    "docs/decisions/v3_g2_release.md",
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _driver() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip().splitlines()
        return out[0] if out else "unknown"
    except Exception:
        return "unknown"


def env_record() -> dict[str, Any]:
    import numpy as np
    import torch
    import transformers

    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "transformers": transformers.__version__,
        "numpy": np.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
        "nvidia_driver": _driver(),
        "dtype": "bfloat16",
        "kernel": "sdpa",
        "seeds": [0, 1, 2],
        "scheduling": "serial_single_gpu",
    }


def code_record(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    out = {p: sha256_file(ROOT / p) for p in CODE_PATHS}
    if extra:
        out.update(dict(extra))
    return out


def model_record(*, teacher: str | Path, student: str | Path,
                 manifest: str = MODEL_MANIFEST) -> dict[str, Any]:
    """Bind a SHA-named symlink dir to the frozen model_manifest file hashes."""
    man_path = ROOT / manifest
    man = json.loads(man_path.read_text(encoding="utf-8"))
    by_local_dir = {v["local_dir"]: (k, v) for k, v in man["models"].items()}
    out: dict[str, Any] = {
        "model_manifest_path": manifest,
        "model_manifest_sha256": sha256_file(man_path),
        "downloaded_at_utc": man.get("downloaded_at_utc"),
        "source": man.get("source"),
    }
    for role, path in (("teacher", teacher), ("student", student)):
        p = Path(path)
        resolved = p.resolve()
        parts_lower = {x.lower() for x in p.parts}
        cfg_sha = sha256_file(p / "config.json")
        name = None
        entry = None
        for key, value in by_local_dir.values():
            if value["files"]["config.json"]["sha256"] == cfg_sha:
                name, entry = key, value
                break
        if entry is None:
            raise ValueError(f"{role} config.json SHA {cfg_sha} not found in frozen model manifest")
        if resolved != Path(entry["local_dir"]).resolve():
            raise ValueError(f"{role} symlink resolves outside the frozen snapshot: {resolved}")
        if parts_lower & {"master", "main", "latest"}:
            raise ValueError(f"{role} path is a bare mutable alias: {path}")
        mismatches = []
        for fname, meta in entry["files"].items():
            computed = sha256_file(resolved / fname)
            if computed != meta["sha256"]:
                mismatches.append({"file": fname, "expected": meta["sha256"], "computed": computed})
        out[role] = {
            "model": name,
            "path": str(p),
            "resolved_snapshot_dir": str(resolved),
            "sha_named_pin": True,
            "file_count": int(entry["file_count"]),
            "total_bytes": int(entry["total_bytes"]),
            "config_json_sha256_computed": cfg_sha,
            "all_files_sha256_from_manifest": {
                f: m["sha256"] for f, m in sorted(entry["files"].items())
            },
            "per_file_hash_mismatches": mismatches,
        }
        if mismatches:
            raise ValueError(f"{role} model file hash mismatch: {mismatches}")
    return out


def variants_manifest_record() -> dict[str, Any]:
    p = ROOT / VARIANTS_MANIFEST
    return {"path": VARIANTS_MANIFEST, "sha256": sha256_file(p)}


def cf_data_fingerprint(*, seed: int, sizes: Mapping[str, int],
                        model_pair: str | None = None,
                        splits: tuple[str, ...] = ("train", "val")) -> dict[str, Any]:
    """Hash the deterministic generated pairs that a G3 cell actually fits/evaluates.

    No test split is read or hashed here.  ``model_pair`` only populates a
    metadata field in build_cf_pairs (verified at src/readkv/data/build_cf_pairs.py:474)
    and never changes text, split, labels or candidate order.
    """
    from dataclasses import asdict

    from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs

    # Generate ONLY the splits we fingerprint; no test/probe pairs are built here.
    reduced_sizes = {s: (int(sizes.get(s, 0)) if s in splits else 0) for s in splits}
    kwargs: dict[str, Any] = {"sizes": reduced_sizes, "seed": int(seed)}
    if model_pair is not None:
        kwargs["model_pair"] = model_pair
    pairs = build_cf_pairs(**kwargs)
    out: dict[str, Any] = {
        "generator": "src/readkv/data/build_cf_pairs.py",
        "seed": int(seed),
        "sizes_generated": reduced_sizes,
        "sizes_frozen_full": dict(sizes),
        "model_pair_argument": model_pair,
        "note": "model_pair sets metadata only; it does not change text/split/label/candidate order",
        "splits": {},
    }
    for split in splits:
        rows = [asdict(p) for p in split_pairs(pairs, split)]
        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        out["splits"][split] = {
            "n": len(rows),
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    return out
