# RooFit and RooStats methods

How to run and check RooFit fits and RooStats calculators so that what they return can be reported. API names below
were checked against the ROOT 6.40 reference guide (root.cern/doc/v640, class pages read 2026-10-17); the local tests
ran ROOT 6.38.04, and CI runs its own ROOT. Statistical meaning (which interval, which test statistic) is in
[inference recipes](inference-recipes.md); likelihood construction and weighted fits in
[likelihood fitting](likelihood-fitting.md).

## Before trusting a fit or a workspace

Specify observable and yield ranges, extended mode, constraints, global observables, and ModelConfig. Preserve fit results and inspect status, covariance quality, EDM, invalid evaluations, and boundary hits. Check exact APIs against the installed release.

Use several reasonable initial values and scan POIs/nuisances to identify local minima. Hessian errors can be unreliable at boundaries or for nonquadratic likelihoods; supplement them with profile scans. State the method for asymmetric intervals. Optimizer bounds are not confidence intervals.

Preserve workspace data, PDFs, parameter snapshots, and name mappings, plus external payloads and versions. Ownership, scope, and automatic reuse of identically named objects can connect the wrong components; inspect the actual dependency graph.

Before using a workspace downstream, inspect: variables and their ranges, values,
errors, and constant flags; PDFs and their server dependencies; datasets and entry
counts; functions and normalization objects; and snapshots, named sets, and
categories. Confirm the expected model, data, and observable names match what the
statistical tool expects. `<plugin root>/skills/hep-computing/scripts/roofit_workspace_summary.py` prints this inventory
for a `RooWorkspace` inside a ROOT file.

## HESSE versus MINOS

- `RooFit::Hesse(true)` (the default after MIGRAD) gives the inverse of the second-derivative matrix at the minimum:
  symmetric errors, exact only for a parabolic NLL. `RooFitResult::covQual()` 3 means a full, accurate covariance;
  1 (approximate, for example `Hesse(false)`) or 2 (forced positive definite) are not good enough to report.
- `RooFit::Minos(true)`, or `Minos(RooArgSet(poi))`, scans the profile NLL for the points where it rises by the error
  definition (0.5 for an NLL): asymmetric errors (`getAsymErrorLo`, `getAsymErrorHi`) that follow a non-parabolic
  likelihood and respect parameter limits. Report MINOS for the parameter of interest when the two disagree.
- Neither is a coverage statement: near a boundary or at low counts, check with toys (below).
- `roofit_fit_check.py result` maps a saved result to a status (status 0, covQual 3, EDM below a declared threshold)
  and records `method_kind` (hesse or minos) for `result_artifact.py`.

## Pull studies with RooMCStudy

`RooMCStudy(pdf, observables, FitOptions(Save(true), ...), Silence(), [Extended()])` then `generateAndFit(ntoys,
nevents)` generates samples at the current parameter values and fits each; `fitParDataSet()` holds the fitted values,
errors and pulls (`<name>pull`), `fitResult(i)` each fit. Read the pull mean and width with their uncertainties, and
count the failed fits instead of dropping them. Pulls are N(0, 1) only when the asymptotic approximation holds and the
parameter is far from its limits; otherwise compare with the pull distribution of the toys. `roofit_fit_check.py toys`
runs this on a workspace PDF and fails when a mean or width is more than 3 of its uncertainties from 0 or 1, or a fit
failed.

## RooStats calculators

A `ModelConfig` names the PDF, the parameters of interest, the nuisance parameters, the observables and the global
observables, and carries a snapshot of the POI values; the background-only model is a clone with the POI at 0.

- `ProfileLikelihoodCalculator`: the profile-likelihood interval (`GetInterval`) and the hypothesis test
  (`GetHypoTest`); asymptotic (Wilks).
- `HypoTestInverter` with an `AsymptoticCalculator` (`SetOneSided(true)`, `SetQTilde(true)` for a POI bounded at 0)
  or a `FrequentistCalculator` (toys: `SetToys(n_sb, n_b)`, with a `ProfileLikelihoodTestStat` set one-sided through
  `GetTestStatSampler()`): `UseCLs(true)`, `SetConfidenceLevel`, `SetFixedScan` or `SetAutoScan`; the result's
  `UpperLimit()` and `GetExpectedUpperLimit(k)`. At low counts the asymptotic CLs limit can differ from the toy limit
  by ten percent or more; the toy limit is the reference there.
- `BayesianCalculator` and `MCMCCalculator`: posterior intervals. Their results are Bayesian: label them
  `paradigm: bayesian` (`result_artifact.py --paradigm bayesian`, with priors, sampler and convergence), never as a
  frequentist interval.

`roofit_fit_check.py crosscheck` builds a small multi-bin counting model (the core/stats `multibin-limit` format) in
RooFit and compares it with core/stats: the MLE, the MINOS interval against the core profile interval, the profile
scan, and the asymptotic CLs limit of RooStats against core's; with `--cls-toys` it adds the RooStats toy CLs limit.
RooFit runs MIGRAD with a tight tolerance (`RooMinimizer::setEps(1e-6)`), so the comparison tests the likelihood, not
MIGRAD's stopping rule. On a synthetic three-bin model with a 10% common background scale it agrees to 3e-7 (MLE),
3e-5 (interval), 1e-10 (scan) and 0.3% (CLs limit), with ROOT 6.38.04.

## Weighted data

Weighted fits need a declared error treatment: `SumW2Error(true)` or `AsymptoticError(true)` treat the weights as
known constants (with known, constant per-event weights the asymptotic, sandwich estimate covers and the naive inverse
Hessian does not: 300 toys of 200 events with weight 3 give 0.71 and 0.46 for the 68.27% interval of a Gaussian mean;
`tests/skills/hep_statistics/test_roofit_fit_check.py`, slow tier); sWeights need the sPlot
correction of [likelihood fitting](likelihood-fitting.md#weighted-unbinned-fits-and-sweights). `roofit_fit_check.py
weighted` refuses weighted data without `--weighted-errors`.

## Worked walkthrough: a RooFit signal + background fit (verified 2026-09-24)

Run from the skill directory with a ROOT-capable Python (e.g. Homebrew `python3.14`):

```bash
python3 <plugin root>/tests/skills/hep_computing/make_root_fixtures.py fx          # synthetic mass peak (m=91, sigma=2.5, 3000 sig) on an exponential
python3 <plugin root>/adapters/root-uproot/assets/pyroot_roofit_signal_background.py --input fx/histograms.root --hist mass_hist \
    --output fit.root --min 60 --max 120
python3 <plugin root>/skills/hep-computing/scripts/roofit_workspace_summary.py --input fit.root --workspace workspace
```

Observed on the fixture: status 0, covQual 3; mean 90.89 +- 0.06, sigma 2.43 +- 0.05,
nsig 2944 +- 67 (3000 generated), nbkg 5488 +- 84 (about 5440 expected in range).
Checks to do on a real fit, in this order: status and covQual; parameters away from their
bounds; pulls of the generated truth in a toy study before trusting the errors; and the fit
repeated with an alternative background shape, whose difference is a systematic. Weighted
histograms with known, constant per-event weights can use `SumW2Error(True)` (the template sets it). It and RooFit's
`AsymptoticError` (the sandwich estimate) both treat the weights as known constants, so neither carries the
uncertainty of sWeights or of weights estimated from the data: for those use the asymptotically correct covariance
below (Langenbruch, EPJC 82 (2022) 393), which `sweighted_fit.py` computes, or a bootstrap of the whole chain, and
check coverage either way.
