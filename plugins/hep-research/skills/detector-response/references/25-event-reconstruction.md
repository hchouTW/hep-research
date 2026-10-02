# Event Reconstruction

Covers the chain that turns raw detector signals into the physics objects an analysis
consumes: hits, clusters, tracks, vertices, identified particles, and event-level
quantities. The subsystem physics feeding this chain is in
[tracking](22-tracking-and-vertexing.md),
[calorimetry](23-calorimetry-ecal-hcal.md), and
[particle identification](24-particle-identification.md); the object-level corrections
applied afterwards are in
[18-physics-objects-jets-btagging-met.md](18-physics-objects-jets-btagging-met.md),
and how to measure whether reconstruction worked is in
[reconstruction performance and truth matching](26-reconstruction-performance-and-truth-matching.md).

## The chain, and why its order matters

Reconstruction proceeds roughly as: raw readout -> calibrated digits -> hits ->
clusters and track candidates -> fitted tracks -> vertices -> identified particles ->
composite objects (jets, missing transverse momentum) -> event-level selection
quantities.

Each stage consumes the previous stage's output *and its uncertainty*, and each stage
makes decisions that later stages cannot undo. A hit dropped by a threshold cut is not
recoverable by a better track fit; a track that failed pattern recognition is invisible
to vertexing; energy assigned to the wrong cluster is missing from the right one. This
one-directional information loss is why reconstruction is normally re-run rather than
patched, and why a change in an early stage requires revalidating everything
downstream rather than only the stage that changed.

The practical corollary for analysis: reconstruction-level systematic variations must
be applied at the stage where the effect physically occurs and propagated forward.
Applying a "tracking efficiency" uncertainty as a flat event weight is wrong whenever
the missing track would have changed jet clustering, isolation, or missing transverse
momentum - the same requirement stated as an analysis invariant for kinematic
variations.

## Digitization boundary and calibration

The first stage converts readout values into physical quantities using calibration
constants: pedestals, gains, channel-by-channel intercalibration, timing offsets, and
dead or noisy channel maps. Everything downstream inherits these, and their versioning
is part of the analysis's reproducibility record - see
[calibration and alignment](29-calibration-and-alignment.md).

Two failure modes recur. **Dead and noisy channel maps must match between data and
simulation**, or simulated events see a detector that does not exist; when the masks
are time-dependent, the simulation must reproduce the time-averaged mask weighted by
the luminosity actually collected. And **zero suppression and thresholds discard
information irreversibly** at the readout, so a signal below threshold is not merely
noisy, it is absent - which produces an efficiency turn-on that must be modeled rather
than assumed flat.

## Clustering

Calorimeter clustering groups deposits into objects. The two standard approaches are
fixed-geometry windows (simple, stable under pileup, but poorly matched to showers
that spread irregularly) and topological growth from seeds above a
noise-scaled threshold (better containment, but with a cluster size and hence a noise
and pileup contribution that varies event by event).

The seed threshold and the growth threshold are the two parameters that matter most.
Raising them suppresses noise and pileup at the cost of low-energy efficiency and of
truncating shower tails; lowering them recovers energy but couples the measurement to
pileup. Because the optimum depends on the pileup level, a clustering configuration
tuned for one running condition is not automatically valid for another - and
comparisons across data-taking periods must confirm that the clustering behaved the
same way, not just that the calibration was applied.

**Cluster splitting** - deciding whether one broad deposit is one particle or two
nearby ones - is where nearby-particle resolution is set, and it fails in a
characteristic way: two nearby particles merged into one cluster produce an object with
roughly the summed energy and an intermediate position, which is not obviously wrong in
any single-object distribution but distorts multiplicity and isolation.

## Track-cluster association and particle-flow reconstruction

When both a tracker and calorimeters cover the same solid angle, the same particle is
measured twice, and combining the two measurements well is worth a great deal:
the tracker is more precise at low momentum, the calorimeter at high energy, and the
calorimeter additionally sees neutrals.

**Particle-flow-style reconstruction** attempts to identify every individual particle
in the event by linking tracks to clusters, then choosing the best measurement for
each: charged particles take their momentum from the track, and the calorimeter energy
they deposited is *subtracted* so that the remainder can be attributed to neutrals.
This gives substantially better jet and missing-momentum resolution than using
calorimeter energy alone, at the price of a much stronger dependence on the quality of
the link.

