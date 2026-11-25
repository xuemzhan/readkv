"""E1 单缺陷干预筛查独立入口（protocol-v3.0，G1 实现；本轮未运行任何 GPU）。

严格独立：**显式接收 train / val / manifest 三条路径 + 各自 SHA-256**，只读这些
文件里的 CFPair 记录；**绝不调用** ``P1_gpu.py`` 的自动数据重建 / 质量门路径。
Panel A = 变体 train + 固定 clean v2.1 val；Panel B = 固定 clean v2.1 train +
变体 val。等深 28→28 identity、bf16 / sdpa / zero-re-prefill、affine 闭式 ridge
λ=1e-3 全部固定；不得临场调参。

用法（本轮只做 CPU 自检；以下命令未经 PI G2/G3 放行不得执行）：
    python3 -m experiments.e1_variant_gpu --cpu-selfcheck

    python3 -m experiments.e1_variant_gpu --run-id v3_E1_dedup_only_s0_smoke \\
        --variant dedup_only --panel A \\
        --train-path data/variants_v3/dedup_only/train_seed0.jsonl \\
        --train-sha256 <frozen> --val-path data/variants_v3/fully_repaired/val_seed0.jsonl \\
        --val-sha256 <frozen> --manifest-path data/variants_v3/manifest.json \\
        --manifest-sha256 <frozen> --seed 0 --model-pair qwen3-1.7b-to-0.6b \\
        --teacher <pinned-snapshot> --student <pinned-snapshot> --smoke

module-level 只依赖标准库；torch / transformers / numpy 全部在 GPU 路径内惰性导入，
因此 ``--cpu-selfcheck`` 在没有安装任何科学栈的机器上也能运行。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

VARIANTS = (
    "legacy_bundle", "dedup_only", "degenerate_only",
    "entity_disjoint_only", "template_disjoint_only", "fully_repaired",
)
PANELS = ("A", "B")
SEEDS = (0, 1, 2)
MODEL_PAIRS = ("qwen3-1.7b-to-0.6b",)

RIDGE_LAMBDA = 1e-3          # 冻结，不得按结果调整
TAU = 1.0                    # 与 audit_2x2_gpu / sequence_scoring_gpu 同口径
SELF_THRESHOLD = 0.1
N_RESAMPLES = 10_000
MIN_CLUSTERS = 24            # prereg §2 bootstrap.min_clusters_for_inference
CRITERIA_SOURCE = "configs/prereg/gpu_followup_v3.0.yaml"
CLEAN_VARIANT = "fully_repaired"   # 固定 clean v2.1（另一 commit，视为版本差异）

# 改变输入文本（query / 实体串）的变体：Panel B 需要 GPU 前向，CPU replay 无效。
TEXT_CHANGING_VARIANTS = {"entity_disjoint_only", "template_disjoint_only"}

CONFIG_KEYS = {
    "run_id", "protocol_version", "git_hash", "created_at", "seed", "device",
    "dtype", "kernel", "zero_re_prefill", "experiment_config", "metadata",
}
SCORE_KEYS = {
    "pair_id", "split", "slice_id", "template_family", "cluster", "arm",
    "variant", "panel", "seed", "E_CF", "dual_correct", "evaluable",
}
METRIC_KEYS = {
    "run_id", "variant", "panel", "arms", "L_self_minus_joint", "bootstrap",
    "exploratory", "zero_re_prefill", "sealed_test_read", "criteria_source",
}
MANIFEST_KEYS = {"run_id", "files"}


class HashMismatch(ValueError):
    """输入文件 SHA-256 与冻结期望不符。"""


class PathRejected(ValueError):
    """路径命中隔离规则（test / 未钉 master）。"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--cpu-selfcheck", action="store_true",
                   help="纯标准库自检：CLI / 哈希绑定 / 路径拒绝 / 产物 schema；不加载模型、不建 run 目录")
    p.add_argument("--run-id", default=None, help="v3_E1_<variant>_s<seed>[_smoke]")
    p.add_argument("--variant", choices=VARIANTS, default=None)
    p.add_argument("--panel", choices=PANELS, default=None)
    p.add_argument("--train-path", default=None)
    p.add_argument("--train-sha256", default=None)
    p.add_argument("--val-path", default=None)
    p.add_argument("--val-sha256", default=None)
    p.add_argument("--manifest-path", default=None)
    p.add_argument("--manifest-sha256", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--model-pair", default=MODEL_PAIRS[0], choices=MODEL_PAIRS)
    p.add_argument("--teacher", default=None, help="钉到具体 snapshot；禁止裸 master 别名")
    p.add_argument("--student", default=None, help="钉到具体 snapshot；禁止裸 master 别名")
    p.add_argument("--mapper", default="affine", choices=["affine"])
    p.add_argument("--ridge-lambda", type=float, default=RIDGE_LAMBDA)
    p.add_argument("--dtype", default="bfloat16", choices=["bfloat16"])
    p.add_argument("--kernel", default="sdpa", choices=["sdpa"])
    p.add_argument("--device", default="cuda", choices=["cuda"])
    p.add_argument("--n-resamples", type=int, default=N_RESAMPLES)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--smoke-n-val", type=int, default=6)
    p.add_argument("--out-dir", default=None,
                   help="产物父目录；仅 smoke 允许指向 reports/_non_authoritative/")
    p.add_argument("--cpu-replay-only", action="store_true",
                   help="只用冻结的逐对 logits 做 CPU 重算：不加载模型、不做 GPU 前向")
    p.add_argument("--replay-logits-path", default=None,
                   help="CPU replay 输入 JSONL（pair_id/arm/两侧 logits），须配 --replay-sha256")
    p.add_argument("--replay-sha256", default=None)
    p.add_argument("--allow-input-change-gpu-forward", action="store_true",
                   help="显式授权：输入文本被变体改动时仍做 GPU 前向，并单列 data_task_change")
    return p


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    required = {
        "run-id": args.run_id, "variant": args.variant, "panel": args.panel,
        "train-path": args.train_path, "train-sha256": args.train_sha256,
        "val-path": args.val_path, "val-sha256": args.val_sha256,
        "manifest-path": args.manifest_path, "manifest-sha256": args.manifest_sha256,
        "seed": args.seed, "teacher": args.teacher, "student": args.student,
    }
    missing = [f"--{k}" for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(missing)}")
    if args.seed not in SEEDS:
        raise ValueError(f"--seed must be one of {SEEDS}")
    if args.ridge_lambda != RIDGE_LAMBDA:
        raise ValueError(f"--ridge-lambda is frozen at {RIDGE_LAMBDA}")
    if args.n_resamples <= 0:
        raise ValueError("--n-resamples must be positive")
    if args.smoke_n_val <= 0:
        raise ValueError("--smoke-n-val must be positive")
    if args.out_dir and "_non_authoritative" in str(args.out_dir) and not args.smoke:
        raise ValueError("--out-dir may point at reports/_non_authoritative/ only with --smoke")
    if args.cpu_replay_only and not (args.replay_logits_path and args.replay_sha256):
        raise ValueError("--cpu-replay-only requires --replay-logits-path and --replay-sha256")
    if not str(args.run_id).startswith("v3_E1_"):
        raise ValueError("--run-id must follow v3_E1_<variant>_s<seed>[_smoke]")
    if args.variant not in str(args.run_id) or f"s{args.seed}" not in str(args.run_id):
        raise ValueError("--run-id must encode variant and seed")


# ---------------------------------------------------------------------------
# 哈希绑定 / 路径隔离
# ---------------------------------------------------------------------------


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_path_not_test(path: str | Path, label: str) -> None:
    """拒绝任何含 test 分量 / 文件名的路径（照搬 sequence_scoring_gpu 的隔离规则）。"""
    p = Path(path)
    parts = {x.lower() for x in p.parts}
    name = p.name.lower()
    # cf_pairs.jsonl 是含 sealed test split 的原始全量导出；E1 一律不读。
    if "test" in parts or "test" in name or name == "cf_pairs.jsonl":
        raise PathRejected(f"{label} path points at sealed test: {p}")


def check_model_pin(path: str | Path, label: str) -> None:
    """拒绝漂移别名 master / main / latest；只接受钉住的具体 snapshot。"""
    p = str(path).rstrip("/")
    parts = {x.lower() for x in p.split("/")}
    if not p or parts & {"master", "main", "latest"}:
        raise PathRejected(f"{label} must be pinned to a fixed revision (got {p!r})")


def verify_hash_binding(args: argparse.Namespace) -> dict[str, str]:
    """运行时重算三条输入（及可选 replay）的 SHA-256，不符即 abort。"""
    expected = {
        "train": args.train_sha256, "val": args.val_sha256,
        "manifest": args.manifest_sha256,
    }
    paths = {
        "train": args.train_path, "val": args.val_path,
        "manifest": args.manifest_path,
    }
    if args.replay_logits_path:
        expected["replay"] = args.replay_sha256
        paths["replay"] = args.replay_logits_path
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


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not rows:
        raise ValueError(f"empty JSONL: {path}")
    return rows


# ---------------------------------------------------------------------------
# 变体登记 / Panel 角色校验
# ---------------------------------------------------------------------------


def variants_for_hash(manifest: Mapping[str, Any], digest: str) -> list[str]:
    """一个哈希可对应多个变体（no-op 变体与 legacy 逐字节相同），返回全部候选。"""
    out: list[str] = []
    for variant, data in manifest.get("variants", {}).items():
        if any(str(e.get("sha256", "")).lower() == digest.lower()
               for e in data.get("files", [])):
            out.append(variant)
    return out


def register_variant(manifest: Mapping[str, Any], args: argparse.Namespace,
                     sha: Mapping[str, str]) -> dict[str, Any]:
    """逐变体登记改动 / 样本数 / slice+family 计数；校验 Panel 角色。"""
    variant, panel = args.variant, args.panel
    defn = dict(manifest.get("variant_definitions", {}).get(variant, {}))
    vdata = manifest.get("variants", {}).get(variant, {})
    train_candidates = variants_for_hash(manifest, sha["train"])
    val_candidates = variants_for_hash(manifest, sha["val"])
    if not train_candidates or not val_candidates:
        raise ValueError("train/val SHA-256 is not registered in the variant manifest")
    expected = (variant, CLEAN_VARIANT) if panel == "A" else (CLEAN_VARIANT, variant)
    if expected[0] not in train_candidates or expected[1] not in val_candidates:
        raise ValueError(
            f"Panel {panel} requires (train,val) variants {expected}; "
            f"hash matches train={train_candidates}, val={val_candidates}"
        )
    # 登记的角色按 CLI/Panel 期望确定；哈希可能同时命中 no-op 变体与 legacy（逐字节相同）。
    def _entry_for(v: str, split: str) -> dict[str, Any]:
        for e in manifest.get("variants", {}).get(v, {}).get("files", []):
            if e.get("split") == split and str(e.get("sha256", "")).lower() == sha[
                "train" if split == "train" else "val"].lower():
                return e
        return {}
    train_f, val_f = _entry_for(expected[0], "train"), _entry_for(expected[1], "val")
    if not train_f or not val_f:
        raise ValueError("train/val registered entry missing for the expected role")
    changes = dict(vdata.get("changes", {}).get(f"seed{args.seed}", {}))
    composition_changed = bool(vdata.get("composition_changed_vs_legacy")) or bool(
        train_f.get("rows") != 120 or val_f.get("rows") != 60
    )
    return {
        "variant": variant,
        "panel": panel,
        "changed_attribute": defn.get("changed_attribute"),
        "scope": defn.get("scope"),
        "rule": defn.get("rule"),
        "caveat": defn.get("caveat"),
        "composition_changed_vs_legacy": composition_changed,
        "family_count_changed_vs_legacy": bool(vdata.get("family_count_changed_vs_legacy")),
        "version_difference_flag": bool(vdata.get("version_difference_flag")) or composition_changed,
        "train": {
            "variant": expected[0], "hash_matches_variants": train_candidates,
            "path": args.train_path, "sha256": sha["train"],
            "rows_registered": train_f.get("rows"),
            "template_family_count": train_f.get("template_family_count"),
            "template_families": train_f.get("template_families", []),
            "slice_counts": train_f.get("slice_counts", {}),
            "degenerate_mustflip_rows": train_f.get("degenerate_mustflip_rows"),
        },
        "val": {
            "variant": expected[1], "hash_matches_variants": val_candidates,
            "path": args.val_path, "sha256": sha["val"],
            "rows_registered": val_f.get("rows"),
            "template_family_count": val_f.get("template_family_count"),
            "template_families": val_f.get("template_families", []),
            "slice_counts": val_f.get("slice_counts", {}),
            "degenerate_mustflip_rows": val_f.get("degenerate_mustflip_rows"),
        },
        "changes": {
            "removed_pair_ids": changes.get("removed_pair_ids", {}),
            "added_pair_ids": changes.get("added_pair_ids", {}),
            "n_text_hash_changed": {
                k: len(v) for k, v in changes.get("text_hash_changed", {}).items()
            },
            "substitution_map_present": changes.get("substitution_map") is not None,
            "n_query_rewrites": len(changes.get("query_rewrites", [])),
        },
    }


def input_text_changed(manifest: Mapping[str, Any], args: argparse.Namespace) -> bool:
    """该 Panel 的评分输入是否被变体改了文本（决定 CPU replay 是否合法）。"""
    changes = manifest.get("variants", {}).get(args.variant, {}).get(
        "changes", {}).get(f"seed{args.seed}", {})
    split = "val" if args.panel == "B" else "train"
    changed = bool(changes.get("text_hash_changed", {}).get(split))
    rewrites = bool(changes.get("query_rewrites"))
    # 这两个变体在 manifest 中声明 VAL only / TRAIN verbatim：query 改写只影响 Panel B。
    if rewrites and (args.panel == "B" or args.variant not in TEXT_CHANGING_VARIANTS):
        changed = True
    return bool(changed or (args.panel == "B" and args.variant in TEXT_CHANGING_VARIANTS))


def require_gpu_forward_authorization(args: argparse.Namespace, text_changed: bool) -> dict[str, Any]:
    """输入文本改变才要求显式授权；授权后单列 data_task_change。"""
    if text_changed and not args.allow_input_change_gpu_forward:
        raise PathRejected(
            "input text was changed by variant/panel (DATA-TASK change); GPU forward needs "
            "explicit --allow-input-change-gpu-forward. CPU replay on original logits is NOT valid."
        )
    return {
        "input_text_changed": bool(text_changed),
        "data_task_change": bool(text_changed),
        "gpu_forward_authorized_by_flag": bool(args.allow_input_change_gpu_forward),
        "cpu_replay_valid": not bool(text_changed),
    }


# ---------------------------------------------------------------------------
# 逐对指标（与 readkv.evaluate.counterfactual 公式一致，纯标准库实现）
# ---------------------------------------------------------------------------


def _logp_at(logits: Sequence[float], idx: int) -> float:
    m = max(logits)
    return float(logits[idx] - m - math.log(sum(math.exp(v - m) for v in logits)))


def _pick_correct(logits: Sequence[float], correct: str) -> bool:
    lab = str(correct).strip().upper()
    if lab.startswith("A") and lab.startswith("B"):
        return True  # F5 非翻转负控
    idx = max(range(len(logits)), key=lambda i: logits[i])
    return idx == (0 if lab.startswith("A") else 1)


def pair_score(pair: Mapping[str, Any], arm: str, self_a: Sequence[float], self_b: Sequence[float],
               trans_a: Sequence[float], trans_b: Sequence[float], *,
               tau: float = TAU, self_threshold: float = SELF_THRESHOLD) -> dict[str, Any]:
    # 每份缓存单独算 g(C,q) = logP(A|C,q) − logP(B|C,q)，与 PairCFRecord 同口径。
    g_sa = _logp_at(self_a, 0) - _logp_at(self_a, 1)
    g_sb = _logp_at(self_b, 0) - _logp_at(self_b, 1)
    g_ta = _logp_at(trans_a, 0) - _logp_at(trans_a, 1)
    g_tb = _logp_at(trans_b, 0) - _logp_at(trans_b, 1)
    d_self, d_trans = float(g_sa - g_sb), float(g_ta - g_tb)
    e_cf = abs(d_trans - d_self)
    evaluable = abs(d_self) > self_threshold
    dual = float(_pick_correct(trans_a, pair["correct_A"]) and
                 _pick_correct(trans_b, pair["correct_B"]))
    flip = None
    if evaluable:
        flip = float((d_self > 0) == (d_trans > 0))
    return {
        "pair_id": pair.get("pair_id", ""),
        "sample_id": pair.get("sample_id", ""),
        "sample_hash": pair.get("sample_hash", ""),
        "version_tag": pair.get("version_tag", ""),
        "split": pair.get("split", "val"),
        "slice_id": pair.get("slice_id", "F1"),
        "template_family": pair.get("template_family", pair.get("cluster", "")),
        "cluster": pair.get("cluster", pair.get("pair_id", "")),
        "arm": arm,
        "must_flip": bool(pair.get("must_flip", True)),
        "candidate_A": pair.get("candidate_A", ""),
        "candidate_B": pair.get("candidate_B", ""),
        "g_self_A": g_sa, "g_self_B": g_sb, "g_trans_A": g_ta, "g_trans_B": g_tb,
        "D_self": d_self, "D_trans": d_trans,
        "E_CF": e_cf,
        "normalized_E_CF": float(e_cf / (abs(d_self) + tau)),
        "evaluable": evaluable,
        "flip_consistency": flip,
        "dual_correct": dual,
        "self_dual_correct": float(_pick_correct(self_a, pair["correct_A"]) and
                                   _pick_correct(self_b, pair["correct_B"])),
    }


def bootstrap_ci(values: Sequence[float], clusters: Sequence[str], *,
                 n_resamples: int = N_RESAMPLES, seed: int = 0) -> dict[str, Any]:
    """簇级百分位 bootstrap（主）+ 逐对区间（敏感性）由调用方各调一次。"""
    if len(values) != len(clusters) or not values:
        return {"point": 0.0, "ci": [0.0, 0.0], "n": 0}
    groups: dict[str, list[float]] = defaultdict(list)
    for v, c in zip(values, clusters):
        groups[str(c)].append(float(v))
    keys = sorted(groups)
    rng = random.Random(seed)
    draws = []
    for _ in range(n_resamples):
        picked = [keys[rng.randrange(len(keys))] for _ in keys]
        pool = [x for k in picked for x in groups[k]]
        draws.append(sum(pool) / len(pool))
    draws.sort()
    lo_i = min(len(draws) - 1, int(0.025 * len(draws)))
    hi_i = min(len(draws) - 1, int(0.975 * len(draws)))
    return {
        "point": float(sum(values) / len(values)),
        "ci": [float(draws[lo_i]), float(draws[hi_i])],
        "n": len(values),
        "n_clusters": len(keys),
    }


def summarize(rows: Sequence[Mapping[str, Any]], *, n_resamples: int, seed: int) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_arm[str(row["arm"])].append(dict(row))
    summaries: dict[str, Any] = {}
    for arm, arm_rows in by_arm.items():
        ecf = [float(r["E_CF"]) for r in arm_rows]
        fams = [str(r["template_family"]) for r in arm_rows]
        pair_ids = [str(r["pair_id"]) for r in arm_rows]
        fam_ci = bootstrap_ci(ecf, fams, n_resamples=n_resamples, seed=seed)
        pair_ci = bootstrap_ci(ecf, pair_ids, n_resamples=n_resamples, seed=seed)
        evaluable = [r for r in arm_rows if r["evaluable"]]
        flips = [float(r["flip_consistency"]) for r in evaluable
                 if r["flip_consistency"] is not None]
        summaries[arm] = {
            "n": len(arm_rows),
            "n_evaluable": len(evaluable),
            "dual_correct": float(sum(float(r["dual_correct"]) for r in arm_rows) / len(arm_rows)),
            "self_dual_correct": float(sum(float(r["self_dual_correct"]) for r in arm_rows) / len(arm_rows)),
            "E_CF": {"mean": fam_ci["point"], "ci_family": fam_ci["ci"],
                     "ci_pair_sensitivity": pair_ci["ci"]},
            "coverage": len(evaluable) / len(arm_rows),
            "flip_consistency": float(sum(flips) / len(flips)) if flips else None,
            "n_flip_evaluable": len(flips),
            "n_families": len(set(fams)),
        }
    joint = summaries.get("joint", {})
    info_gap = {
        name: float(summaries[name]["E_CF"]["mean"] - joint.get("E_CF", {}).get("mean", 0.0))
        for name in ("control:mismatch", "control:random", "control:zero") if name in summaries
    }
    all_fams = {str(r["template_family"]) for r in rows}
    return {
        "arms": summaries,
        "L_self_minus_joint": float(summaries.get("self", {}).get("dual_correct", 0.0)
                                    - summaries.get("joint", {}).get("dual_correct", 0.0)),
        "info_gap_control_minus_joint": info_gap,
        "bootstrap": {
            "primary_unit": "template_family", "n_resamples": n_resamples, "seed": seed,
            "sensitivity_unit": "pair", "min_clusters_for_inference": MIN_CLUSTERS,
        },
        "n_families": len(all_fams),
        "exploratory": len(all_fams) < MIN_CLUSTERS,
    }


# ---------------------------------------------------------------------------
# v2_context 风格配置 + stdlib 产物写入（与 RunContext 文件契约一致）
# ---------------------------------------------------------------------------


def v2_context(args: argparse.Namespace, *, sha: Mapping[str, str],
               registration: Mapping[str, Any], n_train: int, n_val: int,
               forward_auth: Mapping[str, Any], replay_only: bool) -> dict[str, Any]:
    exp = {
        "stage": "E1", "gate": "GPU_followup_v3.0", "backend": "cpu_replay" if replay_only else "gpu",
        "variant": args.variant, "panel": args.panel, "seed": args.seed,
        "bootstrap_seed": args.seed, "model_pair": args.model_pair,
        "teacher": args.teacher, "student": args.student,
        "train_path": args.train_path, "val_path": args.val_path,
        "manifest_path": args.manifest_path, "input_sha256": dict(sha),
        "criteria_source": CRITERIA_SOURCE,
        "sealed_test_read": False,
        "zero_re_prefill": True,
        "zero_re_prefill_basis": "no_gpu_forward_cpu_replay" if replay_only else "forward_audit",
        "dtype": args.dtype, "kernel": args.kernel, "device": args.device,
        "mapper": "affine_per_layer_head", "ridge_lambda": RIDGE_LAMBDA,
        "layer_map": {"kind": "identity", "n_student_layers": 28, "n_teacher_layers": 28},
        "tau": TAU, "self_threshold": SELF_THRESHOLD, "n_resamples": args.n_resamples,
        "n_train": n_train, "n_val": n_val,
        "smoke": bool(args.smoke), "smoke_n_val": args.smoke_n_val if args.smoke else None,
        "cpu_replay_only": bool(replay_only),
        "replay_logits_path": args.replay_logits_path,
        "variant_registration": dict(registration),
        **dict(forward_auth),
    }
    try:
        git = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        git = "no-git"
    from datetime import datetime, timezone
    return {
        "run_id": args.run_id,
        "protocol_version": "3.0",
        "git_hash": git,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": int(args.seed),
        "device": args.device, "dtype": args.dtype, "kernel": args.kernel,
        "zero_re_prefill": True,
        "experiment_config": exp,
        "metadata": {
            "stage": "E1", "backend": exp["backend"], "protocol_version": "3.0",
            "non_authoritative": bool(args.smoke),
            "variant": args.variant, "panel": args.panel,
            "criteria_source": CRITERIA_SOURCE, "sealed_test_read": False,
        },
    }


def run_root(args: argparse.Namespace) -> Path:
    if args.out_dir:
        return Path(args.out_dir)
    return ROOT / "reports" / ("_non_authoritative" if args.smoke else "runs")


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_abort_config(args: argparse.Namespace, root: Path, reason: str) -> Path:
    """哈希/路径不符：写失败 config（不写 scores/metrics），不覆盖历史。"""
    out = root / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    _write_json(out / "config.json", {
        "run_id": args.run_id, "protocol_version": "3.0", "status": "ABORTED",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed, "device": args.device, "dtype": args.dtype, "kernel": args.kernel,
        "zero_re_prefill": True,
        "experiment_config": {
            "stage": "E1", "variant": args.variant, "panel": args.panel,
            "criteria_source": CRITERIA_SOURCE, "sealed_test_read": False,
            "reason": reason,
        },
    })
    # 明确不产生 scores.jsonl / metrics.json；不写空文件冒充 Results。
    _write_json(out / "manifest.json", {
        "run_id": args.run_id, "status": "ABORTED",
        "files": [{"name": "config.json", "sha256": sha256_file(out / "config.json"),
                   "size": (out / "config.json").stat().st_size}],
    })
    return out


def write_artifacts(args: argparse.Namespace, root: Path, config: Mapping[str, Any],
                    rows: Sequence[Mapping[str, Any]], metrics: Mapping[str, Any]) -> Path:
    """config.json / scores.jsonl / metrics.json / manifest.json，与 RunContext 同布局。"""
    out = root / args.run_id
    out.mkdir(parents=True, exist_ok=False)  # 不覆盖历史
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


# ---------------------------------------------------------------------------
# GPU 路径（惰性导入；本轮未执行）
# ---------------------------------------------------------------------------


def load_model(path: str, dtype: str, kernel: str, device: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(
        path, dtype=getattr(torch, dtype), attn_implementation=kernel
    ).to(device)
    model.eval()
    model.config.use_cache = True
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok


def fit_ready_pairs(train: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """must-flip 退化对（candidate_A==candidate_B）不进入 ridge 监督拟合。"""
    return [dict(p) for p in train if not (
        bool(p.get("must_flip")) and p.get("candidate_A") == p.get("candidate_B"))]


def build_backend_and_mapper(args: argparse.Namespace, trains: Sequence[Mapping[str, Any]]):
    import torch  # noqa: F401  (GPU 路径约定：模型/环境必须可用)
    from readkv.evaluate.pipeline import stack_caches
    from readkv.mapper.representation import AffineMapper
    from readkv.models.gpu_backend import GPUBackend
    from readkv.models.layer_map import LayerMap

    tm, tt = load_model(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load_model(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers)
    n_t = int(tm.config.num_hidden_layers)
    if n_s != n_t or n_s != 28:
        raise ValueError(f"E1 requires equal-depth 28->28 identity; got teacher {n_t} student {n_s}")
    lmap = LayerMap(n_s, n_t, kind="identity")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)
    fit_rows = fit_ready_pairs(trains)
    docs = [{"doc_id": f"{p['pair_id']}-{s}", "text": p[f"context_{s}"]}
            for p in fit_rows for s in ("A", "B")]
    mapper = AffineMapper(lam=RIDGE_LAMBDA, channel="both").fit(
        stack_caches(backend, docs, "teacher"),
        stack_caches(backend, docs, "student"),
        layer_map=lmap,
    )
    return backend, mapper, lmap


def arm_caches(backend: Any, mapper: Any, pair: Mapping[str, Any],
               mismatch_pair: Mapping[str, Any] | None):
    from readkv.evaluate.controls import build_control
    from readkv.evaluate.pipeline import combine

    self_a = backend.pair_side_cache(pair, "A", "student")
    self_b = backend.pair_side_cache(pair, "B", "student")
    m_a = mapper.transform(backend.pair_side_cache(pair, "A", "teacher"))
    m_b = mapper.transform(backend.pair_side_cache(pair, "B", "teacher"))
    arms = {
        "self": (self_a, self_b),
        "identity": (backend.inject(self_a), backend.inject(self_b)),
        "joint": (m_a, m_b),
        "k_only": (combine(m_a, self_a), combine(m_b, self_b)),
        "v_only": (combine(self_a, m_a), combine(self_b, m_b)),
        "control:random": (
            build_control(m_a, "random_gaussian", seed=0),
            build_control(m_b, "random_gaussian", seed=1),
        ),
        "control:zero": (build_control(m_a, "zero", seed=0), build_control(m_b, "zero", seed=1)),
    }
    if mismatch_pair is not None:
        arms["control:mismatch"] = (
            mapper.transform(backend.pair_side_cache(mismatch_pair, "A", "teacher")),
            mapper.transform(backend.pair_side_cache(mismatch_pair, "B", "teacher")),
        )
    return arms


def candidate_logits(backend: Any, cache: Any, pair: Mapping[str, Any]) -> list[float]:
    qdoc = {"query": pair["query"], "text": pair["query"]}
    out = backend.candidate_logits(
        cache, qdoc, candidates=(pair["candidate_A"], pair["candidate_B"]))
    return [float(v) for v in out]


def run_gpu_cell(args: argparse.Namespace, trains: Sequence[Mapping[str, Any]],
                 vals: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    backend, mapper, _ = build_backend_and_mapper(args, trains)
    rows: list[dict[str, Any]] = []
    for i, pair in enumerate(vals):
        mismatch = vals[(i + 1) % len(vals)] if len(vals) > 1 else None
        arms = arm_caches(backend, mapper, pair, mismatch)
        sa = candidate_logits(backend, arms["self"][0], pair)
        sb = candidate_logits(backend, arms["self"][1], pair)
        for arm, (ca, cb) in arms.items():
            la = candidate_logits(backend, ca, pair)
            lb = candidate_logits(backend, cb, pair)
            row = pair_score(pair, arm, sa, sb, la, lb)
            row.update({"variant": args.variant, "panel": args.panel, "seed": int(args.seed)})
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# CPU replay 路径（纯标准库，不加载模型）
# ---------------------------------------------------------------------------


def run_replay_cell(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in read_jsonl(args.replay_logits_path):
        # must-flip 退化对不参与重计分（标签/任务有效性缺陷）。
        if bool(raw.get("must_flip")) and raw.get("candidate_A") == raw.get("candidate_B"):
            continue
        sa = [float(v) for v in raw["self_logits_A"]]
        sb = [float(v) for v in raw["self_logits_B"]]
        la = [float(v) for v in raw["transfer_logits_A"]]
        lb = [float(v) for v in raw["transfer_logits_B"]]
        row = pair_score(raw, str(raw.get("arm", "joint")), sa, sb, la, lb)
        row.update({"variant": args.variant, "panel": args.panel, "seed": int(args.seed)})
        rows.append(row)
    if not rows:
        raise ValueError("CPU replay produced no evaluable rows")
    return rows


# ---------------------------------------------------------------------------
# CPU-only 自检
# ---------------------------------------------------------------------------


def cpu_selfcheck() -> int:
    import tempfile

    checks: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="e1_selfcheck_") as td:
        base = Path(td)
        train = base / "train_seed0.jsonl"
        val = base / "val_seed0.jsonl"
        mani = base / "manifest.json"
        train.write_text('{"pair_id": "x"}\n', encoding="utf-8")
        val.write_text('{"pair_id": "y"}\n', encoding="utf-8")
        mani.write_text('{"variants": {}, "variant_definitions": {}}\n', encoding="utf-8")
        sha = {"train": sha256_file(train), "val": sha256_file(val), "manifest": sha256_file(mani)}

        argv = [
            "--cpu-selfcheck", "--run-id", "v3_E1_legacy_bundle_s0_smoke",
            "--variant", "legacy_bundle", "--panel", "A",
            "--train-path", str(train), "--train-sha256", sha["train"],
            "--val-path", str(val), "--val-sha256", sha["val"],
            "--manifest-path", str(mani), "--manifest-sha256", sha["manifest"],
            "--seed", "0", "--model-pair", "qwen3-1.7b-to-0.6b",
            "--teacher", "/models/Qwen3-1.7B/snapshots/abc1234def5678",
            "--student", "/models/Qwen3-0.6B/snapshots/98fedcba7654321", "--smoke",
        ]
        args = parse_args(argv)
        validate_args(args)
        checks["cli_accepts_frozen_arguments"] = True

        # CLI 必填 / 冻结值拒绝
        bad = parse_args([a for a in argv if a != "--run-id" and a != "v3_E1_legacy_bundle_s0_smoke"])
        try:
            validate_args(bad)
            raise AssertionError("missing --run-id was accepted")
        except ValueError:
            checks["cli_rejects_missing_required"] = True
        try:
            validate_args(parse_args(argv + ["--ridge-lambda", "0.01"]))
            raise AssertionError("unfrozen ridge lambda was accepted")
        except ValueError:
            checks["cli_rejects_unfrozen_ridge_lambda"] = True

        # 哈希绑定：一致通过，篡改即 abort
        bound = verify_hash_binding(args)
        checks["hash_binding_matches"] = bound == sha
        train.write_text('{"pair_id": "x"}\n{"pair_id": "tampered"}\n', encoding="utf-8")
        try:
            verify_hash_binding(args)
            raise AssertionError("hash mismatch was not detected")
        except HashMismatch:
            checks["hash_mismatch_aborts"] = True
        train.write_text('{"pair_id": "x"}\n', encoding="utf-8")

        # 路径拒绝：test 分量 / 漂移 master 别名
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

        # 文本改动需显式授权；CPU replay 对文本改动无效
        auth = require_gpu_forward_authorization(args, text_changed=False)
        checks["no_flag_needed_without_text_change"] = auth["cpu_replay_valid"] is True
        try:
            require_gpu_forward_authorization(args, text_changed=True)
            raise AssertionError("text-changing GPU forward was allowed without flag")
        except PathRejected:
            checks["text_change_requires_explicit_flag"] = True
        authorized = require_gpu_forward_authorization(
            parse_args(argv + ["--allow-input-change-gpu-forward"]), text_changed=True)
        checks["explicit_flag_records_data_task_change"] = authorized["data_task_change"] is True

        # 产物 schema
        cfg = v2_context(args, sha=sha, registration={"variant": "legacy_bundle", "panel": "A"},
                         n_train=1, n_val=1, forward_auth=auth, replay_only=False)
        row = pair_score(
            {"pair_id": "p0", "correct_A": "A", "correct_B": "B"}, "joint",
            [1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0])
        row.update({"variant": "legacy_bundle", "panel": "A", "seed": 0})
        met = summarize([row], n_resamples=8, seed=0)
        met.update({
            "run_id": args.run_id, "variant": args.variant, "panel": args.panel,
            "zero_re_prefill": True, "sealed_test_read": False,
            "criteria_source": CRITERIA_SOURCE,
        })
        validate_artifact_schema({
            "config.json": cfg, "scores.jsonl": [row], "metrics.json": met,
            "manifest.json": {"run_id": args.run_id, "files": []},
        })
        checks["artifact_schema_valid"] = True
        bad_cfg = dict(cfg)
        bad_cfg.pop("experiment_config")
        try:
            validate_artifact_schema({"config.json": bad_cfg, "scores.jsonl": [row],
                                      "metrics.json": met,
                                      "manifest.json": {"run_id": args.run_id, "files": []}})
            raise AssertionError("broken config schema was accepted")
        except ValueError:
            checks["artifact_schema_rejects_broken_config"] = True

    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = ("build_cf_" + "pairs(", "run_cf_" + "pipeline(")
    checks["no_auto_data_rebuild_calls"] = all(token not in source for token in forbidden)
    if not checks["no_auto_data_rebuild_calls"]:
        raise AssertionError("entry point must not rebuild data")
    print(json.dumps({
        "mode": "cpu-selfcheck", "status": "PASS", "checks": checks,
        "note": "no model load / no GPU forward / no run directory created",
    }, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


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
    replay_only = bool(args.cpu_replay_only)
    try:
        sha = verify_hash_binding(args)
        manifest = json.loads(Path(args.manifest_path).read_text(encoding="utf-8"))
        registration = register_variant(manifest, args, sha)
        text_changed = input_text_changed(manifest, args)
        if replay_only:
            if text_changed:
                raise ValueError(
                    "CPU replay is NOT valid when the variant changed input text; "
                    "use GPU forward with --allow-input-change-gpu-forward instead"
                )
            forward_auth = {
                "input_text_changed": False, "data_task_change": False,
                "gpu_forward_authorized_by_flag": False, "cpu_replay_valid": True,
            }
        else:
            forward_auth = require_gpu_forward_authorization(args, text_changed)
    except (ValueError, OSError) as exc:
        # 哈希/路径/角色不符：写失败 config，绝不产生逐对分数。
        out = write_abort_config(args, root, f"{type(exc).__name__}: {exc}")
        print(json.dumps({"status": "ABORTED", "run_dir": str(out), "reason": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 2

    t0 = time.time()
    prefill_basis = "no_gpu_forward_cpu_replay" if replay_only else "forward_audit"
    try:
        if replay_only:
            rows = run_replay_cell(args)
            trains, vals = [], read_jsonl(args.val_path)
        else:
            trains, vals = read_jsonl(args.train_path), read_jsonl(args.val_path)
            if args.smoke:
                vals = vals[: args.smoke_n_val]
            if len(trains) < 2 or len(vals) < 2:
                raise ValueError("need at least 2 train and 2 val pairs")
            rows = run_gpu_cell(args, trains, vals)
    except Exception as exc:
        # 计算/前向失败：写失败 config（无 scores/metrics），如实入账，不伪造结果。
        out = write_abort_config(args, root, f"COMPUTE_FAILED: {type(exc).__name__}: {exc}")
        print(json.dumps({"status": "ABORTED", "run_dir": str(out),
                          "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
              file=sys.stderr)
        return 2

    metrics = summarize(rows, n_resamples=args.n_resamples, seed=args.seed)
    metrics.update({
        "run_id": args.run_id, "variant": args.variant, "panel": args.panel,
        "seed": int(args.seed), "backend": "cpu_replay" if replay_only else "gpu",
        "dtype": args.dtype, "kernel": args.kernel, "device": args.device,
        "zero_re_prefill": True,
        "zero_re_prefill_basis": prefill_basis,
        "sealed_test_read": False, "criteria_source": CRITERIA_SOURCE,
        "input_sha256": dict(sha), "variant_registration": registration,
        **forward_auth,
        "n_train": len(trains), "n_val": len(vals), "n_scores": len(rows),
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "E1 单缺陷干预筛查；版本差异不作因果分解；familes<24 标 exploratory；不碰封存 test。",
    })
    config = v2_context(args, sha=sha, registration=registration,
                        n_train=len(trains), n_val=len(vals),
                        forward_auth=forward_auth, replay_only=replay_only)
    out = write_artifacts(args, root, config, rows, metrics)
    print(json.dumps({
        "run_id": args.run_id, "variant": args.variant, "panel": args.panel,
        "status": "COMPLETE", "run_dir": str(out), "exploratory": metrics["exploratory"],
        "n_scores": len(rows),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
