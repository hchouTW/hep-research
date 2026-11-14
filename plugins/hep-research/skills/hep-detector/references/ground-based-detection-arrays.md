# Ground-Based Detection Arrays: Surface Detectors and Fluorescence

Covers the two complementary techniques for observing an extensive air shower (see
[extensive-air-showers.md](extensive-air-showers.md)) from the
ground - sampling it at one depth with a surface array, or imaging its full
longitudinal development with fluorescence telescopes - and the hybrid combination
that dominates modern ultra-high-energy cosmic-ray observatories. Detector-technology
material that is not air-shower-specific (photomultiplier response, timing
electronics) is out of scope here; this file is about what each technique measures
and how that becomes an energy and a composition estimate.

## Surface detector arrays

A surface array is a grid of individual detector stations - scintillator panels (still
used, for example as an upper layer on water-Cherenkov stations added to improve the
mass-composition determination), and in water-Cherenkov form (used because water is cheap, robust outdoors, and
efficiently converts shower particles including a good fraction of the muon and
electromagnetic content into detectable Cherenkov light) a tank of water instrumented
with photomultipliers - spaced over a wide area (hundreds to thousands of meters
between stations, chosen to match the target energy range: bigger spacing for higher
energy, since the shower footprint grows with energy). Each station records a signal
(particle density or integrated charge) and an arrival time.

- **Arrival direction** comes from the relative timing of the shower front across
  stations, fit to a shower-front shape (commonly a plane or a slightly curved cone
  centered on the shower axis); timing resolution per station directly sets angular
  resolution.
- **Energy** comes from the signal size at a species- and zenith-angle-independent
  *reference distance* from the reconstructed shower core - chosen (from simulation)
  as the distance at which the signal interpolated by the lateral-distribution fit is
  least sensitive to the assumed lateral-distribution shape; that distance is set
  mainly by the array spacing (station geometry), with shower-to-shower fluctuations
  a secondary consideration, so that the density-to-energy conversion is as
  model-independent as practical. This is a direct application of shower
  universality (see [extensive-air-showers.md](extensive-air-showers.md)):
  the conversion still carries residual hadronic-model and composition dependence,
  which must be calibrated against an independent energy estimator (fluorescence, in
  a hybrid detector) rather than assumed from simulation alone.
- **Zenith-angle dependence (attenuation)**: a more inclined shower traverses more
  atmosphere before reaching the array, attenuating its electromagnetic content more
  than its muon content (which is more penetrating). The standard correction is the
  **constant-intensity-cut method**: since the underlying cosmic-ray flux is
  isotropic to good approximation at these energies, the signal at a fixed rate
  (equal number of events above threshold, integrated over exposure) should be
  independent of zenith angle absent attenuation - so the observed zenith dependence
  of a fixed-rate signal directly calibrates the atmospheric attenuation curve, without
  needing a shower simulation to normalize it.
- **Duty cycle is effectively 100%**: a surface array runs continuously regardless of
  weather or moonlight, unlike fluorescence detectors below. This is why an array is
  the workhorse for spectrum measurements (above the energy of full trigger efficiency for the
  zenith range used, exposure is straightforward: array area times live time times the solid-angle
  factor; below it the composition-dependent trigger efficiency enters) and
  why hybrid designs use fluorescence for calibration rather than as the primary
  exposure-defining detector.

### Surface-array event reconstruction

- **Station signal scale.** Each station's signal is expressed in units of a reference
  muon signal (the vertical through-going muon in a water-Cherenkov tank, the
  minimum-ionizing peak in a scintillator), calibrated continuously from the
  atmospheric-muon background, so the scale follows ageing and temperature without a
  separate run. That background is omnidirectional, so its peak is related to the
  reference unit by a fixed ratio measured separately, not equal to it.
- **Saturation.** Stations near the core can saturate. A low-gain channel or a fit to the
  undistorted part of the pulse recovers part of the range; beyond that the signal is a
  lower bound and enters the lateral-distribution fit as censored, not as a measured value.
