"""阶段脚本共享的后端/参数构建器。

默认 ``--backend mock``：在没有 GPU 的机器上跑通整条管线。
``--backend gpu`` 保留给目标机器，需先实现 models/hooks.py 契约。
"""

from __future__ import annotations

import argparse
from dataclasses import replace

from readkv.config import load_config
from readkv.evaluate.pipeline import PipelineConfig
from readkv.models.mock_backend import MockBackend, MockSpec


def add_backend_args(parser: argparse.ArgumentParser, *, default_stage: str) -> None:
    parser.add_argument("--backend", choices=["mock", "gpu"], default="mock")
    parser.add_argument("--run-id", default=f"{default_stage}_mock")
    parser.add_argument("--n-docs", type=int, default=None)
    parser.add_argument("--n-calib", type=int, default=None)
    parser.add_argument("--n-eval", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)


def build_mock(args: argparse.Namespace) -> tuple[MockBackend, PipelineConfig]:
    cfg = load_config("mock")
    spec = MockSpec.from_config(cfg)
    p = cfg["pipeline"]
    backend = MockBackend(spec)
    pipeline = PipelineConfig(
        n_docs=args.n_docs if args.n_docs is not None else p["n_docs"],
        n_calibration=args.n_calib if args.n_calib is not None else p["n_calibration"],
        n_eval=args.n_eval if args.n_eval is not None else p["n_eval"],
        seed=args.seed if args.seed is not None else p["seed"],
    )
    return backend, pipeline


def clone_pipeline(cfg: PipelineConfig, **overrides) -> PipelineConfig:
    """复制管线配置并覆盖字段，供多臂/多 runner 使用。"""
    return replace(cfg, **overrides)


def require_gpu_backend(args) -> None:
    if args.backend == "gpu":
        raise NotImplementedError(
            "GPU backend requires an implementation of readkv.models.hooks "
            "(capture_teacher_cache / inject_and_generate) against the pinned transformers version"
        )
