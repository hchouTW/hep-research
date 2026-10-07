---
name: physics-ml
description: "Use when the deliverable is a machine-learning model or study for physics, in PyTorch: classifiers and regressors for events, particles or detector signals, generative models and fast simulation, surrogates of expensive simulations or predictions, ML-assisted or simulation-based inference, calibration of model outputs, grouped train/validation/test splits and leakage checks, domain shift between simulation and data, uncertainty estimation, and the PyTorch engineering behind them (models, training loops, data loading, mixed precision, distributed training, debugging NaNs and shapes, checkpoints, export). Not for: the physics a surrogate encodes (hep-theory), validity of inference built on a model (hep-statistics), non-ML code (hep-computing). PyTorch only."
---

# physics-ml: machine learning for physics

**Owns:** classification and regression, generation, surrogates, ML-assisted inference, calibration, domain shift, and PyTorch engineering.
**Typical artifacts:** `ml-artifact` (labels, features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation).
**Never:** let a metric such as AUC stand in for physics validity; extrapolate a surrogate outside its declared domain without saying so.

## Invariants

- Splits are grouped by the unit that carries correlation (run, event, detector period, simulation seed, parameter point). Overlap between splits is checked and reported.
- The training domain is declared; inputs outside it are flagged at inference time.
- Simulation-trained models are checked on data or control samples for domain shift before their outputs feed a measurement.
- Classifier outputs used as probabilities are calibrated and the calibration is validated.
- Event weights (including negative generator weights) are handled explicitly in losses and metrics.
- A model feeding a measurement or an inference is validated downstream (effect on the physics result, not only on the ML metric).

## Workflow

1. First read `hep-research.project.json` if present and any profile it binds (stanza below).
2. Define the task, labels, features and grouping key; build grouped splits and check leakage.
3. Train with recorded seeds and environment; monitor; checkpoint.
4. Evaluate on held-out groups, calibrate, assess domain shift and the downstream effect.
5. Write the `ml-artifact` and validate it.

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

Start with [the PyTorch engineering guide](references/deep-learning-guide.md). Physics-facing references: [multivariate analysis](references/multivariate-analysis-bdt-nn.md), [ML in analyses](references/ml-analysis.md), [scientific ML](references/scientific-machine-learning.md), data strategy, evaluation, uncertainty and calibration, robustness and distribution shift, reproducibility; engineering references cover training, scaling, debugging and deployment, all under `references/`.

Scripts in `<plugin root>/skills/physics-ml/scripts/` (read `--help` first): `check_split_integrity.py` (group leakage), `check_surrogate_domain.py` (surrogate queries outside or in sparse parts of the training domain), `check_dataset_contract.py`, `compare_model_runs.py`, `find_nan_batches.py`, `inspect_checkpoint.py`, `check_pytorch_env.py`, and budget estimators. Code starting points are in `assets/`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics assumptions or validity domain of a surrogate | hep-theory | `prediction` |
| Inference using the model (coverage, systematics) | hep-statistics | `ml-artifact` |
| Pipeline, I/O, batch training jobs | hep-computing | `computational-run` |
| Fast-simulation validation against full simulation | detector-response | `ml-artifact` |
| Writing up results and figures | research-communication | `ml-artifact` |
