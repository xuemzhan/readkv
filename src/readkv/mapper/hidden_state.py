"""hidden-state 映射探针（方向五）：映射 hidden state，再由学生自己的 W_K/W_V 投影。

K 落在学生寻址空间、V 落在学生读取空间，构造上满足一部分兼容性。
代价是每层多一次 K/V 投影，但跳过 attention 与 FFN。此路线成本与效果未验证，
先做小规模探针。
"""

from __future__ import annotations

from typing import Any

from readkv.cache.cache import KVCache
from readkv.mapper.base import BaseMapper, ridge_solve


class HiddenStateMapper(BaseMapper):
    name = "hidden_state"

    def __init__(self, lam: float = 1e-3) -> None:
        self.lam = lam
        self.matrices: dict[int, Any] = {}

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "HiddenStateMapper":  # pragma: no cover
        teacher_hidden = kwargs.get("teacher_hidden")
        student_hidden = kwargs.get("student_hidden")
        if teacher_hidden is None or student_hidden is None:
            raise ValueError("hidden-state probe requires captured hidden states, not only KV")
        for layer in student.layers:
            self.matrices[layer] = ridge_solve(
                teacher_hidden[layer], student_hidden[layer], self.lam
            )
        return self

    def transform(self, teacher: KVCache) -> KVCache:  # pragma: no cover
        raise NotImplementedError("apply mapped hidden states through student W_K/W_V and re-wrap as KVCache")
