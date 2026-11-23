"""C3 回归：consistency_check._check_model_pair 的 2×2 等价字段识别。

覆盖：
(a) 带 calibration_version/validation_version 的 2×2 config → ok=true（推断 MVP，等深断言）；
(b) 既有 model_pair config 判定不变（正常 + 误配）；
(c) 锚点 config 判定不变（teacher/student 路径推断豁免）。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts.consistency_check import _check_model_pair


def _cfg(ec, meta=None):
    return {"experiment_config": ec, "metadata": meta or {}}


def test_2x2_calibration_validation_fields_ok():
    ec = {
        "stage": "audit_2x2", "calibration_version": "legacy", "validation_version": "fixed",
        "layer_map": {"kind": "identity", "n_student_layers": 28, "n_teacher_layers": 28},
        "input_sha256": {"train-old": "a" * 64},
    }
    r = _check_model_pair(_cfg(ec))
    assert r["ok"] is True
    assert r["inferred_model_pair"] == "qwen3-1.7b-to-0.6b"
    assert r["equal_depth_asserted"] is True
    assert "entrypoint default" in r["inference_note"]


def test_2x2_bad_equal_depth_fails():
    ec = {
        "calibration_version": "fixed", "validation_version": "legacy",
        "layer_map": {"n_student_layers": 28, "n_teacher_layers": 36},
    }
    r = _check_model_pair(_cfg(ec))
    assert r["ok"] is False
    assert r["equal_depth_asserted"] is False


def test_existing_model_pair_unchanged_ok():
    ec = {"model_pair": "qwen3-1.7b-to-0.6b",
          "teacher": "/x/Qwen3-1.7B", "student": "/x/Qwen3-0.6B",
          "layer_map": {"n_student_layers": 28, "n_teacher_layers": 28}}
    r = _check_model_pair(_cfg(ec))
    assert r["ok"] is True and r["exempt"] is False


def test_existing_model_pair_unchanged_mismatch():
    ec = {"model_pair": "qwen3-4b-to-1.7b",
          "teacher": "/x/Qwen3-1.7B", "student": "/x/Qwen3-0.6B"}
    r = _check_model_pair(_cfg(ec))
    assert r["ok"] is False
    assert any("teacher path" in p for p in r["problems"])


def test_anchor_config_unchanged():
    ec = {"stage": "external_anchor", "anchor_benchmark": "SQuAD v2.0 dev",
          "teacher": "/x/Qwen3-1.7B", "student": "/x/Qwen3-0.6B"}
    r = _check_model_pair(_cfg(ec))
    assert r["ok"] is True
    assert r["exempt"] is True and r["inferred_model_pair"] == "qwen3-1.7b-to-0.6b"
