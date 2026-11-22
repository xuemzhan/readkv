"""配置加载与最小校验；所有实验入口必须通过这里读取 yaml。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"


def load_config(name: str) -> dict[str, Any]:
    """按名字加载 configs/ 下的 yaml。

    name 可以是 ``gates``、``stage1_key``，也可以是 ``prereg/stage1_decision``。
    """
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return data


def validate_gates(data: dict[str, Any]) -> None:
    """门限配置的最小完整性检查，防止缺字段时静默跑出不可比结果。"""
    for key in ("H1_identity", "H2_replacement", "H3_exploitability", "metrics"):
        if key not in data:
            raise ValueError(f"gates config missing section: {key}")
    if data["H1_identity"]["min_per_sample"] <= 0.99:
        raise ValueError("H1 tolerance must stay near 0.9998")
    eps = data["H2_replacement"]["epsilon"]
    if not 0.0 < eps <= 0.05:
        raise ValueError(f"epsilon out of supported range: {eps}")


def resolve_pair(name: str) -> dict[str, Any]:
    pairs = load_config("pairs")
    if name not in pairs["pairs"]:
        raise KeyError(f"unknown pair: {name}; available: {list(pairs['pairs'])}")
    merged = dict(pairs["defaults"])
    merged.update(pairs["pairs"][name])
    return merged
