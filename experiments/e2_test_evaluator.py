"""E2 dedicated ONE-SHOT evaluator for the previously unevaluated held-out split.

FROZEN CONTRACT (read-only sources)
-----------------------------------
* configs/prereg/gpu_followup_v3.0.yaml  §4 (E2) and §2/§8
* docs/decisions/gpu_v3_scope_ruling.md  §1 (PI unlock)
* reports/data/v3_e2_test_lock.md        (data hashes + lock checklist)
* docs/audit/GPU_experiment_plan_2026-11-25.md §4

This module is deliberately stdlib-only at import time. torch / transformers /
readkv are imported LAZILY inside ``run_gpu_cells`` so that the CPU self-check and
all gate logic work in an environment without torch. NO test content is read in
``--cpu-selfcheck`` mode (synthetic temp files are used instead), and NO model is
loaded before every gate passes.

Hard refusals (before any forward pass):
  1. any tuning / threshold-selection / error-rework / multi-round flag;
  2. any val path or val-style flag (no val/test mixed runs);
  3. an unlocked / hash-mismatched lock file, test file, or eval config;
  4. a run id that is not a fresh ``v3_E2_...`` directory.

Fixed design: mappers = (affine, kd_only), seeds = (0, 1, 2), the SAME fixed
300-pair test set for all 6 cells, 16 template families -> exploratory=True.
The three seed scores are mapper/calibration seeds, NEVER three independent test
replicates; the schema validator forbids pooled inference.

Naming: the split is a "previously unevaluated held-out split"; it is never
claimed to be sealed. ``sealed_test_read`` is emitted as False with an explicit
designation string, so no artefact can be misread as a sealed-test read.

Usage (authorized operator only; NOT executed by this implementation task):
    .venv/bin/python -m experiments.e2_test_evaluator \
        --run-id v3_E2_fixed_s0 \
        --test-path <test jsonl> --test-sha256 <sha> \
        --lock-file reports/data/v3_e2_test_lock.md \
        --eval-config-hash <sha of configs/prereg/gpu_followup_v3.0.yaml> \
        --train-path <frozen train jsonl> --train-sha256 <sha> \
        --teacher <pinned dir> --student <pinned dir> --seed-set 0,1,2

    # gate/regression check only (no model, no real test data, no repo writes):
    .venv/bin/python -m experiments.e2_test_evaluator --cpu-selfcheck
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# Frozen constants. Do not expose any of these as tunable CLI knobs.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
CRITERIA_SOURCE = "configs/prereg/gpu_followup_v3.0.yaml"
EVAL_CONFIG_PATH = REPO_ROOT / CRITERIA_SOURCE
LOCK_RELATIVE = "reports/data/v3_e2_test_lock.md"
LOCK_PATH = REPO_ROOT / LOCK_RELATIVE
RUNS_ROOT = REPO_ROOT / "reports" / "runs"
NON_AUTHORITATIVE_ROOT = REPO_ROOT / "reports" / "_non_authoritative"

MAPPERS: tuple[str, ...] = ("affine", "kd_only")
SEEDS: tuple[int, ...] = (0, 1, 2)
N_EXPECTED_PAIRS = 300
N_EXPECTED_FAMILIES = 16
EXPLORATORY = True
N_RESAMPLES = 10_000
RIDGE_LAMBDA = 1e-3
KD_EPOCHS = 8
KD_LR = 1e-3
FLIP_DENOMINATOR_EXCLUDES: tuple[str, ...] = ("F5", "F6")
SPLIT_DESIGNATION = "previously_unevaluated_held_out_split"
SEALED_TEST_READ = False  # honest marker: never claim a sealed test
# Canonical SHA-256 of the 300 split=="test" rows of the whole-file-bound JSONL
# (json.dumps(ensure_ascii=False) + LF per row); recorded in the lock file §2.
TEST_SPLIT_SHA256 = "c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2"

ARTIFACT_FILES: tuple[str, ...] = ("config.json", "scores.jsonl", "metrics.json", "manifest.json")
SCORE_REQUIRED_FIELDS: tuple[str, ...] = (
    "pair_id", "split", "mapper", "seed", "template_family", "cluster",
    "E_CF", "dual_correct", "self_dual_correct", "coverage", "flip_consistency",
)
CELL_REQUIRED_FIELDS: tuple[str, ...] = (
    "mapper", "seed", "self_dual", "joint_dual", "L", "E_CF", "coverage",
    "flip", "template_family_ci", "pair_level_ci", "pair_set_fingerprint",
    "n_pairs", "n_template_families",
)

_HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
_RUN_ID_RE = re.compile(r"^v3_E2_[A-Za-z0-9][A-Za-z0-9_]*$")
_PATH_SPLIT_RE = re.compile(r"[./_\\-]+")
_VAL_FLAG_RE = re.compile(r"^--(val|validation|eval[-_]splits)\b", re.IGNORECASE)

# Substrings that must never appear in a flag: they would change the frozen
# configuration, select on the test set, or rework errors after peeking.
DENIED_FLAG_SUBSTRINGS: tuple[str, ...] = (
    "tune", "tuning", "threshold", "select", "selection", "rework", "grid",
    "sweep", "search", "huber", "delta", "adjust", "pick", "retry", "reselect",
    "multi-round", "rerun", "re-run", "peek", "epoch", "resample", "tau",
    "lambda", "lam-", "--lr", "n-train", "n-test", "cf-distortion",
)


class E2Refusal(RuntimeError):
    """Raised whenever a gate fails. Nothing is loaded or written on refusal."""


# ---------------------------------------------------------------------------
# Hashing / lock parsing (pure stdlib, no test-content evaluation)
# ---------------------------------------------------------------------------
def sha256_file(path: Path | str) -> str:
    """File-byte SHA-256. This is metadata-only: no field is interpreted."""
    p = Path(path)
    if not p.is_file():
        raise E2Refusal(f"file not found: {p}")
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_hex(value: str | None, field: str) -> str:
    if not isinstance(value, str):
        raise E2Refusal(f"{field} must be a 64-hex SHA-256 string")
    v = value.strip().lower()
    if not _HEX64.fullmatch(v):
        raise E2Refusal(f"{field} is not a 64-hex SHA-256 string: {value!r}")
    return v


@dataclass(frozen=True)
class LockInfo:
    whole_file_sha256: str
    test_split_sha256: str
    lock_sha256: str
    unlock_evidence: tuple[str, ...]
    designation_ok: bool

    @property
    def accepted_test_hashes(self) -> frozenset[str]:
        return frozenset({self.whole_file_sha256, self.test_split_sha256})


def parse_lock(text: str, *, lock_sha256: str) -> LockInfo:
    """Extract the two data hashes and the PI-unlock evidence from the lock md.

    The lock is a checklist, not a config: we require (a) both 64-hex data
    hashes, (b) the G0 ruling reference + PI/unlock wording, and (c) the honest
    previously-unevaluated-held-out designation. Anything else -> refuse.
    """
    if not isinstance(text, str) or not text.strip():
        raise E2Refusal("lock file is empty")

    whole: str | None = None
    split: str | None = None
    for line in text.splitlines():
        hexes = _HEX64.findall(line)
        if not hexes:
            continue
        if "整文件" in line or "data/tasks/cf_pairs.jsonl" in line:
            whole = whole or hexes[0]
        if "test split" in line:
            # Line 29 repeats both hashes; prefer the one that is not the
            # already-seen whole-file hash.
            candidates = [h for h in reversed(hexes) if h != whole]
            split = candidates[0] if candidates else hexes[-1]
    if not whole or not split or whole == split:
        raise E2Refusal("lock file does not record two distinct whole-file/test-split SHA-256 values")

    evidence: list[str] = []
    if "gpu_v3_scope_ruling.md" not in text:
        evidence.append("missing G0 ruling reference (gpu_v3_scope_ruling.md)")
    if "§1" not in text:
        evidence.append("missing §1 unlock reference")
    if "PI" not in text:
        evidence.append("missing PI unlock attribution")
    if not any(w in text for w in ("解锁", "unlock", "unlocked")):
        evidence.append("missing explicit unlock statement")
    if evidence:
        raise E2Refusal("lock file does not record PI unlock: " + "; ".join(evidence))

    designation_ok = "previously unevaluated held-out split" in text
    if not designation_ok:
        raise E2Refusal(
            "lock file must designate the split as 'previously unevaluated held-out split' "
            "(never 'sealed')"
        )
    return LockInfo(
        whole_file_sha256=whole,
        test_split_sha256=split,
        lock_sha256=lock_sha256,
        unlock_evidence=("PI", "gpu_v3_scope_ruling.md §1", "解锁"),
        designation_ok=True,
    )


# ---------------------------------------------------------------------------
# Refusal gates (all run before model load / test-content read)
# ---------------------------------------------------------------------------
def scan_forbidden_flags(argv: Sequence[str]) -> list[str]:
    """Return human-readable reasons; empty list means no forbidden flag."""
    reasons: list[str] = []
    for token in argv:
        low = token.lower()
        if _VAL_FLAG_RE.match(low):
            reasons.append(f"val/validation flag refused: {token}")
        if low.startswith("--"):
            for bad in DENIED_FLAG_SUBSTRINGS:
                if bad in low:
                    reasons.append(f"tuning/selection/rework flag refused: {token} (matches {bad!r})")
                    break
    return reasons


def check_test_path(path: str | Path) -> None:
    """Reject any path that looks like validation data. No exceptions."""
    s = str(path)
    low = s.lower()
    if "validation" in low:
        raise E2Refusal(f"validation path refused as test input: {s}")
    for tok in _PATH_SPLIT_RE.split(low):
        if tok == "val" or tok.startswith("val.") or tok == "validation":
            raise E2Refusal(f"validation path refused as test input: {s}")


def check_train_path(path: str | Path) -> None:
    """Calibration path must be train-only: no val and no test component."""
    s = str(path)
    low = s.lower()
    if "validation" in low:
        raise E2Refusal(f"validation path refused as calibration input: {s}")
    for tok in _PATH_SPLIT_RE.split(low):
        if tok in {"val", "test"} or tok.startswith(("val.", "test.")):
            raise E2Refusal(f"non-train path refused as calibration input: {s}")


@dataclass(frozen=True)
class Verification:
    run_id: str
    test_path: str
    test_sha256: str
    binding_kind: str                 # "whole_file" or "test_split"
    lock_path: str
    lock_sha256: str
    lock_info: LockInfo
    eval_config_path: str
    eval_config_sha256: str
    smoke: bool
    out_dir: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "test_path": self.test_path,
            "test_sha256": self.test_sha256,
            "binding_kind": self.binding_kind,
            "lock_path": self.lock_path,
            "lock_sha256": self.lock_sha256,
            "data_hashes_in_lock": {
                "whole_file": self.lock_info.whole_file_sha256,
                "test_split": self.lock_info.test_split_sha256,
            },
            "eval_config_path": self.eval_config_path,
            "eval_config_sha256": self.eval_config_sha256,
            "criteria_source": CRITERIA_SOURCE,
            "smoke": self.smoke,
            "out_dir": self.out_dir,
            "split_designation": SPLIT_DESIGNATION,
            "sealed_test_read": SEALED_TEST_READ,
        }


def verify_hashes(
    *,
    test_path: Path,
    test_sha256_expected: str,
    lock_path: Path,
    lock_sha256_expected: str | None,
    eval_config_path: Path,
    eval_config_sha256_expected: str,
) -> tuple[LockInfo, str, str, str]:
    """Low-level gate: file hashes + lock content. Used by real runs and by CPU self-check."""
    expected_test = normalize_hex(test_sha256_expected, "--test-sha256")
    expected_cfg = normalize_hex(eval_config_sha256_expected, "--eval-config-hash")

    lock_sha = sha256_file(lock_path)
    if lock_sha256_expected is not None:
        if normalize_hex(lock_sha256_expected, "--lock-file-sha256") != lock_sha:
            raise E2Refusal(f"lock file hash mismatch: expected {lock_sha256_expected}, got {lock_sha}")
    lock_info = parse_lock(lock_path.read_text(encoding="utf-8"), lock_sha256=lock_sha)

    cfg_sha = sha256_file(eval_config_path)
    if cfg_sha != expected_cfg:
        raise E2Refusal(
            f"eval config hash mismatch ({CRITERIA_SOURCE}): expected {expected_cfg}, got {cfg_sha}"
        )

    actual_test = sha256_file(test_path)
    if actual_test != expected_test:
        raise E2Refusal(
            f"test file hash mismatch: expected {expected_test}, got {actual_test} "
            f"for {test_path}"
        )
    if actual_test not in lock_info.accepted_test_hashes:
        raise E2Refusal(
            "test hash is not bound in the lock file: "
            f"{actual_test} not in {sorted(lock_info.accepted_test_hashes)}"
        )
    binding = "whole_file" if actual_test == lock_info.whole_file_sha256 else "test_split"
    return lock_info, actual_test, cfg_sha, binding


def verify_gates(args: argparse.Namespace, argv: Sequence[str]) -> Verification:
    """Full pre-flight gate chain. Raises E2Refusal on any failed check."""
    bad = scan_forbidden_flags(argv)
    if bad:
        raise E2Refusal("; ".join(bad))

    if not args.run_id or not _RUN_ID_RE.match(args.run_id):
        raise E2Refusal(f"run-id must be a fresh v3_E2_* id: {args.run_id!r}")
    if args.smoke and not args.run_id.endswith("_smoke"):
        raise E2Refusal("smoke runs must use a run-id ending in _smoke")
    if not args.smoke and args.run_id.endswith("_smoke"):
        raise E2Refusal("non-smoke run-id must not end in _smoke")

    check_test_path(args.test_path)
    lock_path = Path(args.lock_file).resolve()
    if lock_path != LOCK_PATH.resolve():
        raise E2Refusal(f"--lock-file must be {LOCK_RELATIVE}: got {args.lock_file}")

    out_root = NON_AUTHORITATIVE_ROOT if args.smoke else RUNS_ROOT
    out_dir = out_root / args.run_id
    if out_dir.exists():
        raise E2Refusal(f"one-shot rule: output directory already exists, refusing overwrite: {out_dir}")

    lock_info, test_sha, cfg_sha, binding = verify_hashes(
        test_path=Path(args.test_path),
        test_sha256_expected=args.test_sha256,
        lock_path=lock_path,
        lock_sha256_expected=args.lock_file_sha256,
        eval_config_path=EVAL_CONFIG_PATH,
        eval_config_sha256_expected=args.eval_config_hash,
    )
    return Verification(
        run_id=args.run_id,
        test_path=str(args.test_path),
        test_sha256=test_sha,
        binding_kind=binding,
        lock_path=str(lock_path),
        lock_sha256=lock_info.lock_sha256,
        lock_info=lock_info,
        eval_config_path=CRITERIA_SOURCE,
        eval_config_sha256=cfg_sha,
        smoke=bool(args.smoke),
        out_dir=str(out_dir),
    )


# ---------------------------------------------------------------------------
# Per-seed calibration binding (PI ruling v3_e2_interface_ruling.md §2).
# Minimal extension: three explicit hash-bound train JSONLs, one per seed.
# The legacy single --train-path/--train-sha256 pair is kept ONLY for
# --cpu-selfcheck compatibility and is NOT accepted as a GPU-mode fallback.
# ---------------------------------------------------------------------------
def entry_sha256() -> str:
    """Self-hash of this entry file: the frozen implementation identity."""
    return sha256_file(Path(__file__).resolve())


def per_seed_train_bindings(args: argparse.Namespace) -> dict[int, tuple[str, str]]:
    """Collect the three declared (path, expected_sha) pairs without I/O."""
    return {
        seed: (
            str(getattr(args, f"train_path_s{seed}", None) or ""),
            str(getattr(args, f"train_sha256_s{seed}", None) or ""),
        )
        for seed in SEEDS
    }


def per_seed_train_manifest(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    """Reproducibility record of the declared (hash-verified) per-seed train bindings."""
    return {
        str(seed): {"path": path, "sha256": expected}
        for seed, (path, expected) in per_seed_train_bindings(args).items()
    }


def verify_per_seed_trains(args: argparse.Namespace) -> dict[int, list[dict[str, Any]]]:
    """Hash-bind and load each seed's calibration JSONL. No model, no test data.

    Any missing pair, val-like path, or hash mismatch raises E2Refusal before a
    model is loaded or a score is produced (same refusal contract as the legacy
    single-train hash gate in ``run_gpu_cells``).
    """
    loaded: dict[int, list[dict[str, Any]]] = {}
    for seed, (path, expected) in per_seed_train_bindings(args).items():
        if not path or not expected:
            raise E2Refusal(
                f"GPU mode requires --train-path-s{seed} and --train-sha256-s{seed}"
            )
        check_train_path(path)
        got = sha256_file(Path(path))
        if got != normalize_hex(expected, f"--train-sha256-s{seed}"):
            raise E2Refusal(
                f"per-seed train hash mismatch for seed {seed}: "
                f"expected {expected}, got {got} for {path}"
            )
        loaded[seed] = _load_jsonl_pairs(Path(path), "train")
    return loaded


# ---------------------------------------------------------------------------
# Fixed cell plan + artifact schema (validated in CPU self-check)
# ---------------------------------------------------------------------------
def plan_cells() -> list[dict[str, Any]]:
    cells = [{"mapper": m, "seed": s} for m in MAPPERS for s in SEEDS]
    assert len(cells) == 6
    return cells


def pair_set_fingerprint(pair_ids: Sequence[str]) -> str:
    canonical = "\n".join(str(x) for x in sorted(pair_ids)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_artifact_schema(
    metrics: Mapping[str, Any], scores: Iterable[Mapping[str, Any]]
) -> list[str]:
    """Check the E2 report contract. Pure structure/flags: no numeric claims."""
    errors: list[str] = []
    scores = list(scores)

    if metrics.get("criteria_source") != CRITERIA_SOURCE:
        errors.append(f"criteria_source must be {CRITERIA_SOURCE}")
    if metrics.get("split_designation") != SPLIT_DESIGNATION:
        errors.append(f"split_designation must be {SPLIT_DESIGNATION}")
    if metrics.get("sealed_test_read") is not False:
        errors.append("sealed_test_read must be False (previously-unevaluated held-out, never sealed)")
    if metrics.get("exploratory") is not True:
        errors.append("exploratory must be True (16 < 24 families)")
    if metrics.get("n_template_families") != N_EXPECTED_FAMILIES:
        errors.append(f"n_template_families must be {N_EXPECTED_FAMILIES}")
    if metrics.get("n_pairs") != N_EXPECTED_PAIRS:
        errors.append(f"n_pairs must be {N_EXPECTED_PAIRS}")
    if metrics.get("pooled_inference") is not False:
        errors.append("pooled_inference must be False (3 seed scores are not 3 test replicates)")
    if str(metrics.get("zero_re_prefill", "true")).lower() != "true":
        errors.append("zero_re_prefill must be true")

    cells = metrics.get("cells")
    if not isinstance(cells, list) or len(cells) != 6:
        errors.append("cells must contain exactly 6 entries (2 mappers x 3 seeds)")
        cells = []
    seen = set()
    fps: set[str] = set()
    for cell in cells:
        if not isinstance(cell, Mapping):
            errors.append("cell is not a mapping")
            continue
        key = (cell.get("mapper"), cell.get("seed"))
        if key in seen:
            errors.append(f"duplicate cell {key}")
        seen.add(key)
        for field in CELL_REQUIRED_FIELDS:
            if field not in cell:
                errors.append(f"cell {key} missing field {field}")
        if cell.get("pair_set_fingerprint") is not None:
            fps.add(str(cell["pair_set_fingerprint"]))
        flip = cell.get("flip")
        if isinstance(flip, Mapping):
            if tuple(flip.get("excluded_slices", ())) != FLIP_DENOMINATOR_EXCLUDES:
                errors.append(f"cell {key} flip denominator must exclude {FLIP_DENOMINATOR_EXCLUDES}")
            if "direction_consistency" not in flip or "denominator" not in flip:
                errors.append(f"cell {key} flip must report direction_consistency and denominator")
        else:
            errors.append(f"cell {key} flip must be a mapping")
        ci = cell.get("template_family_ci")
        if isinstance(ci, Mapping):
            if ci.get("exploratory") is not True:
                errors.append(f"cell {key} template_family_ci.exploratory must be True")
            if ci.get("unit") != "template_family":
                errors.append(f"cell {key} template_family_ci.unit must be template_family")
        else:
            errors.append(f"cell {key} template_family_ci must be a mapping")
    expected_cells = {(m, s) for m in MAPPERS for s in SEEDS}
    if seen != expected_cells:
        errors.append(f"cells mismatch: expected {sorted(expected_cells)}, got {sorted(seen)}")
    if len(fps) > 1:
        errors.append("cells do not share one pair_set_fingerprint (same fixed 300-pair set required)")

    for row in scores:
        if str(row.get("split", "")).lower() != "test":
            errors.append(f"non-test score row: {row.get('pair_id')!r}")
        for field in SCORE_REQUIRED_FIELDS:
            if field not in row:
                errors.append(f"score row {row.get('pair_id')!r} missing {field}")
    return errors


def synthetic_metrics_for_schema_check(fp: str) -> dict[str, Any]:
    """In-memory schema skeleton with PLACEHOLDERS, never numeric results."""
    cells = []
    for cell in plan_cells():
        cells.append({
            "mapper": cell["mapper"],
            "seed": cell["seed"],
            "self_dual": "<placeholder>",
            "joint_dual": "<placeholder>",
            "L": "<placeholder>",
            "E_CF": "<placeholder>",
            "coverage": "<placeholder>",
            "flip": {
                "direction_consistency": "<placeholder>",
                "denominator": "<placeholder>",
                "excluded_slices": list(FLIP_DENOMINATOR_EXCLUDES),
            },
            "template_family_ci": {
                "unit": "template_family",
                "n_resamples": N_RESAMPLES,
                "n_clusters": N_EXPECTED_FAMILIES,
                "ci": "<placeholder>",
                "exploratory": True,
            },
            "pair_level_ci": {"unit": "pair", "ci": "<placeholder>"},
            "pair_set_fingerprint": fp,
            "n_pairs": N_EXPECTED_PAIRS,
            "n_template_families": N_EXPECTED_FAMILIES,
        })
    return {
        "run_id": "<selfcheck>",
        "criteria_source": CRITERIA_SOURCE,
        "split_designation": SPLIT_DESIGNATION,
        "sealed_test_read": SEALED_TEST_READ,
        "exploratory": True,
        "n_pairs": N_EXPECTED_PAIRS,
        "n_template_families": N_EXPECTED_FAMILIES,
        "pooled_inference": False,
        "zero_re_prefill": True,
        "cells": cells,
    }


def synthetic_scores_for_schema_check(fp: str) -> list[dict[str, str]]:
    row = {field: "<placeholder>" for field in SCORE_REQUIRED_FIELDS}
    row.update({"split": "test", "pair_set_fingerprint": fp})
    return [row]


# ---------------------------------------------------------------------------
# CPU-only self-check: gates, refusal paths, schema. No model / no real test data.
# ---------------------------------------------------------------------------
def cpu_selfcheck() -> int:
    checks: list[dict[str, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    def refuses(name: str, fn: Any, expected_marker: str) -> None:
        try:
            fn()
        except E2Refusal as exc:
            ok = expected_marker in str(exc)
            record(name, ok, str(exc))
        except Exception as exc:  # noqa: BLE001 - self-check reports any leak
            record(name, False, f"unexpected {type(exc).__name__}: {exc}")
        else:
            record(name, False, "expected E2Refusal was not raised")

    with tempfile.TemporaryDirectory(prefix="e2_selfcheck_") as tmp:
        td = Path(tmp)
        fake_test = td / "synthetic_test.jsonl"
        fake_test.write_text('{"pair_id":"synthetic","split":"test"}\n', encoding="utf-8")
        test_sha = sha256_file(fake_test)
        fake_lock = td / "synthetic_lock.md"
        fake_lock.write_text(
            "# synthetic lock\n"
            "| 整文件 | " + "a" * 64 + " |\n"
            "| test split | " + test_sha + " |\n"
            "PI 已在 gpu_v3_scope_ruling.md §1 明确解锁 E2；"
            "称 previously unevaluated held-out split，不称 sealed。\n",
            encoding="utf-8",
        )

        # 1) valid synthetic verification
        try:
            info, got_sha, _, binding = verify_hashes(
                test_path=fake_test,
                test_sha256_expected=test_sha,
                lock_path=fake_lock,
                lock_sha256_expected=None,
                eval_config_path=EVAL_CONFIG_PATH,
                eval_config_sha256_expected=sha256_file(EVAL_CONFIG_PATH),
            )
            ok = got_sha == test_sha and binding in ("whole_file", "test_split") and info.designation_ok
            record("valid_hash_and_unlock", ok, f"binding={binding}, designation_ok={info.designation_ok}")
        except Exception as exc:  # noqa: BLE001
            record("valid_hash_and_unlock", False, f"{type(exc).__name__}: {exc}")

        # 1b) real lock metadata structure (reads only the lock markdown, never cf_pairs.jsonl)
        try:
            real_info = parse_lock(LOCK_PATH.read_text(encoding="utf-8"),
                                   lock_sha256=sha256_file(LOCK_PATH))
            ok = (len(real_info.accepted_test_hashes) == 2
                  and bool(real_info.unlock_evidence) and real_info.designation_ok)
            record("real_lock_structure", ok,
                   f"two data hashes + PI unlock + designation: {ok}")
        except Exception as exc:  # noqa: BLE001
            record("real_lock_structure", False, f"{type(exc).__name__}: {exc}")

        # 2) hash mismatch aborts
        refuses(
            "hash_mismatch_abort",
            lambda: verify_hashes(
                test_path=fake_test,
                test_sha256_expected="1" * 64,
                lock_path=fake_lock,
                lock_sha256_expected=None,
                eval_config_path=EVAL_CONFIG_PATH,
                eval_config_sha256_expected=sha256_file(EVAL_CONFIG_PATH),
            ),
            "hash mismatch",
        )

        # 3) eval config hash mismatch aborts
        refuses(
            "eval_config_hash_mismatch_abort",
            lambda: verify_hashes(
                test_path=fake_test,
                test_sha256_expected=test_sha,
                lock_path=fake_lock,
                lock_sha256_expected=None,
                eval_config_path=EVAL_CONFIG_PATH,
                eval_config_sha256_expected="2" * 64,
            ),
            "eval config hash mismatch",
        )

        # 4) lock without PI unlock is refused
        unlocked_off = td / "no_unlock.md"
        unlocked_off.write_text(
            "| 整文件 | " + test_sha + " |\n| test split | " + "3" * 64 + " |\n"
            "previously unevaluated held-out split\n",
            encoding="utf-8",
        )
        refuses(
            "lock_unlock_missing_abort",
            lambda: parse_lock(unlocked_off.read_text(encoding="utf-8"), lock_sha256="4" * 64),
            "PI unlock",
        )

        # 5) val path / val flag rejected (no val-test mixing)
        refuses(
            "val_path_rejected",
            lambda: check_test_path(td / "val" / "cf_pairs_val.jsonl"),
            "validation path refused",
        )
        refuses(
            "val_flag_rejected",
            lambda: (_ for _ in ()).throw(E2Refusal("; ".join(scan_forbidden_flags(["--val-path", "x"]))))
            if scan_forbidden_flags(["--val-path", "x"])
            else (_ for _ in ()).throw(AssertionError("val flag not detected")),
            "val/validation flag refused",
        )

        # 6) tuning / threshold / error-rework flags rejected
        refuses(
            "tuning_flags_rejected",
            lambda: (_ for _ in ()).throw(E2Refusal("; ".join(scan_forbidden_flags([
                "--tune-threshold", "--error-rework", "--huber-delta", "--n-resamples",
            ])))) if scan_forbidden_flags([
                "--tune-threshold", "--error-rework", "--huber-delta", "--n-resamples",
            ]) else (_ for _ in ()).throw(AssertionError("tuning flags not detected")),
            "refused",
        )

        # 7) artifact schema: valid skeleton passes, corrupted skeleton fails
        fp = pair_set_fingerprint(["synthetic-a", "synthetic-b"])
        good = synthetic_metrics_for_schema_check(fp)
        good_scores = synthetic_scores_for_schema_check(fp)
        errs = validate_artifact_schema(good, good_scores)
        record("artifact_schema_valid", not errs, "; ".join(errs) or "6 cells, all required fields")

        bad = json.loads(json.dumps(good))
        bad["pooled_inference"] = True
        bad["sealed_test_read"] = True
        bad["cells"][0].pop("L")
        bad["cells"][1]["flip"]["excluded_slices"] = []
        bad_errs = validate_artifact_schema(bad, good_scores)
        ok = any("pooled_inference" in e for e in bad_errs) and any("sealed_test_read" in e for e in bad_errs) \
            and any("missing field L" in e for e in bad_errs) and any("exclude" in e for e in bad_errs)
        record("artifact_schema_rejects_corruption", ok, f"{len(bad_errs)} schema errors detected")

        # 8) per-seed calibration bindings (interface ruling §2); synthetic train rows only.
        train_paths: list[Path] = []
        train_hashes: list[str] = []
        for seed in SEEDS:
            tp = td / f"synthetic_train_seed{seed}.jsonl"
            tp.write_text('{"pair_id":"synthetic","split":"train"}\n', encoding="utf-8")
            train_paths.append(tp)
            train_hashes.append(sha256_file(tp))

        cli = parse_args([
            "--train-path-s0", str(train_paths[0]), "--train-sha256-s0", train_hashes[0],
            "--train-path-s1", str(train_paths[1]), "--train-sha256-s1", train_hashes[1],
            "--train-path-s2", str(train_paths[2]), "--train-sha256-s2", train_hashes[2],
        ])
        ok = all(
            getattr(cli, f"train_path_s{s}") == str(train_paths[s])
            and getattr(cli, f"train_sha256_s{s}") == train_hashes[s]
            for s in SEEDS
        )
        record("per_seed_cli_bindings", ok, "six per-seed flags parse into three (path,sha) pairs")

        def _with_args(**changes: Any) -> argparse.Namespace:
            d = dict(vars(cli))
            d.update(changes)
            return argparse.Namespace(**d)

        try:
            loaded = verify_per_seed_trains(cli)
            ok = set(loaded) == set(SEEDS) and all(len(v) == 1 for v in loaded.values())
            record("per_seed_hash_bound_load", ok, "3 synthetic train files hash-verified and loaded")
        except Exception as exc:  # noqa: BLE001
            record("per_seed_hash_bound_load", False, f"{type(exc).__name__}: {exc}")

        refuses(
            "per_seed_hash_mismatch_abort",
            lambda: verify_per_seed_trains(_with_args(train_sha256_s1="1" * 64)),
            "per-seed train hash mismatch for seed 1",
        )
        refuses(
            "per_seed_legacy_fallback_rejected",
            lambda: verify_per_seed_trains(_with_args(
                train_path_s0="", train_sha256_s0="",
                train_path_s1="", train_sha256_s1="",
                train_path_s2="", train_sha256_s2="",
                train_path=str(train_paths[0]), train_sha256=train_hashes[0],
            )),
            "requires --train-path-s0",
        )
        refuses(
            "per_seed_val_path_rejected",
            lambda: verify_per_seed_trains(_with_args(
                train_path_s2=str(td / "val" / "synthetic_train_seed2.jsonl")
            )),
            "refused as calibration input",
        )

        # 9) whole file with non-test rows: filter to test-only + canonical hash gate.
        synthetic_rows = [
            {"pair_id": "probe-1", "split": "probe"},
            {"pair_id": "train-1", "split": "train"},
            {"pair_id": "val-1", "split": "val"},
            {"pair_id": "test-1", "split": "test"},
            {"pair_id": "test-2", "split": "test"},
        ]
        whole = td / "synthetic_whole.jsonl"
        whole.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in synthetic_rows),
            encoding="utf-8",
        )
        expected_canonical = canonical_split_sha256([r for r in synthetic_rows if r["split"] == "test"])
        try:
            filtered = load_bound_test_rows(whole, expected_canonical)
            ok = len(filtered) == 2 and all(r["split"] == "test" for r in filtered)
            record("test_rows_filtered_and_hash_bound", ok,
                   f"kept {len(filtered)} test rows out of {len(synthetic_rows)} whole-file rows")
        except Exception as exc:  # noqa: BLE001
            record("test_rows_filtered_and_hash_bound", False, f"{type(exc).__name__}: {exc}")

        refuses(
            "test_split_canonical_hash_mismatch_abort",
            lambda: load_bound_test_rows(whole, "5" * 64),
            "test split canonical SHA-256 mismatch",
        )
        # Non-test-only filtering must NOT be applied to train calibration files.
        refuses(
            "train_file_stays_strict",
            lambda: _load_jsonl_pairs(whole, "train"),
            "non-train row",
        )

    n_pass = sum(c["status"] == "PASS" for c in checks)
    summary = {
        "mode": "cpu_selfcheck",
        "authoritative": False,
        "uses_real_test_data": False,
        "loads_model": False,
        "writes_repo_files": False,
        "checks": checks,
        "passed": n_pass,
        "total": len(checks),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if n_pass == len(checks) else 1


# ---------------------------------------------------------------------------
# GPU evaluation path (LAZY IMPORTS; never executed by this implementation task)
# ---------------------------------------------------------------------------
def _pair_content_hash(pair: Mapping[str, Any]) -> str:
    """Content fingerprint for an explicit pair dict (same fields as stable_hash)."""
    import hashlib as _hl

    payload = "|".join(str(pair.get(k, "")) for k in (
        "query", "context_A", "context_B", "candidate_A", "candidate_B"
    ))
    return _hl.sha256(payload.encode("utf-8")).hexdigest()


def _load_jsonl_pairs(path: Path, expected_split: str) -> list[dict[str, Any]]:
    """Read an explicitly supplied JSONL. No build_cf_pairs, no quality gate.

    For ``expected_split == "test"`` the input is the whole hash-bound file,
    which also contains probe/train/val rows: those rows are SKIPPED and never
    scored. For train calibration files the strict all-rows check is retained.
    """
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("split", "")).lower() != expected_split:
                if expected_split == "test":
                    continue  # probe/train/val rows are never evaluated
                raise E2Refusal(
                    f"{path} contains a non-{expected_split} row: {row.get('pair_id')!r}; "
                    "val/test mixing is forbidden"
                )
            rows.append(row)
    return rows


def canonical_split_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    """Lock §2 canonical form: json.dumps(ensure_ascii=False) + LF per row."""
    h = hashlib.sha256()
    for row in rows:
        h.update((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    return h.hexdigest()


def load_bound_test_rows(path: Path, expected_split_sha: str) -> list[dict[str, Any]]:
    """Filter test rows from the whole file and bind their canonical hash."""
    rows = _load_jsonl_pairs(path, "test")
    got = canonical_split_sha256(rows)
    if got != normalize_hex(expected_split_sha, "test split SHA-256"):
        raise E2Refusal(
            f"test split canonical SHA-256 mismatch: expected {expected_split_sha}, got {got}"
        )
    return rows


def run_gpu_cells(args: argparse.Namespace, ver: Verification) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One-shot 6-cell evaluation. Only called after every gate passed and by an authorized operator.

    This implementation requires three explicit hash-bound train JSONLs (one per
    mapper seed) and pinned (non-`master`) teacher/student snapshot directories.
    It deliberately does NOT call ``build_cf_pairs`` or ``run_cf_pipeline``: those
    rebuild data and would violate the test-only explicit-entry requirement of
    prereg §4.
    """
    if not args.teacher or not args.student:
        raise E2Refusal("GPU mode requires pinned --teacher and --student snapshot directories")
    for seed, (path, expected) in per_seed_train_bindings(args).items():
        if not path or not expected:
            raise E2Refusal(
                f"GPU mode requires --train-path-s{seed} and --train-sha256-s{seed} "
                "(legacy single --train-path pair is self-check only)"
            )

    import numpy as np  # noqa: F401  (used by the imported readkv helpers)
    import torch  # noqa: F401
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from readkv.evaluate.counterfactual import PairCFRecord, summarize_cf
    from readkv.mapper.representation import AffineMapper
    from readkv.models.gpu_backend import GPUBackend
    from readkv.models.layer_map import LayerMap
    from readkv.runtime import v2_context
    from readkv.stats.bootstrap import cluster_bootstrap
    from readkv.train.kd_gpu import train_kd_gpu

    ev = __import__("readkv.config", fromlist=["load_config"]).load_config("eval")
    tau = float(ev["tau"])                  # frozen; never a CLI flag
    self_threshold = float(ev["self_threshold"])
    dtype, kernel = "bfloat16", "sdpa"      # frozen; never CLI flags

    # Per-seed calibration hash gate (train-only explicit paths, one per seed).
    train_rows_by_seed = verify_per_seed_trains(args)
    if ver.lock_info.test_split_sha256 != TEST_SPLIT_SHA256:
        raise E2Refusal(
            "lock test-split SHA-256 does not match the frozen E2 split hash: "
            f"{ver.lock_info.test_split_sha256} != {TEST_SPLIT_SHA256}"
        )
    test_rows = load_bound_test_rows(Path(args.test_path), TEST_SPLIT_SHA256)
    if len(test_rows) != N_EXPECTED_PAIRS:
        raise E2Refusal(f"expected {N_EXPECTED_PAIRS} test pairs, got {len(test_rows)}")
    families = {str(r.get("template_family", r.get("cluster", ""))) for r in test_rows}
    if len(families) != N_EXPECTED_FAMILIES:
        raise E2Refusal(f"expected {N_EXPECTED_FAMILIES} template families, got {len(families)}")
    fp = pair_set_fingerprint([str(r["pair_id"]) for r in test_rows])

    def load_model(path: str):
        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForCausalLM.from_pretrained(
            path, dtype=getattr(torch, dtype), attn_implementation=kernel
        ).to(args.device)
        model.eval()
        model.config.use_cache = True
        return model, tok

    tm, tt = load_model(args.teacher)
    sm, st = load_model(args.student)
    n_s, n_t = int(sm.config.num_hidden_layers), int(tm.config.num_hidden_layers)
    if n_s != n_t:
        raise E2Refusal(
            "E2 requires the equal-depth MVP pair; non-equal depth hits the E5 "
            "injection layer-map blocker and must not be reported as E2"
        )
    lmap = LayerMap(n_s, n_t, kind="identity")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=dtype,
                         kernel=kernel, layer_map=lmap)

    # Per-seed calibration stacks: seed k uses train_seed{k}.jsonl only.
    # The test set stays the same fixed 300 pairs for every seed (never split).
    from readkv.evaluate.pipeline import stack_caches
    stacks_by_seed: dict[int, tuple[Any, Any]] = {}
    for seed in SEEDS:
        cal_docs = [
            {"doc_id": f"{r['pair_id']}-{side}", "text": r[f"context_{side}"],
             "pair_id": r["pair_id"], "side": side,
             "query": r["query"], "cluster": r.get("cluster", r["pair_id"])}
            for r in train_rows_by_seed[seed] for side in ("A", "B")
        ]
        stacks_by_seed[seed] = (
            stack_caches(backend, cal_docs, "teacher"),
            stack_caches(backend, cal_docs, "student"),
        )

    rows: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    for mapper_kind in MAPPERS:
        for seed in SEEDS:
            train_rows = train_rows_by_seed[seed]
            tstack, sstack = stacks_by_seed[seed]
            if mapper_kind == "affine":
                mapper = AffineMapper(lam=RIDGE_LAMBDA, channel="both").fit(
                    tstack, sstack, layer_map=lmap
                )
            else:
                mapper = train_kd_gpu(
                    backend, train_rows, method="kd", epochs=KD_EPOCHS, lr=KD_LR,
                    lam_kd=1.0, lam_cf=0.0, lam_reg=1e-4,
                    self_threshold=self_threshold, seed=seed,
                )
            records: list[dict[str, Any]] = []
            for pair in test_rows:
                family = str(pair.get("template_family", pair.get("cluster", "")))
                self_a = backend.pair_side_cache(pair, "A", "student")
                self_b = backend.pair_side_cache(pair, "B", "student")
                teacher_a = backend.pair_side_cache(pair, "A", "teacher")
                teacher_b = backend.pair_side_cache(pair, "B", "teacher")
                mapped_a = mapper.transform(teacher_a)
                mapped_b = mapper.transform(teacher_b)
                qa = backend.candidate_logits(
                    self_a, {"text": pair["query"]},
                    candidates=(pair["candidate_A"], pair["candidate_B"]),
                    correct_index=None,
                )
                qb = backend.candidate_logits(
                    self_b, {"text": pair["query"]},
                    candidates=(pair["candidate_A"], pair["candidate_B"]),
                    correct_index=None,
                )
                ja = backend.candidate_logits(
                    mapped_a, {"text": pair["query"]},
                    candidates=(pair["candidate_A"], pair["candidate_B"]),
                    correct_index=None,
                )
                jb = backend.candidate_logits(
                    mapped_b, {"text": pair["query"]},
                    candidates=(pair["candidate_A"], pair["candidate_B"]),
                    correct_index=None,
                )
                rec = PairCFRecord(
                    pair_id=str(pair["pair_id"]), split="test",
                    slice_id=str(pair.get("slice_id", "")), cluster=family,
                    self_logits_A=qa, self_logits_B=qb,
                    transfer_logits_A=ja, transfer_logits_B=jb,
                    correct_A=pair["correct_A"], correct_B=pair["correct_B"],
                    must_flip=bool(pair.get("must_flip", True)),
                    tau=tau, self_threshold=self_threshold,
                ).compute()
                rec["template_family"] = family
                rec["mapper"] = mapper_kind
                rec["seed"] = seed
                records.append(rec)
                rows.append({
                    "pair_id": rec["pair_id"], "split": "test",
                    "template_family": family, "cluster": family,
                    "mapper": mapper_kind, "seed": seed,
                    "E_CF": rec["E_CF"], "dual_correct": rec["dual_correct"],
                    "self_dual_correct": rec["self_dual_correct"],
                    "coverage": float(rec["evaluable"]),
                    "flip_consistency": rec["flip_consistency"],
                    "pair_set_fingerprint": fp,
                    "cache_hash": _pair_content_hash(pair),
                })

            summary = summarize_cf(records, tau=tau, n_resamples=N_RESAMPLES, seed=seed)
            flip_records = [
                r for r in records
                if r["slice_id"] not in FLIP_DENOMINATOR_EXCLUDES
            ]
            flip_summary = summarize_cf(flip_records, tau=tau, n_resamples=N_RESAMPLES, seed=seed)
            ecf_values = [float(r["E_CF"]) for r in records]
            pair_ci = cluster_bootstrap(
                ecf_values, [r["pair_id"] for r in records],
                n_resamples=N_RESAMPLES, seed=seed,
            )
            # Self and Joint are distinct dual-correctness columns; never alias them.
            self_dual = float(sum(float(r["self_dual_correct"]) for r in records) / len(records))
            joint_dual = float(summary.dual_correct)  # PairCFRecord dual_correct = transfer/Joint
            cells.append({
                "mapper": mapper_kind,
                "seed": seed,
                "self_dual": self_dual,
                "joint_dual": joint_dual,
                "L": self_dual - joint_dual,
                "E_CF": summary.as_dict()["E_CF"],
                "coverage": summary.coverage,
                "flip": {
                    "direction_consistency": flip_summary.flip_consistency,
                    "denominator": flip_summary.detail.get("n_flip_evaluable", 0),
                    "excluded_slices": list(FLIP_DENOMINATOR_EXCLUDES),
                },
                "template_family_ci": {
                    "unit": "template_family",
                    "n_resamples": N_RESAMPLES,
                    "n_clusters": len(families),
                    "ci": summary.as_dict()["E_CF"]["ci"],
                    "exploratory": True,
                },
                "pair_level_ci": {"unit": "pair", "ci": [pair_ci[1], pair_ci[2]]},
                "pair_set_fingerprint": fp,
                "n_pairs": len(records),
                "n_template_families": len(families),
            })

    metrics = {
        "run_id": args.run_id,
        "criteria_source": CRITERIA_SOURCE,
        "split_designation": SPLIT_DESIGNATION,
        "sealed_test_read": SEALED_TEST_READ,
        "exploratory": True,
        "n_pairs": N_EXPECTED_PAIRS,
        "n_template_families": N_EXPECTED_FAMILIES,
        "pooled_inference": False,
        "zero_re_prefill": True,
        "backend": "gpu",
        "entry_sha256": entry_sha256(),
        "per_seed_train": per_seed_train_manifest(args),
        "verification": ver.as_dict(),
        "cells": cells,
        "cell_plan": plan_cells(),
    }
    schema_errors = validate_artifact_schema(metrics, rows)
    if schema_errors:
        raise E2Refusal("artifact schema validation failed: " + "; ".join(schema_errors))
    return metrics, rows


