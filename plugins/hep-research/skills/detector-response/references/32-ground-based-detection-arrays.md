# Ground-Based Detection Arrays: Surface Detectors and Fluorescence

Covers the two complementary techniques for observing an extensive air shower (see
[31-extensive-air-showers.md](31-extensive-air-showers.md)) from the
ground - sampling it at one depth with a surface array, or imaging its full
longitudinal development with fluorescence telescopes - and the hybrid combination
that dominates modern ultra-high-energy cosmic-ray observatories. Detector-technology
material that is not air-shower-specific (photomultiplier response, timing
electronics) is out of scope here; this file is about what each technique measures
and how that becomes an energy and a composition estimate.

## Surface detector arrays

A surface array is a grid of individual detector stations - historically scintillator
panels, and in water-Cherenkov form (used because water is cheap, robust outdoors, and
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
  *reference distance* from the reconstructed shower core - typically chosen (from
  simulation) to be the distance at which shower-to-shower fluctuations in the
  lateral distribution are minimized, so that the density-to-energy conversion is as
  model-independent as practical. This is a direct application of shower
  universality (see [31-extensive-air-showers.md](31-extensive-air-showers.md)):
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
  the workhorse for spectrum measurements (exposure is straightforward, being
  essentially detector-area times live time times a geometric solid-angle factor) and
  why hybrid designs use fluorescence for calibration rather than as the primary
  exposure-defining detector.

## Fluorescence detectors

As a shower's charged particles ionize atmospheric nitrogen, the nitrogen fluoresces,
emitting isotropic UV light proportional to the local ionization energy deposit -
which fluorescence telescopes (segmented mirrors with pixelated photomultiplier
cameras) image from the side, reconstructing the shower's longitudinal profile
`N(X)` directly, essentially independent of any hadronic interaction model, since the
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
  see [31-extensive-air-showers.md](31-extensive-air-showers.md)), making
  fluorescence the primary composition-measuring technique among ground-based methods.
- **Duty cycle is roughly 10-15%**: fluorescence light is faint UV, requiring dark,
  clear, moonless nights, so only a fraction of showers that trigger a co-located
  surface array are also seen by fluorescence. This asymmetry is exactly what a
  **hybrid** design (fluorescence plus surface array, e.g. Pierre Auger Observatory,
  Telescope Array) exploits: use the small, high-quality, calorimetric-energy hybrid
  subsample to calibrate the surface array's density-to-energy conversion, then apply
  that calibration to the full, 100%-duty-cycle surface-only dataset for the spectrum
  measurement, tying the absolute energy scale to the fluorescence calorimetric
  measurement's own systematic uncertainty (dominated by the fluorescence yield and
  atmospheric transparency/aerosol content, both requiring independent atmospheric
  monitoring instruments co-located with the telescopes).

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
