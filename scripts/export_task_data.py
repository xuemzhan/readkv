"""Export the deterministic counterfactual task dataset used by P1-P5 runs.

The dataset is generated from the frozen builder in
``src/readkv/data/build_cf_pairs.py`` using the sizes in
``configs/protocol.yaml``.  No external download or manual editing is
involved; the manifest records the generator, seed, hashes and the data
quality gate so the export can be reproduced and audited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from readkv.data.build_cf_pairs import build_cf_pairs, quality_report, save_pairs

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs" / "protocol.yaml"
DEFAULT_OUT = ROOT / "data" / "tasks"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    sizes = {k: int(v) for k, v in protocol["data_sizes"].items()}

    pairs = build_cf_pairs(sizes=sizes, seed=args.seed)
    out_dir: Path = args.out_dir
    data_path = save_pairs(pairs, out_dir / "cf_pairs.jsonl")
    report = quality_report(pairs)
    if report["quality_gate"] != "pass":
        raise SystemExit(f"data quality gate failed: {report}")

    manifest = {
        "dataset": "cf_pairs_v2",
        "description": (
            "Deterministic synthetic F1-F6 counterfactual task pairs; "
            "each record follows the CFPair schema (context_A/B, query, "
            "candidates, split, slice, cluster)."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "src/readkv/data/build_cf_pairs.py::build_cf_pairs",
        "config": str(PROTOCOL.relative_to(ROOT)),
        "protocol_version": protocol["version"],
        "seed": args.seed,
        "sizes": sizes,
        "files": [
            {
                "name": data_path.name,
                "sha256": sha256(data_path),
                "size": data_path.stat().st_size,
                "lines": len(pairs),
            }
        ],
        "quality": report,
        "limitations": [
            "Synthetic, template-generated data; not real-world benchmark data.",
            "real split is empty; external HellaSwag/ARC/SQuAD data is not included.",
            "length_mismatch pairs must be reported as a separate stratum.",
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {data_path} ({len(pairs)} pairs)")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
