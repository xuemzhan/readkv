# Cover letter — TMLR submission (draft; final submission by the author via OpenReview)

**Venue:** Transactions on Machine Learning Research (TMLR)

**Manuscript:** *A Finding Reversed After Corpus Reconstruction: A Controlled Version-Contrast Study of Cross-Model KV Handoff*

**Author / corresponding author:** Zhang Xuein <zxm0813@gmail.com>

**Status of this draft:** ready-to-submit; the author (real PI) completes the OpenReview submission and signs off. Agent-generated draft, not a submission.

---

Dear TMLR editors,

We submit an empirical, negative-result study on cross-model key--value (KV)
cache handoff. An earlier release of our benchmark reported an apparent
"utility-preserving counterfactual gap" and a receiver-side mechanism. A data
audit of that corpus found degenerate must-flip pairs, verbatim cross-split
document leakage, train/test template-skeleton overlap, and a bootstrap
degenerate to pair-level i.i.d. In a controlled contrast between corpus
versions, the reported finding **did not survive reconstruction of the
corpus**; because the changes were applied together, the design identifies only
the whole-version switch, not any single defect. On the reconstructed data, the
tested affine mapper shows a transfer-failure boundary. The earlier mechanism
*evidence* is **withdrawn**, but we do **not** claim the mechanism was shown
absent or traced to a specific defect: whether it exists on clean data is
**undecided**, because no clean-data mechanism experiment was run. A `kd_only`
baseline on the same pairs/model configuration shows a smaller aggregate dual
accuracy drop that is sensitive to slice definition, reported only as an
exploratory observation --- not as established utility preservation.

## Why this may interest a general TMLR readership

The paper reports a descriptive, preregistered version contrast in one KV-cache
transfer benchmark: a finding reported on an earlier corpus release did not
survive reconstruction of that corpus, and the whole-version contrast cannot
attribute the change to any single defect. We present the concrete comparison
and its audit trail (candidate-level paired documents, no-information /
mismatched / zero-cache controls, jointly reported `dual_correct` /
`flip_consistency` / `coverage` / `info_attribution`, and a paired
counterfactual `E_CF` readout), together with a preregistered sequence-scoring
robustness check under which the point estimates keep the same direction. We
do **not** offer a general audit method, a new model, a mechanism, or a new
benchmark paradigm, and we do not claim a general utility-versus-fidelity
distinction or a general leakage lesson as our own; those are established in
prior work.

## Honest statement of contribution scope and limitations

This is a modest, boundary/empirical result. We state its limits plainly:

- **Contributions withdrawn / withheld.** The earlier evaluation-layer "gap"
  claim (contribution 1) is **withdrawn**; the mechanism claim (contribution 2)
  is **withdrawn** --- its old evidence no longer holds, while the question of
  a clean-data mechanism remains open (no clean P2). The method-layer claim
  (contribution 3) is **withheld**. No method was trained, and the preregistered
  primary endpoint (paired `E_CF` difference vs `kd_only`, CI upper bound < 0)
  is **unevaluated**.
- **Single synthetic equal-depth pair.** All clean-data evidence comes from one
  equal-depth pair (Qwen3-1.7B -> 0.6B) on synthetic templates; no cross-pair,
  cross-model, real-world, or strong-significance claim is made.
- **Exploratory statistics.** Under the frozen v2.3 convention there are only
  8 `template_family` clusters (< 24), so all clean CIs are marked
  `exploratory`; we report the template-family-cluster CI as the main CI and
  present the pair-level CI as a side-by-side sensitivity analysis, never the
  narrower interval alone.
- **Controlled version contrast, not single-defect attribution.** The
  preregistered 2x2 design crosses calibration-corpus version with
  validation-corpus version (12 cells, 3 seeds). Point estimates of the
  Self-minus-Joint gap rise in all nine reconstruction-containing cells, but
  the interaction direction is not stable and most contrast intervals cross
  zero; all inferences are exploratory. This identifies only the whole-version
  switch, not any single data defect.
- **No real documents.** The real-document collection task was formally
  blocked (licence/network constraints and semantic unsuitability of the only
  licence-clean candidate); `real = 0`, and real-document external validity is
  **unverified**. No real-document verification is claimed. An AI-generated-data
  proposal was evaluated and withdrawn (not activated); no such data or result
  exists.
- **Anchor is exploratory only.** The SQuAD v2.0 dev external anchor uses a
  single-reference subset: the first 240 answerable questions in file order
  from two Wikipedia articles, scored against the first reference answer. Under
  the preregistered v2.4 rule it is `exploratory_disclosure`: a descriptive F1
  decrease is observed on this subset, but the `kd_only` contrast is not
  reproduced and EM is at floor for all arms; the cause of the EM floor was not
  identified (no controlled intervention). It is **not** cross-source
  generalization, **not** real-document validation, and **not** a restoration
  of any contribution.
- **Sealed test never evaluated**; mock numbers are not evidence; `P > 0.05` is
  nowhere treated as equivalence.

## Reference-verification disclosure

Related-work citations **N1--N9** are identified by title / arXiv ID / version /
date from public metadata, and their author names were completed from arXiv
API metadata; **full-text reading was not completed at submission**. Accordingly,
we cite these works only for existence and at the title/abstract level and make
**no section-level or detailed claim** about them. The KV-Lingo and CacheLink
entries were verified at the title/author/year/version/DOI level from their arXiv
records; SQuAD references were likewise metadata-checked. This limitation in
related-work coverage concerns corroborating context only; it does **not**
affect the paper's core contribution, which is the concrete version-contrast
case and the failure-boundary finding established from our own frozen artifacts.

## Originality

This is a single-author original work; it is not an extended version of a
conference paper. Novelty is confined to the concrete, preregistered
before/after version-contrast case and the paired counterfactual `E_CF` audit
trail in this specific benchmark. We do not claim priority for the general
utility/fidelity distinction, a mechanism-layer first, a new audit metric, or a
general reproducibility lesson.

## Reproducibility

The study is well suited to TMLR's **Reproducibility Certification**: the
rebuilt dataset and hashes are fixed (SHA-256 `f910f1f1...a894a`), the run
provenance is recorded (clean-data commits `efc3ba3` / `6413ba0`, anchor commit
`b7b9f50`), and all experiments use fixed dtype/kernel (`bfloat16`/`sdpa`) and
strict zero re-prefill. Reports are reproducible with the frozen
`bootstrap_ci_report` and `consistency_check` scripts. We note that
Reproducibility Certification is decided by the editors/reviewers and is **not
guaranteed** by submission; figures 1--3 remain textual placeholders, to be
drawn from the frozen artifacts after acceptance if the editors wish.

Sincerely,

Zhang Xuein <zxm0813@gmail.com>
