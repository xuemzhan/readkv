"""Render the Chinese twins of the six figures (`*_zh.pdf`).

Same geometry, same data, Chinese strings: `zh_labels` rewrites what matplotlib
draws, this module only changes the font (so CJK glyphs exist) and the output
name. Each Chinese figure is audited before it is saved — overlap,
legend-over-data, arrow-through-box, effective type size, colour separation —
and any missing glyph is a failure.
"""
from __future__ import annotations

import importlib
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt

import audit_figures
import check_layout
import plot_style
import zh_labels

MODULES = ("gen_fig1_design", "gen_fig2_corpus", "gen_fig3_factorial",
           "gen_fig4_scoring", "gen_fig5_controls", "gen_fig6_slices")


def _use_cjk_font() -> None:
    """SimSun: a CJK serif that also carries Latin and digits.

    The PDF backend cannot fall back between fonts inside one text run, so the
    Chinese figures use one family and ASCII hyphens for negative values.
    """
    plt.rcParams["font.family"] = ["SimSun"]
    plt.rcParams["font.serif"] = ["SimSun"]
    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["axes.unicode_minus"] = False   # SimSun has no U+2212


def main() -> int:
    zh_labels.install()
    _use_cjk_font()

    problems = []
    rendered = []
    original = plot_style.save_fig

    def wrapped(fig, path, stamp=False):
        stem = Path(path).stem + "_zh"
        target = Path(path).with_name(stem + ".pdf")
        # Audits run on the drawn canvas, before the file is written.
        problems.extend(check_layout.check(fig, stem))
        problems.extend(audit_figures.audit(fig, stem))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            original(fig, target, stamp=stamp)
        missing = [str(item.message) for item in caught if "missing from font" in str(item.message)]
        if missing:
            problems.extend(missing)
            print(f"[{stem}] MISSING GLYPHS: {missing[:3]}")
        rendered.append(stem)

    plot_style.save_fig = wrapped
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    for module_name in MODULES:
        module = importlib.import_module(module_name)
        module.save_fig = wrapped
        module.main()

    plt.close("all")
    print(f"\n{len(rendered)} Chinese figures, {len(problems)} issue(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
