# Statistical Inference, Significance, and Limits

## Define the question

State the POI, null and alternative hypotheses, one- or two-sided convention, confidence level, nuisance treatment, and data type. A p-value is a probability of results at least as incompatible under a hypothesis, not the probability that the hypothesis is true. For a one-sided Gaussian equivalent, use `Z=Phi_inverse(1-p)` without mixing two-sided conventions.

## Profile likelihood

Define `lambda(mu)=L(mu,theta_hat_hat_mu)/L(mu_hat,theta_hat)`. The usual two-sided statistic is `-2 log lambda`. For discovery q0, treatment of negative fitted strength must match the fitting convention. Upper-limit q_mu is commonly zero when the fitted strength exceeds the tested value. Physical lower bounds require the corresponding bounded statistic; do not mix q_mu and q-tilde formulas or reference distributions.

Wilks/Wald/Asimov approximations have regularity requirements. Sparse bins, weak identifiability, boundaries, discrete models, and strongly nonlinear nuisances may require toy calibration or other checks. A fixed rule such as five entries per bin does not guarantee validity. See the [original Cowan et al. paper](https://arxiv.org/abs/1007.1727).

Measured example (synthetic ratio of two Poisson yields with known leakage backgrounds, nuisance profiled; from a
synthetic-twin study outside the plugin, with no script, seed or test shipped here, so a note rather than a
reproducible result): the interval `-2 log lambda <= 1` covered 0.57 to 0.79 instead of 0.683 for a few to about 50
events per bin. A Neyman construction with the threshold calibrated by toys at each tested value (nuisance at its
profiled value, common random numbers across the scan) restored 0.67-0.71 (nested toys, about ±0.03). Measure
coverage before quoting a Wilks interval at such counts, and put every background that scales with a fitted yield (for
example a species leaking into the other selection of a ratio) inside the likelihood, not as a fixed subtraction.

**Wald approximation and the Asimov width.** For large samples `-2 ln lambda(mu) = (mu - mu_hat)^2 / sigma^2 + O(1/sqrt N)`
(Cowan et al., arXiv:1007.1727, eq. 17), and the width `sigma` is read off the Asimov data set generated at `mu'`:
`sigma_A^2 = (mu - mu')^2 / q_mu,A` with `q_mu,A = -2 ln lambda_A(mu)` (eq. 30). With nuisances the Asimov set uses
the nuisances at their values under `mu'` (profiled on the data for an observed-data Asimov set, or at the nominal
values for a pre-data expectation); state which, because the expected bands differ.

**Profile likelihood with nuisances at low counts.** Rolke, Lopez and Conrad (NIM A551 (2005) 493,
physics/0403059) give profile-likelihood intervals for a Poisson signal with a background (and efficiency) measured in
auxiliary samples and show their coverage is close to nominal over a wide range; it is still a property to check with
toys at the counts in hand (the measured example above shows how far Wilks can be off).

**Cousins-Highland.** Integrating a background or efficiency uncertainty over a prior inside an otherwise frequentist
limit (Cousins and Highland, NIM A320 (1992) 331) is a hybrid: its coverage is not guaranteed, it depends on the prior
chosen for the nuisance, and it is not the same as profiling. `poisson_diagnostics.py --sigma-b` implements it; label
it as such and compare with `likelihood_limits.py` (profiled) when the result matters.

## CLs and upper limits

Fix a convention in which larger q_mu is less compatible with the tested strength. Define `p_mu=P(q_mu>=q_obs | mu)` and `p_b_tail=P(q_mu>=q_obs | 0)`. A common convention is then `CLs=p_mu/p_b_tail`. Sources defining p_b through the opposite tail write the denominator as `1-p_b`. Verify a backend's definition instead of inferring it from the symbol alone.

For example, exclusion may use CLs<0.05. CLs is a modified exclusion criterion, not a posterior probability or a generic exact Neyman interval. Expected median and one-/two-standard-deviation bands describe background-only expected results or a specified asymptotic construction, not the standard error of an observed limit.

**Power-constrained limits.** PCL (Cowan, Cranmer, Gross and Vitells, arXiv:1105.3166) reports the unconstrained
(CLs+b-type) limit but never below a power threshold, the expected limit at a stated quantile (often the -1 sigma
expected) of the background-only distribution; it avoids excluding signals the experiment is not sensitive to without
the over-coverage of CLs. State the threshold; `pcl_efficiency_ratio.py pcl` computes it for a counting experiment.

The scan must bracket the threshold crossing. If it does not, report that the limit lies outside the scanned range rather than returning an endpoint. Investigate failed fits and model behavior for nonmonotonic curves; report multiple intervals when appropriate.

## Toys, coverage, and trials

Record seeds, toy counts, generating parameters, auxiliary-observation fluctuations, nuisance generation strategy, and refitting rules. Fixed truth values, plug-in nuisances, and nuisance draws define different procedures and are not interchangeable.

For a tail estimate k/N, report Monte Carlo uncertainty. Zero exceedances do not establish p=0; use a binomial bound. Small toy ensembles cannot directly calibrate five-sigma tails. Coverage studies repeat the full procedure at multiple POI/nuisance truth points and report coverage, failure rates, and failure handling. Dropping failed fits can bias results.

Searching across masses, channels, or cuts creates a look-elsewhere effect. Obtain a global p-value from the full search procedure or a validated approximation; a single-point local p-value is not global. `<plugin root>/skills/hep-statistics/scripts/global_significance.py` repeats the whole procedure (1D or 2D scan, refitted background normalization, choice among nested selections) in every toy. Toy studies record their ensemble, partition seeds and every failure (`core/stats/toy_ensemble.py`); coverage reports C/N, (C+F)/N and C/(N-F) under a failure policy fixed in advance.

## Look-elsewhere: global significance of a scan

A scan over a signal position reports its largest local excess; the probability of an excess at least that large
*anywhere* in the scan is the global p-value. Report both, with the method and the trials factor (global p over local
p). `<plugin root>/skills/hep-statistics/scripts/look_elsewhere.py` (needs NumPy) does this for a binned,
exactly known background and a 1D family of signal templates (one-sided `q0`, asymptotic local p):

- `local`: `q0`, local p and Z at every scan point and the maximum. Never the final answer for a scan.
- `brute --toys N --seed S`: background-only toys, maximize `q0` over the scan in each, count toys reaching the
  observed maximum. Exact for the model up to Monte Carlo error; cost grows as 1/p, so it cannot reach 5 sigma.
- `gross-vitells --toys N --seed S [--ref-level C0]`: count the mean number of upcrossings `<N(c0)>` of a low level
  `c0` in a few hundred toys and extrapolate,
  `p_global ~= p_local(c) + <N(c0)> exp(-(c - c0)/2)` for one degree of freedom
  ([Gross & Vitells 2010](https://doi.org/10.1140/epjc/s10052-010-1470-8), eq. 3, an upper bound at every `c`
  that they expect to become an equality for large `c`). The output gives `c0`, the toy count, the extrapolation
  distance `c - c0` and the highest level the same toys checked empirically; beyond that level it warns.
- One scan point: no correction, global = local. The global p is never reported below the local p; zero toy
  exceedances give a 95% binomial bound, not zero.
- Not modeled: a background uncertainty or a background fitted in the scan, several scan dimensions, or signal
  widths that vary with the position beyond the templates you supply; for those, toys of the full procedure.

Verified on a synthetic scan (2026-10-03; 50 bins of background 50, Gaussian signal of width 3 scanned over 46
positions; `tests/skills/hep_statistics/test_look_elsewhere.py`, `HEP_SLOW_TESTS=1`): with `c0 = 1` (1,000 toys,
`<N(c0)> = 1.96`) the Gross-Vitells global p is 0.110, 0.0337, 0.0111, 0.00289 and 0.00127 where 20,000 brute
toys give 0.1, 0.03, 0.01, 0.003 and 0.001: within 20% or three Monte Carlo standard errors at each level. The
agreement holds for this configuration; check a new one the same way at a level the brute toys can reach.

The astroparticle bound `1 - (1 - p_local)^N_eff` ([astroparticle statistics](astroparticle-statistics.md)) needs an
effective number of independent trials, which the upcrossing count replaces when the scan is correlated.

## Expected sensitivity

Quote the expected sensitivity with every observed result, computed before unblinding.

- **Discovery, counting:** the median significance under signal plus background is the Asimov value
  `Z_A = sqrt(2((s+b) ln(1 + s/b) - s))` ([Cowan et al. 2011](https://arxiv.org/abs/1007.1727), eq. 97 in the arXiv
  numbering; erratum EPJC 73 (2013) 2501). For `s = 5`, `b = 20`, `Z_A = 1.0757`.
- **With a background uncertainty:** when the background is constrained by a Poisson auxiliary measurement
  `m ~ Pois(tau b)` with `tau = b/sigma_b^2`, use
  `Z_A = sqrt(2[(s+b) ln((s+b)(b+sigma_b^2)/(b^2+(s+b)sigma_b^2)) - (b^2/sigma_b^2) ln(1 + sigma_b^2 s/(b(b+sigma_b^2)))])`
  (G. Cowan, "Discovery sensitivity for a counting experiment with background uncertainty", unpublished note,
  2012, eq. 20). For `s = 5`, `b = 20`, `sigma_b = 2` it gives 0.9755; a numerical profile of `q0` on the Asimov data
  of that model gives the same to 1e-6. It does not hold for a Gaussian constraint or a background from simulation
  with an unrelated uncertainty.
- `s/sqrt(b)` (and `s/sqrt(b + sigma_b^2)`) is the `s << b` limit of these formulas (expand ln(1 + s/b) for small
  s/b; Cowan et al., arXiv:1007.1727 eq. 98 for `s/sqrt(b)`; the `sigma_b` form is the same limit of the 2012 note's
  formula). Never quote it without saying so; at small `b` it overstates the sensitivity.
- **Limits:** the median expected limit and its 1- and 2-sigma bands under background only come from
  `core/stats/poisson_diagnostics.py cls-limit` (known background), `likelihood_limits.py profile-cls` or
  `multibin-limit` (asymptotic: median and 1- and 2-sigma bands), or pyhf with `return_expected_set=True` ([pyhf and Combine](statistical-tools.md)).

`<plugin root>/skills/hep-statistics/scripts/sensitivity_and_gof.py asimov-z --s S --b B [--sigma-b SB]`
computes both forms (checked in `tests/skills/hep_statistics/test_sensitivity_and_gof.py`).

**On/off and ratio-of-Poisson-means significance.** For a signal region count against a background measured in a
control region (ratio of exposures tau), the frequentist test conditional on the total count (a binomial test of the
ratio of Poisson means, the Z_Bi of the HEP literature) is recommended over the Bayesian-frequentist hybrid, which can
undercover severely at high Z (Cousins, Linnemann and Tucker, NIM A595 (2008) 480, physics/0702156); for very low
counts the conditional test can over-cover severely because of discreteness (same paper).
`li_ma_significance.py --exact-conditional` gives that conditional p-value; Li-Ma's formula is its large-count limit.

## Goodness of fit

- For Poisson bins use the saturated-model deviance `D = 2 sum(nu - n + n ln(n/nu))`, with each zero-count term
  replaced by its limit `2 nu`. Its chi-square reference with `bins - fitted parameters` degrees of freedom is
  asymptotic; with fitted parameters, boundaries and small counts calibrate it with toys drawn from the fitted model,
  **refitting each toy**.
- That deviance is the Poisson likelihood-ratio chi-square of Baker and Cousins (NIM 221 (1984) 437): for fits to
  histograms it is the statistic to minimize and to use for goodness of fit: it gives the maximum-likelihood
  estimates, whereas minimizing Pearson's or Neyman's chi-square biases the fitted normalization at small counts. Its
  estimates can still be biased when counts are small (Baker and Cousins say so too).
- Pearson `sum (n - nu)^2/nu` and Neyman `sum (n - nu)^2/n` chi-square need large expectations in every bin (state
  the condition, for example every `nu >= 5`); Neyman's is undefined at `n = 0`.
- A good GoF p-value says the model is not rejected by this statistic; it says nothing about bias in the parameter of
  interest. Bias needs closure and injection tests.
- `sensitivity_and_gof.py gof --input FILE --toys N --seed S` fits nonnegative template yields, reports the deviance,
  its toy p-value with Monte Carlo error, the asymptotic reference labeled as such, and Pearson/Neyman only when the
  stated condition holds. Calibration check (synthetic, 20 bins, 200 background + 60 signal, 2026-10-03): over 300
  datasets from the true model, each calibrated with 200 refitted toys, the p-values pass a KS test for uniformity at
  alpha = 0.01 (`HEP_SLOW_TESTS=1`; KS p = 0.71); fitting the same data with the background shape alone gives a median
  p-value below 0.05 over 40 datasets (no toy reached the observed deviance in most of them).

## Model comparison

- **Nested models** (the null is the alternative with parameters fixed): the likelihood ratio, with Wilks' chi-square
  reference only when its conditions hold. A parameter on the boundary under the null gives a half-chi-square mixture;
  a parameter that exists only under the alternative (a signal position when the yield is zero) breaks Wilks entirely
  and leads to the look-elsewhere treatment above.
- **Non-nested models** (two background functions, two generators): no chi-square reference. Use toys under each
  hypothesis for the distribution of the log-likelihood ratio, and report both tail probabilities.
- **AIC and BIC** are heuristics for ranking models by fit quality and complexity, not tests. AIC assumes the
  regularity conditions behind its asymptotic derivation; BIC approximates a Bayes factor under specific
  unit-information priors. Neither gives a p-value or a probability that a model is true.
- **Bayes factors** depend on the priors of the parameters that differ between the models, even when the posteriors
  do not: widening a prior on a parameter present only in the larger model drives the factor towards the smaller one
  (Bartlett's effect, [Bartlett 1957](https://doi.org/10.1093/biomet/44.3-4.533); see [Cousins 2017](https://arxiv.org/abs/1310.3791), Synthese 194 (2017) 395; Lindley's paradox, [Lindley 1957](https://doi.org/10.1093/biomet/44.1-2.187), is the related conflict between a small p-value and a Bayes factor favoring the null). Report the priors and a prior
  sensitivity study with any Bayes factor (Bayesian section below).

## Bayesian inference

Specify priors and parameterization, and check posterior propriety. A flat prior in signal strength is not flat in its logarithm. For MCMC inspect multiple chains, R-hat, effective sample size, divergences, mixing, and tail sampling. State whether intervals are central or highest-posterior-density and assess prior sensitivity.

- **Priors.** Reference and Jeffreys priors are conventions (invariance or information arguments), not "no
  information"; they depend on the model (a reference prior also on which parameter is of interest), are invariant
  under reparametrization (of the parameter of interest, for a reference prior), can be improper, and a Jeffreys prior
  for a Poisson mean differs from a flat one. An improper prior needs a proof that the posterior is proper.
- **Reference priors in HEP.** Demortier, Jain and Prosper (PRD 82 (2010) 034002, arXiv:1002.1111) construct
  reference priors (parametrization-invariant, by reference analysis) for cross-section measurements with nuisance
  parameters; they are a defensible default when a prior must be stated, still a convention, and the posterior
  sensitivity to the prior is reported as for any other choice.
- **Marginalization vs profiling.** A Bayesian result integrates nuisances over their priors; a frequentist profile
  maximizes over them. They agree for near-Gaussian likelihoods and can differ at boundaries or with skewed
  constraints; do not mix them in one result, and label which one was done.
- **Wording.** A credible interval is a statement about the posterior; a confidence interval about the coverage of a
  procedure. Do not call one the other ([inference reasoning](statistical-inference-for-physics.md)).
- **Bayes factors** depend on the priors of the parameters not shared by the models (Bartlett's
  effect, [Bartlett 1957](https://doi.org/10.1093/biomet/44.3-4.533); see [Cousins 2017](https://arxiv.org/abs/1310.3791), Synthese 194 (2017) 395); report a prior-sensitivity study with any Bayes factor.

### Convergence and prior-sensitivity checks

`<plugin root>/skills/hep-statistics/scripts/bayes_diagnostics.py` (needs NumPy) works on chains you supply:

- `diagnose --input CHAINS`: rank-normalized split-R-hat (bulk and folded), bulk and tail ESS and the Monte Carlo
  standard error of quantiles ([Vehtari et al. 2021](https://doi.org/10.1214/20-BA1221)). `converged` needs R-hat
  below 1.01 and bulk and tail ESS of at least 100 per chain; fewer than 2 chains or 50 draws per chain is
  `incomplete` (exit 3), and fewer than 4 chains is flagged. Seeded checks
  (`tests/skills/hep_statistics/test_bayes_diagnostics.py`): four independent normal chains give R-hat below 1.01;
  two chains offset by one standard deviation from the other two give R-hat above 1.1; an AR(1) chain with
  `rho = 0.9` (4 x 5,000 draws) gives a bulk ESS within 15% of `N(1 - rho)/(1 + rho)`.
- `reweight --input DRAWS`: importance-reweight draws to another prior and report the quantile shifts and the
  weight ESS. Below 10% of the draws, or when the new prior has support the old one lacked, the answer is a rerun
  with the new prior, not a reweighting.
- `demo-sampler`: a seeded random-walk Metropolis sampler for `n ~ Pois(s + b)` with a flat prior, a demonstration
  and test oracle only. For `n = 0`, `b = 0` (4 x 20,000 draws, seed 11) its 95% upper bound is 2.957 +- 0.059
  against the exact `-ln 0.05 = 2.995732` of `counting_reference.py` (hep-measurement); with `--artifact` it writes a
  `statistical-result` that validates, and the validator refuses the same artifact if it claims `converged` with an
  R-hat above 1.01 (`stats.convergence_mismatch`).

No production sampler is shipped: run one (Stan, PyMC, emcee or a framework's own) and feed its chains to
`diagnose`.

## Extrapolating a background tail

A background that is only known in a control region (CR) and must be carried into a signal region (SR) further along
a falling tail (a mass, an energy, a score) is an extrapolation, not a measurement: the shape outside the CR is an
assumption, and the uncertainty has two parts that must stay apart.

1. **Fit the CR with more than one model family.** An exponential, a power law, their sum, or a declared model of
   your own. Fit binned Poisson likelihoods over the CR bins; the statistical uncertainty of each SR prediction comes
   from the fit covariance.
2. **Validate before you extrapolate.** Cut a validation region (VR) from the CR at the edge facing the SR, refit
   without it, predict the VR and compare with its observed count (a Poisson p-value with the prediction's
   uncertainty folded in). A model that fails is not used; if the nominal model fails, there is no background
   estimate. The VR test only has power against deviations the VR can show: a model that passes may still fail
   further out.
3. **Report the envelope between models separately.** The spread of the central SR predictions over the models that
   passed is a model uncertainty. With only one passing model the spread is zero by construction, not a measured
   model uncertainty; `tail_extrapolation.py` then reports `low = high` (and `gaussian_sigma = 0` under a
   prescription) with a warning that names the model: state that the model uncertainty was not assessed. The spread
   is not a Gaussian standard deviation; it becomes one only through a prescription the analysis declares and owns
   (half-range, or a uniform distribution over the range), and the choice is stated with the result.
4. **State the extrapolation distance.** Declare how far beyond the CR the prediction may reach; beyond it, the result
   carries a warning.
5. **Hand over.** The nominal SR prediction and its statistical sigma (and, with a declared prescription, the envelope
   sigma) go to `<plugin root>/core/stats/poisson_diagnostics.py cls-limit` or `likelihood_limits.py profile-cls`;
   these are not interchangeable (with `--sigma-b`, `cls-limit` is the Cousins-Highland hybrid above, `profile-cls`
   profiles the background), so name the one used. The envelope is stated next to the limit.

Run: `<plugin root>/skills/hep-statistics/scripts/tail_extrapolation.py --input tail.json` (input format in its
`--help`; a user model only with `--allow-plugin`). Its tests check that the envelope interval covers a known
exponential tail at least at the declared rate, and that a wrong model is rejected by the VR test with the power its
Asimov fit predicts.

## Minimal cross-check

`<plugin root>/skills/hep-measurement/scripts/counting_reference.py` assumes nonnegative signal, exactly known background, and a flat prior in signal yield. Its credible bound is not expected to match CLs with background uncertainty. With zero observations and zero background, its 95% upper bound is `-log(0.05)≈2.995732`; this is a reference for that specific model.
