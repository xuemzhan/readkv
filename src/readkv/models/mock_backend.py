"""确定性 CPU mock 后端。

用途：在没有 GPU / 模型权重的机器上验证整条管线的接线：缓存生成、mapper 拟合、
四臂注入、对照、探针、门限统计、报告落盘。**mock 产生的数字不是科学证据**，
不得写入论文；它的唯一目的是让 GPU 机器上的实现可以逐一替换并回归。

设计上刻意复刻论文中的三类现象，便于验证判据逻辑：
  1. identity 注入与 student self-prefill 数值一致（cosine≈1）；
  2. 映射 V 可被 consumer-space mapper 恢复，映射 K 会扰动 routing；
  3. 任意注入缓存都抬高 teacher-forced LL（含错文档/随机/零），但只有正确内容
     才给出正确答案（LL/EM 解耦）。

契约与 models/hooks.py 相同，GPU 后端实现后通过 ``backend=...`` 注入即可。
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from readkv.cache.cache import KVCache


@dataclass
class MockSpec:
    n_layers: int = 6
    n_kv_heads: int = 2
    head_dim: int = 8
    content_rank: int = 4
    tokens_per_doc: int = 6
    n_choices: int = 4
    identity_noise: float = 1e-12   # 读出矩阵是伪逆，放大噪声；需极小才能保真
    ll_injection_bonus: float = 2.5
    readout_noise: float = 0.1
    key_noise: float = 0.15
    value_noise: float = 0.02
    # V2: 可注入的反事实失真强度（仅用于接线测试，不预设实验结论）
    cf_distortion: float = 0.0
    seed: int = 0

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any]) -> "MockSpec":
        return cls(**dict(cfg.get("spec", cfg)))


class MockBackend:
    """一个确定性的线性“模型”：文档 -> 内容向量 -> K/V -> 四选项 logits。"""

    def __init__(self, spec: MockSpec | None = None) -> None:
        self.spec = spec or MockSpec()
        rng = np.random.default_rng(self.spec.seed)
        k, d, h = self.spec.content_rank, self.spec.head_dim, self.spec.n_kv_heads
        self.w_task = rng.normal(size=(self.spec.n_choices, k))
        # teacher/student 的投影：学生 V 与教师 V 近似线性，学生 K 有更大噪声（routing 扰动）
        self.w: dict[str, dict[tuple[int, int], np.ndarray]] = {
            "teacher": {}, "student": {}, "q": {}, "read": {}, "pos": {}, "cf_read": {}
        }
        for layer in range(self.spec.n_layers):
            for head in range(h):
                kt = rng.normal(size=(d, k))
                vt = rng.normal(size=(d, k))
                av = rng.normal(size=(k, k)) + np.eye(k)
                ak = rng.normal(size=(k, k)) + np.eye(k)
                self.w["teacher"][(layer, head)] = {"K": kt, "V": vt}
                self.w["student"][(layer, head)] = {
                    "K": kt @ ak + self.spec.key_noise * rng.normal(size=(d, k)),
                    "V": vt @ av + self.spec.value_noise * rng.normal(size=(d, k)),
                }
                self.w["q"][(layer, head)] = rng.normal(size=(d, k))
                vs = self.w["student"][(layer, head)]["V"]  # (d, k)
                self.w["read"][(layer, head)] = np.linalg.pinv(vs.T) @ self.w_task.T / h  # (d, 4)
                # V2 反事实读出：把消费后的状态映射回内容空间，用候选 embedding 打分
                self.w["cf_read"][(layer, head)] = np.linalg.pinv(vs.T) / h  # (d, k)
                # 位置偏置：让 routing 变化真实影响答案，复刻 key 侧路由扰动
                self.w["pos"][(layer, head)] = rng.normal(size=(self.spec.tokens_per_doc, 4))

    # ---------- 文档与内容 ----------
    def content(self, doc: Mapping[str, Any]) -> np.ndarray:
        text = str(doc.get("text", doc.get("doc_id", "")))
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = np.frombuffer(digest[: self.spec.content_rank], dtype=np.uint8).astype(float)
        c = raw / 127.5 - 1.0
        return c / (np.linalg.norm(c) + 1e-9)

    def _tokens(self, doc: Mapping[str, Any]) -> np.ndarray:
        c = self.content(doc)
        rng = np.random.default_rng(int(hashlib.sha256(str(doc.get("doc_id", "x")).encode()).hexdigest()[:8], 16))
        noise = 0.05 * rng.normal(size=(self.spec.tokens_per_doc, self.spec.content_rank))
        return c[None, :] + noise

    # ---------- 缓存 ----------
    def cache(self, doc: Mapping[str, Any], role: str) -> KVCache:
        if role not in ("teacher", "student"):
            raise ValueError("role must be teacher or student")
        tokens = self._tokens(doc)
        keys, values = {}, {}
        for layer in range(self.spec.n_layers):
            k_rows, v_rows = [], []
            for head in range(self.spec.n_kv_heads):
                proj = self.w[role][(layer, head)]
                k_raw = tokens @ proj["K"].T
                # 学生 key 带非线性，线性 mapper 只能近似：复刻“key 侧靠重加权修不好”
                k_rows.append(np.tanh(2.0 * k_raw) if role == "student" else k_raw)
                v_rows.append(tokens @ proj["V"].T)
            keys[layer] = np.stack(k_rows)
            values[layer] = np.stack(v_rows)
        return KVCache(keys, values, {"doc_id": str(doc.get("doc_id", "")), "role": role})

    def teacher_cache(self, doc: Mapping[str, Any]) -> KVCache:
        return self.cache(doc, "teacher")

    def student_cache(self, doc: Mapping[str, Any]) -> KVCache:
        return self.cache(doc, "student")

    # ---------- 注入 ----------
    def inject(self, cache: KVCache) -> KVCache:
        """identity 注入：加极小噪声模拟数值残差，保真门限仍应通过。"""
        rng = np.random.default_rng(self.spec.seed)
        keys = {i: a + self.spec.identity_noise * rng.normal(size=a.shape) for i, a in cache.keys.items()}
        values = {i: a + self.spec.identity_noise * rng.normal(size=a.shape) for i, a in cache.values.items()}
        meta = dict(cache.metadata)
        meta["injected"] = True
        return KVCache(keys, values, meta)

    # ---------- 查询与注意力 ----------
    def query_states(self, layer: int, head: int, doc: Mapping[str, Any]) -> np.ndarray:
        tokens = self._tokens(doc)
        return tokens @ self.w["q"][(layer, head)].T

    def attention_matrices(self, cache: KVCache, doc: Mapping[str, Any]) -> dict[tuple[int, int], np.ndarray]:
        out: dict[tuple[int, int], np.ndarray] = {}
        scale = np.sqrt(self.spec.head_dim)
        for layer in cache.layers:
            for head in range(cache.keys[layer].shape[0]):
                q = self.query_states(layer, head, doc)
                scores = q @ cache.keys[layer][head].T / scale
                scores -= scores.max(axis=1, keepdims=True)
                probs = np.exp(scores)
                out[(layer, head)] = probs / probs.sum(axis=1, keepdims=True)
        return out

    # ---------- 读数与打分 ----------
    def _readout(self, values: np.ndarray, layer: int, head: int) -> np.ndarray:
        w = self.w["read"][(layer, head)]
        return values @ w  # (T, n_choices)

    def answer_logits(self, cache: KVCache, doc: Mapping[str, Any], *, arm: str = "self") -> np.ndarray:
        """注意力读出：A = softmax(Q_S @ K_cache^T)，logits ∝ Σ_h (A @ V_cache) @ W_read,h。

        这样映射 key 引起的 routing 扰动会真实传播到答案，key 侧诊断与任务臂
        才有可验证的因果链（与论文 1 的 routing/consumption 分解一致）。
        """
        total = np.zeros(self.spec.n_choices)
        count = 0
        scale = np.sqrt(self.spec.head_dim)
        for layer in cache.layers:
            v = cache.values[layer]
            for head in range(v.shape[0]):
                q = self.query_states(layer, head, doc)
                scores = q @ cache.keys[layer][head].T / scale
                scores -= scores.max(axis=1, keepdims=True)
                probs = np.exp(scores)
                attn = probs / probs.sum(axis=1, keepdims=True)
                total += (attn @ self._readout(v[head], layer, head)).mean(axis=0)
                total += (attn @ self.w["pos"][(layer, head)]).mean(axis=0)
                count += 1
        logits = total / max(count, 1)
        # 读出噪声只依赖文档，不依赖 arm：identity 注入必须与 self 完全一致，
        # 否则 H1 门测的是 mock 的随机性而不是注入保真度。
        rng = np.random.default_rng(
            int(hashlib.sha256(str(doc.get("doc_id", "")).encode()).hexdigest()[:8], 16)
        )
        logits = logits + self.spec.readout_noise * rng.normal(size=logits.shape)
        return logits

    def logits_from_mapped(self, mapped: Mapping[int, tuple[Any, Any]], gold_letter: int, doc: Mapping[str, Any] | None = None) -> Any:
        """torch 版注意力 readout，供行为目标训练使用；doc 提供学生 query。"""
        import torch

        total = torch.zeros(self.spec.n_choices)
        count = 0
        scale = np.sqrt(self.spec.head_dim)
        for layer, (k, v) in mapped.items():
            for head in range(v.shape[0]):
                w = torch.as_tensor(self.w["read"][(layer, head)], dtype=v.dtype)
                pos = torch.as_tensor(self.w["pos"][(layer, head)], dtype=v.dtype)
                if doc is None:
                    read = (v[head] @ w).mean(axis=0) + pos.mean(axis=0)
                else:
                    q = torch.as_tensor(self.query_states(layer, head, doc), dtype=v.dtype)
                    scores = q @ torch.as_tensor(k[head], dtype=v.dtype).T / scale
                    attn = torch.softmax(scores, dim=-1)
                    read = (attn @ (v[head] @ w)).mean(axis=0) + (attn @ pos).mean(axis=0)
                total = total + read
                count += 1
        return total / max(count, 1)

    def gold_letter(self, doc: Mapping[str, Any]) -> int:
        c = self.content(doc)
        return int(np.argmax(c @ self.w_task.T))

    def answer_text(self, logits: np.ndarray) -> str:
        return "ABCD"[int(np.argmax(logits))]

    def logprob(self, logits: np.ndarray, *, arm: str) -> float:
        """teacher-forced LL 代理：注入臂统一加 bonus，复刻内容无关的 LL 增益。"""
        x = np.asarray(logits, float)
        base = float(np.log(np.exp(x - x.max()).sum()) + x.max())
        return base + (self.spec.ll_injection_bonus if arm != "self" else 0.0)

    # ---------- V2: 反事实成对支持 ----------
    def pair_side_cache(self, pair: Mapping[str, Any], side: str, role: str) -> KVCache:
        """按 pair 的某一侧（A/B）独立生成缓存；绝不篡改另一侧的字节。"""
        doc = {
            "doc_id": f"{pair['pair_id']}-{side}",
            "text": pair[f"context_{side}"],
            "side": side,
            "query": pair.get("query", ""),
        }
        return self.cache(doc, role)

    def candidate_embedding(self, candidate: str) -> np.ndarray:
        """把候选字符串确定性地映射到内容空间，作为两选一打分的 embedding。"""
        digest = hashlib.sha256(str(candidate).encode("utf-8")).digest()
        raw = np.frombuffer(digest[: self.spec.content_rank], dtype=np.uint8).astype(float)
        c = raw / 127.5 - 1.0
        return c / (np.linalg.norm(c) + 1e-9)

    def _cf_vector(self, cache: KVCache, query_doc: Mapping[str, Any]) -> np.ndarray:
        """注意力读出到内容空间（与 answer_logits 同构，但用 cf_read 权重）。"""
        total = np.zeros(self.spec.content_rank)
        count = 0
        scale = np.sqrt(self.spec.head_dim)
        for layer in cache.layers:
            v = cache.values[layer]
            for head in range(v.shape[0]):
                q = self.query_states(layer, head, query_doc)
                scores = q @ cache.keys[layer][head].T / scale
                scores -= scores.max(axis=1, keepdims=True)
                probs = np.exp(scores)
                attn = probs / probs.sum(axis=1, keepdims=True)
                w = self.w["cf_read"][(layer, head)]
                total += (attn @ (v[head] @ w)).mean(axis=0)
                count += 1
        return total / max(count, 1)

    def candidate_logits(self, cache: KVCache, query_doc: Mapping[str, Any],
                         *, candidates: Sequence[str] | None = None,
                         correct_index: int | None = None,
                         correctness_bonus: float = 3.0) -> np.ndarray:
        """两选一候选 logits：内容读出内积 + 可选的正确性偏置。

        ``base`` 项由映射缓存决定（key routing / value 消费误差会传播到分数）；
        ``correct_index`` 的正确性偏置让 mock 的答题口径确定，便于验证 E_CF 判据
        接线。注入 ``cf_distortion`` 后 base 项可压过偏置，用于测试失真检测。
        """
        if candidates is None:
            candidates = ("A", "B")
        vec = self._cf_vector(cache, query_doc)
        emb = np.stack([self.candidate_embedding(c) for c in candidates])
        logits = emb @ vec / np.sqrt(max(self.spec.content_rank, 1))
        if correct_index is not None:
            if not 0 <= correct_index < len(logits):
                raise ValueError("correct_index out of range")
            logits[correct_index] += correctness_bonus
        return logits

    def torch_candidate_logits(self, mapped: Mapping[int, tuple[Any, Any]],
                               query_doc: Mapping[str, Any],
                               candidates: Sequence[str],
                               *, correct_index: int | None = None,
                               correct_bonus: float = 3.0) -> Any:
        """可微的两选一 logits，供 CF-RCT 训练（torch 张量）。"""
        import torch

        q_doc = query_doc
        emb = torch.stack([
            torch.as_tensor(self.candidate_embedding(c), dtype=torch.float32) for c in candidates
        ])
        total = torch.zeros(self.spec.content_rank, dtype=torch.float32)
        count = 0
        scale = float(np.sqrt(self.spec.head_dim))
        for layer, (k, v) in mapped.items():
            for head in range(v.shape[0]):
                q = torch.as_tensor(self.query_states(layer, head, q_doc), dtype=torch.float32)
                kt = torch.as_tensor(k[head], dtype=torch.float32)
                vt = torch.as_tensor(v[head], dtype=torch.float32)
                scores = q @ kt.T / scale
                attn = torch.softmax(scores, dim=-1)
                w = torch.as_tensor(self.w["cf_read"][(layer, head)], dtype=torch.float32)
                total = total + (attn @ (vt @ w)).mean(axis=0)
                count += 1
        vec = total / max(count, 1)
        logits = emb @ vec / float(np.sqrt(max(self.spec.content_rank, 1)))
        if correct_index is not None:
            logits[correct_index] += correct_bonus
        return logits

    def inject_counterfactual_distortion(self, cache: KVCache, *, strength: float | None = None,
                                         upstream_bias: float = 0.0) -> KVCache:
        """在映射缓存上注入可控的成对失真，用于验证 E_CF 判据接线。

        ``upstream_bias`` 为正/负时使 d_A/d_B 的响应差偏移，制造可检测的
        ``D_trans ≠ D_self``；仅用于 mock 回归，不代表任何实验结论。
        """
        s = self.spec.cf_distortion if strength is None else strength
        if s == 0.0 and upstream_bias == 0.0:
            return cache
        keys = {i: a.copy() for i, a in cache.keys.items()}
        values = {i: a.copy() for i, a in cache.values.items()}
        # 对所有层最后一个 token 的 V 施加偏置（模拟消费侧失真）
        for layer in values:
            v = values[layer]
            v[:, -1, :] += s * self.w["read"].get((layer, 0), np.eye(v.shape[-1]))[:, :v.shape[-1]].mean(axis=-1)[None, :] * upstream_bias
        meta = dict(cache.metadata)
        meta["cf_distortion_injected"] = True
        return KVCache(keys, values, meta)

