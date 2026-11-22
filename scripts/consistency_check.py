"""审计产物完整性：git hash、协议版本、zero-reprefill 标志、逐样本分数。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from readkv.config import ROOT


def check_run(run_dir: Path) -> dict:
    problems = []
    for name in ("config.json", "manifest.json"):
        if not (run_dir / name).exists():
            problems.append(f"missing {name}")
    # 阶段汇总 run 只有 summary/mechanism/paper_artifacts 等；逐样本 run 必须有 scores.jsonl。
    summary_names = ("summary.json", "mechanism.json", "paper_artifacts.json",
                     "generalization.json", "metrics.json")
    is_summary = any((run_dir / n).exists() for n in summary_names)
    if not is_summary and not (run_dir / "scores.jsonl").exists():
        problems.append("missing scores.jsonl")
    config = {}
    if (run_dir / "config.json").exists():
        config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
        for key in ("protocol_version", "git_hash", "seed", "dtype", "kernel", "zero_re_prefill"):
            if key not in config:
                problems.append(f"config missing {key}")
        if config.get("zero_re_prefill") is not True:
            problems.append("zero_re_prefill flag is not true")
    return {"run_id": run_dir.name, "ok": not problems, "problems": problems}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", default=str(ROOT / "reports"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    root = Path(args.reports_root)
    run_dirs = [p for p in sorted(root.iterdir()) if p.is_dir()]
    # V2 布局：reports/runs/<run_id>/；不要再把手积目录 runs/ 本身当 run
    v2_root = root / "runs"
    if v2_root.is_dir():
        run_dirs = [p for p in run_dirs if p != v2_root]
        run_dirs += [p for p in sorted(v2_root.iterdir()) if p.is_dir()]
    results = [check_run(p) for p in run_dirs]
    out = Path(args.output) if args.output else root / "consistency_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checked": len(results), "failed": sum(not r["ok"] for r in results), "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
