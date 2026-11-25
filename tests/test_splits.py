from readkv.data.splits import disjoint_split, make_calibration_budget
from readkv.data.synthetic import generate_synthetic_domain


def test_disjoint_split_by_cluster():
    items = list(range(12))
    cluster_of = lambda x: f"C{x // 4}"
    cal, ev = disjoint_split(items, calibration=4, evaluation=4, seed=0, cluster_of=cluster_of)
    assert set(cal).isdisjoint(ev)
    assert len(cal) == 4 and len(ev) == 4


def test_calibration_budget():
    items = list(range(100))
    budget = make_calibration_budget(items, 30, seed=0)
    assert len(budget) == 30 and len(set(budget)) == 30


def test_synthetic_domain():
    items = generate_synthetic_domain(n_entities=8, n_docs=4, seed=0)
    assert len(items) == 16
    assert all(item.answer in {"active", "paused", "shipped", "cancelled"} for item in items)
