# Calibration, Monte Carlo, and Systematic Uncertainties

## When to read this file

Read when linking conditions and calibrations to reconstructed quantities, validating MC against data, assembling a systematic ledger, or checking that a systematic is neither missing nor counted twice. The four correction categories are defined in [reconstruction-and-data-quality](../methods/reconstruction-and-data-quality.md#four-categories-of-correction); the likelihood treatment of nuisances in [inference-and-unfolding](../methods/inference-and-unfolding.md).

## Contents

1. [Calibration chain](#calibration-chain)
2. [MC provenance](#mc-provenance)
3. [Data-MC validation](#data-mc-validation)
4. [Systematic ledger](#systematic-ledger)
5. [Required systematic families](#required-systematic-families)
6. [Propagation and correlations](#propagation-and-correlations)
7. [Double-counting checks](#double-counting-checks)
8. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Calibration chain

For each calibration: what reconstructed quantity it changes, its granularity, its validation observable, and its residual systematic.

| Calibration | Changes | Validation observable (independent of the tuned quantity) | Residual enters as |
|---|---|---|---|
| Tracker alignment | `R` scale/resolution, `|Z|` | Track residuals, split-track consistency, redundant partial-fit rigidities | Rigidity-scale + resolution nuisance |
| Magnetic field / rigidity scale | Absolute `R` | A physically motivated reference (redundant measurement, known-mass relation, or a beam-like control where available) | Scale nuisance, amplified by local spectral index |
| TOF time offsets/slewing | `β`, direction | `β` of abundant ultra-relativistic species; up/down separation | `β` scale/resolution |
| Charge-response (Tracker/TOF/RICH) | `|Z|` | Element peak positions and widths, layer consistency | Charge migration matrix |
| TRD gas/gain | Discriminant | Discriminant of an abundant control species vs time | Template shape nuisance |
| ECAL energy scale and linearity | `E`, `E/p` | `E/p` of a clean lepton sample (physics-motivated), shower shapes | Energy-scale nuisance |
| RICH refractive index/alignment | `β` | `β` residual for known-mass species | `β` scale nuisance |
| Inter-subsystem matching | Efficiency and residuals | Matching residual distributions | Efficiency nuisance |
| Time-dependent drift | All above | Stability plots vs time | Period-split or drift systematic |

**Rule.** A calibration must not be tuned on the observable being measured (e.g. do not tune `R` scale to remove a spectral feature). If tuning is unavoidable, use an independent observable and carry the residual freedom as a systematic.

**Where the calibration comes from** (flight data, beam tests at accelerators, ground tests, simulation) is analysis-specific and, for AMS internals, not public beyond sources; state as user-supplied or cite.

## MC provenance

Record every item; a result with any missing item is not reproducible.

- Generator/source and species, generated spectrum, generation surface/volume and solid angle (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md#mc-generation-record)).
- Transport engine, physics list (hadronic and electromagnetic), geometry and material description, version.
- Detector response model, digitization, noise/dead channels applied, calibration constants applied.
- Reconstruction version; production period; statistics and weights.

**Version invalidation.** A change in reconstruction or calibration requires regeneration or a demonstrated insensitivity of the response products (efficiency, response matrix, templates). A production period that does not match the data period (hardware era, dead channels) is a systematic or a defect. Alternative hadronic, material, electromagnetic and generated-spectrum models must be tested for any quantity that depends on them.

## Data-MC validation

Quantitative validation means a metric and a threshold that triggers action; "reasonable agreement" is not accepted.

- Validation observables: control-sample efficiencies, track residuals, charge estimators (peak positions and widths per `Z`), `β` distributions, shower variables, TRD discriminant, interaction/fragmentation tails (e.g. probability of charge change between layers), phase-space coverage of MC vs data, MC statistics per bin.
- For each: state the metric (e.g. ratio and difference of efficiencies, χ²/ndf with correlations, Kolmogorov–Smirnov *with* a stated caveat on finite-statistics and binning), the acceptable deviation (determined from the size of the effect on the result), and the action on failure (reweight/scale factor with uncertainty; additional systematic; method change).
- Tails matter more than cores for backgrounds and charge confusion; compare data and MC on the tail region using an abundant sample that populates the tail (e.g. a loosened selection).

## Systematic ledger

```yaml
systematic:
  name: null
  source: calibration | efficiency | acceptance | background | response | model | exposure
  affected_objects: []
  representation: nuisance | alternate_sample | covariance | envelope
  variation_basis: null              # what is varied, by how much, and why (source/evidence)
  effect: normalization | shape | migration | mixed
  correlations_across_bins: null
  correlations_across_species_or_time: null
  validation: null
  double_counting_checks: []
```

Record for each uncertainty: source, evidence, variation or nuisance definition, effect type, bin/species/time correlations, symmetry (up/down asymmetric?), and covariance/likelihood propagation.

## Required systematic families

- Trigger and selection efficiency (conditional efficiencies; factorization bias).
- Acceptance, material, interactions, fragmentation (cross-section model variation, upstream material).
- Backgrounds and charge confusion (template shape, transfer to signal region, tail modeling).
- Rigidity/energy/`β`/charge scale and resolution (scale shifts times local spectral index; resolution tails).
- Response, unfolding and forward-model dependence (prior, regularization, response perturbation).
- Template statistics and fit model (finite-template nuisances, alternative templates).
- Livetime, geomagnetic cutoff and time dependence (cutoff model variation, safety factor, time binning).
- MC statistics, generator and transport (alternative generators/physics lists).

## Propagation and correlations

1. Represent each systematic as a nuisance in the likelihood, a set of alternate samples propagated through the full analysis, or a covariance block; state which and why.
2. For scale shifts: shift the reconstructed variable, re-run migration (not only rescale the final spectrum).
3. Classify correlations: fully correlated across bins (normalization), partially (smooth shape), independent (statistical-like); across species (shared acceptance) and time (persisting calibration).
4. Combine covariances, not variances, unless correlations are demonstrated to be zero; **never quadratically combine unknown correlations**; report the full covariance or a reproducible correlation model.
5. Numerator-denominator correlations for ratios and fractions are part of the systematic model (see [charged-cosmic-rays](../species/charged-cosmic-rays.md#ratio-or-fraction-blueprint)).

## Double-counting checks

For each systematic ask: (a) does the calibration already absorb this effect? (b) is the same MC variation used as both an efficiency uncertainty and a response uncertainty? (c) is a fit constraint (template statistics) also inside the statistical covariance? (d) are data-MC scale factors and an independent MC-model variation both counting the same discrepancy? (e) is a time-dependent drift counted as both a veto and a systematic? Record the answer in `double_counting_checks`.

## Failure modes

- Calibration tuned on the measured observable; residual not carried.
- Single MC configuration with no alternative physics-list/material/spectrum test.
- Data-MC "agreement" without metric or action; tail region ignored.
- Percentage systematics combined in quadrature ignoring correlations; correlation across species/time omitted.
- Scale systematic applied to the final spectrum instead of through migration.
- Reconstruction version mismatch between data and MC.

## Required source classes

Tier 1 AMS papers for specific systematic treatments of a specific result; Tier 2 subsystem calibration papers (e.g. detector NIM papers on tracker performance, TRD, RICH, ECAL parametrization; see [source-index](../../evidence/index.md)); Tier 4 for Geant4/MC and systematic-uncertainty methodology. Internal calibration constants are not public; use only user-supplied.

## Questions to ask the user

Which calibrations have you applied and how were they validated? MC provenance items above? Which alternative models do you have for material, interactions, fragmentation? Which systematics are already in a covariance you inherit? Are scale systematics propagated through migration?
