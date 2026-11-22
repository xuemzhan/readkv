"""诊断量：routing、消费空间误差、R²、PPL、成本估算。

这些量用于解释与归因，不替代任务指标。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def routing_tv(p: np.ndarray, q: np.ndarray) -> float:
    """注意力分布的总变差距离。"""
    a, b = np.asarray(p, float), np.asarray(q, float)
    return float(0.5 * np.abs(a - b).sum())


def top1_agreement(p: np.ndarray, q: np.ndarray) -> float:
    return float(np.mean(np.argmax(np.asarray(p), axis=-1) == np.argmax(np.asarray(q), axis=-1)))


def attention_cosine(p: np.ndarray, q: np.ndarray) -> float:
    a, b = np.asarray(p, float).ravel(), np.asarray(q, float).ravel()
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 1.0


def relative_frobenius_error(mapped: np.ndarray, target: np.ndarray) -> float:
    x, y = np.asarray(mapped, float), np.asarray(target, float)
    denom = np.linalg.norm(y)
    return float(np.linalg.norm(x - y) / denom) if denom else float(np.linalg.norm(x - y))


def r2_score(predicted: np.ndarray, target: np.ndarray) -> float:
    y, yhat = np.asarray(target, float), np.asarray(predicted, float)
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot else 0.0


def suffix_perplexity(negative_log_likelihoods: Sequence[float]) -> float:
    """平均 NLL 的指数；只作流畅度代理，不代表任务质量。"""
    arr = np.asarray(negative_log_likelihoods, float)
    if arr.size == 0:
        raise ValueError("empty NLL sequence")
    return float(np.exp(np.clip(arr.mean(), -700, 700)))


def mapper_cost(config: Mapping[str, int], *, bytes_per_token: int) -> dict[str, float]:
    """传输 mapper 与传输缓存的字节交叉点（论文 1 附录 B，启发式）。"""
    ns, heads, dim = config["n_layers"], config["n_kv_heads"], config["head_dim"]
    n_params = ns * heads * (dim * dim + dim)
    mapper_bytes = n_params * 4  # fp32
    return {"mapper_params": float(n_params), "mapper_bytes": float(mapper_bytes), "crossover_tokens": mapper_bytes / bytes_per_token}
