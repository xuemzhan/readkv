"""评测层：修正评测器、对照、三道门、探针、诊断量 + V2 反事实保真。"""

from .controls import build_control
from .counterfactual import (
    CounterfactualSummary,
    PairCFRecord,
    counterfactual_error,
    g_score,
    paired_ecf_difference,
    response_difference,
    summarize_cf,
)
from .evaluator import answer_probability, corrected_em, gold_letter_prob, normalize_answer
from .gates import GateResult, evaluate_h1, evaluate_h2, evaluate_h3
from .pipeline import PipelineConfig, fit_mapper, run_pipeline
from .probes import fraction_probe, octant_probe, window_probe
from .validator import logit_cosine

__all__ = [
    "corrected_em",
    "gold_letter_prob",
    "answer_probability",
    "normalize_answer",
    "PipelineConfig",
    "fit_mapper",
    "run_pipeline",
    "build_control",
    "GateResult",
    "evaluate_h1",
    "evaluate_h2",
    "evaluate_h3",
    "fraction_probe",
    "window_probe",
    "octant_probe",
    "logit_cosine",
    # V2
    "CounterfactualSummary",
    "PairCFRecord",
    "g_score",
    "response_difference",
    "counterfactual_error",
    "summarize_cf",
    "paired_ecf_difference",
]
