"""Local, CPU-only reanalyses requested by the docs/audit revision plan.

E3  Controls with per-seed CIs, paired tolerance tests and TOST equivalence.
E4  E_CF validity: dual-vs-E_CF scatter data, scale normalisation, mapper overlap.
E7  Sequence-scoring extension from the 6-family `retained` subset to the
    full F1--F4 set (8 families) using archived per-pair scores only.

No GPU run and no new data are produced.  Every input is read from the
verified anonymous supplement (`evaluation.json`) and the pre-declared
equivalence margin (`configs/prereg/equivalence_margin_v2.9.yaml`).

Usage:
    python -m scripts.audit_reanalysis
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "papers" / "readkv_v2_tmlr_anonymous"
OUT = ROOT / "reports" / "audit_reanalysis.json"
DELTA = 2.0  # must match configs/prereg/equivalence_margin_v2.9.yaml

# Reuse the exact statistical helpers of the verified reproduction script so
# intervals cannot drift from the published ones.
_spec = importlib.util.spec_from_file_location("_reproduce", PAPER / "reproduce.py")
repro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repro)

READINGS = repro.READINGS
SEMANTIC = repro.SEMANTIC


def rnd(x, nd=4):
    if isinstance(x, (list, tuple)):
        return [rnd(v, nd) for v in x]
    if isinstance(x, (int, float, np.floating, np.integer)):
        return round(float(x), nd)
    return x


def family_means(values: np.ndarray, labels: list[str]) -> np.ndarray:
    families = sorted(set(labels))
    return np.array([values[[i for i, l in enumerate(labels) if l == f]].mean() for f in families])


def ecf(rows, key_a: str = "dself", key_b: str = "djoint") -> np.ndarray:
    return np.abs(np.array([r[key_b] - r[key_a] for r in rows], dtype=float))


def tost(fam_diff: np.ndarray, delta: float = DELTA):
    """Two one-sided tests + 90% CI on family means (df = n_families - 1)."""
    n = len(fam_diff)
    mean = float(fam_diff.mean())
    se = float(stats.sem(fam_diff))
    df = n - 1
    t_lo = (mean + delta) / se            # H0: mean <= -delta
    t_hi = (mean - delta) / se            # H0: mean >= +delta
    p_lo = float(stats.t.sf(t_lo, df))
    p_hi = float(stats.t.cdf(t_hi, df))
    p_tost = max(p_lo, p_hi)
    crit = float(stats.t.ppf(0.95, df))
    ci90 = [mean - crit * se, mean + crit * se]
    two_sided = stats.ttest_1samp(fam_diff, 0.0)
    return {
        "n_families": n,
        "family_mean_diff": rnd(mean),
        "family_se": rnd(se),
        "two_sided_p": rnd(float(two_sided.pvalue), 5),
        "tost_p_lo": rnd(p_lo, 5),
        "tost_p_hi": rnd(p_hi, 5),
        "tost_p": rnd(p_tost, 5),
        "ci90_family": rnd(ci90),
        "equivalent_at_delta": bool(p_tost < 0.05 and ci90[0] > -delta and ci90[1] < delta),
    }


# ---------------------------------------------------------------------------
# E3 -- controls, tolerance and equivalence
# ---------------------------------------------------------------------------
def e3(dataset):
    out = {}
    for seed in range(3):
        rows = dataset["factorial"][f"A11_{seed}"]
        labels = [r["family"] for r in rows]
        joint = ecf(rows)
        out[str(seed)] = {
            "joint_ecf_cluster": rnd(repro.interval(joint, labels, seed)),
            "n_pairs": len(rows),
            "n_families": len(set(labels)),
            "controls": {},
        }
        for name in ("mismatch", "zero", "random"):
            ctrl = np.array([r["controls"][name] for r in rows], dtype=float)
            diff = joint - ctrl
            out[str(seed)]["controls"][name] = {
                "control_mean_cluster_ci": rnd(repro.interval(ctrl, labels, seed)),
                "joint_minus_control_cluster_ci": rnd(repro.interval(diff, labels, seed)),
                "family_test": tost(family_means(diff, labels)),
            }
    return out


# ---------------------------------------------------------------------------
# E4 -- E_CF validity, scale and mapper separation
# ---------------------------------------------------------------------------
def e4(dataset, results):
    scale, scatter, overlap = {}, {}, {}
    for cell in ("A00", "A11"):
        scale[cell] = {}
        for seed in range(3):
            rows = dataset["factorial"][f"{cell}_{seed}"]
            ds = np.abs(np.array([r["dself"] for r in rows], dtype=float))
            j = ecf(rows)
            scale[cell][str(seed)] = {
                "mean_abs_dself": rnd(ds.mean()),
                "mean_joint_ecf": rnd(j.mean()),
                "ecf_over_abs_dself": rnd(j.mean() / ds.mean()),
            }
    scatter["affine"] = []
    scatter["kd"] = []
    for seed in range(3):
        for row in dataset["factorial"][f"A11_{seed}"]:
            scatter["affine"].append({
                "seed": seed, "family": row["family"], "slice": row["slice"],
                "dual_joint": row["joint"], "ecf": abs(row["djoint"] - row["dself"]),
                "abs_dself": abs(row["dself"]),
            })
        for row in dataset["kd"][str(seed)]:
            scatter["kd"].append({
                "seed": seed, "family": row["family"], "slice": row["slice"],
                "dual_joint": row["joint"], "ecf": abs(row["djoint"] - row["dself"]),
                "abs_dself": abs(row["dself"]),
            })
    rho = {}
    for arm in ("affine", "kd"):
        dual = [r["dual_joint"] for r in scatter[arm]]
        err = [r["ecf"] for r in scatter[arm]]
        r, p = stats.spearmanr(dual, err)
        rho[arm] = {"spearman_rho": rnd(r), "p": float(p), "n": len(dual)}
    for seed in range(3):
        overlap[str(seed)] = {
            "affine_joint_ecf_cluster": rnd(results["factorial"][f"A11_{seed}"]["joint_ecf"]),
            "kd_joint_ecf_cluster": rnd(results["kd"][str(seed)]["joint_ecf"]),
            "affine_dual_joint": rnd(results["factorial"][f"A11_{seed}"]["joint"]),
            "kd_dual_joint": rnd(results["kd"][str(seed)]["joint"]),
        }
    return {"scale": scale, "scatter": scatter, "rank_correlation": rho, "mapper_separation": overlap}


# ---------------------------------------------------------------------------
# E7 -- sequence scoring on the full F1--F4 set
# ---------------------------------------------------------------------------
def e7(dataset):
    out = {"subsets": {}, "per_seed": {}}
    for name, keep in (
        ("retained_6_family", repro.retained),
        ("f1_f4_all_6_family", lambda rows: [r for r in rows if r["slice"] in SEMANTIC]),
        ("all_60_pairs_8_family", lambda rows: rows),
    ):
        counts = {}
        for cell in ("A00", "A11"):
            for seed in range(3):
                rows = keep(dataset["sequence"][f"{cell}_{seed}"])
                counts[f"{cell}_{seed}"] = {"pairs": len(rows), "families": len({r["family"] for r in rows})}
        out["subsets"][name] = counts
    for seed in range(3):
        seed_obj = {}
        for subset_name, keep in (
            ("f1_f4", lambda rows: [r for r in rows if r["slice"] in SEMANTIC]),
            ("all_60", lambda rows: rows),
        ):
            obj = {}
            prepared = {}
            for cell in ("A00", "A11"):
                rows = keep(dataset["sequence"][f"{cell}_{seed}"])
                labels = [r["family"] for r in rows]
                values = {}
                for mode in READINGS:
                    a, _ = repro.by_reading(rows, mode, "self")
                    b, _ = repro.by_reading(rows, mode, "joint")
                    values[mode] = a - b
                    obj[f"{cell}_{mode}_L"] = rnd(repro.interval(a - b, labels, seed))
                prepared[cell] = (values, labels)
            for mode in READINGS:
                hi, hf = prepared["A11"]
                lo, lf = prepared["A00"]
                obj[f"contrast_{mode}"] = rnd(repro.interval(hi[mode], hf, seed, (lo[mode], lf)))
            seed_obj[subset_name] = obj
        out["per_seed"][str(seed)] = seed_obj
    return out


def main() -> None:
    dataset = json.loads((PAPER / "evaluation.json").read_text(encoding="utf-8"))
    results = json.loads((PAPER / "results.json").read_text(encoding="utf-8"))
    output = {
        "protocol": "configs/prereg/equivalence_margin_v2.9.yaml",
        "delta": DELTA,
        "external_registration": False,
        "exploratory": True,
        "source": "verified anonymous supplement; no new GPU runs",
        "E3_controls_equivalence": e3(dataset),
        "E4_ecf_validity": e4(dataset, results),
        "E7_extended_sequence_scoring": e7(dataset),
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
