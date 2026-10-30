# Gaseous and Specialized Tracking Technologies

Technology-specific reconstruction for trackers beyond the general treatment in
[tracking and vertexing](tracking-and-vertexing.md): drift chambers and tubes, TPCs, MWPCs, straw
trackers, RPCs, micro-pattern gaseous detectors (GEM, Micromegas), scintillating
fibers, nuclear emulsions, monolithic and other silicon variants, and radiation-hard
sensors. Physics of signal formation is in
[signal formation and readout](signal-formation-and-readout.md); alignment and drift calibration in
[calibration and alignment](calibration-and-alignment.md). Each family ends with the required
**Distinctive but generalizable reconstruction and performance features** block.

## Silicon pixels and strips (recap of what is distinctive)

**Hybrid pixels**: 2D binary or ToT-encoded hits; charge sharing among neighbors
gives sub-pixel position by centroid or by template (charge-profile) fit; the
**Lorentz drift** shifts and broadens clusters in a field (calibrate `theta_L`);
merged clusters at high density; radiation damage lowers `CCE` and shifts thresholds
and depletion voltage.

**Strips/microstrips**: 1D measurement; a 2D point needs a stereo pair, creating
`n^2` candidate intersections for `n` hits, of which `n^2 - n` are ghosts; capacitive coupling, common-mode noise, and
occupancy dominate ambiguity.

**MAPS, depleted MAPS, CCD, DEPFET**: sensor and first amplification integrated, so
low material and small pitch (excellent vertexing) at the price of slower or
rolling readout (integration-time ambiguity, hit-time association) and, for MAPS,
smaller depleted region (less charge, more diffusion-driven sharing).

### Distinctive but generalizable reconstruction and performance features (silicon)

- **Information topology**: sparse points with cluster structure.
- **Unique inverse problem**: position from shared charge; degeneracy: ghosts
  (strips), merged clusters (pixels).
- **Natural objects**: cluster, hit, track seed. **Most informative residual**:
  unbiased track-to-hit residual in the sensor's measurement direction, versus
  incidence angle and cluster size.
- **Scaling**: hit resolution `~ pitch/sqrt(12)` (binary, approximate) improved by charge
  sharing; momentum and impact-parameter floors from multiple scattering and lever
  arm ([tracking and vertexing](tracking-and-vertexing.md)).
- **Tails**: delta rays, merged clusters, noise hits, dead/noisy channels.
- **Dependence**: occupancy, pileup, dose (leakage, `CCE`, threshold, Lorentz angle
  drift), temperature. **Data sample**: `Z -> ll`/cosmic tracks for hit efficiency
  and alignment, overlaps and tag-and-probe for module efficiency.
- **Transfers**: charge-sharing interpolation and template methods to any segmented
  readout (TPC pads, fibers); does not transfer: time-of-arrival coordinates.

## Drift chambers and drift tubes

**Measurement.** Time `t` between passage and arrival at a sense wire is converted to
distance by the **time-to-distance relation** `r(t)` (space-time relation), calibrated
per cell and per operating condition (`v_d` depends on gas, `T`, `P`, `E`, `B`; the
relation is nonlinear near the wire and cell boundary).

**Pieces.** `t0` (event/particle passage time relative to the clock), time walk
(amplitude-dependent discriminator delay), signal propagation along the wire, wire
**sag** (gravitational/electrostatic), and stereo/small-angle wires for the second
coordinate. A drift measurement gives a *radius*, not a point: **left-right
ambiguity** (the particle passed one side of the wire or the other), resolved by
adjacent-layer staggering, by segment or track fit, or by wire signal timing.

**Reconstruction.** Segment building within a chamber (line fit through
`(z, +-r)` circles with a two-fold ambiguity per layer), then linking segments to
tracks.

**Diagnostics.** Residual versus drift distance (the standard plot): state the residual convention
([glossary](detector-glossary.md): signed track coordinate). In the signed coordinate a `t0` offset
gives opposite-sign residuals for left and right passages, a drift-velocity error a residual growing
with distance, and a wire offset the same sign on both sides; in the unsigned drift radius the `t0`
and wire-offset patterns swap. `t0` and alignment become degenerate when one side dominates the
track population or the geometry is fixed. Residual versus
angle and versus amplitude reveal time walk and crossing-angle effects.

### Distinctive but generalizable reconstruction and performance features (drift systems)

- **Topology**: sparse radius measurements (hits are circles around wires).
- **Inverse problem**: `r` from `t` needs `v_d`, `t0`, geometry; degeneracy:
  left-right, wire-position (sag), `t0` versus alignment (a timing offset looks like
  a spatial shift - see [calibration and alignment](calibration-and-alignment.md)).
