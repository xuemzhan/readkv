import numpy as np

from readkv.cache.cache import CacheStore, KVCache, estimate_bytes_per_token


def _cache():
    return KVCache(
        {0: np.ones((2, 4, 3), dtype=np.float16), 1: np.zeros((2, 4, 3), dtype=np.float16)},
        {0: np.ones((2, 4, 3), dtype=np.float16), 1: np.zeros((2, 4, 3), dtype=np.float16)},
        {"doc": "d0"},
    )


def test_cache_basics():
    c = _cache()
    assert c.n_layers == 2 and c.seq_len == 4
    assert c.subset([0]).n_layers == 1
    assert c.clone().keys[0].shape == (2, 4, 3)
    assert c.estimate_bytes() > 0


def test_cache_store_roundtrip(tmp_path):
    store = CacheStore(tmp_path / "caches")
    path = store.save(_cache(), "teacher_d0")
    assert path.exists()
    loaded = store.load("teacher_d0")
    assert loaded.metadata["doc"] == "d0"
    np.testing.assert_array_equal(loaded.keys[0], np.ones((2, 4, 3), dtype=np.float16))


def test_size_estimate():
    n = estimate_bytes_per_token({"n_layers": 28, "n_kv_heads": 8, "head_dim": 128})
    assert n == 2 * 28 * 8 * 128 * 2
