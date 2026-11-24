"""R2/R3 合规修复回归：consistency_check 的 2.8 协议校验 + bootstrap 的三读数 E_CF。

纯 CPU；不跑 GPU、不改运行产物、不重判结果。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.bootstrap_ci_report import _ecf_value, _sequence_readings, summarize_run
from scripts.consistency_check import _check_protocol_compat, _check_v28_fields


# ---------------------------------------------------------------------------
# R2: protocol 白名单 + v2.8 字段校验
# ---------------------------------------------------------------------------


def v28_cfg(**overrides):
    ec = {
        "stage": "sequence_scoring", "cell": "A11",
        "calibration_version": "fixed", "validation_version": "fixed",
        "version_tag": "fixed_efc3ba3", "seed": 0,
        "input_sha256": {"train": "a" * 64, "val": "b" * 64},
        "dtype": "bfloat16", "kernel": "sdpa", "zero_re_prefill": True,
        "sealed_test_read": False,
        "teacher": "/x/Qwen3-1.7B", "student": "/x/Qwen3-0.6B",
        "tokenizer_fingerprint": {"sha256": "c" * 64, "path": "/x/tokenizer"},
        "scoring": ["first", "full", "length_normalized"],
    }
    ec.update(overrides.get("ec", {}))
    cfg = {"protocol_version": "2.8", "git_hash": "abc1234", "seed": 0,
           "dtype": "bfloat16", "kernel": "sdpa", "zero_re_prefill": True,
           "experiment_config": ec}
    cfg.update({k: v for k, v in overrides.items() if k != "ec"})
    return cfg


def test_protocol_whitelist_includes_2_7_and_2_8():
    for pv in ("2.0", "2.1", "2.7", "2.8"):
        cfg = v28_cfg(protocol_version=pv)
        assert not any("incompatible with frozen V2 prereg" in p
                       for p in _check_protocol_compat(cfg)["problems"])
    bad = _check_protocol_compat(v28_cfg(protocol_version="9.9"))
    assert any("incompatible" in p for p in bad["problems"]) and bad["ok"] is False


def test_v28_valid_config_passes():
    r = _check_protocol_compat(v28_cfg())
    assert r["ok"] is True and r["protocol_version"] == "2.8"
    f = r["v28_fields"]
    assert f["ok"] is True and f["version_tag"] == "fixed_efc3ba3"
    assert f["input_sha256_present"] == {"train": True, "val": True}
    assert f["zero_re_prefill"] is True and f["sealed_test_read"] is False
    assert f["tokenizer_fingerprint"] == "c" * 16


def test_v28_field_violations_detected():
    cases = [
        ({"ec": {"version_tag": ""}}, "version_tag"),
        ({"ec": {"version_tag": "fixed_wrong", "calibration_version": "legacy",
                 "validation_version": "legacy"}}, "does not match"),
        ({"ec": {"input_sha256": {"train": "short"}}}, "input_sha256.val"),
        ({"ec": {"sealed_test_read": True}}, "sealed_test_read"),
        ({"ec": {"tokenizer_fingerprint": {"sha256": "unavailable:TypeError"}}}, "tokenizer fingerprint"),
        ({"ec": {"scoring": ["first"]}}, "three readings"),
        ({"ec": {"seed": 1}}, "seed mismatch"),
        ({"zero_re_prefill": False}, "zero_re_prefill"),
    ]
    for kw, needle in cases:
        r = _check_v28_fields(v28_cfg(**kw))
        assert r["ok"] is False and any(needle in p for p in r["problems"]), (needle, r["problems"])


def test_v28_diagonal_cell_mismatch_detected():
    r = _check_v28_fields(v28_cfg(ec={"calibration_version": "legacy"}))
    assert r["ok"] is False and any("calibration==validation" in p for p in r["problems"])


# ---------------------------------------------------------------------------
# R3: dict 型 E_CF（v2.8 三读数）
# ---------------------------------------------------------------------------


def _dict_rows(tmp_path: Path, *, n=12, families=6):
    rows = []
    for i in range(n):
        for arm in ("self", "joint"):
            rows.append({
                "pair_id": f"p{i}", "arm": arm,
                "template_family": f"T{i % families}",
                "E_CF": {
                    "first": float(i % 3) + (0.5 if arm == "joint" else 0.0),
                    "full": float(i % 4) + (0.25 if arm == "joint" else 0.0),
                    "length_normalized": float(i % 5) + (0.1 if arm == "joint" else 0.0),
                },
            })
    p = tmp_path / "scores.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def test_ecf_value_never_casts_dict_to_float():
    row = {"E_CF": {"first": 1.0, "full": 2.0, "length_normalized": 3.0}}
    assert _ecf_value(row) is None
    assert _ecf_value(row, "full") == 2.0
    assert _ecf_value(row, "missing") is None
    assert _ecf_value({"E_CF": 4.5}) == 4.5


def test_sequence_readings_detected():
    rows = [{"E_CF": {"full": 1.0, "first": 0.5, "length_normalized": 0.2}}]
    assert _sequence_readings(rows) == ["first", "full", "length_normalized"]


def test_dict_ecf_summarized_per_reading(tmp_path):
    r = summarize_run(_dict_rows(tmp_path), n_resamples=64, epsilon=0.02, seed=0)
    assert r["sequence_scoring"] is True
    assert r["protocol"] == "v2.8"
    assert r["sequence_readings"] == ["first", "full", "length_normalized"]
    assert "handled separately" in r["sequence_scoring_note"]
    for arm in ("self", "joint"):
        a = r["arms"][arm]
        assert a["n"] == 12 and a["n_excluded_non_numeric_total"] == 0
        assert set(a["readings"]) == {"first", "full", "length_normalized"}
        for rd in a["readings"]:
            v = a["readings"][rd]
            assert v["n"] == 12 and v["cluster_unit"] == "template_family"
            assert v["n_clusters"] == 6 and v["exploratory"] is True
            assert "[" in v["E_CF"] and "[" in v["E_CF_pair_level_sensitivity"]
    assert r["primary_endpoint"] is None  # 无 new_joint arm，不臆造主终点


def test_float_ecf_path_unchanged(tmp_path):
    p = tmp_path / "scores.jsonl"
    rows = [{"pair_id": f"p{i}", "arm": "joint", "template_family": f"T{i % 6}", "E_CF": float(i)}
            for i in range(12)]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    r = summarize_run(p, n_resamples=64, epsilon=0.02, seed=0)
    assert r["sequence_scoring"] is False and r["protocol"] == "v2.0"
    assert "E_CF" in r["arms"]["joint"] and "readings" not in r["arms"]["joint"]


def test_mixed_dict_and_float_exclusions_reported(tmp_path):
    rows = []
    for i in range(12):
        ec = {"first": 1.0, "full": 2.0, "length_normalized": 3.0} if i % 2 == 0 else 7.0
        rows.append({"pair_id": f"p{i}", "arm": "self", "template_family": f"T{i % 6}", "E_CF": ec})
    p = tmp_path / "scores.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    r = summarize_run(p, n_resamples=64, epsilon=0.02, seed=0)
    assert r["sequence_scoring"] is True
    a = r["arms"]["self"]
    assert a["n"] == 12 and a["n_excluded_non_numeric_total"] == 18  # 3 readings × 6 float 行
    assert a["n_excluded_non_numeric_per_reading"] == {
        "first": 6, "full": 6, "length_normalized": 6}  # 不静默丢数
    assert all(v["n"] == 6 for v in a["readings"].values())
