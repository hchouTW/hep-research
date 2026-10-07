# Scientific Machine Learning Reference

Reasoning about physics-informed and simulation-adjacent ML: when a physical
constraint, surrogate model, or inverse-problem method is justified and how to
validate it. This is a scientific-reasoning reference, not a physics textbook - it
does not teach what a constraint or a surrogate is, only how to decide whether to use
one and how to check it. For the statistical/inference validity of the resulting
scientific claim (likelihoods, discovery significance) see
`hep-statistics`, not this file - see the boundary note in `deep-learning-guide.md`. For
symmetry-specific architecture decisions see
[geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md).

## Before introducing a physical constraint

Do not assume more physics constraints always produce a better model - a constraint
can also remove valid solutions or bias a fit. Work through, in order:

1. What physical assumption is actually being imposed?
2. Is the assumption exact (e.g. a conservation law from an exact symmetry) or
   approximate (e.g. a simplified interaction, a mean-field approximation)?
3. What is its domain of validity, and does the data stay inside it?
4. Where should it be represented - architecture, parameterization, objective/loss,
   augmentation, preprocessing, or post-processing? (Table below.)
5. Could enforcing the constraint remove valid solutions the data actually supports?
6. What unconstrained baseline is it compared against? An architecture that "bakes in"
   physics but is never compared to a flexible unconstrained model has not shown the
   constraint helped - see
   [ablation-and-design-review.md](ablation-and-design-review.md).

| Where to encode | When it fits | Risk |
|---|---|---|
| Architecture (hard constraint) | Assumption is exact and known to hold everywhere in the data domain | Removes solutions if the assumption is only approximate |
| Objective/loss (soft constraint, penalty term) | Assumption is approximate, or exactness is uncertain | Constraint can be traded off against fit quality by the loss weight; that weight itself needs justification |
| Parameterization (e.g. predict a constrained quantity directly) | Constraint defines the output space itself | Can make optimization harder if the parameterization is ill-conditioned |
| Augmentation | Assumption is a symmetry that should hold statistically, not exactly per-sample | Weaker guarantee than architecture; effectiveness depends on augmentation coverage |
| Preprocessing / post-processing | Constraint is best enforced on inputs/outputs rather than internal representations | Can mask a model that has not actually learned the constraint internally |

## Surrogate models and emulators

A learned surrogate's speed advantage must not hide a loss of scientific validity.
Require, for any surrogate/emulator:

- **Training-domain coverage** - the parameter ranges the surrogate was actually
  trained on, stated explicitly.
- **Interpolation vs. extrapolation** - is the intended use inside or outside that
  coverage? A surrogate accurate within its training range and used outside it is an
  extrapolation-risk case by default, not an edge case - flag it and require
  validation before trusting the output.
- **Approximation error against the original simulator/model**, measured across the
  covered range, not only at a few spot-checked points.
- **Uncertainty** - does the surrogate report its own approximation uncertainty, and
  does that uncertainty grow appropriately near and beyond the training-domain edge?
  See [uncertainty-and-calibration.md](uncertainty-and-calibration.md).
- **Failure regions** - are there known sub-regions where the surrogate is known to be
  unreliable, and are they documented and checked at inference time?
- **Downstream sensitivity** - how much does surrogate error actually move the final
  scientific quantity of interest? A surrogate with large local error in a
  downstream-irrelevant direction may be fine; small error in a sensitive direction
  may not be.

## Inverse problems and simulation-based inference

For neural likelihood estimation, neural posterior estimation, and other
simulation-based-inference approaches, the network output is an estimated
density/posterior, not a ground-truth one - it inherits every concern in
[uncertainty-and-calibration.md](uncertainty-and-calibration.md) plus:

- **Coverage validation** - do stated credible/confidence intervals actually contain
  the true parameter at the claimed rate, checked via simulated ground truth
  (simulation-based calibration)? A posterior that is not coverage-checked is an
  unvalidated posterior regardless of how it was produced.
- **Simulator mismatch** - the method learns the mapping implied by the simulator used
  to train it; simulator misspecification propagates directly into the inferred
  posterior, and is the
  [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)
  simulation-to-data question applied to inference specifically.
- **Interpolation vs. extrapolation** in parameter space, the same distinction as for
  surrogates above, applied to the region of parameter space actually queried at
  inference time.

Whether the resulting interval, limit or posterior is statistically valid (ratio
calibration, closure, toy coverage, simulation-based calibration, systematics through the
network) is `hep-statistics` work: see its
[ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md).
This file covers training and the ML-side checks only.

## Deliverables

- For each physical constraint used: the six-question walkthrough above, and the
  unconstrained baseline it was compared against.
- For each surrogate/emulator: training-domain coverage, approximation error over that
  range, and whether the current use case is interpolation or extrapolation.
- For simulation-based inference: a coverage-validation result, not only point-estimate
  accuracy.
- Explicit statement of what would have to be true for the physical assumption or
  surrogate to fail, and whether that was checked.
