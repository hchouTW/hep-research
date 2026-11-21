# Muon Systems: Spectrometers, Identification, and Trigger

Muon chambers (drift tube, cathode strip, RPC, GEM, Micromegas) and muon types (standalone, combined, tagged,
trigger-level). The PID summary is in [particle identification](particle-identification.md);
technology physics is in [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md).
Environment codes: COL collider; FXT fixed-target
and test beam; SPC space and high-altitude balloon; UGD underground, neutrino and rare-event; GND ground-based
cosmic-ray and gamma-ray arrays; NUC nuclear and low-energy physics. Sourced here: COL and UGD, FXT and SPC are gaps or redirected, GND is reached through links only; NUC has
no muon system source. Non-collider muons:
[non-collider muon detection](non-collider-muon-detection.md). Neutrino-telescope muon rejection is in [neutrino astronomy](neutrino-astronomy.md#backgrounds).

## Why muons are special

Muons are close to minimum-ionizing, rarely shower below a few hundred GeV and traverse the calorimeters, so
the outer layers see them nearly alone. Above the muon critical energy (a few hundred GeV in iron) radiative
losses dominate and must be modelled ([Relations](#relations)). A muon system identifies (it survives the
absorbers) and measures momentum independently at a large lever arm, often in its own field.

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
  arXiv:1908.00005, sec. 9.2, p. 47): `c_i (1 - c_j) + (1 - c_i) c_j`.

## Reconstruction chain

1. **Chamber hits** (drift time -> radius; strip/pad charge centroid; RPC strip time).
2. **Segments**: line fit per station (direction, position), resolving left-right ambiguity, rejecting
   delta-ray and noise hits.
3. **Standalone track**: link segments across stations through the field, fit with material (scattering,
   absorber loss).
4. **Extrapolation and matching**: propagate the tracker track through calorimeter material (loss, scattering)
   and match position and direction with the extrapolated covariance (a `chi^2` match).
5. **Combined fit**: refit hits from both systems; the inner tracker dominates the fit at low
   `p`, and the muon system's long lever arm only improves it at high `p` ([tracking and vertexing](tracking-and-vertexing.md), COL
   crossover in `pT`: arXiv:1206.4071, secs. 3 and 6.2.1, PDF pp. 7 and 37).
6. **Trigger matching**: the coarse hardware-level candidate matched to the offline muon for the trigger efficiency ([triggers luminosity pileup](triggers-luminosity-pileup.md)).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track reaching at least one muon segment (low-momentum muons).
*Calorimeter-tagged*: tracker track with a minimum-ionizing calorimeter deposit (gaps). *Trigger-level*: coarse online track.

## Performance and scaling

- **Resolution**: at low `p`, multiple scattering and energy-loss fluctuations in the absorbers and
  calorimeters upstream of the muon system dominate; at high `p`, spatial
  resolution and alignment of the muon stations limits the *sagitta*
  `s ≈ 0.3 z B L^2/(8 p_perp)`-like measurement (approximate, uniform field; `s` and `L`
  in m, `B` in T, `p_perp` in GeV/c, `z` the charge number; `p_perp` the momentum component
  perpendicular to `B` (`p cos lambda` for pitch angle `lambda`) and `L` the path length in
  the field projected on the bending plane: PDG RPP 2025, eq. 35.57, p. 108, eqs. 35.66 and
  35.68 (`L'`), p. 112; momentum error `∝ p^2 sigma_s`). Weak modes add a bias (**Charge sign**).
- **Efficiency**: geometric gaps (cracks, supports, feet), chamber, matching and reconstruction losses, quoted
  **per type and versus the detector's coordinates and momentum**; binning and reference sample are parameters. At a collider (COL): versus `pT` (Fig. 11) and `eta` (Fig. 12), with a
  tag-and-probe on tracker-track probes from `J/psi` (low `pT`) and `Z -> mu mu` (arXiv:1206.4071, sec. 5.1, PDF pp. 20-23;
  [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement)). Muon counters and
  outer muon vetoes (GND, UGD) need reference samples of their own: see [veto-efficiency measurement](non-collider-muon-detection.md#veto-efficiency-measurement).
- **Rate capability**: limited by drift length, space charge and occupancy (drift tubes, MWPC-type
  cathode-strip chambers), resistivity (RPCs) or discharges (GEM/Micromegas) ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).
