# Event Reconstruction

Covers the chain that turns raw detector signals into the physics objects an analysis
consumes: hits, clusters, tracks, vertices, identified particles, and event-level
quantities. The subsystem physics feeding this chain is in
[tracking](tracking-and-vertexing.md),
[calorimetry](calorimetry-ecal-hcal.md), and
[particle identification](particle-identification.md); the object-level corrections
applied afterwards are in
[physics-objects-jets-btagging-met.md](physics-objects-jets-btagging-met.md),
and how to measure whether reconstruction worked is in
[reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md).
How to choose the estimator for a reconstructed quantity is in
[detector measurement framework](detector-measurement-framework.md#choosing-the-estimator);
likelihood reconstruction from many photosensor hits is in
[photon likelihood reconstruction](photon-likelihood-reconstruction.md).
Reconstructing the DIS variables x, y and Q^2 from the scattered lepton and the hadronic final state
(electron, Jacquet-Blondel, double-angle and Sigma methods; a crossing angle) is in
[DIS kinematic reconstruction](dis-kinematic-reconstruction.md).
Method text scoped to the sources read, with the gaps stated, for instruments outside this chain's usual objects:
superconducting photon sensors, bubble and droplet detectors and Skipper CCDs in
[threshold and quantum sensor reconstruction](threshold-and-quantum-sensor-reconstruction.md); Compton,
pair-conversion and coded-aperture imaging and polarimetry in
[gamma-ray imaging and polarimetry reconstruction](gamma-ray-imaging-and-polarimetry-reconstruction.md); CRES,
haloscopes and retarding spectrometers in
[frequency- and scan-encoded spectroscopy reconstruction](frequency-and-scan-encoded-spectroscopy-reconstruction.md);
scanning radiometers in [timestream to map reconstruction](timestream-to-map-reconstruction.md).

## The chain, and why its order matters

Reconstruction proceeds roughly as: raw readout -> calibrated digits -> hits ->
clusters, track or image candidates -> fitted objects (tracks, showers, vertices, shower
axes) -> identified particles -> event-level quantities. At a collider the composite stage
adds jets and missing transverse momentum; a LArTPC goes from signal processing to pattern
recognition to calorimetry and PID (PDG RPP 2025 sec. 35.7.6, p. 61); an imaging Cherenkov
telescope parametrizes images by ellipses and intersects their axes (sec. 36.2.2, p. 8;
[imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md)).

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

**Check:** Each reconstruction-level variation is applied at the stage where the effect occurs and propagated forward, not as a flat event weight.

## Digitization boundary and calibration

The first stage converts readout values into physical quantities using calibration
constants: pedestals, gains, channel-by-channel intercalibration, timing offsets, and
dead or noisy channel maps. Everything downstream inherits these, and their versioning
is part of the analysis's reproducibility record - see
[calibration and alignment](calibration-and-alignment.md); a residual left after calibration is propagated as in
[calibration residual propagation](calibration-residual-propagation.md).

Two failure modes recur. **Dead and noisy channel maps must match between data and
simulation**, or simulated events see a detector that does not exist; when the masks
are time-dependent, simulated events must be assigned to runs or periods in
proportion to the luminosity (at a collider) or the live time and exposure actually
collected, each with that period's mask (or per-period simulation combined with exposure
weights); in a space or balloon instrument the exposure can depend on the measured quantity
(on rigidity through the geomagnetic cutoff, arXiv:1407.1657v1, secs. 3.5 and 3.7); an averaged mask is not a
substitute, since `sum_t w_t R(theta_t) != R(sum_t w_t theta_t)` in general. And **zero suppression and thresholds discard
information irreversibly** at the readout, so a signal below threshold is not merely
noisy, it is absent - which produces an efficiency turn-on that must be modeled rather
than assumed flat.

