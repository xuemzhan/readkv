"""教师层 -> 学生层映射：identity / proportional / offset / permutation。

论文 1 的“修复后打乱层映射”只做过 1.7B→0.6B；MATCHA 式多对多带状映射
仍待补，接口在此预留。
"""

from __future__ import annotations

from typing import Literal

import numpy as np


class LayerMap:
    def __init__(
        self,
        n_student_layers: int,
        n_teacher_layers: int,
        *,
        kind: Literal["identity", "proportional", "offset", "permutation", "learned"] = "proportional",
        offset: int = 0,
        permutation: list[int] | np.ndarray | None = None,
    ) -> None:
        self.ns = n_student_layers
        self.nt = n_teacher_layers
        if kind == "identity" and n_student_layers != n_teacher_layers:
            raise ValueError("identity layer map requires equal depth")
        self.kind = kind
        self.offset = offset
        self.permutation = None if permutation is None else np.asarray(permutation, dtype=int)

    def source_for(self, student_layer: int) -> int:
        if not 0 <= student_layer < self.ns:
            raise IndexError(student_layer)
        if self.kind == "identity":
            return student_layer
        if self.kind == "proportional":
            return min(self.nt - 1, round(student_layer * self.nt / self.ns))
        if self.kind == "offset":
            idx = student_layer + self.offset
            if not 0 <= idx < self.nt:
                raise IndexError(f"offset maps layer {student_layer} to {idx}")
            return idx
        if self.kind == "permutation":
            if self.permutation is None or len(self.permutation) < self.ns:
                raise ValueError("permutation must cover all student layers")
            return int(self.permutation[student_layer])
        raise NotImplementedError("learned layer maps (MATCHA-style) are not implemented yet")

    def __call__(self, student_layer: int) -> int:
        return self.source_for(student_layer)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "n_student_layers": self.ns,
            "n_teacher_layers": self.nt,
            "offset": self.offset,
            "permutation": None if self.permutation is None else self.permutation.tolist(),
        }
