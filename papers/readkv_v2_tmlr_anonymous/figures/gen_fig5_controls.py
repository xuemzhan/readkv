"""Figure 5: counterfactual error next to the control caches, and per-pair signs."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import data_access as data
from plot_style import (BAND, FS, GRID, JOINT, MUTED, NEUTRAL, SEED_MARKERS, TEXT_WIDTH_IN,
                        panel_title, save_fig)

W, H = TEXT_WIDTH_IN, 2.95
ARMS = (("joint_ecf", "Joint"), ("mismatch", "Mismatched"), ("zero", "Zero"),
        ("random", "Randomised"))
# The three controls share one fill colour; hatching is what tells them apart
# in the legend and in grayscale.
HATCHES = {"joint_ecf": None, "mismatch": "//", "zero": "..", "random": "\\\\"}


def main() -> None:
    results = data.results()
    factorial = results["factorial"]
    dataset = data.evaluation()["factorial"]

    fig, (left, right) = plt.subplots(
        1, 2, figsize=(W, H), gridspec_kw={"width_ratios": [1.06, 0.94], "wspace": 0.26})

    positions = np.arange(len(data.SEEDS))
    width = 0.20
    for arm_index, (key, label) in enumerate(ARMS):
        offset = (arm_index - 1.5) * width
        if key == "joint_ecf":
            values = [factorial[f"A11_{seed}"]["joint_ecf"][0] for seed in data.SEEDS]
            low = [factorial[f"A11_{seed}"]["joint_ecf"][1] for seed in data.SEEDS]
            high = [factorial[f"A11_{seed}"]["joint_ecf"][2] for seed in data.SEEDS]
            face = JOINT
        else:
            values = [factorial[f"A11_{seed}"]["controls"][key] for seed in data.SEEDS]
            low = high = None
            face = "white"
        left.bar(positions + offset, values, width * 0.92, color=face, edgecolor=JOINT,
                 linewidth=0.9, label=label, zorder=3, hatch=HATCHES[key])
        if low is not None:
            left.errorbar(positions + offset, values,
                          yerr=[np.subtract(values, low), np.subtract(high, values)],
                          fmt="none", ecolor=NEUTRAL, elinewidth=0.9, capsize=2.0,
                          capthick=0.8, zorder=4)
    left.set_xticks(positions, [f"seed {seed}" for seed in data.SEEDS])
    left.tick_params(axis="x", length=0)
    left.set_ylabel("$E_{\\mathrm{CF}}$ (first token, nats)")
    left.set_ylim(0, 16.5)
    left.set_yticks([0, 4, 8, 12, 16])
    left.yaxis.grid(True, color=GRID, linewidth=0.6)
    left.set_axisbelow(True)
    left.legend(ncol=2, loc="upper left", fontsize=FS["small"], handlelength=1.0,
                columnspacing=1.0, borderaxespad=0.3)
    panel_title(left, "a")

    limit = 20
    for seed in data.SEEDS:
        rows = [row for row in dataset[f"A11_{seed}"]
                if row["slice"] in data.SEMANTIC and abs(row["dself"]) > 0.1]
        keep = [row for row in rows if abs(row["dself"]) <= limit and abs(row["djoint"]) <= limit]
        right.scatter([row["dself"] for row in keep], [row["djoint"] for row in keep],
                      s=13, marker=SEED_MARKERS[seed], facecolor="none", edgecolor=JOINT,
                      linewidth=0.8, alpha=0.85, zorder=3)
    right.add_patch(plt.Rectangle((-limit, -limit), 2 * limit, 2 * limit, facecolor="white",
                                  edgecolor="none", zorder=0))
    # Shaded quadrants mark sign flips; the inset therefore sits in the
    # unshaded top-right quadrant. Points outside +/-20 nats are clipped.
    right.axhspan(0, limit, xmin=0, xmax=0.5, color=BAND, zorder=1)   # self<0, joint>0: sign flip
    right.axvspan(0, limit, ymin=0, ymax=0.5, color=BAND, zorder=1)   # self>0, joint<0: sign flip
    right.axhline(0, color=MUTED, linewidth=0.8, zorder=2)
    right.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
    right.plot([-limit, limit], [-limit, limit], color=NEUTRAL, linewidth=0.8,
               linestyle=(0, (4, 3)), zorder=2)
    agreement = [factorial[f"A11_{seed}"]["flip"] for seed in data.SEEDS]
    right.text(limit - 0.8, limit - 0.8,
               "sign agreement\n" + "\n".join(f"seed {seed}:  {a}/{b}"
                                             for seed, (a, b) in zip(data.SEEDS, agreement)),
               ha="right", va="top", fontsize=FS["small"], linespacing=1.45,
               bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=GRID,
                         linewidth=0.6))
    right.text(limit - 0.8, -limit + 0.8, "sign flip", ha="right", va="bottom",
               fontsize=FS["micro"], color=MUTED)
    right.set_xlim(-limit, limit)
    right.set_ylim(-limit, limit)
    right.set_xticks([-15, -5, 0, 5, 15])
    right.set_yticks([-15, -5, 0, 5, 15])
    right.set_xlabel("$D_{\\mathrm{Self}}$")
    right.set_ylabel("$D_{\\mathrm{Joint}}$")
    right.set_aspect("equal", adjustable="box")
    right.tick_params(length=0)
    panel_title(right, "b")
    fig.subplots_adjust(top=0.92, bottom=0.18, left=0.11, right=0.97)
    save_fig(fig, data.FIGDIR / "fig5_controls.pdf")


if __name__ == "__main__":
    main()
