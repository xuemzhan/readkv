"""CPU-only gate tests for the v3 E2 dedicated one-shot evaluator.

NO GPU, NO model, NO real test content, NO experiment results. All inputs are
synthetic objects created in a temp directory. Pure stdlib: runnable under
pytest or directly with ``python3 tests/test_v3_entries.py`` (no pytest needed).
"""
from __future__ import annotations

import sys
import tempfile
from argparse import Namespace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experiments import e2_test_evaluator as ev  # noqa: E402


def _synthetic_pair_set(tmp: Path) -> tuple[Path, str, Path, str]:
    """Create a fake 'test' file and lock md. No real test data is opened."""
    test = tmp / "synthetic_held_out.jsonl"
    test.write_text('{"pair_id":"synthetic","split":"test"}\n', encoding="utf-8")
    test_sha = ev.sha256_file(test)
    lock = tmp / "synthetic_lock.md"
    # Two distinct locked hashes, as in the real lock: whole-file and test-split.
    lock.write_text(
        "# synthetic lock\n"
        "| 整文件 | " + "a" * 64 + " |\n"
        "| test split（300 对） | " + test_sha + " |\n"
        "PI 已在 gpu_v3_scope_ruling.md §1 明确解锁 E2；"
        "称 previously unevaluated held-out split，不称 sealed。\n",
        encoding="utf-8",
    )
    lock_sha = ev.sha256_file(lock)
    return test, test_sha, lock, lock_sha


def _patch_paths(tmp_lock: Path, tmp_config: Path):
    """Minimal mock: redirect the two frozen path constants to synthetic files."""
    old_lock, old_cfg = ev.LOCK_PATH, ev.EVAL_CONFIG_PATH
    ev.LOCK_PATH = tmp_lock
    ev.EVAL_CONFIG_PATH = tmp_config
    return old_lock, old_cfg


def _restore_paths(old_lock: Path, old_cfg: Path) -> None:
    ev.LOCK_PATH = old_lock
    ev.EVAL_CONFIG_PATH = old_cfg


def _args(test: Path, test_sha: str, lock: Path, cfg_sha: str, **kw) -> Namespace:
    defaults = dict(
        run_id="v3_E2_fixed_s0",
        test_path=str(test),
        test_sha256=test_sha,
        lock_file=str(lock),
        lock_file_sha256=None,
        eval_config_hash=cfg_sha,
        smoke=False,
        train_path=None,
        train_sha256=None,
        train_path_s0=None,
        train_sha256_s0=None,
        train_path_s1=None,
        train_sha256_s1=None,
        train_path_s2=None,
        train_sha256_s2=None,
        teacher=None,
        student=None,
        device="cpu",
    )
    defaults.update(kw)
    return Namespace(**defaults)


