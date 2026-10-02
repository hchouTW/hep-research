# Uncertainty and Calibration Reference

Whether a model's confidence and predictive uncertainty can be trusted as stated - a
distinct question from whether its predictions are accurate. High priority for
scientific ML, where a probability or interval is often the actual deliverable. For
metric computation see [evaluation-metrics.md](evaluation-metrics.md); for evaluation
design see [evaluation-strategy.md](evaluation-strategy.md); for behavior under shift
see [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

This is predictive-probability calibration - a different sense of "calibration" from
the quantization calibration data used in
[efficient-finetuning.md](efficient-finetuning.md) and
[export-and-deployment.md](export-and-deployment.md).

## Confidence is not calibration

**A model's confidence score is not automatically a calibrated probability of
correctness.** A softmax value of `0.99` means the model is confident, not that it is
right 99% of the time it says so - those are only equal if the model is calibrated,
which must be measured, not assumed. Neural networks are commonly overconfident,
especially after heavy training or on inputs unlike the training distribution.

**For scientific ML specifically: improved predictive performance does not
automatically imply improved downstream scientific inference.** A classifier with
higher AUC does not necessarily produce better parameter estimates, better confidence
intervals, better discovery significance, or more reliable uncertainty - each of those
is a separate claim requiring separate validation. Do not substitute a predictive
metric for a downstream one; see the deep-learning/academic-papers boundary in
`deep-learning-guide.md`.

## Aleatoric vs. epistemic uncertainty

- **Aleatoric** - irreducible noise in the data-generating process itself. More data or
  a better model does not remove it; a well-specified model should learn to predict it
  (e.g. heteroscedastic regression), not eliminate it.
- **Epistemic** - uncertainty from limited data or model knowledge. Should shrink with
  more relevant data and should be *large* far from the training distribution - if it
  is not, the epistemic-uncertainty estimate itself is untrustworthy.

Conflating the two produces a single "uncertainty" number that cannot be acted on: a
high-aleatoric, low-epistemic prediction (genuinely noisy, well-understood) calls for a
different response than a low-aleatoric, high-epistemic one (looks confident, poorly
covered by training data).

## Measuring calibration

- **Negative log-likelihood (NLL)** - a proper scoring rule; rewards both accuracy and
  calibration jointly, so it can worsen even as accuracy improves if confidence grows
  faster than correctness.
- **Brier score** - mean squared error between predicted probability and the 0/1
  outcome; another proper scoring rule, more interpretable at a glance than NLL.
- **Expected calibration error (ECE)** bins predictions by confidence and compares
  average confidence to average accuracy per bin. Known limitations: sensitive to bin
  count/edges, can be near-zero for a model that is calibrated only in aggregate while
  badly miscalibrated within a class or slice, and says nothing about sharpness (a
  model that always predicts the base rate is "calibrated" and useless). Report a
  reliability diagram alongside the scalar, and check calibration **per slice**, not
  only in aggregate - see [evaluation-strategy.md](evaluation-strategy.md) on slices.

## Calibration and uncertainty methods

No single technique is universally correct; match the method to what is actually
needed:

- **Temperature scaling** - a single learned scalar rescaling logits post-hoc, fit on a
  held-out set. Cheap and effective for in-distribution miscalibration; does not fix
  miscalibration under distribution shift and does not change ranking/accuracy.
- **Deep ensembles** - train several models from different seeds/initializations;
  disagreement across members is an epistemic-uncertainty signal. Costs N times the
  training and inference compute; the seed variance already measured for
  [ablation-and-design-review.md](ablation-and-design-review.md) purposes is a
  by-product worth reusing here.
- **MC-dropout-style approximations** - keep dropout active at inference and sample
  multiple forward passes. Cheaper than a real ensemble, but the resulting uncertainty
  quality depends heavily on the dropout placement/rate used in training and is a
  weaker approximation than an ensemble; validate it against a held-out calibration
  check rather than assuming it works.
- **Predictive intervals** - report a range, not only a point estimate, when the
  downstream use consumes the spread (error propagation, decision thresholds).
  Validate empirical coverage (does the true value fall inside the interval at the
  stated rate?) rather than trusting the interval's construction.
- **Selective prediction / abstention** - allow the model to decline to predict below a
  confidence threshold. Only meaningful if the confidence used to gate is itself
  calibrated; an uncalibrated confidence produces an abstention policy that abstains on
  the wrong cases.

## Uncertainty under distribution shift

Calibration measured in-distribution routinely fails to hold under shift, and the
failure direction is usually overconfidence, not underconfidence - a model tends to
stay confident on inputs it has never seen. Re-measure calibration on the shifted
population itself; do not extrapolate an in-distribution ECE/reliability diagram to a
claim about shifted behavior. See
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

## Deliverables

- Which uncertainty is being reported (aleatoric, epistemic, or both, and how they were
  separated).
- Calibration metric(s) used, with their known blind spots stated, plus a reliability
  diagram.
- Per-slice calibration, not only aggregate.
- The calibration method used (if any) and what it was validated against (a held-out
  set, not the same set it was fit on).
- Whether calibration was re-checked under the shift the deployment will actually see.
- For any downstream scientific claim: the specific downstream validation performed,
  not only the predictive-metric improvement.
