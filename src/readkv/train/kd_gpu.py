"""真实 GPU 上的 kd_only / CF-RCT-lite 训练（冻结学生，只训 KV Mapper）。

与 mock 后端 train/cf_rct.py 同损失骨架，但把可微 candidate readout 换成冻结学生的
真实前向：映射后的内容空间 K/V 经学生位置 re-RoPE 写入 DynamicCache，学生只前向
query token，首 token logits 取 query 末位。梯度经映射缓存回传到 gθ，学生主权重冻结。

方法：
  * kd_only : L = λ_KD·L_KD                         （primary baseline, configs/eval.yaml）
  * cf_lite : L = λ_KD·L_KD + λ_CF·mean_{|D_self|>=0.1} Huber_δ(D_trans − D_self)

Oracle Self 锚点在 no_grad 下离线预计算，不进 Joint 推理图，不读封存 test。
"""

from __future__ import annotations

import random
from typing import Any, Mapping, Sequence

import torch

from readkv.cache.cache import KVCache
from readkv.data.build_cf_pairs import CFPair
from readkv.models.cf_rct import CFRCTMapper, CFRCTModule
from readkv.models.hooks import _apply_rope, _rope_cos_sin
from readkv.train.cf_rct import _correct_index, _g, _huber, _init_module, _pair_dict


def _pair_dict_safe(pair: Any) -> dict[str, Any]:
    return _pair_dict(pair)


def _gpu_candidate_logits(
    model: Any,
    mapped: Mapping[int, tuple[torch.Tensor, torch.Tensor]],
    q_ids: Sequence[int],
    cand_idx: Sequence[int],
    *,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """可微的 (2,) 候选 logits；mapped 为内容空间 K/V（H,T,d，fp32，带梯度）。"""
    from transformers import DynamicCache

    doc_len = next(iter(mapped.values()))[0].shape[1]
    doc_pos = torch.arange(doc_len, device=device)[None]
    cos, sin = _rope_cos_sin(model, doc_pos, dtype=torch.float32)
    kv = DynamicCache(config=model.config)
    for layer in sorted(mapped):
        k, v = mapped[layer]
        k, v = k.to(device=device), v.to(device=device)
        k_roped = _apply_rope(k.unsqueeze(0), cos, sin).to(dtype=dtype)
        kv.update(k_roped, v.unsqueeze(0).to(dtype=dtype), layer)
    q_t = torch.as_tensor(list(q_ids), device=device, dtype=torch.long).unsqueeze(0)
    q_pos = (torch.arange(len(q_ids), device=device) + doc_len).unsqueeze(0)
    logits = model(
        input_ids=q_t, cache=kv, position_ids=q_pos, use_cache=True, return_dict=True
    ).logits[0, -1].float()
    idx = torch.as_tensor(list(cand_idx), device=device, dtype=torch.long)
    return logits[idx]


def _cand_first_tokens(tok: Any, candidates: Sequence[str]) -> list[int]:
    out = []
    for c in candidates:
        ids = tok(str(c), add_special_tokens=False).input_ids
        out.append(ids[0] if ids else 0)
    return out


def train_kd_gpu(
    backend: Any,
    cal_pairs: Sequence[CFPair],
    *,
    method: str = "kd",             # kd / cf_lite
    epochs: int = 8,
    lr: float = 1e-3,
    lam_kd: float = 1.0,
    lam_cf: float = 1.0,
    lam_reg: float = 1e-4,
    huber_delta: float = 1.0,
    self_threshold: float = 0.1,
    seed: int = 0,
) -> CFRCTMapper:
    """训练返回可被 run_cf_pipeline 直接使用的 mapper（method 写入模块属性）。"""
    if method not in ("kd", "cf_lite"):
        raise ValueError("method must be kd / cf_lite (GPU baseline trainer)")
    torch.manual_seed(seed)
    random.seed(seed)

    student = backend.student
    device = next(student.parameters()).device
    dtype = next(student.parameters()).dtype
    tok = backend.tok_s

    module = _init_module(backend, cal_pairs, rank=0)
    setattr(module, "method", method)
    optimizer = torch.optim.Adam(module.parameters(), lr=lr)

    # 预计算：教师缓存（训练时映射）+ 学生原生 Self 的候选 logits（离线锚点，no_grad）
    prepared: list[dict[str, Any]] = []
    with torch.no_grad():
        for pair_obj in cal_pairs:
            pair = _pair_dict_safe(pair_obj)
            q_ids = tok(str(pair["query"]), add_special_tokens=False).input_ids
            cand_idx = _cand_first_tokens(tok, (pair["candidate_A"], pair["candidate_B"]))
            entry: dict[str, Any] = {"pair": pair, "q_ids": q_ids, "cand_idx": cand_idx, "teachers": {}}
            for side in ("A", "B"):
                t = backend.pair_side_cache(pair, side, "teacher")
                s = backend.pair_side_cache(pair, side, "student")
                entry["teachers"][side] = t
                s_native = {
                    l: (
                        torch.as_tensor(s.keys[l], device=device, dtype=torch.float32),
                        torch.as_tensor(s.values[l], device=device, dtype=torch.float32),
                    )
                    for l in s.layers
                }
                entry[f"self_logits_{side}"] = _gpu_candidate_logits(
                    student, s_native, q_ids, cand_idx, device=device, dtype=dtype
                )
            ds = _g(entry["self_logits_A"]) - _g(entry["self_logits_B"])
            entry["d_self"] = ds
            entry["mask"] = torch.tensor(float(abs(float(ds)) >= self_threshold))
            prepared.append(entry)

    module.train()
    for epoch in range(epochs):
        order = list(range(len(prepared)))
        random.Random(seed + epoch).shuffle(order)
        for i in order:
            e = prepared[i]
            optimizer.zero_grad()
            mapped_a = module.map_cache(e["teachers"]["A"])
            mapped_b = module.map_cache(e["teachers"]["B"])
            trans_a = _gpu_candidate_logits(student, mapped_a, e["q_ids"], e["cand_idx"],
                                            device=device, dtype=dtype)
            trans_b = _gpu_candidate_logits(student, mapped_b, e["q_ids"], e["cand_idx"],
                                            device=device, dtype=dtype)

            l_kd = torch.nn.functional.kl_div(
                torch.log_softmax(trans_a, dim=-1), torch.log_softmax(e["self_logits_A"], dim=-1),
                log_target=True, reduction="batchmean",
            ) + torch.nn.functional.kl_div(
                torch.log_softmax(trans_b, dim=-1), torch.log_softmax(e["self_logits_B"], dim=-1),
                log_target=True, reduction="batchmean",
            )
            loss = lam_kd * l_kd + lam_reg * module.regularization()
            if method == "cf_lite" and lam_cf > 0:
                d_trans = _g(trans_a) - _g(trans_b)
                l_cf = _huber(d_trans - e["d_self"], huber_delta) * e["mask"]
                loss = loss + lam_cf * l_cf
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
            optimizer.step()

    module.eval()
    setattr(module, "method", method)
    setattr(module, "huber_delta", float(huber_delta))
    return CFRCTMapper(module)
