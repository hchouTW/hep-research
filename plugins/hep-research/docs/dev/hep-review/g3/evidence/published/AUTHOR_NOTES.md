# Author notes

All samples are synthetic. The public method is deliberately reproduced before any correction; O-compute is supported even in C01. C03 is nonidentifiable from supplied inputs. C04 has a separate coverage gap in the review plan: neither O-stat nor O-compute requires a pre-use consistency test. The brief's reference to 16 oracles is interpreted as 20, consistently with its instance table.

A correction set is indexed by the order of the defects in each gold file. Gold corrected_values always refer to the jointly corrected model, whereas the oracle separately checks each one-defect intervention. Shared downstream quantities couple the defects; most upstream steps remain unchanged. No external literature, data, or dependency is used.

- `g7cd4ff2a`: endpoint; C02. Correct control.
- `g3dd81149`: logposterior; C01. A prior flat in theta transforms to exp(z) dz; the Gaussian posterior in z therefore has mean log_observation+log_sigma^2, not log_observation. Equal-tail lognormal endpoints do not give the shortest interval in theta; its endpoints must have equal posterior density in theta.
- `g192291b8`: resonance; C01. The ten-cell midpoint ratio does not resolve the narrow peak and biases the efficiency; a converged quadrature changes the reported cross section. The transformation of a density specified with respect to dm requires the Jacobian 1/(2*sqrt(t)); canceling a common cell width does not cancel this varying factor.
- `g91002406`: coverage; C01. Equal weighting of the two conditional regime coverages conflicts with the supplied population mixture probabilities. Dropping failed interval fits from the denominator estimates coverage conditional on success rather than the declared unconditional coverage.
- `g4d2a7736`: exposure; C03. The positive exposure normalization from the external run-accounting ledger.
- `g814f15fa`: odds; C02. Correct control.
- `g19d6b014`: fieller; C02. Correct control.
- `g9fc0e784`: truncation; C01. The inverse selected-sample mean ignores the parameter-dependent normalization of the doubly truncated exponential likelihood. The extrapolation probability omits the upper gate; the selected probability is exp(-lambda*low)-exp(-lambda*high).
- `gb04b4e76`: permutation; C02. Correct control.
- `geac9572a`: response; C01. Midpoint sampling replaces the required uniform-within-bin response integral, missing the localized efficiency structure. The arithmetic trigger mean is substituted for the distinct trigger probability of each interval before correcting the interval yields.
- `g62cf1e30`: deadtime; C01. The exponential correction does not invert the specified nonparalyzable mean relation; inversion gives r/(1-r*dead_time). The incident-rate standard error omits the derivative of the nonlinear rate inversion with respect to recorded rate.
- `ga50ce70b`: pileup; C01. At finite occupancy, one minus the empty-crossing probability is a crossing probability rather than a Poisson mean; the thinned mean is -log(empty_fraction). The tag-conditional vertex efficiency is substituted for the stated unbiased per-interaction thinning probability.
- `g9fdace66`: mixture; C02. Correct control.
- `g6bcd18f0`: branching; C01. The charged-parent candidate sample is normalized with the neutral-pair production fraction instead of the charged fraction. A reconstruction efficiency conditional on the visible daughter mode cannot replace its branching probability when extracting the inclusive parent branching probability.
- `gf8f4e811`: poisson_channels; C04. REQ-2 is not examined by the two-question review plan.
- `g48ebe90a`: clusters; C01. Equal averaging of interval rates is not the stated maximum-likelihood common rate; the Poisson parent likelihood gives total hits divided by total duration. The two hits from one parent are fully clustered, so the plug-in variance of a hit count is twice its count, not its count.
- `gb22f6deb`: scan; C01. The calibration uses only the observed winning window in each null record, whereas the declared statistic is the maximum across all four windows. Discarding records with failed optional refinements conditions the null ensemble on a diagnostic correlated with the already valid score vectors.
- `ga2467e91`: luminosity; C01. Multiplying recorded luminosity by the live fraction applies a correction already contained in the recorded exposure a second time. Dividing a charge-summed yield by two converts it to a single-charge cross section despite the explicitly charge-summed target.
- `g87a93b02`: difference; C03. The paired Gaussian correlation coefficient from the external joint-calibration record.
- `g3b5d0b40`: heteroscedastic; C01. The parameter-dependent Gaussian normalizations contribute sum log(variance) to minus twice log likelihood; minimizing residual terms alone shifts the stated MLE. The frozen-variance inverse weight sum omits derivatives of the parameter-dependent variance and is not the stated observed-information curvature.
