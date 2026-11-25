"""Shared publication style for the readkv audit figures.

One place for rcParams, the palette and the save helper, so every figure looks
like it came from the same paper. The scale is set for a 6.5 in text width
(`\\textwidth` of the TMLR style), which is also the figure width, so a size in
this file is the size on the page.

Palette note: the two arms differ in hue *and* in luminance (grayscale contrast
2.3:1), so the figures survive a black-and-white print. `audit_figures.py`
enforces that.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

TEXT_WIDTH_IN = 6.5

# Type scale: nothing on the page may fall below 7 pt.
FS = {"base": 9.0, "title": 8.6, "label": 8.0, "tick": 7.6, "small": 7.2, "micro": 7.0}
BASE = FS["base"]
DPI = 400

# Semantic colours. Terracotta marks the worse/problematic condition throughout
# the paper (Joint arm, original/defective corpus, weaker affine transfer); navy
# marks the native (Self) reference. The distillation baseline uses a much darker
# olive so that it separates from terracotta in grayscale (3.3:1).
SELF = "#22456F"
JOINT = "#C0604F"
DISTILL = "#20330F"
# Corpus-version colours: the defective original corpus inherits the
# "problematic" terracotta; the clean rebuild uses a neutral cool gray so the
# corpus axis does not reuse Self/Joint semantics.
LEGACY = JOINT
REBUILT = "#AAB4BD"

NEUTRAL = "#2E2E2E"
MUTED = "#7A7A7A"
BAND = "#EDF1F6"
GRID = "#E1E5EA"
PANEL_FILL = "#F7F8FA"

SEED_MARKERS = ("o", "s", "^")


def use_style() -> None:
    plt.rcParams.update({
        "font.size": FS["base"],
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "axes.labelsize": FS["label"],
        "axes.titlesize": FS["title"],
        "xtick.labelsize": FS["tick"],
        "ytick.labelsize": FS["tick"],
        "legend.fontsize": FS["small"],
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.edgecolor": NEUTRAL,
        "axes.labelcolor": NEUTRAL,
        "text.color": NEUTRAL,
        "xtick.color": NEUTRAL,
        "ytick.color": NEUTRAL,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.major.size": 2.8,
        "ytick.major.size": 2.8,
        "xtick.minor.width": 0.5,
        "lines.linewidth": 1.2,
        "lines.markersize": 5.0,
        "legend.frameon": False,
        "legend.handletextpad": 0.5,
        "legend.labelspacing": 0.35,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


use_style()


def panel_title(ax, letter: str) -> None:
    """Uniform panel tag in the top-left corner, outside the data."""
    ax.set_title(f"({letter})", fontsize=FS["title"], loc="left", pad=5)


def save_fig(fig, path, stamp: bool = False) -> None:
    """Write the vector PDF (and a PNG twin for quick reading) next to it."""
    if stamp:  # provenance note kept out of the way of the plotted data
        fig.text(0.995, 0.004, "readkv audit, regenerated from archived ledgers",
                 ha="right", va="bottom", fontsize=FS["micro"], color=MUTED)
    fig.savefig(path, format="pdf")
    fig.savefig(path.with_suffix(".png"), format="png")
    plt.close(fig)
    print(f"saved {path.name} (+png)")
