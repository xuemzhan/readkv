# arXiv conversion notes — `papers/readkv_v2_arxiv`

Date: 2026-11-23. Scope: format conversion of the negative/empirical
boundary-and-audit study into a self-contained arXiv submission package.
**No code, data, preregistration file, run artifact, or `papers/readkv_v2_draft/**`
file was modified by this work.** No statistic was recomputed.

## 1. Conversion assumptions

1. **Class and layout.** Draft `\documentclass[11pt,a4paper]{article}` +
   `geometry` (single column) → `\documentclass[11pt,twocolumn]{article}`
   without `geometry`, allowing arXiv to control page margins.
2. **Packages.** Only standard arXiv-safe packages are used: `inputenc`,
   `fontenc`, `amsmath`, `amssymb`, `graphicx`, `booktabs`, `natbib`,
   `hyperref[hidelinks]`. No local `.cls`/`.sty`.
3. **Citations.** Draft `\cite{...}` commands were converted to natbib
   `\citep`/`\citet`; `\bibliographystyle{plain}` + embedded `thebibliography`
   → `\bibliographystyle{plainnat}` + `\bibliography{references}`.
4. **Figures.** Figures 1--3 remain text-only `fbox`/`parbox` schematics inside
   `main.tex`, so the source is self-contained (no external image files).
   The draft's "placeholder; figure file not yet generated" wording was
   changed to "schematic; text-only". No mechanism heatmap, method-ablation
   figure, or generalization/cost--Pareto figure was added: the corresponding
   results were withdrawn or never run and would have to be fabricated.
5. **Tables.** All tables use `booktabs`; wide tables use `table*`. Every table
   reporting $E_{\mathrm{CF}}$ (clean affine, clean kd, reversal) lists the
   primary `template_family` cluster-paired CI ($n_{\mathrm{clusters}}=8$,
   `exploratory=true`) and the pair-level sensitivity CI side by side; no
   table reports a pair-level CI alone. This closes reviewer R1.
6. **Sections.** Added explicit *Research Questions* (RQ1--RQ4, descriptive
   negative framing from the frozen scope update), split the draft's sections
   into *Data and Audit*, *Method and Evaluation Protocol*, *Discussion*, and
   *Limitations*, and added *Data Availability* plus a *Status and
   Pre-registration / Contribution Record* section with a status table.
7. **Status wording (updated this round).** The earlier "submission is
   deferred / citation verification pending" wording is **superseded** by
   `docs/decisions/p5_final_signoff.md`: venue = TMLR (decision 5), P5
   **conditionally signed off**, paper **ready-to-submit**, with the real PI
   submitting personally via OpenReview (no agent submits on the author's
   behalf). The status section/table now state this. Scientific claims,
   contribution status, and exploratory boundaries are unchanged.
8. **Training-budget asymmetry (synced with draft fix).** Matching is now
   stated only for pairs/dtype/kernel/forward budget; no claim of matching
   trainable parameter count, training steps, or tuning budget. Disclosed:
   affine $0$ params / $0$ epochs vs kd\_only $7{,}340{,}032$ params / $8$
   epochs, in both Method (`sec:baselines`) and Limitations. Numbers verified
   from frozen run configs: `p1_kd_clean_mvp_seed{0,1,2}/metrics.json`
   `"trainable_params": 7340032`, `"epochs": 8`; affine mapper
   `"mapper_trainable_params": 0` / `"epochs": 0`.
9. **Related-work conservatism (synced with draft fix).** Three section-level
   descriptions were downgraded to explicitly abstract-level statements:
   CacheLink's four-arm K/V source-swap diagnostic and Heo's closed-form ridge
   / per-pair degradation; the N7 causal-audit mismatched/zero/random controls
   and preregistered equivalence test; and ``Does Accuracy Equal Evidence?''
   answer-vs-evidence finding. All citation keys are preserved. A blanket note
   states the N1--N9 characterizations are abstract-level and section-level
   claims were not verified.
10. **Family/cluster bridging (synced with draft fix).** Added a sentence in
    `sec:datafix` distinguishing the $56$ corpus-wide template families
    (over $24$ structures) from the $8$ per-split `template_family` bootstrap
    clusters that set the v2.3 exploratory flag.

## 2. Numbers: transcribed sources and known cross-source discrepancies

All numbers were transcribed, never recomputed. Sources, in priority order:
`reports/bootstrap_summary.json`, `reports/anchor_eval_summary.json`,
`reports/data/data_fix_report.md`, and the latest draft.

