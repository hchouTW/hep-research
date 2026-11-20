# Non-Collider Muon Detection: Vetoes, Cosmogenic Tagging, Muon Counting, and Muons in Orbit

Muons as the background to veto, the cause of cosmogenic backgrounds, the observable of air-shower arrays, and the
calibration source outside collider muon systems. Environment codes: COL collider; FXT fixed-target and test beam;
SPC space and high-altitude balloon; UGD underground, neutrino and rare-event; GND ground-based cosmic-ray and
gamma-ray arrays; NUC nuclear and low-energy physics. Covered: UGD, FXT, SPC, GND, and COL for multi-muon cosmic
events and chamber alignment with cosmic muons; NUC is a gap. Collider muon systems, chamber alignment, energy loss
in absorbers and charge-sign quality are in [muon systems](muon-systems.md). Environment pages own their
content and are linked:
[neutrino astronomy](neutrino-astronomy.md#backgrounds) (atmospheric-muon veto, self-veto, up-going selection),
[noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors),
[ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays),
[space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff) (albedo). The background budget
and the live time after vetoes belong to hep-measurement:
[rare-event and neutrino measurements](../../hep-measurement/references/rare-event-and-neutrino-measurements.md#background-budget).

## Relations

- **k-of-n layer coincidence** (exact for independent layers of equal efficiency `eps`; arXiv:2510.13798, sec. 6.2,
  eq. 1, p. 10): 3 of 4 layers give `eps_3/4 = eps^4 + 4 eps^3 (1 - eps) = 4 eps^3 - 3 eps^4`. It fails when the
  layer inefficiencies are correlated, and the bias can have either sign. In the cited measurement the low-threshold
  inefficiency comes from muons running along gaps between counters, and staggered layers make a second gap crossing
  unlikely, so the inefficiencies are anti-correlated and the direct `eps_3/4` exceeds the extrapolation (sec. 6.2,
  pp. 11-12, Figs. 6-7). A gap shared by several layers would push the other way, so measure `eps_3/4` directly as well.
- **Muon band in an absorber-free spectrometer** (exact kinematics for unit charge, with the band width set by the
  velocity resolution; arXiv:astro-ph/0205344, sec. 4, p. 7): `1/beta = sqrt((m_mu/R)^2 + 1)`, with `R` the
  rigidity in GV and `m_mu` in GeV; a band of `± n sigma(1/beta)` selects muon candidates. The band separates protons
  only at low rigidity, so an independent e+- identifier and, above the rigidity where the proton band merges, a
  proton subtraction complete the selection (sec. 4, p. 7).
- **Time veto length** (approximate rule; arXiv:1101.3101, sec. 4, p. 17): veto several half-lives of the isotope
  after each muon. The dead exposure grows with the muon rate times the veto length, so long-lived isotopes need a
  veto restricted in space.

## Muon vetoes

Underground detectors are surrounded by water, oil or other shielding and equipped with muon vetoes; light reflection
is maximized in outer veto detectors to raise the muon detection efficiency, while it is minimized in the inner
detector for reconstruction (UGD; PDG RPP 2025, particle detectors for non-accelerator physics, sec. 36.3.1, p. 12).
The veto must identify muons with very high efficiency and, where cosmogenic isotopes matter, also reconstruct
their tracks (UGD; arXiv:1101.3101, abstract). The same design problem appears in two other environments: a
cosmic-ray veto of scintillator layers around the detector solenoid of a fixed-target experiment declares a muon,
in most areas it covers, by a space-time coincidence of at least 3 of 4 layers (FXT; arXiv:2510.13798, sec. 6,
p. 9), and the anticoincidence shield of a
space gamma-ray telescope vetoes charged particles with segmented tiles, because an unsegmented shield would also
fire on backsplash from the telescope's own showers (**self-veto**; SPC; arXiv:astro-ph/0702581, abstract). The
parameters are the coverage (hermeticity, gaps), the coincidence logic, the threshold, the segmentation against
self-veto, and the veto window.

<!-- example: source citation -->
Borexino: an outer water-Cherenkov detector around the inner detector; combined veto efficiency at least 99.992%
(arXiv:1101.3101, abstract; sec. 3.2.3, p. 17). Mu2e cosmic-ray veto: four layers of scintillation counters with
wavelength-shifting fibres and SiPMs; required efficiency up to 99.99% in critical regions (arXiv:2510.13798,
abstract; sec. 6, p. 9). Fermi LAT (GLAST) anticoincidence detector: about 8.3 m^2, 89 tiles; efficiency, averaged
over the detector area, for singly charged relativistic particles entering the tracker from the top or sides, above
the required 0.9997 (arXiv:astro-ph/0702581, abstract; sec. 2.1, p. 3).
<!-- /example -->

### Veto-efficiency measurement

The efficiency of a veto is measured on a reference sample of muons selected **without the flag being tested**
(arXiv:1101.3101, sec. 3.2.1, p. 15). Three methods, by what supplies the reference:

1. **Direct**: an independent detector or signal selects the muons, such as high-energy events in the inner detector
   for the outer-veto flags, or muons timed to a beam spill (UGD; sec. 3.2.1, p. 15). The reference must cover the
   veto's acceptance: a beam sample with near-horizontal tracks is a poor reference for a veto optimized for
   near-vertical cosmic muons (sec. 3.2.1, p. 15).
2. **Mutual**: each tag is measured against samples selected by the others; tags that share sensors are not
   independent, so their mutual efficiencies are not a valid test of each other (UGD; sec. 3.2.2, p. 16).
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
for two outer-detector flags, with 95% C.L. Clopper-Pearson intervals (arXiv:1101.3101, sec. 3.2, p. 14; sec.
3.2.1, p. 15; Table 3, p. 16). The mutual efficiencies of these two flags, which share their PMTs, are 0.9997 each,
above the direct ones (Table 3, p. 16; sec. 3.2.2, p. 16), as a high bias would give. Daya Bay inner water shield
efficiency for muons tagged by an antineutrino detector: (99.98 ± 0.01)%, confidence level not stated, the small
apparent inefficiency being rock neutrons tagged as muons (arXiv:1407.0275, sec. 4.3, eq. 2, p. 15).
<!-- /example -->

## Cosmogenic tagging (UGD only)

Muons make radioisotopes by spallation inside the active volume and neutrons in the surroundings. Short-lived
isotopes are removed by a veto on the time correlation with the crossing muon; long-lived ones need more (PDG RPP
2025, sec. 36.6.5, p. 54): a veto restricted to a **cylinder around the reconstructed muon track** (arXiv:1101.3101,
sec. 4, p. 17), or a **threefold coincidence** of muon, neutron capture and isotope decay, or a similar delayed
coincidence (PDG RPP 2025, sec. 36.6.5, p. 55). The efficiency of a distance-to-track cut is measured on spallation
products themselves, such as short-lived isotopes and muon-induced neutrons (arXiv:0907.0066, sec. V B, Fig. 10,
p. 8). The technique exists in one environment: it needs a muon rate low enough that a veto of several isotope
half-lives after each muon leaves usable live time.

<!-- example: source citation -->
Borexino: 11C (half-life 20.38 min) is accompanied by a knock-out neutron in only 95% of cases, so the tag is incomplete, but this makes the threefold
coincidence possible where a full-volume veto would leave a dead exposure close to 100% (arXiv:1101.3101, sec. 4,
p. 17); the remaining 5% of 11C, made without a neutron, and any undetected neutron escape the coincidence. KamLAND:
a cut at 3 m from the muon track keeps (91.6 ± 4.3)% of 12B and (95.9 ± 0.7)% of neutron events from non-showering
muons, confidence level not stated (arXiv:0907.0066, sec. V B, Fig. 10, p. 8).
<!-- /example -->

## Muon counting

The muon content of air showers is counted with shielded or buried counters, segmented **in space and in time** so
that simultaneous muons are not undercounted (GND; arXiv:1703.06193, sec. 3, p. 4); the array side is in
[ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays).
A tracking detector under rock records multi-muon cosmic events; a muon crossing it may be reconstructed as two
tracks, which are matched to avoid **double counting**, with simulated high-multiplicity events used to tune the
matching (COL detector used for cosmic rays; arXiv:1507.07577, sec. 3, p. 4).

<!-- example: source citation -->
Pierre Auger Observatory, AMIGA: buried counters of three 10 m^2 scintillator modules, each in 64 segments; light
signals 25 to 35 ns wide set the time segmentation (arXiv:1703.06193, abstract; sec. 3, p. 4). ALICE, 52 m
underground under 28 m of rock: up and down TPC tracks matched per muon, events with more than 100 muons studied
(arXiv:1507.07577, abstract; sec. 3, p. 4).
<!-- /example -->

## Muons and albedo in orbit (SPC)

No space-borne muon system (absorber-backed chambers) was found in the sources surveyed. A magnetic spectrometer
without absorber identifies muons as a band in velocity versus rigidity ([Relations](#relations)), with protons,
electrons and positrons as the main contamination (arXiv:astro-ph/0205344, sec. 4, p. 7). The cited run was at
ground level (GND; abstract), and no in-flight muon selection was found, so this technique is a gap for SPC. Particles below the geomagnetic cutoff seen in orbit are
atmospheric secondaries (albedo; arXiv:astro-ph/0101559, abstract): the cutoff, albedo and their removal are in
[space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).

<!-- example: source citation -->
BESS at sea level and 360 m altitude: muons selected by `1/beta` within ±3.89 sigma of the muon curve versus
rigidity (arXiv:astro-ph/0205344, abstract; sec. 4, p. 7). AMS-01 in orbit: sub-cutoff fluxes with 3He/4He of order
10 and e+/e- of order 4, reproduced as atmospheric secondaries (arXiv:astro-ph/0101559, abstract).
<!-- /example -->

## Cosmic muons as calibration samples

Stopping cosmic muons serve as the minimum-ionizing reference of a scintillator calorimeter, with their position on
the Bethe-Bloch curve accounted for (UGD; arXiv:0805.3170, sec. 3.8.3, p. 46); cosmic-muon energy deposition fixes
the absolute energy scale of a water-Cherenkov detector (UGD; PDG RPP 2025, sec. 36.3.1.2, p. 14); veto tiles are
characterized with cosmic muons before flight (SPC; arXiv:astro-ph/0702581, sec. 3.4, p. 10); a cosmic-ray test
stand measures counter efficiency and light-yield ageing (FXT; arXiv:2510.13798, abstract); collider muon chambers
are aligned with cosmic-ray and beam-halo muons (COL; arXiv:0911.4022, abstract; the method is in
[muon systems](muon-systems.md#chamber-alignment-and-momentum-scale)). Surface arrays calibrate
on atmospheric muons ([ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).

<!-- example: source citation -->
Super-Kamiokande: absolute energy scale known to about 2-3% from cosmic-muon energy deposition, Michel electrons and
pi0 (PDG RPP 2025, sec. 36.3.1.2, p. 14).
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Veto with an independent inner detector | Direct efficiency from inner-detector-selected muons | Flag independent of the selection | Reference impurities; acceptance mismatch | UGD |
| Veto with several tags | Mutual efficiencies | Tags share no sensors | Shared sensors correlate the tags (high in the cited case) | UGD |
| Layered veto | Defining layers; k-of-n from single layers and directly | Pure muon sample | Correlated layer inefficiencies bias the extrapolation either way (pessimistic with staggered layers, optimistic with a shared gap) | FXT, SPC |
| Short-lived cosmogenics | Time veto after each muon | Low muon rate | Dead time | UGD |
| Long-lived cosmogenics | Track cylinder; muon-neutron-decay coincidence | Muon tracking; neutron tag | Track-cut efficiency not measured; isotopes made without a detected neutron escape the coincidence | UGD |
| Muon counting in showers | Space and time segmentation | Segment size against the expected density | Undercounting from pile-up | GND |
| Multi-muon cosmic events in a tracker | Track matching across halves | Simulated high-multiplicity events | Double counting | COL |
| Muons in an absorber-free spectrometer | `1/beta` band versus rigidity | Time of flight and rigidity; protons separated only at low rigidity; an independent e+- identifier; proton subtraction above that rigidity | p, e+- contamination | GND (SPC a gap) |

## Distinctive but generalizable features (non-collider muons)

- **Topology**: one or a few through-going muons per readout window, mostly near-vertical, rate set by depth or
  altitude.
- **Inverse problem**: veto efficiency and cosmogenic tagging efficiency from samples that are themselves impure.
- **Natural objects**: veto flag, muon track, delayed-coincidence candidate, muon count per counter.
- **Informative residual**: the efficiency difference between independent reference samples, and between the
  extrapolated and direct k-of-n efficiency.
- **Scaling**: required veto inefficiency falls as the signal rate falls; dead time grows with muon rate times veto
  length.
- **Conventions**: efficiency per flag and combined, quoted as a lower limit when the reference purity is unknown.
- **Tails**: corner-clipping and gap-crossing muons; showering muons; neutrons from the rock.
- **Dependence**: thresholds, light yield ageing, sensor gain drift, overburden profile.
- **Data sample**: the cosmic muons themselves, beam-timed muons, spallation products.
- **Transfers**: the reference-sample logic transfers to any veto or anticoincidence; the cosmogenic veto does not
  transfer to high-rate surface or collider detectors.

## Common misconceptions and failure modes

- **A reference sample selected with the flag under test.** The efficiency is then biased high.
- **Mutual efficiencies of tags that share sensors.** They are correlated, not independent.
- **k-of-n efficiency from single layers only.** Gaps make layer inefficiencies non-independent (anti-correlated
  when layers are staggered, correlated when a gap is shared); measure it directly too.
- **Apparent inefficiency read as veto failure.** Check the reference impurities first.
- **A full-volume veto for long-lived isotopes.** It costs most of the exposure; restrict it to the track.

## Deliverables

- Veto efficiency per flag and combined, with the reference sample, its impurities and the limit type stated.
- The cosmogenic veto definition (window, cylinder radius, coincidence), its efficiency and its dead time, handed to
  hep-measurement for the live time and background budget.
- For muon counters, the segmentation and the pile-up correction; for spectrometers, the `1/beta` band and the
  contamination subtracted.

## Tool hooks

A veto-efficiency tool (not yet in the plugin):

- **Inputs**: per test layer, counts of reference muons and of those detected (integers), the coincidence `k` of `n`,
  and optionally the direct count of reference muons meeting `k` of `n`.
- **Outputs**: single-layer efficiencies with intervals and their confidence level, the k-of-n efficiency
  extrapolated under independence, the direct k-of-n efficiency, and their difference `Z` in standard errors of the
  difference (bootstrap over reference muons, because both estimates use the same muons). Efficiencies are fractions
  in [0, 1].
- **Decision rule**: `independence-violated` when `|Z| > Z_max` in either direction (`Z_max` an input, default 3);
  `ok` when the test ran and `|Z| <= Z_max`.
- **Negative controls** (each with 10^6 reference muons and single-layer efficiency about 0.99, so every layer and
  the direct count have failures): a sample in which a shared gap removes two layers together must give a direct
  k-of-n efficiency below the extrapolation and `independence-violated`; a staggered sample, in which a muon crosses
  at most one gap, must give one above it and `independence-violated`; an independent sample must give exactly
  `{ok}`.
- **Statuses** (a set): `ok`; `independence-violated`; `no-failures` (a layer or the direct count has no failed
  muon: only an upper limit on that inefficiency); `no-direct-count` (extrapolation only, labelled as an assumption).
  With `no-failures` or `no-direct-count` the test does not run, and neither `ok` nor `independence-violated` is
  emitted.

## Environment coverage

Cells give source IDs of the run's cache (PDG = PDG RPP 2025, particle detectors for non-accelerator physics).

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Muon vetoes, segmentation against self-veto | n/a: timing and vertex cuts ([muon systems](muon-systems.md#backgrounds-and-fakes)) | arxiv_2510.13798 | arxiv_astro-ph_0702581 | PDG; arxiv_1101.3101 | gap | gap |
| Veto-efficiency measurement | n/a | arxiv_2510.13798 | arxiv_astro-ph_0702581 | arxiv_1101.3101; arxiv_1407.0275 | gap | gap |
| Cosmogenic tagging | n/a: single-environment technique (text) | n/a: same | n/a: activation is a different problem | PDG; arxiv_1101.3101; arxiv_0907.0066 | n/a: single-environment technique | n/a: single-environment technique |
| Muon counting | arxiv_1507.07577 | gap | gap | gap | arxiv_1703.06193 | gap |
| Muons in absorber-free spectrometers | n/a: muon systems used | gap | gap: no in-flight muon selection found | n/a | arxiv_astro-ph_0205344 | n/a |
| Albedo below cutoff | n/a | n/a | arxiv_astro-ph_0101559; [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff) | n/a | n/a | n/a |
| Cosmic muons as calibration samples | arxiv_0911.4022 (chamber alignment) | arxiv_2510.13798 | arxiv_astro-ph_0702581 | PDG; arxiv_0805.3170 | [ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction) | gap |

## Citations

Inline citations give the arXiv number and a locator. Page numbers are the printed page numbers of the cached
arXiv version (for arXiv:1101.3101, 1703.06193 and 2510.13798 they differ from the PDF page index). Annotated
entries for every source of this page, the PDG review included, are in the
[muon-systems bibliography](detector-principles-bibliography-muon-systems.md), a split file of the
[bibliography](detector-principles-bibliography.md).
