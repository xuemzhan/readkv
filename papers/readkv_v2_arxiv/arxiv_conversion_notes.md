# arXiv conversion notes — `papers/readkv_v2_arxiv`

Date: 2026-11-24 (third sync round). Scope: format conversion of the
negative/empirical version-contrast and data-audit study into a self-contained
arXiv submission package. **No code, data, preregistration file, run artifact,
`papers/readkv_v2_draft/**`, or `papers/readkv_v2_tmlr_anonymous/**` file was
modified by this work.** No statistic was recomputed.

## 1. Conversion assumptions

1. **Class and layout.** Draft `\documentclass[11pt,a4paper]{article}` +
   `geometry` (single column) → `\documentclass[11pt,twocolumn]{article}`
   without `geometry`, allowing arXiv to control page margins.
2. **Packages.** Only standard arXiv-safe packages: `inputenc`, `fontenc`,
   `amsmath`, `amssymb`, `graphicx`, `booktabs`, `natbib`, `hyperref[hidelinks]`.
   No local `.cls`/`.sty`.
3. **Citations.** Draft `\cite{...}` → natbib `\citep`/`\citet`;
   `\bibliographystyle{plain}` + embedded `thebibliography` →
   `\bibliographystyle{plainnat}` + `\bibliography{references}`.
4. **Figures.** Figures 1--3 remain text-only `fbox`/`parbox` schematics inside
   `main.tex` (no external image files). No mechanism heatmap, method-ablation,
   or generalization/cost figure is added: those results were withdrawn or never
   run and would have to be fabricated.
5. **Tables.** All tables use `booktabs`; wide tables use `table*`. Every table
   reporting $E_{\mathrm{CF}}$ (clean affine, clean kd, reversal) lists the
   `template_family` primary CI ($n_{\mathrm{clusters}}=8$, `exploratory=true`)
   and the pair-level sensitivity CI side by side; no table reports a pair-level
   CI alone (R1). The 2$\times$2 and sequence-scoring tables carry sample-weighted
   `template_family` primary intervals with pair-level / family-equal
   sensitivities alongside.
6. **Sections.** Added explicit *Research Questions* (RQ1--RQ4, descriptive
   negative framing), split the draft's sections into *Data and Audit*, *Method
   and Evaluation Protocol*, *Discussion*, and *Limitations*, and added *Data
   Availability* and a *Status and Pre-registration / Contribution Record*
   section/table.

## 2. Numbers: transcribed sources

All numbers were transcribed, never recomputed. Sources:
`reports/bootstrap_summary.json`, `reports/anchor_eval_summary.json`,
`reports/audit_2x2_l_ci.json`, `reports/audit_2x2_formal_summary.json`,
`docs/audit_seq_statistical_interpretation.md` (with the six authoritative
`reports/runs/audit_seq_*_b0` cells), `reports/data/data_fix_report.md`, and the
latest draft.

- Clean affine (commit `efc3ba3`), from `bootstrap_summary.json`: seed0 6.900
  primary [3.564,10.100] / pair [5.496,8.321]; seed1 8.159 [4.357,11.584] /
  [6.648,9.701]; seed2 8.540 [5.326,11.610] / [7.046,10.051].
- Clean kd (commit `6413ba0`): seed0 6.388 primary [3.653,8.814] / pair
  [5.340,7.400]; seed1 6.479 [3.899,8.798] / [5.431,7.529]; seed2 7.210
  [4.417,9.799] / [6.074,8.331]. Two CI sets match the frozen file and draft.
- Historical cross-source discrepancy (not adjudicated): `notes.md` /
  `final_boundary_study_signoff.md` quote slightly different pair-level values
  from `metrics.json` (e.g. kd seed2 7.211 [6.078,8.322] vs 7.210 [6.074,8.331]).
  This package follows the instruction to transcribe `bootstrap_summary.json`
  and the latest draft; it recomputes nothing. The differences do not affect any
  directional claim.
- 2$\times$2 contrast: cell $L$ values and primary CIs transcribed from
  `audit_2x2_l_ci.json` (e.g. A00 s0 +1.7 [-3.333,7.018], A11 s0 +40.0
  [16.667,62.712]); sample-weighted / family-equal contrast CIs, the 12
  predeclared contrasts, interaction intervals and sensitivity slices transcribed
  from `audit_2x2_formal_summary.json` / second-round review as reported in the
  draft. Counts: A01$-$A00 crosses zero 1/3 seeds, A11$-$A10 2/3 (3/6
  cross-version intervals); interaction $-23.3[-47.6,3.4]$ / $+5.0[-22.9,31.0]$ /
  $-15.0[-44.0,16.1]$, all covering zero.
