# hep-statistics

Use when the deliverable is a statistical inference or its diagnostics in physics: likelihoods, binned and unbinned fits, template fits, fits to published data points with their covariance, frequentist intervals and limits (Neyman, Feldman-Cousins, CLs, profile likelihood, asymptotics), Bayesian posteriors, significance and look-elsewhere effects, low or zero counts, nuisance parameters, covariance assembly and validation, unfolding with regularization and coverage, fits that use a folded prediction, toys and Asimov datasets, goodness of fit, model comparison, and combinations.

**Owns:** likelihoods, frequentist and Bayesian inference, intervals and limits, covariance assembly, model comparison, unfolding algorithms and regularization, fits that use a response, toys, coverage, combinations; stewardship of `core/stats`. Typical artifacts: `statistical-result`, the inference part of `comparison-spec`, diagnostics.

**Never:** invent a correlation, a prior or a physics assumption; turn a theory envelope into a Gaussian without the hep-theory prescription; report a fit that did not converge as a result.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, Step 0 for a quick question and the task-to-tool table (default tool, fallback, or "no shipped tool"), workflow, context resolution |
| `references/` | eleven references: the `core/stats` decision guide and its command reference, combinations (BLUE, Peelle, likelihood-level), nuisance modeling, likelihood fitting (including sWeights and weighted unbinned fits), unfolding, inference recipes, statistical tools (pyhf, Combine), astroparticle statistics, ML-assisted inference, inference reasoning |
| `assets/` | `combine.example.json`: SYNTHETIC input for `combine_measurements.py` (two experiments, shared luminosity) |
| `scripts/` | fifteen helpers; the executable checks themselves (limits, template fits, unfolding diagnostics, Poisson diagnostics, toys, covariance and response validation) live in `core/stats/` |

## Scripts

`li_ma_significance.py` (ON/OFF significance, exact conditional p-values at low counts), `look_elsewhere.py` (global significance of a 1D scan), `sensitivity_and_gof.py` (Asimov discovery sensitivity, toy-calibrated goodness of fit), `global_significance.py`, `bayes_diagnostics.py` (R-hat, ESS, MCSE, prior reweighting), `bayes_calibration.py`, `combine_measurements.py` (generalized least squares once a combination plan accepts the inputs), `combine_asymmetric.py` (Barlow's asymmetric errors), `covariance_fit.py`, `discrete_profile.py`, `eft_scan.py`, `pcl_efficiency_ratio.py`, `ratio_estimation.py`, `sweighted_fit.py`, `result_artifact.py` (writes a `statistical-result` from a tool's output). When a shell is available, run the matching check and report its output; a value worked by hand is labeled as such. pyhf and Combine starting points are under `adapters/pyhf-combine/assets/`, unbinned fits under `adapters/unbinned-fit/assets/`.

## References

`references/core-stats-guide.md` for choosing and reading the executable checks; `references/statistical-inference-for-physics.md` for checking a likelihood, test, interval or limit against the stated conclusion (its claim-calibration table is what research-communication cites).

## Handoffs

| Need | Hand to |
|---|---|
| Missing systematic or correlation evidence | hep-analysis or detector-response |
| Theory-uncertainty prescription | hep-theory |
| Large toy campaigns, batch partitioning | hep-computing |
| Reporting the result | research-communication |
| SBI, neural likelihoods | physics-ml |

## Tests and validation

`tests/skills/hep_statistics/` (seventeen modules) plus the `core/stats` tests under `tests/core/`, the statistics benchmarks under `examples/stats-benchmarks/`, the `unfolding-coverage` example, and the GitHub `stats-backends` and `statistics-validation` jobs (pyhf, ArviZ, Combine) recorded in `VALIDATION.md`. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
