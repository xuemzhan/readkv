"""把预注册 decision rule 的机器可读 conditions 应用到观测事实。

V1：只做精确相等匹配（``field == value``）。
V2：在保持相等匹配的同时，支持显式比较算子，便于用 τ / Huber 阈值 / CI 边界
这类数值判据，而不必把阈值硬编码在 Python facts 里：

    conditions:
      ecf_improved: true                  # 精确相等
      ecf_point: { "$lt": 0 }             # 数值比较
      ci_upper: { "$lt": 0 }
      flip_consistency: { "$gte": 0.7 }

支持的算子：$eq/$ne/$lt/$lte/$gt/$gte/$in/$all。没有命中时返回 None，
由实验脚本如实写入 inconclusive，不做事后解释。
"""

from __future__ import annotations

from typing import Any, Mapping

_OPERATORS = {
    "$eq": lambda a, b: a == b,
    "$ne": lambda a, b: a != b,
    "$lt": lambda a, b: a < b,
    "$lte": lambda a, b: a <= b,
    "$gt": lambda a, b: a > b,
    "$gte": lambda a, b: a >= b,
    "$in": lambda a, b: a in b,
    "$all": lambda a, b: all(x in a for x in b),
}


def _match_condition(actual: Any, expected: Any) -> bool:
    if isinstance(expected, Mapping):
        for op, target in expected.items():
            fn = _OPERATORS.get(op)
            if fn is None:
                raise ValueError(f"unsupported decision operator: {op}")
            try:
                if not fn(actual, target):
                    return False
            except TypeError:
                return False
        return True
    return actual == expected


def match_decision(rules: list[Mapping[str, Any]], facts: Mapping[str, Any]) -> dict[str, Any] | None:
    for rule in rules:
        conditions = rule.get("conditions")
        if not isinstance(conditions, dict):
            continue
        if all(_match_condition(facts.get(key), expected) for key, expected in conditions.items()):
            return dict(rule)
    return None
