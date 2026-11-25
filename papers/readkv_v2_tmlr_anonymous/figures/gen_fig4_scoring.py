"""Figure 4: does the direction survive a different candidate score?"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import data_access as data
from plot_style import (BAND, FS, GRID, JOINT, MUTED, NEUTRAL, SEED_MARKERS, TEXT_WIDTH_IN,
                        panel_title, save_fig)

W, H = TEXT_WIDTH_IN, 3.0
SHORT = {"first": "first", "full": "full", "length_normalized": "length-norm"}


def main() -> None:
    results = data.results()
    sequence = results["sequence"]
    contrasts = results["sequence_contrasts"]

    fig, (left, right) = plt.subplots(
        1, 2, figsize=(W, H), gridspec_kw={"width_ratios": [0.86, 1.14], "wspace": 0.34})

    x = np.arange(len(data.READOUTS))
    for cell in ("A00", "A11"):
        for seed in data.SEEDS:
            levels = [100 * sequence[f"{cell}_{seed}"]["main"][mode]["L"][0]
                      for mode, _ in data.READOUTS]
            colour = NEUTRAL if cell == "A00" else JOINT
            left.plot(x, levels, color=colour, linewidth=1.2,
                      linestyle="--" if cell == "A00" else "-",
                      marker=SEED_MARKERS[seed], markersize=4.8,
                      markeredgecolor="white", markeredgewidth=0.5, zorder=3)
    left.axhline(0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)), zorder=1)
    left.set_xticks(x, [label for _, label in data.READOUTS], fontsize=FS["tick"])
    left.set_xlim(-0.32, len(x) - 0.68)
    left.set_ylim(-8, 95)   # headroom keeps the (longer, translated) legend off the data
    left.set_yticks([0, 20, 40, 60])
    left.set_ylabel("$L$ (points)")
    left.yaxis.grid(True, color=GRID, linewidth=0.6)
    left.set_axisbelow(True)
    panel_title(left, "a")

    handles = [plt.Line2D([], [], color=NEUTRAL, linestyle="--", linewidth=1.2, label="A00"),
               plt.Line2D([], [], color=JOINT, linewidth=1.2, label="A11")]
    handles += [plt.Line2D([], [], marker=SEED_MARKERS[seed], linestyle="", color=MUTED,
                           markeredgecolor="white", markersize=4.6, label=f"seed {seed}")
                for seed in data.SEEDS]
    left.legend(handles=handles, loc="upper left", ncol=2, fontsize=FS["small"],
                handletextpad=0.4, columnspacing=1.0, borderaxespad=0.3)

    rows = [(seed, mode) for seed in data.SEEDS for mode, _ in data.READOUTS]
    positions = np.arange(len(rows))[::-1]
    for (seed, mode), y in zip(rows, positions):
        mean, low, high = (100 * value for value in
                           contrasts[str(seed)]["main"][mode]["cluster"])
        right.errorbar(mean, y, xerr=[[mean - low], [high - mean]], fmt=SEED_MARKERS[seed],
                       color=JOINT, ecolor=JOINT, elinewidth=1.0, capsize=2.2, capthick=0.9,
                       markeredgecolor="white", markeredgewidth=0.6, markersize=5.4, zorder=4)
    right.axvline(0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)), zorder=2)
    right.axvspan(0, 120, color=BAND, zorder=0)
    for seed_index in range(1, len(data.SEEDS)):
        right.axhline(len(data.READOUTS) * seed_index - 0.5, color=MUTED, linewidth=0.5,
                      alpha=0.7)
    right.set_yticks(positions, [f"{SHORT[mode]}  s{seed}" for seed, mode in rows])
    right.tick_params(axis="y", length=0, pad=3)
    right.set_xlabel("$L_{\\mathrm{A11}}-L_{\\mathrm{A00}}$ (points)")
    right.set_xlim(-14, 110)
    right.set_xticks([0, 25, 50, 75, 100])
    right.set_ylim(-0.8, len(rows) - 0.2)
    right.xaxis.grid(True, color=GRID, linewidth=0.6)
    right.set_axisbelow(True)
    panel_title(right, "b")
    fig.subplots_adjust(top=0.92, bottom=0.17, left=0.09, right=0.98)
    save_fig(fig, data.FIGDIR / "fig4_scoring.pdf")


if __name__ == "__main__":
    main()