def test_hash_mismatch_aborts_before_eval():
    """Wrong --test-sha256 must raise E2Refusal (no evaluation reachable)."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_hash_") as td:
        tmp = Path(td)
        test, test_sha, lock, _ = _synthetic_pair_set(tmp)
        cfg = tmp / "frozen_config.yaml"
        cfg.write_text("version: '3.0'\n", encoding="utf-8")
        cfg_sha = ev.sha256_file(cfg)
        old_lock, old_cfg = _patch_paths(lock, cfg)
        try:
            args = _args(test, "0" * 64, lock, cfg_sha)  # deliberately wrong hash
            try:
                ev.verify_gates(args, ["--test-sha256", "0" * 64])
            except ev.E2Refusal as exc:
                assert "hash mismatch" in str(exc)
            else:
                raise AssertionError("hash mismatch did not abort")
        finally:
            _restore_paths(old_lock, old_cfg)


def test_eval_config_hash_mismatch_aborts():
    with tempfile.TemporaryDirectory(prefix="v3_entry_cfg_") as td:
        tmp = Path(td)
        test, test_sha, lock, _ = _synthetic_pair_set(tmp)
        cfg = tmp / "frozen_config.yaml"
        cfg.write_text("version: '3.0'\n", encoding="utf-8")
        old_lock, old_cfg = _patch_paths(lock, cfg)
        try:
            args = _args(test, test_sha, lock, "1" * 64)
            try:
                ev.verify_gates(args, ["--eval-config-hash", "1" * 64])
            except ev.E2Refusal as exc:
                assert "eval config hash mismatch" in str(exc)
            else:
                raise AssertionError("eval-config hash mismatch did not abort")
        finally:
            _restore_paths(old_lock, old_cfg)


def test_test_path_rejected_when_val():
    for bad in ("data/val/cf_pairs_val.jsonl", "data/cf_pairs_validation.jsonl",
                "reports/runs/val_probe.jsonl"):
        try:
            ev.check_test_path(bad)
        except ev.E2Refusal as exc:
            assert "validation path refused" in str(exc)
        else:
            raise AssertionError(f"val path was not rejected: {bad}")


def test_val_flag_rejected():
    assert ev.scan_forbidden_flags(["--val-path", "x"])
    assert ev.scan_forbidden_flags(["--eval-splits", "test,val"])
    assert not ev.scan_forbidden_flags([
        "--run-id", "v3_E2_fixed_s0", "--test-path", "x.jsonl",
        "--eval-config-hash", "a" * 64, "--lock-file", "lock.md",
    ])


def test_tuning_and_rework_flags_rejected():
    for flag in ("--tune-threshold", "--threshold-select", "--error-rework",
                 "--huber-delta", "--n-resamples", "--grid-search", "--multi-round"):
        reasons = ev.scan_forbidden_flags([flag])
        assert reasons, f"tuning flag not refused: {flag}"


def test_lock_without_pi_unlock_rejected():
    try:
        ev.parse_lock(
            "| 整文件 | " + "a" * 64 + " |\n"
            "| test split | " + "b" * 64 + " |\n"
            "previously unevaluated held-out split\n",
            lock_sha256="c" * 64,
        )
    except ev.E2Refusal as exc:
        assert "PI unlock" in str(exc)
    else:
        raise AssertionError("lock without PI unlock was accepted")


def test_valid_synthetic_gate_chain_and_schema():
    with tempfile.TemporaryDirectory(prefix="v3_entry_ok_") as td:
        tmp = Path(td)
        test, test_sha, lock, lock_sha = _synthetic_pair_set(tmp)
        cfg = tmp / "frozen_config.yaml"
        cfg.write_text("version: '3.0'\n", encoding="utf-8")
        cfg_sha = ev.sha256_file(cfg)
        old_lock, old_cfg = _patch_paths(lock, cfg)
        try:
            args = _args(test, test_sha, lock, cfg_sha, lock_file_sha256=lock_sha)
            ver = ev.verify_gates(
                args,
                ["--run-id", args.run_id, "--test-path", args.test_path,
                 "--test-sha256", args.test_sha256, "--lock-file", args.lock_file,
                 "--eval-config-hash", args.eval_config_hash],
            )
            assert ver.binding_kind in {"whole_file", "test_split"}
            assert ver.lock_info.unlock_evidence
            assert ver.as_dict()["split_designation"] == ev.SPLIT_DESIGNATION
            assert ver.as_dict()["sealed_test_read"] is False

            fp = ev.pair_set_fingerprint(["a", "b"])
            metrics = ev.synthetic_metrics_for_schema_check(fp)
            scores = ev.synthetic_scores_for_schema_check(fp)
            assert ev.validate_artifact_schema(metrics, scores) == []

            # Corrupt: pooled inference + sealed claim + missing L + wrong flip denom
            bad = __import__("json").loads(__import__("json").dumps(metrics))
            bad["pooled_inference"] = True
            bad["sealed_test_read"] = True
            bad["cells"][0].pop("L")
            bad["cells"][1]["flip"]["excluded_slices"] = []
            errs = " ".join(ev.validate_artifact_schema(bad, scores))
            assert "pooled_inference" in errs
            assert "sealed_test_read" in errs
            assert "missing field L" in errs
            assert "exclude" in errs
        finally:
            _restore_paths(old_lock, old_cfg)


def _synthetic_per_seed_trains(tmp: Path) -> tuple[list[Path], list[str]]:
    """Three synthetic train JSONLs (one per seed). No real train/test content."""
    paths: list[Path] = []
    hashes: list[str] = []
    for seed in (0, 1, 2):
        p = tmp / f"synthetic_train_seed{seed}.jsonl"
        p.write_text('{"pair_id":"synthetic","split":"train"}\n', encoding="utf-8")
        paths.append(p)
        hashes.append(ev.sha256_file(p))
    return paths, hashes


def _per_seed_args(paths: list[Path], hashes: list[str], **changes) -> Namespace:
    d = dict(
        train_path_s0=str(paths[0]), train_sha256_s0=hashes[0],
        train_path_s1=str(paths[1]), train_sha256_s1=hashes[1],
        train_path_s2=str(paths[2]), train_sha256_s2=hashes[2],
    )
    d.update(changes)
    return Namespace(**d)


def test_per_seed_hash_verified_load():
    """All three per-seed train files load only when each hash matches."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_perseed_ok_") as td:
        paths, hashes = _synthetic_per_seed_trains(Path(td))
        loaded = ev.verify_per_seed_trains(_per_seed_args(paths, hashes))
        assert set(loaded) == {0, 1, 2}
        assert all(len(rows) == 1 for rows in loaded.values())


