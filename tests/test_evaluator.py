import numpy as np

from readkv.evaluate.evaluator import corrected_em, gold_letter_prob, normalize_answer, validator_agreement
from readkv.evaluate.validator import check_identity, logit_cosine


def test_normalize_and_em():
    assert normalize_answer("The  Status, is SHIPPED!") == "status is shipped"
    assert corrected_em("A shipped status", "a shipped status") == 1.0
    assert corrected_em("paused", "shipped") == 0.0


def test_gold_letter_prob():
    logits = np.array([2.0, 1.0, 0.0, -1.0])
    p = gold_letter_prob(logits, [0, 1, 2, 3])
    assert 0.5 < p < 0.8


def test_validator_agreement():
    a = [{"generated": "ok", "first_token": 1, "token_probs": [0.6, 0.4]} for _ in range(4)]
    b = [{"generated": "ok", "first_token": 1, "token_probs": [0.6, 0.4]} for _ in range(4)]
    result = validator_agreement(a, b)
    assert result["normalized_em_agreement"] == 1.0
    assert result["top1_agreement"] == 1.0
    assert result["median_kl"] < 1e-6


def test_identity_gate():
    assert check_identity([0.99999, 0.9999]).passed
    assert not check_identity([0.99999, 0.99]).passed
    assert logit_cosine([1, 0], [1, 0]) == 1.0