- **Objects**: drift circle, segment, track. **Informative residual**: residual
  versus drift distance and versus angle.
- **Scaling**: single-hit resolution limited by diffusion (`~ sqrt(L)`), primary
  ionization statistics near the wire, electronics; efficiency drops near cell boundary
  and wire.
- **Tails**: two mechanisms with opposite signs. Primary-cluster statistics: the
  nearest cluster can lie farther from the wire than the track's closest approach, so
  the time is late and the distance overestimated (largest near the wire). Delta rays:
  a delta electron can deposit charge closer to the wire, so the time is early and the
  distance underestimated. Also out-of-time hits.
- **Dependence**: rate/occupancy (space charge, deadtime), `T`/`P`/gas composition
  (drift velocity), aging (Malter effect, deposits on wires).
- **Data sample**: cosmic rays and collision tracks for `r(t)` self-calibration.
- **Transfers**: time-to-distance calibration to muon tubes, straws and TPC drift coordinates;
time-difference coordinates (RPC strip ends, TOP) reuse the offset and velocity calibration logic; does not transfer: charge-centroid interpolation.

## Time projection chambers (TPC)

**Principle.** Ionization electrons from a track drift in a uniform `E` (and often
parallel `B`) to a readout plane: the transverse coordinates come from where they
arrive, the third from arrival time (`z = v_d (t - t_0)`), giving a continuous 3D
image and many `dE/dx` samples per track.

**Pieces.** Diffusion (transverse `~ sqrt(L)`; reduced by `B`), gain stage
(wires, GEM, Micromegas), **ion backflow** (positive ions drifting back distort `E`),
**space-charge distortions** (a radially and `z`-dependent position shift), field-cage
and `E x B` distortions, gating, and **crossing-time ambiguity**: the absolute drift
coordinate needs the interaction time `t_0`, unknown for particles not associated with
a bunch crossing or trigger (pileup/out-of-time tracks are displaced along `z`).

**`dE/dx`.** Truncated mean or cluster counting over `~10^2` samples, corrected for
path length, saturation, gain, and attachment ([particle identification](particle-identification.md)).

### Distinctive but generalizable reconstruction and performance features (TPC)

- **Topology**: dense 3D point cloud/image; many samples per track.
- **Inverse problem**: 3D position and `t_0`; degeneracies: `z` vs `t_0`; distortion
  vs alignment.
- **Objects**: cluster, track, `dE/dx` vector. **Informative residual**: cluster-to-track
  residuals vs radius/`z`/`phi`, and matching to an outer (or inner) precision tracker
  as a distortion map.
- **Scaling**: `sigma_xy ~ sqrt(sigma_0^2 + C_D^2 L/N_eff)`; momentum resolution from
  lever arm and `B`, with a stable multiple-scattering term; `dE/dx` resolution improves
  with the number of samples.
- **Tails**: track merging at high density, distortion-induced tails, `z` offset for
  out-of-time tracks.
- **Dependence**: rate and ion backflow (space charge), `T`/`P`, gas purity (attachment
  and diffusion), field homogeneity. **Data sample**: laser/UV lines or cosmic tracks and
  cross-detector matching to map distortions.
- **Transfers**: drift-plus-readout concept to noble-liquid TPCs
  ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)) and any imaging detector;
  does not transfer: gas-specific diffusion and ion-backflow numerology.

## MWPCs, straw tubes, and RPCs

- **MWPC**: wire planes with proportional gain; hit position from the wire (pitch/`sqrt(12)`)
  or from induced cathode charge for the second coordinate; fast, robust; limited
  granularity and rate by wire pitch and space charge.
- **Straw-tube tracker**: many thin drift tubes; combination of drift measurement and a
  large number of hits per track (good tracking robustness at low material); also the
  basis for transition radiation stacks (electron ID, [particle identification](particle-identification.md));
  left-right ambiguity per straw resolved by staggered layers.
- **RPC / multi-gap RPC (MRPC)**: resistive plates with a gas gap and a high
  uniform field; fast signal from a streamer/avalanche, strip readout, timing resolution
  much better than a drift chamber (in MRPC many narrow gaps); efficiency and time
  resolution depend on rate (plate resistivity limits rate capability), gas mixture, and
  applied voltage; used for trigger muon layers and time of flight ([timing detectors](timing-detectors.md),
  [muon systems](muon-systems.md)).

### Distinctive but generalizable reconstruction and performance features (wire/RPC)

- **Topology**: sparse points/segments. **Ambiguity**: left-right (straws), ghosts
  (wire crossing), efficiency dead zones at wire/cell edges and spacer positions.
