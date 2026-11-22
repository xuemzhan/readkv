"""机制诊断包：Routing / Consumption 分解与层头 Oracle 干预。"""

from readkv.diagnostics.route_value import (
    AttentionDecomposition,
    build_four_arms,
    decompose_attention,
    key_objective_matrix,
    oracle_transplant,
    rank_units_by_repair,
)

__all__ = [
    "AttentionDecomposition",
    "build_four_arms",
    "decompose_attention",
    "key_objective_matrix",
    "oracle_transplant",
    "rank_units_by_repair",
]
