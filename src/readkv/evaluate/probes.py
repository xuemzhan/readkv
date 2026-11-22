"""Teacher-content probes 与路由引导选择性重算（成本核算必须诚实）。

probe 是测量工具而非可部署系统：它们需要学生的 own cache 作为基底。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from readkv.cache.cache import KVCache


def _blend(native: np.ndarray, translated: np.ndarray, alpha: float) -> np.ndarray:
    return alpha * translated + (1.0 - alpha) * native


def fraction_probe(native: KVCache, translated: KVCache, alpha: float) -> KVCache:
    """α·teacher-derived + (1−α)·native，α∈{0.25,0.5,0.75}。"""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0,1]")
    if set(native.layers) != set(translated.layers):
        raise ValueError("native and translated caches must share layer sets")
    keys, values = {}, {}
    for layer in native.layers:
        nk, nv = native.layer(layer)
        tk, tv = translated.layer(layer)
        keys[layer] = _blend(nk, tk, alpha)
        values[layer] = _blend(nv, tv, alpha)
    meta = dict(native.metadata)
    meta["probe"] = f"fraction_{alpha}"
    return KVCache(keys, values, meta)


def _third(layer: int, n_layers: int) -> str:
    return "bottom" if layer < n_layers / 3 else "middle" if layer < 2 * n_layers / 3 else "top"


def window_probe(native: KVCache, translated: KVCache, window: str) -> KVCache:
    """替换底/中/顶三分之一层；top third 在论文 2 中为 neutral。"""
    if window not in ("bottom_third", "middle_third", "top_third"):
        raise ValueError("window must be bottom_third / middle_third / top_third")
    want = window.split("_")[0]
    keys = {}
    values = {}
    n = native.n_layers
    for idx, layer in enumerate(native.layers):
        use_translated = _third(idx, n) == want
        src = translated if use_translated else native
        keys[layer] = src.keys[layer].copy()
        values[layer] = src.values[layer].copy()
    meta = dict(native.metadata)
    meta["probe"] = f"window_{window}"
    return KVCache(keys, values, meta)


def octant_probe(native: KVCache, translated: KVCache, octant: int) -> KVCache:
    """八层窗中选一个替换；探索性分析，不对正增益做事后选择。"""
    if not 0 <= octant <= 7:
        raise ValueError("octant must be 0..7")
    n = native.n_layers
    lo = int(octant * n / 8)
    hi = int((octant + 1) * n / 8)
    keys, values = {}, {}
    for idx, layer in enumerate(native.layers):
        src = translated if lo <= idx < hi else native
        keys[layer] = src.keys[layer].copy()
        values[layer] = src.values[layer].copy()
    meta = dict(native.metadata)
    meta["probe"] = f"octant_{octant}"
    return KVCache(keys, values, meta)


def selective_recompute_plan(
    routing_tv: Sequence[float], top1_agreement: Sequence[float], budget: int
) -> list[int]:
    """按 routing 发散度（TV 大、top-1 低）排序，取前 budget 个层/位置。"""
    if budget < 0 or budget > len(routing_tv):
        raise ValueError("budget out of range")
    tv, top1 = np.asarray(routing_tv, float), np.asarray(top1_agreement, float)
    score = tv + (1.0 - top1)
    return np.argsort(-score)[:budget].tolist()


def estimate_recompute_cost(n_recomputed_layers: int, n_student_layers: int) -> dict[str, float]:
    """重算第 l 层 K 需要该层输入 hidden state：要么重算前面所有层，
    要么先映射 hidden state。此代价必须计入总成本，否则“省 prefill”站不住。

    最坏情况：每次重算都从 token 0 重新跑到目标层，代价 = 层数 × n_recomputed_layers。
    平均情况：目标层均匀分布在 0..n-1，代价 = 层数 × (n+1)/2。
    """
    worst = n_recomputed_layers * n_student_layers
    average = n_recomputed_layers * (n_student_layers + 1) / 2
    return {
        "naive_worst_case_layers": float(worst),
        "naive_average_layers": float(average),
        "with_hidden_state_mapping": float(n_recomputed_layers),
        "fraction_of_full_prefill": float(worst / n_student_layers),
    }
