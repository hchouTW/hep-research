# Guide to the `core/stats` diagnostics

The owner's decision guide to the seven scripts in `<plugin root>/core/stats/`: conventions, caps, which tool to
choose, the skill scripts, and what is not implemented. What each subcommand assumes, needs and returns is in the
[command reference](core-stats-commands.md). Experiment profiles may record how an experiment applies these tools; the general rules live here, and
where a profile's copy differs, this guide applies.

The scripts are **diagnostics, not frameworks**: small counting, template and unfolding problems with stated
simplifications. A many-nuisance shape model, a workspace combination or a production sampler goes through the
pyhf/Combine adapter ([statistical tools](statistical-tools.md)). Run any script with `--help` for its input format.

## Contents

1. [Common conventions](#common-conventions)
2. [Choosing a tool](#choosing-a-tool)
3. [Skill scripts](#skill-scripts)
4. [Not implemented](#not-implemented)
5. [Failure modes](#failure-modes)

**Reference index**: the [command reference](core-stats-commands.md) (per-module
subcommands, inputs and outputs, validation tools outside `core/stats`, publication-gate rules),
[nuisance modeling](nuisance-modeling.md), [likelihood fitting](likelihood-fitting.md) (with sWeights),
[unfolding](unfolding.md), [combinations](combinations.md), [inference recipes](inference-recipes.md),
[pyhf and Combine](statistical-tools.md), [astroparticle](astroparticle-statistics.md),
[binned time series](time-series-inference.md),
[ML-assisted inference](ml-assisted-inference.md), [inference reasoning](statistical-inference-for-physics.md).

## Common conventions

- **Dependencies.** Standard library only (the covariance and response validators use NumPy for their eigenvalues
  when it is installed, and record which solver ran in `eigen_solver`); output is JSON labeled `[General method]`. Nothing in the output is the
  performance of any experiment.
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
| `likelihood_limits.py multibin-limit` | bins <= 50, bin b <= 200, total n <= 400, mc_stat <= 100 | the pyhf adapter |
| `likelihood_limits.py shape-limit` with toys, `shape-gof`, `contour` (`SHAPE_TOY_CAPS`) | bins <= 40, bin b <= 200, total n <= 400, mc_stat <= 100 | `shape-limit` without toys, or the pyhf adapter |
| `likelihood_limits.py shape-limit` without toys (`SHAPE_ASYMPTOTIC_CAPS`) | bins <= 100, bin b <= 1e4, total n <= 1000000 | the pyhf adapter |
| `likelihood_limits.py` toy counts | toys 100 to 100000 | partition the toys (hep-computing) and merge |
| `statistical_toys.py` toy counts (`MAX_TOYS`) | toys <= 200000 | partition the toys and merge |
| `statistical_toys.py ratio-cov` | numerator, denominator <= 1e5 | `ratio-cov-analytic`, or `ratio-measured` (measured covariance, denominator <= 1e12) |
| `statistical_toys.py ratio-cov-analytic` (`ANALYTIC_MIN_COUNTS`, `ANALYTIC_MAX_COUNTS`) | counts 1e4 to 1e12 | below: `ratio-cov` (toys) |
| `statistical_toys.py unfold-scan` | reco and truth bins <= 60 | a dedicated unfolding framework |
| `unfolding_diagnostics.py` response-stat, outer-coverage, response-covariance | mc_events <= 1e5 | the analytic response covariance by hand, labeled |
| `unfolding_diagnostics.py` response-covariance, response-measured | response cells <= 400 | rebin, or a dedicated framework |
| `unfolding_diagnostics.py dagostini-unfold` (`UNFOLD_MAX_COUNTS`, `UNFOLD_MAX_MC_EVENTS`) | data <= 1e9, mc_events <= 1e12 | a dedicated framework |
| `template_fit.py` (`MAX_TEMPLATES`, `MAX_BINS`) | templates <= 6, bins <= 60 | the pyhf adapter |
- **Fit verdicts** (`fit_diagnostics.py`, helper, no CLI). The damped Newton fits of `shape-limit`, `shape-gof` and
  `contour` return a verdict: `converged` only with a finite NLL, a positive-definite Hessian and EDM = g^T H^-1 g / 2
  at most 1e-5 (stricter than iminuit's default: Migrad stops at EDM < 0.002 x tol x errordef, with tol 0.1,
  that is 1e-4 for a negative log-likelihood with errordef 0.5; the threshold depends on the tolerance, iminuit
  reference documentation); otherwise `failed` with reasons (`invalid_domain`,
  `hessian_not_positive_definite`, `gradient_not_small`, `max_iterations`, `line_search_stalled`). A best fit on the
  boundary `mu = 0` is checked by the KKT condition (the profile rises into `mu > 0`), not by an interior Hessian. A
  conditional NLL below the global one by more than 1e-4 triggers a global refit from the conditional point and, if
  it remains, a recorded failure, never a silently clipped `q`. Results carry `fit_diagnostics` (fits, failures and
  reasons for the observed data and for toys) and `status`: `failed` (exit 1) when a fit on the data failed,
  `incomplete` (exit 3) when only toy fits failed; failed toys are counted, never dropped, and toy p-values then
  carry the range `[k/N, (k+F)/N]`.
- **Poisson domain.** A negative or non-finite Poisson mean is outside every likelihood here (NLL = +inf); a mean of
  0 is allowed only for an empty bin. A shape template that interpolates below zero is therefore excluded by the fit
  instead of being read as an empty bin.
- **Toy tails** (`tail_estimation.py`, helper, no CLI). A toy p-value is k exceedances of N toys. Outputs carry
  `toy_tail`: k, N, the estimate k/N (None at k = 0), the Clopper-Pearson interval at 68.27%, and at k = 0 a one-sided
  95% upper bound `1 - 0.05^(1/N)` (0.0295 for N = 100); the legacy `p_value_toys` and binomial-error fields are None
  where they would claim p = 0 or an error of 0. Exact Poisson tails stay in log space (`log_p_value_exact_poisson`).
- **Toy ensembles** (`toy_ensemble.py`, helper, no CLI): every toy study states its ensemble, counts every toy's
  outcome and never pools ensembles; details in the [command reference](core-stats-commands.md#toy-ensembles).
- **Broken power law** (`broken_power_law.py`, helper, no CLI): one parametrization for `covariance_fit.py` and
  hep-analysis `cr_spectrum_powerlaw_fit.py` ([conventions](core-stats-commands.md#broken-power-law)).
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

Command-line helpers in `skills/hep-statistics/scripts/` (read `--help` first); they call the modules above and never
replace them. The rule "run, do not hand-compute" applies.

Dependencies are marked per script: unmarked scripts use the standard library only; marked ones refuse to run
without NumPy (and SciPy) with exit 2 and a JSON message, and every script prints `--help` without them.

- `li_ma_significance.py`: ON/OFF significance, with toy or exact conditional p-values at low counts.
- `look_elsewhere.py` (needs NumPy): global significance of a one-dimensional scan (brute-force toys or upcrossings).
- `global_significance.py` (needs NumPy): toy-calibrated global significance for a recorded scan.
- `sensitivity_and_gof.py` (needs NumPy): Asimov discovery sensitivity (standard library) and toy-calibrated goodness of fit (NumPy).
- `bayes_diagnostics.py` (needs NumPy): R-hat, ESS and MCSE of supplied chains, prior reweighting; `bayes_calibration.py` (needs NumPy and SciPy): quantile and SBC calibration checks.
- `combine_measurements.py` (needs NumPy): generalized least squares combination of one observable once the combination plan accepts the inputs (declared cross-dataset blocks, shared auxiliary measurements, no Gaussianized envelope); a worked SYNTHETIC input (2 experiments, 3 bins, shared luminosity) is `skills/hep-statistics/assets/combine.example.json`; `combine_asymmetric.py`: Barlow's asymmetric errors.
- `covariance_fit.py` (needs NumPy and SciPy): fits to published points with their covariance, with the Peelle diagnostics (constant, line, normalized exponential, sharp or smooth broken power law, plug-in `function(theta, x)`, `tabulated-grid`); `break-scan`: toy-calibrated break interval and no-break test (no Wilks); `discrete_profile.py` (needs NumPy and SciPy): discrete profiling over a model family; `eft_scan.py` (needs NumPy and SciPy): EFT parameter scans; `pcl_efficiency_ratio.py` (needs NumPy and SciPy), `ratio_estimation.py` (needs NumPy): ratio and efficiency intervals; `sweighted_fit.py` (needs NumPy and SciPy): sWeighted fits with covering uncertainties.
- `result_artifact.py`: writes a `statistical-result` artifact from a tool's output, with its status label.
- Inference scripts owned by hep-analysis (read their `--help`). `cr_spectrum_powerlaw_fit.py` fits a single or
  continuous broken power law in log flux (a full covariance, linearized); a free break is calibrated here
  (`break-scan`, `global_significance.py`). `particle_ratio_with_uncertainty.py` gives a ratio or fraction of two yields by the
  delta method with one optional correlation coefficient: with correlated points or bin-to-bin correlated
  systematics use `covariance_fit.py fit` or
  `statistical_toys.py ratio-cov` / `ratio-measured` here, and at low counts an exact construction
  (`pcl_efficiency_ratio.py ratio`, Fieller or Clopper-Pearson). Two different "counting references":
  `skills/hep-analysis/scripts/counting_reference.py` is a flat-prior Bayesian upper bound with an exactly known
  background (not CLs, no nuisances); the frequentist counting constructions are `core/stats/poisson_diagnostics.py`
  (and `likelihood_limits.py` with an uncertain background). pyhf and Combine starting points: `adapters/pyhf-combine/assets/` (with `pyhf_nuisance_diagnostics.py` for pulls, constraints and impacts); unbinned fits: `adapters/unbinned-fit/assets/unbinned_fit.py`.

## Not implemented

Weights that vary within a bin in the toy MC; non-Gaussian or correlated priors in the template fit; a Berger-Boos
construction for several nuisances or for the multi-bin or shape model; bin-to-bin correlated shape nuisances;
correlated gamma nuisances; Poisson-exact cross-validation for the linear estimators and K-fold variants;
forward-folding priors learned from data or with free hyperparameters; efficiency uncertainties that depend on the
unfolded spectrum; a measured covariance of anything other than the response cells. Each would be a framework, not a
diagnostic. Post-fit nuisance impacts, look-elsewhere corrections, expected sensitivity, goodness of fit and Bayesian
convergence live outside `core/stats` (the reference index and skill scripts).

## Failure modes

- Quoting the classical limit when it is zero or negative; reading a Feldman-Cousins lower bound of 0 as a failure or
  as evidence for zero signal; quoting a CLs limit without its expected band, or as an exact-coverage confidence
  interval or a Bayesian bound.
- Quoting an asymptotic limit or significance at small counts without the toy calibration; a boundary significance
  from naive Wilks; reporting a profile limit as CLs.
- Treating a profile-construction interval or limit as having guaranteed coverage, or the finite-grid `neyman-limit` as
  a proof of coverage; reading one coverage number as proof of coverage; omitting the seed.
- Using an exact interval for a count whose background is uncertain, as if it were known; reporting a marginalized
  result without varying `sigma_b`; choosing a Gaussian, log-normal or gamma constraint by convenience.
- Ignoring finite MC statistics in a response or template; quoting a naive-fit error when `bb-fit` shows it inflated;
  using independent response cells for a high-efficiency column; ignoring an efficiency systematic that scales whole
  columns.
- Choosing a regularization or iteration count from a scan that used the same truth as its prior; picking one
  criterion without a toy comparison; ignoring a strongly negative adjacent-bin correlation; letting a fitted index
  depend on the regularization without `fold-compare`; quoting a Laplace error of a penalized fit without toys;
  treating a pull width near 1 on one truth as validation on another; comparing forward-fold priors by their ranking
  on one truth.
- Using a diagonal-only covariance for a ratio or fit whose bins share systematics; assuming a ratio cancels a
  systematic without a stated correlation.
- Feeding a `failed` template fit into an inference, or applying a script outside its stated range (means above 1e5,
  or 500 for `fc-interval`; more than 60 bins, more than 6 templates or 8 nuisances) without a validated
  approximation.
