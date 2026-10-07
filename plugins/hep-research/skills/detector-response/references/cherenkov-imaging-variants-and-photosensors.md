# Cherenkov Imaging Variants and Photosensors

Fills the gaps around the RICH/TRD/`dE/dx`/TOF treatment in
[particle identification](particle-identification.md): threshold and differential counters, DIRC and
time-of-propagation (TOP) detectors, water/ice/aerogel/gas/liquid radiators, and the
optical and radiation sensors and light-transport elements shared by most detectors
(PMT, SiPM, APD, hybrid photodetectors, microchannel plates, gaseous photon detectors,
wavelength shifters, fibers, light guides). Physics of emission and yield is in
[signal formation and readout](signal-formation-and-readout.md); `<plugin root>/skills/detector-response/scripts/cherenkov_angle.py` evaluates the
RICH design relations.

## Cherenkov PID variants

**Threshold counters.** A particle emits light only if `beta > 1/n`, i.e.
`p > p_th = m c/sqrt(n^2 - 1)`. Using two radiators (or gas pressure) sets thresholds
that separate species by which counter fires. The **turn-on curve** `epsilon(p)` rises
over a range set by photon statistics (few photoelectrons) rather than a step; the
efficiency near threshold is `1 - exp(-N_pe(p))` (Poisson; approximate for a smooth
`N_pe`). Systematics: pressure/temperature/index stability (`n` shifts move the
threshold), mirror/window aging, noise (dark counts) versus low `N_pe`.

**Differential counters.** Select a Cherenkov angle (`cos theta_C = 1/(n beta)`) with
an optical system so that only a narrow velocity band gives light; excellent for a
particular momentum, with the acceptance and alignment of the angular selection
dominating the systematic.

**DIRC (detection of internally reflected Cherenkov light).** Light is trapped by
total internal reflection in a solid radiator bar and carried to a photosensor array
at the end: the ring is imaged after propagation as a pattern of hit positions,
requiring a reconstruction of the angle from position and (in TOP) **time of
propagation**. **TOP** detectors add the photon arrival time, breaking degeneracies
in the path. Distinctive features: **multiple photon paths** with the same detected
position (left/right bounces, mirror-image "ambiguities") that overlap in the
image, correction for **chromatic dispersion** through timing, and the need to calibrate
the bar's optical quality, surface reflectivity, and the photosensor's timing. PID by a
**timing-position likelihood** per hypothesis.

**RICH** (imaging in a gas or aerogel radiator with mirror or proximity focusing): ring
finding, track-photon association, likelihood PID; contributions to the per-photon
angle resolution: emission-point (radiator thickness), chromatic (dispersion `dn/d lambda`),
optical aberration, pixelization, and (per track) division by `sqrt(N_pe)`
([particle identification](particle-identification.md)). Background hits from other tracks, delta rays,
and noise enter the likelihood as a flat term. **Radiators**: aerogel (intermediate
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
- **Scaling**: `sigma_track = sigma_photon/sqrt(N_pe)`; species separation
  `N_sigma = Delta theta_C / sigma_theta ≈ |m_1^2 - m_2^2| / (2 p^2 tan theta_C sigma_theta)`
  (approximate: ultrarelativistic, `beta ≈ 1`) falls as `1/p^2`
  ([particle identification](particle-identification.md)); the angle saturates as `beta -> 1`.
- **Conventions**: efficiency/mis-ID at a stated likelihood-difference cut; separation
  power in `N_sigma` (Gaussian approximation, check with the actual distribution).
- **Tails**: wrong-ring association, low-`N_pe` tracks, background-dominated events.
- **Dependence**: refractive index (temperature/pressure/composition/dose), aerogel
  transparency, mirror alignment, photosensor gain/timing/aging, occupancy.
- **Data sample**: decays with kinematic PID (`D^* -> D pi`, `K_s -> pi pi`,
  `Lambda -> p pi`, `phi -> K K`), and `mu` from `Z`/`J/psi`.
- **Transfers**: photon-counting likelihood to any counting/imaging device; index/pressure
  monitoring to threshold counters; **does not transfer**: the specific dispersion terms.

## Photosensors and light transport

| Sensor | Gain/mechanism | Strengths | Characteristic systematics |
|---|---|---|---|
| Photomultiplier tube (PMT) | dynode chain, gain `10^5-10^7` | low noise, large area, fast | gain drift, afterpulses, magnetic-field sensitivity, transit-time spread, single-photoelectron (SPE) response |
| Silicon photomultiplier (SiPM) | Geiger-mode pixel array | compact, magnetic-field tolerant, photon counting | dark counts (temperature, dose), optical crosstalk, afterpulse, saturation (finite pixels) |
| Avalanche photodiode (APD) | linear avalanche in silicon | high `QE`, compact | gain/temperature sensitivity, excess noise |
| Hybrid photodetector | photocathode + silicon anode | good SPE resolution | high-voltage requirements |
| Microchannel plate (MCP) | channel electron multiplier | very fast, position sensitive | aging, ion feedback, rate/gain droop |
| Gaseous photon detector | photoionization + gas gain | large area, magnetic-field tolerant | quantum efficiency (window/gas), aging, ion backflow |

**Response model.** `N_pe ~ Poisson(N_gamma * eps_coll * QE)`; gain per photoelectron
fluctuates (Polya/excess-noise `F`); SiPMs add crosstalk and afterpulsing as
compound-Poisson terms; a dark count rate `DCR` contributes an offset `DCR * gate`;
timing has transit-time spread and jitter ([timing detectors](timing-detectors.md)).

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

### Features (photosensors)

- **Topology**: pulses per channel (counts, time, amplitude), possibly a waveform.
- **Inverse problem**: `N_gamma`, arrival time from a pulse with gain and noise
  fluctuations and detection efficiency; degeneracy: gain vs light yield vs coupling.
- **Informative residual**: SPE spectrum, gain and DCR vs time, LED-linearity curve,
  light-yield vs position.
- **Scaling**: `sigma/N ≈ sqrt(F/N_pe)`; timing `~ 1/sqrt(N_pe)`.
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
- **Ignoring dose-dependent aging** of scintillators, WLS fibers, and mirrors.
- **Assuming the gain is constant across an SPE calibration** interval.

## Deliverables

- The radiator/sensor response model and the per-track/per-photon resolution
  decomposition.
- Threshold turn-on or ring-angle likelihood with the background model.
- SPE, gain, dark count, crosstalk, and afterpulse calibration and monitoring plan.
- The optical calibration (attenuation, coupling, reflectivity) and its time dependence.