- **Station and hit selection** (three schemes read, cited below). In the sparse station array
  read, an offline trigger keeps events mainly on a coincidence of adjacent stations within the
  propagation time of the shower front; stations whose times do not fit the estimated front are
  removed as random, and a search of each trace for time-compatible peaks rejects random-muon
  signals. A fiducial cut keeps only events whose highest-signal station has all its operating
  neighbours, for a reliable core and a simple exposure; a looser cut may serve direction
  studies. In the two dense arrays read (one hit per photosensor or unit), hits are first cut by
  a time window (around the trigger in one; in the other a 400 ns window and a 100 m circle),
  without abnormal units and known-bad hits (afterpulses after a high-charge hit, crossing
  patterns unlike real light, charges above the calibrated range); core and direction are
  fitted, hits far in time from the fitted plane (or far from the core) are dropped, and the fit
  is repeated. Final counts or gamma/hadron variables use the hits near the last plane: one
  accidental muon can make a gamma-ray shower look hadronic.
- **Core and size fit.** The core position and the signal at the reference distance are
  fitted together with a lateral-distribution function, using Poisson-like statistics for
  small signals and including stations that did not trigger (they bound the footprint, as
  unhit channels do in [photon likelihood reconstruction](photon-likelihood-reconstruction.md#the-per-channel-likelihood)).
  The station-signal model includes shower-to-shower and particle-sampling fluctuations,
  which set the per-event uncertainty of the size and of the energy; that uncertainty also
  includes the uncertainty of the assumed lateral-distribution shape, which the
  reference-distance choice above keeps small but not zero.
- **Station times.** The arrival-direction fit (above) weights each station's start time by
  a time-variance model: the first particle's arrival time fluctuates more far from the core,
  where the shower front is thicker, and less when many particles are sampled.
- **Muon and electromagnetic components.** Separating them needs a second response:
  dedicated shielded or buried muon detectors, layered detectors with different relative
  response to muons and to electrons and photons, or the time structure of the station
  signal (muons arrive earlier and sharper). Each separation is a model-dependent
  decomposition with its own calibration.

<!-- example: source citation -->
Sparse array: the Pierre Auger surface detector (T4 physics trigger, time cuts keeping 99% of
stations with a shower signal, 6T5 fiducial cut; The Pierre Auger Collaboration, Nucl. Instrum.
Methods A 798 (2015) 172, arXiv:1502.01323, sec. 11.1). Dense arrays: HAWC (hits from -150 to
+400 ns around the trigger; second fit on hits within 50 ns of the first plane; compactness and
PINCness from hits within 20 ns of the second; Abeysekara et al. (HAWC), ApJ 843 (2017) 39,
arXiv:1701.01778, secs. 2.3 and 2.7, Table 1) and LHAASO-KM2A (second selection: hits within
[-30, 50] ns of the plane and 200 m of the core; Aharonian et al. (LHAASO), Chin. Phys. C 45
(2021) 025002, arXiv:2010.06205, sec. 3 opening).
<!-- /example -->

**Check:** The hit or station selection, the station signal scale, the treatment of saturated
and non-triggered stations, the station time-variance model used in the direction fit, and the
per-event uncertainty of the size estimator are stated.

## Fluorescence detectors

As a shower's charged particles ionize atmospheric nitrogen, the nitrogen fluoresces,
emitting isotropic UV light proportional to the local ionization energy deposit -
which fluorescence telescopes (segmented mirrors with pixelated photomultiplier
cameras) image from the side, reconstructing the shower's energy-deposit profile `dE/dX(X)` directly, essentially independent of any hadronic interaction model, since the
fluorescence yield per unit deposited energy is a well-measured property of air
rather than of the shower physics.

- **Calorimetric energy measurement**: integrating the reconstructed `dE/dX` profile
  over depth gives the total electromagnetic energy deposited, and adding a
  simulation-based correction for the "invisible energy" carried away by muons and
  neutrinos (which is why fluorescence energy is not fully model-independent, but the
  correction is a much smaller and better-constrained effect than a surface array's
  full density-to-energy conversion) gives the primary energy - the reason a
  fluorescence measurement is treated as the more direct energy calibration in a
  hybrid design.
- **`X_max` is read directly off the fitted longitudinal profile** (Gaisser-Hillas,
  see [extensive-air-showers.md](extensive-air-showers.md)), making
  fluorescence the primary composition-measuring technique among ground-based methods.
<!-- example: experiment-specific illustration -->
- **Duty cycle is roughly 10-15%**: fluorescence light is faint UV, requiring dark,
  clear, moonless nights, so only a fraction of showers that trigger a co-located
  surface array are also seen by fluorescence. This asymmetry is exactly what a
  **hybrid** design (fluorescence plus surface array, e.g. Pierre Auger Observatory,
  Telescope Array) exploits: use the small, high-quality, calorimetric-energy hybrid
  subsample to calibrate the surface array's density-to-energy conversion, then apply
  that calibration to the full, 100%-duty-cycle surface-only dataset for the spectrum
  measurement, tying the absolute energy scale to the fluorescence calorimetric
  measurement's own systematic uncertainty (in the published Auger budget, 14% in total, the
  photometric calibration, with its absolute, relative and wavelength terms, is the largest term,
  9.9%, with the atmosphere 3.4-6.2% and the
  fluorescence yield 3.6%; Dawson for the Pierre Auger Collaboration, PoS ICRC2019 (2019) 231, opened
  2026-10-14; take the budget from the experiment's energy-scale paper).
<!-- /example -->

### Fluorescence geometry and profile reconstruction

- **Pixel signal and pixel selection.** In the scheme cited below, the baseline is subtracted
  from each pixel's ADC trace, the noise taken from the variance of early signal-free bins, and
  counts converted to photons at the aperture by calibration. Each triggered pixel's trace is
  scanned for the pulse start and stop that maximize the signal-to-noise ratio; only pulses with
  a ratio of at least 5 enter the geometry fits. The pulse time is the signal-weighted centroid of
  the pulse bins, the charge their sum, with uncertainties from the noise variance and Poisson
  photoelectron fluctuations. For the light profile, each time bin sums the pixels pointing within
  an angle `zeta` of the direction to the shower centre at that time, `zeta` chosen to maximize
  the signal-to-noise ratio; divided by the diaphragm area, this is the light flux at the
  aperture. Light outside the collection angle `zeta`, from the shower's lateral extent, is
  corrected with universal lateral distributions of fluorescence and Cherenkov light.
- **Shower-detector plane.** The pixels on the shower image define, through their
  pointing directions weighted by signal, the plane containing the shower axis and the
  telescope.
- **Axis within the plane.** The arrival time at each pixel against its viewing angle
  `chi_i` in that plane follows `t_i = t_0 + (R_p/c) tan((chi_0 - chi_i)/2)` for a shower at
  the speed of light, where `t_0` is the time the shower front passes the point of closest
  approach, giving the distance of closest approach `R_p` and the axis angle `chi_0`. For short
  or distant tracks the curvature of this relation is weak and `R_p` and
  `chi_0` are degenerate, the main weakness of monocular reconstruction. One surface
  station's time breaks the degeneracy (hybrid reconstruction); a second telescope gives
  the axis as the intersection of two planes (stereo).
- **Profile.** The light at the aperture is converted to energy deposit per depth with the
  atmospheric transmission of the night. The light sources are disentangled: fluorescence light,
  the direct and scattered Cherenkov light that the shower also sends toward the telescope, and
  multiply scattered light. Fluorescence and Cherenkov light are tied to the energy deposit by a
  linear set of equations, solved together by linear least squares; the deposit profile is then
  fitted (see [extensive air showers](extensive-air-showers.md)). Geometry errors propagate
  into both `X_max` and energy, so the event selection usually requires a well-constrained
  geometry and a viewed shower maximum.

<!-- example: source citation -->
These steps follow the reconstruction described for a hybrid observatory (The Pierre Auger
Collaboration, Nucl. Instrum. Methods A 798 (2015) 172, arXiv:1502.01323; pulse
reconstruction, sec. 10.1; light collection, sec. 10.4; lateral-light correction and the joint
linear solution for fluorescence and Cherenkov light, sec. 10.5).
<!-- /example -->

**Check:** Fluorescence events state monocular, hybrid or stereo geometry, the pixel selection
for the light profile, the treatment of Cherenkov light and the atmospheric transmission used,
and the propagation of geometry errors into `X_max` and energy.

## Atmospheric monitoring

Both techniques treat the atmosphere as part of the detector, not as an inert medium:

- **Fluorescence yield** depends on temperature, pressure, and humidity, requiring a
  parameterized yield model as a function of atmospheric conditions rather than a
  single constant.
- **Aerosol content and cloud cover** attenuate the fluorescence and Cherenkov light
  reaching the telescopes and vary hour-to-hour, requiring dedicated
  lidars/monitoring telescopes and per-night (sometimes per-hour) atmospheric
  transparency corrections; observations on nights without adequate monitoring
  coverage are normally excluded rather than corrected with an assumed average.
- **Atmospheric density profile** sets the mapping between altitude and slant depth
  `X` in the Gaisser-Hillas fit, and its seasonal variation is a genuine (not purely
  instrumental) systematic on `X_max` that composition analyses must account for
  when combining data across a full year.

## Muon detectors, radio detection and wide-field gamma-ray arrays

- **Muon detectors** are particle counters shielded by an overburden (soil, rock,
  water) thick enough to absorb the electromagnetic component, so the signal is almost
  entirely muons except near the core of very energetic showers, where some
  electromagnetic particles punch through. The muon-to-electron ratio separates
  muon-poor gamma-ray showers from muon-rich hadronic ones; state the per-counter efficiency, the single-muon resolution, the
  punch-through region excluded and the shielding depth.
- **Radio detection** of air showers measures the coherent radio emission of the
  shower's electromagnetic component (geomagnetic emission dominates in air, Askaryan
  Cherenkov-like emission in dense media). It is calorimetric: the field amplitude is
  proportional to the shower energy and the energy fluence to its square, falling with
  distance as `1/R` and `1/R^2` plus absorption; the arrival direction comes from the
  antenna timing with a curved (hyperbolic) wavefront. Backgrounds are anthropogenic
  and instrument noise, atmospheric effects (lightning, blowing snow) and Galactic
  radio emission at low frequency, and narrow-band and impulsive noise make triggering
  on the radio signal itself a challenge (PDG RPP 2025, sec. 36.3.3).
- **Wide-field ground gamma-ray arrays** (dense water-Cherenkov ponds or tanks, and
  scintillator plus muon-detector arrays at high altitude) observe continuously, day and
  night, over a field of view of about 2 sr. Gamma/hadron separation uses the lateral
  hit pattern (isolated high-charge hits far from the core from penetrating particles of
  hadronic showers, and a less smooth lateral distribution) or the muon content; the background rejection, angular resolution, energy bias and their
  dependence on energy and zenith are the instrument response to state.

<!-- example: experiment-specific illustration -->
Examples (sources opened 2026-10-15): HAWC, 300 water-Cherenkov tanks over 22 000 m^2
at 4100 m, field of view nearly 2 sr, gamma/hadron parameters "compactness" and
"PINCness" from the hit pattern (ApJ 843 (2017) 39, arXiv:1701.01778). LHAASO-KM2A,
5195 scintillator detectors (1 m^2, 15 m spacing) and 1188 water-Cherenkov muon
detectors (36 m^2, under 2.5 m of soil, efficiency above 95%) over 1.3 km^2, field of
view about 2 sr, operating day and night; gamma/hadron cut on `log(N_mu/N_e)`, with
`N_e/N_mu` about 10 for proton and about 1000 for gamma-ray showers, rejection better
than 4e3 above 100 TeV at 48-93% gamma survival (Chin. Phys. C 45 (2021) 025002,
arXiv:2010.06205). The Pierre Auger Observatory upgrade adds radio antennas and 4 m^2
scintillators on its water-Cherenkov stations (PDG RPP 2025, sec. 36.2.1;
arXiv:1604.03637).
<!-- /example -->

### Radio reconstruction

The emission and its scaling are summarized above; this subsection covers how an event is
reconstructed from the antenna signals (background review: Huege, Phys. Rep. 620 (2016) 1; the
review does not give the vector effective length, the iteration of field and direction, or the
signal power lost to transmitter removal).

- **Voltage to electric field.** Each antenna records two or three polarization channels.
  The field vector is obtained by unfolding the antenna's vector effective length (its
  direction- and frequency-dependent pattern) and the gain and phase of the analogue chain.
  The unfolding needs the arrival direction, so field and direction are iterated. The result
  is a band-limited field, so the band is part of every quoted amplitude. Narrow-band
  transmitters are removed in the frequency domain, which also removes some signal power.
  The antenna pattern and absolute gain, calibrated with a reference source and monitored
  with the Galactic radio background, are usually the leading energy-scale systematic.
