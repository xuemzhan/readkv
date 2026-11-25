"""Unit tests for the frozen v3-BM-MLP-KD internal control (PART A).

Pure CPU: asserts the exact parameter budget and the no-bias structure from
``docs/decisions/v3_baseline_spec.md`` §2.  Also exercises the entry's
``--cpu-selfcheck`` (no model load, no GPU, no run directory).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (str(REPO / "src"), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch  # noqa: E402

from readkv.mapper.mlp_kd import (  # noqa: E402
    EXPECTED_PARAMS, HEAD_DIM, N_HEADS, N_LAYERS,
    MLPLinearKDMapper, MLPLinearKDModule,
)


def test_parameter_count_is_exactly_frozen_budget():
    """28 layers × 8 KV heads × 128² × 2 (K,V) == 7,340,032."""
    assert (N_LAYERS, N_HEADS, HEAD_DIM) == (28, 8, 128)
    assert EXPECTED_PARAMS == 7_340_032
    module = MLPLinearKDModule()
    assert module.parameter_count() == 7_340_032
    assert sum(p.numel() for p in module.parameters()) == module.parameter_count()


def test_no_bias_structure():
    """Exactly two bias-free tensors, each (28, 8, 128, 128); no affine row."""
    module = MLPLinearKDModule()
    named = dict(module.named_parameters())
    assert set(named) == {"W_K", "W_V"}
    assert all("bias" not in name for name in named)
    assert all("affine" not in name for name in named)
    assert named["W_K"].shape == torch.Size([28, 8, 128, 128])
    assert named["W_V"].shape == torch.Size([28, 8, 128, 128])
    assert named["W_K"].ndim == 4 and named["W_V"].ndim == 4
    module.assert_budget()  # must not raise


def test_identity_init_and_separate_kv_weights():
    """K and V are separate parameters; frozen identity start."""
    module = MLPLinearKDModule()
    eye = torch.eye(HEAD_DIM)
    assert torch.allclose(module.W_K[0, 0].detach().cpu(), eye)
    assert torch.allclose(module.W_V[27, 7].detach().cpu(), eye)
    assert module.W_K.data_ptr() != module.W_V.data_ptr()


def test_hyperparameter_guards_are_frozen():
    """train_mlp_kd_gpu refuses any change to the frozen KD config."""
    import pytest

    from readkv.mapper.mlp_kd import train_mlp_kd_gpu

    with pytest.raises(ValueError):
        train_mlp_kd_gpu(None, [], epochs=4)
    with pytest.raises(ValueError):
        train_mlp_kd_gpu(None, [], lr=0.01)
    with pytest.raises(ValueError):
        train_mlp_kd_gpu(None, [], lam_cf=1.0)
    with pytest.raises(ValueError):
        train_mlp_kd_gpu(None, [], n_layers=27)


def test_mapper_wrapper_refuses_untrained_module():
    mapper = MLPLinearKDMapper()
    try:
        mapper.transform(None)  # type: ignore[arg-type]
    except RuntimeError:
        return
    raise AssertionError("untrained mapper must refuse transform")


def test_entry_cpu_selfcheck_passes(capsys):
    from experiments import v3_e6_control_gpu as entry

    assert entry.cpu_selfcheck() == 0
    out = capsys.readouterr().out
    payload = __import__("json").loads(out)
    assert payload["status"] == "PASS"
    assert payload["checks"]["param_count_frozen"] is True
    assert payload["checks"]["no_bias_structure"] is True
    assert payload["checks"]["test_path_rejected"] is True
    assert payload["checks"]["bare_master_rejected"] is True