Amplitude and time come from the digitized samples through an estimator (largest sample,
template fit, optimal filter, possibly constrained against phase or baseline errors) whose
bias depends on the phase, the pileup level and the baseline; its weights are conditions
data, and simulation must use the same ones. The estimators, their bias and noise, and the
threshold-level operating window (efficiency against noise occupancy for the charge on the
channel) are in [front-end waveform processing](front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms)
and [front-end electronics](front-end-electronics-and-signal-processing.md#thresholds-fake-hits-and-zero-suppression).

**Check:** Dead and noisy channel maps match between data and simulation period by period (weighted by luminosity or exposure), and threshold turn-ons are modeled.

## Clustering

Calorimeter clustering groups deposits into objects. The two standard approaches are
fixed-geometry windows (simple, stable under pileup, but poorly matched to showers
that spread irregularly) and topological growth from seeds above a
noise-scaled threshold (better containment, but with a cluster size and hence a noise
and pileup contribution that varies event by event).

The seed threshold and the growth threshold are the two parameters that matter most.
Raising them suppresses noise and pileup at the cost of low-energy efficiency and of
truncating shower tails; lowering them recovers energy but couples the measurement to
pileup. Because the optimum depends on the noise level and, where unrelated interactions
overlap in the readout window (at a collider, pileup), on the pileup level, a clustering
configuration tuned for one running condition is not automatically valid for another - and
comparisons across data-taking periods must confirm that the clustering behaved the
same way, not just that the calibration was applied.

**Cluster splitting** - deciding whether one broad deposit is one particle or two
nearby ones - is where nearby-particle resolution is set, and it fails in a
characteristic way: two nearby particles merged into one cluster produce an object with
roughly the summed energy and an intermediate position, which is not obviously wrong in
any single-object distribution but distorts multiplicity and isolation.

**Check:** Seed and growth thresholds are stated and shown to behave the same way across the periods combined; split and merged clusters are treated as reconstruction outcomes with rates.

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

**Check:** With particle flow, tracking and calorimeter systematics are varied together (correlated), and over-subtraction, under-subtraction and double counting are checked.

## Ambiguity resolution across the event

Reconstruction produces overlapping interpretations that must be reduced to a
consistent event: duplicate tracks from the same particle, a photon candidate that is
also part of a jet, an electron whose track is also a jet constituent. Resolving these
is not a detail - it determines what "number of objects" means, and inconsistent
resolution between data and simulation produces multiplicities that do not agree for
reasons unrelated to physics.

Overlap removal (which object wins when two definitions claim the same energy) is
specified at the analysis level and is covered in
[physics-objects-jets-btagging-met.md](physics-objects-jets-btagging-met.md);
what matters here is that the reconstruction-level and analysis-level removals must be
consistent with each other, and that the ordering of removal steps changes the result.

**Check:** Reconstruction-level and analysis-level removals are consistent and applied in the same order in data and simulation.

## Timing and event association

Where the detector has adequate timing, associating deposits and tracks by arrival time
suppresses out-of-time contributions - cosmic-ray tracks and, at a collider, pileup from
adjacent bunch crossings and cavern background. Timing association is an efficiency-versus-
purity trade like any other, with the added subtlety that a timing window is only as
good as the time calibration, the start-time source (an accelerator clock, the scintillation
light of the interaction in a LArTPC, PDG RPP 2025 sec. 35.7.4, pp. 59-60, or the instrument's
own timing layers) and the assumed time of flight to the measurement point - which depends on
the assumed velocity, and therefore on the species hypothesis, and on the assumed direction.
In a space instrument albedo (upward-going) particles are separated by the sign of the
measured time difference, not by an out-of-time window (arXiv:hep-ex/0305074v1, sec. 2;
arXiv:1407.1657v1, sec. 2).

**Check:** Timing windows are stated with the time calibration, the start-time source and the time-of-flight (species and direction) hypothesis they assume.

## Reconstruction under pileup

Pileup is unrelated activity inside the resolving time of the readout; its form and
mitigation depend on the environment. At a collider, where several interactions overlap in a
bunch crossing, reconstruction must assign objects to a primary
vertex and estimate the diffuse energy from the rest. Standard components are vertex
selection (which vertex is the interesting one - a choice with its own efficiency and
its own mis-assignment rate), charged-hadron subtraction using track-to-vertex
association, and an event-by-event estimate of the pileup energy density used to
correct object energies. Elsewhere: in slow cryogenic and germanium detectors two pulses
merge within the resolving time and are rejected by pulse-shape tests
([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md#pileup-and-position-in-cryogenic-and-germanium-detectors);
low-temperature calorimeters keep a low rate per device, PDG RPP 2025 sec. 36.5.3, p. 46); in a
surface LArTPC cosmic tracks share the drift window
([single-phase LArTPCs](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs));
in surface arrays random muons enter station traces
([ground based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction));
in imaging Cherenkov cameras night-sky background piles up unless the exposure is a few ns
(sec. 36.2.2, p. 8).

Two points are easy to get wrong. Pileup mitigation is a *correction with an
uncertainty*, not a clean removal, and its residual must appear as a systematic. And,
at a collider, because the pileup distribution differs between data and simulation, the reweighting of
[triggers-luminosity-pileup.md](triggers-luminosity-pileup.md) must be
applied consistently with the mitigation - reweighting to a data pileup profile while
reconstructing with a mitigation tuned for a different profile leaves a residual that
neither step catches.

**Check:** Pileup mitigation carries a residual systematic and, at a collider, is consistent with the pileup profile used for reweighting.

## Validating a learned reconstruction

A machine-learned tracking, clustering or particle-flow step is validated like any reconstruction, plus: compare its
outputs in data and simulation in control samples; check that its per-object uncertainties are calibrated (pull
widths and coverage); test it under the domain shift between simulation and data, and under other conditions (pileup,
time-dependent detector state); and check its behaviour outside the training range, where it must flag rather than
extrapolate silently. Training belongs to hep-ml; the validation of the reconstructed objects stays here.

**Check:** Data/simulation agreement in control samples, calibrated per-object uncertainties, behaviour under domain shift and out-of-range flagging are each shown.

## Reproducibility of the reconstruction

Reconstruction output depends on software version, calibration and alignment payloads,
geometry description, and configuration. All four belong in the analysis record; a
"same" sample reprocessed with a different payload is a different sample, and mixing
processings within one measurement is a defect unless explicitly justified and
validated. Multithreaded reconstruction can also introduce ordering-dependent results
where algorithms are not order-invariant - check that a rerun reproduces the same
output before attributing a difference to anything physical.

**Check:** Software, payload, geometry and configuration versions are recorded, one processing per measurement, and a rerun reproduces the output.

## Planning a reconstruction: the method contract

Before choosing an algorithm, decide what the request needs and record it: the method semantics, the conditions
context actually resolved, the uncertainty representation, whether associations are assignments or candidates, the
routing questions per subsystem, selection bias and exposure, and how partitioning is checked. The full contract, with
its routing table and representative cases, is in [reconstruction method contract](reconstruction-method-contract.md).

## Common misconceptions and failure modes

- **Reconstruction order treated as arbitrary.** Each step's output is the next step's input, so a change propagates downstream.
- **Particle-flow double counting**: the same energy attributed to a track and to a calorimeter cluster.
- **Pileup modeled as extra noise only.** It also creates fake objects and merges real ones.
- **Clustering output taken as truth.** Split and merged clusters are reconstruction outcomes with their own rates.
- **Different reconstruction versions or conditions used for data and simulation.**

## Deliverables

- The reconstruction chain used, with software version, geometry, and calibration/
  alignment payload versions recorded.
- Clustering algorithm and thresholds, and confirmation that they are consistent across
  the data-taking periods being combined.
- Whether particle-flow-style combination is used and, if so, an explicit statement
  that tracking and calorimeter systematics are treated as correlated.
- Ambiguity and overlap-removal steps in the order applied, consistent between
  reconstruction and analysis levels.
- Timing association windows, if used, with the start-time source and the assumed
  time-of-flight (species and direction) hypothesis.
- Pileup mitigation method, its residual uncertainty, and (at a collider) its consistency
  with the pileup reweighting applied to simulation.
- Confirmation that a rerun reproduces the same output (no ordering or threading
  dependence).

## Linked pages

- [References: in-situ calibration and alignment](detector-principles-bibliography-calibration.md): annotated sources of the in-situ calibration and alignment pages
- [References: particle identification reference PDFs](detector-principles-bibliography-particle-identification.md): annotated sources of the multisample PID and reference-PDF page
- [in-situ calibration methods](in-situ-calibration-methods.md): detector constants from data: unknowns, reference samples and residuals; per-channel iteration, global least squares and Millepede-type solvers; unconstrained modes, convergence, bias and per-channel precision; ECAL, HCAL, TOF, gas-gain and RICH instances (simcal is hep-statistics')
- [in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md): track and chamber alignment from data (Millepede-II with General Broken Lines, iterative chi2, optical, acoustic and photogrammetric positioning) and the momentum scale from resonances, cosmic muons or range versus curvature
- [Multisample PID and reference PDFs](multisample-pid-and-reference-pdfs.md): combining many samples of one particle (charge from many dE/dx layers, per-layer log-likelihood ratio), per-layer reference PDFs from control samples (COL V0, conversions, tag-and-probe; SPC charge- and velocity-selected flight data; FXT tagged beams), binning, layer correlations, and the multisample_pid.py input format
- [Calorimeter cluster reconstruction](calorimeter-cluster-reconstruction.md): clustering, cluster position and direction, shower shapes for electron, photon and neutral-pion separation, converted photons, cluster energy corrections, preshower, dual readout and high-granularity imaging
- [References: calorimeter cluster reconstruction](detector-principles-bibliography-calorimetry.md): annotated sources of the calorimeter cluster reconstruction page
- [Resolution shape models](resolution-shape-models.md): Crystal Ball and double-sided Crystal Ball (alpha-n correlation), Gaussian plus pedestal, core-plus-tail time PDF, hadronic or partially contained response, effective sigma, and when to use each.
- [Hadronic calorimeter reconstruction](hadronic-calorimeter-reconstruction.md): software compensation, the hadronic calibration chain, leakage and punch-through, high-granularity HCALs
- [Hadronic calorimeter timing and model validation](hadronic-calorimeter-timing-and-model-validation.md): shower timing and the observables that validate hadronic physics lists
- [Gaseous tracker distortions](gaseous-tracker-distortions.md): TPC space charge and E x B distortion maps (gas TPC and LArTPC treated separately), drift-velocity and t0 references, and drift-chamber r(t) calibration
- [Silicon hit reconstruction](silicon-hit-reconstruction.md): pixel and strip clustering, centre of gravity and eta correction, head-tail, Lorentz shift, charge templates, cluster size versus incidence angle, nuclear charge from cluster charge
- [Event time and timing association](event-time-and-timing-association.md): event-time (start-time) estimators and their self-use bias with and without a bunch clock, bunch or beam-bucket assignment, track-to-hit and hit-to-event association in space and time, up- versus down-going discrimination, and synchronisation of separated stations
- [Muon systems](muon-systems.md): muon chambers and the muon reconstruction chain, muon types, chamber alignment and momentum scale, energy loss in iron and other absorbers, and charge-sign quality
- [Non-collider muon detection](non-collider-muon-detection.md): muon vetoes and veto-efficiency measurement, cosmogenic tagging, muon counting in air-shower arrays, and muons and albedo in orbit
- [References: muon systems](detector-principles-bibliography-muon-systems.md): annotated sources of the muon systems and non-collider muon detection pages
