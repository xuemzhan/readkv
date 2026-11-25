"""E2 technical-path pilot probe (NON-AUTHORITATIVE, NO TEST CONTENT).

Verifies that the frozen fixed affine / kd_only configs load and run on a small
NON-test validation sample (6 pairs) with the pinned 1.7B/0.6B snapshots, and
records peak memory / elapsed / forward count / strict zero-re-prefill.

This does NOT run the E2 one-shot test evaluator and does NOT read any test
split.  The actual one-shot test evaluation is G3 (not released).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from readkv.evaluate.counterfactual import PairCFRecord
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap
from readkv.train.kd_gpu import train_kd_gpu


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def read_jsonl(path, n, label):
    low = str(path).lower()
    if "test" in low:
        raise ValueError(f"{label} path must not reference test: {path}")
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        if str(r.get("split", "")).lower() == "test":
            raise ValueError("test row refused in E2 pilot probe")
    return rows[:n]


def load(path):
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16,
                                                 attn_implementation="sdpa").to("cuda")
    model.eval()
    model.config.use_cache = True
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--student", required=True)
    ap.add_argument("--train-path", required=True)
    ap.add_argument("--val-path", required=True)
    ap.add_argument("--n-train", type=int, default=6)
    ap.add_argument("--n-val", type=int, default=6)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    trains = read_jsonl(a.train_path, a.n_train, "train")
    vals = read_jsonl(a.val_path, a.n_val, "val")
    if not trains or not vals:
        raise ValueError("empty train/val")

    tm, tt = load(a.teacher)
    sm, st = load(a.student)
    n_s, n_t = int(sm.config.num_hidden_layers), int(tm.config.num_hidden_layers)
    if n_s != n_t:
        raise ValueError("E2 requires equal-depth pair")
    lmap = LayerMap(n_s, n_t, kind="identity")
    backend = GPUBackend(tm, sm, tt, st, device="cuda", dtype="bfloat16", kernel="sdpa", layer_map=lmap)

    docs = [{"doc_id": f"{p['pair_id']}-{s}", "text": p[f"context_{s}"],
             "pair_id": p["pair_id"], "side": s, "query": p["query"],
             "cluster": p.get("cluster", p["pair_id"])}
            for p in trains for s in ("A", "B")]
    tstack = stack_caches(backend, docs, "teacher")
    sstack = stack_caches(backend, docs, "student")

    forward_lengths: list[int] = []

    def hook(mod, args, kwargs):
        ids = kwargs.get("input_ids")
        if ids is None and args:
            ids = args[0]
        if isinstance(ids, torch.Tensor):
            forward_lengths.append(int(ids.shape[-1]))

    ht = tm.register_forward_pre_hook(hook, with_kwargs=True)
    hs = sm.register_forward_pre_hook(hook, with_kwargs=True)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()

    mappers = {
        "affine": AffineMapper(lam=1e-3, channel="both").fit(tstack, sstack, layer_map=lmap),
        "kd_only": train_kd_gpu(backend, trains, method="kd", epochs=8, lr=1e-3,
                                lam_kd=1.0, lam_cf=0.0, lam_reg=1e-4,
                                self_threshold=0.1, seed=0),
    }

    # Snapshot: cache-capture forwards above are allowed doc tokens.
    n_capture = len(forward_lengths)
    results: dict[str, dict] = {}
    for name, mapper in mappers.items():
        recs = []
        for pair in vals:
            qdoc = {"query": pair["query"], "text": pair["query"]}
            sa = backend.candidate_logits(backend.pair_side_cache(pair, "A", "student"), qdoc,
                                          candidates=(pair["candidate_A"], pair["candidate_B"]))
            sb = backend.candidate_logits(backend.pair_side_cache(pair, "B", "student"), qdoc,
                                          candidates=(pair["candidate_A"], pair["candidate_B"]))
            ma = backend.candidate_logits(
                mapper.transform(backend.pair_side_cache(pair, "A", "teacher")), qdoc,
                candidates=(pair["candidate_A"], pair["candidate_B"]))
            mb = backend.candidate_logits(
                mapper.transform(backend.pair_side_cache(pair, "B", "teacher")), qdoc,
                candidates=(pair["candidate_A"], pair["candidate_B"]))
            recs.append(PairCFRecord(
                pair_id=str(pair["pair_id"]), split="val",
                slice_id=str(pair.get("slice_id", "")),
                cluster=str(pair.get("template_family", pair.get("cluster", ""))),
                self_logits_A=sa, self_logits_B=sb, transfer_logits_A=ma, transfer_logits_B=mb,
                correct_A=pair["correct_A"], correct_B=pair["correct_B"],
                must_flip=bool(pair.get("must_flip", True)),
                tau=1.0, self_threshold=0.1,
            ).compute())
        results[name] = {
            "n_val": len(recs),
            "self_dual": float(np.mean([r["dual_correct"] for r in recs])),  # overwritten below
            "joint_dual": float(np.mean([r["dual_correct"] for r in recs])),
            "E_CF_mean": float(np.mean([r["E_CF"] for r in recs])),
            "coverage": float(np.mean([float(r["evaluable"]) for r in recs])),
            "flip": float(np.mean([r["flip_consistency"] for r in recs
                                   if r["flip_consistency"] is not None])) if any(
                r["flip_consistency"] is not None for r in recs) else None,
        }
        # PairCFRecord.dual_correct is the transfer/Joint arm; Self is separate.
        results[name]["self_dual"] = float(np.mean([r["self_dual_correct"] for r in recs]))

    # Explicit strict zero-re-prefill audit on a real injection (separate from
    # offline cache-capture forwards, which legitimately consume doc tokens).
    from readkv.models.hooks import inject_and_generate, verify_zero_re_prefill

    first = vals[0]
    q_ids = st(str(first["query"]), add_special_tokens=False).input_ids
    q_t = torch.tensor(q_ids, device="cuda", dtype=torch.long)
    native = backend.pair_side_cache(first, "A", "student")
    res = inject_and_generate(sm, native, q_t, attn_implementation="sdpa")
    zrp_ok = bool(verify_zero_re_prefill(res, expected_query_len=len(q_ids), strict=True))
    inj_lengths = list(res.audit.input_token_counts)

    ht.remove()
    hs.remove()
    peak = int(torch.cuda.max_memory_allocated())
    out = {
        "pilot_only": True, "authoritative": False, "reads_test": False,
        "one_shot_test_evaluation": "G3_NOT_RELEASED",
        "config": {"mappers": ["affine", "kd_only"], "seeds": [0],
                   "affine_lambda": 1e-3, "kd_epochs": 8, "kd_lr": 1e-3,
                   "lam_kd": 1.0, "lam_cf": 0.0, "lam_reg": 1e-4,
                   "dtype": "bfloat16", "kernel": "sdpa"},
        "data": {"train": {"path": a.train_path, "sha256": sha(a.train_path), "n": len(trains)},
                 "val": {"path": a.val_path, "sha256": sha(a.val_path), "n": len(vals)}},
        "model_pair": {"teacher": a.teacher, "student": a.student,
                       "teacher_config_sha256": sha(Path(a.teacher) / "config.json"),
                       "student_config_sha256": sha(Path(a.student) / "config.json")},
        "mappers_loaded_and_ran": sorted(results),
        "results_non_authoritative": results,
        "forward_count": {
            "total_student_forwards": len(forward_lengths),
            "note": "total includes offline cache-capture forwards that legitimately consume doc tokens",
            "strict_audit_injection_input_lengths": inj_lengths, "query_len": len(q_ids),
        },
        "zero_re_prefill": {"basis": "forward_audit(strict) on inject_and_generate",
                            "passed": zrp_ok, "audit": res.audit.as_dict()},
        "memory": {"peak_allocated_bytes": peak, "peak_allocated_mib": round(peak / 1024 ** 2, 1)},
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "E2 technical path only; no test read, no formal cell, no scientific conclusion.",
    }
    out["PASS"] = bool(set(out["mappers_loaded_and_ran"]) == {"affine", "kd_only"}
                       and out["zero_re_prefill"]["passed"])
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": a.out, "PASS": out["PASS"],
                      "peak_allocated_mib": out["memory"]["peak_allocated_mib"],
                      "elapsed_sec": out["elapsed_sec"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
