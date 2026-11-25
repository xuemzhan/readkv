"""数据：合成 KG 域、HellaSwag/ARC、SQuAD、不相交切分 + V2 反事实文档对。"""

from .build_cf_pairs import CFPair, build_cf_pairs, load_pairs, quality_report, save_pairs, split_pairs
from .qa import load_four_choice, load_squad
from .splits import disjoint_split, make_calibration_budget
from .synthetic import generate_synthetic_domain

__all__ = [
    "generate_synthetic_domain", "load_four_choice", "load_squad",
    "disjoint_split", "make_calibration_budget",
    "CFPair", "build_cf_pairs", "split_pairs", "quality_report", "save_pairs", "load_pairs",
]