- **Finding the pulses.** Most arrays read out on an external trigger from particle
  detectors, which then sets the radio efficiency. Self-triggering must reject impulsive
  man-made noise: it requires coincidences between neighbouring antennas consistent with a
  front moving at about the speed of light, a polarization consistent with geomagnetic
  emission, and directions away from known noise sources near the horizon. Within the
  trigger-predicted window an antenna counts as having a signal above a signal-to-noise
  threshold; near that threshold, noise produces false pulses and biases the measured signal
  upward.
- **Energy fluence per antenna.** The observable is the energy fluence, the time-integrated
  Poynting flux `epsilon_0 c ∫ E^2 dt` (definition) in the signal window. The noise
  fluence measured outside the window is subtracted; the noise, including its interference
  term with the signal, sets the per-antenna uncertainty.
- **Direction and core.** Antenna times fit a wavefront, a plane as first guess and then a
  hyperbolic (conical far from the axis) front; interferometric beamforming is an
  alternative. The footprint is not rotationally symmetric: geomagnetic emission is
  polarized along `v x B` and charge-excess emission radially, so they interfere along the
  `v x B` axis and add without interference along `v x (v x B)`, where the polarization
  measures the charge-excess fraction. The core and the lateral distribution are therefore
  fitted in these shower-plane coordinates.
