# hep-detector

Use when the deliverable is about how a detector responds: signal formation and readout, reconstruction (tracking, vertexing, calorimetry, particle identification, timing, Cherenkov, transition radiation, time of flight, muon systems), calibration and alignment, efficiency and resolution measurement, detector simulation, data/MC agreement, conditions and their provenance, response matrices, folding a prediction through the response, and parametrized response for recasting. Load it first even for a quick question on a named experiment's detector: it reads the profile and asks which configuration is meant instead of quoting from memory.

Formerly `detector-response`; the old name is a deprecated alias in contracts 2.9.0.

**Owns:** signal formation, reconstruction, calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, response matrices, forward folding of predictions, double-counting checks. Typical artifact: `response`.

**Never:** invent detector facts; detector specifics come from an experiment profile, the user, the sourced detector atlas, or are `unknown`. Inference on top of a response belongs to hep-statistics.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-five references: a principles summary that indexes the rest, one file per subsystem or topic, astroparticle instruments, case studies, comparison tables, glossary, bibliography |
| `scripts/` | nineteen helpers: the sourced detector atlas (validate, render, query, audit), a tracker resolution for a stated layout (exact fit and Gluckstern, scattering, MDR, impact parameter, requirement scan), a response artifact from matched events, era responses mixed or stacked, calorimeter resolution, Cherenkov angle, front-end electronics (noise, thresholds, timing, quantization, pileup, SiPM, dead time), multiple scattering, PID separation power, pileup reweighting, tag-and-probe efficiency, the Gaisser-Hillas longitudinal profile, a seeded toy spectrometer (synthetic events and periods), propagation of a calibration residual into yields and ratios, many-sample PID, stability over time, survival and fragmentation feed-down in material, charge-sign confusion rates, species-migration responses |
| `assets/` | synthetic example inputs: a calorimeter response, a detector stack, pileup profiles, a fictional toy-spectrometer configuration, multisample PID events and a response curve, a stability series |

## Scripts

`build_response.py`, `calorimeter_resolution.py`, `charge_confusion_rate.py`, `cherenkov_angle.py`, `detector_atlas.py`, `frontend_response.py`, `mix_period_responses.py`, `multiple_scattering.py`, `multisample_pid.py`, `pid_separation_power.py`, `pileup_reweight.py`, `propagate_scale_distortion.py`, `species_response.py`, `stability_monitor.py`, `survival_feeddown.py`, `tag_and_probe_efficiency.py`, `tracker_resolution.py`, `toy_spectrometer.py`, `xmax_gaisser_hillas.py`. Each reads `--help`, echoes a `--status` label and prints JSON at every exit code (0 ok, 1 failed, 2 invalid input; `toy_spectrometer.py` 3 without NumPy; `propagate_scale_distortion.py` 1 when a user plugin fails; `build_response.py` and `mix_period_responses.py` 1 when the artifact fails its validation and nothing is written); `multisample_pid.py` combines many samples (a charge from many dE/dx layers with the leakage matrix between neighbouring charges, or a log-likelihood ratio from per-layer PDFs with its efficiency - mis-identification curve); `tag_and_probe_efficiency.py` takes counts, or a CSV of probes with frequency or sampling weights (Kish effective sample size; negative weights go to hep-statistics) and bins, with no cap on the total; `charge_confusion_rate.py` measures the charge-sign confusion rate per bin (Barlow-Beeston template fit with a profile-likelihood interval, or a control sample with Clopper-Pearson; a Gaussian-core lower bound labelled not an estimate) and writes sign rates for `species_response.py`; `species_response.py` ties per-species responses into a block manifest (assemble with column-sum checks, sparse fold, a double-count check against the correction chain, blocks from sign rates); `survival_feeddown.py` gives the survival probability of nuclei through the material above the measuring layers and the first-order fragmentation feed-down, with cross-section scale derivatives and recipe steps for the analysis check (no built-in cross sections); `stability_monitor.py` tests a quantity over time (trends, change points and CUSUM with thresholds calibrated by toys to a declared false-alarm rate, periods out of tolerance, proposed calibration era boundaries that are never written into a spec; statistics in `core/stats/change_point.py`); five have tool contracts in `contracts/tool_contracts/` (`frontend_response.json` with one operation per subcommand); particle masses come from the caller or the primary-source table, never from a built-in constant presented as a measurement.

## References

Start with `references/detector-principles-summary.md`, then the topic file the task needs (front-end electronics and signal processing, tracking, calorimetry, PID, timing, muon systems, noble-liquid and rare-event detectors, physics objects, triggers and pileup, reconstruction, truth matching, performance metrics, response and forward folding, charge-sign confusion (a synthesis note: mechanisms, how the rate is measured, handoff to hep-measurement; status `documented`), data/MC validation, simulation, calibration and alignment). Astroparticle instruments have their own files (cosmic-ray spectrum and composition, air showers, ground arrays, imaging atmospheric Cherenkov telescopes, neutrino telescopes, space-based direct detection, multimessenger analysis).

## Handoffs

| Need | Hand to |
|---|---|
| Unfolding, fits on the response | hep-statistics |
| Measurement design using these numbers | hep-measurement |
| Simulation production, conditions code | hep-computing |
| ML-based reconstruction or calibration | hep-ml |
| Writing up results | hep-communication |

## Tests and validation

`tests/skills/hep_detector/` (six modules: the scripts, their validity-range guards, the front-end electronics script, reference values, the audit regression suite, and a link check of every reference), `tests/contracts/test_response_contract.py` for the response contract, and the `detector-resolution` and `recasting` examples under `examples/`. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
