"""Figure 6: slice breakdown, and the distillation baseline beside the affine map."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import data_access as data
from plot_style import (DISTILL, FS, GRID, JOINT, MUTED, NEUTRAL, TEXT_WIDTH_IN, panel_title,
                        save_fig)

W, H = TEXT_WIDTH_IN, 3.25


def main() -> None:
    results = data.results()
    levels = data.slice_levels()

    fig, (left, right) = plt.subplots(
        1, 2, figsize=(W, H), gridspec_kw={"width_ratios": [1.50, 1.0], "wspace": 0.34})

    rows = data.row_labels()
    grid = np.array([[levels[cell, seed][slice_id] for slice_id in data.SLICES]
                     for cell, seed in rows])
    image = left.imshow(grid, cmap="RdBu_r", vmin=-70, vmax=70, aspect="auto")
    for row_index in range(grid.shape[0]):
        for column_index in range(grid.shape[1]):
            value = grid[row_index, column_index]
            left.text(column_index, row_index, f"{value:.0f}", ha="center", va="center",
                      fontsize=FS["micro"], color="white" if abs(value) > 44 else NEUTRAL)
    left.set_xticks(np.arange(len(data.SLICES)), data.SLICES, fontsize=FS["tick"])
    left.set_yticks(np.arange(len(rows)), [f"{cell} $\\cdot$ s{seed}" for cell, seed in rows],
                    fontsize=FS["tick"])
    left.tick_params(length=0)
    left.axvline(3.5, color="white", linewidth=2.0)
    left.text(1.5, -0.74, "semantic slices", ha="center", va="bottom", fontsize=FS["small"])
    left.text(4.5, -0.74, "controls", ha="center", va="bottom", fontsize=FS["small"],
              color=MUTED)
    for row_index in (2.5, 5.5, 8.5):
        left.axhline(row_index, color="white", linewidth=2.0)
    left.set_xlim(-0.5, len(data.SLICES) - 0.5)
    colourbar = fig.colorbar(image, ax=left, orientation="horizontal", fraction=0.05, pad=0.30,
                             aspect=38)
    colourbar.set_label("$L$ (points)", fontsize=FS["small"], labelpad=2)
    colourbar.set_ticks([-60, -30, 0, 30, 60])
    colourbar.ax.tick_params(labelsize=FS["micro"], length=2.5)
    colourbar.outline.set_linewidth(0.6)
    panel_title(left, "a")

    positions = np.arange(len(data.SEEDS))
    width = 0.36
    for arm_index, (key, label, colour) in enumerate(
            (("affine", "Affine", JOINT), ("kd", "Distillation", DISTILL))):
        if key == "affine":
            triples = [results["factorial"][f"A11_{seed}"]["L"] for seed in data.SEEDS]
        else:
            triples = [results["kd"][str(seed)]["L"] for seed in data.SEEDS]
        # Multiply element-wise. `100 * triple` would repeat the list 100 times
        # and silently plot the original 0--1 fractions on a points axis.
        estimates = [[100 * value for value in triple] for triple in triples]
        mean = [value[0] for value in estimates]
        low = [value[1] for value in estimates]
        high = [value[2] for value in estimates]
        offset = (arm_index - 0.5) * width
        right.bar(positions + offset, mean, width * 0.90, color=colour, edgecolor="white",
                  linewidth=0.6, label=label, zorder=3, hatch=None if key == "affine" else "//")
        right.errorbar(positions + offset, mean,
                       yerr=[np.subtract(mean, low), np.subtract(high, mean)],
                       fmt="none", ecolor=NEUTRAL, elinewidth=0.9, capsize=2.2, capthick=0.8,
                       zorder=4)
        for position, value, top in zip(positions + offset, mean, high):
            right.annotate(f"{value:.1f}", (position, max(top, 1.0)), textcoords="offset points",
                           xytext=(0, 2), ha="center", va="bottom", fontsize=FS["micro"],
                           color=NEUTRAL)
    right.axhline(0, color=MUTED, linewidth=0.8, zorder=2)
    right.set_xticks(positions, [f"seed {seed}" for seed in data.SEEDS])
    right.tick_params(axis="x", length=0)
    right.set_ylabel("$L$ (points)")
    right.set_ylim(-8, 96)
    right.set_yticks([0, 20, 40, 60, 80])
    right.yaxis.grid(True, color=GRID, linewidth=0.6)
    right.set_axisbelow(True)
    right.legend(loc="upper right", fontsize=FS["small"], handlelength=1.0,
                 handletextpad=0.5, borderaxespad=0.3)
    panel_title(right, "b")
    fig.subplots_adjust(top=0.93, bottom=0.14, left=0.10, right=0.98)
    save_fig(fig, data.FIGDIR / "fig6_slices.pdf")


if __name__ == "__main__":
    main()
