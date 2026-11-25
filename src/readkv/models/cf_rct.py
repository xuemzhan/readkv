"""CF-RCT 候选 Mapper（V2.0 方案 §7.1，工作名）。

以一个可学习的 K/V Mapper 为主体；学生主权重冻结。Mapper 参数化从低风险起步：
  ① per-(layer, head) affine + 层映射；
  ② 加低秩残差修正；
  ③ 仅当显著必要时加入小型跨层 Mixer（此处不默认启用）。

两个版本：
  CF-RCT-lite : 仅 L_KD + L_CF（无机制约束）
  CF-RCT-mech : 加入由局部干预选出的层/Head 机制约束（L_local）

注意：本模块是候选算法实现，不预设其优于 KD 基线；是否有增益须由 §7.4 的
公平比较与封存测试判定。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch
from torch import nn

from readkv.cache.cache import KVCache


class CFRCTModule(nn.Module):
    """torch 参数化：per-(layer, channel, head) affine + 可选低秩残差。"""

    def __init__(self, init_state: Mapping[str, np.ndarray] | None = None,
                 *, rank: int = 0, n_layers: int | None = None,
                 n_heads: int | None = None, dim: int | None = None) -> None:
        super().__init__()
        self.rank = int(rank)
        self.matrices = nn.ParameterDict()
        self.residual_a = nn.ParameterDict()
        self.residual_b = nn.ParameterDict()

        if init_state:
            for key, mat in init_state.items():
                parts = key.split("_")
                # 支持 "layer_ch_head" 与 "layer_head" 两种 key
                if len(parts) == 3:
                    layer, ch, head = parts
                elif len(parts) == 2:
                    layer, ch, head = parts[0], "K", parts[1]
                else:  # pragma: no cover
                    raise ValueError(f"unsupported mapper state key: {key}")
                k = f"{layer}_{ch}_{head}"
                self.matrices[k] = nn.Parameter(torch.as_tensor(np.asarray(mat, dtype=np.float32)))
                if self.rank > 0:
                    d_in, d_out = self.matrices[k].shape
                    r = min(self.rank, d_in, d_out)
                    self.residual_a[k] = nn.Parameter(torch.randn(d_in, r) * 0.01)
                    self.residual_b[k] = nn.Parameter(torch.zeros(r, d_out))
        elif n_layers is not None and n_heads is not None and dim is not None:
            for layer in range(n_layers):
                for head in range(n_heads):
                    for ch in ("K", "V"):
                        k = f"{layer}_{ch}_{head}"
                        self.matrices[k] = nn.Parameter(torch.eye(dim))
                        if self.rank > 0:
                            r = min(self.rank, dim)
                            self.residual_a[k] = nn.Parameter(torch.randn(dim, r) * 0.01)
                            self.residual_b[k] = nn.Parameter(torch.zeros(r, dim))

    def weight(self, layer: int, ch: str, head: int) -> torch.Tensor:
        base = self.matrices[f"{layer}_{ch}_{head}"]
        if self.rank > 0:
            base = base + self.residual_a[f"{layer}_{ch}_{head}"] @ self.residual_b[f"{layer}_{ch}_{head}"]
        return base

    def map_cache(self, cache: KVCache) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
        out: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for layer in cache.layers:
            k, v = cache.layer(layer)
            k_t, v_t = [], []
            for head in range(k.shape[0]):
                wk = self.weight(layer, "K", head)
                wv = self.weight(layer, "V", head)
                k_t.append(torch.as_tensor(k[head], dtype=torch.float32) @ wk)
                v_t.append(torch.as_tensor(v[head], dtype=torch.float32) @ wv)
            out[layer] = (torch.stack(k_t), torch.stack(v_t))
        return out

    def regularization(self) -> torch.Tensor:
        if self.rank == 0:
            return torch.tensor(0.0)
        terms = [torch.norm(a) ** 2 + torch.norm(b) ** 2
                 for a, b in zip(self.residual_a.values(), self.residual_b.values())]
        return sum(terms) if terms else torch.tensor(0.0)

    def state_dict_numpy(self) -> dict[str, np.ndarray]:
        return {k: v.detach().numpy().copy() for k, v in self.matrices.items()}


class CFRCTMapper:
    """BaseMapper 风格的封装，transform(teacher KVCache) -> mapped KVCache。"""

    name = "cf_rct"

    def __init__(self, module: CFRCTModule | None = None) -> None:
        self.module = module

    @property
    def method(self) -> str:
        return getattr(self.module, "method", "cf_rct")

    def transform(self, teacher: KVCache) -> KVCache:
        if self.module is None:
            raise RuntimeError("CFRCTMapper has no trained module")
        self.module.eval()
        with torch.no_grad():
            mapped = self.module.map_cache(teacher)
        keys = {l: v[0].numpy() for l, v in mapped.items()}
        values = {l: v[1].numpy() for l, v in mapped.items()}
        return KVCache(keys, values, dict(teacher.metadata) | {"mapper": "cf_rct"})

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        torch.save({"state": self.module.state_dict_numpy(), "rank": self.module.rank}, path)
        return path

    @classmethod
    def load(cls, path: Path | str) -> "CFRCTMapper":
        payload = torch.load(path, weights_only=False)
        module = CFRCTModule(payload["state"], rank=payload["rank"])
        return cls(module)

    # BaseMapper.fit 接口兼容：CF-RCT 由 train/cf_rct.py 训练，不在 fit 内完成
    def fit(self, *args: Any, **kwargs: Any) -> "CFRCTMapper":
        raise NotImplementedError("use readkv.train.cf_rct.train_cf_rct to fit CFRCTMapper")