- `_b0` sequence-scoring (authoritative set = six `audit_seq_*_b0` cells; older
  ids superseded): from `docs/audit_seq_statistical_interpretation.md` and
  `reports/review/sequence_scoring_summary_b0.md`. Primary analysis F1--F4, 6
  families (A11 46/46/46, A00 42/42/41); A11 full $L$ +0.4783/+0.4348/+0.5217;
  cell_diff first +0.4348/+0.7474/+0.3860, full +0.4783/+0.5062/+0.4730,
  norm +0.5000/+0.5714/+0.5817; reading_diff(A11)
  +0.0435[-0.2553,0.3182]/-0.2174[-0.3404,-0.1304]/+0.0870[-0.1087,0.3043];
  reading_of_diff +0.0435[-0.2612,0.3211]/-0.2412[-0.3978,-0.1054]/+0.0870
  [-0.1064,0.3043]. All-60-pair 8-family sensitivity A11 reading_diff s1
  -0.2167[-0.3333,-0.1167]. Denominator-convention difference (Primary
  F1--F4 6 families vs all-60 8 families, e.g. A11 s0 first $L$ +0.4348 vs
  +0.3833) is recorded honestly; the two sets are never mixed. Verdict: branch 1
  `consistent_across_scoring`, preregistered, no post-hoc branch selection.
- SQuAD anchor, from `anchor_eval_summary.json`: single-reference subset (first
  240 answerable, two articles, first reference answer); Self EM/F1 0.000/0.1975,
  Joint(affine) F1 0.0051 (2.6% of Self, drop 0.1924), Joint(kd) 0.0014 (0.7%,
  drop 0.1961); all Joint EM 0.000; verdict `exploratory_disclosure`. Official
  all-reference re-scoring of the saved predictions (Self / affine Joint / KD
  Joint F1 $\approx$ 0.2178 / 0.0082 / 0.0014, EM still zero) is cited as a
  review-side recomputation, not a new run.
- 398 = corpus-level must-flip count; per-cell 46 F1--F4 pairs; after F1--F4 +
  Self-threshold filters A11 34/45, 35/46, 34/46 for seeds 0/1/2. First-token
  binary proxy: F5 identical candidates (proxy error 0, dual 1), F6 changes name
  and gold label; both excluded from must-flip denominators.

## 3. Citations: verified vs. unverified

- **Metadata fixes (this round, synced from draft).** Contrast Sets now carries
  the full verified author list (Gardner, Artzi, Basmov, ... Zhou), venue
  *Findings of ACL: EMNLP 2020*, pages 1307--1323, doi
  10.18653/v1/2020.findings-emnlp.117. Heo uses corrected initials
  (T. Heo, R. Shafipour, R. Zhao, M. Golub, M. M. Kamani, R. Borkar, M. T.
  Chandran, P. Zardoshti, B. D. Rouhani) with [cs.LG] and 4 Aug 2026. BridgeKV
  (n9b, arXiv:2611.11761) now carries the full author list (Behnam, Sanyal, ...
  Tumanov) with [cs.CL], 9 Nov 2026, instead of the earlier "author not verified"
  placeholder. N1--N9 author names are from arXiv API metadata (parent-session
  verification); only title/abstract-level claims are made about them in text.
- **arXiv-only entries.** N1--N9 are recorded only as arXiv preprints + year
  (with arXiv class / date where the draft records them); no conference venue is
  invented.
- **Still unverified.** No protocol §9 full-text verification was performed in
  this session. Section-level details of CacheLink, Heo, N7 causal-audit, and
  ``Does Accuracy Equal Evidence?'' are stated only at abstract level in the
  text. The cover letter discloses this limitation (N1--N9 identified by
  title/arXiv/version/date from public metadata; full text not read at
  submission). This is a residual item for the real PI to clear; it does not
  affect the core version-contrast / failure-boundary result.

## 4. Draft/anonymous synchronization and abstract accounting

