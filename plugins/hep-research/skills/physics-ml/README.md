# physics-ml

Use when the deliverable is a machine-learning model or study for physics: classifiers and regressors for events, particles or detector signals, generative models and fast simulation, surrogates of expensive simulations or predictions, ML-assisted or simulation-based inference, calibration of model outputs, grouped train/validation/test splits and leakage checks, domain shift between simulation and data, uncertainty estimation, and the PyTorch engineering behind them. Neural networks in PyTorch; BDT and classical MVA guidance for analyses.

**Owns:** classification and regression, generation, surrogates, ML-assisted inference, calibration, domain shift, and PyTorch engineering. Typical artifact: `ml-artifact` (labels, features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation).

**Never:** let a metric such as AUC stand in for physics validity; extrapolate a surrogate outside its declared domain without saying so.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-eight references: ML in analyses (weights, metrics, decorrelation, systematics, sim-to-data, weak supervision), multivariate analysis, particle and jet architectures, space and astroparticle detectors, fast-simulation validation, SBI training, scientific ML, the PyTorch engineering guide, data strategy, evaluation, uncertainty and calibration, robustness and distribution shift, reproducibility, training, scaling, debugging, deployment |
| `scripts/` | twelve helpers: split integrity, surrogate domain, dataset contract, run comparison, NaN batches, checkpoints, PyTorch environment, compute and memory budgets, dataloader profiling, serving capacity, benchmarking |
| `assets/` | code starting points: HEP metrics with signed weights (`hep_metrics.py`, NumPy) and losses (`hep_losses.py`: signed-weight BCE, DisCo, NaN-safe masking), dataset template, models, training loops (classifier, DDP skeleton, LoRA fine-tune, vision transfer, transformer classifier), metrics, inference, config, example split and run records |

## Scripts

`check_split_integrity.py` (group leakage between splits), `check_surrogate_domain.py` (queries outside or in sparse parts of the training domain), `check_dataset_contract.py`, `compare_model_runs.py`, `find_nan_batches.py`, `inspect_checkpoint.py`, `check_pytorch_env.py` (exits 3 when the build cannot use the GPU), `estimate_compute_budget.py`, `estimate_training_memory.py`, `profile_dataloader.py`, `serving_capacity.py`, `benchmark_model.py`. Scripts that need PyTorch say so and skip cleanly without it.

## References

Start with `references/ml-analysis.md` for physics work and `references/deep-learning-guide.md` for PyTorch engineering; `SKILL.md` has the task-to-reference table.

## Handoffs

| Need | Hand to |
|---|---|
| Physics assumptions or validity domain of a surrogate | hep-theory |
| Inference using the model (coverage, systematics) | hep-statistics |
| Pipeline, I/O, batch training jobs | hep-computing |
| Selection design, normalization, systematics plan around a score | hep-analysis |
| Scale factors, tag-and-probe, fast-simulation validation against full simulation | detector-response |
| Writing up results and figures | research-communication |

## Tests and validation

`tests/skills/physics_ml/` (six modules, including analytic checks of the HEP metrics and, with PyTorch, of the losses; the GPU module runs only with `HEP_TORCH_GPU_TEST=1` on hardware the maintainer may use) and the `optional (torch-cpu)` CI job. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
