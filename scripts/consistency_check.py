"""审计产物完整性：键、zero-reprefill、git 可追溯、model_pair 一致性、协议兼容。

在冻结判据之外做**只读审计增强**（PI p1_go_no_go.md §5 / R2）：
  (a) config.git_hash vs git HEAD；跑分路径工作区脏状态；commit tree 是否真含跑分代码；
  (b) model_pair vs teacher/student 路径与 layer_map 层数一致；
  (c) protocol_version 与 configs/prereg/ 版本兼容。
不改冻结判据、不改 reports/runs/** 任何产物。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from readkv.config import ROOT

# 产出这些 run 所必需的跑分/实现代码路径（R1 traceability 检查集合）
# M1：纳入 SQuAD 锚点评测的真正产出代码 experiments/anchor_squad_gpu.py。
RUN_CODE_PATHS = (
    "experiments/P0_gpu.py",
    "experiments/P1_gpu.py",
    "experiments/P1_kd_gpu.py",
    "experiments/anchor_squad_gpu.py",
    "src/readkv/models/gpu_backend.py",
    "src/readkv/models/hooks.py",
    "src/readkv/evaluate/cf_pipeline.py",
    "scripts/gen_teacher_cache.py",
    "scripts/consistency_check.py",
    "src/readkv/train/kd_gpu.py",
    "src/readkv/models/cf_rct.py",
    "src/readkv/train/cf_rct.py",
    "src/readkv/models/layer_map.py",
    "src/readkv/models/loader.py",
)

# model_pair -> (teacher 路径标记, student 路径标记, 教师层数, 学生层数)
PAIR_EXPECT: dict[str, tuple[str, str, int, int]] = {
    "qwen3-1.7b-to-0.6b": ("Qwen3-1.7B", "Qwen3-0.6B", 28, 28),
    "qwen3-4b-to-1.7b": ("Qwen3-4B", "Qwen3-1.7B", 36, 28),
    "qwen3-8b-to-0.6b": ("Qwen3-8B", "Qwen3-0.6B", 36, 28),
}

# M1：锚点脚本于 938f3a0 才引入；早于该 commit 的历史 run 不可能包含它。
# 锚点 run 用全量 RUN_CODE_PATHS（含锚点脚本）校验；其余 run 用历史集合，
# 避免"HEAD 前进/文件后引入"误伤既有 run（按既有 ancestry 语义处理，不改 run）。
ANCHOR_CODE_PATHS = ("experiments/anchor_squad_gpu.py",)
LEGACY_RUN_CODE_PATHS = tuple(p for p in RUN_CODE_PATHS if p not in ANCHOR_CODE_PATHS)


def _is_anchor_run(cfg: dict) -> bool:
    """按 config 元数据识别 external_anchor run（不依赖 run_id 命名）。"""
    ec = cfg.get("experiment_config", {}) or {}
    meta = cfg.get("metadata", {}) or {}
    return (
        str(ec.get("stage", "")) == "external_anchor"
        or str(meta.get("stage", "")) == "external_anchor"
        or bool(ec.get("anchor_benchmark"))
        or bool(ec.get("anchor_file"))
    )


def _producing_paths(code_paths: tuple[str, ...]) -> tuple[str, ...]:
    """审计脚本自身不属于产出 run 的代码，从一致性比对中排除。"""
    return tuple(p for p in code_paths if p != "scripts/consistency_check.py")


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # pragma: no cover - 无 git 环境
        return ""


def _head_hash() -> str:
    return _git("rev-parse", "--short", "HEAD")


def _code_tracked(commit_hash: str, code_paths: tuple[str, ...] = RUN_CODE_PATHS) -> dict[str, Any]:
    """该 commit tree 是否包含要求的跑分代码路径（M1：按 run 类型选择集合）。"""
    if not commit_hash:
        return {"code_tracked": False, "missing_code_paths": list(code_paths)}
    missing = []
    for rel in code_paths:
        r = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_hash}:{rel}"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if r.returncode != 0:
            missing.append(rel)
    return {"code_tracked": not missing, "missing_code_paths": missing}


def _dirty_run_paths() -> list[str]:
    # 审计脚本自身非"产出 run 的代码"，其演进不应使所有 run 变脏（与
    # _run_code_unchanged 的既有排除语义一致）；锚点脚本仍是产出代码，保留检查。
    out = _git("status", "--porcelain", "--", *_producing_paths(RUN_CODE_PATHS))
    return [line.strip() for line in out.splitlines() if line.strip()]


def _hash_in_history(commit_hash: str) -> bool:
    if not commit_hash:
        return False
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_hash, "HEAD"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def _run_code_unchanged(commit_hash: str, code_paths: tuple[str, ...] = RUN_CODE_PATHS) -> bool:
    """config.git_hash 与 HEAD 之间的跑分代码是否完全一致（HEAD 可含无关后续 commit）。"""
    if not commit_hash or not _hash_in_history(commit_hash):
        return False
    r = subprocess.run(
        ["git", "diff", "--quiet", commit_hash, "HEAD", "--", *_producing_paths(code_paths)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def _check_model_pair(cfg: dict) -> dict[str, Any]:
    ec = cfg.get("experiment_config", {}) or {}
    pair = str(ec.get("model_pair", ""))
    teacher = str(ec.get("teacher", ""))
    student = str(ec.get("student", ""))
    model = str(ec.get("model", ""))  # E0：仅单一模型
    lm = ec.get("layer_map", {}) or {}
    exp = PAIR_EXPECT.get(pair)
    if exp is None:
        # M2：未知/空 model_pair 不再静默放行。锚点 run 按 teacher/student 路径
        # 推断配对并给显式豁免理由；其余 run 记为明确 problem。
        inferred = ""
        if teacher or student:
            for cand, (tmark, smark, _, _) in PAIR_EXPECT.items():
                t_ok = not teacher or tmark.lower() in teacher.lower()
                s_ok = not student or smark.lower() in student.lower()
                if t_ok and s_ok:
                    inferred = cand
                    break
        if _is_anchor_run(cfg) and inferred:
            return {
                "ok": True, "model_pair": pair, "inferred_model_pair": inferred,
                "exempt": True,
                "exempt_reason": (
                    "anchor config declares teacher/student paths directly (no model_pair field); "
                    f"pair inferred from paths as {inferred!r} and path markers verified"
                ),
                "problems": [],
            }
        # C3 (protocol-v2.7, option B): 2×2 审计入口用 calibration_version/validation_version
        # 代替 model_pair 字段。按入口硬编码默认推断 MVP 等深对 (Qwen3-1.7B→0.6B)，
        # 以 layer_map 28→28 等深断言确认；泛化到任何带这两字段的 2×2 类 run，不硬编码 run_id。
        # 不改变任何既有 model_pair / 锚点 / 历史 run 的判定（仅在本 exp is None 分支生效）。
        if ec.get("calibration_version") and ec.get("validation_version"):
            mvp = "qwen3-1.7b-to-0.6b"
            t_marker, s_marker, nt, ns = PAIR_EXPECT[mvp]
            ns_lm = int((lm.get("n_student_layers", -1)) if lm else -1)
            nt_lm = int((lm.get("n_teacher_layers", -1)) if lm else -1)
            equal_depth = (ns_lm == ns and nt_lm == nt)
            inference_note = (
                "2×2 audit run: model determined by hardcoded 1.7B→0.6B entrypoint default "
                "+ equal-depth assertion (v2.7 §1); model_pair field replaced by "
                "calibration_version/validation_version + input_sha256 (no run_id hardcoded)"
            )
            problems_2x2 = [] if equal_depth else [
                f"2×2 equal-depth assertion failed: layer_map {nt_lm}/{ns_lm} != {nt}/{ns}"
            ]
            return {
                "ok": not problems_2x2,
                "model_pair": pair,
                "inferred_model_pair": mvp,
                "exempt": True,
                "infer_2x2": True,
                "inference_note": inference_note,
                "equal_depth_asserted": equal_depth,
                "problems": problems_2x2,
            }
        problem = f"unknown model_pair {pair!r}: no PAIR_EXPECT entry"
        if not inferred:
            problem += " and teacher/student paths do not identify a known pair"
        return {"ok": False, "model_pair": pair, "exempt": False, "problems": [problem]}
    t_marker, s_marker, nt, ns = exp
    problems = []
    if teacher and t_marker.lower() not in teacher.lower():
        problems.append(f"teacher path {teacher!r} does not match {pair} ({t_marker})")
    if student and s_marker.lower() not in student.lower():
        problems.append(f"student path {student!r} does not match {pair} ({s_marker})")
    if model and s_marker.lower() not in model.lower() and t_marker.lower() not in model.lower():
        problems.append(f"single-model path {model!r} does not match {pair}")
    if lm:
        if int(lm.get("n_student_layers", -1)) != ns or int(lm.get("n_teacher_layers", -1)) != nt:
            problems.append(
                f"layer_map {lm.get('n_student_layers')}/{lm.get('n_teacher_layers')} "
                f"!= expected student/teacher {ns}/{nt}"
            )
    return {
        "ok": not problems,
        "model_pair": pair,
        "exempt": False,
        "expected": {"teacher": t_marker, "student": s_marker,
                     "n_teacher_layers": nt, "n_student_layers": ns},
        "problems": problems,
        "errata_hint": (
            f"model_pair_corrected='qwen3-4b-to-1.7b' (teacher path + 36→28 layer_map)"
            if problems and "4B" in teacher else None
        ),
    }


def _check_protocol_compat(cfg: dict) -> dict[str, Any]:
    pv = str(cfg.get("protocol_version", ""))
    problems = []
    if pv not in ("2.0", "2.1"):
        problems.append(f"protocol_version {pv!r} incompatible with frozen V2 prereg")
    prereg_dir = ROOT / "configs" / "prereg"
    ec = cfg.get("experiment_config", {})
    declared = str(ec.get("prereg", ""))
    if declared:
        candidate = prereg_dir / declared.split()[0].split("/")[-1]
        if not candidate.exists():
            problems.append(f"declared prereg file not found: {declared}")
    if not (prereg_dir / "phase1_benchmark_decision.yaml").exists():
        problems.append("missing frozen phase1_benchmark_decision.yaml")
    return {"ok": not problems, "protocol_version": pv, "problems": problems}


def check_run(run_dir: Path, head: str, dirty: list[str], superseded: bool = False) -> dict:
    problems: list[str] = []
    for name in ("config.json", "manifest.json"):
        if not (run_dir / name).exists():
            problems.append(f"missing {name}")
    summary_names = ("summary.json", "mechanism.json", "paper_artifacts.json",
                     "generalization.json", "metrics.json")
    is_summary = any((run_dir / n).exists() for n in summary_names)
    if not is_summary and not (run_dir / "scores.jsonl").exists():
        problems.append("missing scores.jsonl")
    config: dict[str, Any] = {}
    if (run_dir / "config.json").exists():
        config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
        for key in ("protocol_version", "git_hash", "seed", "dtype", "kernel", "zero_re_prefill"):
            if key not in config:
                problems.append(f"config missing {key}")
        if config.get("zero_re_prefill") is not True:
            problems.append("zero_re_prefill flag is not true")

    # M1：锚点 run 用含 anchor_squad_gpu.py 的全量集合校验其真正产出代码；
    # 历史 run 用其 commit 时代已存在的集合，避免后引入文件误伤既有结论。
    is_anchor = _is_anchor_run(config)
    code_paths = RUN_CODE_PATHS if is_anchor else LEGACY_RUN_CODE_PATHS
    if is_anchor:
        # 可选硬门：data_sha256 必填；逐样本 zero_ok（记于 metrics.json）必须为真。
        ec = config.get("experiment_config", {}) or {}
        if not ec.get("data_sha256"):
            problems.append("anchor config missing experiment_config.data_sha256")
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if metrics.get("zero_re_prefill") is not True:
                problems.append("anchor metrics.json zero_re_prefill is not true (zero_ok hard gate)")

    git_hash = str(config.get("git_hash", ""))
    tracked = _code_tracked(git_hash, code_paths)
    in_history = _hash_in_history(git_hash)
    code_same = _run_code_unchanged(git_hash, code_paths)
    traceable = bool(in_history and code_same and tracked["code_tracked"])
    if not in_history:
        problems.append(f"git_hash={git_hash!r} not in HEAD history (HEAD={head!r})")
    if in_history and not code_same:
        problems.append("run-producing code differs between config.git_hash and HEAD")
    if not tracked["code_tracked"]:
        problems.append("commit tree lacks run code: " + ",".join(tracked["missing_code_paths"][:4]))
    if dirty:
        problems.append("run code paths have uncommitted changes: " + ",".join(dirty[:4]))

    pair_check = _check_model_pair(config)
    # M2：显式取键。任何分支都必须给出 problems；未知项不得静默放行。
    problems.extend(pair_check["problems"])
    proto_check = _check_protocol_compat(config)
    problems.extend(proto_check["problems"])

    return {
        "run_id": run_dir.name,
        "ok": not problems,
        "problems": problems,
        "superseded": superseded,
        "git_hash": git_hash,
        "head_hash": head,
        "git_hash_in_history": in_history,
        "run_code_unchanged_vs_head": code_same,
        "traceable": traceable,
        "anchor_run": is_anchor,
        "code_paths_checked": list(code_paths),
        "anchor_code_checked": bool(is_anchor and "experiments/anchor_squad_gpu.py" in code_paths),
        **tracked,
        "dirty_run_paths": list(dirty),
        "model_pair_check": pair_check,
        "protocol_compat": proto_check,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", default=str(ROOT / "reports"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    root = Path(args.reports_root)
    # 只把含 run 产物的目录当 run；排除 review/ 等非 run 目录（PI signoff §5.2）
    run_dirs = [p for p in sorted(root.iterdir())
                if p.is_dir() and p.name != "review" and ((p / "config.json").exists() or (p / "scores.jsonl").exists())]
    v2_root = root / "runs"
    if v2_root.is_dir():
        run_dirs = [p for p in run_dirs if p != v2_root]
        run_dirs += [p for p in sorted(v2_root.iterdir())
                     if p.is_dir() and ((p / "config.json").exists() or (p / "scores.jsonl").exists())]

    head = _head_hash()
    dirty = _dirty_run_paths()

    # 从 runs_index.json 读取 superseded 标记（若有）
    superseded: set[str] = set()
    idx_path = root / "runs_index.json"
    if idx_path.exists():
        try:
            for row in json.loads(idx_path.read_text(encoding="utf-8")):
                if row.get("superseded"):
                    superseded.add(str(row.get("run_id")))
        except Exception:  # pragma: no cover
            pass

    results = [check_run(p, head, dirty, p.name in superseded) for p in run_dirs]
    out = Path(args.output) if args.output else root / "consistency_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked": len(results),
        "failed": sum(not r["ok"] for r in results),
        "head_hash": head,
        "dirty_run_paths": dirty,
        "output": str(out),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
