"""真实 GPU 后端：实现 evaluate/cf_pipeline.py 所需的 MockBackend 契约子集。

与 MockBackend 完全相同的接口语义（pair_side_cache / inject / candidate_logits /
cache），但所有缓存来自真实 Qwen3 前向。教师与学生各自独立 prefill，绝不篡改
缓存字节；g(C,q) 用真正的 next-token 候选 logits（不含 mock 的正确性偏置）。
Mock 数字不进入任何真实 run。
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field
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


# ===========================================================================
# 显式候选序列评分模式（protocol-v2.8）
# ---------------------------------------------------------------------------
# 本段为新增内容，**不改动**上面 GPUBackend 的贪解码路径（inject_and_generate /
# candidate_logits / torch_candidate_logits）。teacher-forcing 走独立入口：
# 每条候选分支从同一份（已映射的）内容空间缓存新建自己的可变 DynamicCache，
# 只把 query + 当前候选真实前缀 token 喂进学生显式输入，文档长度只经注入缓存
# 与 position_ids 偏移进入。前向长度序列严格为 [Q, 1 × (m−1)]。
# 下方纯函数（*_fp32 / *_sequence / token_boundary_report / audit_sequence_forwards /
# single_token_consistency）不依赖 GPU，供 CPU 自检与实验入口共用。
# ===========================================================================

# 每次 score_candidate_sequence 调用都构造一个全新 DynamicCache；用单调实例号
# 标记分支身份（id() 会被 GC 复用，不适合作为跨分支独立性证据）。
_SEQUENCE_BRANCH_COUNTER = itertools.count(1)


def log_softmax_fp32(logits: Any) -> np.ndarray:
    """FP32 log-softmax（numpy 路径）；接受 torch.Tensor 或 array-like，返回 1-D fp32。"""
    if isinstance(logits, torch.Tensor):
        x = logits.detach().float().cpu().numpy()
    else:
        x = np.asarray(logits)
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if x.size == 0:
        raise ValueError("log_softmax_fp32 needs a non-empty vector")
    z = x - float(x.max())
    return (z - np.log(np.exp(z).sum(dtype=np.float32))).astype(np.float32)


def token_id_fingerprint(ids: Any) -> str:
    """候选 token id 序列的规范 sha256（用于逐次输入审计与报告指纹）。"""
    if isinstance(ids, torch.Tensor):
        seq = [int(v) for v in ids.detach().flatten().cpu().tolist()]
    else:
        seq = [int(v) for v in np.asarray(ids).flatten().tolist()]
    payload = json.dumps(seq, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def expected_input_length_sequence(query_len: int, candidate_len: int) -> list[int]:
    """对长度 m 的候选，学生显式输入长度序列应为 [Q, 1 × (m−1)]。纯函数。"""
    q, m = int(query_len), int(candidate_len)
    if q <= 0 or m <= 0:
        raise ValueError("query_len and candidate_len must be positive")
    return [q] + [1] * (m - 1)


def prefix_relation(a: Sequence[int], b: Sequence[int]) -> str:
    """返回 'a_prefix_of_b' / 'b_prefix_of_a' / 'both' / 'none'（候选互为前缀计数用）。"""
    x, y = list(a), list(b)
    ab = len(x) <= len(y) and y[: len(x)] == x
    ba = len(y) <= len(x) and x[: len(y)] == y
    if ab and ba:
        return "both"
    if ab:
        return "a_prefix_of_b"
    if ba:
        return "b_prefix_of_a"
    return "none"


def token_boundary_report(ids_query: Sequence[int], ids_candidate: Sequence[int],
                          ids_joint: Sequence[int]) -> dict[str, Any]:
    """检查 encode(query+candidate) 是否等于两段独立 token 序列的拼接（关闭特殊 token）。纯函数。"""
    q, c, j = list(ids_query), list(ids_candidate), list(ids_joint)
    split = q + c
    return {
        "consistent": j == split,
        "joint_len": len(j),
        "split_len": len(split),
        "query_len": len(q),
        "candidate_len": len(c),
        "prefix_relation": prefix_relation(q, c),
    }


def single_token_consistency(first_logprob: float, full_logprob_sum: float,
                             candidate_len: int, *, tol: float = 1e-5) -> dict[str, Any]:
    """单 token 候选下整串和必须等于首 token logprob（历史回放锚点）。纯函数。"""
    m = int(candidate_len)
    d = abs(float(first_logprob) - float(full_logprob_sum))
    return {
        "applicable": m == 1,
        "passed": (d <= tol) if m == 1 else True,
        "abs_diff": d,
        "tol": tol,
    }


def audit_sequence_forwards(
    *,
    input_lengths: Sequence[int],
    position_starts: Sequence[int],
    input_token_fingerprints: Sequence[str],
    query_len: int,
    candidate_len: int,
    doc_len: int,
    position_offset: int,
    candidate_token_ids: Sequence[int],
    initial_cache_prefix_length: int,
    cache_prefix_lengths: Sequence[int],
) -> dict[str, Any]:
    """逐次输入审计（纯函数）：长度序列 / 位置 / zero re-prefill / 缓存增长。

    对长度 m 候选：期望 m 次 forward，输入长度 [Q, 1×(m−1)]；首次 position 为
    ``position_offset``，后续每次 +1；喂进学生的 token 总数 = Q+(m−1)（文档 token
    一个都没进显式输入）；注入缓存前缀每步只增长对应输入长度。
    """
    q, m = int(query_len), int(candidate_len)
    offset = int(position_offset)
    exp_len = expected_input_length_sequence(q, m) if q > 0 and m > 0 else []
    exp_pos = [offset] + [offset + q + i for i in range(m - 1)] if m > 0 else []
    exp_prefix = ([int(initial_cache_prefix_length)]
                  + [int(initial_cache_prefix_length) + q + i for i in range(m - 1)] if m > 0 else [])
    lens = [int(v) for v in input_lengths]
    pos = [int(v) for v in position_starts]
    pref = [int(v) for v in cache_prefix_lengths]
    fps = [str(v) for v in input_token_fingerprints]
    toks = [int(v) for v in candidate_token_ids]

    checks: dict[str, bool] = {
        "forward_count": len(lens) == m,
        "length_sequence": lens == exp_len,
        "position_offset_first": bool(pos) and pos[0] == offset,
        # 首个 query forward 跨 Q 个位置，故第二个 forward 起点 = offset+Q；
        # 之后每次候选前缀 forward 位置 +1（v2.8「后续每次位置加一」）。
        "position_increments": len(pos) == m and pos == exp_pos and all(
            pos[i + 1] == pos[i] + 1 for i in range(1, len(pos) - 1)),
        "zero_re_prefill_no_doc_tokens": (sum(lens) == q + m - 1)
                                         and bool(pos) and all(p >= offset for p in pos)
                                         and offset >= int(doc_len),
        "cache_prefix_growth": pref == exp_prefix,
        "fingerprints_recorded": len(fps) == m and all(bool(v) for v in fps),
        "candidate_ids_recorded": toks == list(candidate_token_ids) and len(toks) == m,
    }
    failures = [k for k, ok in checks.items() if not ok]
    return {
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "expected": {"length_sequence": exp_len, "position_starts": exp_pos,
                     "cache_prefix_lengths": exp_prefix},
        "observed": {"length_sequence": lens, "position_starts": pos,
                     "cache_prefix_lengths": pref, "input_token_fingerprints": fps,
                     "candidate_token_ids": toks},
    }


@dataclass
class SequenceScoreAudit:
    """一次候选分支 teacher-forcing 的逐次前向审计（写 forward_audit.jsonl）。"""

    branch_tag: str = ""
    doc_len: int = 0
    query_len: int = 0
    candidate_len: int = 0
    candidate_token_ids: list[int] = field(default_factory=list)
    candidate_token_id_fingerprint: str = ""
    position_offset: int = 0
    input_lengths: list[int] = field(default_factory=list)
    input_token_fingerprints: list[str] = field(default_factory=list)
    position_starts: list[int] = field(default_factory=list)
    cache_prefix_lengths: list[int] = field(default_factory=list)
    branch_cache_id: int = 0
    branch_cache_object_id: int = 0
    initial_cache_prefix_length: int = 0
    passed: bool = True
    failures: list[str] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def zero_re_prefill(self) -> bool:
        return self.passed and "zero_re_prefill_no_doc_tokens" not in self.failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "branch_tag": self.branch_tag,
            "doc_len": self.doc_len,
            "query_len": self.query_len,
            "candidate_len": self.candidate_len,
            "candidate_token_ids": list(self.candidate_token_ids),
            "candidate_token_id_fingerprint": self.candidate_token_id_fingerprint,
            "position_offset": self.position_offset,
            "input_length_sequence": list(self.input_lengths),
            "input_token_fingerprints": list(self.input_token_fingerprints),
            "forward_position_starts": list(self.position_starts),
            "cache_prefix_lengths": list(self.cache_prefix_lengths),
            "branch_cache_id": self.branch_cache_id,
            "branch_cache_object_id": self.branch_cache_object_id,
            "expected_input_length_sequence": expected_input_length_sequence(self.query_len, self.candidate_len)
                                              if self.query_len > 0 and self.candidate_len > 0 else [],
            "zero_re_prefill": self.passed and "zero_re_prefill_no_doc_tokens" not in self.failures,
            "audit_passed": self.passed,
            "audit_failures": list(self.failures),
            "audit_report": self.report,
        }


@dataclass
class SequenceScoreResult:
    """一条候选的三读数 + 审计轨迹。"""

    first_logprob: float
    full_logprob_sum: float
    length_normalized: float
    candidate_len: int
    audit: SequenceScoreAudit

    def as_scores(self) -> dict[str, float]:
        return {
            "first": float(self.first_logprob),
            "full": float(self.full_logprob_sum),
            "length_normalized": float(self.length_normalized),
        }


def score_candidate_sequence(
    model: Any,
    cache: KVCache,
    query_tokens: Any,
    candidate_token_ids: Sequence[int],
    *,
    position_offset: int | None = None,
    layer_map: Any = None,
    branch_tag: str = "",
    strict_audit: bool = True,
    attn_implementation: str = "sdpa",
) -> SequenceScoreResult:
    """显式 teacher-forcing 评分（不复用贪解码 inject_and_generate）。

    Args:
        model: 冻结学生（eval）。Joint 推理图中只处理 query + 当前候选前缀。
        cache: 内容空间（de-ROPed）K/V 的 KVCache（同一文档缓存，多个候选分支各自
               调用本函数以新建独立的 DynamicCache，不共享可变状态）。
        query_tokens: query token ids (Q,) 或 (1,Q)。
        candidate_token_ids: 该候选的 token id 序列（学生 tokenizer，
                             add_special_tokens=False），长度 m≥1，不追加 EOS。
        position_offset: 文档占据的位置数，默认 cache.seq_len。
        layer_map: 教师→学生层映射（仅用于真正的教师缓存）。缺省时若缓存已在
            学生层空间（深度 <= 学生层数）则恒等注入，不再施加 metadata 中的
            teacher→student 映射（与 ``inject_and_generate`` 同口径）。
        strict_audit: True 时任一审计断言失败即抛 AssertionError（中止该格）。

    Returns:
        SequenceScoreResult：首 token logprob / 整串 FP32 条件 logprob 之和 /
        长度归一和，以及逐次前向审计。前向长度序列严格为 [Q, 1 × (m−1)]。
    """
    from readkv.models import hooks as H
    from readkv.models.loader import resolve_layers

    meta = cache.metadata
    if not meta.get("de_roped", True):
        raise ValueError("cache keys must be de-ROPed content space before scoring")
    H._check_rope_compatible(meta, model)

    device = H._model_device(model)
    model_dtype = H._model_dtype(model)
    query = H._as_token_tensor(query_tokens, device)
    Q = int(query.shape[1])
    if Q <= 0:
        raise ValueError("query must have at least one token")
    cand_ids = [int(t) for t in candidate_token_ids]
    m = len(cand_ids)
    if m == 0:
        raise ValueError("candidate must have at least one token (no EOS is appended)")

    doc_len = int(cache.seq_len)
    offset = int(doc_len if position_offset is None else position_offset)
    if offset < 0:
        raise ValueError("position_offset must be >= 0")

    n_teacher = cache.n_layers
    n_student = len(resolve_layers(model))
    if n_teacher < n_student:
        raise ValueError(f"cache has {n_teacher} teacher layers but student has {n_student}")
    # 关键修复（非等深路径）：mapper.transform 后缓存已处于学生层空间，注入必须
    # 恒等；若复用捕获时记录的 teacher→student map，会再读 mp[s] % n_student，
    # 只有 s=0,1 正确且全部落在合法层号内 -> silent corruption。source_layer_map
    # 仅作溯源元数据保留，绝不在这里二次施加。
    layer_map = H.resolve_injection_layer_map(layer_map, meta, n_teacher, n_student)

    # 每条候选分支都新建自己的 DynamicCache：从 numpy 源数组重新构造张量，不共享可变状态。
    from transformers import DynamicCache

    student_cache = DynamicCache(config=getattr(model, "config", None))
    doc_pos = torch.arange(doc_len, device=device).unsqueeze(0)
    cos_doc, sin_doc = H._rope_cos_sin(model, doc_pos, dtype=torch.float32)
    for s_layer in range(n_student):
        t_layer = H._layer_map_entry(layer_map, s_layer, n_teacher)
        k_content = H._to_tensor_array(cache.keys[t_layer], device, torch.float32)[None]
        v = H._to_tensor_array(cache.values[t_layer], device, model_dtype)[None]
        k_roped = H._apply_rope(k_content, cos_doc, sin_doc).to(dtype=model_dtype)
        student_cache.update(k_roped, v, s_layer)
    initial_prefix = int(student_cache.layers[0].get_seq_length())

    audit = SequenceScoreAudit(
        branch_tag=branch_tag,
        doc_len=doc_len, query_len=Q, candidate_len=m,
        candidate_token_ids=list(cand_ids),
        candidate_token_id_fingerprint=token_id_fingerprint(cand_ids),
        position_offset=offset,
        branch_cache_id=next(_SEQUENCE_BRANCH_COUNTER),
        branch_cache_object_id=id(student_cache),
        initial_cache_prefix_length=initial_prefix,
    )

    def pre_hook(module: Any, args: tuple, kwargs: dict) -> None:
        ids = kwargs.get("input_ids")
        if ids is None and args:
            ids = args[0]
        if isinstance(ids, torch.Tensor):
            audit.input_lengths.append(int(ids.shape[-1]))
            audit.input_token_fingerprints.append(token_id_fingerprint(ids))
        else:  # pragma: no cover - 入口只传 tensor
            audit.input_lengths.append(int(np.asarray(ids).shape[-1]))
            audit.input_token_fingerprints.append(token_id_fingerprint(ids if ids is not None else []))
        pos = kwargs.get("position_ids")
        if isinstance(pos, torch.Tensor):
            audit.position_starts.append(int(pos[0, 0].item()))
        else:  # pragma: no cover
            audit.position_starts.append(-1)

    handle = model.register_forward_pre_hook(pre_hook, with_kwargs=True)
    was_training = model.training
    model.eval()
    try:
        with torch.inference_mode():
            # 1) query prefill -> 首 token 分布（预测 cand[0]）
            q_pos = (torch.arange(Q, device=device) + offset).unsqueeze(0)
            audit.cache_prefix_lengths.append(int(student_cache.layers[0].get_seq_length()))
            out = model(input_ids=query, cache=student_cache, use_cache=True,
                        position_ids=q_pos, return_dict=True)
            first_logprob = float(log_softmax_fp32(out.logits[:, -1, :])[cand_ids[0]])

            # 2) 依次 teacher-force 真实候选前缀 token：喂 cand[i] 预测 cand[i+1]
            total = first_logprob
            for i in range(m - 1):
                feed = torch.tensor([[cand_ids[i]]], device=device, dtype=torch.long)
                step_pos = torch.tensor([[offset + Q + i]], device=device, dtype=torch.long)
                audit.cache_prefix_lengths.append(int(student_cache.layers[0].get_seq_length()))
                out = model(input_ids=feed, cache=student_cache, use_cache=True,
                            position_ids=step_pos, return_dict=True)
                total += float(log_softmax_fp32(out.logits[:, -1, :])[cand_ids[i + 1]])
    finally:
        handle.remove()
        if was_training:
            model.train()

    audit.report = audit_sequence_forwards(
        input_lengths=audit.input_lengths,
        position_starts=audit.position_starts,
        input_token_fingerprints=audit.input_token_fingerprints,
        query_len=Q, candidate_len=m, doc_len=doc_len, position_offset=offset,
        candidate_token_ids=cand_ids,
        initial_cache_prefix_length=initial_prefix,
        cache_prefix_lengths=audit.cache_prefix_lengths,
    )
    audit.passed = bool(audit.report["passed"])
    audit.failures = list(audit.report["failures"])
    if strict_audit and not audit.passed:
        raise AssertionError(f"sequence scoring input audit failed for {branch_tag!r}: "
                             f"{audit.failures}; report={json.dumps(audit.report, ensure_ascii=False)}")

    return SequenceScoreResult(
        first_logprob=first_logprob,
        full_logprob_sum=float(total),
        length_normalized=float(total) / float(m),
        candidate_len=m,
        audit=audit,
    )


__all__ = [
    "ForwardAudit",
    "InjectionResult",
    "GPUBackend",
    "SequenceScoreAudit",
    "SequenceScoreResult",
    "audit_sequence_forwards",
    "capture_teacher_cache",
    "expected_input_length_sequence",
    "inject_and_generate",
    "log_softmax_fp32",
    "prefix_relation",
    "single_token_consistency",
    "score_candidate_sequence",
    "token_boundary_report",
    "token_id_fingerprint",
    "verify_zero_re_prefill",
]
