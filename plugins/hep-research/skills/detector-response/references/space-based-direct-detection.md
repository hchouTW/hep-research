# Space-Based and Balloon-Borne Direct Cosmic-Ray Detection

<!-- example: experiment-specific illustration -->
Covers cosmic-ray measurements made *above the atmosphere* (satellite or long-duration
balloon magnetic spectrometers and calorimeters, e.g. AMS-02-class instruments), where
individual nuclei are measured directly rather than inferred from an air shower. The
detector technology - magnetic spectrometry, calorimetry, TOF, TRD, RICH - is exactly
the material in
[detector-systems-overview.md](detector-systems-overview.md) through
[particle-identification.md](particle-identification.md), applied
unchanged; this file covers what is specific to the near-Earth space environment:
geomagnetic and solar effects that ground- and space-based measurements alike must
correct for, and that have no collider-physics analog.
<!-- /example -->

## Rigidity, not energy, is the natural variable

As in any magnetic spectrometer (see
[detector-systems-overview.md](detector-systems-overview.md)), a
space-based instrument directly measures rigidity `R = pc/(Ze)`, and every
geomagnetic and solar effect below acts on rigidity, not on energy or momentum
separately - because both the geomagnetic field's confinement and a Fermi-accelerated
source's maximum energy are set by how a particle's gyroradius compares to a length
scale, which depends on `p/(Ze)`. Reporting a direct-detection flux in kinetic energy
per nucleon rather than rigidity discards this natural scaling and makes comparison
across species (which differ in `Z` and `A`) needlessly indirect.

## Geomagnetic cutoff

The Earth's magnetic field acts as a rigidity filter: a charged particle arriving from
a given direction at a given geomagnetic location can only reach the top of the
atmosphere (or a near-Earth satellite) if its rigidity exceeds a minimum, the
**geomagnetic cutoff rigidity**. For a simple dipole approximation, the vertical
(zenith-pointing) cutoff at geomagnetic latitude `lambda_m` is the **Störmer cutoff**:

    R_c = C * cos^4(lambda_m) / (r^2 * (1 + sqrt(1 - sin(eps) sin(xi) cos^3(lambda_m)))^2)

with zenith angle `eps`, azimuth `xi`, `C = 59.6 GV` (proportional to the Earth's dipole
moment `M`) and `r` the geocentric distance in Earth radii. For vertical arrival the
square root is 1, so `R_c = 14.9 GV * cos^4(lambda_m) / r^2` (Smart & Shea 2005): about
15 GV at the geomagnetic equator at the surface (~13 GV at ISS altitude), falling to
essentially zero at the poles - the reason polar-orbit low-cutoff regions are preferred for measuring the
lowest-rigidity cosmic rays, and why any flux measurement from a satellite in an
inclined orbit must either restrict to high-cutoff geomagnetic regions for a clean
low-energy cutoff or explicitly model the orbit-averaged, direction-dependent cutoff
(off-vertical arrival directions have a higher, angle-dependent cutoff than the
vertical Störmer value, and the real, non-dipolar field further complicates this into
a "penumbra" of partially-forbidden trajectories requiring backtracing simulation
rather than the analytic formula). `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/geomagnetic_cutoff.py` evaluates the
analytic vertical Störmer cutoff as a first-order estimate; a rigorous cutoff for a
specific orbit and epoch requires particle backtracing through a full geomagnetic
field model and is not something the analytic formula replaces.

**Selection rule for a flux.** Keep an event in a rigidity bin only if the bin's lower edge
is above a safety factor (typically 1.2) times the maximum cutoff, where the cutoff is
backtraced through a realistic field model (e.g. IGRF plus an external-field model) over the
detector's acceptance cone at that second. Add that second's livetime to the exposure of the
same bins, and only those bins. The Störmer value is a planning check and does not replace
this rule. Using a different rule for events than for exposure biases the flux near the cutoff.

Below its local geomagnetic cutoff, any flux an instrument records at that rigidity
is not primary cosmic radiation reaching from outside the magnetosphere - it is
**re-entrant/albedo** particles (secondaries produced in the atmosphere and reflected
back upward) or trapped radiation-belt particles, and must be excluded from a
primary-spectrum measurement rather than corrected for.

## Solar modulation

The Sun's magnetized wind carries the heliospheric magnetic field outward, and its
turbulence scatters and decelerates incoming Galactic cosmic rays as they diffuse
inward - suppressing the flux below roughly a few tens of GV in a way that varies
with the ~11-year solar activity cycle (weaker suppression near solar minimum,
stronger near solar maximum) and, more weakly, with the ~22-year solar magnetic
polarity cycle (which affects the *charge-sign-dependent* drift pattern of cosmic rays
through the heliosphere, producing measurable differences between particle and
antiparticle modulation, e.g. electrons versus positrons, that a purely diffusive
treatment does not capture).

The standard first-order correction is the **force-field approximation**: treating
modulation as an effective energy loss characterized by a single **modulation
potential** `phi` (units of rigidity/potential, typically hundreds of MV), relating
the flux at 1 AU, `J(E)`, to the flux outside the heliosphere (the local interstellar
spectrum, LIS), `J_LIS(E_LIS)`, via

    J(E) = (2 m E + E^2) / (2 m E_LIS + E_LIS^2) * J_LIS(E_LIS),   E_LIS = E + |Z|*phi

