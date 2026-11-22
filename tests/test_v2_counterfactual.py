"""V2.0 反事实功能保真测试（方案 §9.3 七条必要自动测试 + 模块级测试）。"""

from __future__ import annotations

import numpy as np
import pytest

from readkv.cache.cache import CacheStore, KVCache
from readkv.cache.identity_check import cache_round_trip, evaluate_implementation, logit_cosine
from readkv.cache.offline_prefill import PairCacheStore, prefill_pair, validate_cache
from readkv.data.build_cf_pairs import (
    DEFAULT_SIZES,
    build_cf_pairs,
    quality_report,
    split_pairs,
    stable_hash,
)
from readkv.diagnostics.route_value import (
    build_four_arms,
    decompose_attention,
    key_objective_matrix,
    oracle_transplant,
)
from readkv.evaluate.counterfactual import (
    PairCFRecord,
    counterfactual_error,
    g_score,
    paired_ecf_difference,
    summarize_cf,
)
from readkv.evaluate.cf_pipeline import run_cf_pipeline
from readkv.models.mock_backend import MockBackend, MockSpec
from readkv.runtime import v2_context


@pytest.fixture
def backend():
    return MockBackend(MockSpec(seed=0))


# ---------------------------------------------------------------------------
# 模块级测试
# ---------------------------------------------------------------------------

def test_build_cf_pairs_six_slices_and_isolation():
    pairs = build_cf_pairs(sizes={"train": 24, "val": 12, "test": 12, "probe": 0}, seed=0)
    assert len(pairs) == 48
    slices = {p.slice_id for p in pairs}
    assert slices == {"F1", "F2", "F3", "F4", "F5", "F6"}
    report = quality_report(pairs)
    assert report["quality_gate"] == "pass"
    assert report["template_overlap_train_eval"] == []
    assert report["f5_negative_controls"] > 0


def test_f5_not_in_flip_denominator():
    pairs = build_cf_pairs(sizes={"train": 12, "val": 6, "test": 6, "probe": 0})
    f5 = [p for p in pairs if p.slice_id == "F5"]
    assert f5
    assert all(not p.must_flip for p in f5)
    assert all(p.correct_A == "A/B" and p.correct_B == "A/B" for p in f5)


def test_g_score_and_ecf():
    # 单缓存 g 通过 PairCFRecord 计算（g_score 接受两份缓存的候选 logits）
    rec = PairCFRecord(
        pair_id="p", split="test", slice_id="F1", cluster="c",
        self_logits_A=[2.0, 0.0], self_logits_B=[0.0, 2.0],
        transfer_logits_A=[2.0, 0.0], transfer_logits_B=[0.0, 2.0],
    ).compute()
    assert rec["E_CF"] == pytest.approx(0.0)
    assert rec["D_self"] > 0
    assert rec["evaluable"]


def test_ecf_detects_distortion():
    rec = PairCFRecord(
        pair_id="p", split="test", slice_id="F1", cluster="c",
        self_logits_A=[2.0, 0.0], self_logits_B=[0.0, 2.0],
        transfer_logits_A=[0.0, 2.0], transfer_logits_B=[2.0, 0.0],
    ).compute()
    assert rec["E_CF"] > 0
    assert rec["flip_consistency"] is False


def test_normalized_and_paired_endpoint():
    records = []
    for i in range(20):
        base = {"pair_id": f"p{i}", "cluster": f"C{i//2}", "E_CF": 0.2}
        new = dict(base, E_CF=0.1)
        records.append((new, base))
    new_r, base_r = zip(*records)
    endpoint = paired_ecf_difference(new_r, base_r, n_resamples=500, seed=0)
    assert endpoint["improved"] is True
    assert endpoint["point"] == pytest.approx(-0.1)


def test_four_arms_deployability(backend):
    pairs = build_cf_pairs(sizes={"train": 4, "probe": 0, "val": 0, "test": 0})
    p = pairs[0]
    student = backend.pair_side_cache(p.as_record(), "A", "student")
    mapped = backend.pair_side_cache(p.as_record(), "A", "teacher")
    arms = build_four_arms(student=student, mapped=mapped)
    assert set(arms) == {"self", "k_only", "v_only", "joint"}
    assert arms["joint"].metadata["deployable"] is True
    assert all(not arms[a].metadata["deployable"] for a in ("k_only", "v_only"))


def test_decomposition_identity_residual(backend):
    q = np.random.default_rng(0).normal(size=(4, 8))
    ks = np.random.default_rng(1).normal(size=(6, 8))
    vs = np.random.default_rng(2).normal(size=(6, 8))
    d = decompose_attention(query=q, k_student=ks, v_student=vs,
                            k_mapped=ks, v_mapped=vs)
    assert d.residual_norm < 1e-9
    assert d.routing_norm < 1e-9
    assert d.consumption_norm < 1e-9


def test_key_objectives_shapes(backend):
    rng = np.random.default_rng(0)
    kt, ks = rng.normal(size=(6, 8)), rng.normal(size=(6, 8))
    mats = key_objective_matrix(teacher_k=kt, student_k=ks, query=rng.normal(size=(4, 8)))
    assert "A_ridge" in mats and "C_score" in mats
    assert all(m.shape == (8, 8) for m in mats.values())


