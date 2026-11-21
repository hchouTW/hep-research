# Transition Radiation Detectors

How a transition radiation detector (TRD) turns the Lorentz factor of a charged particle into a measurement: TR
emission and radiators, X-ray absorption in the gas, the signal time profile, clusters, tracklets and hits on track,
estimators, their calibration, and rejection reported versus `gamma`; also hadron separation, the Lorentz factor of
nuclei, and silicon TR detection.
Kept elsewhere: TR in [signal formation](signal-formation-and-readout.md#light-scintillation-wavelength-shifting-attenuation)
and the comparison of techniques in
[particle identification](particle-identification.md#transition-radiation-detectors-trd); per-layer PDFs,
layer correlations and `multisample_pid.py` in [multisample PID](multisample-pid-and-reference-pdfs.md);
gas-gain equalization in [in-situ calibration](in-situ-calibration-methods.md#gas-gain-equalization); straws in
[gaseous tracking](gaseous-and-specialized-tracking-technologies.md#mwpcs-straw-tubes-and-rpcs);
tuning simulators to TRD spectra is simcal (hep-statistics) ([TRD simcal](simulation-calibration/trd.md));
training networks is hep-ml's ([space ML](../../hep-ml/references/space-and-astroparticle-ml.md)).

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground, neutrino
and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Radiator, gas, layer count, field, rate and the
track source are parameters of every method below. Sources are named by ID (`arxiv_<id>` is arXiv:<id>, `/` written
`_`; `pdg_2025_<review>` the PDG RPP 2025 review of that title); entries are in
[the TR bibliography](detector-principles-bibliography-transition-radiation.md).
Page numbers are PDF pages.

## Relations

- **Single interface** (exact for a vacuum-medium boundary and `gamma >> 1`; PDG passage review sec. 34.7.3,
  eqs. 34.45-34.46, p. 35): `I = alpha z^2 gamma hbar omega_p / 3`, `hbar omega_p = 28.81 eV sqrt(rho <Z/A>)`
  (`rho` in g/cm3); about 20 eV for styrene-like plastics, 0.7 eV for air.
- **Hardening, not yield** (exact to `(hbar omega_0 / gamma hbar omega_p)^2`; same sec., eq. 34.47, p. 36): the
  number of photons above a fixed fraction of `gamma hbar omega_p` is constant (above a tenth of it,
  `N = 0.59% z^2` per interface); above a fixed energy it grows as `(ln gamma)^2`. Energy rises with `gamma` as
  the spectrum hardens; at `gamma = 10^3` the photons are soft X-rays of 2-40 keV.
- **Formation length** (exact, a definition; same sec., p. 36):
  `d(omega) = (2c/omega) (1/gamma^2 + theta^2 + omega_p^2/omega^2)^-1`, for `theta = 1/gamma` largest,
  `gamma c / (sqrt(2) omega_p)`, at `omega = gamma omega_p / sqrt(2)`; tens of micrometres in practice. Written per medium as the formation zone `Z_i`,
  the yield is suppressed for a foil or gap much thinner than its `Z_i` (arXiv:1111.4188 sec. 2.2, eq. 6, p. 4).
- **Emission angle** (approximate): about `1/gamma` for a single interface (PDG passage review sec. 34.7.3, p. 36);
  in a stack the radiator sets it, `theta ~ 1.2 / (omega1 sqrt(l1 l2))` mrad at the last interference maximum, near
  its limit from `gamma_sat` on, within a few mrad (PDG detectors review sec. 35.6.5, p. 45), so photon and track
  deposits share a cell.
- **Stack of `N_f` foils** (exact with absorption, regular spacing; arXiv:1111.4188 sec. 2.2, eq. 5, p. 3): interference
  of the foil amplitudes times an absorption factor; low-energy photons are absorbed in the radiator. Without absorption the intensity
  grows as `N_f`, not `N_f^2` (PDG passage review sec. 34.7.3, p. 36); with it, the factor `1 - exp(-N_f sigma)`
  saturates it at an effective number of foils (arXiv:1111.4188 eq. 10, p. 5).
- **Threshold, saturation, spectrum peak** (approximate; PDG detectors review sec. 35.6.5, p. 45):
  `gamma_thr ~ l1 omega1 / c`, `gamma_sat = 0.6 omega1 sqrt(l1 l2) / c`, `omega_max = l1 omega1^2 / (2 pi c)`, with
  `omega1` the foil plasma frequency, `l1` the foil thickness and `l2` the spacing (analytic forms);
  PDG's practical forms
  `gamma_thr ~ 3e3 omega1 l1`, `gamma_sat ~ 3e3 omega1 sqrt(l1 l2)`, `omega_max = 0.65 l1 omega1^2` (`omega1` in eV,
  lengths in mm, `omega_max` in keV) differ: with `hbar c` the analytic ones give 5.1e3, 3.0e3, 0.81; use one set.
  Another form of `gamma_s` is arXiv:1111.4188 eq. 9; analytically `gamma_sat / gamma_thr = 0.6 sqrt(l2 / l1)`, 2-5
  for `l2 / l1` of 10-60; the factor ten of arXiv:1901.11265 sec. 1, p. 2 counts from an empirical onset. Most detectors choose
  `gamma_sat ~ 3000` (PDG detectors review, p. 45).
- **Absorption** (approximate; PDG detectors review sec. 35.6.5, p. 45): photoabsorption per atom goes as
  `Z^n / omega^3`, `n` between 4 and 5, so a low-`Z` radiator and a high-`Z` (xenon) gas. Xenon, the heaviest gas,
  absorbs best: absorption length about 2 mm at 3 keV and again just above the L edges near 5 keV, 10 mm at 10 keV,
  30 mm at 15 keV, the text's 10 mm being for typical TR energies (arXiv:1111.4188 sec. 3.1, Fig. 4, p. 7).
- **Layer likelihood** (exact as a definition; assumes independent layers; arXiv:1111.4188 sec. 3.2, eqs. 12-13, p. 8):
  `L_e = P_e / (P_e + P_pi)`, `P_k = prod_i P(E_i | k)`, or `sum_i log [P(E_i|e) / P(E_i|pi)]`, with `P(E_i|k)` the
  measured per-layer spectra of identified particles.
- **Rejection versus length** (approximate, empirical; PDG detectors review sec. 35.6.5, p. 47, Fig. 35.18 on p. 48): at 90%
  electron efficiency, rescaled to 10 GeV, the pion rejection of past TRDs grows as `5 x 10^(L/38)` for overall length
  `L = 20-100 cm`.
- **Onset curve** (approximate, a fit form; arXiv:1709.02743 sec. 11, eq. 2, p. 48): the TR part of the most
  probable signal as a logistic function of `ln gamma`, added to a `dE/dx` parameterisation (eq. 1).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Choosing a radiator | Regular foils, fibre or foam; irregular ones as a tuned regular radiator or with an efficiency factor | Measured spectra to tune on | Foam gives less TR than foils at equal density; tuned parameters not unique, miss the momentum dependence | FXT (arXiv:1111.4188 secs. 2.3, 3.3.1; arXiv:physics/0402131 sec. 3); SPC (arXiv:1706.10182 sec. 2) |
| Setting the `gamma` window | Choose `l1`, `l2` and material for `gamma_thr`, `gamma_sat`, `omega_max` | Target species and momentum band | Saturation reached by the background species | FXT (PDG detectors review sec. 35.6.5; arXiv:1901.11265 sec. 1); SPC (PDG detectors review p. 48; arXiv:2201.07901) |
| Detecting the photons | Xe-rich gas, thickness matched to the spectrum; build-up over thin layers | Gas purity; Xe content monitored | Argon fill loses TR; L-escape line; soft TR absorbed in the radiator | COL (arXiv:1702.06473 sec. 3.1); FXT (arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 3) |
| Architecture | Thick radiator plus 2-4 cm Xe chamber per module, or thin straws through the radiator as part of a tracker | Space, material, rate | Few thick layers: fewer samples; thin layers: soft TR lost | COL (arXiv:1111.4188 sec. 4); FXT (arXiv:1111.4188 sec. 4.4; PDG detectors review p. 46); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Drift chamber with time sampling | Slice the signal in drift time; TR arrives at the radiator-side entrance (long drift) | Calibrated drift velocity and `t0`; ion-tail cancellation | Slices treated as independent | COL (arXiv:1709.02743 secs. 2.1, 11.2); FXT (arXiv:physics/0402131 secs. 3-4) |
| Hits on a track | Pad clusters per time bin into tracklets on a propagated seed; straw hits on an extrapolated or stand-alone track | External tracker or enough TRD layers | Hits of a secondary or neighbour; wrong path length | COL (arXiv:1709.02743 secs. 8-8.2; arXiv:1109.5925 sec. 2); SPC (arXiv:1706.10182 sec. 2); FXT (arXiv:astro-ph/0608641 sec. 4.2.5) |
| Thick gas, full charge | Total charge or truncated mean | Many layers | Landau tail of the background | FXT (PDG detectors review sec. 35.6.5, p. 47; arXiv:1111.4188 sec. 3.2) |
| Thin gas | Cluster counting: hits above a 5-7 keV threshold; high-threshold fraction | Threshold stable in energy | Threshold drift with gain | COL (arXiv:1109.5925 sec. 4); FXT (arXiv:astro-ph/0608641 sec. 5.1) |
| Best separation | Layer likelihood (charge; charge and largest-cluster position; per-slice charges), neural network | References from clean samples | Correlations ignored; bins that must be non-empty cost efficiency | COL (arXiv:1709.02743 sec. 11.2); FXT (arXiv:astro-ph/0608641 sec. 5; arXiv:physics/0402131 sec. 4); SPC (arXiv:1706.10182 sec. 3) |
| TR plus `dE/dx` in one estimator | One likelihood per species from TR hits and a `dE/dx` measure | One reference set for both | Multiplying them as independent | COL (arXiv:1109.5925 sec. 1); SPC (arXiv:1108.4838 sec. 3.3) |
| Simulation of the response | PAI ionization in thin gas, tuned TR generator, delta-electron escape, empirical non-linearity | Flight or beam data per species | Tails wrong without delta escape; one non-linearity for point-like X-ray conversions and spread ionization | FXT (arXiv:1111.4188 sec. 4.3.1; arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 2) |
| Response calibration | Gain per channel, then per chamber in time; then references in momentum or `gamma` bins; environment corrections | Clean samples; conditions record | References before the gain calibration; drifting Xe pressure | COL (arXiv:1709.02743 sec. 11.2); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Hadron separation | Long TRD; radiator sets with different thresholds; TR energy and angle | Fixed-target hadron or hyperon beam | All hadrons radiate at TeV momenta | FXT only (see below) |
| Lorentz factor of nuclei | `z^2`-scaled TR on top of the relativistic rise | Charge measured independently | Response gap at the onset | SPC only (see below) |
| TR energy and angle | Silicon strips or pixels behind the radiator, a field deflecting the track | Low occupancy | Photon-track association | FXT only, R&D (see below) |

**Single-environment techniques.** Hadron separation with TRDs exists only in fixed-target hadron and hyperon beams:
pions from protons and kaons at momenta up to 200 GeV/c in past detectors, and kaons from pions roughly at 200-700 GeV/c
(PDG detectors review sec. 35.6.5, p. 48; arXiv:1111.4188 secs. 1-2.4, pp. 2, 5). It needs longer detectors than electron identification and, at TeV momenta where all hadrons radiate, several
thresholds or the TR energy and angle (arXiv:1901.11265 sec. 1, pp. 3-4). TeV hadron identification at a future collider
is a stated need, not a practice (arXiv:1901.11265 sec. 1, p. 3; arXiv:2201.07901 abstract). The Lorentz factor of nuclei is measured with TR only in balloon and space
instruments: no accelerator gives heavy nuclei at the `gamma ~ 1e5` aimed at (arXiv:1111.4188 sec.
3.4.1, p. 15). Tuned radiators, best of dense materials such as Al, extend the rise to `gamma ~ 1e5` with photons
up to 100 keV, and Compton-scatter detection is proposed (PDG detectors review sec. 35.6.5, p. 48); compound radiators of varied foils
widen the range (arXiv:2201.07901 abstract). Their use in composition studies is in
[space-based direct detection](space-based-direct-detection.md#direct-detection-composition-and-the-local-antiparticle-excesses),
the spectrum in [cosmic-ray spectrum](cosmic-ray-spectrum-and-composition.md#the-all-particle-spectrum-and-its-features)
and [composition](cosmic-ray-spectrum-and-composition.md#composition-and-its-observables). Silicon TR
detection, separating photons from the track in space and measuring the angle with the energy, is test-beam R&D (PDG
detectors review p. 48; arXiv:1901.11265 sec. 1, p. 4; arXiv:1111.4188 sec. 3.4.2, pp. 15-16).

Rules that hold across the rows:

- **TR depends on `gamma` and `z^2`, not on mass.** Electrons and muons at equal `beta gamma` give consistent signals, so muons
  calibrate the onset (arXiv:1709.02743 sec. 11, p. 47; arXiv:1702.06473 sec. 1, p. 4).
- **Rejection is not monotonic in momentum.** It improves through the onset and falls once TR saturates and the
  background's `dE/dx` rises (arXiv:1111.4188 sec. 3.2, Fig. 8, p. 10; arXiv:1709.02743 sec. 11.2,
  p. 51); it also falls at high momentum against protons, plausibly as their `gamma` nears the onset (an inference:
  arXiv:1706.10182 sec. 1 gives only numbers).
- **The working point is an analysis choice.** The background efficiency depends strongly on the signal efficiency;
  90% is the convention (arXiv:1111.4188 sec. 3.2, pp. 9-10). A momentum-dependent cut keeps it
  constant (arXiv:1709.02743 sec. 11.2, p. 51).
- **Time bins are correlated.** Ion tails carry charge into later bins; amplitudes per bin cannot enter a likelihood
  as independent factors (arXiv:physics/0402131 sec. 4, p. 4; arXiv:1709.02743 sec. 8.2, p. 35): use a joint
  reference over slices or slice groups (sec. 11.2, p. 51), the largest-cluster position jointly with the charge, or
  a network; tail cancellation reduces the correlation (sec. 8.2, p. 35).
- **"Cluster" has two meanings**: a charge cluster in pad chambers, a hit above threshold in cluster counting
  (arXiv:1709.02743 sec. 8.1; arXiv:astro-ph/0608641 sec. 5.1); state which.
- **TR builds up with depth in thin-layer detectors.** Photons above about 4 keV cross several layers before
  converting (PDG detectors review sec. 35.6.5, p. 46), so electron deposits grow with depth, hadron deposits stay flat (arXiv:1706.10182
  sec. 3, p. 4): references are per layer
  ([layer correlations](multisample-pid-and-reference-pdfs.md#layer-correlations)).

<!-- example: named apparatus and their numbers (collider, test-beam, space and balloon instances of the rows above) -->
- ALICE TRD: 6 layers, foam/fibre radiator, Xe-CO2 chamber with 3 cm drift (arXiv:1709.02743 sec. 1, p. 2); clusters
  from up to 3 adjacent pads per 100 ns time bin, straight-line tracklets (secs. 8.1-8.2, p. 35);
  7 slices of about 5 mm each; LQ2D sums the first four and the last three; LQ7D's non-empty bins cost about 40% of
  electrons (sec. 11.2, pp. 50-51). Onset fit `TR/TR_mip = 0.706 / (1 + exp(-1.85 (ln gamma - 7.80)))`, half-maximum
  at `beta gamma = 2.4e3`, onset visible above `beta gamma ~ 800` (sec. 11, eq. 2, pp. 47-48). Pion rejection at
  1 GeV/c, p-Pb, 6 layers, 90% electron efficiency: about 70 (LQ1D), up to 410 with the time evolution (design goal
  100 at 90%) (p. 51; sec. 13, p. 65; Fig. 42, p. 52); references
  centrality-dependent in Pb-Pb (about 15% shift, p. 51).
- ALICE TRD prototypes, CERN PS, 1-6 GeV/c: likelihood on charge gives pion rejection about 100 at 90% electron efficiency, for six layers extrapolated from four measured; charge plus
  largest-cluster position about 1.6 times better (arXiv:physics/0402131 sec. 4, pp. 3-4); tuned regular-radiator
  parameters `d1 = 10 um`, `d2 = 80 um`, `N_f = 270` describe 2 GeV/c but not the momentum dependence (sec. 3, p. 3).
- ATLAS TRT: 4 mm straws, 70% Xe, 27% CO2, 3% O2 for TR photons of 6-15 keV; argon in leaking modules in Run 2
  (arXiv:1702.06473 sec. 3.1, p. 7); emission probability steps from about zero to its maximum between `gamma` 500
  and 2000 (sec. 1, p. 4). Low threshold about 300 eV, high threshold 6-7 keV; HT probability
  rises from 0.05 to a plateau of 0.2-0.3 by region; onset mapped with pions, conversion electrons and Z electrons
  (arXiv:1109.5925 secs. 2, 4.1, pp. 1-3).
- AMS-02 TRD: 20 straw layers, 20 mm fleece radiator, Xe/CO2 (91.5/8.5%); Geant4 fibre
  thickness tuned to 12 um against 10 um nominal; per-module gain versus time from protons (arXiv:1706.10182 sec. 2,
  pp. 1-2); flight data selected within +-30 mbar of the simulated 850 mbar xenon pressure (sec. 3, p. 4). Proton
  rejection above 1e4 at 10 GeV/c and 10 at 1 TeV/c, electron efficiency not stated (sec. 1, p. 1, from its ref. [3]).
- AMS-02 TRD 20-layer prototype, CERN SPS X7: single-track roads of 1.5 and 5 tube diameters (arXiv:astro-ph/0608641
  sec. 4.2.5, p. 5); TR photon detection efficiency about 30% above 5 keV, Xe L-escape line at 4.2 keV (sec. 4.3,
  pp. 5-6); cluster counting at 6.5 keV with `N_cut = 6`: proton rejection 360 +- 60 for 100 GeV protons at 89% electron
  efficiency (sec. 5.1, p. 6).
- TRACER (balloon): `dE/dx` gives 10-400 GeV/amu, the TRD above about 1000 GeV/amu, 400-1500 GeV/amu excluded;
  more xenon moved the TR appearance threshold to `gamma = 785 +- 140` (arXiv:1108.4838 sec. 3.3, p. 7).
- CREAM-I TRD (balloon): `4 < gamma < 5e2` from the xenon relativistic rise, beam-test calibrated
  (arXiv:0808.1718 sec. 2, p. 5).
- Silicon TR set-up, CERN SPS: 300 um double-sided strip detector, 50 um pitch; 20 GeV/c electrons and 120-290 GeV/c
  muons (arXiv:1901.11265 sec. 1, p. 4); 20 GeV electrons emit mostly near 0.9 mrad (PDG detectors review sec. 35.6.5, p. 45).
<!-- /example -->

## Distinctive but generalizable features (TRDs)

- **Topology**: radiator-detector layers along the track; a deposit per layer and, in drift chambers, its time profile.
- **Inverse problem**: species (or `gamma`) from per-layer deposits that mix ionization and absorbed TR.
- **Natural objects**: hit or cluster, tracklet, per-layer deposit and path length, track estimator.
- **Informative residual**: most probable deposit (the statistic of the onset curve) or high-threshold probability versus `gamma` from several samples, against
  the onset curve; per-layer electron/hadron ratio versus depth or time slice.
- **Scaling**: threshold and saturation with `l1`, `l2`, `omega1`; yield `z^2`; rejection exponential in length.
- **Conventions**: signal efficiency of the working point; rejection as inverse efficiency; momentum or `gamma`
  binning of references, carried through the tool hooks.
- **Tails**: Landau and delta-electron tails of the background, saturated channels, secondary tracks.
- **Dependence**: gas gain, xenon content and pressure, temperature, occupancy, incidence angle.
- **Data sample**: tagged beams (FXT); conversions, decays and tag-and-probe (COL); species selected by other
  subdetectors (SPC).
- **Transfers**: the `gamma` dependence, estimators and reporting. **Does not transfer**: references and
  thresholds between radiators, gases or gain settings.

## Common misconceptions and failure modes

- **A rejection without its momentum, efficiency, layer count, species pair and conditions.** One number at one
  momentum, with an unstated efficiency, layer count, species pair or run conditions, cannot be compared or extrapolated.
- **Regular-radiator parameters taken as physical.** For fibre and foam they are tuning parameters: check them at all
  momenta (arXiv:physics/0402131 sec. 3).
- **TR and `dE/dx` treated as independent.** They share the deposit (arXiv:1111.4188 sec. 3.2, p. 7); combine them in
  one reference set.
- **References built before the gain calibration, or on other conditions.** Pads, then chambers in time
  (arXiv:1709.02743 sec. 11.2, p. 51); xenon pressure and temperature are conditions (arXiv:1706.10182 sec. 3;
  arXiv:1111.4188 sec. 4.5).
- **Simulation used without its tails checked.** Delta-electron escape sets the tails (arXiv:1111.4188 sec. 4.3.1,
  p. 29).

## Deliverables

- Radiator type and material, for foils `l1`, `l2` and count, for fibre or foam density, fibre diameter and
  thickness plus any equivalent `l1`, `l2`, `N_f` marked as tuned with the momenta checked; gas, its xenon fraction and
  pressure; layer count and gas thickness per layer; field, rate (occupancy) and track source.
- Estimator, its inputs (charge, threshold, slices, path length) and any requirement it imposes.
- Rejection with its interval at a stated signal efficiency, versus momentum or `gamma`, with the layers on
  track and the samples and their purity.
- The onset curve from data, with its samples and `gamma` ranges.
- Calibration order, conditions ranges (gain, xenon pressure, temperature) and the reference version used.

## Tool hooks

- **Inputs**: per hit, layer index, deposit (keV after gain calibration), path length (cm), optional slice
  charges; per track, momentum or rigidity and charge; references per species, layer and momentum or `gamma` bin, with
  their conditions range.
- **Outputs**: per track, log-likelihood ratio per hypothesis pair, number of layers used; per sample, signal and
  background efficiency with binomial intervals at a stated confidence level, and rejection versus momentum or `gamma`.
- **Conventions**: signal efficiency fixed before the background is counted; rejection = 1 / background efficiency.
- **Closure test**: references built on one half of the control samples; the efficiency at the working point,
  measured on the disjoint half in every momentum or `gamma` bin, must contain the target signal efficiency in its
  interval, of half-width below a stated tolerance (else `inconclusive`), and the background efficiency must agree
  between the halves.
- **Negative control**: two species at the same `gamma`, scored with `gamma`-binned or common references
  (momentum-binned ones make it inapplicable; electrons and muons at equal `beta gamma`,
  arXiv:1709.02743 sec. 11, p. 47) must give, at the electron working point and with a stated minimum muon count
  (else `inconclusive`), a muon efficiency whose interval contains the electron efficiency (rejection `1 / eps_s`,
  not 1); a separation means the estimator
  uses momentum or a reference mismatch, not TR.
- **Statuses**: per track `ok`, `below-onset`, `saturated`, `insufficient-layers`, `out-of-range` (momentum or `gamma`
  outside the references), `conditions-mismatch`; per check `passed`, `failed`, `inconclusive` (too few events or too wide an interval).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Emission, `gamma` scaling, formation length | arxiv_1709.02743, arxiv_1702.06473 | pdg_2025_passage-of-particles-through-matter, arxiv_1111.4188 | arxiv_1108.4838 | gap | gap | gap |
| Radiators: threshold, saturation, irregular | gap | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265 | arxiv_1706.10182 | gap | gap | gap |
| Self-absorption, Xe conversion, build-up | arxiv_1702.06473 | arxiv_1111.4188, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Time profile | arxiv_1709.02743 | arxiv_physics_0402131 | gap | gap | gap | gap |
| Clusters, tracklets, hits on track | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Estimators | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641, arxiv_1111.4188 | arxiv_1706.10182 | gap | gap | gap |
| Ionization under TR, simulation | gap | arxiv_1111.4188, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Response calibration | arxiv_1709.02743 | [gas gain](in-situ-calibration-methods.md#gas-gain-equalization) | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap |
| Reporting rejection versus `gamma` | arxiv_1709.02743, arxiv_1109.5925 | pdg_2025_particle-detectors-at-accelerators, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Architectures | arxiv_1111.4188 | arxiv_1111.4188, pdg_2025_particle-detectors-at-accelerators | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap |
| Hadron separation | gap: a stated need at TeV (arxiv_1901.11265, arxiv_2201.07901) | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265 | gap: no instrument in the sources read | gap | gap | gap |
| Lorentz factor of nuclei | n/a: no heavy-nucleus beams at `gamma ~ 1e5` (arxiv_1111.4188) | n/a: as COL; beam tests calibrate only | arxiv_1108.4838, arxiv_0808.1718, arxiv_2201.07901 | gap | gap | gap |
| Silicon TR energy and angle | gap | pdg_2025_particle-detectors-at-accelerators, arxiv_1901.11265, arxiv_1111.4188 | gap: no instrument; proposed for low occupancy (arxiv_1111.4188) | gap | gap | gap |

`gap` marks content not found in the sources read; `n/a` gives the reason. UGD, GND and NUC are `gap` alike: no TRD of
these environments was surveyed. An accelerator neutrino TRD in arxiv_1111.4188 Table 1 was
not read.

## Citations

Each source was read in its arXiv e-print (PDG: the 2025 review PDFs) on 2026-11-21, arXiv:2201.07901 in its
abstract only; cells that link another reference rest on that reference's sources. Full entries with DOIs and the
sections read are in
[the TR bibliography](detector-principles-bibliography-transition-radiation.md).
