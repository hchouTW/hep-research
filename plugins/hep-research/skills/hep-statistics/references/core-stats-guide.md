# Guide to the `core/stats` diagnostics

The owner's guide to the seven scripts in `<plugin root>/core/stats/`. Each section says which question a
subcommand answers, what it assumes, what it needs and returns, when to use it instead of an alternative, and what it
does not do. Experiment profiles may record how an experiment applies these tools; the general rules live here, and
where a profile's copy differs, this guide applies.

The scripts are **diagnostics, not frameworks**: small counting, template and unfolding problems with stated
simplifications. A many-nuisance shape model, a workspace combination or a production sampler goes through the
pyhf/Combine adapter ([statistical tools](statistical-tools.md)). Run any script with `--help` for its input format.

## Contents

1. [Common conventions](#common-conventions)
2. [Choosing a tool](#choosing-a-tool)
3. [`poisson_diagnostics.py`: exact Poisson constructions](#poisson_diagnosticspy-exact-poisson-constructions)
4. [`likelihood_limits.py`: profile-likelihood constructions](#likelihood_limitspy-profile-likelihood-constructions)
5. [`statistical_toys.py`: narrow toy studies](#statistical_toyspy-narrow-toy-studies)
6. [`template_fit.py`: Barlow-Beeston template fits](#template_fitpy-barlow-beeston-template-fits)
7. [`unfolding_diagnostics.py`: regularization, closure, folding](#unfolding_diagnosticspy-regularization-closure-folding)
8. [`validate_covariance.py` and `validate_response.py`](#validate_covariancepy-and-validate_responsepy)
9. [Not implemented](#not-implemented)
10. [Failure modes](#failure-modes)

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
| `likelihood_limits.py`, `statistical_toys.py`, `unfolding_diagnostics.py` | ok | — | rejected input |
| `template_fit.py` | ok | fit `failed` (infeasible model or no convergence) | rejected input |
| `validate_covariance.py` | pass (or warnings without `--strict`) | errors (or warnings with `--strict`) | unreadable or not JSON |
| `validate_response.py` | pass (or warnings without `--strict`) | errors | unreadable or not JSON |

- **Poisson means** are limited to 1e5 in every module (`_poisson.py`, private: log-space distribution, tail and
  quantile, accurate to that limit). A limit that cannot be bracketed below it is reported `failed`, never
  clipped to the limit. `fc-interval` alone scans a grid and is limited to total means of 500.
- **Covariance and correlation matrices** go through one strict Cholesky (`_linalg.py`, private, no CLI). It works
  on the matrix scaled to a unit diagonal, so units never change the verdict. A pivot below -1e-10 is an error
  that names the matrix, a fit refuses a singular matrix, and toy sampling accepts a semi-definite one and records
  the shift in `regularization`. Nothing is repaired silently.
- A `failed` fit never feeds an inference or a `statistical-result` except one whose `fit_status` is `failed`.
- Toy tails: a tail estimate `k/N` carries its binomial Monte Carlo error; zero exceedances give a bound, not zero.

## Choosing a tool

| Question | First tool | Then, or instead |
|---|---|---|
| Limit or interval for a count with a **known** background | `poisson_diagnostics.py upper-limit`, `fc-interval`, `cls-limit` | `interval` for a mean with no background; `coverage` to check a construction |
| Same with an **uncertain** background | `likelihood_limits.py profile-limit`, `profile-cls`, `profile-fc` | compare with the marginalized `--sigma-b` result; `neyman-limit` when coverage over the nuisance matters |
| Discovery significance of a count | `likelihood_limits.py profile-significance` (uncertain b), `statistical_toys.py boundary` (known b) | ON/OFF counting: `<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py` |
| Several bins sharing one signal strength | `likelihood_limits.py multibin-limit` | `shape-limit` when shapes and several nuisances matter; the pyhf adapter beyond that |
| Finite Monte Carlo statistics in templates | `statistical_toys.py template-stat`, then `template-bb` | `template_fit.py bb-fit`/`bb-toys` for several templates, `wbb-fit`/`wbb-toys` for weighted MC and nuisances |
| Unfolding regularization, closure, response statistics | `unfolding_diagnostics.py regularized-scan`, `closure` | `choose-regularization`, `response-stat`, `response-covariance`, `fold-compare`, `nonparam-fold` |
| Ratio or fraction with correlated systematics | `statistical_toys.py ratio-measured` (measured covariance) | `ratio-cov` (declared structures), `ratio-toys` (counts with systematic nuisances) |
| Is this covariance or response matrix well formed? | `validate_covariance.py`, `validate_response.py` | — |

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
  1- and 2-sigma expected limits under background only. CLs over-covers by design; it is not a frequentist interval
  and a Feldman-Cousins interval is not a CLs limit: never label one as the other. With `--sigma-b`, vary `sigma_b`
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
  one common multiplicative background nuisance; asymptotic observed limit (CLs+b-type) and asymptotic CLs limit, expected median and 1/2-sigma limits for both
  from the Asimov data set,
  and a seeded-toy p-value at the asymptotic limit as the calibration check (it should be near `1 - cl`; if not, use a
  toy-calibrated construction). Shapes and other nuisances are not modeled.
- `shape-limit --input FILE [--cl --toys --seed]`: multi-bin limit with several nuisances: background and signal
  normalization, background and signal shape by vertical interpolation, a damped Newton profile, asymptotic observed
  and Asimov expected limits with the same asymptotic CLs limit and bands, and an optional toy p-value at the limit. A normalization nuisance may be `gaussian`
  (factor `1 + sigma theta`), `lognormal` (`exp(sigma theta)`) or `gamma` (`1 + sigma theta` with a Poisson auxiliary
  measurement of `tau = 1/sigma^2`); an optional correlation matrix correlates the Gaussian-type nuisances (gamma ones
  cannot be correlated). Choose the constraint from the origin of the uncertainty
  ([nuisance modeling](nuisance-modeling.md)), not by convenience. Slow for many nuisances.
- `neyman-limit --n --b --sigma-b [--cl --beta --points --toys --seed]`: an approximation of the Berger-Boos
  construction over the background nuisance (finite nuisance grid, seeded toys): a signal is excluded only if the
  supremum of the toy p-value over the `(1 - beta)` confidence set of the background, plus `beta`, is at most
  `1 - cl`. The output carries the toy errors, a `coverage_claim` and whether the inputs lie in the range validated by
  seeded coverage scans. Single-bin background nuisance only.
- `neyman-coverage --s --b --sigma-b [--cl --beta --outer --inner --points --seed]`: coverage at one true point of the
  plug-in profile construction against the supremum construction. Outside the validated range, run it at the true
  values that matter before relying on `neyman-limit`; a single point is not global coverage.

Decision rule: with an uncertain background prefer `profile-limit`, `profile-significance` or `multibin-limit` to a
marginalized result, and compare the two: a difference is itself a systematic on the method. A profile limit is not a
CLs limit (no CLs protection). Always report the expected sensitivity next to an observed limit. Near a boundary
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
Poisson data, no systematics. `--method` is `dagostini` (iterations; nonlinear, spread from toys), `tikhonov`
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
  counts; spread from data, from the response and from both, and the response share of the variance.
- `response-covariance --input --method --param [--response-model --toys --seed]`: the finite-response effect
  propagated analytically at first order (numerical Jacobian of the estimator, also for D'Agostini) as a full
  covariance among truth bins, cross-checked against toys. `--response-model multinomial` uses the exact multinomial
  covariance with a lost-event class (`Var R_ij = R_ij (1 - R_ij) / gen_j`, `Cov(R_ij, R_kj) = -R_ij R_kj / gen_j`),
  appropriate for high-efficiency columns; an `efficiency_uncertainty` entry adds a declared systematic scaling whole
  columns.
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
  correlations, zero-variance rows with covariance, near-singularity and blocks that do not add up. `--demo-psd-clip`
  shows the effect of eigenvalue clipping as a labeled `[Proposal]` diagnostic, never as a repair: a construction error
  is fixed at its source.
- `validate_response.py FILE.json [--strict]`: orientation, normalization against the declared convention, efficiency
  or acceptance counted twice or not at all, probability lost outside the axes, empty bins, phase-space holes, and with
  `closure` spectra the folded residuals. A clean report says `"physical_validity": "not_assessed"`.

Run both before an unfolding, a forward fold or a fit that uses a supplied matrix. A column sum below one has two
readings (inefficiency, or migration outside the tabulated range); the declared metadata decides which.

## Not implemented

Weights that vary within a bin in the toy MC; non-Gaussian or correlated priors in the template fit; a Berger-Boos
construction for several nuisances or for the multi-bin or shape model; bin-to-bin correlated shape nuisances;
correlated gamma nuisances; Poisson-exact cross-validation for the linear estimators and K-fold variants;
forward-folding priors learned from data or with free hyperparameters; efficiency uncertainties that depend on the
unfolded spectrum; a measured covariance of anything other than the response cells. Each would be a framework, not a
diagnostic. Post-fit nuisance impacts, look-elsewhere corrections, expected sensitivity, goodness of fit and Bayesian
convergence live outside `core/stats` (see the SKILL.md resources).

## Failure modes

- Quoting the classical limit when it is zero or negative; reading a Feldman-Cousins lower bound of 0 as a failure or
  as evidence for zero signal; quoting a CLs limit without its expected band or as a frequentist interval.
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