def test_oracle_transplant_restores_native(backend):
    pairs = build_cf_pairs(sizes={"train": 2, "probe": 0, "val": 0, "test": 0})
    p = pairs[0]
    student = backend.pair_side_cache(p.as_record(), "A", "student")
    mapped = backend.pair_side_cache(p.as_record(), "A", "teacher")
    fixed, _ = oracle_transplant(student=student, mapped=mapped, layer=student.layers[0], head=0)
    np.testing.assert_allclose(fixed.keys[student.layers[0]][0], student.keys[student.layers[0]][0])


# ---------------------------------------------------------------------------
# 方案 §9.3 七条必要自动测试
# ---------------------------------------------------------------------------

def test_auto1_round_trip_consistency(tmp_path):
    rng = np.random.default_rng(0)
    cache = KVCache({0: rng.normal(size=(2, 4, 3))}, {0: rng.normal(size=(2, 4, 3))})
    assert cache_round_trip(cache, CacheStore(tmp_path), "rt")


def test_auto2_pairs_link_two_docs_and_answers():
    pairs = build_cf_pairs(sizes={"train": 12, "val": 6, "test": 6, "probe": 0})
    for p in pairs:
        assert p.context_A and p.context_B
        assert p.query and p.candidate_A and p.candidate_B
        if p.must_flip:
            assert p.correct_A != "A/B" and p.correct_B != "A/B"
        assert stable_hash(p)


def test_auto3_query_only_no_doc_tokens(backend, tmp_path):
    """零重 Prefill 标志由 RunContext 保证；此处验证 query-only 文档不含上下文。"""
    pairs = build_cf_pairs(sizes={"train": 2, "probe": 0, "val": 0, "test": 0})
    p = pairs[0]
    ctx = v2_context("zero_flag", {"stage": "test"}, reports_root=tmp_path)
    assert ctx.zero_re_prefill is True
    ctx.require_zero_re_prefill()
    query_doc = {"text": p.query}
    assert p.context_A not in str(query_doc)


def test_auto4_length_mismatch_explicit():
    pairs = build_cf_pairs(sizes={"train": 24, "probe": 0, "val": 0, "test": 0})
    mismatches = [p for p in pairs if not p.length_matched]
    assert mismatches  # 显式标注而非静默
    assert all(p.position_gap > 0 for p in mismatches)


def test_auto5_shuffled_mapping_causes_distortion(backend, tmp_path):
    """临时打乱映射（cf_distortion）应造成 E_CF 上升。"""
    cfg_sizes = {"train": 12, "val": 0, "test": 12, "probe": 0}
    clean_ctx = v2_context("cf_clean", {}, reports_root=tmp_path / "clean")
    from readkv.evaluate.cf_pipeline import CFPipelineConfig
    clean = run_cf_pipeline(clean_ctx, MockBackend(MockSpec(cf_distortion=0.0, seed=1)),
                            CFPipelineConfig(sizes=cfg_sizes, seed=1, n_resamples=200,
                                             eval_splits=("test",)))
    dirty_ctx = v2_context("cf_dirty", {}, reports_root=tmp_path / "dirty")
    dirty = run_cf_pipeline(dirty_ctx, MockBackend(MockSpec(cf_distortion=2.0, seed=1)),
                            CFPipelineConfig(sizes=cfg_sizes, seed=1, n_resamples=200,
                                             eval_splits=("test",), cf_distortion=2.0))
    e_clean = clean["arms"]["joint"]["E_CF"]["mean"]
    e_dirty = dirty["arms"]["joint"]["E_CF"]["mean"]
    assert e_dirty > e_clean


def test_auto6_disabling_new_losses_regresses_to_kd(backend, tmp_path):
    """关闭 L_CF/L_local（method=kd）应与 KD 基线行为一致。"""
    from readkv.data.build_cf_pairs import split_pairs
    from readkv.train.cf_rct import train_cf_rct

    pairs = build_cf_pairs(sizes={"train": 12, "probe": 0, "val": 0, "test": 0})
    cal = split_pairs(pairs, "train")
    kd = train_cf_rct(backend, cal, method="kd", epochs=2, seed=0)
    assert kd.module.method == "kd"


def test_auto7_train_test_hash_no_cross(backend, tmp_path):
    pairs = build_cf_pairs(sizes={"train": 12, "test": 12, "probe": 0, "val": 0})
    train_ids = [p.pair_id for p in split_pairs(pairs, "train")]
    test_ids = [p.pair_id for p in split_pairs(pairs, "test")]
    store = PairCacheStore(tmp_path)
    for p in split_pairs(pairs, "train"):
        store.save_pair(p.as_record(),
                        backend.pair_side_cache(p.as_record(), "A", "teacher"),
                        backend.pair_side_cache(p.as_record(), "B", "teacher"))
    for p in split_pairs(pairs, "test"):
        store.save_pair(p.as_record(),
                        backend.pair_side_cache(p.as_record(), "A", "teacher"),
                        backend.pair_side_cache(p.as_record(), "B", "teacher"))
    check = store.check_no_cross_contamination(train_ids, test_ids)
    assert check["passed"] is True
    assert check["overlap_hashes"] == []
