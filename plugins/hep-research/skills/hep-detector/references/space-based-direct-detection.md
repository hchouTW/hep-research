# Space-Based and Balloon-Borne Direct Cosmic-Ray Detection

Covers cosmic-ray measurements made *above the atmosphere* (satellite or long-duration
balloon magnetic spectrometers and calorimeters), where
individual nuclei are measured directly rather than inferred from an air shower. The
detector technology - magnetic spectrometry, calorimetry, TOF, TRD, RICH - is exactly
the material in
[detector-systems-overview.md](detector-systems-overview.md) through
[particle-identification.md](particle-identification.md), applied
unchanged; this file covers what is specific to the near-Earth space environment:
geomagnetic and solar effects that ground- and space-based measurements alike must
correct for, and that have no collider-physics analog.

<!-- example: experiment-specific illustration -->
Example: AMS-02-class instruments (a magnetic spectrometer on a space station).
<!-- /example -->

## Rigidity, not energy, is the natural variable - for a spectrometer

Space instruments are of two kinds, and they measure different things:

<!-- example: source citation (experiment named as the source of a general method or number) -->
- **Magnetic spectrometers** (see
  [detector-systems-overview.md](detector-systems-overview.md)) measure rigidity
  `R = pc/(Ze)` from the track curvature, the sign of the charge, and, with an
  independent velocity measurement, the mass and so the isotope. Their resolution is
  bounded by the maximum detectable rigidity (MDR), and charge confusion near it is a
  background.
- **Calorimetric instruments** (thick calorimeter plus charge detectors, without a
  magnet) measure the energy deposited in the calorimeter and the charge magnitude.
  Because the calorimeter does not contain the whole hadronic shower, the incident
  energy is obtained by unfolding the deposited-energy spectrum with an energy response
  matrix from simulation (the DAMPE proton spectrum, Sci. Adv. 5 (2019) eaax3793,
  arXiv:1909.12860, solves for the incident spectrum with a Bayesian unfolding of the
  deposited-energy bins; opened 2026-10-14). They have no MDR, measure no charge sign
  and so have no charge confusion, and do not separate isotopes.
<!-- /example -->

Every geomagnetic and solar effect below acts on rigidity, not on energy or momentum
separately - because both the geomagnetic field's confinement and a Fermi-accelerated
source's maximum energy are set by how a particle's gyroradius compares to a length
scale, which depends on `p/(Ze)`. A spectrometer flux is therefore reported in rigidity;
reporting it only in kinetic energy per nucleon discards this scaling and makes
comparison across species (which differ in `Z` and `A`) needlessly indirect. A
calorimetric flux is reported in (kinetic) energy, and any comparison in rigidity needs
an `A/Z` assumption.

## Geomagnetic cutoff

The Earth's magnetic field acts as a rigidity filter: a charged particle arriving from
a given direction at a given geomagnetic location can only reach the top of the
atmosphere (or a near-Earth satellite) if its rigidity exceeds a minimum, the
**geomagnetic cutoff rigidity**. For a simple dipole approximation, the vertical
(zenith-pointing) cutoff at geomagnetic latitude `lambda_m` is the **Störmer cutoff**:

    R_c = C * cos^4(lambda_m) / (r^2 * (1 + sqrt(1 - sin(eps) sin(xi) cos^3(lambda_m)))^2)

with zenith angle `eps`, azimuth `xi` measured clockwise from geomagnetic north (east = 90 deg; this sign is for a positive particle), `C = 59.6 GV` (proportional to the Earth's dipole
moment `M`; 59.6 GV corresponds to the IGRF-14 dipole of 1955, and the 2025 dipole gives
values about 4.5% lower, from the degree-1 IGRF-14 coefficients) and `r` the geocentric distance in Earth radii. For vertical arrival the
square root is 1, so `R_c = 14.9 GV * cos^4(lambda_m) / r^2` (Smart & Shea 2005): about
15 GV at the geomagnetic equator at the surface (~13 GV at ISS altitude), falling to
essentially zero at the poles - the reason polar-orbit low-cutoff regions are preferred for measuring the
lowest-rigidity cosmic rays. A flux measurement from a satellite in an inclined orbit
fills its low-rigidity bins only from the low-cutoff parts of the orbit (high
geomagnetic latitude), and must model the orbit-averaged, direction-dependent cutoff.
The cutoff is east-west asymmetric: for the positively charged majority of cosmic rays
it is lower for arrival from the west and higher from the east (ECSS-E-ST-10-04C,
annex B.8, "Geomagnetic shielding (Størmer theory)", via SPENVIS; formula and azimuth
convention as in R. Nolty, Caltech thesis (2002), arXiv:hep-ex/0201015, section on the
Störmer cutoff; both opened 2026-10-14). Off-vertical arrival is therefore not
uniformly higher: in the eastern half of the sky horizontal particles have a higher
cutoff than vertical ones, in the western half a lower one.
From the formula above at the equator and the surface, horizontal arrival from the west
(`sin(eps) sin(xi) = -1`) gives `59.6/(1 + sqrt(2))^2 ≈ 10.2 GV` against the vertical
14.9 GV, and from the east (`sin(eps) sin(xi) = +1`) `59.6 GV`. The real, non-dipolar
field further complicates this into a "penumbra" of partially-forbidden trajectories
requiring backtracing simulation rather than the analytic formula. `<plugin root>/skills/hep-measurement/scripts/geomagnetic_cutoff.py` evaluates the
analytic vertical Störmer cutoff as a first-order estimate; a rigorous cutoff for a
specific orbit and epoch requires particle backtracing through a full geomagnetic
field model and is not something the analytic formula replaces.

