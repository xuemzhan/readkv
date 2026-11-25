"""v3-BM-MLP-KD internal control — real GPU entry (G1 released, G2 pilot only).

Frozen spec: ``docs/decisions/v3_baseline_spec.md`` §2.  This package does NOT
touch ``configs/prereg/gpu_followup_v3.0.yaml`` or any frozen file, and the
control is explicitly NOT a published-method (faithful) baseline.

Hard discipline (mirrors ``experiments/e1_variant_gpu.py``): explicit hash-bound
train / val / manifest paths, no test path, no bare ``master`` alias, no data
rebuild, no test-content read.  Module level is stdlib only; torch / models /
readkv are imported lazily in the GPU path and in ``--cpu-selfcheck``.

Usage (G2 technical pilot only, single seed / small sample)::

    .venv/bin/python -m experiments.v3_e6_control_gpu --cpu-selfcheck
    .venv/bin/python -m experiments.v3_e6_control_gpu \
        --run-id v3_E6_BM-MLP-KD_s0_smoke --seed 0 --smoke \
        --out-dir reports/_non_authoritative/v3_g2_pilot \
        --train-path data/variants_v3/fully_repaired/train_seed0.jsonl \
        --train-sha256 <frozen> \
        --val-path data/variants_v3/fully_repaired/val_seed0.jsonl \
        --val-sha256 <frozen> \
        --manifest-path data/variants_v3/manifest.json --manifest-sha256 <frozen> \
        --teacher <pinned-snapshot> --student <pinned-snapshot>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

CRITERIA_SOURCE = "configs/prereg/gpu_followup_v3.0.yaml"
SPEC_SOURCE = "docs/decisions/v3_baseline_spec.md"
SEEDS = (0, 1, 2)
EPOCHS = 8
LR = 1e-3
LAM_KD, LAM_REG, LAM_CF = 1.0, 1e-4, 0.0
DTYPE, KERNEL = "bfloat16", "sdpa"
SMOKE_N_TRAIN, SMOKE_N_VAL = 6, 6
EXPECTED_PARAMS = 7_340_032
TAU, SELF_THRESHOLD = 1.0, 0.1

CONFIG_KEYS = {
    "run_id", "protocol_version", "git_hash", "created_at", "seed", "device",
    "dtype", "kernel", "zero_re_prefill", "experiment_config", "metadata",
}
SCORE_KEYS = {
    "pair_id", "split", "arm", "seed", "E_CF", "dual_correct", "evaluable",
    "template_family", "cluster",
}
METRIC_KEYS = {
    "run_id", "mapper", "trainable_params", "zero_re_prefill", "sealed_test_read",
    "criteria_source", "spec_source", "train_audit", "memory", "elapsed_sec",
}
MANIFEST_KEYS = {"run_id", "files"}


class HashMismatch(ValueError):
    pass


class PathRejected(ValueError):
    pass


# ---------------------------------------------------------------------------
# CLI / validation
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--cpu-selfcheck", action="store_true",
                   help="stdlib+torch CPU check: frozen structure, CLI, hashing, path isolation, schema")
    p.add_argument("--run-id", default=None, help="v3_E6_<tag>_s<seed>[_smoke]")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--out-dir", default=None,
                   help="artifact parent dir; reports/_non_authoritative/ only with --smoke")
    p.add_argument("--train-path", default=None)
    p.add_argument("--train-sha256", default=None)
    p.add_argument("--val-path", default=None)
    p.add_argument("--val-sha256", default=None)
    p.add_argument("--manifest-path", default=None)
    p.add_argument("--manifest-sha256", default=None)
    p.add_argument("--teacher", default=None, help="pinned snapshot dir; bare master forbidden")
    p.add_argument("--student", default=None, help="pinned snapshot dir; bare master forbidden")
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b")
    p.add_argument("--device", default="cuda", choices=["cuda"])
    p.add_argument("--epochs", type=int, default=EPOCHS)
    p.add_argument("--lr", type=float, default=LR)
    p.add_argument("--n-train-smoke", type=int, default=SMOKE_N_TRAIN)
    p.add_argument("--n-val-smoke", type=int, default=SMOKE_N_VAL)
    return p


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    required = {
        "run-id": args.run_id, "seed": args.seed,
        "train-path": args.train_path, "train-sha256": args.train_sha256,
        "val-path": args.val_path, "val-sha256": args.val_sha256,
        "manifest-path": args.manifest_path, "manifest-sha256": args.manifest_sha256,
        "teacher": args.teacher, "student": args.student,
    }
    missing = [f"--{k}" for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(missing)}")
    if args.seed not in SEEDS:
        raise ValueError(f"--seed must be one of {SEEDS}")
    if args.epochs != EPOCHS or args.lr != LR:
        raise ValueError(f"training hyperparameters are frozen at epochs={EPOCHS} lr={LR}")
    if args.n_train_smoke <= 0 or args.n_val_smoke <= 0:
        raise ValueError("smoke sample sizes must be positive")
    if args.out_dir and "_non_authoritative" in str(args.out_dir) and not args.smoke:
        raise ValueError("--out-dir may point at reports/_non_authoritative/ only with --smoke")
    if not str(args.run_id).startswith("v3_E6_"):
        raise ValueError("--run-id must start with v3_E6_")
    if f"s{args.seed}" not in str(args.run_id):
        raise ValueError("--run-id must encode the seed")


# ---------------------------------------------------------------------------
# Hashing / path isolation
# ---------------------------------------------------------------------------


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_path_not_test(path: str | Path, label: str) -> None:
    p = Path(path)
    parts = {x.lower() for x in p.parts}
    name = p.name.lower()
    if "test" in parts or "test" in name or name == "cf_pairs.jsonl":
        raise PathRejected(f"{label} path points at sealed/unlocked test: {p}")


def check_model_pin(path: str | Path, label: str) -> None:
    p = str(path).rstrip("/")
    parts = {x.lower() for x in p.split("/")}
    if not p or parts & {"master", "main", "latest"}:
        raise PathRejected(f"{label} must be pinned to a fixed revision (got {p!r})")


def verify_hash_binding(args: argparse.Namespace) -> dict[str, str]:
    expected = {"train": args.train_sha256, "val": args.val_sha256,
                "manifest": args.manifest_sha256}
    paths = {"train": args.train_path, "val": args.val_path,
             "manifest": args.manifest_path}
    actual: dict[str, str] = {}
    for label, path in paths.items():
        check_path_not_test(path, label)
        if not Path(path).is_file():
            raise FileNotFoundError(f"{label}: {path}")
        actual[label] = sha256_file(path)
        want = str(expected[label]).strip().lower()
        if actual[label] != want:
            raise HashMismatch(
                f"{label} SHA-256 mismatch: expected {want}, computed {actual[label]} ({path})"
            )
    check_model_pin(args.teacher, "teacher")
    check_model_pin(args.student, "student")
    return actual


def register_clean_split(manifest: Mapping[str, Any], args: argparse.Namespace,
                         sha: Mapping[str, str]) -> dict[str, Any]:
    """E6 uses the same clean v2.1 train/val as kd_only: fully_repaired seed."""
    fr = manifest.get("variants", {}).get("fully_repaired", {})
    registered: dict[str, str] = {}
    rows: dict[str, int] = {}
    for entry in fr.get("files", []):
        if entry.get("seed") == args.seed:
            registered[str(entry.get("split"))] = str(entry.get("sha256", "")).lower()
            rows[str(entry.get("split"))] = int(entry.get("rows", 0))
    for label in ("train", "val"):
        if registered.get(label) != sha[label]:
            raise ValueError(
                f"{label} SHA-256 does not match fully_repaired seed{args.seed} "
                f"registered in the frozen manifest"
            )
    return {
        "variant": "fully_repaired", "seed": int(args.seed),
        "train": {"path": args.train_path, "sha256": sha["train"], "rows_registered": rows.get("train")},
        "val": {"path": args.val_path, "sha256": sha["val"], "rows_registered": rows.get("val")},
        "manifest": {"path": args.manifest_path, "sha256": sha["manifest"]},
        "reason": "E6 frozen clean split (same as kd_only); fully_repaired is a version difference vs legacy",
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not rows:
        raise ValueError(f"empty JSONL: {path}")
    return rows


# ---------------------------------------------------------------------------
# Config / artifacts (same layout as the v3 entries)
# ---------------------------------------------------------------------------


def run_root(args: argparse.Namespace) -> Path:
    if args.out_dir:
        return Path(args.out_dir)
    return ROOT / "reports" / ("_non_authoritative" if args.smoke else "runs")


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def build_config(args: argparse.Namespace, *, sha: Mapping[str, str],
                 registration: Mapping[str, Any], n_train: int, n_val: int) -> dict[str, Any]:
    import subprocess
    from datetime import datetime, timezone

    try:
        git = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        git = "no-git"
    exp = {
        "stage": "E6", "gate": "GPU_followup_v3.0", "backend": "gpu" if not args.cpu_selfcheck else "cpu_selfcheck",
        "experiment": "v3-BM-MLP-KD", "seed": int(args.seed), "device": args.device,
        "dtype": DTYPE, "kernel": KERNEL, "zero_re_prefill": True,
        "teacher": args.teacher, "student": args.student, "model_pair": args.model_pair,
        "trainable_params": EXPECTED_PARAMS, "epochs": EPOCHS, "lr": LR,
        "lam_kd": LAM_KD, "lam_reg": LAM_REG, "lam_cf": LAM_CF,
        "input_sha256": dict(sha), "split_registration": dict(registration),
        "criteria_source": CRITERIA_SOURCE, "spec_source": SPEC_SOURCE,
        "sealed_test_read": False, "smoke": bool(args.smoke),
        "n_train": n_train, "n_val": n_val,
    }
    return {
        "run_id": args.run_id,
        "protocol_version": "3.0",
        "git_hash": git,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": int(args.seed), "device": args.device, "dtype": DTYPE, "kernel": KERNEL,
        "zero_re_prefill": True,
        "experiment_config": exp,
        "metadata": {
            "stage": "E6", "experiment": "v3-BM-MLP-KD", "protocol_version": "3.0",
            "non_authoritative": bool(args.smoke), "sealed_test_read": False,
            "criteria_source": CRITERIA_SOURCE,
            "faithful_published_baseline": False, "reproduction_gate": "NOT_PASSED",
        },
    }


def validate_artifact_schema(files: Mapping[str, Any]) -> None:
    cfg = files.get("config.json")
    if not isinstance(cfg, Mapping) or not CONFIG_KEYS <= set(cfg):
        raise ValueError("config.json schema violation")
    scores = files.get("scores.jsonl")
    if not isinstance(scores, list) or not scores:
        raise ValueError("scores.jsonl schema violation (empty or not a list)")
    for row in scores:
        if not SCORE_KEYS <= set(row):
            raise ValueError(f"scores.jsonl row schema violation: {sorted(SCORE_KEYS - set(row))}")
    met = files.get("metrics.json")
    if not isinstance(met, Mapping) or not METRIC_KEYS <= set(met):
        raise ValueError("metrics.json schema violation")
    man = files.get("manifest.json")
    if not isinstance(man, Mapping) or not MANIFEST_KEYS <= set(man):
        raise ValueError("manifest.json schema violation")


def write_artifacts(args: argparse.Namespace, root: Path, config: Mapping[str, Any],
                    rows: Sequence[Mapping[str, Any]], metrics: Mapping[str, Any]) -> Path:
    out = root / args.run_id
    out.mkdir(parents=True, exist_ok=False)  # never overwrite history
    _write_json(out / "config.json", config)
    with (out / "scores.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), ensure_ascii=False, default=str) + "\n")
    _write_json(out / "metrics.json", metrics)
    files = []
    for name in ("config.json", "scores.jsonl", "metrics.json"):
        p = out / name
        files.append({"name": name, "sha256": sha256_file(p), "size": p.stat().st_size})
    _write_json(out / "manifest.json", {"run_id": args.run_id, "files": files})
    validate_artifact_schema({
        "config.json": json.loads((out / "config.json").read_text(encoding="utf-8")),
        "scores.jsonl": [json.loads(x) for x in (out / "scores.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()],
        "metrics.json": json.loads((out / "metrics.json").read_text(encoding="utf-8")),
        "manifest.json": json.loads((out / "manifest.json").read_text(encoding="utf-8")),
    })
    return out


def write_abort_config(args: argparse.Namespace, root: Path, reason: str) -> Path:
    out = root / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    _write_json(out / "config.json", {
        "run_id": args.run_id, "protocol_version": "3.0", "status": "ABORTED",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed, "device": args.device, "dtype": DTYPE, "kernel": KERNEL,
        "zero_re_prefill": True,
        "experiment_config": {
            "stage": "E6", "experiment": "v3-BM-MLP-KD", "criteria_source": CRITERIA_SOURCE,
            "spec_source": SPEC_SOURCE, "sealed_test_read": False, "reason": reason,
        },
    })
    _write_json(out / "manifest.json", {
        "run_id": args.run_id, "status": "ABORTED",
        "files": [{"name": "config.json", "sha256": sha256_file(out / "config.json"),
                   "size": (out / "config.json").stat().st_size}],
    })
    return out


# ---------------------------------------------------------------------------
# CPU-only self-check (no model, no GPU, no run directory)
# ---------------------------------------------------------------------------


def cpu_selfcheck() -> int:
    import tempfile

    from readkv.mapper.mlp_kd import EXPECTED_PARAMS as MODULE_BUDGET, MLPLinearKDModule

    checks: dict[str, Any] = {}
    module = MLPLinearKDModule()
    module.assert_budget()
    checks["param_count_frozen"] = module.parameter_count() == EXPECTED_PARAMS == MODULE_BUDGET == 7_340_032
    named = dict(module.named_parameters())
    checks["no_bias_structure"] = (
        set(named) == {"W_K", "W_V"}
        and all("bias" not in n for n in named)
        and named["W_K"].shape == (28, 8, 128, 128)
        and named["W_V"].shape == (28, 8, 128, 128)
    )
    checks["identity_init"] = bool(
        torch_allclose(module.W_K.detach().cpu(), module.W_V.detach().cpu())
    )

    with tempfile.TemporaryDirectory(prefix="e6_selfcheck_") as td:
        base = Path(td)
        train = base / "train_seed0.jsonl"
        val = base / "val_seed0.jsonl"
        mani = base / "manifest.json"
        train.write_text('{"pair_id": "x"}\n', encoding="utf-8")
        val.write_text('{"pair_id": "y"}\n', encoding="utf-8")
        mani.write_text('{"variants": {}}\n', encoding="utf-8")
        sha = {"train": sha256_file(train), "val": sha256_file(val), "manifest": sha256_file(mani)}
        argv = [
            "--cpu-selfcheck", "--run-id", "v3_E6_BM-MLP-KD_s0_smoke", "--seed", "0",
            "--train-path", str(train), "--train-sha256", sha["train"],
            "--val-path", str(val), "--val-sha256", sha["val"],
            "--manifest-path", str(mani), "--manifest-sha256", sha["manifest"],
            "--teacher", "/models/Qwen3-1.7B/snapshots/abc1234def5678",
            "--student", "/models/Qwen3-0.6B/snapshots/98fedcba7654321", "--smoke",
        ]
        args = parse_args(argv)
        validate_args(args)
        checks["cli_accepts_frozen_arguments"] = True

        bad = parse_args([a for a in argv if a != "--run-id" and a != "v3_E6_BM-MLP-KD_s0_smoke"])
        try:
            validate_args(bad)
            raise AssertionError("missing --run-id was accepted")
        except ValueError:
            checks["cli_rejects_missing_required"] = True
        for bad_argv, label in (
            (argv + ["--epochs", "4"], "cli_rejects_unfrozen_epochs"),
            (argv + ["--lr", "0.01"], "cli_rejects_unfrozen_lr"),
        ):
            try:
                validate_args(parse_args(bad_argv))
                raise AssertionError(f"{label} accepted")
            except ValueError:
                checks[label] = True

        bound = verify_hash_binding(args)
        checks["hash_binding_matches"] = bound == sha
        train.write_text('{"pair_id": "x"}\n{"pair_id": "tampered"}\n', encoding="utf-8")
        try:
            verify_hash_binding(args)
            raise AssertionError("hash mismatch was not detected")
        except HashMismatch:
            checks["hash_mismatch_aborts"] = True
        train.write_text('{"pair_id": "x"}\n', encoding="utf-8")

        for bad_path in ("data/tasks/cf_pairs.jsonl", "/root/data/test/val_seed0.jsonl"):
            try:
                check_path_not_test(bad_path, "val")
                raise AssertionError(f"test path accepted: {bad_path}")
            except PathRejected:
                pass
        checks["test_path_rejected"] = True
        for bad_pin in ("/models/Qwen3-1.7B/snapshots/master", "master"):
            try:
                check_model_pin(bad_pin, "teacher")
                raise AssertionError(f"unpinned model accepted: {bad_pin}")
            except PathRejected:
                pass
        checks["bare_master_rejected"] = True

        cfg = build_config(args, sha=sha, registration={"variant": "fully_repaired", "seed": 0},
                           n_train=1, n_val=1)
        row = {
            "pair_id": "p0", "split": "val", "arm": "joint", "seed": 0, "E_CF": 0.0,
            "dual_correct": 1.0, "evaluable": True, "template_family": "F1", "cluster": "c0",
        }
        met = {
            "run_id": args.run_id, "mapper": "v3-BM-MLP-KD", "trainable_params": EXPECTED_PARAMS,
            "zero_re_prefill": True, "sealed_test_read": False,
            "criteria_source": CRITERIA_SOURCE, "spec_source": SPEC_SOURCE,
            "train_audit": {"trainable_params": EXPECTED_PARAMS},
            "memory": {}, "elapsed_sec": 0.0,
        }
        validate_artifact_schema({
            "config.json": cfg, "scores.jsonl": [row], "metrics.json": met,
            "manifest.json": {"run_id": args.run_id, "files": []},
        })
        checks["artifact_schema_valid"] = True
        bad_met = dict(met)
        bad_met.pop("train_audit")
        try:
            validate_artifact_schema({"config.json": cfg, "scores.jsonl": [row],
                                      "metrics.json": bad_met,
                                      "manifest.json": {"run_id": args.run_id, "files": []}})
            raise AssertionError("broken metrics schema was accepted")
        except ValueError:
            checks["artifact_schema_rejects_broken_metrics"] = True

    if not all(checks.values()):
        raise AssertionError(f"cpu selfcheck failed: {checks}")
    print(json.dumps({"mode": "cpu-selfcheck", "status": "PASS", "checks": checks,
                      "note": "no model load / no GPU forward / no run directory created"},
                     ensure_ascii=False, indent=2))
    return 0


def torch_allclose(a: Any, b: Any) -> bool:
    import torch

    return bool(torch.allclose(a, b))


# ---------------------------------------------------------------------------
# GPU path
# ---------------------------------------------------------------------------


def load_model(path: str, device: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(
        path, dtype=getattr(torch, DTYPE), attn_implementation=KERNEL
    ).to(device)
    model.eval()
    model.config.use_cache = True
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok


def run_gpu(args: argparse.Namespace, sha: Mapping[str, str],
            registration: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    import numpy as np  # noqa: F401
    import torch
    from transformers import DynamicCache

    from readkv.mapper.mlp_kd import train_mlp_kd_gpu
    from readkv.models.gpu_backend import GPUBackend
    from readkv.models.hooks import _apply_rope, _rope_cos_sin, inject_and_generate, verify_zero_re_prefill
    from readkv.models.layer_map import LayerMap

    try:
        from experiments.e1_variant_gpu import pair_score
    except ImportError:  # pragma: no cover
        from e1_variant_gpu import pair_score  # type: ignore

    tm, tt = load_model(args.teacher, args.device)
    sm, st = load_model(args.student, args.device)
    n_s, n_t = int(sm.config.num_hidden_layers), int(tm.config.num_hidden_layers)
    if n_s != n_t or n_s != 28:
        raise ValueError(f"v3-BM-MLP-KD requires equal-depth 28->28; got teacher {n_t} student {n_s}")
    lmap = LayerMap(n_s, n_t, kind="identity")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=DTYPE,
                         kernel=KERNEL, layer_map=lmap)

    trains = read_jsonl(args.train_path)
    vals = read_jsonl(args.val_path)
    if args.smoke:
        trains, vals = trains[: args.n_train_smoke], vals[: args.n_val_smoke]
    if len(trains) < 1 or len(vals) < 1:
        raise ValueError("need at least one train and one val pair")

    torch.cuda.reset_peak_memory_stats()
    t_train = time.time()
    mapper, train_audit = train_mlp_kd_gpu(
        backend, trains, epochs=args.epochs, lr=args.lr, seed=args.seed
    )
    train_sec = round(time.time() - t_train, 1)

    rows: list[dict[str, Any]] = []
    self_identity_max_abs_diff = 0.0
    joint_audit_example: dict[str, Any] | None = None
    for pair in vals:
        self_a = backend.pair_side_cache(pair, "A", "student")
        self_b = backend.pair_side_cache(pair, "B", "student")
        id_a = backend.inject(self_a)
        id_b = backend.inject(self_b)
        joint_a = mapper.transform(backend.pair_side_cache(pair, "A", "teacher"))
        joint_b = mapper.transform(backend.pair_side_cache(pair, "B", "teacher"))
        qdoc = {"query": pair["query"], "text": pair["query"]}
        sa = backend.candidate_logits(self_a, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        sb = backend.candidate_logits(self_b, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        ia = backend.candidate_logits(id_a, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        ib = backend.candidate_logits(id_b, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        self_identity_max_abs_diff = max(
            self_identity_max_abs_diff,
            float(np.max(np.abs(sa - ia))), float(np.max(np.abs(sb - ib))),
        )
        ja = backend.candidate_logits(joint_a, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        jb = backend.candidate_logits(joint_b, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
        for arm, la, lb in (("self", sa, sb), ("identity", ia, ib), ("joint", ja, jb)):
            row = pair_score(pair, arm, [float(x) for x in sa], [float(x) for x in sb],
                             [float(x) for x in la], [float(x) for x in lb],
                             tau=TAU, self_threshold=SELF_THRESHOLD)
            row.update({"seed": int(args.seed)})
            rows.append(row)

        if joint_audit_example is None:
            q_ids = st(str(pair["query"]), add_special_tokens=False).input_ids
            q_t = torch.as_tensor(q_ids, device=args.device, dtype=torch.long)
            mapped = mapper.module.map_cache(backend.pair_side_cache(pair, "A", "teacher"))
            doc_len = next(iter(mapped.values()))[0].shape[1]
            doc_pos = torch.arange(doc_len, device=args.device)[None]
            cos, sin = _rope_cos_sin(sm, doc_pos, dtype=torch.float32)
            kv = DynamicCache(config=sm.config)
            for layer in sorted(mapped):
                k, v = mapped[layer]
                k_roped = _apply_rope(k.unsqueeze(0), cos, sin).to(dtype=getattr(torch, DTYPE))
                kv.update(k_roped, v.unsqueeze(0).to(dtype=getattr(torch, DTYPE)), layer)
            # Formal inject_and_generate audit on a native student cache (identity path).
            res = inject_and_generate(sm, self_a, q_t, attn_implementation=KERNEL)
            ok = verify_zero_re_prefill(res, expected_query_len=len(q_ids), strict=True)
            joint_audit_example = {
                "zero_re_prefill": bool(ok),
                "forward_audit": res.audit.as_dict(),
                "doc_len": int(doc_len),
                "n_cache_layers": int(joint_a.n_layers),
                "cache_shapes": {str(l): list(joint_a.layer(l)[0].shape) for l in joint_a.layers[:2]},
            }

    peak_alloc = int(torch.cuda.max_memory_allocated())
    peak_reserved = int(torch.cuda.max_memory_reserved())
    joint_rows = [r for r in rows if r["arm"] == "joint"]
    self_rows = [r for r in rows if r["arm"] == "self"]
    metrics: dict[str, Any] = {
        "run_id": args.run_id,
        "mapper": "v3-BM-MLP-KD",
        "trainable_params": mapper.module.parameter_count(),
        "zero_re_prefill": bool(train_audit["zero_re_prefill_train"]
                                and joint_audit_example and joint_audit_example["zero_re_prefill"]),
        "sealed_test_read": False,
        "criteria_source": CRITERIA_SOURCE, "spec_source": SPEC_SOURCE,
        "authoritative": False, "pilot": True,
        "faithful_published_baseline": False, "reproduction_gate": "NOT_PASSED",
        "train_audit": train_audit,
        "self_identity_max_abs_diff": float(self_identity_max_abs_diff),
        "joint_audit_example": joint_audit_example,
        "memory": {"peak_allocated_bytes": peak_alloc, "peak_reserved_bytes": peak_reserved,
                   "peak_allocated_mib": round(peak_alloc / 1024 ** 2, 1),
                   "peak_reserved_mib": round(peak_reserved / 1024 ** 2, 1)},
        "n_student_forwards_eval": int(backend.n_injections),
        "n_captures_eval": int(backend.n_captures),
        "n_train": len(trains), "n_val": len(vals), "n_scores": len(rows),
        "joint_E_CF_mean": float(np.mean([r["E_CF"] for r in joint_rows])) if joint_rows else None,
        "self_dual_correct": float(np.mean([r["dual_correct"] for r in self_rows])) if self_rows else None,
        "joint_dual_correct": float(np.mean([r["dual_correct"] for r in joint_rows])) if joint_rows else None,
        "train_sec": train_sec,
        "elapsed_sec": round(time.time() - t_train, 1),
        "note": "G2 technical pilot only; not authoritative, no scientific conclusion, no test read.",
    }
    if metrics["trainable_params"] != EXPECTED_PARAMS:
        raise AssertionError("trainable parameter count drifted from the frozen budget")
    if self_identity_max_abs_diff > 1e-4:
        raise AssertionError("Self/Identity mismatch exceeds tolerance")
    if not metrics["zero_re_prefill"]:
        raise AssertionError("zero re-prefill violated in E6 pilot")
    return metrics, rows


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.cpu_selfcheck:
        return cpu_selfcheck()
    try:
        validate_args(args)
    except ValueError as exc:
        print(json.dumps({"status": "ABORTED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    root = run_root(args)
    try:
        sha = verify_hash_binding(args)
        manifest = json.loads(Path(args.manifest_path).read_text(encoding="utf-8"))
        registration = register_clean_split(manifest, args, sha)
    except (ValueError, OSError) as exc:
        out = write_abort_config(args, root, f"{type(exc).__name__}: {exc}")
        print(json.dumps({"status": "ABORTED", "run_dir": str(out), "reason": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        metrics, rows = run_gpu(args, sha, registration)
    except Exception as exc:  # noqa: BLE001 - honest failure accounting
        out = write_abort_config(args, root, f"COMPUTE_FAILED: {type(exc).__name__}: {exc}")
        print(json.dumps({"status": "ABORTED", "run_dir": str(out),
                          "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    config = build_config(args, sha=sha, registration=registration,
                          n_train=metrics["n_train"], n_val=metrics["n_val"])
    out = write_artifacts(args, root, config, rows, metrics)
    print(json.dumps({
        "run_id": args.run_id, "status": "COMPLETE", "run_dir": str(out),
        "trainable_params": metrics["trainable_params"],
        "zero_re_prefill": metrics["zero_re_prefill"],
        "peak_allocated_mib": metrics["memory"]["peak_allocated_mib"],
        "elapsed_sec": metrics["elapsed_sec"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
