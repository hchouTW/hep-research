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
measurement, and which no amount of chi-square improvement will reveal. Because the offset is
additive in curvature, the relative bias `delta R/R ≈ -q R delta` grows linearly with rigidity,
mimicking or masking a spectral feature; charge-symmetric modes (a radial expansion, a field-scale
error) give a relative scale error constant in rigidity.

<!-- example: experiment-specific illustration -->
Three weak modes named in the CMS tracker alignment (JINST 9 (2014) P06009,
arXiv:1403.2286, sec. 4.4 and the summary) `[General method]`:

| Mode | Deformation | What the paper reports |
|---|---|---|
| twist | `Delta phi = tau z` | biases the track curvature `q/p_T`; controlled mainly by Z-boson decays (resonance mass with a common vertex) |
| sagitta (off-centring of layers and rings) | `(Delta x, Delta y) = sigma r (sin phi_sigma, cos phi_sigma)` | among the distortions most difficult to control; only partly recovered |
| skew | `Delta z = omega sin(phi + phi_omega)` | among the distortions most difficult to control |

Cosmic-ray tracks (which break the cylindrical symmetry), straight tracks taken with the
field off, vertex knowledge and resonance masses are the inputs the paper uses against
weak modes; the cosmic tracks have limited power against a twist.
<!-- /example -->

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
  sign of the physics effect but not of the instrumental one, in detector coordinates; in charge-signed curvature the instrumental bias is the term that flips.

Every measurement sensitive to charge sign or to the high-rigidity spectrum should
state which of these constrains its charge-antisymmetric bias, and quote the resulting
limit as a systematic. See [tracking and vertexing](tracking-and-vertexing.md).

### Calibration standards and their pitfalls

- **`E/p` with electrons**: bremsstrahlung lowers the track momentum and the track momentum scale enters directly;
  use it with a bremsstrahlung-aware track fit, in bins where both are controlled.
- **A resonance mass**: fit the line shape (natural width convolved with the resolution, with a final-state-radiation
  tail), not the peak position; a peak position moves with the resolution and the radiation.
- **Low-momentum scale**: the J/psi and Upsilon resonances anchor the scale at low transverse momentum, and the Z at
  higher; the extrapolation between them in pT is part of the uncertainty
  <!-- example: source citation -->
  (CMS muon performance, JINST 7 (2012) P10002, arXiv:1206.4071, section 6; read 2026-10-14).
  <!-- /example -->
- **MIP calibration**: use the most probable value of the Landau-like deposit with a path-length correction
  (`1/cos theta` for inclined tracks), not the mean, which is pulled by the tail (PDG RPP 2024, Passage of particles
  through matter).
- **Intercalibration**: pi0 and eta diphoton masses, or phi symmetry of the deposited energy, equalize channels; the
  absolute scale still needs a reference.
- **Hadronic calorimeters**: `E/p` of isolated single hadrons, with its own selection bias from the isolation cut.

## Time dependence and conditions data

Detectors change: gains drift with temperature, sensors accumulate radiation damage,
gas composition and pressure vary, channels die, and alignment moves with thermal
cycles and magnet ramps. Calibration constants are therefore time-dependent payloads
indexed by run or by a finer interval-of-validity, and this creates its own set of
requirements:

- **Simulation must follow the conditions run by run or period by period**: assign
  simulated events to runs or periods in proportion to the luminosity or exposure
  actually collected, each with that period's conditions (or simulate each period
  separately and combine them with exposure weights). Do not average the conditions
  themselves: in general `sum_t w_t R(theta_t) != R(sum_t w_t theta_t)`, especially for
  thresholds, dead channels and non-linear gain, and an averaged dead-channel mask
  describes no real detector state. A simulation using a single snapshot of the
  dead-channel map or the gain set is likewise wrong for the dataset as a whole.
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
  [multivariate-analysis-bdt-nn.md](../../hep-ml/references/multivariate-analysis-bdt-nn.md).
- Compare the affected distributions before and after with an explicit method - event
  counts per cut, histogram integrals, maximum absolute and relative bin difference -
  as required for any change that risks altering physics output.
- Keep the calibration uncertainty correlated across regions and samples where it
  shares a source; treating the same energy-scale uncertainty as independent between a
  signal and a control region is a standard way to understate a systematic. See
  [systematics.md](../../hep-measurement/references/systematics.md).

## Propagating a calibration residual

A calibration change is re-derived; a calibration *residual* (the uncertainty left after the best calibration, or a
weak-mode bound) is propagated as a systematic. Declare its form, then compute what it does to every bin:

| Form | Model | Effect on a power law `dN/dx ~ x^-gamma` |
|---|---|---|
| Scale | `x_m = (1+s) x` (energy or momentum scale) | every bin `(1+s)^(gamma-1) - 1 ~ (gamma-1) s`, the same in all bins |
| Inverse offset | `1/x_m = 1/x + q delta` (curvature offset, e.g. a weak mode) | density factor `(1 - q x delta)^(gamma-2)`, first order `(2-gamma) q x delta`: grows with x, opposite for the two charge signs |
| Resolution | core and tail widths scaled by `1 +/- r` | factor `E[(1+eps)^(gamma-1)]`, about `1 + (gamma-1)(gamma-2) sigma^2/2` for a Gaussian |

- **Opposite-sign ratios.** One curvature offset moves both operands, in opposite directions: the signed shifts
  subtract and their magnitudes add. A ratio does not cancel this residual; it doubles it. Same-sign operands with
  different spectral indices cancel only partly.
- **Validity.** The first-order inverse-offset form fails when `|q x delta|` approaches 0.3; at `q x delta >= 1` the
  mapping is no longer one-to-one and events change charge sign (see [charge-confusion.md](charge-confusion.md)).
- **No default size.** `s` or `delta` comes from the calibration itself (a reference line, E/p, a known-mass peak,
  the external constraint on a weak mode), never from a typical value.
- **Deliverables.** Per-variation yields and per-bin shifts, `{nominal, up, down}` for
  `check_systematic_variations.py` (with the variance of the *difference*, because the variations reuse the same
  events), a fully correlated covariance block, and the ratio shift. A validation record that states the
  correlation between operands is written only on request.

Tool: `propagate_scale_distortion.py` (`response`: analytic yields for power-law components; `events`: the same
distortions applied to an event table; modes `scale`, `inverse-offset`, `resolution`, `plugin`). A seeded test
sample comes from `toy_spectrometer.py`.

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
- Time dependence of the constants, and confirmation that simulation assigns events
  to runs or periods with their own conditions in proportion to the exposure (or
  combines per-period simulation with exposure weights), rather than using a snapshot
  or averaged conditions.
- A per-period stability check for any measurement combining data-taking periods.
- For any calibration update: what was re-derived, what was re-validated, and a
  before/after comparison of the affected distributions.
- Correlation treatment of calibration uncertainties across regions and samples.
