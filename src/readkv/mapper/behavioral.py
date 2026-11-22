"""行为目标 mapper：冻结学生，只训练 mapper；答案 CE + 批内错文档负样本。

与论文 1 的 adapter 路线的区别：这里不改任何学生权重。
与 KV-Lingo / CacheLink 的区别：必须有对比负样本 + 过三道门审计。
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import torch
from torch import nn

from readkv.cache.cache import KVCache
from readkv.mapper.base import BaseMapper


class AffineMapperModule(nn.Module):
    """可训练的 per-(layer, head) 仿射参数；初始化自闭式 consumer-space mapper。"""

    def __init__(self, init: dict) -> None:
        super().__init__()
        parsed = {}
        for key, mat in init.items():
            if isinstance(key, tuple):
                layer, ch, head = key
            else:  # state_dict 的字符串键 "layer_ch_head"
                layer, ch, head = str(key).split("_")
                layer, head = int(layer), int(head)
            parsed[f"{layer}_{ch}_{head}"] = nn.Parameter(torch.as_tensor(np.asarray(mat, dtype=np.float32)))
        self.weights = nn.ParameterDict(parsed)

    def map_cache(self, cache: KVCache) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
        out: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for layer in cache.layers:
            k, v = cache.layer(layer)
            kt, vt = torch.as_tensor(k, dtype=torch.float32), torch.as_tensor(v, dtype=torch.float32)
            mk = [self.weights.get(f"{layer}_K_{h}") for h in range(k.shape[0])]
            mv = [self.weights.get(f"{layer}_V_{h}") for h in range(v.shape[0])]
            if all(m is not None for m in mk):
                kt = torch.stack([kt[h] @ mk[h] for h in range(k.shape[0])])
            if all(m is not None for m in mv):
                vt = torch.stack([vt[h] @ mv[h] for h in range(v.shape[0])])
            out[layer] = (kt, vt)
        return out


def contrastive_loss(right: torch.Tensor, wrong: torch.Tensor, margin: float = 0.1) -> torch.Tensor:
    """正确文档 CE + 错文档对比项：wrong 的损失应显著高于 right。"""
    return right + torch.nn.functional.relu(margin + right - wrong)


def train_behavioral_mapper(
    module: AffineMapperModule,
    *,
    batches: list[tuple[KVCache, KVCache]],
    score_fn: Callable[[dict[int, tuple[torch.Tensor, torch.Tensor]]], torch.Tensor],
    epochs: int = 20,
    lr: float = 1e-3,
    margin: float = 0.1,
) -> AffineMapperModule:
    """score_fn(cache) -> CE loss；runner 负责把 cache 注入冻结学生并算 CE。"""
    optimizer = torch.optim.Adam(module.parameters(), lr=lr)
    module.train()
    for _ in range(epochs):
        for right_cache, wrong_cache in batches:
            optimizer.zero_grad()
            right = score_fn(module.map_cache(right_cache))
            wrong = score_fn(module.map_cache(wrong_cache)).detach()
            loss = contrastive_loss(right, wrong, margin)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
            optimizer.step()
    return module


class BehavioralMapper(BaseMapper):
    """BaseMapper 接口封装，便于与闭式 mapper 在同一实验框架中对照。"""

    name = "behavioral"

    def __init__(self, init: dict[tuple[int, str, int], np.ndarray] | None = None, **kwargs: Any) -> None:
        self.init = init or {}
        self.kwargs = kwargs
        self.module: AffineMapperModule | None = None

    def fit(self, teacher: KVCache, student: KVCache, **kwargs: Any) -> "BehavioralMapper":  # pragma: no cover
        batches = kwargs.get("batches")
        score_fn = kwargs.get("score_fn")
        if batches is None or score_fn is None:
            raise ValueError("behavioral mapper requires contrastive batches and a score_fn callback")
        self.module = train_behavioral_mapper(
            AffineMapperModule(self.init), batches=batches, score_fn=score_fn, **self.kwargs
        )
        return self

    def transform(self, teacher: KVCache) -> KVCache:  # pragma: no cover
        if self.module is None:
            raise RuntimeError("mapper is not fitted")
        out: dict[int, np.ndarray] = {}
        out_v: dict[int, np.ndarray] = {}
        mapped = self.module.map_cache(teacher)
        for layer, (k, v) in mapped.items():
            out[layer] = k.detach().numpy().astype(teacher.keys[layer].dtype)
            out_v[layer] = v.detach().numpy().astype(teacher.values[layer].dtype)
        return KVCache(out, out_v, dict(teacher.metadata))
