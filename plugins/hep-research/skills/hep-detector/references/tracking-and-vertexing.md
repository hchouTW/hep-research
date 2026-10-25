# Tracking and Vertexing

Covers charged-particle trajectory measurement: the sensor technologies, how hits
become tracks, what the track fit actually estimates, and where tracking failures
enter an analysis as efficiency loss, fakes, or charge confusion. Builds on the
rigidity and multiple-scattering material in
[detector systems overview](detector-systems-overview.md); the downstream use of
reconstructed tracks in jets, b-tagging, and missing transverse momentum is in
[physics-objects-jets-btagging-met.md](physics-objects-jets-btagging-met.md).

## Sensor technologies

**Silicon pixel and strip** detectors collect electron-hole pairs created by
ionization in a depleted semiconductor. Pixels give unambiguous two-dimensional
position at high occupancy and are used closest to the interaction point where track
density is highest; strips give one precise coordinate per sensor at much lower
channel count and cost, with the second coordinate obtained from a stereo layer at a
small crossing angle. That stereo arrangement introduces **ghost hits**: two genuine
particles crossing a stereo pair produce four candidate intersections, only two of
which are real. Ghost rate grows quadratically with occupancy, which is why strip
detectors are placed outside the highest-density region.

Silicon position resolution is set by pitch and by charge sharing. A binary readout (hit/no-hit)
gives about pitch divided by the square root of twelve for single-channel clusters; charge sharing
into two-channel clusters does better even without amplitudes, depending on incidence angle,
threshold and Lorentz drift; analog
or multi-threshold readout that interpolates the charge division between neighboring
channels does substantially better, at the cost of calibration complexity - the
interpolation depends on the charge-sharing model, which is itself a calibration that
drifts with radiation damage and bias voltage. Sharing also lowers the charge on each
channel, so hit efficiency at a threshold depends on the track position in the cell; the
efficiency-occupancy window for a given charge on the channel is in
[front-end electronics](front-end-electronics-and-signal-processing.md#thresholds-fake-hits-and-zero-suppression).

**Silicon response and radiation damage** (approximate; PDG RPP 2025, sec. 35.8). A
pair costs `w_i ≈ 3.65 eV`; a minimum-ionizing particle deposits most probably about
23 000 electrons (3.7 fC) in 300 um. The depletion depth is
`d = sqrt(2 eps (V + V_bi)/(N e))`, so full depletion of a thickness `d` needs about
`V ≈ e |N_eff| d^2/(2 eps)`. Bulk damage scales, to first order, with non-ionizing energy
loss expressed as 1 MeV neutron-equivalent fluence (`n_eq/cm^2`): the leakage current
grows as `alpha_I Phi_eq V` (`alpha_I ≈ 4e-17 A/cm` after the standard anneal), trapping
cuts the collected charge (effective trapping times of order 1 ns near `1e15 n_eq/cm^2`,
so electron collection is favoured), and space charge changes the depletion voltage,
with beneficial and then reverse annealing over months at room temperature. In a
magnetic field carriers drift at the Lorentz angle `tan alpha_L = r_H mu B` (`r_H` about
1.15 for electrons and 0.8 for holes at room temperature and small `B`). Leakage current
and its temperature scaling: [front-end electronics](front-end-electronics-and-signal-processing.md).
Treat damage constants as conditions data, not as these reference values.

Silicon also measures deposited charge, which is approximately proportional to `Z^2` (before readout saturation, quenching and delta-ray escape) for a
traversing nucleus. A silicon tracker is therefore simultaneously a charge (|Z|)
measuring device, and multi-layer charge consistency is a powerful rejection tool
against interactions and against tracks built from mismatched hits - see
[particle identification](particle-identification.md) for the dE/dx treatment.

**Gaseous detectors** - time projection chambers, drift chambers, straw tubes -
measure ionization in a gas volume and reconstruct position from drift time, requiring
a known drift velocity and a start time. They offer very low material budget per
measurement and, in the TPC case, hundreds of samples along a track for excellent
dE/dx, at the cost of slower response and a drift-velocity calibration sensitive to
gas composition, temperature, and pressure. A drift-time measurement converts an uncertainty in the
event start time into a common drift-*distance* bias: a common position shift along the drift
direction in a TPC, and in a drift chamber a radius bias whose sign in track coordinates depends on
the side of the wire ([glossary](detector-glossary.md), residual sign),
which the track fit will partly absorb into the trajectory parameters rather than
flagging - a class of error that shows up as an apparent alignment problem.

## From hits to tracks: pattern recognition

Pattern recognition is the combinatorial problem of deciding which hits belong to the
same particle, and it is where most tracking inefficiency and nearly all fake tracks
originate. Seeding starts from a small number of hits consistent with a plausible
trajectory; the seed is then extrapolated outward or inward, collecting compatible
hits within a search window that must account for multiple scattering and for the
current parameter uncertainty.

Two failure modes dominate and pull in opposite directions. Too tight a search window
loses hits after a scatter and truncates or splits the track, costing efficiency. Too
loose a window collects wrong hits, producing a track whose fit is contaminated -
often with a plausible chi-square, because the fit will shift the trajectory to
accommodate the outlier. The tuning between them is not neutral with respect to
physics: it is momentum dependent (low-momentum tracks scatter more and need wider
windows) and density dependent, so tracking performance is not a single number but a
function of momentum, direction, and local occupancy.

**Ambiguity resolution** follows: multiple track candidates sharing hits must be
reduced to a consistent set, typically by ranking on hit count and fit quality and
removing candidates that share too many hits with a better one. The shared-hit
threshold is a tunable parameter that directly trades duplicate tracks against
efficiency for genuinely nearby tracks, such as those in a dense jet core or a
collimated decay.

## The track fit

A track fit estimates trajectory parameters - typically a position and direction at a
reference surface plus a curvature - from the collected hits. The **Kalman filter** formulation is
standard because it handles multiple scattering naturally. It assumes Gaussian process noise;
electron bremsstrahlung is not Gaussian, so electrons need a Gaussian-sum filter or a dedicated
bremsstrahlung fit, and their track momentum is biased low with a long tail. Use the smoother for
unbiased residuals at every layer and outlier down-weighting for wrong hits: rather than
treating the trajectory as a single deterministic curve, it propagates the parameter
estimate and its covariance layer by layer, inflating the covariance at each material
crossing by the expected scattering. This makes the fit's own uncertainty estimate
depend on the material model - so an incorrect material description produces
incorrect, usually overconfident, track parameter errors, without any obvious symptom
in the fitted values themselves.

Several points routinely cause trouble:

- **The chi-square is not a sufficient quality measure.** A fit that absorbed a wrong
  hit by shifting the trajectory can have an unremarkable chi-square. Combine it with
  hit count, missing-layer pattern, and where available a charge-consistency or
  timing-consistency requirement.
- **Parameter errors are correlated.** The covariance between curvature and direction
  is large; propagating a momentum uncertainty into a derived quantity using only the
  diagonal element understates or overstates it depending on the derived quantity.
  Use the full covariance matrix.
- **The fit is biased at low momentum** by energy loss, which must be corrected during
  propagation using an assumed particle mass. That mass assumption is a hidden input:
  a track fitted under a pion hypothesis and then used as a proton has a small,
  systematic momentum bias.
- **Fitting quality varies across the detector.** Efficiency and resolution must be
  quoted differentially in the relevant variables, not integrated.

## Rigidity resolution and its two regimes

As introduced in [detector systems overview](detector-systems-overview.md), a
spectrometer's relative rigidity resolution combines an intrinsic-resolution term
that grows linearly with rigidity and a multiple-scattering term that is roughly
constant in rigidity (falling as `1/(beta p)` in angle, which translates to an
approximately rigidity-independent contribution to `sigma(R)/R` in the relativistic
regime). The **crossover** rigidity is where the two terms are equal; it is not the
minimum of their quadrature sum. If the scattering term were exactly constant the
sum would rise monotonically with rigidity; the minimum exists only because the
scattering term rises as `1/beta` at low rigidity, so it lies below the crossover and
depends on the particle mass. For the model `sigma(R)/R = sqrt((c/beta)^2 + (a*R)^2)`
with `1/beta^2 = 1 + (m/(z*R))^2` the minimum is at `R_min = sqrt(c*m/(z*a))`: with
`c = 0.01`, `a = 1e-3 /GV` and a proton, `R_min` is about 3.06 GV while the crossover
`c/a` is 10 GV. Resolution degrades on both sides of `R_min`.

The intrinsic term scales as `sigma_x * R / (B * L^2)`, i.e. with the sensor resolution
and inversely with the product of the field integral (`~ B*L`) and the lever arm `L`.
For `N` equally spaced points in a uniform field the Gluckstern estimates (approximate;
PDG Review of Particle Physics, "Particle detectors at accelerators", momentum
measurement: eq. (35.68), p. 112, RPP 2025, eq. (35.61), p. 109, RPP 2024, read 2026-10-21) are, with `p_T` in GeV/c, `B` in T and lengths in m, for unit charge:

    measurement: sigma(p_T)/p_T ~= sigma_x * p_T / (0.3 * B * L^2) * sqrt(720/(N+4))
    scattering:  sigma(p_T)/p_T ~= 0.016 / (0.3 * beta * B * L) * sqrt(L/X0)

PDG states the measurement term for many (N >= 10) uniformly spaced points; for N = 3
the exact coefficient is `8 sqrt(3/2) = 9.8`, not `sqrt(720/7) = 10.1`. Below N = 10, `multiple_scattering.py` reports the
exact coefficient for equally spaced points next to Gluckstern and warns (Gluckstern is 5.4% high at N = 4). `L` in the
measurement term is the track length projected onto the bending plane, and `X0` is a
length (the radiation length in g/cm^2 divided by the density, here in m). The
scattering term carries `beta` to the first power: PDG eq. 35.70 gives
`delta k_ms ~= 0.016 z / (L p beta cos^2 lambda) * sqrt(L/X0)`, and dividing by
`k = 0.3 z B / p_T` gives the line above at `lambda = 0` (PDG RPP 2025, sec. 35.12).

The scattering coefficient 0.016 GeV/c is the PDG value for this fit term; it differs
from the Highland 13.6 MeV coefficient (without its log factor; Highland is eq. (34.16), p. 16, of "Passage of
Particles Through Matter", RPP 2024) that `multiple_scattering.py` uses for its scattering term. The `1/L^2` dependence is why
lever arm is the most valuable quantity in a spectrometer design and why tracks that
fail to reach the outermost layer have sharply worse resolution. Selections requiring a full-span
track are therefore selecting on resolution, which correlates with the physics being
measured and must be accounted for in the efficiency correction.

`<plugin root>/skills/hep-detector/scripts/multiple_scattering.py` evaluates the Highland scattering angle for a
material stack, the accumulated budget, and the crossover rigidity for a given
intrinsic resolution, which is the quickest way to check whether an observed
resolution curve is consistent with the detector's material.

## Charge confusion

At high rigidity, where `sigma(R)/R` approaches unity, the measured curvature can
change sign. The resulting **charge confusion** migrates particles into the
oppositely-charged sample and is a background whose rate is set by the resolution
function's tail, not its core. This is the practical reason a core-Gaussian resolution
description is inadequate: the rate is set mainly by the resolution function's tail: a Gaussian
extrapolation of the core underestimates it, often by orders of magnitude, except near the MDR,
where the core itself contributes (the Gaussian core alone gives 0.135% at MDR/3, where `sigma(R)/R
= 1/3`).

Control it by measuring the tail directly rather than modeling it - using a
independent estimate of the same track (an independent subset of layers, or a second
tracking system), or a sample of known charge sign. Analyses of charge ratios,
antiparticle fractions, or any rare oppositely-signed species should treat charge
confusion as a dedicated background component in the likelihood, with its own
nuisance parameter, following
[backgrounds.md](../../hep-measurement/references/backgrounds.md). How the rate is measured and handed over:
[charge-sign confusion](charge-confusion.md).

## Vertexing

A vertex fit estimates a common origin for several tracks, and its resolution is
dominated by the extrapolation distance from the innermost measurement to the vertex -
which is why the innermost layer's radius and material budget dominate impact
parameter resolution, and why impact parameter resolution degrades at low momentum
where scattering in that first layer matters most.

The impact parameter - the distance of closest approach between a track and a
reference point - underlies displaced-vertex identification and lifetime-based
tagging. Its resolution has an approximately constant term from sensor precision plus a scattering
term falling with momentum (approximate: `sigma_d0 ≈ a ⊕ b/(p sin^{3/2} theta)` in the transverse
plane; for two layers at `r1 < r2`, `sigma_d0^2 ≈ ((r2 sigma_1)^2 + (r1 sigma_2)^2)/(r2 - r1)^2`
plus a scattering term `~ r1 theta_0`; take `a` and `b` from the profile), and quoting it without the momentum
dependence hides the regime where it matters. Secondary vertex finding must also
contend with material interactions producing genuine displaced vertices that are not
signal; a map of reconstructed vertices reproduces the detector material layout, and
that map is both a background to reject and a useful tool for validating the material
model against data.

## Alignment coupling

A track fit assumes it knows where the sensors are. Alignment errors propagate
directly into trajectory parameters, and the dangerous ones are not random
misplacements - which mostly inflate chi-square and are visible - but coherent
distortions that the fit can absorb without degrading chi-square at all. A systematic
deformation that mimics a curvature produces a rigidity bias that is
charge-antisymmetric, meaning it shifts positive and negative particles in opposite
directions and directly fakes a charge-ratio signal. These **weak modes** are
invisible to internal fit quality by construction and must be constrained with
external information - see
[calibration and alignment](calibration-and-alignment.md).

## Common misconceptions and failure modes

- **One resolution number.** Rigidity resolution has two regimes (multiple-scattering-dominated and measurement-dominated) with a crossover.
- **Charge confusion assumed negligible.** It grows steeply toward the maximum detectable rigidity.
- **Pattern-recognition efficiency quoted without fakes and duplicates.**
- **Alignment or field error mistaken for noise.** Coherent residual trends are systematics, not resolution.
- **Gaussian vertex errors** assumed when a mis-associated track or a nuclear interaction dominates the tail.

## Deliverables

- Tracker technology, layer layout, lever arm, and material budget per layer.
- Track selection actually applied (minimum hits, required layers, fit quality,
  charge consistency) and its efficiency measured differentially in momentum and
  direction, not integrated.
- Rigidity or momentum resolution as a function of rigidity, with the scattering and
  intrinsic regimes identified and the crossover stated.
- Maximum detectable rigidity and, for any charge-sensitive measurement, the charge
  confusion estimate with its measurement method and its treatment in the likelihood.
- Mass hypothesis used in the fit's energy-loss correction, where it affects the
  measurement.
- Impact parameter and vertex resolution quoted with momentum dependence.
- Alignment weak modes considered, and what external constraint bounds a
  charge-antisymmetric rigidity bias.
