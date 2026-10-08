---
name: detector-response
description: "Use when the deliverable is about how a detector responds: signal formation and readout, reconstruction (tracking, vertexing, calorimetry, particle identification, timing, Cherenkov/RICH, TRD, TOF, muon systems), calibration and alignment, efficiency and resolution measurement (tag-and-probe, truth matching), detector simulation (Geant4), data/MC agreement, conditions and their provenance, response matrices, folding a prediction through the response, and parametrized response for recasting. Works for collider, fixed-target, neutrino, rare-event and astroparticle instruments, with or without a profile. Load it first even for a quick question on a named experiment's detector or resolution: it reads the profile and asks which configuration is meant instead of quoting from memory. Not for: measurement design (hep-analysis); unfolding, fits, limits (hep-statistics); theory (hep-theory); generic code (hep-computing)."
---

# detector-response: detector performance and response

**Owns:** signal formation, reconstruction, calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, response matrices, forward folding of predictions, double-counting checks.
**Typical artifacts:** `response` (truth/reco axes, orientation, normalization, what sits inside the matrix), performance reports, conditions provenance.
**Never:** invent detector facts; detector specifics come from an experiment profile, the user, or are `unknown`. Inference on top of a response belongs to hep-statistics.

## Invariants

- Declare matrix orientation, normalization convention, where inefficiency and acceptance live (inside or outside the matrix), underflow/overflow handling, and which corrections are included. A correction inside the matrix is never applied again outside it.
- Truth and reco variables are named with units; if they differ, the conversion and Jacobian are stated.
- Efficiencies are conditional probabilities with a named denominator; resolution is reported with the core and the tails separately, and non-Gaussian tails are measured, not assumed.
- Calibration is legitimate when it uses independent control samples with provenance; tuning toward the expected signal outcome is flagged.
- Conditions are time-dependent until shown otherwise; record periods and versions.
- A passing validator shows self-consistency under declared metadata, not physical validity.

## Workflow

1. Resolve context (stanza below); then only needed subsystem modules.
2. State the quantity (efficiency, resolution, scale, response matrix) and its conditioning.
3. Choose the reference: truth matching in simulation, tag-and-probe or control sample in data, or both with a data/MC comparison.
4. Report central value, statistical and systematic parts, validity range, and conditions.
5. Write and validate the `response` artifact when another skill consumes it.

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

Start with [the principles summary](references/detector-principles-summary.md), then the topic needed: [measurement framework](references/detector-measurement-framework.md), [core equations](references/core-detector-equations.md), [signal formation and readout](references/signal-formation-and-readout.md), [detector systems](references/detector-systems-overview.md), [tracking](references/tracking-and-vertexing.md), [gaseous tracking](references/gaseous-and-specialized-tracking-technologies.md), [timing](references/timing-detectors.md), [calorimetry](references/calorimetry-ecal-hcal.md), [PID](references/particle-identification.md), [Cherenkov and photosensors](references/cherenkov-imaging-variants-and-photosensors.md), [muon systems](references/muon-systems.md), [noble-liquid, neutrino and rare-event detectors](references/noble-liquid-neutrino-and-rare-event-detectors.md), [physics objects](references/physics-objects-jets-btagging-met.md), [triggers, luminosity and pileup](references/triggers-luminosity-pileup.md), [reconstruction](references/event-reconstruction.md), [truth matching](references/reconstruction-performance-and-truth-matching.md), [performance metrics](references/performance-metrics-and-residual-diagnostics.md), [folding](references/response-and-forward-folding.md), [data/MC and systematics](references/data-mc-validation-and-detector-systematics.md), [simulation](references/detector-simulation.md), [calibration and alignment](references/calibration-and-alignment.md), [case studies](references/detector-case-studies-and-checklists.md), [comparison tables](references/detector-comparison-tables.md), [glossary](references/detector-glossary.md), [bibliography](references/detector-principles-bibliography.md). Astroparticle instruments: [cosmic-ray spectrum](references/cosmic-ray-spectrum-and-composition.md), [air showers](references/extensive-air-showers.md), [ground arrays](references/ground-based-detection-arrays.md), [IACTs](references/imaging-atmospheric-cherenkov.md), [neutrino telescopes](references/neutrino-astronomy.md), [space-based detectors](references/space-based-direct-detection.md), [multimessenger analysis](references/multimessenger-analysis.md).

Scripts in `<plugin root>/skills/detector-response/scripts/` (read `--help` first): `calorimeter_resolution.py`, `cherenkov_angle.py`, `multiple_scattering.py`, `pid_separation_power.py`, `pileup_reweight.py`, `tag_and_probe_efficiency.py`, `xmax_gaisser_hillas.py`. Example inputs: `assets/`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Unfolding, fits on the response | hep-statistics | `response` |
| Measurement design using these numbers | hep-analysis | `response` / report |
| Simulation production, conditions code | hep-computing | `computational-run` |
| ML-based reconstruction or calibration | physics-ml | `ml-artifact` |
| Writing up results | research-communication | report |

<!-- example: routing -->
- "AMS-02 RICH velocity resolution vs charge" → this skill + `experiment:ams-02` subsystem module only.
- "Parametrized muon efficiency for recasting a published search" → this skill, then hep-statistics.
<!-- /example -->
