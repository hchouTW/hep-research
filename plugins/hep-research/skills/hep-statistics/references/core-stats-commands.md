# `core/stats` command reference

Per-module reference for the scripts in `<plugin root>/core/stats/`, split from the [core/stats guide](core-stats-guide.md) (conventions, caps, choosing a tool, skill scripts, failure modes), which applies to everything here. Each section says which question a subcommand answers, what it assumes, what it needs and returns, when to use it instead of an alternative, and what it does not do. Run any script with `--help` for its input format.

## Contents

1. [`poisson_diagnostics.py`: exact Poisson constructions](#poisson_diagnosticspy-exact-poisson-constructions)
2. [`likelihood_limits.py`: profile-likelihood constructions](#likelihood_limitspy-profile-likelihood-constructions)
3. [`statistical_toys.py`: narrow toy studies](#statistical_toyspy-narrow-toy-studies)
4. [`template_fit.py`: Barlow-Beeston template fits](#template_fitpy-barlow-beeston-template-fits)
5. [`unfolding_diagnostics.py`: regularization, closure, folding](#unfolding_diagnosticspy-regularization-closure-folding)
6. [`validate_covariance.py` and `validate_response.py`](#validate_covariancepy-and-validate_responsepy)
7. [Validation tools outside `core/stats`](#validation-tools-outside-corestats)
8. [Toy ensembles](#toy-ensembles)

## `poisson_diagnostics.py`: exact Poisson constructions

Single-bin counting with an exactly known background (no toys except `coverage`). A background uncertainty is
available only as a Cousins-Highland marginalization (`--sigma-b`).

- `upper-limit --n N --b B --cl CL`: classical one-sided upper limit on a signal mean, from
  `P(N' <= N | s + B) = 1 - CL`. For `N = 0`, `B = 0` it is `-ln(1 - CL)` (about 3.00 at 95%). When the limit is zero
  or negative (`N` small against `B`) the script reports no limit: that is not a result. Use `fc-interval` or
  `cls-limit` and report the expected sensitivity. For `N = 0` the classical limit is `-ln(1 - CL) - B`: it shrinks as
  `B` grows; it is `B`-independent only for a flat-prior Bayesian bound, which answers a different question.
- `interval --n N --cl CL`: Garwood central interval on a Poisson mean; conservative (coverage at least `CL`).
- `fc-interval --n N --b B --cl CL [--step X]`: Feldman-Cousins unified interval on `s >= 0` with a known background,
  by a deterministic grid scan (default step 0.005; the step bounds the accuracy and discreteness makes it slightly
  conservative). The upper end is forced non-increasing in `B`, as Feldman and Cousins did for their tables; this
  reproduces their Tables IV and VI (90% and 95%, `N = 0..10`, `B = 0..5`) within 0.01, for example `N = 0`, `B = 2`,
  90%: upper 1.26 (`tests/core/test_stats_poisson.py`). `--plain-construction` gives the unadjusted interval at this
  `B` alone (1.08 there); the output names the construction in `construction`. A lower bound of 0 at small `N` is
  expected, not a failure. With
  `--sigma-b S [--nodes K]` the background is marginalized over a truncated normal prior (default step 0.02); it
  converges to the known-background interval as `S -> 0`. That is not a profile treatment and its coverage at the true
  background is not guaranteed.
- `cls-limit --n N --b B --cl CL [--sigma-b S] [--nodes K]`: CLs upper limit (`CLs = CLs+b / CLb`) with the median and
  1- and 2-sigma expected limits under background only. CLs is a modified frequentist exclusion prescription (PDG,
  Statistics review): it over-covers by design and is not an exact nominal-coverage Neyman or Feldman-Cousins
  confidence belt, nor a Bayesian credible bound; a toy or plug-in implementation of it does not guarantee its
  coverage either. A Feldman-Cousins interval is not a CLs limit: never label one as the other. With `--sigma-b`, vary `sigma_b`
  and check the result moves little.
- `coverage --mu MU --cl CL --toys T --seed S`: fraction of seeded pseudo-experiments whose Garwood interval contains
  `MU`. Coverage of a discrete distribution oscillates with the true mean: one number is a diagnostic, scan the mean
  before claiming coverage.

Decision rule: a known background, one bin, no nuisance: use this module. Anything with an uncertain background,
nuisance parameters or a template fit needs `likelihood_limits.py` or a toy construction. Means above 1e5 (500 for
`fc-interval`) are outside the validated range.

## `likelihood_limits.py`: profile-likelihood constructions

Counting experiments with one signal strength `mu >= 0` and a Gaussian-constrained background (single bin unless
stated). The asymptotic results use the one-sided `q-tilde` and half-chi2 forms (Cowan et al. 2011); toys are seeded
and use common random numbers across a scan.

- `profile-limit --n --b --sigma-b [--cl --toys --seed]`: asymptotic upper limit (`q-tilde = z^2`) and a toy-calibrated
  limit; for `sigma_b = 0` the toy limit is compared with the exact classical limit. The asymptotic limit undershoots
  at small counts; the toy limit is the reference and is toy-noise limited.
- `profile-significance --n --b --sigma-b [--toys --seed]`: `q0` with the nuisance profiled; toy, half-chi2 asymptotic
  and naive Wilks p-values, and for `sigma_b = 0` the exact Poisson tail.
- `profile-fc --n --b --sigma-b [--cl --step --toys --seed]`: Feldman-Cousins-style interval with the nuisance profiled
  (critical values from toys at the profiled background). It reduces to Feldman-Cousins at `sigma_b = 0` and does not
  guarantee coverage over all true backgrounds; compare it with the marginalized `fc-interval --sigma-b` (they can
  differ either way).
- `profile-cls --n --b --sigma-b [--cl --expected-toys --toys --seed]`: CLs from toys of the one-sided profile
  statistic, with observed and (with `--expected-toys`) median and 1/2-sigma expected limits; it reproduces the exact
  `cls-limit` for a known background within toy noise.
- `multibin-limit --input FILE [--cl --toys --seed]`: bins sharing one `mu` with no, independent per-bin (Gaussian) or
  one common multiplicative background nuisance; the asymptotic observed limit (CLs+b-type, `q-tilde = z^2`) and the
  asymptotic CLs limit, the expected median and 1/2-sigma limits for both from the Asimov data set, and a seeded-toy
  p-value at the asymptotic limit as the calibration check (it should be near `1 - cl`; if not, use a toy-calibrated
  construction). Shapes and other nuisances are not modeled. A per-bin `mc_stat` (MC-statistics uncertainty of the
  background, also in `shape-limit` and `contour`) adds a Barlow-Beeston-lite factor per bin; leave it out only when
  the templates' MC statistics are negligible.
- `shape-limit --input FILE [--cl --toys --seed --cls-toys --cls-points --cls-max-runtime]`: multi-bin limit with several nuisances:
  background and signal normalization, background and signal shape by vertical interpolation (piecewise linear
  `code0` by default, or the smooth `code4p`; asymmetric normalization factors `hi`/`lo` with `code4`, `code1` or
  `code0`, as in pyhf), a damped Newton profile, the same asymptotic limits and bands as `multibin-limit`, and an
  optional toy p-value at the limit. With `--cls-toys N` it adds a toy-based CLs limit and expected 1/2-sigma limits on
  a grid of `--cls-points` values of `mu` (use it at low counts, where the asymptotic bands are too wide; the cost grows
  as toys x grid points x two fits: the run times three profile evaluations on the data, records
  `toy_cls_runtime_estimate_s` and refuses (exit 2) above `--cls-max-runtime`, default 600 s). A one-bin count
  with `b = 0` and `n = 0` reaches its optimum on the `mu = 0` boundary, judged by KKT; the toy CLs limit then
  equals CLs+b, `-ln(1 - cl)` within its Monte Carlo range. A normalization nuisance may be `gaussian` (factor `1 + sigma theta`), `lognormal`
  (`exp(sigma theta)`) or `gamma` (`1 + sigma theta` with a Poisson auxiliary measurement of `tau = 1/sigma^2`); an
  optional correlation matrix correlates the Gaussian-type nuisances (gamma ones cannot be correlated). Choose the
  constraint from the origin of the uncertainty ([nuisance modeling](nuisance-modeling.md)), not by convenience. Slow
  for many nuisances. Without toys (`--toys 0`, no `--cls-toys`) it runs on the asymptotic path at ordinary sizes (up to
  100 bins, 1e4 expected background events per bin, 1e6 events; `path` in the output); its asymptotic CLs limit agrees
  with pyhf 0.7.6 within 1% at 100 bins x 1000 events (`tests/adapters/test_backend_likelihood_equivalence.py`). The
  toy paths keep the small caps and point to the pyhf adapter beyond them.
- `shape-significance --input FILE [--toys --seed]`: discovery statistic q0 of a `shape-limit` model (several bins,
  the same nuisances): asymptotic p-value and, with `--toys`, a toy p-value from background-only toys at the nuisances
  profiled at `mu = 0` with the auxiliary measurements redrawn, reported through `toy_tail` (a bound at zero
  exceedances). Without nuisances it equals `look_elsewhere.py local` at the same template to 1e-6. Without toys the
  asymptotic caps apply.
- `shape-gof --input FILE [--mu --toys --seed]`: saturated-model goodness of fit of a `shape-limit` model (Poisson
  bins plus constraint terms, so pulled nuisances count), `mu` fitted (`mu >= 0`) or fixed, calibrated by toys from
  the fitted model; the chi-square reference (bins - 1 or bins degrees of freedom) is approximate and
  anti-conservative at a few events per bin. For template yields without nuisances use
  `sensitivity_and_gof.py gof`.
- `contour --input FILE [--cl 0.6827,0.95 --rays 36]`: two signal strengths (bins with `s1` and `s2`; the shape-limit
  nuisances except signal shapes; `mc_stat`): best fit, Hessian covariance and profile-likelihood contours at the
  chi-square 2-dof levels. Wilks coverage was checked with toys at about 50 events per bin; at low counts, check it
  with toys at the true point before quoting a region.
- `neyman-limit --n --b --sigma-b [--cl --beta --points --toys --seed]`: an approximation of the Berger-Boos
  construction over the background nuisance (finite nuisance grid, seeded toys): a signal is excluded only if the
  supremum of the toy p-value over the `(1 - beta)` confidence set of the background, plus `beta`, is at most
  `1 - cl`. The output carries the toy errors, a `coverage_claim` and whether the inputs lie in the range validated by
  seeded coverage scans. Single-bin background nuisance only.
- `neyman-coverage --s --b --sigma-b [--cl --beta --outer --inner --points --seed]`: coverage at one true point of the
  plug-in profile construction against the supremum construction. Outside the validated range, run it at the true
  values that matter before relying on `neyman-limit`; a single point is not global coverage.

Every toy p-value in this module carries `toy_tail` (see the guide's [Common conventions](core-stats-guide.md#common-conventions)); `shape-limit`, `shape-gof` and
`contour` carry `fit_diagnostics` and a `status` that sets the exit code. Write a `statistical-result` from any of
these outputs with `<plugin root>/skills/hep-statistics/scripts/result_artifact.py`, which keeps the status (a failed
fit becomes `fit_status: failed` with the `failed` label) and writes a toy p-value with no exceedance as a typed
bound. An output without a `status` (for example `li_ma_significance.py`) is refused unless `--assume-status` names
it, and the assumption is recorded (`results.cli_status_assumed`); a coverage value or toy count under
`--coverage-check not-checked` is refused. Check a result before calling it validated with `contracts/validate.py RESULT.json --gate publication`.

Decision rule: with an uncertain background prefer `profile-limit`, `profile-significance` or `multibin-limit` to a
marginalized result, and compare the two: the profile and the marginalized (Cousins-Highland) treatments answer
different questions, so a difference between them is information about the nuisance treatment, not an uncertainty to
add to the result; only a model or method uncertainty prescribed before the result (with its owner) is quantified and
combined. A profile limit is not a CLs limit (no CLs protection). Always report the expected sensitivity next to an observed limit. Near a boundary
or at small counts quote the toy value, not the asymptotic one.

## `statistical_toys.py`: narrow toy studies

Each subcommand answers one question under stated simplifications.

- `boundary --n --b [--toys --seed]`: discovery `q0` at the `s >= 0` boundary with a known background: exact Poisson,
  toy, half-chi2 and naive Wilks (chi2, 1 dof, which doubles the p-value) p-values and the fraction of toys at
  `q0 = 0` (about one half at large `B`). Run it before quoting a Wilks significance near a boundary; an uncertain
  background is not covered.
- `template-stat --sig --bkg --n-data --f --mc-sig --mc-bkg [--toys --seed]`: a one-parameter template-fraction fit with
  true and with finite-MC templates; bias, spread ratio (finite over true) and boundary fraction. It measures the cost
  of ignoring MC statistics; it is not a Barlow-Beeston fit. A spread ratio above about 1.1, or a bias above a stated
  fraction of the statistical error, is the trigger to put template statistics in the likelihood or enlarge the
  sample (a `[Proposal]` threshold).
- `template-bb ...` (same options): the same toys fit three ways (true templates, naive finite templates, a
  Barlow-Beeston-lite per-bin nuisance after Conway); bias, spread, pull width and coverage of the
  `delta lnL = 0.5` interval. A naive pull width above 1 with low coverage, restored by the nuisance, is the evidence
  that template statistics must enter the likelihood. It is the per-bin total-count approximation; use
  `template_fit.py` for several templates.
- `ratio-measured --input FILE [--toys --seed]`: per-bin ratios of two measured vectors with a supplied joint
  covariance (numerator then denominator, cross block included): linear and toy sigma, nonlinearity bias, bin-to-bin
  correlation, and a constant-ratio fit with the full covariance against diagonal only. Only symmetry and positive
  semi-definiteness of your covariance are checked.
- `ratio-cov --input FILE [--toys --seed]`: per-bin ratios with declared systematics (per-bin fractional sigma for
  numerator and denominator, numerator-denominator `rho`, bin-to-bin `full`, `none` or `exponential`); the weighted-mean
  spread against the independent-bins assumption. Use it only when no measured covariance exists.
- `ratio-cov-analytic --input FILE`: the full covariance matrix of the same per-bin ratios (same input) without toys,
  for every numerator and denominator count at least 1e4 (up to 1e12): first-order Poisson term `r^2 (1/N + 1/D)`,
  exact log-normal systematics. It agrees with toys within 5% per element at denominators 1e5-1e7
  (`tests/core/test_stats_statistical_toys.py`); below 1e4 it refuses and points to `ratio-cov`.
- `ratio-toys --n1 --n2 --sys name:sigma_num:sigma_den:rho [--toys --seed]`: ratio of two Poisson counts with
  multiplicative systematic nuisances of declared correlation; statistical, systematic and total spread against the
  residual, "cancels" and "independent" assumptions, plus the low-denominator bias. Run it before claiming that a ratio
  cancels a systematic; the correlation is your input.
- `unfold-scan --input FILE [--toys --seed]`: D'Agostini unfolding of seeded toys of a supplied response and truth;
  rms relative bias, spread and their sum per iteration. The bias is against the truth you supply, so the scan is
  circular: repeat with a different truth and prior before choosing an iteration count, and document the stopping rule
  separately.

## `template_fit.py`: Barlow-Beeston template fits

Several templates with free yields and the full per-template Barlow-Beeston likelihood (Barlow & Beeston 1993): one
nuisance per bin and template with a Poisson constraint from the MC count, profiled bin by bin through the single
Barlow-Beeston multiplier; yields by Nelder-Mead and errors from a numerical Hessian.

- `bb-fit --input FILE`: naive and full fits, yields, errors and the error inflation.
- `bb-toys --input FILE [--toys --seed]`: MC and data redrawn; bias, spread, pull width (standard deviation and robust
  MAD) and coverage per yield for each fit.
- `wbb-fit --input FILE`: weighted MC (per-bin sums of weights and of squared weights, effective counts with the
  scaled-Poisson constraint), shape nuisances (vertical interpolation between down, nominal and up per-bin weight sums)
  and normalization nuisances (a linear factor on a yield), all with a unit Gaussian constraint and fitted jointly
  with the yields by BFGS.
- `wbb-toys --input FILE [--toys --seed]`: toys for the weighted fit (effective counts redrawn at the nominal scale;
  data at the true yields with every nuisance at zero).

Limits: up to 6 templates, 8 nuisances and 60 bins; Hessian errors are unreliable for a yield near zero. Every fit
reports its diagnostics (minimizer convergence, a finite likelihood at the optimum, covariance quality, yields at the
boundary). A bin with data and no MC in any template makes the naive fit infeasible (reported in `naive_fit_failed`);
the Barlow-Beeston fit keeps each template's true content in such a bin as a nuisance and describes it. The status
follows the Barlow-Beeston fit: unconverged (or infeasible) means `failed` with **exit code 1**.

Decision rule: use `bb-fit`/`bb-toys` instead of the one-parameter `template-bb` whenever there are several templates,
and quote the full-fit error when `bb-fit` shows it inflated. Use either Barlow-Beeston or a per-bin `staterror`-type
nuisance for one statistical source, never both ([nuisance modeling](nuisance-modeling.md)).

## `unfolding_diagnostics.py`: regularization, closure, folding

Small response matrices (at most 60 bins; orientation and efficiency convention of `validate_response.py`), independent
Poisson data, no systematics. `--method` is `dagostini` (iterations; nonlinear, spread from toys; not accepted by
`regularized-scan`, which is analytic: scan D'Agostini iterations with `statistical_toys.py unfold-scan`), `tikhonov`
(curvature penalty, strength relative to the mean diagonal of `R^T W^2 R`) or `tsvd` (retained singular values of the
Poisson-weighted response); `--param` sets the strength, iterations or truncation.

- `regularized-scan --input --method [--values --toys --seed]`: analytic bias and covariance of the linear methods per
  setting, the minimum adjacent-bin correlation (strongly negative means too weak a regularization) and the fraction
  of toys with a negative bin.
- `closure --input --method --param [--toys --seed]`: noise-free closure of a different `test_truth` (the model
  dependence of the response weights and prior) with its bias significance, and seeded pulls (mean with standard
  error, width).
- `fold-compare --input --method --param [--toys --seed]`: a power-law index from a forward-folded Poisson likelihood
  against an unfold-then-chi2 fit with the unfolded covariance; bias and spread of each, with the true spectral form
  assumed known.
- `response-stat --input --method --param [--response-model --toys --seed]`: the response redrawn from finite generated
  counts; spread from data, from the response and from both, and the response share of the variance. It records
  `toys_generated`, `toys_used` and `toys_skipped` with the reason (a redrawn column with no event is never filled),
  never renormalizes a column, and counts toys where the independent-cell model gives a column efficiency above 1
  (use `--response-model multinomial` for high-efficiency columns).
- `outer-coverage --input --method --values --criterion --toys --seed`: independent outer-toy validation (linear
  methods). Every toy draws data from the generation truth (`test_truth` if given), redraws the MC response
  (`mc_events_per_truth_bin`, multinomial) and the efficiency factors (`efficiency_uncertainty`) when declared,
  chooses the regularization inside the toy (`gcv`, `loo_cv`, `l_curve_corner`; one value or `fixed`: none), and
  builds that toy's covariance from its own counts and estimate. It reports the bias per bin, marginal and
  simultaneous (chi-square, n_truth dof) coverage at 68.27%, the settings chosen and every toy's outcome (failures
  count as not covering). `covariance_omits` drops a generated source from the covariance: a negative baseline that
  must undercover. Pulls measured on the ensemble that tuned the regularization are not this evidence.
- `response-covariance --input --method --param [--response-model --toys --seed]`: the finite-response effect
  propagated analytically at first order (numerical Jacobian of the estimator, also for D'Agostini) as a full
  covariance among truth bins, cross-checked against toys. `--response-model multinomial` uses the exact multinomial
  covariance with a lost-event class (`Var R_ij = R_ij (1 - R_ij) / gen_j`, `Cov(R_ij, R_kj) = -R_ij R_kj / gen_j`),
  appropriate for high-efficiency columns; an `efficiency_uncertainty` entry adds a declared systematic scaling whole
  columns.
- `dagostini-unfold --input --param [--response-model]`: unfolds the measured `data` (input also `response`,
  optional `prior` and `mc_events_per_truth_bin`) with `--param` D'Agostini iterations and returns the estimate with its
  first-order covariance: data (Poisson at the folded estimate) and response statistics (`multinomial` by default, or
  `poisson_cells`), separately and in total, with correlations. No toys, so counts up to 1e9 and generated events up to
  1e12 are accepted; on a 15 x 15 example its variances agree with toys within 10%
  (`tests/core/test_stats_unfolding_outer.py`). Choose the iterations with `unfold-scan` and `closure` first.
- `response-measured --input --method --param`: first-order propagation of a supplied measured response covariance
  (row-major reco-truth cells) or of response replicas, with every replica unfolded as a nonlinear cross-check; the
  shift of the replica mean is reported as a bias, not a covariance.
- `choose-regularization --input --method [--values --toys --seed]`: L-curve corner (a heuristic), generalized and
  exact leave-one-out cross-validation for the given data, and a toy comparison of each criterion against the best
  fixed setting.
- `nonparam-fold --input [--tau --compare-tau --prior --toys --seed]`: penalized Poisson maximum likelihood of the
  (log-parametrized) truth bins with a Laplace covariance, against Tikhonov on the same toys. `--prior` is
  `log_curvature` (exact for a power law), `log_slope`, `entropy` (toward a flat or supplied default), `curvature` or
  `none` (can be unstable). The log-curvature and log-slope priors favor falling spectra: say so and repeat with
  another prior.
- `compare-fold-priors --input --priors name:tau,... [--toys --seed]`: several priors on the same toys; strengths are
  not comparable across priors and the ranking is circular for the supplied truth.
- `choose-penalty-poisson --input [--prior --taus --toys --seed]`: Poisson-exact leave-one-bin-out cross-validation of
  the forward-fold penalty, with a toy comparison; it can favor too weak a penalty for strongly correlated neighbors.

Decision rules: run `regularized-scan` and `closure` before fixing a strength, and choose it by a stated criterion (for
example closure bias on a different truth below a stated fraction of the statistical sigma and no adjacent correlation
below a stated value), not from the scan's own minimum. A pull width above 1 or a mean pull beyond about 3 standard
errors is a trigger to add an uncertainty or change the method (`[Proposal]` thresholds). When the strength is chosen
from data, compare the criteria on toys with `choose-regularization`; the L-curve corner is often far from the best
fixed setting. Quote the response covariance as a full matrix with the data covariance when the unfolded result is
fitted, run `fold-compare` when a parameter is fitted from an unfolded spectrum, and `response-stat` when the response
comes from a finite MC sample.

## `validate_covariance.py` and `validate_response.py`

Single-command validators that never modify their input (no subcommands).

- `validate_covariance.py FILE.json [--strict] [--demo-psd-clip]`: asymmetry, negative variance, non-PSD, impossible
  correlations, zero-variance rows with covariance, near-singularity and blocks that do not add up. PSD, rank and
  conditioning are judged on the correlation matrix D^-1/2 C D^-1/2, so they do not depend on each bin's units (a
  negative eigenvalue of the correlation structure fails even when one bin's variance dominates); `metrics` reports the
  scaled and the unscaled eigenvalues. `--demo-psd-clip`
  shows the effect of eigenvalue clipping as a labeled `[Proposal]` diagnostic, never as a repair: a construction error
  is fixed at its source.
- `validate_response.py FILE.json [--strict]`: orientation, normalization against the declared convention, efficiency
  or acceptance counted twice or not at all, probability lost outside the axes, empty bins, phase-space holes, and with
  `closure` spectra the folded residuals (counts are divided by `generated_per_truth_bin`; without it the closure is
  `not_assessable`). `metadata.intended_use` sets the identifiability verdict: rank deficiency, fewer reco than truth
  bins and empty truth bins are errors for `unfolding` and when the use is undeclared (plus a warning to declare it),
  warnings for `forward_folding` and `parametric_fit`. Declare `unfolding` before an unfolding. A clean report says
  `"physical_validity": "not_assessed"`. A `response` artifact is converted to this input with
  `contracts/response_adapter.py`.

Run both before an unfolding, a forward fold or a fit that uses a supplied matrix. A column sum below one has two
readings (inefficiency, or migration outside the tabulated range); the declared metadata decides which.

## Validation tools outside `core/stats`

Each tool states its validity domain and has a test with an
independent oracle and a negative baseline; the ones marked EXPERIMENTAL are controlled examples, not general support.
Scripts are in `<plugin root>/skills/hep-statistics/scripts/` unless an adapter path is given; run `--help` first.

| Tool | Question | Oracle and negative baseline (test) |
|---|---|---|
| `result_artifact.py` | write a `statistical-result` that keeps a CLI's status | failed fit -> `failed` label; zero-exceedance bound typed (`test_result_artifact.py`) |
| `covariance_fit.py` | fits with a declared covariance: constrained spectra, C(theta) with ln det, multiplicative (Peelle) | closed forms; diagonal approximation and data-scaled covariance detected (`test_covariance_fit.py`) |
| `sweighted_fit.py` | sWeighted fits: naive, SumW2, sandwich, asymptotic, bootstrap; sPlot independence check | RooFit AsymptoticError, toys and bootstrap; broken factorization flagged invalid (`test_sweighted_fit.py`) |
| `bayes_calibration.py` | posterior quantiles vs a conjugate posterior; SBC with stated power (not PPC, not coverage) | missing Jacobian and mis-scaled posteriors fail (`test_bayes_calibration.py`); `bayes_diagnostics.py` matches ArviZ 0.23.4 (`test_bayes_arviz_oracle.py`) |
| `eft_scan.py` (EXPERIMENTAL) | quadratic (EFT-like) models: disconnected sets, joint vs profiled, toy belt | closed-form boundaries; hull never reported (`test_eft_scan.py`) |
| `discrete_profile.py` (EXPERIMENTAL) | envelope over background forms fixed in advance, reselected in every toy | truths inside and outside the family; a single form as baseline (`examples/stats-benchmarks/discrete-profile/`) |
| `global_significance.py` (EXPERIMENTAL) | global p of the complete procedure: 1D/2D scans, refitted normalization, selection variants | look_elsewhere brute force; Gross-Vitells flagged where not validated (`test_global_significance.py`) |
| `pcl_efficiency_ratio.py` (EXPERIMENTAL) | PCL with a stated power threshold; Clopper-Pearson vs Beta credible; Fieller sets | exact coverage sums; delta method fails (`test_pcl_efficiency_ratio.py`) |
| `ratio_estimation.py` (EXPERIMENTAL) | classifier likelihood ratio on a calibratable Gaussian model | exact ratio; domain shift and wrong nuisance rejected with stated power (`test_ratio_estimation.py`) |
| `adapters/pyhf-combine/assets/backend_comparison.py` | the same likelihood in core and pyhf: pointwise and profiled | 1e-15 / 1e-11; wrong interpolation code caught (`test_backend_likelihood_equivalence.py`) |
| `adapters/pyhf-combine/assets/model_card.py` | SR/CR fits from a model card: shared auxiliary measurements, contamination | closed form; omitted contamination biases by the analytic amount (`test_sr_cr_model_card.py`) |
| `examples/stats-benchmarks/published-likelihood-sbottom/` | a public full likelihood (HEPData ins1748602) against preregistered paper values | full CLs scans and bands; a fit without the control region fails |

Contract side: `contracts/validate.py --strict` and `--gate publication`, `contracts/migrate_statistical_result.py`, and
`tools/run_required_backends.py` (a required backend missing fails, never skips).

Publication-gate rules of contracts 2.6.0 (`_stat_hardening`, `_bayesian_hardening` in `contracts/validate.py`; the
gate always applies them, the validator natively from 2.6.0 or with `--strict`). Failed: a `synthetic` or `asimov`
label (`gate.not_observed_data`: a result on synthetic data is never a result on data); toy coverage whose 68.27%
Clopper-Pearson upper end, from round(coverage x n_toys) of n_toys, lies more than 0.01 below nominal; `coverage.cl`
different from `results.cl`; a recorded coverage interval the counts do not allow; a p-value of exactly 0 (record the
bound); a probability-like `results` value (p0, p_value, CLs, CLb, CLs+b, `p_...`) outside [0, 1]; z and p that
disagree by more than 0.01 one-sided (`significance.convention: "two-sided"` uses p/2); global_z above local_z; a
construction and a recognized test statistic that do not belong together (Feldman-Cousins: likelihood ratio or chi2;
CLs: q_mu, q-tilde, the LEP statistic, likelihood ratio, chi2; asymptotic and Wilks: q0, q_mu, q-tilde, likelihood
ratio, chi2; Neyman and Feldman-Cousins do not produce CLs/CLb values); a `model_sha256` that is not 64 hex digits.
Unresolved: fewer than 200 coverage toys; an observed limit without the expected median and both bands; global_z
without global_p; toys (construction, coverage, goodness of fit, significance) without `extension.seeds` or
`coverage.seed`; toy goodness of fit without `n_toys`; Bayesian: an improper prior whose propriety is not
`{argument, ref}`, a parameter of interest without a prior, bulk or tail ESS below 100 per chain, no chain count.

## Toy ensembles

`toy_ensemble.py` (helper, no CLI). A toy study states its ensemble explicitly (no default):
`conditional-fluctuated-aux` (nuisances at the conditional fit, auxiliary measurements redrawn: the profile
construction), `conditional-fixed-aux`, `unconditional-prior` (nuisances drawn from their constraints: a
prior-predictive average, not coverage at a true nuisance) or `plug-in` (nuisances at a given point, as in a
coverage study at a true point). Toy i uses a seed derived from (seed, i), so partitioned tasks merge to the single
run and `merge` refuses duplicates and gaps. Every toy has one outcome (ok, fit_failed, invalid_data, empty_data,
timeout, error); `coverage` keeps C/N, (C+F)/N and C/(N-F) with exact intervals and takes the headline from a
predeclared failure policy; `coverage_gate` passes a point when the one-sided lower bound (Bonferroni over a
grid) is at least nominal - 0.01, fails it when the upper bound is below, and otherwise reports insufficient
precision. Results of different ensembles are never pooled; there are no automatic retries.
`likelihood_limits.shape_toy_generator` and `shape_q_evaluator` connect it to the shape model (every toy refitted).
Benchmarks: `<plugin root>/examples/stats-benchmarks/` (coverage grid of the counting constructions).
