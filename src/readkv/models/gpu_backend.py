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

    def torch_candidate_logits(
        self,
        mapped: Mapping[int, tuple[torch.Tensor, torch.Tensor]],
        query_doc: Mapping[str, Any],
        candidates: Sequence[str],
        *,
        correct_index: int | None = None,
        correct_bonus: float = 0.0,
        **kwargs: Any,
    ) -> torch.Tensor:
        """可微候选 readout（与 MockBackend.torch_candidate_logits 同接口/返回形状）。

        `mapped`: `{layer: (K, V)}`，K/V 为内容空间 torch 张量 (H, T, d)，fp32，
        可由 CFRCTModule.map_cache 产出并携带梯度。学生主权重冻结（requires_grad=False），
        梯度经映射缓存回传到 gθ，不更新学生权重。

        候选在同一生成位置（query 末位）取首 token logits，返回 (n_candidates,) 张量。
        `correct_index` / `correct_bonus` 仅为接口兼容保留；真实 GPU 前向**不注入**
        任何人工正确性偏置（默认 0.0），logits 全部来自冻结学生真实前向。
        """
        from transformers import DynamicCache

        from readkv.models.hooks import _apply_rope, _rope_cos_sin

        # 防御性冻结：学生（与教师）主权重不得进入梯度更新
        for p in self.student.parameters():
            if p.requires_grad:
                raise RuntimeError("student parameters must be frozen for torch_candidate_logits")

        cands = tuple(candidates)
        if len(cands) < 2:
            raise ValueError("torch_candidate_logits needs at least two candidates")
        device = next(self.student.parameters()).device
        dtype = next(self.student.parameters()).dtype

        k0, v0 = next(iter(mapped.values()))
        doc_len = int(k0.shape[1])
        doc_pos = torch.arange(doc_len, device=device).unsqueeze(0)
        cos, sin = _rope_cos_sin(self.student, doc_pos, dtype=torch.float32)

        kv = DynamicCache(config=self.student.config)
        for layer in sorted(mapped):
            k, v = mapped[layer]
            k = k.to(device=device, dtype=torch.float32)
            v = v.to(device=device, dtype=torch.float32)
            k_roped = _apply_rope(k.unsqueeze(0), cos, sin).to(dtype=dtype)
            kv.update(k_roped, v.unsqueeze(0).to(dtype=dtype), layer)

        q_ids = self._tokens(str(query_doc.get("query", query_doc.get("text", ""))), "student")
        q_t = torch.as_tensor(q_ids, device=device, dtype=torch.long).unsqueeze(0)
        q_pos = (torch.arange(len(q_ids), device=device) + doc_len).unsqueeze(0)
        self.n_injections += 1
        logits = self.student(
            input_ids=q_t, cache=kv, position_ids=q_pos, use_cache=True, return_dict=True
        ).logits[0, -1].float()

        idx = []
        for cand in cands[:2]:
            tids = self._tokens(str(cand), "student")
            idx.append(tids[0] if tids else 0)
        out = logits[torch.as_tensor(idx, device=device, dtype=torch.long)]
        if correct_index is not None and correct_bonus:
            if not 0 <= correct_index < out.shape[0]:
                raise ValueError("correct_index out of range")
            out = out.clone()
            out[correct_index] = out[correct_index] + float(correct_bonus)
        return out

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
