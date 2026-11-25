"""不相交校准/评测切分与校准预算阶梯。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

T = TypeVar("T")


def disjoint_split(
    items: Sequence[T], *, calibration: int, evaluation: int, seed: int = 0, cluster_of=lambda x: "default"
) -> tuple[list[T], list[T]]:
    """按 cluster 分组后切分，避免同一文档/实体同时进入校准与评测。"""
    import random

    rng = random.Random(seed)
    by_cluster: dict[str, list[T]] = {}
    for item in items:
        by_cluster.setdefault(cluster_of(item), []).append(item)
    keys = sorted(by_cluster)
    rng.shuffle(keys)
    cal: list[T] = []
    ev: list[T] = []
    for key in keys:
        group = by_cluster[key]
        if len(cal) < calibration:
            cal.extend(group)
        elif len(ev) < evaluation:
            ev.extend(group)
        if len(cal) >= calibration and len(ev) >= evaluation:
            break
    if len(cal) < calibration or len(ev) < evaluation:
        raise ValueError("not enough clusters for the requested split")
    return cal[:calibration], ev[:evaluation]


def make_calibration_budget(items: Sequence[T], budget: int, *, seed: int = 0) -> list[T]:
    """校准阶梯 c∈{10,30,60,100,200,500}：从校准池内不放回抽样。"""
    import random

    if budget > len(items):
        raise ValueError(f"budget {budget} exceeds calibration pool {len(items)}")
    return random.Random(seed).sample(list(items), budget)
