"""教师缓存离线生成（V2.0 方案 §9.2）。

固定 tokenizer/模板 → 对 d_A、d_B **分别** Prefill（绝不篡改缓存字节伪造
另一文档）→ 校验长度、position_ids、layer/KV 形状 → 按 pair_id 落盘 →
记录文件哈希与配置指纹 → 卸载教师。

本模块提供与后端无关的编排与落盘逻辑；真实前向由调用方注入的
``prefill_fn(doc) -> KVCache`` 提供（GPU 机器上由 models/hooks.py 实现）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from readkv.cache.cache import CacheStore, KVCache


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def config_fingerprint(config: Mapping[str, Any]) -> str:
    """配置指纹：模型版本、模板、dtype、kernel、seed 变化即视为不同缓存。"""
    keys = ("model_pair", "model_revision", "tokenizer", "template", "dtype",
            "kernel", "seed", "max_length", "rope_scaling")
    payload = {k: config[k] for k in keys if k in config}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()[:16]


def validate_cache(cache: KVCache, *, doc_id: str, expected_tokens: int | None = None,
                   min_tokens: int = 1, max_tokens: int = 4096) -> None:
    """形状/位置/长度门禁；异常显式报错，不静默通过。"""
    if cache.seq_len < min_tokens or cache.seq_len > max_tokens:
        raise ValueError(f"{doc_id}: seq_len {cache.seq_len} outside [{min_tokens},{max_tokens}]")
    if expected_tokens is not None and cache.seq_len != expected_tokens:
        raise ValueError(f"{doc_id}: token length {cache.seq_len} != expected {expected_tokens}")
    for layer in cache.layers:
        k, v = cache.layer(layer)
        if k.shape != v.shape:
            raise ValueError(f"{doc_id}: layer {layer} K/V shape mismatch: {k.shape} vs {v.shape}")
        if k.ndim != 3:
            raise ValueError(f"{doc_id}: layer {layer} keys must be (H,T,d), got {k.ndim}D")
    pos = cache.metadata.get("position_ids")
    if pos is not None and len(pos) != cache.seq_len:
        raise ValueError(f"{doc_id}: position_ids length {len(pos)} != seq_len {cache.seq_len}")


def prefill_pair(
    prefill_fn: Callable[[Mapping[str, Any]], KVCache],
    pair: Mapping[str, Any],
) -> tuple[KVCache, KVCache]:
    """对 d_A、d_B 分别独立 Prefill，返回两份缓存。"""
    doc_a = _doc_from_pair(pair, "A")
    doc_b = _doc_from_pair(pair, "B")
    cache_a = prefill_fn(doc_a)
    cache_b = prefill_fn(doc_b)
    validate_cache(cache_a, doc_id=f"{pair['pair_id']}:A")
    validate_cache(cache_b, doc_id=f"{pair['pair_id']}:B")
    # 长度不匹配不报错，但显式标注（方案 §4.4：分层报告，防止位置编码效应）
    if cache_a.seq_len != cache_b.seq_len:
        for cache in (cache_a, cache_b):
            cache.metadata = dict(cache.metadata)
            cache.metadata["length_mismatch"] = True
    return cache_a, cache_b


def _doc_from_pair(pair: Mapping[str, Any], side: str) -> dict[str, Any]:
    return {
        "doc_id": f"{pair['pair_id']}-{side}",
        "pair_id": pair["pair_id"],
        "side": side,
        "text": pair[f"context_{side}"],
        "context": pair[f"context_{side}"],
        "query": pair.get("query", ""),
        "cluster": pair.get("cluster", ""),
    }


class PairCacheStore:
    """按 pair_id 管理教师缓存落盘、索引与哈希（§9.2）。"""

    def __init__(self, root: Path | str, *, protocol_version: str = "2.0") -> None:
        self.root = Path(root)
        self.cache_dir = self.root / "data" / "cache"
        self.store = CacheStore(self.cache_dir)
        self.protocol_version = protocol_version
        self.index_path = self.root / "data" / "cache_index.json"
        self._index: dict[str, Any] = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        return {"protocol_version": self.protocol_version, "pairs": {}}

    def save_pair(self, pair: Mapping[str, Any], cache_a: KVCache, cache_b: KVCache,
                  *, model_pair: str = "", mapper_id: str = "",
                  model_revision: str = "", dtype: str = "", kernel: str = "") -> dict[str, Any]:
        pid = str(pair["pair_id"])
        a_name, b_name = f"{pid}_A", f"{pid}_B"
        path_a = self.store.save(cache_a, a_name)
        path_b = self.store.save(cache_b, b_name)
        entry = {
            "pair_id": pid,
            "side_A": a_name,
            "side_B": b_name,
            "sha256_A": hashlib.sha256(path_a.read_bytes()).hexdigest(),
            "sha256_B": hashlib.sha256(path_b.read_bytes()).hexdigest(),
            "token_count_A": cache_a.seq_len,
            "token_count_B": cache_b.seq_len,
            "layers": cache_a.layers,
            "model_pair": model_pair,
            "mapper_id": mapper_id,
            "model_revision": model_revision,
            "dtype": dtype,
            "kernel": kernel,
            "protocol_version": self.protocol_version,
            "length_mismatch": cache_a.seq_len != cache_b.seq_len,
        }
        self._index["pairs"][pid] = entry
        self._write_index()
        return entry

    def load_pair(self, pair_id: str) -> tuple[KVCache, KVCache]:
        entry = self._index["pairs"][pair_id]
        return self.store.load(entry["side_A"]), self.store.load(entry["side_B"])

    def _write_index(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(_json(self._index), encoding="utf-8")

    def check_no_cross_contamination(self, train_ids: Sequence[str], test_ids: Sequence[str]) -> dict[str, Any]:
        """训练/测试缓存哈希无交叉检查（方案 §9.3 自动测试 ⑦）。"""
        train = set(train_ids) & set(self._index["pairs"])
        test = set(test_ids) & set(self._index["pairs"])
        train_hash = {self._index["pairs"][p]["sha256_A"] for p in train}
        test_hash = {self._index["pairs"][p]["sha256_A"] for p in test}
        overlap = train_hash & test_hash
        return {
            "train_pairs": len(train),
            "test_pairs": len(test),
            "overlap_hashes": sorted(overlap),
            "passed": not overlap,
        }
