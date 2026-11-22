"""RunContext：一次实验的全部可追溯元数据与产物入口。

产物布局（reports/<run_id>/）：
    config.json      冻结的配置、种子、dtype/kernel、git hash、协议版本
    scores.jsonl     逐样本分数（唯一真值来源）
    metrics.json     由 scores 重算的统计结论
    manifest.json    文件清单与写入时间
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[3]  # src/readkv/runtime/context.py -> repo root


def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "no-git"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RunContext:
    """创建即写 config.json；所有写入都留在 run 目录，禁止跨 run 覆盖。"""

    def __init__(
        self,
        run_id: str,
        config: Mapping[str, Any],
        *,
        protocol_version: str = "1.0",
        seed: int = 0,
        device: str = "cpu",
        dtype: str = "bfloat16",
        kernel: str = "sdpa",
        zero_re_prefill: bool = True,
        reports_root: Path | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.protocol_version = protocol_version
        self.seed = seed
        self.device = device
        self.dtype = dtype
        self.kernel = kernel
        self.zero_re_prefill = zero_re_prefill
        self.git_hash = _git_hash()
        self.created_at = _now()
        self.root = Path(reports_root) if reports_root else ROOT / "reports"
        self.out_dir = self.root / run_id
        self.out_dir.mkdir(parents=True, exist_ok=False)

        self.config = {
            "run_id": run_id,
            "protocol_version": protocol_version,
            "git_hash": self.git_hash,
            "created_at": self.created_at,
            "seed": seed,
            "device": device,
            "dtype": dtype,
            "kernel": kernel,
            "zero_re_prefill": zero_re_prefill,
            "experiment_config": dict(config),
        }
        if metadata:
            self.config["metadata"] = dict(metadata)
        self._write("config.json", self.config)
        self.seed_everything(seed)

    # ---------- 可复现性 ----------
    def seed_everything(self, seed: int) -> None:
        random.seed(seed)
        np.random.seed(seed)
        os.environ["PYTHONHASHSEED"] = str(seed)
        with suppress(ImportError):
            import torch

            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        # 注意：未启用 deterministic kernel selection；梯度训练族按多次训练报告范围。

    # ---------- 产物 ----------
    def _write(self, name: str, payload: Any) -> Path:
        path = self.out_dir / name
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        return path

    def write_scores(self, rows: Iterable[Mapping[str, Any]]) -> Path:
        path = self.out_dir / "scores.jsonl"
        n = 0
        with path.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(dict(row), ensure_ascii=False, default=str) + "\n")
                n += 1
        if n == 0:
            raise ValueError("no score rows written")
        return path

    def read_scores(self) -> list[dict[str, Any]]:
        path = self.out_dir / "scores.jsonl"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def write_metrics(self, name: str, payload: Mapping[str, Any]) -> Path:
        return self._write(name, payload)

    def write_ledger(self, name: str, rows: Iterable[Mapping[str, Any]]) -> Path:
        """V2：写逐对台账到 reports/runs/<run_id>/（JSONL，追加语义同 write_scores）。"""
        path = self.out_dir / name
        n = 0
        with path.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(dict(row), ensure_ascii=False, default=str) + "\n")
                n += 1
        if n == 0:
            raise ValueError("no ledger rows written")
        return path

    def finalize(self) -> Path:
        manifest = {"run_id": self.run_id, "files": []}
        for path in sorted(self.out_dir.iterdir()):
            if path.is_file():
                manifest["files"].append(
                    {
                        "name": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "size": path.stat().st_size,
                    }
                )
        return self._write("manifest.json", manifest)

    def require_zero_re_prefill(self) -> None:
        if not self.zero_re_prefill:
            raise RuntimeError("run is not marked zero_re_prefill; audit gates do not apply")

    def __repr__(self) -> str:
        return f"RunContext({self.run_id!r}, protocol={self.protocol_version}, seed={self.seed})"