- Clean affine (commit `efc3ba3`) — from `bootstrap_summary.json`:
  seed0 6.900, primary CI [3.564,10.100], pair-level [5.496,8.321];
  seed1 8.159, [4.357,11.584], [6.648,9.701];
  seed2 8.540, [5.326,11.610], [7.046,10.051]. These match the latest draft
  exactly.
- Clean kd (commit `6413ba0`) — from `bootstrap_summary.json`:
  seed0 6.388, primary [3.653,8.814], pair-level [5.340,7.400];
  seed1 6.479, [3.899,8.798], [5.431,7.529];
  seed2 7.210, [4.417,9.799], [6.074,8.331]. These match the latest draft.
- **Discrepancy (documented, not adjudicated):** `papers/readkv_v2_draft/notes.md`
  and `final_boundary_study_signoff.md` quote slightly different pair-level
  numbers from `metrics.json`: affine seed0 [5.499,8.313] vs. [5.496,8.321];
  kd seed0 [5.360,7.400] vs. [5.340,7.400], seed1 [5.419,7.539] vs.
  [5.431,7.529], seed2 point 7.211 vs. 7.210 with [6.078,8.322] vs.
  [6.074,8.331]. The arXiv package follows the explicit instruction to
  transcribe `reports/bootstrap_summary.json` and the latest draft; it does
  **not** recompute or silently reconcile either set. The differences do not
  affect any directional claim. The meta-review's earlier cluster-CI values
  (e.g. kd seed1 [3.883,8.773]) used `bootstrap_seed=0` for all rows and are
  likewise not used here.
- SQuAD anchor — from `anchor_eval_summary.json`: Self EM/F1 0.000/0.1975;
  Joint(affine) F1 0.0051 (2.6% of Self, drop 0.1924); Joint(kd) F1 0.0014
  (0.7%, drop 0.1961); all Joint EM 0.000; verdict `exploratory_disclosure`.
- Data-quality table and SHA-256 strings transcribed from the draft's
  `tab:datafix`, which cites the frozen data-fix report and acceptance checks.

## 3. Citations: verified vs. unverified

- **Author strings.** N1--N5 author names came from the latest draft's
  bibliography (parent-session arXiv API verification). N6--N9a author names
  were filled in by the other writer **during** this task (see §4) and were
  adopted here verbatim: S. Sarkar, S. Mitra, S. Huang, S. Kundu, P. A. Beerel
  (arXiv:2610.11358); J. Cheng, S. Das, R. Ramnath (arXiv:2608.04893);
  R. Khare (arXiv:2610.16165); P. Kvedaras, T. Rasymas (arXiv:2611.12062).
- **arXiv-only entries.** N1--N9 are recorded only as arXiv preprints + year
  (no venue invented), per instruction. Only titles, arXiv IDs, and years are
  used in the text; no unverified section-level claims are made about them.
- **n9b BridgeKV (arXiv:2611.11761).** Author list not independently verified;
  the bib entry carries a `note` to that effect and no author field.
- **KV-Lingo / CacheLink / Heo.** Kept as arXiv preprints with their verified
  arXiv IDs/DOIs. The frozen sources available here did not contain a verified
  conference venue for these three, so none was supplied. (The task brief
  mentions "verified conference papers" including these names; if the parent
  session has verified venues, they should be added before submission rather
  than guessed.)
- **SQuAD.** Keys `squad16`/`squad18` were adopted to match the draft's final
  citation keys; entries use full first names plus the required DOIs
  (10.18653/v1/D16-1264 and 10.18653/v1/P18-2124), whereas the draft uses
  initials. Bibliographically equivalent.
- **Section-level detail (still unverified).** The CacheLink four-arm
  diagnostic, Heo per-pair degradation, N7 causal-audit controls/TOST, and
  ``Does Accuracy Equal Evidence?'' finding are now stated only at abstract
  level in the text (this round), but no full-text/§-level verification was
  performed in this session per protocol §9. They remain a residual risk for
  the real PI to clear before submission. **n9b BridgeKV author list remains
  unverified** (no author field; bib `note` records this).

## 4. Draft synchronization log (start vs. end)

The draft was read once at task start and once at task end, as instructed.