- **Charge sign**: from curvature direction; **charge misidentification** grows as the sagitta shrinks toward
  the alignment/resolution floor; measure it from the non-Gaussian curvature tail, not a Gaussian extrapolation of
  the core ([charge-sign quality](#charge-sign-quality)); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts by a constant offset, so `delta p/p` grows with `p` and flips sign with charge.

## Chamber alignment and momentum scale

Muon chambers are aligned with tracks relative to each other and to the inner tracker, while photogrammetry and
in-situ sensors monitor movements and fix the degrees of freedom that tracks constrain weakly; material between
stations (scattering) limits track-based alignment (COL; arXiv:0911.4022, sec. 1, p. 1, PDF page 3). General methods, weak
modes and external constraints are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes); chamber alignment is
shown here for COL only. The **momentum scale** is calibrated against an independent momentum estimate: a resonance
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

Fit and extrapolation through absorbers ([Relations](#relations)) follow
from three facts (PDG RPP 2025, sec. 34.6, p. 31): the distribution is skewed, so the **most probable loss is far below the mean**; the
radiative tail comes mostly from bremsstrahlung, with photonuclear interactions in the hardest losses; and hard
losses can exceed the detector resolution, so the lost energy must be reconstructed, not only modelled. The
standalone muon-system track is corrected back to the vertex with the absorber loss; a combined fit treats the loss
as a measurement with its own error. The loss is parametrized from the geometry,
measured in the calorimeter, or both combined (COL; arXiv:1603.05598, sec. 3.2,
p. 5). In a magnetized-iron detector the energy-loss model enters the range momentum directly (UGD;
arXiv:0805.3170, sec. 2.4.1, p. 18).

<!-- example: source citation (simulated case in PDG RPP 2025 and one apparatus) -->
A 1 TeV/c muon crossing 3 m of iron (simulation): most probable loss 8 GeV, full width at half maximum 9 GeV/c,
mean loss 23 GeV (PDG RPP 2025, sec. 34.6, text p. 31, Fig. 34.25 on p. 32). A collider muon reconstruction (ATLAS) combining
the parametrized and calorimeter-measured loss reaches a precision of about 30 MeV on the mean loss for 50 GeV
muons (arXiv:1603.05598, sec. 3.2, p. 5).
<!-- /example -->

## Charge-sign quality

Mechanisms, measurement routes and the hep-measurement handoff: [charge confusion](charge-confusion.md).

- **Significance cut**: require `|q/p| / sigma(q/p)` above a threshold fixed in simulation, blind to the measured
  ratio, then check that the measured ratio is flat above it within its errors, as a cross-check only: if not flat,
  tighten the cut in simulation or carry the slope as a systematic, and record it (UGD;
  flat above the cut in arXiv:0705.3815, sec. III B 3, p. 5).
- **Fit agreement**: take the combined (tracker plus muon system) fit only when both fits give a transverse momentum
  above a stated crossover (variable and value) where the muon system improves the resolution and its `q/p` agrees
  with the tracker-only fit within a stated number of `sigma(q/p)` of that fit; otherwise the tracker-only fit (COL; arXiv:1206.4071, sec. 3, PDF p. 9).
- **Field reversal**: combine forward and reversed field data with the geometric mean of [Relations](#relations),
  which cancels the acceptance and alignment errors that swap with the field, and charge-sign bias errors, but not
  random confusion, which survives eq. 4 (UGD only in the sources found; arXiv:0705.3815, secs. IV A and IV D, pp. 7 and 9-10).
- **Weak-mode curvature bias**: a twist (`delta phi = tau z`) biases `kappa ∝ q/pT` and is weakly constrained by
  cosmic tracks alone (COL inner tracker in the sources found; arXiv:1403.2286, sec. 4.4, PDF p. 14).
- **Two charges of one muon**: a through-going cosmic muon reconstructed in the upper and lower halves, with strict
  cuts on the tag half; multi-muon events are the background, so require exactly one muon per half (COL only in the
  sources found; arXiv:0911.4994, sec. 7, PDF pp. 25 and 26).
- **Resonance same-sign pairs**: the pair model of [Relations](#relations), both legs fitted together with the
  same-sign background as an additive term of the fitted Poisson expectation, not subtracted (COL in the sources
  found; shown for `Z -> ee` in arXiv:1908.00005, sec. 9.2, p. 47). The route with a beam of known sign (FXT) is a **gap**: no source was found.

<!-- example: source citation -->
Atmospheric-muon charge ratio in a magnetized-iron detector (MINOS): `|q/p|/sigma(q/p) >= 2.2`, set where the
measured ratio turns flat (Fig. 5), i.e. on the data, which the rule above forbids (plateau as cross-check only), and the ratio from
forward and reversed field runs, whose single-polarity ratios on the significance plateau were 1.40 and 1.33
(arXiv:0705.3815, sec. III B 3, p. 5; sec. IV, eq. 4, p. 7). Collider "sigma
switch" (CMS): the global fit is used when both fits give `pT` above 200 GeV/c and their `q/p` agree within
`2 sigma(q/p)` of the tracker-only fit (arXiv:1206.4071, sec. 3, PDF p. 9). Its cosmic split tracks need, per half, hits in
at least eight strip layers and one pixel hit (sec. 6.2.1, PDF p. 36).
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
| Veto, counting, cosmogenics | See [non-collider muon detection](non-collider-muon-detection.md) | | | COL (multi-muon events), FXT, SPC, UGD, GND; NUC a gap |

## Backgrounds and fakes

- **Punch-through**: hadrons that leak through calorimeter absorbers; falls with
  absorber thickness, rises with hadron energy.
- **Decay in flight**: `pi/K -> mu nu` inside the tracker: often (not always) a kinked track
  with poor combined-fit `chi^2` and tracker-muon momentum mismatch (arXiv:1603.05598 section 5, page 6), and a residual passes: take it from simulation per working point and `pT` bin, with its data validation stated or marked unvalidated.
- **Accidental matches**: an unrelated segment (cavern background (COL),
  noise) matched to a tracker track; grows with rate.
- **Cosmic rays and beam halo** (COL): out-of-time or off-vertex muons; suppress with timing, impact parameter
  and back-to-back topology. Outside a collider the same muons
  are a background to veto or remove by an up-going selection (neutrino telescopes,
  PDG RPP 2025, sec. 36.3.2), a source of cosmogenic backgrounds (UGD; sec. 36.6.5, pp. 54-55), or calibrate a surface array
  ([ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).
- **Mis-identified hadron**: a pion called a muon is a real object with a wrong identity, not a fake track ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).

<!-- example: source citation -->
ATLAS muon identification passes 0.11-0.76% of hadrons decaying in flight, by working point and `pT` (`ttbar`
simulation; arXiv:1603.05598, Table 1, p. 8), validated with `K0S -> pi pi` pions in data (sec. 5, p. 7).
<!-- /example -->

## Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits in segments over a large lever arm; few other particles (clean, low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes that leave `chi^2` nearly
  unchanged; a twist biases `kappa ∝ q/pT` (arXiv:1403.2286, sec. 4.4, PDF p. 14, COL, transferred);
  derived, not in it: at fixed `eta` the `q/pT` offset is charge- and `pT`-independent,
  so the momentum bias flips sign with charge (the twist in [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes)).
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: at a collider (COL), `Z -> mu mu` mass versus `eta`, `phi`, `pT`,
  and charge (`m` and `q/p` residual versus `q * eta`); cosmic split tracks (below) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions** (COL): tag-and-probe efficiency at fixed working point and isolation, resolution from the
  `Z` line-shape width or MC truth.
  Charge misID per muon: fit `c` per bin with the pair model of [Relations](#relations) (about `2c` for equal small
  rates) to the same-sign counts with their background ([charge-sign quality](#charge-sign-quality)), vary the
  mass window and check `c` against truth in simulation, never quoting the same-sign fraction as the rate.
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate and occupancy, field-map stability, chamber temperature and gas, alignment drifts.
- **Strongest data sample**: at a collider (COL), `Z -> mu mu` and `J/psi -> mu mu` (mass
  scale and resolution in bins) and collision tracks for alignment with external
  constraints; in a spectrometer crossed in two independently measured halves, cosmic split tracks required to
  pass near the interaction point, with a stated hit count per half (example in [Charge-sign quality](#charge-sign-quality); COL, barrel only: arXiv:1206.4071, sec. 6.2.1, PDF p. 36).
  For vetoes, air-shower counters and Cherenkov-telescope muon rings the closure sample is a parameter: see
  [non-collider muon detection](non-collider-muon-detection.md)
  and [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md).
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([tracking and vertexing](tracking-and-vertexing.md)); **does not transfer**: the
  specific punch-through/absorber background model.

## Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation and trigger efficiencies differ, each
  conditional on the previous ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **A single-polarity charge ratio.** Charge-dependent acceptance survives; reverse the field or model it.

## Deliverables

- The muon-type definitions, with efficiency, purity, resolution, and charge misID per type
  (a per-muon rate, not the same-sign pair fraction).
- Tag-and-probe (or equivalent) efficiency with its uncertainty, tag-probe correlations handled (bootstrap over events if both legs are tag and probe) and the method bias measured versus MC truth, for every sample: Clopper-Pearson (exact: coverage at least nominal) only for unweighted (or
  frequency-weighted), background-free, independent probes, approximate with positive weights (Kish size), neither with mixed-sign weights (a bootstrap, stated); any background needs a subtracting estimate: for a resonance the pass/fail
  fit of [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement), else a stated subtraction with propagated error; and the trigger matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.
- The momentum-scale reference (resonance or range), the absorber energy-loss treatment (mean or most probable,
  parametrized or measured), and the charge-sign cuts with the polarities used.

## Tool hooks

A field-reversal charge-ratio tool (not yet in the plugin):

- **Inputs**: per momentum bin, counts `N+` and `N-` and live time `t` for each field polarity (integers;
  seconds) and the relative live-time uncertainty per polarity (required: if absent, 0 and `no-live-time-uncertainty`), optionally as forward/reverse subsets of equal live time; `n_min` (default 10, at least 5) and `k` (default
  3, 2 to 5), fixed in advance and written out; a simulated confusion bias.
- **Outputs**, with statistical errors: `r_a = (N+/t)_forward / (N-/t)_reverse`,
  `r_b = (N+/t)_reverse / (N-/t)_forward` (arXiv:0705.3815, sec. IV A, eqs. 2-3, p. 7), `r = (r_a r_b)^(1/2)`
  (eq. 4), and `|r_a - r_b|/2` on equal-live-time subsets, the residual of bias errors (acceptance, field, alignment)
  (sec. IV D, item 1, p. 10); `r` per equal-live-time pair and its range over shifted pairs (eqs. 5-6 on p. 8;
  item 2, p. 10); the one-sided confusion systematic from the simulated bias (`r` biased low for `r > 1`; item 3 there); the
  single-polarity ratios, whose spread measures the acceptance asymmetry only when the swap holds.
- **Conventions**: polarity labels `forward` and `reverse`; `N+` means positive reconstructed charge.
- **Negative control**: (1) an exact swap with `A+ != A-`, equal-live-time subsets, a zero simulated bias and live-time uncertainty given: the single-polarity ratios are biased,
  `r_a = r_b` and `r` give the true ratio within errors (exactly {`ok`}); (2) reverse-polarity `mu+`
  acceptance drifted by `d` = 1.2, 10^4 muons per charge and polarity, subsets, zero bias and zero live-time uncertainty given: `r_b/r_a = d`
  (9 sigma), `r` +9.5% (`d^(1/2)`): {`cancellation-failed`}, `r` kept with `|r_a - r_b|/2` (0.09 `r`) as systematic;
  (3) confusion `c` = 0.1, `A+ = A-`, true `R` = 1.37, subsets and live-time uncertainty given: `r_a = r_b`, `r = ((1-c)R + c)/((1-c) + cR)`, 6.2% low,
  {`ok`} with the confusion systematic covering it, {`no-confusion-systematic`} without it; (4) the forward live time recorded 10% high, uncertainty 10% per polarity, 10^4 muons per charge and polarity, `R` = 1, subsets and zero bias given: `r` exact and
  kept, `r_b/r_a = 1.21` (9.5 sigma statistical, 0.7 with the live-time uncertainty): {`live-time-limited`, `cancellation-failed`}, `|r_a - r_b|/2` kept as a bias bound. (5) as (2) with 10% live-time uncertainty: the set of (4) (0.6 sigma), bound 0.1 covers the +9.5% bias.
- **Statuses** (a set, all written out; headline `polarity-missing` > `low-counts` > `live-time-limited` > `cancellation-failed` >
  `no-live-time-uncertainty` > `no-confusion-systematic` > `no-drift-check` > `ok`): `ok`;
  `polarity-missing` (one polarity only: no cancellation, ratio flagged as biased);
  `low-counts` (a count below `n_min`: exact binomial intervals on `N+_forward/(N+_forward + N-_reverse)` and its
  `r_b` twin, mapped to `r_a`, `r_b` with the live times; no ratio at zero);
  `cancellation-failed` (`|r_a - r_b|` above `k` times its statistical error, on equal-live-time subsets, else on the full sample:
  the swap failed; a live-time error alone also splits them, so a warning: `r` is kept, `|r_a - r_b|/2` its bias systematic); `live-time-limited` (only with `cancellation-failed`: within `k` errors once the live-time uncertainty is included: drift test inconclusive, `|r_a - r_b|/2` kept as a bias bound), `no-live-time-uncertainty` (0 assumed); `no-drift-check` (no equal-live-time
  subsets: time drifts untested); `no-confusion-systematic` (no simulated confusion bias). Confusion and
  charge-dependent effects that do not reverse with the field leave `r_a = r_b`: the test
  is blind to them.

## Environment coverage

Cells give source IDs (PDG = PDG RPP 2025, passage of particles through matter), `gap` when no source was found, `n/a:` with the reason the technique does not apply, `same` for the cell to the left, or a link to the reference that covers it. GND means arrays; ground-level magnetic spectrometers have no code and are a gap.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Muon-chamber alignment | arxiv_0911.4022 | gap | gap | gap | n/a: counter-only arrays (arrays with tracking chambers: gap) | gap |
| Momentum scale | arxiv_1603.05598 | gap | gap | arxiv_0805.3170 | n/a: arrays measure no momentum (spectrometers: gap) | gap |
| Energy loss in absorbers | PDG; arxiv_1603.05598 | gap | gap (spectrometers) | PDG; arxiv_0805.3170 | gap | gap |
| `q/p` significance, fit agreement | arxiv_1206.4071 | gap | gap ([space-based direct detection](space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer): confusion near the MDR, no cut) | arxiv_0705.3815 | n/a: no charge sign | gap |
| Field reversal | gap | gap | gap | arxiv_0705.3815 | n/a: no charge sign | gap |
| Weak-mode curvature bias | arxiv_1403.2286 (inner tracker; transfer) | gap | gap | gap (field reversal cancels swapping misalignment: its row) | n/a: no charge sign | gap |
| Split cosmic halves | arxiv_0911.4994 | gap | gap | gap | n/a: no charge sign | gap |
| Resonance same-sign pairs | arxiv_1908.00005 (`Z -> ee`; muons a transfer) | gap | n/a: no resonance sample | n/a: no resonance sample | n/a: no charge sign | gap |
| Known-sign beam | n/a: no muon beam | gap | n/a: no muon beam | n/a: same | n/a: same | gap |
| Vetoes, counting, cosmogenics, albedo | [non-collider muon detection](non-collider-muon-detection.md#environment-coverage) | same | same | same | same | gap |

## Citations

Inline citations give the arXiv number and a locator (p. printed page; PDF p. where it differs). Bibliography:
[muon systems](detector-principles-bibliography-muon-systems.md).
