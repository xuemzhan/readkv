# Cover letter for Transactions on Machine Learning Research

**Manuscript** — *A Benchmark Rebuild Reverses a Cross-Model KV Transfer Finding: Controlled Version Contrasts, Control Tests, and Metric Diagnostics*

Dear TMLR Editors,

I am submitting an empirical audit of cross-model key–value cache handoff. An earlier comparison on a synthetic paired-document benchmark suggested that affine transfer preserved answer correctness while changing counterfactual scores. The paper documents the audit, the withdrawal of that result, and what the rebuilt benchmark now shows.

A calibration-by-validation comparison across twelve cell–seed combinations shows that replacing either corpus moves the native-minus-transferred dual-correctness gap from near zero to 23–62 percentage points. We add two diagnostics that the version contrast alone could not supply. First, against mismatched, zero and randomized caches, the transferred counterfactual error is no larger than the mismatched and zero-cache controls, close to the randomized control and significantly smaller than zero-cache in one seed, while dual correctness collapses to 28–42%; a pre-declared equivalence margin succeeds in only one of three seeds, so we do not overstate the result. Second, counterfactual error has weak discriminative validity: its rank correlation with dual correctness reverses sign between the affine mapper and a distillation baseline, and its intervals overlap although their correctness differs by 28–45 points. A follow-up with full candidate-sequence scores retains the direction of the version contrast in all seeds but reduces its magnitude by 21.7 points in one seed. An anonymous supplement provides numeric ledgers and a CPU replay that reconstruct the tables and control tests without model weights or accelerators.

The study is scoped to one equal-depth model pair, two versions of one synthetic benchmark, and at most eight template families; the sealed test remains unevaluated. We distinguish evidence for whole-version sensitivity from the single-defect interventions that would attribute the effect to a particular flaw, which are left as future work. The central lesson is relevant to readers who build contrast sets, audit benchmark leakage, or interpret counterfactual scores from model interventions.

Sincerely,

Zhang Xuein
