"""Reproduce the paper's tables from anonymized evaluation summaries on a CPU."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import string

import numpy as np


CELLS = ("A00", "A01", "A10", "A11")
READINGS = ("first", "full", "length_normalized")
SEMANTIC = {"F1", "F2", "F3", "F4"}
RESAMPLES = 10_000


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def normalized_bytes(path):
    return path.read_bytes().replace(b"\r\n", b"\n")


def digest(path):
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


def verify_file_manifest(run):
    for record in read_json(run / "manifest.json")["files"]:
        content = normalized_bytes(run / record["name"])
        if len(content) != record["size"] or hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError(f"File manifest mismatch in {run.name}/{record['name']}")


def token_digest(ids):
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode("utf-8")).hexdigest()


def verify_forward_audit(folder, scored):
    branches = read_rows(folder / "forward_audit.jsonl")
    identities = set()
    cache_ids = set()
    queries = {}
    calls = 0
    for row in branches:
        sample = row["sample_id"]
        arm, side, candidate = (row[name] for name in ("arm", "doc_side", "candidate"))
        key = (sample, arm, side, candidate)
        ids = row["candidate_token_ids"]
        q, m, doc = row["query_len"], len(ids), row["doc_len"]
        positions = [doc, *range(doc + q, doc + q + m - 1)]
        fingerprints = row["input_token_fingerprints"]
        first_query = queries.setdefault(sample, fingerprints[0])
        if (key in identities or row["branch_cache_id"] in cache_ids
                or row["position_offset"] != doc
                or row["candidate_len"] != m
                or row["input_length_sequence"] != [q] + [1] * (m - 1)
                or row["forward_position_starts"] != positions
                or row["cache_prefix_lengths"] != positions
                or fingerprints != [first_query, *(token_digest([i]) for i in ids[:-1])]
                or row["candidate_token_id_fingerprint"] != token_digest(ids)
                or not row["audit_passed"] or not row["zero_re_prefill"]):
            raise ValueError(f"Forward audit mismatch in {folder.name}: {key}")
        score_row = scored[sample, arm]
        if row["sample_hash"] != score_row["sample_hash"] or m != score_row[f"candidate_len_{candidate}"]:
            raise ValueError("Forward audit and score record disagree")
        identities.add(key)
        cache_ids.add(row["branch_cache_id"])
        calls += m
    expected = {(sid, arm, side, candidate)
                for sid, arm in scored for side in "AB" for candidate in "AB"}
    if identities != expected:
        raise ValueError("Forward audit does not cover all scoring branches")
    return {"branches": len(branches), "forwards": calls}


def normalize(answer):
    answer = answer.lower().translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\b(a|an|the)\b", " ", answer).split()


def anchor_scores(repo):
    path = repo / "data/anchors/squad/dev-v2.0.json"
    source = read_json(path)
    refs = {}
    for article in source["data"]:
        for paragraph in article["paragraphs"]:
            for query in paragraph["qas"]:
                if not query["is_impossible"]:
                    refs[query["id"]] = [
                        tokens for answer in query["answers"] if (tokens := normalize(answer["text"]))
                    ] or [[]]
    output = {}
    for name in ("affine", "kd"):
        run = repo / "reports/runs" / f"anchor_squad_{name}_seed0"
        output[name] = {"self": [], "joint": []}
        for row in read_rows(run / "scores.jsonl"):
            prediction = normalize(row["pred"])
            gold = refs[row["example_id"]]
            overlaps = [sum((Counter(prediction) & Counter(answer)).values()) for answer in gold]
            f1 = max(2 * n / (len(prediction) + len(answer)) if n else float(prediction == answer)
                     for n, answer in zip(overlaps, gold))
            output[name][row["arm"]].append([float(prediction in gold), f1, row["EM"], row["F1"]])
        if any(len(rows) != 240 for rows in output[name].values()):
            raise ValueError("Expected 240 saved predictions per SQuAD arm")
    return output


def extract(repo):
    runs = repo / "reports/runs"
    data_root = repo / "data/audit_2x2"
    output = {"factorial": {}, "sequence": {}, "kd": {}, "audit": {}, "squad": anchor_scores(repo)}
    for seed in range(3):
        for cell in CELLS:
            folder = runs / f"audit_2x2_{cell}_s{seed}"
            verify_file_manifest(folder)
            version = "legacy" if cell in ("A00", "A10") else "fixed"
            source = read_rows(data_root / version / f"val_seed{seed}.jsonl")
            arms = {(row["sample_id"], row["arm"]): row for row in read_rows(folder / "scores.jsonl")}
            if len(source) != 60 or any(
                arms[row["sample_id"], arm]["sample_hash"] != row["sample_hash"]
                for row in source for arm in ("self", "joint")
            ):
                raise ValueError("Factorial sample input mismatch")
            output["factorial"][f"{cell}_{seed}"] = [
                {
                    "id": pair["pair_id"],
                    "family": pair["template_family"],
                    "slice": pair["slice_id"],
                    "distinct": pair["candidate_A"] != pair["candidate_B"],
                    "self": arms[pair["sample_id"], "self"]["dual_correct"],
                    "joint": arms[pair["sample_id"], "joint"]["dual_correct"],
                    "dself": arms[pair["sample_id"], "self"]["D_self"],
                    "djoint": arms[pair["sample_id"], "joint"]["D_trans"],
                    "controls": {name: arms[pair["sample_id"], f"control:{name}"]["E_CF"]
                                 for name in ("mismatch", "random", "zero")},
                }
                for pair in source
            ]
            if cell in ("A00", "A11"):
                folder = runs / f"audit_seq_{cell}_s{seed}_b0"
                verify_file_manifest(folder)
                config = read_json(folder / "config.json")
                for split in ("train", "val"):
                    path = data_root / version / f"{split}_seed{seed}.jsonl"
                    if digest(path) != config["experiment_config"]["input_sha256"][split]:
                        raise ValueError("Sequence input hash mismatch")
                sequence = {(row["sample_id"], row["arm"]): row for row in read_rows(folder / "scores.jsonl")}
                if len(sequence) != 120 or any(
                    sequence[pair["sample_id"], arm]["sample_hash"] != pair["sample_hash"]
                    or sequence[pair["sample_id"], arm]["gold"] != {side: pair[f"correct_{side}"] for side in "AB"}
                    for pair in source for arm in ("self", "joint")
                ):
                    raise ValueError("Sequence sample or gold mismatch")
                output["audit"][f"{cell}_{seed}"] = verify_forward_audit(folder, sequence)
                output["sequence"][f"{cell}_{seed}"] = [
                    {
                        "id": pair["pair_id"], "family": pair["template_family"],
                        "slice": pair["slice_id"], "distinct": pair["candidate_A"] != pair["candidate_B"],
                        "gold": [pair["correct_A"], pair["correct_B"]],
                        "lengths": [sequence[pair["sample_id"], "self"][f"candidate_len_{side}"] for side in "AB"],
                        **{arm: {
                            "scores": [
                                [sequence[pair["sample_id"], arm]["scores"][side][cand] for cand in "AB"]
                                for side in "AB"
                            ],
                            "archived_first_dual": sequence[pair["sample_id"], arm]["dual_correct"]["first"],
                         } for arm in ("self", "joint")},
                    }
                    for pair in source
                ]
        kd_run = repo / "reports/data/gpu_experiments/v1/raw" / f"p1_kd_clean_mvp_seed{seed}"
        arms = {(row["pair_id"], row["arm"]): row for row in read_rows(kd_run / "scores.jsonl")}
        fixed_val = read_rows(data_root / "fixed" / f"val_seed{seed}.jsonl")
        if any(arms[pair["pair_id"], arm]["cache_hash"] != pair["sample_hash"]
               for pair in fixed_val for arm in ("self", "joint")):
            raise ValueError("Distillation and affine validation samples disagree")
        output["kd"][str(seed)] = [
            {
                "id": pair["id"], "family": pair["family"], "slice": pair["slice"],
                "self": arms[pair["id"], "self"]["dual_correct"],
                "joint": arms[pair["id"], "joint"]["dual_correct"],
                "dself": arms[pair["id"], "self"]["D_self"],
                "djoint": arms[pair["id"], "joint"]["D_trans"],
            }
            for pair in output["factorial"][f"A11_{seed}"]
        ]
    return output


def cluster_arrays(values, labels):
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels)
    groups = [values[labels == label] for label in sorted(set(labels))]
    return np.array([group.sum() for group in groups]), np.array([len(group) for group in groups])


def draws(stats, picks, *, family_equal=False):
    sums, counts = stats
    if family_equal:
        return (sums / counts)[picks].mean(axis=1)
    return sums[picks].sum(axis=1) / counts[picks].sum(axis=1)


def interval(values, labels, seed, other=None, *, family_equal=False):
    first = cluster_arrays(values, labels)
    n_first = len(first[0])
    rng = np.random.default_rng(seed)
    estimate = float(np.mean(first[0] / first[1]) if family_equal else np.mean(values))
    if other is None:
        picks = rng.integers(0, n_first, (RESAMPLES, n_first))
        boot = draws(first, picks, family_equal=family_equal)
    else:
        baseline, other_labels = other
        second = cluster_arrays(baseline, other_labels)
        n_second = len(second[0])
        if n_first == n_second:
            picks = rng.integers(0, n_first, (RESAMPLES, 2, n_first))
            left, right = picks[:, 0, :], picks[:, 1, :]
        else:
            left = rng.integers(0, n_first, (RESAMPLES, n_first))
            right = rng.integers(0, n_second, (RESAMPLES, n_second))
        boot = draws(first, left, family_equal=family_equal) - draws(second, right, family_equal=family_equal)
        estimate -= float(np.mean(second[0] / second[1]) if family_equal else np.mean(baseline))
    return [estimate, *map(float, np.quantile(boot, (.025, .975)))]


def by_reading(rows, mode, arm):
    margins = []
    dual = []
    for row in rows:
        scores = row[arm]["scores"]
        gs = [side[0][mode] - side[1][mode] for side in scores]
        margins.append(gs[0] - gs[1])
        dual.append(all(label == "A/B" or label == ("A" if g >= 0 else "B")
                        for label, g in zip(row["gold"], gs)))
    return np.array(dual, dtype=float), np.array(margins)


def retained(rows):
    return [row for row in rows if row["slice"] in SEMANTIC and row["distinct"] and set(row["gold"]) == {"A", "B"}]


def score_summary(a, b, ds, dj, labels, seed):
    return {
        "n": len(a), "families": len(set(labels)),
        "self": float(a.mean()), "joint": float(b.mean()),
        "L": interval(a-b, labels, seed),
        "joint_ecf": interval(abs(ds-dj), labels, seed),
        "self_ecf": 0.0,
    }


def analyze(dataset):
    output = {"factorial": {}, "contrasts": {}, "sequence": {}, "sequence_contrasts": {}, "kd": {}, "squad": {}}
    old_agreement = corrected_agreement = 0
    for seed in range(3):
        obs = {}
        for cell in CELLS:
            key = f"{cell}_{seed}"
            rows = dataset["factorial"][key]
            f = [r["family"] for r in rows]
            a, b, ds, dj = (np.array([r[name] for r in rows]) for name in ("self", "joint", "dself", "djoint"))
            obs[cell] = (a-b, f)
            summary = score_summary(a, b, ds, dj, f, seed)
            summary["controls"] = {name: float(np.mean([r["controls"][name] for r in rows]))
                                   for name in ("mismatch", "random", "zero")}
            eligible = np.array([r["slice"] in SEMANTIC for r in rows]) & (abs(ds) > 0.1)
            summary["flip"] = [int(np.sum(eligible & (np.sign(dj) == np.sign(ds)))), int(eligible.sum())]
            summary["slice_L"] = {
                label: float(np.mean((a-b)[[condition(row) for row in rows]]))
                for label, condition in (
                    ("F1-F4", lambda row: row["slice"] in SEMANTIC),
                    ("distinct", lambda row: row["distinct"]),
                    ("F6", lambda row: row["slice"] == "F6"),
                )
            }
            summary["joint_ecf_pair"] = interval(abs(ds-dj), [r["id"] for r in rows], seed)
            output["factorial"][key] = summary
        old_cal = obs["A10"][0] - obs["A00"][0]
        fixed_cal = obs["A11"][0] - obs["A01"][0]
        output["contrasts"][str(seed)] = {
            "A10-A00": interval(old_cal, obs["A00"][1], seed),
            "A11-A01": interval(fixed_cal, obs["A11"][1], seed),
            "A01-A00": interval(*obs["A01"], seed, obs["A00"]),
            "A11-A10": interval(*obs["A11"], seed, obs["A10"]),
            "interaction": interval(fixed_cal, obs["A11"][1], seed, (old_cal, obs["A00"][1])),
        }
        for name, hi, lo in (("A01-A00", "A01", "A00"), ("A11-A10", "A11", "A10")):
            output["contrasts"][str(seed)][f"{name}_family_equal"] = interval(*obs[hi], seed, obs[lo], family_equal=True)
        seq = {"main": {}, "all": {}}
        for cell in ("A00", "A11"):
            key = f"{cell}_{seed}"
            full_rows = dataset["sequence"][key]
            if [r["id"] for r in full_rows] != [r["id"] for r in dataset["factorial"][key]]:
                raise ValueError(f"Replay ledgers do not align for {key}")
            for arm in ("self", "joint"):
                original = [r[arm] for r in dataset["factorial"][key]]
                archived = [r[arm]["archived_first_dual"] for r in full_rows]
                corrected = by_reading(full_rows, "first", arm)[0]
                old_agreement += sum(a == b for a, b in zip(original, archived))
                corrected_agreement += sum(a == b for a, b in zip(original, corrected))
            output["sequence"][key] = {}
            for subset, rows in (("main", retained(full_rows)), ("all", full_rows)):
                labels = [r["family"] for r in rows]
                ids = [r["id"] for r in rows]
                obj = {}
                values = {}
                for mode in READINGS:
                    a, ds = by_reading(rows, mode, "self")
                    b, dj = by_reading(rows, mode, "joint")
                    obj[mode] = score_summary(a, b, ds, dj, labels, seed)
                    values[mode] = a-b
                difference = values["full"]-values["first"]
                obj["reading_difference"] = {
                    "cluster": interval(difference, labels, seed),
                    "pair": interval(difference, ids, seed),
                    "family_equal": interval(difference, labels, seed, family_equal=True),
                }
                seq[subset][cell] = (values, labels, ids)
                output["sequence"][key][subset] = obj
        output["sequence_contrasts"][str(seed)] = {}
        for subset in seq:
            hi, hf, hp = seq[subset]["A11"]
            lo, lf, lp = seq[subset]["A00"]
            comparisons = {m: (hi[m], lo[m]) for m in READINGS}
            comparisons["reading_of_difference"] = (hi["full"]-hi["first"], lo["full"]-lo["first"])
            output["sequence_contrasts"][str(seed)][subset] = {
                name: {
                    "cluster": interval(x, hf, seed, (y, lf)),
                    "pair": interval(x, hp, seed, (y, lp)),
                    "family_equal": interval(x, hf, seed, (y, lf), family_equal=True),
                }
                for name, (x, y) in comparisons.items()
            }
        rows = dataset["kd"][str(seed)]
        a, b, ds, dj = (np.array([r[name] for r in rows]) for name in ("self", "joint", "dself", "djoint"))
        f = [r["family"] for r in rows]
        output["kd"][str(seed)] = score_summary(a, b, ds, dj, f, seed)
        output["kd"][str(seed)]["L_semantic"] = float(np.mean((a-b)[[r["slice"] in SEMANTIC for r in rows]]))
    output["replay"] = {"archived_matches": int(old_agreement), "harmonized_matches": int(corrected_agreement), "total": 720}
    if output["replay"] != {"archived_matches": 630, "harmonized_matches": 720, "total": 720}:
        raise ValueError(f"Unexpected first-token replay: {output['replay']}")
    output["audit"] = {name: sum(run[name] for run in dataset["audit"].values())
                       for name in ("branches", "forwards")}
    if output["audit"] != {"branches": 2880, "forwards": 5340}:
        raise ValueError("Unexpected forward audit totals")
    for name, arms in dataset["squad"].items():
        output["squad"][name] = {arm: np.mean(rows, axis=0).tolist() for arm, rows in arms.items()}
    return output


def latex_tables(results):
    def percent(x):
        return f"{100*x:.1f}"

    def triplet(x):
        mean, lo, hi = map(percent, x)
        return f"${mean}\\;[{lo},{hi}]$"

    def plain_ci(x):
        mean, lo, hi = x
        return f"${mean:.2f}\\;[{lo:.2f},{hi:.2f}]$"

    def rows(name, content):
        lines.append("\\newcommand{\\" + name + "}{%")
        lines.extend(" & ".join(row) + r" \\" for row in content)
        lines.append("}")

    lines = ["% Generated by reproduce.py. Edit the renderer or source data."]
    f = results["factorial"]
    q = results["sequence"]
    contrast = results["sequence_contrasts"]
    rows("FactorialRows", (
        [cell, str(seed), percent(v["self"]), percent(v["joint"]), triplet(v["L"])]
        for cell in CELLS for seed in range(3) for v in [f[f"{cell}_{seed}"]]
    ))
    rows("SequenceRows", (
        [cell, str(seed), str(v["full"]["n"]),
         f'{percent(v["first"]["self"])} / {percent(v["first"]["joint"])}',
         f'{percent(v["full"]["self"])} / {percent(v["full"]["joint"])}',
         percent(v["first"]["L"][0]), percent(v["full"]["L"][0]),
         percent(v["length_normalized"]["L"][0])]
        for cell in ("A00", "A11") for seed in range(3) for v in [q[f"{cell}_{seed}"]["main"]]
    ))
    rows("MainContrastRows", (
        [str(seed), *(triplet(contrast[str(seed)]["main"][m]["cluster"]) for m in READINGS)]
        for seed in range(3)
    ))
    rows("AffineControlRows", (
        [str(seed), plain_ci(v["joint_ecf"]), plain_ci(v["joint_ecf_pair"]),
         *(f'{v["controls"][m]:.2f}' for m in ("mismatch", "zero", "random")),
         "/".join(map(str, v["flip"]))]
        for seed in range(3) for v in [f[f"A11_{seed}"]]
    ))
    rows("KDRows", (
        [str(seed), percent(v["self"]), percent(v["joint"]), triplet(v["L"]),
         percent(v["L_semantic"]), plain_ci(v["joint_ecf"])]
        for seed in range(3) for v in [results["kd"][str(seed)]]
    ))
    c = results["contrasts"]
    rows("FactorialContrastRows", (
        [label.replace("-", "$-$"), *(triplet(c[str(s)][label]) for s in range(3))]
        for label in ("A10-A00", "A11-A01", "A01-A00", "A11-A10", "interaction")
    ))
    rows("EqualFamilyRows", (
        [label.replace("-", "$-$"), *(triplet(c[str(s)][f"{label}_family_equal"]) for s in range(3))]
        for label in ("A01-A00", "A11-A10")
    ))
    rows("ScoringChangeRows", (
        [str(seed), triplet(q[f"A11_{seed}"]["main"]["reading_difference"]["cluster"]),
         triplet(contrast[str(seed)]["main"]["reading_of_difference"]["cluster"]),
         triplet(contrast[str(seed)]["main"]["reading_of_difference"]["pair"]),
         triplet(contrast[str(seed)]["main"]["reading_of_difference"]["family_equal"])]
        for seed in range(3)
    ))
    rows("AllPairsRows", (
        [cell, str(seed), *(percent(q[f"{cell}_{seed}"]["all"][m]["L"][0]) for m in READINGS)]
        for cell in ("A00", "A11") for seed in range(3)
    ))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="Extract numeric ledgers from a full project checkout")
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    output_path = args.directory
    output_path.mkdir(parents=True, exist_ok=True)
    ledger = output_path / "evaluation.json"
    if args.repo:
        dataset = extract(args.repo)
        ledger.write_text(json.dumps(dataset, separators=(",", ":")) + "\n", encoding="utf-8")
    else:
        dataset = read_json(ledger)
    results = analyze(dataset)
    (output_path / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (output_path / "results.tex").write_text(latex_tables(results), encoding="utf-8")
    print(f"Verified {results['replay']['harmonized_matches']}/{results['replay']['total']} historical decisions")
    print(f"Replayed {len(results['factorial'])} factorial cells and {len(results['sequence'])} scoring cells")


if __name__ == "__main__":
    main()
