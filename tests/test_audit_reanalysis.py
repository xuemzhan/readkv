"""Regression tests for the CPU-only E3/E4/E7 reanalyses (docs/audit revision)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_reanalysis as ar

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "papers" / "readkv_v2_tmlr_anonymous"


@pytest.fixture(scope="module")
def ledger():
    return json.loads((PAPER / "evaluation.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def results():
    return json.loads((PAPER / "results.json").read_text(encoding="utf-8"))


def test_delta_matches_predeclared_config():
    config = (ROOT / "configs" / "prereg" / "equivalence_margin_v2.9.yaml").read_text(encoding="utf-8")
    assert "delta_ecf: 2.0" in config
    assert ar.DELTA == 2.0


def test_e3_reports_significance_and_seed_dependent_equivalence(ledger):
    e3 = ar.e3(ledger)
    seed0_zero = e3["0"]["controls"]["zero"]["family_test"]
    seed1_zero = e3["1"]["controls"]["zero"]["family_test"]
    # Joint is significantly closer to Self than the zero-cache control in seed 0.
    assert seed0_zero["two_sided_p"] < 0.05
    assert seed0_zero["family_mean_diff"] < 0
    assert seed0_zero["equivalent_at_delta"] is False
    # Pre-declared equivalence succeeds in seed 1.
    assert seed1_zero["equivalent_at_delta"] is True
    assert seed1_zero["tost_p"] < 0.05
    assert all(e3["1"]["controls"][c]["family_test"]["equivalent_at_delta"]
               for c in ("mismatch", "zero", "random"))


def test_e4_scale_and_rank_reversal(ledger, results):
    e4 = ar.e4(ledger, results)
    a00 = e4["scale"]["A00"]["0"]["ecf_over_abs_dself"]
    a11 = e4["scale"]["A11"]["0"]["ecf_over_abs_dself"]
    assert 0.30 < a00 < 0.35
    assert 0.75 < a11 < 0.95
    assert e4["rank_correlation"]["affine"]["spearman_rho"] < 0
    assert e4["rank_correlation"]["kd"]["spearman_rho"] > 0
    assert abs(e4["rank_correlation"]["affine"]["spearman_rho"]) > 0.4


def test_e7_cluster_counts_and_direction(ledger):
    e7 = ar.e7(ledger)
    assert e7["subsets"]["retained_6_family"]["A11_0"] == {"pairs": 46, "families": 6}
    assert e7["subsets"]["f1_f4_all_6_family"]["A00_0"] == {"pairs": 46, "families": 6}
    assert e7["subsets"]["all_60_pairs_8_family"]["A00_0"] == {"pairs": 60, "families": 8}
    seed1 = e7["per_seed"]["1"]["all_60"]
    assert seed1["A11_full_L"][0] < seed1["A11_first_L"][0]
    assert seed1["contrast_full"][0] > 0


def test_table_generator_is_deterministic(tmp_path):
    from scripts import reanalysis_tables as rt

    d = json.loads((ROOT / "reports" / "audit_reanalysis.json").read_text(encoding="utf-8"))
    first = rt.build(d)
    second = rt.build(d)
    assert first == second
    for macro in ("ControlTestRows", "ControlMeanRows", "ScaleRows", "RankRows",
                  "MapperGapRows", "ExtendedScoringRows", "ExtendedContrastRows",
                  "ScoringCountRows"):
        assert f"\\newcommand{{\\{macro}}}{{%" in first
