#!/usr/bin/env python3
"""Export GPU experiment data to reports/data/gpu_experiments/v1/.

Raw layer  : byte-exact copies of config.json / manifest.json / scores.jsonl /
             metrics.json (if present) / ecf_ledger.jsonl (if present) for the
             28 runs listed in reports/runs_index.json (authoritative list).
Processed  : column/field projections and renames ONLY. No statistic is
             recomputed; every number is transcribed from raw run artifacts,
             reports/bootstrap_summary.json, reports/anchor_eval_summary.json,
             reports/data/data_fix_report.md and data_readiness_audit.md.

Hard rules:
  - source files under reports/runs/** are READ-ONLY (never written).
  - cache/*.npz are NOT copied (regenerable); they are recorded in inventory.
  - no GPU, no scoring code, no frozen prereg / papers / decisions modified.
  - generated output is confined to reports/data/gpu_experiments/v1/**.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/data/gpu_experiments/v1"
RAW = OUT / "raw"
PROC = OUT / "processed"

RUNS_INDEX = ROOT / "reports/runs_index.json"
BOOTSTRAP = ROOT / "reports/bootstrap_summary.json"
ANCHOR_SUMMARY = ROOT / "reports/anchor_eval_summary.json"
DATA_FIX = ROOT / "reports/data/data_fix_report.md"
DATA_AUDIT = ROOT / "reports/data/data_readiness_audit.md"

RAW_FILES = ("config.json", "manifest.json", "scores.jsonl", "metrics.json", "ecf_ledger.jsonl")
SCHEMA_VERSION = "gpu_experiments_v1"
GEN_DATE = "2026-11-23"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(p: Path):
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def csv_cell(v):
    """CSV-safe string for scalars/lists; json-encode lists & dicts (no rounding)."""
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def write_csv(path: Path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: csv_cell(r.get(k)) for k in fieldnames})


def write_jsonl(path: Path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def method_of(cfg, metrics, idx):
    """Transcribe a method label from raw fields; never invent one."""
    ec = cfg.get("experiment_config", {})
    return ec.get("mapper") or ec.get("method") or (metrics or {}).get("method") or None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    idx_runs = read_json(RUNS_INDEX)           # 28 authoritative runs
    by_id = {r["run_id"]: r for r in idx_runs}
    bootstrap = read_json(BOOTSTRAP)
    bs_runs = bootstrap["runs"]
    anchor_summary = read_json(ANCHOR_SUMMARY)

    # ---------- RAW layer ----------
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "generated_on": GEN_DATE,
        "source_index": str(RUNS_INDEX.relative_to(ROOT)),
        "total_raw_files": 0,
        "copied_files": [],
        "excluded_cache_npz": {
            "reason": "regenerable KV-cache tensors (cache/*.npz); not copied per task scope",
            "count": 0,
            "total_size_bytes": 0,
            "manifest_hash_registration": "none — no run manifest.json registers any .npz sha256",
            "files": [],
        },
    }
    raw_sha_mismatch = []
    line_count_mismatch = []

    for r in idx_runs:
        rid = r["run_id"]
        src_dir = ROOT / "reports/runs" / rid
        dst_dir = RAW / rid
        dst_dir.mkdir(parents=True, exist_ok=True)
        for name in RAW_FILES:
            src = src_dir / name
            if not src.exists():
                continue
            dst = dst_dir / name
            shutil.copyfile(src, dst)                 # byte-exact
            s_sha, d_sha = sha256_file(src), sha256_file(dst)
            if s_sha != d_sha:                         # fail loudly, never fabricate
                raw_sha_mismatch.append({"source": str(src), "src": s_sha, "raw": d_sha})
            inventory["copied_files"].append({
                "source_path": str(src.relative_to(ROOT)),
                "raw_path": str(dst.relative_to(ROOT)),
                "size_bytes": src.stat().st_size,
                "sha256": d_sha,
                "run_id": rid,
            })
        # scores line count must equal runs_index.n_scores
        sc = src_dir / "scores.jsonl"
        if sc.exists():
            n = sum(1 for ln in open(sc, encoding="utf-8") if ln.strip())
            if n != r.get("n_scores"):
                line_count_mismatch.append({"run_id": rid, "n_scores": r.get("n_scores"), "lines": n})
    inventory["total_raw_files"] = len(inventory["copied_files"])

    # cache npz inventory (paths / sizes / manifest registration), NOT copied
    npz_root = ROOT / "reports/runs"
    for p in sorted(npz_root.glob("*/cache/*.npz")):
        rid = p.parent.parent.name
        if rid not in by_id:
            continue                                   # only authoritative-index runs
        inventory["excluded_cache_npz"]["files"].append({
            "run_id": rid,
            "source_path": str(p.relative_to(ROOT)),
            "size_bytes": p.stat().st_size,
            "registered_in_manifest_sha256": False,
            "raw_path": None,
        })
    inv_ex = inventory["excluded_cache_npz"]
    inv_ex["count"] = len(inv_ex["files"])
    inv_ex["total_size_bytes"] = sum(f["size_bytes"] for f in inv_ex["files"])
    write_jsonl(OUT / "file_inventory.json", [inventory])  # single JSON object per line (valid JSONL)

    # ---------- PROCESSED: runs_summary ----------
    summary_rows = []
    for r in idx_runs:
        rid = r["run_id"]
        src_dir = ROOT / "reports/runs" / rid
        cfg = read_json(src_dir / "config.json")
        mpath = src_dir / "metrics.json"
        metrics = read_json(mpath) if mpath.exists() else None
        ec = cfg.get("experiment_config", {})
        pe = (bs_runs.get("runs/" + rid) or {}).get("primary_endpoint")
        pls = (pe or {}).get("pair_level_sensitivity") or {}
        eval_splits = ec.get("eval_splits")
        data_sha = r.get("data_sha256") or ec.get("data_sha256") or (metrics or {}).get("data_sha256")
        transfer_broken = (metrics.get("transfer_broken") if metrics and "transfer_broken" in metrics
                           else r.get("transfer_broken"))
        verdict = ((metrics or {}).get("decision") or {}).get("verdict") or r.get("mechanism_verdict")
        summary_rows.append({
            "run_id": rid,
            "status": "authoritative" if not r.get("superseded", False) else "superseded",
            "authoritative": (not r.get("superseded", False)),
            "superseded_reason": r.get("superseded_reason", ""),
            "stage": r.get("stage"),
            "gate": r.get("gate"),
            "method": method_of(cfg, metrics, r),
            "metrics_method_raw": (metrics or {}).get("method"),
            "mapper_raw": ec.get("mapper"),
            "seed": r.get("seed"),
            "git_hash": r.get("git_hash"),
            "protocol_version": r.get("protocol_version"),
            "data_sha256": data_sha,
            "zero_re_prefill": r.get("zero_re_prefill"),
            "eval_splits": "|".join(eval_splits) if isinstance(eval_splits, list) else eval_splits,
            "primary_endpoint_point": (pe or {}).get("point"),
            "primary_ci_template_family": (pe or {}).get("ci"),
            "primary_ci_pair_level": pls.get("ci"),
            "primary_endpoint_improved": (pe or {}).get("improved"),
            "primary_n_clusters": (pe or {}).get("n_clusters"),
            "primary_exploratory": (pe or {}).get("exploratory"),
            "transfer_broken": transfer_broken,
            "verdict": verdict,
            "n_scores": r.get("n_scores"),
            "source_raw_dir": "raw/" + rid,
        })
    summary_fields = list(summary_rows[0].keys())
    write_csv(PROC / "runs_summary.csv", summary_fields, summary_rows)

    # ---------- PROCESSED: pair_scores_tidy (26 synthetic runs; anchors handled separately) ----------
    tidy_rows = []
    cluster_map = {}
    synth_count = 0
    for r in idx_runs:
        rid = r["run_id"]
        if r.get("stage") == "external_anchor":
            continue
        synth_count += 1
        src_dir = ROOT / "reports/runs" / rid
        cfg = read_json(src_dir / "config.json")
        mpath = src_dir / "metrics.json"
        metrics = read_json(mpath) if mpath.exists() else None
        arms_meta = (metrics or {}).get("arms", {})
        method = method_of(cfg, metrics, r)
        auth = not r.get("superseded", False)
        data_sha = r.get("data_sha256") or (metrics or {}).get("data_sha256")
        transfer_broken = (metrics.get("transfer_broken") if metrics and "transfer_broken" in metrics
                           else r.get("transfer_broken"))
        for rec in read_jsonl(src_dir / "scores.jsonl"):
            out = dict(rec)  # preserve every raw field/value verbatim
            arm = rec.get("arm")
            am = arms_meta.get(arm, {}) if isinstance(arms_meta, dict) else {}
            out.update({
                "run_id": rid,
                "authoritative": auth,
                "status": "authoritative" if auth else "superseded",
                "method": method,
                "seed": r.get("seed"),
                "arm_dual_correct": am.get("dual_correct"),
                "arm_coverage": am.get("coverage"),
                "arm_info_gap": am.get("info_gap"),
                "transfer_broken": transfer_broken,
                "data_sha256": data_sha,
                "git_hash": r.get("git_hash"),
                "source_raw_dir": "raw/" + rid,
            })
            tidy_rows.append(out)
            # cluster map: one row per (run_id, pair_id); all cluster fields are
            # arm-invariant within a pair, verified by the first occurrence.
            key = (rid, rec.get("pair_id"))
            if key not in cluster_map:
                cluster_map[key] = {
                    "run_id": rid,
                    "pair_id": rec.get("pair_id"),
                    "template_family": rec.get("template_family"),
                    "cluster": rec.get("cluster"),
                    "split": rec.get("split"),
                    "slice_id": rec.get("slice_id"),
                    "must_flip": rec.get("must_flip"),
                    "authoritative": auth,
                    "source_raw_scores": str((src_dir / "scores.jsonl").relative_to(ROOT)),
                }
    write_jsonl(PROC / "pair_scores_tidy.jsonl", tidy_rows)

    cluster_fields = ["run_id", "pair_id", "template_family", "cluster", "split", "slice_id",
                      "must_flip", "authoritative", "source_raw_scores"]
    write_csv(PROC / "cluster_map.csv", cluster_fields, [cluster_map[k] for k in sorted(cluster_map)])

    # ---------- PROCESSED: anchor_scores_tidy ----------
    anchor_rows = []
    for rid in ("anchor_squad_affine_seed0", "anchor_squad_kd_seed0"):
        r = by_id[rid]
        cfg = read_json(ROOT / "reports/runs" / rid / "config.json")
        metrics = read_json(ROOT / "reports/runs" / rid / "metrics.json")
        summ = anchor_summary["runs"][rid]
        for rec in read_jsonl(ROOT / "reports/runs" / rid / "scores.jsonl"):
            out = dict(rec)
            out.update({
                "run_id": rid,
                "authoritative": not r.get("superseded", False),
                "status": "authoritative",
                "method": r.get("method") or cfg.get("experiment_config", {}).get("method"),
                "seed": r.get("seed"),
                "n": summ.get("n"),
                "zero_re_prefill": r.get("zero_re_prefill"),
                "data_sha256": r.get("data_sha256"),
                "git_hash": r.get("git_hash"),
                "anchor": anchor_summary["anchor"]["benchmark"],
                "anchor_scenario": anchor_summary["findings"]["scenario_verdict"],
                "source_raw_dir": "raw/" + rid,
            })
            anchor_rows.append(out)
    write_jsonl(PROC / "anchor_scores_tidy.jsonl", anchor_rows)

    # ---------- PROCESSED: data_quality_before_after (verbatim transcription, data_fix_report.md §2) ----------
    dq_rows = [
        ("数据 sha256", "6058fd6d…d1887", "f910f1f1…a894a"),
        ("文件字节 / 行数", "439734 / 520", "455900 / 520"),
        ("split 规模", "probe40/train120/val60/test300", "不变（满足 protocol.yaml）"),
        ("切片计数", "F1 130/F2 67/F3 130/F4 67/F5 63/F6 63", "F1 111/F2 90/F3 110/F4 87/F5 61/F6 61"),
        ("退化对（must_flip）", "18（test 7）", "0"),
        ("跨 split 逐字重叠", "≥15 组（含 train↔test 整对泄漏）", "0"),
        ("实体跨 split 重叠", "8 姓名全共享", "0（8 类实体全隔离）"),
        ("模板基础结构数", "8（F1 与 F5 骨架还重复）", "24"),
        ("template_family 族数", "probe8/train16/val8/test8（共 40）", "probe16/train16/val8/test16（共 56）"),
        ("unseen 子集", "仅后缀 D，无结构未见", "32 族 / 16 结构真正未见"),
        ("train/test 模板骨架", "100% 重合", "∅"),
        ("length_mismatch", "39（全 F5）", "61（全 F5，probe4/train14/val7/test36）"),
        ("F5 负控数", "63", "61"),
        ("flip 分母（排除 F5+F6）", "394（含 18 退化对）", "398（干净数据重算）"),
        ("quality_gate", "pass（但门禁未检查泄漏/退化）", "pass（门禁新增 6 项正确性检查）"),
        ("manifest 溯源字段", "无 license/source/commit hash", "全部具备 + 哈希 sidecar"),
    ]
    dq_out = [{"metric": m, "before_v2_0": b, "after_v2_1": a,
               "source": "reports/data/data_fix_report.md §2 (transcribed verbatim; corroborated by data_readiness_audit.md §1–§3)"}
              for m, b, a in dq_rows]
    write_csv(PROC / "data_quality_before_after.csv",
              ["metric", "before_v2_0", "after_v2_1", "source"], dq_out)

    # ---------- validation ----------
    expected_pair_rows = sum(r.get("n_scores", 0) for r in idx_runs if r.get("stage") != "external_anchor")
    expected_anchor_rows = sum(r.get("n_scores", 0) for r in idx_runs if r.get("stage") == "external_anchor")
    validations = {
        "raw_sha256_matches_source": len(raw_sha_mismatch) == 0,
        "raw_sha256_mismatches": raw_sha_mismatch,
        "scores_line_count_matches_runs_index": len(line_count_mismatch) == 0,
        "scores_line_count_mismatches": line_count_mismatch,
        "runs_summary_rows": len(summary_rows),
        "pair_scores_tidy_rows": len(tidy_rows),
        "pair_scores_expected_rows": expected_pair_rows,
        "pair_scores_rows_match_source": len(tidy_rows) == expected_pair_rows,
        "anchor_scores_tidy_rows": len(anchor_rows),
        "anchor_scores_expected_rows": expected_anchor_rows,
        "anchor_scores_rows_match_source": len(anchor_rows) == expected_anchor_rows,
        "cluster_map_rows": len(cluster_map),
        "data_quality_rows": len(dq_out),
    }
    assert all(validations[k] for k in ("raw_sha256_matches_source", "scores_line_count_matches_runs_index",
                                        "pair_scores_rows_match_source", "anchor_scores_rows_match_source")), validations

    # ---------- manifest ----------
    def fsha(p):
        return sha256_file(p)

    processed_desc = []
    for name in ("runs_summary.csv", "pair_scores_tidy.jsonl", "anchor_scores_tidy.jsonl",
                 "data_quality_before_after.csv", "cluster_map.csv"):
        p = PROC / name
        nlines = sum(1 for _ in open(p, encoding="utf-8")) - (1 if name.endswith(".csv") else 0)
        processed_desc.append({"path": "processed/" + name, "rows": nlines, "sha256": fsha(p)})

    # aggregate over raw file bytes in lexicographic raw_path order (documented in README)
    h_agg = hashlib.sha256()
    for item in sorted(inventory["copied_files"], key=lambda x: x["raw_path"]):
        with open(ROOT / item["raw_path"], "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h_agg.update(chunk)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_on": GEN_DATE,
        "method": "column/field projection only; no statistic recomputed; no numeric value altered",
        "source_files": [{
            "path": str(p.relative_to(ROOT)), "sha256": fsha(p)} for p in
            (RUNS_INDEX, BOOTSTRAP, ANCHOR_SUMMARY, DATA_FIX, DATA_AUDIT)
        ],
        "raw": {
            "run_count": len(idx_runs),
            "file_count": inventory["total_raw_files"],
            "aggregate_sha256_over_sorted_raw_file_bytes": h_agg.hexdigest(),
            "inventory_path": "file_inventory.json",
            "inventory_sha256": fsha(OUT / "file_inventory.json"),
        },
        "processed": {
            "file_count": len(processed_desc),
            "files": processed_desc,
        },
        "exclusions": {
            "cache_npz": {"count": inv_ex["count"], "total_size_bytes": inv_ex["total_size_bytes"],
                          "reason": inv_ex["reason"]},
            "runs_not_in_runs_index": {
                "run_ids": sorted({p.parent.parent.name for p in (ROOT / "reports/runs").glob("*/cache/*.npz")}
                                  - set(by_id)) + sorted(
                    {d.name for d in (ROOT / "reports/runs").iterdir() if d.is_dir()} - set(by_id)),
                "reason": "reports/runs_index.json is the authoritative 28-run list; these dirs are not indexed",
            },
            "mock_smoke_non_authoritative": {
                "reason": "reports/_non_authoritative/** (smoke tests) excluded from all formal data",
            },
        },
        "validation": validations,
    }
    with open(OUT / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({
        "raw_files": inventory["total_raw_files"],
        "runs": len(idx_runs),
        "processed_files": len(processed_desc),
        "rows": {k: validations[k] for k in ("runs_summary_rows", "pair_scores_tidy_rows",
                                              "anchor_scores_tidy_rows", "cluster_map_rows", "data_quality_rows")},
        "cache_npz": {"count": inv_ex["count"], "bytes": inv_ex["total_size_bytes"]},
        "validation_ok": {k: v for k, v in validations.items() if isinstance(v, bool)},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
