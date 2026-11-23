"""从 reports/{runs,}/**/scores.jsonl 重算 CI；不加载模型。

V1：CHG（gold_prob − gold_prob_self）。
V2：自动检测 E_CF 字段，重算反事实协议的主终点与 E_CF 区间。

V2.3（依据 configs/prereg/stats_convention_v2.3.yaml，只读引用）：
  * 主聚类单元改为 ``template_family``（不再用逐对唯一的 pair_id/cluster）；
  * 同时输出 pair-level 敏感性 CI（不得只报较窄的一套）；
  * 模板族数 < 24 时标记 exploratory，禁止强显著性主张；
  * flip 分母口径 [F5, F6] 从数据 manifest 读取并写入汇总（本脚本不回写任何冻结文件）。
mock 数字不是科学证据。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from readkv.config import ROOT
from readkv.stats.bootstrap import cluster_bootstrap, paired_bootstrap
from readkv.stats.reporting import direction_from_ci, format_ci, replacement_from_ci

MIN_CLUSTERS_FOR_INFERENCE = 24
STATS_CONVENTION_VERSION = "2.3"


def _fill_template_family(rows: list[dict]) -> list[dict]:
    """同一 scores.jsonl 内用其它 arm 的 pair_id→template_family 映射补齐缺失字段。"""
    fam_by_pair: dict[str, str] = {}
    for r in rows:
        if r.get("template_family") and r.get("pair_id") is not None:
            fam_by_pair[str(r["pair_id"])] = str(r["template_family"])
    out: list[dict] = []
    for r in rows:
        if not r.get("template_family") and str(r.get("pair_id")) in fam_by_pair:
            rr = dict(r)
            rr["template_family"] = fam_by_pair[str(r["pair_id"])]
            out.append(rr)
        else:
            out.append(r)
    return out


def _cluster_labels(rows: list[dict], pair_ids: list[str]) -> tuple[list[str], str]:
    """按 v2.3 选主聚类单元：template_family 优先，缺失时显式标记 fallback。"""
    if rows and all("template_family" in r for r in rows):
        return [str(r["template_family"]) for r in rows], "template_family"
    # 旧产物兼容：无 template_family 时退化为原 cluster，但诚实标记
    return [str(r.get("cluster", pid)) for r, pid in zip(rows, pair_ids)], "cluster-fallback"


def _dual_ci(values: list[float], rows: list[dict], pair_ids: list[str],
             *, n_resamples: int, seed: int) -> dict:
    """返回 template_family 主 CI + pair-level 敏感性 CI。"""
    fam_labels, unit = _cluster_labels(rows, pair_ids)
    point, low, high = cluster_bootstrap(values, fam_labels,
                                         n_resamples=n_resamples, seed=seed)
    p_point, p_low, p_high = cluster_bootstrap(values, [str(x) for x in pair_ids],
                                               n_resamples=n_resamples, seed=seed)
    n_clusters = len(set(fam_labels))
    return {
        "point": point,
        "ci": [low, high],
        "cluster_unit": unit,
        "n_clusters": n_clusters,
        "exploratory": bool(n_clusters < MIN_CLUSTERS_FOR_INFERENCE),
        "pair_level_sensitivity": {
            "point": p_point,
            "ci": [p_low, p_high],
            "cluster_unit": "pair_id",
            "n_clusters": len(set(pair_ids)),
        },
    }


def summarize_run(path: Path, *, n_resamples: int, epsilon: float, seed: int = 0) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return {"run_id": path.parent.name, "arms": {}}

    # V2 检测：任一行含 E_CF 即按反事实协议重算
    if any("E_CF" in r for r in rows):
        rows = _fill_template_family(rows)
        arms: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if "E_CF" in row:
                arms[str(row.get("arm", "unknown"))].append(row)
        out: dict[str, dict] = {}
        for arm, arm_rows in arms.items():
            vals = [float(r["E_CF"]) for r in arm_rows]
            ids = [str(r.get("pair_id", f"row{i}")) for i, r in enumerate(arm_rows)]
            dual = _dual_ci(vals, arm_rows, ids, n_resamples=n_resamples, seed=seed)
            out[arm] = {
                "n": len(vals),
                "E_CF": format_ci(dual["point"], dual["ci"][0], dual["ci"][1]),
                "E_CF_pair_level_sensitivity": format_ci(
                    dual["pair_level_sensitivity"]["point"],
                    dual["pair_level_sensitivity"]["ci"][0],
                    dual["pair_level_sensitivity"]["ci"][1]),
                "cluster_unit": dual["cluster_unit"],
                "n_clusters": dual["n_clusters"],
                "exploratory": dual["exploratory"],
                "protocol": "v2.0",
                "stats_convention": f"v{STATS_CONVENTION_VERSION}",
            }

        # 主终点：new_joint vs joint 的成对差异
        endpoint = None
        if "new_joint" in out and "joint" in out:
            new_rows = arms["new_joint"]
            base_map = {str(r["pair_id"]): float(r["E_CF"]) for r in arms["joint"]
                        if r.get("pair_id") is not None}
            paired = [(r, float(r["E_CF"]) - base_map[str(r["pair_id"])])
                      for r in new_rows
                      if r.get("pair_id") is not None and str(r["pair_id"]) in base_map]
            if paired:
                paired_rows, deltas = zip(*paired)
                ids = [str(r["pair_id"]) for r in paired_rows]
                dual = _dual_ci(list(deltas), list(paired_rows), ids,
                                n_resamples=n_resamples, seed=seed)
                endpoint = {
                    "point": dual["point"],
                    "ci": dual["ci"],
                    "improved": dual["ci"][1] < 0,
                    "cluster_unit": dual["cluster_unit"],
                    "n_clusters": dual["n_clusters"],
                    "exploratory": dual["exploratory"],
                    "pair_level_sensitivity": {
                        "point": dual["pair_level_sensitivity"]["point"],
                        "ci": dual["pair_level_sensitivity"]["ci"],
                    },
                    "note": "paired E_CF difference (new - baseline); primary cluster = template_family",
                }

        # F1：oracle_U 的 repair-vs-random 成对 CI
        repair = None
        u_rows = [r for r in rows if r.get("arm") == "oracle_U"
                  and "delta_ecf" in r and "delta_rand" in r]
        if u_rows:
            diffs = [float(r["hit_u"]) - float(r["hit_rand"]) if ("hit_u" in r and "hit_rand" in r)
                     else float(float(r["delta_ecf"]) > 0) - float(float(r["delta_rand"]) > 0)
                     for r in u_rows]
            ids = [str(r.get("pair_id", f"row{i}")) for i, r in enumerate(u_rows)]
            dual = _dual_ci(diffs, u_rows, ids, n_resamples=n_resamples, seed=seed)
            repair = {
                "point": dual["point"], "ci": dual["ci"], "n_pairs": len(u_rows),
                "ci_lower_gt_0": bool(dual["ci"][0] > 0),
                "cluster_unit": dual["cluster_unit"],
                "n_clusters": dual["n_clusters"],
                "exploratory": dual["exploratory"],
                "pair_level_sensitivity": {
                    "point": dual["pair_level_sensitivity"]["point"],
                    "ci": dual["pair_level_sensitivity"]["ci"],
                },
                "source": "per-pair scores.jsonl oracle_U arm (delta_ecf / delta_rand)",
                "note": "repair hit(U) - hit(random); primary cluster = template_family",
            }
        return {
            "run_id": path.parent.name,
            "arms": out,
            "primary_endpoint": endpoint,
            "repair_vs_random": repair,
            "protocol": "v2.0",
            "stats_convention": f"v{STATS_CONVENTION_VERSION}",
            "cluster_bootstrap_convention": {
                "primary_cluster_unit": "template_family",
                "pair_level_sensitivity_reported": True,
                "min_clusters_for_inference": MIN_CLUSTERS_FOR_INFERENCE,
            },
        }

    # V1 兼容（旧产物，无 E_CF / template_family）
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
        point, low, high = paired_bootstrap(deltas, n_resamples=n_resamples, seed=seed)
        cpoint, clow, chigh = cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=seed)
        out[arm] = {
            "n": len(deltas),
            "paired": format_ci(point, low, high),
            "cluster": format_ci(cpoint, clow, chigh),
            "replacement": replacement_from_ci(low, epsilon),
            "direction": direction_from_ci(low, high),
        }
    return {"run_id": path.parent.name, "arms": out, "protocol": "v1.0",
            "stats_convention": "n/a (v1 scores)"}


def _flip_denominator_info() -> dict:
    """从重建后的数据 manifest 读取 flip 分母口径（只读，不回写版本文件）。"""
    manifest = ROOT / "data" / "tasks" / "manifest.json"
    if not manifest.exists():
        return {"available": False}
    q = json.loads(manifest.read_text(encoding="utf-8")).get("quality", {})
    return {
        "available": True,
        "excludes": q.get("flip_denominator_excludes"),
        "recomputed_value": q.get("flip_denominator"),
        "source": "data/tasks/manifest.json::quality (stats_convention_v2.3.yaml 口径)",
        "note": "PI 负责把 recomputed_value 回填到 configs/prereg/stats_convention_v2.3.yaml",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", default=str(ROOT / "reports"))
    parser.add_argument("--n-resamples", type=int, default=10_000)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = Path(args.reports_root)
    score_files = sorted(root.glob("*/scores.jsonl")) + sorted(root.glob("runs/*/scores.jsonl"))

    def _seed_for(score_path: Path) -> int:
        cfg_path = score_path.parent / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            return int(cfg.get("experiment_config", {}).get("bootstrap_seed", cfg.get("seed", 0)))
        return 0

    summary = {}
    for p in score_files:
        seed = _seed_for(p)
        r = summarize_run(p, n_resamples=args.n_resamples, epsilon=args.epsilon, seed=seed)
        r["bootstrap_seed"] = seed
        r["bootstrap_seed_source"] = "run config (experiment_config.bootstrap_seed / seed)"
        summary[str(p.parent.relative_to(root))] = r
    out = Path(args.output) if args.output else root / "bootstrap_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "stats_convention": f"v{STATS_CONVENTION_VERSION}",
        "cluster_bootstrap_convention": {
            "primary_cluster_unit": "template_family",
            "pair_level_sensitivity": "reported alongside primary for every endpoint",
            "min_clusters_for_inference": MIN_CLUSTERS_FOR_INFERENCE,
        },
        "flip_denominator": _flip_denominator_info(),
        "runs": summary,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(summary), "output": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
