"""Cross-check the figures against the paper: table values, prose counts, output files."""
from __future__ import annotations

import io
import re
from pathlib import Path

import data_access as data

ORDER = [("A00", 0), ("A00", 1), ("A00", 2), ("A01", 0), ("A01", 1), ("A01", 2),
         ("A10", 0), ("A10", 1), ("A10", 2), ("A11", 0), ("A11", 1), ("A11", 2)]


def table_rows(name: str):
    tex = io.open(data.PAPER / "results.tex", encoding="utf-8").read()
    body = re.search(r"\\newcommand\{\\" + name + r"\}\{%(.*?)\n\}", tex, re.S).group(1)
    return [line.strip() for line in body.strip().splitlines()]


def check_factorial():
    rows = table_rows("FactorialRows")
    results = data.results()["factorial"]
    problems = []
    assert len(rows) == len(ORDER), len(rows)
    for (cell, seed), row in zip(ORDER, rows):
        columns = [column.strip() for column in row.rstrip("\\").split("&")]
        expected_self, expected_joint = columns[2], columns[3]
        expected_L = re.match(r"\$(-?[\d.]+)", columns[4]).group(1)
        actual = results[f"{cell}_{seed}"]
        for name, expected, value in (("Self", expected_self, 100 * actual["self"]),
                                      ("Joint", expected_joint, 100 * actual["joint"]),
                                      ("L", expected_L, 100 * actual["L"][0])):
            if f"{value:.1f}" != expected:
                problems.append(f"{cell} s{seed} {name}: table {expected} vs figure {value:.1f}")
    return problems


def check_contrasts():
    rows = table_rows("MainContrastRows")
    results = data.results()["sequence_contrasts"]
    problems = []
    for seed, row in enumerate(rows):
        columns = [column.strip() for column in row.rstrip("\\").split("&")]
        assert columns[0] == str(seed), columns[0]
        for column, (mode, _) in zip(columns[1:], data.READOUTS):
            expected = re.match(r"\$(-?[\d.]+)", column).group(1)
            actual = 100 * results[str(seed)]["main"][mode]["cluster"][0]
            if f"{actual:.1f}" != expected:
                problems.append(f"seed {seed} {mode}: table {expected} vs figure {actual:.1f}")
    return problems


def check_kd():
    rows = table_rows("KDRows")
    results = data.results()["kd"]
    problems = []
    for seed, row in enumerate(rows):
        columns = [column.strip() for column in row.rstrip("\\").split("&")]
        expected_L = re.match(r"\$(-?[\d.]+)", columns[3]).group(1)
        actual = 100 * results[str(seed)]["L"][0]
        if f"{actual:.1f}" != expected_L:
            problems.append(f"kd seed {seed}: table {expected_L} vs figure {actual:.1f}")
    return problems


def check_corpus_prose():
    """The defect counts the figure plots must be the ones the paper states."""
    prose = io.open(data.PAPER / "main.tex", encoding="utf-8").read()
    defects = data.corpus_defects()
    degenerate = [defects["legacy"][seed]["degenerate"] for seed in data.SEEDS]
    overlap = [defects["legacy"][seed]["doc_overlap"] for seed in data.SEEDS]
    problems = []
    sentence = re.search(r"original validation sets have (\d+), (\d+) and (\d+) degenerate", prose)
    if not sentence or [int(value) for value in sentence.groups()] != degenerate:
        problems.append(f"prose degenerate pairs {sentence and sentence.groups()} vs figure {degenerate}")
    sentence = re.search(r"either document side, is (\d+), (\d+) and (\d+)", prose)
    if not sentence or [int(value) for value in sentence.groups()] != overlap:
        problems.append(f"prose document overlap {sentence and sentence.groups()} vs figure {overlap}")
    if any(defects["fixed"][seed][key] for seed in data.SEEDS
           for key in ("degenerate", "doc_overlap", "query_overlap")):
        problems.append("rebuilt corpus still shows a defect")
    return problems


def check_fig6_bars():
    """Re-render fig6 and check the plotted bar heights against the ledger.

    A `100 * list` typo previously plotted the raw 0--1 fractions on an axis
    labelled in points; table-only checks could not see it.
    """
    import importlib
    import matplotlib.pyplot as plt

    module = importlib.import_module("gen_fig6_slices")
    captured = {}
    original = module.save_fig

    def wrapped(fig, path, stamp=False):
        captured["fig"] = fig
        original(fig, path, stamp=stamp)

    module.save_fig = wrapped
    try:
        module.main()
    finally:
        module.save_fig = original

    fig = captured["fig"]
    bar_axes = [ax for ax in fig.axes if len(ax.patches) == 6]
    if not bar_axes:
        return ["fig6(b): could not locate the six bar patches"]
    heights = sorted(round(patch.get_height(), 1) for patch in bar_axes[0].patches)
    results = data.results()
    expected = sorted(
        [round(100 * results["factorial"][f"A11_{seed}"]["L"][0], 1) for seed in data.SEEDS]
        + [round(100 * results["kd"][str(seed)]["L"][0], 1) for seed in data.SEEDS]
    )
    problems = []
    if heights != expected:
        problems.append(f"fig6(b) bar heights {heights} vs ledger {expected}")
    plt.close(fig)
    return problems


def check_files():
    problems = []
    for stem in ("fig1_design", "fig2_corpus", "fig3_factorial", "fig4_scoring",
                 "fig5_controls", "fig6_slices", "fig7_ecf"):
        for suffix in (".pdf", ".png"):
            path = data.FIGDIR / f"{stem}{suffix}"
            if not path.exists() or path.stat().st_size < 2000:
                problems.append(f"missing or empty {path.name}")
    return problems


def main() -> int:
    problems = []
    for name, check in (("factorial table", check_factorial), ("sequence contrasts", check_contrasts),
                        ("distillation baseline", check_kd), ("corpus prose", check_corpus_prose),
                        ("fig6 bar heights", check_fig6_bars), ("figure files", check_files)):
        found = check()
        print(f"[{name}] {'ok' if not found else str(len(found)) + ' mismatch(es)'}")
        for problem in found:
            print(f"    {problem}")
        problems += found
    print(f"\n{len(problems)} mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
