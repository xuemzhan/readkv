"""Figure 2: what the corpus audit removed, recomputed from the corpus files."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import data_access as data
from plot_style import FS, GRID, LEGACY, NEUTRAL, REBUILT, TEXT_WIDTH_IN, save_fig

PANELS = (
    ("degenerate", "pairs"),
    ("doc_overlap", "strings"),
    ("query_overlap", "strings"),
)

W, H = TEXT_WIDTH_IN, 2.15


def main() -> None:
    defects = data.corpus_defects()
    fig, axes = plt.subplots(1, 3, figsize=(W, H))
    positions = np.arange(len(data.SEEDS))
    width = 0.36

    for index, (ax, (key, unit)) in enumerate(zip(axes, PANELS)):
        legacy = [defects["legacy"][seed][key] for seed in data.SEEDS]
        rebuilt = [defects["fixed"][seed][key] for seed in data.SEEDS]
        ax.bar(positions - width / 2 - 0.01, legacy, width, color=LEGACY, edgecolor="white",
               linewidth=0.5, label="original corpus", zorder=3)
        ax.bar(positions + width / 2 + 0.01, rebuilt, width, color=REBUILT, edgecolor="white",
               linewidth=0.5, label="rebuilt corpus", zorder=3)
        for offset, values in ((-width / 2, legacy), (width / 2, rebuilt)):
            for position, value in zip(positions + offset - 0.01, values):
                ax.annotate(f"{value:.0f}", (position, value), textcoords="offset points",
                            xytext=(0, 1.2), ha="center", va="bottom", fontsize=FS["micro"])
        ax.set_xticks(positions, [f"seed {seed}" for seed in data.SEEDS])
        ax.set_ylim(0, max(max(legacy), 1) * 1.30)  # independent scale: counts differ by 6x
        ax.set_ylabel(unit)
        ax.yaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)
        ax.set_title(f"({chr(97 + index)})", fontsize=FS["title"], loc="left", pad=5)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=LEGACY, edgecolor="white", linewidth=0.5),
               plt.Rectangle((0, 0), 1, 1, facecolor=REBUILT, edgecolor="white", linewidth=0.5)]
    fig.legend(handles, ["original corpus", "rebuilt corpus"], loc="upper center",
               bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=FS["small"],
               handlelength=1.1, columnspacing=1.6)
    fig.tight_layout(rect=(0, 0, 1, 0.93), w_pad=1.6)
    save_fig(fig, data.FIGDIR / "fig2_corpus.pdf")


if __name__ == "__main__":
    main()