| Snapshot | `papers/readkv_v2_draft/main.tex` |
|---|---|
| **Start** | 825 lines. Title: "Data Defects Reverse a Reported Finding: A Failure-Boundary and Audit Study of Cross-Model KV Handoff"; author Zhang Xuein <zxm0813@gmail.com>. Abstract still ~270--290 words (per `notes.md` §6), not yet compressed. Dual-CI tables (`tab:cleanmvp`, `tab:cleankd`) already present. No SQuAD citations in text; bibliography is `thebibliography` with N6--N9b lacking author names and no SQuAD bibitems. |
| **End** | 839 lines (+14). Title/author/abstract unchanged (abstract still not compressed). Dual-CI tables unchanged. **New:** `\cite{squad16,squad18}` added in the SQuAD anchor paragraph; a comment states "N1--N9 author lists below were verified by the main session via the arXiv API"; full author names added for n6--n9a; n9b gained an "author list not independently verified" note; new bibitems `squad16` and `squad18` with the required DOIs. |

`papers/readkv_v2_draft/notes.md` was unchanged (156 lines) across the two reads.

**Sync actions taken in this package:** adopted the newly added SQuAD citation
keys `squad16`/`squad18`; adopted the newly verified author lists for n6--n9a;
retained the n9b "not independently verified" caveat. The arXiv abstract is
independently compressed to **191 whitespace tokens** (LaTeX commands counted
once each), matching the draft writer's 191-word bookkeeping; it preserves all
mandatory boundary wording and adds the budget-asymmetry disclosure. The exact
rendered word count can differ by counter (e.g. whether `key--value`, math
expressions, or `\texttt{...}` tokens are split); both this package and the
draft report 191 by the same whitespace-token convention, and both are under
the 200-word cap.

### 4.1 Second sync round (training budget / status / related work / bridging)

The parent session reported that the other writer was applying three fixes to
the draft (training-budget mismatch, ready-to-submit status, related-work
conservatism) plus a family/cluster bridging sentence and 191-word abstract
bookkeeping. This package applied the equivalent changes (see §1 items 7--10):
budget asymmetry disclosed with verified numbers; status updated per
`p5_final_signoff.md` (TMLR, P5 conditional, ready-to-submit, real PI submits);
three related-work passages downgraded to abstract-level; 56-vs-8 bridging
added; abstract set to 191 tokens. The draft is re-read once more at the very
end of this round; the result is recorded in §4.2.

### 4.2 End-of-round draft re-read (as instructed)

Re-read at the end of this round: `papers/readkv_v2_draft/main.tex` is **still
839 lines** and does **not yet** contain the three fixes — it still says
"submission is deferred" (header note, `\date`, intro, conclusion), still lists
"trainable parameter count, training steps, and tuning budget" as matched
(`sec:baselines`), still has the "four-arm K/V source-swap diagnostic" and
section-level related-work statements, has no 56-vs-8 bridging sentence, and
its abstract is still the ~270-word pre-compression version. In other words,
the other writer's fixes were **still in progress** at this snapshot.

**Consequence:** this arXiv package is deliberately **ahead of the draft** on
these five items, having applied the parent-supplied fix specification and the
frozen `p5_final_signoff.md` / `human_decisions.md` decision 5. All five changes
are traceable to frozen/authoritative sources (TMLR + P5 signoff docs; verified
run config numbers for 7.34M/8 epochs; protocol §9 abstract-level verification
status; data-fix report counts 56 families / 24 structures / 8 per-split
clusters). No fix was invented. If the writer's landed wording differs in
detail from this package's, the real PI should do one final consistency check
before submission; the scientific content and boundary wording are identical.
The R1 dual-CI tables were untouched by this round and remain closed.

## 5. Deliberate omissions and non-claims

- No mechanism heatmap, method-ablation, or generalization/cost figure.
- No method gain, no restored contribution, no cross-model/real-world/strong-
  significance claim; `P>0.05` not treated as equivalence; mock numbers not
  used as evidence.
- `real=0` (M4 blocked), SQuAD/ARC anchors evaluation-only (ARC not run),
  v2.6 AI-data proposal withdrawn and not activated (no artifacts), sealed test
  unevaluated, contributions (1)(2) withdrawn and (3) withheld, P2/P3/P4
  permanently cancelled, G1 not performed, primary endpoint unevaluated.
- No LaTeX compilation was performed in this session (to avoid writing build
  artifacts); `README.md` gives the `pdflatex → bibtex → pdflatex ×2` sequence.
  Cite keys and bibliography entries were cross-checked by text search: 19
  bibliography entries, all cited keys resolve.
