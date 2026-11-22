"""Mapper 基类与闭式 ridge 求解器。

约定：每个 (layer, head) 拟合一个矩阵 M，使得 ``X @ M ≈ Y``，
X/Y 形状 (T, d_in) / (T, d_out)。keys 默认为 de-RoPE 内容空间。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from readkv.cache.cache import KVCache


def ridge_solve(X: np.ndarray, Y: np.ndarray, lam: float = 1e-3) -> np.ndarray:
    """闭式岭回归：min ||X M - Y||² + λ||M||²。"""
    x, y = np.asarray(X, float), np.asarray(Y, float)
    if x.ndim != 2 or y.ndim != 2 or x.shape[0] != y.shape[0]:
        raise ValueError("X and Y must be 2-D with the same number of rows")
    gram = x.T @ x + lam * np.eye(x.shape[1])
    return np.linalg.solve(gram, x.T @ y)


def affine_design(X: np.ndarray) -> np.ndarray:
    """为仿射映射增广常数列。"""
    return np.concatenate([np.asarray(X, float), np.ones((X.shape[0], 1))], axis=1)


class BaseMapper(ABC):
    """统一接口：fit 只吃校准缓存；transform 只产缓存。"""

    name = "base"

    @abstractmethod
    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "BaseMapper":
        raise NotImplementedError

    @abstractmethod
    def transform(self, teacher: KVCache) -> KVCache:
        raise NotImplementedError

    def save(self, path: Path | str) -> Path:
        payload = {k: np.asarray(v) for k, v in self.state_dict().items()}
        path = Path(path)
        np.savez(path, **payload)
        return path

    def state_dict(self) -> Mapping[str, np.ndarray]:
        raise NotImplementedError

    def load(self, path: Path | str) -> "BaseMapper":
        with np.load(Path(path), allow_pickle=False) as data:
            self.load_state_dict({k: data[k] for k in data.files})
        return self

    def load_state_dict(self, state: Mapping[str, np.ndarray]) -> None:
        raise NotImplementedError