def write_artifacts(
    args: argparse.Namespace, ver: Verification,
    metrics: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> None:
    """Write into a NEW run directory only; nothing is ever overwritten."""
    from readkv.runtime import v2_context

    ctx = v2_context(
        args.run_id,
        {
            "stage": "E2", "gate": "held_out_one_shot", "backend": "gpu",
            "mappers": list(MAPPERS), "mapper_seeds": list(SEEDS),
            "eval_splits": ["test"], "n_pairs": N_EXPECTED_PAIRS,
            "n_template_families": N_EXPECTED_FAMILIES, "exploratory": True,
            "dtype": "bfloat16", "kernel": "sdpa", "n_resamples": N_RESAMPLES,
            "verification": ver.as_dict(), "criteria_source": CRITERIA_SOURCE,
            "split_designation": SPLIT_DESIGNATION,
            "sealed_test_read": SEALED_TEST_READ,
            "prereg": CRITERIA_SOURCE + " (frozen protocol-v3.0)",
            "entry_sha256": entry_sha256(), "entry_source": "experiments/e2_test_evaluator.py",
            "per_seed_train": per_seed_train_manifest(args),
        },
        seed=0, device=args.device, dtype="bfloat16", kernel="sdpa",
        zero_re_prefill=True,
        reports_root=NON_AUTHORITATIVE_ROOT if args.smoke else RUNS_ROOT,
        metadata={
            "stage": "E2", "backend": "gpu",
            "prereg_version": "3.0",
            "run_context_schema_version": "2.0",
            "criteria_source": CRITERIA_SOURCE,
            "authoritative": not args.smoke, "one_shot": True,
        },
    )
    ctx.require_zero_re_prefill()
    ctx.write_scores(rows)
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cpu-selfcheck", action="store_true",
                   help="CPU-only gate/schema self-check; no model, no real test data, no repo writes")
    p.add_argument("--run-id", default=None,
                   help="fresh v3_E2_* id; smoke ids must end with _smoke")
    p.add_argument("--test-path", default=None)
    p.add_argument("--test-sha256", default=None)
    p.add_argument("--lock-file", default=None)
    p.add_argument("--lock-file-sha256", default=None,
                   help="optional extra binding of the lock file bytes")
    p.add_argument("--eval-config-hash", default=None)
    p.add_argument("--train-path", default=None,
                   help="LEGACY self-check compatibility only; NOT accepted for GPU mode")
    p.add_argument("--train-sha256", default=None,
                   help="LEGACY self-check compatibility only; NOT accepted for GPU mode")
    p.add_argument("--train-path-s0", default=None, help="per-seed calibration train JSONL (seed 0)")
    p.add_argument("--train-sha256-s0", default=None, help="per-seed train SHA-256 (seed 0)")
    p.add_argument("--train-path-s1", default=None, help="per-seed calibration train JSONL (seed 1)")
    p.add_argument("--train-sha256-s1", default=None, help="per-seed train SHA-256 (seed 1)")
    p.add_argument("--train-path-s2", default=None, help="per-seed calibration train JSONL (seed 2)")
    p.add_argument("--train-sha256-s2", default=None, help="per-seed train SHA-256 (seed 2)")
    p.add_argument("--teacher", default=None, help="pinned snapshot dir, never a bare master alias")
    p.add_argument("--student", default=None, help="pinned snapshot dir, never a bare master alias")
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b", help="label only")
    p.add_argument("--device", default="cuda")
    p.add_argument("--smoke", action="store_true",
                   help="route artifacts to reports/_non_authoritative/; not authoritative")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw)
    if args.cpu_selfcheck:
        return cpu_selfcheck()

    missing = [
        name for name, val in (
            ("--run-id", args.run_id), ("--test-path", args.test_path),
            ("--test-sha256", args.test_sha256), ("--lock-file", args.lock_file),
            ("--eval-config-hash", args.eval_config_hash),
        ) if not val
    ]
    if missing:
        print(json.dumps({"status": "REFUSED", "reason": "missing required args: " + ", ".join(missing)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        ver = verify_gates(args, raw)
    except E2Refusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc),
                          "note": "no model loaded, no evaluation run"}, ensure_ascii=False),
              file=sys.stderr)
        return 2

    try:
        metrics, rows = run_gpu_cells(args, ver)
        write_artifacts(args, ver, metrics, rows)
    except E2Refusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except ImportError as exc:
        print(json.dumps({"status": "PENDING",
                          "reason": "torch/transformers/readkv unavailable: " + str(exc),
                          "note": "no GPU result produced"}, ensure_ascii=False), file=sys.stderr)
        return 3
    print(json.dumps({"status": "COMPLETED", "run_id": args.run_id,
                      "authoritative": not args.smoke,
                      "out_dir": ver.out_dir}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
