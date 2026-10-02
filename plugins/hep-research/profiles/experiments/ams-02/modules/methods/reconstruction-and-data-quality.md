# Reconstruction, Selection, and Data Quality

> Method owner: [detector-response](../../../../../skills/detector-response/SKILL.md) defines the general method (reconstruction and data-quality methods). This module records how AMS-02 analyses apply it. General statements here are snapshots carried from the legacy `ams-analysis` skill; where they differ from the owner, the owner's text applies.

## When to read this file

Read when defining or reviewing reconstruction objects, matching, cut flows, run/event quality, time dependence, or the separation of training/tuning/control/measurement samples. It owns the **conditions model** and the **four-category distinction** (veto, calibration, efficiency, response). Subsystem physics is in [detector-and-observables](../subsystems/detector-and-observables.md); calibrations and MC provenance in [calibration-mc-systematics](../methods/calibration-mc-systematics.md).

## Contents

1. [Reconstruction objects and matching](#reconstruction-objects-and-matching)
2. [Cut-flow ledger](#cut-flow-ledger)
3. [Run and event quality](#run-and-event-quality)
4. [Conditions model](#conditions-model)
5. [Four categories of correction](#four-categories-of-correction)
6. [Sample separation and leakage prevention](#sample-separation-and-leakage-prevention)
7. [Diagnostic plots](#diagnostic-plots)
8. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Reconstruction objects and matching

**Purpose.** Decide what an "event" and "track" mean before any efficiency is defined. **Inputs.** Per-subsystem reconstructed objects (Tracker track and charge estimates, TOF hits and `β`, TRD track segment and discriminant, ECAL shower, RICH ring, ACC activity) and their software version. **Definitions.** Measurement-level objects are what the reconstruction returns; truth-level objects exist only in MC. A "matched" object is matched under a stated criterion (geometric residual, time, charge consistency); the criterion is part of the selection. **Procedure.** (1) Fix the primary particle definition (e.g. downward-going, single track, charge `|Z|` compatible); (2) list which subsystems must contribute and which are optional; (3) state matching criteria between Tracker and TOF/TRD/ECAL/RICH; (4) state the truth definition used in MC (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md)). **Dependencies.** Reconstruction version, alignment, calibration interval, MC digitization. **Validation.** Matching-residual distributions in data and MC, efficiency of each match vs `R`, angle, region, time. **Output.** An object ledger: object, definition, subsystems, criteria, version.

Public AMS reconstruction algorithms exist only in publications; **do not assume internal pass names or algorithm parameters**. If the user names a pass or software version, treat it as user-supplied and flag that the skill cannot verify it.

## Cut-flow ledger

For every cut the analysis must state: the **targeted background or failure mode**, **signal efficiency**, **efficiency method** (data-driven, MC, hybrid), **correlations with other cuts**, **MC dependence**, **effect on response or shape (sculpting)**, and the **stability variation** used to test it. Use the ledger below (canonical; referenced by other files).

```yaml
selection:
  name: null
  level: event | track | subsystem | truth
  definition: null            # observables and how thresholds are set; numeric only if user-supplied/sourced
  target_failure_mode: null
  conditional_denominator: null   # exactly what population the efficiency is conditional on
  efficiency_source: data | simulation | hybrid
  correlated_with: []
  sculpts_observables: []     # e.g. rigidity spectrum, charge estimator shape, discriminant shape
  validation: []
  uncertainty: null
```

**Ordering rule.** A cut flow is an ordered conditional chain; the efficiency of a later cut is conditional on all earlier ones. Reordering changes individual efficiencies but not the total; the total is what must close (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md#conditional-efficiencies)).

**Numeric thresholds.** Give a threshold only when a source or the user supplies it. Otherwise describe: the optimization metric (e.g. background rejection at fixed efficiency on an independent sample), the optimization sample (not the measurement sample), and the validation (data/MC agreement of the discriminant, stability of the result when the cut varies).

## Run and event quality

Checks to enumerate (all inputs, not AMS practice unless a source says so): run/event quality flags; detector status per subsystem; livetime and time intervals; trigger type and **prescales**; **unbiased trigger samples** for efficiency measurements; track multiplicity; hit pattern; fit quality; lever arm; fiducial geometry; cross-subsystem matching; direction; charge consistency across subsystems; shower/ring quality; correlations between selections; observable sculpting.

Good-run rules, bad-period lists, and quality flags used inside the Collaboration are **not public**; treat any list as analyst-supplied and record its version.

## Conditions model

Every time-dependent detector condition needs a row. Template (fill with user inputs; do not fill with invented values):

| Condition | May change with time? | Validity granularity of the calibration | Source of calibration | Effect if bad | Handling |
|---|---|---|---|---|---|
| Tracker alignment | Yes (thermal, orbital, long-term) | Per interval defined by the analysis | Flight data with physical constraints | Rigidity scale/resolution shift | Correct per interval; residual drift → systematic |
| Tracker hit efficiency / noisy channels | Yes | Per run/period | Flight data | Efficiency, resolution | Map, exposure removal if unavailable |
| Magnetic field | Slow (temperature) | Long | Ground measurement + flight checks | `R` scale | Scale validation with redundant measure |
| TOF timing offsets, slewing | Yes | Per period | Flight data | `β`, direction | Recalibrate; efficiency separate from trigger |
| TRD gas and gain | Yes | Short (hours-days) | Flight data | Discriminant shape | Time-dependent templates |
| ECAL cell gains, energy scale | Yes (slow) | Per period | Flight data | Energy scale/linearity | Recalibration; scale systematic |
| RICH refractive index, alignment | Yes | Per period | Flight data | `β` bias | Recalibrate; region-dependent |
| ACC thresholds/inefficiency | Slow | Per period | Flight data | Veto efficiency | Efficiency measure |
| Geomagnetic environment / solar activity | Continuous | Orbit / rotation | Field model + ephemeris | Primary selection, low-`R` flux | Cutoff per event, time bins |
| Configuration changes (hardware, reconstruction version) | Discrete | Between eras | Collaboration documentation | Breaks response | Treat as separate periods |

**Which quantities come from where.** Flight data, beam tests, ground tests and simulation each calibrate different quantities. Record which; do not assert an AMS-specific origin without a source.

**Temporal analyses.** Time-resolved fluxes, solar-cycle comparisons and periodicity searches add binning, per-bin exposure and correlation questions: see [time-dependent-analysis](../periods/time-dependent-analysis.md).

**Version invalidation.** A change in reconstruction or calibration version changes reconstructed observables and hence efficiencies, response and templates; MC response products must be regenerated (or shown to be insensitive) for the new version. A results table mixing MC from one version with data from another is a defect (see [calibration-mc-systematics](../methods/calibration-mc-systematics.md#mc-provenance)).

**Hardware eras.** If the analysis spans a documented hardware configuration change, split by era or justify a combined treatment. Public documents describe some changes (e.g. a Tracker upgrade announced on the Collaboration site); verify date and scope in the primary source before citing.

## Four categories of correction

| Category | Changes what | Example | Rule |
|---|---|---|---|
| Data-quality veto | Removes exposure (time) | Excluding a period with unavailable subsystem | Reduce livetime/exposure accordingly; do not also correct efficiency for the same period |
| Calibration correction | Changes reconstructed observable | Time-dependent energy scale | Applied before selection and response; residual becomes a scale systematic |
| Efficiency correction | Changes normalization | Trigger or selection inefficiency | Measured as a conditional efficiency with named denominator |
| Response uncertainty | Changes migration | Rigidity resolution tail | Enters the response matrix and its variations |

**Anti-double-counting.** A single physical effect (e.g. a drifting TRD gain) must be treated in exactly one category; if a calibration removes it, a residual systematic covers only what remains, and the efficiency correction does not also include it. Record the category in the systematic ledger (see [calibration-mc-systematics](../methods/calibration-mc-systematics.md#systematic-ledger)).

## Sample separation and leakage prevention

Maintain at least four disjoint roles: **training** (classifiers, templates derived from data), **tuning** (cut/threshold choice), **control** (efficiency and background validation), **measurement** (the result). Checks: no event appears in two roles; controls do not contain the measured signal at a level that biases the efficiency (control contamination); a variable used in the selection is not also used to derive the template that measures its own efficiency without a correction; repeated tuning on the same data is disclosed and accounted for (blinding or masking where appropriate, especially for rare events). Input-variable audit for any classifier: no variable that encodes the target (e.g. rigidity charge sign) directly or indirectly.

## Diagnostic plots

For each stability plot specify the **expected invariant or correction model** and how residual drift becomes a systematic:

- Versus time: an abundant control species' rate or an efficiency; expect flat after livetime and cutoff correction; drift → time-dependent systematic or period split.
- Versus orbital/geographic coordinates: expect dependence only through the geomagnetic cutoff and known environment.
- Versus incidence geometry and detector region: expect smooth acceptance; sharp features → alignment or dead-region issue.
- Versus rigidity/energy: expect smooth efficiency; steps → selection sculpting or calibration boundary.
- Versus charge (`|Z|`, sign): expect only physical differences; sign asymmetry not explained by physics → charge-dependent bias.

## Failure modes

- Cut flow with unnamed denominators, so efficiencies cannot be combined.
- Measurement and control samples overlap; classifier trained on the measurement sample.
- Prescales or unbiased-trigger samples ignored; livetime taken as the calendar interval.
- Version mismatch between data reconstruction and MC production.
- A time-dependent effect corrected once as a veto and again as an efficiency.
- Invented good-run rules or pass names presented as AMS practice.

## Required source classes

Tier 1 AMS paper methods/supplement sections for the selections and data periods of any specific result; Tier 2 detector documentation for subsystem status; general method references (Tier 4) for tag-and-probe and closure. Internal good-run rules and versions are **user-supplied**, never cited.

## Questions to ask the user

Data or MC, and which reconstruction/production version? Which hardware era and time interval? Which trigger and are unbiased/prescaled samples available? Which quality flags/good-run list are you applying (supplied by you)? Which samples are already used for training or tuning?
