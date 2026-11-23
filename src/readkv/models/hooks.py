"""KV 捕获与注入：真实 GPU 前向实现（pinned transformers>=5.24 / Qwen3）。

本模块把原来只定义契约的占位替换为真正的前端实现，接口语义与
``readkv.models.mock_backend.MockBackend`` 保持一致，替换后无需改动评测 /
mapper / 训练代码。

实现要点（对照 docs/gpu_handoff.md §2 与 docs/algorithm_spec.md §2/§3.4）：

* ``capture_teacher_cache``：对一份文档 ``d_A``/``d_B`` **分别独立** prefill
  一次；从 ``DynamicCache`` 中取每层 K/V（Qwen3 中是 **post QK-Norm + post
  RoPE** 的 key 与 V-proj 的 value，形状 ``(1, H_kv, T, d)``）；用 fp32 做
  de-RoPE 得到内容空间 key（这样注入时 re-RoPE 可精确恢复原 bf16 key）。
* ``inject_and_generate``：把（映射后的）缓存按学生位置 re-RoPE 后写入一个
  全新 ``DynamicCache``；query token 的 ``position_ids`` **显式**偏移 doc 长度
  （严格 zero re-prefill：学生只处理 query，不处理文档 token）；首 token 的
  logits 取自 query prefill 的最后一个位置，而不是在已推进的 cache 上生成。
* ``verify_zero_re_prefill``：instrument 学生 forward（pre-hook 记录每次
  forward 的 input token 数），断言没有任何文档 token 进入学生、forward 次数
  恰为 query-prefill + 解码步数，并回写 run 的 ``zero_re_prefill=true`` 标志。

dtype/kernel 口径：与 configs/eval.yaml 一致使用 bfloat16 + sdpa；de-RoPE /
re-RoPE 在 fp32 中计算以压低 bf16 舍入残差（E0 测量误差门的关键）。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence

import numpy as np
import torch

from readkv.cache.cache import KVCache
from readkv.models.loader import resolve_layers

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class ForwardAudit:
    """``inject_and_generate`` 期间记录的学生 forward 调用轨迹。"""

    input_token_counts: list[int] = field(default_factory=list)
    cache_prefix_lengths: list[int] = field(default_factory=list)
    doc_len: int = 0
    query_len: int = 0
    n_decode_steps: int = 0

    @property
    def total_input_tokens(self) -> int:
        return sum(self.input_token_counts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_token_counts": list(self.input_token_counts),
            "cache_prefix_lengths": list(self.cache_prefix_lengths),
            "doc_len": self.doc_len,
            "query_len": self.query_len,
            "n_decode_steps": self.n_decode_steps,
            "doc_tokens_fed_to_student": max(0, self.total_input_tokens - self.query_len - self.n_decode_steps),
        }


@dataclass
class InjectionResult:
    """``inject_and_generate`` 的返回值（含首 token logits 与审计轨迹）。"""

    logits: torch.Tensor                     # (1, vocab) 首 token（query 末位）logits
    audit: ForwardAudit
    cache: Any = None                        # 填充后的 transformers Cache
    generated_ids: torch.Tensor | None = None
    zero_re_prefill: bool = True

    def logits_numpy(self) -> np.ndarray:
        return self.logits.detach().float().cpu().numpy()


# ---------------------------------------------------------------------------
# 底层工具
# ---------------------------------------------------------------------------


def _model_device(model: Any) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:  # pragma: no cover - 无参数模型不存在
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _model_dtype(model: Any) -> torch.dtype:
    for p in model.parameters():
        return p.dtype
    return torch.bfloat16  # pragma: no cover


def _as_token_tensor(tokens: Any, device: torch.device) -> torch.Tensor:
    """把 list / 1D / 2D token ids 统一为 (1, T) long tensor。"""
    if isinstance(tokens, torch.Tensor):
        t = tokens.detach().to(device=device, dtype=torch.long)
    else:
        t = torch.as_tensor(list(tokens), device=device, dtype=torch.long)
    if t.ndim == 1:
        t = t.unsqueeze(0)
    if t.ndim != 2 or t.shape[0] != 1:
        raise ValueError(f"tokens must be a single sequence (T,) or (1,T), got {tuple(t.shape)}")
    return t


def _rope_module(model: Any):
    inner = getattr(model, "model", model)
    rope = getattr(inner, "rotary_emb", None)
    if rope is None:  # pragma: no cover
        raise NotImplementedError("model has no rotary_emb; adapt hooks for this checkpoint")
    return rope


def _rope_cos_sin(
    model: Any, position_ids: torch.Tensor, *, dtype: torch.dtype = torch.float32
) -> tuple[torch.Tensor, torch.Tensor]:
    """用模型自身的 rotary_emb 计算 cos/sin；以 fp32 入参得到 fp32 cos/sin。

    Qwen3RotaryEmbedding.forward(x, position_ids) 的 cos/sin 由 inv_freq 在 fp32
    计算后再 cast 到 ``x.dtype``；传入 fp32 dummy x 即可拿到未舍入的 fp32 值，
    供 de-RoPE / re-RoPE 使用。
    """
    rope = _rope_module(model)
    dummy = torch.ones(
        (position_ids.shape[0], position_ids.shape[1], 1),
        device=position_ids.device,
        dtype=dtype,
    )
    cos, sin = rope(dummy, position_ids)
    return cos.to(dtype=dtype), sin.to(dtype=dtype)


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    """与 Qwen3 的 rotate_half 一致：后半取负换到前半（half-split 约定）。"""
    d = x.shape[-1]
    if d % 2:
        raise ValueError("head_dim must be even for RoPE")
    x1, x2 = x[..., : d // 2], x[..., d // 2 :]
    return torch.cat((-x2, x1), dim=-1)


def _apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """x: (..., H, T, d) 或 (H, T, d); cos/sin: (..., T, d) 或 (T, d)。

    用 ``unsqueeze(-3)`` 同时在带 batch 与不带 batch 的张量上正确广播。
    """
    c, s = cos.unsqueeze(-3), sin.unsqueeze(-3)
    return x * c + _rotate_half(x) * s


def _de_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """_apply_rope 的正交逆变换。"""
    c, s = cos.unsqueeze(-3), sin.unsqueeze(-3)
    return x * c - _rotate_half(x) * s


def _layer_map_entry(layer_map: Any, student_layer: int, n_teacher: int) -> int:
    """把学生层号映射到教师层号；兼容 LayerMap / dict / callable / None。"""
    if layer_map is None:
        return student_layer
    if callable(layer_map):
        return int(layer_map(student_layer)) % n_teacher
    if isinstance(layer_map, Mapping):
        v = layer_map.get(student_layer, layer_map.get(str(student_layer)))
        if v is not None:
            return int(v) % n_teacher
        raise KeyError(f"layer_map has no entry for student layer {student_layer}")
    raise TypeError(f"unsupported layer_map type: {type(layer_map)!r}")


def _serialize_layer_map(layer_map: Any) -> Any:
    if layer_map is None:
        return None
    # LayerMap：落成显式 student->teacher 层号字典，注入端可直接查表
    if hasattr(layer_map, "source_for") and hasattr(layer_map, "ns"):
        return {int(i): int(layer_map.source_for(int(i))) for i in range(int(layer_map.ns))}
    if isinstance(layer_map, Mapping):
        return {str(k): int(v) for k, v in layer_map.items()}
    return {"repr": repr(layer_map)}


def _rope_config_meta(model: Any) -> dict[str, Any]:
    cfg = getattr(model, "config", None)
    if cfg is None:  # pragma: no cover
        return {}
    rp = getattr(cfg, "rope_parameters", {}) or {}
    return {
        "rope_theta": rp.get("rope_theta", getattr(cfg, "rope_theta", None)),
        "rope_type": rp.get("rope_type", "default"),
        "max_position_embeddings": getattr(cfg, "max_position_embeddings", None),
        "head_dim": getattr(cfg, "head_dim", None),
        "num_hidden_layers": getattr(cfg, "num_hidden_layers", None),
        "num_attention_heads": getattr(cfg, "num_attention_heads", None),
        "num_key_value_heads": getattr(cfg, "num_key_value_heads", None),
    }


def _check_rope_compatible(cache_meta: Mapping[str, Any], model: Any) -> None:
    """教师/学生 RoPE 参数不一致时拒绝注入（否则 de/re-RoPE 不对消）。"""
    cur = _rope_config_meta(model)
    for key in ("rope_theta", "rope_type", "max_position_embeddings", "head_dim"):
        a, b = cache_meta.get("teacher_" + key), cur.get(key)
        if a is not None and b is not None and a != b:
            raise ValueError(
                f"RoPE config mismatch on {key}: cache teacher={a}, student={b}; "
                "de-RoPE/re-RoPE would not cancel; refuse to inject silently"
            )


# ---------------------------------------------------------------------------
# 1) capture_teacher_cache
# ---------------------------------------------------------------------------


def capture_teacher_cache(
    model: Any,
    tokens: Any,
    layer_map: Any = None,
    *,
    position_ids: Sequence[int] | torch.Tensor | None = None,
    de_rope: bool = True,
    attn_implementation: str = "sdpa",
) -> KVCache:
    """对一份文档独立 prefill，返回 de-RoPE 内容空间的 :class:`KVCache`。

    Args:
        model: 冻结的教师（或做 identity 检查时的学生本体），``eval()`` 模式。
        tokens: 文档 token ids，(T,) 或 (1,T)。**只含文档，不含 query**。
        layer_map: 教师→学生层映射（仅记录进 metadata，供注入时使用）。
        position_ids: 文档位置；默认 ``0..T-1``。
        de_rope: 是否把 key 反旋转到内容空间（默认 True；落盘标准口径）。
        attn_implementation: 仅用于 metadata 记录；kernel 由模型 config 决定。

    Returns:
        KVCache：``keys[layer]`` / ``values[layer]`` 形状 ``(H_kv, T, d)`` 的
        numpy 数组（fp32），metadata 含 position_ids / RoPE / 层映射等。
    """
    device = _model_device(model)
    input_ids = _as_token_tensor(tokens, device)
    T = input_ids.shape[1]
    if position_ids is None:
        pos = torch.arange(T, device=device).unsqueeze(0)
    else:
        pos = torch.as_tensor(list(position_ids) if not isinstance(position_ids, torch.Tensor) else position_ids,
                              device=device, dtype=torch.long)
        if pos.ndim == 1:
            pos = pos.unsqueeze(0)
        if pos.shape[-1] != T:
            raise ValueError(f"position_ids length {pos.shape[-1]} != tokens length {T}")

    # fp32 cos/sin：de-RoPE 用（与注入端 re-RoPE 同一数值路径）
    cos32, sin32 = _rope_cos_sin(model, pos, dtype=torch.float32)

    was_training = model.training
    model.eval()
    with torch.inference_mode():
        from transformers import DynamicCache

        kv = DynamicCache(config=getattr(model, "config", None))
        outputs = model(
            input_ids=input_ids,
            cache=kv,
            use_cache=True,
            position_ids=pos,
            return_dict=True,
        )
    if was_training:
        model.train()

    keys: dict[int, np.ndarray] = {}
    values: dict[int, np.ndarray] = {}
    for layer_idx, layer in enumerate(kv.layers):
        k = layer.keys     # (1, H_kv, T, d) post QK-Norm + post RoPE, bf16
        v = layer.values   # (1, H_kv, T, d)
        if k is None or v is None:  # pragma: no cover
            raise RuntimeError(f"layer {layer_idx} has no K/V after prefill")
        k32 = k.detach().to(device="cpu", dtype=torch.float32)[0]  # (H,T,d)
        if de_rope:
            c = cos32.detach().to(device="cpu", dtype=torch.float32)[0]
            s = sin32.detach().to(device="cpu", dtype=torch.float32)[0]
            k32 = _de_rope(k32, c, s)
        keys[layer_idx] = k32.contiguous().numpy()
        values[layer_idx] = v.detach().to(device="cpu", dtype=torch.float32)[0].contiguous().numpy()

    meta: dict[str, Any] = {
        "kind": "teacher_cache",
        "de_roped": bool(de_rope),
        "position_ids": pos[0].detach().to(device="cpu", dtype=torch.long).tolist(),
        "seq_len": T,
        "dtype": str(_model_dtype(model)).replace("torch.", ""),
        "kernel": attn_implementation,
        "n_kv_heads": keys[0].shape[0],
        "head_dim": keys[0].shape[-1],
        "n_layers": len(keys),
        "layer_map": _serialize_layer_map(layer_map),
        "rope_convention": "half_split",  # Qwen3: cat(freqs,freqs) + rotate_half
    }
    for k, v in _rope_config_meta(model).items():
        meta["teacher_" + k] = v
    # 全序列 logits 的浅摘要（不落盘，仅调用方需要时从 outputs 读取）
    if outputs is not None:  # pragma: no cover - 保持引用避免被优化
        meta["prefill_logits_shape"] = list(tuple(outputs.logits.shape))
    return KVCache(keys, values, meta)


# ---------------------------------------------------------------------------
# 2) inject_and_generate
# ---------------------------------------------------------------------------


@contextmanager
def _forward_audit(model: Any, audit: ForwardAudit) -> Iterator[None]:
    """在模型顶层 forward 前记录输入 token 数，供 zero-re-prefill 断言。"""
    def pre_hook(module: Any, args: tuple, kwargs: dict) -> None:
        ids = kwargs.get("input_ids")
        if ids is None and args:
            ids = args[0]
        if ids is None:
            audit.input_token_counts.append(0)
            return
        if isinstance(ids, torch.Tensor):
            audit.input_token_counts.append(int(ids.shape[-1]))
        else:  # pragma: no cover
            audit.input_token_counts.append(int(np.asarray(ids).shape[-1]))

    handle = model.register_forward_pre_hook(pre_hook, with_kwargs=True)
    try:
        yield
    finally:
        handle.remove()


def _to_tensor_array(arr: Any, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    if isinstance(arr, torch.Tensor):
        return arr.detach().to(device=device, dtype=dtype)
    return torch.as_tensor(np.asarray(arr), device=device, dtype=dtype)


def inject_and_generate(
    model: Any,
    cache: KVCache,
    query_tokens: Any,
    *,
    position_offset: int | None = None,
    layer_map: Any = None,
    max_new_tokens: int = 0,
    return_audit: bool = True,
    grad_ok: bool = False,
    attn_implementation: str = "sdpa",
) -> InjectionResult:
    """用映射缓存初始化学生，显式位置偏移，首 token 取自 query prefill logits。

    Args:
        model: 冻结的学生（``eval()``）；Joint 推理图中它只处理 query token。
        cache: 内容空间（de-ROPed）K/V 的 :class:`KVCache`。
        query_tokens: query token ids，(Q,) 或 (1,Q)。
        position_offset: 文档占据的位置数；默认 ``cache.seq_len``（doc 在 0..T-1）。
        layer_map: 教师→学生层映射；缺省用 cache.metadata 中记录的映射。
        max_new_tokens: >0 时在 query-prefill 之后继续贪心解码（仍零重 prefill）。
        grad_ok: True 时不进入 inference_mode，允许梯度回传到映射缓存（训练用）。
    Returns:
        InjectionResult：``logits`` 为 query 末位的首 token logits ``(1,V)``。
    """
    meta = cache.metadata
    if not meta.get("de_roped", True):
        raise ValueError("cache keys must be de-ROPed content space before injection")
    _check_rope_compatible(meta, model)

    device = _model_device(model)
    model_dtype = _model_dtype(model)
    query = _as_token_tensor(query_tokens, device)
    Q = query.shape[1]
    doc_len = cache.seq_len
    offset = int(doc_len if position_offset is None else position_offset)
    if offset < 0:
        raise ValueError("position_offset must be >= 0")

    if layer_map is None:
        layer_map = meta.get("layer_map")
    n_teacher = cache.n_layers
    n_student = len(resolve_layers(model))
    if n_teacher < n_student:
        raise ValueError(f"cache has {n_teacher} teacher layers but student has {n_student}")

    # 学生位置：文档段 0..T-1（re-RoPE 用），query 段 offset..offset+Q-1
    doc_pos = torch.arange(doc_len, device=device).unsqueeze(0)
    q_pos = (torch.arange(Q, device=device) + offset).unsqueeze(0)
    cos_doc, sin_doc = _rope_cos_sin(model, doc_pos, dtype=torch.float32)
    grad_ctx = torch.enable_grad() if grad_ok else torch.inference_mode()

    from transformers import DynamicCache

    student_cache = DynamicCache(config=getattr(model, "config", None))
    cache_prefix_lengths: list[int] = []
    for s_layer in range(n_student):
        t_layer = _layer_map_entry(layer_map, s_layer, n_teacher)
        k_content = _to_tensor_array(cache.keys[t_layer], device, torch.float32)[None]  # (1,H,T,d)
        v = _to_tensor_array(cache.values[t_layer], device, model_dtype)[None]
        k_roped = _apply_rope(k_content, cos_doc, sin_doc).to(dtype=model_dtype)
        student_cache.update(k_roped, v, s_layer)
        cache_prefix_lengths.append(int(student_cache.layers[s_layer].get_seq_length()))

    audit = ForwardAudit(
        doc_len=doc_len,
        query_len=Q,
        cache_prefix_lengths=cache_prefix_lengths,
    )

    was_training = model.training
    model.eval()
    ctx = _forward_audit(model, audit) if return_audit else _nullcontext()
    with ctx, grad_ctx:
        outputs = model(
            input_ids=query,
            cache=student_cache,
            use_cache=True,
            position_ids=q_pos,
            return_dict=True,
        )
        logits = outputs.logits[:, -1, :]  # 首 token：query 最后位置的分布
        generated = None
        cur = logits.argmax(dim=-1, keepdim=True)
        generated = cur
        for _ in range(max_new_tokens):
            step_pos = (torch.arange(1, device=device) + offset + Q + int(generated.shape[1]) - 1).unsqueeze(0)
            step_out = model(
                input_ids=cur,
                cache=student_cache,
                use_cache=True,
                position_ids=step_pos,
                return_dict=True,
            )
            cur = step_out.logits[:, -1, :].argmax(dim=-1, keepdim=True)
            generated = torch.cat([generated, cur], dim=-1)
        audit.n_decode_steps = max_new_tokens
    if was_training:
        model.train()

    return InjectionResult(
        logits=logits,
        audit=audit,
        cache=student_cache,
        generated_ids=generated.detach() if generated is not None else None,
        zero_re_prefill=True,
    )


class _nullcontext:  # pragma: no cover - 标准库 contextlib.nullcontext 的轻量替身
    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: Any) -> None:
        return None


# ---------------------------------------------------------------------------
# 3) verify_zero_re_prefill
# ---------------------------------------------------------------------------


def verify_zero_re_prefill(
    audit: ForwardAudit | InjectionResult | Mapping[str, Any],
    *,
    expected_query_len: int | None = None,
    max_new_tokens: int = 0,
    run_config: Any = None,
    strict: bool = True,
) -> bool:
    """断言学生 forward 未接收任何文档 token（zero re-prefill）。

    检查三件事：
      1. 每次 forward 的 input token 数不超过 ``query_len + 1``（解码每步 1）；
      2. 喂给学生的文档 token 数为 0（文档 K/V 全部来自注入缓存）；
      3. forward 次数恰为 1（query prefill）+ ``max_new_tokens``（贪心解码）。

    通过时把 ``zero_re_prefill=true`` 写入 ``run_config``（dict 或 RunContext）。
    """
    if isinstance(audit, InjectionResult):
        audit = audit.audit
    if isinstance(audit, Mapping):
        counts = list(audit.get("input_token_counts", []))
        query_len = int(audit.get("query_len", 0))
        n_decode = int(audit.get("n_decode_steps", 0))
        doc_len = int(audit.get("doc_len", 0))
        total = sum(counts)
    else:
        counts = list(audit.input_token_counts)
        query_len = audit.query_len
        n_decode = audit.n_decode_steps
        doc_len = audit.doc_len
        total = audit.total_input_tokens

    if expected_query_len is not None and query_len != expected_query_len:
        ok_len = False
    else:
        ok_len = bool(counts) and all(c <= max(1, query_len) + (1 if n_decode else 0) for c in counts)
    ok_doc = (total - query_len - n_decode) == 0
    ok_calls = len(counts) == 1 + n_decode
    passed = bool(ok_len and ok_doc and ok_calls)

    if run_config is not None:
        if isinstance(run_config, dict):
            run_config["zero_re_prefill"] = passed
        else:
            setattr(run_config, "zero_re_prefill", passed)
    if strict and not passed:
        raise AssertionError(
            "zero re-prefill violated: "
            f"counts={counts}, query_len={query_len}, n_decode={n_decode}, doc_len={doc_len}, "
            f"ok_len={ok_len}, ok_doc={ok_doc}, ok_calls={ok_calls}"
        )
    return passed


__all__ = [
    "ForwardAudit",
    "InjectionResult",
    "capture_teacher_cache",
    "inject_and_generate",
    "verify_zero_re_prefill",
]
