# hep-ml

Machine-learning models and studies for physics, delivered as a validated `ml-artifact` (labels, features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation) with the training, calibration and domain checks behind it.

## Core capabilities

- Owns: classification and regression, generation (fast simulation training), surrogates, ML-assisted inference (training side), calibration of model outputs, domain shift, and PyTorch engineering; BDT and classical MVA guidance for analyses.
- Classifiers and regressors for events, particles, jets or detector signals: PyTorch networks, and cross-trained BDTs in analyses (XGBoost primary, scikit-learn fallback; classifier or regression, mass sculpting) with export.
- Event weights including negative ones, handled explicitly in losses and metrics; working points and mass decorrelation; systematic-aware training; weak supervision and anomaly detection.
- Grouped train/validation/test or k-fold splits (by run, period, seed or parameter point, or a composite key), stratified splits, and leakage checks.
- Domain shift between simulation and data: per-feature distances, a grouped cross-validated classifier two-sample test, per-period breakdown.
- Surrogates: Gaussian-process emulator of a vector-valued simulator output, a declared training domain and out-of-domain flags at inference.
- Generative models and fast simulation, ML-assisted or simulation-based inference (training side).
- Calibration of model outputs (temperature, Platt, weighted isotonic, reliability, ECE) and uncertainty estimation.
- Particle and jet architectures (sets, hits, point clouds, graphs; Deep Sets/PFN, ParT-lite); space and astroparticle detectors.
- PyTorch engineering: training loops, data loading, mixed precision, distributed training, debugging NaNs and shapes, checkpoints, export; compute, memory and serving budgets.

## Triggering conditions

Use when:

- the deliverable is a machine-learning model or study for physics (classifier, regressor, generative model, surrogate, ML-assisted inference on the training side);
- the question concerns event weights, working points, decorrelation, grouped splits, leakage, calibration of model outputs, domain shift or uncertainty estimation;
- the question is PyTorch engineering (load it first even for a quick classifier, metric or training question).

Not for:

| Need | Hand to |
|---|---|
| Physics assumptions or validity domain of a surrogate; the physics a surrogate encodes | hep-theory |
| Inference using the model (coverage, systematics); any limit, fit or significance with the model | hep-statistics |
| Selection design, normalization, systematics plan around a score | hep-measurement |
| Scale factors, tag-and-probe, fast-simulation validation against full simulation | hep-detector |
| Pipeline, I/O, batch training jobs; non-ML code | hep-computing |
| Writing up results and figures | hep-authoring |

## Workspace directory architecture

