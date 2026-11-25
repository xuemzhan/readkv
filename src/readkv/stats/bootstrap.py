"""百分位 bootstrap：配对、文档聚类、family-wise 最大值、秩相关。

所有函数接受逐样本/逐配置的数组，返回 ``(point, low, high)``。
默认 10^4 重采样，与 docs/protocol.md 一致。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.stats import spearmanr


def _interval(values: np.ndarray, ci: float) -> tuple[float, float]:
    alpha = (1.0 - ci) / 2.0
    return float(np.quantile(values, alpha)), float(np.quantile(values, 1.0 - alpha))


def paired_bootstrap(
    paired_deltas: Sequence[float],
    *,
    n_resamples: int = 10_000,
    ci: float = 0.95,
    seed: int = 0,
    stat=np.mean,
) -> tuple[float, float, float]:
    """对配对差值做百分位 bootstrap（handoff − self）。"""
    x = np.asarray(paired_deltas, dtype=float)
    if x.ndim != 1 or x.size == 0:
        raise ValueError("paired_deltas must be a non-empty 1-D sequence")
    point = float(stat(x))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_resamples, x.size))
    draws = np.asarray([stat(x[i]) for i in idx])
    low, high = _interval(draws, ci)
    return point, low, high


def cluster_bootstrap(
    values: Sequence[float],
    clusters: Sequence[str | int],
    *,
    n_resamples: int = 10_000,
    ci: float = 0.95,
    seed: int = 0,
) -> tuple[float, float, float]:
    """以文档为重采样单位（论文 1：每 seed 8 个文档簇）。"""
    x = np.asarray(values, dtype=float)
    c = np.asarray(clusters)
    if x.shape != c.shape or x.size == 0:
        raise ValueError("values and clusters must align and be non-empty")
    groups = [x[c == g] for g in np.unique(c)]
    rng = np.random.default_rng(seed)
    point = float(np.mean(x))
    draws = np.empty(n_resamples)
    for i in range(n_resamples):
        picked = rng.integers(0, len(groups), size=len(groups))
        draws[i] = np.mean(np.concatenate([groups[j] for j in picked]))
    low, high = _interval(draws, ci)
    return point, low, high


def max_family_bootstrap(
    config_means: Sequence[float],
    *,
    n_resamples: int = 10_000,
    ci: float = 0.95,
    seed: int = 0,
) -> tuple[float, float, float]:
    """H3 family-wise 最大值 bootstrap：报告“最佳可达增益”的上界。"""
    means = np.asarray(config_means, dtype=float)
    if means.ndim != 1 or means.size == 0:
        raise ValueError("config_means must be a non-empty 1-D sequence")
    rng = np.random.default_rng(seed)
    draws = np.max(rng.choice(means, size=(n_resamples, means.size), replace=True), axis=1)
    low, high = _interval(draws, ci)
    return float(np.max(means)), low, high


def spearman_with_ci(
    x: Sequence[float], y: Sequence[float], *, n_resamples: int = 10_000, ci: float = 0.95, seed: int = 0
) -> tuple[float, float, float]:
    """平均秩的 Spearman 相关 + 配置级 bootstrap 区间（mapper objective sweep）。"""
    a, b = np.asarray(x, float), np.asarray(y, float)
    if a.shape != b.shape or a.size < 3:
        raise ValueError("x and y must align with at least 3 points")
    point = float(spearmanr(a, b).statistic)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_resamples, a.size))
    draws = np.asarray([spearmanr(a[i], b[i]).statistic for i in idx])
    low, high = _interval(draws, ci)
    return point, low, high
