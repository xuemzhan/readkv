import numpy as np

from readkv.cache.cache import KVCache
from readkv.mapper.base import ridge_solve
from readkv.mapper.consumer import alpha_grid, consumer_solve
from readkv.mapper.key_objectives import score_regression_solve


def test_ridge_solve():
    x = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    y = x @ np.array([[1.0, 2.0], [3.0, 4.0]])
    m = ridge_solve(x, y, lam=0.0)
    np.testing.assert_allclose(x @ m, y, atol=1e-6)


def test_consumer_solve_alpha_zero_matches_ridge():
    rng = np.random.default_rng(0)
    x, y = rng.normal(size=(8, 3)), rng.normal(size=(8, 3))
    a = np.eye(8)
    np.testing.assert_allclose(consumer_solve(x, y, a, alpha=0.0, lam=1e-3), ridge_solve(x, y, 1e-3))


def test_alpha_grid_size():
    assert len(alpha_grid()) == 33


def test_score_regression_reduces_residual():
    rng = np.random.default_rng(1)
    q, kt, ks = rng.normal(size=(6, 4)), rng.normal(size=(8, 4)), rng.normal(size=(8, 4))
    m = score_regression_solve(q, kt, ks)
    mapped_residual = np.linalg.norm(q @ (kt @ m).T - q @ ks.T)
    raw_residual = np.linalg.norm(q @ kt.T - q @ ks.T)
    assert mapped_residual < raw_residual


def test_key_mapper_transform_keeps_student_values():
    from readkv.mapper.key_objectives import ScoreRegressionKeyMapper

    rng = np.random.default_rng(2)
    k_t = rng.normal(size=(1, 5, 4))
    k_s = rng.normal(size=(1, 5, 4))
    q = rng.normal(size=(5, 4))
    mapper = ScoreRegressionKeyMapper().fit(
        KVCache({0: k_t}, {0: k_t}), KVCache({0: k_s}, {0: k_s}), query_states={(0, 0): q}
    )
    out = mapper.transform(KVCache({0: k_t}, {0: k_t}))
    assert out.keys[0].shape == (1, 5, 4)
    np.testing.assert_array_equal(out.values[0], k_t)
