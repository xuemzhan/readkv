"""从 reports/{runs,}/**/scores.jsonl 重算 CI；不加载模型。

V1：CHG（gold_prob − gold_prob_self）。
V2：自动检测 E_CF 字段，重算簇级 paired E_CF 均值与 CI，以及新方法与基线的
成对 E_CF 差异（主终点）。mock 数字不是科学证据。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from readkv.config import ROOT
from readkv.stats.bootstrap import cluster_bootstrap, paired_bootstrap
from readkv.stats.reporting import direction_from_ci, format_ci, replacement_from_ci


def summarize_run(path: Path, *, n_resamples: int, epsilon: float) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return {"run_id": path.parent.name, "arms": {}}

    # V2 检测：任一行含 E_CF 即按反事实协议重算
    if any("E_CF" in r for r in rows):
        arms: dict[str, tuple[list[float], list[str]]] = defaultdict(lambda: ([], []))
        for row in rows:
            arm = str(row.get("arm", "unknown"))
            if "E_CF" not in row:
                continue
            arms[arm][0].append(float(row["E_CF"]))
            arms[arm][1].append(str(row.get("cluster", row.get("pair_id", "default"))))
        out: dict[str, dict] = {}
        for arm, (ecfs, clusters) in arms.items():
            point, low, high = cluster_bootstrap(ecfs, clusters, n_resamples=n_resamples, seed=0)
            out[arm] = {
                "n": len(ecfs),
                "E_CF": format_ci(point, low, high),
                "protocol": "v2.0",
            }
        # 主终点：new_joint vs joint 的成对差异
        endpoint = None
        if "new_joint" in out and "joint" in out:
            new_map = {r["pair_id"]: float(r["E_CF"]) for r in rows if r.get("arm") == "new_joint"}
            base_map = {r["pair_id"]: float(r["E_CF"]) for r in rows if r.get("arm") == "joint"}
            common = sorted(set(new_map) & set(base_map))
            if common:
                deltas = [new_map[p] - base_map[p] for p in common]
                clusters = [str(next(r.get("cluster", p) for r in rows if r.get("pair_id") == p and r.get("arm") == "new_joint"))
                            for p in common]
                point, low, high = cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=0)
                endpoint = {"point": point, "ci": [low, high], "improved": high < 0,
                            "note": "paired E_CF difference (new - baseline)"}
        return {"run_id": path.parent.name, "arms": out, "primary_endpoint": endpoint,
                "protocol": "v2.0"}

    # V1 兼容
    arms: dict[str, tuple[list[float], list[str]]] = defaultdict(lambda: ([], []))
    for row in rows:
        arm = str(row.get("arm", "unknown"))
        handoff, self_ = row.get("gold_prob"), row.get("gold_prob_self")
        if handoff is None or self_ is None:
            continue
        arms[arm][0].append(float(handoff) - float(self_))
        arms[arm][1].append(str(row.get("doc_id", row.get("item_id", "default"))))
    out: dict[str, dict] = {}
    for arm, (deltas, clusters) in arms.items():
        point, low, high = paired_bootstrap(deltas, n_resamples=n_resamples, seed=0)
        cpoint, clow, chigh = cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=0)
        out[arm] = {
            "n": len(deltas),
            "paired": format_ci(point, low, high),
            "cluster": format_ci(cpoint, clow, chigh),
            "replacement": replacement_from_ci(low, epsilon),
            "direction": direction_from_ci(low, high),
        }
    return {"run_id": path.parent.name, "arms": out, "protocol": "v1.0"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", default=str(ROOT / "reports"))
    parser.add_argument("--n-resamples", type=int, default=10_000)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = Path(args.reports_root)
    score_files = sorted(root.glob("*/scores.jsonl")) + sorted(root.glob("runs/*/scores.jsonl"))
    summary = {
        str(p.parent.relative_to(root)): summarize_run(p, n_resamples=args.n_resamples, epsilon=args.epsilon)
        for p in score_files
    }
    out = Path(args.output) if args.output else root / "bootstrap_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(summary), "output": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
