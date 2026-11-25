"""Representation-space 基线：per-head / per-layer ridge、affine。

论文 1/2 的主要基线；注意 raw representation error 与任务 EM 同运行内正相关，
这些 mapper 只作为对照，不是默认方法。
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from readkv.cache.cache import KVCache
from readkv.mapper.base import BaseMapper, affine_design, ridge_solve


class _PerHeadLinearMapper(BaseMapper):
    def __init__(self, *, lam: float = 1e-3, affine: bool = False, channel: str = "both") -> None:
        self.lam = lam
        self.affine = affine
        self.channel = channel
        self.matrices: dict[tuple[int, str, int], np.ndarray] = {}

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "_PerHeadLinearMapper":
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
                    x = affine_design(x) if self.affine else x
                    self.matrices[(s_layer, ch, head)] = ridge_solve(x, y, self.lam)
        return self

    def transform(self, teacher: KVCache) -> KVCache:
        out_k: dict[int, np.ndarray] = {}
        out_v: dict[int, np.ndarray] = {}
        # transform 用与 fit 相同的层索引；调用方通过 layer_map 先选好 teacher 层。
        for s_layer in teacher.layers:
            heads = []
            for head in range(teacher.layer(s_layer)[0].shape[0]):
                heads.append(head)
            k_rows, v_rows = [], []
            for head in heads:
                tmat = self.matrices.get((s_layer, "K", head))
                vmat = self.matrices.get((s_layer, "V", head))
                k, v = teacher.layer(s_layer)
                if tmat is not None:
                    x = affine_design(k[head]) if self.affine else k[head]
                    mapped = x @ tmat
                    k_rows.append(mapped)
                else:
                    k_rows.append(k[head])
                if vmat is not None:
                    x = affine_design(v[head]) if self.affine else v[head]
                    mapped = x @ vmat
                    v_rows.append(mapped)
                else:
                    v_rows.append(v[head])
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


class RidgeMapper(_PerHeadLinearMapper):
    name = "ridge_per_head"

    def __init__(self, lam: float = 1e-3, channel: str = "both") -> None:
        super().__init__(lam=lam, affine=False, channel=channel)


class AffineMapper(_PerHeadLinearMapper):
    name = "affine_per_head"

    def __init__(self, lam: float = 1e-3, channel: str = "both") -> None:
        super().__init__(lam=lam, affine=True, channel=channel)


class TaskAwareMapper(AffineMapper):  # pragma: no cover - 需要下游 loss 回调
    """论文 2 的 task-aware 族：用校准答案监督替代纯状态重构。"""

    name = "task_aware"

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "TaskAwareMapper":
        raise NotImplementedError("provide a downstream loss callback from the experiment runner")


class RATMapper(AffineMapper):  # pragma: no cover - 需要两模型投影与词表对齐
    """Residual-anchored translator；需要 W_K/W_V 与共享词表对齐。"""

    name = "rat"

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "RATMapper":
        raise NotImplementedError("RAT requires teacher/student projections and vocabulary alignment")


class TopKRidgeMapper(RidgeMapper):  # pragma: no cover - 需要源层选择
    """Heo-style top-k 源层选择（averaged / concatenated 两型）。"""

    name = "topk_ridge"

    def __init__(self, k: int = 3, mode: str = "averaged", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.k = k
        self.mode = mode

    def transform(self, teacher: KVCache) -> KVCache:
        raise NotImplementedError("select and combine teacher layers before calling the per-head solver")
