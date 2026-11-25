"""v3-BM-MLP-KD — clean budget-matched per-layer K/V linear mapper (KD objective).

Frozen contract: ``docs/decisions/v3_baseline_spec.md`` §2 (new file, does NOT
rewrite ``configs/prereg/gpu_followup_v3.0.yaml``).  This is an *internal
budget-matched control*, explicitly NOT a faithful baseline of any published
method (the E6 reproduction gate is NOT PASSED).

Architecture (frozen)
---------------------
* per student layer, per KV head: ``W_K, W_V ∈ R^{128×128}``, **no bias**;
* 28 layers × 8 KV heads × head_dim 128 × 2 (K,V) = **7,340,032** trainable
  parameters, deliberately identical to the existing ``kd_only`` budget;
* student weights stay frozen; only the mapped K/V cache carries gradient;
* objective = the frozen ``L_KD`` of ``src/readkv/train/kd_gpu.py``:
  ``KL(Self ‖ mapped)`` with ``lam_kd=1.0, lam_reg=1e-4, lam_cf=0``;
* 8 epochs, Adam lr=1e-3, seeds 0/1/2, strictly zero re-prefill.

Design notes (implementation choices the frozen spec leaves open, recorded
here rather than silently assumed):
* initialization = identity for both W_K and W_V.  This makes the control a
  *freshly learned* linear map, distinct from the ridge-initialized
  ``kd_only``; it is the plain "linear W" reading of the frozen architecture.
* ``regularization()` returns 0 (there is no low-rank residual), matching the
  effective objective of ``kd_only`` (``rank=0``).  ``lam_reg`` is still
  recorded as a frozen hyperparameter.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import nn

from readkv.cache.cache import KVCache
from readkv.data.build_cf_pairs import CFPair
from readkv.models.cf_rct import CFRCTMapper

# Frozen architecture constants — do NOT expose as tunable CLI knobs.
N_LAYERS = 28
N_HEADS = 8
HEAD_DIM = 128
EXPECTED_PARAMS = N_LAYERS * N_HEADS * HEAD_DIM * HEAD_DIM * 2  # 7,340,032
NAME = "v3-BM-MLP-KD"

KD_LAM_KD = 1.0
KD_LAM_REG = 1e-4
KD_LAM_CF = 0.0
KD_EPOCHS = 8
KD_LR = 1e-3


class MLPLinearKDModule(nn.Module):
    """Clean parameterization: only two bias-free tensors ``W_K``/``W_V``.

    Shapes ``(n_layers, n_heads, dim, dim)``.  No affine row, no residual, no
    student parameter is registered here.
    """

    def __init__(
        self,
        n_layers: int = N_LAYERS,
        n_heads: int = N_HEADS,
        dim: int = HEAD_DIM,
        *,
        init: str = "identity",
    ) -> None:
        super().__init__()
        if init != "identity":
            raise ValueError("v3-BM-MLP-KD frozen init is 'identity'")
        self.n_layers = int(n_layers)
        self.n_heads = int(n_heads)
        self.dim = int(dim)
        self.init = init
        # nn.ParameterDict-free: exactly two parameters, hence trivially no bias.
        self.W_K = nn.Parameter(torch.empty(self.n_layers, self.n_heads, dim, dim))
        self.W_V = nn.Parameter(torch.empty(self.n_layers, self.n_heads, dim, dim))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        eye = torch.eye(self.dim, dtype=self.W_K.dtype, device=self.W_K.device)
        with torch.no_grad():
            self.W_K.copy_(eye.expand_as(self.W_K))
            self.W_V.copy_(eye.expand_as(self.W_V))

    # ---- structural guarantees (used by the unit test and the pilot gate) ----
    def parameter_count(self) -> int:
        return int(sum(p.numel() for p in self.parameters()))

    def assert_budget(self) -> None:
        params = dict(self.named_parameters())
        if set(params) != {"W_K", "W_V"}:
            raise AssertionError(f"expected only W_K/W_V parameters, got {sorted(params)}")
        if any("bias" in n for n in params):
            raise AssertionError("v3-BM-MLP-KD must have no bias parameters")
        expected_shape = (self.n_layers, self.n_heads, self.dim, self.dim)
        if params["W_K"].shape != expected_shape or params["W_V"].shape != expected_shape:
            raise AssertionError(f"unexpected weight shape, expected {expected_shape}")
        if self.parameter_count() != EXPECTED_PARAMS:
            raise AssertionError(
                f"parameter budget mismatch: {self.parameter_count()} != {EXPECTED_PARAMS}"
            )

    def weight(self, layer: int, ch: str, head: int) -> torch.Tensor:
        if ch == "K":
            return self.W_K[layer, head]
        if ch == "V":
            return self.W_V[layer, head]
        raise ValueError(f"channel must be K or V, got {ch!r}")

    def _as_f32(self, x: Any) -> torch.Tensor:
        device = self.W_K.device
        if isinstance(x, torch.Tensor):
            return x.detach().to(device=device, dtype=torch.float32)
        return torch.as_tensor(np.asarray(x), device=device, dtype=torch.float32)

    def map_cache(
        self, cache: Any
    ) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
        """内容空间 (H, T, d) K/V → mapped torch tensors（K/V 各自一套 W）。"""
        out: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for layer in cache.layers:
            k, v = cache.layer(layer)
            k_t, v_t = [], []
            for head in range(k.shape[0]):
                k_t.append(self._as_f32(k[head]) @ self.weight(layer, "K", head))
                v_t.append(self._as_f32(v[head]) @ self.weight(layer, "V", head))
            out[layer] = (torch.stack(k_t), torch.stack(v_t))
        return out

    def regularization(self) -> torch.Tensor:
        # rank=0 control: no low-rank residual → no reg term (kd_only parity).
        return torch.zeros((), dtype=torch.float32, device=self.W_K.device)

    def state_dict_numpy(self) -> dict[str, np.ndarray]:
        return {k: v.detach().cpu().numpy().copy() for k, v in self.state_dict().items()}


class MLPLinearKDMapper:
    """BaseMapper-style wrapper; ``fit`` lives in :func:`train_mlp_kd_gpu`."""

    name = NAME

    def __init__(self, module: MLPLinearKDModule | None = None) -> None:
        self.module = module

    @property
    def method(self) -> str:
        return NAME

    def transform(self, teacher: KVCache) -> KVCache:
        if self.module is None:
            raise RuntimeError("MLPLinearKDMapper has no trained module")
        self.module.eval()
        with torch.no_grad():
            mapped = self.module.map_cache(teacher)
        keys = {l: v[0].detach().cpu().numpy() for l, v in mapped.items()}
        values = {l: v[1].detach().cpu().numpy() for l, v in mapped.items()}
        return KVCache(keys, values, dict(teacher.metadata) | {"mapper": NAME})

    def save(self, path: Path | str) -> Path:
        if self.module is None:
            raise RuntimeError("no module to save")
        self.module.assert_budget()
        path = Path(path)
        torch.save({"state": self.module.state_dict_numpy(), "name": NAME,
                    "budget": EXPECTED_PARAMS}, path)
        return path

    @classmethod
    def load(cls, path: Path | str) -> "MLPLinearKDMapper":
        payload = torch.load(path, weights_only=False)
        if payload.get("name") != NAME or payload.get("budget") != EXPECTED_PARAMS:
            raise ValueError("checkpoint is not a frozen v3-BM-MLP-KD module")
        module = MLPLinearKDModule()
        module.load_state_dict({k: torch.as_tensor(v) for k, v in payload["state"].items()})
        module.assert_budget()
        return cls(module)

    def fit(self, *args: Any, **kwargs: Any) -> "MLPLinearKDMapper":
        raise NotImplementedError("use readkv.mapper.mlp_kd.train_mlp_kd_gpu")


def train_mlp_kd_gpu(
    backend: Any,
    cal_pairs: Sequence[CFPair | Mapping[str, Any]],
    *,
    epochs: int = KD_EPOCHS,
    lr: float = KD_LR,
    lam_kd: float = KD_LAM_KD,
    lam_reg: float = KD_LAM_REG,
    lam_cf: float = KD_LAM_CF,
    seed: int = 0,
    n_layers: int = N_LAYERS,
    n_heads: int = N_HEADS,
    dim: int = HEAD_DIM,
    init: str = "identity",
) -> tuple[MLPLinearKDMapper, dict[str, Any]]:
    """Train the frozen control with the verbatim ``L_KD`` of ``kd_gpu.py``.

    Returns ``(mapper, audit)`` where ``audit`` records the training-loss log,
    the number of student forwards and a zero-re-prefill check based on a
    forward pre-hook (no document token is ever fed to the student).
    """
    # Frozen hyperparameter guards — these are never tunable at run time.
    if (epochs, lr, lam_kd, lam_reg, lam_cf) != (KD_EPOCHS, KD_LR, KD_LAM_KD, KD_LAM_REG, KD_LAM_CF):
        raise ValueError("v3-BM-MLP-KD hyperparameters are frozen (8ep/1e-3/1.0/1e-4/0.0)")
    if (n_layers, n_heads, dim, init) != (N_LAYERS, N_HEADS, HEAD_DIM, "identity"):
        raise ValueError("v3-BM-MLP-KD architecture is frozen (28/8/128/identity)")

    # Readout helpers are imported from the frozen trainer so the KL formula
    # and the candidate-readout path are byte-for-byte the same as kd_only.
    from readkv.train.kd_gpu import (
        _cand_first_tokens,
        _gpu_candidate_logits,
        _pair_dict_safe,
    )

    torch.manual_seed(seed)
    random.seed(seed)

    student = backend.student
    for p in student.parameters():
        if p.requires_grad:
            raise RuntimeError("student parameters must be frozen for v3-BM-MLP-KD")
    device = next(student.parameters()).device
    dtype = next(student.parameters()).dtype
    tok = backend.tok_s

    module = MLPLinearKDModule(n_layers, n_heads, dim, init=init).to(device)
    module.assert_budget()
    optimizer = torch.optim.Adam(module.parameters(), lr=lr)

    # Offline anchors: teacher caches (train-time mapping) + native Self logits
    # (no_grad, never in the Joint graph).  Mirrors kd_gpu.py:99-124.
    prepared: list[dict[str, Any]] = []
    with torch.no_grad():
        for pair_obj in cal_pairs:
            pair = _pair_dict_safe(pair_obj)
            q_ids = tok(str(pair["query"]), add_special_tokens=False).input_ids
            cand_idx = _cand_first_tokens(tok, (pair["candidate_A"], pair["candidate_B"]))
            entry: dict[str, Any] = {"pair": pair, "q_ids": q_ids, "cand_idx": cand_idx,
                                     "teachers": {}}
            for side in ("A", "B"):
                t = backend.pair_side_cache(pair, side, "teacher")
                s = backend.pair_side_cache(pair, side, "student")
                entry["teachers"][side] = t
                s_native = {
                    l: (
                        torch.as_tensor(np.asarray(s.keys[l]), device=device, dtype=torch.float32),
                        torch.as_tensor(np.asarray(s.values[l]), device=device, dtype=torch.float32),
                    )
                    for l in s.layers
                }
                entry[f"self_logits_{side}"] = _gpu_candidate_logits(
                    student, s_native, q_ids, cand_idx, device=device, dtype=dtype
                )
            prepared.append(entry)

    if not prepared:
        raise ValueError("no calibration pairs for v3-BM-MLP-KD")

    # Forward-length audit: every student forward in training feeds query tokens
    # only (never document tokens).  Count via a top-level forward pre-hook.
    forward_lengths: list[int] = []

    def _pre_hook(mod: Any, args: tuple, kwargs: dict) -> None:
        ids = kwargs.get("input_ids")
        if ids is None and args:
            ids = args[0]
        if isinstance(ids, torch.Tensor):
            forward_lengths.append(int(ids.shape[-1]))
        else:  # pragma: no cover
            forward_lengths.append(0)

    handle = student.register_forward_pre_hook(_pre_hook, with_kwargs=True)
    max_query_len = max(len(e["q_ids"]) for e in prepared)
    module.train()
    loss_log: list[float] = []
    try:
        for epoch in range(epochs):
            order = list(range(len(prepared)))
            random.Random(seed + epoch).shuffle(order)
            for i in order:
                e = prepared[i]
                optimizer.zero_grad()
                mapped_a = module.map_cache(e["teachers"]["A"])
                mapped_b = module.map_cache(e["teachers"]["B"])
                trans_a = _gpu_candidate_logits(student, mapped_a, e["q_ids"], e["cand_idx"],
                                                device=device, dtype=dtype)
                trans_b = _gpu_candidate_logits(student, mapped_b, e["q_ids"], e["cand_idx"],
                                                device=device, dtype=dtype)
                # Verbatim L_KD from kd_gpu.py:140-147 (log_target, batchmean).
                l_kd = torch.nn.functional.kl_div(
                    torch.log_softmax(trans_a, dim=-1),
                    torch.log_softmax(e["self_logits_A"], dim=-1),
                    log_target=True, reduction="batchmean",
                ) + torch.nn.functional.kl_div(
                    torch.log_softmax(trans_b, dim=-1),
                    torch.log_softmax(e["self_logits_B"], dim=-1),
                    log_target=True, reduction="batchmean",
                )
                # lam_cf=0 frozen: no CF term is ever added.
                loss = lam_kd * l_kd + lam_reg * module.regularization()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
                optimizer.step()
                loss_log.append(float(loss.detach()))
    finally:
        handle.remove()

    module.eval()
    mapper = MLPLinearKDMapper(module)
    audit: dict[str, Any] = {
        "name": NAME,
        "trainable_params": module.parameter_count(),
        "parameter_structure": {
            "W_K": list(module.W_K.shape), "W_V": list(module.W_V.shape),
            "bias_params": 0, "init": init,
        },
        "loss_formula": (
            "L_KD = sum_sides KL(log_softmax(mapped_s) || log_softmax(self_s), "
            "log_target=True, reduction='batchmean'); "
            "loss = 1.0*L_KD + 1e-4*reg; lam_cf=0; reg=0 (rank-0 control)"
        ),
        "hyperparameters": {"epochs": epochs, "lr": lr, "lam_kd": lam_kd,
                            "lam_reg": lam_reg, "lam_cf": lam_cf, "seed": seed},
        "n_optimizer_steps": int(epochs * len(prepared)),
        "n_student_forwards_train": len(forward_lengths),
        "student_forward_input_lengths_train": forward_lengths,
        "max_query_len": int(max_query_len),
        "zero_re_prefill_train": bool(
            forward_lengths and all(c <= max_query_len for c in forward_lengths)
        ),
        "loss_log": loss_log,
        "loss_first": float(loss_log[0]) if loss_log else None,
        "loss_last": float(loss_log[-1]) if loss_log else None,
        "loss_finite": bool(loss_log and all(np.isfinite(v) for v in loss_log)),
    }
    if not audit["zero_re_prefill_train"]:
        raise AssertionError("training forwards violated zero re-prefill (doc tokens fed to student)")
    if not audit["loss_finite"]:
        raise AssertionError("L_KD produced non-finite loss")
    return mapper, audit


__all__ = [
    "NAME", "N_LAYERS", "N_HEADS", "HEAD_DIM", "EXPECTED_PARAMS",
    "MLPLinearKDModule", "MLPLinearKDMapper", "train_mlp_kd_gpu",
]
