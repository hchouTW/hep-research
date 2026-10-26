# Guide to the `core/stats` diagnostics

The owner's decision guide to the seven scripts in `<plugin root>/core/stats/`: conventions, caps, which tool to
choose, the skill scripts, and what is not implemented. What each subcommand assumes, needs and returns is in the
[command reference](core-stats-commands.md). Where an experiment profile's copy of these rules differs, this guide
applies.

The scripts are **diagnostics, not frameworks**: small counting, template and unfolding problems with stated
simplifications. A many-nuisance shape model, a workspace combination or a production sampler goes through the
pyhf/Combine adapter ([statistical tools](statistical-tools.md)). Run any script with `--help` for its input format.

**Reference index**: the [command reference](core-stats-commands.md) (per-module
subcommands, inputs and outputs, validation tools outside `core/stats`, publication-gate rules),
[nuisance modeling](nuisance-modeling.md), [likelihood fitting](likelihood-fitting.md) (with sWeights),
[unfolding](unfolding.md), [combinations](combinations.md), [inference recipes](inference-recipes.md),
[pyhf and Combine](statistical-tools.md), [astroparticle](astroparticle-statistics.md),
[binned time series](time-series-inference.md),
[ML-assisted inference](ml-assisted-inference.md), [inference reasoning](statistical-inference-for-physics.md).

## Common conventions

- **Dependencies.** Standard library only (the covariance and response validators use NumPy for eigenvalues when
  installed and record the solver in `eigen_solver`); output is JSON labeled `[General method]`. Nothing in it is
  any experiment's performance.
- **Run, do not hand-compute.** When a shell is available, run the matching subcommand for an exact limit or
  interval and quote its JSON output; a value worked by hand (no shell, or a quick check) is labeled as such and is
  not presented as the script's result.
- **Seeds.** Every toy-based subcommand requires `--seed` and echoes it with the toy count and configuration. Record
  the seed, toy count, confidence level and script version next to any toy-based number.
