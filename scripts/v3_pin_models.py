"""G1: download models from modelscope.cn and pin revision + file SHA-256.

CPU/network only. No GPU, no model forward, no experiment.
Writes reports/_non_authoritative/v3_env/model_manifest.json (non-authoritative path).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from modelscope import snapshot_download

MODEL_IDS = (
    "Qwen/Qwen3-0.6B",
    "Qwen/Qwen3-1.7B",
    "Qwen/Qwen3-4B",
)
OUT = Path("reports/_non_authoritative/v3_env/model_manifest.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "purpose": "v3.0 G1 model provenance pinning (non-authoritative until G1 release)",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "modelscope.cn",
        "driver_version": os.environ.get("DRIVER_VERSION", "see G1 release"),
        "models": {},
    }
    for mid in MODEL_IDS:
        print(f"[v3-pin] downloading {mid}", flush=True)
        local_dir = Path(snapshot_download(mid))
        snapshot_commit = local_dir.name if local_dir.parent.name == "snapshots" else None
        files = {}
        for p in sorted(local_dir.rglob("*")):
            if p.is_file() and p.suffix in {".safetensors", ".json", ".txt", ".model", ".bin"}:
                files[str(p.relative_to(local_dir))] = {
                    "sha256": sha256(p),
                    "bytes": p.stat().st_size,
                }
        manifest["models"][mid] = {
            "local_dir": str(local_dir),
            "resolved_revision": snapshot_commit,
            "file_count": len(files),
            "total_bytes": sum(v["bytes"] for v in files.values()),
            "files": files,
        }
        print(f"[v3-pin] {mid}: {snapshot_commit}, {len(files)} files", flush=True)
        OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[v3-pin] wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
