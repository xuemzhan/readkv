"""P2 机制：对称 Key 目标、K/V 四臂、层/头 Oracle 干预。

放行条件：机制诊断在验证集有预测价值；产出机制报告和候选单元。
Oracle 依赖学生原生 Prefill，仅离线诊断使用。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Mapping

from readkv.data.build_cf_pairs import build_cf_pairs, split_pairs
from readkv.diagnostics.route_value import (
    build_four_arms,
    decompose_cache,
    key_objective_matrix,
    rank_units_by_repair,
)
from readkv.evaluate.counterfactual import PairCFRecord
from readkv.evaluate.pipeline import fit_mapper

from experiments._common_v2 import add_v2_args, build_v2_mock, new_ctx, require_gpu


def _d(pair: Any) -> dict[str, Any]:
    return dict(pair) if isinstance(pair, Mapping) else asdict(pair)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P2")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "protocol": "2.0", "gate": "mechanism"}, indent=2))
        return
    require_gpu(args)

    backend, cfg = build_v2_mock(args)
    ctx = new_ctx(args, "P2")
    pairs = build_cf_pairs(sizes=cfg.sizes, seed=cfg.seed)
    cal = split_pairs(pairs, "train")
    val = split_pairs(pairs, "val")[:4]

    cal_docs = []
    for p in cal:
        pd = _d(p)
        for side in ("A", "B"):
            cal_docs.append({
                "doc_id": f"{pd['pair_id']}-{side}",
                "text": pd["context_A"] if side == "A" else pd["context_B"],
                "query": pd["query"],
                "cluster": pd["cluster"],
            })
    value_mapper = fit_mapper(backend, cal_docs, "consumer", seed=cfg.seed)

    decomposition_rows = []
    mechanism_rows = []
    for pair_obj in val:
        pair = _d(pair_obj)
        student_a = backend.pair_side_cache(pair, "A", "student")
        student_b = backend.pair_side_cache(pair, "B", "student")
        teacher_a = backend.pair_side_cache(pair, "A", "teacher")
        teacher_b = backend.pair_side_cache(pair, "B", "teacher")
        mapped_a = value_mapper.transform(teacher_a)
        mapped_b = value_mapper.transform(teacher_b)
        build_four_arms(student=student_a, mapped=mapped_a)  # 四臂接线校验

        queries = {}
        for layer in mapped_a.layers:
            k, _ = mapped_a.layer(layer)
            for head in range(k.shape[0]):
                queries[(layer, head)] = backend.query_states(layer, head, {"text": pair["query"]})

        decomps = decompose_cache(queries=queries, student=student_a, mapped=mapped_a)
        for d in decomps:
            decomposition_rows.append({"pair_id": pair["pair_id"], **d.as_dict()})

        query_doc = {"text": pair["query"]}
        candidates = (pair["candidate_A"], pair["candidate_B"])
        idx_a = 0 if pair["correct_A"].startswith("A") else 1
        idx_b = 0 if pair["correct_B"].startswith("A") else 1

        self_a = backend.candidate_logits(student_a, query_doc, candidates=candidates, correct_index=idx_a)
        self_b = backend.candidate_logits(student_b, query_doc, candidates=candidates, correct_index=idx_b)
        fixed_b = backend.candidate_logits(mapped_b, query_doc, candidates=candidates, correct_index=idx_b)

        def ecf_fn(cache):
            trans_a = backend.candidate_logits(cache, query_doc, candidates=candidates, correct_index=idx_a)
            return PairCFRecord(
                pair_id=pair["pair_id"], split="val", slice_id=pair["slice_id"],
                cluster=pair["cluster"],
                self_logits_A=self_a, self_logits_B=self_b,
                transfer_logits_A=trans_a, transfer_logits_B=fixed_b,
            ).compute()["E_CF"]

        baseline_ecf = ecf_fn(mapped_a)
        ranked = rank_units_by_repair(student=student_a, mapped=mapped_a,
                                      baseline_ecf=baseline_ecf, ecf_fn=ecf_fn)
        mechanism_rows.extend({"pair_id": pair["pair_id"], **r} for r in ranked[:8])

    key_rows = []
    if cal:
        pair = _d(cal[0])
        kt = backend.pair_side_cache(pair, "A", "teacher").keys
        ks = backend.pair_side_cache(pair, "A", "student").keys
        layer = sorted(kt)[0]
        queries = backend.query_states(layer, 0, {"text": pair["query"]})
        matrices = key_objective_matrix(teacher_k=kt[layer][0], student_k=ks[layer][0], query=queries)
        key_rows = [{"objective": name, "shape": list(mat.shape)} for name, mat in matrices.items()]

    payload = {
        "n_decomposition": len(decomposition_rows),
        "routing_mean": sum(r["routing_norm"] for r in decomposition_rows) / max(len(decomposition_rows), 1),
        "consumption_mean": sum(r["consumption_norm"] for r in decomposition_rows) / max(len(decomposition_rows), 1),
        "top_mechanism_units": mechanism_rows[:20],
        "key_objectives": key_rows,
        "note": "mock 诊断仅用于接线与候选单元排序，不是因果结论",
    }
    ctx.write_metrics("mechanism.json", payload)
    ctx.write_ledger("decomposition.jsonl", decomposition_rows)
    ctx.write_ledger("mechanism_units.jsonl", mechanism_rows)
    ctx.finalize()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
