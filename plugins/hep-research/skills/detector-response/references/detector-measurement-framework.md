# Detector Measurement Framework: Forward Model, Inverse Problem, and the Chain

The organizing frame for the detector references
(the system references from [detector systems overview](detector-systems-overview.md) to
[calibration and alignment](calibration-and-alignment.md), and the technique references from
[signal formation and readout](signal-formation-and-readout.md) to [case studies and checklists](detector-case-studies-and-checklists.md)).
Use it on any detector, including one not covered by name: answer the fourteen
questions below, and the detector-specific vocabulary follows. It assumes no
experiment; numbers here are orders of magnitude or definitions, never a quoted
performance.

## The chain

```
particle & interaction -> detector response -> signal formation & transport
 -> electronics & raw data -> calibration & alignment -> local reconstruction
 -> pattern recognition & object reconstruction -> PID & detector fusion
 -> performance measurement -> data/MC validation -> systematic uncertainties
 -> physics-observable bias
```

Each arrow is a separate model with its own parameters, failure modes, and validation
sample. A defect is diagnosed by asking at which arrow it first becomes visible, and
its physics impact is found by pushing it through every later arrow (see
[data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md)).

The two lower arrows are not one-way: validation and performance measurements feed back
into calibration and reconstruction, which is why circularity (tuning on the observable
being measured) is a named failure mode.

## Forward model and inverse problem

Treat a measurement as a probabilistic inverse problem:

```
y = f(x; theta) + epsilon        p(y | x, theta)        p(x | y, theta)
```

- `x`: latent particle/event properties (momentum, charge, species, vertex, energy,
  direction, arrival time). Never observed directly.
- `y`: recorded observables (ADC counts, TDC values, waveforms, binary hits,
  time-over-threshold, images, trigger primitives).
- `theta`: nuisance parameters - geometry, alignment, magnetic/electric field,
  material, gains, pedestals, timing offsets, drift velocity, refractive index,
  temperature, pressure, high voltage, aging.
- `epsilon`: stochastic fluctuation and noise. `p(y | x, theta)` is the *likelihood*
  (forward, simulable); `p(x | y, theta)` is the *posterior* (what reconstruction
  approximates). Bayes: `p(x|y,theta) ∝ p(y|x,theta) p(x)`.

Relations in this framework are labeled throughout the package as **exact**,
**approximate**, **asymptotic**, **empirical**, or **detector-specific**; `y = f + eps`
with additive Gaussian `eps` is an approximation, and Poisson, Landau-like, and
heavy-tailed noise violate it routinely.

### What the inverse problem needs to be identifiable

An estimate of `x` from `y` is only as good as the answer to four questions:

1. **Identifiability.** Does `p(y|x,theta)` differ for different `x`? A single 1D strip
   measurement does not identify a 2D position; a threshold counter does not identify
   velocity above threshold. Where two `x` give the same `y`, the problem is
   *degenerate* and the estimate depends entirely on a prior or on other detectors.
2. **Assumed `theta`.** Reconstruction runs with a *best estimate* `theta_hat`.
   The error `theta - theta_hat` is not noise; it is a shared, correlated,
   possibly time-dependent bias (a systematic), not averaged away by more events.
3. **Priors and regularization.** Track seeding, vertex constraints, clustering
   thresholds, and ML classifiers embed a prior `p(x)`. Its influence is largest
   exactly where the data are least informative (low occupancy edges, high
   momentum, forward regions).
4. **Model mismatch.** If the true `p(y|x)` is not in the fitted family (non-Gaussian
   tails, unmodeled crosstalk), the estimator is biased and its quoted covariance is
   wrong even when the fit `chi^2/ndf` looks fine.

### Separating the sources of spread

| Source | Nature | Averages away with more events? | Example |
|---|---|---|---|
| Physical fluctuation | Stochastic, irreducible for a given detector | Yes (per event no) | Landau tail, shower sampling fluctuations, photostatistics |
| Electronic noise | Stochastic, correctable in mean, reducible by design | Yes | Pedestal noise, ENC |
| Calibration error | Systematic, shared across channels/time | No | Gain scale, `t0`, drift velocity |
| Alignment / field / material error | Systematic, geometry-correlated | No | Weak modes, field map |
| Reconstruction prior / algorithm | Systematic, phase-space dependent | No | Seeding bias, clustering threshold |
| Model mismatch | Systematic | No | Simulation missing a physics process |

A "resolution" in a plot usually blends the first two and hides the rest; a
"systematic uncertainty" is the leftover freedom in the last four.

## Bias, variance, resolution, efficiency, robustness, calibration

