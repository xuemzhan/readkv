import numpy as np

from readkv.cache.cache import KVCache
from readkv.evaluate.controls import build_control, moment_matched_random
from readkv.evaluate.probes import (
    estimate_recompute_cost,
    fraction_probe,
    octant_probe,
    selective_recompute_plan,
    window_probe,
)


def _cache():
    rng = np.random.default_rng(0)
    return KVCache(
        {i: rng.normal(size=(2, 6, 4)).astype(np.float32) for i in range(6)},
        {i: rng.normal(size=(2, 6, 4)).astype(np.float32) for i in range(6)},
    )


def test_control_kinds():
    c = _cache()
    for kind in ("random_gaussian", "zero", "shuffle_k", "shuffle_v", "same_permutation"):
        out = build_control(c, kind, seed=0)
        assert out.keys[0].shape == c.keys[0].shape
        assert out.metadata["control"] == kind
    assert np.all(build_control(c, "zero").keys[0] == 0)


def test_same_permutation_keeps_correspondence():
    c = _cache()
    out = build_control(c, "same_permutation", seed=0)
    assert np.allclose(out.keys[0][:, :, 0], out.values[0][:, :, 0]) == np.allclose(c.keys[0][:, :, 0], c.values[0][:, :, 0])


def test_moment_matching():
    ref = np.random.default_rng(1).normal(3.0, 2.0, size=(2, 100, 4))
    out = moment_matched_random(ref, np.random.default_rng(2))
    assert out.shape == ref.shape
    assert abs(float(np.mean(out)) - float(np.mean(ref))) < 0.2


def test_probes():
    c, t = _cache(), _cache()
    mixed = fraction_probe(c, t, 0.5)
    assert mixed.metadata["probe"] == "fraction_0.5"
    assert window_probe(c, t, "top_third").n_layers == c.n_layers
    assert octant_probe(c, t, 3).metadata["probe"] == "octant_3"


def test_recompute_plan_and_cost():
    plan = selective_recompute_plan([0.3, 0.1, 0.5], [0.9, 0.8, 0.7], 2)
    assert plan == [2, 0]
    cost = estimate_recompute_cost(2, 6)
    assert cost["naive_worst_case_layers"] == 12.0
    assert cost["naive_average_layers"] == 7.0
