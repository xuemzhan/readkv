"""Key 侧目标：阶段 1 的 A–E。

C：score regression，min ||Q_S (M K̂^T) − Q_S K_S^T||²，对同一 KV head 的多个
GQA query head 堆叠；de-RoPE 内容空间有闭式解，带 RoPE 的版本用 SGD。
D：同目标但 target 来自另一文档；E：注意力分布 KL 的梯度版。
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from readkv.cache.cache import KVCache
from readkv.mapper.base import BaseMapper, affine_design, ridge_solve


def score_regression_solve(
    Q: np.ndarray, K_teacher: np.ndarray, K_student: np.ndarray, *, lam: float = 1e-3, weights: np.ndarray | None = None
) -> np.ndarray:
    """单个 KV head 的闭式 score 回归。

    Q: (T_q, d)，按 GQA 组堆叠 query head；K_teacher: (T, d)；
    K_student: (T, d)。返回 M: (d, d)，使得 K̂ = M @ K_teacher。

    返回 M 使用行向量约定：K̂ = K_teacher @ M，与 readkv 其他 mapper 一致。
    要求 teacher/student 的 head_dim 相同（Qwen3 各尺寸均为 128）；若不同，
    pre-softmax score 无法直接比较，须先做维度投影，这里显式报错而非静默出错。
    """
    q, kt, ks = np.asarray(Q, float), np.asarray(K_teacher, float), np.asarray(K_student, float)
    if q.shape[1] != kt.shape[1] or ks.shape[1] != kt.shape[1]:
        raise ValueError("score regression requires equal teacher/student head_dim")

    # min_M ||Q M K_T^T − Q K_S^T||² + λ||M||² 分两步闭式求解：
    #   Z = argmin_Z ||Q Z − Q K_S^T||² + λ||Z||²      (Z = M K_T^T, T_q×T)
    #   M = argmin_M ||M K_T^T − Z||² + λ||M||²
    target = q @ ks.T  # (T_q, T)
    if weights is not None:
        w = np.sqrt(np.asarray(weights, float))
        if w.shape != (target.shape[0],):
            raise ValueError("weights must have one value per query token")
        q, target = q * w[:, None], target * w[:, None]

    gram_q = q.T @ q + lam * np.eye(q.shape[1])          # (d, d)
    z = np.linalg.solve(gram_q, q.T @ target)            # (d, T)
    gram_k = kt.T @ kt + lam * np.eye(kt.shape[1])       # (d, d)
    # 返回行向量约定矩阵：K_T @ M ≈ K_S（与 readkv 其他 mapper 一致）
    return np.linalg.solve(gram_k, kt.T @ z.T)          # (d, d)


class ScoreRegressionKeyMapper(BaseMapper):
    name = "score_regression_key"

    def __init__(self, *, lam: float = 1e-3, attention_weighted: bool = False, shuffled: bool = False) -> None:
        self.lam = lam
        self.attention_weighted = attention_weighted
        self.shuffled = shuffled
        self.matrices: dict[tuple[int, int], np.ndarray] = {}

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "ScoreRegressionKeyMapper":
        queries = kwargs.get("query_states")  # {(layer, head): (T_q, d_out)}
        weights = kwargs.get("attention_weights", {})
        shuffled_target = kwargs.get("shuffled_student", student)
        if queries is None:
            raise ValueError("score regression requires student query states from calibration")
        layer_map = kwargs.get("layer_map")
        for s_layer in student.layers:
            t_layer = layer_map(s_layer) if layer_map is not None else s_layer
            if t_layer not in teacher.layers:
                continue
            tk, _ = teacher.layer(t_layer)
            sk, _ = shuffled_target.layer(s_layer)
            for head in range(min(tk.shape[0], sk.shape[0])):
                key = (s_layer, head)
                q = queries.get(key)
                if q is None:
                    raise KeyError(f"missing query states for {key}")
                w = weights.get(key) if self.attention_weighted else None
                self.matrices[key] = score_regression_solve(q, tk[head], sk[head], lam=self.lam, weights=w)
        return self

    def transform(self, teacher: KVCache) -> KVCache:
        out_k: dict[int, np.ndarray] = {}
        out_v: dict[int, np.ndarray] = {}
        for s_layer in teacher.layers:
            k, v = teacher.layer(s_layer)
            rows = []
            for head in range(k.shape[0]):
                mat = self.matrices.get((s_layer, head))
                rows.append(k[head] @ mat if mat is not None else k[head])
            out_k[s_layer] = np.stack(rows)
            out_v[s_layer] = v.copy()  # K-only：V 保持学生自己的
        return KVCache(out_k, out_v, dict(teacher.metadata))

    def state_dict(self) -> Mapping[str, np.ndarray]:
        return {f"{layer}_{head}": mat for (layer, head), mat in self.matrices.items()}

    def load_state_dict(self, state: Mapping[str, np.ndarray]) -> None:
        self.matrices = {}
        for key, mat in state.items():
            layer, head = key.split("_")
            self.matrices[(int(layer), int(head))] = mat


class AttentionKLKeyMapper(BaseMapper):  # pragma: no cover - 需要可微 attention
    """E：对注意力分布做 KL 的梯度版（需要可微学生 forward）。"""

    name = "attention_kl_key"

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "AttentionKLKeyMapper":
        raise NotImplementedError("KL objective needs a differentiable student attention callback")

    def transform(self, teacher: KVCache) -> KVCache:
        raise NotImplementedError