```text
hep-ml/
├── SKILL.md          entry point loaded by the host
├── README.md         this folder guide
├── references/       physics-ML and PyTorch references, entries: ml-analysis.md, deep-learning-guide.md
├── scripts/          command-line helpers
└── assets/           code starting points, training pipeline, example records
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources (task-to-reference table), pipeline, handoffs; its front matter carries the routing description and it stays under 8 KiB |
| `references/` | forty-two references: ML in analyses (weights, metrics, decorrelation, systematics, sim-to-data, weak supervision), multivariate analysis, particle and jet architectures, space and astroparticle detectors, fast-simulation validation, SBI training, scientific ML, the PyTorch engineering guide, data strategy, evaluation, uncertainty and calibration, robustness and distribution shift, reproducibility, training, scaling, debugging, deployment |
| `scripts/` | nineteen helpers: grouped split builder, split integrity, cross-trained BDT (`train_bdt.py`, optional extra `bdt`; classifier or regression, mass sculpting) and its export (`export_bdt.py`), domain-shift report, ml-artifact writer, surrogate domain, Gaussian-process emulator (`train_emulator.py`), dataset contract, run comparison, NaN batches, checkpoints, PyTorch environment, compute and memory budgets, dataloader profiling, serving capacity, benchmarking, the naming extractor for models and features |
| `assets/` | code starting points: HEP metrics with signed weights (`hep_metrics.py`, NumPy) and losses (`hep_losses.py`: signed-weight BCE, DisCo, NaN-safe masking), output calibration (`calibration.py`: temperature, Platt, weighted isotonic, reliability, ECE; records the model it was made for, `model_hash`), set classifiers (`set_classifier.py`: Deep Sets/PFN, ParT-lite), the classifier training pipeline (`train_classifier.py`: grouped split manifest and its `split_manifest_sha256`, signed weights, run summary) and `inference.py` (out-of-domain flags; refuses a calibration made for another model and reports a changed split manifest), dataset template, models, other training loops (DDP skeleton, LoRA fine-tune, vision transfer, transformer classifier), metrics, config, example split and run records, and a pre-training freeze example (`pretraining-decision.example.json` with its exposure record and split manifest) |

References:

- Start with `references/ml-analysis.md` for physics work (its Task routes index covers other tasks) and `references/deep-learning-guide.md` for PyTorch engineering; `SKILL.md` has the task-to-reference table.
- Files marked "Generic ML engineering" at the top (serving, monitoring, fine-tuning, large-model scaling) are not physics-specific.

## Input and output specifications

Inputs:

- Request: a model or study to design, train, calibrate, evaluate, debug or record.
- Profiles and context: the profiles the user names, else those bound in `hep-research.project.json` (checked with `contracts/project.py --preflight`); space or ground-based astroparticle work uses the bound profile.
- Files and artifacts read: event or feature tables, split manifests, training run summaries, calibration and domain-shift results, checkpoints and exported models, training sets and query points for surrogates, dataset contracts.

Outputs:

- Artifacts written: `ml-artifact`, with `scripts/write_ml_artifact.py --out <artifacts_dir>/<name>.json`, then `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`.
- Work files: configs, run folders (`--out-dir`) and raw tool outputs go in a work folder such as `./ml-work/`, not `artifacts_dir`.
- Naming inventories: a working file under `<project>/naming/`, refused inside `artifacts_dir`.

Pipeline (read `--help` first):

```text
make_grouped_splits.py
  -> check_split_integrity.py
  -> assets/train_classifier.py --split-manifest   (refuses a leaky split; signed weights)
  -> assets/calibration.py                         (fit on validation, evaluate on test)
  -> assets/inference.py                           (flags out-of-domain inputs)
  -> write_ml_artifact.py                          (validated ml-artifact)
