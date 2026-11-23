# Cherenkov Imaging Variants and Photosensors

Fills the gaps around the RICH/TRD/`dE/dx`/TOF treatment in
[particle identification](particle-identification.md): threshold and differential counters, DIRC and
time-of-propagation (TOP) detectors, water/ice/aerogel/gas/liquid radiators, and the
optical and radiation sensors and light-transport elements shared by most detectors
(PMT, SiPM, APD, hybrid photodetectors, microchannel plates, gaseous photon detectors,
wavelength shifters, fibers, light guides). Physics of emission and yield is in
[signal formation and readout](signal-formation-and-readout.md); `<plugin root>/skills/hep-detector/scripts/cherenkov_angle.py` evaluates the
RICH design relations. Ring reconstruction is in
[Cherenkov ring reconstruction](cherenkov-ring-reconstruction.md), DIRC and TOP reconstruction in
[DIRC and TOP reconstruction](dirc-and-time-of-propagation-reconstruction.md). Environment codes used here: COL
collider; FXT fixed target and test beam; UGD underground, neutrino and rare-event; GND ground-based cosmic-ray and
gamma-ray arrays.

## Cherenkov PID variants

**Threshold counters.** A particle emits light only if `beta > 1/n`, i.e.
`p > p_th = m c/sqrt(n^2 - 1)`. Using two radiators (or gas pressure) sets thresholds
that separate species by which counter fires. The **turn-on curve** `epsilon(p)` rises
over a range set by photon statistics (few photoelectrons) rather than a step; the
efficiency near threshold is `1 - exp(-N_pe(p))` (Poisson; approximate for a smooth
`N_pe`). Systematics: pressure/temperature/index stability (`n` shifts move the
threshold), mirror/window aging, noise (dark counts) versus low `N_pe`, and the
photodetector's excess noise, which lowers the effective `N_pe` (PDG RPP 2025, sec. 35.5).
The rejection of the below-threshold species is set by the light it produces anyway, not
by `1 - exp(-N_pe)` alone: delta rays and scintillation in the radiator, decay to an
above-threshold particle, Cherenkov light in the radiator wrapping, interactions in
upstream material, and overlapping or accidental tracks (sec. 35.5;
arXiv:hep-ex/9805001, p. 10).

**Differential counters.** Select a Cherenkov angle (`cos theta_C = 1/(n beta)`) with
an optical system so that only a narrow velocity band gives light; excellent for a
particular momentum, with the acceptance and alignment of the angular selection
dominating the systematic. They exist in one environment, high-momentum beam lines (FXT), with very limited
acceptance (pdg_2025_particle-detectors-at-accelerators sec. 35.5, p. 22); no source found one elsewhere.
<!-- example: named apparatus -->NA62 (FXT) identifies the kaons of its beam with a differential Cherenkov
counter, KTAG (arXiv:1809.04026 sec. 1, p. 2).<!-- /example -->

**DIRC (detection of internally reflected Cherenkov light).** Light trapped by total internal reflection in a
solid radiator bar is imaged after transport in position and, from the long paths, in time (PDG RPP 2025,
sec. 35.5; arXiv:hep-ex/0010068, p. 3); **time-of-propagation (TOP)** detectors emphasize timing for the imaging
itself. Multiple photon paths per pixel, chromatic correction by timing, the start time and the
timing-position likelihood per hypothesis are in
[DIRC and TOP reconstruction](dirc-and-time-of-propagation-reconstruction.md).

**RICH** (imaging in a gas or aerogel radiator with mirror or proximity focusing): contributions to the per-photon
angle resolution are emission point (radiator thickness), chromatic (dispersion `dn/d lambda`), optical
aberration and pixelization, and per track division by `sqrt(N_pe)`
([particle identification](particle-identification.md)). Ring finding, track-photon association, the likelihood
per hypothesis and its background term are in
[Cherenkov ring reconstruction](cherenkov-ring-reconstruction.md). **Radiators**: aerogel (intermediate
`n`, Rayleigh scattering), gas (low `n`, high threshold, high `beta`), liquid, water,
and ice (large volumes, optics dominated by absorption/scattering, e.g.
[neutrino astronomy](neutrino-astronomy.md)).

