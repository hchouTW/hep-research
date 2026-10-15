# Calorimetry: Electromagnetic and Hadronic

Covers destructive energy measurement - how showers develop, what sets the resolution,
why hadronic calorimetry is fundamentally harder than electromagnetic, and how
calorimeter information feeds particle identification. Assumes the material-budget and
resolution vocabulary of [detector systems overview](detector-systems-overview.md);
jet energy scale and its calibration are treated at the object level in
[physics-objects-jets-btagging-met.md](physics-objects-jets-btagging-met.md),
and the calibration machinery itself in
[calibration and alignment](calibration-and-alignment.md).

## The measurement, and why it complements tracking

A calorimeter absorbs a particle and measures the energy deposited. Its defining
property is that relative resolution *improves* with energy, roughly as `1/sqrt(E)`,
because the measurement is a count of shower constituents subject to Poisson
fluctuations. This is exactly opposite to a magnetic spectrometer, whose relative
resolution degrades with rigidity. The two are therefore complementary: tracking wins
at low momentum, calorimetry wins at high energy, and the crossover is a basic design
parameter of any experiment that has both. A calorimeter also measures neutral
particles, which leave no track at all.

## Electromagnetic showers

A high-energy electron or photon initiates a cascade: bremsstrahlung and pair
production alternate, roughly doubling the number of particles every radiation length
`X0`, while the average energy per particle halves. The cascade stops multiplying at
the **critical energy**, below which ionization loss overtakes radiative loss, and the
remaining particles are absorbed.

Approximate scales, with `Z`, `A` the absorber's atomic number and atomic mass (g/mol)
(empirical fits from the PDG Review of Particle Physics, "Passage of particles through
matter", radiation length and electromagnetic cascades; use the PDG tabulated material
values when they exist):

    X0    ~= 716.4 * A / (Z * (Z + 1) * ln(287 / sqrt(Z)))   g/cm^2
    E_c   ~= 610 MeV / (Z + 1.24)    (solids and liquids; 710 MeV / (Z + 0.92) for gases)
    R_M   ~= X0 * (21.2 MeV / E_c)
    t_max ~= ln(E / E_c) + C   (in X0; C = -0.5 for electrons, +0.5 for photons)

Two consequences matter for design and for analysis. Shower *depth* grows only
logarithmically with energy - measured in `X0`, the depth of shower maximum scales as
`ln(E)` - so a calorimeter deep enough for a given energy remains adequate over a wide
range, and depth requirements are modest. Shower *width* is set by the Molière radius,
which is a material property largely independent of energy, so lateral containment is
essentially an energy-independent geometric requirement. Because the Molière radius
sets the transverse scale, granularity finer than it buys shower-shape discrimination,
not better energy resolution.

Longitudinal and lateral shower shape are the basis of calorimeter-level particle
identification. Electromagnetic showers are compact, start early, and deposit a
characteristic longitudinal profile; hadronic showers are deeper, broader, and more
irregular. Discriminants built from the depth of shower maximum, the fraction of
energy in the first layers, and the lateral spread separate electrons and photons from
hadrons with rejection factors that can be large but are strongly
energy-dependent - and are exactly the kind of variable that a classifier will exploit
and that must therefore be validated for data/MC agreement before use, following
[multivariate-analysis-bdt-nn.md](../../hep-ml/references/multivariate-analysis-bdt-nn.md).

## Homogeneous versus sampling calorimeters

A **homogeneous** calorimeter is built entirely of active material, so in principle
every shower particle contributes to the signal; the stochastic term can be very small.
A **sampling** calorimeter interleaves dense passive absorber with thinner active
layers and measures only the fraction of the shower crossing the active material. The
sampling fraction introduces an additional, dominant Poisson fluctuation - the
**sampling term** - which is the price paid for compactness, cost, and the ability to
build a deep hadronic section.

The practical distinction for analysis is that a sampling calorimeter's energy scale
depends on the sampling fraction, which is *not* the same for electromagnetic and
hadronic showers. That difference is the origin of the non-compensation problem below.

## The resolution decomposition

Calorimeter energy resolution is conventionally parameterized as three terms added in
quadrature:

    (sigma_E / E)^2 = a^2 / E + b^2 / E^2 + c^2

- **`a`, the stochastic (sampling) term** - Poisson fluctuations in the number of
  detected shower constituents. Dominates at low energy.
- **`b`, the noise term** - electronic noise and, at a collider, pileup energy inside
  the reconstruction cone. It enters as a fixed energy uncertainty, so its *relative*
  contribution falls as `1/E`. It is the term that grows when pileup increases, and
  the reason optimal cluster size is pileup-dependent. Coherent noise makes the
  cluster noise grow faster than `sqrt(N_cells)`, and the pileup part follows
  Campbell's theorem ([front-end electronics and signal processing](front-end-electronics-and-signal-processing.md)).
- **`c`, the constant term** - calibration non-uniformity, channel-to-channel
  intercalibration error, hardware non-uniformity (dead material, cracks, temperature
  and light-collection variations), energy leakage (only approximately: leakage grows with energy and adds a low-side tail that a constant term does not describe), and in hadronic calorimeters the
  fluctuations of the electromagnetic fraction when `e/h != 1` (non-compensation). It
  does not improve with energy and therefore *sets the ultimate high-energy
  performance*. A calorimeter's high-energy precision depends on calibration and
  uniformity as much as on the detector technology.

The most common analysis error here is quoting a stochastic term alone and
extrapolating it to high energy, which predicts an arbitrarily good resolution that
the constant term forbids. `<plugin root>/skills/hep-detector/scripts/calorimeter_resolution.py` fits all three terms
from measured points and reports which one dominates at a given energy and where the
crossovers lie; note that the parameterization is *linear* in `(a^2, b^2, c^2)` over
the basis `{1/E, 1/E^2, 1}`, so the fit is an exact linear least squares with no minimizer and no
starting values required. A squared coefficient can come out negative on noisy or narrow-range data;
the script reports it as a failure. Do not clip it to zero.

