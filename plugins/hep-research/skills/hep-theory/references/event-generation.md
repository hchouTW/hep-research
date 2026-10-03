# Event Generation

Covers the layer upstream of the detector: producing the particle-level events that
detector simulation then propagates. Deliberately complements rather than repeats
[weights-normalization.md](../../hep-analysis/references/weights-normalization.md), which owns
luminosity, cross-section normalization, and the sum-of-weights convention, and
[systematics.md](../../hep-analysis/references/systematics.md), which owns how theory variations
enter the likelihood. What is added here is the structure of the generation chain and
the failure modes specific to it. The downstream stage is
[detector simulation](../../detector-response/references/detector-simulation.md).

## The generation chain

Simulated events are built in stages, each with its own approximation and its own
uncertainty:

1. **Parton distributions** describe the momentum fractions of the incoming partons in
   the colliding hadrons (or, for a non-collider experiment, the incident flux model
   plays the analogous role of specifying the initial state).
2. **Matrix element** - the fixed-order calculation of the hard process, at leading or
   next-to-leading order, for a chosen final-state multiplicity.
3. **Parton shower** - resummation of soft and collinear emissions, evolving the hard
   process down to a low scale.
4. **Hadronization** - conversion of partons into hadrons, described by a
   phenomenological model with parameters tuned to data.
5. **Decays** of unstable hadrons and taus, often handled by a dedicated package.
6. **Underlying event and multiple parton interactions**, plus, where relevant,
   overlaid pileup interactions.

Each stage is a separate source of uncertainty and each is tuned separately. The output
is a particle-level event record - typically interchanged as LHE for the matrix-element
stage and HepMC for the showered, hadronized event.

## Matching and merging: the double-counting problem

A matrix element with an extra explicit parton and a parton shower emitting that same
parton describe the *same* configuration. Combining them naively double counts it. The
standard remedies - merging schemes for combining multiplicities at leading order,
matching schemes for avoiding double counting at next-to-leading order - all work by
introducing a separation scale and vetoing shower emissions that the matrix element
already covers.

Three consequences matter in practice:

- **The merging scale is not physical.** Results must be insensitive to it within
  uncertainty. A visible dependence means the merging is not working, and the standard
  check is to vary the scale and confirm stability of the distributions actually used
  in the analysis - not just of the inclusive cross section, which is much less
  sensitive.
- **A discontinuity at the merging scale** in a jet-multiplicity or jet-pT
  distribution is the characteristic symptom of a misconfigured merge, and it is
  usually visible only in the specific variable where the transition occurs.
- **Samples generated with different multiplicities must be combined with the
  scheme's own weights**, not stacked by cross section as if they were independent
  processes. Doing the latter is the most common way to silently double count.

## Negative weights

Next-to-leading-order generators produce events with negative weights, which are not a
defect but a necessary part of the cancellation between real and virtual contributions.
Handling them correctly is a hard requirement:

- **Never discard negative-weight events**, and never take absolute values. Both bias
  the prediction.
- **The effective statistical power is reduced.** A sample with a fraction `f` of
  negative-weight events has an effective size smaller than its entry count by roughly
  `(1 - 2f)^2`, so a sample with 25% negative weights carries only about a quarter of
  the statistical power its entry count suggests. Quote effective sample size, not
  entries.
- **Bins can go negative** from statistical fluctuation. As stated in the analysis
  invariants, do not silently clip - investigate whether it is statistics, binning, or
  a genuine modeling problem, and treat the bin properly in the likelihood.
- **Normalization uses the sum of weights of the full production**, not the selected
  entry count. This is the rule in
  [weights-normalization.md](../../hep-analysis/references/weights-normalization.md) and it is
  violated most often when a sample is split across production batches or partially
  reprocessed.

## Systematic variations from generation

Generator-level uncertainties are usually delivered as per-event weight vectors, which
is efficient but easy to misuse:

- **Scale variations** (renormalization and factorization) are conventionally taken as
  an envelope over a set of discrete variations, excluding the combinations where the
  two scales move in opposite directions. State which envelope convention was used;
  they differ and are not interchangeable.
- **PDF uncertainties** must be combined according to the set's own prescription -
  Hessian sets and replica-based sets require different formulas, and applying the
  wrong one gives an uncertainty that can be wrong by a large factor.
- **Parton-shower and hadronization variations** generally require alternative samples
  or dedicated weights, not scale weights, and their statistical uncertainty is often
  comparable to the effect being measured - smoothing or a shape-only treatment may be
  needed, and must be documented.
- **A weight-based variation only captures rate and shape at the same particle-level
  configuration.** Where a variation changes the kinematics enough to alter object
  reconstruction or category assignment, it must be propagated through reconstruction,
  not applied as a final histogram weight - the analysis invariant on kinematic
  variations applies here too.

Do not treat a generator's central prediction as data. A tuned generator reproduces the
data it was tuned on, which makes agreement in those observables uninformative; the
meaningful comparisons are in observables outside the tuning set.

## Reproducibility

Record the generator and version, the process and its order, the PDF set and its
version, the tune name, the merging scheme and scale, the decay package, and the random
seeds. Two samples produced from the same configuration with different seeds are
statistically independent; two produced with the same seed are not, and averaging them
as if independent understates the uncertainty. Where the analysis combines samples from
different generator configurations, state which regions each covers and confirm they do
not overlap.

## Deliverables

- Generator, version, process, perturbative order, PDF set, and tune, with the
  interchange format (LHE/HepMC) used between stages.
- Merging or matching scheme, its scale, and evidence of insensitivity to that scale in
  the distributions the analysis actually uses.
- Negative-weight fraction and the effective sample size, with confirmation that
  negative weights are neither dropped nor absolute-valued.
- Normalization based on the sum of generator weights for the full production, with the
  production boundary stated.
- Scale-variation envelope convention, PDF combination prescription matched to the set
  type, and the shower/hadronization variation method.
- Which variations were applied as weights and which required propagation through
  reconstruction, with the justification.
- Random seeds and the independence status of combined samples.
