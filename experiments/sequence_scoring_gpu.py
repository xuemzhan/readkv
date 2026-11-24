"""完整候选答案评分的独立 GPU 入口（protocol-v2.8 · 测量稳健性补充）。

严格独立：**显式接收 train/val 版本 legacy(458de18) / fixed(efc3ba3)**，从
``data/audit_2x2/<version>/{train,val}_seed{k}.jsonl`` 读取；**绝不调用
P1_gpu.py**（其 run_cf_pipeline 会自动重建数据 + 质量门）；**不读取封存 test**；
**不跑 A01/A10**（--version 仅 legacy=A00 / fixed=A11）。

三读数对同一批样本：
  * first               : 首 token logprob（历史回放锚点，FP32 log-softmax）；
  * full                : 整串 teacher-forcing 候选 token 条件 logprob 之和（FP32，
                          固定不追加 EOS）；
  * length_normalized   : full / 候选 token 数。

teacher-forcing 走 ``readkv.models.gpu_backend.score_candidate_sequence`` 显式评分
模式，**不复用** ``inject_and_generate`` 的贪解码。每条候选分支从同一文档缓存新建
独立可变 DynamicCache；严格 zero re-prefill：只有 query + 当前候选真实前缀进入学生
显式输入，输入长度序列 [Q, 1×(m−1)]，文档长度只经注入缓存与 position_ids 偏移。

用法（本轮只实现 + CPU 自检，不启动 GPU run）：
  .venv/bin/python -m experiments.sequence_scoring_gpu --cpu-selfcheck
  # 以下为后续经 PI 下达 GPU 指令后才执行的命令（本轮禁止运行）：
  .venv/bin/python -m experiments.sequence_scoring_gpu \\
      --run-id audit_seq_A11_s0 --version fixed --seed 0
  .venv/bin/python -m experiments.sequence_scoring_gpu \\
      --run-id audit_seq_smoke_A00_s0 --version legacy --seed 0 --smoke
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from readkv.cache.cache import KVCache
from readkv.evaluate.pipeline import stack_caches
from readkv.mapper.representation import AffineMapper
from readkv.models.gpu_backend import GPUBackend
from readkv.models.layer_map import LayerMap
from readkv.runtime import RunContext

ROOT = Path(__file__).resolve().parents[1]
RIDGE_LAM = 0.001
READINGS = ("first", "full", "length_normalized")
TAU = 1.0
SELF_THRESHOLD = 0.1  # 沿用归档 2x2（audit_2x2_gpu / p1_gpu），未按测试集调整
N_RESAMPLES = 10_000

# legacy=旧生成器 458de18 -> A00；fixed=修复版 efc3ba3 -> A11。A01/A10 本轮不做。
VERSIONS: dict[str, dict[str, str]] = {
    "legacy": {"dir": "legacy", "tag": "legacy_458de18", "cell": "A00",
               "archived_run": "audit_2x2_A00_s0"},
    "fixed": {"dir": "fixed", "tag": "fixed_efc3ba3", "cell": "A11",
              "archived_run": "audit_2x2_A11_s0"},
}
DEFAULT_TEACHER = "/root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master"
DEFAULT_STUDENT = "/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master"


# ---------------------------------------------------------------------------
# CLI / 工具
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cpu-selfcheck", action="store_true",
                   help="纯函数 CPU 自检；不加载模型、不创建 run 目录、不碰 GPU")
    p.add_argument("--run-id", default=None)
    p.add_argument("--version", choices=list(VERSIONS), default=None,
                   help="legacy=A00(旧/旧)，fixed=A11(修复/修复)；A01/A10 本轮不做")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out-dir", default=None,
                   help="产物父目录（run 写入 <out-dir>/<run-id>/）；默认 reports/runs")
    p.add_argument("--smoke", action="store_true",
                   help="技术门：val 取小子集 + A/B 顺序交换 + 首 token 历史回放 + 逐次审计")
    p.add_argument("--smoke-n-val", type=int, default=6)
    p.add_argument("--train-path", default=None, help="可选显式 train JSONL；默认按 version+seed 派生")
    p.add_argument("--val-path", default=None, help="可选显式 val JSONL；默认按 version+seed 派生")
    p.add_argument("--teacher", default=DEFAULT_TEACHER)
    p.add_argument("--student", default=DEFAULT_STUDENT)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--kernel", default="sdpa")
    p.add_argument("--device", default="cuda")
    p.add_argument("--n-resamples", type=int, default=N_RESAMPLES)
    p.add_argument("--swap-ab", action="store_true",
                   help="额外跑一次 B→A 顺序，按候选身份核验分数不变（每次正式格也可开）")
    p.add_argument("--first-token-tol", type=float, default=0.02,
                   help="冒烟门首 token 历史回放容差（绝对 logit 差）")
    return p.parse_args(argv)


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_pairs(path: str | Path) -> list[dict[str, Any]]:
    """从显式 JSONL 读 CFPair 记录（不重建、不过质量门）。"""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not rows:
        raise ValueError(f"empty JSONL: {path}")
    return rows


def derive_paths(version: str, seed: int, *, train_path: str | None,
                 val_path: str | None) -> tuple[Path, Path]:
    """只接受 version 对应目录的 train/val；任何 test 路径直接拒绝。"""
    cfg = VERSIONS[version]
    base = ROOT / "data" / "audit_2x2" / cfg["dir"]
    train = Path(train_path) if train_path else base / f"train_seed{seed}.jsonl"
    val = Path(val_path) if val_path else base / f"val_seed{seed}.jsonl"
    for label, path in (("train", train), ("val", val)):
        parts = {p.lower() for p in path.parts}
        if "test" in parts or "test" in path.name.lower():
            raise ValueError(f"{label} path points at sealed test: {path}")
        if not path.exists():
            raise FileNotFoundError(path)
        if f"{label}_seed{seed}" not in path.name:
            raise ValueError(f"{label} path {path} does not match seed {seed}")
        if cfg["dir"] not in path.parts:
            raise ValueError(f"{label} path {path} is outside data/audit_2x2/{cfg['dir']}/")
    return train, val


def load_model(path: str, dtype: str, kernel: str, device: str) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(path)
    m = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype),
                                            attn_implementation=kernel).to(device)
    m.eval()
    m.config.use_cache = True
    for p in m.parameters():
        p.requires_grad_(False)
    return m, tok


def tokenizer_fingerprint(tok: Any, path: str) -> dict[str, Any]:
    """与模型权重无关的 tokenizer 指纹（词表 + 特殊 token + 类 + 路径）。"""
    try:
        vocab = sorted((str(k), int(v)) for k, v in tok.get_vocab().items())
        # added_tokens_decoder: {int_id: AddedToken}（AddedToken 不可 int()）
        added = sorted((str(k), str(v)) for k, v in getattr(tok, "added_tokens_decoder", {}).items())
        special = tok.all_special_ids
        payload = {
            "class": type(tok).__name__,
            "path": path,
            "vocab": vocab,
            "added_tokens_decoder": added,
            "special_ids": [int(x) for x in special],
            "model_max_length": int(getattr(tok, "model_max_length", -1)),
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    except Exception as exc:  # pragma: no cover - 不同 tokenizer 实现差异
        digest = f"unavailable:{type(exc).__name__}"
    return {"sha256": digest, "path": path, "class": type(tok).__name__}


def tokenize_candidate(tok: Any, query: str, candidate: str) -> tuple[list[int], list[int], list[int]]:
    """固定 token 边界：两段独立 tokenize + 联合 tokenize，均关闭自动特殊 token。"""
    q = list(tok(query, add_special_tokens=False).input_ids)
    c = list(tok(candidate, add_special_tokens=False).input_ids)
    j = list(tok(query + candidate, add_special_tokens=False).input_ids)
    return q, c, j


def fit_mapper_once(backend: GPUBackend, trains: Sequence[Mapping[str, Any]],
                    lmap: LayerMap) -> AffineMapper:
    """每格只拟合一次 affine（逐层逐头 K/V，ridge λ=0.001）。"""
    docs = [{"doc_id": f"{p['pair_id']}-{s}", "text": p[f"context_{s}"]}
            for p in trains for s in ("A", "B")]
    ts = stack_caches(backend, docs, "teacher")
    ss = stack_caches(backend, docs, "student")
    return AffineMapper(lam=RIDGE_LAM, channel="both").fit(ts, ss, layer_map=lmap)


def side_cache(backend: GPUBackend, mapper: AffineMapper, pair: Mapping[str, Any],
               side: str, arm: str) -> KVCache:
    student_self = backend.pair_side_cache(pair, side, "student")
    if arm == "self":
        return student_self
    if arm == "identity":
        return backend.inject(student_self)
    if arm == "joint":
        return mapper.transform(backend.pair_side_cache(pair, side, "teacher"))
    raise ValueError(f"unknown arm {arm!r}")


def _pred_from_g(g: float) -> str:
    return "A" if float(g) > 0 else "B"


def _is_correct(g: float, correct: str) -> bool:
    lab = str(correct).strip().upper()
    if lab.startswith("A") and lab.startswith("B"):
        return True  # F5 非翻转负控：两个候选都正确（沿用 counterfactual._pick）
    return _pred_from_g(g) == ("A" if lab.startswith("A") else "B")


def score_arm(
    backend: GPUBackend, mapper: AffineMapper, pair: Mapping[str, Any], arm: str,
    tok: Any, *, layer_map: LayerMap, device: str, kernel: str,
    version: str, seed: int, cell: str, swap_ab: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """一（pair, arm）的三种读数 + 该 arm 的逐次前向审计记录。"""
    from readkv.models.gpu_backend import score_candidate_sequence, token_boundary_report

    # 签名一个 arm 内 query 与候选用同一 token 边界（modeller 的 token id 由学生 tokenizer 给出）
    ids_q, ids_a, joint_a = tokenize_candidate(tok, pair["query"], pair["candidate_A"])
    ids_q_b, ids_b, joint_b = tokenize_candidate(tok, pair["query"], pair["candidate_B"])
    if ids_q != ids_q_b:  # pragma: no cover - 同一 query 两次 tokenize 必相同
        raise AssertionError("query tokenization is not deterministic")
    q_ids = [int(v) for v in ids_q]

    boundary = {
        "A": token_boundary_report(ids_q, ids_a, joint_a),
        "B": token_boundary_report(ids_q_b, ids_b, joint_b),
    }
    cand_ids = {"A": [int(v) for v in ids_a], "B": [int(v) for v in ids_b]}
    caches = {s: side_cache(backend, mapper, pair, s, arm) for s in ("A", "B")}

    scores: dict[str, dict[str, dict[str, float]]] = {}
    audit_rows: list[dict[str, Any]] = []
    order = ("B", "A") if swap_ab else ("A", "B")
    for side in ("A", "B"):
        scores[side] = {}
        for cand in order:
            tag = f"{pair['pair_id']}:{arm}:doc{side}:cand{cand}"
            res = score_candidate_sequence(
                backend.student, caches[side], q_ids, cand_ids[cand],
                layer_map=layer_map, branch_tag=tag,
                strict_audit=True, attn_implementation=kernel,
            )
            scores[side][cand] = res.as_scores()
            audit_rows.append({
                "pair_id": pair["pair_id"], "sample_id": pair.get("sample_id", ""),
                "sample_hash": pair.get("sample_hash", ""), "version_tag": pair.get("version_tag", ""),
                "cell": cell, "version": version, "seed": seed, "arm": arm,
                "doc_side": side, "candidate": cand, "token_boundary": boundary[cand],
                **res.audit.as_dict(),
            })

    # 双侧各读数：g = logP(A|doc_side,q) − logP(B|doc_side,q)
    g = {r: {s: float(scores[s]["A"][r] - scores[s]["B"][r]) for s in ("A", "B")}
         for r in READINGS}
    d = {r: float(g[r]["A"] - g[r]["B"]) for r in READINGS}
    gold = {"A": pair.get("correct_A", "A"), "B": pair.get("correct_B", "B")}
    pred = {r: {s: _pred_from_g(g[r][s]) for s in ("A", "B")} for r in READINGS}
    dual = {r: float(_is_correct(g[r]["A"], gold["A"]) and _is_correct(g[r]["B"], gold["B"]))
            for r in READINGS}

    row = {
        "pair_id": pair["pair_id"], "sample_id": pair.get("sample_id", ""),
        "sample_hash": pair.get("sample_hash", ""), "version_tag": pair.get("version_tag", ""),
        "template_family": pair.get("template_family", pair.get("cluster", "")),
        "cluster": pair.get("cluster", ""), "slice_id": pair.get("slice_id", "F1"),
        "split": pair.get("split", "val"), "cell": cell,
        "calibration_version": version, "validation_version": version,
        "arm": arm, "seed": seed,
        "candidate_len_A": len(cand_ids["A"]), "candidate_len_B": len(cand_ids["B"]),
        "candidate_token_ids_sha256": {
            "A": hashlib.sha256(json.dumps(cand_ids["A"]).encode()).hexdigest(),
            "B": hashlib.sha256(json.dumps(cand_ids["B"]).encode()).hexdigest(),
        },
        "token_boundary": boundary, "scores": scores, "g": g, "D": d,
        "gold": gold, "prediction": pred, "dual_correct": dual,
        # 下面三个字段由 postprocess() 在同一 pair 的 self/joint(/identity) 间回填
        "E_CF": {r: None for r in READINGS},
        "evaluable": {r: None for r in READINGS},
        "flip_consistency": {r: None for r in READINGS},
        "failure": False,
    }
    return row, audit_rows


def postprocess(rows: list[dict[str, Any]], arms: Sequence[str]) -> None:
    """回填逐对 E_CF / evaluable / flip（self 为原生基线，joint 为迁移）。"""
    index = {(r["pair_id"], r["arm"]): r for r in rows}
    pair_ids = [pid for pid, arm in index if arm == "self"]
    for pid in pair_ids:
        base = index[(pid, "self")]
        for arm in arms:
            if arm == "self" or (pid, arm) not in index:
                continue
            cur = index[(pid, arm)]
            for r in READINGS:
                ds, dt = base["D"][r], cur["D"][r]
                ecf = abs(float(dt) - float(ds))
                ev = abs(float(ds)) > SELF_THRESHOLD
                flip = bool(np.sign(dt) == np.sign(ds)) if ev else None
                for row in (base, cur):
                    row["E_CF"][r] = ecf
                    row["evaluable"][r] = ev
                    row["flip_consistency"][r] = flip


def _archived_first_token_dself(run_id: str) -> dict[tuple[str, str], float]:
    """只读归档 2x2 的 first-token 原生 D，作为历史回放锚点。

    归档每行都带原生 ``D_self``（对所有 arm 相同）；该 arm 自身的迁移 D 在
    ``D_trans``。因此 self arm 比 ``D_self``，joint arm 必须比归档 joint 行的
    ``D_trans``，否则会把 joint 与 self 的差当成回放差异。
    """
    path = ROOT / "reports" / "runs" / run_id / "scores.jsonl"
    out: dict[tuple[str, str], float] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        arm = r.get("arm")
        if arm not in ("self", "joint"):
            continue
        field = "D_self" if arm == "self" else "D_trans"
        if field in r:
            out[(r.get("sample_id", r["pair_id"]), arm)] = float(r[field])
    return out


def summarize(rows: list[dict[str, Any]], arms: Sequence[str], *, n_resamples: int,
              seed: int) -> dict[str, Any]:
    """逐 arm 三读数汇总 + L=Self−Joint + 配对 L_full−L_first（template_family CI）。"""
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    per_arm: dict[str, Any] = {}
    for arm in arms:
        ar = by_arm.get(arm, [])
        entry: dict[str, Any] = {"n": len(ar)}
        for r in READINGS:
            dual = [float(x["dual_correct"][r]) for x in ar]
            ecf = [float(x["E_CF"][r]) for x in ar if x["E_CF"][r] is not None]
            ev = [bool(x["evaluable"][r]) for x in ar if x["evaluable"][r] is not None]
            flips = [bool(x["flip_consistency"][r]) for x in ar
                     if x["flip_consistency"][r] is not None]
            entry[r] = {
                "dual_correct": float(np.mean(dual)) if dual else None,
                "D_mean": float(np.mean([float(x["D"][r]) for x in ar])) if ar else None,
                "E_CF_mean": float(np.mean(ecf)) if ecf else None,
                "coverage": float(np.mean(ev)) if ev else None,
                "n_flip_evaluable": len(flips),
                "flip_consistency": float(np.mean(flips)) if flips else None,
            }
        per_arm[arm] = entry

    L = {}
    for r in READINGS:
        a, b = per_arm.get("self", {}).get(r, {}).get("dual_correct"), \
               per_arm.get("joint", {}).get(r, {}).get("dual_correct")
        L[r] = float(a - b) if (a is not None and b is not None) else None

    # 同格内配对差：(Self_full−Self_first) − (Joint_full−Joint_first)，按 template_family 重采样
    index = {(r["pair_id"], r["arm"]): r for r in rows}
    deltas, clusters = [], []
    for pid in {pid for pid, arm in index if arm == "self"}:
        s, j = index.get((pid, "self")), index.get((pid, "joint"))
        if s is None or j is None:
            continue
        d_self = float(s["dual_correct"]["full"]) - float(s["dual_correct"]["first"])
        d_joint = float(j["dual_correct"]["full"]) - float(j["dual_correct"]["first"])
        deltas.append(d_self - d_joint)
        clusters.append(str(s["template_family"]))
    if deltas:
        from readkv.stats.bootstrap import cluster_bootstrap
        point, low, high = cluster_bootstrap(deltas, clusters, n_resamples=n_resamples, seed=seed)
        reading_diff_ci = {"point": point, "ci": [low, high], "n": len(deltas)}
    else:
        reading_diff_ci = None
    n_families = len(set(clusters))
    return {
        "per_arm": per_arm,
        "L_self_minus_joint": L,
        "reading_diff_L_full_minus_L_first": reading_diff_ci,
        "n_template_families": n_families,
        "exploratory": bool(n_families < 24),
        "n_resamples": n_resamples,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    # 用 torch 前先导入纯函数做 CPU 自检分支（--cpu-selfcheck 绝不加载模型 / 创建 run）
    args = parse_args(argv)
    if args.cpu_selfcheck:
        return cpu_selfcheck()

    if not args.run_id or args.version is None or args.seed is None:
        raise SystemExit("--run-id / --version / --seed are required unless --cpu-selfcheck")

    t0 = time.time()
    version = args.version
    cfg = VERSIONS[version]
    cell = cfg["cell"]  # legacy->A00, fixed->A11；A01/A10 无入口
    if cell not in ("A00", "A11"):
        raise ValueError(f"cell {cell} is out of scope for v2.8 (A01/A10 not run this round)")

    train_path, val_path = derive_paths(version, args.seed,
                                        train_path=args.train_path, val_path=args.val_path)
    sha = {"train": sha256_file(train_path), "val": sha256_file(val_path)}
    trains = load_pairs(train_path)
    vals = load_pairs(val_path)
    if args.smoke:
        vals = vals[: args.smoke_n_val]

    # 模型 + tokenizer 指纹
    tm, tt = load_model(args.teacher, args.dtype, args.kernel, args.device)
    sm, st = load_model(args.student, args.dtype, args.kernel, args.device)
    n_s = int(sm.config.num_hidden_layers)
    n_t = int(tm.config.num_hidden_layers)
    if n_s != n_t:
        raise ValueError(f"v2.8 requires equal depth (28->28 identity); got teacher {n_t} vs student {n_s}")
    lmap = LayerMap(n_s, n_t, kind="identity")
    tok_fp = tokenizer_fingerprint(st, args.student)
    tok_fp_teacher = tokenizer_fingerprint(tt, args.teacher)
    backend = GPUBackend(tm, sm, tt, st, device=args.device, dtype=args.dtype,
                         kernel=args.kernel, layer_map=lmap)
    mapper = fit_mapper_once(backend, trains, lmap)

    # run 目录：默认 reports/runs，冒烟 reports/_non_authoritative（不污染正式归档）
    root = Path(args.out_dir) if args.out_dir else (
        ROOT / "reports" / "_non_authoritative" if args.smoke else ROOT / "reports" / "runs")
    ctx = RunContext(
        args.run_id,
        {
            "stage": "sequence_scoring", "gate": "full_candidate_scoring_v2.8",
            "backend": "gpu", "cell": cell,
            "calibration_version": version, "validation_version": version,
            "version_tag": cfg["tag"], "seed": args.seed,
            "train_path": str(train_path), "val_path": str(val_path),
            "input_sha256": sha,
            "dtype": args.dtype, "kernel": args.kernel, "zero_re_prefill": True,
            "teacher": args.teacher, "student": args.student,
            "tokenizer_fingerprint": tok_fp, "tokenizer_fingerprint_teacher": tok_fp_teacher,
            "layer_map": lmap.to_dict(), "mapper": "affine_per_layer_head",
            "ridge_lambda": RIDGE_LAM, "layer_map_kind": "identity",
            "scoring": ["first", "full", "length_normalized"],
            "token_boundary": "query+candidate 独立 tokenize（add_special_tokens=False），不追加 EOS",
            "teacher_forcing": "explicit score_candidate_sequence（非贪解码 inject_and_generate）",
            "input_length_sequence": "[Q, 1*(m-1)]",
            "n_train": len(trains), "n_val": len(vals),
            "tau": TAU, "self_threshold": SELF_THRESHOLD,
            "n_resamples": args.n_resamples, "smoke": args.smoke,
            "zero_re_prefill": True, "sealed_test_read": False,
            "criteria_source": "configs/prereg/full_candidate_scoring_v2.8.yaml (frozen)",
            "protocol_version": "2.8",
        },
        protocol_version="2.8", seed=args.seed, device=args.device,
        dtype=args.dtype, kernel=args.kernel, zero_re_prefill=True,
        reports_root=root,
        metadata={"stage": "sequence_scoring", "backend": "gpu", "cell": cell,
                  "protocol_version": "2.8", "non_authoritative": bool(args.smoke)},
    )

    arms = ("self", "joint", "identity") if args.smoke else ("self", "joint")
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    try:
        for pair in vals:
            for arm in arms:
                row, arows = score_arm(
                    backend, mapper, pair, arm, st,
                    layer_map=lmap, device=args.device, kernel=args.kernel,
                    version=version, seed=args.seed, cell=cell,
                    swap_ab=bool(args.swap_ab),
                )
                # 候选缓存独立性断言（4 条分支 = 2 doc side × 2 candidate）：
                # 每次 score_candidate_sequence 都新建 DynamicCache，实例号必须互异。
                instance_ids = [a["branch_cache_id"] for a in arows]
                if len(set(instance_ids)) != len(instance_ids):
                    raise AssertionError(
                        f"candidate branch caches are not independent: ids={instance_ids} "
                        f"at pair={pair['pair_id']} arm={arm}")
                if not all(a["audit_passed"] and a["zero_re_prefill"] for a in arows):
                    raise AssertionError(f"forward audit failed at pair={pair['pair_id']} arm={arm}")
                rows.append(row)
                audit_rows.extend(arows)
        postprocess(rows, arms)
    except AssertionError as exc:
        # 审计失败：中止该格，保留失败信息（config 已在 RunContext 初始化时落盘）
        failure = {"stage": "sequence_scoring", "run_id": args.run_id, "cell": cell,
                   "status": "ABORTED", "reason": str(exc), "n_rows_before_abort": len(rows)}
        if audit_rows:
            ctx.write_ledger("forward_audit.jsonl", audit_rows)
        ctx.write_metrics("metrics.json", failure)
        ctx.finalize()
        print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    # 逐次审计全通过（score_candidate_sequence strict_audit=True 已保证）
    all_pass = all(a["audit_passed"] and a["zero_re_prefill"] for a in audit_rows)
    if not all_pass:  # pragma: no cover - 防御性双检
        raise AssertionError("forward audit has a failed record despite strict mode")

    # 冒烟门专属：A/B 顺序交换一轮（B→A），按候选身份核验分数与审计；
    # 在落盘前执行，保证其逐次审计记录也写入 forward_audit.jsonl。
    swap_diffs: list[float] = []
    if args.smoke:
        first_pair = vals[0]
        swap_row, swap_arows = score_arm(
            backend, mapper, first_pair, "joint", st,
            layer_map=lmap, device=args.device, kernel=args.kernel,
            version=version, seed=args.seed, cell=cell, swap_ab=True,
        )
        base_row = next((r for r in rows if r["pair_id"] == first_pair["pair_id"]
                         and r["arm"] == "joint"), None)
        if base_row is not None:
            for side in ("A", "B"):
                for cand in ("A", "B"):
                    for rd in READINGS:
                        swap_diffs.append(abs(float(base_row["scores"][side][cand][rd])
                                              - float(swap_row["scores"][side][cand][rd])))
        audit_rows.extend(swap_arows)

    ctx.write_scores(rows)
    ctx.write_ledger("forward_audit.jsonl", audit_rows)
    metrics = summarize(rows, arms, n_resamples=args.n_resamples, seed=args.seed)
    metrics.update({
        "run_id": args.run_id, "backend": "gpu", "protocol_version": "2.8",
        "cell": cell, "calibration_version": version, "validation_version": version,
        "seed": args.seed, "dtype": args.dtype, "kernel": args.kernel,
        "zero_re_prefill": True, "sealed_test_read": False,
        "input_sha256": sha, "version_tag": cfg["tag"],
        "n_train": len(trains), "n_val": len(vals), "n_audit_forwards": len(audit_rows),
        "token_boundary_inconsistent": {
            c: sum(1 for r in rows if not r["token_boundary"][c]["consistent"])
            for c in ("A", "B")
        },
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "v2.8 读数稳健性补充；首/整串/长度归一并列；不重算主终点、不碰封存 test、不恢复贡献。",
    })
    if args.smoke:
        checks: dict[str, Any] = {}
        from readkv.models.gpu_backend import single_token_consistency

        # 1) 单 token 候选：整串 == 首 token（历史回放锚点）
        singles = [c for r in rows for cand in ("A", "B")
                   for c in [single_token_consistency(
                       r["scores"]["A"][cand]["first"], r["scores"]["A"][cand]["full"],
                       r[f"candidate_len_{cand}"])] if c["applicable"]]
        checks["single_token_consistency"] = {
            "n": len(singles), "passed": all(c["passed"] for c in singles),
            "max_abs_diff": max((c["abs_diff"] for c in singles), default=0.0),
        }
        # 2) 首 token 历史回放（只读归档，按 sample_id+arm 对齐 D_self）
        archived = _archived_first_token_dself(cfg["archived_run"])
        replay_diffs = []
        for r in rows:
            if r["arm"] not in ("self", "joint"):
                continue
            key = (r["sample_id"], r["arm"])
            if key in archived:
                replay_diffs.append(abs(r["D"]["first"] - archived[key]))
        checks["first_token_replay"] = {
            "n": len(replay_diffs),
            "max_abs_diff": max(replay_diffs) if replay_diffs else None,
            "tol": args.first_token_tol,
            "passed": (len(replay_diffs) > 0 and max(replay_diffs) <= args.first_token_tol)
                      if replay_diffs else None,
        }
        # 3) 多 token teacher-forcing 位置 + 逐次输入审计 + zero re-prefill + 缓存独立
        multi = [a for a in audit_rows if int(a["candidate_len"]) > 1]
        checks["multi_token_positions"] = {
            "n_records": len(multi),
            "n_forwards": sum(len(a["input_length_sequence"]) for a in multi),
            "passed": bool(multi) and all(a["audit_passed"] for a in multi),
        }
        checks["forward_audit"] = {
            "n_records": len(audit_rows),
            "n_forwards": sum(len(a["input_length_sequence"]) for a in audit_rows),
            "all_passed": all(a["audit_passed"] for a in audit_rows),
            "all_zero_re_prefill": all(a["zero_re_prefill"] for a in audit_rows),
            "passed": all(a["audit_passed"] and a["zero_re_prefill"] for a in audit_rows),
        }
        ids = [a["branch_cache_id"] for a in audit_rows]
        checks["candidate_cache_independence"] = {
            "n_records": len(ids), "n_unique_instance_ids": len(set(ids)),
            "passed": len(ids) > 0 and len(set(ids)) == len(ids),
        }
        checks["sealed_test_not_read"] = {"read": False, "passed": True}
        # 4) Self/Identity 锚点：同一 mapper，Identity 是 Self 缓存的原样注入副本
        idx = {(r["pair_id"], r["arm"]): r for r in rows}
        anchor_diffs = []
        for pid in {p for p, a in idx if a == "self"}:
            if (pid, "identity") in idx:
                for rd in READINGS:
                    anchor_diffs.append(abs(idx[(pid, "self")]["D"][rd]
                                            - idx[(pid, "identity")]["D"][rd]))
        checks["self_identity_anchor"] = {
            "n": len(anchor_diffs),
            "max_abs_diff": max(anchor_diffs) if anchor_diffs else None,
            "tol": 1e-4,
            "passed": (len(anchor_diffs) > 0 and max(anchor_diffs) <= 1e-4)
                      if anchor_diffs else None,
        }
        # 5) A/B 顺序交换：首对 joint arm 反向顺序，按候选身份比三读数
        checks["swap_ab_by_candidate_identity"] = {
            "n": len(swap_diffs),
            "max_abs_diff": max(swap_diffs) if swap_diffs else None,
            "tol": 1e-5,
            "passed": (len(swap_diffs) > 0 and max(swap_diffs) <= 1e-5)
                      if swap_diffs else None,
        }
        checks["swap_ab_requested"] = bool(args.swap_ab)
        metrics["smoke_checks"] = checks
        hard = ("single_token_consistency", "multi_token_positions", "forward_audit",
                "candidate_cache_independence", "self_identity_anchor",
                "swap_ab_by_candidate_identity")
        failed = [k for k in hard if checks[k]["passed"] is False]
        if checks["first_token_replay"]["passed"] is False:
            failed.append("first_token_replay")
        if failed:
            metrics["status"] = "SMOKE_GATE_FAILED"
            metrics["failed_checks"] = failed
        elif checks["first_token_replay"]["passed"] is None:
            # 归档 run 缺失：按 v2.8 §4 明示差异，不伪造一致性
            metrics["status"] = "SMOKE_GATE_PASSED_NON_AUTHORITATIVE_REPLAY_SKIPPED"
        else:
            metrics["status"] = "SMOKE_GATE_PASSED_NON_AUTHORITATIVE"
    ctx.write_metrics("metrics.json", metrics)
    ctx.finalize()
    print(json.dumps({"run_id": args.run_id, "cell": cell,
                      "status": metrics.get("status", "OK"),
                      "n_scores": len(rows), "n_audit_forwards": len(audit_rows),
                      "zero_re_prefill": True}, ensure_ascii=False, indent=2))
    return 3 if metrics.get("status") == "SMOKE_GATE_FAILED" else 0


# ---------------------------------------------------------------------------
# CPU 自检（纯函数，零 GPU、零模型、零产物）
# ---------------------------------------------------------------------------


def cpu_selfcheck() -> int:
    from readkv.models.gpu_backend import (
        audit_sequence_forwards, expected_input_length_sequence, log_softmax_fp32,
        prefix_relation, single_token_consistency, token_boundary_report,
        token_id_fingerprint,
    )

    out: dict[str, Any] = {}
    # token 边界：拼接一致 / 不一致 / 互为前缀
    out["token_boundary"] = {
        "consistent": token_boundary_report([1, 2, 3], [4, 5], [1, 2, 3, 4, 5]),
        "inconsistent": token_boundary_report([1, 2], [3, 4], [1, 2, 9, 3, 4]),
        "prefix": prefix_relation([1, 2], [1, 2, 3]),
    }
    assert out["token_boundary"]["consistent"]["consistent"] is True
    assert out["token_boundary"]["inconsistent"]["consistent"] is False
    assert out["token_boundary"]["prefix"] == "a_prefix_of_b"

    # 长度序列：m=1 -> [Q]; m=3 -> [Q,1,1]
    out["length_sequences"] = {
        "m1": expected_input_length_sequence(7, 1),
        "m3": expected_input_length_sequence(7, 3),
    }
    assert out["length_sequences"]["m1"] == [7]
    assert out["length_sequences"]["m3"] == [7, 1, 1]

    # 首 token vs 单 token 候选整串一致（纯函数 + FP32 log-softmax）
    logits = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    lp = log_softmax_fp32(logits)
    out["single_token_consistency"] = single_token_consistency(float(lp[2]), float(lp[2]), 1)
    assert out["single_token_consistency"]["passed"] is True

    # 逐次输入审计：通过 + 失败两类
    good = audit_sequence_forwards(
        input_lengths=[7, 1, 1], position_starts=[11, 18, 19],
        input_token_fingerprints=["q", "c0", "c1"],
        query_len=7, candidate_len=3, doc_len=11, position_offset=11,
        candidate_token_ids=[4, 5, 6], initial_cache_prefix_length=11,
        cache_prefix_lengths=[11, 18, 19],
    )
    bad = audit_sequence_forwards(
        input_lengths=[7, 3, 1], position_starts=[11, 18, 19],
        input_token_fingerprints=["q", "c0", "c1"],
        query_len=7, candidate_len=3, doc_len=11, position_offset=11,
        candidate_token_ids=[4, 5, 6], initial_cache_prefix_length=11,
        cache_prefix_lengths=[11, 18, 19],
    )
    out["audit"] = {"good": good["passed"], "bad_failures": bad["failures"],
                    "fingerprint": token_id_fingerprint([4, 5, 6])}
    assert good["passed"] is True
    assert "length_sequence" in bad["failures"]

    print(json.dumps({"cpu_selfcheck": "PASSED", "detail": out}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
