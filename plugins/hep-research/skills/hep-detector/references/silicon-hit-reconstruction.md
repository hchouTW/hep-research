# Silicon Hit Reconstruction

From pixel and strip signals to hits: clustering and splitting, two-coordinate readout, hit position (centre
of gravity, eta correction, head-tail and end-pixel estimators, templates), the Lorentz shift, cluster size and
resolution versus angle, and nuclear charge from cluster charge. Sensors, radiation damage, ghosts:
[tracking and vertexing](tracking-and-vertexing.md#sensor-technologies),
[silicon recap](gaseous-and-specialized-tracking-technologies.md#silicon-pixels-and-strips-recap-of-what-is-distinctive);
thresholds and zero suppression:
[front-end electronics](front-end-electronics-and-signal-processing.md#thresholds-fake-hits-and-zero-suppression);
common mode: [noise](front-end-electronics-and-signal-processing.md#noise);
dE/dx: [particle identification](particle-identification.md#ionization-energy-loss-dedx); many layers into one
charge: [multisample PID](multisample-pid-and-reference-pdfs.md); alignment and pulls:
[in-situ alignment](in-situ-alignment-and-momentum-scale.md),
[performance metrics](performance-metrics-and-residual-diagnostics.md#residuals-pulls-and-their-covariance).
Fitting the Lorentz angle or charge sharing of a simulation to data is simcal, owned by hep-statistics
([tracker simcal](simulation-calibration/tracker.md)); training a splitting or charge network is hep-ml's
([multivariate analysis](../../hep-ml/references/multivariate-analysis-bdt-nn.md)). Space:
[space-based direct detection](space-based-direct-detection.md).

Environments: COL collider; FXT fixed target, test beam; SPC space, balloon; UGD underground; GND ground arrays;
NUC nuclear. Pitch, thickness, floating strips, field, noise, occupancy, fluence and angle range are parameters.
Source IDs: `arxiv_<id>` is arXiv:<id> with `/` written `_`; `pdg_2025_<review>` is the PDG 2025 review.
Entries are in the [bibliography](detector-principles-bibliography.md).

## Relations

- **Centre of gravity** (exact as a definition, biased as an estimator; arXiv:2209.03006 sec. 2):
  `x_cog = sum_i S_i x_i / sum_i S_i` over the cluster channels. A noise-weighted form uses `S_i / N_i`
  (arXiv:1712.02739 sec. 4.1). It is pulled toward the channel centres when charge division is non-linear.
- **Eta** (exact, a definition; arXiv:hep-ex/0212037 sec. 5.1, eq. 3; arXiv:2603.25080 sec. 3.1, eq. 1):
  `eta = S_R / (S_L + S_R)` from the two highest adjacent channels.
- **Eta correction** (exact under its assumptions: uniform illumination across the pitch within one angle bin
  and charge range; arXiv:hep-ex/0212037 sec. 5.1, eqs. 4-5; arXiv:2603.25080 sec. 4.2, eqs. 3-4):
  `f(eta_0) = (1/N) integral_0^eta_0 (dN/deta) deta`, `x = x_L + p f(eta)`, `p` the readout pitch, `x_L` the
  left channel. A non-flat `dN/deta` under uniform illumination signals non-linear sharing (for example floating
  strips). `dN/deta` changes with `Z`: wider charge clouds make the central peaks less pronounced
  (arXiv:2603.25080 sec. 4.2, p. 18), so `f` is built per charge range and per angle bin.
- **Binary resolution** (approximate: single-channel clusters, uniform illumination; arXiv:2603.25085 sec. 4.3,
  p. 4): `p / sqrt(12)`. With one floating strip between readout strips the digital reference is
  `p / (2 sqrt(12))` (arXiv:2209.03006 sec. 3). A cluster much wider than expected and incompatible with it
  takes its width over `sqrt(12)` as its position uncertainty (arXiv:1405.6569 sec. 3.2, p. 10).
- **Head-tail** (approximate, for wide clusters; arXiv:hep-ex/0212037 sec. 7.1, eq. 12):
  `x = (x_head + x_tail)/2 + p (S_tail - S_head) / (2 <S>)`, head and tail the first and last channels above
  threshold, `<S>` the mean channel signal of the cluster. It uses the near-proportionality of charge to the
  path under each channel (sec. 7.1, p. 32).
- **End-pixel estimator** (approximate; arXiv:1405.6569 sec. 3.1.1, eqs. 1-2): with the projected cluster's
  geometric centre `u_geom` and end charges `Q_first`, `Q_last`,
  `u = u_geom + (Q_last - Q_first) / (2 (Q_last + Q_first)) |W - W_inner| - L/2`, where
  `W = D |tan(alpha - pi/2) + tan(theta_L)|` is the expected charge width from the track angle `alpha` and
  `W_inner` the width without the end pixels (zero below three pixels). Variant:
  `x = x_centre + Delta(phi, N) (Omega - 1/2)`, `Omega = q_last / (q_first + q_last)` (arXiv:1406.7690 sec. 2,
  eqs. 2.1-2.2).
- **Template fit** (approximate; arXiv:1405.6569 sec. 3.1.2, eqs. 3-4):
  `chi2(j) = sum_i ((P_i - N_j S_ij) / Delta P_i)^2`, `N_j = sum_i (P_i / Delta P_i^2) / sum_i (S_ij / Delta P_i^2)`,
  `S_ij` the simulated mean projected charge for intercept bin `j`, `Delta P_i` its expected spread. The bias and the
  error of the hit are taken from the same simulated sample (pp. 9-10).
- **Lorentz angle** (approximate; pdg_2025_particle-detectors-at-accelerators sec. 35.8.1.2, p. 65;
  arXiv:physics/0012050 sec. 2, eq. 1): `tan(theta_L) = r_H mu B`; for silicon at room temperature and small `B`,
  `r_H ≈ 1.15` (electrons) and `≈ 0.8` (holes), `≈ 1` at large `B`. The mobility falls with the electric field, so
  `theta_L` changes with bias, depletion depth, temperature and fluence, and varies with depth in the sensor
  (arXiv:physics/0012050 secs. 2-3, pp. 3-4): a conditions quantity.
- **Lorentz shift of the hit** (approximate, uniform drift through the full thickness `D`; arXiv:1405.6569
  sec. 3.1.1, eq. 1): `L/2 = D tan(theta_L) / 2`.
- **Size minimum at the Lorentz angle** (approximate; arXiv:physics/0012050 sec. 2): the mean cluster size versus
  incidence angle is smallest at `theta = theta_L`; a parabola fit near the minimum gives `theta_L`, and data at
  `B = 0` must give zero.
- **Path-length scaling of the cluster charge** (approximate, a relativistic particle well below front-end
  saturation; arXiv:2603.25080 sec. 3.1; arXiv:1712.08011 secs. 2, 4.5): `Q ∝ Z^2 D / cos(theta)`; the charge
  estimator is `Q cos(theta)`. A test-beam fit of the peak signal to `P1 / cos(theta)^P2` gave `P2` compatible with
  one (arXiv:hep-ex/0212037 sec. 7, eq. 11, Fig. 17).
- **Linear charge sharing** (approximate: linear electronics, a strip-network model; arXiv:1712.08011 sec. 3.2,
  eqs. 1-6): `S_i = G sum_k R_|i-k| Q_k` with `Q_k = Q_total h_k / D`, `h_k` the depth of the track under strip
  `k`. With the angle known and two or more channels,
  `Q_total` and the impact point follow; an overdetermined cluster's residual flags a bad reconstruction.
- **Telescope subtraction** (approximate, independent Gaussian terms; arXiv:2603.25085 sec. 4.1, eq. 1;
  arXiv:hep-ex/0212037 sec. 5.2, eq. 6): `sigma_DUT^2 = sigma_meas^2 - sigma_tel^2`, the telescope term including
  multiple scattering.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Strip clusters | Seed above `k_s` times the noise, neighbours above `k_n`, cluster kept above a cluster-noise cut | Per-channel pedestal and noise | Thresholds in ADC units carried across noise changes; low-signal edges lost | COL (arXiv:1405.6569 sec. 3.2); SPC (arXiv:1712.02739 sec. 4.1; arXiv:1407.1657 sec. 3.1); FXT (arXiv:2603.25085 sec. 4.1) |
| Pixel clusters | Connected pixels, sides and corners, with a cluster-charge minimum | Per-pixel thresholds and gains | Merged clusters when particles are closer than about a pixel | COL only (sources read) (arXiv:1405.6569 sec. 3.1; arXiv:1406.7690 sec. 2) |
| Two signal peaks in one cluster | Split where the signal rises again away from the seed, or a trained splitter | Noise known per channel | Delta-ray clusters split; merged pairs left whole, so hits are shared between tracks | SPC (arXiv:1712.02739 sec. 4.1); COL (arXiv:1406.7690 abstract, sec. 2) |
| Two coordinates per layer | Double-sided sensors or two single-sided planes; combine only views read by the same readout region | Known view orientation; strip pitch per view | Ghost combinations at multiplicity above one | COL (arXiv:2209.03006 sec. 1); SPC (arXiv:1407.1657 sec. 2; arXiv:1712.02739 sec. 4.1); FXT telescopes (arXiv:2603.25085 sec. 3; arXiv:physics/0012050 sec. 1) |
| Small angle, analog readout | Centre of gravity, or eta with `f(eta)` | Uniform illumination sample per angle and charge range | `f` from another `Z` or angle; delta rays on the two highest channels | FXT (arXiv:hep-ex/0212037 sec. 5.1; arXiv:2603.25080 sec. 4.2); COL, centre of gravity only (arXiv:2209.03006 sec. 2; arXiv:2201.09824 sec. 8.2.2); SPC (arXiv:1712.02739 sec. 4.1; arXiv:1712.08011 sec. 2) |
| Wide strip clusters (large angle) | Head-tail; choose it by the width expected from the track angle | Threshold for the edge channels | Eta used on wide clusters; noise on the edges | FXT (arXiv:hep-ex/0212037 secs. 7.1-7.2); COL (arXiv:2201.09824 sec. 8.2.2, eq. 8.9) |
| Pixel position with a track angle | End-pixel estimator with the expected charge width | Track or vertex direction | Wrong angle before the fit; biases after irradiation | COL only (sources read) (arXiv:1405.6569 sec. 3.1.1; arXiv:1406.7690 sec. 2) |
| Irradiated pixels | Simulated charge templates per angle range, chi2 to the observed profile | A sensor simulation validated per fluence | Templates from the wrong fluence; delta-ray clusters | COL only (arXiv:1405.6569 sec. 3.1.2); none found elsewhere, though nothing in it is collider-specific |
| Sensor in a magnetic field | Lorentz shift correction; `theta_L` from the size minimum versus angle, with a `B = 0` control | Angle scan, or tracks over a range of angles | One `theta_L` kept after bias or fluence changes | COL (arXiv:1405.6569 secs. 3.1.1, 3.2; pdg_2025_particle-detectors-at-accelerators sec. 35.8.1.2); FXT (arXiv:physics/0012050 sec. 2) |
| Saturated channels (high `Z`) | Treat saturated channels as digital and take the geometric centre, or reject saturated seeds | Saturation threshold from charge injection or the response curve | Eta loses sensitivity when the seed sits at saturation | SPC (arXiv:1407.1657 sec. 3.1); FXT (arXiv:1705.09791 sec. 3.3; arXiv:2603.25080 sec. 5.2) |
| Nuclear charge from one cluster | Correct the cluster charge for path length and for impact position and angle: binned tables from known-`Z` samples, a linear charge-sharing model, or a data-driven regressor | Known-`Z` reference (beam tag, other detector); angle known | Wrong impact bin biases silently; tables thin at large angle; non-linear electronics | SPC (arXiv:1712.08011 secs. 3.1-3.2); FXT (arXiv:1705.09791 sec. 3.2.3; arXiv:2603.25080 secs. 3.1-3.4, 4.2) |
| Charge from many layers | Truncated mean over layers (drop the highest values), or a per-layer likelihood ([multisample PID](multisample-pid-and-reference-pdfs.md)) | Per-layer gain equalized | Landau tail; fragments after an interaction | FXT (arXiv:2603.25080 sec. 5.1); SPC ([multisample PID](multisample-pid-and-reference-pdfs.md#control-samples-by-environment)) |
| Hit uncertainty for the track fit | Parametrize by cluster size and expected width; scale so pulls have unit width | Simulation with true positions | Errors from the formula alone give pulls not of unit width | COL only (sources read) (arXiv:1405.6569 sec. 3.2; arXiv:2201.09824 sec. 8.2.2) |
| Resolution in data | Unbiased residual minus the track term, versus angle and cluster size: event by event, global (median and MAD), overlap pairs, or a telescope | Track excluding the hit; scattering known | Track term underestimated; one number quoted for all angles | COL (arXiv:2209.03006 secs. 2-3); FXT (arXiv:2603.25085 secs. 4.1, 4.3); SPC (arXiv:1712.02739 sec. 6.1) |

Across the rows:

- **The estimator follows the expected width.** One channel: the channel centre (plus the Lorentz and
  radiation-bias correction for pixels); small `W`: centre of gravity or eta; large `W`: head-tail or an
  end-channel estimator (strips, by size: arXiv:2201.09824 sec. 8.2.2; pixels of two or more channels, end-pixel
  or templates: arXiv:1405.6569 secs. 3.1.1-3.1.2, every projection). `W` is the width expected from the track
  angle (end-pixel `W` above), not the observed size, which floating strips and high `Z` widen at any angle. Eta is
  better at small angles, head-tail at large ones (arXiv:hep-ex/0212037 sec. 7.2); measure the crossover angle.
- **Cluster shape is a track-quality variable.** Grazing tracks give longer clusters; requiring the size
  expected from the seed direction removes fake seeds (arXiv:1405.6569 sec. 4.1, p. 17), and the template chi2
  rejects hits whose profile does not fit the track angle (sec. 3.1.2, p. 9).
- **Where the resolution minimum sits.** Without floating strips most clusters near normal incidence have one
  channel and the resolution nears the binary value; the resolution is then best where the track crosses about two
  strip pitches (arXiv:2209.03006 sec. 3) and degrades again when three or more channels share and dilute the
  signal (arXiv:2603.25085 sec. 4.3). Floating strips share charge already at normal incidence: the resolution
  there is well below `p/sqrt(12)`, and the minimum can sit at normal incidence (sec. 4.3, Figs. 7-8). Isotropic
  fluxes (SPC, cosmic rays anywhere) fill the whole range: characterise it over the acceptance before flight
  (sec. 4.3) and in flight (arXiv:1712.02739 sec. 6.1).
- **Charge corrections need the position, the position needs the charge.** `f(eta)` depends on `Z`, and the
  charge correction depends on `eta` (arXiv:2603.25080 secs. 3.1, 4.2): iterate, or use a model that solves both
  (arXiv:1712.08011 sec. 3.2).

<!-- example: named apparatus and their numbers (collider, test-beam and space instances of the rows above) -->
- CMS tracker (COL): pixel readout threshold 3200 electrons, cluster minimum 4000 electrons, a MIP about 21000
  electrons; pixel barrel Lorentz shift about 59 um; strip zero suppression at 5 times the noise, offline seeds
  at 3, neighbours at 2, cluster at 5 times the cluster noise; strip Lorentz corrections about 10 um (TIB) and
  20 um (TOB); binary-resolution uncertainty
  (width over `sqrt(12)`) when the width is at least 3.5 times the expected one and incompatible with it
  (arXiv:1405.6569 secs. 3.1 and 3.2, pp. 7-10). Templates from PIXELAV, nine intercept bins per pixel; end-pixel
  biases up to 50 um in highly irradiated sensors (sec. 3.1.2, pp. 8-10).
- ATLAS pixel detector (COL): eight-cell connectivity; a neural-network splitter cut clusters shared between
  tracks in jets by up to a factor of three (arXiv:1406.7690 abstract, sec. 2).
- ATLAS pixel test-beam assemblies (FXT, 1.4 T, 180 GeV pions): `theta_L` 9.0 +- 0.4 +- 0.5 degrees unirradiated
  at 150 V, 2.6 to 3.1 degrees at `0.5-1 x 10^15 n_eq/cm^2` and 600 V (arXiv:physics/0012050 Table 1, p. 3).
- Belle II SVD (COL): double-sided 300-320 um sensors, one floating strip; resolution minimum expected at 4 (7)
  degrees on the u/P side and 14 (21) degrees on v/N for layer 3 (4-6); EBE resolution at normal incidence 7 to
  32 um by layer and side (arXiv:2209.03006 secs. 1, 3, Tables 1, 3). Position by cluster size (one strip,
  two-strip centre of gravity, head-tail for wider clusters) and pull scale factors per sensor type, side and size
  (arXiv:2201.09824 sec. 8.2.2, PDF pp. 160-161, printed 154-155).
- ZEUS MVD sensors (FXT): 120 um readout pitch with intermediate strips, non-flat `dN/deta`; head-tail edge
  threshold 3 times the chip noise; eta better below about 30 degrees, head-tail above 30-40 degrees
  (arXiv:hep-ex/0212037 secs. 5.1, 7.1-7.2, pp. 19-32).
- PAMELA spectrometer (SPC): six double-sided layers, read-out pitch 51 um (bending X) and 66.5 um (Y); seeds
  above S/N 7, neighbours above 4; for saturated boron and carbon the geometric centre gives about 14 um (X) and
  19 um (Y), pitch over `sqrt(12)` (arXiv:1407.1657 secs. 2, 3.1, pp. 5-8).
- DAMPE STK (SPC, and FXT with ions): single-sided x and y planes, 242 um readout pitch, one floating strip
  (121 um implant pitch, arXiv:1712.08011 sec. 2); on board seeds S/N > 3.5 with neighbours ADC > 5, offline
  seeds S/N > 4 with neighbours S/N > 1.5, and a split where the signal rises by more than five times the noise
  moving away from the seed; cluster size 2.3 to 2.9 (protons) and 3.2 to 4.0 (helium) with direction
  (arXiv:1712.02739 sec. 4.1). Floating- versus readout-strip incidence changes the carbon MPV by about 35%;
  binned tables or a charge-sharing model with `R_1 = 28.7%` measured on carbon (arXiv:1712.08011 secs. 2, 4.2);
  channel saturation above about 3000 ADC counts, linear up to carbon (readout strip) or neon (floating strip),
  confirmed by charge injection (arXiv:1705.09791 sec. 3.3).
- AMS-02 Layer-0 flight-model ladders (FXT, before flight): 109 um readout pitch, three floating strips; seeds at
  3.5 and neighbours at 2 times the noise; mean cluster size about 1.97 at normal incidence and 2.46 at 30 degrees;
  resolution 11.4 um at normal incidence to about 17 um at 30 degrees (12-sensor ladder) (arXiv:2603.25085
  secs. 2, 4.1, 4.3, Figs. 7-8). "Head" and "Tail" there are the ladder ends, not the head-tail algorithm.
- Nine-layer heavy-ion telescope of the same sensors (FXT): central `eta` peaks less pronounced for heavier
  nuclei, none near `eta = 0` or `1` for `Z >= 15`; a boosted decision tree for the charge; truncated mean over
  nine layers (highest values dropped) of the per-layer BDT charges, Gaussian sigma of the peak about 0.08 charge
  units for `Z = 4-20`, at normal incidence with about 150 GeV/n ions; single-layer resolution about 7.8 um
  (protons) to 1.5 um near `Z = 20-22`, worse again for `Z >= 26` from seed saturation
  (arXiv:2603.25080 secs. 2, 3.1-3.4, 4.2, 5.1-5.2, 6).
<!-- /example -->

## Distinctive but generalizable features (silicon hits)

- **Topology**: a sparse 1D (strip) or 2D (pixel) image of channel charges per sensor, with one or two views
  per strip layer (two from double-sided sensors or paired stereo planes), both coordinates from a pixel layer.
- **Inverse problem**: impact point and deposited charge from shared charge; one wide cluster from an inclined
  track, a delta ray and two merged particles are degenerate.
- **Natural objects**: channel, cluster, split cluster, 1D (single-view) hit, 2D hit (pixel cluster or a
  combination of views). **Informative residual**: unbiased track-to-hit residual versus intercept position in
  the pitch, incidence angle and cluster size; cluster charge versus `eta`.
- **Scaling**: binary `p/sqrt(12)` (readout pitch, or `p/(2 sqrt(12))` with one floating strip); charge
  `∝ Z^2 / cos(theta)`; Lorentz shift `D tan(theta_L)/2`.
- **Conventions**: readout versus implant pitch; sign and plane of the Lorentz shift; the depth at which a hit is
  quoted (mid-plane for templates, arXiv:1405.6569 sec. 3.1.2); charge in ADC, electrons or MIP units.
- **Tails**: delta rays, merged clusters, saturated channels, noisy or dead channels, sensor edges.
- **Dependence**: angle, `Z`, field, bias, temperature, fluence, noise and occupancy.
- **Data sample**: telescopes and ion beams (FXT); tracks from collisions with overlapping sensors (COL); flight
  protons and nuclei over the full angle range (SPC).
- **Transfers**: thresholds in noise units, eta and head-tail, the size minimum for `theta_L`, path-length
  correction. **Does not transfer**: `f(eta)` and charge tables between sensor layouts, `Z` ranges or fluences;
  thresholds in ADC counts.

## Common misconceptions and failure modes

- **One `f(eta)` for all particles.** It changes with `Z` and angle; from the wrong species it biases positions
  and, through the position, the charge.
- **`theta_L` as a constant.** It follows bias, temperature and fluence; re-measure after changes, with the
  field-off control.
- **Resolution quoted at normal incidence only.** For isotropic fluxes the angle-averaged resolution is
  worse than at normal incidence when it grows from there, and can be better when the minimum lies inside the
  acceptance (rule above); quote it versus angle.
- **Electronics saturation modelled as physics.** A flattening charge response at high `Z` may be front-end
  saturation or physics (quenching, delta-ray escape); a knee at a fixed ADC level, not at a fixed `Z`, points to
  the electronics (arXiv:1705.09791 sec. 3.3); confirm with charge injection before modelling it as physics.
- **Lorentz drift and radiation damage are separate entries.** Fluence changes `theta_L`, collection and the
  templates together; for fluence dependence see
  [tracking and vertexing](tracking-and-vertexing.md#sensor-technologies).

## Deliverables

- Clustering thresholds in noise units, splitting rule, merged-cluster rate where density matters.
- Position estimator per expected width, with `f(eta)` or template provenance (species, angle range, fluence) and
  the Lorentz correction with its conditions.
- Resolution versus incidence angle and cluster size, with the track or telescope term and how it was removed.
- For charge: path-length and impact-position correction, saturation threshold and how saturated channels were
  treated, the reference samples, and the multi-layer estimator.

## Tool hooks

- **Inputs**: per-channel signals after pedestal and common mode (ADC or electrons), noise per channel, channel
  positions and pitch (um), sensor thickness (um), track angle per view (degrees) where known, field (T), a
  per-species `f(eta)` or charge table with its validity range, `theta_L` per view with its conditions (bias,
  temperature, fluence) or a conditions tag, and templates with their simulation, fluence and angle range.
- **Outputs**: clusters with size, total charge, `eta`, position by the chosen estimator, its uncertainty, the
  path-corrected charge, and flags.
- **Conventions**: thresholds in noise units; angle from the sensor normal; Lorentz shift sign stated per view.
- **Closure test and negative control**: in every charge range and angle bin of `f(eta)`, on a
  uniform-illumination sample disjoint from the one that built it, with true or telescope positions and at least
  `N` entries per intercept bin, the largest `|mean residual|` over intercept bins within one pitch must stay below
  a stated fraction of the resolution, both fixed in advance, in every bin; the uncorrected centre of gravity,
  the negative control, must fail it, and if it does not, or if `dN/deta` passes a flatness test fixed in advance,
  the closure is `inconclusive`.
- **Statuses**: per cluster `ok`, `single-channel`, `split`, `wide` (head-tail used), `saturated`, `edge`
  (bad or edge channel inside), `out-of-range` (angle or `Z` outside the table); per hit `ambiguous` (more than one view
  combination); per check `passed`, `failed`, `inconclusive`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Clustering and splitting | arxiv_1405.6569, arxiv_1406.7690 | arxiv_2603.25085 | arxiv_1712.02739, arxiv_1407.1657 | gap | gap | gap |
| Two-coordinate readout | arxiv_2209.03006 | arxiv_2603.25085, arxiv_physics_0012050 (telescopes) | arxiv_1407.1657, arxiv_1712.02739 | gap | gap | gap |
| Centre of gravity and eta correction | arxiv_2209.03006, arxiv_2201.09824 (centre of gravity; eta: gap) | arxiv_hep-ex_0212037, arxiv_2603.25080 | arxiv_1712.02739, arxiv_1712.08011 (eta as impact estimator) | gap | gap | gap |
| Head-tail and end-channel estimators | arxiv_2201.09824, arxiv_1405.6569, arxiv_1406.7690 | arxiv_hep-ex_0212037 | gap | gap | gap | gap |
| Lorentz shift and `theta_L` | arxiv_1405.6569, pdg_2025_particle-detectors-at-accelerators | arxiv_physics_0012050 | gap: magnet spectrometers not read for it | gap | gap | gap |
| Templates | arxiv_1405.6569 | gap: none found | gap: none found | gap | gap | gap |
| Cluster size and resolution versus angle | arxiv_2209.03006, arxiv_1405.6569 | arxiv_physics_0012050, arxiv_2603.25085 | arxiv_1712.02739 | gap | gap | gap |
| Nuclear charge from cluster charge | gap: not sought; unit-charge [dE/dx](particle-identification.md#ionization-energy-loss-dedx) | arxiv_1705.09791, arxiv_2603.25080 | arxiv_1712.08011, arxiv_1407.1657 | gap | gap | gap |

`gap` marks content not found in the sources read; templates were searched for and found only in COL (single
environment). Silicon in UGD, GND and NUC instruments was not surveyed (`gap` in those columns).

## Citations

Sources were read in their arXiv e-prints (PDG: the 2025 review PDF) on 2026-11-17 to 2026-11-21; page numbers
are PDF pages. Entries are in the
[bibliography](detector-principles-bibliography.md); the PDG review is its general entry.
