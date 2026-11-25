"""实现正确性门 E0（V2.0 方案 §5.2 / §8）。

先确证位置、RoPE、评测器与保存/加载正确，再研究反事实保真。
报指标：identity logit cosine、first-token KL、Self—Identity 差异、
cache round-trip。E0 判据是“测量误差上限显著低于待研究效应”；
V1 继承的 cosine ≥0.9998 仅作 identity 锚点一致性参考，不是 V2.0 主终点阈值。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from readkv.cache.cache import KVCache, CacheStore


@dataclass
class ImplementationGate:
    """E0 实现门结果。"""

    passed: bool
    min_logit_cosine: float
    max_first_token_kl: float
    round_trip_ok: bool
    identity_self_gap: float
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "min_logit_cosine": self.min_logit_cosine,
            "max_first_token_kl": self.max_first_token_kl,
            "round_trip_ok": self.round_trip_ok,
            "identity_self_gap": self.identity_self_gap,
            **self.detail,
        }


def logit_cosine(a: Sequence[float] | np.ndarray, b: Sequence[float] | np.ndarray) -> float:
    x, y = np.asarray(a, float).reshape(-1), np.asarray(b, float).reshape(-1)
    if x.shape != y.shape or x.size == 0:
        raise ValueError("logit vectors must align and be non-empty")
    denom = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.dot(x, y) / denom) if denom > 0 else 1.0


def first_token_kl(p: Sequence[float] | np.ndarray, q: Sequence[float] | np.ndarray) -> float:
    a, b = np.asarray(p, float).reshape(-1), np.asarray(q, float).reshape(-1)
    if a.shape != b.shape or a.size == 0:
        raise ValueError("distributions must align and be non-empty")
    pa, pb = a / a.sum(), b / b.sum()
    return float(np.sum(pa * np.log((pa + 1e-12) / (pb + 1e-12))))


def cache_round_trip(cache: KVCache, store: CacheStore, name: str) -> bool:
    """落盘→加载是否 bit-identical（方案 §9.3 自动测试 ①）。"""
    store.save(cache, name)
    loaded = store.load(name)
    if set(loaded.keys) != set(cache.keys):
        return False
    for layer in cache.layers:
        a, b = cache.layer(layer)
        c, d = loaded.layer(layer)
        if not (np.array_equal(a, c) and np.array_equal(b, d)):
            return False
    return True


def evaluate_implementation(
    *,
    identity_logits: Sequence[Sequence[float]] | None = None,
    self_logits: Sequence[Sequence[float]] | None = None,
    round_trip_ok: bool = True,
    cosine_reference: float = 0.9998,
    max_kl: float = 1e-3,
    effect_size_floor: float | None = None,
) -> ImplementationGate:
    """汇总 E0 指标。

    ``effect_size_floor`` 为待研究效应的下界估计；若提供，则要求测量误差上限
    （1 − min cosine 与 max KL 中较大者）显著低于该效应（严格小于）。
    """
    cosines: list[float] = []
    kls: list[float] = []
    gaps: list[float] = []
    if identity_logits is not None and self_logits is not None:
        if len(identity_logits) != len(self_logits):
            raise ValueError("identity and self logits must align")
        for ident, self_l in zip(identity_logits, self_logits):
            cosines.append(logit_cosine(ident, self_l))
            kls.append(first_token_kl(ident, self_l))
            gaps.append(abs(float(np.max(np.asarray(ident, float)) - np.max(np.asarray(self_l, float)))))

    min_cos = float(min(cosines)) if cosines else 1.0
    max_kl = float(max(kls)) if kls else 0.0
    gap = float(np.mean(gaps)) if gaps else 0.0

    # E0 核心：measurement error ceiling 显著低于待研究效应
    err_ceiling = max(1.0 - min_cos, max_kl)
    if effect_size_floor is not None:
        passed = bool(round_trip_ok and err_ceiling < effect_size_floor)
    else:
        # 未提供效应下界时，退回 V1 继承的 identity 锚点一致性参考
        passed = bool(round_trip_ok and min_cos >= cosine_reference and max_kl <= max_kl)

    return ImplementationGate(
        passed=passed,
        min_logit_cosine=min_cos,
        max_first_token_kl=max_kl,
        round_trip_ok=round_trip_ok,
        identity_self_gap=gap,
        detail={
            "n_samples": len(cosines),
            "measurement_error_ceiling": err_ceiling,
            "effect_size_floor": effect_size_floor,
            "n_cosines_below_reference": sum(c < cosine_reference for c in cosines),
            "cosine_reference": cosine_reference,
            "note": "E0 主判据为测量误差上限显著低于待研究效应；cosine≥0.9998 仅为 V1 继承参考",
        },
    )
