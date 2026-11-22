"""反事实功能保真指标（V2.0 方案 §5.1）。

统一输出口径：学生只比较固定候选 A/B 的条件分数

    g(C,q) = log P(A|C,q) − log P(B|C,q)

单 token 候选统一在同一生成位置提取 logits；多 token 自由回答须单独报告
corrected EM 与预定义序列概率评分，不能混合。

    D_self  = g(C_S(d_A),q) − g(C_S(d_B),q)
    D_trans = g(Ĉ_S(d_A),q) − g(Ĉ_S(d_B),q)
    E_CF    = |D_trans − D_self|
    归一化误差 = |D_trans − D_self| / (|D_self| + τ)

τ 只从验证集固定，不可按测试结果调整。

注意：仅降低 E_CF 不保证信息正确利用。若 D_self 近零，恒定输出也可能有低
E_CF。因此必须联合报告：双向成功率、方向一致率、Self 可评价子集覆盖率、
与无信息控制组的差距。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# 基础量
# ---------------------------------------------------------------------------

def g_score(logits_a: Sequence[float] | np.ndarray,
            logits_b: Sequence[float] | np.ndarray,
            *,
            candidate_a_index: int = 0,
            candidate_b_index: int = 1) -> float:
    """g(C,q) = log P(A|C,q) − log P(B|C,q)。

    单 token 候选在同一生成位置提取；对两选一 A/B，默认候选索引 0/1。
    """
    la = np.asarray(logits_a, dtype=float).reshape(-1)
    lb = np.asarray(logits_b, dtype=float).reshape(-1)
    if la.size < 2 or lb.size < 2:
        raise ValueError("g_score needs at least 2 candidate logits")

    def logp(x: np.ndarray, idx: int) -> float:
        m = float(x.max())
        return float(x[idx] - m - np.log(np.exp(x - m).sum()))

    return logp(la, candidate_a_index) - logp(lb, candidate_b_index)


def response_difference(g_a: float, g_b: float) -> float:
    """D = g(C(d_A),q) − g(C(d_B),q)。"""
    return float(g_a - g_b)


def counterfactual_error(d_trans: float, d_self: float) -> float:
    """E_CF = |D_trans − D_self|。"""
    return float(abs(d_trans - d_self))


def normalized_error(d_trans: float, d_self: float, tau: float) -> float:
    """归一化误差；τ > 0 且只能从验证集固定。"""
    if tau <= 0:
        raise ValueError("tau must be positive")
    return float(abs(d_trans - d_self) / (abs(d_self) + tau))


def direction_consistent(d_trans: float, d_self: float, *, tol: float = 0.0) -> bool:
    """方向一致率判定；tol 为可接受的零附近容差。"""
    if abs(d_self) <= tol:
        return False  # 原生无可辨识信息时，一致性不计入
    return bool(np.sign(d_trans) == np.sign(d_self))


# ---------------------------------------------------------------------------
# 聚合结果
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualSummary:
    """一组反事实对的聚合指标。所有字段只来自逐对记录。"""

    n_total: int = 0
    n_evaluable: int = 0
    e_cf_mean: float = 0.0
    e_cf_ci: tuple[float, float] = (0.0, 0.0)
    normalized_e_cf_mean: float = 0.0
    flip_consistency: float = 0.0
    dual_correct: float = 0.0
    coverage: float = 0.0
    info_gap: float | None = None
    self_gap: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_total": self.n_total,
            "n_evaluable": self.n_evaluable,
            "E_CF": {"mean": self.e_cf_mean, "ci": list(self.e_cf_ci)},
            "normalized_E_CF": self.normalized_e_cf_mean,
            "flip_consistency": self.flip_consistency,
            "dual_correct": self.dual_correct,
            "coverage": self.coverage,
            "info_gap": self.info_gap,
            "self_gap": self.self_gap,
            "detail": self.detail,
        }


@dataclass
class PairCFRecord:
    """单个反事实对的完整指标记录（对应附录 A schema 的指标列）。"""

    pair_id: str
    split: str
    slice_id: str
    cluster: str
    self_logits_A: Sequence[float]
    self_logits_B: Sequence[float]
    transfer_logits_A: Sequence[float]
    transfer_logits_B: Sequence[float]
    candidate_a_index: int = 0
    candidate_b_index: int = 1
    correct_A: str = "A"
    correct_B: str = "B"
    must_flip: bool = True
    control_logits: Mapping[str, tuple[Sequence[float], Sequence[float]]] | None = None
    tau: float = 1.0
    self_threshold: float = 1e-3

    def compute(self) -> dict[str, Any]:
        # g(C,q) 对每份缓存单独计算：log P(A|C,q) − log P(B|C,q)。
        # self_logits_A/B 分别是 C(d_A)/C(d_B) 的候选 logits 向量。
        g_self_A = _single_cache_g(self.self_logits_A, self.candidate_a_index, self.candidate_b_index)
        g_self_B = _single_cache_g(self.self_logits_B, self.candidate_a_index, self.candidate_b_index)
        g_trans_A = _single_cache_g(self.transfer_logits_A, self.candidate_a_index, self.candidate_b_index)
        g_trans_B = _single_cache_g(self.transfer_logits_B, self.candidate_a_index, self.candidate_b_index)

        d_self = response_difference(g_self_A, g_self_B)
        d_trans = response_difference(g_trans_A, g_trans_B)
        e_cf = counterfactual_error(d_trans, d_self)
        evaluable = abs(d_self) > self.self_threshold

        # 双向成功率：每份缓存是否选出正确候选
        self_A_correct = _pick(self.self_logits_A, self.correct_A)
        self_B_correct = _pick(self.self_logits_B, self.correct_B)
        trans_A_correct = _pick(self.transfer_logits_A, self.correct_A)
        trans_B_correct = _pick(self.transfer_logits_B, self.correct_B)

        out: dict[str, Any] = {
            "pair_id": self.pair_id,
            "split": self.split,
            "slice_id": self.slice_id,
            "cluster": self.cluster,
            "g_self_A": g_self_A,
            "g_self_B": g_self_B,
            "g_trans_A": g_trans_A,
            "g_trans_B": g_trans_B,
            "D_self": d_self,
            "D_trans": d_trans,
            "E_CF": e_cf,
            "normalized_E_CF": normalized_error(d_trans, d_self, self.tau),
            "evaluable": evaluable,
            "flip_consistency": direction_consistent(d_trans, d_self) if evaluable else None,
            "dual_correct": float(trans_A_correct and trans_B_correct),
            "self_dual_correct": float(self_A_correct and self_B_correct),
            "must_flip": self.must_flip,
            "sign_self": float(np.sign(d_self)),
            "sign_trans": float(np.sign(d_trans)),
        }

        # 信息归因：正确缓存 vs 控制缓存的 D 差
        if self.control_logits:
            gaps: dict[str, float] = {}
            for name, (ctrl_A, ctrl_B) in self.control_logits.items():
                g_c_a = _single_cache_g(ctrl_A, self.candidate_a_index, self.candidate_b_index)
                g_c_b = _single_cache_g(ctrl_B, self.candidate_a_index, self.candidate_b_index)
                gaps[name] = abs(response_difference(g_c_a, g_c_b) - d_self)
            out["control_E_CF"] = gaps
            out["info_gap"] = out["E_CF"] - float(np.mean(list(gaps.values()))) if gaps else None
        return out


def _single_cache_g(logits: Sequence[float], a_idx: int, b_idx: int) -> float:
    x = np.asarray(logits, dtype=float).reshape(-1)
    m = float(x.max())
    logp = x - m - np.log(np.exp(x - m).sum())
    return float(logp[a_idx] - logp[b_idx])


def _pick(logits: Sequence[float], correct: str) -> bool:
    x = np.asarray(logits, dtype=float).reshape(-1)
    idx = int(np.argmax(x))
    label = correct.strip().upper()
    if label.startswith("A") and label.startswith("B"):
        return True  # F5 非翻转负控：两个候选都正确
    expected = 0 if label.startswith("A") else 1
    return idx == expected


# ---------------------------------------------------------------------------
# 聚合
# ---------------------------------------------------------------------------

def summarize_cf(records: Sequence[Mapping[str, Any]], *, tau: float,
                 n_resamples: int = 10_000, seed: int = 0,
                 self_threshold: float = 1e-3) -> CounterfactualSummary:
    """从逐对记录聚合反事实指标；E_CF 的 CI 用簇级 paired bootstrap。"""
    from readkv.stats.bootstrap import cluster_bootstrap

    if not records:
        return CounterfactualSummary()

    e_cf = [float(r["E_CF"]) for r in records]
    clusters = [str(r.get("cluster", r["pair_id"])) for r in records]
    point, low, high = cluster_bootstrap(e_cf, clusters, n_resamples=n_resamples, seed=seed)

    evaluable = [r for r in records if r.get("evaluable", abs(float(r["D_self"])) > self_threshold)]
    flip_vals = [float(r["flip_consistency"]) for r in evaluable if r.get("flip_consistency") is not None]
    norm_vals = [float(r["normalized_E_CF"]) for r in records]
    dual_vals = [float(r["dual_correct"]) for r in records]
    info_gaps = [float(r["info_gap"]) for r in records if r.get("info_gap") is not None]

    # Self Gap：迁移 E_CF 相对于 Identity/原生残差的差（baseline 由调用方提供时更精确）
    self_gap = point - float(np.mean([r.get("identity_E_CF", 0.0) for r in records]))

    return CounterfactualSummary(
        n_total=len(records),
        n_evaluable=len(evaluable),
        e_cf_mean=point,
        e_cf_ci=(low, high),
        normalized_e_cf_mean=float(np.mean(norm_vals)),
        flip_consistency=float(np.mean(flip_vals)) if flip_vals else 0.0,
        dual_correct=float(np.mean(dual_vals)),
        coverage=len(evaluable) / len(records),
        info_gap=float(np.mean(info_gaps)) if info_gaps else None,
        self_gap=float(self_gap),
        detail={"tau": tau, "evaluable_threshold": self_threshold,
                "n_flip_evaluable": len(flip_vals)},
    )


def paired_ecf_difference(new_records: Sequence[Mapping[str, Any]],
                          baseline_records: Sequence[Mapping[str, Any]],
                          *, n_resamples: int = 10_000, seed: int = 0) -> dict[str, Any]:
    """主终点：新方法与最强行为基线的成对 E_CF 差异。

    返回 point / ci / 是否改善（CI 上界 < 0 视为稳健改善）。
    """
    from readkv.stats.bootstrap import cluster_bootstrap

    if len(new_records) != len(baseline_records):
        raise ValueError("new and baseline records must be paired 1:1")
    deltas = [float(n["E_CF"]) - float(b["E_CF"])
              for n, b in zip(new_records, baseline_records)]
    clusters = [str(n.get("cluster", n["pair_id"])) for n in new_records]
    point, low, high = cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=seed)
    return {
        "point": point,
        "ci": [low, high],
        "improved": high < 0.0,
        "n": len(deltas),
        "note": "paired E_CF difference (new - baseline); negative means new method is better",
    }
