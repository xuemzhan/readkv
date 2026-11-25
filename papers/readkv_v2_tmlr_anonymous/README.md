# Anonymous TMLR submission

**Manuscript source** is `main.tex`. The checked-in `main.pdf` and `supplement.zip` predate the E3/E4/E7 revision and must be regenerated on a machine with a LaTeX engine before submission. **Anonymous supplementary material** is `supplement.zip`. The authoritative source is this directory; the separate named drafts and arXiv directory are kept in sync with its scientific claims.

## Rebuild the tables and manuscript

With Python 3.10 or newer and NumPy installed, run the CPU replay in this directory:

    python reproduce.py

This reads the anonymous numeric ledger `evaluation.json`, writes `results.json` and updates `results.tex`. From a full repository checkout, `python papers/readkv_v2_tmlr_anonymous/reproduce.py --repo .` re-extracts that ledger from the archived runs and official local SQuAD file.

The E3/E4/E7 diagnostics added in this revision are generated from the verified ledger by two CPU-only scripts run at the repository root:

    python -m scripts.audit_reanalysis     # writes reports/audit_reanalysis.json
    python -m scripts.reanalysis_tables    # writes results_extra.tex here and in readkv_v2_zh

The equivalence margin is declared in `configs/prereg/equivalence_margin_v2.9.yaml` before the reported numbers. No GPU run is involved; single-defect interventions, the sealed test and a second model pair remain unevaluated.

## Rebuild the figures

The seven figures are generated from the same ledgers (figure 7 also uses `reports/audit_reanalysis.json`), without model weights:

    cd figures
    python run_all.py          # writes fig*.pdf (vector) and fig*.png previews
    python check_layout.py     # re-renders; fails on overlapping labels or a legend over data
    python audit_figures.py    # fails on labels < 7 pt, strokes < 0.5 pt, or poor grayscale contrast
    python verify_figures.py   # fails if any plotted number disagrees with results.tex, the text, or the fig6(b) bar heights

`fig1_design.py` to `fig7_ecf_validity.py` hold one figure each; `data_access.py` is the only place that
reads corpus data, and it reads `results.json`, `evaluation.json` and `data/audit_2x2/` only. Figure 7
reads the generated reanalysis JSON. `figures/preview.html` shows the first six with captions for quick reading.

File prefixes are generation order, not paper numbers: the corpus-defect figure appears first in
the manuscript, so `fig2_corpus.py` is Figure 1, `fig1_design.py` is Figure 2, `fig3_factorial.py`
is Figure 3, `fig5_controls.py` is Figure 4, `fig4_scoring.py` is Figure 5, `fig6_slices.py` is
Figure 6, and `fig7_ecf_validity.py` is Figure 7.

All figures are drawn at `\textwidth` (6.5 in), so a size in `plot_style.py` is the size on the
page: body labels 8 pt, ticks 7.6 pt, nothing below 7 pt.

To compile in this directory:

    tectonic main.tex

Alternatively run `pdflatex main`, `bibtex main` and `pdflatex main` twice. The supplied TMLR style and BibTeX files come from revision `7bf90efe3a0debbba703c05c43f3ff7e4d4a2992` of [the official template repository](https://github.com/JmlrOrg/tmlr-style-file). Third-party notices are supplied in the included style files and in `TEMPLATE-LICENSE`.

The ledger contains evaluation-derived values rather than document or annotation text. The anonymous supplement bundles the replay, numeric ledger, results and reproduction guide. It verifies the reported statistics without loading model weights.
