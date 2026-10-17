# Cosmic-ray measurements: index and anisotropy design

An index for designing a cosmic-ray measurement: for each measurement type it points to the sections that already
cover it, in this skill and in hep-detector, hep-statistics and hep-communication. Only the anisotropy
section has its own content. Links are relative to this file. Experiment conventions (cutoff safety factor, binning,
periods, resolutions) come from the bound profile, never from this file.

## Contents

- [Absolute flux](#absolute-flux)
- [Flux ratios](#flux-ratios)
- [Isotope ratios](#isotope-ratios)
- [Time-dependent flux](#time-dependent-flux)
- [Rare-event searches](#rare-event-searches)
- [Anisotropy](#anisotropy) (new content: estimand, exposure, harmonic and dipole estimators, spurious modulations, upper limits)
- [Astroparticle and cosmic-ray invariants](#astroparticle-and-cosmic-ray-invariants) (moved from the analysis guide)

## Absolute flux

| Step | Read |
|---|---|
| Estimand per bin, normalization kind (`exposure` or `live-time`) | [Correction chain, generic forms](correction-chain.md#generic-forms), [estimand and fiducial definition](measurements-and-unfolding.md#estimand-and-fiducial-definition) |
| Efficiency factors and their denominators | [Correction chain, factorized efficiency](correction-chain.md#factorized-efficiency) |
| Rigidity vs energy as the variable | hep-detector: [rigidity, not energy](../../hep-detector/references/space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer) |
| Geomagnetic cutoff and the cutoff-filtered exposure | hep-detector: [geomagnetic cutoff](../../hep-detector/references/space-based-direct-detection.md#geomagnetic-cutoff) |
| A flux point from counts, low-count bins | hep-detector: [worked walkthrough](../../hep-detector/references/space-based-direct-detection.md#worked-walkthrough-a-proton-flux-point-from-counts-verified-2026-09-24), [low-count bins](../../hep-detector/references/space-based-direct-detection.md#low-count-high-rigidity-bins); script `cosmic_ray_flux.py` (the bin-width unit is a free string, reported and never converted; beyond the Feldman-Cousins grid, total mean above 500, `auto` takes an asymptotic profile-likelihood interval, labelled approximate, within 5% of Feldman-Cousins at the grid edge) |
| Orbit-averaged cutoff, retrograde orbits | script `orbit_averaged_geomagnetic_cutoff.py` (an inclination above 90 deg reaches the latitudes of 180 - i; `--edges` sets the exposure-versus-cutoff bins) |
| Instrument response checklist | hep-detector: [instrument response functions](../../hep-detector/references/space-based-direct-detection.md#instrument-response-functions-checklist) |
| Spillover near the resolution limit; forward-fold or unfold | [Steeply falling spectra](measurements-and-unfolding.md#steeply-falling-spectra-and-spillover) |
| Spectral features and what they mean | hep-detector: [all-particle spectrum](../../hep-detector/references/cosmic-ray-spectrum-and-composition.md#the-all-particle-spectrum-and-its-features); script `cr_spectrum_powerlaw_fit.py` |
| Corrected-measurement checklist | [Design checklist](measurements-and-unfolding.md#design-checklist-for-a-corrected-measurement) |
| Figures (flux scaled by a power of energy, exposure curves) | hep-communication: [figures](../../hep-communication/references/astroparticle-and-cosmic-ray-papers.md#figures-spectra-skymaps-and-exposure) |

## Flux ratios

| Step | Read |
|---|---|
| Shared systematics and the covariance of the two yields | [analysis guide, astroparticle invariants](#astroparticle-and-cosmic-ray-invariants); script `particle_ratio_with_uncertainty.py` |
| Charge confusion and species-specific backgrounds in antiparticle ratios | [Backgrounds, antiparticles](backgrounds.md#antiparticles-and-charge-sign-confusion) |
| Secondary-to-primary ratios: fragmentation feed-down, survival probability | [Correction chain, nuclei](correction-chain.md#nuclei-and-isotopes) |
| Which systematics cancel and which do not | [Systematics, source inventory](systematics.md#source-inventory) |
| Physics of secondary/primary ratios (propagation) | hep-detector: [propagation](../../hep-detector/references/cosmic-ray-spectrum-and-composition.md#propagation) |
| Antiparticle fractions and their status | hep-detector: [local antiparticle excesses](../../hep-detector/references/space-based-direct-detection.md#direct-detection-composition-and-the-local-antiparticle-excesses) |

## Isotope ratios

| Step | Read |
|---|---|
| Mass from velocity and rigidity; range limited by mass resolution | [Correction chain, nuclei](correction-chain.md#nuclei-and-isotopes), hep-detector: [rigidity, not energy](../../hep-detector/references/space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer) |
| Velocity measurements and their combination | hep-detector: [time of flight](../../hep-detector/references/particle-identification.md#time-of-flight-tof), [RICH](../../hep-detector/references/particle-identification.md#ring-imaging-cherenkov-detectors-rich), [combining measurements](../../hep-detector/references/particle-identification.md#combining-measurements) |
| Mass-template fit, migration between isotopes | [Steeply falling spectra](measurements-and-unfolding.md#steeply-falling-spectra-and-spillover) (migration), hep-statistics for the template fit |
| Per-isotope survival and fragmentation feed-down | [Correction chain, nuclei](correction-chain.md#nuclei-and-isotopes) |

## Time-dependent flux

| Step | Read |
|---|---|
| Per-period exposure, exposure-weighted averages, efficiency drift, period-correlated systematics | [Correction chain, time dependence](correction-chain.md#time-dependent-measurements) |
| Solar modulation and the epoch to state | hep-detector: [solar modulation](../../hep-detector/references/space-based-direct-detection.md#solar-modulation); script `solar_modulation_force_field.py`; the solar-phase rule in the [analysis guide](#astroparticle-and-cosmic-ray-invariants) |
| Periodicity in a flux time series (known vs unknown period, binning, charge-sign comparison) | hep-detector: [periodicity](../../hep-detector/references/space-based-direct-detection.md#searching-for-periodicity-and-time-structure-in-a-flux-time-series) |
| Event-level periodicity tests and variability | hep-statistics: [astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md#point-sources-test-statistics-periodicity-and-variability) |
| Time-bin covariance and binned-series inference | [hep-statistics time-series inference](../../hep-statistics/references/time-series-inference.md) (hands off the period-correlated evidence from the correction chain) |

## Rare-event searches

| Step | Read |
|---|---|
| Rate or flux from a handful of counts, with background | [Correction chain, generic forms](correction-chain.md#generic-forms); script `cosmic_ray_flux.py` (Feldman-Cousins with a known or uncertain background) |
| Background from misidentified abundant species | [Backgrounds, antiparticles](backgrounds.md#antiparticles-and-charge-sign-confusion), [sidebands](backgrounds.md#sidebands-and-data-driven-shapes) |
| Selection optimized without seeing the signal region | [Selection optimization](analysis-design.md#selection-optimization-without-bias), [blinding](analysis-design.md#blinding) |
| Trials over bins, species or windows fixed in advance | [Look-elsewhere at the design stage](analysis-design.md#look-elsewhere-at-the-design-stage) |
| Upper limits and significance | hep-statistics: [CLs and upper limits](../../hep-statistics/references/inference-recipes.md#cls-and-upper-limits), [astroparticle look-elsewhere](../../hep-statistics/references/astroparticle-statistics.md#the-look-elsewhere-effect-in-its-astroparticle-forms) |

## Anisotropy

Context already covered elsewhere: why anisotropy constrains diffusion
([propagation](../../hep-detector/references/cosmic-ray-spectrum-and-composition.md#propagation)); how papers
present it as its own block, skymap conventions and trials
([structure](../../hep-communication/references/astroparticle-and-cosmic-ray-papers.md#how-the-structure-differs-from-collider-hep),
[figures](../../hep-communication/references/astroparticle-and-cosmic-ray-papers.md#figures-spectra-skymaps-and-exposure),
[reading checklist](../../hep-communication/references/astroparticle-and-cosmic-ray-papers.md#reading-checklist-additions));
arrival directions near the cutoff ([geomagnetic cutoff](../../hep-detector/references/space-based-direct-detection.md#geomagnetic-cutoff)).
A review of the observations and methods: Ahlers & Mertsch, Prog. Part. Nucl. Phys. 94 (2017) 184, arXiv:1612.01873.

### Estimand

State, in one sentence: species (or all particles), rigidity or energy range (threshold fixed before looking), the
coordinate frame (equatorial, Galactic, or a solar or local frame), and which quantity is reported:

- the **first-harmonic amplitude r and phase** in right ascension (or another angle), a raw observable;
- the **dipole projection** onto the plane the exposure is sensitive to (for a right-ascension analysis, the
  equatorial component `d_perp`);
- the **full three-dimensional dipole** `d` (amplitude and direction), which needs exposure over the whole sky.

For an intensity `I(u) proportional to 1 + d . u` the dipole amplitude is `|d| = (I_max - I_min) / (I_max + I_min)`.
To first order in `d`, the right-ascension first harmonic of a pure dipole is `r = d_perp <cos delta>`, with the mean
over the declinations of the events (Inferred: integrate the dipole over the exposure at fixed right ascension); the
component along the rotation axis does not appear in r at all. Converting r to `d_perp` therefore needs the
declination distribution, and quoting r as a dipole amplitude without it is a defect.

### Directional exposure

The exposure is a function of direction, not a number: `omega(u) = integral dt A(u_local(t)) T_live(t)
step(R > f R_c(u_local, t))` in the chosen frame, where `u_local(t)` follows the instrument's orientation (for a ground
array the Earth's rotation; for an instrument in orbit its orbit and attitude), A is the direction-dependent acceptance
and the cutoff mask uses the profile's safety factor f per direction (the cutoff differs east to west, see
[geomagnetic cutoff](../../hep-detector/references/space-based-direct-detection.md#geomagnetic-cutoff)). Where the
geomagnetic deflection is not small, the arrival direction at the instrument is not the asymptotic direction: trace
back through a field model, and state the model and epoch.

- **Model or data.** A simulated exposure (acceptance times live time, per direction) is exact in principle but
  carries the acceptance model's systematics directly into the anisotropy. Data-driven estimates (time scrambling or
  direct integration of the local-coordinate distribution over the live time; Alexandreas et al., Nucl. Instrum.
  Meth. A 328 (1993) 570) absorb instrumental structure, but also absorb any signal that is constant in local
  coordinates; for a ground array this removes the dipole component along the rotation axis and reduces large-scale
  structure (reviewed in Ahlers & Mertsch 2017). State which estimate is used and what it cannot see.
- **Differential methods.** The east-west method (Bonino et al., ApJ 738 (2011) 67, arXiv:1106.2651) takes the
  difference between eastward- and westward-arriving events in right ascension, cancelling direction-independent
  modulations of the exposure (for example in time) at the cost of sensitivity.
- **Non-uniformity in time.** Live-time gaps, efficiency drifts and cutoff changes along the orbit modulate the
  exposure; a modulation that correlates with the frame's angle (right ascension, local time) mimics an anisotropy.
  Use the per-period exposure of [time-dependent measurements](correction-chain.md#time-dependent-measurements).
- **Species comparison (Inferred).** Comparing the arrival directions of two species selected with the same exposure
  cancels the common exposure model; species-specific selection efficiencies that vary with direction do not cancel.

### Estimators

- **Harmonic analysis** (Linsley, Phys. Rev. Lett. 34 (1975) 1530): with right ascensions `alpha_i` and weights
  `w_i = 1 / omega(alpha_i)` that correct the relative exposure in right ascension, `a = (2/W) sum w_i cos alpha_i`,
  `b = (2/W) sum w_i sin alpha_i`, `W = sum w_i`, amplitude `r = sqrt(a^2 + b^2)`, phase `phi = atan2(b, a)`. Under
  isotropy and for large N, a and b are Gaussian with variance `2/N` each, so r follows the Rayleigh distribution and
  `P(>= r) = exp(-N r^2 / 4)`.
- **Full-sky dipole** (Sommers, Astropart. Phys. 14 (2001) 271, arXiv:astro-ph/0004016): with exposure on the whole sky,
  `d = 3 sum_i (u_i / omega(u_i)) / sum_i (1 / omega(u_i))`, the unit vectors `u_i` weighted by the inverse exposure;
  for uniform exposure each Cartesian component has variance about `3/N` (Inferred from `Var(3 u_x) = 3` per event).
  Directions where `omega = 0` make the estimator undefined.
- **Partial sky.** With incomplete coverage the multipoles couple: a quadrupole leaks into the dipole estimate.
  Fix the maximum multipole order before looking and estimate the coefficients jointly (Sommers 2001; Billoir &
  Deligny, JCAP 02 (2008) 009).
- **Amplitude bias.** r is positive by construction, so for a small true amplitude it is biased upward: under isotropy
  its mean is `sqrt(pi/N)`. For a true amplitude s, r follows the Rice distribution with the same width; the phase is
  meaningful only when s is well above that width.

### Spurious modulations: checks to plan

- **Frequencies.** Analyse the solar (one cycle per solar day), sidereal and anti-sidereal frequencies. The solar
  frame carries a known dipole from the observer's motion (Compton & Getting, Phys. Rev. 47 (1935) 817: relative
  amplitude `(gamma + 2) v / c` for an intensity spectrum `E^-gamma`), a check of the method. No physical signal is
  expected at the anti-sidereal frequency; a non-zero amplitude there signals a seasonally modulated solar-frequency
  effect leaking into the sidereal one (Farley & Storey, Proc. Phys. Soc. A 67 (1954) 996).
- **Instrument periods (Inferred).** For an instrument in orbit, the orbital period, its precession and attitude
  changes play the role of the solar day: check the amplitude at those frequencies and in the local frame.
- **Systematics ledger.** Each entry is evaluated through its effect on r, phi or `d`: exposure model (acceptance
  versus direction, live time, cutoff mask and field model), direction reconstruction and backtracing, rigidity scale
  near the threshold, background species with a different exposure. Angular resolution matters little for a dipole
  but does for small-scale structure.
- **Blinding.** Fix the frame, threshold, multipole order and exposure method on scrambled or simulated skies before
  the real map is looked at ([blinding](analysis-design.md#blinding)); thresholds or species scanned afterwards are
  trials ([look-elsewhere at the design stage](analysis-design.md#look-elsewhere-at-the-design-stage)).

### Upper limits on the amplitude

When the amplitude is not significant, report an upper limit on the amplitude (r, `d_perp` or `|d|`, said which),
not the observed r, together with the expected limit under isotropy for the same exposure. The design supplies the
estimator, the exposure, N and the systematic ledger; the construction is hep-statistics': the limit follows from the
Rice distribution of r for each true amplitude, with the choice
between a Neyman upper limit, a Feldman-Cousins interval on `s >= 0` or a Bayesian bound, its coverage checked on
simulated skies drawn with the real exposure, and the trials over energy bins
([inference recipes](../../hep-statistics/references/inference-recipes.md#cls-and-upper-limits),
[astroparticle look-elsewhere](../../hep-statistics/references/astroparticle-statistics.md#the-look-elsewhere-effect-in-its-astroparticle-forms)).

### Script

`<plugin root>/skills/hep-measurement/scripts/anisotropy.py` implements the right-ascension part of this section:

- `exposure`: the relative exposure per right-ascension bin from data-taking periods (the period table of
  `collection_time.py`), for a top-hat field of view of declared half-width around the zenith right ascension, which
  advances one turn per sidereal day from the user's local sidereal time at the clock's zero (no default). A planning
  model; a real exposure comes from the acceptance per direction and can be passed as the map.
- `harmonic`: the weighted first harmonic (amplitude, phase, Rayleigh probability with the effective count), `d_perp`
  when declinations are given, the amplitude upper limit (Neyman, from the Rice distribution, power-constrained at the
  expected limit so it is never empty; its coverage is checked on toys) and, with event times, the solar, sidereal and
  anti-sidereal harmonics: a significant anti-sidereal amplitude makes the run `failed` (exit 1). Without an exposure
  map it warns that uniform exposure is assumed; without times the checks are reported as not run.

The full three-dimensional dipole (whole-sky exposure) and the joint multipole fit for partial coverage are not
implemented; they belong to hep-statistics.

### Deliverables

- Estimand sentence: species, range, frame, quantity (r, `d_perp` or `d`), and the declination distribution if r is
  converted.
- Exposure map, its method (simulated or data-driven) and what that method cannot see.
- Amplitude and phase with their uncertainties, or the upper limit and the expected limit, with the Rayleigh
  probability of the observed amplitude.
- Solar, sidereal and anti-sidereal (or instrument-period) results as checks; the systematics ledger.

## Astroparticle and cosmic-ray invariants

Moved here from the [analysis guide](hep-measurement-guide.md) (B-03); they apply to every measurement above.

- In an ON/OFF or blind sky-scan search, the OFF/background region must not overlap the ON region, and a reported significance must account for the number of independent trials (positions, energy bins, time windows, source catalogs) actually tested, not just the one presented.
- Distinguish a flux measured at the top of the atmosphere or at an instrument from one corrected to the local interstellar spectrum; state the solar-modulation epoch/potential and the geomagnetic cutoff applied whenever a low-rigidity cosmic-ray flux is reported. Keep an event in a rigidity bin only if the bin's lower edge is above f times the maximum cutoff over the acceptance cone, backtraced through a realistic field model at that time; f is an experiment's convention taken from its profile, and the same rule defines the exposure, E_i = sum over t of T_live(t) A_i step(R_low,i > f Rc_max(t)) ([selection rule](../../hep-detector/references/space-based-direct-detection.md)); a Stormer formula is only a planning estimate. Take the epoch's solar phase from the SILSO sunspot record, never from memory: look up in the [SILSO cycle table](https://www.sidc.be/SILSO/cyclesmm) the minimum and the 13-month smoothed maximum of the cycle that contains the data-taking period, and state them with the date the table was read (smoothed values are revised); a multi-peaked maximum is solar maximum, not a declining phase. The detector reference gives a worked reading for cycles 24 and 25 ([space-based direct detection](../../hep-detector/references/space-based-direct-detection.md)).
- Do not draw a composition conclusion from a single shower observable (X_max or muon content alone) without stating the hadronic interaction model assumed (quote more than one) and checking consistency against the other observable, given the current muon-content/X_max modeling discrepancy. Use the X_max distribution width (sigma(X_max)), not only the mean: simulations give about 60 g/cm2 for protons and about 20 g/cm2 for iron near 1e18 eV, far wider than the naive superposition value sigma_p/sqrt(A) (about 8 g/cm2); a mixed composition adds the spread of the component means, sigma(X_max)^2 = <sigma_i^2> + (spread of <X_max>_i), so the width measures the variance of lnA; convert mean and width to lnA moments for each hadronic model ([Kampert & Unger 2012, arXiv:1201.0018](https://arxiv.org/abs/1201.0018), Sec. 2).
- A flux or rate reported from raw counts must use an exact Poisson interval, not a Gaussian sqrt(N) approximation, whenever counts are low enough for the two to disagree (routine in a steeply falling spectrum's high-energy tail); state the exposure (effective area/geometric factor times live time times solid angle) and bin width used, separately from the raw count. If asked whether `sqrt(N)` is right for a few-count bin, answer no (not "approximately right"), run `<plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py` for the interval, and for a high-rigidity/energy bin also address resolution spillover and background ([space-based direct detection, low-count bins](../../hep-detector/references/space-based-direct-detection.md#low-count-high-rigidity-bins)).
- A ratio or fraction of two yields (e.g. a positron fraction or an antiproton/proton ratio) must use the yields' actual covariance, not an independence assumption, whenever they share a systematic (the same acceptance, exposure, or background-template shape) - state which systematics are shared and whether they were treated as correlated. Species-specific effects (e.g. charge confusion, which feeds protons into the antiproton sample) belong to one yield only and do not cancel.