for a particle of total rest mass `m`, total kinetic energy `E` and charge `|Z|`
(Gleeson & Axford 1968), evaluated at the same time as the measurement. In kinetic
energy per nucleon the shift is `(|Z|/A)*phi` with `m` the nucleon mass - mixing
per-nucleon `E` with `|Z|*phi` over-modulates every `A > 1` nucleus. This is an effective, not physical, one-parameter model - it does not
capture charge-sign dependence, latitude dependence, or short-timescale transients -
and its use should be limited to what it is good for: comparing or combining
measurements made in similar solar conditions, and providing a rough LIS estimate
outside the range where a direct low-cutoff, low-solar-activity measurement exists.
Any comparison of fluxes from different epochs, instruments, or even different
detectors on the same mission across a long enough mission duration to span a
meaningful change in `phi`, must state the modulation potential (or the neutron-
monitor-count-rate proxy commonly used to track it) for each dataset compared.

**Comparing with Voyager, and naming the cycle phase.** Voyager 1 crossed the heliopause in
August 2012 (Voyager 2 in November 2018). Beyond it, the spacecraft measure the low-energy
LIS directly. Demodulate only the 1 AU flux, not the Voyager data. Take the epoch's phase from
the sunspot record instead of guessing. Solar cycle 24 began at a minimum in December 2008 and
peaked in April 2014 (smoothed). It had a double maximum: a northern-hemisphere peak in
November 2011, then a plateau from early 2012 to mid 2013. So 2011-2013 is **solar maximum**,
not a declining phase, and the solar magnetic polarity reversed during it. In that period `phi` is higher than at the 2009 minimum,
and it changes fast enough that a single `phi` for all three years is itself an approximation.

**Forbush decreases** - sudden, transient flux depressions lasting days, caused by a
coronal mass ejection's magnetic structure sweeping past Earth - and **solar
energetic particle (SEP) events** - direct particle acceleration at the Sun or in
interplanetary shocks, producing a distinct, time-localized, typically softer-
spectrum flux enhancement dominated by protons and heavier ions up to at most a few
GeV/nucleon - are both short-timescale contaminants that a Galactic-cosmic-ray flux
measurement must identify (from neutron-monitor or space-weather-instrument data) and
exclude from the integration time window, rather than average over silently.

## Searching for periodicity and time structure in a flux time series

Beyond excluding transients, a long-duration mission's flux time series is itself
a measurement: heliospheric transport imprints known periodicities on top of the
smooth force-field trend, and finding or bounding them is a distinct statistical
task from fitting the time-averaged spectrum.

