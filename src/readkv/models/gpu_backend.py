"""真实 GPU 后端：实现 evaluate/cf_pipeline.py 所需的 MockBackend 契约子集。

与 MockBackend 完全相同的接口语义（pair_side_cache / inject / candidate_logits /
cache），但所有缓存来自真实 Qwen3 前向。教师与学生各自独立 prefill，绝不篡改
缓存字节；g(C,q) 用真正的 next-token 候选 logits（不含 mock 的正确性偏置）。
Mock 数字不进入任何真实 run。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import torch

from readkv.cache.cache import KVCache
from readkv.models.hooks import capture_teacher_cache, inject_and_generate


class GPUBackend:
    name = "gpu"

    def __init__(self, teacher: Any, student: Any, tok_teacher: Any, tok_student: Any,
                 *, device: str = "cuda", dtype: str = "bfloat16", kernel: str = "sdpa",
                 layer_map: Any = None) -> None:
        self.teacher, self.student = teacher, student
        self.tok_t, self.tok_s = tok_teacher, tok_student
        self.device = device
        self.dtype = dtype
        self.kernel = kernel
        self.layer_map = layer_map
        self.n_captures = 0
        self.n_injections = 0

    def _tokens(self, text: str, role: str) -> list[int]:
        tok = self.tok_t if role == "teacher" else self.tok_s
        return tok(text, add_special_tokens=False).input_ids

    def cache(self, doc: Mapping[str, Any], role: str) -> KVCache:
        if role not in ("teacher", "student"):
            raise ValueError("role must be teacher or student")
        model = self.teacher if role == "teacher" else self.student
        toks = self._tokens(str(doc.get("text", "")), role)
        t = torch.tensor(toks, device=self.device, dtype=torch.long)
        lm = self.layer_map if role == "teacher" else None
        self.n_captures += 1
        return capture_teacher_cache(model, t, lm, attn_implementation=self.kernel)

    def pair_side_cache(self, pair: Mapping[str, Any], side: str, role: str) -> KVCache:
        key = "context_A" if side == "A" else "context_B"
        doc = {"doc_id": f"{pair['pair_id']}-{side}", "text": pair[key],
               "context": pair[key], "side": side}
        return self.cache(doc, role)

    def inject(self, cache: KVCache) -> KVCache:
        """identity 注入锚点：内容空间缓存原样拷贝（仅标记），不伪造字节。"""
        c = cache.clone()
        c.metadata = dict(c.metadata)
        c.metadata["injected"] = True
        return c

    def inject_counterfactual_distortion(self, cache: KVCache, **kwargs: Any) -> KVCache:
        raise NotImplementedError("GPU backend does not inject synthetic distortion")

    def candidate_logits(self, cache: KVCache, query_doc: Mapping[str, Any],
                         *, candidates: Sequence[str] | None = None,
                         correct_index: int | None = None,
                         **kwargs: Any) -> np.ndarray:
        """(2,) 候选 logits；索引 0/1 对应 candidates[0]/[1]，无正确性偏置。"""
        cands = tuple(candidates or ("A", "B"))
        if len(cands) < 2:
            raise ValueError("candidate_logits needs at least two candidates")
        q_ids = self._tokens(str(query_doc.get("query", query_doc.get("text", ""))), "student")
        q_t = torch.tensor(q_ids, device=self.device, dtype=torch.long)
        self.n_injections += 1
        res = inject_and_generate(self.student, cache, q_t, attn_implementation=self.kernel)
        logits = res.logits[0].float().cpu().numpy()
        idx = []
        for cand in cands[:2]:
            tids = self._tokens(str(cand), "student")
            idx.append(tids[0] if tids else 0)
        return np.asarray([float(logits[i]) for i in idx], dtype=float)
