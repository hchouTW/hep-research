# Calibration and Alignment

Covers the constants that connect a simulated or idealized detector to the real one:
energy and timing calibration, alignment of sensor positions, their time dependence,
and how a change in any of them propagates through everything downstream. This is the
feedback loop that closes the chain from
[detector simulation](detector-simulation.md) back to
[event reconstruction](event-reconstruction.md).

## Calibration is a chain, and its order is part of the definition

A reconstructed energy or position is the product of a sequence of corrections -
pedestal subtraction, gain, channel-to-channel intercalibration, an absolute scale, and
finally residual corrections for known dependences. The sequence is not commutative in
practice, because later steps are derived assuming earlier ones were applied. Applying
a correction twice, or out of order, or mixing constants derived under different
upstream assumptions, are all common and all produce a scale error that is difficult to
diagnose from the final numbers alone.

Record the full chain, in order, with the payload version of each step. "Which
calibration was applied" is not a single answer.

## Test-beam versus in-situ calibration

**Test-beam** calibration measures the response of detector modules to particles of
known type and energy before installation. It gives an absolute, well-controlled
reference, but it applies to a small sample of modules, under conditions - no magnetic
field, no surrounding material, no pileup, pre-irradiation - that differ from the final
environment. Test-beam constants are a starting point, not a final answer.

**In-situ** calibration derives constants from the data itself, using physics that is
known independently: a resonance of known mass, momentum-energy consistency (`E/p`),
back-to-back balance in transverse momentum, or the uniformity of an isotropic flux.
It is the only way to capture the real environment and its time evolution, and it is
what sets the achievable constant term of a calorimeter (see
[calorimetry](calorimetry-ecal-hcal.md)).

The limitation of in-situ calibration is circularity: the reference physics is measured
with the same detector being calibrated. A resonance mass calibration constrains the
energy scale at the resonance's energy and must be extrapolated elsewhere, and the
extrapolation - not the calibration point - is usually the dominant uncertainty. State
where the calibration is anchored and how far it is extrapolated.

## Alignment and weak modes

Alignment determines the actual positions and orientations of sensors, typically by
minimizing track residuals over a large sample. The residual-minimization approach has
a structural blind spot that deserves explicit attention.

**Weak modes** are coherent detector deformations that leave track residuals almost
unchanged while systematically biasing the fitted track parameters. Because the
alignment procedure minimizes exactly the quantity that weak modes do not affect, they
are invisible to it by construction, and internal fit quality gives no warning.

The dangerous ones bias curvature. A deformation that adds a curvature offset shifts
positive and negative particles in *opposite* directions - a charge-antisymmetric
rigidity bias - which directly fakes any charge-ratio or antiparticle-fraction
measurement, and which no amount of chi-square improvement will reveal. Related modes
produce a rigidity scale error that grows with rigidity, mimicking or masking a
spectral feature.

Weak modes must be constrained with information the alignment fit does not use:

- **A resonance of known mass**, whose reconstructed mass must not depend on the
  charge, the direction, or the momentum of its decay products.
- **`E/p` symmetry** between positive and negative particles - a calorimeter energy
  measurement is charge-blind, so a charge-dependent `E/p` is a tracker alignment
  signature, not a calorimeter one.
- **Cosmic-ray or halo tracks** traversing the detector, which are fitted as two
  independent halves and compared; a coherent deformation appears as a mismatch.
- **Comparison of independent subdetectors** measuring the same track.
- **Field-reversal or detector-inversion running**, where available, which changes the
  sign of the physics effect but not of the instrumental one.

Every measurement sensitive to charge sign or to the high-rigidity spectrum should
state which of these constrains its charge-antisymmetric bias, and quote the resulting
limit as a systematic. See [tracking and vertexing](tracking-and-vertexing.md).

## Time dependence and conditions data

Detectors change: gains drift with temperature, sensors accumulate radiation damage,
gas composition and pressure vary, channels die, and alignment moves with thermal
cycles and magnet ramps. Calibration constants are therefore time-dependent payloads
indexed by run or by a finer interval-of-validity, and this creates its own set of
requirements:

- **Simulation must reproduce the time-averaged conditions**, weighted by the
  luminosity or exposure actually collected - not the conditions at any single moment.
  A simulation using a single snapshot of the dead-channel map or the gain set is
  systematically wrong for the dataset as a whole.
- **Analyses combining periods must confirm the constants were applied consistently**
  in each, and should check stability by repeating the measurement per period. A
  result that varies across periods beyond its statistical uncertainty has an
  unaccounted conditions problem, and finding it after unblinding is much worse than
  finding it before.
- **Reprocessing changes results.** A sample reconstructed with a newer payload is a
  different sample; mixing processings within one measurement requires explicit
  justification and a comparison.
- **Interval-of-validity boundaries are a real failure mode.** Data near a boundary
  can pick up the wrong payload if the intervals are misaligned with the run
  structure, producing a small population of badly-calibrated events that shows up as
  a non-Gaussian tail rather than a shift.

## Propagating a calibration change

Because a calibration constant sits at the base of the chain, changing it changes
efficiencies, resolutions, scale factors, background estimates derived from control
regions, and the trained response of any classifier that used the affected variables.
A calibration update is therefore not a local change:

- Re-derive, do not reuse, any scale factor or data-driven background estimate that
  was measured with the old constants.
- Re-validate classifiers whose input distributions have moved, following
  [multivariate-analysis-bdt-nn.md](../../physics-ml/references/multivariate-analysis-bdt-nn.md).
- Compare the affected distributions before and after with an explicit method - event
  counts per cut, histogram integrals, maximum absolute and relative bin difference -
  as required for any change that risks altering physics output.
- Keep the calibration uncertainty correlated across regions and samples where it
  shares a source; treating the same energy-scale uncertainty as independent between a
  signal and a control region is a standard way to understate a systematic. See
  [systematics.md](../../hep-analysis/references/systematics.md).

## Common misconceptions and failure modes

- **Tuning on the measured observable**, then reading agreement as validation (circularity).
- **Calibration order treated as irrelevant.** The order of the chain is part of the definition of each constant.
- **Test-beam constants applied unchanged in situ**, or a calibration applied to data but not simulation.
- **A good alignment `chi^2` taken as proof of correct alignment.** Weak modes leave it nearly unchanged.
- **Constants assumed static.** Intervals of validity, temperature, high voltage, and dose all move them.

## Deliverables

- The calibration chain in the order applied, with the payload version of each step.
- Which constants come from test beam and which from in-situ measurement, with the
  in-situ anchor point and the range over which it is extrapolated.
- The alignment procedure, the weak modes considered, and the external constraint
  bounding a charge-antisymmetric rigidity bias, with its quoted limit.
- Time dependence of the constants, and confirmation that simulation reproduces the
  exposure-weighted average conditions rather than a snapshot.
- A per-period stability check for any measurement combining data-taking periods.
- For any calibration update: what was re-derived, what was re-validated, and a
  before/after comparison of the affected distributions.
- Correlation treatment of calibration uncertainties across regions and samples.
