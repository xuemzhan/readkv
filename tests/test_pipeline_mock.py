import numpy as np

from readkv.evaluate.decision import match_decision
from readkv.evaluate.pipeline import PipelineConfig, fit_mapper, make_items, run_pipeline
from readkv.models.mock_backend import MockBackend, MockSpec
from readkv.runtime import RunContext


def _small():
    backend = MockBackend(MockSpec(n_layers=4, n_kv_heads=2, head_dim=6, content_rank=3, tokens_per_doc=4, seed=0))
    cfg = PipelineConfig(
        n_docs=8, n_calibration=4, n_eval=4, seed=0, n_resamples=100,
        controls=("wrong_document", "zero"), probes=("fraction_0.5", "top_third"),
    )
    return backend, cfg


def test_mock_backend_deterministic():
    backend, _ = _small()
    doc = {"doc_id": "D0", "text": "hello"}
    a, b = backend.teacher_cache(doc), backend.teacher_cache(doc)
    np.testing.assert_array_equal(a.keys[0], b.keys[0])
    other = backend.teacher_cache({"doc_id": "D1", "text": "world"})
    assert not np.allclose(a.keys[0], other.keys[0])


def test_pipeline_end_to_end(tmp_path):
    backend, cfg = _small()
    ctx = RunContext("pipeline_test", {"stage": 0}, reports_root=tmp_path)
    metrics = run_pipeline(ctx, backend, cfg)
    assert metrics["H1"]["passed"]
    assert metrics["H1"]["observed_min"] >= 0.9998
    for arm in ("self", "k_only", "v_only", "joint", "identity", "control:wrong_document", "probe:top_third"):
        assert arm in metrics["arms"]
    rows = ctx.read_scores()
    assert len(rows) > 0
    assert all("gold_prob_self" in row for row in rows)
    assert (tmp_path / "pipeline_test" / "metrics.json").exists()
    assert (tmp_path / "pipeline_test" / "manifest.json").exists()


def test_decision_rule_matching():
    rules = [
        {"verdict": "positive", "conditions": {"h2_pass_any": True}},
        {"verdict": "negative", "conditions": {"h2_pass_any": False}},
    ]
    assert match_decision(rules, {"h2_pass_any": True})["verdict"] == "positive"
    assert match_decision(rules, {"h2_pass_any": False})["verdict"] == "negative"
    assert match_decision(rules, {}) is None


def test_fit_mapper_variants():
    backend, cfg = _small()
    cal = make_items(backend, cfg.n_docs, cfg.seed)[: cfg.n_calibration]
    for kind in ("affine", "affine_k", "consumer", "wo_aware", "score", "score_weighted", "score_shuffled"):
        mapper = fit_mapper(backend, cal, kind)
        assert mapper is not None