**Selection rule for a flux.** Keep an event in a rigidity bin only if the bin's lower edge
is above a safety factor times the maximum cutoff (1.2 is one experiment's convention,
not a general standard; state the value used), where the cutoff is
backtraced through a realistic field model (e.g. IGRF plus an external-field model) over the
detector's acceptance cone at that second. Add that second's livetime to the exposure of the
same bins, and only those bins. The Störmer value is a planning check and does not replace
this rule. Using a different rule for events than for exposure biases the flux near the cutoff.

Below its local geomagnetic cutoff, any flux an instrument records at that rigidity
is not primary cosmic radiation reaching from outside the magnetosphere - it is
albedo particles (atmospheric secondaries: splash albedo moving upward, re-entrant albedo guided to
the conjugate point and arriving downward) or trapped radiation-belt particles; near the cutoff
primaries also arrive through penumbral windows, and the transmission differs between charge signs,
so treat e+/e- and antiproton/proton cutoffs separately. They and must be excluded from a
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

The standard first-order correction is the **force-field approximation**, one effective modulation potential `phi`
per period. Its formula (total and per-nucleon forms), validity range and charge-sign limits are owned by hep-theory:
[force-field solar modulation](../../hep-theory/references/cosmic-ray-propagation.md#force-field-solar-modulation),
implemented by `solar_modulation_force_field.py` (hep-measurement; worked example below). On the detector side, use it
only for comparing or combining measurements made in similar solar conditions and for a rough local interstellar
spectrum estimate where no direct low-cutoff, low-activity measurement exists.
Any comparison of fluxes from different epochs, instruments, or even different
detectors on the same mission across a long enough mission duration to span a
meaningful change in `phi`, must state the modulation potential (or the neutron-
monitor-count-rate proxy commonly used to track it) for each dataset compared.

**Comparing with Voyager, and naming the cycle phase.** Voyager 1 crossed the heliopause in
August 2012 (Voyager 2 in November 2018). Beyond it, the spacecraft measure the low-energy
LIS directly. Demodulate only the 1 AU flux, not the Voyager data. Take the epoch's phase from
the sunspot record instead of guessing. Solar cycle 24 began at a minimum in December 2008 and
peaked in April 2014 (13-month smoothed). It had a double maximum: a first peak from the northern
hemisphere (hemispheric maximum November 2011), a long plateau between the peaks (early 2012 to mid 2013), and the higher
second peak from the southern hemisphere in early 2014. So about 2011-2014 is **solar maximum**,
not a declining phase, and the solar magnetic polarity reversed during it ([SILSO cycle table](https://www.sidc.be/SILSO/cyclesmm), [SILSO news: 2014, maximum year for cycle 24](https://www.sidc.be/SILSO/news004)). Solar cycle 25 began at the December 2019 minimum ([Royal Observatory of Belgium, 15 September 2020](https://astro.oma.be/en/december-2019-confirmed-as-starting-point-of-the-new-solar-activity-cycle)) and reached its smoothed maximum in October 2024 ([SIDC](https://www.sidc.be/article/solar-cycle-25-reached-its-maximum-october-2024); both read 2026-10-14; smoothed values are revised, so re-check the cycle table). Data from 2020 on need their own phase and polarity statement. In that period `phi` is higher than at the 2009 minimum,
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

Beyond excluding transients, a long-duration mission's flux time series is itself a measurement. The statistical
method (a known period tested alone, a periodogram against a red-noise null for an unknown one, the trials across
periods and energy bins, comparing species of opposite charge sign) is owned by hep-statistics:
[time-series inference](../../hep-statistics/references/time-series-inference.md#periodicity-in-a-binned-series).
What the detector side must supply:

- **Corrections at the cadence of the series.** A daily-flux series needs per-day acceptance, livetime and
  geomagnetic-cutoff corrections (see the per-event cutoff treatment above); a periodicity search is only as good as
  the bin-to-bin stability of that normalization, and the time-bin covariance it hands to hep-statistics.
- **Instrumental periods.** List the periods the instrument itself imposes (orbit, attitude, precession, calibration
  cycles) so that they are tested as candidates or vetoed, not found as signals.
- **The epoch and solar-activity phase** each series covers (rising, maximum, declining, minimum, and the polarity
  era), as the solar-modulation discussion above requires for a spectrum.

## Direct-detection composition and the local antiparticle excesses

<!-- example: source citation (experiment named as the source of a general method or number) -->
Because a space-based magnetic spectrometer measures the charge (with its sign) and,
with a velocity measurement, the mass (through the PID chain in
[particle-identification.md](particle-identification.md)), it gives a species and
isotope identification that no ground-based technique provides; a calorimetric space
instrument identifies the element by its charge magnitude but not the isotope or the
charge sign - the reason direct detection remains the reference measurement
for composition, isotopic ratios, and antiparticle fluxes, even though its
geometric-factor-limited exposure caps its reach well below the knee. Two antiparticle
results are often quoted together but differ in status. The measured **positron
fraction** (positron flux relative to positron-plus-electron flux) rises with energy
above a few GeV, whereas standard secondary production (cosmic-ray nuclei spallating
on the interstellar medium, per
[cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md))
predicts a falling fraction; this positron excess is interpreted either as nearby
primary sources of `e+ e-` pairs (pulsars are the leading astrophysical candidate) or,
more speculatively, as dark-matter annihilation or decay. Pulsars produce only `e+-`,
not antiprotons. The **antiproton** spectrum at high rigidity is harder than some
secondary-production predictions, but whether it exceeds the secondary expectation at
all is still debated, because the prediction's uncertainties (production cross
sections, propagation) are comparable to the difference. Distinguishing source
hypotheses requires the spectral shape (including any published high-energy drop and its
model-dependent significance) and consistency with other channels (gamma-ray, anisotropy), not an
excess alone. For numbers, significances and the current status read the bound experiment profile's
ledger (for AMS-02: the [antimatter and leptons
module](../../../profiles/experiments/ams-02/modules/species/antimatter-and-leptons.md), claims C04
and C96), not this file.
<!-- /example -->

## Worked walkthrough: a proton flux point from counts (verified 2026-09-24)

The bin is 5.0-6.0 GV, with the spacecraft at geomagnetic latitude 40 deg and r = 1.0627 Earth
radii (ISS-like).

```bash
python3 <plugin root>/skills/hep-measurement/scripts/geomagnetic_cutoff.py --latitude 40 --radius-re 1.0627
python3 <plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py --counts 320 --exposure 2.4e5 --bin-width 1.0 --bin-width-unit GV
python3 <plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py --demodulate --energy 4.641 --mass 0.938272 \
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
   convert to kinetic energy (5.5 GV, the bin centre, is used here for simplicity; a real analysis uses the spectrum-weighted rigidity -> T = 4.641 GeV for a proton), convert the flux per GV to
   a flux per GeV, and demodulate. At phi = 0.6 GV the LIS flux is 1.233x the TOA flux, at
   T_LIS = 5.241 GeV. The force field is a one-parameter approximation, so state phi, the
   epoch, and the model.

### Low-count, high-rigidity bins

For 4 events in 1.3-2.0 TV with exposure 2.0e7 m^2 sr s
(`<plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py --counts 4 --exposure 2.0e7 --bin-width 700 --bin-width-unit GV`, verified 2026-09-25):

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

### Instrument response functions (checklist)

State, with its version: the acceptance (geometric factor times selection efficiency, m^2 sr) versus rigidity or energy, per species; for a calorimeter also the energy response matrix; the energy threshold and the energy bias and resolution versus energy; the angular
resolution (PSF, for example the 68% containment radius R68) versus energy; and the IRF set and its validity range
(zenith, conditions). Numbers come from the experiment's IRF release or profile, not from this file.

Also state the material above the instrument (balloon overburden, in g/cm^2, and the correction for secondaries
made in it) and fragmentation of nuclei inside the instrument, which moves events between species.

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
