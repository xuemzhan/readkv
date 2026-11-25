"""运行上下文与不可变产物管理。"""

from .context import ROOT, RunContext

__all__ = ["ROOT", "RunContext"]


def v2_context(run_id: str, config: dict, *, seed: int = 0,
               device: str = "cpu", dtype: str = "bfloat16", kernel: str = "sdpa",
               zero_re_prefill: bool = True, metadata: dict | None = None,
               reports_root=None) -> RunContext:
    """创建 V2.0 运行上下文（reports/runs/<run_id>/，protocol_version=2.0）。"""
    root = reports_root if reports_root is not None else ROOT / "reports" / "runs"
    return RunContext(
        run_id, config,
        protocol_version="2.0",
        seed=seed, device=device, dtype=dtype, kernel=kernel,
        zero_re_prefill=zero_re_prefill,
        reports_root=root,
        metadata=metadata,
    )
