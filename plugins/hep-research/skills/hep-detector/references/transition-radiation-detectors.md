# Transition Radiation Detectors

How a transition radiation detector (TRD) turns the Lorentz factor of a charged particle into a measurement: TR
emission at interfaces and in radiator stacks, self-absorption and X-ray conversion in the gas, the time profile of the
signal, clusters, tracklets and hits on track, identification estimators, the response calibration they need, and how
rejection is reported versus `gamma`. Also: hadron separation, the Lorentz factor of nuclei, and silicon TR detection.
Kept elsewhere: the TR paragraph of [signal formation and readout](signal-formation-and-readout.md#light-scintillation-wavelength-shifting-attenuation)
and the comparison with other identification techniques in
[particle identification](particle-identification.md#transition-radiation-detectors-trd); per-layer reference PDFs,
layer correlations and `multisample_pid.py` in [multisample PID and reference PDFs](multisample-pid-and-reference-pdfs.md);
gas-gain equalization in [in-situ calibration methods](in-situ-calibration-methods.md#gas-gain-equalization); straw
trackers in [gaseous tracking technologies](gaseous-and-specialized-tracking-technologies.md#mwpcs-straw-tubes-and-rpcs);
fitting simulator parameters to TRD spectra is simcal, owned by hep-statistics ([TRD simcal](simulation-calibration/trd.md));
training neural-network estimators belongs to hep-ml
([space and astroparticle ML](../../hep-ml/references/space-and-astroparticle-ml.md)).

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground, neutrino
and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Radiator, gas, layer count, field, rate and the
track source are parameters of every method below. Sources are named by ID (`arxiv_<id>` is arXiv:<id>, `/` written
`_`; `pdg_2025_<review>` the PDG RPP 2025 review of that title); entries are in
[detector-principles-bibliography-transition-radiation.md](detector-principles-bibliography-transition-radiation.md).
Page numbers are PDF pages.

## Relations

- **Single interface** (exact for a vacuum-medium boundary and `gamma >> 1`; PDG passage review sec. 34.7.3,
  eqs. 34.45-34.46, p. 35): `I = alpha z^2 gamma hbar omega_p / 3`, `hbar omega_p = 28.81 eV sqrt(rho <Z/A>)`
  (`rho` in g/cm3); about 20 eV for styrene-like plastics, 0.7 eV for air.
- **Hardening, not yield** (exact to `(hbar omega_0 / gamma hbar omega_p)^2`; same sec., eq. 34.47, p. 36): the
  number of photons above a fixed fraction of `gamma hbar omega_p` is constant (above a tenth of it,
  `N = 0.59% z^2` per interface); above a fixed energy it grows as `(ln gamma)^2`. The energy rises with `gamma`
  because the spectrum hardens; at `gamma = 10^3` the photons are soft X-rays of 2-40 keV.
- **Formation length** (exact, a definition; same sec., p. 36):
  `d(omega) = (2c/omega) (1/gamma^2 + theta^2 + omega_p^2/omega^2)^-1`, largest, `gamma c / (sqrt(2) omega_p)`, at
  `omega = gamma omega_p / sqrt(2)`; tens of micrometres in practice. Written per medium as the formation zone `Z_i`,
  the yield is suppressed when a foil or gap is much thinner than its `Z_i` (arXiv:1111.4188 sec. 2.2, eq. 6, p. 4).
- **Emission angle** (approximate): characteristically `1/gamma` (PDG passage review sec. 34.7.3, p. 36), within a few
  mrad (PDG detectors review sec. 35.6.5, p. 45),
  so TR photons and the track deposit in the same cell.
- **Stack of `N_f` foils** (exact with absorption, regular spacing; arXiv:1111.4188 sec. 2.2, eq. 5, p. 3): interference
  of the foil amplitudes times an absorption factor; low-energy photons are absorbed in the radiator. The intensity
  grows as `N_f`, not `N_f^2` (PDG passage review sec. 34.7.3, p. 36).
- **Threshold, saturation, spectrum peak** (approximate; PDG detectors review sec. 35.6.5, p. 45):
  `gamma_thr ~ l1 omega1 / c`, `gamma_sat = 0.6 omega1 sqrt(l1 l2) / c`, `omega_max = l1 omega1^2 / (2 pi c)`, with
  `omega1` the foil plasma frequency, `l1` the foil thickness and `l2` the spacing; numerically
  `gamma_thr ~ 3e3 omega1 l1`, `gamma_sat ~ 3e3 omega1 sqrt(l1 l2)`, `omega_max = 0.65 l1 omega1^2` (`omega1` in eV,
  lengths in mm, `omega_max` in keV). Another form of `gamma_s` is arXiv:1111.4188 eq. 9; saturation sits near ten
  times the threshold in conventional radiators (arXiv:1901.11265 sec. 1, p. 2). Most detectors choose
  `gamma_sat ~ 3000` (PDG, p. 45).
- **Absorption** (approximate; PDG detectors review sec. 35.6.5, p. 45): photoabsorption per atom goes as
  `Z^n / omega^3`, `n` between 4 and 5, so a low-`Z` radiator and a high-`Z` (xenon) gas. Xenon, the heaviest gas,
  absorbs best: about 10 mm absorption length at 3-15 keV (arXiv:1111.4188 sec. 3.1, Fig. 4, p. 7).
- **Layer likelihood** (exact as a definition; assumes independent layers; arXiv:1111.4188 sec. 3.2, eqs. 12-13, p. 8):
  `L_e = P_e / (P_e + P_pi)`, `P_k = prod_i P(E_i | k)`, or `sum_i log [P(E_i|e) / P(E_i|pi)]`, with `P(E_i|k)` the
  measured per-layer spectra of identified particles.
- **Rejection versus length** (approximate, empirical; PDG detectors review sec. 35.6.5, Fig. 35.18, p. 47): at 90%
  electron efficiency, rescaled to 10 GeV, the pion rejection of past TRDs grows as `5 x 10^(L/38)` for overall length
  `L = 20-100 cm`.
- **Onset curve** (approximate, a fit form; arXiv:1709.02743 sec. 11, eq. 2, p. 48): the TR part of the most
  probable signal as a logistic function of `ln gamma`, added to a `dE/dx` parameterisation (eq. 1); values in the
  examples.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Choosing a radiator | Regular foils, or fibre or foam; a regular-radiator model with tuned parameters or an efficiency factor for the irregular kind | Measured spectra to tune on | Foils give more TR than foam at equal density; tuned parameters not unique, momentum dependence missed | FXT (arXiv:1111.4188 secs. 2.3, 3.3.1; arXiv:physics/0402131 sec. 3); SPC (arXiv:1706.10182 sec. 2) |
| Setting the `gamma` window | Choose `l1`, `l2` and material for `gamma_thr`, `gamma_sat`, `omega_max` | Target species and momentum band | Saturation reached by the background species | FXT (PDG sec. 35.6.5; arXiv:1901.11265 sec. 1); SPC (PDG p. 48; arXiv:2201.07901) |
| Detecting the photons | Xe-rich gas; thickness matched to the spectrum; build-up over thin layers | Gas purity; Xe content monitored | Argon fill keeps tracking, loses TR; L-escape line; low-energy loss in the radiator | COL (arXiv:1702.06473 sec. 3.1); FXT (arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 3) |
| Architecture | Thick radiator plus 2-4 cm Xe chamber per module, or thin straws spread through the radiator as part of a tracker | Space, material budget, rate | Few thick layers: fewer samples; thin layers: soft TR lost | COL (arXiv:1111.4188 sec. 4); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Drift chamber with time sampling | Slice the signal in drift time; TR appears at the radiator-side entrance (long drift) | Calibrated drift velocity and `t0`; ion-tail cancellation | Tail correlates time bins; slices treated as independent | COL (arXiv:1709.02743 secs. 2.1, 11.2); FXT (arXiv:physics/0402131 secs. 3-4) |
| Hits on a track | Pad clusters per time bin into chamber tracklets on a propagated seed; straw hits from an extrapolated or stand-alone track | External tracker, or enough TRD layers | Hits of a secondary or neighbour; wrong path length | COL (arXiv:1709.02743 secs. 8-8.2; arXiv:1109.5925 sec. 2); SPC (arXiv:1706.10182 sec. 2); FXT (arXiv:astro-ph/0608641 sec. 4.2.5) |
| Thick gas, full charge | Total charge or truncated mean | Many layers | Landau tail of the background | FXT (PDG p. 47; arXiv:1111.4188 sec. 3.2) |
| Thin gas | Cluster counting: hits above a 5-7 keV threshold; high-threshold fraction | Threshold stable in energy | Threshold drift with gain | COL (arXiv:1109.5925 sec. 4); FXT (arXiv:astro-ph/0608641 sec. 5.1) |
| Best separation | Layer likelihood (charge; charge and largest-cluster position; per-slice charges), neural network | References from clean samples | Correlations ignored; bins that must be non-empty cost efficiency | COL (arXiv:1709.02743 sec. 11.2); FXT (arXiv:astro-ph/0608641 sec. 5); SPC (arXiv:1706.10182 sec. 3) |
| TR plus `dE/dx` in one estimator | One likelihood per species from TR hits and a `dE/dx` measure | Both in one reference set | Multiplying them as independent | COL (arXiv:1109.5925 sec. 1); SPC (arXiv:1108.4838 sec. 3.3) |
| Simulation of the response | PAI ionization in thin gas, tuned TR generator, delta-electron escape, empirical non-linearity | Flight or beam data per species | Tails wrong without delta escape; ideal-chamber linearity | FXT (arXiv:1111.4188 sec. 4.3.1; arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 2) |
| Response calibration | Gain per channel, then per chamber in time; references in momentum bins after it; environment corrections | Clean samples; conditions record | References built before the gain calibration; drifting Xe pressure | COL (arXiv:1709.02743 sec. 11.2; arXiv:1109.5925 sec. 3.1); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Hadron separation | Long TRD; radiator sets with different thresholds; TR energy and angle | Fixed-target hadron or hyperon beam | All hadrons radiate at TeV momenta | FXT only (see below) |
| Lorentz factor of nuclei | `z^2`-scaled TR on top of the relativistic rise | Charge measured independently | Response gap at the onset | SPC only (see below) |
| TR energy and angle | Silicon strip or pixel detector behind the radiator, field to deflect the track | Low occupancy | Photon-track association | FXT only, R&D (see below) |

**Single-environment techniques.** Hadron separation with TRDs exists only in fixed-target hadron and hyperon beams:
pions from protons and kaons up to 200 GeV/c (PDG detectors review sec. 35.6.5, p. 48; arXiv:1111.4188 secs. 1-2.4,
pp. 2, 5). It needs longer detectors than electron identification, and at TeV momenta, where all hadrons radiate, sets
with different thresholds or the TR energy and angle (arXiv:1901.11265 sec. 1, pp. 3-4). TeV hadron identification in the forward region of
a future collider experiment is a stated need, not a practice (arXiv:1901.11265 sec. 1, p. 3; arXiv:2201.07901 abstract). The Lorentz factor of nuclei is measured with TR only in balloon and space
instruments: no accelerator provides heavy nuclei at the `gamma ~ 1e5` the radiators aim at (arXiv:1111.4188 sec.
3.4.1, p. 15). Radiators are tuned, with dense materials such as Al, to extend the rise to `gamma ~ 1e5` with photons
up to 100 keV, and Compton-scatter detection is proposed (PDG p. 48); compound radiators with varying foil parameters
widen the range (arXiv:2201.07901 abstract). The flux measurements are in
[space-based direct detection](space-based-direct-detection.md#direct-detection-composition-and-the-local-antiparticle-excesses)
and [cosmic-ray composition](cosmic-ray-spectrum-and-composition.md#composition-and-its-observables). Silicon TR
detection, separating photons from the track in space and measuring the angle with the energy, is test-beam R&D (PDG
p. 48; arXiv:1901.11265 sec. 1, p. 4; arXiv:1111.4188 sec. 3.4.2, pp. 15-16).

Rules that hold across the rows:

- **TR depends on `gamma` alone.** Electrons and muons at equal `beta gamma` give consistent signals, so muons of
  known momentum calibrate the onset (arXiv:1709.02743 sec. 11, p. 47; arXiv:1702.06473 sec. 1, p. 4).
- **Rejection is not monotonic in momentum.** It improves through the onset and falls once TR saturates and the
  background's `dE/dx` rises relativistically (arXiv:1111.4188 sec. 3.2, Fig. 8, p. 10; arXiv:1709.02743 sec. 11.2,
  p. 51); it also falls as the background species' own `gamma` approaches the onset (arXiv:1706.10182 sec. 1).
- **The working point is an analysis choice.** The background efficiency depends strongly on the signal efficiency;
  90% is the convention (arXiv:1111.4188 sec. 3.2, pp. 9-10). A momentum-dependent cut keeps the signal efficiency
  constant versus momentum (arXiv:1709.02743 sec. 11.2, p. 51).
- **Time bins are correlated.** Ion tails carry charge into later bins; amplitudes per bin cannot enter a likelihood
  as independent (arXiv:physics/0402131 sec. 4, p. 4; arXiv:1709.02743 sec. 8.2, p. 35); group slices, use the
  position of the largest cluster, or a network.
- **"Cluster" has two meanings.** In pad chambers it is a reconstructed charge cluster; in cluster counting a hit
  above the threshold (arXiv:1709.02743 sec. 8.1; arXiv:astro-ph/0608641 sec. 5.1). State which.
- **TR builds up with depth in thin-layer detectors.** Photons above about 4 keV cross several layers before
  converting (PDG p. 46), so electron deposits grow with depth while hadron deposits stay flat (arXiv:1706.10182
  sec. 3, p. 4): per-layer references are per layer
  ([layer correlations](multisample-pid-and-reference-pdfs.md#layer-correlations)).
- **Point-like conversions saturate differently.** An X-ray converts at one point; track ionization is spread, so a
  gas non-linearity differs for the two (arXiv:1706.10182 sec. 2, p. 3).

<!-- example: named apparatus and their numbers (collider, test-beam, space and balloon instances of the rows above) -->
- ALICE TRD: 6 layers, foam/fibre radiator, Xe-CO2 chamber with 3 cm drift (arXiv:1709.02743 sec. 1, p. 2); clusters
  from up to 3 adjacent pads per 100 ns time bin, E x B corrected, straight-line tracklets (secs. 8.1-8.2, p. 35);
  7 slices of about 5 mm each; LQ2D sums the first four and the last three; LQ7D's non-empty bins cost about 40% of
  electrons (sec. 11.2, pp. 50-51). Onset fit `TR/TR_mip = 0.706 / (1 + exp(-1.85 (ln gamma - 7.80)))`, half-maximum
  at `beta gamma = 2.4e3`, onset visible above `beta gamma ~ 800` (sec. 11, eq. 2, pp. 47-48). Pion rejection at
  1 GeV/c, p-Pb: about 70 (LQ1D), up to 410 with the time evolution, efficiency as in its Fig. 42 (design goal 100 at
  90%) (p. 51); references
  centrality-dependent in Pb-Pb (about 15% shift, p. 51).
- ALICE TRD prototypes, CERN PS, 1-6 GeV/c: likelihood on charge gives pion rejection about 100; charge plus
  largest-cluster position about 1.6 times better (arXiv:physics/0402131 sec. 4, pp. 3-4); tuned regular-radiator
  parameters `d1 = 10 um`, `d2 = 80 um`, `N_f = 270` describe 2 GeV/c but not the momentum dependence (sec. 3, p. 3).
- ATLAS TRT: 4 mm straws, 70% Xe, 27% CO2, 3% O2 for TR photons of 6-15 keV; argon in leaking modules in Run 2
  (arXiv:1702.06473 sec. 3.1, p. 7); emission probability steps from about zero to its maximum between `gamma` 500
  and 2000 (sec. 1, p. 4). Low threshold about 300 eV, high threshold 6-7 keV, about 34 hits per track; HT probability
  rises from 0.05 to a plateau of 0.2-0.3 by region; onset mapped with pions, conversion electrons and Z electrons
  (arXiv:1109.5925 secs. 2, 4.1, pp. 1-3).
- AMS-02 TRD: 20 straw layers, 20 mm fleece radiator, Xe/CO2 (91.5/8.5%), 18.5 hits per track; Geant4 fibre
  thickness tuned to 12 um against 10 um nominal; per-module gain versus time from protons (arXiv:1706.10182 sec. 2,
  pp. 1-2); flight data selected within +-30 mbar of the simulated 850 mbar xenon pressure (sec. 3, p. 4). Proton
  rejection above 1e4 at 10 GeV/c and 10 at 1 TeV/c (sec. 1, p. 1).
- AMS-02 TRD 20-layer prototype, CERN SPS X7: single-track roads of 1.5 and 5 tube diameters (arXiv:astro-ph/0608641
  sec. 4.2.5, p. 5); TR photon detection efficiency about 30% above 5 keV, Xe L-escape line at 4.2 keV (sec. 4.3,
  pp. 5-6); cluster counting at 6.5 keV with `N_cut = 6`: proton rejection 360 +- 60 for 100 GeV protons at 89% electron
  efficiency (sec. 5.1, p. 6).
- Model TRD of the review (calculation; 100 foils of 15 um, 300 um gaps, 1 cm Xe-CO2): about 2/3 of the TR photons
  detected (arXiv:1111.4188 sec. 3.1, p. 7); most rejection gained up to 1.5 cm gas (sec. 3.3.2, Fig. 9, p. 12).
- TRACER (balloon): `dE/dx` gives 10-400 GeV/amu, the TRD above about 1000 GeV/amu, 400-1500 GeV/amu excluded;
  more xenon moved the TR appearance threshold to `gamma = 785 +- 140` (arXiv:1108.4838 sec. 3.3, p. 7).
- CREAM-I TRD (balloon): xenon relativistic rise gives `4 < gamma < 5e2` below the TR onset, beam-test calibrated
  (arXiv:0808.1718 sec. 2, p. 5).
- Hadron beams: kaons from pions roughly at 200-700 GeV/c (arXiv:1111.4188 sec. 2.4, p. 5); a few percent pion
  contamination at 90% kaon efficiency at 140 GeV/c needed 15 module sets (arXiv:1901.11265 sec. 1, p. 3).
- Silicon TR set-up, CERN SPS: 300 um double-sided strip detector, 50 um pitch; 20 GeV/c electrons and 120-290 GeV/c
  muons (arXiv:1901.11265 sec. 1, p. 4); 20 GeV electrons emit mostly near 0.9 mrad (PDG sec. 35.6.5, p. 45).
<!-- /example -->

## Distinctive but generalizable features (TRDs)

- **Topology**: radiator-detector layers along the track; one deposit per layer and, in drift chambers, its time profile.
- **Inverse problem**: species (or `gamma`) from per-layer deposits that mix ionization and absorbed TR.
- **Natural objects**: hit or cluster, tracklet, per-layer deposit with path length, track estimator.
- **Informative residual**: mean deposit or high-threshold probability versus `gamma` from several samples, against
  the onset curve; per-layer electron/hadron ratio versus depth or time slice.
- **Scaling**: threshold and saturation with `l1`, `l2`, `omega1`; yield `z^2`; rejection exponential in length.
- **Conventions**: signal efficiency of the working point; rejection as inverse efficiency; momentum or `gamma`
  binning of references.
- **Tails**: Landau and delta-electron tails of the background; saturated channels; secondary tracks.
- **Dependence**: gas gain, xenon content and pressure, temperature, occupancy, incidence angle.
- **Data sample**: tagged beams (FXT); conversions, decays and tag-and-probe (COL); species selected by the other
  subdetectors (SPC).
- **Transfers**: the `gamma` dependence, estimators and reporting, to any TRD. **Does not transfer**: references and
  thresholds between radiators, gases or gain settings.

## Common misconceptions and failure modes

- **A rejection without its momentum and efficiency.** One number at one momentum and an unstated efficiency cannot be
  compared or extrapolated.
- **Regular-radiator parameters taken as physical.** For fibre and foam they are tuning parameters: check them at all
  momenta (arXiv:physics/0402131 sec. 3).
- **TR and `dE/dx` treated as independent.** They share the deposit (arXiv:1111.4188 sec. 3.2, p. 7); combine them in
  one reference set.
- **References built before the gain calibration, or on other conditions.** Pads, then chambers in time
  (arXiv:1709.02743 sec. 11.2, p. 51); xenon pressure and temperature are run conditions (arXiv:1706.10182 sec. 3;
  arXiv:1111.4188 sec. 4.5).
- **Simulation used without its tails checked.** Delta-electron escape sets the tails (arXiv:1111.4188 sec. 4.3.1,
  p. 29).

## Deliverables

- Radiator (type, `l1`, `l2`, material, count), gas and its xenon fraction and pressure, layer count and thickness.
- Estimator, its inputs (charge, threshold, slices, path length), and any requirement it imposes.
- Rejection with its interval at a stated signal efficiency, versus momentum or `gamma`, with the number of layers on
  track, and the samples and their purity.
- The onset curve from data, with the samples and `gamma` ranges they cover.
- Calibration order, conditions ranges (gain, xenon pressure, temperature) and the reference version used.

## Tool hooks

- **Inputs**: per hit, layer index, deposit (keV after gain calibration), path length (cm), optional time-slice
  charges; per track, momentum or rigidity and charge; references per species, layer and momentum bin, with their
  conditions range.
- **Outputs**: per track, log-likelihood ratio per hypothesis pair, number of layers used; per sample, signal and
  background efficiency with binomial intervals at a stated confidence level, and rejection versus momentum.
- **Conventions**: signal efficiency fixed before the background is counted; rejection = 1 / background efficiency.
- **Closure test**: references built on one half of the control samples; the efficiency at the working point,
  measured on the disjoint half, must contain the target signal efficiency in its interval.
- **Negative control**: two species at the same `gamma` (electrons and muons at equal `beta gamma`,
  arXiv:1709.02743 sec. 11, p. 47) must give a rejection whose interval contains 1; a separation means the estimator
  uses momentum or a reference mismatch, not TR.
- **Statuses**: per track `ok`, `below-onset`, `saturated`, `insufficient-layers`, `out-of-range` (momentum outside the
  references), `conditions-mismatch`; per check `passed`, `failed`, `inconclusive` (too few events).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Emission, `gamma` scaling, formation length | arxiv_1709.02743, arxiv_1702.06473 | pdg_2025_passage-of-particles-through-matter, arxiv_1111.4188 | arxiv_1108.4838 | gap | gap | gap: unsurveyed |
| Radiators: threshold, saturation, irregular | gap | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Self-absorption, Xe conversion, build-up | arxiv_1702.06473 | arxiv_1111.4188, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Time profile | arxiv_1709.02743 | arxiv_physics_0402131 | gap | gap | gap | gap: unsurveyed |
| Clusters, tracklets, hits on track | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Estimators | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641, arxiv_1111.4188 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Ionization under TR, simulation | gap | arxiv_1111.4188, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Response calibration | arxiv_1709.02743, arxiv_1109.5925 | [gas gain](in-situ-calibration-methods.md#gas-gain-equalization) | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap: unsurveyed |
| Reporting rejection versus `gamma` | arxiv_1709.02743, arxiv_1109.5925 | pdg_2025_particle-detectors-at-accelerators, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap: unsurveyed |
| Architectures | arxiv_1111.4188 | pdg_2025_particle-detectors-at-accelerators | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap: unsurveyed |
| Hadron separation | gap: a stated need at TeV (arxiv_1901.11265, arxiv_2201.07901) | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265 | n/a: no instrument found in the sources read | gap | gap | gap: unsurveyed |
| Lorentz factor of nuclei | n/a: no heavy-nucleus beams at `gamma ~ 1e5` (arxiv_1111.4188) | n/a: as COL; beam tests calibrate only | arxiv_1108.4838, arxiv_0808.1718, arxiv_2201.07901 | gap | gap | gap: unsurveyed |
| Silicon TR energy and angle | gap | arxiv_1901.11265, arxiv_1111.4188 | gap: proposed for low occupancy (arxiv_1111.4188) | gap | gap | gap: unsurveyed |

`gap` marks content not found in the sources read; `n/a` gives the reason. UGD and GND detectors with TRDs were not
surveyed; NUC TRDs were not surveyed. An accelerator neutrino experiment with a TRD is listed in arxiv_1111.4188
Table 1 but was not read.

## Citations

Each source was read in its arXiv e-print (PDG: the 2025 review PDFs) on 2026-11-21. Full entries with DOIs and the
sections read are in
[detector-principles-bibliography-transition-radiation.md](detector-principles-bibliography-transition-radiation.md).
