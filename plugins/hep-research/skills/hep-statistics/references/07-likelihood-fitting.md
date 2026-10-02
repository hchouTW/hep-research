# Likelihood Construction and Fitting

## Binned likelihoods

A common model is `L(mu,theta)=product_cb Pois(n_cb | nu_cb(mu,theta)) × L_aux(a | theta)`, where c denotes nonoverlapping channels and b bins. Expected counts combine processes and modifiers; interference or EFT models need not reduce to `mu*s+b`.

Auxiliary likelihood terms describe control measurements. In a frequentist treatment they should not simply be called Bayesian priors. A Bayesian analysis additionally specifies priors and avoids reusing the same information. List observables, global observables, POIs, nuisance parameters, fixed parameters, units, and bounds.

## Unbinned and extended likelihoods

A normalized shape-only likelihood omits total-rate information. To estimate rates, use an extended likelihood such as `exp(-nu)*nu^N/N! × product_i f(x_i)`, with appropriate mixtures/intensities for multiple processes. Normalize consistently over the fit range, especially for sidebands, disjoint ranges, and restricted mass windows.

A covariance correction for weighted unbinned fits does not automatically guarantee coverage. Signed weights and sWeights need suitable methods. Do not treat background-subtracted observations as independent pure-signal Poisson data.

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
python3 ${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_computing/hep_analysis_make_root_fixtures.py fx          # synthetic mass peak (m=91, sigma=2.5, 3000 sig) on an exponential
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
