"""报告辅助：把统计结果格式化为论文可直接引用的字符串。"""

from __future__ import annotations

from collections.abc import Sequence


def format_ci(point: float, low: float, high: float, digits: int = 3) -> str:
    return f"{point:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}]"


def direction_from_ci(low: float, high: float) -> str:
    if high < 0:
        return "degraded"
    if low > 0:
        return "gain"
    return "neutral"


def replacement_from_ci(low: float, epsilon: float) -> bool:
    return low > -epsilon


def summarize_rows(rows: Sequence[dict], key: str) -> dict[str, float]:
    values = [float(r[key]) for r in rows if key in r]
    if not values:
        return {}
    return {"n": len(values), "mean": sum(values) / len(values), "min": min(values), "max": max(values)}
