---
name: physics-ml
description: "Use when the deliverable is a machine-learning model or study for physics, in PyTorch: classifiers and regressors for events, particles or detector signals, generative models and fast simulation, surrogates of expensive simulations or predictions, ML-assisted or simulation-based inference, calibration of model outputs, grouped train/validation/test splits and leakage checks, domain shift between simulation and data, uncertainty estimation, and the PyTorch engineering behind them (models, training loops, data loading, mixed precision, distributed training, debugging NaNs and shapes, checkpoints, export). Not for the physics assumptions a surrogate encodes (hep-theory), the statistical validity of inference built on a model (hep-statistics), or general non-ML code (hep-computing). PyTorch only."
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

1. Resolve context (stanza below).
2. Define the task, labels, features and grouping key; build grouped splits and check leakage.
3. Train with recorded seeds and environment; monitor; checkpoint.
4. Evaluate on held-out groups, calibrate, assess domain shift and the downstream effect.
5. Write the `ml-artifact` and validate it.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
<!-- END context-resolution -->

## Resources

PyTorch engineering references, the split-integrity checker, and the scientific-ML boundaries reference arrive in M2.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics assumptions or validity domain of a surrogate | hep-theory | `prediction` |
| Inference using the model (coverage, systematics) | hep-statistics | `ml-artifact` |
| Pipeline, I/O, batch training jobs | hep-computing | `computational-run` |
