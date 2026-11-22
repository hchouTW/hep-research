# Transition Radiation Detectors

Transition radiation detectors (TRD): emission, radiators, absorption, time profile, tracklets, estimators,
calibration, rejection versus `gamma`, hadrons, nuclei, silicon TR.
Elsewhere: TR in [signal formation](signal-formation-and-readout.md#light-scintillation-wavelength-shifting-attenuation),
technique comparison in
[particle identification](particle-identification.md#transition-radiation-detectors-trd); per-layer PDFs
and `multisample_pid.py` in [multisample PID](multisample-pid-and-reference-pdfs.md);
gas-gain equalization in [in-situ calibration](in-situ-calibration-methods.md#gas-gain-equalization); straws in
[gaseous tracking](gaseous-and-specialized-tracking-technologies.md#mwpcs-straw-tubes-and-rpcs);
simulator tuning is simcal ([TRD simcal](simulation-calibration/trd.md), hep-statistics);
training networks is hep-ml's ([space ML](../../hep-ml/references/space-and-astroparticle-ml.md)).

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground, neutrino
and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Radiator, gas, layers, field, rate and track
source are parameters throughout. Source IDs: `arxiv_<id>` (`/` as `_`), `pdg_2025_<review>` (PDG RPP 2025);
entries in [the TR bibliography](detector-principles-bibliography-transition-radiation.md); pages are PDF pages.

## Relations

- **Single interface** (exact for a vacuum-medium boundary and `gamma >> 1`; PDG passage review sec. 34.7.3,
  eqs. 34.45-34.46, p. 35): `I = alpha z^2 gamma hbar omega_p / 3`, `hbar omega_p = 28.81 eV sqrt(rho <Z/A>)`
  (`rho` in g/cm3); about 20 eV for styrene-like plastics, 0.7 eV for air.
- **Hardening, not yield** (exact to `(hbar omega_0 / gamma hbar omega_p)^2`; same sec., eq. 34.47, p. 36): the
  number of photons above a fixed fraction of `gamma hbar omega_p` is constant; above a fixed energy it grows as `(ln gamma)^2`.
- **Formation length** (exact, a definition; same sec., p. 36):
  `d(omega) = (2c/omega) (1/gamma^2 + theta^2 + omega_p^2/omega^2)^-1`, for `theta = 1/gamma` largest,
  `gamma c / (sqrt(2) omega_p)`, at `omega = gamma omega_p / sqrt(2)`; tens of micrometres. As the formation zone `Z_i`
  per medium: yield suppressed for a foil or gap much thinner than `Z_i` (arXiv:1111.4188 sec. 2.2, eq. 6, p. 4).
- **Emission angle** (approximate): about `1/gamma` for a single interface (PDG passage review sec. 34.7.3, p. 36);
  in a stack the radiator sets it, `theta ~ 1.2 / (omega1 sqrt(l1 l2))` (mrad; `omega1` in eV, lengths in mm) at the
  last interference maximum, near its limit from `gamma_sat` on, within a few mrad (PDG detectors review p. 45, sec.
  35.6.5): photon and track deposits share a cell unless the cells are fine and far from the radiator (about 1 m
  gives separations near 100 um), or a magnetic field deflects the track to silicon strips at modest distances
  (arXiv:1901.11265 sec. 1, pp. 3-4).
- **Stack of `N_f` foils** (exact with absorption for regular spacing in the `gamma >> 1` small-angle limit of its
  phases; arXiv:1111.4188 sec. 2.2, eq. 5, p. 3): foil
  amplitudes interfere, times an absorption factor; soft photons are absorbed in the radiator. Without absorption the intensity
  grows as `N_f`, not `N_f^2` (PDG passage review sec. 34.7.3, p. 36); with it, the factor `1 - exp(-N_f sigma)` of a simpler,
  approximate form saturates it near `1/sigma` foils (an inference from arXiv:1111.4188 sec. 2.4, eq. 10, p. 5).
- **Threshold, saturation, spectrum peak** (approximate; PDG detectors review sec. 35.6.5, p. 45):
  analytic forms `gamma_thr ~ l1 omega1 / c`, `gamma_sat = 0.6 omega1 sqrt(l1 l2) / c`,
  `omega_max = l1 omega1^2 / (2 pi c)`, `omega1` the foil plasma frequency, `l1` the foil thickness, `l2` the spacing;
  PDG's printed practical forms `gamma_thr ~ 3e3 omega1 l1`, `gamma_sat ~ 3e3 omega1 sqrt(l1 l2)`,
  `omega_max = 0.65 l1 omega1^2` (`omega1` in eV, lengths in mm, `omega_max` in keV) differ: converted with `hbar c`
  the analytic ones give 5.1e3, 3.0e3 and 0.81 keV, so only `gamma_sat` agrees and both sets are estimates
  (record which in the inputs and deliverables; practical ratio `sqrt(l2 / l1)`); use one set.
  Analytically `gamma_sat / gamma_thr = 0.6 sqrt(l2 / l1)`. It is 2-5
  for `l2 / l1` of 10-60, 10 near 280; arXiv:1901.11265 sec. 1 (p. 2) gives a factor of about ten above a threshold near
  5e2 and ties it to `l2 / l1`, which its typical foils and spacings allow. Most detectors choose
  `gamma_sat ~ 3000` (PDG detectors review, p. 45).
- **Absorption** (approximate; PDG detectors review sec. 35.6.5, p. 45): photoabsorption per atom goes as
  `Z^n / omega^3`, `n` between 4 and 5, so a low-`Z` radiator and a high-`Z` (xenon) gas. Of argon, krypton and xenon,
  xenon absorbs best: absorption length about 2 mm at 3 keV and again just above the L edges near 5 keV, 10 mm at
  10 keV, 30 mm at 15 keV (read off the figure; gas density not stated), the text giving about 10 mm for
  TR of 3-15 keV (arXiv:1111.4188 sec. 3.1, Fig. 4, p. 7).
- **Layer likelihood** (exact as a definition; assumes independent layers; arXiv:1111.4188 sec. 3.2, eqs. 12-13, p. 8):
  `L_e = P_e / (P_e + P_pi)`, `P_k = prod_i P(E_i | k)`, with `P(E_i|k)` the
  measured per-layer spectra of identified particles.
- **Rejection versus length** (approximate, empirical; PDG detectors review p. 47 and Fig. 35.18, p. 48, sec. 35.6.5):
  at 90% electron efficiency, with data of 1-40 GeV rescaled to 10 GeV when possible (scatter also from beam
  energy and analysis), the pion rejection of past TRDs grows as `5 x 10^(L/38)` for overall length
  `L = 20-100 cm`.
- **Onset curve** (approximate, a fit form; arXiv:1709.02743 sec. 11, eq. 2, p. 48): the TR part of the most
  probable signal as a logistic function of `ln gamma`, added to a `dE/dx` parameterisation (eq. 1).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Choosing a radiator | Regular foils, fibre or foam; irregular ones as a tuned regular radiator or an efficiency factor | Measured spectra to tune on | Foam gives less TR than foils at equal density; tuned parameters not unique, miss the momentum dependence | FXT (arXiv:1111.4188 secs. 2.3, 3.3.1; arXiv:physics/0402131 sec. 3); SPC (arXiv:1706.10182 sec. 2) |
| Setting the `gamma` window | Choose `l1`, `l2` and material for `gamma_thr`, `gamma_sat`, `omega_max` | Target species and momentum band | Saturation reached by the background species | FXT (PDG detectors review sec. 35.6.5, p. 45; arXiv:1901.11265 sec. 1, pp. 2, 4); SPC (PDG detectors review p. 48; arXiv:2201.07901 abstract) |
| Detecting the photons | Xe-rich gas, thickness matched to the spectrum; build-up over thin layers | Gas purity; Xe content monitored | Argon fill loses TR; L-escape line; soft TR absorbed in the radiator | COL (arXiv:1702.06473 sec. 3.1); FXT (arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 3) |
| Architecture | Thick radiator plus 2-4 cm Xe chamber per module, or thin straws through the radiator as part of a tracker | Space, material, rate | Few thick layers: fewer samples; thin layers: soft TR lost | COL (arXiv:1111.4188 sec. 4); FXT (arXiv:1111.4188 sec. 4.4; PDG detectors review p. 46); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Drift chamber with time sampling | Slice the signal in drift time; TR arrives at the radiator-side entrance (long drift) | Calibrated drift velocity and `t0`; ion-tail cancellation | Slices treated as independent | COL (arXiv:1709.02743 secs. 2.1, 11.2); FXT (arXiv:physics/0402131 secs. 3-4) |
| Hits on a track | Pad clusters per time bin into tracklets on a propagated seed; straw hits on a track; an extrapolated or stand-alone track in space | External tracker or enough TRD layers | Hits of a secondary or neighbour; wrong path length | COL (arXiv:1709.02743 secs. 8-8.2; arXiv:1109.5925 sec. 2); SPC (extrapolated or stand-alone: arXiv:1706.10182 sec. 2); FXT (arXiv:astro-ph/0608641 sec. 4.2.5) |
| Thick gas, full charge | Total charge or truncated mean | Many layers | Landau tail of the background | FXT (PDG detectors review sec. 35.6.5, p. 47; arXiv:1111.4188 sec. 3.2) |
| Thin gas | Cluster counting: hits above a threshold (typically 5-7 keV; PDG detectors review sec. 35.6.5, p. 47); high-threshold fraction | Threshold stable in energy | Threshold drift with gain | COL (arXiv:1109.5925 secs. 2, 4); FXT (arXiv:astro-ph/0608641 sec. 5.1) |
| Best separation | Layer likelihood (charge; charge and largest-cluster position; per-slice charges), neural network | References from clean samples | Correlations ignored; bins that must be non-empty cost efficiency | COL (arXiv:1709.02743 sec. 11.2); FXT (arXiv:astro-ph/0608641 sec. 5; arXiv:physics/0402131 sec. 4, pp. 3-4, charge and position); SPC (arXiv:1706.10182 sec. 3) |
| TR plus `dE/dx` in one estimator | One likelihood per species from TR hits and a `dE/dx` measure | One reference set for both | Multiplying them as independent | COL only (arXiv:1109.5925 sec. 1); SPC correlates a separate `dE/dx` array with the TRD signal instead (arXiv:1108.4838 sec. 3.3, pp. 7-8) |
| Simulation of the response | PAI ionization in thin gas, tuned TR generator, delta-electron escape, empirical non-linearity | Flight or beam data per species | Tails wrong without delta escape; one non-linearity for point-like conversions and spread ionization | FXT (arXiv:1111.4188 sec. 4.3.1; arXiv:astro-ph/0608641 sec. 4.3); SPC (arXiv:1706.10182 sec. 2) |
| Response calibration | Gain per channel, then per chamber in time; then references in momentum or `gamma` bins; environment corrections | Clean samples; conditions record | References before the gain calibration; drifting Xe pressure | COL (arXiv:1709.02743 sec. 11.2); FXT ([gas gain](in-situ-calibration-methods.md#gas-gain-equalization)); SPC (arXiv:1706.10182 sec. 2; arXiv:1111.4188 sec. 4.5) |
| Hadron separation | Long TRD; radiator sets with different thresholds; TR energy and angle | Fixed-target hadron or hyperon beam | All hadrons radiate at TeV momenta | FXT only (see below) |
| Lorentz factor of nuclei | `z^2`-scaled TR on top of the relativistic rise | Charge measured independently | Response gap at the onset | SPC only (see below) |
| TR energy and angle | Silicon strips or pixels behind the radiator; a field deflecting the track, or about 1 m of distance, separates the photons | Low occupancy | Photon-track association | FXT only, R&D (see below) |

**Single-environment techniques.** Hadron separation with TR exists only in fixed-target hadron and hyperon beams:
pions from protons and kaons up to 200 GeV/c in past detectors, pions identified in a 250 GeV hadron beam, and kaons
from pions stated feasible roughly at 200-700 GeV/c by one cited study, not shown
(PDG detectors review sec. 35.6.5, p. 48; arXiv:1111.4188 pp. 2, 5, secs. 1 and 2.4); a collider TRD separates hadrons
at low momentum by truncated-mean `dE/dx` instead (arXiv:1709.02743 sec. 11.1, Fig. 40, pp. 49-50). It needs longer
TRDs than electron identification and, at TeV where all hadrons radiate, several thresholds or the TR energy and angle
(arXiv:1901.11265 sec. 1, pp. 3-4); TeV hadron identification at modern or planned accelerators is a stated need (forward hadrons: sec. 1, p. 3;
a future accelerator experiment: arXiv:2201.07901 abstract). The Lorentz factor of nuclei is measured with TR only in balloons and space: no
accelerator gives heavy nuclei at the `gamma ~ 1e5` aimed at (arXiv:1111.4188 sec. 3.4.1, p. 15). Tuned radiators of
dense materials such as Al extend the rise to `gamma ~ 1e5` with photons up to 100 keV, with Compton-scatter detection
proposed (PDG detectors review sec. 35.6.5, p. 48); compound radiators of varied foils
are proposed to widen the range, their yield derived, not measured (arXiv:2201.07901 abstract). Composition by charge and mass, without TR:
[space-based direct detection](space-based-direct-detection.md#direct-detection-composition-and-the-local-antiparticle-excesses);
spectrum: [cosmic-ray spectrum](cosmic-ray-spectrum-and-composition.md#the-all-particle-spectrum-and-its-features)
and [composition](cosmic-ray-spectrum-and-composition.md#composition-and-its-observables). Silicon TR
detection (photons apart from the track, angle measured with energy) is test-beam R&D (PDG
detectors review p. 48; arXiv:1901.11265 sec. 1, p. 4; arXiv:1111.4188 sec. 3.4.2, pp. 15-16).

Rules that hold across the rows:

- **TR depends on `gamma` and `z^2`, not on mass** (`z^2`: PDG passage review sec. 34.7.3, p. 35). Electrons and muons at equal `beta gamma` give consistent signals, so muons
  calibrate the onset (arXiv:1709.02743 sec. 11, p. 47; arXiv:1702.06473 sec. 1, p. 4).
- **Rejection is not monotonic in momentum.** It improves through the onset and falls once TR saturates and the
  background's `dE/dx` rises (arXiv:1111.4188 sec. 3.2, Fig. 8, p. 10; arXiv:1709.02743 sec. 11.2,
  p. 51); against protons it also falls at high momentum (space example below), plausibly as their `gamma` nears the onset:
  an inference from two numbers of unstated signal efficiency, perhaps not comparable (arXiv:1706.10182 sec.
  1 states no mechanism).
- **The working point is an analysis choice.** Background efficiency depends strongly on it; 90% is the convention
  (arXiv:1111.4188 sec. 3.2, pp. 9-10). A momentum-dependent cut keeps it constant (arXiv:1709.02743 sec. 11.2, p. 51).
- **Time bins are correlated** in readouts that sample drift time. Ion tails carry charge into later bins; per-bin amplitudes cannot enter a likelihood
  as independent factors (arXiv:physics/0402131 sec. 4, p. 4; arXiv:1709.02743 sec. 8.2, p. 35): use joint
  references over slice groups (sec. 11.2, p. 51), cluster position with charge, or a network; tail cancellation
  helps (arXiv:1709.02743 sec. 8.2, p. 35).
- **TR builds up with depth in thin-layer detectors.** TR below about 4 keV is mostly lost in the radiator; harder
  photons are registered over several consecutive layers (PDG detectors review sec. 35.6.5, p. 46): electron deposits
  grow with depth, hadron ones stay flat (arXiv:1706.10182 sec. 3, p. 4), so references are per layer
  ([layer correlations](multisample-pid-and-reference-pdfs.md#layer-correlations)).

<!-- example: named apparatus and their numbers (collider, test-beam, space and balloon instances of the rows above) -->
- ALICE TRD: 6 layers, foam/fibre radiator, Xe-CO2 chamber with 3 cm drift (arXiv:1709.02743 sec. 1, p. 2); clusters
  from up to 3 adjacent pads per 100 ns time bin, straight-line tracklets (secs. 8.1-8.2, p. 35);
  7 slices of about 5 mm each; LQ7D's non-empty bins cost about 40% of
  electrons (sec. 11.2, pp. 50-51). Onset fit `TR/TR_mip = 0.706 / (1 + exp(-1.85 (ln gamma - 7.80)))`, half-maximum
  at `beta gamma = 2.4e3`, onset visible above `beta gamma ~ 800` (sec. 11, eq. 2, pp. 47-48). Pion rejection at
  1 GeV/c, p-Pb, 6 layers, 90% electron efficiency: about 70 (LQ1D), up to 410 with the time evolution (sec. 13,
  p. 65; Fig. 42 right, p. 52), beside a design goal of 100 at 90% (sec. 11.2, p. 51); references
  centrality-dependent in Pb-Pb (about 15% shift, p. 51).
- ALICE TRD prototypes, CERN PS, 1-6 GeV/c: a likelihood on charge gives pion rejection about 100 at 90% electron
  efficiency, six layers extrapolated from four measured (Figs. 4-5); charge plus
  largest-cluster position about 1.6 times better (arXiv:physics/0402131 sec. 4, pp. 3-4); tuned regular-radiator
  parameters `l1 = 10 um`, `l2 = 80 um`, `N_f = 270` describe 2 GeV/c but not the momentum dependence (sec. 3, p. 3).
- ATLAS TRT: 4 mm straws (arXiv:1702.06473 sec. 3.1, p. 6); 70% Xe, 27% CO2, 3% O2 for TR photons of 6-15 keV;
  argon in leaking modules in Run 2 (p. 7); emission probability steps from about zero to its maximum between `gamma` 500
  and 2000 (sec. 1, p. 4). High threshold 6-7 keV; HT probability
  rises from 0.05 to a plateau of 0.2-0.3 by region; onset mapped with pions, conversion electrons and Z electrons
  (arXiv:1109.5925 secs. 2, 4.1, pp. 1-3).
- AMS-02 TRD: 20 straw layers, 20 mm fleece radiator, Xe/CO2 (91.5/8.5%); Geant4 fibre
  thickness tuned to 12 um against 10 um nominal; per-module gain versus time from protons (arXiv:1706.10182 sec. 2,
  pp. 1-2); flight data selected within +-30 mbar of the simulated 850 mbar xenon pressure (sec. 3, p. 4). Proton
  rejection above 1e4 at 10 GeV/c and 10 at 1 TeV/c, signal efficiency not stated in the source (sec. 1, p. 1, from its ref. [3]).
- AMS-02 TRD 20-layer prototype, CERN SPS X7: single-track roads of 1.5 and 5 tube diameters (arXiv:astro-ph/0608641
  sec. 4.2.5, p. 5); simulated (Geant3) TR photon detection efficiency about 30% above 5 keV, Xe L-escape line at 4.2 keV (sec. 4.3,
  pp. 5-6); cluster counting at 6.5 keV with `N_cut = 6`: proton rejection 360 +- 60 for 100 GeV protons at 89% electron
  efficiency (sec. 5.1, p. 6).
- TRACER (balloon): `dE/dx` gives 10-400 GeV/amu; TR identifies particles above about 1000 GeV/amu, but
  400-1500 GeV/amu is excluded;
  more xenon moved the TR appearance threshold to `gamma = 785 +- 140` (arXiv:1108.4838 sec. 3.3, p. 7).
- CREAM-I TRD (balloon): `4 < gamma < 5e2` from the xenon relativistic rise, beam-test calibrated (arXiv:0808.1718
  sec. 2, p. 5).
- Silicon TR set-up, CERN SPS: double-sided strips (arXiv:1901.11265 sec. 1, p. 4) 2.2 m behind the radiator (sec. 2.2, p. 7).
<!-- /example -->

## Distinctive but generalizable features (TRDs)

- **Topology**: radiator-detector layers along the track; a deposit per layer, in drift chambers with a time profile.
- **Inverse problem**: species (or `gamma`) from per-layer deposits mixing ionization and absorbed TR.
- **Natural objects**: hit or cluster (a pad charge cluster, or a hit above threshold in cluster counting, arXiv:1709.02743
  sec. 8.1, arXiv:astro-ph/0608641 sec. 5.1: state which), tracklet, per-layer deposit and path length.
- **Informative residual**: most probable deposit or high-threshold probability versus `gamma`, against the onset; per-layer electron/hadron ratio versus depth or time slice.
- **Scaling**: threshold and saturation with `l1`, `l2`, `omega1`; yield `z^2`; rejection exponential in length.
- **Conventions**: working-point signal efficiency; rejection as inverse efficiency; reference binning.
- **Tails**: Landau and delta-electron tails, saturated channels, secondary tracks.
- **Dependence**: gas gain, xenon content and pressure, temperature, occupancy, incidence angle.
- **Data sample**: tagged beams (FXT); conversions, decays, tag-and-probe (COL); species from other subdetectors (SPC).
- **Transfers**: the `gamma` dependence, estimators, reporting. **Does not transfer**: references and thresholds
  across radiators, gases or gains.

## Common misconceptions and failure modes

- **A rejection without its momentum, efficiency, layer count, species pair and conditions.** One number at one
  momentum, without its efficiency, layer count, species pair and run conditions, can be neither compared nor
  extrapolated.

## Deliverables

- Radiator type and material; for regular foils `l1`, `l2` and count; for fibre or foam the density, nominal (and any tuned)
  fibre diameter and radiator thickness; tuned equivalent `l1`, `l2`, `N_f` wherever used, with the momenta compared
  with data, agreement measure and value at each, and validity range (outside it: the measured onset curve, else `out-of-range`);
  `gamma_thr`, `gamma_sat` and their formula set; gas, its xenon fraction and
  pressure; layer count and gas thickness per layer; field, rate (occupancy) and track source.
- Estimator, its inputs (charge, threshold, slices, path length) and any requirement it imposes.
- Rejection with its interval at a stated confidence level and signal efficiency, for a stated species pair, versus
  momentum or `gamma`, with layers on track, samples and purity, and the closure and negative-control statuses.
- The onset curve from data (observable, fit form), with its samples and `gamma` ranges and the `gamma` values taken
  as the end of its rise and the start of its plateau.
- Calibration order, conditions ranges (gain, xenon pressure, temperature) and the reference version used.

## Tool hooks

- **Inputs**: per hit, layer, deposit (keV, gain-calibrated), path length (cm), optional slice charges; per track,
  momentum or rigidity and charge, and run conditions (gain, xenon pressure, temperature); references per species, layer and momentum or `gamma` bin, with conditions range;
  per radiator `gamma_thr` and `gamma_sat` with their formula set (analytic or practical, one for both), or the
  measured onset curve with its `gamma` range.
- **Outputs**: per track, log-likelihood ratio per hypothesis pair and layers used; per sample, signal and background
  efficiency with binomial intervals at a stated confidence level, and rejection versus momentum or `gamma`.
- **Conventions**: signal efficiency fixed before the background is counted; rejection = 1 / background efficiency.
- **Closure test**: references built on one half of the control samples; in every momentum or `gamma` bin the
  disjoint half's signal efficiency interval must contain the target, with half-width at most a stated tolerance (for
  example `0.25 (1 - eps_target)`; fixed before the test, at most this unless the record justifies more, and
  reported), and its background efficiency must lie in the reference half's interval, with at
  least a stated count (for example 10); a bin short of either is `inconclusive`, and the check
  passes only if no bin fails, at most a stated share (fixed in advance, for example 0.3) is inconclusive and at
  least one bin is conclusive.
- **Negative control**: two species in one `gamma` bin, scored with `gamma`-binned references (rebin a copy of
  momentum-binned ones, else report `inapplicable`; electrons and muons at equal `beta gamma`,
  muons radiator-first (cosmic ones selected by flight direction, arXiv:1709.02743 p. 46), matched in angle and conditions, most probable signals agreeing, p.
  47, sec. 11): at the electron working point of that copy (version recorded), the matched muons' efficiency
  (rejection `1 / eps_s`, not 1) minus that of disjoint electrons of the bin must have an interval holding 0, fixed
  in advance (a simulated bremsstrahlung difference is only reported beside a failure: a momentum-using estimator
  reproduces it), half-widths within the closure tolerance (else `inconclusive`), bins combined as in the closure
  test; an inconclusive or `inapplicable` control is reported as not done, claiming no momentum independence; a pass covers only the copy tested;
  a separation means the estimator uses momentum or mismatched references, not TR.
- **Statuses**: per track and hypothesis `below-onset` (`gamma < gamma_thr` of the recorded set, or below the onset curve's rise),
  `TR-saturated` (`gamma > gamma_sat`, or on its plateau); `gamma` from momentum, or rigidity and charge, and the
  hypothesis mass; per track `ok`, `insufficient-layers`, `conditions-mismatch` (run conditions outside the
  references' range); per track, and per hypothesis for `gamma`-binned references, `out-of-range` (outside the
  references, or outside the tuned radiator's validity range); per check `passed`, `failed`, `inconclusive` (too few events or too wide an interval),
  `inapplicable`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Emission, `gamma` scaling, formation length | arxiv_1709.02743, arxiv_1702.06473 | pdg_2025_passage-of-particles-through-matter, arxiv_1111.4188 | arxiv_1108.4838 | gap | gap | gap |
| Radiators: threshold, saturation, irregular | arxiv_1709.02743, arxiv_1702.06473 (irregular radiators; threshold, saturation: gap) | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265, arxiv_physics_0402131 | arxiv_1706.10182, pdg_2025_particle-detectors-at-accelerators; arxiv_2201.07901 (proposal, abstract only) | gap | gap | gap |
| Self-absorption, Xe conversion, build-up | arxiv_1702.06473 | arxiv_1111.4188, arxiv_astro-ph_0608641, pdg_2025_particle-detectors-at-accelerators | arxiv_1706.10182 | gap | gap | gap |
| Time profile | arxiv_1709.02743 | arxiv_physics_0402131 | gap | gap | gap | gap |
| Clusters, tracklets, hits on track | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Estimators | arxiv_1709.02743, arxiv_1109.5925 | arxiv_astro-ph_0608641, arxiv_1111.4188, arxiv_physics_0402131, pdg_2025_particle-detectors-at-accelerators | arxiv_1706.10182 | gap | gap | gap |
| Ionization under TR, simulation | gap | arxiv_1111.4188, arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | gap | gap |
| Response calibration | arxiv_1709.02743 | [gas gain](in-situ-calibration-methods.md#gas-gain-equalization) | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap |
| Reporting rejection versus `gamma` | arxiv_1709.02743 (Fig. 43) | arxiv_astro-ph_0608641 (Figs. 15, 20) | gap: arxiv_1706.10182 gives no efficiency | gap | gap | gap |
| Architectures | arxiv_1111.4188 | arxiv_1111.4188 (sec. 4.4), pdg_2025_particle-detectors-at-accelerators | arxiv_1706.10182, arxiv_1111.4188 | gap | gap | gap |
| Hadron separation | gap with TR: a stated need at TeV (arxiv_1901.11265, arxiv_2201.07901); `dE/dx`: arxiv_1709.02743 | pdg_2025_particle-detectors-at-accelerators, arxiv_1111.4188, arxiv_1901.11265 | gap | gap | gap | gap |
| Lorentz factor of nuclei | gap: no collider source read (arxiv_1111.4188 sec. 3.4.1, p. 15: no beams of heavy elements at `gamma ~ 1e5`) | gap for a measurement: beam tests calibrate (arxiv_0808.1718) or test radiators with `Z = 1` at `gamma ~ 1e5` and boron nuclei, setting not stated (arxiv_1111.4188 sec. 3.4.1, Figs. 12-13) | arxiv_1108.4838; arxiv_0808.1718 (relativistic rise; TR negligible below ~1 TeV/n, p. 11) | gap | gap | gap |
| Silicon TR energy and angle | gap | pdg_2025_particle-detectors-at-accelerators, arxiv_1901.11265, arxiv_1111.4188 | gap: proposed (arxiv_1111.4188) | gap | gap | gap |

`gap`: not found in the sources read. GND and NUC: no TRD surveyed. UGD and the filing of arxiv_1111.4188 Table 1 (p. 14) TRDs: as its sec. 1 (p. 1)
groups them: accelerator-based as COL (collider, secs. 4.1-4.3, p. 17) or FXT (fixed target, sec. 4.4, p. 30)
where the source says which, astro-particle as SPC (sec. 4.5, p. 31); none is called underground or neutrino there, and a
row whose beam no source read states is filed in no cell (example below).

<!-- example: a listed TRD and how this page files it -->
- NOMAD TRD: foils, Xe-CO2, 9 layers, 150 cm, pion rejection 1000 (arXiv:1111.4188 Table 1, p. 14); accelerator-based
  in sec. 1 (p. 1); no source read states its beam or environment, so no UGD cell cites it.
<!-- /example -->

## Citations

Each source was read in its arXiv e-print (PDG: the 2025 review PDFs) on 2026-11-21/22, except arXiv:2201.07901, read
in its abstract only; cells that link another reference rest on that reference's sources.
