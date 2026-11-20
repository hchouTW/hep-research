# Muon Systems: Spectrometers, Identification, and Trigger

Muon detection and reconstruction: drift-tube, cathode-strip, RPC-, GEM-, and
Micromegas-based chambers; standalone, combined, segment-tagged, calorimeter-tagged, and
trigger-level muons. The PID summary is in [particle identification](particle-identification.md);
technology physics is in [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md);
alignment weak modes in [calibration and alignment](calibration-and-alignment.md) and
[tracking and vertexing](tracking-and-vertexing.md). Also: chamber alignment and momentum scale, energy loss in iron
and other absorbers, and the muon part of charge-sign quality. Environment codes: COL collider; FXT fixed-target
and test beam; SPC space and high-altitude balloon; UGD underground, neutrino and rare-event; GND ground-based
cosmic-ray and gamma-ray arrays; NUC nuclear and low-energy physics. Environments covered: COL, UGD, SPC, FXT
(coverage table below); NUC has no muon system source. Muon vetoes, veto-efficiency measurement, cosmogenic tagging,
muon counting, and muons and albedo in orbit are in
[non-collider muon detection](non-collider-muon-detection.md). Atmospheric-muon rejection in neutrino telescopes
(upward-going selection, containment and veto regions, self-veto) is in
[neutrino astronomy](neutrino-astronomy.md#backgrounds).

## Why muons are special

Muons are close to minimum-ionizing, rarely shower below a few hundred GeV, and
traverse the calorimeters, so the outermost layers see them nearly free of other
particles. Radiative losses (bremsstrahlung, pair production, photonuclear) equal ionization near
the muon critical energy (a few hundred GeV in iron) and dominate at TeV energies, so catastrophic energy losses and accompanying showers in the
absorbers must be expected and modelled. A muon system therefore
does two jobs: identification (it is the layer that survives absorbers) and an
independent momentum measurement at large lever arm, often in its own field.

## Relations

- **Mean muon energy loss** (approximate; PDG RPP 2025, passage of particles through matter, sec. 34.6, eq. 34.39,
  p. 30): `<-dE/dx> = a(E) + b(E) E`, with `a` the ionization loss and `b` the sum of pair production,
  bremsstrahlung and photonuclear terms; the muon critical energy `E_muc` solves `E_muc = a(E_muc)/b(E_muc)`
  (radiative equals ionization loss; p. 30-31). Valid for the mean only: the loss is not continuous at high energy.
- **Mean range** (approximate: `a` and `b` taken constant; eq. 34.40, p. 30): `x0 ≈ (1/b) ln(1 + E0/E_muc)`. It
  is a mean; radiative losses make the range and the momentum after an absorber straggle.
- **Field-reversal charge ratio** (exact when reversing the field swaps the two charges' acceptances; arXiv:0705.3815,
  sec. IV, eqs. 2-4, p. 7): `r = [(N+/N-)_forward × (N+/N-)_reverse]^(1/2)`; acceptance and live time cancel.
- **Same-sign pair probability** for per-muon confusion rates `c_i`, `c_j` (exact for independent legs;
  arXiv:1908.00005, sec. 9.2, p. 47): `c_i (1 - c_j) + (1 - c_i) c_j`; see Conventions below.
- **Sagitta and resolution**: see [Performance and scaling](#performance-and-scaling) (approximate, uniform field).

## Reconstruction chain

1. **Chamber hits** (drift time -> radius; strip/pad charge centroid; RPC strip time).
2. **Segments**: line fit per chamber station (direction and position), resolving
   left-right ambiguity and rejecting delta-ray and noise hits.
3. **Standalone track**: link segments across stations through the spectrometer field,
   fit with material (multiple scattering, energy loss in absorbers).
4. **Extrapolation and matching** to the inner tracker: propagate the tracker track
   through calorimeter material (energy loss, scattering) to the muon system; match by
   position/direction with the extrapolated covariance (a `chi^2` match, not a fixed
   cut only).
5. **Combined fit**: refit hits from both systems; the inner tracker dominates at low
   `p`, the muon system's long lever arm at high `p`. Resolution scales as (approximate)
   `sigma_pT/pT ≈ a pT (measurement) ⊕ b (multiple scattering)`
   ([tracking and vertexing](tracking-and-vertexing.md)).
6. **Trigger matching**: the hardware-level (coarse) muon candidate matched to the
   offline muon for the trigger efficiency ([triggers luminosity pileup](triggers-luminosity-pileup.md)).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track that extrapolates to at least one muon segment (recovers
low-momentum muons that do not reach far). *Calorimeter-tagged*: tracker track with
minimum-ionizing calorimeter deposit (recovers acceptance gaps). *Trigger-level*: coarse
online track. Each type has its own efficiency, purity, and momentum resolution.

## Performance and scaling

- **Resolution**: at low `p`, multiple scattering and energy-loss fluctuations in the absorbers and
  calorimeters upstream of the muon system dominate; at high `p`, spatial
  resolution and alignment of the muon stations limits the *sagitta*
  `s ≈ 0.3 z B L^2/(8 p_perp)`-like measurement (approximate, uniform field; `s` and `L`
  in m, `B` in T, `p_perp` in GeV/c, `z` the charge number; `p_perp` the momentum component
  perpendicular to `B` (`p cos lambda` for pitch angle `lambda`) and `L` the path length in
  the field projected on the bending plane: PDG RPP 2025, eq. 35.57, p. 108, eqs. 35.66 and
  35.68 (`L'`), p. 112; momentum error `∝ p^2 sigma_s`). High-momentum resolution is a **weak-mode/alignment** problem
  (see below).
- **Efficiency**: geometric gaps (cracks, support structures, feet), chamber
  inefficiency, matching and reconstruction inefficiency, quoted **per type and versus
  the detector's coordinates and momentum**; the binning variables and the reference
  sample are parameters to state. At a collider (COL): versus `eta`, `phi`, `pT`, with a
  tag-and-probe from `J/psi` and `Z -> mu mu`
  ([triggers luminosity pileup](triggers-luminosity-pileup.md)). Muon counters of
  ground-based and underground arrays and the outer muon vetoes of underground detectors
  (GND, UGD; PDG RPP 2025, secs. 35.6.6.1 and 36.3.1) need a reference sample of their
  own: see [veto-efficiency measurement](non-collider-muon-detection.md#veto-efficiency-measurement).
- **Rate capability**: drift tubes (long drift, space-charge and occupancy limits),
  cathode-strip chambers (high granularity, good for high rate), RPCs (fast, rate
  limited by resistivity), GEM/Micromegas (high rate, discharge risk)
  ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).
- **Charge sign**: from curvature direction; at high momentum the sagitta shrinks
  toward the alignment/resolution floor and **charge misidentification** grows; it is
  measured from the non-Gaussian tail of the curvature distribution, since a Gaussian
  extrapolation of the core underestimates it ([tracking and vertexing](tracking-and-vertexing.md),
  charge confusion); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts by a constant offset, so `delta p/p` grows with `p` and
  flips sign with charge, mimicking a charge asymmetry.

## Chamber alignment and momentum scale

Muon chambers are aligned with tracks relative to each other and to the inner tracker, while photogrammetry and
in-situ sensors monitor movements and fix the degrees of freedom that tracks constrain weakly; material between
stations (scattering) limits track-based alignment (COL; arXiv:0911.4022, sec. 1, p. 3). The general methods,
weak modes and external constraints are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes); this page keeps the
muon-specific needs and shows chamber alignment for one environment (COL). The **momentum scale** is calibrated against an independent momentum estimate: a resonance
mass (COL), or the range of stopping muons compared with their curvature momentum (UGD, magnetized iron). Scale
terms separate the field integral from the energy loss upstream of the muon system (COL; arXiv:1603.05598, sec. 8.1,
eq. 5, p. 19). A range-based scale inherits the detector mass, the geometry model and the energy-loss model
(UGD; arXiv:0805.3170, sec. 2.4.1, p. 18).

<!-- example: source citation -->
A magnetized steel-scintillator neutrino detector (MINOS) compares range and curvature momenta of stopping muons;
the range momentum carries a 2% systematic error from detector mass, geometry and energy-loss model, which bounds
the field-scale check (arXiv:0805.3170, sec. 2.4.1, p. 18). A collider muon spectrometer (ATLAS) uses a scale term
for the field integral and one for the calorimeter energy loss, per eta-phi region (arXiv:1603.05598, sec. 8.1,
eq. 5, p. 19).
<!-- /example -->

## Energy loss in iron and other absorbers

A muon crossing an absorber or calorimeter loses energy mostly by ionization at low energy and by radiation above
the muon critical energy ([Relations](#relations)). Fit and extrapolation choices follow from three facts (PDG RPP
2025, sec. 34.6, p. 31): the distribution is skewed, so the **most probable loss is far below the mean**; the
radiative tail comes mostly from bremsstrahlung, with photonuclear interactions in the hardest losses; and hard
losses can exceed the detector resolution, so the lost energy must be reconstructed, not only modelled. The
standalone muon-system track is corrected back to the vertex with the absorber loss; a combined fit treats the loss
as a measurement with its own error. Two estimates of the loss exist: a parametrization from the detector
geometry, and the energy measured in the calorimeter, which can be combined (COL; arXiv:1603.05598, sec. 3.2,
p. 5). In a magnetized-iron detector the energy-loss model enters the range momentum directly (UGD;
arXiv:0805.3170, sec. 2.4.1, p. 18).

<!-- example: source citation (simulated case in PDG RPP 2025 and one apparatus) -->
A 1 TeV/c muon crossing 3 m of iron (simulation): most probable loss 8 GeV, full width at half maximum 9 GeV/c,
mean loss 23 GeV (PDG RPP 2025, sec. 34.6, Fig. 34.25, p. 31). A collider muon reconstruction (ATLAS) combining
the parametrized and calorimeter-measured loss reaches a precision of about 30 MeV on the mean loss for 50 GeV
muons (arXiv:1603.05598, sec. 3.2, p. 5).
<!-- /example -->

## Charge-sign quality

The muon part of charge-sign confusion; mechanisms, the three measurement routes and the handoff to hep-measurement
are in [charge confusion](charge-confusion.md#how-hep-detector-measures-the-rate).

- **Significance cut**: require `|q/p| / sigma(q/p)` above a threshold, and check that the charge ratio no longer
  changes with it (UGD; arXiv:0705.3815, sec. III B 3, p. 5).
- **Fit agreement**: take the combined (tracker plus muon system) fit only when its `q/p` agrees with the
  tracker-only fit within a few `sigma(q/p)` (COL; arXiv:1206.4071, sec. 3, p. 9).
- **Field reversal**: combine forward and reversed field data with the geometric mean of [Relations](#relations),
  which cancels charge-dependent acceptance and alignment errors (UGD, the one environment in the sources found;
  arXiv:0705.3815, sec. IV, p. 7).
- **Weak-mode curvature bias**: a twist (`delta phi = tau z`) biases `kappa ∝ q/pT` and is weakly constrained by
  cosmic tracks alone (COL in the sources found; arXiv:1403.2286, sec. 4.4, p. 14); see
  [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes).
- **Two charges of one muon**: a through-going cosmic muon reconstructed in the upper and lower halves, with strict
  cuts on the tag half; multi-muon events are the background, so require exactly one muon per half (COL only in the
  sources found; arXiv:0911.4994, sec. 7, p. 25).
- **Resonance same-sign pairs**: the pair model of [Relations](#relations), both legs fitted together and
  same-sign backgrounds subtracted (COL only: it needs abundant neutral resonances; arXiv:1908.00005, sec. 9.2,
  p. 47). The route with a beam of known sign (FXT) is a **gap**: no source was found.

<!-- example: source citation -->
Atmospheric-muon charge ratio in a magnetized-iron detector (MINOS): `|q/p|/sigma(q/p) >= 2.2`, and the ratio from
forward and reversed field runs, whose single-polarity ratios on the significance plateau were 1.40 and 1.33
(arXiv:0705.3815, sec. III B 3, p. 5; sec. IV, eq. 4, p. 7). Collider "sigma
switch" (CMS): the global fit is used when both fits give `pT` above 200 GeV/c and their `q/p` agree within
`2 sigma(q/p)` of the tracker-only fit (arXiv:1206.4071, sec. 3, p. 9).
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Momentum scale | Resonance mass versus eta, phi, charge | Abundant dimuon resonance | Weak modes mimic a scale; FSR tail | COL |
| Momentum scale, stopping muons | Range versus curvature momentum | Contained tracks; known mass and loss model | Loss-model and mass error enter the range | UGD |
| Track to vertex through absorbers | Parametrized loss, combined with calorimeter energy | Geometry model; calorimeter readout | Mean used where most probable applies; hard losses | COL, UGD |
| Charge-sign selection | `q/p` significance cut; fit-agreement switch | Fit covariance trusted | Cut tuned on the measured ratio | UGD, COL |
| Charge-dependent acceptance | Field reversal, geometric mean | Reversible field; stable detector | Time-dependent drifts between polarities | UGD |
| Confusion rate | Split cosmic halves; resonance same-sign pairs | Two independent measurements of one muon or a zero-charge pair | Multi-muon events; same-sign background | COL |
| Veto, counting, cosmogenics | See [non-collider muon detection](non-collider-muon-detection.md) | | | UGD, FXT, SPC, GND |

## Backgrounds and fakes

- **Punch-through**: hadrons that leak through calorimeter absorbers; falls with
  absorber thickness, rises with hadron energy.
- **Decay in flight**: `pi/K -> mu nu` inside the tracker: a kinked track whose
  combined-fit `chi^2` is bad and whose tracker-muon momentum mismatch is large.
- **Accidental matches**: an unrelated segment (cavern background at a collider (COL),
  noise) matched to a tracker track; grows with rate.
- **Cosmic rays and beam halo** (COL): out-of-time or off-vertex muons; suppress with timing,
  vertex/impact parameter, and back-to-back topology. Outside a collider the same muons
  are the background to reject with a veto or an up-going selection (neutrino telescopes,
  PDG RPP 2025, sec. 36.3.2; [neutrino astronomy](neutrino-astronomy.md#backgrounds)), the
  source of cosmogenic backgrounds removed by a veto on the time correlation with the
  crossing muon (UGD; sec. 36.6.5), or the calibration source of a surface array
  ([ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).
- **Hadron mis-identification vs reconstruction fake**: a pion identified as a muon
  (mis-ID, real object with wrong identity) is a different failure from a fake track
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).

## Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits grouped into segments over a large lever arm; almost no
  other particles (clean but low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes that leave `chi^2` nearly
  unchanged; curl, sagitta and twist modes add a curvature offset that shifts `q/p`
  charge-antisymmetrically, while a radial expansion is charge-symmetric (a momentum-scale
  error constant in `p`; [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes)).
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: at a collider (COL), `Z -> mu mu` mass versus `eta`, `phi`, `pT`,
  and charge (`m` and `q/p` residual versus `q * eta`); in any spectrometer, cosmic-ray
  track splitting (upper/lower half fits) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions** (COL): efficiency measured with tag-and-probe at fixed working point and
  isolation; resolution from `Z` line-shape width or MC truth for the momentum range.
  Charge misID per muon comes from same-sign pairs of a resonance that decays to an
  opposite-sign pair (`Z -> mu mu` at a collider): with per-muon rates `c_i`, `c_j` a pair
  is same-sign with probability `c_i (1 - c_j) + (1 - c_i) c_j` (about `2c` for equal small
  rates), so fit `c` per bin to the background-corrected same-sign counts rather than
  quoting the same-sign fraction as the per-muon rate (the same pair model is fitted for
  `Z -> ee` in arXiv:1908.00005, sec. 9.2).
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate/occupancy (background hits), magnetic field map stability,
  chamber temperature/gas, alignment time-dependence.
- **Strongest data sample**: at a collider (COL), `Z -> mu mu` and `J/psi -> mu mu` (mass
  scale and resolution in bins) and collision tracks for alignment with external
  constraints; in any spectrometer, cosmic muons (split tracks; arXiv:1206.4071, sec. 6.2.1).
  For other muon detectors (the muon vetoes of underground detectors, the muon counters of
  air-shower arrays, muon rings in imaging Cherenkov telescopes; PDG RPP 2025, secs. 36.3.1
  and 36.2.2) the closure sample is a parameter: see
  [non-collider muon detection](non-collider-muon-detection.md),
  [noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md),
  [ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays)
  and [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md).
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([tracking and vertexing](tracking-and-vertexing.md)); **does not transfer**: the
  specific punch-through/absorber background model.

## Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation, and trigger
  efficiencies differ, and each is conditional on the previous
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **Trusting `chi^2` for alignment.** Weak modes leave the fit quality unchanged; check
  `q/p` versus `q*eta` and mass versus `eta`, `phi`.
- **Same-sign fraction read as charge flip only.** Backgrounds also contribute; correct
  for them before quoting charge misID.
- **Identical efficiency applied to all muon types.** A segment-tagged muon is not a
  combined muon.
- **Ignoring decay in flight for hadron-mimic estimates.** Depends on the track's
  position in the tracker.
- **Mean loss used as the typical loss.** At high energy the most probable loss in iron is far below the mean;
  correcting every track by the mean biases the core.
- **A single-polarity charge ratio.** Charge-dependent acceptance and alignment errors survive; reverse the field or
  model them.

## Deliverables

- The muon-type definitions, with efficiency, purity, resolution, and charge misID per type
  (a per-muon rate, not the same-sign pair fraction).
- Tag-and-probe (or equivalent) efficiency with its uncertainty: binomial (Clopper-Pearson)
  only for unweighted, background-free, independent probes; a background-subtracted
  resonance sample needs the simultaneous pass/fail fit of
  [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement),
  with the tag-probe correlations handled; and the trigger matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.
- The momentum-scale reference (resonance or range), the absorber energy-loss treatment (mean or most probable,
  parametrized or measured), and the charge-sign cuts with the polarities used.

## Tool hooks

A field-reversal charge-ratio tool (not yet in the plugin):

- **Inputs**: per momentum bin, counts `N+` and `N-` and live time for each field polarity (integers; seconds).
- **Outputs**: `r_a`, `r_b` and `r = (r_a r_b)^(1/2)` with statistical errors, the single-polarity ratios, and their
  spread as a measure of the acceptance asymmetry ([Relations](#relations)).
- **Conventions**: polarity labels `forward` and `reverse`; `N+` means positive reconstructed charge.
- **Negative control**: a synthetic sample with charge-asymmetric acceptance (`A+ != A-`) and a known true ratio:
  each single-polarity ratio is biased, the geometric mean returns the true ratio within its error.
- **Statuses**: `ok`; `polarity-missing` (only one polarity: no cancellation, ratio reported as biased);
  `low-counts` (a zero count in a bin: no ratio).

## Environment coverage

Cells give source IDs of the run's cache (PDG = PDG RPP 2025, passage of particles through matter).

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Muon-chamber alignment | arxiv_0911.4022 | gap ([calibration and alignment](calibration-and-alignment.md)) | n/a: no muon system in orbit found | gap ([calibration and alignment](calibration-and-alignment.md)) | n/a: counters, not tracking chambers | gap |
| Momentum scale | arxiv_1603.05598 | gap | gap | arxiv_0805.3170 | n/a: no momentum measurement | gap |
| Energy loss in absorbers | PDG; arxiv_1603.05598 | gap | n/a: absorber-free spectrometers | PDG; arxiv_0805.3170 | gap | gap |
| `q/p` significance, fit agreement | arxiv_1206.4071 | gap | [space-based direct detection](space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer) | arxiv_0705.3815 | n/a: no charge sign | n/a |
| Field reversal | gap | gap | gap | arxiv_0705.3815 | n/a: no charge sign | n/a |
| Weak-mode curvature bias | arxiv_1403.2286 | gap | gap | gap | n/a | n/a |
| Split cosmic halves | arxiv_0911.4994 | gap | gap | gap | n/a | n/a |
| Resonance same-sign pairs | arxiv_1908.00005 | n/a: no abundant neutral resonance | n/a: same | n/a: same | n/a | n/a |
| Known-sign beam | n/a | gap | n/a | n/a | n/a | gap |
| Vetoes, counting, cosmogenics, albedo | [non-collider muon detection](non-collider-muon-detection.md#environment-coverage) | same | same | same | same | same |

## Citations

Inline citations give the arXiv number and a locator; annotated entries are in the
[bibliography](detector-principles-bibliography.md) (PDG reviews under General and cross-cutting; the muon-system
sources in its muon-systems split file).
