"""Consumer-space mapper：论文 1 的核心方法。

拟合目标不是状态距离，而是学生消费该状态的量：
    attention-output-aware: A_S @ V_target
    WO-aware: (A_S @ V_target @ W_O,q) 对每个 GQA query head

单参数目标 L_alpha = (1-α)||X M − Y||² + α||A X M − A Y||² 有闭式解：
把 X_aug = [sqrt(1-α) X ; sqrt(α) A X]、Y_aug 同理，再解 ridge 即可。
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from readkv.cache.cache import KVCache
from readkv.mapper.base import BaseMapper, ridge_solve


def consumer_solve(
    X: np.ndarray, Y: np.ndarray, A: np.ndarray, *, alpha: float = 1.0, lam: float = 1e-3
) -> np.ndarray:
    """对单个 (layer, head)：X,Y (T,d)，A (T,T) 学生注意力矩阵。"""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0,1]")
    x, y, attn = np.asarray(X, float), np.asarray(Y, float), np.asarray(A, float)
    wa, wb = np.sqrt(1.0 - alpha), np.sqrt(alpha)
    x_aug = np.concatenate([wa * x, wb * (attn @ x)], axis=0)
    y_aug = np.concatenate([wa * y, wb * (attn @ y)], axis=0)
    return ridge_solve(x_aug, y_aug, lam)


class ConsumerSpaceMapper(BaseMapper):
    """per-(layer, head) consumer-space mapper。

    attention_matrices: {(layer, head): array(T, T)}，由学生的真实 query 计算；
    alpha=0 退化为 affine；alpha=1 为 attention-output-aware。
    """

    name = "consumer_space"

    def __init__(self, *, alpha: float = 1.0, lam: float = 1e-3, channel: str = "V") -> None:
        self.alpha = alpha
        self.lam = lam
        self.channel = channel
        self.matrices: dict[tuple[int, str, int], np.ndarray] = {}

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "ConsumerSpaceMapper":
        attention = kwargs.get("attention_matrices", {})
        layer_map = kwargs.get("layer_map")
        for s_layer in student.layers:
            t_layer = layer_map(s_layer) if layer_map is not None else s_layer
            if t_layer not in teacher.layers:
                continue
            tk, tv = teacher.layer(t_layer)
            sk, sv = student.layer(s_layer)
            for head in range(min(tk.shape[0], sk.shape[0])):
                for ch in ("K", "V"):
                    if self.channel not in ("both", ch):
                        continue
                    x = (tk if ch == "K" else tv)[head]
                    y = (sk if ch == "K" else sv)[head]
                    attn = attention.get((s_layer, head))
                    if attn is None:
                        raise KeyError(f"missing student attention for layer {s_layer}, head {head}")
                    self.matrices[(s_layer, ch, head)] = consumer_solve(
                        x, y, attn, alpha=self.alpha, lam=self.lam
                    )
        return self

    def transform(self, teacher: KVCache) -> KVCache:
        out_k: dict[int, np.ndarray] = {}
        out_v: dict[int, np.ndarray] = {}
        for s_layer in teacher.layers:
            k, v = teacher.layer(s_layer)
            k_rows, v_rows = [], []
            for head in range(k.shape[0]):
                kmat = self.matrices.get((s_layer, "K", head))
                vmat = self.matrices.get((s_layer, "V", head))
                k_rows.append(k[head] @ kmat if kmat is not None else k[head])
                v_rows.append(v[head] @ vmat if vmat is not None else v[head])
            out_k[s_layer] = np.stack(k_rows)
            out_v[s_layer] = np.stack(v_rows)
        return KVCache(out_k, out_v, dict(teacher.metadata))

    def state_dict(self) -> Mapping[str, np.ndarray]:
        return {f"{layer}_{ch}_{head}": mat for (layer, ch, head), mat in self.matrices.items()}

    def load_state_dict(self, state: Mapping[str, np.ndarray]) -> None:
        self.matrices = {}
        for key, mat in state.items():
            layer, ch, head = key.split("_")
            self.matrices[(int(layer), ch, int(head))] = mat


class WOAwareMapper(ConsumerSpaceMapper):
    """WO-aware：把学生 o_proj 计入目标。

    调用方需为每个 KV head 提供 ``wo_matrices[(layer, head)]``（GQA 组内 query head
    的 W_O 堆叠/平均），并把 attention 与投影后的目标传入；数学核心仍是 consumer_solve。
    """

    name = "wo_aware"

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "WOAwareMapper":
        wo = kwargs.get("wo_matrices", {})
        if not wo:
            raise ValueError("WOAwareMapper requires wo_matrices")
        raise NotImplementedError(
            "WO-aware fitting requires runner-supplied per-query-head targets "
            "(A_S V_S W_O,q); wire them into consumer_solve before use"
        )


def alpha_grid(lam_values: tuple[float, ...] = (1e-4, 1e-3, 1e-2)) -> list[tuple[float, float]]:
    """映射目标 sweep：α∈{0,0.1,...,1} × λ ∈ 三个值 = 33 配置。"""
    return [(round(0.1 * i, 1), lam) for lam in lam_values for i in range(11)]
