# readkv_v2_arxiv — self-contained arXiv submission package

This directory is an **independent** arXiv-format working package. It does not
modify `papers/readkv_v2_draft/**`, `papers/readkv_v2_tmlr_anonymous/**`, any
source code, data, preregistration files, or run artifacts. All numbers are
transcribed verbatim from frozen artifacts; **no statistic was recomputed** for
this package.

## Files

| File | Purpose |
|---|---|
| `main.tex` | Self-contained arXiv-ready LaTeX source (11pt, two-column article). |
| `references.bib` | 19 BibTeX entries, used via natbib `plainnat`. |
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
  `\citep`/`\citet` keys resolve to the 19 entries. Contrast Sets carries the
  full verified author list, venue, pages and doi; Heo uses the corrected
  initials; BridgeKV (n9b) carries the full author list from arXiv metadata.
- **Abstract length.** 186 whitespace tokens (LaTeX commands counted once each),
  i.e. **under the 200-word cap**. The draft's internal bookkeeping calls its
  abstract "191 rendered tokens"; the difference is a counting-convention
  artifact (the abstract text is transcribed verbatim from the current draft).
  See `arxiv_conversion_notes.md` §4 for the accounting note. Mandatory boundary
  phrases are retained: *approaches but does not exceed* controls,
  *single-signal dual-drop*, 8 *template_family* clusters *exploratory*, single
  synthetic MVP pair, sealed test *unevaluated*, contributions (1)/(2)
  *withdrawn* and (3) *withheld*, old mechanism evidence withdrawn / clean-data
  mechanism undecided, no method trained or improvement claimed.
- **Statistics wording.** Every table reporting $E_{\mathrm{CF}}$ lists the
  primary `template_family` cluster-paired CI (`n_clusters=8`,
  `exploratory=true`) **and** the pair-level sensitivity CI side by side. No
  table reports a pair-level CI alone (reviewer R1 blocking item). The 2$\times$2
  and sequence-scoring tables use sample-weighted `template_family` primary
  intervals with pair-level / family-equal sensitivities alongside.
- **Status.** Venue = **TMLR**. Earlier P5 sign-offs are **superseded** by the
  2026-11-24 second-round review; the manuscript is **ready-to-submit** pending
  a **new** sign-off from the real PI over the revised text. The real PI submits
  personally via OpenReview; no agent submits on the author's behalf.
- **Static compile check.** Bare underscores, bare `E_CF`, `\begin`--`\end`
  balance, table column counts, and citation-key resolution were checked by
  text search; one bare `E_CF` in a `\textbf{}` was found and fixed. No LaTeX
  compiler (`pdflatex`/`tectonic`) is available on this machine, so the package
  was **not** compiled to PDF; the build sequence above must be run in a
  compiler environment before submission.

## Differences from `papers/readkv_v2_draft/main.tex`

1. **Class/layout:** draft uses `[11pt,a4paper]{article}` with `geometry` and
   single-column layout; this package uses standard two-column `article` with
   no `geometry`, for arXiv compatibility.
2. **Packages:** draft uses `hyperref` with custom `colorlinks` setup; this
   package uses `natbib` + `hyperref[hidelinks]` and drops `geometry` and the
   custom `hypersetup`.
3. **Bibliography:** draft embeds a `thebibliography` block with numbered
   `\bibitem`s; this package uses natbib `plainnat` with the external
   `references.bib`. Metadata fixes synced from the draft: full Contrast Sets
   author list + venue/pages/doi (10.18653/v1/2020.findings-emnlp.117),
   corrected Heo initials + arXiv class/date, full BridgeKV (n9b) author list +
   [cs.CL]/date; SQuAD references carry the required ACL/EMNLP DOIs.
4. **Sections:** added an explicit *Research Questions* section, split the
   draft's combined sections into *Data and Audit*, *Method and Evaluation
   Protocol*, *Discussion*, and *Limitations*, and added *Data Availability* and
   a *Status and Pre-registration / Contribution Record* section/table.
5. **Tables:** all tables use `booktabs` (some as full-width `table*`). Every
   $E_{\mathrm{CF}}$ table (clean affine, clean kd, reversal) prints the
   `template_family` primary CI and pair-level sensitivity together, closing R1.
6. **Version-contrast framing (synced with 2026-11-24 revision).** Title and
   abstract are descriptive; no single-defect strong causal wording. Mechanism
   status: old mechanism evidence withdrawn, clean-data existence undecided
   (no clean P2). Added a controlled 2$\times$2 corpus-version contrast
   (`mixed_interaction`) and a preregistered sequence-scoring robustness section
   (branch 1 `consistent_across_scoring`), both exploratory.
7. **Metadata / measurement fixes (synced).** Three distinct denominators
   (398 corpus-level; 46 F1--F4 per cell; 34/45--34/46 after Self threshold);
   first-token binary proxy with F5/F6 behaviour; SQuAD single-reference subset
   plus official all-reference F1 (0.2178/0.0082/0.0014, review-side
   re-scoring); descriptive KD utility language (dual drop 11.7/16.7/1.7 pp,
   slice-sensitive); affine described as zero gradient-optimization epochs;
   budget asymmetry disclosed as a limitation.
8. **Status (synced).** ready-to-submit at TMLR pending a new PI sign-off;
   earlier sign-offs superseded; real PI submits in person.
