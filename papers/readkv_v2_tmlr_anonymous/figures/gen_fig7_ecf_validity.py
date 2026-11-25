"""Figure 7: dual correctness vs counterfactual error, and the scale check.

All points come from `reports/audit_reanalysis.json`, which is regenerated
from the verified anonymous numeric ledger by `scripts.audit_reanalysis`.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from data_access import REPO, FIGDIR
from plot_style import (DISTILL, GRID, JOINT, NEUTRAL, panel_title,
                        save_fig, use_style)

use_style()


def main() -> None:
    d = json.loads((REPO / "reports" / "audit_reanalysis.json").read_text(encoding="utf-8"))
    scatter = d["E4_ecf_validity"]["scatter"]
    scale = d["E4_ecf_validity"]["scale"]
    rho = d["E4_ecf_validity"]["rank_correlation"]

    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.5))
    ax = axes[0]
    for arm, colour, marker, label in (
        ("affine", JOINT, "o", r"affine ($\rho=-0.44$)"),
        ("kd", DISTILL, "s", r"distillation ($\rho=+0.43$)"),
    ):
        rows = scatter[arm]
        x = [r["ecf"] for r in rows]
        y = [r["dual_joint"] for r in rows]
        ax.scatter(x, y, s=11, alpha=0.55, c=colour, marker=marker, label=label,
                   edgecolors="none")
    ax.set_xlim(0, 30)
    ax.set_ylim(-0.06, 1.06)
    ax.set_yticks([0, 1], ["incorrect", "correct"])
    ax.set_xlabel(r"Joint $E_{\mathrm{CF}}$ (log-probability units)")
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.5))
    ax.axhline(0.5, color=GRID, lw=0.6, zorder=0)
    panel_title(ax, "a")

    ax = axes[1]
    seeds = ("0", "1", "2")
    xpos = np.arange(3)
    for cell, colour, marker, label in (
        ("A00", JOINT, "o", "original / original"),
        ("A11", DISTILL, "s", "rebuilt / rebuilt"),
    ):
        ratios = [scale[cell][s]["ecf_over_abs_dself"] for s in seeds]
        ax.plot(xpos, ratios, marker=marker, color=colour, lw=1.2, label=label)
    ax.set_xticks(xpos, ["seed 0", "seed 1", "seed 2"])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel(r"mean $E_{\mathrm{CF}}$ / mean $|D_{\mathrm{Self}}|$")
    ax.legend(loc="upper left")
    panel_title(ax, "b")

    fig.tight_layout(w_pad=1.6)
    save_fig(fig, FIGDIR / "fig7_ecf.pdf", stamp=True)


if __name__ == "__main__":
    main()
