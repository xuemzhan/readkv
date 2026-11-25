"""Render every figure and audit the drawn canvas for what a reader would see.

Four mechanical checks per figure:

  * no two visible text labels overlap by more than a quarter of the smaller box,
  * no legend covers a data mark (a point, a line vertex or a bar top),
  * no arrow runs through the interior of a container box,
  * a switched-off axis contributes no tick labels to the audit.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import plot_style

MODULES = ("gen_fig1_design", "gen_fig2_corpus", "gen_fig3_factorial",
           "gen_fig4_scoring", "gen_fig5_controls", "gen_fig6_slices")

OVERLAP_FRACTION = 0.25
INSIDE_FRACTION = 0.02


def _visible_ticks(ax):
    """Tick labels a reader actually sees: visible and inside the view interval."""
    ticks = []
    left, right_edge = ax.get_xlim()
    ticks += [text for text in ax.get_xticklabels()
              if text.get_visible() and left <= text.get_position()[0] <= right_edge]
    bottom, top = ax.get_ylim()
    ticks += [text for text in ax.get_yticklabels()
              if text.get_visible() and bottom <= text.get_position()[1] <= top]
    return ticks


def _texts(fig):
    artists = list(fig.texts)
    for ax in fig.axes:
        artists += list(ax.texts)
        if ax.axison:
            artists += _visible_ticks(ax)
        if ax.get_title():
            artists.append(ax.title)
        artists.append(ax.xaxis.label)
        artists.append(ax.yaxis.label)
        legend = ax.get_legend()
        if legend is not None:
            artists += list(legend.get_texts())
    return [artist for artist in artists if artist.get_text().strip() and artist.get_visible()]


def _marks(fig):
    """Data marks in display coordinates: points, line vertices, bar tops."""
    points = []
    for ax in fig.axes:
        if ax.images:  # a heatmap cell is meant to hold its own number
            continue
        for line in ax.get_lines():
            data = np.asarray(line.get_xydata(), dtype=float)
            if data.ndim == 2 and data.size:
                points += list(ax.transData.transform(data))
        for collection in ax.collections:
            offsets = np.asarray(collection.get_offsets(), dtype=float)
            if offsets.ndim == 2 and offsets.size:
                points += list(ax.transData.transform(offsets[:400]))
        for patch in ax.patches:  # a bar top is data, not decoration
            if not hasattr(patch, "get_height") or not patch.get_height():
                continue
            if not hasattr(patch, "get_xy"):
                continue
            x0, y0 = patch.get_xy()
            points.append(ax.transData.transform((x0 + patch.get_width() / 2, y0 + patch.get_height())))
    return points


def _arrows_in_boxes(fig):
    """An arrow must not run through the interior of a container box."""
    problems = []
    for ax in fig.axes:
        boxes = [patch for patch in ax.patches if isinstance(patch, FancyBboxPatch)]
        if not boxes:
            continue
        box_paths = [patch.get_path().transformed(patch.get_transform()) for patch in boxes]
        for patch in ax.patches:
            if not isinstance(patch, FancyArrowPatch):
                continue
            path = patch.get_path().transformed(patch.get_transform())
            samples = path.interpolated(80).vertices
            for box_path in box_paths:
                inside = sum(1 for point in samples if box_path.contains_point(point))
                if inside > INSIDE_FRACTION * len(samples):
                    problems.append("an arrow runs through a container box "
                                    f"({inside / len(samples):.0%} of its path)")
                    break
    return problems


def check(fig, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    problems = []

    boxes = []
    for artist in _texts(fig):
        box = artist.get_window_extent(renderer=renderer)
        if box.width and box.height:
            boxes.append((artist.get_text().replace("\n", " / ")[:34], box))
    for index, (label_a, box_a) in enumerate(boxes):
        for label_b, box_b in boxes[index + 1:]:
            width = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            height = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if width <= 0 or height <= 0:
                continue
            smaller = min(box_a.width * box_a.height, box_b.width * box_b.height)
            if smaller and (width * height) / smaller > OVERLAP_FRACTION:
                problems.append(f"overlap {(width * height) / smaller:.0%}: "
                                f"{label_a!r} vs {label_b!r}")

    points = _marks(fig)
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend is None or not legend.get_visible():
            continue
        box = legend.get_window_extent(renderer=renderer)
        inside = sum(1 for x, y in points if box.x0 <= x <= box.x1 and box.y0 <= y <= box.y1)
        if inside:
            problems.append(f"legend covers {inside} data mark(s)")

    problems += _arrows_in_boxes(fig)

    print(f"[{name}] {'ok' if not problems else str(len(problems)) + ' issue(s)'}")
    for problem in problems:
        print(f"    {problem}")
    return problems


def main() -> int:
    recorded = {}
    original = plot_style.save_fig

    def wrapped(fig, path, stamp=False):
        recorded[Path(path).stem] = check(fig, Path(path).stem)
        original(fig, path, stamp=stamp)

    plot_style.save_fig = wrapped
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        module.save_fig = wrapped
        module.main()
    plt.close("all")
    total = sum(len(value) for value in recorded.values())
    print(f"\n{len(recorded)} figures rendered, {total} layout issue(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
