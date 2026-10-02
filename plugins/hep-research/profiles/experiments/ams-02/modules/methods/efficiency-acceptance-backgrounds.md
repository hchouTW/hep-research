# Efficiency, Acceptance, Exposure, Backgrounds, and Template-Fit Design

> Method owner: [hep-analysis](../../../../../skills/hep-analysis/SKILL.md) defines the general method (correction chains and background estimation (efficiency methods themselves: detector-response)). This module records how AMS-02 analyses apply it. General statements here are snapshots carried from the legacy `ams-analysis` skill; where they differ from the owner, the owner's text applies.

## When to read this file

Read when defining efficiencies, acceptance, exposure, MC generation, background ledgers, or when designing/reviewing a template fit. It is the canonical home for conditional efficiencies, the exposure/acceptance definitions, the background ledger, and the template-fit checklist. The count/response likelihood is in [inference-and-unfolding](../methods/inference-and-unfolding.md); calibrations and MC provenance in [calibration-mc-systematics](../methods/calibration-mc-systematics.md).

## Contents

1. [Definitions](#definitions)
2. [Conditional efficiencies](#conditional-efficiencies)
3. [Efficiency methods](#efficiency-methods)
4. [Acceptance, exposure, livetime](#acceptance-exposure-livetime)
5. [MC generation record](#mc-generation-record)
6. [Background ledger](#background-ledger)
7. [Template fits](#template-fits)
8. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Definitions

| Term | Definition | Unit | Not to be confused with |
|---|---|---|---|
| Geometric acceptance `A_geo` | Integral over the generation surface of area × solid angle passing a purely geometric fiducial definition | m² sr | Selection efficiency |
| Effective acceptance `A_eff` | `A_geo` times the average selection-and-reconstruction efficiency for a stated species/bin | m² sr | Exposure |
| Livetime `T_live` | Time the trigger/DAQ were live and quality-approved | s | Calendar time |
| Exposure | Time-integrated acceptance: `Σ_t A_eff(t) T_live(t) × geomagnetic transmission` (in bin) | m² sr s | Acceptance |
| Efficiency `ε` | Conditional probability that an event in a named denominator passes a named numerator | dimensionless | Acceptance |
| Purity | Fraction of selected events that are signal | dimensionless | Efficiency |

If a response matrix "includes inefficiency", say so; then `A` and `ε` are already inside it and must not be applied again (see [inference-and-unfolding](../methods/inference-and-unfolding.md#count-and-response-model)).

## Conditional efficiencies

**Rule.** `ε_total = ε_1 · ε_2|1 · ε_3|12 ...` where each factor is conditional on the preceding selections. Multiplying marginal (unconditional) efficiencies is valid only if the selections are independent for the population of interest, which must be shown, not assumed. **Correlations arise** when two cuts use related information: both use the Tracker charge estimate; a shower-shape cut and an `E/p` cut share ECAL energy; a TRD cut and a rigidity cut share rigidity dependence; track quality and geometry are correlated with hit patterns.

Procedure to combine factors:
1. Write each numerator and the conditional denominator (population after all prior selections).
2. Measure each factor on a sample where its denominator is populated without bias (see methods).
3. Check **factorization bias**: compute the joint efficiency directly in data/MC where possible and compare to the product; the difference is a systematic or a reason to measure jointly.
4. **Ordering closure.** Apply the chain in two different orders in MC; totals must agree to statistical precision, individual factors change.
5. **Bounds are not estimates.** Without independence, two efficiencies `ε_A`, `ε_B` only bound the joint: `max(0, ε_A + ε_B - 1) ≤ ε_{A∧B} ≤ min(ε_A, ε_B)` (Fréchet). Two 99% selections give a joint between 98% and 99%: quoting 98% is a floor, not a measured efficiency.
6. **Combined-efficiency closure.** In MC compare the product of the measured factors (with data-derived corrections) to the truth-level combined efficiency, per bin and per relevant kinematic/time slice.
7. Propagate dependence on species, kinematics, time, and geometry (efficiency is a function, not a number).

## Efficiency methods

- **Tag-and-probe.** Select a probe with an independent tag; measure the fraction passing. Requires: probe independence from the tested selection, tag bias evaluated, background subtraction in the probe sample (with its own uncertainty), purity of the tag, migration of the probe's kinematic variable between bins.
- **Unbiased or prescaled triggers.** A subsample of events recorded with a minimum-bias-like trigger measures trigger efficiency; account for the prescale and for the sample's own selection. Trigger internals are not public beyond what sources give; use only user-supplied definitions.
- **Orthogonal selectors.** A control sample selected by a different subsystem (e.g. TOF/TRD/RICH information when testing a Tracker cut). Independence of the two subsystems for the population must be argued.
- **MC-based with data/MC scale factors.** `ε_data = SF · ε_MC` where `SF = ε_data/ε_MC` from a control; scale factors depend on the same variables as the efficiency and carry their own statistical and systematic uncertainty; do not apply a scale factor measured on one species or period to another without justification.
- **Interval estimation.** Efficiencies from finite samples are binomial (or Poisson-ratio with background subtraction): use exact/Bayesian binomial intervals near 0 or 1, not Wald.

## Acceptance, exposure, livetime

**Generation record (needed for every MC-derived acceptance).** Generation surface or volume and its orientation; generated solid angle; generated rigidity/energy spectrum and species; truth definition of "in acceptance"; event weights (including reweighting to an assumed spectrum); material/geometry model version; reconstruction and selection version.

**Procedure.**
1. Define the fiducial phase space (truth-level) and the bin edges of the true variable.
2. Compute `A_geo` from the generation record (`A_geo = π A_gen` for an isotropic flux through a planar surface of area `A_gen` when the solid-angle integral over the accepted hemisphere is used; verify the conventions and cut-offs for the actual generation).
3. Obtain the effective acceptance by dividing the number passing selection and reconstruction by the number generated, per bin, per species, with the generated spectrum reweighted to the target spectrum **without circularity**: if the target spectrum is what you measure, iterate or use a response that does not depend on it (see [inference-and-unfolding](../methods/inference-and-unfolding.md#unfolding)).
4. Combine with time-resolved livetime and geomagnetic transmission to form exposure: integrate over intervals so that the product is correct when acceptance and livetime vary simultaneously.
5. Check bin centering: a differential flux quoted at a bin "center" needs a stated prescription (e.g. a spectral-shape-dependent correction to the position where the flux equals the bin average), not the arithmetic center by default.
6. Check for prescale and dead-time effects, and for any time dependence of acceptance (e.g. after hardware changes).

**Geomagnetic transmission.** Depends on the cutoff model, direction, position, time, and the safety factor applied to select "primary" cosmic rays. See [charged-cosmic-rays](../species/charged-cosmic-rays.md#geomagnetic-selection).

**Material interactions.** Survival probability of the primary through upstream material and in-detector interactions is an efficiency/acceptance-type correction dependent on the interaction cross-section model; separate it from geometric acceptance and document the cross-section model variation (see [calibration-mc-systematics](../methods/calibration-mc-systematics.md#mc-provenance)).

## MC generation record

Record: generator or beam source, particle species, energy/rigidity spectrum, transport engine and physics list, geometry and material model, detector response and digitization, noise and dead channels, calibration constants applied, reconstruction version, production period, sample statistics (and weights). Validate before use (see [calibration-mc-systematics](../methods/calibration-mc-systematics.md#data-mc-validation)).

## Background ledger

Canonical schema (other files reference it):

```yaml
background:
  name: null
  physical_or_instrumental_origin: null
  entry_mechanism: null         # how it enters the signal region
  signal_region: null
  control_region: null          # orthogonal, signal-depleted, same detector conditions
  estimator: sideband | template_fit | simultaneous_fit | mc_corrected | migration_matrix | tag_and_probe
  transfer_model: null          # extrapolation from control to signal region, with assumptions
  contamination_correction: null # signal leaking into the control region
  closure_test: null
  nuisance_parameters: []
  correlations: []
```

For every background: origin; how it enters the signal region; estimator; control region and its **signal contamination**; the extrapolation (transfer) and what it assumes; closure test; nuisance parameters and their correlations with other backgrounds and with the signal shape.

Supported estimators: data sidebands; simultaneous or template fits; MC shapes corrected with data; charge-sign migration matrices; tag-and-probe; orthogonal selectors. For each, state where the method could fail (control region not representative, template shape not universal in rigidity/time, signal contamination of the control sample).

## Template fits

**Choose** binned Poisson likelihood by default; unbinned only when template shapes are smooth and well-defined; state which.

**Checklist.**
- **Provenance** of each template: MC, data-derived with a control, or hybrid, and how it was derived without using the fitted data itself in a circular way.
- **Finite template statistics**: bin-by-bin nuisance (Barlow-Beeston or the Conway light variant), or an equivalent that includes template uncertainty; do not treat templates as exact.
- **Morphing/interpolation** across rigidity, energy, or time; **kinematic dependence** (templates differ per rigidity bin); **smoothing** and its bias; **regularization** if used.
- **Cross-contamination** between templates (e.g. signal in the background template); **identifiability** (degenerate shapes, fit-parameter correlations near ±1).
- **Constraints and nuisance correlations** across bins/species; avoid constraining nuisances using the same information as the fit unless declared.
- **Goodness of fit** (pulls, residuals, saturated-likelihood or toy-based p-value), **toys/Asimov** for expected behavior, **closure** with injected signal, **alternative templates**, **fit-bias tests** across the signal-strength range including zero.
- **Repeated tuning on the same data** (template choice, binning, discriminant) inflates apparent agreement; predefine or blind, and record iterations.

**Classifier-derived discriminants.** Require independent training sample; audit inputs for target leakage; overtraining test; domain-shift validation between MC training and data; stability versus kinematics and time; and state that a shape mismatch between data and MC is not a validation success.

## Failure modes

- Product of marginal efficiencies; no combined-efficiency closure.
- Efficiency measured on a control contaminated by signal or biased by the tag.
- Acceptance defined with the same selection twice (geometry cut plus efficiency loss).
- Circular reweighting: generated spectrum tuned to the measured spectrum then used to derive acceptance.
- Template fit with signal-contaminated background template, ignoring finite-template statistics, or tuned repeatedly on the fit sample.
- Bin-center flux taken at the arithmetic center without prescription.
- Control-region transfer assumed flat in rigidity or time without evidence.

## Required source classes

Tier 4 for tag-and-probe, binomial intervals, and finite-template likelihood (Barlow-Beeston 1993, Conway 2011); Tier 1 AMS methods sections for how a specific AMS result determined its efficiencies and templates. AMS-specific claims about how a specific analysis measured efficiency need a primary source; otherwise label proposal.

## Questions to ask the user

Which population defines the denominator of each efficiency? Which control sample and is it signal-free? Do you have a generation record (surface, solid angle, spectrum)? Which species and range? Is the response matrix conditional on selection or does it include inefficiency? Which templates and how were they derived?
