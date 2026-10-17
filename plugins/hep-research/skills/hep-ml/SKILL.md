---
name: hep-ml
description: "Use when the deliverable is a machine-learning model or study for physics: classifiers and regressors for events, particles, jets or detector signals (PyTorch networks, and BDTs in analyses, e.g. XGBoost), event weights including negative ones, working points and mass decorrelation, systematic-aware training, domain shift between simulation and data, weak supervision, generative models and fast simulation, surrogates, ML-assisted or simulation-based inference (training side), calibration of model outputs, grouped train/validation/test splits and leakage checks, uncertainty estimation, and PyTorch engineering (training loops, data loading, mixed precision, distributed training, debugging NaNs and shapes, checkpoints, export). Load it first even for a quick classifier, metric or training question. Not for: the physics a surrogate encodes (hep-theory), validity of inference built on a model (hep-statistics), detector-level fast-simulation validation (hep-detector), non-ML code (hep-computing)."
---

# hep-ml: machine learning for physics

**Owns:** classification and regression, generation (fast simulation training), surrogates, ML-assisted inference (training side), calibration of model outputs, domain shift, and PyTorch engineering; BDT and classical MVA guidance for analyses.
**Typical artifacts:** `ml-artifact` (labels, features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation).
**Never:** let a metric such as AUC stand in for physics validity; extrapolate a surrogate outside its declared domain without saying so.

## Invariants

- Splits are grouped by the unit that carries correlation (run, event, detector period, simulation seed, parameter point). Overlap between splits is checked and reported.
- The training domain is declared; inputs outside it are flagged at inference time.
- Simulation-trained models are checked on data or control samples for domain shift before their outputs feed a measurement.
- Classifier outputs used as probabilities are calibrated and the calibration is validated.
- Event weights (including negative generator weights) are handled explicitly in losses and metrics; training weights and evaluation weights are recorded separately.
- A model feeding a measurement or an inference is validated downstream (effect on the physics result, not only on the ML metric).

## Workflow

1. Resolve context (stanza below).
2. Define the task, labels, features and grouping key; build grouped splits and check leakage.
3. Train with recorded seeds and environment; monitor; checkpoint.
4. Evaluate on held-out groups with physics-weighted metrics at the working point, calibrate, assess domain shift and the downstream effect.
5. Write the `ml-artifact` and validate it.

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
| Classifier or regressor for an analysis: splits, weights, metrics, working points, decorrelation, systematics, sim-to-data; other tasks via its Task routes index | [ml-analysis.md](references/ml-analysis.md) |
| BDT vs NN, regression targets; cross-trained XGBoost BDT (negative weights, working points, mass sculpting), its export, external TMVA/LightGBM scores | [multivariate-analysis-bdt-nn.md](references/multivariate-analysis-bdt-nn.md); `train_bdt.py`, `export_bdt.py` |
| Jets, particle sets, hits, point clouds, graphs | [particle-and-jet-architectures.md](references/particle-and-jet-architectures.md) |
| Space or ground-based astroparticle detectors (with the bound profile) | [space-and-astroparticle-ml.md](references/space-and-astroparticle-ml.md) |
| Fast simulation, generative models | [fast-simulation-validation.md](references/fast-simulation-validation.md), [generative-models.md](references/generative-models.md) |
| Surrogates, SBI training | [scientific-machine-learning.md](references/scientific-machine-learning.md), [sbi-training.md](references/sbi-training.md) |
| Calibration, uncertainty, distribution shift; simulation-vs-data shift report | [uncertainty-and-calibration.md](references/uncertainty-and-calibration.md), [robustness-and-distribution-shift.md](references/robustness-and-distribution-shift.md); `domain_shift_report.py` |
| Grouped splits and leakage checks (composite keys, stratified by class or period) | `make_grouped_splits.py`, `check_split_integrity.py` |
| Train, calibrate, infer | `assets/train_classifier.py`, `assets/calibration.py`, `assets/inference.py` |
| Record the model for inference | `write_ml_artifact.py` |
| Surrogate training domain | `check_surrogate_domain.py` |
| PyTorch engineering (training, data, debugging, scaling, export) | [deep-learning-guide.md](references/deep-learning-guide.md), which routes to the rest |

Pipeline (scripts in `<plugin root>/skills/hep-ml/scripts/`, assets in `assets/`; read `--help` first): `make_grouped_splits.py` → `check_split_integrity.py` → `assets/train_classifier.py --split-manifest` (refuses a leaky split; signed weights) → `assets/calibration.py` (fit on validation, evaluate on test) → `assets/inference.py` (flags out-of-domain inputs) → `write_ml_artifact.py` (validated `ml-artifact`). Worked example: `<plugin root>/examples/ml-classifier-to-inference/`. Also `assets/hep_metrics.py`, `assets/hep_losses.py`, `assets/set_classifier.py` (Deep Sets, ParT-lite), `check_surrogate_domain.py` (whitened Mahalanobis and kNN, calibrated threshold), debugging and budget scripts. Folder guide: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics assumptions or validity domain of a surrogate | hep-theory | `prediction` |
| Inference using the model (coverage, systematics) | hep-statistics | `ml-artifact` |
| Selection design, normalization, systematics plan around a score | hep-measurement | `ml-artifact` |
| Scale factors, tag-and-probe, fast-simulation validation against full simulation | hep-detector | `ml-artifact` |
| Pipeline, I/O, batch training jobs | hep-computing | `computational-run` |
| Writing up results and figures | hep-communication | `ml-artifact` |
