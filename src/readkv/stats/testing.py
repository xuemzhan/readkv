"""显著性检验封装（仅用于论文 1 约定的配对 Wilcoxon）。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.stats import wilcoxon


def wilcoxon_signed_rank(
    a: Sequence[float], b: Sequence[float], *, alpha: float = 0.05
) -> dict[str, float | bool]:
    """配对符号秩检验；返回统计量、p 值、是否在 alpha 下显著。"""
    x, y = np.asarray(a, float), np.asarray(b, float)
    if x.shape != y.shape:
        raise ValueError("paired samples must have the same shape")
    result = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
    p = float(result.pvalue)
    return {"statistic": float(result.statistic), "p_value": p, "significant": p < alpha}
