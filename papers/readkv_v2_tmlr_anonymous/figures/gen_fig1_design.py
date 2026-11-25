"""Figure 1: cache path and the calibration-by-validation design (schematic + grid)."""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import data_access as data
from plot_style import (BAND, FS, JOINT, NEUTRAL, SELF, TEXT_WIDTH_IN, panel_title,
                        save_fig)

W, H = TEXT_WIDTH_IN, 4.0


def _box(ax, x, y, w, h, text, *, face="white", edge=NEUTRAL, size=FS["label"]):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.14", linewidth=0.8,
                                edgecolor=edge, facecolor=face, mutation_aspect=0.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            linespacing=1.25)


def _arrow(ax, start, end, *, label=None, label_xy=None, color=NEUTRAL, dashed=False,
           size=FS["micro"]):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8, linewidth=0.8,
                                 color=color, shrinkA=2.0, shrinkB=2.0,
                                 linestyle="--" if dashed else "-"))
    if label:
        ax.text(*label_xy, label, ha="center", va="center", fontsize=size, color=color,
                linespacing=1.3)


def _pipeline(ax):
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")
    panel_title(ax, "a")
    ax.text(4.0, 47.6, "Joint arm transports the sender's keys and values.  "
                       "Self arm substitutes the receiver's own cache of the same document.",
            ha="left", va="center", fontsize=FS["small"], color=NEUTRAL)

    top, height, mid = 30, 12, 36.0
    _box(ax, 0.5, top, 12, height, "document\n$d_A$ / $d_B$")
    _box(ax, 18, top, 14, height, "sender\nQwen3-1.7B")
    _box(ax, 37.5, top, 20, height, "affine ridge map\nper layer, K and V\n$\\lambda=10^{-3}$",
         face=BAND, edge=JOINT)
    _box(ax, 63, top, 14, height, "receiver\nQwen3-0.6B\n(frozen)")
    _box(ax, 82.5, top, 17, height, "candidate score\n$s(c;C,q)$")

    _arrow(ax, (12.9, mid), (17.6, mid), label="document", label_xy=(15.2, mid + 7.6))
    _arrow(ax, (32.4, mid), (37.1, mid), label="keys / values", label_xy=(34.8, mid + 7.6))
    _arrow(ax, (57.9, mid), (62.6, mid), label="transported\ncache", label_xy=(60.2, mid + 6.4))
    _arrow(ax, (77.4, mid), (82.1, mid))

    _box(ax, 60.0, 10, 20, 11.5,
         "query $q$ + candidate prefix\n(first token, or teacher-forced)", size=FS["micro"])
    _arrow(ax, (70.0, 21.6), (70.0, 29.6))
    # Keep the label clear of its own arrow and of both boxes.
    ax.text(77.0, 26.0, "positions read\noff the cache", ha="left", va="center",
            fontsize=FS["micro"], color=NEUTRAL, linespacing=1.3)

    # The Self arm carries the receiver's own cache, so it bypasses the mapper and
    # enters the receiver from below. The route keeps seven units of clearance
    # from the pipeline row and stops short of the query/prefix box, so it crosses
    # no box and no other connector.
    route = [(6.5, 29.5), (6.5, 23.0), (65.5, 23.0), (65.5, 28.7)]
    ax.plot([point[0] for point in route], [point[1] for point in route], color=SELF,
            linewidth=0.8, linestyle=(0, (3.2, 2.2)), solid_capstyle="butt", zorder=2)
    ax.add_patch(FancyArrowPatch((65.5, 28.7), (65.5, 29.4), arrowstyle="-|>",
                                 mutation_scale=8, linewidth=0.8, color=SELF, zorder=2))
    ax.text(31.0, 20.3, "Self arm", fontsize=FS["small"], color=SELF,
            ha="center", va="center", style="italic")

    ax.text(0.5, 4.4,
            "$g(C,q)=s(A;C,q)-s(B;C,q)$        "
            "$D=g(C(d_A),q)-g(C(d_B),q)$        "
            "$L=\\mathrm{Self}-\\mathrm{Joint}$        "
            "$E_{\\mathrm{CF}}=|D_{\\mathrm{Joint}}-D_{\\mathrm{Self}}|$",
            fontsize=FS["small"], va="center", color=NEUTRAL)


def _design(ax, results):
    ax.set_xlim(-0.60, 2.12)
    ax.set_ylim(-0.42, 2.10)
    ax.axis("off")
    ax.text(-0.56, 2.04, "(b)", ha="left", va="top", fontsize=FS["title"])

    for row, cell_row in enumerate((("A00", "A01"), ("A10", "A11"))):
        for column, cell in enumerate(cell_row):
            x0, y0 = column, 1 - row
            historical = cell == "A00"
            ax.add_patch(plt.Rectangle((x0 + 0.04, y0 + 0.05), 0.92, 0.88, linewidth=0.8,
                                       edgecolor=NEUTRAL if historical else JOINT,
                                       facecolor=BAND if historical else "white"))
            gaps = [100 * results["factorial"][f"{cell}_{seed}"]["L"][0] for seed in data.SEEDS]
            ax.text(x0 + 0.50, y0 + 0.72, cell, ha="center", va="center", fontsize=FS["base"])
            ax.text(x0 + 0.50, y0 + 0.47, "  ".join(f"{gap:+.1f}" for gap in gaps),
                    ha="center", va="center", fontsize=FS["label"])
            ax.text(x0 + 0.50, y0 + 0.22, "seed 0 / 1 / 2", ha="center", va="center",
                    fontsize=FS["micro"], color=NEUTRAL)

    for column, name in enumerate(("original", "rebuilt")):
        ax.text(column + 0.50, -0.11, name, ha="center", va="center", fontsize=FS["small"])
    for row, name in enumerate(("original", "rebuilt")):
        ax.text(-0.07, 1 - row + 0.49, name, ha="right", va="center", fontsize=FS["small"])
    ax.text(1.0, -0.35, "validation corpus", ha="center", va="center", fontsize=FS["label"])
    ax.text(-0.50, 1.0, "calibration corpus", ha="center", va="center", fontsize=FS["label"],
            rotation=90)
    ax.text(2.12, -0.33, "$L$ in points, one per seed", ha="right", va="center",
            fontsize=FS["micro"], color=NEUTRAL)


def main() -> None:
    results = data.results()
    fig = plt.figure(figsize=(W, H))
    grid = fig.add_gridspec(2, 1, height_ratios=[1.34, 1.0], hspace=0.04)
    _pipeline(fig.add_subplot(grid[0]))
    _design(fig.add_subplot(grid[1]), results)
    save_fig(fig, data.FIGDIR / "fig1_design.pdf")


if __name__ == "__main__":
    main()
