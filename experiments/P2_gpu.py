"""P2 机制诊断（真实 GPU，E2）——沿用 repro 权威代码口径。

四臂（Self/K-only/V-only/Joint，仅 Joint deployable）+ 局部 Routing/Consumption
分解（d_A/d_B 分别诊断再比较差值）+ 层/头/Token Oracle 移植的 held-out 预测价值检验。
Oracle 只在离线诊断期使用，绝不进入 Joint 推理图；候选单元只用 train/val 选择。

判据来自 configs/prereg/phase3_loss_config_v2.1.yaml e2_mechanism_prediction
（v2.2 原样继承）：repair 命中率显著高于随机（簇级 paired bootstrap CI 下界>0）、
方向一致 ΔE_CF>0 占比>0.5、分解残差≈0。三者全达才称有预测价值，否则如实降级。

用法：
  .venv/bin/python -m experiments.P2_gpu --run-id p2_gpu_mvp_seed0 \
      --teacher <1.7B> --student <0.6B> --seed 0
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Callable

import numpy as np
import torch

from readkv.cache.cache import KVCache
from readkv.config import load_config
from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
from readkv.diagnostics.route_value import (
    build_four_arms, decompose_attention, oracle_transplant,
)
from readkv.evaluate.counterfactual import PairCFRecord
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.hooks import inject_and_generate, verify_zero_re_prefill
from readkv.models.layer_map import LayerMap
from readkv.runtime import v2_context
from readkv.stats.bootstrap import cluster_bootstrap


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--teacher", required=True)
    p.add_argument("--student", required=True)
    p.add_argument("--model-pair", default="qwen3-1.7b-to-0.6b")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--n-train", type=int, default=None)
    p.add_argument("--n-val", type=int, default=None)
    p.add_argument("--n-select", type=int, default=8, help="用于 Oracle 排序的训练对数量")
    p.add_argument("--n-heldout", type=int, default=40, help="独立验证对数量（与选择集不重叠）")
    p.add_argument("--top-k", type=int, default=5, help="候选机制单元数 U")
    p.add_argument("--n-resamples", type=int, default=10000)
    p.add_argument("--smoke", action="store_true", help="小规模接线验证")
    return p.parse_args()


def load(path, dtype, kernel, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                             attn_implementation=kernel).to(device)
    m.eval(); m.config.use_cache = True
    return m, tok


def pair_doc(pair: dict, side: str) -> dict:
    return {"doc_id": f"{pair['pair_id']}-{side}",
            "text": pair["context_A"] if side == "A" else pair["context_B"],
            "query": pair["query"], "cluster": pair["cluster"]}


def make_pair_caches(backend, pair: dict) -> dict[str, dict[str, KVCache]]:
    """teacher/student 两角色、A/B 两侧，各自独立 prefill。"""
    out = {}
    for role in ("teacher", "student"):
        out[role] = {s: backend.pair_side_cache(pair, s, role) for s in ("A", "B")}
    return out


def candidate_logits(backend, cache, qdoc, candidates):
    return np.asarray(backend.candidate_logits(cache, qdoc, candidates=candidates), dtype=float)


def ecf_from_logits(la, lb, correct_a, correct_b, pair_id, cluster, slice_id):
    return PairCFRecord(
        pair_id=pair_id, split="val", slice_id=slice_id, cluster=cluster,
        self_logits_A=la, self_logits_B=lb, transfer_logits_A=la, transfer_logits_B=lb,
        correct_A=correct_a, correct_B=correct_b,
    ).compute()


def pair_ecf(backend, pair, cache_a, cache_b, student_a, student_b):
    """E_CF = |D_trans − D_self|；D_self 取学生原生缓存（离线锚点），D_trans 取传入缓存。"""
    qdoc = {"doc_id": f"{pair['pair_id']}-query", "text": pair["query"], "query": pair["query"]}
    cands = (pair["candidate_A"], pair["candidate_B"])
    self_a = candidate_logits(backend, student_a, qdoc, cands)
    self_b = candidate_logits(backend, student_b, qdoc, cands)
    trans_a = candidate_logits(backend, cache_a, qdoc, cands)
    trans_b = candidate_logits(backend, cache_b, qdoc, cands)
    return PairCFRecord(
        pair_id=pair["pair_id"], split="val", slice_id=pair["slice_id"],
        cluster=pair["cluster"], self_logits_A=self_a, self_logits_B=self_b,
        transfer_logits_A=trans_a, transfer_logits_B=trans_b,
        correct_A=pair["correct_A"], correct_B=pair["correct_B"],
    ).compute()


def capture_query_states(model, doc_tokens, device):
    """学生文档 prefill 时钩取 q_norm 输出（内容空间 Q，固定 Query），形状 (H,T,d)。"""
    captured = {}
    handles = []

    def hook(module, inp, out):
        captured["q"] = out.detach().float().cpu()

    for layer in model.model.layers:
        handles.append(layer.self_attn.q_norm.register_forward_hook(hook))
    try:
        with torch.inference_mode():
            model(input_ids=doc_tokens[None], use_cache=False, return_dict=True)
    finally:
        for h in handles:
            h.remove()
    if "q" not in captured:
        raise RuntimeError("failed to capture Q via q_norm hook")
    # q_norm 输出 (B,T,H,d) -> (H,T,d)；取 batch 0
    q = captured["q"][0].permute(1, 0, 2).numpy()  # (H,T,d)
    return q


def main() -> None:
    args = parse_args()
    t0 = time.time()
    protocol = load_config("protocol"); ev = load_config("eval")
    sizes = dict(protocol["data_sizes"])
    if args.n_train is not None: sizes["train"] = args.n_train
    if args.n_val is not None: sizes["val"] = args.n_val

    tm, tt = load(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers); n_t = int(tm.config.num_hidden_layers)
    lmap = LayerMap(n_s, n_t, kind="identity" if n_s == n_t else "proportional")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)

    # 1) 校准 affine mapper（与 P1 repro 一致，只用 train）
    trains = split_pairs(build_cf_pairs(sizes=sizes, seed=args.seed,
                                        model_pair=args.model_pair), "train")
    cal_docs = [{"doc_id": f"{p.pair_id}-{s}",
                 "text": getattr(p, f"context_{s}")} for p in trains for s in ("A", "B")]
    tstack = stack_caches(backend, cal_docs, "teacher")
    sstack = stack_caches(backend, cal_docs, "student")
    mapper = AffineMapper(lam=1e-3, channel="both").fit(tstack, sstack, layer_map=lmap)

    # 2) 划分：Oracle 选择集（train 子集）与 held-out 验证集（val，不重叠）
    all_pairs = build_cf_pairs(sizes=sizes, seed=args.seed, model_pair=args.model_pair)
    val_pairs = split_pairs(all_pairs, "val")
    sel_pairs = trains[:args.n_select] if not args.smoke else trains[:2]
    held_pairs = val_pairs[:args.n_heldout] if not args.smoke else val_pairs[:4]

    forward_count = {"capture": 0, "candidate": 0, "oracle": 0}
    # ---------------- K/V 四臂（在 val 上） ----------------
    four_arm_rows = []
    arm_ecf: dict[str, list[float]] = {}
    zero_ok = True
    for pobj in held_pairs:
        pair = pobj.as_record()
        caches = make_pair_caches(backend, pair)
        mapped_a = mapper.transform(caches["teacher"]["A"])
        mapped_b = mapper.transform(caches["teacher"]["B"])
        arms = build_four_arms(student=caches["student"]["A"], mapped=mapped_a)
        arms_b = build_four_arms(student=caches["student"]["B"], mapped=mapped_b)
        qdoc = {"doc_id": f"{pair['pair_id']}-query", "text": pair["query"], "query": pair["query"]}
        cands = (pair["candidate_A"], pair["candidate_B"])
        # 四臂（A/B 两侧同一臂），每臂按 (D_trans^arm − D_self) 口径
        self_a = candidate_logits(backend, arms["self"], qdoc, cands)
        self_b = candidate_logits(backend, arms_b["self"], qdoc, cands)
        for arm in ("self", "k_only", "v_only", "joint"):
            la = candidate_logits(backend, arms[arm], qdoc, cands)
            lb = candidate_logits(backend, arms_b[arm], qdoc, cands)
            rec = PairCFRecord(
                pair_id=pair["pair_id"], split="val", slice_id=pair["slice_id"],
                cluster=pair["cluster"], self_logits_A=self_a, self_logits_B=self_b,
                transfer_logits_A=la, transfer_logits_B=lb,
                correct_A=pair["correct_A"], correct_B=pair["correct_B"],
            ).compute()
            arm_ecf.setdefault(arm, []).append(float(rec["E_CF"]))
            four_arm_rows.append({
                "pair_id": pair["pair_id"], "cluster": pair["cluster"], "arm": arm,
                "deployable": arm == "joint", "E_CF": float(rec["E_CF"]),
                "dual_correct": float(rec["dual_correct"]),
                "flip_consistency": rec["flip_consistency"],
            })
    forward_count["candidate"] = backend.n_injections

    # ---------------- Routing/Consumption 分解（d_A / d_B 分别） ----------------
    decomp_rows = []
    for pobj in held_pairs:
        pair = pobj.as_record()
        caches = make_pair_caches(backend, pair)
        mapped_a = mapper.transform(caches["teacher"]["A"])
        for side in ("A", "B"):
            student = caches["student"][side]
            mapped = mapper.transform(caches["teacher"][side])
            doc_ids = torch.tensor(tt(pair[f"context_{side}"], add_special_tokens=False).input_ids,
                                   device=args.device, dtype=torch.long)
            q_full = capture_query_states(sm, doc_ids, args.device)  # (H,T,d) 内容空间 Q
            hd = int(sm.config.head_dim); nq = int(sm.config.num_attention_heads)
            nkv = int(sm.config.num_key_value_heads); rep = nq // nkv
            for layer in mapped.layers:
                km, vm = mapped.layer(layer)
                ks, vs = student.layer(layer)
                wo_l = sm.model.layers[layer].self_attn.o_proj.weight.detach().float().cpu().numpy()
                for head in range(km.shape[0]):
                    qh = q_full[head * rep]  # GQA 组内代表 query head（内容空间）
                    wo_slice = wo_l[:, head * rep * hd:(head * rep + 1) * hd].T  # (d, hidden)
                    d = decompose_attention(
                        query=qh, k_student=ks[head], v_student=vs[head],
                        k_mapped=km[head], v_mapped=vm[head], w_o=wo_slice,
                        layer=layer, head=head,
                    )
                    decomp_rows.append({"pair_id": pair["pair_id"], "side": side, **d.as_dict()})

    # d_A / d_B 分别汇总再比较差值（不用单文档热图替代反事实差）
    da = [r for r in decomp_rows if r["side"] == "A"]
    db = [r for r in decomp_rows if r["side"] == "B"]
    max_resid = max((r["residual_norm"] for r in decomp_rows), default=0.0)
    decomp_summary = {
        "n_units": len(decomp_rows),
        "routing_norm_mean": float(np.mean([r["routing_norm"] for r in decomp_rows])) if decomp_rows else 0.0,
        "consumption_norm_mean": float(np.mean([r["consumption_norm"] for r in decomp_rows])) if decomp_rows else 0.0,
        "max_residual_norm": float(max_resid),
        "d_A_routing_mean": float(np.mean([r["routing_norm"] for r in da])) if da else 0.0,
        "d_B_routing_mean": float(np.mean([r["routing_norm"] for r in db])) if db else 0.0,
        "d_A_consumption_mean": float(np.mean([r["consumption_norm"] for r in da])) if da else 0.0,
        "d_B_consumption_mean": float(np.mean([r["consumption_norm"] for r in db])) if db else 0.0,
        "delta_routing_A_minus_B": (float(np.mean([r["routing_norm"] for r in da])) - float(np.mean([r["routing_norm"] for r in db]))) if da and db else 0.0,
        "delta_consumption_A_minus_B": (float(np.mean([r["consumption_norm"] for r in da])) - float(np.mean([r["consumption_norm"] for r in db]))) if da and db else 0.0,
        "constraint": "局部固定 Q 代数恒等式，非全模型因果分解；d_A/d_B 分别诊断再比较差值",
    }

    # ---------------- Oracle 单元排序（仅 train 选择集） ----------------
    def transplant_pair(pair, mapped_a, mapped_b, student_a, student_b, unit):
        layer, head, channel, token = unit["layer"], unit["head"], unit["channel"], unit["token"]
        fa, _ = oracle_transplant(student=student_a, mapped=mapped_a, layer=layer,
                                  head=head, token=token, channel=channel)
        fb, _ = oracle_transplant(student=student_b, mapped=mapped_b, layer=layer,
                                  head=head, token=token, channel=channel)
        return fa, fb

    def repair_delta(pair, unit):
        caches = make_pair_caches(backend, pair)
        ma = mapper.transform(caches["teacher"]["A"]); mb = mapper.transform(caches["teacher"]["B"])
        before = pair_ecf(backend, pair, ma, mb, caches["student"]["A"], caches["student"]["B"])["E_CF"]
        fa, fb = transplant_pair(pair, ma, mb, caches["student"]["A"], caches["student"]["B"], unit)
        after = pair_ecf(backend, pair, fa, fb, caches["student"]["A"], caches["student"]["B"])["E_CF"]
        return float(before - after)

    # 单元全集：层 × 头 × 通道（token=None 整头，离线 Oracle）
    units = [{"layer": l, "head": h, "channel": ch, "token": None}
             for l in range(n_s) for h in range(8) for ch in ("K", "V", "both")]
    sel_pairs_d = [p.as_record() for p in sel_pairs]
    rank_rows = []
    for pair in sel_pairs_d:
        caches = make_pair_caches(backend, pair)
        ma = mapper.transform(caches["teacher"]["A"]); mb = mapper.transform(caches["teacher"]["B"])
        before = pair_ecf(backend, pair, ma, mb, caches["student"]["A"], caches["student"]["B"])["E_CF"]
        for u in units:
            fa, fb = transplant_pair(pair, ma, mb, caches["student"]["A"], caches["student"]["B"], u)
            after = pair_ecf(backend, pair, fa, fb, caches["student"]["A"], caches["student"]["B"])["E_CF"]
            rank_rows.append({"pair_id": pair["pair_id"], "cluster": pair["cluster"],
                              "layer": u["layer"], "head": u["head"], "channel": u["channel"],
                              "token": None, "improvement": float(before - after),
                              "repair_ok": bool(after < before)})
    # 按平均改善降序选 U（只用选择集）
    agg: dict[tuple, list[float]] = {}
    for r in rank_rows:
        agg.setdefault((r["layer"], r["head"], r["channel"]), []).append(r["improvement"])
    ranked = sorted(({"layer": k[0], "head": k[1], "channel": k[2],
                      "mean_improvement": float(np.mean(v))}
                     for k, v in agg.items()), key=lambda r: r["mean_improvement"], reverse=True)
    U = [{"layer": r["layer"], "head": r["head"], "channel": r["channel"], "token": None}
         for r in ranked[:args.top_k]]

    # ---------------- held-out 独立验证（val，与选择集不重叠） ----------------
    rng = np.random.default_rng(args.seed)
    held_d = [p.as_record() for p in held_pairs]
    hit_u, hit_rand = [], []
    for pair in held_d:
        du = [repair_delta(pair, u) for u in U]
        # 随机单元集基线：同数量随机抽（不重复）
        ridx = rng.choice(len(units), size=len(U), replace=False)
        dr = [repair_delta(pair, units[int(i)]) for i in ridx]
        hit_u.append(float(np.mean([x > 0 for x in du])))
        hit_rand.append(float(np.mean([x > 0 for x in dr])))
        four_arm_rows.append({"pair_id": pair["pair_id"], "cluster": pair["cluster"],
                              "arm": "oracle_U", "delta_ecf": float(np.mean(du)),
                              "hit": hit_u[-1]})
    clusters = [p["cluster"] for p in held_d]
    diffs = [a - b for a, b in zip(hit_u, hit_rand)]
    point, low, high = cluster_bootstrap(diffs, clusters, n_resamples=args.n_resamples, seed=args.seed)
    direction_ratio = float(np.mean([h > 0.5 for h in hit_u]))
    delta_positive_ratio = float(np.mean([d > 0 for d in diffs]))
    heldout = {
        "n_heldout_pairs": len(held_d),
        "hit_u_mean": float(np.mean(hit_u)),
        "hit_random_mean": float(np.mean(hit_rand)),
        "repair_vs_random_point": float(point),
        "repair_vs_random_ci": [float(low), float(high)],
        "repair_vs_random_ci_lower_gt_0": bool(low > 0),
        "direction_consistency_ratio": direction_ratio,
        "direction_ratio_gt_half": bool(direction_ratio > 0.5),
        "delta_positive_ratio": delta_positive_ratio,
        "U_topk": U,
    }

    # ---------------- E2 三项判据总判定 ----------------
    decompose_ok = bool(max_resid < 1e-3)
    predictive = bool(low > 0 and direction_ratio > 0.5 and decompose_ok)
    judgment = {
        "repair_vs_random_ci_lower_gt_0": bool(low > 0),
        "direction_consistency_gt_0_5": bool(direction_ratio > 0.5),
        "decomposition_residual_ok": decompose_ok,
        "has_predictive_value": predictive,
        "verdict": "mechanism_predictive" if predictive else "no_predictive_value__phenomenon_report",
        "note": "三项全达方可支撑贡献(2)；未达按 protocol §8 降级现象报告，不硬升格",
    }

    # provenance / zero-re-prefill 验证：抽查一次 Joint 注入
    sample_pair = held_d[0]
    sample_caches = make_pair_caches(backend, sample_pair)
    sample_mapped = mapper.transform(sample_caches["teacher"]["A"])
    q_ids = torch.tensor(st(sample_pair["query"], add_special_tokens=False).input_ids,
                         device=args.device, dtype=torch.long)
    sample_res = inject_and_generate(sm, sample_mapped, q_ids, attn_implementation=args.kernel)
    zsample = verify_zero_re_prefill(sample_res, expected_query_len=int(q_ids.shape[0]), strict=False)

    ctx = v2_context(
        args.run_id,
        {
            "stage": "P2", "gate": "E2_mechanism", "backend": "gpu",
            "teacher": args.teacher, "student": args.student, "model_pair": args.model_pair,
            "layer_map": lmap.to_dict(), "seed": args.seed, "bootstrap_seed": args.seed,
            "seeds": [args.seed], "dtype": args.dtype, "kernel": args.kernel,
            "n_resamples": args.n_resamples, "tau": ev["tau"],
            "self_threshold": ev["self_threshold"], "sizes": sizes,
            "forward_counts": forward_count,
            "mapper": "affine", "top_k_units": args.top_k,
            "n_select_pairs": len(sel_pairs_d), "n_heldout_pairs": len(held_d),
            "criteria_source": "configs/prereg/phase3_loss_config_v2.1.yaml e2_mechanism_prediction (v2.2 inherited)",
            "oracle_isolation": "Oracle only in offline diagnosis; never in Joint inference graph",
            "transfer_broken": False,
            "quality_pass_scope": "data_quality_gate_only",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        metadata={"stage": "P2", "backend": "gpu", "protocol_version": "2.0"},
    )
    ctx.write_scores(four_arm_rows)
    payload = {
        "run_id": args.run_id, "backend": "gpu", "protocol_version": "2.0",
        "four_arms": {arm: {"E_CF_mean": float(np.mean(v)), "n": len(v)}
                      for arm, v in arm_ecf.items()},
        "decomposition": decomp_summary,
        "oracle_ranking": {"top_units": ranked[:10], "n_units_scored": len(rank_rows)},
        "heldout": heldout, "judgment": judgment,
        "zero_re_prefill": bool(zero_ok and zsample),
        "forward_counts": forward_count,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    ctx.write_metrics("mechanism.json", payload)
    ctx.write_ledger("decomposition.jsonl", decomp_rows)
    ctx.write_ledger("mechanism_units.jsonl", rank_rows)
    ctx.finalize()
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