Fitting fewer than three distinct energies cannot separate three terms, and fitting
over a narrow energy range gives strongly correlated parameters even when it converges:
quote the covariance, or at least the range fitted, alongside the values.

## Hadronic showers and non-compensation

A hadronic shower develops through nuclear interactions over the interaction length
`lambda_I` (roughly `35 * A^(1/3)` g/cm^2, a rough empirical scaling; PDG tabulates
the values per material), which is much larger than `X0` in dense absorbers - so hadronic
calorimeters are far deeper than electromagnetic ones, and shower fluctuations are
much larger.

The dominant complication is that a hadronic shower contains a variable
**electromagnetic fraction**, mostly from neutral pions decaying to photons, which
develop as electromagnetic sub-showers. That fraction fluctuates event to event and
rises with energy. Meanwhile, part of the purely hadronic energy is *invisible* - spent
on nuclear binding energy, slow neutrons, and nuclear fragments - and is not detected.

If the calorimeter's response to the electromagnetic component differs from its
response to the hadronic component (the ratio conventionally written `e/h` differs from
1, the **non-compensating** case, which is the usual case), then the measured energy
depends on the fluctuating electromagnetic fraction `f_em`. The pion-to-electron
response ratio is (approximate; PDG Review of Particle Physics, "Calorimetry")

    pi/e = f_em + (1 - f_em) * h/e

This produces three effects simultaneously, and they are often confused:

- **Degraded resolution**, because the electromagnetic fraction fluctuates.
- **Non-linearity**, because the mean electromagnetic fraction rises with energy, so
  the response is not a constant times the true energy.
- **Non-Gaussian response**, with tails that a Gaussian resolution parameterization
  understates.

Compensation can be approached by hardware design or recovered offline by weighting
techniques that estimate the electromagnetic fraction from the shower's measured
density and correct each deposit accordingly. Either way, the hadronic energy scale is
a *derived, calibrated* quantity with its own substantial uncertainty, and it is
routinely one of the leading systematics in any analysis using jets or missing
transverse momentum - which is why jet energy scale and resolution get their own
variation treatment in
[systematics.md](../../hep-measurement/references/systematics.md).

**Routes to compensation** (PDG RPP 2025, sec. 35.10.3): a high-Z absorber, which
lowers the electromagnetic response, with a hydrogenous active medium (organic
scintillator) whose sensitivity to spallation neutrons tracks the invisible energy,
at a carefully chosen sampling fraction and integration time; fission in uranium
absorbers adds signal; dual readout uses Cherenkov light, produced mainly by the
electromagnetic component, next to scintillation to estimate `f_em` per event; offline
(software) weighting uses longitudinal or fine-grained shower information; particle flow
replaces calorimeter measurements of charged hadrons by tracks. Intrinsically compensating
calorimeters are not used in current large collider experiments.

## Leakage, dead material, and containment

Energy that escapes the calorimeter is not measured. **Longitudinal leakage** (punch
through the back) produces a low-side tail that grows with energy and is the practical
limit on how far a calorimeter's calibration can be extrapolated. **Lateral leakage**
outside the reconstruction cluster is a clustering choice, and trades against the noise
and pileup term - a larger cluster recovers energy but collects more noise. For
electromagnetic showers about 90% of the energy lies on average within one Molière
radius `R_M` and about 99% within `3.5 R_M` (PDG RPP 2025, sec. 34.5). **Dead
material** upstream or between compartments absorbs energy invisibly and must be
corrected using the observed energy sharing between compartments.

All three are energy-dependent and direction-dependent, so a single global correction
is inadequate; corrections are normally parameterized in energy and pseudorapidity or
polar angle, and their residual uncertainty flows into the constant term.

## Calorimeter-based identification

Beyond shower shape, the ratio of calorimeter energy to track momentum, `E/p`, is a
powerful identifier: it is near 1 for electrons (which deposit all their energy electromagnetically
and have a measured track; without bremsstrahlung recovery the track momentum is biased low and
`E/p` has a tail above 1) and much smaller for hadrons, which
deposit only part of their energy in the electromagnetic section. `E/p` is also the
standard in-situ handle for cross-calibrating the calorimeter energy scale against the
tracker momentum scale - a check that is only as good as the tracker's own alignment,
so a disagreement in `E/p` is not automatically a calorimeter problem. See
[particle identification](particle-identification.md) for how this combines with
the other identification systems.

## Common misconceptions and failure modes

- **The stochastic term treated as universal** across energies and detectors; noise and constant terms dominate at the extremes.
- **`e/h = 1` assumed**, or single-hadron calibration assumed to equal jet calibration.
- **Leakage and dead material ignored**, then absorbed into the constant term.
- **Noise thresholds that bias low-energy clusters** upward or clip them.
- **Scale, linearity, uniformity, resolution, tails, and category migration conflated.**

## Deliverables

- Calorimeter type (homogeneous or sampling), absorber and active material, depth in
  `X0` and `lambda_I`, and transverse granularity relative to the Molière radius.
- Resolution quoted as all three terms with the energy range over which they were
  fitted and their correlations, not a stochastic term alone.
- For hadronic measurements: whether the calorimeter is compensating, what offline
  weighting is applied, and the resulting non-linearity and its uncertainty.
- Leakage and dead-material corrections applied, with their energy and angular
  dependence.
- Shower-shape or `E/p` discriminants used for identification, with data/MC agreement
  demonstrated in a control region before they are relied on.
