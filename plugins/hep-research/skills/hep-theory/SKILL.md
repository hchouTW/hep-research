---
name: hep-theory
description: "Use when the deliverable is a theoretical or phenomenological result: model definition and conventions (units, metric, couplings, schemes, scales), symbolic or analytic derivations, amplitudes, cross sections, decay rates and widths, whether a process or Feynman diagram is allowed (selection rules), approximations and validity domains, theory uncertainties (scale envelopes, truncation, PDFs, model alternatives), event-generation physics (ME order, shower, matching, weights), SMEFT conventions, consistency checks, predictions for comparing a model with an experiment's published data, and recasting a published analysis. Works with no experiment. Load it first even for a quick derivation, cross section or recast, and for topics outside v1 (lattice QCD, EFT global fits), where it says what it cannot cover. Not for: measurement design (hep-analysis), detector response (detector-response), fits and limits (hep-statistics), code (hep-computing), manuscripts (research-communication)."
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

1. First read `hep-research.project.json` if present and any profile it binds (stanza below). Load a theory-domain profile only if one is named or configured.
2. Write the theory spec: model, assumptions, conventions, order, parameters, scales, validity domain.
3. Derive (symbolically where useful), recording status and each check. Use hep-computing for heavy numerics.
4. Produce the prediction in the observable space it will be compared in, with uncertainties by type and allowed transformations.
5. For comparisons with data, state the dataset record and hand the inference to hep-statistics.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`; `<plugin root>/...` paths are relative to it.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile found in neither place may come from a companion plugin: load the installed `<plugin>:profile` skill that names it and use the folder it gives as a local profile. If none is installed, say the profile is unavailable; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language (for example English or Traditional Chinese); keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

References under `references/`: [mathematical reasoning and proof status](references/mathematical-reasoning-and-proof.md) (derivation validity, approximation domains, counterexamples, separating derivation from numerical corroboration), [higher-order predictions](references/higher-order-predictions.md) (scale envelopes, truncation), [PDFs and LHAPDF](references/pdfs-and-lhapdf.md), [SMEFT and EFT conventions](references/smeft-and-eft.md), [cosmic-ray propagation](references/cosmic-ray-propagation.md) (models, degeneracies; fits outside v1), [event-generation physics](references/event-generation.md), [recasting toolchain](references/recasting-toolchain.md) (MadGraph, Rivet, Delphes, SModelS, MadAnalysis 5; templates documented, not run) and [DIS kinematics](references/dis-kinematics.md) (invariants, beam relations, Jacobians, frames). Scripts in `<plugin root>/skills/hep-theory/scripts/`: `dis_kinematics.py`, `pdf_uncertainty.py`, `event_weights.py`, `eft_truncation.py`. A HEPData table becomes a dataset record with `<plugin root>/adapters/hepdata/assets/hepdata_record.py` (tested on synthetic tables); `<plugin root>/adapters/hepdata/assets/hepdata_export.py` writes a binned record back as a HEPData submission. Scientific-ML boundaries are in `<plugin root>/skills/physics-ml/references/scientific-machine-learning.md`. Shipped theory-domain profiles are listed in `<plugin root>/profiles/registry.json`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Fit, interval, limit, model comparison | hep-statistics | `prediction` + dataset record |
| Numerical convergence, symbolic/numeric cross-check code | hep-computing | `computational-run` |
| Folding into detector space | detector-response then hep-statistics | `prediction` |
| Surrogate of an expensive prediction | physics-ml | `prediction` (validity domain) |
| Paper section or Feynman diagram rendering | research-communication | `communication` |
