# hep-statistics

Use when the deliverable is a statistical inference or its diagnostics in physics: likelihoods, binned and unbinned fits, template fits, fits to published data points with their covariance, frequentist intervals and limits (Neyman, Feldman-Cousins, CLs, profile likelihood, asymptotics), Bayesian posteriors, significance and look-elsewhere effects, low or zero counts, nuisance parameters, covariance assembly and validation, unfolding with regularization and coverage, fits that use a folded prediction, toys and Asimov datasets, goodness of fit, model comparison, and combinations.

**Owns:** likelihoods, frequentist and Bayesian inference, intervals and limits, covariance assembly, model comparison, unfolding algorithms and regularization, fits that use a response, toys, coverage, combinations; stewardship of `core/stats`. Typical artifacts: `statistical-result`, the inference part of `comparison-spec`, diagnostics.

**Never:** invent a correlation, a prior or a physics assumption; turn a theory envelope into a Gaussian without the hep-theory prescription; report a fit that did not converge as a result.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, Step 0 for a quick question and the task-to-tool table (default tool, fallback, or "no shipped tool"), workflow, context resolution |
| `references/` | fourteen references: PDF, nPDF and FF fit statistics (chi2 forms, t0, tolerances, reweighting, profiling), the `core/stats` decision guide and its command reference, combinations (BLUE, Peelle, likelihood-level), nuisance modeling, likelihood fitting (including sWeights and weighted unbinned fits), unfolding, inference recipes, statistical tools (pyhf, Combine), astroparticle statistics, binned time series (documented; its time-bin covariance recipe demonstrated on synthetic data by `test_time_series_covariance.py`), ML-assisted inference, inference reasoning |
| `assets/` | `combine.example.json`: SYNTHETIC input for `combine_measurements.py` (two experiments, shared luminosity) |
| `scripts/` | twenty-six helpers (including `degeneracy.py`, the two-level degeneracy diagnostics: a Fisher screen, then profile-likelihood scans that record the range where a degeneracy holds; `extract_names.py`, the naming extractor for nuisances, channels and processes; `roofit_fit_check.py`: RooFit status, pulls, cross-checks with core; `pdf_reweighting.py` and `hessian_profiling.py` for updating published PDF sets); the executable checks themselves (limits, template fits, unfolding diagnostics, Poisson diagnostics, toys, covariance and response validation) live in `core/stats/` |

## Scripts

`li_ma_significance.py` (ON/OFF significance, exact conditional p-values at low counts), `look_elsewhere.py` (global significance of a 1D scan), `sensitivity_and_gof.py` (Asimov discovery sensitivity, toy-calibrated goodness of fit), `global_significance.py`, `bayes_diagnostics.py` (R-hat, ESS, MCSE, prior reweighting), `bayes_calibration.py`, `combine_measurements.py` (generalized least squares once a combination plan accepts the inputs), `combine_asymmetric.py` (Barlow's asymmetric errors), `tail_extrapolation.py` (a control-region tail extrapolated into the signal region, validated on a cut of the control region, the envelope between models kept apart), `project_uncertainty.py` (an uncertainty budget and Asimov significance projected to k times the exposure with the M5 scaling classes, and the reach; every output labeled `projection`), `split_consistency.py` (agreement of split samples such as eras: chi2 of the difference with the declared shared covariance subtracted, a generalized chi2 for K splits, Sidak or toy correction of the pairwise tests), `covariance_fit.py` (its `tabulated-grid` model fits parameters tabulated on a grid of predictions, one gated `prediction` per node, and reports degenerate directions, with a `degeneracy_scan` block also profile-likelihood scans through `degeneracy.py`; demonstrated on synthetic data, end to end in `examples/bc-propagation-fit/`; exit 3 when a data covariance or an uncertainty correlation is missing; a joint fit of several datasets in which a dataset may declare a scale nuisance on its abscissa), `discrete_profile.py`, `eft_scan.py`, `pcl_efficiency_ratio.py`, `ratio_estimation.py`, `sweighted_fit.py`, `result_artifact.py` (writes a `statistical-result` from a tool's output; `--paradigm bayesian` from `bayes_diagnostics.py diagnose` output with priors and sampler). When a shell is available, run the matching check and report its output; a value worked by hand is labeled as such. pyhf and Combine starting points are under `adapters/pyhf-combine/assets/`, unbinned fits under `adapters/unbinned-fit/assets/`. `build_covariance.py` (a `[Proposal]` covariance from declared correlation models: none, full, log-length, antisymmetric, AR(1), exponential in time, a user matrix; each block checked for positive semi-definiteness; a scan of the length). `periodicity_scan.py` (weighted generalized Lomb-Scargle on unevenly sampled series; band-maximum global p-value from white, AR(1) or Ornstein-Uhlenbeck surrogates, the red-noise null refitted on every surrogate by default; caps on points, frequencies and surrogates). `time_structure.py` (`changepoint`: binary segmentation or PELT with the threshold or penalty calibrated by toys to a declared false-alarm rate, toys from a declared covariance or independence stated; `lag`: cross-correlation with phase-randomized surrogates and a look-elsewhere correction over lags, hysteresis between rising and falling branches). Iterative unfolding through pyunfold or RooUnfold, validated the same way (closure, stress tests, toy coverage): `adapters/unfolding/assets/unfold.py`.

## References

`references/core-stats-guide.md` for choosing and reading the executable checks; `references/statistical-inference-for-physics.md` for checking a likelihood, test, interval or limit against the stated conclusion (its claim-calibration table is what hep-authoring cites).

## Handoffs

| Need | Hand to |
|---|---|
| Missing systematic or correlation evidence | hep-measurement or hep-detector |
| Theory-uncertainty prescription | hep-theory |
| Large toy campaigns, batch partitioning | hep-computing |
| Reporting the result | hep-authoring |
| SBI, neural likelihoods | hep-ml |

## Tests and validation

`tests/skills/hep_statistics/` (twenty test modules, including `test_grid_fit.py` for the `tabulated-grid` model and `test_time_series_covariance.py`) plus the `core/stats` tests under `tests/core/`, the statistics benchmarks under `examples/stats-benchmarks/`, the `unfolding-coverage` example, the `bc-propagation-fit` example (`tests/examples/test_bc_propagation_fit.py`), and the GitHub `stats-backends` and `statistics-validation` jobs (pyhf, ArviZ, Combine) recorded in `VALIDATION.md`. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
