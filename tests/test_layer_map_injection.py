"""非等深层映射注入回归（audit §1.4 / BLOCKER）。

36→28 proportional 映射后，缓存已处于学生层空间（28 层）。旧实现把捕获时的
teacher→student 映射二次施加并对 28 取模，只有 s=0,1 读对；其余层静默读错
（s=2 读 3，s=22 读 0……），且全部索引合法、zero-re-prefill 断言照常通过。

本文件断言：对每个学生层 s，注入读取的缓存层就是 s，而不是 ``mp[s] % 28``；
并断言 zero-re-prefill 仍通过。V 不做 RoPE，因此用 V 的常量值给每层打标记，
可直接从注入后的 DynamicCache 读出实际使用的缓存层。

torch / transformers 不可用时整模块 skip（G1 环境尚无 torch；属 deferred，
不是 PASS）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

torch = pytest.importorskip("torch", reason="torch unavailable: GPU/hook checks deferred")
pytest.importorskip("transformers", reason="transformers unavailable: hook checks deferred")

from transformers import DynamicCache  # noqa: E402
from transformers.models.qwen3.configuration_qwen3 import Qwen3Config  # noqa: E402
from transformers.models.qwen3.modeling_qwen3 import Qwen3ForCausalLM  # noqa: E402

from readkv.cache.cache import KVCache  # noqa: E402
from readkv.models import hooks as H  # noqa: E402
from readkv.models.gpu_backend import score_candidate_sequence  # noqa: E402
from readkv.models.layer_map import LayerMap  # noqa: E402

N_STUDENT, N_TEACHER = 28, 36  # Qwen3-4B → Qwen3-1.7B 的真实深度
HEADS, HEAD_DIM, DOC_LEN = 2, 16, 3
QUERY_LEN = 2


@pytest.fixture(scope="module")
def lmap() -> LayerMap:
    return LayerMap(N_STUDENT, N_TEACHER, kind="proportional")


@pytest.fixture(scope="module")
def student_model():
    """28 层微型 Qwen3（CPU fp32）：只为走注入前向，不做真实任务评分。"""
    cfg = Qwen3Config(
        vocab_size=256, hidden_size=64, intermediate_size=128,  # 4 heads × 16 head_dim
        num_hidden_layers=N_STUDENT, num_attention_heads=4,
        num_key_value_heads=HEADS, head_dim=HEAD_DIM,
        max_position_embeddings=128,
    )
    m = Qwen3ForCausalLM(cfg).to("cpu").to(torch.float32).eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m


def stamped_student_space_cache(lmap: LayerMap) -> KVCache:
    """构造已映射的学生空间缓存：第 s 层 V 常量 = s（K 全零），元数据保留原 map。"""
    keys = {s: np.zeros((HEADS, DOC_LEN, HEAD_DIM), dtype=np.float32)
            for s in range(N_STUDENT)}
    values = {s: np.full((HEADS, DOC_LEN, HEAD_DIM), float(s), dtype=np.float32)
              for s in range(N_STUDENT)}
    serialized = {s: lmap.source_for(s) for s in range(N_STUDENT)}
    meta = {
        "kind": "mapped_student_space_cache",
        "de_roped": True,
        "position_ids": list(range(DOC_LEN)),
        "seq_len": DOC_LEN,
        "dtype": "float32",
        "kernel": "sdpa",
        "n_kv_heads": HEADS,
        "head_dim": HEAD_DIM,
        "n_layers": N_STUDENT,
        "layer_space": "student",
        "layer_map": dict(serialized),               # 溯源字段，禁止二次施加
        H.SOURCE_LAYER_MAP_KEY: dict(serialized),    # provenance，同上
        "rope_convention": "half_split",
    }
    return KVCache(keys, values, meta)


def wrong_double_mapped_source(lmap: LayerMap) -> dict[int, int]:
    """旧（错误）实现的读取层号：mp[s] % 28；仅 s=0,1 与 s 相同。"""
    return {s: lmap.source_for(s) % N_STUDENT for s in range(N_STUDENT)}


def read_layer_stamps(cache_after_injection: DynamicCache) -> dict[int, float]:
    """从注入后的学生缓存读出每层 V 的标记值。"""
    return {s: float(cache_after_injection.layers[s].values[0, 0, 0, 0].item())
            for s in range(N_STUDENT)}


def test_proportional_map_is_not_identity_and_old_bug_is_detectable(lmap):
    """前置条件：mp 非恒等且 mp[s]%28 与 s 在多处不同（否则测试无判别力）。"""
    mp = {s: lmap.source_for(s) for s in range(N_STUDENT)}
    assert mp[0] == 0 and mp[1] == 1 and mp[27] == 35  # 与 audit §1.3 一致
    wrong = wrong_double_mapped_source(lmap)
    assert wrong[0] == 0 and wrong[1] == 1
    assert wrong[2] == 3 and wrong[22] == 0  # 错层且回绕
    assert sum(v != s for s, v in wrong.items()) > 0


def test_resolve_injection_layer_map_student_space_is_identity(lmap):
    cache = stamped_student_space_cache(lmap)
    # 学生空间（28 层）：必须返回 None（恒等），即便 metadata 里带着原 map。
    assert H.resolve_injection_layer_map(None, cache.metadata, cache.n_layers, N_STUDENT) is None
    # 真正的教师缓存（36 层）：才允许用捕获时的原 map。
    resolved = H.resolve_injection_layer_map(None, cache.metadata, N_TEACHER, N_STUDENT)
    assert resolved == cache.metadata["layer_map"]
    assert cache.metadata[H.SOURCE_LAYER_MAP_KEY] == cache.metadata["layer_map"]


def test_inject_each_student_layer_uses_cache_layer_s(lmap, student_model):
    cache = stamped_student_space_cache(lmap)
    query = torch.randint(0, 200, (QUERY_LEN,), dtype=torch.long)
    res = H.inject_and_generate(student_model, cache, query, return_audit=True)

    seen = read_layer_stamps(res.cache)
    expected = {s: float(s) for s in range(N_STUDENT)}
    assert seen == expected, (
        f"injection read wrong cache layers: "
        f"{ {s: (seen[s], expected[s]) for s in range(N_STUDENT) if seen[s] != expected[s]} }"
    )
    # zero re-prefill 必须仍然成立（文档 token 一个都没进学生显式输入）。
    assert H.verify_zero_re_prefill(res, expected_query_len=QUERY_LEN, strict=True) is True
    assert res.zero_re_prefill is True


def test_full_chain_teacher_remap_then_inject_uses_proportional_source(lmap, student_model):
    """审计 §1.4 原链路：36 层教师缓存 → LayerMappedMapper 式重索引 → 注入。

    第 t 层教师 V 标记为 t；映射后第 s 层学生空间缓存承载教师 mp[s] 的 V。
    正确注入应读到 mp[s]（即映射后缓存的第 s 层），错误二次施加会读 mp[mp[s]%28]。
    """
    tkeys = {t: np.zeros((HEADS, DOC_LEN, HEAD_DIM), dtype=np.float32)
             for t in range(N_TEACHER)}
    tvals = {t: np.full((HEADS, DOC_LEN, HEAD_DIM), float(t), dtype=np.float32)
             for t in range(N_TEACHER)}
    serialized = {s: lmap.source_for(s) for s in range(N_STUDENT)}
    tcache = KVCache(tkeys, tvals, {
        "kind": "teacher_cache", "de_roped": True,
        "position_ids": list(range(DOC_LEN)), "seq_len": DOC_LEN,
        "n_layers": N_TEACHER, "n_kv_heads": HEADS, "head_dim": HEAD_DIM,
        "layer_space": "teacher", "layer_map": dict(serialized),
        H.SOURCE_LAYER_MAP_KEY: dict(serialized),
    })
    # 复刻 P1_gpu.LayerMappedMapper.transform：按 mp[s] 取教师层，键改为学生层 0..27，
    # metadata 原样透传（这正是 bug 的触发条件）。
    mapped = KVCache(
        {s: tcache.layer(lmap.source_for(s))[0] for s in range(N_STUDENT)},
        {s: tcache.layer(lmap.source_for(s))[1] for s in range(N_STUDENT)},
        dict(tcache.metadata),
    )
    query = torch.randint(0, 200, (QUERY_LEN,), dtype=torch.long)
    res = H.inject_and_generate(student_model, mapped, query, return_audit=True)
    seen = read_layer_stamps(res.cache)
    expected = {s: float(lmap.source_for(s)) for s in range(N_STUDENT)}
    wrong = {s: float(lmap.source_for(lmap.source_for(s) % N_STUDENT))
             for s in range(N_STUDENT)}
    assert seen == expected
    assert seen != wrong  # 该链路确实能区分正确实现与二次施加
    assert H.verify_zero_re_prefill(res, expected_query_len=QUERY_LEN, strict=True) is True


def test_score_candidate_sequence_each_student_layer_uses_cache_layer_s(lmap, student_model, monkeypatch):
    """score_candidate_sequence 逐学生层的注入来源核对（正向证据，不放宽断言）。

    ``SequenceScoreResult`` 不暴露内部 cache，且注入是直接 ``cache.update``、
    随后的 query/candidate forward 也会调用 ``DynamicCache.update``（spy 后者会
    混入模型算出的 K/V）。因此改在真正的注入读取边界 ``H._to_tensor_array``
    记录被取用的 V 数组标记：注入循环每层先取 K 再取 V；用大 offset 给 V 重打标，
    即可与全零 K 严格区分，并按学生层顺序还原每层实际读到的缓存标记。
    """
    OFFSET = 1000.0  # 远大于模型算出的 logits/K/V，且 V stamp 与全零 K 可区分
    cache = stamped_student_space_cache(lmap)
    for s in cache.layers:
        cache.values[s] = np.full(
            (HEADS, DOC_LEN, HEAD_DIM), OFFSET + float(s), dtype=np.float32)

    observed: list[float] = []
    original_to_array = H._to_tensor_array

    def spy_to_array(arr, device, dtype):
        observed.append(float(np.asarray(arr).reshape(-1)[0]))
        return original_to_array(arr, device, dtype)

    monkeypatch.setattr(H, "_to_tensor_array", spy_to_array)

    query = torch.randint(0, 200, (QUERY_LEN,), dtype=torch.long)
    res = score_candidate_sequence(
        student_model, cache, query, [11, 12],
        branch_tag="non_equal_depth:36to28",
        strict_audit=True,
    )

    # 只保留 V 注入标记（K 全零、模型值远小于 offset）；顺序即学生层 0..27。
    stamps = [v - OFFSET for v in observed if v >= OFFSET]
    expected = [float(s) for s in range(N_STUDENT)]
    assert len(observed) == 2 * N_STUDENT, f"expected 2 reads per layer, got {len(observed)}"
    assert stamps == expected, f"sequence scoring injected stamps: {stamps} != {expected}"
    assert res.audit.zero_re_prefill is True
