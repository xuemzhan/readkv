"""Mapper 家族：representation / consumer / behavioral / adapter / hidden-state。

所有 mapper 只用校准集拟合；评测与门限判定不在此包内。
"""

from .base import BaseMapper, ridge_solve
from .representation import AffineMapper, RidgeMapper
from .consumer import ConsumerSpaceMapper
from .key_objectives import ScoreRegressionKeyMapper

__all__ = [
    "BaseMapper",
    "ridge_solve",
    "RidgeMapper",
    "AffineMapper",
    "ConsumerSpaceMapper",
    "ScoreRegressionKeyMapper",
]
