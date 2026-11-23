"""CF-RCT 成对训练（V2.0 方案 §7.2）。

冻结学生；教师缓存离线固定；每 batch 载入两份教师缓存 + 学生原生 Self 目标；
两次学生 Query Forward；计算

    L_total = λ_KD·L_KD + λ_CF·L_CF + λ_local·L_local + λ_reg·L_reg

反向传播只更新 Mapper。τ、Huber 阈值、标签平衡必须在验证集固定；本函数只接受
已固定的超参，不读取封存测试标签。

mock 后端提供可微的 candidate readout（backend.torch_candidate_logits），GPU 后端
需把该函数换成冻结学生的真实前向，并保持返回形状不变。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import torch
from torch import nn

from readkv.cache.cache import KVCache
from readkv.data.build_cf_pairs import CFPair
from readkv.models.cf_rct import CFRCTMapper, CFRCTModule


def _cache_to_tensors(cache: KVCache) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
    out: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
    for layer in cache.layers:
        k, v = cache.layer(layer)
        out[layer] = (
            torch.stack([torch.as_tensor(k[h], dtype=torch.float32) for h in range(k.shape[0])]),
            torch.stack([torch.as_tensor(v[h], dtype=torch.float32) for h in range(v.shape[0])]),
        )
    return out


def _g(logits: torch.Tensor) -> torch.Tensor:
    """单份缓存的 g(C,q) = log P(A) − log P(B)。"""
    lp = torch.log_softmax(logits, dim=-1)
    return lp[..., 0] - lp[..., 1]


def _correct_index(pair: CFPair | dict, side: str) -> int | None:
    pair = _pair_dict(pair)
    label = (pair["correct_A"] if side == "A" else pair["correct_B"]).strip().upper()
    if label.startswith("A") and label.startswith("B"):
        return None
    return 0 if label.startswith("A") else 1


def _huber(x: torch.Tensor, delta: float) -> torch.Tensor:
    abs_x = torch.abs(x)
    return torch.where(abs_x <= delta, 0.5 * x ** 2, delta * (abs_x - 0.5 * delta))


def _pair_dict(pair: Any) -> dict[str, Any]:
    from dataclasses import asdict
    from collections.abc import Mapping
    return dict(pair) if isinstance(pair, Mapping) else asdict(pair)


def _init_module(backend: Any, cal_pairs: Sequence[CFPair], *, rank: int = 0) -> CFRCTModule:
    """从闭式线性 ridge 初始化（d×d，无偏置行），降低训练起步风险。"""
    from readkv.evaluate.pipeline import stack_caches
    from readkv.mapper.representation import RidgeMapper

    docs = []
    for pair_obj in cal_pairs:
        pair = _pair_dict(pair_obj)
        for side in ("A", "B"):
            docs.append({
                "doc_id": f"{pair['pair_id']}-{side}",
                "text": pair["context_A"] if side == "A" else pair["context_B"],
                "query": pair["query"],
                "cluster": pair["cluster"],
            })
    teacher = stack_caches(backend, docs, "teacher")
    student = stack_caches(backend, docs, "student")
    ridge = RidgeMapper(channel="both").fit(teacher, student)
    return CFRCTModule(ridge.state_dict(), rank=rank)


def train_cf_rct(
    backend: Any,
    cal_pairs: Sequence[CFPair],
    *,
    method: str = "cf_lite",        # kd / cf_lite / cf_mech
    epochs: int = 20,
    lr: float = 1e-3,
    lam_kd: float = 1.0,
    lam_cf: float = 1.0,
    lam_local: float = 0.0,
    lam_reg: float = 1e-4,
    huber_delta: float = 1.0,
    tau: float = 1.0,
    rank: int = 0,
    mechanism_units: Sequence[Mapping[str, Any]] | None = None,
    seed: int = 0,
) -> CFRCTMapper:
    """训练 CF-RCT mapper；返回可被 cf_pipeline 直接使用的 mapper 对象。"""
    torch.manual_seed(seed)
    if method not in ("kd", "cf_lite", "cf_mech"):
        raise ValueError("method must be kd / cf_lite / cf_mech")
    if method == "kd":
        lam_cf = 0.0
        lam_local = 0.0
    elif method == "cf_lite":
        lam_local = 0.0
    # cf_mech 保留传入的 lam_local（由局部干预选出的层/Head 机制约束）

    module = _init_module(backend, cal_pairs, rank=rank)
    setattr(module, "method", method)
    optimizer = torch.optim.Adam(module.parameters(), lr=lr)

    # 预计算校准集的缓存（与 V2 一致：两份文档各自独立 Prefill）
    prepared = []
    for pair_obj in cal_pairs:
        pair = _pair_dict(pair_obj)
        ta = backend.pair_side_cache(pair, "A", "teacher")
        tb = backend.pair_side_cache(pair, "B", "teacher")
        sa = backend.pair_side_cache(pair, "A", "student")
        sb = backend.pair_side_cache(pair, "B", "student")
        prepared.append((pair, ta, tb, sa, sb))

    module.train()
    loss_log: list[float] = []
    for _ in range(epochs):
        for pair, ta, tb, sa, sb in prepared:
            optimizer.zero_grad()
            mapped_a = module.map_cache(ta)
            mapped_b = module.map_cache(tb)

            query_doc = {"doc_id": f"{pair['pair_id']}-query", "text": pair["query"]}
            candidates = (pair["candidate_A"], pair["candidate_B"])
            idx_a, idx_b = _correct_index(pair, "A"), _correct_index(pair, "B")

            # 原生 Self 目标（离线锚点，不参与梯度）
            with torch.no_grad():
                native_a = _cache_to_tensors(sa)
                native_b = _cache_to_tensors(sb)
                self_logits_a = backend.torch_candidate_logits(native_a, query_doc, candidates, correct_index=idx_a)
                self_logits_b = backend.torch_candidate_logits(native_b, query_doc, candidates, correct_index=idx_b)
                d_self = _g(self_logits_a) - _g(self_logits_b)

            trans_logits_a = backend.torch_candidate_logits(mapped_a, query_doc, candidates, correct_index=idx_a)
            trans_logits_b = backend.torch_candidate_logits(mapped_b, query_doc, candidates, correct_index=idx_b)
            d_trans = _g(trans_logits_a) - _g(trans_logits_b)

            # L_KD：单文档预测分布一致性
            p_self = torch.log_softmax(self_logits_a, dim=-1)
            p_trans = torch.log_softmax(trans_logits_a, dim=-1)
            l_kd = nn.functional.kl_div(p_trans, p_self, log_target=True, reduction="batchmean")
            p_self_b = torch.log_softmax(self_logits_b, dim=-1)
            p_trans_b = torch.log_softmax(trans_logits_b, dim=-1)
            l_kd = l_kd + nn.functional.kl_div(p_trans_b, p_self_b, log_target=True, reduction="batchmean")

            # L_CF：成对响应差保真（Huber）
            l_cf = _huber(d_trans - d_self, huber_delta)

            # L_local：机制约束（routing/消费一致）——mock 下用映射前后 V 输出差近似
            l_local = torch.tensor(0.0)
            if lam_local > 0:
                for layer in mapped_a:
                    kv_m, kv_n = mapped_a[layer], native_a[layer]
                    l_local = l_local + torch.norm(kv_m[1].mean(dim=1) - kv_n[1].mean(dim=1))
                if mechanism_units:
                    # 只约束被局部干预选出的层/Head
                    allowed = {(int(u["layer"]), int(u["head"])) for u in mechanism_units}
                    for layer in list(mapped_a):
                        for head in range(mapped_a[layer][1].shape[0]):
                            if (layer, head) not in allowed:
                                continue
                            l_local = l_local + torch.norm(
                                mapped_a[layer][1][head].mean(dim=0) - native_a[layer][1][head].mean(dim=0)
                            )

            l_reg = module.regularization()
            loss = lam_kd * l_kd + lam_cf * l_cf + lam_local * l_local + lam_reg * l_reg
            loss_log.append(float(loss.detach()))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
            optimizer.step()

    module.eval()
    setattr(module, "method", method)
    setattr(module, "train_loss_log", loss_log)
    return CFRCTMapper(module)
