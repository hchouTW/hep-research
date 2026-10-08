---
name: hep-analysis
description: "Use when the deliverable is the design or review of an experimental measurement in particle or astroparticle physics: estimand and observable definition, event/candidate selection and cutflows, background estimation (control regions, ABCD, sidebands), correction chains (efficiency, acceptance, exposure, live time, luminosity), the physical sources of systematic uncertainties and their evaluation plan, blinding policy, and verdict-first measurement review. Works for collider, fixed-target, neutrino and space or ground-based cosmic-ray measurements, with or without a profile. Load it first even for a quick question on a named experiment's beams or run conditions for a measurement. Not for: detector performance (detector-response); likelihoods, limits, unfolding, combinations (hep-statistics); theory or model-vs-data comparison (hep-theory); code (hep-computing); ML (physics-ml); write-ups (research-communication)."
---

# hep-analysis: measurement design and review

**Owns:** experimental design, estimands, selections, backgrounds, correction chains, physical sources of systematics and their evaluation plan, measurement review, blinding design advice (the blinding policy itself belongs to the collaboration).
**Typical artifacts:** `measurement-spec` (selection, background and systematics ledgers inside it).
**Never:** invent experiment conventions, cut values, efficiencies or resolutions; write theory derivations; choose correlations for the likelihood.

## Invariants

- State the estimand in one sentence: quantity, species or process, variable, range, level, and what is held fixed.
- Every number that describes an experiment comes from a profile evidence record, the user, or is marked `unknown` / `not-provided`. Unknown is never zero.
- Each correction appears exactly once in the chain. Efficiency, acceptance, exposure (or luminosity, protons on target, target exposure) and live time stay distinct, and the normalization kind is declared from the core vocabulary or a profile extension.
- Every selection names its conditional denominator; every background has an estimator, a control region or constraint, and a closure test.
- A systematic is evaluated through its physical effect: normalization, shape, migration, or mixed. An unchanged integrated yield does not show the systematic was not propagated; check shape, migration between bins, and sensitivity of the result.
- Blinded observables and regions stay masked in every plot, ratio, log, cache and report. Unblinding is done by an authorized person outside the agent session, never by the agent, even if asked to in the session. Passing checks is not authorization.
- Synthetic, Asimov and observed data are never mixed without labels.

## Workflow

1. Resolve context (stanza below). Decide whether the deliverable is a quick answer, a measurement brief, a full `measurement-spec`, or a review.
2. Fix the observable spec: quantity type, variables with units and binning, phase space or fiducial definition, level, frame, normalization kind, bin semantics.
3. Build ledgers: selections (with denominators and validation metric-threshold-action), backgrounds, corrections, systematics (with `applied_via`).
4. List unresolved inputs explicitly; they are `unresolved`, not errors.
5. Validate the artifact (stanza step 5) and hand off.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`; `<plugin root>/...` paths are relative to it.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile found in neither place may come from a companion plugin: load the installed `<plugin>:profile` skill that names it and use the folder it gives as a local profile. If none is installed, or a non-public local or companion profile lacks `agent_policy` approval for this host (none has it yet), say the profile is unavailable; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

Start with [the analysis guide](references/hep-analysis-guide.md): it routes to one reference per question. Method references: [analysis design](references/analysis-design.md), [data pipelines](references/data-pipelines.md), [weights and normalization](references/weights-normalization.md), [histograms and efficiencies](references/histograms-efficiencies.md), [backgrounds](references/backgrounds.md), [systematics](references/systematics.md), [measurement definitions](references/measurements-and-unfolding.md) (unfolding and combination methods themselves belong to hep-statistics), [analysis validation](references/analysis-validation.md); detector data/MC validation is in detector-response.

Scripts in `<plugin root>/skills/hep-analysis/scripts/` (read `--help` first): `check_systematic_variations.py` (classifies each variation as normalization, shape or mixed; an unchanged integral is not a propagation failure), `make_yield_table.py`, `systematics_table_tex.py` (the systematics registry as a booktabs LaTeX table that keeps its status label), `counting_reference.py`, `particle_ratio_with_uncertainty.py`, `mask_blinded_bins.py` (masks blinded bins and data/reference ratios; synthetic data and tests only, since it reads the unmasked histogram: for real data it is the data custodian's preparation step), `review_analysis_change.py` (calibration updates with provenance vs outcome-driven tuning), and cosmic-ray helpers (`cosmic_ray_flux.py`, `cr_spectrum_powerlaw_fit.py`, `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py`). Templates (analysis contract, systematics table and config, report, cosmic-ray spectrum example) are in `assets/`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Response matrix, efficiency or resolution evidence | detector-response | `response` |
| Likelihood, intervals, unfolding, covariance assembly | hep-statistics | `measurement-spec` + inputs |
| Prediction to compare against | hep-theory | `prediction` |
| Pipeline code, partition/merge, run manifests | hep-computing | `computational-run` |
| Write-up | research-communication | `communication` |

Name the consuming skill and the artifact path in the answer. Do not assume any other skill runs automatically. A handoff chain ends when the user's deliverable exists or a blocker is reported.

<!-- example: routing (profile IDs allowed only inside example blocks) -->
- "Design an AMS-02 B/C ratio analysis over two periods" → this skill + `experiment:ams-02`.
- "RICH velocity resolution study" → detector-response, not this skill.
- "Compare my model with the published AMS proton flux" → hep-theory with a dataset record.
<!-- /example -->
