# Detector Simulation

Covers propagating generated particles through a model of the apparatus and producing
simulated readout: geometry and materials, physics processes, digitization, fast
simulation, and - most importantly for an analysis - how to establish that the
simulated response matches the real detector. The upstream stage is
[event generation](../../hep-theory/references/event-generation.md); the constants that tie simulation to the
real detector are in [calibration and alignment](calibration-and-alignment.md).

## What full simulation does

A full simulation (Geant4 being the standard toolkit) transports each particle through
a geometry description in small steps, at each step sampling the physics processes that
may occur - ionization, bremsstrahlung, pair production, multiple scattering, nuclear
interaction, decay - and recording energy deposits in volumes designated as sensitive.
The output is a set of true energy deposits with positions and times, which is *not
yet* detector output; converting those into readout values is digitization, below.

The three inputs that determine whether the result is trustworthy are the geometry, the
physics list, and the production cuts.

## Geometry and materials

The geometry description must include everything that interacts, not just the active
sensors: support structures, cables, cooling, electronics, and the material between
subsystems. **Passive material is where simulation geometries are most often wrong**,
because it is not what anyone is trying to measure and is frequently simplified into
averaged "lumped" volumes.

A mismodeled material budget produces a characteristic pattern of symptoms, and
recognizing it saves a great deal of debugging: data-simulation disagreement that
varies with polar angle (because path length through material does), a mismatch in
photon conversion or nuclear-interaction rates, tracking efficiency that disagrees at
low momentum but agrees at high, and calorimeter response that disagrees in a way no
energy-scale factor fixes uniformly.

The strongest data-driven handles on material are the reconstructed conversion and
nuclear-interaction vertex maps, which image the material distribution directly (see
[tracking and vertexing](tracking-and-vertexing.md)), and the momentum dependence of
tracking efficiency. Material uncertainty is normally propagated by producing a
simulation variant with the budget scaled in specific regions - it cannot be
represented as a weight.

## Physics lists and their validity

A physics list is a bundled choice of models and cross sections for each process and
energy range. Different lists differ most in hadronic interactions, where models are
phenomenological and are stitched together across energy ranges, with the transitions
between models being a known source of discontinuity.

Practical requirements:

- **State the physics list and version.** It is as much a part of the sample definition
  as the generator, and results are not comparable across lists without checking.
- **Confirm the list is validated for the relevant energy range and particle types.**
  A list validated for GeV-scale collider physics is not automatically appropriate for
  low-energy nuclear recoils, for heavy ions, or for very high energy cosmic-ray
  primaries.
- **Hadronic shower modeling is a real uncertainty**, not a fixed truth, and where a
  measurement depends on it (hadronic calorimeter response, punch-through, secondary
  production), an alternative list is the honest way to estimate it.

## Production cuts and stepping

Full simulation is expensive, and cost is controlled by **production cuts** - a
threshold, usually expressed as a range rather than an energy, below which secondary
particles are not produced and their energy is deposited locally instead. This is an
approximation with a physics consequence: too coarse a cut removes the low-energy
secondaries that carry the signal in a thin detector, distorting deposits in exactly
the sensitive volumes that matter. Cuts must be set per region, tighter in sensitive
volumes than in bulk absorber, and the choice validated by confirming the observable of
interest is stable against tightening them.

**Step limits** matter similarly in thin sensitive volumes and in strong field
gradients, where too long a step misplaces the deposit or mistracks the trajectory.

## Digitization

Digitization converts true energy deposits into simulated readout, and it is where the
simulation stops being physics and starts being an electronics model. It must
reproduce: charge collection and sharing between channels, the response function and
its saturation, electronic noise with its real correlations, discriminator thresholds
and zero suppression, time structure including any integration window that admits
out-of-time signals, and the dead/noisy channel map for the period being simulated.

Digitization is the most common place for a data-simulation mismatch that no
calibration fixes, because it is the stage most often simplified. Specific things worth
checking explicitly:

- **Noise is not white and not uncorrelated.** Common-mode noise across a readout group
  behaves very differently from independent per-channel noise, especially after
  clustering, and a simulation with independent Gaussian noise will produce cluster
  size and occupancy distributions that do not match.
- **Thresholds and zero suppression must match the data exactly**, including any
  time-dependence; a simulation with the wrong threshold has a different efficiency
  turn-on that will be misattributed to physics.
- **Pileup overlay** must reproduce the data's pileup distribution and its
  out-of-time structure, consistently with the reweighting applied later - see
  [triggers-luminosity-pileup.md](triggers-luminosity-pileup.md) and
  the pileup discussion in [event reconstruction](event-reconstruction.md).
- **Simulated events must be reconstructed with the same code and configuration as
  data.** Any divergence between the two reconstruction paths becomes a systematic
  that is invisible in every internal cross-check.