def test_per_seed_hash_mismatch_aborts():
    """A wrong hash on ANY seed aborts before any evaluation is reachable."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_perseed_bad_") as td:
        paths, hashes = _synthetic_per_seed_trains(Path(td))
        for bad_seed in (0, 1, 2):
            bad_hashes = list(hashes)
            bad_hashes[bad_seed] = "0" * 64
            try:
                ev.verify_per_seed_trains(_per_seed_args(paths, bad_hashes))
            except ev.E2Refusal as exc:
                assert f"per-seed train hash mismatch for seed {bad_seed}" in str(exc)
            else:
                raise AssertionError(f"seed {bad_seed} hash mismatch did not abort")


def test_per_seed_legacy_pair_is_not_a_fallback():
    """The single --train-path pair (self-check only) cannot bind GPU calibration."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_perseed_legacy_") as td:
        paths, hashes = _synthetic_per_seed_trains(Path(td))
        legacy = _per_seed_args(
            paths, hashes,
            train_path_s0="", train_sha256_s0="",
            train_path_s1="", train_sha256_s1="",
            train_path_s2="", train_sha256_s2="",
            train_path=str(paths[0]), train_sha256=hashes[0],
        )
        try:
            ev.verify_per_seed_trains(legacy)
        except ev.E2Refusal as exc:
            assert "requires --train-path-s0" in str(exc)
        else:
            raise AssertionError("legacy single train pair was accepted as GPU calibration")


def test_per_seed_val_path_rejected():
    with tempfile.TemporaryDirectory(prefix="v3_entry_perseed_val_") as td:
        paths, hashes = _synthetic_per_seed_trains(Path(td))
        bad = _per_seed_args(paths, hashes, train_path_s1=str(Path(td) / "val" / "seed1.jsonl"))
        try:
            ev.verify_per_seed_trains(bad)
        except ev.E2Refusal as exc:
            assert "refused as calibration input" in str(exc)
        else:
            raise AssertionError("val-like per-seed train path was accepted")


def test_whole_file_filters_to_test_rows_with_canonical_hash():
    """Whole-file input: only split=='test' rows survive; canonical SHA is bound."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_rows_") as td:
        rows = [
            {"pair_id": "probe-1", "split": "probe"},
            {"pair_id": "train-1", "split": "train"},
            {"pair_id": "val-1", "split": "val"},
            {"pair_id": "test-1", "split": "test"},
            {"pair_id": "test-2", "split": "test"},
        ]
        whole = Path(td) / "synthetic_whole.jsonl"
        whole.write_text(
            "".join(__import__("json").dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
        expected = ev.canonical_split_sha256([r for r in rows if r["split"] == "test"])
        kept = ev.load_bound_test_rows(whole, expected)
        assert len(kept) == 2
        assert all(r["split"] == "test" for r in kept)
        try:
            ev.load_bound_test_rows(whole, "0" * 64)
        except ev.E2Refusal as exc:
            assert "test split canonical SHA-256 mismatch" in str(exc)
        else:
            raise AssertionError("canonical split hash mismatch did not abort")


def test_train_file_keeps_strict_split_check():
    """The filter applies only to test; train calibration files stay strict."""
    with tempfile.TemporaryDirectory(prefix="v3_entry_rows_train_") as td:
        whole = Path(td) / "synthetic_whole.jsonl"
        whole.write_text(
            '{"pair_id":"probe-1","split":"probe"}\n'
            '{"pair_id":"train-1","split":"train"}\n',
            encoding="utf-8",
        )
        try:
            ev._load_jsonl_pairs(whole, "train")
        except ev.E2Refusal as exc:
            assert "non-train row" in str(exc)
        else:
            raise AssertionError("non-train row was silently filtered")


def _run_all() -> int:
    """Minimal stdlib runner so tests work without pytest installed."""
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {name}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