- **Energy.** The fluence integrated over the footprint is the radiation energy. After
  dividing out the geomagnetic-angle dependence (the geomagnetic field amplitude scales with
  `sin alpha`, so its fluence with `sin^2 alpha`; the charge-excess part does not depend on
  `alpha`, and its fraction grows with the air density) and correcting for the air density at
  shower maximum, it scales quadratically with the electromagnetic energy (*approximate*:
  the exponent, close to 2, is fitted in simulation; Glaser et al., J. Cosmol. Astropart. Phys.
  09 (2016) 024). Showers arriving close to the field direction carry little radio signal and
  are measured poorly. Radio measures the electromagnetic energy only; the absolute scale is
  tied to the antenna calibration or to another detector.
- **Depth of maximum and composition.** The footprint size and its Cherenkov-like ring
  depend on the geometric distance to the shower maximum. Comparing each event with
  simulated footprints spanning `X_max` gives `X_max` (Buitink et al., Phys. Rev. D 90 (2014)
  082003); parametric lateral functions with a distance-to-`X_max` term are the faster
  alternative, and the wavefront curvature and the spectral slope are further
  `X_max`-sensitive observables. The fit returns a geometric distance; converting it to slant
  depth needs the atmospheric density profile, an uncertainty to list. Muon content needs a
  particle detector (see the muon and electromagnetic bullet in surface-array reconstruction
  above).
