"""模型加载与冻结。

实际推理需要带 GPU 的机器；此模块只做与 transformers 版本无关的最小封装。
"""

from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_model_and_tokenizer(
    model_id: str, *, device: str = "cuda", dtype: str = "bfloat16", freeze: bool = True
) -> tuple[Any, Any]:
    torch_dtype = getattr(torch, dtype)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model.to(device)
    if freeze:
        freeze_model(model)
    model.eval()
    return model, tokenizer


def freeze_model(model: Any) -> None:
    for param in model.parameters():
        param.requires_grad_(False)


def resolve_layers(model: Any) -> list[Any]:
    """返回 transformer block 列表；兼容常见 ``model.model.layers`` 布局。"""
    try:
        return list(model.model.layers)
    except AttributeError as exc:  # pragma: no cover - 仅在新版 transformers 触发
        raise NotImplementedError("unsupported model layout; adapt resolve_layers for this checkpoint") from exc


def layer_input_dim(model: Any) -> int:  # pragma: no cover - 依赖具体 checkpoint
    raise NotImplementedError("derive hidden size from model.config.hidden_size in the runner")
