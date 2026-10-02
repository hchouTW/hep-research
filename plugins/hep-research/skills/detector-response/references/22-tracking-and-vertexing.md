# Tracking and Vertexing

Covers charged-particle trajectory measurement: the sensor technologies, how hits
become tracks, what the track fit actually estimates, and where tracking failures
enter an analysis as efficiency loss, fakes, or charge confusion. Builds on the
rigidity and multiple-scattering material in
[detector systems overview](21-detector-systems-overview.md); the downstream use of
reconstructed tracks in jets, b-tagging, and missing transverse momentum is in
[18-physics-objects-jets-btagging-met.md](18-physics-objects-jets-btagging-met.md).

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

Silicon position resolution is set by pitch and by charge sharing. A binary readout
(hit/no-hit) gives a resolution of pitch divided by the square root of twelve; analog
or multi-threshold readout that interpolates the charge division between neighboring
channels does substantially better, at the cost of calibration complexity - the
interpolation depends on the charge-sharing model, which is itself a calibration that
drifts with radiation damage and bias voltage.

Silicon also measures deposited charge, which is proportional to `Z^2` for a
traversing nucleus. A silicon tracker is therefore simultaneously a charge (|Z|)
measuring device, and multi-layer charge consistency is a powerful rejection tool
against interactions and against tracks built from mismatched hits - see
[particle identification](24-particle-identification.md) for the dE/dx treatment.

**Gaseous detectors** - time projection chambers, drift chambers, straw tubes -
measure ionization in a gas volume and reconstruct position from drift time, requiring
a known drift velocity and a start time. They offer very low material budget per
measurement and, in the TPC case, hundreds of samples along a track for excellent
dE/dx, at the cost of slower response and a drift-velocity calibration sensitive to
gas composition, temperature, and pressure. A drift-time measurement converts an
uncertainty in the event start time directly into a position bias common to all hits,
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
reference surface plus a curvature - from the collected hits. The **Kalman filter**
formulation is standard because it handles multiple scattering naturally: rather than
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

As introduced in [detector systems overview](21-detector-systems-overview.md), a
spectrometer's relative rigidity resolution combines an intrinsic-resolution term
that grows linearly with rigidity and a multiple-scattering term that is roughly
constant in rigidity (falling as `1/(beta p)` in angle, which translates to an
approximately rigidity-independent contribution to `sigma(R)/R` in the relativistic
regime). Added in quadrature they give a curve with a minimum at the crossover
rigidity, degrading in both directions.

The intrinsic term scales with the sensor resolution, inversely with the field
integral, and inversely with the square of the lever arm, which is why lever arm is
the most valuable quantity in a spectrometer design and why tracks that fail to reach
the outermost layer have sharply worse resolution. Selections requiring a full-span
track are therefore selecting on resolution, which correlates with the physics being
measured and must be accounted for in the efficiency correction.

`${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/multiple_scattering.py` evaluates the Highland scattering angle for a
material stack, the accumulated budget, and the crossover rigidity for a given
intrinsic resolution, which is the quickest way to check whether an observed
resolution curve is consistent with the detector's material.

## Charge confusion

At high rigidity, where `sigma(R)/R` approaches unity, the measured curvature can
change sign. The resulting **charge confusion** migrates particles into the
oppositely-charged sample and is a background whose rate is set by the resolution
function's tail, not its core. This is the practical reason a core-Gaussian resolution
description is inadequate: the confusion probability is entirely a tail property, and
a Gaussian extrapolation underestimates it, often by orders of magnitude.

Control it by measuring the tail directly rather than modeling it - using a
independent estimate of the same track (an independent subset of layers, or a second
tracking system), or a sample of known charge sign. Analyses of charge ratios,
antiparticle fractions, or any rare oppositely-signed species should treat charge
confusion as a dedicated background component in the likelihood, with its own
nuisance parameter, following
[05-backgrounds.md](../../hep-analysis/references/05-backgrounds.md).

## Vertexing

A vertex fit estimates a common origin for several tracks, and its resolution is
dominated by the extrapolation distance from the innermost measurement to the vertex -
which is why the innermost layer's radius and material budget dominate impact
parameter resolution, and why impact parameter resolution degrades at low momentum
where scattering in that first layer matters most.

The impact parameter - the distance of closest approach between a track and a
reference point - underlies displaced-vertex identification and lifetime-based
tagging. Its resolution has an approximately constant term from sensor precision plus
a scattering term falling with momentum, and quoting it without the momentum
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
[calibration and alignment](29-calibration-and-alignment.md).

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
