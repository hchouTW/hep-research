# Combining measurements

How to combine measurements of one quantity (or one binned observable) from several analyses or experiments, and when
not to. The executable steps are `<plugin root>/contracts/comparison/combination.py` (`plan_combination`: may these
inputs be combined at all) and `<plugin root>/skills/hep-statistics/scripts/combine_measurements.py` (generalized least
squares once the plan accepts them; a worked SYNTHETIC input is `assets/combine.example.json`); asymmetric
uncertainties go through `combine_asymmetric.py`.

## Before any combination

- In a protected project (`agent_policy` in the project config) `plan_combination`, the comparison gate and
  `combine_measurements.py` first check the revocation and qualification inputs and refuse (exit 3, `"status":
  "refused"`) when they cannot be established or an input is revoked. A combination meant for publication is formal
  use, which needs a formal-use permit the plugin cannot check yet; passing the checks authorizes nothing.
- The inputs measure the same thing: the comparison gate passes pairwise with no transformation (same quantity, units,
  binning, phase space, level, normalization, conventions). `plan_combination` refuses otherwise, and refuses a
  dataset entered twice (`combine.duplicate_id`).
- Every cross-dataset correlation is stated with evidence or a scoped assumption, including independence. A shared
  auxiliary measurement (luminosity, a calibration, a background model) is declared once; two likelihoods are never
  multiplied as if independent when they share one.
- A missing covariance stays missing: no diagonal is assumed. Non-Gaussian uncertainty objects (scale envelopes, model
  alternatives) never enter a Gaussian covariance.

## BLUE and generalized least squares

The best linear unbiased estimate (Lyons, Gibaut and Clifford, NIM A270 (1988) 110) is the weighted mean with weights
`w = C^-1 1 / (1^T C^-1 1)` for one quantity; for several quantities measured by several inputs it is the generalized
least-squares solution `x = (H^T C^-1 H)^-1 H^T C^-1 y` (Valassi, NIM A500 (2003) 391), which is what
`combine_measurements.py` solves with the full joint covariance C (cross blocks included).

- **Negative weights.** For two measurements with sigma_1 < sigma_2 and correlation rho, the weight of the less precise
  one is negative when rho > sigma_1 / sigma_2. That is not an error of the method but a sign of a high-correlation
  regime: the combined value can lie outside the range of the inputs, and the result becomes very sensitive to the
  assumed correlation. Valassi and Chierici (EPJC 74 (2014) 2717, arXiv:1307.4003) show that in this regime assuming
  full correlation of a systematic is not conservative; vary the uncertain correlations and report the spread.
- **chi2 of the combination.** Report it with its degrees of freedom (inputs minus fitted quantities); a poor chi2 is
  a tension between the inputs, not something to absorb by scaling errors without saying so.

## Multiplicative uncertainties: Peelle's pertinent puzzle

When a common normalization uncertainty is a fraction of each measured value, building the covariance from the
measured values (`C_ij = s^2 y_i y_j`) biases the GLS average low, sometimes below every input (D'Agostini, NIM A346
(1994) 306). Use the covariance at the fitted value, or fit the normalization as an explicit nuisance with its
constraint; `covariance_fit.py` implements the three modes and measures their bias (`multiplicative.mode`:
"data" is biased, "nuisance" is the recommended form for a common normalization).

## Likelihood-level combination

When the full likelihoods are available (published statistical models: Cranmer et al., arXiv:2109.04981), a joint
likelihood with shared parameters for the common nuisances is better than combining point estimates, above all with
non-Gaussian uncertainties, physical boundaries or low counts. Shared nuisances need one parameter and one constraint
term (the model card rule in `contracts/validate.py`); correlated but different nuisances need a stated correlation
model. pyhf and Combine workspaces are combined through the adapters (`<plugin root>/adapters/pyhf-combine/`).

## What to report

The combined value with its uncertainty and its breakdown (with the method of the breakdown), the weights (BLUE) or
the joint likelihood used, every correlation assumed and how it was varied, the chi2 and its degrees of freedom, and
the inputs' status labels (a combination of synthetic or preliminary inputs keeps that label).
