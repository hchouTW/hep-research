# Scientific Machine Learning Reference

How to decide whether a physical constraint, a surrogate or an inverse-problem method is justified, and how to check
it. Statistical validity of the resulting claim: hep-statistics
([ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md)). Symmetries:
[geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md). SBI training: [sbi-training.md](sbi-training.md).

## Before introducing a physical constraint

More constraints are not automatically better: a constraint can remove valid solutions or bias a fit. Ask: what
assumption is imposed; is it exact (a conservation law from an exact symmetry) or approximate; what is its domain of
validity and does the data stay inside it; where is it encoded; could it exclude solutions the data support; and which
unconstrained baseline it is compared against ([ablation-and-design-review.md](ablation-and-design-review.md)).

| Where to encode | When it fits | Risk |
|---|---|---|
| Architecture (hard) | exact everywhere in the data domain | removes solutions if only approximate |
| Loss penalty (soft) | approximate or uncertain | the penalty weight needs a justification |
| Parameterization | the constraint defines the output space | ill-conditioned optimization |
| Augmentation | a symmetry that holds statistically | guarantee only as good as the coverage |
| Pre- or post-processing | the constraint is on inputs or outputs | can hide a model that did not learn it |

## Surrogates and emulators

State the training-domain coverage (the parameter ranges actually trained on); say whether the use is interpolation
or extrapolation (outside the coverage is an extrapolation risk by default: flag it, `scripts/check_surrogate_domain.py`,
and record the `extrapolation_policy` of the ml-artifact); measure the approximation error against the original
simulator across the covered range, not at a few points; check that the reported uncertainty grows near and beyond the
edge ([uncertainty-and-calibration.md](uncertainty-and-calibration.md)); document known failure regions and check them
at inference; and measure how much surrogate error moves the final quantity of interest.

## Inverse problems and simulation-based inference

A neural likelihood or posterior is an estimate: validate coverage with simulated ground truth (simulation-based
calibration), treat simulator misspecification as the simulation-to-data problem of inference
([robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)), and distinguish interpolation from
extrapolation in parameter space. Whether the resulting interval, limit or posterior is statistically valid (ratio
calibration, closure, toy coverage, systematics through the network) is `hep-statistics` work.

Deliver, per constraint, the walkthrough above and its unconstrained baseline; per surrogate, its coverage, error over
that range and whether the use is interpolation; for SBI, a coverage result; and what would make the assumption or the
surrogate fail, and whether it was checked.
