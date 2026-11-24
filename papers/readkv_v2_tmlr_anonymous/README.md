# Anonymous TMLR submission source

This directory holds the **double-blind / anonymous** TMLR manuscript source.

- `main.tex` — self-contained LaTeX source (author = "Anonymous Author(s)";
  no acknowledgments; no author email; no self-identifying citation). Numeric
  tables are readable from the PDF itself; the 2×2 statistics live in an
  appendix (`\label{sec:stats}`).
- No result is fabricated. Every number is transcribed from frozen artifacts in
  `reports/` (`metrics.json`, `bootstrap_summary.json`,
  `anchor_eval_summary.json`, `audit_2x2_l_ci.json`,
  `audit_2x2_formal_summary.json`, six `runs/audit_seq_*_b0/` cells, and the
  frozen statistical interpretations) and the frozen data-fix reports. Old
  sequence-scoring run ids are superseded and are not used. No statistic
  was recomputed for this manuscript. Paths are repository-relative; no absolute
  paths are embedded.

## Compile

The source intentionally uses only standard packages (`inputenc`, `fontenc`,
`amsmath`, `booktabs`, `graphicx`, `geometry`, `hyperref`) so it compiles with a
standard LaTeX installation without an external `.sty`:

```
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Tectonic also works:

```
tectonic main.tex
```

If the local toolchain has `pdflatex`/`bibtex` but not a complete package set,
the reviewer environment used Tectonic; consult `papers/readkv_v2_draft/notes.md`
for the compile note and the earlier overflow/escape findings.

## For the camera-ready

TMLR's official style and anonymity rules may require swapping the preamble to
`\usepackage{tmlr}`, restoring the author line and adding an acknowledgments
section. Do **not** add author identity or acknowledgments to the anonymous
version. The venue and submission are handled by the real PI via OpenReview;
this directory is a source draft, not a submission.

## Relationship to other versions

- `papers/readkv_v2_draft/` — named long draft with internal ruling notes and
  cover letter (`cover_letter.md`). The scientific content here matches the
  revised draft after the 2026-11-24 directed revision.
- `papers/readkv_v2_arxiv/` — arXiv version, synchronized separately by another
  agent (do not edit from this directory).

## Anonymity checklist

- [x] `\author{Anonymous Author(s)}`, empty `\date`
- [x] no `acknowledgments` section
- [x] no author email / affiliation / self-citation by name
- [x] earlier release described as "an earlier release of this benchmark"
- [x] no absolute paths; no fabricated results; sequence-scoring results filled from the six authoritative `_b0` cells (old ids superseded)
