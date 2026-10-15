# hep-ml

Use when the deliverable is a machine-learning model or study for physics: classifiers and regressors for events, particles or detector signals, generative models and fast simulation, surrogates of expensive simulations or predictions, ML-assisted or simulation-based inference, calibration of model outputs, grouped train/validation/test splits and leakage checks, domain shift between simulation and data, uncertainty estimation, and the PyTorch engineering behind them. Neural networks in PyTorch; BDT and classical MVA guidance for analyses.

Formerly `physics-ml`; the old name is a deprecated alias in contracts 2.9.0.

**Owns:** classification and regression, generation, surrogates, ML-assisted inference, calibration, domain shift, and PyTorch engineering. Typical artifact: `ml-artifact` (labels, features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation).

**Never:** let a metric such as AUC stand in for physics validity; extrapolate a surrogate outside its declared domain without saying so.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-eight references: ML in analyses (weights, metrics, decorrelation, systematics, sim-to-data, weak supervision), multivariate analysis, particle and jet architectures, space and astroparticle detectors, fast-simulation validation, SBI training, scientific ML, the PyTorch engineering guide, data strategy, evaluation, uncertainty and calibration, robustness and distribution shift, reproducibility, training, scaling, debugging, deployment |
| `scripts/` | fourteen helpers: grouped split builder, split integrity, ml-artifact writer, surrogate domain, dataset contract, run comparison, NaN batches, checkpoints, PyTorch environment, compute and memory budgets, dataloader profiling, serving capacity, benchmarking |
| `assets/` | code starting points: HEP metrics with signed weights (`hep_metrics.py`, NumPy) and losses (`hep_losses.py`: signed-weight BCE, DisCo, NaN-safe masking), output calibration (`calibration.py`: temperature, Platt, weighted isotonic, reliability, ECE), set classifiers (`set_classifier.py`: Deep Sets/PFN, ParT-lite), the classifier training pipeline (`train_classifier.py`: grouped split manifest, signed weights, run summary) and `inference.py` (out-of-domain flags), dataset template, models, other training loops (DDP skeleton, LoRA fine-tune, vision transfer, transformer classifier), metrics, config, example split and run records, and a pre-training freeze example (`pretraining-decision.example.json` with its exposure record and split manifest) |

## Scripts

`make_grouped_splits.py` (train/val/test or k-fold assignment by run, period, seed or parameter point; random-groups or temporal), `check_split_integrity.py` (group leakage between splits; null groups and case or whitespace variants are reported), `check_surrogate_domain.py` (whitened Mahalanobis, k-NN and subspace-residual distances with thresholds calibrated on held-out training points, split by group when given; categorical features; reports the false-positive rate with an interval; its `DomainModel` is the one domain method `train_classifier.py` stores and `inference.py` applies), `write_ml_artifact.py` (builds and validates an `ml-artifact` from a training run summary, calibration and domain-shift results), `check_dataset_contract.py`, `compare_model_runs.py`, `find_nan_batches.py`, `inspect_checkpoint.py`, `check_pytorch_env.py` (exits 3 when the build cannot use the GPU), `estimate_compute_budget.py`, `estimate_training_memory.py`, `profile_dataloader.py`, `serving_capacity.py`, `benchmark_model.py`. Scripts that need PyTorch say so and skip cleanly without it.

## References

Start with `references/ml-analysis.md` for physics work and `references/deep-learning-guide.md` for PyTorch engineering; `SKILL.md` has the task-to-reference table. Files marked "Generic ML engineering" at the top (serving, monitoring, fine-tuning, large-model scaling) are not physics-specific.

## Worked example

`examples/ml-classifier-to-inference/` (journey J9, SYNTHETIC): grouped split and leakage check, signed-weight training, calibration on a separate sample, domain-shift check, a validated `ml-artifact`, then a template fit of the signal strength written as a `statistical-result`.

## Handoffs

| Need | Hand to |
|---|---|
| Physics assumptions or validity domain of a surrogate | hep-theory |
| Inference using the model (coverage, systematics) | hep-statistics |
| Pipeline, I/O, batch training jobs | hep-computing |
| Selection design, normalization, systematics plan around a score | hep-measurement |
| Scale factors, tag-and-probe, fast-simulation validation against full simulation | hep-detector |
| Writing up results and figures | hep-communication |

## Tests and validation

`tests/skills/hep_ml/` (twenty-two modules, including the pre-training freeze check (`test_pretraining_freeze.py`), analytic checks of the HEP metrics, calibration and the domain check and, with PyTorch, of the losses, the set classifiers and the training pipeline; the GPU module runs only with `HEP_TORCH_GPU_TEST=1` on hardware the maintainer may use) and the `optional (torch-cpu)` CI job. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
