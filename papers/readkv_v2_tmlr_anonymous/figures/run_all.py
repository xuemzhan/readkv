"""Regenerate every paper figure (and the LaTeX include snippets)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data_access as data  # noqa: E402

MODULES = ("gen_fig1_design", "gen_fig2_corpus", "gen_fig3_factorial",
           "gen_fig4_scoring", "gen_fig5_controls", "gen_fig6_slices",
           "gen_fig7_ecf_validity")


def main() -> None:
    for name in MODULES:
        importlib.import_module(name).main()
    print(f"figures written to {data.FIGDIR}")


if __name__ == "__main__":
    main()