```

Script CLI contract: JSON output with a `status` key; `--status` label on most tools; exit codes 0-3 only, with each script's meaning in its `--help`:

```text
exit 0              ok, written or passed
exit 1              negative verdict (shift found, query outside the domain, artifact not written, does not fit)
exit 2              bad input
exit 3              missing optional package, numerical failure or incomplete
```

Script notes:

- `make_grouped_splits.py`: train/val/test or k-fold assignment by run, period, seed or parameter point, or a composite key such as run and luminosity block; random-groups or temporal; `--stratify-column` splits each class or period on its own and lists strata with too few groups.
- `check_split_integrity.py`: group leakage between splits; null groups and case or whitespace variants are reported; the coverage of each stratum when the manifest carries one.
- `check_surrogate_domain.py`: whitened Mahalanobis, k-NN and subspace-residual distances with thresholds calibrated on held-out training points, split by group when given; categorical features; reports the false-positive rate with an interval; its `DomainModel` is the one domain method `train_classifier.py` stores and `inference.py` applies.
- `domain_shift_report.py`: weighted KS, Wasserstein-1 and binned chi2 per feature, a grouped cross-validated classifier two-sample test, a per-period breakdown and the features that drive the shift; its `--domain-shift-out` file is the `domain_shift` input of the writer.
- `write_ml_artifact.py`: builds and validates an `ml-artifact` from a training run summary, calibration and domain-shift results, and the task's validation block such as a surrogate's `extrapolation_policy`.
- `train_emulator.py`: Gaussian-process emulator of a vector-valued simulator output on a box of inputs: principal components, one Matern-5/2 GP each with a nugget floor that keeps every kernel matrix's condition number under `--max-condition` (default 1e10, so the model reproduces on other libm/BLAS builds), an error estimate per prediction, the `DomainModel` stored in the model file, a run summary for the writer with task surrogate.
- `check_pytorch_env.py`: exit 1 when torch cannot be imported, 2 when the smoke test fails, 3 when the build cannot use the GPU.
- Other helpers: `check_dataset_contract.py`, `compare_model_runs.py`, `find_nan_batches.py`, `inspect_checkpoint.py`, `estimate_compute_budget.py`, `estimate_training_memory.py`, `profile_dataloader.py`, `serving_capacity.py`, `benchmark_model.py`, `extract_names.py`.
- Scripts that need PyTorch say so and skip cleanly without it.

## Setup requirements

- Python 3.13 or newer.
- Standard library first (`write_ml_artifact.py` and the naming extractor are standard library only).
- NumPy and SciPy (plugin core stack, `requirements-core.txt`): `check_surrogate_domain.py`, `domain_shift_report.py`, `train_emulator.py`, `assets/hep_metrics.py`.
- PyTorch (optional extra `torch`; CPU wheels are enough for the tests): the PyTorch scripts and assets.
- XGBoost and scikit-learn (optional extra `bdt`): `train_bdt.py`.
- `export_bdt.py`: `--to onnx` needs onnxmltools and onnx, which the plugin does not install; `--to tmva` needs PyROOT with TMVA and xgboost in the same interpreter; a missing optional package gives status `missing-dependency` (exit 3) and nothing is written.
- Environment variables: `HEP_TORCH_GPU_TEST=1` enables the GPU test module (tests only).

## Operational constraints

- Never lets a metric such as AUC stand in for physics validity; never extrapolates a surrogate outside its declared domain without saying so.
- A limit, fit or significance with the model is hep-statistics': that skill is loaded before computing one, even when this skill was loaded first.
- Splits are grouped by the unit that carries correlation (run, event, detector period, simulation seed, parameter point); overlap between splits is checked and reported.
- The training domain is declared; inputs outside it are flagged at inference time.
- Simulation-trained models are checked on data or control samples for domain shift before their outputs feed a measurement.
- Classifier outputs used as probabilities are calibrated and the calibration is validated.
- Training weights and evaluation weights are recorded separately.
- A model feeding a measurement or an inference is validated downstream (effect on the physics result, not only on the ML metric).
- Profiles are read only through the context-resolution steps; no experiment facts are embedded; durable results are JSON artifacts in `artifacts_dir`, never inside the plugin.
- A successful script run is a software check, not scientific validity.
- [SKILL.md](SKILL.md) is the authoritative statement of what the skill owns, never does, and its invariants.

## Validation

- `tests/skills/hep_ml/`: 30 test modules, including the pre-training freeze check (`test_pretraining_freeze.py`), analytic checks of the HEP metrics, calibration and the domain check and, with PyTorch, of the losses, the set classifiers and the training pipeline; the GPU module runs only with `HEP_TORCH_GPU_TEST=1` on hardware the maintainer may use.
- The `optional (torch-cpu)` CI job.
- Worked example `examples/ml-classifier-to-inference/` at the plugin root (journey J9, SYNTHETIC): grouped split and leakage check, signed-weight training, calibration on a separate sample, domain-shift check, a validated `ml-artifact`, then a template fit of the signal strength written as a `statistical-result`.
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

- "Build grouped train/validation/test splits by run and check them for leakage."
- "Train a cross-trained BDT with negative generator weights and choose a working point."
- "Is this improvement real?" (ablations, seed variance, model comparison)
- "Check this simulation-trained classifier for domain shift against data before it feeds the measurement."