## Fast and parametrized simulation

Full simulation of calorimeter showers dominates the cost, so fast alternatives
replace shower transport with a parametrized response - a library of pre-simulated
showers, an analytic parameterization, or a learned generative model. Fast simulation is
legitimate and often necessary, but its validity is conditional:

- It is valid **only where it was validated**. A parameterization tuned on single
  particles at fixed energies may not describe overlapping showers, unusual
  topologies, or the tails that drive a specific selection.
- **Tails are the first thing lost.** A parameterization matching the core response can
  badly misrepresent the tail, which is exactly what matters for fake missing momentum
  and for background estimates.
- **Correlations are the second.** Longitudinal-lateral shower correlations, and
  correlations between nearby particles, are frequently not preserved, which affects
  shower-shape discriminants and isolation.
- The difference between fast and full simulation, evaluated on the analysis's own
  observables, is the natural systematic - and if that difference is large, the fast
  sample is not a substitute for the analysis in question, however good its agreement
  in inclusive distributions.

## Validating the simulation

Simulation is a model to be tested, not a reference to be trusted. A useful validation
ladder:

1. **Geometry and material** - total budget and its distribution against the
   engineering description; conversion and interaction vertex maps against data.
2. **Single-particle response** - energy scale, resolution, and shower shapes against
   test-beam data where available, and against in-situ resonances or `E/p` in data.
3. **Occupancy and noise** - hit multiplicity, cluster size, and noise distributions,
   which test digitization directly and are sensitive to problems that energy-level
   comparisons miss.
4. **Reconstruction-level distributions** in a control region orthogonal to the signal
   selection, where any disagreement can be characterized without unblinding.
5. **Efficiency and resolution** against their data-driven measurements, with the
   residual difference becoming the scale factor and its uncertainty - see
   [reconstruction performance](reconstruction-performance-and-truth-matching.md).

**Do not tune simulation parameters to remove a disagreement in the observable the
analysis measures.** Tuning is legitimate on independent control observables with a
physical justification stated, and the tuned parameter's remaining freedom becomes a
systematic. Tuning against the measurement itself destroys the measurement, for the
same reason that tuning a fit to obtain a desired significance does.

## Worked walkthrough: setting up a Geant4 simulation for a calorimeter test-beam comparison

Not executed in this package (no Geant4 installation). This is the order of decisions, each
with the check that closes it.

1. **Geometry and material.** Build the geometry from the engineering description, then
   compare the total material budget (`X/X0` and `lambda_I` versus eta or depth, from a
   geantino scan) with the design table and survey. It must agree before any physics
   comparison is meaningful.
2. **Physics list.** Pick the collaboration's validated list for the energy range (e.g. an
   `FTFP_BERT`-family list for hadron showers at test-beam energies). Record its name and
   the Geant4 version. Run an alternative list (e.g. `QGSP_BIC`) for the model systematic,
   never to choose the list that agrees best with the data.
3. **Production cuts and step limits.** Scan the range cut (for example 0.7 mm, 0.35 mm,
   0.1 mm). Keep the smallest value beyond which the response and resolution stop changing
   within statistics.
4. **Digitization.** Apply Birks saturation, photostatistics, noise, and the readout
   threshold. Validate each on its own control sample (MIPs, pedestals) before tuning
   anything else.
5. **Compare with the test beam** in observables *not* used to tune steps 1-4: response
   linearity, resolution versus E, and longitudinal and lateral profiles. If showers are too
   narrow, first check the material and the digitized lateral cross-talk, and only then the
   physics list. Carry the list difference as a systematic, not as a tuning knob.

## Common misconceptions and failure modes

- **The simulation treated as truth about the detector.** It is a model with validated ranges.
- **Tuning the simulation on the measured observable.**
- **Physics-list validity ranges ignored**, especially for hadronic showers.
- **Fast simulation used outside the phase space where it was validated.**
- **Digitization, noise, and pileup overlay not matched to data conditions.**

## Deliverables

- Simulation toolkit and version, geometry version, physics list and version, and
  production cuts per region, all recorded alongside the sample.
- Material budget comparison against the engineering description and against a
  data-driven material probe.
- Digitization model details: noise model and its correlations, thresholds and zero
  suppression, integration window, dead/noisy channel map and its time dependence.
- Pileup overlay configuration and its consistency with the pileup reweighting applied
  downstream.
- Confirmation that simulation and data are reconstructed with identical code and
  configuration.
- If fast simulation is used: what it was validated against, the observables where it
  was checked, and the full-versus-fast difference quoted as a systematic.
- Validation evidence at each rung of the ladder above, with disagreements quantified
  rather than tuned away, and any tuning justified physically on independent
  observables.
