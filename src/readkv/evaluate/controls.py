"""内容对照：错文档、矩匹配随机 K、零缓存、破坏 K-V 对应。

同序置换 K 与 V 不是内容对照（attention 对共同重排不变），只作不变性检查。
"""

from __future__ import annotations

import numpy as np

from readkv.cache.cache import KVCache

CONTROL_KINDS = (
    "wrong_document",
    "random_gaussian",
    "zero",
    "shuffle_k",
    "shuffle_v",
    "same_permutation",
)


def moment_matched_random(reference: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """按每层每头均值/方差生成随机张量（论文 1 的随机 Gaussian key）。"""
    mean = reference.mean(axis=1, keepdims=True)
    std = reference.std(axis=1, keepdims=True)
    return mean + std * rng.standard_normal(reference.shape).astype(reference.dtype)


def build_control(cache: KVCache, kind: str, *, seed: int = 0, other: KVCache | None = None) -> KVCache:
    if kind not in CONTROL_KINDS:
        raise ValueError(f"unknown control kind: {kind}")
    rng = np.random.default_rng(seed)
    keys = {i: a.copy() for i, a in cache.keys.items()}
    values = {i: a.copy() for i, a in cache.values.items()}

    if kind == "wrong_document":
        if other is None:
            raise ValueError("wrong_document needs another document's cache")
        if set(other.layers) != set(cache.layers):
            raise ValueError("control cache layer set must match")
        keys = {i: other.keys[i].copy() for i in cache.layers}
        values = {i: other.values[i].copy() for i in cache.layers}
    elif kind == "random_gaussian":
        keys = {i: moment_matched_random(a, rng) for i, a in keys.items()}
    elif kind == "zero":
        keys = {i: np.zeros_like(a) for i, a in keys.items()}
        values = {i: np.zeros_like(a) for i, a in values.items()}
    elif kind == "shuffle_k":
        perm = rng.permutation(cache.seq_len)
        keys = {i: a[:, perm, :] for i, a in keys.items()}
    elif kind == "shuffle_v":
        perm = rng.permutation(cache.seq_len)
        values = {i: a[:, perm, :] for i, a in values.items()}
    elif kind == "same_permutation":
        perm = rng.permutation(cache.seq_len)
        keys = {i: a[:, perm, :] for i, a in keys.items()}
        values = {i: a[:, perm, :] for i, a in values.items()}

    metadata = dict(cache.metadata)
    metadata["control"] = kind
    return KVCache(keys, values, metadata)
