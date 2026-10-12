# detector-response

Use when the deliverable is about how a detector responds: signal formation and readout, reconstruction (tracking, vertexing, calorimetry, particle identification, timing, Cherenkov, transition radiation, time of flight, muon systems), calibration and alignment, efficiency and resolution measurement, detector simulation, data/MC agreement, conditions and their provenance, response matrices, folding a prediction through the response, and parametrized response for recasting. Load it first even for a quick question on a named experiment's detector: it reads the profile and asks which configuration is meant instead of quoting from memory.

**Owns:** signal formation, reconstruction, calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, response matrices, forward folding of predictions, double-counting checks. Typical artifact: `response`.

**Never:** invent detector facts; detector specifics come from an experiment profile, the user, or are `unknown`. Inference on top of a response belongs to hep-statistics.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-four references: a principles summary that indexes the rest, one file per subsystem or topic, astroparticle instruments, case studies, comparison tables, glossary, bibliography |
| `scripts/` | eight helpers: calorimeter resolution, Cherenkov angle, front-end electronics (noise, thresholds, timing, quantization, pileup, SiPM, dead time), multiple scattering, PID separation power, pileup reweighting, tag-and-probe efficiency, the Gaisser-Hillas longitudinal profile |
| `assets/` | synthetic example inputs: a calorimeter response, a detector stack, pileup profiles |

## Scripts

`calorimeter_resolution.py`, `cherenkov_angle.py`, `multiple_scattering.py`, `pid_separation_power.py`, `pileup_reweight.py`, `tag_and_probe_efficiency.py`, `xmax_gaisser_hillas.py`. Each reads `--help`; particle masses come from the caller or the primary-source table, never from a built-in constant presented as a measurement.

## References

Start with `references/detector-principles-summary.md`, then the topic file the task needs (front-end electronics and signal processing, tracking, calorimetry, PID, timing, muon systems, noble-liquid and rare-event detectors, physics objects, triggers and pileup, reconstruction, truth matching, performance metrics, response and forward folding, data/MC validation, simulation, calibration and alignment). Astroparticle instruments have their own files (cosmic-ray spectrum and composition, air showers, ground arrays, imaging atmospheric Cherenkov telescopes, neutrino telescopes, space-based direct detection, multimessenger analysis).

## Handoffs

| Need | Hand to |
|---|---|
| Unfolding, fits on the response | hep-statistics |
| Measurement design using these numbers | hep-analysis |
| Simulation production, conditions code | hep-computing |
| ML-based reconstruction or calibration | physics-ml |
| Writing up results | research-communication |

## Tests and validation

`tests/skills/detector_response/` (four modules: the scripts, their validity-range guards, the front-end electronics script, and a coverage test that every bullet of the principles summary is backed by a reference) and the `detector-resolution` and `recasting` examples under `examples/`. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
