# readkv_v2_arxiv — self-contained arXiv submission package

This directory is an **independent** arXiv-format working package. It does not
modify `papers/readkv_v2_draft/**`, any source code, data, preregistration
files, or run artifacts. All numbers are transcribed verbatim from frozen
artifacts; **no statistic was recomputed** for this package.

## Files

| File | Purpose |
|---|---|
| `main.tex` | Self-contained arXiv-ready LaTeX source (11pt, two-column article). |
| `references.bib` | 19 BibTeX entries (`.bib`), used via natbib `plainnat`. |
| `README.md` | This file: build, submission notes, draft differences. |
| `arxiv_conversion_notes.md` | Conversion assumptions, unverified items, draft-sync log. |

## Build

```bash
cd papers/readkv_v2_arxiv
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

A PDF should be produced as `main.pdf`. The same sequence works with
`latexmk -pdf main.tex` if available. No `make` file, custom class, or style
file is required.

## arXiv submission notes

- **Class / packages.** `\documentclass[11pt,twocolumn]{article}` with only
  standard, arXiv-safe packages: `inputenc`, `fontenc`, `amsmath`, `amssymb`,
  `graphicx`, `booktabs`, `natbib`, `hyperref` (`hidelinks`). No local `.cls`
  or `.sty` is loaded.
- **Self-contained source.** No `\input` of external files. Figures 1--3 are
  text-only `fbox`/`parbox` schematics embedded in `main.tex`; there are no
  external image files to upload. No mechanism heatmap, method-ablation, or
  generalization/cost figure is included: the corresponding results were
  withdrawn or never run and must not be fabricated.
- **Bibliography.** `references.bib` is in this package; `\bibliography{references}`
  plus `\bibliographystyle{plainnat}` (shipped with natbib) is used. All
  `\citep`/`\citet` keys resolve to the 19 entries.
- **Abstract length.** 191 whitespace tokens (LaTeX commands counted once each),
  i.e. **under the 200-word cap**, matching the draft writer's 191-word
  bookkeeping. All mandatory boundary phrases are retained: *approaches but does
  not exceed* controls, *single-signal dual-drop*, 8 *template_family* clusters
  *exploratory*, single synthetic MVP pair, sealed test *unevaluated*,
  contributions (1)/(2) *withdrawn* and (3) *withheld*, plus the budget-asymmetry
  disclosure (affine 0 params/0 epochs vs kd\_only 7.34M/8 epochs).
- **Statistics wording.** Every table reporting $E_{\mathrm{CF}}$ lists the
  primary `template_family` cluster-paired CI (`n_clusters=8`,
  `exploratory=true`) **and** the pair-level sensitivity CI side by side. No
  table reports a pair-level CI alone (reviewer R1 blocking item).
- **Status.** Venue = **TMLR** (decision 5); P5 has a **conditional final
  sign-off**, so the paper is **ready-to-submit**. The real PI submits personally
  via OpenReview; no agent submits on the author's behalf. (The earlier
  "submission deferred / citation verification pending" wording is superseded
  by `docs/decisions/p5_final_signoff.md`.)

## Differences from `papers/readkv_v2_draft/main.tex`

1. **Class/layout:** draft uses `[11pt,a4paper]{article}` with `geometry` and
   single-column layout; this package uses standard two-column `article` with
   no `geometry`, for arXiv compatibility.
2. **Packages:** draft uses `hyperref` with custom `colorlinks` setup; this
   package uses `natbib` + `hyperref[hidelinks]` and drops `geometry` and the
   custom `hypersetup`.
3. **Bibliography:** draft embeds a `thebibliography` block with numbered
   `\bibitem`s; this package uses natbib `plainnat` with the external
   `references.bib`. Added the two SQuAD references (Rajpurkar et al., EMNLP
   2016, doi:10.18653/v1/D16-1264; Rajpurkar, Jia et al., ACL 2018,
   doi:10.18653/v1/P18-2124). Added verified author names for arXiv preprints
   N1--N9a as supplied by the parent session; no venue was invented for any
   arXiv-only item.
4. **Sections:** added an explicit *Research Questions* section (RQ1--RQ4,
   descriptive/negative framing), split the draft's combined sections into
   *Data and Audit*, *Method and Evaluation Protocol*, *Discussion*, and
   *Limitations*, and added *Data Availability* and a
   *Status and Pre-registration / Contribution Record* section/table.
5. **Tables:** all tables use `booktabs` (some as full-width `table*`). Every
   $E_{\mathrm{CF}}$ table (clean affine, clean kd, and the reversal table)
   now prints the `template_family` primary CI and the pair-level sensitivity
   CI together, closing reviewer R1. Added the preregistration/contribution
   status table. No numbers were changed or recomputed.
6. **Abstract:** compressed from the draft's earlier ~270--290 words to 191
   tokens (matching the draft's current 191-word bookkeeping), keeping all
   mandated boundary wording and adding the budget-asymmetry disclosure.
7. **Removed:** the draft's author-internal note block, the
   "Draft --- generated from frozen results; submission deferred" date line,
   and all references to mechanism heatmaps / method ablation / generalization
   or cost figures. No positive-contribution or method-gain narrative is kept.
8. **Figures:** kept Figures 1--3 as text-only self-contained schematics (no
   external files), with "schematic; text-only" labels instead of the draft's
   "placeholder; figure file not yet generated" wording.
9. **Boundary wording retained verbatim in substance:** `real=0` (M4 blocked),
   SQuAD/ARC anchors evaluation-only, v2.6 AI-data proposal withdrawn (not
   activated, no artifacts), sealed test unevaluated, contributions (1)/(2)
   withdrawn and (3) withheld, P2/P3/P4 permanently cancelled, G1 not
   performed, primary endpoint unevaluated.
10. **Training-budget asymmetry (synced with draft fix).** No claim of matching
    on trainable parameter count, training steps, or tuning budget; matching is
    limited to pairs/dtype/kernel/forward budget. The affine mapper
    ($0$ params, $0$ epochs) vs kd\_only ($7{,}340{,}032$ params, $8$ epochs)
    asymmetry is disclosed in the Method and Limitations sections.
11. **Related-work conservatism (synced with draft fix).** Section-level
    descriptions of prior work (CacheLink four-arm diagnostic, Heo mapping,
    the causal-audit controls, ``Does Accuracy Equal Evidence?'') are downgraded
    to explicitly abstract-level statements; citation keys are preserved.
12. **Family/cluster bridging (synced with draft fix).** Added a sentence
    distinguishing the 56 corpus-wide template families from the 8 per-split
    `template_family` bootstrap clusters that set the exploratory flag.