Sources read this round: `papers/readkv_v2_draft/main.tex` (1193 lines),
`papers/readkv_v2_draft/notes.md` (243 lines),
`papers/readkv_v2_draft/cover_letter.md`, and
`papers/readkv_v2_tmlr_anonymous/main.tex` (755 lines). All five sync items
from the parent-session brief were applied: (1) descriptive title/abstract and
version-contrast framing with mechanism evidence withdrawn / clean-data
existence undecided; (2) 2$\times$2 table note (A00/A10 legacy val, A01/A11
reconstructed val), sample-weighted main + family-equal sensitivity, 12
predeclared contrasts, cross-zero counts, interaction covering zero; (3) SQuAD
single-reference subset + official all-reference F1, descriptive KD language,
affine zero gradient-optimization epochs, first-token proxy, denominator
bracket; (4) `_b0` sequence-scoring section and tables with branch 1; (5)
metadata fixes and status (TMLR, ready-to-submit pending **new** PI sign-off;
earlier sign-offs superseded; real PI submits in person).

**Abstract accounting.** The abstract is transcribed verbatim from the current
draft. By this package's whitespace-token count it is **186 tokens**; the draft's
`notes.md` §0.4 bookkeeping calls its abstract "191 rendered tokens". The
difference is a counting-convention artifact (how `key--value`, math expressions,
and `\texttt{...}` are split); both counts are under the 200-word cap. The
previous arXiv abstract (a different, independently compressed text) was 191
whitespace tokens; that number no longer applies after the verbatim resync.

**Status nuance.** The 2026-11-24 second-round review supersedes the earlier
`p5_final_signoff.md` and `p5_final_resignoff.md`; `docs/decisions/sequence_scoring_baseline_ruling.md`
requires a **new** PI sign-off after R1--R4 and the targeted revisions close.
Accordingly the arXiv status text says ready-to-submit pending a new PI sign-off
rather than claiming an active sign-off.

**Historical sync log (earlier rounds, retained).** Earlier rounds synced the
SQuAD bibitems and N6--N9a author lists (round 1), then the training-budget
asymmetry, ready-to-submit status, related-work conservatism, and 56-vs-8 family
bridging (round 2). Those changes are all carried forward into the present file.
At the time of round 2 the draft was still the 839-line version with fixes in
progress; this round the draft has landed the full 1193-line revision, and the
arXiv package now tracks it.

## 5. Static compile check (performed this round)

Text-search checks completed:
- **Bare underscores:** grep for `[a-zA-Z]_[a-zA-Z]` — all hits are math-mode
  subscripts (`$d_A$`, `$C_T$`, `$K_S$`), escaped `\_` inside `\texttt{}`,
  comments, or bib keys; the only bare `E_CF` in text (a `\textbf{E_CF ...}`
  in Limitations) was found and fixed to `\textbf{$E_{\mathrm{CF}}$ ...}`.
- **Bare `E_CF`:** one hit, fixed; all other uses are `$E_{\mathrm{CF}}$`.
- **`\begin`/`\end` balance:** 34 of each; `document`, `abstract`, three
  `figure`, two `enumerate`, one `description`, one `align`, one `center`,
  and the `table`/`table*`/`tabular` sets all pair.
- **Table column counts:** each row matches its `\begin{tabular}{...}` spec
  (e.g. `tab:cleanmvp` 9 columns, `tab:cleankd` 8, `tab:seqcell` 3,
  `tab:seqdiff` 4, `tab:audit2x2` 4, status table 3).
- **Citation keys:** all `\citep`/`\citet` keys resolve to the 19 bib entries.

**Limitation.** No LaTeX compiler (`pdflatex`/`tectonic`) is available on this
machine, so the package was **not** compiled to PDF; the above are static checks
only. The build sequence in `README.md` must be run in a compiler environment.
A prior review noted a $\sim$103 pt horizontal overflow in the draft's wide
tables; the arXiv version uses full-width `table*` for the widest tables, but
this should be re-checked when a compiler is available.

## 6. Deliberate omissions and non-claims

- No mechanism heatmap, method-ablation, or generalization/cost figure.
- No method gain, no restored contribution, no cross-model/real-world/strong-
  significance claim, no single-defect causal attribution; `P>0.05` not treated
  as equivalence; mock numbers not used as evidence.
- `real=0` (M4 blocked), SQuAD/ARC anchors evaluation-only (ARC not run), v2.6
  AI-data proposal withdrawn and not activated (no artifacts), sealed test
  unevaluated, contributions (1)(2) withdrawn and (3) withheld, P2/P3/P4
  permanently cancelled, G1 not performed, primary endpoint unevaluated.
- Sequence-scoring branch 1 reported only as point-estimate direction
  consistency under two scorings; no strong-significance, method-gain, or
  contribution-restoration claim; $E_{\mathrm{CF}}$ not compared across readings.