### Distinctive but generalizable reconstruction and performance features (Cherenkov imaging)

- **Topology**: rings, arcs, or time-resolved photon patterns (a dense image with few
  photons: Poisson limited).
- **Inverse problem**: velocity `beta` (and species, given `p`) from a partial
  ring; degeneracies: photon-path ambiguity (DIRC/TOP), emission-point vs chromatic
  vs aberration, background photons.
- **Objects**: photon hit, ring/arc, track-level angle, likelihood per hypothesis.
  **Informative residual**: photon Cherenkov-angle residual versus track (per-photon
  distribution centered and its width, with the background pedestal), and the
  per-track angle residual versus momentum.
- **Scaling** (approximate; PDG Review of Particle Physics, "Passage of particles
  through matter", Cherenkov radiation, and "Particle detectors at accelerators",
  Cherenkov detectors): photoelectron yield `N_pe = N_0 L z^2 sin^2 theta_C` for radiator
  length `L` and detector figure of merit `N_0` (cm^-1; it folds in the photon yield,
  optics and quantum efficiency), from a raw emission of about `490 z^2 sin^2 theta_C`
  photons/cm between 400 and 700 nm; per-track angle resolution
  `sigma_theta = sqrt(sigma_photon^2/N_pe + sigma_trk^2)`, where `sigma_trk` is the
  contribution of the track direction and other terms common to all photons, which
  does not average down with `N_pe`; species separation
  `N_sigma = Delta theta_C / sigma_theta ≈ |m_1^2 - m_2^2| / (2 p^2 tan theta_C sigma_theta)`
  (approximate: ultrarelativistic, `beta ≈ 1`; single-measurement convention of
  [performance metrics](performance-metrics-and-residual-diagnostics.md)) falls as `1/p^2`
  ([particle identification](particle-identification.md)); the angle saturates as `beta -> 1`.
- **Conventions**: efficiency/mis-ID at a stated likelihood-difference cut; separation
  power in `N_sigma` (Gaussian approximation, check with the actual distribution).
- **Tails**: wrong-ring association, low-`N_pe` tracks, background-dominated events.
- **Dependence**: refractive index (temperature/pressure/composition/dose), aerogel
  transparency, mirror alignment, photosensor gain/timing/aging, occupancy.
- **Data sample**: at accelerators, decays with kinematic PID (`D^* -> D pi`,
  `K_s -> pi pi`, `Lambda -> p pi`, `phi -> K K`), and `mu` from `Z`/`J/psi`. In a large
  water-Cherenkov volume (UGD): cosmic-ray muons, muon-decay (Michel) electrons and `pi^0`
  produced in the detector (PDG RPP 2025, sec. 36.3.1.2; arXiv:1307.0162, sec. 1;
  [noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors)).
  In an imaging air-Cherenkov camera (GND): muon rings, which calibrate the telescope
  response (sec. 36.2.2; [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md)).
  A sample for space-borne counters is not given here (a gap).
- **Transfers**: photon-counting likelihood to any counting/imaging device; index/pressure
  monitoring to threshold counters; **does not transfer**: the specific dispersion terms.

## Photosensors and light transport

