# Uncertainty and Calibration Reference

Whether a model's confidence and predictive uncertainty can be trusted as stated, a question separate from accuracy.
Metrics: [evaluation-metrics.md](evaluation-metrics.md); behaviour under shift:
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md). (Predictive calibration, not the
quantization calibration of [efficient-finetuning.md](efficient-finetuning.md).)

## Confidence is not calibration

A softmax of 0.99 means the model is confident, not that it is right 99% of the time; networks are commonly
overconfident, most of all far from the training data. Better predictive performance does not imply better
downstream inference (estimates, intervals, significance): each is a separate claim.

**Aleatoric** uncertainty (irreducible noise; a well-specified model predicts it, for example a heteroscedastic
regression) and **epistemic** uncertainty (limited data or knowledge; it must grow far from the training data, or the
estimate is untrustworthy) call for different responses; do not merge them into one number.

## Measuring calibration

NLL and the Brier score are proper scoring rules. ECE bins predictions by confidence and compares with the observed
rate: it depends on the binning, can hide miscalibration within a class or slice, says nothing about sharpness (always
predicting the base rate is "calibrated"), and has a finite-sample floor (`assets/calibration.py` reports it). Report a
reliability diagram with the scalar, per slice. With event weights, compute all of them weighted.

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
- **Platt scaling** - a logistic fit sigmoid(a·logit + b) on the held-out sample; unlike
  temperature scaling it also fits an offset, so it can absorb a class-prior shift.
  `assets/calibration.py --method platt` (Platt's original reference is `unverified`
  here: not opened).
- **Isotonic regression** - a monotone, non-parametric map (pool-adjacent-violators);
  needs more calibration data than a one- or two-parameter fit and is the most
  optimistic when judged on its fit sample. `assets/calibration.py --method isotonic`
  (it refuses negative weights unless cells are merged).
- **Prior correction** - a classifier trained under one class ratio estimates p(s|x)
  under that ratio; `f_phys = r·f / (r·f + 1 − f)` maps it to the physics ratio
  ([ml-analysis.md](ml-analysis.md), "Class balancing and the prior";
  `assets/hep_metrics.py undo_prior_shift`, `calibration.py --prior-ratio-change`).
  Temperature scaling cannot do this.
- **Conformal prediction** - wraps any trained model in prediction sets that contain the
  true outcome at a chosen rate without distributional assumptions, given exchangeable
  calibration and test samples (Angelopoulos & Bates, arXiv:2107.07511, abstract, read
  2026-10-14). The guarantee is marginal and breaks under the data/simulation shift a
  physics deployment usually has; check exchangeability first.
- **Selective prediction / abstention** - allow the model to decline to predict below a
  confidence threshold. Only meaningful if the confidence used to gate is itself
  calibrated; an uncalibrated confidence produces an abstention policy that abstains on
  the wrong cases.

## When an ML uncertainty is a measurement systematic

- **A frozen score used as an observable** (a cut or a template variable) needs no
  ensemble or seed nuisance: any fixed function of the inputs is a valid observable, and
  the analysis calibrates the distribution of the score in data and simulation (its
  systematics are those of the inputs, propagated through the fixed function). Seed or
  ensemble spread measures how optimal the selection is, not a bias of the result.
- **A learned quantity used inside the likelihood** (a density ratio, a likelihood ratio,
  a posterior, a surrogate prediction) is part of the model: its training uncertainty
  (ensemble spread, finite training statistics, calibration residual) biases the result
  and must enter as a nuisance or a coverage-checked correction. Hand the treatment to
  hep-statistics ([ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md)).
- **A regressed correction** (energy, momentum) carries its non-closure and the in-situ
  data/simulation scale and resolution difference as systematics
  ([multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md), "Regression targets").

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
