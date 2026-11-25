"""消费侧 adapter：论文 1 的 rank-8 低秩修正，作为干预/对照组。

proj'(x) = W x + B(A x)，B 初始化为 0，只训练 {A,B}；学生与 mapper 冻结。
"""

from __future__ import annotations

from typing import Any, Callable

import torch
from torch import nn


class LowRankAdapter(nn.Module):
    def __init__(self, base: nn.Module, in_features: int, out_features: int, rank: int = 8) -> None:
        super().__init__()
        self.base = base
        for p in base.parameters():
            p.requires_grad_(False)
        self.A = nn.Linear(in_features, rank, bias=False)
        self.B = nn.Linear(rank, out_features, bias=False)
        nn.init.zeros_(self.B.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x) + self.B(self.A(x))


def train_adapter(
    adapter: LowRankAdapter,
    *,
    batches: list[Any],
    score_fn: Callable[[Any], torch.Tensor],
    epochs: int = 20,
    lr: float = 1e-3,
) -> LowRankAdapter:
    optimizer = torch.optim.Adam(
        [p for p in adapter.parameters() if p.requires_grad], lr=lr
    )
    adapter.train()
    for _ in range(epochs):
        for batch in batches:
            optimizer.zero_grad()
            loss = score_fn(adapter, batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1.0)
            optimizer.step()
    return adapter


def apply_adapter_to_model(model: Any, module_name: str, rank: int = 8) -> LowRankAdapter:  # pragma: no cover
    """把 adapter 挂到学生的 o_proj / v_proj / q_proj,k_proj（模型结构版本相关）。"""
    raise NotImplementedError("resolve projection modules against the pinned transformers version")