- **Informative residual**: layer-by-layer (unbiased) residual versus position in the
  cell. **Scaling**: RPC rate capability inverse to resistivity; timing set by gap
  width and gas.
- **Tails**: streamers, afterpulses, cluster-size multiplicity growth with high
  voltage. **Data sample**: cosmic/collision muons for efficiency versus voltage
  (efficiency-plateau scan).
- **Transfers**: plateau-scan concept (efficiency vs voltage) to every gas detector.

## Micro-pattern gaseous detectors (GEM, Micromegas, and relatives)

**Principle.** Micro-structured gain (GEM holes; Micromegas mesh over a narrow
amplification gap) gives high rate capability, fine pitch, and fast signals compared with
wires. **Reconstruction.** Pad/strip charge centroid or template; cluster size and
charge sharing set position resolution; a mesh-anode gap gives, in **micro-TPC** mode
(drift plus fine gap), a track segment per chamber and thus angle information.

**Failure/response features.** Gain nonuniformity (hole/gap geometry), **discharges**
(sparks that cause dead time and can damage readout), charge spreading, **rate
effects** (space charge, gain drop), and time resolution set by gap and gas.

### Distinctive but generalizable reconstruction and performance features (MPGD)

- **Topology**: pad/strip images. **Ambiguity**: 2D projections (strips) and
  charge-sharing symmetry. **Informative residual**: residual vs incident angle
  (strong dependence for inclined tracks unless micro-TPC mode is used).
- **Scaling**: position resolution ~ (pitch and diffusion)/`sqrt(cluster size)` (heuristic);
  rate capability set by gain and space charge.
- **Tails**: discharge events, gain-nonuniformity-induced position biases.
- **Data sample**: cosmic/test-beam and in-situ tracks for gain map.
- **Transfers**: charge-centroid/micro-TPC to other segmented gas detectors.

## Scintillating-fiber trackers

**Principle.** Light from a scintillating fiber is guided to a photosensor (SiPM
array, [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md)); multi-layer stacks at a
small stereo angle provide two coordinates. **Distinctive**: light attenuation along
the fiber (position along the fiber changes amplitude), light sharing between adjacent
fibers (used for sub-pitch position), **multi-layer ambiguity** (ghost hits in
stereo), channel-mapping errors, SiPM noise/crosstalk and radiation-induced dark count,
and time information that can assist matching in high rate. Resolution ~ fiber pitch
`/sqrt(12)` improved by light sharing; efficiency depends on attenuation and threshold.

### Features (fibers)

- **Topology**: sparse points with amplitude. **Residual**: hit-to-track by layer and
  versus position along fiber (attenuation signature).
- **Tails**: ghosts, cross-talk clusters, mapping errors, dark-count hits.
- **Dependence**: dose (SiPM dark rate), temperature (gain), rate.
- **Transfers**: amplitude-based interpolation and attenuation correction to
  scintillator calorimeters and timing layers.

### Fibre-tracker reconstruction

- **Clusters.** Adjacent fibres above threshold form a cluster whose position is the
  amplitude-weighted centroid (light sharing gives sub-pitch position). The cluster size
  grows with the track angle; clusters wider than expected (cross-talk, showers, two close
  tracks) are flagged or split. One view gives no position along the fibres.