| Sensor | Gain/mechanism | Strengths | Characteristic systematics |
|---|---|---|---|
| Photomultiplier tube (PMT) | dynode chain, gain `10^5-10^7` | low noise, large area, fast | gain drift, afterpulses, magnetic-field sensitivity, transit-time spread, single-photoelectron (SPE) response |
| Silicon photomultiplier (SiPM) | Geiger-mode pixel array | compact, magnetic-field tolerant, photon counting | dark counts (temperature, dose), optical crosstalk, afterpulse, saturation (finite pixels) |
| Avalanche photodiode (APD) | linear avalanche in silicon | high `QE`, compact | gain/temperature sensitivity, excess noise |
| Hybrid photodetector | photocathode + silicon anode | good SPE resolution | high-voltage requirements, magnetic-field sensitivity |
| Microchannel plate (MCP) | channel electron multiplier | very fast, position sensitive | aging, ion feedback, rate/gain droop |
| Gaseous photon detector | photoionization + gas gain | large area, magnetic-field tolerant | quantum efficiency (window/gas), aging, ion backflow |

Mechanisms and monitoring of SiPM, MCP-PMT and gas ageing: [radiation and ageing effects](radiation-and-aging-effects.md).

**Response model.** `N_pe ~ Poisson(N_gamma * eps_coll * QE)`; gain per photoelectron
fluctuates (Polya/excess-noise `F`); SiPMs add crosstalk and afterpulsing as
compound-Poisson terms (optical crosstalk is a branching process: with `lambda` the mean
number of secondaries per avalanche, `lambda = -ln(1 - P_ct)`, a primary gives mean
`1/(1-lambda)` cells, variance `lambda/(1-lambda)^3`); a dark count rate `DCR` contributes a mean
`DCR * gate` *and* a variance, so pedestal subtraction removes only the mean;
SiPM saturation `N_cells (1 - exp(-N_pe/N_cells))` makes the response nonlinear
([front-end waveform processing](front-end-waveform-processing.md#photosensor-readout));
timing has transit-time spread and jitter ([timing detectors](timing-detectors.md)).
SiPM gain `G = (C_d + C_q)(V_bias - V_off)/e` (pixel and quench capacitances; the
turn-off voltage `V_off` is usually within 1 V of the breakdown voltage, so
`G ≈ C (V_bias - V_bd)/e`); `PDE = FF * QE * P_T` (fill factor, quantum efficiency,
Geiger-trigger probability, which depends on the bias and the wavelength) (R. Klanner, NIM A926
(2019) 36, arXiv:1809.04346, eqs. 1-2). APD excess noise for electron injection in the
local model (McIntyre): `F = k M + (1 - k)(2 - 1/M)`, `k` the hole-to-electron ionization
coefficient ratio; dead-space effects make it an overestimate for thin multiplication
regions (J. S. Marsland, arXiv:1102.0132, eq. 1).

**Light transport elements.**
- **Wavelength shifters** absorb short-wavelength (e.g. UV) light and re-emit at longer
  wavelength (a second stochastic step, with trapping efficiency and self-absorption);
  spectra of emitter, shifter, and sensor `QE` must overlap.
- **Fibers and light guides** transport light with attenuation
  `exp(-L/lambda_att)` and geometric (Liouville/etendue) limits: coupling area and
  acceptance angle cap the collected fraction; **optical coupling** (grease, gaps) sets
  an interface efficiency, a source of channel-to-channel nonuniformity.
- **Reflectors and coatings** age; reflectivity changes with humidity, radiation, and
  time.

**Calibration.** Single-photoelectron peak (gain, pedestal, noise threshold), LED/laser
pulsing (linearity, timing, monitoring of gain drift), radioactive sources and cosmic
muons (light yield, uniformity), and in-situ standard candles (electron/muon light
yield in detector volume) ([calibration and alignment](calibration-and-alignment.md)). Track *monitoring
time series* (gain versus temperature/dose) rather than a single constant.

**Magnetic fields and immersion.** PMT gain changes with orientation even in the geomagnetic field; a
high-permeability shield is often needed, while fine-mesh PMTs work in strong fields aligned with the tube
axis (pdg_2025_particle-detectors-at-accelerators sec. 35.2.1.1, p. 5). Large immersed arrays (UGD) wrap each tube
or compensate the field with coils around the volume, measure the residual field at the sensor positions, pot the
tubes against water or oil and may need covers against an implosion chain reaction
(pdg_2025_particle-detectors-for-non-accelerator-physics sec. 36.3.1, p. 12; arXiv:1307.0162 sec. 2.3.2, p. 5).
In a spectrometer field (COL) the sensor type is chosen for it (arXiv:2008.06251 sec. 2.2.2, p. 4). Both enter
the per-pixel efficiency of the ring likelihood.
<!-- example: named apparatus and their numbers -->
Super-Kamiokande (UGD): 26 sets of coils; a 100 mG field along the dynode plate of a 20-inch PMT lowers the hit
collection efficiency by 10%, asymmetrically; residual field 32 mG on average at 458 PMT positions, 2% in collection
efficiency (arXiv:1307.0162 sec. 2.3.2, pp. 5-6). Belle II ARICH (COL): hybrid avalanche photodetectors for 1.5 T
(arXiv:2008.06251 sec. 2.2.2, p. 4).
<!-- /example -->

**Night-sky background** reaches only sensors that look at the sky (GND, imaging air-Cherenkov cameras; enclosed
detectors are dark): SiPMs tolerate moonlight but their red sensitivity raises the night-sky rate unless filtered,
and the exposure per image is kept to a few ns against pile-up
(pdg_2025_particle-detectors-for-non-accelerator-physics sec. 36.2.2, p. 8;
[imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md)). Even with blue-sensitive PMTs behind large
mirrors the night-sky rate per pixel stays high (same page). In a hit model it is a per-pixel background
rate.

### Features (photosensors)

- **Natural objects** and **Conventions**: not stated here for photosensors (a gap); those of Cherenkov imaging are in
  the block above, those of timing in [timing detectors](timing-detectors.md).
- **Topology**: pulses per channel (counts, time, amplitude), possibly a waveform.
- **Inverse problem**: `N_gamma`, arrival time from a pulse with gain and noise
  fluctuations and detection efficiency; degeneracy: gain vs light yield vs coupling.
- **Informative residual**: SPE spectrum, gain and DCR vs time, LED-linearity curve,
  light-yield vs position.
- **Scaling**: `sigma/N ≈ sqrt(F/N_pe)`; timing from the first photoelectrons `~ tau_decay/N_pe`
  for a negligible rise time, closer to `sqrt(tau_rise tau_decay/N_pe)` with a finite one
  (`tau_decay`, `tau_rise` the emission decay and rise times, not the dead time `tau_d`;
  [timing detectors](timing-detectors.md)).
- **Tails**: afterpulses, crosstalk clusters, dark-count pileup, saturation.
- **Dependence**: temperature (SiPM), magnetic field (PMT), dose, rate.
- **Data sample**: LED/laser, SPE, MIPs, mono-energetic lines.
- **Transfers**: to every light-based detector (calorimeters, TOF, RICH, neutrino).

## Common misconceptions and failure modes

- **Using the Gaussian `N_sigma` for PID with few photons.** Distributions are
  Poisson-non-Gaussian; use the likelihood or ROC ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **Neglecting `n(T, P, lambda)`.** Small index drift shifts angles and thresholds.
- **DIRC/TOP ambiguities ignored.** Multiple photon paths produce a structured
  background if not modeled in the likelihood.
- **SiPM dark counts and crosstalk treated as Gaussian noise.** They are correlated and
  non-Gaussian; model as compound Poisson.
- **Ignoring dose-dependent aging** of scintillators, WLS fibers, and mirrors (scintillator and WLS
  mechanisms, including ageing without dose: [radiation and ageing effects](radiation-and-aging-effects.md)).
- **Assuming the gain is constant across an SPE calibration** interval.

## Deliverables

- The radiator/sensor response model and the per-track/per-photon resolution
  decomposition.
- Threshold turn-on or ring-angle likelihood with the background model.
- SPE, gain, dark count, crosstalk, and afterpulse calibration and monitoring plan.
- The optical calibration (attenuation, coupling, reflectivity) and its time dependence.
