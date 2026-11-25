"""KVCache：按层的 K/V 容器（H, T, d），npz 落盘，层子集，体积估算。

Teacher 缓存离线生成后只读；mapper 产出的缓存同样走这里，保证注入管线只有一条。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np


@dataclass
class KVCache:
    """layer index -> array of shape (H, T, d)。

    keys 默认存放 de-RoPE 后的内容空间张量；注入前由 models.rope 按学生位置 re-RoPE。
    """

    keys: dict[int, np.ndarray]
    values: dict[int, np.ndarray]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if set(self.keys) != set(self.values):
            raise ValueError("keys and values must cover the same layers")
        if not self.keys:
            raise ValueError("empty cache")
        lengths = {v.shape[1] for v in self.values.values()}
        if len(lengths) != 1:
            raise ValueError("all layers must have the same token length")

    @property
    def layers(self) -> list[int]:
        return sorted(self.keys)

    @property
    def n_layers(self) -> int:
        return len(self.keys)

    @property
    def seq_len(self) -> int:
        return next(iter(self.values.values())).shape[1]

    def layer(self, idx: int) -> tuple[np.ndarray, np.ndarray]:
        return self.keys[idx], self.values[idx]

    def subset(self, layers: list[int]) -> KVCache:
        return KVCache(
            {i: self.keys[i] for i in layers},
            {i: self.values[i] for i in layers},
            dict(self.metadata),
        )

    def clone(self) -> KVCache:
        return KVCache({i: a.copy() for i, a in self.keys.items()}, {i: a.copy() for i, a in self.values.items()}, dict(self.metadata))

    def estimate_bytes(self) -> int:
        return sum(a.nbytes for a in self.keys.values()) + sum(a.nbytes for a in self.values.values())


class CacheStore:
    """按 run 目录保存/加载缓存；npz 便于 memmap 且不含 pickle。"""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, cache: KVCache, name: str) -> Path:
        path = self.root / f"{name}.npz"
        payload: dict[str, np.ndarray] = {}
        for layer in cache.layers:
            k, v = cache.layer(layer)
            payload[f"k_{layer}"] = k
            payload[f"v_{layer}"] = v
        payload["_layers"] = np.asarray(cache.layers, dtype=np.int64)
        np.savez_compressed(path, **payload)
        (self.root / f"{name}.meta.json").write_text(
            _json_dumps(cache.metadata), encoding="utf-8"
        )
        return path

    def load(self, name: str) -> KVCache:
        path = self.root / f"{name}.npz"
        if not path.exists():
            raise FileNotFoundError(path)
        import json

        with np.load(path, allow_pickle=False) as data:
            layers = [int(x) for x in data["_layers"]]
            keys = {i: data[f"k_{i}"] for i in layers}
            values = {i: data[f"v_{i}"] for i in layers}
        meta_path = self.root / f"{name}.meta.json"
        metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        return KVCache(keys, values, metadata)


def _json_dumps(payload: Mapping[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def estimate_bytes_per_token(config: Mapping[str, Any]) -> int:
    """按层数、KV 头数、head_dim 粗算 fp16 体积；需实测确认。"""
    n_layers = int(config["n_layers"])
    heads = int(config["n_kv_heads"])
    dim = int(config["head_dim"])
    return 2 * n_layers * heads * dim * 2  # K+V, fp16 = 2 bytes
