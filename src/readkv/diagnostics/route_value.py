"""Routing / Consumption 机制诊断（V2.0 方案 §6）。

局部注意力扰动分解（固定 Q、固定位置、当前层的代数恒等式）：

    Ô − O_S = (Â − A_S) V_S W_O^S  +  Â (V̂ − V_S) W_O^S
              └──── Routing ────┘     └──── Consumption ────┘

注意：这不是全模型任务损失的加性因果分解；前层注入会改变后层 Q 与非线性状态。
A/B 层只是关联，C 层（Oracle 状态移植）才能帮助识别必要/充分的局部影响。
Oracle 依赖学生原生 Prefill，只能发生在离线诊断阶段，不得进入推理路径。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from readkv.cache.cache import KVCache


# ---------------------------------------------------------------------------
# 局部注意力分解
# ---------------------------------------------------------------------------

@dataclass
class AttentionDecomposition:
    """单个 (layer, head) 的 Routing / Consumption 分解。"""

    layer: int
    head: int
    routing_norm: float
    consumption_norm: float
    total_norm: float
    residual_norm: float  # 数值残差校验：‖(routing+consumption) − total‖
    routing_detail: np.ndarray | None = None
    consumption_detail: np.ndarray | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "head": self.head,
            "routing_norm": self.routing_norm,
            "consumption_norm": self.consumption_norm,
            "total_norm": self.total_norm,
            "residual_norm": self.residual_norm,
            "share_routing": (self.routing_norm / self.total_norm) if self.total_norm > 0 else 0.0,
            "share_consumption": (self.consumption_norm / self.total_norm) if self.total_norm > 0 else 0.0,
        }


def softmax_rows(scores: np.ndarray) -> np.ndarray:
    x = np.asarray(scores, float)
    m = x.max(axis=-1, keepdims=True)
    e = np.exp(x - m)
    return e / e.sum(axis=-1, keepdims=True)


def decompose_attention(
    *,
    query: np.ndarray,
    k_student: np.ndarray,
    v_student: np.ndarray,
    k_mapped: np.ndarray,
    v_mapped: np.ndarray,
    w_o: np.ndarray | None = None,
    layer: int = 0,
    head: int = 0,
    store_detail: bool = False,
) -> AttentionDecomposition:
    """对一个 (layer, head) 计算 Routing / Consumption 分解。

    query: (T_q, d)，固定接收端 Query（训练期可为 Oracle，推理期不可读）。
    k_*, v_*: (T, d) 单头 K/V。w_o: (d, d_o) 输出投影；None 时取单位阵。
    """
    q = np.asarray(query, float)
    ks, vs = np.asarray(k_student, float), np.asarray(v_student, float)
    km, vm = np.asarray(k_mapped, float), np.asarray(v_mapped, float)
    scale = float(np.sqrt(q.shape[-1]))
    if q.shape[1] != ks.shape[1]:
        raise ValueError("query head_dim must match K/V head_dim")

    a_s = softmax_rows(q @ ks.T / scale)
    a_hat = softmax_rows(q @ km.T / scale)
    wo = np.eye(ks.shape[1]) if w_o is None else np.asarray(w_o, float)

    routing = (a_hat - a_s) @ vs @ wo
    consumption = a_hat @ (vm - vs) @ wo
    total = (a_hat @ vm - a_s @ vs) @ wo
    residual = float(np.linalg.norm(routing + consumption - total))

    return AttentionDecomposition(
        layer=layer,
        head=head,
        routing_norm=float(np.linalg.norm(routing)),
        consumption_norm=float(np.linalg.norm(consumption)),
        total_norm=float(np.linalg.norm(total)),
        residual_norm=residual,
        routing_detail=routing if store_detail else None,
        consumption_detail=consumption if store_detail else None,
    )


def decompose_cache(
    *,
    queries: Mapping[tuple[int, int], np.ndarray],
    student: KVCache,
    mapped: KVCache,
    w_o: Mapping[tuple[int, int], np.ndarray] | None = None,
) -> list[AttentionDecomposition]:
    """对整个缓存逐层头分解；queries 必须覆盖所有 mapped 层头。"""
    out: list[AttentionDecomposition] = []
    for layer in mapped.layers:
        km, vm = mapped.layer(layer)
        ks, vs = student.layer(layer)
        for head in range(km.shape[0]):
            key = (layer, head)
            q = queries.get(key)
            if q is None:
                continue
            wo = None if w_o is None else w_o.get(key)
            out.append(decompose_attention(
                query=q,
                k_student=ks[head], v_student=vs[head],
                k_mapped=km[head], v_mapped=vm[head],
                w_o=wo, layer=layer, head=head,
            ))
    return out


# ---------------------------------------------------------------------------
# 四臂
# ---------------------------------------------------------------------------

def build_four_arms(*, student: KVCache, mapped: KVCache) -> dict[str, KVCache]:
    """Self / K-only / V-only / Joint 四臂（方案 §6.2）。

    K-only / V-only 是非可部署 Oracle：另一半来自学生自身 Prefill。
    Joint 是唯一严格零重 Prefill 主路径。
    """
    ks, vs = student.keys, student.values
    km, vm = mapped.keys, mapped.values
    if set(ks) != set(km):
        raise ValueError("student and mapped caches must cover the same layers")

    def make(k: dict[int, np.ndarray], v: dict[int, np.ndarray], arm: str) -> KVCache:
        return KVCache({i: a.copy() for i, a in k.items()},
                       {i: a.copy() for i, a in v.items()},
                       {"arm": arm, "deployable": arm == "joint"})

    return {
        "self": make(ks, vs, "self"),
        "k_only": make(km, vs, "k_only"),
        "v_only": make(ks, vm, "v_only"),
        "joint": make(km, vm, "joint"),
    }


# ---------------------------------------------------------------------------
# Oracle 干预（C 层因果诊断）
# ---------------------------------------------------------------------------

def oracle_transplant(
    *,
    student: KVCache,
    mapped: KVCache,
    layer: int,
    head: int,
    token: int | None = None,
    channel: str = "both",
    ecf_fn: Callable[[KVCache], float] | None = None,
) -> tuple[KVCache, float | None]:
    """把选定层/头/Token 的学生原生状态移植回 mapped cache，观察 E_CF 改变。

    ``ecf_fn`` 接收修复后的 cache 并返回 E_CF；None 时只返回修复后的 cache。
    注意：本函数依赖学生原生 Prefill（C_S(d)），只能离线诊断使用。
    """
    if layer not in mapped.layers or layer not in student.layers:
        raise ValueError(f"layer {layer} not present in both caches")
    if channel not in ("K", "V", "both"):
        raise ValueError("channel must be K, V or both")

    fixed = mapped.clone()
    sk, sv = student.layer(layer)
    mk, mv = fixed.layer(layer)
    if head >= mk.shape[0] or head >= sk.shape[0]:
        raise ValueError(f"head {head} out of range")

    if token is None:
        if channel in ("K", "both"):
            mk[head] = sk[head].copy()
        if channel in ("V", "both"):
            mv[head] = sv[head].copy()
    else:
        if token >= mk.shape[1]:
            raise ValueError(f"token {token} out of range")
        if channel in ("K", "both"):
            mk[head, token] = sk[head, token].copy()
        if channel in ("V", "both"):
            mv[head, token] = sv[head, token].copy()

    return fixed, (ecf_fn(fixed) if ecf_fn is not None else None)


def rank_units_by_repair(
    *,
    student: KVCache,
    mapped: KVCache,
    baseline_ecf: float,
    ecf_fn: Callable[[KVCache], float],
    channels: Sequence[str] = ("K", "V", "both"),
    tokens: Sequence[int | None] = (None,),
) -> list[dict[str, Any]]:
    """对每个层/头记录“修复该单元后 E_CF 改善多少”，再用独立文档验证稳定性。

    返回按改善量降序排列的候选单元（仅训练/验证集使用，不得用封存标签）。
    """
    rows: list[dict[str, Any]] = []
    for layer in mapped.layers:
        km, _ = mapped.layer(layer)
        for head in range(km.shape[0]):
            for channel in channels:
                for token in tokens:
                    fixed, ecf = oracle_transplant(
                        student=student, mapped=mapped,
                        layer=layer, head=head, token=token,
                        channel=channel, ecf_fn=ecf_fn,
                    )
                    if ecf is None:
                        continue
                    rows.append({
                        "layer": layer,
                        "head": head,
                        "channel": channel,
                        "token": token,
                        "ecf_before": baseline_ecf,
                        "ecf_after": float(ecf),
                        "improvement": float(baseline_ecf - ecf),
                        "repair_ok": ecf < baseline_ecf,
                    })
    rows.sort(key=lambda r: r["improvement"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# 对称 Key 前置实验（方案 §6.4）
# ---------------------------------------------------------------------------

def key_objective_matrix(
    *,
    teacher_k: np.ndarray,
    student_k: np.ndarray,
    query: np.ndarray | None = None,
    attention: np.ndarray | None = None,
    lam: float = 1e-3,
) -> dict[str, np.ndarray]:
    """Key 侧四类目标矩阵：A ridge / B attention-mass 加权 / C score / D ranking 近似。

    返回 ``{name: M}``，使用行向量约定 K̂ = K_teacher @ M。
    V 侧暂固定 consumer-space Mapper；GQA 下 query 应按 KV head 聚合。
    """
    from readkv.mapper.base import ridge_solve
    from readkv.mapper.key_objectives import score_regression_solve

    kt, ks = np.asarray(teacher_k, float), np.asarray(student_k, float)
    out: dict[str, np.ndarray] = {}
    out["A_ridge"] = ridge_solve(kt, ks, lam)
    if attention is not None:
        w = np.asarray(attention, float).sum(axis=0)  # (T,)
        w = np.sqrt(np.maximum(w, 1e-12))
        out["B_attention_weighted"] = ridge_solve(kt * w[:, None], ks * w[:, None], lam)
    if query is not None:
        out["C_score"] = score_regression_solve(query, kt, ks, lam=lam)
        if attention is not None:
            weights = np.asarray(attention, float).sum(axis=0)
            out["C_score_weighted"] = score_regression_solve(query, kt, ks, lam=lam, weights=weights)
        # D: ranking/attention KL 目标需要可微学生 forward，GPU 端由 AttentionKLKeyMapper 实现
    return out
