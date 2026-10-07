# AMS-02 Case Study: A Long-Duration Space-Based Spectrometer

If this session has not read them yet, read the profile's [working rules](../working-rules.md) first.

Short overview of how the generic detector references
([detector-systems-overview.md](../../../../../skills/detector-response/references/detector-systems-overview.md) through
[particle identification](../../../../../skills/detector-response/references/particle-identification.md)) and
[space-based direct detection](../../../../../skills/detector-response/references/space-based-direct-detection.md) combine in one real
instrument, the Alpha Magnetic Spectrometer (AMS-02) on the International Space
Station. **For AMS-specific design, review, or "what did AMS publish / latest result"
work, use the rest of this profile ([index](../../index.md))**: it holds the
source-traced facts (selections, templates, unfolding, isotope methods, cutoff factor,
data periods) and the public-evidence boundary. This file deliberately keeps no AMS
numbers, publication lists, or hardware-history dates so there is one place, not two, to
keep correct; anything AMS-specific must be checked against the collaboration's
publications (see [primary-sources-and-version-checks.md](../../../../../skills/research-communication/references/primary-sources-and-version-checks.md)).

## Subsystem stack (roles only)

A silicon tracker inside a **permanent** magnet gives signed rigidity (the only charge-sign
source); time-of-flight planes give trigger, direction and velocity; a transition radiation
detector separates leptons from hadrons; anti-coincidence counters veto side-entering
particles; a ring-imaging Cherenkov detector with two radiator types gives velocity for
charge and, with rigidity, isotope separation; an electromagnetic calorimeter gives energy
and shower shape. The lessons that generalize:

- Each subsystem answers a different question, and a rare-species measurement combines
  several of them. Correlated inputs (a shared track, shared calorimeter energy) must not
  be summed as independent evidence - see [particle identification](../../../../../skills/detector-response/references/particle-identification.md).
- A veto or direction requirement removes events before any charge or rigidity
  measurement is trusted; it is an exposure/efficiency question, not a downstream
  correction.
- TRD-type discrimination has no charge-sign information; sign comes from the magnetic
  spectrometer.

## What is distinctive about a multi-year space mission

- **No routine servicing, so conditions change over time.** Alignment, gains, and
  detector configuration must be tracked per data-taking period, and an analysis spanning
  a documented hardware change must treat the eras separately or justify combining them
  - see [calibration and alignment](../../../../../skills/detector-response/references/calibration-and-alignment.md). Verify any specific
  servicing or upgrade date and scope in a primary source before citing it. As of
  2026-10-01, the Layer-0 tracker upgrade (an extra silicon layer on top, quoted ~300%
  acceptance gain) was not yet installed. A CERN news item of 2026-08-21 plans launch to
  the ISS in April 2027 with connections completed by May 2027 (planned dates, may have
  slipped), which will create a new detector era (see [sources](../../../../../skills/research-communication/references/primary-sources-and-version-checks.md)).
- **Orbital environment.** The orbit sweeps a wide range of geomagnetic latitudes, so the
  cutoff is a per-event (or per-time-bin) quantity from spacecraft position and pointing,
  not one number; a "primary" selection uses a safety factor above it and varies that
  factor as a systematic - see
  [space-based direct detection](../../../../../skills/detector-response/references/space-based-direct-detection.md),
  `<plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py` and `<plugin root>/skills/hep-analysis/scripts/orbit_averaged_geomagnetic_cutoff.py`
  (planning-level estimates, not field-model backtracing). Periodic thermal cycling and
  high-background regions likewise call for binning or exclusion, not averaging.
- **Solar modulation.** A multi-year series is itself a solar-modulation measurement;
  time-resolved results use short time blocks, and combining them without accounting for
  the changing modulation reintroduces a bias - see
  `<plugin root>/skills/hep-analysis/scripts/solar_modulation_force_field.py`.

## Rare-species measurement pattern

Positron fraction, antiproton/proton ratio, and antinucleus searches share a structure:

1. **Ratios or fractions of two yields from one detector** cancel only part of the
   acceptance/exposure systematics; cancellation must be shown per effect, not assumed.
   `<plugin root>/skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py` gives the two-yield first-order
   propagation, including a correlation term (see
   [histograms-efficiencies.md](../../../../../skills/hep-analysis/references/histograms-efficiencies.md)).
2. **The background for the rarer species is the far more abundant one mis-identified**
   (or, for charge-sign measurements, charge-confused), so the working point is chosen for
   rejection power, and the residual contamination is modeled by a template fit or
   control-region estimate rather than assumed negligible - see
   [particle identification](../../../../../skills/detector-response/references/particle-identification.md).
3. **A null result is reported as an exposure-normalized limit** with the Poisson or
   likelihood machinery in [inference-recipes.md](../../../../../skills/hep-statistics/references/inference-recipes.md) and
   [astroparticle-statistics.md](../../../../../skills/hep-statistics/references/astroparticle-statistics.md), and
   `<plugin root>/skills/hep-analysis/scripts/cosmic_ray_flux.py` for flux from counts, exposure and bin width.

## Composition ratios as a propagation diagnostic

A secondary-to-primary ratio versus rigidity is the generic propagation diagnostic in
[cosmic-ray spectrum and composition](../../../../../skills/detector-response/references/cosmic-ray-spectrum-and-composition.md#propagation).
Sort a species into primary, secondary, or mixed before interpreting its rigidity
dependence, and treat the physical interpretation as a model step beyond the measurement.
Which species AMS has measured, and with what result, is a profile-evidence / primary-paper
question, not something to take from this file.

## Deliverables

- Which subsystems' information entered each selection, their correlations, and the
  working-point efficiency and rejection at each stage.
- Whether results are time-binned to resolve solar modulation and cutoff variation or
  averaged, and the resulting systematic.
- The alignment/gain calibration cadence relative to orbital and long-term drift.
- Whether the analyzed period spans a hardware-configuration change, and how it is treated.
- For a ratio or fraction: which systematics are shared and the covariance used, not naive
  quadrature.
- For any quoted AMS parameter or result: the specific publication it was checked against.
