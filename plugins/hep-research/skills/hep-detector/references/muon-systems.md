# Muon Systems: Spectrometers, Identification, and Trigger

Muon detection and reconstruction: drift-tube, cathode-strip, RPC-, GEM-, and
Micromegas-based chambers; standalone, combined, segment-tagged, calorimeter-tagged, and
trigger-level muons. The PID summary is in [particle identification](particle-identification.md);
technology physics is in [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md);
alignment weak modes in [calibration and alignment](calibration-and-alignment.md) and
[tracking and vertexing](tracking-and-vertexing.md). Environment codes: COL collider; FXT fixed-target
and test beam; SPC space and high-altitude balloon; UGD underground, neutrino and rare-event; GND ground-based
cosmic-ray and gamma-ray arrays; NUC nuclear and low-energy physics. Environments covered: COL, UGD, SPC, FXT
(table below); NUC has no muon system source. Muon vetoes, veto-efficiency measurement, cosmogenic tagging,
muon counting, and muons and albedo in orbit are in
[non-collider muon detection](non-collider-muon-detection.md). Atmospheric-muon rejection in neutrino telescopes (up-going
selection, veto regions) and the self-veto of atmospheric neutrinos are in [neutrino astronomy](neutrino-astronomy.md#backgrounds).

## Why muons are special

Muons are close to minimum-ionizing, rarely shower below a few hundred GeV, and
traverse the calorimeters, so the outermost layers see them nearly free of other
particles. Radiative losses dominate above the muon critical energy (a few hundred GeV in iron), so
catastrophic losses and showers in the absorbers must be modelled ([Relations](#relations)). A muon system therefore
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

## Reconstruction chain

1. **Chamber hits** (drift time -> radius; strip/pad charge centroid; RPC strip time).
2. **Segments**: line fit per chamber station (direction and position), resolving
   left-right ambiguity and rejecting delta-ray and noise hits.
3. **Standalone track**: link segments across stations through the spectrometer field,
   fit with material (multiple scattering, energy loss in absorbers).
4. **Extrapolation and matching** to the inner tracker: propagate the tracker track
   through calorimeter material (energy loss, scattering) to the muon system; match by
   position/direction with the extrapolated covariance (a `chi^2` match).
5. **Combined fit**: refit hits from both systems; the inner tracker dominates at low
   `p`, the muon system's long lever arm at high `p` ([tracking and vertexing](tracking-and-vertexing.md)).
6. **Trigger matching**: the hardware-level (coarse) muon candidate matched to the
   offline muon for the trigger efficiency ([triggers luminosity pileup](triggers-luminosity-pileup.md)).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track that extrapolates to at least one muon segment (recovers
low-momentum muons). *Calorimeter-tagged*: tracker track with
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
  35.68 (`L'`), p. 112; momentum error `∝ p^2 sigma_s`). High-momentum resolution is a **weak-mode/alignment** problem.
- **Efficiency**: geometric gaps (cracks, support structures, feet), chamber
  inefficiency, matching and reconstruction inefficiency, quoted **per type and versus
  the detector's coordinates and momentum**; the binning variables and the reference
  sample are parameters to state. At a collider (COL): versus `pT` and `eta`, with a
  tag-and-probe from `J/psi` (low `pT`) and `Z -> mu mu` (arXiv:1206.4071, sec. 5.1, Figs. 11-12, PDF pp. 20-23;
  [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement)). Muon counters of
  ground-based and underground arrays and the outer muon vetoes of underground detectors
  (GND, UGD; counters: [ground-based detection arrays](ground-based-detection-arrays.md); vetoes: PDG RPP 2025,
  sec. 36.3.1) need a reference sample of their own: see [veto-efficiency measurement](non-collider-muon-detection.md#veto-efficiency-measurement).
- **Rate capability**: drift tubes (long drift, space-charge and occupancy limits),
  cathode-strip chambers (multiwire chambers read on cathode strips: wire pitch and space charge limit
  rate as for an MWPC), RPCs (fast, rate
  limited by resistivity), GEM/Micromegas (high rate, discharge risk)
  ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).
- **Charge sign**: from curvature direction; at high momentum the sagitta shrinks
  toward the alignment/resolution floor and **charge misidentification** grows;
  measure it from the non-Gaussian curvature tail, not a Gaussian extrapolation of the
  core ([tracking and vertexing](tracking-and-vertexing.md),
  charge confusion); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts by a constant offset, so `delta p/p` grows with `p` and
  flips sign with charge, mimicking a charge asymmetry.

## Chamber alignment and momentum scale

Muon chambers are aligned with tracks relative to each other and to the inner tracker, while photogrammetry and
in-situ sensors monitor movements and fix the degrees of freedom that tracks constrain weakly; material between
stations (scattering) limits track-based alignment (COL; arXiv:0911.4022, sec. 1, p. 1). General methods, weak
modes and external constraints are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes); chamber alignment is
shown here for one environment (COL). The **momentum scale** is calibrated against an independent momentum estimate: a resonance
mass (COL), or the range of stopping muons compared with their curvature momentum (UGD, magnetized iron). Scale
terms separate the field integral from the energy loss upstream of the muon system (COL; arXiv:1603.05598, sec. 8.1,
eq. 5, p. 19). A range-based scale inherits the detector mass, the geometry model and the energy-loss model
(UGD; arXiv:0805.3170, sec. 2.4.1, p. 18).

<!-- example: source citation -->
A magnetized steel-scintillator neutrino detector (MINOS) compares range and curvature momenta of stopping muons;
the range momentum carries a 2% systematic error from detector mass, geometry and energy-loss model, which bounds
the field-scale check (arXiv:0805.3170, sec. 2.4.1, p. 18).
<!-- /example -->

## Energy loss in iron and other absorbers

For a muon crossing absorbers and calorimeters ([Relations](#relations)), fit and extrapolation choices follow
from three facts (PDG RPP 2025, sec. 34.6, p. 31): the distribution is skewed, so the **most probable loss is far below the mean**; the
radiative tail comes mostly from bremsstrahlung, with photonuclear interactions in the hardest losses; and hard
losses can exceed the detector resolution, so the lost energy must be reconstructed, not only modelled. The
standalone muon-system track is corrected back to the vertex with the absorber loss; a combined fit treats the loss
as a measurement with its own error. Two estimates of the loss exist: a parametrization from the detector
geometry, and the energy measured in the calorimeter, which can be combined (COL; arXiv:1603.05598, sec. 3.2,
p. 5). In a magnetized-iron detector the energy-loss model enters the range momentum directly (UGD;
arXiv:0805.3170, sec. 2.4.1, p. 18).

<!-- example: source citation (simulated case in PDG RPP 2025 and one apparatus) -->
A 1 TeV/c muon crossing 3 m of iron (simulation): most probable loss 8 GeV, full width at half maximum 9 GeV/c,
mean loss 23 GeV (PDG RPP 2025, sec. 34.6, p. 31, and Fig. 34.25, p. 32). A collider muon reconstruction (ATLAS) combining
the parametrized and calorimeter-measured loss reaches a precision of about 30 MeV on the mean loss for 50 GeV
muons (arXiv:1603.05598, sec. 3.2, p. 5).
<!-- /example -->

## Charge-sign quality

The muon part of charge-sign confusion; mechanisms, the three measurement routes and the handoff to hep-measurement
are in [charge confusion](charge-confusion.md#how-hep-detector-measures-the-rate).

- **Significance cut**: require `|q/p| / sigma(q/p)` above a threshold fixed without the measured ratio (in
  simulation), then check that the measured ratio is flat above it within its errors, as a cross-check only (UGD;
  flat above the cut in arXiv:0705.3815, sec. III B 3, p. 5).
- **Fit agreement**: take the combined (tracker plus muon system) fit only when both fits give a momentum above the
  crossover where the muon system improves the resolution and its `q/p` agrees with the tracker-only fit within a
  stated number of `sigma(q/p)` of that fit; otherwise the tracker-only fit (COL; arXiv:1206.4071, sec. 3, PDF p. 9).
- **Field reversal**: combine forward and reversed field data with the geometric mean of [Relations](#relations),
  which cancels the acceptance and alignment errors that swap with the field, not charge confusion (UGD, the one environment in the sources found;
  arXiv:0705.3815, sec. IV, p. 7).
- **Weak-mode curvature bias**: a twist (`delta phi = tau z`) biases `kappa ∝ q/pT` and is weakly constrained by
  cosmic tracks alone (COL inner tracker in the sources found; arXiv:1403.2286, sec. 4.4, PDF p. 14); see
  [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes).
- **Two charges of one muon**: a through-going cosmic muon reconstructed in the upper and lower halves, with strict
  cuts on the tag half; multi-muon events are the background, so require exactly one muon per half (COL only in the
  sources found; arXiv:0911.4994, sec. 7, PDF p. 25).
- **Resonance same-sign pairs**: the pair model of [Relations](#relations), both legs fitted together with the
  same-sign background as an additive term of the expected count (COL only: it needs abundant neutral resonances;
  shown for `Z -> ee` in arXiv:1908.00005, sec. 9.2, p. 47). The route with a beam of known sign (FXT) is a **gap**: no source was found.

<!-- example: source citation -->
Atmospheric-muon charge ratio in a magnetized-iron detector (MINOS): `|q/p|/sigma(q/p) >= 2.2`, read off where the
measured ratio turns flat (Fig. 5: the cross-check route, not the simulation-fixed rule above), and the ratio from
forward and reversed field runs, whose single-polarity ratios on the significance plateau were 1.40 and 1.33
(arXiv:0705.3815, sec. III B 3, p. 5; sec. IV, eq. 4, p. 7). Collider "sigma
switch" (CMS): the global fit is used when both fits give `pT` above 200 GeV/c and their `q/p` agree within
`2 sigma(q/p)` of the tracker-only fit (arXiv:1206.4071, sec. 3, PDF p. 9).
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
  source of cosmogenic backgrounds, whose short-lived part a veto on the time correlation with the crossing muon
  removes and whose long-lived isotopes need other mitigation (UGD; sec. 36.6.5, pp. 54-55), or the calibration source of a surface array
  ([ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).
- **Hadron mis-identification vs fake**: a pion identified as a muon (real object, wrong identity) is
  not a fake track
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).

## Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits grouped into segments over a large lever arm; almost no
  other particles (clean but low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes that leave `chi^2` nearly
  unchanged; a twist mode adds a `q/pT` offset that is the same for both charges, so the momentum bias flips
  sign with charge (arXiv:1403.2286, sec. 4.4, PDF p. 14, a collider inner tracker, transferred;
  [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes)).
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: at a collider (COL), `Z -> mu mu` mass versus `eta`, `phi`, `pT`,
  and charge (`m` and `q/p` residual versus `q * eta`); in a spectrometer that a cosmic muon crosses in two independently
  measured halves, cosmic-ray track splitting (upper/lower half fits) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions** (COL): efficiency measured with tag-and-probe at fixed working point and
  isolation; resolution from `Z` line-shape width or MC truth for the momentum range.
  Charge misID per muon: fit `c` per bin with the pair model of [Relations](#relations) (about `2c` for equal small
  rates) to the same-sign counts of an opposite-sign resonance with their background, vary the mass window and
  check `c` against truth in simulation, never quoting the same-sign fraction as the rate (pair model fitted for
  `Z -> ee` in arXiv:1908.00005, sec. 9.2, p. 47).
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate/occupancy (background hits), magnetic field map stability,
  chamber temperature/gas, alignment time-dependence.
- **Strongest data sample**: at a collider (COL), `Z -> mu mu` and `J/psi -> mu mu` (mass
  scale and resolution in bins) and collision tracks for alignment with external
  constraints; in a spectrometer that a cosmic muon crosses in two independently measured halves, cosmic muons (split
  tracks, halves selected to resemble the physics tracks; COL in the source: near the interaction point, barrel
  only: arXiv:1206.4071, sec. 6.2.1, PDF p. 36).
  For other muon detectors (underground muon vetoes, air-shower muon counters, muon
  rings in imaging Cherenkov telescopes; PDG RPP 2025, secs. 36.3.1,
  35.6.6.1 (RPC counters only) and 36.2.2) the closure sample is a parameter: see
  [non-collider muon detection](non-collider-muon-detection.md),
  [ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays)
  and [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md).
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([tracking and vertexing](tracking-and-vertexing.md)); **does not transfer**: the
  specific punch-through/absorber background model.

## Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation, and trigger
  efficiencies differ, and each is conditional on the previous
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **Trusting `chi^2` for alignment.** Weak modes leave the fit quality nearly unchanged; check
  `q/p` versus `q*eta` and mass versus `eta`, `phi`.
- **Same-sign fraction read as charge flip only.** Backgrounds also contribute; correct
  for them before quoting charge misID.
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
  exact only for unweighted (or frequency-weighted), background-free, independent probes, approximate with positive
  sampling weights (Kish effective size); a resonance sample with any background needs the simultaneous pass/fail
  fit of [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement),
  with the tag-probe correlations handled and the method bias measured in simulation; and the trigger matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.
- The momentum-scale reference (resonance or range), the absorber energy-loss treatment (mean or most probable,
  parametrized or measured), and the charge-sign cuts with the polarities used.

## Tool hooks

A field-reversal charge-ratio tool (not yet in the plugin):

- **Inputs**: per momentum bin, counts `N+` and `N-` and live time `t` for each field polarity (integers;
  seconds), optionally as forward/reverse subsets of equal live time; `n_min` (default 10, at least 5) and `k` (default
  3, 2 to 5), fixed in advance and written out; a simulated confusion bias.
- **Outputs**, with statistical errors: `r_a = (N+/t)_forward / (N-/t)_reverse`,
  `r_b = (N+/t)_reverse / (N-/t)_forward` (arXiv:0705.3815, sec. IV A, eqs. 2-3, p. 7), `r = (r_a r_b)^(1/2)`
  (eq. 4), and `|r_a - r_b|/2` on equal-live-time subsets, the residual of bias errors (acceptance, field, alignment)
  (sec. IV D, item 1, p. 10); `r` per equal-live-time pair and its range over shifted pairs (eqs. 5-6 on p. 8;
  item 2, p. 10); the one-sided confusion systematic (`r` biased low for `r > 1`; item 3); the single-polarity
  ratios, whose spread measures the acceptance asymmetry only when the swap holds.
- **Conventions**: polarity labels `forward` and `reverse`; `N+` means positive reconstructed charge.
- **Negative control**: (1) an exact swap with `A+ != A-`: the single-polarity ratios are biased,
  `r_a = r_b` and `r` give the true ratio within errors (`ok`); (2) the reverse-polarity
  `mu+` acceptance drifted by `d` = 1.2 with 10^4 muons per charge and polarity (significant at `k` = 3):
  `r_b/r_a = d`, `r` biased by `d^(1/2)`: `cancellation-failed`; (3) confusion 0.1 with `A+ = A-`: `r_a = r_b`, `r`
  6% low, never reported without the confusion systematic; (4) a 10% live-time error: `r` exact and kept.
- **Statuses** (a set; headline `polarity-missing` > `low-counts` > `cancellation-failed` > `ok`): `ok`;
  `polarity-missing` (only one polarity: no cancellation, ratio reported as biased);
  `low-counts` (a count below `n_min`: exact binomial intervals on `N+_forward/(N+_forward + N-_reverse)` and its
  `r_b` twin, mapped to `r_a`, `r_b` with the live times; no ratio at zero);
  `cancellation-failed` (`|r_a - r_b|` above `k` times its error, on equal-live-time subsets: the swap failed;
  a live-time error alone also splits them, so a warning: `r` is kept); `no-drift-check` (no equal-live-time
  subsets). Confusion and charge-dependent effects that do not reverse with the field leave `r_a = r_b`: the test
  is blind to them.

## Environment coverage

Cells give source IDs (PDG = PDG RPP 2025, passage of particles through matter).

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Muon-chamber alignment | arxiv_0911.4022 | gap | n/a: no muon system in orbit found | gap | n/a: counters, not tracking chambers | gap |
| Momentum scale | arxiv_1603.05598 | gap | gap | arxiv_0805.3170 | n/a: no momentum measurement | gap |
| Energy loss in absorbers | PDG; arxiv_1603.05598 | gap | n/a: absorber-free spectrometers | PDG; arxiv_0805.3170 | gap | gap |
| `q/p` significance, fit agreement | arxiv_1206.4071 | gap | gap ([space-based direct detection](space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer): MDR only) | arxiv_0705.3815 | n/a: no charge sign | n/a |
| Field reversal | gap | gap | gap | arxiv_0705.3815 | n/a: no charge sign | n/a |
| Weak-mode curvature bias | arxiv_1403.2286 (inner tracker; transfer) | gap | gap | arxiv_0705.3815 (cancelled by field reversal) | n/a | n/a |
| Split cosmic halves | arxiv_0911.4994 | gap | gap | gap | n/a | n/a |
| Resonance same-sign pairs | arxiv_1908.00005 | n/a: no abundant neutral resonance | n/a: same | n/a: same | n/a | n/a |
| Known-sign beam | n/a | gap | n/a | n/a | n/a | gap |
| Vetoes, counting, cosmogenics, albedo | [non-collider muon detection](non-collider-muon-detection.md#environment-coverage) | same | same | same | same | same |

## Citations

Inline citations give the arXiv number and a locator (p. is the printed page; PDF p. the PDF page where it differs); annotated entries are in the
[muon-systems bibliography](detector-principles-bibliography-muon-systems.md), a split file of the
[bibliography](detector-principles-bibliography.md).
