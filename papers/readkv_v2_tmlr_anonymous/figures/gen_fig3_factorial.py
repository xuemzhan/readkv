"""Figure 3: the calibration-by-validation result, with its two components."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import data_access as data
from plot_style import (BAND, FS, GRID, JOINT, MUTED, NEUTRAL, SELF, SEED_MARKERS,
                        TEXT_WIDTH_IN, panel_title, save_fig)

W, H = TEXT_WIDTH_IN, 3.55


def main() -> None:
    factorial = data.results()["factorial"]
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(W, H), sharey=True,
        gridspec_kw={"width_ratios": [1.0, 0.98], "wspace": 0.10})

    rows = data.row_labels()
    positions = np.arange(len(rows))[::-1]

    for (cell, seed), y in zip(rows, positions):
        mean, low, high = (100 * value for value in factorial[f"{cell}_{seed}"]["L"])
        colour = NEUTRAL if cell == "A00" else JOINT
        left.errorbar(mean, y, xerr=[[mean - low], [high - mean]], fmt=SEED_MARKERS[seed],
                      color=colour, ecolor=colour, elinewidth=1.0, capsize=2.2, capthick=0.9,
                      markeredgecolor="white", markeredgewidth=0.6, markersize=5.4, zorder=4)
        left.plot(mean, y, SEED_MARKERS[seed], color=colour, markeredgecolor="white",
                  markeredgewidth=0.6, markersize=5.4, zorder=5)
    left.axvline(0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)), zorder=2)
    left.set_xlabel("$L$ = Self $-$ Joint dual correctness (points)")
    left.set_xlim(-26, 96)
    left.set_xticks([-20, 0, 20, 40, 60, 80])

    for (cell, seed), y in zip(rows, positions):
        self_level = 100 * factorial[f"{cell}_{seed}"]["self"]
        joint_level = 100 * factorial[f"{cell}_{seed}"]["joint"]
        right.plot([joint_level, self_level], [y, y], color=MUTED, linewidth=1.0, zorder=2)
        right.plot(self_level, y, SEED_MARKERS[seed], color=SELF, markersize=5.4,
                   markeredgecolor="white", markeredgewidth=0.6, zorder=4)
        right.plot(joint_level, y, SEED_MARKERS[seed], color=JOINT, markersize=5.4,
                   markeredgecolor="white", markeredgewidth=0.6, zorder=4)
    right.set_xlabel("dual correctness (\\%)")
    right.set_xlim(12, 98)
    right.set_xticks([20, 40, 60, 80])

    for ax in (left, right):
        ax.set_ylim(-0.8, len(rows) - 0.2)
        ax.xaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)

    for cell_index, cell in enumerate(data.CELLS):
        top = positions[3 * cell_index] + 0.5
        bottom = positions[3 * cell_index + 2] - 0.5
        if cell == "A00":
            for ax in (left, right):
                ax.axhspan(bottom, top, color=BAND, zorder=0)
        if cell_index:
            for ax in (left, right):
                ax.axhline(top, color=MUTED, linewidth=0.5, alpha=0.7)

    left.set_yticks(positions, [f"{cell} $\\cdot$ s{seed}" for cell, seed in rows])
    left.tick_params(axis="y", length=0, pad=3)
    panel_title(left, "a")
    panel_title(right, "b")

    handles = [plt.Line2D([], [], marker=SEED_MARKERS[seed], linestyle="", color=MUTED,
                          markeredgecolor="white", markersize=5.2, label=f"seed {seed}")
               for seed in data.SEEDS]
    handles += [plt.Line2D([], [], marker="o", linestyle="", color=SELF, markeredgecolor="white",
                           markersize=5.2, label="Self level"),
                plt.Line2D([], [], marker="o", linestyle="", color=JOINT, markeredgecolor="white",
                           markersize=5.2, label="Joint level")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.01), ncol=5,
               fontsize=FS["small"], handletextpad=0.4, columnspacing=1.4)
    fig.subplots_adjust(bottom=0.24, top=0.93, left=0.10, right=0.98)
    save_fig(fig, data.FIGDIR / "fig3_factorial.pdf")


if __name__ == "__main__":
    main()
