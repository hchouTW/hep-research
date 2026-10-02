---
name: hep-theory
description: "Use when the deliverable is a theoretical or phenomenological result: model definition, assumptions and conventions (units, metric, couplings, schemes, scales), symbolic or analytic derivations, amplitudes, cross sections, decay rates and other predictions, approximations and validity domains, theory uncertainty prescriptions (scale envelopes, truncation, model alternatives), event-generation physics (matrix-element order, PDFs, shower, matching/merging, weights), consistency checks, and comparing a model with an experiment's published data or recasting a published analysis (predictions in the published observable space). Works with no experiment at all. Not for measurement design (hep-analysis), detector response (detector-response), fitting or limit-setting itself (hep-statistics), numerical code engineering (hep-computing), or manuscript writing (research-communication)."
---

# hep-theory: models, derivations, predictions

**Owns:** models, assumptions, conventions, derivations, predictions, event-generation physics, approximations, validity, theory-uncertainty prescriptions, consistency checks; definitions of units, constants and generic kinematics.
**Typical artifacts:** `theory-spec` (with a Markdown derivation record carrying a JSON header), `prediction` (JSON plus CSV for grids, explicit units).
**Never:** require experiment, detector, data or blinding fields; claim support for a domain because a tool ran; report numerical agreement as proof.

## Invariants

- Every result carries a derivation status from the core vocabulary: formal proof, analytic derivation, perturbative argument (state the order), asymptotic argument (state the limit), heuristic argument, numerical evidence, empirical observation, conjecture, not derived. Never upgrade a status when reusing a result.
- A conventions block travels with every derivation and prediction: unit system, whether hbar = c = 1, metric signature, coupling normalization, scheme, scales, energy variable, frame, angle definition, spin treatment, mass approximation.
- State the validity domain and what was neglected. Inapplicable fields are marked `not-applicable`, not left blank.
- Independent checks are listed as run or not run: units and dimensions, known limits, symmetries, normalization, analytic vs numerical integration with a stated tolerance and convergence study. Termination of a computation is not convergence.
- Benchmarks cite an authoritative source that was actually read, with its exact location.
- Scale envelopes, truncation estimates and model alternatives are distinct uncertainty objects and are never turned into Gaussians without a stated prescription.
- A request outside the validated theory profiles gets an explicit "no validated domain profile" notice, then general discipline.

## Workflow

1. Resolve context (stanza below). Load a theory-domain profile only if one is named or configured.
2. Write the theory spec: model, assumptions, conventions, order, parameters, scales, validity domain.
3. Derive (symbolically where useful), recording status and each check. Use hep-computing for heavy numerics.
4. Produce the prediction in the observable space it will be compared in, with uncertainties by type and allowed transformations.
5. For comparisons with data, state the dataset record and hand the inference to hep-statistics.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
<!-- END context-resolution -->

## Resources

Migrated references (mathematical reasoning and proof status, event-generation physics, scientific-ML boundaries) arrive in M2 under `references/`; the first theory-domain profile arrives in M3.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Fit, interval, limit, model comparison | hep-statistics | `prediction` + dataset record |
| Numerical convergence, symbolic/numeric cross-check code | hep-computing | `computational-run` |
| Folding into detector space | detector-response then hep-statistics | `prediction` |
| Surrogate of an expensive prediction | physics-ml | `prediction` (validity domain) |
| Paper section or Feynman diagram rendering | research-communication | `communication` |
