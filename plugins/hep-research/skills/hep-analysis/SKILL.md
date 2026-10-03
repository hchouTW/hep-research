---
name: hep-analysis
description: "Use when the deliverable is the design or review of an experimental measurement in particle or astroparticle physics: estimand and observable definition, event/candidate selection and cutflows, background estimation (control regions, ABCD, sidebands), correction chains (efficiency, acceptance, exposure, live time, luminosity), the physical sources of systematic uncertainties and their evaluation plan, blinding policy, and verdict-first measurement review. Works for collider, fixed-target, neutrino and space or ground-based cosmic-ray measurements, with or without an experiment profile. Not for detector performance or calibration studies (detector-response), likelihoods, limits, unfolding algorithms or combinations (hep-statistics), theory predictions or comparing a model with published data (hep-theory), code debugging (hep-computing), ML training (physics-ml), or writing up results (research-communication)."
---

# hep-analysis: measurement design and review

**Owns:** experimental design, estimands, selections, backgrounds, correction chains, physical sources of systematics and their evaluation plan, measurement review, blinding policy.
**Typical artifacts:** `measurement-spec` (selection, background and systematics ledgers inside it).
**Never:** invent experiment conventions, cut values, efficiencies or resolutions; write theory derivations; choose correlations for the likelihood.

## Invariants

- State the estimand in one sentence: quantity, species or process, variable, range, level, and what is held fixed.
- Every number that describes an experiment comes from a profile evidence record, the user, or is marked `unknown` / `not-provided`. Unknown is never zero.
- Each correction appears exactly once in the chain. Efficiency, acceptance, exposure (or luminosity, protons on target, target exposure) and live time stay distinct, and the normalization kind is declared from the core vocabulary or a profile extension.
- Every selection names its conditional denominator; every background has an estimator, a control region or constraint, and a closure test.
- A systematic is evaluated through its physical effect: normalization, shape, migration, or mixed. An unchanged integrated yield does not show the systematic was not propagated; check shape, migration between bins, and sensitivity of the result.
- Blinded observables and regions stay masked in every plot, ratio, log, cache and report until unblinding is authorized by the user or their collaboration process. Passing checks is not authorization.
- Synthetic, Asimov and observed data are never mixed without labels.

## Workflow

1. Resolve context (stanza below). Decide whether the deliverable is a quick answer, a measurement brief, a full `measurement-spec`, or a review.
2. Fix the observable spec: quantity type, variables with units and binning, phase space or fiducial definition, level, frame, normalization kind, bin semantics.
3. Build ledgers: selections (with denominators and validation metric-threshold-action), backgrounds, corrections, systematics (with `applied_via`).
4. List unresolved inputs explicitly; they are `unresolved`, not errors.
5. Validate the artifact (stanza step 5) and hand off.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the language the user writes in (for example English or Traditional Chinese); keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

Start with [the analysis guide](references/hep-analysis-guide.md): it routes to one reference per question. Method references: [analysis design](references/analysis-design.md), [data pipelines](references/data-pipelines.md), [weights and normalization](references/weights-normalization.md), [histograms and efficiencies](references/histograms-efficiencies.md), [backgrounds](references/backgrounds.md), [systematics](references/systematics.md), [measurement definitions](references/measurements-and-unfolding.md) (unfolding and combination methods themselves belong to hep-statistics), [analysis validation](references/analysis-validation.md); detector data/MC validation is in detector-response.

Scripts in `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/` (read `--help` first): `check_systematic_variations.py` (classifies each variation as normalization, shape or mixed; an unchanged integral is not a propagation failure), `make_yield_table.py`, `counting_reference.py`, `particle_ratio_with_uncertainty.py`, `mask_blinded_bins.py` (masks blinded bins and data/reference ratios before plotting or tabulating), `review_analysis_change.py` (calibration updates with provenance vs outcome-driven tuning), and cosmic-ray helpers (`cosmic_ray_flux.py`, `cr_spectrum_powerlaw_fit.py`, `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py`). Templates (analysis contract, systematics table and config, report, cosmic-ray spectrum example) are in `assets/`.

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
