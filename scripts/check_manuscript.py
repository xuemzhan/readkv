"""Static consistency check for the four synced manuscripts.

Checks, without a LaTeX engine: defined references/citations, figure files,
tabular column counts and the presence of the new E3/E4/E7 diagnostics.

Usage:
    python -m scripts.check_manuscript
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = (
    "readkv_v2_tmlr_anonymous",
    "readkv_v2_draft",
    "readkv_v2_arxiv",
    "readkv_v2_zh",
)
NEW_MARKERS = ("TOST", "0.436", "61.7", "single-defect", "single defect")


def check(paper: str) -> list[str]:
    folder = ROOT / "papers" / paper
    tex = (folder / "main.tex").read_text(encoding="utf-8")
    problems: list[str] = []

    labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex))
    for ref in sorted(refs - labels):
        problems.append(f"undefined ref: {ref}")

    bib = folder / "references.bib"
    if bib.exists():
        keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib.read_text(encoding="utf-8")))
        cites = set()
        for group in re.findall(r"\\cite\w*\{([^}]+)\}", tex):
            cites.update(k.strip() for k in group.split(","))
        for key in sorted(cites - keys):
            problems.append(f"undefined citation: {key}")

    for figure in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex):
        target = folder / figure
        if not target.exists():
            problems.append(f"missing figure: {figure}")

    for block in re.findall(r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}", tex, re.S):
        spec, body = block
        ncols = len(re.findall(r"[lcr]|@\{[^}]*\}|p\{[^}]*\}", spec))
        structural = ("\\toprule", "\\midrule", "\\bottomrule", "\\cmidrule")
        merged: list[str] = []
        buffer = ""
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("%", *structural)) or re.match(r"^\\[A-Za-z]", stripped):
                continue
            buffer = (buffer + " " + stripped).strip() if buffer else stripped
            if not buffer.endswith("&"):
                merged.append(buffer)
                buffer = ""
        rows = merged
        for line in rows:
            cells = [c for c in line.split("&")]
            if len(cells) != ncols and "\\multicolumn" not in line and "\\cmidrule" not in line:
                problems.append(f"tabular has {len(cells)} cells but spec has {ncols}: {line.strip()[:70]}")
                break

    for marker in NEW_MARKERS:
        alternatives = (marker, "单缺陷干预", "单缺陷") if marker.startswith("single") else (marker,)
        if not any(alt in tex for alt in alternatives):
            problems.append(f"missing new-diagnostic marker: {marker}")
    return problems


def main() -> int:
    total = 0
    for paper in PAPERS:
        problems = check(paper)
        print(f"[{paper}] {len(problems)} issue(s)")
        for problem in problems:
            print("  -", problem)
        total += len(problems)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
