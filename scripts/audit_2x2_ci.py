"""2×2 统计口径补算（纯 CPU，从冻结 scores + val JSONL 重算，不重跑 GPU）。

按 configs/prereg/gpu_followup_v2.7.yaml：
  - 主指标 L = Self 双侧正确率 − Joint 双侧正确率（百分点），逐对配对；
  - 主 CI = template_family 簇级 bootstrap 10000；pair-level 逐对敏感性 CI；
  - 关联键 = version_tag + sample_hash（跨版本 pair_id 碰撞，绝不只用 pair_id）；
  - val 模板族 8 < 24 → exploratory=true；
  - 两项预固定对比（同 val 内按样本配对、按模板族重采样）：
      ① A10−A00（legacy val）、A11−A01（fixed val）
      ② A01−A00（legacy cal）、A11−A10（fixed cal）
  - E_CF 区间也按 template_family 主口径补正；拿不到族则标 fallback+exploratory。

输出 reports/audit_2x2_l_ci.json（补充文件，不改原 12 格产物 / bootstrap.json）。
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from readkv.stats.bootstrap import cluster_bootstrap, paired_bootstrap

ROOT = Path("/root/readkv")
RUNS = ROOT / "reports" / "runs"
DATA = ROOT / "data" / "audit_2x2"
CELLS = ["A00", "A11", "A01", "A10"]
SEEDS = [0, 1, 2]
CELL_CAL = {"A00": "legacy", "A01": "legacy", "A10": "fixed", "A11": "fixed"}
CELL_VAL = {"A00": "legacy", "A01": "fixed", "A10": "legacy", "A11": "fixed"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def sample_family_map(version: str, seed: int) -> dict[str, str]:
    """key = version_tag|sample_hash[:16] -> template_family（与 scores.sample_id 同格式）。"""
    rows = load_jsonl(DATA / version / f"val_seed{seed}.jsonl")
    out = {}
    for r in rows:
        fam = r.get("template_family") or r.get("cluster") or "UNKNOWN"
        out[str(r.get("sample_id", ""))] = str(fam)
    return out


def fmt(ci: tuple[float, float, float]) -> dict:
    return {"point": round(ci[0], 6), "ci": [round(ci[1], 6), round(ci[2], 6)]}


def cell_data(cell: str, seed: int):
    rid = f"audit_2x2_{cell}_s{seed}"
    rows = load_jsonl(RUNS / rid / "scores.jsonl")
    fam = sample_family_map(CELL_VAL[cell], seed)
    by_pair: dict[str, dict[str, float]] = defaultdict(dict)
    meta: dict[str, Any] = {}
    for r in rows:
        if r["arm"] not in ("self", "joint"):
            continue
        sid = str(r.get("sample_id", ""))
        by_pair[sid][r["arm"]] = float(r["dual_correct"])
        meta[sid] = {
            "family": fam.get(sid, "UNKNOWN"),
            "E_CF_joint": float(r["E_CF"]) if r["arm"] == "joint" else meta.get(sid, {}).get("E_CF_joint"),
            "sample_hash": r.get("sample_hash", ""),
        }
    # joint E_CF 单独取
    for r in rows:
        if r["arm"] == "joint":
            sid = str(r.get("sample_id", ""))
            if sid in meta:
                meta[sid]["E_CF_joint"] = float(r["E_CF"])
    ids = sorted(sid for sid, d in by_pair.items() if "self" in d and "joint" in d)
    return ids, by_pair, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-resamples", type=int, default=10000)
    ap.add_argument("--out", default=str(ROOT / "reports" / "audit_2x2_l_ci.json"))
    args = ap.parse_args()

    result: dict[str, Any] = {
        "file": "reports/audit_2x2_l_ci.json",
        "protocol": "gpu_followup_v2.7",
        "method": "pure CPU recompute from frozen scores + val JSONL; no GPU, no run产物改动",
        "cluster_unit": "template_family (primary) + pair-level sensitivity",
        "n_resamples": args.n_resamples,
        "cells": {},
        "predeclared_contrasts": {},
    }
    cache: dict[tuple[str, int], tuple[list[str], dict, dict]] = {}
    for c in CELLS:
        for s in SEEDS:
            cache[(c, s)] = cell_data(c, s)

    for c in CELLS:
        for s in SEEDS:
            ids, by_pair, meta = cache[(c, s)]
            L = [(by_pair[i]["self"] - by_pair[i]["joint"]) * 100.0 for i in ids]  # 百分点
            fams = [meta[i]["family"] for i in ids]
            n_clusters = len(set(fams))
            unknown = sum(1 for f in fams if f == "UNKNOWN")
            exploratory = bool(n_clusters < 24)
            main_ci = cluster_bootstrap(L, fams, n_resamples=args.n_resamples, seed=s)
            pair_ci = cluster_bootstrap(L, ids, n_resamples=args.n_resamples, seed=s)
            # E_CF 主口径补正
            ecf = [meta[i]["E_CF_joint"] for i in ids if "E_CF_joint" in meta[i]]
            ecf_ci = cluster_bootstrap(ecf, [meta[i]["family"] for i in ids if "E_CF_joint" in meta[i]],
                                       n_resamples=args.n_resamples, seed=s) if ecf else (0, 0, 0)
            result["cells"][f"{c}_s{s}"] = {
                "run_id": f"audit_2x2_{c}_s{s}", "cell": c, "seed": s, "n_pairs": len(ids),
                "L_point_pp": round(float(sum(L) / len(L)), 6) if L else None,
                "L_template_family_ci": fmt(main_ci),
                "L_pair_level_sensitivity": fmt(pair_ci),
                "n_clusters": n_clusters, "unknown_family_pairs": unknown,
                "exploratory": exploratory,
                "joint_E_CF_template_family_ci": fmt(ecf_ci),
                "family_source": f"data/audit_2x2/{CELL_VAL[c]}/val_seed{s}.jsonl (version_tag+sample_hash join)",
            }

    def contrast(c_hi: str, c_lo: str, label: str, val_or_cal: str, s: int) -> dict:
        ids_hi, hi, _ = cache[(c_hi, s)]
        ids_lo, lo, meta_lo = cache[(c_lo, s)]
        common = sorted(set(ids_hi) & set(ids_lo))
        deltas = [(hi[i]["self"] - hi[i]["joint"]) * 100.0 - (lo[i]["self"] - lo[i]["joint"]) * 100.0 for i in common]
        fams = [meta_lo[i]["family"] for i in common]
        if not deltas:
            return {"point": None, "ci": None, "n_pairs": 0}
        ci = cluster_bootstrap(deltas, fams, n_resamples=args.n_resamples, seed=s)
        return {"point": round(ci[0], 6), "ci": [round(ci[1], 6), round(ci[2], 6)],
                "n_pairs": len(common), "n_clusters": len(set(fams)),
                "exploratory": bool(len(set(fams)) < 24), "label": label, "scope": val_or_cal}

    for s in SEEDS:
        result["predeclared_contrasts"][f"s{s}"] = {
            "calibration_legacy_val_A10_minus_A00": contrast("A10", "A00", "固定旧 val 换校准", "legacy val", s),
            "calibration_fixed_val_A11_minus_A01": contrast("A11", "A01", "固定修复 val 换校准", "fixed val", s),
            "eval_legacy_cal_A01_minus_A00": contrast("A01", "A00", "固定旧校准换 val", "legacy cal", s),
            "eval_fixed_cal_A11_minus_A10": contrast("A11", "A10", "固定修复校准换 val", "fixed cal", s),
        }

    result["note"] = ("L 主口径=template_family 簇级 bootstrap；pair-level 仅敏感性；8 族<24 全标 exploratory=true。"
                      "跨版本 pair_id 碰撞已规避（关联键 version_tag+sample_hash）。不改任何 run 产物 / bootstrap.json 原文件。")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "cells": len(result["cells"]),
                      "all_exploratory": all(v["exploratory"] for v in result["cells"].values())},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
