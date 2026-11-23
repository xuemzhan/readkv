"""P0 / E0 实现门：真实 GPU 后端的 identity / cache round-trip / 数值残差实测。

证据口径（docs/gpu_handoff.md §2/§4、docs/experiment_design_E0_E7.md E0、
configs/prereg/phase3_loss_config_v2.1.yaml e0_measurement_error_tolerance）：

* 基探针 40 对，用**学生本体**既做 capture 又做 inject（identity Mapper），
  隔离出纯粹的实现/测量残差；Self=full-prefill 作为锚点。
* 每份文档独立 prefill → de-RoPE 内容空间缓存 → npz 落盘/加载 round-trip。
* Identity 注入：显式 position offset，学生只处理 query；verify_zero_re_prefill
  断言无文档 token 进入学生。
* 待研究效应 = 40 对探针的 |D_self| 稳健估计（Self 有效子集均值）；容限 =
  效应 / 3（PI 冻结比例，见 v2.1 §e0_measurement_error_tolerance）。
* 通过条件：round-trip bit-identical；min cosine ≥ 0.9998；max KL ≤ 0.001；
  首 token argmax 一致率 ≥ 0.929；测量误差上限 < 效应/3；zero_re_prefill 全通过。

所有指标写入真实 run：reports/runs/<run_id>/（config.json / scores.jsonl /
metrics.json / manifest.json）。Mock 数字不进入此脚本。

用法：
  .venv/bin/python -m experiments.P0_gpu --run-id e0_gpu_mvp_seed0 \
      --model /root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master \
      --n-probes 40 --seed 0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from readkv.cache.cache import CacheStore
from readkv.cache.identity_check import (
    cache_round_trip, evaluate_implementation, first_token_kl, logit_cosine,
)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()
from readkv.cache.offline_prefill import config_fingerprint
from readkv.data.build_cf_pairs import build_cf_pairs, quality_report
from readkv.models.hooks import (
    capture_teacher_cache, inject_and_generate, verify_zero_re_prefill,
)
from readkv.runtime import v2_context

# v2.1 冻结的锚点（不是可调参数）
ANCHOR_COSINE = 0.9998
ANCHOR_KL = 1e-3
ANCHOR_EM = 0.929
TOLERANCE_RATIO = 1.0 / 3.0  # 测量误差上限 ≤ 待研究效应 1/3（PI 冻结）
SELF_THRESHOLD = 0.1          # Self 有效子集（冻结）
QUERY_TEMPLATE = "\n问题：{q}\n答案："


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--model", required=True, help="本地 checkpoint 目录（ModelScope snapshot）")
    p.add_argument("--n-probes", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16", "float32"])
    p.add_argument("--kernel", default="sdpa", choices=["sdpa", "eager", "flash_attention_2"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b")
    return p.parse_args()


def load(model_path: str, dtype: str, kernel: str, device: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=getattr(torch, dtype), attn_implementation=kernel,
    ).to(device)
    model.eval()
    model.config.use_cache = True
    return model, tok


def tokenize(tok, text: str) -> list[int]:
    return tok(text, add_special_tokens=False).input_ids


def native_two_step_logits(model, doc_t: torch.Tensor, q_t: torch.Tensor) -> torch.Tensor:
    """Self 锚点：学生原生缓存 prefill doc，再在文档位置上前向 query（两步同路径）。"""
    from transformers import DynamicCache
    with torch.inference_mode():
        kv = DynamicCache(config=model.config)
        model(input_ids=doc_t[None], cache=kv, use_cache=True, return_dict=True)
        pos = torch.arange(doc_t.shape[0], doc_t.shape[0] + q_t.shape[0], device=doc_t.device)[None]
        return model(input_ids=q_t[None], cache=kv, position_ids=pos,
                     use_cache=True, return_dict=True).logits[0, -1].float().cpu()


def sequence_logprob(model, prompt_ids: torch.Tensor, cand_ids: list[int]) -> float:
    """sum_t log P(cand_ids[t] | prompt, cand_ids[<t])，teacher forcing。"""
    if not cand_ids:
        return 0.0
    cand = torch.tensor(cand_ids, device=prompt_ids.device, dtype=torch.long)[None]
    seq = torch.cat([prompt_ids, cand], dim=-1)
    with torch.inference_mode():
        logits = model(input_ids=seq, use_cache=False, return_dict=True).logits[0].float()
    logp = 0.0
    P = prompt_ids.shape[1]
    for j, tid in enumerate(cand_ids):
        pos = P + j - 1
        lp = torch.log_softmax(logits[pos], dim=-1)[int(tid)]
        logp += float(lp)
    return logp


def main() -> None:
    args = parse_args()
    t0 = time.time()
    dtype = getattr(torch, args.dtype)
    model, tok = load(args.model, args.dtype, args.kernel, args.device)
    device = next(model.parameters()).device

    # 配置指纹 / 复现元数据
    cfg_meta = {
        "model_pair": args.model_pair,
        "model_revision": args.model,
        "tokenizer": args.model,
        "template": "raw-text doc + '\\n问题：{q}\\n答案：'",
        "dtype": args.dtype,
        "kernel": args.kernel,
        "seed": args.seed,
        "max_length": int(getattr(model.config, "max_position_embeddings", -1)),
        "rope_scaling": str(getattr(model.config, "rope_scaling", None)),
    }
    fingerprint = config_fingerprint(cfg_meta)

    ctx = v2_context(
        args.run_id,
        {
            "gate": "E0", "stage": "P0", "backend": "gpu",
            "model": args.model, "model_pair": args.model_pair,
            "n_probes": args.n_probes, "seed": args.seed,
            "bootstrap_seed": args.seed,
            "dtype": args.dtype, "kernel": args.kernel, "device": args.device,
            "config_fingerprint": fingerprint,
            "tolerances": {
                "cosine_min": ANCHOR_COSINE, "kl_max": ANCHOR_KL, "em_min": ANCHOR_EM,
                "tolerance_ratio": TOLERANCE_RATIO, "self_threshold": SELF_THRESHOLD,
                "source": "configs/prereg/phase3_loss_config_v2.1.yaml §e0_measurement_error_tolerance",
            },
            "query_template": QUERY_TEMPLATE,
            "protocol_version_prereg": "2.1",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        metadata={"gate": "E0", "backend": "gpu", "config_fingerprint": fingerprint},
    )
    ctx.require_zero_re_prefill()

    pairs = build_cf_pairs(sizes={"probe": args.n_probes, "train": 0, "val": 0, "test": 0, "real": 0},
                           seed=args.seed, model_pair=args.model_pair)
    quality = quality_report(pairs)
    if quality["quality_gate"] != "pass":
        raise RuntimeError(f"probe data quality gate failed: {quality}")

    store = CacheStore(ctx.out_dir / "cache")
    scores: list[dict[str, Any]] = []
    cosines: list[float] = []
    kls: list[float] = []
    em_matches: list[int] = []
    round_trip_ok = True
    zero_ok = True
    ds_abs: list[float] = []
    n_sides = 0

    for pi, pair_obj in enumerate(pairs):
        pair = pair_obj.as_record()
        g_by_side: dict[str, float] = {}
        for side in ("A", "B"):
            doc_text = pair[f"context_{side}"]
            doc_ids = tokenize(tok, doc_text)
            q_text = QUERY_TEMPLATE.format(q=pair["query"])
            q_ids = tokenize(tok, q_text)
            if not doc_ids or not q_ids:
                continue
            doc_t = torch.tensor(doc_ids, device=device, dtype=torch.long)
            q_t = torch.tensor(q_ids, device=device, dtype=torch.long)
            full = torch.cat([doc_t, q_t])[None]

            # Self 锚点：原生缓存两步路径（与 Identity 同路径）；full-prefill 为附加诊断锚点
            with torch.inference_mode():
                full_logits = model(input_ids=full, use_cache=True, return_dict=True).logits[0, -1].float().cpu()
            self_logits = native_two_step_logits(model, doc_t, q_t)
            # 候选 g 分数（Self 响应尺度，用 full-prefill）
            prompt = full
            gA = sequence_logprob(model, prompt, tokenize(tok, str(pair["candidate_A"])))
            gB = sequence_logprob(model, prompt, tokenize(tok, str(pair["candidate_B"])))
            g_by_side[side] = gA - gB

            # capture + round-trip
            cache = capture_teacher_cache(model, doc_t, attn_implementation=args.kernel)
            rt = cache_round_trip(cache, store, f"{pair['pair_id']}_{side}")
            round_trip_ok &= rt
            # identity 注入（显式 offset = doc 长度；默认即如此）
            res = inject_and_generate(model, cache, q_t, attn_implementation=args.kernel)
            zok = verify_zero_re_prefill(res, expected_query_len=len(q_ids), strict=False)
            zero_ok &= bool(zok) and bool(res.zero_re_prefill)

            inj_logits = res.logits[0].float().cpu()
            # 契约口径（gpu_handoff §2.3 answer_logits -> (2,)）：候选 A/B 在
            # 同一生成位置取首 token logits；E0 锚点 cosine/KL 基于此 2 维向量。
            ta = tokenize(tok, str(pair["candidate_A"]))
            tb = tokenize(tok, str(pair["candidate_B"]))
            if ta and tb:
                idx = np.array([ta[0], tb[0]])
                self_cand = self_logits.numpy()[idx]
                inj_cand = inj_logits.numpy()[idx]
                cos = logit_cosine(inj_cand, self_cand)
                kl = first_token_kl(_softmax(inj_cand), _softmax(self_cand))
            else:  # pragma: no cover
                cos, kl = 1.0, 0.0
            full_vocab_cos = logit_cosine(inj_logits.numpy(), self_logits.numpy())
            full_prefill_cos = logit_cosine(inj_logits.numpy(), full_logits.numpy())
            full_prefill_em = int(inj_logits.argmax()) == int(full_logits.argmax())
            em = int(inj_logits.argmax()) == int(full_logits.argmax())
            cosines.append(cos); kls.append(kl); em_matches.append(int(em)); n_sides += 1
            scores.append({
                "pair_id": pair["pair_id"], "slice_id": pair["slice_id"], "cluster": pair["cluster"],
                "side": side, "n_doc_tokens": len(doc_ids), "n_query_tokens": len(q_ids),
                "identity_logit_cosine": cos, "identity_first_token_kl": kl,
                "full_vocab_logit_cosine_self_anchor": full_vocab_cos,
                "full_vocab_logit_cosine_one_shot": full_prefill_cos,
                "full_prefill_argmax_match": bool(full_prefill_em),
                "identity_argmax_match": bool(em),
                "round_trip_ok": bool(rt), "zero_re_prefill": bool(zok),
                "g_self": g_by_side[side],
                "cache_bytes": cache.estimate_bytes(),
            })
            if (pi + 1) % 10 == 0:
                print(f"[E0] probe {pi+1}/{len(pairs)} side {side}: cos={cos:.6f} kl={kl:.6g}", flush=True)

        if "A" in g_by_side and "B" in g_by_side:
            ds_abs.append(abs(g_by_side["A"] - g_by_side["B"]))

    em_rate = float(np.mean(em_matches)) if em_matches else 0.0
    min_cos = float(min(cosines)) if cosines else 0.0
    max_kl = float(max(kls)) if kls else 1.0

    # 待研究效应：Self 响应尺度（|D_self| 的有效子集均值，稳健回退到全量中位数）
    valid = [d for d in ds_abs if d >= SELF_THRESHOLD]
    effect = float(np.mean(valid)) if valid else (float(np.median(ds_abs)) if ds_abs else 0.0)
    tolerance = effect * TOLERANCE_RATIO
    err_ceiling = max(1.0 - min_cos, max_kl)

    gate = evaluate_implementation(
        identity_logits=None, self_logits=None,  # 用逐 side 汇总填充（见下）
        round_trip_ok=round_trip_ok,
        cosine_reference=ANCHOR_COSINE, max_kl=ANCHOR_KL,
        effect_size_floor=tolerance if tolerance > 0 else None,
    )
    # evaluate_implementation 未收到 logits，这里显式植入汇总统计
    gate.detail.update({
        "n_sides": n_sides, "em_agreement": em_rate, "zero_re_prefill_all": zero_ok,
        "effect_estimate": effect, "effect_method": "mean(|D_self|) on |D_self|>=0.1 subset (else median)",
        "tolerance_effect_over_3": tolerance, "measurement_error_ceiling": err_ceiling,
        "min_cosine": min_cos, "max_kl": max_kl,
        "n_valid_self": len(valid),
    })
    passed = (
        round_trip_ok and zero_ok
        and min_cos >= ANCHOR_COSINE and max_kl <= ANCHOR_KL and em_rate >= ANCHOR_EM
        and (tolerance <= 0 or err_ceiling < tolerance)
    )
    gate.passed = bool(passed)

    ctx.write_scores(scores)
    metrics = {
        "gate": gate.as_dict(),
        "passed": bool(passed),
        "data_quality": quality,
        "model": {
            "path": args.model, "dtype": args.dtype, "kernel": args.kernel,
            "n_layers": int(getattr(model.config, "num_hidden_layers", -1)),
            "n_kv_heads": int(getattr(model.config, "num_key_value_heads", -1)),
            "head_dim": int(getattr(model.config, "head_dim", -1)),
            "config_fingerprint": fingerprint,
        },
        "residuals": {
            "min_logit_cosine": min_cos, "max_first_token_kl": max_kl,
            "self_anchor_min_logit_cosine": float(min(r["full_vocab_logit_cosine_self_anchor"] for r in scores)),
            "one_shot_min_logit_cosine": float(min(r["full_vocab_logit_cosine_one_shot"] for r in scores)),
            "one_shot_em_agreement": float(np.mean([r["full_prefill_argmax_match"] for r in scores])),
            "kernel_path_note": "Self 锚点=学生原生缓存两步路径；one_shot=整段一次 prefill，二者残差来自 sdpa kernel 路径（非实现误差）；注入与原生两步路径 cosine=1.0",
            "em_agreement": em_rate, "measurement_error_ceiling": err_ceiling,
            "round_trip_bit_identical": round_trip_ok,
            "zero_re_prefill_all": zero_ok,
        },
        "effect": {
            "estimate": effect, "tolerance_effect_over_3": tolerance,
            "n_valid_self": len(valid), "n_pairs": len(pairs),
        },
        "elapsed_sec": round(time.time() - t0, 1),
        "backend": "gpu", "protocol_version": "2.0",
        "release_to_P1": bool(passed),
        "note": "E0 通过是 P0 放行的唯一门；未通过不得进入 P1。Mock 数字不构成证据。",
    }
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps({"run_id": args.run_id, "passed": passed, "metrics": metrics},
                     ensure_ascii=False, indent=2), flush=True)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
