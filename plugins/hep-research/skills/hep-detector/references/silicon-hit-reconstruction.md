# Silicon Hit Reconstruction

From pixel and strip signals to clusters, hits, positions, resolution and nuclear charge. Sensors, radiation damage, ghosts:
[tracking and vertexing](tracking-and-vertexing.md#sensor-technologies),
[silicon recap](gaseous-and-specialized-tracking-technologies.md#silicon-pixels-and-strips-recap-of-what-is-distinctive);
thresholds and zero suppression:
[front-end electronics](front-end-electronics-and-signal-processing.md#thresholds-fake-hits-and-zero-suppression);
alignment and pulls:
[in-situ alignment](in-situ-alignment-and-momentum-scale.md),
[performance metrics](performance-metrics-and-residual-diagnostics.md#residuals-pulls-and-their-covariance).
Simcal of the Lorentz angle or charge sharing is hep-statistics'
([tracker simcal](simulation-calibration/tracker.md)); splitting or charge networks are hep-ml's
([multivariate analysis](../../hep-ml/references/multivariate-analysis-bdt-nn.md)).

Environments: COL collider; FXT fixed target, test beam; SPC space, balloon; UGD underground; GND ground arrays;
NUC nuclear. Pitch, thickness, floating strips, field, noise, occupancy, fluence and angle are parameters.
Source IDs: `arxiv_<id>` is arXiv:<id> with `/` written `_`; `pdg_2025_<review>` is the PDG 2025 review.

## Relations (with source locators)

- **Centre of gravity** (exact as a definition, biased as an estimator; arXiv:2209.03006 sec. 2):
  `x_cog = sum_i S_i x_i / sum_i S_i` over the cluster channels. A noise-weighted form uses `S_i / N_i`
  (arXiv:1712.02739 sec. 4.1). With non-linear charge division it is biased toward where `dN/deta` peaks: the
  intermediate strips in one floating-strip layout (arXiv:hep-ex/0212037 sec. 5.1, Fig. 8), readout and floating
  strips in another (arXiv:1705.09791 sec. 3.2.3, Fig. 5a); use `f(eta)` or check per layout.
- **Eta** (exact, a definition; arXiv:hep-ex/0212037 sec. 5.1, eq. 3; arXiv:2603.25080 sec. 3.1, eq. 1):
  `eta = S_R / (S_L + S_R)` from the two highest adjacent channels.
- **Eta correction** (exact for uniform illumination across the pitch within one angle bin and charge
  range; arXiv:hep-ex/0212037 sec. 5.1, eqs. 4-5; arXiv:2603.25080 sec. 4.2, eqs. 3-4):
  `f(eta_0) = (1/N) integral_0^eta_0 (dN/deta) deta`, `x = x_L + p f(eta)`, `p` the readout pitch, `x_L` the
  left channel.
  `dN/deta` changes with `Z`: wider charge clouds make the central peaks less pronounced
  (arXiv:2603.25080 sec. 4.2, p. 18), so `f` is built per charge range and per angle bin.
- **Binary resolution** (approximate: single-channel clusters, uniform illumination; arXiv:2603.25085 sec. 4.3,
  p. 4): `p / sqrt(12)`. With one floating strip between readout strips one source takes the digital reference as
  `p / (2 sqrt(12))` (arXiv:2209.03006 sec. 3).
- **Head-tail** (approximate, for wide clusters; arXiv:hep-ex/0212037 sec. 7.1, eq. 12):
  `x = (x_head + x_tail)/2 + p (S_tail - S_head) / (2 <S>)`, head and tail the first and last channels above
  threshold, `<S>` the mean channel signal of the cluster.
- **End-pixel estimator** (approximate: two or more pixels, `W - W_inner` from zero to two pixel pitches,
  else a modified form; arXiv:1405.6569 sec. 3.1.1, eqs. 1-2): with the projected cluster's
  geometric centre `u_geom` and end charges `Q_first`, `Q_last`,
  `u = u_geom + (Q_last - Q_first) / (2 (Q_last + Q_first)) |W - W_inner| - L/2`, where
  `W = D |tan(alpha - pi/2) + tan(theta_L)|` is the expected charge width from the track angle `alpha` and
  `W_inner` the width without the end pixels (zero below three pixels).
- **Template fit** (approximate: angle ranges and fluence as simulated, clusters below an angle-dependent
  charge maximum; arXiv:1405.6569 sec. 3.1.2, eqs. 3-4):
  `chi2(j) = sum_i ((P_i - N_j S_ij) / Delta P_i)^2`, `N_j = sum_i (P_i / Delta P_i^2) / sum_i (S_ij / Delta P_i^2)`,
  `S_ij` the simulated mean projected charge for intercept bin `j`, `Delta P_i` its expected spread.
- **Lorentz angle** (approximate: `r_H` about 1.15 for electrons, 0.8 for holes at room temperature
  and small `B`, about 1 at large `B`; pdg_2025_particle-detectors-at-accelerators sec. 35.8.1.2, p. 65;
  arXiv:physics/0012050 sec. 2, eq. 1): `tan(theta_L) = r_H mu B`, `r_H` the Hall factor. Through the mobility,
  `theta_L` changes with bias, depletion depth, temperature and fluence, and with depth in the sensor
  (arXiv:physics/0012050 secs. 2-3): a conditions quantity.
- **Lorentz shift of the hit** (approximate, uniform drift through the full thickness `D`; arXiv:1405.6569
  sec. 3.1.1, eq. 1): `L/2 = D tan(theta_L) / 2`.
- **Path-length scaling of the cluster charge** (approximate: relativistic, well below front-end saturation,
  after the impact-position and angle correction where floating strips change the collected charge;
  arXiv:2603.25080 sec. 3.1; arXiv:1712.08011 secs. 2, 4.5): `Q ∝ Z^2 D / cos(theta)`; the charge
  estimator is `Q cos(theta)`.
- **Linear charge sharing** (approximate: linear electronics, a strip-network model; arXiv:1712.08011 sec. 3.2,
  eqs. 1-6): `S_i = G sum_k R_|i-k| Q_k` with `Q_k = Q_total h_k / D`, `h_k` the depth of the track under strip
  `k`. With the angle known and two or more channels,
  `Q_total` and the impact point follow.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Strip clusters | Seed above `k_s` times the noise, neighbours above `k_n`, cluster kept above a cluster-noise cut | Per-channel pedestal and noise | Thresholds in ADC units carried across noise changes; low-signal edges lost | COL (arXiv:1405.6569 sec. 3.2); SPC (arXiv:1712.02739 sec. 4.1; arXiv:1407.1657 sec. 3.1); FXT (arXiv:2603.25085 sec. 4.1) |
| Pixel clusters | Connected pixels, sides and corners, with a cluster-charge minimum | Per-pixel thresholds and gains | Merged clusters when particles are closer than about a pixel | COL only (sources read) (arXiv:1405.6569 sec. 3.1; arXiv:1406.7690 sec. 2) |
| Two signal peaks in one cluster | Split where the signal rises again away from the seed, or a trained splitter | Noise known per channel | Delta-ray clusters split; merged pairs left whole and shared between tracks | SPC (arXiv:1712.02739 sec. 4.1); COL (arXiv:1406.7690 abstract, sec. 2) |
| Two coordinates per layer | Double-sided sensors or two single-sided planes; combine only views read by the same readout region | Known view orientation; strip pitch per view | Ghost combinations at multiplicity above one | COL (arXiv:2209.03006 sec. 1); SPC (arXiv:1407.1657 sec. 2; arXiv:1712.02739 sec. 4.1); FXT telescopes (arXiv:2603.25085 sec. 3; arXiv:physics/0012050 sec. 1) |
| Small angle, analog readout | Centre of gravity, or eta with `f(eta)` | Uniform illumination sample per angle and charge range | `f` from another `Z` or angle; delta rays on the two highest channels | FXT (arXiv:hep-ex/0212037 sec. 5.1; arXiv:2603.25080 sec. 4.2; arXiv:1712.08011 sec. 2); COL, centre of gravity only (arXiv:2209.03006 sec. 2; arXiv:2201.09824 sec. 8.2.2); SPC (arXiv:1712.02739 sec. 4.1) |
| Wide strip clusters (large angle) | Head-tail; choose it by the width expected from the track angle | Threshold for the edge channels | Eta used on wide clusters; noise on the edges | FXT (arXiv:hep-ex/0212037 secs. 7.1-7.3, angle rule 7.3); COL, chosen by observed size above two strips, not by expected width (arXiv:2201.09824 sec. 8.2.2, eq. 8.9) |
| Pixel position with a track angle | End-pixel estimator with the expected charge width | Track or vertex direction | Wrong angle before the fit; biases after irradiation | COL only (sources read) (arXiv:1405.6569 secs. 3.1.1-3.1.2; arXiv:1406.7690 sec. 2) |
| Irradiated pixels | Simulated charge templates per angle range, chi2 to the observed profile | A sensor simulation validated per fluence | Templates from the wrong fluence; delta-ray clusters | COL only (arXiv:1405.6569 sec. 3.1.2), though not collider-specific |
| Sensor in a magnetic field | Lorentz shift correction; `theta_L` where the mean cluster size versus angle is smallest (parabola fit; minimum bracketed by scan points on both sides, else `inconclusive`), with a `B = 0` control whose minimum must be compatible with zero within a tolerance fixed in advance, else `failed` | Angle scan with field-off data at the same angles; without them the `theta_L` check is `inconclusive` | One `theta_L` kept after bias, temperature or fluence changes | Shift correction: COL (arXiv:1405.6569 secs. 3.1.1, 3.2); `theta_L` formula: pdg_2025_particle-detectors-at-accelerators sec. 35.8.1.2; `theta_L` from the size minimum: FXT test beam only (arXiv:physics/0012050 sec. 2) |
| Saturated channels (high `Z`) | Treat saturated channels as digital and take the geometric centre, or reject saturated seeds | Saturation threshold from charge injection or the response curve | Eta loses sensitivity when the seed sits at saturation | SPC (arXiv:1407.1657 sec. 3.1); FXT (arXiv:1705.09791 sec. 3.3; arXiv:2603.25080 sec. 5.2) |
| Nuclear charge from one cluster | Correct the cluster charge for path length and for impact position and angle: binned tables from known-`Z` samples, a linear charge-sharing model, or a data-driven regressor (normal incidence only in the source read; add the angle as an input) | Known-`Z` reference (beam tag, other detector); angle known | Wrong impact bin biases silently; tables thin at large angle; non-linear electronics | FXT, ion beams on space-instrument ladders (arXiv:1712.08011 secs. 3.1-3.2, 4; arXiv:1705.09791 sec. 3.4 with 3.2.3; arXiv:2603.25080 secs. 3.1-3.4, `eta` dependence sec. 4.2); SPC, path-length part only, flight `Z = 1, 2` (arXiv:1712.02739 secs. 6.1-6.2) |
| Charge from many layers | Truncated mean over layers (drop the highest values), or a per-layer likelihood | Per-layer gain equalized | Landau tail; fragments after an interaction | FXT (arXiv:2603.25080 sec. 5.1); SPC ([multisample PID](multisample-pid-and-reference-pdfs.md#control-samples-by-environment)) |
| Hit uncertainty for the track fit | Parametrize by cluster size and expected width; scale so pulls have unit width | Simulation with true positions (arXiv:2201.09824 sec. 8.2.2); recommended here, not done in the sources read: pull widths in data from unbiased residuals, per size, expected-width, sensor-type and side class, within a tolerance fixed in advance: `passed`; else rescale on one data sample and re-check on a disjoint one: `rescaled` if it passes, else `failed`; no such data: `inconclusive` | Errors from the formula alone give pulls not of unit width; pulls unit in simulation only | COL only (sources read) (arXiv:1405.6569 sec. 3.2; arXiv:2201.09824 sec. 8.2.2) |
| Resolution in data | Unbiased residual minus the track term, versus angle and cluster size: event by event, global (median and MAD), overlap pairs, or a telescope | Track excluding the hit; scattering known | Track term underestimated; one number quoted for all angles | COL (arXiv:2209.03006 secs. 2-3); FXT (arXiv:2603.25085 secs. 4.1, 4.3); SPC (arXiv:1712.02739 sec. 6.1) |

Across the rows:

- **The estimator follows the expected width** `W` from the track angle (end-pixel `W` above), not the observed
  size, which floating strips and high `Z` widen at any angle. One channel: the channel centre (plus the Lorentz
  and radiation-bias correction for pixels); small `W`: centre of gravity or eta; large `W`: head-tail or an
  end-channel strip estimator (one strip tracker
  selects by observed size, a proxy that floating strips and high `Z` bias, inferred here,
  though it has one floating strip, arXiv:2201.09824 sec. 8.2.2). Pixel projections of two or more pixels, any
  `W`: end-pixel in seeding and pattern recognition, templates in the final fit (arXiv:1405.6569 secs. 3.1-3.1.2). Eta is
  better at small angles, head-tail at large ones (arXiv:hep-ex/0212037 sec. 7.2); measure the crossover angle.
- **Cluster shape is a track-quality variable.** Requiring the size expected from the seed direction removes
  fake seeds (arXiv:1405.6569 sec. 4.1); the template chi2 rejects profiles that do not fit the track
  angle (sec. 3.1.2).
- **Where the resolution minimum sits.** With one floating strip the resolution at normal incidence is near the
  digital value (Binary resolution above); it is then expected to be best where the projected track crosses about one implant pitch, half
  a readout pitch (derived here from the quoted angles and geometry; the text says two strip
  pitches; not seen on the finest pitch; arXiv:2209.03006 sec. 3, Table 1), and degrades at larger angles as more
  channels share the signal (with three floating strips from normal incidence on, arXiv:2603.25085 sec. 4.3). Characterise it
  over the acceptance before flight
  (sec. 4.3) and in flight (arXiv:1712.02739 sec. 6.1). No source read gives the minimum without floating strips.
- **Charge corrections need the position, the position needs the charge.** `f(eta)` depends on `Z`, and the
  charge correction depends on `eta` (arXiv:2603.25080 secs. 3.1, 4.2): iterate, or use a model that solves both
  (arXiv:1712.08011 sec. 3.2).

<!-- example: named apparatus and their numbers -->
- CMS tracker (COL): pixel readout threshold 3200 electrons, cluster minimum 4000
  electrons (the source's unit, no pixel noise given, a MIP about 21000); strip zero suppression at 5 times the noise, or 2 if it and a neighbour both exceed 2, offline seeds
  (strips passing zero suppression) at 3, neighbours at 2, cluster at 5 times the quadrature sum of strip noises; strip Lorentz corrections about 10 um (TIB) and
  20 um (TOB) (arXiv:1405.6569 secs. 3.1-3.2, PDF pp. 7-10).
- ATLAS pixel detector (COL): a neural-network splitter cut the measurements shared between
  tracks in jets by up to a factor of three (arXiv:1406.7690 abstract, secs. 1, 4.1 with Fig. 10).
- ATLAS pixel test-beam assemblies (FXT, 1.4 T): `theta_L` 9.0 +- 0.4 +- 0.5 degrees unirradiated
  at 150 V, 2.6 to 3.1 degrees at `0.5-1 x 10^15 n_eq/cm^2` and 600 V (arXiv:physics/0012050 Table 1, p. 3).
- Belle II SVD (COL): double-sided 300-320 um sensors, one floating strip; resolution minimum expected at 4 (7)
  degrees on the u/P side and 14 (21) degrees on v/N for layer 3 (4-6), not seen on layer 3 u/P; EBE resolution at normal incidence 7 to
  32 um by layer and side (arXiv:2209.03006 secs. 1, 3, Tables 1, 3). Position by observed cluster size (one strip,
  two-strip centre of gravity, head-tail above two strips) and position-uncertainty scale factors from simulation
  per sensor type, side and size (arXiv:2201.09824
  sec. 8.2.2 with eq. 8.9 and table 23, PDF pp. 160-162).
- ZEUS MVD sensors (FXT): 120 um readout pitch with five intermediate (floating) strips, 20 um implant pitch, non-flat `dN/deta`;
  eta better below about 30 degrees, head-tail above 30-40 degrees
  (arXiv:hep-ex/0212037 abstract, secs. 1, 5.1, 7.1-7.2).
- DAMPE STK (SPC, and FXT with ions): single-sided x and y planes, 242 um readout pitch, one floating strip
  (121 um implant pitch, arXiv:1712.08011 sec. 2); on board seeds S/N > 3.5 with neighbours ADC > 5,
  offline seeds at local maxima with S/N > 4, neighbours S/N > 1.5;
  cluster size 2.3 to 2.9 (protons) and 3.2 to 4.0 (helium) with direction
  (arXiv:1712.02739 sec. 4.1). Floating- versus readout-strip incidence changes the carbon MPV by about 35%;
  binned tables or a charge-sharing model with `R_1 = 28.7%` measured on carbon (arXiv:1712.08011 secs. 2, 4.2);
  channel saturation above about 3000 ADC counts, linear up to carbon (readout strip) or neon (floating strip),
  confirmed by charge injection (arXiv:1705.09791 sec. 3.3).
- AMS-02 Layer-0 flight-model ladders (FXT, before flight): 109 um readout pitch, three floating strips; seeds at
  3.5 and neighbours at 2 times the noise; mean cluster size about 1.97 at normal incidence and 2.46 at 30 degrees;
  resolution 11.4 um at normal incidence (binary 31.5 um) to about 17 um at 30 degrees (12-sensor ladder) (arXiv:2603.25085
  secs. 2, 4.1, 4.3, Figs. 7-8).
- Nine-layer heavy-ion telescope of the same sensors (FXT): central `eta` peaks less pronounced for heavier
  nuclei, none near `eta = 0` or `1` for `Z >= 15`; truncated mean over nine layers (highest
  values dropped) of per-layer boosted-decision-tree charges, a charge resolution (Gaussian sigma) of about
  0.08 charge units for `Z = 4-20` at normal incidence with about 150 GeV/n ions; single-layer resolution about 7.8 um
  (protons) to 1.5 um near `Z = 20-22`, worse again for `Z >= 26`, tentatively attributed to seed saturation
  (arXiv:2603.25080 secs. 2, 3.1-3.4, 4.2, 5.1-5.2, 6).
<!-- /example -->

## Distinctive but generalizable features (silicon hits)

- **Topology**: a sparse 1D (strip) or 2D (pixel) image of channel charges per sensor, one or two views per
  strip layer, both coordinates from one pixel layer.
- **Inverse problem**: impact point and deposited charge from shared charge; one wide cluster from an inclined
  track, a delta ray and two merged particles are degenerate.
- **Natural objects**: channel, cluster, split cluster, 1D (single-view) strip hit, 2D hit (pixel cluster, or a
  combination of views, `ambiguous` when it may be a ghost).
  **Informative residual**: unbiased track-to-hit residual versus intercept position in
  the pitch, incidence angle and cluster size; cluster charge versus `eta`.
- **Scaling**: binary resolution, charge with path length, Lorentz shift: Relations, each within its domain.
- **Conventions**: readout versus implant pitch; sign and plane of the Lorentz shift; the depth at which a hit is
  quoted (mid-plane for templates); charge in ADC, electrons or MIP units.
- **Tails**: delta rays, merged clusters, saturated channels, noisy or dead channels, sensor edges.
- **Dependence**: angle, `Z`, field, bias, temperature, fluence, noise and occupancy.
- **Data sample**: telescopes and ion beams (FXT); collision tracks, overlapping sensors (COL); flight protons
  and nuclei over all angles (SPC).
- **Transfers**: thresholds in noise units, eta and head-tail, the size minimum for `theta_L`, path-length
  correction. **Does not transfer**: `f(eta)` and charge tables between sensor layouts, `Z` ranges or fluences;
  thresholds in ADC counts.

## Common misconceptions and failure modes

- **One `f(eta)` for all particles.** From the wrong `Z` or angle it biases positions and, through them, the
  charge.
- **Resolution quoted at normal incidence only.** For isotropic fluxes the angle-averaged resolution is
  worse than at normal incidence if the resolution grows from there (three floating strips), and
  can be better if its minimum lies inside the acceptance (one floating strip, above); quote it versus angle.
- **Saturation read as physics, or physics as saturation.** A flattening response at high `Z` may be front-end
  saturation or a physics effect (none in the sources read; silicon microstrips do not suffer Birks saturation,
  arXiv:1705.09791 sec. 3.2.3); a knee at a fixed ADC level, not at a fixed `Z`, across sub-samples where the
  same `Z` gives different signals (impact position, angle, gain), points to the electronics (sec. 3.3);
  confirm with charge injection.

## Deliverables

- Clustering thresholds in noise units, splitting rule, merged-cluster rate where density matters.
- Position estimator per expected width, with `f(eta)` or template provenance (sensor layout, species or charge
  range, angle range, fluence; for templates the simulation), the `f(eta)` closure status per bin, and the Lorentz
  correction with its conditions and the `theta_L` check status.
- Resolution versus incidence angle and cluster size, with the track or telescope term and how it was removed.
- Hit uncertainty per cluster size and expected width, its pull scale factors (simulation, sensor type, side) and
  the pull widths in data from unbiased residuals, with the tolerance and the check status.
- For charge: path-length and impact-position correction, saturation threshold and how saturated channels were
  treated, the reference samples, and the multi-layer estimator.

## Tool hooks

- **Inputs**: per-channel signals after pedestal and common mode (ADC or electrons), noise, gain (ADC to
  electrons), saturation threshold (ADC) and bad, dead or noisy flags; channel positions and pitch (um), thickness
  (um), view orientation and readout regions; track angle per view (degrees) where known, field (T); `f(eta)` or charge
  tables per layout, species or charge range, angle bin and fluence, templates (simulation, fluence, angle range) and `theta_L` per view (bias,
  temperature, fluence, or a conditions tag), each with its validity range; clustering and splitting thresholds
  (noise units); the hit-uncertainty parametrisation with its pull scale factors.
- **Outputs**: clusters with size, total charge, `eta`, position by the chosen estimator, its uncertainty, the
  path-length- and impact-position-corrected charge, and flags; 1D and 2D hits with their clusters, position, uncertainty and status (`ok` or `ambiguous`, plus the cluster statuses).
- **Conventions**: thresholds in noise units, or in electrons with the noise in electrons; angle from the sensor normal; Lorentz shift sign stated per view.
- **Closure test and negative control**: in every charge range and angle bin of `f(eta)` (edges fixed in
  advance), on a uniform-illumination sample disjoint from the one that built it, with true or telescope positions
  and alignment fixed beforehand, the largest `|mean residual - mean over intercept bins|` (at least two intercept
  bins per implant pitch, their number and `N` fixed in advance) must stay below a stated fraction of the corrected
  estimator's resolution expected from simulation (not the sample's own RMS); test the full bin and, separately,
  its low- and high-edge sub-samples.
  Each of the three is `failed` if the corrected estimator fails, whatever else holds; else `inconclusive` if an
  intercept bin has fewer than `N` entries or the uncorrected centre of gravity (the negative control) passes too;
  else `passed`. The bin takes the worst of the three. A bin whose `dN/deta` passes a flatness test and threshold
  fixed in advance takes the centre of gravity as its estimator, judged by the same rule without a control.
  The closure takes the worst of all bins, flat ones too (`failed`, then `inconclusive`, then `passed`).
- **Statuses**: per cluster `ok`, `single-channel`, `split`, `wide` (head-tail or end-channel strip estimator used), `saturated`, `edge`
  (bad or edge channel inside), `out-of-range` (angle or `Z` outside the table); per hit `ok` or `ambiguous` (more than one view
  combination); per check `passed`, `failed`, `inconclusive`, `rescaled`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Clustering and splitting | arxiv_1405.6569, arxiv_1406.7690 | arxiv_2603.25085 | arxiv_1712.02739, arxiv_1407.1657 | gap | gap | gap |
| Two-coordinate readout | arxiv_2209.03006 | arxiv_2603.25085, arxiv_physics_0012050 (telescopes) | arxiv_1407.1657, arxiv_1712.02739 | gap | gap | gap |
| Centre of gravity and eta correction | arxiv_2209.03006, arxiv_2201.09824 (centre of gravity only; eta: gap) | arxiv_hep-ex_0212037, arxiv_2603.25080, arxiv_1712.08011 (eta for impact) | arxiv_1712.02739 (noise-weighted) | gap | gap | gap |
| Head-tail and end-channel estimators | arxiv_2201.09824, arxiv_1405.6569, arxiv_1406.7690 | arxiv_hep-ex_0212037 | gap | gap | gap | gap |
| Lorentz shift and `theta_L` | arxiv_1405.6569 (shift), pdg_2025_particle-detectors-at-accelerators (`theta_L` formula and Hall factor only) | arxiv_physics_0012050 | gap: not sought | gap | gap | gap |
| Templates | arxiv_1405.6569 | gap | gap | gap | gap | gap |
| Cluster size and resolution versus angle | arxiv_2209.03006, arxiv_2201.09824, arxiv_1405.6569 | arxiv_physics_0012050, arxiv_2603.25085, arxiv_hep-ex_0212037 | arxiv_1712.02739 | gap | gap | gap |
| Nuclear charge from cluster charge | gap: not sought; see [dE/dx](particle-identification.md#ionization-energy-loss-dedx) | arxiv_1705.09791, arxiv_1712.08011, arxiv_2603.25080 | arxiv_1712.02739 (path-length part, `Z = 1, 2`) | gap | gap | gap |

`gap`: not covered by the sources read, and in the UGD, GND and NUC columns not sought (not surveyed); `gap: not sought`: not
looked for in that environment. Templates were searched for and found only in COL (single environment).

## Citations

Read in arXiv e-prints (PDG: 2025 review PDF), 2026-11-17 to 21; pages are PDF pages unless marked printed.
