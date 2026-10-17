---
name: hep-measurement
description: "Use when the deliverable is the design or review of an experimental measurement in particle or astroparticle physics: estimand and observable definition, event/candidate selection and cutflows, background estimation (control regions, ABCD, sidebands), correction chains (efficiency, acceptance, exposure, live time, luminosity), the physical sources of systematic uncertainties and their evaluation plan, blinding policy, and verdict-first measurement review. For collider, fixed-target, neutrino and cosmic-ray measurements, with or without a profile. Load it first even for a quick question on a named experiment's beams or run conditions for a measurement. Not for: detector performance (hep-detector); likelihoods, limits, unfolding, combinations (hep-statistics); theory or model-vs-data comparison (hep-theory); code (hep-computing); ML (hep-ml); write-ups (hep-communication)."
---

# hep-measurement: measurement design and review

**Owns:** experimental design, estimands, selections, backgrounds, correction chains, physical sources of systematics, their correlation evidence and evaluation plan, measurement review, blinding design advice (the blinding policy itself belongs to the collaboration).
**Typical artifacts:** `measurement-spec` (selection, background and systematics ledgers inside it).
**Never:** invent experiment conventions, cut values, efficiencies or resolutions; write theory derivations; encode correlations in the likelihood.
**Correlations:** hep-measurement supplies the physical correlation evidence and a proposed scheme with its justification; hep-statistics encodes it in the likelihood and checks positive semidefiniteness.

## Invariants

- State the estimand in one sentence: quantity, species or process, variable, range, level, and what is held fixed.
- Every number that describes an experiment comes from a profile evidence record, the user, or is marked `unknown` / `not-provided`. Unknown is never zero.
- Each correction appears exactly once in the chain. Efficiency, acceptance, exposure (or luminosity, protons on target, target exposure) and live time stay distinct, and the normalization kind is declared from the core vocabulary or a profile extension.
- Every selection names its conditional denominator; every background has an estimator, a control region or constraint, and a closure test.
- A systematic is evaluated through its physical effect: normalization, shape, migration, or mixed. An unchanged integrated yield does not show the systematic was not propagated; check shape, migration between bins, and sensitivity of the result.
- Blinded observables and regions stay masked in every plot, ratio, log, cache and report, and only an authorized person unblinds, outside the agent session, never the agent even if asked; passing checks is not authorization ([blinding](references/analysis-design.md#blinding)).
- Synthetic, Asimov and observed data are never mixed without labels.

## Workflow

1. Resolve context (stanza below). Decide whether the deliverable is a quick answer, a measurement brief, a full `measurement-spec`, or a review; a review gives its verdict first ([review procedure](references/review-and-artifacts.md)).
2. Fix the observable spec: quantity type, variables with units and binning, phase space or fiducial definition, level, frame, normalization kind, bin semantics.
3. Build ledgers: selections (with denominators and validation metric-threshold-action), backgrounds, corrections, systematics (with `applied_via`).
4. List unresolved inputs explicitly; they are `unresolved`, not errors.
5. Validate: `python3 "<plugin root>/contracts/validate.py" <artifact.json> [--profiles-from <hep-research.project.json>]`, then hand off.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Any measurement question: check-first proposals, invariants, routing | [analysis guide](references/hep-measurement-guide.md) |
| Design, triggers, optimization, blinding | [analysis design](references/analysis-design.md); `mask_blinded_bins.py` (synthetic only) |
| Estimand, fiducial definitions, result levels | [measurements and unfolding](references/measurements-and-unfolding.md) |
| Efficiencies, exposure, live time, collection time, luminosity, POT | [correction chain](references/correction-chain.md); `collection_time.py` |
| Backgrounds: control regions, ABCD, sidebands | [backgrounds](references/backgrounds.md) |
| Physical sources of systematics, variations, scaling class | [systematics](references/systematics.md); `check_systematic_variations.py`, `systematics_table_tex.py` |
| Normalization, signed weights, cutflows, yields | [weights and normalization](references/weights-normalization.md); `make_yield_table.py` |
| Histograms, efficiencies with uncertainties | [histograms and efficiencies](references/histograms-efficiencies.md) |
| Validation, review checks, preservation | [analysis validation](references/analysis-validation.md) |
| Review a spec or a change; deliverables | [review and artifacts](references/review-and-artifacts.md); `review_measurement_spec.py`, `review_analysis_change.py` |
| Cosmic-ray flux, ratios, isotopes, anisotropy | [cosmic-ray measurements](references/cosmic-ray-measurements.md); `cosmic_ray_flux.py`, `cr_spectrum_powerlaw_fit.py` |
| Geomagnetic cutoff, solar modulation | `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py` |
| Counting reference, ratio of two yields | `counting_reference.py`, `particle_ratio_with_uncertainty.py` |
| A named experiment's beams or run conditions | the bound profile's `index.md` |

Scripts in `<plugin root>/skills/hep-measurement/scripts/` (read `--help` first; the analysis guide's "Executable resources" describes each). Spec template and field guide: `assets/measurement_spec.template.{json,md}`. Unfolding and combination methods belong to hep-statistics; detector data/MC validation to hep-detector. Folder guide: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Response matrix, efficiency or resolution evidence | hep-detector | `response` |
| Likelihood, intervals, unfolding, covariance assembly | hep-statistics | `measurement-spec` + inputs |
| Prediction to compare against | hep-theory | `prediction` |
| Classifier or BDT training, working point | hep-ml | `ml-artifact` |
| Pipeline code, partition/merge, run manifests | hep-computing | `computational-run` |
| Write-up | hep-communication | `communication` |

Name the consuming skill and the artifact path; no other skill runs automatically; a handoff chain ends at the deliverable or a reported blocker.

<!-- example: routing -->
- "Design an AMS-02 B/C ratio analysis over two periods" → this skill + `experiment:ams-02`.
- "RICH velocity resolution study" → hep-detector, not this skill.
- "Compare my model with the published AMS proton flux" → hep-theory with a dataset record.
<!-- /example -->
