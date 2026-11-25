import numpy as np
import pytest

from readkv.models.layer_map import LayerMap
from readkv.models.rope import apply_rope, de_rope, rotate_half


def test_identity_requires_equal_depth():
    assert LayerMap(28, 28, kind="identity")(3) == 3
    with pytest.raises(ValueError):
        LayerMap(28, 36, kind="identity")


def test_proportional_and_offset():
    assert LayerMap(28, 36, kind="proportional")(0) == 0
    assert LayerMap(28, 36, kind="proportional")(27) == 35
    assert LayerMap(28, 36, kind="offset", offset=2)(0) == 2


def test_permutation():
    perm = list(reversed(range(28)))
    assert LayerMap(28, 28, kind="permutation", permutation=perm)(0) == 27


def test_rope_roundtrip():
    x = np.random.default_rng(0).normal(size=(4, 6))
    cos, sin = np.ones((4, 6)), np.zeros((4, 6))
    np.testing.assert_allclose(de_rope(apply_rope(x, cos, sin), cos, sin), x)
    np.testing.assert_allclose(rotate_half(np.array([1.0, 2.0])), np.array([-2.0, 1.0]))
