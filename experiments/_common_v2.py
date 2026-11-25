"""V2 阶段脚本共享的后端/参数构建器。"""

from __future__ import annotations

import argparse
from dataclasses import replace

from readkv.config import load_config
from readkv.evaluate.cf_pipeline import CFPipelineConfig
from readkv.models.mock_backend import MockBackend, MockSpec
from readkv.runtime import v2_context


def add_v2_args(parser: argparse.ArgumentParser, *, default_stage: str) -> None:
    parser.add_argument("--backend", choices=["mock", "gpu"], default="mock")
    parser.add_argument("--run-id", default=f"{default_stage}_mock")
    parser.add_argument("--n-train", type=int, default=None)
    parser.add_argument("--n-val", type=int, default=None)
    parser.add_argument("--n-test", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")


def build_v2_mock(args: argparse.Namespace) -> tuple[MockBackend, CFPipelineConfig]:
    protocol = load_config("protocol")
    mock = load_config("mock")
    spec = MockSpec.from_config(mock)
    backend = MockBackend(spec)
    sizes = dict(protocol["data_sizes"])
    if args.n_train is not None:
        sizes["train"] = args.n_train
    if args.n_val is not None:
        sizes["val"] = args.n_val
    if args.n_test is not None:
        sizes["test"] = args.n_test
    seed = args.seed if args.seed is not None else protocol.get("default_seed", 0)
    cfg = CFPipelineConfig(
        sizes=sizes,
        seed=seed,
        n_resamples=1000,
        tau=protocol["counterfactual"]["tau"],
        self_threshold=protocol["counterfactual"]["self_threshold"],
        cf_distortion=spec.cf_distortion,
    )
    return backend, cfg


def new_ctx(args: argparse.Namespace, stage: str, config: dict | None = None, **kwargs):
    return v2_context(
        args.run_id,
        {"stage": stage, "backend": args.backend, **(config or {})},
        seed=args.seed or 0,
        metadata={"protocol_version": "2.0", "stage": stage},
        **kwargs,
    )


def clone_cf(cfg: CFPipelineConfig, **overrides) -> CFPipelineConfig:
    return replace(cfg, **overrides)


def require_gpu(args) -> None:
    if args.backend == "gpu":
        raise NotImplementedError(
            "GPU backend requires models/hooks.py implementation against the pinned "
            "transformers version (capture_teacher_cache / inject_and_generate / verify_zero_re_prefill)"
        )
