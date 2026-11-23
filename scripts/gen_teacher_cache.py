"""V2 离线 Teacher 缓存生成：d_A/d_B 分别 Prefill，落盘后卸载教师。

GPU 机器上由 models/hooks.py 提供 capture_teacher_cache；本脚本的
非 dry-run 模式要求调用方通过 --prefill 模块注入真实前向（device-agnostic）。
mock 模式下可用 python -m scripts.gen_teacher_cache --backend mock 做接线验证。
"""

from __future__ import annotations

import argparse
import json

from readkv.cache.cache import estimate_bytes_per_token
from readkv.config import load_config, resolve_pair
from readkv.data.build_cf_pairs import build_cf_pairs
from readkv.models.mock_backend import MockBackend, MockSpec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", default="qwen3-4b-to-1.7b")
    parser.add_argument("--backend", choices=["mock", "gpu"], default="mock")
    parser.add_argument("--n-pairs", type=int, default=None, help="反事实文档对数量")
    parser.add_argument("--tokens-per-doc", type=int, default=512)
    parser.add_argument("--teacher-model", default=None, help="GPU 后端教师 checkpoint 本地路径")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--kernel", default="sdpa")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", default="data/cache")
    parser.add_argument("--dry-run", action="store_true", help="只估算体积与层映射")
    args = parser.parse_args()

    protocol = load_config("protocol")
    sizes = dict(protocol["data_sizes"])
    if args.n_pairs is not None:
        sizes["test"] = args.n_pairs
    pairs = build_cf_pairs(sizes={"probe": 0, "train": 0, "val": 0,
                                  "test": sizes["test"], "real": 0}, seed=args.seed)

    # 体积估算（V2：0.6B/1.7B 112KiB/token，4B/8B 144KiB/token）
    model_ids = {
        "qwen3-1.7b-to-0.6b": ("1.7B", "0.6B"),
        "qwen3-4b-to-1.7b": ("4B", "1.7B"),
        "qwen3-8b-to-0.6b": ("8B", "0.6B"),
    }
    teacher_id, student_id = model_ids.get(args.pair, ("4B", "1.7B"))
    models = load_config("models")["models"]
    tcfg = models.get(teacher_id, {"n_layers": 36, "n_kv_heads": 8, "head_dim": 128})
    bytes_per_token = estimate_bytes_per_token(tcfg)
    n_docs = len(pairs) * 2  # 每对两份文档
    plan = {
        "pair": args.pair,
        "teacher": teacher_id,
        "student": student_id,
        "n_layers": tcfg["n_layers"],
        "bytes_per_token_estimate": bytes_per_token,
        "n_pairs": len(pairs),
        "n_docs": n_docs,
        "tokens_per_doc": args.tokens_per_doc,
        "total_gib_estimate": round(bytes_per_token * n_docs * args.tokens_per_doc / (1024**3), 2),
        "teacher_offline_only": True,
        "separate_prefill_per_side": True,
        "backend": args.backend,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    if args.backend == "mock":
        from readkv.cache.offline_prefill import PairCacheStore, prefill_pair
        backend = MockBackend(MockSpec(seed=args.seed))
        store = PairCacheStore(args.out_dir)
        for p in pairs:
            ca, cb = prefill_pair(lambda doc: backend.cache(doc, "teacher"), p.as_record())
            store.save_pair(p.as_record(), ca, cb, model_pair=args.pair)
        print(f"saved {len(pairs)} pairs to {args.out_dir}")
        return

    if not args.teacher_model:
        raise ValueError("--backend gpu requires --teacher-model <local checkpoint>")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from readkv.models.hooks import capture_teacher_cache

    tok = AutoTokenizer.from_pretrained(args.teacher_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.teacher_model, dtype=getattr(torch, args.dtype), attn_implementation=args.kernel
    ).to("cuda").eval()
    model.config.use_cache = True
    store = PairCacheStore(args.out_dir, protocol_version="2.0")

    def prefill(doc):
        ids = tok(str(doc.get("text", "")), add_special_tokens=False).input_ids
        return capture_teacher_cache(model, torch.tensor(ids, device="cuda", dtype=torch.long),
                                     attn_implementation=args.kernel)

    from readkv.cache.offline_prefill import prefill_pair
    for p in pairs:
        rec = p.as_record()
        ca, cb = prefill_pair(prefill, rec)
        store.save_pair(rec, ca, cb, model_pair=args.pair,
                        model_revision=args.teacher_model,
                        dtype=args.dtype, kernel=args.kernel)
    # 教师随即卸载
    del model
    torch.cuda.empty_cache()
    print(f"saved {len(pairs)} pairs (GPU backend) to {args.out_dir}; teacher unloaded")


if __name__ == "__main__":
    main()