- **Per-event uncertainty.** Noise sets the per-antenna errors and the threshold bias.
  Events with few antennas have a degenerate core and `X_max`. Template results also carry
  the simulation's uncertainty: the refractive-index profile (humidity), the antenna model
  and shower-to-shower fluctuations. Validate with pulls in simulation and against an
  independent energy or `X_max` measurement on common events.

**Check:** Radio events state the frequency band, the antenna-pattern and gain calibration,
the trigger (external or self), the wavefront and footprint model with the corrections for
geomagnetic angle and air density, the atmospheric density profile used to convert to
`X_max`, and the validation against an independent measurement.

### Instrument response functions (checklist)

State, with its version: the effective area or aperture (m^2 sr) above full trigger efficiency, the trigger efficiency below it for each primary; the energy threshold and the energy bias and resolution versus energy; the angular
resolution (PSF, for example the 68% containment radius R68) versus energy; and the IRF set and its validity range
(zenith, conditions). Numbers come from the experiment's IRF release or profile, not from this file.

## Deliverables

- Which technique(s) contributed to a reported energy: surface-array density
  conversion, fluorescence calorimetric profile, or a hybrid combination, and (for a
  hybrid result) which subsample calibrated which.
- The reference distance and constant-intensity-cut attenuation curve used for a
  surface-array energy estimate, and its residual composition/interaction-model
  dependence if not hybrid-calibrated.
- The invisible-energy correction applied to a fluorescence calorimetric energy, and
  the interaction model it was derived from.
- Atmospheric monitoring coverage and the transparency/aerosol correction applied,
  or the exclusion criterion used for nights without adequate monitoring.
- For an `X_max`-based composition result: the atmospheric density profile assumed and
  whether its seasonal variation was propagated.
- Duty cycle and exposure calculation for the dataset used, and whether a spectrum
  measurement relies on the surface array's continuous exposure or the fluorescence
  detector's reduced duty cycle.
- Station signal scale and the treatment of saturated and non-triggered stations; for
  fluorescence events, the geometry mode (monocular, hybrid, stereo) and the Cherenkov
  subtraction.
- For radio events: the frequency band, antenna calibration, trigger, footprint model and
  the `X_max` method with its simulation inputs.
