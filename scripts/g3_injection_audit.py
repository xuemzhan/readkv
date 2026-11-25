"""G3 FORMAL technical-gate audit for E5 cells (authoritative instrument).

Adds the per-cell technical audits that ``experiments.P1_gpu.py`` does not record:
per-student-layer injection correctness (source layer map preserved, no modulo),
Self/Identity equality, strict zero-re-prefill, cache shapes, forward counts,
peak memory and elapsed time.  Reads ONLY a hash-bound NON-test JSONL.  Produces
NO scores.jsonl and NO scientific conclusion.

Output goes into the authoritative run directory as ``g3_injection_audit.json``
(post-finalize supplement, like the G2 PILOT_NOTICE pattern).

Usage (one cell, run serially)::

    .venv/bin/python scripts/g3_injection_audit.py \
      --run-id v3_E5_affine_s0 --teacher <sha-named-4B> --student <sha-named-1.7B> \
      --data data/variants_v3/fully_repaired/val_seed0.jsonl \
      --data-sha256 <frozen> --seed 0
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache  # noqa: E402

from readkv.cache.cache import KVCache  # noqa: E402
from readkv.evaluate.pipeline import stack_caches  # noqa: E402
from readkv.mapper.representation import AffineMapper  # noqa: E402
from readkv.models import hooks as H  # noqa: E402
from readkv.models.gpu_backend import GPUBackend  # noqa: E402
from readkv.models.layer_map import LayerMap  # noqa: E402

from scripts.g3_audit_common import (  # noqa: E402
    cf_data_fingerprint, code_record, env_record, model_record,
    sha256_file, variants_manifest_record,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--teacher", required=True)
    p.add_argument("--student", required=True)
    p.add_argument("--data", required=True, help="frozen NON-test val JSONL")
    p.add_argument("--data-sha256", required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--n-pairs", type=int, default=2)
    return p.parse_args(argv)


def read_jsonl(path: str | Path, n: int) -> list[dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    for row in rows:
        if "test" in str(row.get("split", "")).lower():
            raise ValueError("G3 audit refuses test rows")
    return rows[:n]


def shapes(cache: KVCache) -> dict:
    return {str(layer): list(cache.layer(layer)[0].shape)
            for layer in cache.layers[:3]} | {
                "n_layers": cache.n_layers, "seq_len": cache.seq_len}


def load(path: str):
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(
        path, dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda")
    model.eval()
    model.config.use_cache = True
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    out_dir = ROOT / "reports" / "runs" / a.run_id
    if not out_dir.is_dir():
        raise SystemExit(f"run directory does not exist: {out_dir}")
    out = out_dir / "g3_injection_audit.json"
    if out.exists():
        raise SystemExit(f"REFUSE overwrite: {out}")

    data_path = ROOT / a.data
    data_sha = sha256_file(data_path)
    if data_sha != a.data_sha256.strip().lower():
        raise SystemExit(f"data SHA mismatch: {data_sha} != {a.data_sha256}")
    if "test" in {x.lower() for x in data_path.parts}:
        raise SystemExit("REFUSE test path")
    vm = variants_manifest_record()
    if vm["sha256"] != a.manifest_sha256.strip().lower():
        raise SystemExit("variants manifest SHA mismatch")
    for label, path in (("teacher", a.teacher), ("student", a.student)):
        if {x.lower() for x in Path(path).parts} & {"master", "main", "latest"}:
            raise SystemExit(f"REFUSE bare alias for {label}: {path}")

    pairs = read_jsonl(data_path, a.n_pairs)
    if not pairs:
        raise SystemExit("no pairs")

    tm, tt = load(a.teacher)
    sm, st = load(a.student)
    n_s, n_t = int(sm.config.num_hidden_layers), int(tm.config.num_hidden_layers)
    kind = "identity" if n_s == n_t else "proportional"
    lmap = LayerMap(n_s, n_t, kind=kind)
    backend = GPUBackend(tm, sm, tt, st, device="cuda", dtype="bfloat16",
                         kernel="sdpa", layer_map=lmap)

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

    # Fit a small affine mapper on NON-test pairs purely to exercise the mapped
    # cache / injection path.  These are offline cache-capture forwards.
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
    n_capture_forwards = len(lengths)
    q_ids = st(str(pair["query"]), add_special_tokens=False).input_ids
    q_t = torch.tensor(q_ids, device="cuda", dtype=torch.long)

    # (1) Per-student-layer injection: source map preserved, no modulo wrap.
    resolved = H.resolve_injection_layer_map(None, mapped_cache.metadata,
                                             mapped_cache.n_layers, n_s)
    layer_map_entries = {str(s): H._layer_map_entry(lmap, s, n_t)
                         for s in range(n_s)} if n_t > n_s else {
                             str(s): s for s in range(n_s)}
    source_map = {str(s): int(lmap(s)) for s in range(n_s)} if n_t > n_s else {
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
        H.inject_and_generate(sm, stamped, q_t, attn_implementation="sdpa")
    finally:
        H._to_tensor_array = orig
    v_stamps = observed[1::2]  # K then V per layer
    per_layer_ok = bool(v_stamps == [float(s) for s in range(n_s)])

    # (2) Strict zero-re-prefill on a real mapped-cache forward.
    res_joint = H.inject_and_generate(sm, mapped_cache, q_t, attn_implementation="sdpa")
    zrp = bool(H.verify_zero_re_prefill(res_joint, expected_query_len=len(q_ids), strict=True))

    # (3) Self / Identity equality on the native student cache.
    res_self = H.inject_and_generate(sm, student_cache, q_t, attn_implementation="sdpa")
    res_id = H.inject_and_generate(sm, backend.inject(student_cache), q_t,
                                   attn_implementation="sdpa")
    self_id_diff = float(torch.max(torch.abs(res_self.logits - res_id.logits)).item())

    ht.remove()
    hs.remove()
    peak = int(torch.cuda.max_memory_allocated())
    peak_res = int(torch.cuda.max_memory_reserved())
    inf_lengths = lengths[n_capture_forwards:]

    result: dict = {
        "g3_formal_cell": True,
        "authoritative_technical_gate": True,
        "pilot_only": False,
        "reads_test": False,
        "run_id": a.run_id,
        "stage": "E5",
        "criteria_source": "configs/prereg/gpu_followup_v3.0.yaml",
        "release_source": "docs/decisions/v3_g2_release.md",
        "note": "Authoritative G3 formal-cell technical gate; NOT a scientific result.",
        "seed": int(a.seed),
        "environment": env_record(),
        "code_sha256": code_record({
            "scripts/g3_injection_audit.py": sha256_file(Path(__file__)),
        }),
        "model_provenance": model_record(teacher=a.teacher, student=a.student),
        "data": {"path": a.data, "sha256": data_sha, "n_pairs": len(pairs),
                 "variants_manifest": vm},
        "data_fingerprint": cf_data_fingerprint(seed=a.seed, sizes={"train": 120, "val": 60}),
        "depths": {"teacher": n_t, "student": n_s, "layer_map_kind": kind},
        "layer_map": lmap.to_dict(),
        "cache_shapes": {"teacher": shapes(teacher_cache), "student": shapes(student_cache),
                         "mapped_student_space": shapes(mapped_cache)},
        "layer_map_fix": {
            "resolved_injection_map": resolved,
            "source_map": source_map,
            "layer_map_entries": layer_map_entries,
            "entries_match_source_map": all(
                int(layer_map_entries[str(s)]) == source_map[str(s)] for s in range(n_s)),
            "no_silent_wraparound": all(0 <= int(v) < n_t
                                        for v in layer_map_entries.values()),
            "v_stamp_read_order": v_stamps[:n_s + 1],
            "per_layer_injection_correct": per_layer_ok,
        },
        "self_identity": {"max_abs_logits_diff": self_id_diff,
                          "passed": self_id_diff <= 1e-4},
        "zero_re_prefill": {"passed": zrp, "basis": "forward_audit(strict)",
                            "audit": res_joint.audit.as_dict()},
        "forward_count": {
            "total": len(lengths), "capture_forwards": n_capture_forwards,
            "inference_input_lengths": inf_lengths,
            "max_inference_input_len": max(inf_lengths, default=0),
            "query_len": len(q_ids),
            "no_doc_tokens_in_inference": all(c <= len(q_ids) for c in inf_lengths),
        },
        "memory": {"peak_allocated_bytes": peak, "peak_reserved_bytes": peak_res,
                   "peak_allocated_mib": round(peak / 1024 ** 2, 1),
                   "peak_reserved_mib": round(peak_res / 1024 ** 2, 1)},
        "elapsed_sec": round(time.time() - t0, 1),
    }
    result["PASS"] = bool(
        result["layer_map_fix"]["entries_match_source_map"]
        and result["layer_map_fix"]["no_silent_wraparound"]
        and result["layer_map_fix"]["per_layer_injection_correct"]
        and result["self_identity"]["passed"]
        and result["zero_re_prefill"]["passed"]
        and result["forward_count"]["no_doc_tokens_in_inference"]
    )
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps({"run_id": a.run_id, "out": str(out), "PASS": result["PASS"],
                      "peak_allocated_mib": result["memory"]["peak_allocated_mib"],
                      "elapsed_sec": result["elapsed_sec"]}, ensure_ascii=False))
    return 0 if result["PASS"] else 3


if __name__ == "__main__":
    sys.exit(main())
