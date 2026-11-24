"""完整候选评分（v2.8）CPU 自检：纯函数 + 微型 Qwen3 真前向。

**强制 CPU**：本文件显式 device='cpu' / dtype=float32，不调用 cuda，不占用 GPU。
真实 GPU 证据只在 PI 下达运行指令后由 experiments/sequence_scoring_gpu.py 产出。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pytest
import torch
from transformers.models.qwen3.configuration_qwen3 import Qwen3Config
from transformers.models.qwen3.modeling_qwen3 import Qwen3ForCausalLM

from readkv.models.gpu_backend import (
    audit_sequence_forwards,
    expected_input_length_sequence,
    log_softmax_fp32,
    prefix_relation,
    score_candidate_sequence,
    single_token_consistency,
    token_boundary_report,
    token_id_fingerprint,
)
from readkv.models.hooks import capture_teacher_cache, inject_and_generate


# ---------------------------------------------------------------------------
# 1) 纯函数级自检（无模型、无 GPU）
# ---------------------------------------------------------------------------


def test_expected_input_length_sequence():
    """长度 m 候选的学生输入序列必须是 [Q, 1 × (m−1)]。"""
    assert expected_input_length_sequence(7, 1) == [7]
    assert expected_input_length_sequence(7, 3) == [7, 1, 1]
    assert expected_input_length_sequence(1, 4) == [1, 1, 1, 1]
    with pytest.raises(ValueError):
        expected_input_length_sequence(0, 2)


def test_token_boundary_report_and_prefix():
    """encode(query+candidate) 与两段拼接一致/不一致/候选互为前缀。"""
    ok = token_boundary_report([1, 2, 3], [4, 5], [1, 2, 3, 4, 5])
    assert ok["consistent"] is True and ok["split_len"] == 5
    bad = token_boundary_report([1, 2], [3, 4], [1, 2, 9, 3, 4])
    assert bad["consistent"] is False
    assert prefix_relation([1, 2], [1, 2, 3]) == "a_prefix_of_b"
    assert prefix_relation([1, 2, 3], [1, 2]) == "b_prefix_of_a"
    assert prefix_relation([1, 2], [3, 4]) == "none"


def test_first_token_vs_single_token_full_string_consistency():
    """单 token 候选：整串 logprob 之和必须等于首 token logprob（FP32）。"""
    logits = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    lp = log_softmax_fp32(logits)
    # FP32 归一化：exp(log-softmax) 之和为 1
    assert abs(float(np.exp(lp.astype(np.float64)).sum()) - 1.0) < 1e-5
    assert lp[3] > lp[0]
    one = single_token_consistency(float(lp[2]), float(lp[2]), 1)
    assert one["applicable"] is True and one["passed"] is True and one["abs_diff"] == 0.0
    mismatch = single_token_consistency(float(lp[2]), float(lp[3]), 1)
    assert mismatch["passed"] is False
    multi = single_token_consistency(0.0, 1.0, 2)
    assert multi["applicable"] is False and multi["passed"] is True


def test_token_id_fingerprint_deterministic():
    fp = token_id_fingerprint([4, 5, 6])
    assert fp == token_id_fingerprint(torch.tensor([4, 5, 6]))
    assert fp != token_id_fingerprint([4, 5, 7])


def test_forward_audit_sequence_pass_and_fail():
    """逐次审计：长度/位置/缓存增长/zero re-prefill 断言，失败必须被记录。"""
    good = audit_sequence_forwards(
        input_lengths=[7, 1, 1], position_starts=[11, 18, 19],
        input_token_fingerprints=["q", "c0", "c1"],
        query_len=7, candidate_len=3, doc_len=11, position_offset=11,
        candidate_token_ids=[4, 5, 6], initial_cache_prefix_length=11,
        cache_prefix_lengths=[11, 18, 19],
    )
    assert good["passed"] is True and good["failures"] == []

    bad = audit_sequence_forwards(
        input_lengths=[7, 3, 1], position_starts=[11, 18, 19],
        input_token_fingerprints=["q", "c0", "c1"],
        query_len=7, candidate_len=3, doc_len=11, position_offset=11,
        candidate_token_ids=[4, 5, 6], initial_cache_prefix_length=11,
        cache_prefix_lengths=[11, 18, 19],
    )
    assert bad["passed"] is False
    assert "length_sequence" in bad["failures"]
    assert "zero_re_prefill_no_doc_tokens" in bad["failures"]


# ---------------------------------------------------------------------------
# 2) 微型 Qwen3 真前向（CPU only）：验证显式评分模式与审计轨迹
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tiny_cpu_model():
    cfg = Qwen3Config(vocab_size=256, hidden_size=64, intermediate_size=128,
                      num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                      head_dim=16, max_position_embeddings=128)
    torch.manual_seed(0)
    m = Qwen3ForCausalLM(cfg).to("cpu").to(torch.float32).eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m


def test_score_candidate_sequence_cpu_tiny(tiny_cpu_model):
    model = tiny_cpu_model
    torch.manual_seed(1)
    doc = torch.randint(0, 200, (12,))
    query = torch.randint(0, 200, (5,))
    cache = capture_teacher_cache(model, doc)  # de-ROPed 内容空间缓存

    # m=1：整串 == 首 token；输入长度序列 [Q]
    res1 = score_candidate_sequence(model, cache, query, [37], branch_tag="tiny:m1")
    assert res1.audit.passed is True and res1.audit.zero_re_prefill is True
    assert res1.audit.input_lengths == [5]
    assert res1.audit.as_dict()["expected_input_length_sequence"] == [5]
    assert single_token_consistency(res1.first_logprob, res1.full_logprob_sum, 1)["passed"] is True
    assert res1.length_normalized == pytest.approx(res1.full_logprob_sum)

    # m=3：输入长度序列 [Q,1,1]；位置 = doc_len, +Q, +Q+1；FP32 log-softmax
    cand = [37, 88, 12]
    res3 = score_candidate_sequence(model, cache, query, cand, branch_tag="tiny:m3")
    assert res3.audit.passed is True
    assert res3.audit.input_lengths == [5, 1, 1]
    assert res3.audit.position_starts == [12, 17, 18]
    assert res3.audit.cache_prefix_lengths == [12, 17, 18]
    assert res3.length_normalized == pytest.approx(res3.full_logprob_sum / 3.0)
    assert res3.full_logprob_sum <= res3.first_logprob + 1e-6  # 条件概率乘积（log）通常不增

    # 首 token 对齐现有 inject_and_generate（历史回放口径）
    inj = inject_and_generate(model, cache, query)
    first_from_inj = float(log_softmax_fp32(inj.logits[0])[37])
    assert res3.first_logprob == pytest.approx(first_from_inj, abs=1e-4)

    # 候选分支独立：同一 doc 缓存两次调用得到不同可变 cache id，分数一致
    a = score_candidate_sequence(model, cache, query, cand, branch_tag="tiny:A")
    b = score_candidate_sequence(model, cache, query, cand, branch_tag="tiny:B")
    assert a.audit.branch_cache_id != b.audit.branch_cache_id
    assert a.full_logprob_sum == pytest.approx(b.full_logprob_sum, abs=1e-5)


# ---------------------------------------------------------------------------
# 3) 汇总/指标路径（合成行，无模型、无 GPU）
# ---------------------------------------------------------------------------


def test_postprocess_and_summarize_synthetic():
    """E_CF / L / 配对读数差的聚合口径可在纯 CPU 下复算。"""
    from experiments.sequence_scoring_gpu import postprocess, summarize

    def make_row(pid, arm, dself):
        d = {r: dself[i] for i, r in enumerate(("first", "full", "length_normalized"))}
        return {
            "pair_id": pid, "arm": arm, "template_family": f"T-{pid}",
            "D": d, "dual_correct": {r: 1.0 for r in d},
            "E_CF": {r: None for r in d}, "evaluable": {r: None for r in d},
            "flip_consistency": {r: None for r in d},
        }

    rows = []
    for i in range(6):
        base = (-2.0 - i, -3.0 - i, -1.0 - i / 2)
        rows.append(make_row(f"p{i}", "self", base))
        rows.append(make_row(f"p{i}", "joint", tuple(v + 0.25 for v in base)))
    postprocess(rows, ("self", "joint"))

    # E_CF 回填：joint − self = 0.25；evaluable 由 |D_self|>0.1 决定
    assert all(r["E_CF"]["first"] == pytest.approx(0.25) for r in rows)
    assert all(r["evaluable"]["first"] is True for r in rows)
    assert all(r["flip_consistency"]["first"] is True for r in rows)

    m = summarize(rows, ("self", "joint"), n_resamples=32, seed=0)
    assert set(m["L_self_minus_joint"]) == {"first", "full", "length_normalized"}
    assert m["L_self_minus_joint"]["first"] == pytest.approx(0.0)
    assert m["n_template_families"] == 6 and m["exploratory"] is True
    assert m["reading_diff_L_full_minus_L_first"] is not None
