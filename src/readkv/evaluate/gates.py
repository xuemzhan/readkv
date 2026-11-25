"""三道门与双重判定（replacement / direction）。

H1：identity 控制；H2：CHG 的 CI 下界 > −ε；H3：teacher-content probe 是否有
正增益。所有判定只吃逐样本分数，由 stats/bootstrap 重算区间。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from readkv.stats.bootstrap import cluster_bootstrap, max_family_bootstrap, paired_bootstrap
from readkv.stats.reporting import direction_from_ci, replacement_from_ci


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"gate": self.name, "passed": self.passed, **self.detail}


def chg_from_scores(handoff: Sequence[float], self_scores: Sequence[float]) -> np.ndarray:
    a, b = np.asarray(handoff, float), np.asarray(self_scores, float)
    if a.shape != b.shape:
        raise ValueError("handoff and self scores must align")
    return a - b


def evaluate_h2(
    deltas: Sequence[float],
    *,
    epsilon: float = 0.02,
    n_resamples: int = 10_000,
    seed: int = 0,
    clusters: Sequence[str | int] | None = None,
) -> GateResult:
    """H2 replacement + direction 双重判定。"""
    point, low, high = (
        cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=seed)
        if clusters is not None
        else paired_bootstrap(deltas, n_resamples=n_resamples, seed=seed)
    )
    return GateResult(
        name="H2_replacement",
        passed=replacement_from_ci(low, epsilon),
        detail={
            "point": point,
            "ci": [low, high],
            "epsilon": epsilon,
            "replacement": replacement_from_ci(low, epsilon),
            "direction": direction_from_ci(low, high),
            "gain_gate": low > 0,
        },
    )


def evaluate_h3(
    config_deltas: Sequence[Sequence[float]],
    *,
    n_resamples: int = 10_000,
    seed: int = 0,
) -> GateResult:
    """H3：任一配置 CI 下界 > 0；另报 family-wise 最大值上界。"""
    if not config_deltas:
        raise ValueError("no probe configurations")
    cis = [paired_bootstrap(d, n_resamples=n_resamples, seed=seed + i) for i, d in enumerate(config_deltas)]
    any_gain = any(low > 0 for _, low, _ in cis)
    means = [point for point, _, _ in cis]
    observed_max, max_low, max_high = max_family_bootstrap(means, n_resamples=n_resamples, seed=seed)
    return GateResult(
        name="H3_exploitability",
        passed=any_gain,
        detail={
            "per_config": [{"point": p, "ci": [lo, hi]} for p, lo, hi in cis],
            "family_wise_max": {"observed": observed_max, "ci": [max_low, max_high]},
        },
    )


def compute_csg(true_doc: float, wrong_doc: float) -> float:
    """内容特异性增益：真文档的 LL/gold 减错文档的 LL/gold。"""
    return float(true_doc - wrong_doc)


def evaluate_h1(*args: Any, **kwargs: Any) -> GateResult:  # pragma: no cover
    """兼容入口；实际实现见 evaluate.validator.check_identity，避免循环导入。"""
    from readkv.evaluate.validator import check_identity

    return check_identity(*args, **kwargs)
