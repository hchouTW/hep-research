# Background Estimation and Control Data

## Simultaneous control-region models

Use shared process normalization parameters to link CRs and SRs. Model detector, theory, and MC-statistical uncertainties in transfer factors by source. A CR is not exact truth: retain its observation model, other backgrounds, and possible signal contamination. If its observations already enter the joint likelihood, do not add an independent Gaussian estimate derived from the same data.

## ABCD

Fix region definitions first. For example, A=(x pass,y pass), B=(pass,fail), C=(fail,pass), and D=(fail,fail), with A the target. Under background independence and appropriate contamination treatment, `A≈BC/D`. Test correlation in independent validation data or simulation; introduce `kappa=AD/(BC)` and its uncertainty/correlations when justified.

A small or zero D invalidates simple ratio propagation. Use a joint four-region likelihood or another justified model; do not replace D by one. Background-subtracted estimates can be negative and are not Poisson counts. Prefer explicit component modeling where possible. Do not tune closure uncertainties to force agreement with the observed SR.

## Fake factors and matrix methods

Define loose/tight, prompt/fake, measurement/application regions, sample purity, and parameterization. If f is the probability for a loose fake object to pass tight selection, the corresponding failing sample often receives `f/(1-f)`. Multiple-object cases require correct inclusion–exclusion, not arbitrary products that double count events.

Validate prompt subtraction, composition, kinematic dependence, and extrapolation. Extreme weights near f=1 require investigation of method stability rather than an unexplained cap. Nearly equal efficiencies can make matrix-method inversion unstable; report conditioning and identifiability limitations.

## Sidebands and data-driven shapes

Exclude or model signal leakage and specify fit ranges and extrapolation to the SR. Assess bias and spurious signal with independent samples and alternative models. Selecting the best chi-square alone is insufficient. Discrete functional-form uncertainty needs a coherent treatment, not an arbitrary extra rate error.

Propagate covariance and finite control-sample statistics after subtraction, smoothing, or reweighting. If the same control data train a reweighter and test closure, split samples or use cross-fitting.

## Deliverables

Provide region definitions, contamination estimates, transfer factors/kappa, closure plots and uncertainties, correlation choices, and an inventory of how each dataset enters the joint likelihood. Distinguish validation of normalization, shape, and extrapolation.