The failure modes follow directly from the subtraction:

- **Over-subtraction.** If a charged particle's calorimeter deposit is estimated too
  large, real neutral energy is erased. This biases the neutral component low and is
  hard to see in the charged distributions where the problem originates.
- **Under-subtraction.** Residual charged energy is misinterpreted as a fake neutral,
  inflating both multiplicity and energy.
- **Double counting.** A track wrongly linked to a cluster produced by a different
  particle counts one particle twice and loses the other.
- **Sensitivity to tracking efficiency.** Because a missing track means its energy is
  attributed to a neutral (measured with worse calorimeter resolution rather than lost
  entirely), tracking inefficiency degrades resolution and shifts scale in a way that
  depends on the calorimeter response - so tracking and calorimeter systematics are
  *correlated* in a particle-flow analysis and must not be varied independently.

## Ambiguity resolution across the event

Reconstruction produces overlapping interpretations that must be reduced to a
consistent event: duplicate tracks from the same particle, a photon candidate that is
also part of a jet, an electron whose track is also a jet constituent. Resolving these
is not a detail - it determines what "number of objects" means, and inconsistent
resolution between data and simulation produces multiplicities that do not agree for
reasons unrelated to physics.

Overlap removal (which object wins when two definitions claim the same energy) is
specified at the analysis level and is covered in
[18-physics-objects-jets-btagging-met.md](18-physics-objects-jets-btagging-met.md);
what matters here is that the reconstruction-level and analysis-level removals must be
consistent with each other, and that the ordering of removal steps changes the result.

## Timing and event association

Where the detector has adequate timing, associating deposits and tracks by arrival time
suppresses out-of-time contributions - pileup from adjacent bunch crossings, cavern or
albedo background, and cosmic-ray tracks. Timing association is an efficiency-versus-
purity trade like any other, with the added subtlety that a timing window is only as
good as the time calibration and the assumed time-of-flight to the measurement point
- which depends on the assumed particle velocity, and therefore on the species
hypothesis.

## Reconstruction under pileup

When multiple interactions overlap, reconstruction must assign objects to a primary
vertex and estimate the diffuse energy from the rest. Standard components are vertex
selection (which vertex is the interesting one - a choice with its own efficiency and
its own mis-assignment rate), charged-hadron subtraction using track-to-vertex
association, and an event-by-event estimate of the pileup energy density used to
correct object energies.

Two points are easy to get wrong. Pileup mitigation is a *correction with an
uncertainty*, not a clean removal, and its residual must appear as a systematic. And
because the pileup distribution differs between data and simulation, the reweighting of
[19-triggers-luminosity-pileup.md](19-triggers-luminosity-pileup.md) must be
applied consistently with the mitigation - reweighting to a data pileup profile while
reconstructing with a mitigation tuned for a different profile leaves a residual that
neither step catches.

## Reproducibility of the reconstruction

Reconstruction output depends on software version, calibration and alignment payloads,
geometry description, and configuration. All four belong in the analysis record; a
"same" sample reprocessed with a different payload is a different sample, and mixing
processings within one measurement is a defect unless explicitly justified and
validated. Multithreaded reconstruction can also introduce ordering-dependent results
where algorithms are not order-invariant - check that a rerun reproduces the same
output before attributing a difference to anything physical.

## Deliverables

- The reconstruction chain used, with software version, geometry, and calibration/
  alignment payload versions recorded.
- Clustering algorithm and thresholds, and confirmation that they are consistent across
  the data-taking periods being combined.
- Whether particle-flow-style combination is used and, if so, an explicit statement
  that tracking and calorimeter systematics are treated as correlated.
- Ambiguity and overlap-removal steps in the order applied, consistent between
  reconstruction and analysis levels.
- Timing association windows, if used, with the assumed time-of-flight hypothesis.
- Pileup mitigation method, its residual uncertainty, and its consistency with the
  pileup reweighting applied to simulation.
- Confirmation that a rerun reproduces the same output (no ordering or threading
  dependence).