- **Response** `R = <x_reco>/x_true` at fixed truth (a property of the detector plus
  algorithm). **Calibration** is the *procedure* that maps response toward 1; response
  is what the detector does, calibration is what analysts do about it. Do not use one
  word for both.
- **Bias / scale**: central offset of the estimator distribution. **Resolution**:
  width of that distribution. They are independent; a scale error shifts a peak, a
  resolution error broadens it, and unfolding/regularization of the final spectrum is a
  third, separate width ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **Efficiency**: probability of a conditional success. **Robustness**: how little
  the above degrade when `theta` or `p(x)` shifts. A method optimized on simulation can
  be optimal and fragile.
- **Calibrated uncertainty**: the quoted `sigma` covers the truth at its stated
  probability. Narrow is not calibrated ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).

## Thresholds turn continuous shifts into efficiency

A discriminator, zero-suppression cut, or trigger threshold `T` on a continuous
response gives efficiency `eps(x) = P(y > T | x)`. If `y ~ N(mu(x), sigma)` this is
the turn-on `eps = Phi((mu - T)/sigma)` (approximate: Gaussian). A 1% drift in gain
moves `mu`, which *does nothing* on the plateau and changes efficiency steeply on the
edge. Consequences: an efficiency measured on a plateau does not constrain the gain;
a threshold effect is largest for the lowest-signal population (minimum-ionizing
particles in thin sensors, low-energy showers, single photoelectrons); and a change
in threshold or noise looks like a change in efficiency only for events near it.

## Conditional probability as the language of performance

Every performance number is `P(outcome | population)`, so it is undefined until the
population is named. Write the conditioning:

`P(reconstructed | in acceptance, has truth particle, pT > x)`, `P(pass ID | reco'd,
matched)`, `P(truth is X | selected as X)`. The same word ("efficiency") with two
denominators gives two numbers that differ by acceptance or by fake population; the
factorization and its pitfalls are in
[performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md).

## The fourteen questions (template for any detector)

1. What enters the sensitive volume?
2. Which microscopic interaction creates the signal?
3. What is the earliest physical signal (charge, light, heat, phonons, current,
   drift time)?
4. What is digitized (ADC, TDC, waveform, binary hit, time-over-threshold, image,
   trigger primitive)?
5. What is the forward model, with nuisance parameters and stochastic terms?
6. Which calibrations, conditions, geometry, field maps, and material are required?
7. Which local objects are reconstructed?
8. What pattern recognition / association / fit / deconvolution follows?
9. Which ambiguities or degeneracies are characteristic?
10. What creates inefficiency, fakes, duplicates, migrations, tails, catastrophic
    failures?
11. How does performance scale with energy, momentum, angle, occupancy, pileup, dose,
    rate, time?
12. What can be measured in data, and what needs simulation truth?
13. How are data/MC discrepancies corrected or assigned as uncertainties?
14. How can a detector defect bias a final physics result?

Each detector-family reference states its answers in a labeled subsection,
**Distinctive but generalizable reconstruction and performance features**, covering:
information topology, unique inverse problem and degeneracies, natural local/global
objects, the most informative residual or closure variable, scaling laws and floors,
community efficiency/resolution conventions, dominant tails, occupancy/rate/aging
dependence, the strongest data-driven sample, and what transfers to other detectors.

## Truth is simulation-only

Generator truth, simulation truth (energy deposits, true trajectories), digitized
signals, and reconstructed objects are four levels ([detector simulation](detector-simulation.md)).
Only the last two exist in data. Every "measured in data" performance number uses a
*data-accessible proxy* (tag-and-probe, standard candle, redundancy of independent
subdetectors, sidebands, cosmic rays) whose own bias is part of the uncertainty
([reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md),
[data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md)).

## Common misconceptions and failure modes

- **Treating `theta_hat` as `theta`.** Calibration and alignment errors are shared
  systematics, not per-event noise; more statistics never removes them.
- **Quoting "the resolution."** Without estimator, center, width definition, selection,
  and tail, the number is not comparable between detectors or between MC and data.
- **Response = calibration.** Response is the detector's behavior; calibration is the
  correction; a calibrated response can still be nonlinear or non-uniform.
- **Ignoring identifiability.** A good `chi^2` does not mean `x` is determined; check
  which directions in `x` have a flat likelihood.
- **Reading a plateau efficiency as a gain check.** Plateaus are insensitive to the
  parameter that matters at the edge.
- **Simulation truth used as if measurable.** See "Truth is simulation-only."

## Deliverables

- The chain written for the specific detector, with the model and validation sample
  for each arrow.
- The fourteen-question table filled in.
- `x`, `y`, `theta`, `epsilon` named explicitly, with every nuisance parameter's
  source and correlation.
- Every quoted performance number with its conditioning population, estimator,
  center, width, and tail definition.
