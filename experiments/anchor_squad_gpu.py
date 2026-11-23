"""SQuAD v2.0 dev 外部锚点评测（v2.4，仅评测，不恢复任何贡献）。

目的：检验 affine 迁移失败边界是否跨数据源成立，并为 E_CF 提供标准 QA 外部锚点。
**不是**合成主终点重跑；锚点 scores 与合成 test 严格分离，不混算、不重算已冻结 CI。

每个 run 在同一确定性 answerable 子集上评测两臂：
  - self    : 学生原生缓存 prefill（Identity 路径），标准 QA 上限参考；
  - joint   : 教师独立 prefill 文档 → mapper 映射到学生 → 学生只前向 query（zero re-prefill）。

用法：
  .venv/bin/python -m experiments.anchor_squad_gpu --run-id anchor_squad_affine_seed0 \\
      --teacher <1.7B> --student <0.6B> --method affine --seed 0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
import time
from pathlib import Path
from typing import Any

import torch

from readkv.cache.cache import KVCache
from readkv.config import load_config
from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.hooks import capture_teacher_cache, inject_and_generate, verify_zero_re_prefill
from readkv.models.layer_map import LayerMap
from readkv.runtime import v2_context
from readkv.train.kd_gpu import train_kd_gpu

ANCHOR_FILE = Path("/root/readkv/data/anchors/squad/dev-v2.0.json")
ANCHOR_SHA256 = "80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--teacher", required=True)
    p.add_argument("--student", required=True)
    p.add_argument("--method", required=True, choices=["affine", "kd"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--n-examples", type=int, default=240, help="answerable 确定性子集大小")
    p.add_argument("--max-new-tokens", type=int, default=16)
    p.add_argument("--smoke", action="store_true", help="小规模接线验证（non-authoritative）")
    return p.parse_args()


def load(path, dtype, kernel, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                             attn_implementation=kernel).to(device)
    m.eval(); m.config.use_cache = True
    return m, tok


def normalize_answer(s: str) -> str:
    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = remove_articles(s)
    return " ".join(s.split())


def get_examples(path: Path, n: int) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for article in data["data"]:
        title = article["title"]
        for para in article["paragraphs"]:
            context = para["context"]
            for qa in para["qas"]:
                if qa.get("is_impossible") or not qa.get("answers"):
                    continue  # 只用 answerable；unanswerable 不计入 EM（v2.4 仅评测、可比性优先）
                out.append({
                    "example_id": qa["id"], "title": title, "cluster": title,
                    "context": context, "question": qa["question"],
                    "answer": qa["answers"][0]["text"],
                })
    return out[:n]


def qids(tok, text: str, device) -> torch.Tensor:
    return torch.tensor(tok(text, add_special_tokens=False).input_ids, device=device, dtype=torch.long)


def em_f1(pred: str, gold: str) -> tuple[float, float]:
    p, g = normalize_answer(pred), normalize_answer(gold)
    em = float(p == g)
    pt, gt = p.split(), g.split()
    if not pt or not gt:
        return em, float(not pt and not gt)
    common = sum((__import__("collections").Counter(pt) & __import__("collections").Counter(gt)).values())
    prec = common / len(pt); rec = common / len(gt)
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return em, f1


def main() -> None:
    args = parse_args()
    t0 = time.time()
    file_sha = hashlib.sha256(ANCHOR_FILE.read_bytes()).hexdigest()
    if file_sha != ANCHOR_SHA256:
        raise RuntimeError(f"anchor sha mismatch: {file_sha} != {ANCHOR_SHA256}")

    tm, tt = load(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load(args.student, args.dtype, args.kernel, args.device)
    for m in (tm, sm):
        for p in m.parameters():
            p.requires_grad_(False)
    n_s = int(sm.config.num_hidden_layers); n_t = int(tm.config.num_hidden_layers)
    lmap = LayerMap(n_s, n_t, kind="identity" if n_s == n_t else "proportional")
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)

    # mapper：与干净 P1 同预算同数据（合成 train；锚点只用于评测）
    ev = load_config("eval")
    pairs = build_cf_pairs(sizes={"train": 120, "val": 60, "test": 300, "probe": 40, "real": 0},
                           seed=0, model_pair="qwen3-1.7b-to-0.6b")
    trains = split_pairs(pairs, "train")
    if args.method == "affine":
        cal_docs = [{"doc_id": f"{p.pair_id}-{s}", "text": getattr(p, f"context_{s}")}
                    for p in trains for s in ("A", "B")]
        ts = stack_caches(backend, cal_docs, "teacher")
        ss = stack_caches(backend, cal_docs, "student")
        mapper = AffineMapper(lam=1e-3, channel="both").fit(ts, ss, layer_map=lmap)
        mapper_kind = "affine"
    else:
        mapper = train_kd_gpu(backend, trains, method="kd", epochs=8, lr=1e-3,
                              lam_kd=1.0, lam_reg=1e-4, seed=0)
        mapper_kind = "kd_only"
    train_info = {"method": args.method, "epochs": 8 if args.method == "kd" else 0,
                  "seed": 0, "trainable_params": sum(
                      p.numel() for p in (mapper.module.parameters() if hasattr(mapper, "module") else []))}

    examples = get_examples(ANCHOR_FILE, 8 if args.smoke else args.n_examples)
    rows: list[dict[str, Any]] = []
    zero_ok = True
    for ex in examples:
        ctx_ids = qids(tt, ex["context"], args.device)
        t_cache = capture_teacher_cache(tm, ctx_ids, lmap, attn_implementation=args.kernel)
        s_cache = capture_teacher_cache(sm, ctx_ids, None, attn_implementation=args.kernel)
        mapped = mapper.transform(t_cache)
        prompt = f"Question: {ex['question']}\nAnswer:"
        q_tok = qids(st, prompt, args.device)
        for arm, cache in (("self", s_cache), ("joint", mapped)):
            res = inject_and_generate(sm, cache, q_tok, max_new_tokens=args.max_new_tokens,
                                      attn_implementation=args.kernel)
            zero_ok &= bool(verify_zero_re_prefill(res, expected_query_len=int(q_tok.shape[0]), strict=False))
            gen_ids = res.generated_ids[0] if res.generated_ids is not None else res.logits.argmax(-1)[None]
            pred = st.decode(gen_ids.tolist(), skip_special_tokens=True).strip()
            em, f1 = em_f1(pred, ex["answer"])
            rows.append({
                "example_id": ex["example_id"], "pair_id": ex["example_id"], "split": "anchor_squad_dev",
                "cluster": ex["cluster"], "title": ex["title"], "arm": arm, "method": mapper_kind,
                "EM": em, "F1": f1, "pred": pred[:200], "gold": ex["answer"][:200],
            })

    from collections import defaultdict
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    summary = {arm: {"n": len(v), "EM": sum(r["EM"] for r in v) / max(len(v), 1),
                     "F1": sum(r["F1"] for r in v) / max(len(v), 1)}
               for arm, v in by_arm.items()}

    ctx = v2_context(
        args.run_id,
        {
            "stage": "external_anchor", "gate": "SQuAD_v2.0_dev", "backend": "gpu",
            "anchor_protocol_version": "2.4", "protocol_version": "2.4",
            "anchor_benchmark": "SQuAD v2.0 dev", "anchor_license": "CC BY-SA 4.0",
            "anchor_usage": "evaluation_only (no rewriting, no derived corpus release)",
            "anchor_file": str(ANCHOR_FILE), "anchor_file_sha256": file_sha,
            "data_sha256": file_sha,
            "method": args.method, "mapper_kind": mapper_kind,
            "teacher": args.teacher, "student": args.student, "seed": args.seed,
            "dtype": args.dtype, "kernel": args.kernel, "zero_re_prefill": True,
            "n_examples": len(examples), "max_new_tokens": args.max_new_tokens,
            "synthetic_test_used": False, "training": train_info,
            "criteria_source": "configs/prereg/external_validity_v2.4.yaml (predeclared 3 scenarios)",
        },
        seed=args.seed, device=args.device, dtype=args.dtype, kernel=args.kernel,
        zero_re_prefill=True,
        reports_root=(Path("/root/readkv/reports/_non_authoritative") if args.smoke else None),
        metadata={"stage": "external_anchor", "backend": "gpu", "protocol_version": "2.4",
                  "non_authoritative": args.smoke},
    )
    ctx.write_scores(rows)
    metrics = {
        "run_id": args.run_id, "backend": "gpu", "protocol_version": "2.4",
        "anchor": "SQuAD v2.0 dev", "license": "CC BY-SA 4.0 (evaluation only)",
        "anchor_file_sha256": file_sha, "data_sha256": file_sha,
        "method": mapper_kind, "seed": args.seed, "dtype": args.dtype, "kernel": args.kernel,
        "zero_re_prefill": bool(zero_ok), "n_examples": len(examples),
        "arms": summary, "training": train_info,
        "note": "锚点仅外部效度观察；不与合成 test 混算、不重算冻结 CI、不恢复任何贡献。",
        "elapsed_sec": round(time.time() - t0, 1),
    }
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
