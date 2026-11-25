import numpy as np

from readkv.stats.bootstrap import cluster_bootstrap, max_family_bootstrap, paired_bootstrap, spearman_with_ci


def test_paired_bootstrap_covers_zero():
    deltas = np.zeros(20)
    point, low, high = paired_bootstrap(deltas, n_resamples=200, seed=0)
    assert point == 0.0 and low == 0.0 and high == 0.0


def test_cluster_bootstrap_shape():
    values = list(range(10))
    clusters = ["a"] * 5 + ["b"] * 5
    point, low, high = cluster_bootstrap(values, clusters, n_resamples=200, seed=1)
    assert point == 4.5 and low <= point <= high


def test_max_family_bootstrap_upper_positive():
    point, low, high = max_family_bootstrap([0.0, -0.1, -0.2], n_resamples=200, seed=2)
    assert point == 0.0 and high >= 0.0


def test_spearman_sign():
    x = np.arange(10)
    rho, low, high = spearman_with_ci(x, -x, n_resamples=100, seed=3)
    assert abs(rho + 1.0) < 1e-9
