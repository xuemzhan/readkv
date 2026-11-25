"""G2 pilot-only instrumentation probe (NON-AUTHORITATIVE).

Adds the audits the formal entries do not record (peak allocated memory,
student-forward count / input lengths, cache shapes, per-student-layer injection
correctness, Self/Identity equality, strict zero-re-prefill) on real pinned
snapshots.  Reads ONLY an explicitly supplied NON-test JSONL.  Produces NO
scores.jsonl and NO scientific conclusion; output is a single audit JSON.

This file lives under reports/_non_authoritative/v3_g2_pilot/ on purpose:
it is a pilot instrument, not a package module.
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

from readkv.cache.cache import KVCache
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models import hooks as H
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load(path):
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16,
                                                 attn_implementation="sdpa").to("cuda")
    model.eval()
    model.config.use_cache = True
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok


def read_jsonl(path, n):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        if "test" in str(r.get("split", "")).lower():
            raise ValueError("pilot probe refuses test rows")
    return rows[:n]


def shapes(cache):
    return {str(l): list(cache.layer(l)[0].shape) for l in cache.layers[:3]} | {
        "n_layers": cache.n_layers, "seq_len": cache.seq_len}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--student", required=True)
    ap.add_argument("--data", required=True, help="NON-test val/train JSONL")
    ap.add_argument("--n-pairs", type=int, default=2)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    tm, tt = load(a.teacher)
    sm, st = load(a.student)
    n_s, n_t = int(sm.config.num_hidden_layers), int(tm.config.num_hidden_layers)
    kind = "identity" if n_s == n_t else "proportional"
    lmap = LayerMap(n_s, n_t, kind=kind)
    backend = GPUBackend(tm, sm, tt, st, device="cuda", dtype="bfloat16", kernel="sdpa", layer_map=lmap)

    pairs = read_jsonl(a.data, a.n_pairs)
    if len(pairs) < 1:
        raise ValueError("no pairs")
    lengths: list[int] = []

    def hook(mod, args, kwargs):
        ids = kwargs.get("input_ids")
        if ids is None and args:
            ids = args[0]
        if isinstance(ids, torch.Tensor):
            lengths.append(int(ids.shape[-1]))

    ht = tm.register_forward_pre_hook(hook, with_kwargs=True)
    hs = sm.register_forward_pre_hook(hook, with_kwargs=True)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()

    # Fit a small affine mapper purely to exercise the mapped/injection path.
    docs = [{"doc_id": f"{p['pair_id']}-{s}", "text": p[f"context_{s}"],
             "query": p["query"], "cluster": p.get("cluster", p["pair_id"])}
            for p in pairs for s in ("A", "B")]
    tstack = stack_caches(backend, docs, "teacher")
    sstack = stack_caches(backend, docs, "student")
    inner = AffineMapper(lam=1e-3, channel="both").fit(tstack, sstack, layer_map=lmap)

    class LayerMappedMapper:
        def __init__(self, m, lm):
            self.inner, self.lm = m, lm

        def transform(self, tc):
            sel = {s: tc.layer(int(self.lm(s))) for s in range(int(self.lm.ns))}
            remap = KVCache({s: kv[0] for s, kv in sel.items()},
                            {s: kv[1] for s, kv in sel.items()}, dict(tc.metadata))
            return self.inner.transform(remap)

    mapper = LayerMappedMapper(inner, lmap) if n_t != n_s else inner

    pair = pairs[0]
    teacher_cache = backend.pair_side_cache(pair, "A", "teacher")
    student_cache = backend.pair_side_cache(pair, "A", "student")
    mapped_cache = mapper.transform(teacher_cache)

    # Snapshot the forward count: everything up to here is offline cache
    # capture (which legitimately feeds document tokens); zero-re-prefill only
    # governs the inference/injection forwards that follow.
    n_capture_forwards = len(lengths)
    q_ids = st(str(pair["query"]), add_special_tokens=False).input_ids
    q_t = torch.tensor(q_ids, device="cuda", dtype=torch.long)

    # (1) Per-student-layer injection correctness on REAL shapes.
    #     Deterministic layer-map check + empirical V-stamp read-order check.
    resolved = H.resolve_injection_layer_map(None, mapped_cache.metadata,
                                             mapped_cache.n_layers, n_s)
    layer_map_entries = {str(s): H._layer_map_entry(lmap, s, n_t) for s in range(n_s)} if n_t > n_s else {
        str(s): s for s in range(n_s)}
    stamped_k = {l: np.zeros_like(mapped_cache.keys[l]) for l in mapped_cache.layers}
    stamped_v = {l: np.full(mapped_cache.values[l].shape, float(l), dtype=np.float32)
                 for l in mapped_cache.layers}
    stamped = KVCache(stamped_k, stamped_v, dict(mapped_cache.metadata))
    observed: list[float] = []
    orig = H._to_tensor_array

    def spy(arr, device, dtype):
        observed.append(float(np.asarray(arr).reshape(-1)[0]))
        return orig(arr, device, dtype)

    H._to_tensor_array = spy
    try:
        res_stamp = H.inject_and_generate(sm, stamped, q_t, attn_implementation="sdpa")
    finally:
        H._to_tensor_array = orig
    v_stamps = observed[1::2]  # K then V per layer
    per_layer_ok = bool(v_stamps == [float(s) for s in range(n_s)])

    # (2) Strict zero-re-prefill on the mapped cache (real forward).
    res_joint = H.inject_and_generate(sm, mapped_cache, q_t, attn_implementation="sdpa")
    zrp = bool(H.verify_zero_re_prefill(res_joint, expected_query_len=len(q_ids), strict=True))

    # (3) Self / Identity equality on the native student cache.
    res_self = H.inject_and_generate(sm, student_cache, q_t, attn_implementation="sdpa")
    res_id = H.inject_and_generate(sm, backend.inject(student_cache), q_t, attn_implementation="sdpa")
    self_id_diff = float(torch.max(torch.abs(res_self.logits - res_id.logits)).item())

    ht.remove()
    hs.remove()
    peak = int(torch.cuda.max_memory_allocated())
    peak_res = int(torch.cuda.max_memory_reserved())

    out = {
        "pilot_only": True, "authoritative": False, "reads_test": False,
        "data": {"path": a.data, "sha256": sha(a.data), "n_pairs": len(pairs)},
        "model_pair": {"teacher": a.teacher, "student": a.student,
                       "teacher_sha256_config": sha(Path(a.teacher) / "config.json"),
                       "student_sha256_config": sha(Path(a.student) / "config.json")},
        "depths": {"teacher": n_t, "student": n_s, "layer_map_kind": kind},
        "cache_shapes": {"teacher": shapes(teacher_cache), "student": shapes(student_cache),
                         "mapped_student_space": shapes(mapped_cache)},
        "layer_map_fix": {
            "resolved_injection_map": resolved,
            "layer_map_entries": layer_map_entries,
            "entries_match_source_map": all(
                int(v) == (int(lmap(s)) if n_t > n_s else s)
                for s, v in enumerate(layer_map_entries.values())),
            "no_silent_wraparound": all(0 <= int(v) < n_t for v in layer_map_entries.values()),
            "v_stamp_read_order": v_stamps[:n_s + 1],
            "per_layer_injection_correct": per_layer_ok,
        },
        "self_identity": {"max_abs_logits_diff": self_id_diff,
                          "passed": self_id_diff <= 1e-4},
        "zero_re_prefill": {"passed": zrp, "basis": "forward_audit(strict)",
                            "audit": res_joint.audit.as_dict()},
        "forward_count": {
            "total": len(lengths), "capture_forwards": n_capture_forwards,
            "inference_input_lengths": lengths[n_capture_forwards:],
            "max_inference_input_len": max(lengths[n_capture_forwards:], default=0),
            "query_len": len(q_ids),
            "no_doc_tokens_in_inference": all(c <= len(q_ids) for c in lengths[n_capture_forwards:]),
        },
        "memory": {"peak_allocated_bytes": peak, "peak_reserved_bytes": peak_res,
                   "peak_allocated_mib": round(peak / 1024 ** 2, 1)},
        "elapsed_sec": round(time.time() - t0, 1),
    }
    out["PASS"] = bool(out["layer_map_fix"]["per_layer_injection_correct"]
                       and out["self_identity"]["passed"] and out["zero_re_prefill"]["passed"]
                       and out["forward_count"]["no_doc_tokens_in_inference"])
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": a.out, "PASS": out["PASS"],
                      "peak_allocated_mib": out["memory"]["peak_allocated_mib"],
                      "elapsed_sec": out["elapsed_sec"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
