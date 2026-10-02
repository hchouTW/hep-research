---
name: detector-response
description: "Use when the deliverable is about how a detector responds: signal formation and readout, reconstruction (tracking, vertexing, calorimetry, particle identification, timing, Cherenkov/RICH, TRD, TOF, muon systems), calibration and alignment, efficiency and resolution measurement (tag-and-probe, truth matching), detector simulation (Geant4), data/MC agreement, conditions and their provenance, response matrices, and parametrized response for recasting. Works for collider, fixed-target, neutrino, rare-event, and space or ground-based astroparticle instruments, with or without an experiment profile. Not for measurement design or background estimation (hep-analysis), unfolding algorithms, fits or limits (hep-statistics), theory or event-generator physics (hep-theory), or generic code debugging (hep-computing)."
---

# detector-response: detector performance and response

**Owns:** signal formation, reconstruction, calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, and the definition of response matrices.
**Typical artifacts:** `response` (truth/reco axes, orientation, normalization, what sits inside the matrix), performance reports, conditions provenance.
**Never:** invent detector facts; detector specifics come from an experiment profile, the user, or are `unknown`. Inference on top of a response belongs to hep-statistics.

## Invariants

- Declare matrix orientation, normalization convention, where inefficiency and acceptance live (inside or outside the matrix), underflow/overflow handling, and which corrections are included. A correction inside the matrix is never applied again outside it.
- Truth and reco variables are named with units; if they differ, the conversion and Jacobian are stated.
- Efficiencies are conditional probabilities with a named denominator; resolution is reported with the core and the tails separately, and non-Gaussian tails are measured, not assumed.
- Calibration is legitimate when it uses independent control samples with provenance; tuning toward the expected signal outcome is flagged.
- Conditions are time-dependent until shown otherwise; record periods and versions.
- A passing validator means self-consistency under declared metadata, not physical validity.

## Workflow

1. Resolve context (stanza below); load only the subsystem modules the question needs.
2. State the quantity (efficiency, resolution, scale, response matrix) and its conditioning.
3. Choose the reference: truth matching in simulation, tag-and-probe or control sample in data, or both with a data/MC comparison.
4. Report central value, statistical and systematic components, validity range, and conditions.
5. Write the `response` artifact when another skill consumes it; validate it.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
<!-- END context-resolution -->

## Resources

Migrated detector references (detector systems, tracking, calorimetry, PID, reconstruction performance, calibration, simulation, astroparticle instruments) arrive in M2 under `references/`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Unfolding, forward folding, fits using the response | hep-statistics | `response` |
| Measurement design using the performance numbers | hep-analysis | `response` / report |
| Simulation production, conditions database code | hep-computing | `computational-run` |
| ML-based reconstruction or calibration | physics-ml | `ml-artifact` |

<!-- example: routing -->
- "AMS-02 RICH velocity resolution vs charge" → this skill + `experiment:ams-02` subsystem module only.
- "Parametrized muon efficiency for recasting a published search" → this skill (parametrized response), then hep-statistics.
<!-- /example -->
