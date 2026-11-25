"""Measure what a reader actually gets: effective print size, ink coverage, colour separation.

Every figure is rebuilt here and inspected through the artists it draws, so the
report describes the rendered canvas rather than the script's intentions. The
thresholds are the ones a 10pt two-column-wide paper figure has to clear:

  * smallest effective font at 6.5 in width  >= 7.0 pt
  * smallest marker                          >= 4.0 pt
  * thinnest stroke                          >= 0.5 pt
  * grayscale contrast between the two series (Self vs Joint) >= 1.5
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.text import Text

import plot_style

MODULES = ("gen_fig1_design", "gen_fig2_corpus", "gen_fig3_factorial",
           "gen_fig4_scoring", "gen_fig5_controls", "gen_fig6_slices")

TEXT_WIDTH_IN = 6.5      # \textwidth of the TMLR style file
MIN_FONT_PT = 7.0
MIN_MARKER_PT = 4.0
MIN_STROKE_PT = 0.5
MIN_GRAYSCALE_RATIO = 1.5


def luminance(colour) -> float:
    def channel(value):
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = to_rgb(colour)
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast(a, b) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def texts(fig):
    found = []
    for ax in fig.axes:
        found += list(ax.texts)
        found += [ax.title, ax.xaxis.label, ax.yaxis.label]
        found += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
        legend = ax.get_legend()
        if legend is not None:
            found += list(legend.get_texts())
    return [text for text in found if isinstance(text, Text) and text.get_text().strip()]


def strokes(fig):
    """Thinnest stroke and smallest marker actually drawn, in points."""
    widths = []
    markers = []

    def note(artist):
        if hasattr(artist, "get_linewidth"):
            widths.append(artist.get_linewidth())
        if hasattr(artist, "get_marker") and artist.get_marker() not in ("None", None, ""):
            if hasattr(artist, "get_markersize"):
                markers.append(artist.get_markersize())

    for ax in fig.axes:
        for line in ax.get_lines():
            note(line)
        for container in ax.containers:
            for artist in getattr(container, "lines", []):
                for line in (artist if isinstance(artist, (list, tuple)) else [artist]):
                    note(line)
        for patch in ax.patches:
            note(patch)
        for spine in ax.spines.values():
            widths.append(spine.get_linewidth())
    return [width for width in widths if width], markers
    return [width for width in widths if width], markers


def audit(fig, name):
    scale = TEXT_WIDTH_IN / fig.get_size_inches()[0]
    sizes = sorted({round(text.get_fontsize() * scale, 2) for text in texts(fig)})
    widths, markers = strokes(fig)
    axes_area = sum(ax.get_position().width * ax.get_position().height for ax in fig.axes)
    report = {
        "name": name,
        "size": tuple(round(value, 2) for value in fig.get_size_inches()),
        "scale": round(scale, 3),
        "min_font": sizes[0],
        "small_fonts": [size for size in sizes if size < MIN_FONT_PT],
        "fonts": sizes,
        "min_stroke": round(min(widths), 2),
        "min_marker": round(min(markers), 2) if markers else None,
        "ink": round(axes_area, 3),
        "gray_ratio": round(contrast(plot_style.SELF, plot_style.JOINT), 2),
        "gray_ratio_secondary": round(contrast(plot_style.JOINT, plot_style.DISTILL), 2),
    }
    problems = []
    if report["min_font"] < MIN_FONT_PT:
        problems.append(f"font {report['min_font']} pt < {MIN_FONT_PT}")
    if report["min_stroke"] < MIN_STROKE_PT:
        problems.append(f"stroke {report['min_stroke']} pt < {MIN_STROKE_PT}")
    if report["min_marker"] is not None and report["min_marker"] < MIN_MARKER_PT:
        problems.append(f"marker {report['min_marker']} pt < {MIN_MARKER_PT}")
    if report["gray_ratio"] < MIN_GRAYSCALE_RATIO:
        problems.append("Self/Joint not separable in grayscale")
    if name == "fig6_slices" and report["gray_ratio_secondary"] < 3.0:
        problems.append("Affine/Distill not separable in grayscale")
    print(f"[{name}] size={report['size']} scale={report['scale']} "
          f"min_font={report['min_font']}pt stroke={report['min_stroke']}pt "
          f"marker={report['min_marker']} ink={report['ink']:.2f} "
          f"gray={report['gray_ratio']} gray2={report['gray_ratio_secondary']}")
    print(f"    font sizes drawn: {report['fonts']}")
    for problem in problems:
        print(f"    ISSUE {problem}")
    return problems


def main() -> int:
    captured = []
    original = plot_style.save_fig

    def wrapped(fig, path, stamp=False):
        captured.append((fig, Path(path).stem))
        original(fig, path, stamp=stamp)

    plot_style.save_fig = wrapped
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    problems = 0
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        module.save_fig = wrapped
        module.main()
    for fig, name in captured:
        fig.canvas.draw()
        problems += len(audit(fig, name))
    plt.close("all")
    print(f"\n{len(captured)} figures, {problems} issue(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
