---
name: hep-detector
description: "Use when the deliverable is about how a detector responds: signal formation and readout, design principles and trade-offs, sourced facts on large experiments' detectors, reconstruction (tracking, vertexing, calorimetry, particle identification, timing, Cherenkov/RICH, TRD, TOF, muon systems), calibration and alignment, efficiency and resolution (tag-and-probe, truth matching), detector simulation (Geant4), data/MC agreement, conditions and their provenance, response matrices, folding a prediction through the response, and parametrized response for recasting. Works for collider, fixed-target, neutrino, rare-event and astroparticle instruments. Load it first even for a quick question on a named experiment's detector or resolution: it reads the profile or sourced atlas and asks which configuration is meant instead of quoting from memory. Not for: measurement design (hep-measurement); unfolding, fits, limits (hep-statistics); theory (hep-theory); generic code (hep-computing); training ML models (hep-ml)."
---

# hep-detector: detector performance and response

**Owns:** signal formation, reconstruction, detector calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, response matrices, forward folding of predictions, double-counting checks.
**Typical artifacts:** `response` (truth/reco axes, orientation, normalization, what sits inside the matrix, intended use), folded `prediction`, performance reports, conditions provenance.
**Never:** invent detector facts; detector specifics come from an experiment profile, the user, or are `unknown`. Inference on top of a response belongs to hep-statistics.

## Invariants

- Declare matrix orientation, normalization convention, where inefficiency and acceptance live (inside or outside the matrix), underflow/overflow handling, which corrections are included, and the intended use (`forward_folding`, `unfolding`, `parametric_fit`). A correction inside the matrix is never applied again outside it.
- Truth and reco variables are named with units; if they differ, the conversion is stated (a binned response is a conditional distribution; a Jacobian applies only to a continuous density).
- Stop when the inputs cannot determine the answer: a mean and a width do not determine a migration matrix or its tails. Ask for matched events or distributions, or offer a parametrized response labelled as an assumption.
- Efficiencies are conditional probabilities with a named denominator; resolution is reported with the core and the tails separately, and non-Gaussian tails are measured, not assumed.
- Calibration is legitimate when it uses independent control samples with provenance; tuning toward the expected signal outcome is flagged.
- Conditions are time-dependent until shown otherwise; record periods and versions.
- A passing validator shows self-consistency under declared metadata, not physical validity.

## Workflow

1. Resolve context (stanza below); then only needed subsystem modules. What to confirm first, by task type: [task routing](references/detector-principles-summary.md#task-routing-what-to-confirm-first).
2. State the quantity (efficiency, resolution, scale, response matrix) and its conditioning.
3. Choose the reference: truth matching in simulation, tag-and-probe or control sample in data, or both with a data/MC comparison.
4. Report central value, statistical and systematic parts, validity range, and conditions.
5. Write the `response` artifact, then run `python3 "<plugin root>/contracts/validate.py" <artifact>` and `python3 "<plugin root>/contracts/response_adapter.py" <artifact> --validate`; both must pass before another skill consumes it.

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
| Any detector question: the chain, the fourteen questions, task routing | [principles summary](references/detector-principles-summary.md) (section 11 indexes every file) |
| Resolution, efficiency, tag-and-probe, truth matching | [reconstruction performance](references/reconstruction-performance-and-truth-matching.md); `tag_and_probe_efficiency.py` |
| Tracking, vertexing, multiple scattering | [tracking and vertexing](references/tracking-and-vertexing.md); `multiple_scattering.py` |
| Synthetic spectrometer events and periods (test bed, seeded) | `toy_spectrometer.py`; `assets/toy-spectrometer.fictional.json` |
| Calorimeter response and resolution | [calorimetry](references/calorimetry-ecal-hcal.md); `calorimeter_resolution.py` |
| Particle identification, TOF, dE/dx, RICH | [particle identification](references/particle-identification.md); `pid_separation_power.py`, `cherenkov_angle.py` |
| Signal formation, readout, front-end electronics | [front-end electronics](references/front-end-electronics-and-signal-processing.md); `frontend_response.py` |
| Response matrices, forward folding | [response and folding](references/response-and-forward-folding.md) |
| Data/MC agreement, detector systematics | [data/MC validation](references/data-mc-validation-and-detector-systematics.md) |
| Calibration, alignment, conditions | [calibration and alignment](references/calibration-and-alignment.md) |
| Triggers, luminosity, pileup | [triggers and pileup](references/triggers-luminosity-pileup.md); `pileup_reweight.py` |
| Simulation (Geant4) | [detector simulation](references/detector-simulation.md) |
| Charge-sign confusion | [charge confusion](references/charge-confusion.md) |
| Space-based and balloon instruments | [space-based direct detection](references/space-based-direct-detection.md) |
| Air showers, X_max | [extensive air showers](references/extensive-air-showers.md); `xmax_gaisser_hillas.py` |
| A named experiment's detector | the bound profile; ask which configuration is meant |

Scripts in `<plugin root>/skills/hep-detector/scripts/` (read `--help` first); example inputs in `assets/`. Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Truth-level prediction to fold | from hep-theory | `prediction` |
| Unfolding, fits on the response | hep-statistics | `response` |
| Tag-and-probe pass/fail fit, pileup systematics | hep-statistics | performance report |
| Measurement design using these numbers | hep-measurement | `response` / report |
| Simulation production, conditions code | hep-computing | `computational-run` |
| ML-based reconstruction or calibration; training a learned fast simulation or ML response model | hep-ml | `ml-artifact` |
| Writing up results | hep-communication | report |

<!-- example: routing -->
- "AMS-02 RICH velocity resolution vs charge" → this skill + `experiment:ams-02` subsystem module only.
- "Parametrized muon efficiency for recasting a published search" → this skill, then hep-statistics.
<!-- /example -->
