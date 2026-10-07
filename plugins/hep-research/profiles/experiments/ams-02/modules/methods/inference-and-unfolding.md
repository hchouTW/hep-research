# Inference, Unfolding, and Forward Folding

> Method owner: [hep-statistics](../../../../../skills/hep-statistics/SKILL.md) defines the general method (likelihoods, covariance validation, unfolding, forward folding and low-count inference); implementation in `core/stats`. This module records how AMS-02 analyses apply it. Where a general statement here differs from the owner, the owner's text applies.

> Canonical generic guide to the `core/stats` tools: [core/stats guide](../../../../../skills/hep-statistics/references/core-stats-guide.md).

## When to read this file

If this session has not read them yet, read the profile's [working rules](../working-rules.md) first.

Read when writing or reviewing a likelihood, a response/migration model, an unfolding, a forward-folded fit, an interval or limit, a covariance matrix, or a significance. Canonical home for the count/response model, covariance types, unfolding validation, and rare-event inference. Efficiency and background definitions are in [efficiency-acceptance-backgrounds](efficiency-acceptance-backgrounds.md).

## Contents

1. [Count and response model](#count-and-response-model)
2. [Likelihood](#likelihood)
3. [Covariance requirements](#covariance-requirements)
4. [Method selection](#method-selection)
5. [Unfolding](#unfolding)
6. [Forward folding](#forward-folding)
7. [Template likelihood](#template-likelihood)
8. [Intervals, limits, significance](#intervals-limits-significance)
9. [Rare and low-count inference](#rare-and-low-count-inference)
10. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Count and response model

Symbolic; all quantities are inputs the user must supply or that a source must give.

`μ_i(θ, η) = Σ_j R_ij(η) · A_j(η) · T_j(η) · Φ_j(θ) · Δx_j + Σ_k b_ik(η)`

- `i` reconstructed bin; `j` true bin; `k` background component.
- `Φ_j(θ)` true-bin flux (or a model with parameters `θ`), integrated or differential per the convention below; `Δx_j` true bin width (rigidity or energy).
- `A_j` effective acceptance (m² sr) for the true bin; `T_j` exposure time factor including livetime and geomagnetic transmission (s). If exposure is already a single number `E_j = A_j T_j`, do not multiply again.
- `R_ij(η)` migration probability from true bin `j` to reconstructed bin `i`. **State orientation and normalization:** columns (true bins, including any stored under/overflow) sum to one when `R` is conditional on the selected sample and the inefficiency lives in `A_j` (`conditional_on_selected` in `<plugin root>/core/stats/validate_response.py`), or to the efficiency (at most one) when the inefficiency lives inside `R` (`includes_efficiency`). Do not put inefficiency in both. **A column sum below one has two legitimate readings:** inefficiency (true events not reconstructed in the selected sample), or migration of true events into reconstructed bins outside the tabulated range (under/overflow not stored in `R`); the reverse also holds, since feed-in from outside the true range shows up in row totals. Run `<plugin root>/core/stats/validate_response.py` on the supplied matrix (and `<plugin root>/core/stats/validate_covariance.py` for the covariance) before diagnosing. Do not diagnose a sum of, say, 0.85 as inefficiency alone: check whether the matrix stores under/overflow rows, and state which reading the declared metadata implies.
- `b_ik(η)` expected background counts in reconstructed bin `i` from component `k` (from the background ledger), possibly with their own response.
- `η` nuisance parameters (acceptance, efficiency, scale, template shape, background normalization); `θ` parameters of interest.
- **Double-counting check.** For each factor list where it is applied (acceptance, response, exposure, calibration) and confirm each is applied once. Under/overflow, feed-in from outside the true range, and species/charge migration (e.g. `e+`↔`e-`, `p`↔`p̄`) are explicit rows/columns of `R`.

## Likelihood

`L(θ, η) = Π_i Poisson(n_i | μ_i(θ, η)) × Π_a C_a(η_a)`

where `n_i` are observed counts and `C_a` are **auxiliary measurements** (control-region counts, calibration measurements, template statistics), not arbitrary priors, unless the analysis is explicitly Bayesian. Extensions: simultaneous control regions (each with its own Poisson factor sharing `η`); per-bin template statistical nuisances; correlated multivariate Gaussian or log-normal constraints for systematic sets. Do not use the same events in the signal region and in a control region as independent information; do not use a constraint derived from the data being fitted.

**Conventions.** Weighted MC: count effective entries; do not treat weighted sums as Poisson data. Data are unweighted counts. If data were corrected by weights (e.g. prescale), the Poisson assumption changes and the likelihood must reflect it.

## Covariance requirements

Distinguish and carry separately:

1. **Statistical covariance** from data counts or fitted yields.
2. **MC/template statistical covariance** (finite-template uncertainty).
3. **Systematic covariance** from coherent variations (shifts of one nuisance affecting many bins).
4. **Unfolding-induced bin correlations.**
5. **Cross-species, cross-time, and numerator-denominator covariance.**

For any published or used covariance matrix record: bin ordering, units, absolute vs relative, whether components are additive, and check positive-semidefiniteness and unexpected singularities (a singular matrix may mean an over-regularized unfolding or an implicit constraint). Never report only per-bin percentage uncertainties while ignoring their correlations; never combine unknown correlations quadratically. For a ratio use the covariance of numerator and denominator (see [charged-cosmic-rays](../species/charged-cosmic-rays.md#ratio-or-fraction-blueprint)).

### Non-positive-semidefinite covariance: diagnosis and repair

1. Symmetrize `(C + Cᵀ)/2` and compute eigenvalues; compare the most negative to the largest. Round-off level (about machine precision times the largest) is numerical; anything larger is a construction error.
2. Numerical only: clip negative eigenvalues (or take the nearest PSD matrix), record the change, and confirm the fit or χ² result is unchanged within tolerance.
3. Construction error: do not clip. Check mixed conventions (absolute vs relative, bin ordering, units), rounded or guessed correlation tables, subtracted terms with an implausible correlation, components added twice, and unfolding-induced anticorrelation from an under-regularized inversion. Rebuild from coherent variations so each block is PSD by construction, and propagate through the full unfolding with toys (the sample covariance of the toys is PSD).
4. Never repair by dropping correlations or by quadrature-combining components whose correlations are unknown.
5. `<plugin root>/core/stats/validate_covariance.py` performs the diagnosis in step 1 and can show the effect of a clip as a labeled [Proposal] without changing the matrix (see [analysis-artifacts](analysis-artifacts.md#checker-scripts)).

## Method selection

The choice depends on the **estimand**, not on preference. No universal winner.

| Estimand | Typical choice | Reason | Caution |
|---|---|---|---|
| Model-independent spectrum for publication | Unfolding (iterative Bayesian, matrix/SVD, or regularized likelihood) with full covariance | Result is comparable across models | Prior/regularization dependence, bin correlations |
| Model parameters (index, break, cutoff) | Forward-folded likelihood fit | Uses raw counts, no regularization bias | Depends on parametrization; not a spectrum |
| Ratio or fraction | Forward-folded or unfolded with joint covariance | Preserves correlations | Cancellation must be demonstrated |
| Limit on a rare signal | Forward-folded counting/binned likelihood, constructed interval | Low counts, boundary | Not asymptotics unless validated |
| Small migration, wide bins | Bin-by-bin correction only after showing negligible migration | Simple | Purity is not a migration study |

**Diagonal-response estimator** `Φ_i = N_i / (Δx_i T_i A_i ε_i)` is valid only when off-diagonal migration is negligible for the analysis' precision and steepness; a steep spectrum with finite resolution has appreciable migration even when the resolution core looks small (upward migration of abundant low-`R` events into higher bins dominates). Test with the response matrix before adopting it.

## Unfolding

**Define first:** truth and reconstructed bins (edges, and how truth variable relates to reconstructed: rigidity vs energy, `|R|` vs signed `R`); response orientation and normalization; inefficiency treatment; feed-in from outside the range; under/overflow; species/charge migration.

**Methods** (compare, do not rank): iterative Bayesian (D'Agostini), matrix inversion/SVD or Tikhonov-regularized (e.g. TUnfold), regularized likelihood or full forward-folded fits. Each has a bias-variance parameter: iteration count, regularization strength, or number of singular values.

**Required validation, at minimum:**
1. Nominal MC closure (unfold the reconstructed MC of the same sample, recover truth).
2. Reweighted-spectrum closure (change the true spectrum; recover it).
3. Deliberately distorted-spectrum stress tests (features, kinks not in the prior).
4. Response perturbation tests (vary resolution, tails, scale).
5. Coverage/pull tests across pseudo-experiments (Poisson-fluctuated data, fluctuated response).
6. Stability versus binning and boundaries.
7. Bias versus variance as a function of iterations/regularization.
8. Propagation of statistical and systematic covariance (toys through the full unfolding, not only linear error propagation).

**Choosing iteration count/regularization.** Declare the criterion in advance and determine it without optimizing on the final unfolded spectrum: for example, minimize total expected error (bias²+variance) on an ensemble of MC pseudo-data that includes the stress-test spectra; document the chosen value and its sensitivity. Prior/reweighting studies are mandatory: unfold with different priors and quote the spread as a systematic. **Purity is not a substitute for migration studies.** An iteration count or regularization strength copied from another analysis has no meaning outside the response, prior, bins, and statistics it was tuned for.

**Documented AMS practice.** Published AMS flux analyses (S06, S08) use an iterative unfolding whose iteration stops when the fluxes of two successive steps agree within 0.1% (claim C23), i.e. a declared convergence criterion, together with MC closure-type validation and independent analyses by separate groups; bin widths are chosen relative to the resolution (S04). Details of validation beyond the main article are in the Supplemental Material (not read).

**Circularity.** The response matrix shape depends on the assumed true spectrum within each truth bin; iterate or reweight to the unfolded result and check convergence, then verify closure was not achieved trivially.

## Forward folding

Map a truth-level model through acceptance, efficiency, and response into reconstructed space and compare to observed counts: `μ_i(θ, η)` above. Advantages: low statistics, strong migration, model comparison, natural inclusion of nuisance parameters. Costs: results are conditional on the parametrization (a smooth power-law with break cannot represent unmodeled features); the fit gives parameters not a model-free spectrum; goodness of fit tests the family. Use when the estimand is a model parameter, ratio of models, or limit; use unfolding when a model-independent spectrum is required, and consider publishing both response and data so that others can forward-fold.

## Template likelihood

Define discriminant bins, component yields, normalized vs unnormalized shapes, finite-template treatment, degeneracy/shape-interpolation/empty-bin/smoothing/control-sample reweighting checks (details in [efficiency-acceptance-backgrounds](efficiency-acceptance-backgrounds.md#template-fits)). If a classifier defines the discriminant: independent training sample, input-variable audit, overtraining test, domain-shift validation, stability vs kinematics and time. Report convergence, pulls and constraints, correlations of fit parameters, goodness of fit, coverage/calibration, and robustness to alternate templates.

## Intervals, limits, significance

- Distinguish **profile likelihood** intervals, **Bayesian** credible intervals (state prior), **frequentist confidence** intervals, and **upper limits**. State the construction and its operating properties.
- Limits: state one-sided vs two-sided, confidence level, test statistic, expected sensitivity and bands, nuisance treatment (profiling vs marginalization vs hybrid), and whether CLs-type modification is used and why (CLs is a conservative convention, not a confidence-level statement).
- **Significance.** Distinguish local and global; account for the predefined search range and trial factor (look-elsewhere) for searches across energies, rigidities or time windows (Gross-Vitells trial factors).
- Boundary parameters (signal strength ≥ 0, count ≥ 0): asymptotic formulae (Cowan et al.) apply only under validated regularity conditions; check with toys. For a one-sided test with the null on the boundary the asymptotic null distribution is a half-point-mass-at-zero plus half-χ²₁ mixture, not χ²₁, and only when the regularity conditions hold.
- Non-regular problems: a parameter such as a spectral-break position is not identifiable under the no-break hypothesis, so Wilks does not apply to the break significance; use toys and a trial factor over the predefined range.
- When AMS-specific inputs are unavailable, give a **symbolic likelihood** with labeled assumptions rather than invented counts, priors or widths.

## Rare and low-count inference

- Do not automatically use `S/√B`, Wilks' theorem, or Gaussian errors when counts are small, nuisance constraints are weak, or parameters lie on boundaries.
- For zero or few observed events with known background `b`, the Poisson upper limit is exact: for `n_obs = 0`, `b = 0`, the one-sided 95% CL upper limit on signal counts is `-ln(0.05) ≈ 3.00` (Poisson with a flat-prior or classical construction; general method). For `n_obs = 0` and known `b > 0` the classical limit is `-ln(0.05) - b` (it shrinks with `b` and can reach zero or go negative), while the CLs limit is the `b`-independent `-ln(0.05)`; the two are different constructions, so do not present `-ln α` as the classical limit for any `b`. With nonzero background or nuisance constraints use a stated construction (Feldman-Cousins, CLs, profile-likelihood with toys) and check coverage.
- **Acceptance and exposure convert counts to flux limits**: `Φ_UL = N_UL / (E · Δx)` with `E` the exposure (m² sr s) and the uncertainty in `E` (including possible correlations with the background model) propagated as a nuisance.
- Weighted MC, finite-template statistics, overdispersion (extra variance beyond Poisson from unmodeled detector effects), identifiability: explicit checks.
- Reporting: separate candidates (events passing all criteria), excess (statistical deviation), evidence, and discovery, with the significance threshold declared in advance; see [antimatter-and-leptons](../species/antimatter-and-leptons.md#rare-antimatter-blueprint) for the reporting policy.

## Failure modes

- Response inefficiency counted in both `R` and `A`.
- Diagonal estimator under strong migration (spectral bias, especially in steep regions).
- Unfolding iteration count optimized on the unfolded result; no prior variation; covariance dropped.
- Non-PSD covariance or bin correlations ignored in a fit of the unfolded spectrum.
- Asymptotic p-values near a boundary with few counts; trial factor omitted.
- Templates treated as exact; nuisances constrained by the fitted data themselves.
- Publishing per-bin percentage errors as if independent.

## Required source classes

Tier 4: Cowan-Cranmer-Gross-Vitells (asymptotics), Feldman-Cousins, Read/Junk (CLs), Barlow-Beeston and Conway (templates), D'Agostini and Schmitt (unfolding), Gross-Vitells (trial factors); the `hep-analysis` inference and unfolding references for general methodology. AMS-specific statements about how a result was unfolded or how its uncertainties were combined need Tier 1 sources.

## Questions to ask the user

What is the estimand (spectrum, ratio, fraction, parameter, limit)? Reconstructed and true variables and bins? Do you have a response matrix and its orientation/normalization? Expected counts per bin (low-count regime)? Which systematics are correlated across bins/species/time? Is the range predefined (trial factor)?
