# Non-Collider Muon Detection: Vetoes, Cosmogenic Tagging, Muon Counting, and Muons in Orbit

Muons as the background to veto, the cause of cosmogenic backgrounds, the observable of air-shower arrays, and the
calibration source outside collider muon systems. Environment codes: COL collider; FXT fixed-target and test beam;
SPC space and high-altitude balloon; UGD underground, neutrino and rare-event; GND ground-based cosmic-ray and
gamma-ray arrays; NUC nuclear and low-energy physics. Covered: UGD, FXT, SPC, GND, and COL for multi-muon cosmic
events and chamber alignment with cosmic muons; NUC is a gap. Collider muon systems, chamber alignment, energy loss
in absorbers and charge-sign quality are in [muon systems](muon-systems.md). Linked environment pages own
their content:
[neutrino astronomy](neutrino-astronomy.md#backgrounds) (atmospheric-muon veto, self-veto, up-going selection),
[noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors) (protected detectors, vetoes on this page),
[ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays),
[space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff) (albedo). The background budget
and the post-veto live time belong to
[hep-measurement](../../hep-measurement/references/rare-event-and-neutrino-measurements.md#background-budget).

## Relations

- **k-of-n layer coincidence** (exact for independent layers of equal efficiency `eps`; arXiv:2510.13798, sec. 6.2,
  eq. 1, p. 10): 3 of 4 layers give `eps_3/4 = eps^4 + 4 eps^3 (1 - eps) = 4 eps^3 - 3 eps^4`. It fails when the
  layer inefficiencies are not independent, and the bias can have either sign. In the cited measurement the
  low-threshold inefficiency comes from muons running along gaps between counters, and staggered layers make a second
  gap crossing unlikely, so the inefficiencies are anti-correlated and the directly measured `eps_3/4` exceeds the
  extrapolation (sec. 6.2, text and Figs. 6-7, pp. 10-12).
  A gap shared by several layers would push the other way, so measure `eps_3/4` directly as well.
- **Muon band in an absorber-free spectrometer** (exact kinematics for unit charge, with the band width set by the
  velocity resolution; arXiv:astro-ph/0205344, sec. 4, p. 7): `1/beta = sqrt((m_mu/R)^2 + 1)`, with `R` the
  rigidity in GV and `m_mu` in GeV; a band of `± n sigma(1/beta)` around it selects muon candidates, not a pure muon
  sample. The band does not separate electrons and positrons, which an independent identifier (shower
  counter in the cited run) estimates for subtraction, and separates protons only at low rigidity: above the rigidity where the proton band merges the residual protons are
  subtracted statistically with an external proton spectrum normalised to the protons counted below it, with the
  systematic of that subtraction quoted: the result is a corrected muon yield, not a per-event selection
  (sec. 4, pp. 7-8).
- **Time veto length** (approximate rule; arXiv:1101.3101, sec. 4, p. 17): veto for several half-lives of the isotope
  after each muon. The dead exposure grows with the muon rate times the veto length, so long-lived isotopes need a
  veto restricted in space.

## Muon vetoes

Underground detectors are surrounded by water, oil or other shielding and equipped with muon vetoes; light reflection
is maximized in outer veto detectors to raise the muon detection efficiency, while minimized in the inner
detector for reconstruction (UGD; PDG RPP 2025, sec. 36.3.1, p. 12).
The veto must identify muons with very high efficiency and, where cosmogenic isotopes matter, also reconstruct
their tracks (UGD; arXiv:1101.3101, abstract). The same design problem appears in two other environments: a
cosmic-ray veto of scintillator layers around the detector solenoid of a fixed-target experiment declares a muon,
in most of the area it covers, by a space-time coincidence of at least 3 of 4 layers (FXT; arXiv:2510.13798, sec. 6,
first paragraph, p. 9), and the anticoincidence shield of a space gamma-ray telescope vetoes charged particles with
segmented tiles, because an unsegmented shield would also fire on
backsplash from the telescope's own showers (**self-veto** here, not the atmospheric-neutrino one linked above; SPC; arXiv:astro-ph/0702581, abstract). The
parameters are the coverage (hermeticity, gaps), the coincidence logic, the threshold, the segmentation against
self-veto, and the veto window.

<!-- example: source citation -->
Borexino: an outer water-Cherenkov detector around the inner detector; combined veto efficiency at least 99.992%
(arXiv:1101.3101, abstract; sec. 3.2.3, p. 17). Mu2e cosmic-ray veto: four layers of scintillation counters with
wavelength-shifting fibres and SiPMs (arXiv:2510.13798, abstract); required 3-of-4-layer efficiency for cosmic muons as high as 99.99% in
some critical regions (sec. 6, p. 9; overall design goal 99.99%, sec. 1, pp. 2-3). Fermi LAT anticoincidence detector: about 8.3 m^2, 89 tiles; overall efficiency,
averaged over the detector area, for singly charged relativistic particles entering the tracker from the top or the
four sides the shield covers, above the required 0.9997 (arXiv:astro-ph/0702581, abstract; sec. 2.1, p. 3).
<!-- /example -->

### Veto-efficiency measurement

The efficiency of a veto is measured on a reference sample of muons selected **without the flag being tested**
(arXiv:1101.3101, sec. 3.2.1, p. 15). Three methods, by what supplies the reference:

1. **Direct**: an independent detector or signal selects the muons, such as high-energy events in the inner detector
   for the outer-veto flags, or muons timed to a beam spill (UGD; sec. 3.2.1, p. 15). The reference must cover the
   veto's acceptance: a beam sample with near-horizontal tracks is a poor reference for a veto optimized for
   near-vertical cosmic muons (sec. 3.2.1, p. 15).
2. **Mutual**: each tag is measured against samples selected by the others; tags that share sensors are not
   independent, so their mutual efficiencies are not a valid test of each other and are to be handled with care (UGD;
   sec. 3.2.2, p. 16).
3. **Defining layers**: in a layered veto, the other layers (with track-quality cuts) define the muon and the test
   layer or module is measured; the k-of-n efficiency is then extrapolated from single-layer efficiencies
   ([Relations](#relations)) and also measured directly (FXT; arXiv:2510.13798, secs. 6.1-6.2, pp. 9-12). A single
   tile is tested between two trigger tiles with absorbers against the soft component; a clean muon sample is the
   main difficulty (SPC, before flight; arXiv:astro-ph/0702581, sec. 3.4, p. 10).

**Reference impurities** read as inefficiency: non-muon events in the reference sample (neutrons made by muons in
the rock and tagged as muons in the inner detector) give an apparent inefficiency of the veto (UGD;
arXiv:1407.0275, sec. 4.3, p. 15). When the impurity cannot be measured, quote the efficiency as a lower limit
(arXiv:1101.3101, Table 3 caption, p. 16). The binomial interval and the treatment of zero failed probes belong to
hep-statistics; the tag-and-probe structure is in
[triggers, luminosity, pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement).

<!-- example: source citation -->
Borexino direct efficiencies from high-energy inner-detector events: at least (99.25 ± 0.02)% and (99.28 ± 0.02)%
for two outer-detector flags, both lower limits, with 95% C.L. Clopper-Pearson intervals (arXiv:1101.3101, sec.
3.2, p. 14; sec. 3.2.1, p. 15; Table 3, p. 16). The mutual efficiencies of these two flags, which
share their PMTs, are 0.9997 each (Table 3, p. 16; sec. 3.2.2, p. 16), above the direct ones and, by about 0.006
(errors at most 10^-4), above the tests against the independent inner-detector flag, 0.9933 and 0.9935, as a
shared-PMT correlation would make them; that flag's over-efficiency (below 0.7%, section 3.2.2, page 17) may also
contribute, so the bias size is not determined. Daya Bay inner water shield
efficiency for muons tagged by an antineutrino detector: (99.98 ± 0.01)%, confidence level not stated, the small
apparent inefficiency being rock neutrons tagged as muons (arXiv:1407.0275, sec. 4.3, eq. 2, p. 15).
<!-- /example -->

## Cosmogenic tagging (UGD in the sources found)

Muons make radioisotopes by spallation inside the active volume and neutrons in the surroundings. Short-lived
isotopes are removed by a veto on the time correlation with the crossing muon; long-lived ones need more (PDG RPP
2025, sec. 36.6.5, p. 54): a veto restricted to a **cylinder around the reconstructed muon track** (arXiv:1101.3101,
sec. 4, p. 17), or a **threefold coincidence** of muon, neutron capture and isotope decay, or a similar delayed
coincidence (PDG RPP 2025, sec. 36.6.5, p. 55). The efficiency of a distance-to-track cut is measured on spallation
products themselves, such as short-lived isotopes and muon-induced neutrons, and carried to other isotopes with a
simulated systematic (arXiv:0907.0066, sec. V B, Fig. 10, pp. 8-9). Only underground sources were found, where spallation in the
active volume is a dominant background; other environments are gaps.

<!-- example: source citation -->
Borexino: 11C (half-life 20.38 min) is accompanied by a knock-out neutron in only 95% of cases, so the tag is
incomplete, but the neutron makes the threefold coincidence possible where a full-volume veto would leave a dead
exposure close to 100% (arXiv:1101.3101, sec. 4, p. 17);
the remaining 5% of 11C, made without a neutron, and any undetected neutron escape the coincidence. KamLAND:
a cut at 3 m from the muon track keeps (91.6 ± 4.3)% of 12B and (95.9 ± 0.7)% of neutron events from non-showering
muons; for other isotopes the 12B value is used with a FLUKA systematic for the isotope dependence added, giving
(91.6 ± 8.4)%, confidence levels not stated (arXiv:0907.0066, sec. V B, Fig. 10, pp. 8-9).
<!-- /example -->

## Muon counting

The muon content of air showers is counted with shielded or buried counters, segmented **in space and in time** so
that simultaneous muons are not undercounted (GND; arXiv:1703.06193, sec. 3, p. 4); the array side is in
[ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays).
A tracking detector under rock records multi-muon cosmic events; a muon crossing it may be reconstructed as two
tracks, which are matched to avoid **double counting**, with simulated high-multiplicity events tuning the
matching (COL detector; arXiv:1507.07577, sec. 3, p. 4).

<!-- example: source citation -->
Pierre Auger Observatory, AMIGA: buried counters of three 10 m^2 scintillator modules, each in 64 segments; light
signals 25 to 35 ns wide set the time segmentation (arXiv:1703.06193, abstract; sec. 3, p. 4). ALICE, 52 m
underground under 28 m of rock: up and down TPC tracks matched per muon, events with more than 100 muons studied
(arXiv:1507.07577, abstract; sec. 3, p. 4).
<!-- /example -->

## Muons and albedo in orbit (SPC)

No space-borne muon system (absorber-backed chambers) was found in the sources surveyed. A magnetic spectrometer
without absorber identifies muon candidates as a band in velocity versus rigidity ([Relations](#relations)), with
protons,
electrons and positrons as the main contamination (arXiv:astro-ph/0205344, sec. 4, p. 7). The cited run was at ground level (abstract), and no in-flight muon selection was
found. Particles below the geomagnetic cutoff seen in orbit are
atmospheric secondaries (albedo; arXiv:astro-ph/0101559, abstract): the cutoff, albedo and their removal are in
[space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).

<!-- example: source citation -->
BESS, a balloon spectrometer, at sea level and 360 m altitude: muons selected by `1/beta` within ±3.89 sigma of the
muon curve versus
rigidity; protons removed by the band only below 1.4 GV (2.0% contamination at 1.4 GV) and subtracted above it with
an external proton spectrum normalised below 1.4 GV, at a systematic of 1% at 1.4 GeV/c; e+- estimated with a
Cherenkov shower counter behind 12 mm of lead and subtracted, 0.5% systematic at 0.6 GeV/c (arXiv:astro-ph/0205344,
abstract; sec. 4, pp. 7-8). AMS-01 in orbit: sub-cutoff fluxes with 3He/4He of order
10 and e+/e- of order 4, reproduced as atmospheric secondaries (arXiv:astro-ph/0101559, abstract).
<!-- /example -->

## Cosmic muons as calibration samples

Stopping cosmic muons are the minimum-ionizing reference of a scintillator calorimeter, with their position on
the Bethe-Bloch curve accounted for (UGD; arXiv:0805.3170, sec. 3.8.3, p. 46); cosmic-muon energy deposition, with Michel electrons and `pi0` from atmospheric neutrinos, sets
the GeV-regime absolute energy scale of the example's water-Cherenkov detector (UGD; PDG RPP 2025, sec. 36.3.1.2, p. 14); veto tiles are
characterized with cosmic muons before flight (SPC; arXiv:astro-ph/0702581, sec. 3.4, p. 10); a cosmic-ray test
stand measures counter efficiency and light-yield ageing (FXT; arXiv:2510.13798, abstract); collider muon chambers
are aligned with cosmic-ray and beam-halo muons (COL; arXiv:0911.4022, abstract; method in
[muon systems](muon-systems.md#chamber-alignment-and-momentum-scale)). Surface arrays calibrate
on atmospheric muons (GND, not sourced here: see [ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).

<!-- example: source citation -->
Super-Kamiokande: absolute energy scale at GeV energies known to about 2-3% from cosmic-muon energy deposition, Michel
electrons and
pi0 (PDG RPP 2025, sec. 36.3.1.2, p. 14).
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Veto with an independent inner detector | Direct efficiency from inner-detector-selected muons | Flag independent of the selection | Reference impurities; acceptance mismatch | UGD |
| Veto with several tags | Mutual efficiencies | Tags share no sensors | Shared sensors correlate the tags | UGD |
| Layered veto | Defining layers; k-of-n from single layers and directly | Pure muon sample, impurity estimated | Non-independent layer inefficiencies bias the extrapolation either way (pessimistic with staggered layers, as measured; optimistic with a shared gap); reference impurity (mimics the shared gap at high layer efficiency) | FXT, SPC |
| Short-lived cosmogenics | Time veto after each muon | Low muon rate | Dead time | UGD |
| Long-lived cosmogenics | Track cylinder; muon-neutron-decay coincidence | Muon tracking; neutron tag | Track-cut efficiency not measured; isotopes made without a detected neutron escape the coincidence | UGD |
| Muon counting in showers | Space and time segmentation | Segment size against the expected density | Undercounting from pile-up | GND |
| Multi-muon cosmic events in a tracker | Track matching across halves | Simulated high-multiplicity events | Double counting | COL |
| Muons in an absorber-free spectrometer | `1/beta` band versus rigidity | Time of flight and rigidity; an independent e+- identifier; an external proton spectrum to subtract above the rigidity where their band merges | Protons unseparated above that rigidity; residual p, e+-; a corrected yield, not a pure sample; subtraction-model systematic | SPC (ground-level run; in flight a gap) |

## Distinctive but generalizable features (non-collider muons)

- **Topology**: one or a few muons per readout window, mostly near-vertical, rate set by depth or altitude.
- **Inverse problem**: veto efficiency and cosmogenic tagging efficiency from samples that are themselves impure.
- **Natural objects**: veto flag, muon track, delayed-coincidence candidate, muon count per counter.
- **Informative residual**: the efficiency difference between independent reference samples, and between the
  extrapolated and direct k-of-n efficiency.
- **Scaling**: required veto inefficiency falls with the signal rate; dead time as in [Relations](#relations).
- **Conventions**: efficiency per flag and combined, quoted as a lower limit when the reference purity is unknown.
- **Tails**: corner-clipping and gap-crossing muons; showering muons; neutrons from the rock.
- **Dependence**: thresholds, light yield ageing, sensor gain drift, overburden profile.
- **Data sample**: the cosmic muons themselves, beam-timed muons, spallation products.
- **Transfers**: the reference-sample logic transfers to any veto or anticoincidence; the cosmogenic veto is shown only
  underground.

## Common misconceptions and failure modes

- **A reference sample selected with the flag under test.** The efficiency is then biased high.
- **k-of-n efficiency from single layers only.** Gaps make layer inefficiencies non-independent (anti-correlated
  when layers are staggered, as measured, and correlated when a gap is shared); measure it directly too.
- **Apparent inefficiency read as veto failure.** Check the reference impurities first.
- **A full-volume veto for long-lived isotopes.** It costs most of the exposure; restrict it to the track.

## Deliverables

- Veto efficiency per flag and combined, with the reference sample, its impurities and the limit type stated.
- The cosmogenic veto definition (window, cylinder radius, coincidence), its efficiency and its dead time, handed to
  hep-measurement for the live time and background budget.
- For muon counters, the segmentation and the pile-up correction; for spectrometers, the `1/beta` band, the
  contamination subtracted with its subtraction-model systematic, and the result labelled a corrected yield, not a per-event selection.

## Tool hooks

A veto-efficiency tool (not yet in the plugin):

- **Inputs**: the counts of the `2^n` hit patterns over the `n` test layers (integers), from one reference sample
  selected without the test layers (per-layer counts alone give `no-direct-count`), the coincidence `k` of `n`, and
  an estimate or upper bound of the non-muon fraction of the reference sample, with its uncertainty and its provenance
  (required: only an estimate from a stated control-sample count, with an uncertainty not below what that count
  allows, is measured, and a bound, simulated or assumed value gives `impurity-unmeasured`).
- **Outputs**: from the same pattern counts, single-layer efficiencies with intervals and their confidence level,
  the k-of-n efficiency extrapolated under independence, the direct k-of-n efficiency, and their difference `Z` in
  standard errors of the difference (bootstrap over the reference muons, which both estimates share), with the `Z`
  that the estimated impurity alone would give (`Z_imp`), the impurity-corrected `Z_c` (difference less the
  impurity's, in standard errors that include the impurity uncertainty) and the `Z_max` used; efficiencies are fractions.
- **Decision rule**: `independence-violated` when `|Z_c| > Z_max` in either direction (`Z_max` an input from 2 to 5,
  default 3, listed with the status when it is not 3) or, when the direct count alone has no failures, when the
  extrapolated inefficiency less `Z_max` standard errors exceeds the one-sided upper limit on the direct inefficiency
  at the confidence matching `Z_max`; `ok` when a test ran and gave neither that nor `impurity-dominated`
  (`|Z_imp| > Z_max`), meaning that extrapolation and direct count agree, not that the layers are independent
  (a shared gap and staggering can cancel).
- **Negative controls** (each with 10^6 reference muons, `k = 3`, `n = 4`, `Z_max = 3`, single-layer inefficiency
  about 0.01, impurity input 0 ± 10^-5 unless stated (a test convention, taken as measured), and stated seeds): a shared gap removing layers 1 and 2 together
  for 10^-3 of the muons must give the direct efficiency below the extrapolation and `independence-violated` (`Z` about -25); a
  staggered sample (each layer's inefficiency a gap part of about 0.009 that never hits two layers of one muon plus an
  independent 10^-3, about 114 direct failures) must give it above and `independence-violated` (`Z` about +41); at most 40 of 10,000 seeded independent samples may give other than exactly
  `{ok}` at `Z_max = 3` (binomial: a correct tool passes 99.3%, an effective 2.8 or 2.75 cut 6% or 0.5%). With the gap part alone (0.01 per layer) the direct count has no
  failures, and the one-sided test must give `independence-violated`. An independent sample with 10^-3 non-muon
  events that fail every layer, entered as 10^-3 ± 10^-4, must give exactly `{impurity-dominated}` (`Z` and `Z_imp`
  about -24, `|Z - Z_imp|` at most 3), and the staggered sample with 5 x 10^-4 such events, entered as
  5 x 10^-4 ± 5 x 10^-5, must give `independence-violated` and `impurity-dominated`, never `ok` (`Z` +1.6 without sampling noise,
  seed spread ±1.0, so -0.3 to +3.6 in 95% of seeds; `Z_imp` about -19, `Z_c` about +10).
- **Impurity**: non-muon events (modelled here as failing every layer) push the direct efficiency below the
  extrapolation while the single-layer inefficiency is below 1/9 (3 of 4, from eq. 1, above it the sign reverses, which `Z_imp` carries), so they can hide staggering or mimic a shared gap, and in the cited measurement the low-threshold plateau
  of the direct inefficiency is likely due to non-muon events that pass the selection (supported by simulation;
  arXiv:2510.13798, secs. 6.2-6.3, pp. 12-15), at 15-50 PE, where the direct efficiency still exceeds the extrapolation, and at 10 PE, the operating range's low end, they agree within errors (Fig. 6 on page 11): impurity fully masks staggering.
- **Statuses** (a set): `ok`; `independence-violated`; `impurity-dominated` (`|Z_imp| > Z_max`, only when the two-sided test runs); `impurity-unmeasured` (the test
  runs at zero impurity and at the bound, a status holds only if both give it, and the efficiencies and `Z_imp` are
  bounds); `no-failures` (a single layer has no failed
  muon: only an upper limit on its inefficiency, which enters the extrapolation, and only a one-sided test runs: `independence-violated` when the direct inefficiency exceeds that extrapolation by more than `Z_max` standard errors); `no-direct-count` (per-layer counts
  only: the extrapolation is given, labelled as an assumption, without `Z`). With `no-direct-count`, none of
  `ok`, `independence-violated` or `impurity-dominated` is emitted, and with `no-failures` only `independence-violated` can be.

## Environment coverage

Cells give source IDs (PDG = PDG RPP 2025, non-accelerator detectors), `gap` (no source found), `n/a:` with the
reason the technique does not apply, `same` (as the cell to the left) or a link. A
cell counts the environment the instrument is built for; a cited run made elsewhere is labelled.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Muon vetoes, segmentation against self-veto | n/a: timing and vertex cuts ([muon systems](muon-systems.md#backgrounds-and-fakes)) | arxiv_2510.13798 | arxiv_astro-ph_0702581 | PDG; arxiv_1101.3101 | gap | gap |
| Veto-efficiency measurement | n/a: as above | arxiv_2510.13798 (cosmic-ray test stand) | arxiv_astro-ph_0702581 (pre-flight, on ground) | arxiv_1101.3101; arxiv_1407.0275 | gap | gap |
| Cosmogenic tagging | gap | gap | gap | PDG; arxiv_1101.3101; arxiv_0907.0066 | gap | gap |
| Muon counting | arxiv_1507.07577 | gap | gap | gap | arxiv_1703.06193 | gap |
| Muons in absorber-free spectrometers | n/a: muon systems used | gap | arxiv_astro-ph_0205344 (ground-level run; in flight a gap) | gap | n/a: arrays have no spectrometer | gap |
| Albedo below cutoff | n/a: orbit only | n/a: same | arxiv_astro-ph_0101559; [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff) | n/a: orbit only | n/a: same | n/a: same |
| Cosmic muons as calibration samples | arxiv_0911.4022 (chamber alignment, text) | arxiv_2510.13798 (cosmic-ray test stand) | arxiv_astro-ph_0702581 (pre-flight, on ground) | PDG; arxiv_0805.3170 | gap (method in [ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)) | gap |

## Citations

Inline citations give the arXiv number and a locator; page numbers are printed ones. Annotated
entries for every source of this page are in the
[muon-systems bibliography](detector-principles-bibliography-muon-systems.md), a split file of the
[bibliography](detector-principles-bibliography.md).
