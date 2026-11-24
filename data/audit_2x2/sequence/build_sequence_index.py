#!/usr/bin/env python3
"""CPU-only data audit for the full-candidate (sequence) scoring robustness experiment.

Scope (frozen): configs/prereg/full_candidate_scoring_v2.8.yaml and
refine-logs/GPU_SEQUENCE_SCORING_PLAN.md. NO GPU, NO scoring, NO writes outside
data/audit_2x2/sequence/** and reports/data/sequence_scoring_data_audit.md.

Reads ONLY the existing legacy/fixed train/val seed0/1/2 JSONL under data/audit_2x2/.
Never reads any 'test' split (sealed test is out of scope, not evaluated).

For cells A00 (legacy/legacy) and A11 (fixed/fixed), seed 0/1/2, emit one index
file per cell/seed with all per-pair fields needed by the scoring engineer, using
the fixed token boundary: query and candidate tokenized SEPARATELY, automatic
special tokens disabled (add_special_tokens=False) for both.

Run: .venv/bin/python data/audit_2x2/sequence/build_sequence_index.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
SEQ = ROOT / "data/audit_2x2/sequence"
TOKPATH = "/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master"
SEMANTIC = ("F1", "F2", "F3", "F4")
CELLS = {"A00": "legacy", "A11": "fixed"}
SEEDS = (0, 1, 2)
GEN_DATE = "2026-11-24"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   text=True).strip()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    SEQ.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(TOKPATH, use_fast=True)

    def enc(s: str) -> list[int]:
        return tok.encode(s, add_special_tokens=False)

    # provenance of the private tokenizer (identity, not fabricated)
    tok_files = ["tokenizer.json", "tokenizer_config.json", "vocab.json",
                 "merges.txt", "special_tokens_map.json"]
    tok_prov = {f: sha256_file(Path(TOKPATH) / f)
                for f in tok_files if (Path(TOKPATH) / f).exists()}
    tok_prov["path"] = TOKPATH
    tok_prov["class"] = type(tok).__name__
    tok_prov["is_fast"] = tok.is_fast
    tok_prov["add_bos_token"] = bool(tok.add_bos_token)
    tok_prov["bos_token"] = tok.bos_token
    tok_prov["note"] = ("private tokenizer physically present in the offline cache; "
                        "all encode() calls use add_special_tokens=False (fixed boundary).")

    manifest_files: list[dict] = []
    summary: dict = {}
    file_verification: list[dict] = []

    # ---- task 1: verify all 12 source files (LF sha256 / lines / sample identity) ----
    for ver in ("legacy", "fixed"):
        for split in ("train", "val"):
            for seed in SEEDS:
                p = ROOT / f"data/audit_2x2/{ver}/{split}_seed{seed}.jsonl"
                raw = p.read_bytes()
                rows = load_jsonl(p)
                sh_field_ok = sum(
                    1 for r in rows
                    if hashlib.sha256(
                        f'{r["query"]}|{r["context_A"]}|{r["context_B"]}|'
                        f'{r["candidate_A"]}|{r["candidate_B"]}'.encode("utf-8")
                    ).hexdigest() == r["sample_hash"]
                )
                id_ok = sum(1 for r in rows
                            if r["sample_id"] == f'{r["version_tag"]}|{r["sample_hash"][:16]}')
                file_verification.append({
                    "path": str(p.relative_to(ROOT)), "version": ver, "split": split,
                    "seed": seed, "bytes": len(raw), "lf_lines": raw.count(b"\n"),
                    "crlf_count": raw.count(b"\r\n"), "sha256": sha256_bytes(raw),
                    "expected_lines": 120 if split == "train" else 60,
                    "sample_hash_field_ok": sh_field_ok, "sample_id_field_ok": id_ok,
                    "all_ok": (raw.count(b"\n") == (120 if split == "train" else 60)
                               and raw.count(b"\r\n") == 0
                               and sh_field_ok == len(rows) and id_ok == len(rows)),
                })

    # ---- tasks 2-4: per-cell/seed index + denominators + boundary checks ----
    for cell, ver in CELLS.items():
        summary[cell] = {}
        for seed in SEEDS:
            src = ROOT / f"data/audit_2x2/{ver}/val_seed{seed}.jsonl"
            rows = load_jsonl(src)
            idx_rows: list[dict] = []
            c: Counter = Counter()
            for r in rows:
                ca, cb = r["candidate_A"], r["candidate_B"]
                q = r["query"]
                q_ids = enc(q)
                ta, tb = enc(ca), enc(cb)
                qca, qcb = enc(q + ca), enc(q + cb)
                bnd_a = qca == q_ids + ta
                bnd_b = qcb == q_ids + tb
                identical = ca == cb
                prefix_related = ta[:len(tb)] == tb or tb[:len(ta)] == ta
                texts_differ = ca != cb
                toks_differ = ta != tb
                is_f14 = r["slice_id"] in SEMANTIC
                gold_swap = str(r["correct_A"]).strip().upper() != str(r["correct_B"]).strip().upper()
                f14_gold_swap = bool(is_f14 and gold_swap)
                primary = bool(f14_gold_swap and texts_differ)

                rec = {
                    "cell": cell, "source_version": ver, "split": "val", "seed": seed,
                    "pair_id": r["pair_id"], "sample_hash": r["sample_hash"],
                    "sample_id": r["sample_id"], "slice_id": r["slice_id"],
                    "template_family": r["template_family"], "cluster": r.get("cluster", ""),
                    "query": q, "context_A": r["context_A"], "context_B": r["context_B"],
                    "candidate_A": ca, "candidate_B": cb,
                    "correct_A": r["correct_A"], "correct_B": r["correct_B"],
                    "query_token_ids": q_ids, "query_token_count": len(q_ids),
                    "candidate_A_token_ids": ta, "candidate_B_token_ids": tb,
                    "candidate_A_token_count": len(ta), "candidate_B_token_count": len(tb),
                    "candidate_texts_differ": texts_differ,
                    "candidate_token_seqs_differ": toks_differ,
                    "is_f1_f4": is_f14,
                    "gold_labels_swapped": gold_swap,
                    "f1_f4_gold_swapped": f14_gold_swap,
                    "primary_analysis": primary,
                    "boundary_consistent_A": bnd_a, "boundary_consistent_B": bnd_b,
                    "boundary_consistent_pair": bool(bnd_a and bnd_b),
                    "candidates_identical": identical,
                    "candidates_prefix_related": prefix_related,
                    "candidates_prefix_related_distinct_only": bool(prefix_related and not identical),
                }
                idx_rows.append(rec)

                c["rows"] += 1
                c["slice_" + r["slice_id"]] += 1
                c["f5"] += r["slice_id"] == "F5"
                c["f6"] += r["slice_id"] == "F6"
                c["same_candidate"] += identical
                c["flip_denominator_excl_f5_f6"] += r["slice_id"] not in ("F5", "F6")
                c["f1_f4_gold_swapped"] += f14_gold_swap
                c["f1_f4_texts_differ"] += is_f14 and texts_differ
                c["f1_f4_primary"] += primary
                c["f1_f4_primary_tok_level"] += (is_f14 and toks_differ and gold_swap)
                c["boundary_inconsistent_candidates"] += (not bnd_a) + (not bnd_b)
                c["boundary_inconsistent_pairs"] += not (bnd_a and bnd_b)
                c["prefix_related_pairs"] += prefix_related
                c["prefix_related_distinct_pairs"] += prefix_related and not identical
                # template_family cluster count on the primary set
            primary_fams = sorted({r["template_family"] for r in idx_rows if r["primary_analysis"]})
            c["primary_template_family_count"] = len(primary_fams)
            c["primary_template_families"] = primary_fams
            full_fams = sorted({r["template_family"] for r in idx_rows})
            c["all60_template_family_count"] = len(full_fams)

            out = SEQ / f"{cell}_seed{seed}.jsonl"
            with out.open("w", encoding="utf-8") as fh:
                for r in idx_rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            manifest_files.append({
                "cell": cell, "source_version": ver,
                "source_val": str(src.relative_to(ROOT)),
                "source_val_sha256": sha256_file(src),
                "index_path": str(out.relative_to(ROOT)),
                "index_rows": len(idx_rows), "index_sha256": sha256_file(out),
            })
            summary[cell][f"seed{seed}"] = dict(c)

    # ---- cross-version sample-identity check: same pair_id string, different sample_hash ----
    overlap_pairs = 0
    hash_collisions = 0
    s0_old = {r["pair_id"]: r["sample_hash"] for r in load_jsonl(ROOT / "data/audit_2x2/legacy/val_seed0.jsonl")}
    s0_new = {r["pair_id"]: r["sample_hash"] for r in load_jsonl(ROOT / "data/audit_2x2/fixed/val_seed0.jsonl")}
    for pid in set(s0_old) & set(s0_new):
        overlap_pairs += 1
        if s0_old[pid] == s0_new[pid]:
            hash_collisions += 1

    manifest = {
        "dataset": "sequence_scoring_data_audit",
        "description": ("CPU data audit + per-pair candidate-token index for the full-candidate "
                        "(first vs full string) scoring robustness experiment; A00/A11 only, "
                        "sealed test never read."),
        "audit_date": GEN_DATE,
        "governing_frozen_config": "configs/prereg/full_candidate_scoring_v2.8.yaml",
        "plan": "refine-logs/GPU_SEQUENCE_SCORING_PLAN.md",
        "generation_script": str(Path(__file__).relative_to(ROOT)),
        "generation_script_sha256": sha256_file(Path(__file__)),
        "repo_head_at_generation": git_head(),
        "repo_head_note": ("HEAD a05e9b3 is the frozen baseline; v2.8 config and ruling doc are "
                           "untracked additions (frozen before any audit_seq_* GPU run)."),
        "source_generator_commits": {"legacy": "458de18", "fixed": "efc3ba3"},
        "tokenizer": tok_prov,
        "fixed_boundary": ("query and candidate tokenized separately; add_special_tokens=False "
                           "for both; candidate token sequence = encode(candidate, "
                           "add_special_tokens=False); no EOS appended; primary score object "
                           "= query_token_ids + candidate_token_ids."),
        "cells_in_scope": {"A00": "legacy/legacy", "A11": "fixed/fixed"},
        "cells_out_of_scope": ["A01", "A10"],
        "splits_used": ["train (verification only, task 1)", "val (index + denominators)"],
        "prohibited_splits": ["test (sealed; not read, not evaluated)"],
        "index_files": manifest_files,
        "file_verification": file_verification,
        "denominators": summary,
        "cross_version_identity": {
            "seed0_shared_pair_id_strings": overlap_pairs,
            "seed0_sample_hash_collisions": hash_collisions,
            "rule": ("old/repaired are two distinct validation sets: identical pair_id strings "
                     "carry different sample_hash -> key on version_tag+sample_hash, never "
                     "pair_id alone; both readings of a cell use the SAME batch, never mixed."),
        },
        "constraints_observed": [
            "No GPU / no scoring performed.",
            "No existing data/audit_2x2/{legacy,fixed} file modified (read-only).",
            "No data/tasks/** file modified.",
            "No frozen prereg / paper / reports/runs artifact modified.",
            "No sealed test read; no P2/P3/A01/A10.",
        ],
    }
    mpath = SEQ / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(mpath.relative_to(ROOT)),
        "index_files": [f["index_path"] for f in manifest_files],
        "denominators": {cell: {s: {k: v[k] for k in (
            "rows", "f1_f4_primary", "f5", "f6", "same_candidate",
            "boundary_inconsistent_candidates", "prefix_related_pairs",
            "prefix_related_distinct_pairs", "primary_template_family_count")}
            for s, v in cells.items()} for cell, cells in summary.items()},
        "all_files_ok": all(f["all_ok"] for f in file_verification),
        "repo_head": git_head(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
