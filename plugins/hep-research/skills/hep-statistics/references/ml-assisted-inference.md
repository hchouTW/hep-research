# ML-Assisted Inference: Validity and Handoff

What has to be shown before a machine-learned quantity enters a likelihood, a test, an interval or a posterior. Training, architecture, data loading and model calibration in the ML sense belong to `physics-ml` (see [scientific-machine-learning.md](../../physics-ml/references/scientific-machine-learning.md) and [uncertainty-and-calibration.md](../../physics-ml/references/uncertainty-and-calibration.md)); this file covers the inferential validity of the scientific claim built on the trained model.

## Classifier or regressor outputs as observables

A network output used as a fit observable (a discriminant histogram, a regressed mass) is valid by construction: the likelihood is still built from templates of that observable, so any monotonic or non-optimal mapping only costs sensitivity, not correctness. The conditions are:

- **One frozen model.** Data, nominal templates and every systematic variation are evaluated through the same frozen network, with the same preprocessing. Retraining for a variation is a different observable.
- **No training/evaluation overlap.** Events used to train or select the model are not used to build templates or to fit; otherwise the templates are biased towards the training sample. Record the split and its grouping (the project-level split check treats a split without group metadata as incomplete).
- **Systematics through the network.** Systematic variations are propagated by re-evaluating varied inputs through the network, not by assuming the output is insensitive to them. A network can be sensitive to mismodeled features that a cut-based analysis ignores; check data/simulation agreement of the output in control regions.
- **Optimization metrics are not validation.** AUC or loss show separation, not correctness; the contract validator rejects AUC-only downstream validation.

## Neural likelihood ratios and NSBI

When a network estimates a likelihood ratio or density ratio directly (neural simulation-based inference, NSBI), the estimate itself enters the test statistic, so its errors bias the result rather than only costing sensitivity.

- **Calibration of the estimated ratio.** A classifier trained to separate samples at two parameter points approximates a monotonic function of the ratio; calibrating the classifier output (for example by histogramming it under each hypothesis) recovers the ratio (Cranmer, Pavez, Louppe, arXiv:1506.02169, preprint). Show the calibration, not only the classifier.
- **Closure on known-ratio benchmarks.** Before data, apply the full chain to a toy or simplified problem whose ratio is known analytically, and to samples generated at parameter points held out from training; compare the estimated and true ratios and the resulting likelihood scans.
- **Nuisance parameters.** Either parameterize the network in the nuisance parameters (trained over their range) or build the nuisance dependence from per-variation ratio estimates with an interpolation scheme; state which, the ranges covered, and what happens outside them.
- **Coverage of the final intervals.** Run toy experiments from known parameter values (including nuisance-parameter shifts) through the complete pipeline and report the coverage of the quoted intervals. An asymptotic distribution for the test statistic is an assumption to check, not a given, when the ratio is estimated.
- **Ensembles and estimator variance.** Retrain with different seeds or data subsets; the spread of the result is an uncertainty of the method and must be either propagated or shown negligible.

<!-- example: NSBI validation in a published analysis -->
An example of the validation a full NSBI analysis documents is the ATLAS implementation note (ATLAS Collaboration, Rep. Prog. Phys. 88 (2025) 067801, arXiv:2412.01600): calibration of the density-ratio estimates, closure tests, nuisance-parameter treatment, ensembles, and coverage studies with pseudo-experiments.
<!-- /example -->

## Simulation-based posteriors

For neural posterior or likelihood estimation used in a Bayesian analysis:

- **Simulation-based calibration (SBC).** Draw parameters from the prior, simulate, compute the posterior rank of the true value; ranks must be uniform (Talts et al., arXiv:1804.06788, preprint). Non-uniform ranks reveal over- or under-dispersed or biased posteriors.
- **Coverage across the prior.** Report coverage as a function of the parameter, not only averaged over the prior; averaging can hide regions where intervals fail.
- **Simulator mismatch.** SBC tests the estimator against the simulator, not the simulator against nature. Simulator misspecification is a physics-ml and analysis question (`physics-ml` robustness and distribution-shift guidance); here it must appear as a systematic or an explicit limitation.
- **MCMC on a learned likelihood** still needs the convergence diagnostics in [inference-recipes.md](inference-recipes.md) (R-hat, ESS).

## Deliverables checklist

- Which ML artifact enters inference (version, frozen weights, preprocessing) and in what role: observable, ratio estimator, or posterior estimator.
- Training domain: parameter and feature ranges, and the train/evaluation split with its grouping.
- Calibration evidence: ratio calibration or classifier calibration under each hypothesis.
- Closure evidence: known-ratio benchmarks and held-out parameter points.
- Coverage evidence: toys through the full pipeline (frequentist) or SBC and coverage across the prior (Bayesian).
- Systematics propagation through the network, and the method-variance (ensemble) uncertainty.
- Status labels on the `statistical-result`: a result without coverage evidence stays `unvalidated` or `preliminary`, never `validated-in-scope`.