- **Ghosts and track finding.** Two views at a stereo angle give a point, but `n` tracks
  give up to `n^2` view intersections, most of them ghosts. They are resolved by a third
  view, by requiring consistency in all stereo layers at the track level, and by hit time
  where it is measured. Finding usually proceeds in the measured (bending) projection
  first, with seeds and search windows sized for the momentum range, and then adds the
  stereo hits to obtain the second coordinate (a standalone example: Aiola et al., Comput.
  Phys. Commun. 260 (2021) 107713). The generic strategies are in
  [tracking and vertexing](tracking-and-vertexing.md#track-finding-strategies).
- **Parameters.** Once the coordinate along the fibre is known from the stereo layers, the
  amplitude is corrected for attenuation and the time for propagation along the fibre; the
  fit is iterated. Fibre-mat positions and their shape (bending or sagging of long modules)
  are alignment parameters.
- **Position at a vertex.** Fibre layers far from the interaction are matched to upstream
  track segments within a window; where fibres form an active target, the vertex is the
  intersection of fitted tracks, with a resolution set by the pitch and the lever arm.

**Check:** The clustering rule, the ghost-resolution method, the attenuation and
propagation corrections and the fibre-mat alignment are stated, with the ghost rate
measured.

## Nuclear emulsions

**Principle.** Ionizing particles sensitize silver-halide grains; development
produces **grains**, chained into **microtracks** in each emulsion layer, linked across
the plastic base into **base-tracks**, then into tracks and **vertices**. Spatial
resolution is superb (sub-micron grain scale), giving unmatched vertex/kink topology,
but there is **no intrinsic timing** (integrated over exposure) so track-to-event
association relies on electronic detectors, and analysis is dominated by scanning
efficiency, track density (overlap), fading, and distortion of the emulsion.

### Features (emulsion)

- **Topology**: dense micro-scale 3D image with no time axis.
- **Inverse problem**: link tracks across layers; degeneracy: time assignment.
- **Informative residual**: base-track slope/position agreement between
  layers; **scaling**: resolution set by grain size and layer alignment; limits by
  fluence (track overlap).
- **Tails**: fake links at high density, scanning inefficiency near edges.
- **Data sample**: passing-through tracks (cosmic/beam) for alignment;
  **transfers**: precise-vertex and kink analysis to silicon vertex detectors; **does
  not transfer**: event timing.

### Emulsion reconstruction

- **Microtracks.** The scanning microscope takes tomographic images at several focal
  depths in each emulsion layer; grains aligned across the images form a microtrack.
  Randomly developed fog grains form fake microtracks at a rate set by the fog density
  and the slope acceptance.
- **Base-tracks.** The microtracks on the two sides of the plastic base are linked when
  their projections agree in position and slope. The base-track slope is taken from the
  two base-side points, which is precise because the base does not shrink. The emulsion
  layer does shrink on development, so microtrack slopes are rescaled by a shrinkage
  factor measured with base-tracks.
- **Alignment and volume tracks.** Films are aligned with many passing-through tracks
  (an affine transformation per film: shift, rotation, expansion). Base-tracks are then
  connected across films within position and slope tolerances that allow for scattering
  in the passive material between films (Arrabito et al., J. Instrum. 2 (2007) P05004).
  Allowing a missing film recovers scanning inefficiency at the cost of more fake links;
  the background of tracks accumulated over the exposure sets the fake-link rate.
- **Momentum without a field.** Momentum comes from multiple Coulomb scattering along the
  track: from the angle differences between consecutive base-tracks (angular method; De
  Serio et al., Nucl. Instrum. Methods A 512 (2003) 539) or from the position deviations
  (coordinate method). The resolution depends on the number of films crossed, and the
  method saturates at high momentum, where the scattering falls below the measurement
  error, so the measurement has an upper limit like a spectrometer's maximum detectable
  rigidity.
- **Vertices.** A track predicted by an electronic detector is followed back film by film
  to its stopping point; the vertex is where several volume tracks converge within an
  impact-parameter cut, and short-lived particles appear as kinks or secondary vertices.
  The event time comes only from the electronic detectors.

**Check:** The scanning and linking tolerances, the shrinkage and alignment corrections,
the momentum method with its saturation, and the vertex-location efficiency are stated,
with the fake-link rate measured on the exposed background.

## Diamond and other radiation-hard sensors

Diamond and other wide-bandgap sensors (e.g. silicon carbide) offer low leakage current and
tolerance to very high fluence at the cost of smaller signal and lower charge
collection in poly-crystalline material. Reconstruction is the same as for silicon
(cluster/charge or timing), with the focus on **response versus dose** (pumping,
priming, polarization), efficiency loss with fluence, and beam/luminosity monitor
use. Quote fluence-dependent signal loss only with its source and conditions
([timing detectors](timing-detectors.md), [data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md)).

## Common misconceptions and failure modes

- **Left-right ambiguity resolved by hoping.** It must be resolved by geometry or fit; a
  wrong choice produces a systematic residual sign structure.
- **Hiding `t0` in alignment (or vice versa).** A timing offset displaces drift-coordinate
  measurements just like a misalignment ([calibration and alignment](calibration-and-alignment.md)).
- **TPC distortion mistaken for resolution.** Coherent, position-dependent shifts appear
  as broadened or biased residuals, not as noise.
- **Plateau efficiency taken as a quality measure across rate.** RPC/MPGD efficiency
  degrades with rate; measure at operating rate.
- **Emulsion has no timing.** Analyses that need timing must import it from other
  detectors and inherit their systematic.
- **Neglecting angle dependence in MPGDs.** Position bias grows with track inclination.

## Deliverables

- The technology's natural residual and the essential performance plots, with the
  failure signature each catches.
- The ambiguity resolved (left-right, ghost, `t_0`) and how.
- Efficiency versus voltage/rate/occupancy and the operating point.
- The distinctive-but-generalizable block for each family used.
- For fibre trackers, the ghost rate and fibre-mat alignment; for emulsion, the linking
  tolerances, fake-link rate, momentum method and vertex-location efficiency.
