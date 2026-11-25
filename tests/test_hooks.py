"""hooks.py 真实前向的轻量回归（微型 Qwen3，CPU/GPU 均可运行）。

大模型 E0 的实测证据在 reports/runs/<run_id>/；这里只锁住接口接线正确性。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
import torch

from transformers.models.qwen3.configuration_qwen3 import Qwen3Config
from transformers.models.qwen3.modeling_qwen3 import Qwen3ForCausalLM

from readkv.cache.cache import CacheStore
from readkv.cache.identity_check import cache_round_trip, logit_cosine, first_token_kl
from readkv.models.hooks import (
    capture_teacher_cache, inject_and_generate, verify_zero_re_prefill,
)


@pytest.fixture(scope="module")
def tiny_model():
    cfg = Qwen3Config(vocab_size=256, hidden_size=64, intermediate_size=128,
                      num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                      head_dim=16, max_position_embeddings=128)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    m = Qwen3ForCausalLM(cfg).to(dev).to(dtype).eval()
    return m, dev, dtype


def test_capture_inject_identity_matches_full_prefill(tiny_model, tmp_path):
    model, dev, dtype = tiny_model
    torch.manual_seed(0)
    doc = torch.randint(0, 200, (12,))
    query = torch.randint(0, 200, (5,))
    full = torch.cat([doc, query]).to(dev)
    with torch.inference_mode():
        full_logits = model(input_ids=full[None], use_cache=True, return_dict=True).logits[0, -1].float().cpu()

    cache = capture_teacher_cache(model, doc)
    assert cache.seq_len == 12 and cache.n_layers == 2
    assert all(a.shape[0] == 2 and a.shape[-1] == 16 for a in cache.values.values())

    store = CacheStore(tmp_path)
    assert cache_round_trip(cache, store, "tiny")

    res = inject_and_generate(model, cache, query)
    inj_logits = res.logits[0].float().cpu()
    assert logit_cosine(inj_logits.numpy(), full_logits.numpy()) >= 0.9998
    def _softmax(x):
        import numpy as np
        e = np.exp(x - x.max())
        return e / e.sum()
    assert first_token_kl(_softmax(inj_logits.numpy()), _softmax(full_logits.numpy())) <= 1e-3
    assert int(inj_logits.argmax()) == int(full_logits.argmax())
    assert verify_zero_re_prefill(res, expected_query_len=5, strict=False)

    # 显式 position offset（= doc 长度）应与默认一致
    res2 = inject_and_generate(model, cache, query, position_offset=12)
    assert logit_cosine(res2.logits[0].float().cpu().numpy(), full_logits.numpy()) >= 0.9998


def test_zero_re_prefill_guard_fires_on_doc_tokens(tiny_model):
    model, dev, dtype = tiny_model
    from readkv.models.hooks import ForwardAudit
    audit = ForwardAudit(input_token_counts=[25], query_len=5, doc_len=20, n_decode_steps=0)
    assert verify_zero_re_prefill(audit, expected_query_len=5, strict=False) is False
