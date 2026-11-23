# Cover letter — TMLR submission (draft; final submission by the author via OpenReview)

**Venue:** Transactions on Machine Learning Research (TMLR)
**Manuscript:** *Data Defects Reverse a Reported Finding: A Failure-Boundary and Audit Study of Cross-Model KV Handoff*
**Author / corresponding author:** Zhang Xuein <zxm0813@gmail.com>
**Status of this draft:** ready-to-submit; the author (real PI) completes the OpenReview submission and signs off. Agent-generated draft, not a submission.

---

Dear TMLR editors,

We submit an empirical, negative-result study on cross-model key--value (KV)
cache handoff. The manuscript reports a preregistered data-audit reversal: an
apparent "utility-preserving counterfactual gap" and a receiver-side mechanism
reported in an earlier release of our own benchmark were traced to concrete
data defects (degenerate must-flip pairs, verbatim cross-split document
leakage, train/test template-skeleton overlap, and a bootstrap degenerate to
pair-level i.i.d.) and **disappeared and reversed after the corpus was rebuilt**.
On cleaned data, the tested affine mapper shows a transfer-failure boundary; a
matched `kd_only` baseline preserves utility yet retains a stable nonzero gap,
which we report only as an exploratory observation.

## Why this may interest a general TMLR readership

Although the case study is set in KV-cache transfer, the transferable message
is methodological and, we believe, of broad relevance: a statistically
convincing finding in a synthetic benchmark can be manufactured by a small set
of auditable data-construction defects, and a before/after, preregistered
controlled comparison can expose it. The paper's reusable contribution is the
**concrete audit trail and paired counterfactual `E_CF` measurement discipline**
(candidate-level paired documents, no-information / mismatched / zero-cache
controls, jointly reported `dual_correct` / `flip_consistency` / `coverage` /
`info_attribution` and an orthogonal `transfer_broken` annotation), not a new
model, mechanism, or benchmark paradigm. We deliberately avoid claiming a
general utility-versus-fidelity distinction or a general leakage lesson as our
own; those are established in prior work.

## Honest statement of contribution scope and limitations

This is a modest, boundary/empirical result. We state its limits plainly:

- **Contributions withdrawn / withheld.** The earlier evaluation-layer "gap"
  claim (contribution 1) and mechanism-localization claim (contribution 2) are
  **withdrawn**; the method-layer claim (contribution 3) is **withheld**. No
  method was trained, and the preregistered primary endpoint (paired
  `E_CF` difference vs `kd_only`, CI upper bound < 0) is **unevaluated**.
- **Single synthetic equal-depth pair.** All clean-data evidence comes from one
  equal-depth pair (Qwen3-1.7B -> 0.6B) on synthetic templates; no cross-pair,
  cross-model, real-world, or strong-significance claim is made.
- **Exploratory statistics.** Under the frozen v2.3 convention there are only
  8 `template_family` clusters (< 24), so all clean CIs are marked
  `exploratory`; we report the template-family-cluster CI as the main CI and
  present the pair-level CI as a side-by-side sensitivity analysis, never the
  narrower interval alone.
- **No real documents.** The real-document collection task was formally
  blocked (licence/network constraints and semantic unsuitability of the only
  licence-clean candidate); `real = 0`, and real-document external validity is
  **unverified**. No real-document verification is claimed.
- **Anchor is exploratory only.** The SQuAD v2.0 dev external anchor was
  classified under the preregistered v2.4 rule as
  `exploratory_disclosure`: the affine failure direction replicates, but the
  `kd_only` utility-preserving contrast does not, all arms hit an EM floor
  (base model not SQuAD-tuned), and only seed 0 / 240 examples were used. It is
  an exploratory anchor observation, **not** cross-source generalization,
  **not** real-document validation, and **not** a restoration of any contribution.
- **Sealed test never evaluated**; mock numbers are not evidence; `P > 0.05` is
  nowhere treated as equivalence.

## Reference-verification disclosure (item R2)

Related-work citations **N1--N9** are identified by title / arXiv ID / version /
date from public metadata, and their author names were completed from arXiv
API metadata; **full-text reading was not completed at submission**. Accordingly,
we cite these works only for existence and at the title/abstract level and make
**no section-level or detailed claim** about them. The KV-Lingo and CacheLink
entries were verified at the title/author/year/version/DOI level from their arXiv
records; SQuAD references were likewise metadata-checked. This limitation in
related-work coverage concerns corroborating context only; it does **not**
affect the paper's core contribution, which is the data-audit methodology and
the failure-boundary finding established from our own frozen artifacts.

## Originality

This is a single-author original work; it is not an extended version of a
conference paper. Novelty is confined to the concrete, preregistered before/after
reversal case and the paired counterfactual `E_CF` audit trail in this specific
benchmark. We do not claim priority for the general utility/fidelity
distinction, a mechanism-layer first, a new audit metric, or a general
reproducibility lesson.

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