- **Know what period you're looking for before choosing a method.** A **known**
  period (the ~27-day solar (Bartels) rotation and its harmonics, or a diurnal
  cycle tied to the detector's own orbital/attitude geometry) is best tested with
  **epoch-folding / superposed-epoch analysis**: fold the time series at the
  candidate period and look for a coherent, above-noise modulation, rather than a
  free periodogram search, which pays an unnecessary trials penalty for a period
  you already have a physical reason to test. Reserve a periodogram (e.g.
  Lomb-Scargle, which handles the uneven sampling and data gaps a satellite
  time series generally has) for a genuinely unknown or approximate period, and
  correct its detection significance for the number of independent frequencies
  scanned - the same look-elsewhere-effect discipline as
  [astroparticle-statistics.md](../../hep-statistics/references/astroparticle-statistics.md)'s trials-factor
  treatment, applied to frequency space instead of a sky position or mass bin.
- **Bin fine enough to resolve the structure, coarse enough to keep bins
  statistics-limited rather than systematics-limited.** A daily-flux time series
  needs per-day acceptance, livetime, and geomagnetic-cutoff corrections at that
  same cadence (see the per-event cutoff treatment above) - a periodicity search
  is only as good as the systematic stability of the bin-to-bin normalization it
  sits on top of.
- **Charge-sign dependence is itself a diagnostic, not just a nuisance.** Because
  the heliospheric magnetic polarity cycle produces genuinely different transport
  (gradient/curvature drift-dominated vs. diffusion-dominated, alternating roughly
  every 11 years) for positively- and negatively-charged particles, comparing the
  *same* candidate periodicity's amplitude and phase between a particle and its
  antiparticle (or between species of opposite sign, e.g. protons vs. electrons)
  tests whether an observed structure is drift-related or a shared instrumental/
  environmental artifact that would affect both signs identically.
- **State the epoch and solar-activity phase a periodicity claim covers.** A
  periodicity's amplitude and even its presence is not stationary across a solar
  cycle - report the date range and solar-activity phase (rising/maximum/
  declining/minimum) a detection or non-detection applies to, the same way the
  solar-modulation discussion above requires stating the modulation potential
  for a spectrum.

## Direct-detection composition and the local antiparticle excesses

Because a space-based spectrometer measures charge and mass directly (through the
PID chain in [particle-identification.md](particle-identification.md)),
it gives an unambiguous species and isotope identification that no ground-based
technique provides - the reason direct detection remains the reference measurement
for composition, isotopic ratios, and antiparticle fluxes, even though its
geometric-factor-limited exposure caps its reach well below the knee. The measured
**positron fraction** (positron flux relative to positron-plus-electron flux) rising
with energy above a few GeV, and a harder-than-secondary-production **antiproton**
spectrum at high rigidity, are the most consequential such results: standard secondary
production (cosmic-ray nuclei spallating on the interstellar medium, per
[cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md))
predicts a falling positron fraction and a softer antiproton spectrum, so the excess
is interpreted either as evidence of nearby primary sources (pulsars are the leading
astrophysical candidate) or, more speculatively, as a signature of dark-matter
annihilation or decay - distinguishing the two requires the spectral shape, an
eventual high-energy cutoff or lack thereof, and consistency with other channels
(gamma-ray, anisotropy), not the excess alone.

## Worked walkthrough: a proton flux point from counts (verified 2026-09-24)

The bin is 5.0-6.0 GV, with the spacecraft at geomagnetic latitude 40 deg and r = 1.0627 Earth
radii (ISS-like).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/geomagnetic_cutoff.py --latitude 40 --altitude-re 1.0627
python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cosmic_ray_flux.py --counts 320 --exposure 2.4e5 --bin-width 1.0
python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/solar_modulation_force_field.py --demodulate --energy 4.641 --mass 0.938272 \
    --charge 1 --phi 0.6 --toa-flux 1.0
```

1. **Cutoff.** The real selection uses the per-second backtraced cutoff (see the selection rule
   above). As a planning check only, the vertical Stormer cutoff here is 4.54 GV. With a 1.2
   safety factor (5.45 GV), this position contributes exposure only to bins above about 5.5 GV,
   so for this bin the exposure comes only from time spent where `1.2 * Rc < 5.0 GV`.
2. **Flux.** For 320 counts with exposure 2.4e5 m^2 sr s (already cutoff-filtered) and a 1 GV
   bin, the flux is 1.333e-3 (m^2 sr s GV)^-1 with an exact 68% interval of
   [1.259, 1.412]e-3. Report the counts, exposure, and bin width separately. Plot the point at
   the spectrum-weighted rigidity, not at the bin center.
3. **Solar modulation.** The flux is top-of-instrument (TOA). To compare it with a LIS,
   convert to kinetic energy (5.5 GV -> T = 4.641 GeV for a proton), convert the flux per GV to
   a flux per GeV, and demodulate. At phi = 0.6 GV the LIS flux is 1.233x the TOA flux, at
   T_LIS = 5.241 GeV. The force field is a one-parameter approximation, so state phi, the
   epoch, and the model.

### Low-count, high-rigidity bins

For 4 events in 1.3-2.0 TV with exposure 2.0e7 m^2 sr s
(`${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cosmic_ray_flux.py --counts 4 --exposure 2.0e7 --bin-width 700`, verified 2026-09-25):

- If a user proposes `sqrt(N)/exposure/dR` for a bin with a few counts, the answer is **no**.
  Do not call it "approximately correct". Use the exact (Garwood) Poisson interval. At 68% it
  is [2.09, 7.16] counts, which is asymmetric. **Run the script to get the interval. Do not
  estimate it by hand**, because the rounded integer bounds a model guesses (e.g. [2, 6]) are
  wrong.
- Convert TV to GV before dividing, since fluxes are quoted per GV. A 0.7 TV bin used as
  `dR = 0.7` makes the flux 1000x too large. Write the bin width in GV (700 GV here) and give units with every flux value:
  2.86e-10 (m^2 sr s GV)^-1, with interval [1.49, 5.12]e-10.
- At TV rigidities, finite resolution approaches the maximum detectable rigidity (MDR). The
  steep spectrum then spills events into the bin from lower rigidities, so correct for this
  with unfolding or a forward-folded fit and state the resolution model.
- Count charge-confusion and interaction backgrounds before quoting the flux. With 4 events,
  even a background of 0.5 events changes the result.

## Deliverables

- Whether the reported spectrum is quoted at the top of the atmosphere/instrument
  (rigidity- or kinetic-energy-per-nucleon-binned) or corrected to the local
  interstellar spectrum, and if the latter, the modulation potential and model used.
- The geomagnetic cutoff applied (vertical Störmer as a first-order estimate, or a
  backtraced penumbra), the orbit/epoch it was computed for, and how off-vertical
  arrival directions and re-entrant/albedo contamination below cutoff were handled.
- The solar-activity epoch (dates, and neutron-monitor or modulation-potential proxy)
  the dataset spans, and whether Forbush-decrease or SEP-event periods were
  identified and excluded from the integration window.
- For a composition or isotope result: which PID subsystem(s) established charge and
  mass, and the momentum/rigidity range over which the required separation holds (see
  [particle identification](particle-identification.md)).
- For an antiparticle-excess interpretation: the astrophysical secondary-production
  baseline assumed, and what additional evidence (spectral cutoff, anisotropy,
  multi-channel consistency) distinguishes a nearby-source from a dark-matter
  interpretation.