- **Exit codes** (per module, from each module's docstring):

| Script | 0 | 1 | 2 |
|---|---|---|---|
| `poisson_diagnostics.py` | ok | `failed`: a limit or interval end not bracketed below the mean limit (1e5) | rejected input |
| `likelihood_limits.py` | ok | `failed`: a fit on the observed or Asimov data did not converge (`fit_diagnostics` gives the reasons; the numbers are not results); exit 3 `incomplete`: only toy fits failed | rejected input |
| `statistical_toys.py`, `unfolding_diagnostics.py` | ok | — | rejected input |
| `template_fit.py` | ok | fit `failed` (infeasible model or no convergence) | rejected input |
| `validate_covariance.py` | pass (or warnings without `--strict`) | errors (or warnings with `--strict`) | unreadable or not JSON |
| `validate_response.py` | pass (or warnings without `--strict`) | errors | unreadable or not JSON |

- **Caps.** Each module refuses inputs beyond its own range (exit 2), and the ranges differ by subcommand; there is
  no single limit. A limit that cannot be bracketed below the Poisson mean cap is reported `failed`, never clipped.
  This table is checked against the code by `tests/skills/hep_statistics/test_core_stats_guide.py` (`CapsTable`):

| Where | Cap | Beyond it |
|---|---|---|
| every Poisson routine (`_poisson.py` `MAX_MEAN`) | mean <= 1e5 | asymptotic or Gaussian treatment, labeled as such |
| `poisson_diagnostics.py fc-interval` (`FC_MAX_TOTAL_MEAN`) | total mean <= 500 | `cls-limit`, or `likelihood_limits.py profile-fc` |
| `likelihood_limits.py` single-bin subcommands (`_inputs1`: profile-*, neyman-*) | b <= 200, sigma_b <= 100 | the pyhf adapter, or the asymptotic formulas labeled as such |
| `likelihood_limits.py multibin-limit` | bins <= 50 (o), bin b <= 200, total n <= 400 (o), mc_stat <= 100 | the pyhf adapter |
| `likelihood_limits.py shape-limit` with toys, `shape-gof`, `contour` (`SHAPE_TOY_CAPS`) | bins <= 40 (o), bin b <= 200, total n <= 400 (o), mc_stat <= 100, nuisances <= 8 (o) | `shape-limit` without toys, or the pyhf adapter |
| `likelihood_limits.py shape-limit` without toys (`SHAPE_ASYMPTOTIC_CAPS`) | bins <= 100 (o), bin b <= 1e4, total n <= 1000000 (o), nuisances <= 8 (o) | the pyhf adapter |
| `likelihood_limits.py` toy counts | toys 100 to 100000 | partition the toys (hep-computing) and merge |
| `statistical_toys.py` toy counts (`MAX_TOYS`) | toys <= 200000 | partition the toys and merge |
| `statistical_toys.py ratio-cov` | numerator, denominator <= 1e5 | `ratio-cov-analytic`, or `ratio-measured` (measured covariance, denominator <= 1e12) |
| `statistical_toys.py ratio-cov-analytic` (`ANALYTIC_MIN_COUNTS`, `ANALYTIC_MAX_COUNTS`) | counts 1e4 to 1e12 | below: `ratio-cov` (toys) |
| `statistical_toys.py unfold-scan` | reco and truth bins <= 60 (o) | a dedicated unfolding framework |
| `unfolding_diagnostics.py` response-stat, outer-coverage, response-covariance | mc_events <= 1e5 | the analytic response covariance by hand, labeled |
| `unfolding_diagnostics.py` response-covariance, response-measured | response cells <= 400 | rebin, or a dedicated framework |
| `unfolding_diagnostics.py response-stat` with `tsvd` | truth bins <= 20 (o) | `tikhonov`, or a dedicated framework |
| `unfolding_diagnostics.py` Jacobian diagnostics (response-covariance, response-measured) with `tsvd` | bins <= 15 (o) | `tikhonov` |
| `unfolding_diagnostics.py dagostini-unfold` (`UNFOLD_MAX_COUNTS`, `UNFOLD_MAX_MC_EVENTS`) | data <= 1e9, mc_events <= 1e12 | a dedicated framework |
| `template_fit.py` (`MAX_TEMPLATES`, `MAX_BINS`) | templates <= 6 (o), bins <= 60 (o), nuisances <= 8 (o) | the pyhf adapter |

  (o): overridable with `--allow-outside-validated-range` (`_caps.py`): the run goes ahead, lists each cap exceeded
  and is labeled `outside-validated-range`, which the publication gate refuses without a validation record. The
  other caps protect numerical accuracy or are handled by partitioning; a toy loop whose estimated runtime exceeds
  10 s prints the estimate to stderr first.
- **Fit verdicts** (`fit_diagnostics.py`, helper, no CLI). The fits of `shape-limit`, `shape-gof` and `contour` are
  `converged` only with a finite NLL, a positive-definite Hessian and EDM at most 1e-5, else `failed` with reasons
  ([details](core-stats-commands.md#conventions-in-detail)); `failed` (exit 1) when a fit on the data failed,
  `incomplete` (exit 3) when only toy fits failed; failed toys are counted, never dropped.
- **Toy tails** (`tail_estimation.py`, helper, no CLI). A toy p-value is k exceedances of N toys, with its
  Clopper-Pearson interval, and at k = 0 a one-sided 95% upper bound `1 - 0.05^(1/N)`, never p = 0
  ([details](core-stats-commands.md#conventions-in-detail)).
- **Toy ensembles** (`toy_ensemble.py`, helper, no CLI): every toy study states its ensemble, counts every toy's
  outcome and never pools ensembles; details in the [command reference](core-stats-commands.md#toy-ensembles).
- **Broken power law** (`broken_power_law.py`, helper, no CLI): one parametrization for `covariance_fit.py` and
  hep-measurement `cr_spectrum_powerlaw_fit.py` ([conventions](core-stats-commands.md#broken-power-law)).
- **Change points** (`change_point.py`, helper, no CLI): weighted trends, binary segmentation, CUSUM and
  toy-calibrated thresholds for a declared false-alarm rate; used by hep-detector `stability_monitor.py`.
- **Simulation studies** (`distributions.py`, `batch_means.py`, `decisions.py`, helpers, no CLI): t and F
  quantiles; batch means over K blocks (exact intervals at low counts, quantiles, block-mode MPV); the equivalence
  gate and the detection limit. Only study-layer gates of Geant4 studies; verdicts belong to `contracts/design.py`.
- **Covariance and correlation matrices** go through one strict Cholesky (`_linalg.py`, private, no CLI). It works
  on the matrix scaled to a unit diagonal, so units never change the verdict. A pivot below -1e-10 is an error
  that names the matrix, a fit refuses a singular matrix, and toy sampling accepts a semi-definite one and records
  the shift in `regularization`. Nothing is repaired silently.
- A `failed` fit never feeds an inference or a `statistical-result` except one whose `fit_status` is `failed`.

## Choosing a tool

| Question | First tool | Then, or instead |
|---|---|---|
| Limit or interval for a count with a **known** background | `poisson_diagnostics.py upper-limit`, `fc-interval`, `cls-limit` | `interval` for a mean with no background; `coverage` to check a construction |
| Same with an **uncertain** background | `likelihood_limits.py profile-limit`, `profile-cls`, `profile-fc` | compare with the marginalized `--sigma-b` result; `neyman-limit` when coverage over the nuisance matters |
| Discovery significance of a count | `likelihood_limits.py profile-significance` (uncertain b), `statistical_toys.py boundary` (known b), `shape-significance` (several bins, nuisances) | ON/OFF counting: `<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py` |
| N hypotheses, no scan data | Bonferroni or Šidák bound (conservative), worked by hand and labeled | with scan data: `look_elsewhere.py` |
| Several bins sharing one signal strength | `likelihood_limits.py multibin-limit` | `shape-limit` when shapes and several nuisances matter; the pyhf adapter beyond that |
| Finite Monte Carlo statistics in templates | `statistical_toys.py template-stat`, then `template-bb` | `template_fit.py bb-fit`/`bb-toys` for several templates, `wbb-fit`/`wbb-toys` for weighted MC and nuisances |
| Unfolding: D'Agostini iterations | `statistical_toys.py unfold-scan`, then `unfolding_diagnostics.py closure --method dagostini` | then `dagostini-unfold` (the data, with covariance) |
| Unfolding: Tikhonov or truncated SVD | `unfolding_diagnostics.py regularized-scan` (`tikhonov`, `tsvd`; it refuses `dagostini`), `closure` | `choose-regularization`, `response-stat`, `response-covariance`, `fold-compare`, `nonparam-fold` |
| Ratio or fraction with correlated systematics | `statistical_toys.py ratio-measured` (measured covariance) | `ratio-cov` (declared structures), `ratio-cov-analytic` (the same at counts >= 1e4, full covariance), `ratio-toys` (counts with systematic nuisances) |
| Is this covariance or response matrix well formed? | `validate_covariance.py`, `validate_response.py` | — |

## Skill scripts

Helpers in `skills/hep-statistics/scripts/` (read `--help` first); they call the modules above, never replace
them: run them, do not hand-compute.

Dependencies are marked per script: unmarked scripts use the standard library only; marked ones refuse to run
without NumPy (and SciPy) with exit 2 and a JSON message, and every script prints `--help` without them.

- `li_ma_significance.py`: ON/OFF significance, with toy or exact conditional p-values at low counts.
- `look_elsewhere.py` (needs NumPy): global significance of a one-dimensional scan (brute-force toys or upcrossings).
- `global_significance.py` (needs NumPy): toy-calibrated global significance for a recorded scan.
- `sensitivity_and_gof.py` (needs NumPy): Asimov discovery sensitivity (standard library) and toy-calibrated goodness of fit (NumPy).
- `bayes_diagnostics.py` (needs NumPy): R-hat, ESS and MCSE of supplied chains, prior reweighting; `bayes_calibration.py` (needs NumPy and SciPy): quantile and SBC calibration checks.
- `combine_measurements.py` (needs NumPy): GLS combination once the combination plan accepts the inputs (example: `skills/hep-statistics/assets/combine.example.json`); `combine_asymmetric.py`: Barlow's asymmetric errors; `split_consistency.py`: do split samples agree, shared blocks subtracted, said when undeclared; `build_covariance.py`: a `[Proposal]` covariance from declared correlation models and a length scan. Both: NumPy (and SciPy) at run time.
- `covariance_fit.py` (needs NumPy and SciPy): fits to published points with their covariance (Peelle diagnostics; built-in, plug-in and `tabulated-grid` models; per-dataset scale nuisance); `break-scan`: toy-calibrated break; `discrete_profile.py` (needs NumPy and SciPy): discrete profiling; `eft_scan.py` (needs NumPy and SciPy): EFT scans; `pcl_efficiency_ratio.py` (needs NumPy and SciPy), `ratio_estimation.py` (needs NumPy): ratio and efficiency intervals; `sweighted_fit.py` (needs NumPy and SciPy): sWeighted fits.
- `result_artifact.py`: a `statistical-result` artifact from a tool's output, with its status label; `extract_names.py`: N10
  naming inventory.
- `pdf_reweighting.py`: Bayesian reweighting of a PDF replica set (NNPDF and Giele-Keller weights, N_eff);
  `hessian_profiling.py`: linear Hessian profiling of a Hessian set with new data; [PDF fits](pdf-fit-statistics.md).
  NumPy at run time.
- `roofit_fit_check.py` (needs PyROOT): fit status (status 0, covQual 3, EDM below `--edm-max`), `weighted`, `toys` (pulls), `crosscheck` (against core/stats); [RooFit and RooStats](roofit-and-roostats-methods.md).
- `project_uncertainty.py`: an uncertainty budget and Asimov significance at k times the exposure (M5 scaling
  classes) and the reach; outputs are labeled `projection` and fail the publication gate.
- `tail_extrapolation.py`: a control-region tail fitted by several model families and extrapolated into the signal
  region, validated on a cut of the control region; envelope kept apart; NumPy and SciPy at run time.
- `periodicity_scan.py`: generalized Lomb-Scargle with a surrogate global p (white, AR(1), OU);
  `time_structure.py`: change points (toy-calibrated false alarms) and lags with surrogates. NumPy at run time.
- Inference scripts of hep-measurement, the pyhf and Combine starting points and the unbinned fit: [command
  reference](core-stats-commands.md#inference-scripts-outside-hep-statistics).

## Not implemented

Weights that vary within a bin in the toy MC; non-Gaussian or correlated priors in the template fit; a Berger-Boos
construction for several nuisances or for the multi-bin or shape model; bin-to-bin correlated shape nuisances;
correlated gamma nuisances; Poisson-exact cross-validation for the linear estimators and K-fold variants;
forward-folding priors learned from data or with free hyperparameters; efficiency uncertainties that depend on the
unfolded spectrum; a measured covariance of anything other than the response cells. Each would be a framework, not a
diagnostic. Post-fit nuisance impacts, look-elsewhere corrections, expected sensitivity, goodness of fit and Bayesian
convergence live outside `core/stats` (the reference index and skill scripts).

## Failure modes

The failure modes of quoting these results are listed in the [command reference](core-stats-commands.md#failure-modes).
