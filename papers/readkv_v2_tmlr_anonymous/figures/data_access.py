"""Data access for the readkv audit figures.

Nothing here is hard-coded: every number is read from the archived ledgers that
`reproduce.py` already verifies (`results.json`, `evaluation.json`) or recomputed
from the corpus files under `data/audit_2x2/`.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
REPO = PAPER.parents[1]
FIGDIR = Path(__file__).resolve().parent

CELLS = ("A00", "A01", "A10", "A11")
SEEDS = (0, 1, 2)
SEMANTIC = ("F1", "F2", "F3", "F4")
SLICES = ("F1", "F2", "F3", "F4", "F5", "F6")
READOUTS = (("first", "First token"), ("full", "Full sequence"), ("length_normalized", "Length-normalised"))


def _read_json(path: Path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_rows(path: Path):
    with io.open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle.read().splitlines()]


def results():
    return _read_json(PAPER / "results.json")


def evaluation():
    return _read_json(PAPER / "evaluation.json")


def cell_label(cell: str) -> str:
    """A00 -> 'orig/orig' style label used on axes."""
    calibration = "rebuilt" if cell[1] == "1" else "original"
    validation = "rebuilt" if cell[2] == "1" else "original"
    return f"{calibration} cal. / {validation} val."


def row_labels():
    return [(cell, seed) for cell in CELLS for seed in SEEDS]


def corpus_defects():
    """Recompute the corpus defects the paper reports, per version and seed.

    Returns {version: {seed: {...}}} with
      degenerate  identical candidates inside a must-flip semantic pair
      doc_overlap exact document strings shared between calibration and validation
      query_overlap query strings shared between calibration and validation
      span_overlap edited spans shared between calibration and validation
    """
    root = REPO / "data" / "audit_2x2"
    output = {"legacy": {}, "fixed": {}}
    for version in output:
        for seed in SEEDS:
            calibration = _read_rows(root / version / f"train_seed{seed}.jsonl")
            validation = _read_rows(root / version / f"val_seed{seed}.jsonl")
            semantic = [row for row in validation if row["slice_id"] in SEMANTIC]
            calibration_docs = {row[side] for row in calibration for side in ("context_A", "context_B")}
            validation_docs = {row[side] for row in validation for side in ("context_A", "context_B")}
            output[version][seed] = {
                "n_pairs": len(validation),
                "n_semantic": len(semantic),
                "degenerate": sum(1 for row in semantic if row["candidate_A"] == row["candidate_B"]),
                "doc_overlap": len(calibration_docs & validation_docs),
                "query_overlap": len({row["query"] for row in calibration} & {row["query"] for row in validation}),
                "span_overlap": len({row["edited_span"] for row in calibration}
                                    & {row["edited_span"] for row in validation}),
            }
    return output


def slice_levels():
    """Mean L (per cent) per cell, seed and slice from the pair-level ledger."""
    dataset = evaluation()["factorial"]
    output = {}
    for cell in CELLS:
        for seed in SEEDS:
            rows = dataset[f"{cell}_{seed}"]
            output[cell, seed] = {
                slice_id: 100.0 * (
                    sum(row["self"] - row["joint"] for row in rows if row["slice"] == slice_id)
                    / max(1, sum(1 for row in rows if row["slice"] == slice_id))
                )
                for slice_id in SLICES
            }
    return output
