# Likelihood Construction and Fitting

## Binned likelihoods

A common model is `L(mu,theta)=product_cb Pois(n_cb | nu_cb(mu,theta)) × L_aux(a | theta)`, where c denotes nonoverlapping channels and b bins. Expected counts combine processes and modifiers; interference or EFT models need not reduce to `mu*s+b`.

Auxiliary likelihood terms describe control measurements. In a frequentist treatment they should not simply be called Bayesian priors. A Bayesian analysis additionally specifies priors and avoids reusing the same information. List observables, global observables, POIs, nuisance parameters, fixed parameters, units, and bounds.

## Unbinned and extended likelihoods

A normalized shape-only likelihood omits total-rate information. To estimate rates, use an extended likelihood such as `exp(-nu)*nu^N/N! × product_i f(x_i)`, with appropriate mixtures/intensities for multiple processes. Normalize consistently over the fit range, especially for sidebands, disjoint ranges, and restricted mass windows.

A covariance correction for weighted unbinned fits does not automatically guarantee coverage. Signed weights and sWeights need suitable methods. Do not treat background-subtracted observations as independent pure-signal Poisson data.

## Weighted unbinned fits and sWeights

**sPlot** (Pivk & Le Diberder, NIM A 555 (2005) 356). A fit of the yields in a discriminating variable (e.g. a mass) gives per-event sWeights that project out one component in a control variable (e.g. a decay time). The method assumes that, within each component, the control variable is statistically independent of the discriminating variable, and that the discriminating model (shapes and component list) is correct. sWeights can be negative; never clip or drop them. The weights are themselves estimated from the data, so their uncertainty belongs in the covariance of anything fitted with them.

**Weighted unbinned maximum likelihood** (Langenbruch, EPJC 82 (2022) 393). The inverse Hessian of the weighted log-likelihood is not a covariance: it treats `sum w` as the event count. The "sum w²" sandwich `H^-1 (sum w² g g^T) H^-1` corrects for the weights but treats them as known constants. For sWeights the asymptotically correct covariance stacks the estimating equations of the yields, of the weights' normalization and of the fitted parameters, and propagates all of them (a joint M-estimator sandwich). Even the correct covariance is asymptotic: check coverage with toys.

**COWs** (custom orthogonal weight functions; Dembinski, Kenzie, Langenbruch, Schmelling, NIM A 1040 (2022) 167270) generalize sWeights and are the tool when the independence assumption fails or the discriminating model has to be relaxed; they still need their own covariance treatment.

**Signed generator weights** (e.g. from NLO generators) in an unbinned fit: use the weighted likelihood with a sandwich covariance and a toy coverage check; a negative per-event density contribution can make the likelihood ill-defined, so check that the weighted model density stays positive where events lie.

**Background subtraction** (sideband or sWeight subtraction) does not produce Poisson-distributed pure-signal data; do not fit the subtracted counts as if it did.

### Verified walkthrough: sWeighted lifetime fit (verified 2026-10-03)

`tests/skills/hep_statistics/test_weighted_unbinned_fit.py` (SYNTHETIC, seed 20261003, 300 toys): a Gaussian mass peak (mean 0.5, width 0.05) with Poisson(1000) signal events on a flat background with Poisson(2000) events in m in [0, 1]; signal decay times exponential with tau = 1, background with tau = 3. Per toy, an extended fit of the two yields in m, sWeights, and the weighted fit of the signal lifetime. Pull widths of the lifetime:

| Covariance | Pull width |
|---|---|
| (a) inverse weighted Hessian | 2.799 |
| sum w² sandwich, weights treated as known | 1.013 |
| (b) full sandwich including the yield fit | 1.020 |

The mean fitted lifetime is 0.997. Only (b) is asserted (width in [0.9, 1.1]); (a) underestimates the uncertainty by almost a factor of three. The sum w² result is close here but is not guaranteed to be in general.

When the background decay time depends on the mass (tau_b = 1 + 4|m - 0.5|, so the independence assumption fails), the same procedure gives a mean lifetime of 0.575 instead of 1, a mean pull of -8.189 with the correct covariance: a correct covariance does not repair a violated assumption. Test the independence assumption (for example, compare control-variable distributions in mass slices of a background-dominated region) and use COWs or a full two-dimensional model when it fails.

## Identifiability

Check degeneracies before fitting: indistinguishable signal/background shapes, unconstrained CR normalizations, free per-bin backgrounds absorbing signal, or simultaneous freedom in rate and efficiency. Resolve these with justified information or constraints, not arbitrary tightening to make optimization succeed.

## RooFit/RooStats checks

Specify observable and yield ranges, extended mode, constraints, global observables, and ModelConfig. Preserve fit results and inspect status, covariance quality, EDM, invalid evaluations, and boundary hits. Check exact APIs against the installed release.

Use several reasonable initial values and scan POIs/nuisances to identify local minima. Hessian errors can be unreliable at boundaries or for nonquadratic likelihoods; supplement them with profile scans. State the method for asymmetric intervals. Optimizer bounds are not confidence intervals.

Preserve workspace data, PDFs, parameter snapshots, and name mappings, plus external payloads and versions. Ownership, scope, and automatic reuse of identically named objects can connect the wrong components; inspect the actual dependency graph.

Before using a workspace downstream, inspect: variables and their ranges, values,
errors, and constant flags; PDFs and their server dependencies; datasets and entry
counts; functions and normalization objects; and snapshots, named sets, and
categories. Confirm the expected model, data, and observable names match what the
statistical tool expects. `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/roofit_workspace_summary.py` prints this inventory
for a `RooWorkspace` inside a ROOT file.

## Diagnostics

Provide pre/postfit yields, residuals, estimates, correlations, and pulls/constraints. Define a pull convention, such as a shift divided by the prefit standard deviation, and acknowledge when non-Gaussian constraints make that scale inappropriate.

Use goodness-of-fit statistics consistent with the data model. Sparse counts do not automatically justify Gaussian per-bin chi-square tests. Treat zero-count terms in saturated deviance through their limits. Fitted parameters, boundaries, and nuisances affect the reference distribution; use refitted toys when needed. A good goodness-of-fit value does not establish absence of bias; perform closure or injection tests.

## Worked walkthrough: a RooFit signal + background fit (verified 2026-09-24)

Run from the skill directory with a ROOT-capable Python (e.g. Homebrew `python3.14`):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_computing/make_root_fixtures.py fx          # synthetic mass peak (m=91, sigma=2.5, 3000 sig) on an exponential
python3 ${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/pyroot_roofit_signal_background.py --input fx/histograms.root --hist mass_hist \
    --output fit.root --min 60 --max 120
python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/roofit_workspace_summary.py --input fit.root --workspace workspace
```

Observed on the fixture: status 0, covQual 3; mean 90.89 +- 0.06, sigma 2.43 +- 0.05,
nsig 2944 +- 67 (3000 generated), nbkg 5488 +- 84 (about 5440 expected in range).
Checks to do on a real fit, in this order: status and covQual; parameters away from their
bounds; pulls of the generated truth in a toy study before trusting the errors; and the fit
repeated with an alternative background shape, whose difference is a systematic. Weighted
histograms need `SumW2Error(True)` (the template sets it) or an explicit coverage check.
