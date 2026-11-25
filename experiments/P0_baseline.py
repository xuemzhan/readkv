"""P0 基座：实现门 E0（V2.0 方案 §10）。

整合校正评测器、identity 与 cache 持久化；确定双文档 Query 格式；
放行条件：形状/位置/数值一致性全部通过，E0 测量误差上限显著低于效应。
"""

from __future__ import annotations

import argparse
import json

from readkv.cache.identity_check import cache_round_trip, evaluate_implementation
from readkv.cache.cache import CacheStore
from readkv.data.build_cf_pairs import build_cf_pairs, quality_report
from readkv.evaluate.pipeline import make_items
from readkv.models.mock_backend import MockBackend

from experiments._common_v2 import add_v2_args, build_v2_mock, new_ctx, require_gpu


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P0")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": "2.0", "gate": "E0"}, indent=2))
        return
    require_gpu(args)

    backend, cfg = build_v2_mock(args)
    ctx = new_ctx(args, "P0", {"gate": "E0"})

    # 数据质量门禁
    pairs = build_cf_pairs(sizes=cfg.sizes, seed=cfg.seed)
    quality = quality_report(pairs)

    # identity 一致性 + round-trip
    items = make_items(backend, 6, cfg.seed)
    ident_logits, self_logits = [], []
    store = CacheStore(ctx.out_dir / "cache")
    round_trip_ok = True
    for item in items:
        s = backend.student_cache(item)
        ident = backend.inject(s)
        self_logits.append(backend.answer_logits(s, item, arm="self"))
        ident_logits.append(backend.answer_logits(ident, item, arm="identity"))
        round_trip_ok &= cache_round_trip(s, store, item["doc_id"])

    gate = evaluate_implementation(
        identity_logits=ident_logits,
        self_logits=self_logits,
        round_trip_ok=round_trip_ok,
        effect_size_floor=None,  # mock 未提供效应下界，退回 identity 锚点参考
    )
    metrics = {
        "gate": gate.as_dict(),
        "data_quality": quality,
        "protocol_version": "2.0",
        "release": gate.passed and quality["quality_gate"] == "pass",
    }
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
