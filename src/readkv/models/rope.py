"""RoPE 工具：映射 key 前 de-RoPE，注入学生后按学生位置 re-RoPE。

采用常见的“后半维旋转”约定；如实际 checkpoint 使用交错约定，需在此适配。
"""

from __future__ import annotations

import numpy as np


def rotate_half(x: np.ndarray) -> np.ndarray:
    """把向量后半段取负并换到前半段。输入最后一维为 head_dim。"""
    d = x.shape[-1]
    if d % 2:
        raise ValueError("head_dim must be even for rotate_half")
    half = d // 2
    first, second = x[..., :half], x[..., half:]
    return np.concatenate([-second, first], axis=-1)


def apply_rope(x: np.ndarray, cos: np.ndarray, sin: np.ndarray) -> np.ndarray:
    """x: (..., d)，cos/sin: (T, d)，按 token 维广播。"""
    return x * cos + rotate_half(x) * sin


def de_rope(x: np.ndarray, cos: np.ndarray, sin: np.ndarray) -> np.ndarray:
    """apply_rope 的逆变换（RoPE 为正交旋转，转置即逆）。"""
    return x * cos - rotate_half(x) * sin
