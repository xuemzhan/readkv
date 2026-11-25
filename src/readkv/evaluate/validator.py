"""H1 identity 控制的 validator：logit cosine 与最低阈值。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from readkv.evaluate.gates import GateResult


def logit_cosine(a: np.ndarray, b: np.ndarray) -> float:
    x, y = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    if x.shape != y.shape:
        raise ValueError("logit vectors must have the same shape")
    denom = np.linalg.norm(x) * np.linalg.norm(y)
    if denom == 0:
        return 1.0 if np.array_equal(x, y) else 0.0
    return float(np.dot(x, y) / denom)


def check_identity(cosines: Sequence[float], *, threshold: float = 0.9998) -> GateResult:
    """每个评测样本都必须过阈值；同时报告最小值以便复现。"""
    values = np.asarray(cosines, float)
    if values.size == 0:
        raise ValueError("no identity samples")
    passed = bool(np.all(values >= threshold))
    return GateResult(
        name="H1_identity",
        passed=passed,
        detail={
            "threshold": threshold,
            "observed_min": float(values.min()),
            "observed_mean": float(values.mean()),
            "n": int(values.size),
        },
    )
