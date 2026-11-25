from readkv.evaluate.gates import compute_csg, evaluate_h2, evaluate_h3


def test_h2_degraded_and_neutral():
    degraded = evaluate_h2([-0.2] * 30, epsilon=0.02, n_resamples=200)
    assert not degraded.passed and degraded.detail["direction"] == "degraded"
    neutral = evaluate_h2([0.0] * 30, epsilon=0.02, n_resamples=200)
    assert neutral.passed and neutral.detail["direction"] == "neutral"


def test_h3_requires_positive_lower_bound():
    none = evaluate_h3([[0.0] * 30 for _ in range(6)], n_resamples=200)
    assert not none.passed
    assert none.detail["family_wise_max"]["observed"] == 0.0
    gain = evaluate_h3([[0.2] * 30], n_resamples=200)
    assert gain.passed


def test_csg():
    assert abs(compute_csg(0.7, 0.4) - 0.3) < 1e-9
