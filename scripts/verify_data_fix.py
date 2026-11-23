"""独立验收检查：M1/M2/M3/M5/M7′ 数据修复后的可复核证据。

不调用 quality_report 的判定逻辑，直接从 data/tasks/cf_pairs.jsonl 文件与
manifest 重算；另用 build_cf_pairs(seed=0) 在临时目录重建验证确定性。
输出写到 reports/data/acceptance_checks.json（本角色权限内）。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tasks"
sys.path.insert(0, str(ROOT / "src"))

from readkv.data.build_cf_pairs import build_cf_pairs, save_pairs  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skeleton(text: str, entities: list[str]) -> str:
    s = text
    for v in sorted(entities, key=len, reverse=True):
        s = s.replace(v, "<E>")
    s = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", s)
    return re.sub(r"\d+", "<NUM>", s)


def main() -> int:
    data_path = DATA / "cf_pairs.jsonl"
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    checks: dict[str, object] = {}

    # 1. manifest vs file
    f = manifest["files"][0]
    checks["manifest_sha256_match"] = (f["sha256"] == sha256(data_path))
    checks["manifest_size_match"] = (f["size"] == data_path.stat().st_size)
    checks["manifest_lines_match"] = (f["lines"] == len(rows))

    # 2. split sizes
    by_split = defaultdict(int)
    for r in rows:
        by_split[r["split"]] += 1
    checks["split_sizes"] = dict(by_split)
    checks["split_sizes_match_protocol"] = (
        dict(by_split) == {"probe": 40, "train": 120, "val": 60, "test": 300})

    # 3. M2 cross-split verbatim overlap（独立重算）
    overlap: dict[str, int] = {}
    for field in ("context_A", "context_B", "query", "edited_span"):
        sets = defaultdict(set)
        for r in rows:
            sets[r["split"]].add(r[field])
        keys = list(sets)
        overlap[field] = sum(len(sets[a] & sets[b])
                             for i, a in enumerate(keys) for b in keys[i + 1:])
    checks["cross_split_verbatim_overlap"] = overlap
    checks["cross_split_overlap_zero"] = all(v == 0 for v in overlap.values())

    # 4. M1 degenerate pairs（独立重算）
    deg = [r["pair_id"] for r in rows if r["must_flip"] and (
        r["candidate_A"] == r["candidate_B"]
        or r["context_A"] == r["context_B"]
        or r["correct_A"] == r["correct_B"])]
    checks["degenerate_must_flip_pairs"] = len(deg)
    checks["degenerate_ids_sample"] = deg[:10]

    # 5. M3 template skeleton train∩test（独立重算，实体从数据自身聚合近似）
    # 用所有候选/编辑里的实体值做归一化；不同 split 的实体来自不同池
    entities = sorted({r[k] for r in rows for k in ("candidate_A", "candidate_B")},
                      key=len, reverse=True)
    sk_train = {skeleton(r["context_A"], entities) for r in rows if r["split"] == "train"}
    sk_test = {skeleton(r["context_A"], entities) for r in rows if r["split"] == "test"}
    checks["template_skeleton_train_test_shared"] = len(sk_train & sk_test)
    checks["template_skeleton_disjoint"] = not (sk_train & sk_test)

    # 6. entity isolation via candidate names per split
    cand_by_split = defaultdict(set)
    for r in rows:
        cand_by_split[r["split"]].update((r["candidate_A"], r["candidate_B"]))
    keys = list(cand_by_split)
    ent_overlap = sum(len(cand_by_split[a] & cand_by_split[b])
                      for i, a in enumerate(keys) for b in keys[i + 1:])
    checks["candidate_entity_cross_split_overlap"] = ent_overlap

    # 7. flip denominator（v2.3 口径：排除 F5/F6）
    flip = sum(1 for r in rows if r["slice_id"] not in ("F5", "F6"))
    checks["recomputed_flip_denominator"] = flip
    checks["flip_denominator_matches_manifest"] = (flip == manifest["quality"]["flip_denominator"])

    # 8. determinism rebuild
    with tempfile.TemporaryDirectory() as td:
        rebuilt = save_pairs(build_cf_pairs(seed=0), Path(td) / "rebuild.jsonl")
        checks["deterministic_rebuild_identical"] = (sha256(rebuilt) == sha256(data_path))

    # 9. v2.3 冻结文件未被改动
    v23 = ROOT / "configs" / "prereg" / "stats_convention_v2.3.yaml"
    checks["stats_convention_v2_3_sha256"] = sha256(v23)
    checks["manifest_stats_convention_sha_match"] = (
        sha256(v23) == manifest["stats_convention"]["sha256"])

    passed = all([
        checks["manifest_sha256_match"], checks["manifest_size_match"],
        checks["manifest_lines_match"], checks["split_sizes_match_protocol"],
        checks["cross_split_overlap_zero"], checks["degenerate_must_flip_pairs"] == 0,
        checks["template_skeleton_disjoint"], checks["candidate_entity_cross_split_overlap"] == 0,
        checks["flip_denominator_matches_manifest"], checks["deterministic_rebuild_identical"],
        checks["manifest_stats_convention_sha_match"],
    ])
    checks["ALL_ACCEPTANCE_CHECKS_PASS"] = bool(passed)

    out = ROOT / "reports" / "data" / "acceptance_checks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
