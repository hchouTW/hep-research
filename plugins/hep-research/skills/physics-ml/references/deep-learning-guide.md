# PyTorch Engineering (guide)

## When to read this file

This file holds the routing and rules for PyTorch engineering work and ML
engineering decisions; it routes to the other references in this folder. For the
physics side of an ML task (splits by run, event weights, working points, decorrelation,
simulation-to-data checks) start at [ml-analysis.md](ml-analysis.md); the physics
references are listed first under "When to Read a Reference" below.

Produce practical, runnable, maintainable PyTorch code with strong defaults for
correctness, reproducibility, debugging, and extensibility - code another engineer can
run, test, and modify without archaeology.

Out of scope: non-PyTorch DL frameworks, general C++ unrelated to LibTorch/custom ops -
unless porting code into/out of PyTorch.

## Scope and Proportion

- **BDTs and classical MVA in physics analyses are in scope.** XGBoost, LightGBM, TMVA or
  scikit-learn models for an event selection, a regression or a tagger belong to this skill:
  read [multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md) (BDT practice,
  BDT vs NN) and [ml-analysis.md](ml-analysis.md) (grouped splits, negative weights,
  working points, systematics). The PyTorch-specific Workflow, templates, naming conventions,
  file-header rule and Response Format below do not apply to them.
- **Other deep-learning stacks:** for Keras/TensorFlow/JAX, answer in that stack's own
  idioms, keep the physics rules of [ml-analysis.md](ml-analysis.md), and skip the PyTorch
  engineering references; at most one line noting that the engineering advice here is
  PyTorch-specific. Porting to/from PyTorch is the exception.
- **Size the answer to the request.** A one-line shape error gets a short diagnosis and fix,
  not the full template.
- **Vague requests** ("make it faster", "improve accuracy") with no code or numbers: ask what
  is slow or which metric, or state your assumption. Measure or profile first, name at most
  three ranked suspects, and do not recommend `torch.compile`, AMP or DDP before a
  measurement shows that they bind.

## Rules to Apply Even Without Opening a Reference

- **Checkpoint config is plain data.** Store `config` as a dict (`vars(args)`,
  `dataclasses.asdict`). `torch.load` defaults to `weights_only=True` since PyTorch 2.6, so a
  custom-class config fails to load. Use `weights_only=False` only for files you trust.
- **Simulation is not data.** A metric on simulated test events says nothing about
  performance on data. Ask for data-driven validation (control region, sideband or
  tag-and-probe-style check), compare input and score distributions between data and
  simulation, and carry the mismodeling as a systematic uncertainty on any efficiency taken
  from simulation. A score is not a probability until it is calibrated on held-out data that
  is separate from the test set, and calibration on simulation need not hold on data.
- **Diagnose before prescribing regularization.** Check split leakage (jets of one event
  across train and validation), duplicates, seed variance and data size first. Change one
  thing at a time and judge it against the seed-noise baseline; state an expected effect as a
  hypothesis, not a result. For set, point-cloud or particle inputs, say whether the model is
  permutation invariant and whether an ordering (such as pt-sorting) is imposed; keep
  permutation invariance separate from rotation or Lorentz equivariance.
- **Do the memory equation before choosing a parallelism strategy.** Mixed-precision AdamW
  costs about 16 bytes per parameter before activations (2 bf16 weights, 2 gradients, 4 fp32
  master weights, 8 fp32 Adam moments), so a 3B model needs about 48 GB per replica under
  plain DDP. Activations grow with batch and sequence length and can be the binding term, in
  which case sharding weights (FSDP/ZeRO) does not help; recomputation or a smaller
  micro-batch does. Name what binds, use `<plugin root>/skills/physics-ml/scripts/estimate_training_memory.py` for numbers,
  prefer DDP when it fits, and say that the figures are estimates to confirm on the real job.
  Most HEP taggers and regressors (well under 100M parameters) fit one GPU: DDP, not sharding.
- **Comparisons need matched budgets and several seeds** before words like "better" or
  "state-of-the-art" go into text.

## Workflow

1. **Clarify task shape**: classification (binary/multiclass/multilabel), regression,
   or custom? Input/output shapes and label format? State assumptions explicitly if unstated.
2. **Pick the smallest correct structure.** Single script for compact tasks; for
   nontrivial ones, separate `models.py`, `data.py`, `train.py`, `evaluate.py`,
   `infer.py`, `losses.py`, `metrics.py`, `config.yaml` (templates in [assets/](../assets/)).
3. **Write model/training/eval loops** per the conventions below - device handling,
   `train()`/`eval()` modes, `no_grad`/`inference_mode`, correct loss, gradient zeroing,
   checkpointing.
4. **Add reproducibility and shape-safety** where it matters - seed everything, add
   shape comments/asserts on non-obvious tensor dimensions.
5. **Validate before declaring done**: `<plugin root>/skills/physics-ml/scripts/check_pytorch_env.py` if the environment
   is unfamiliar, a tiny forward/backward pass on dummy data, and (data pipelines)
   `<plugin root>/skills/physics-ml/scripts/check_dataset_contract.py` / `<plugin root>/skills/physics-ml/scripts/profile_dataloader.py`.
6. **Present results per the Response Format below.**

## Core Principles

1. Prefer clear, explicit, runnable code over clever abstractions.
2. Separate model, data, training, evaluation, config, and utilities once the task is
   nontrivial.
3. Handle device placement deliberately (see snippet below) - move the model once,
   move batch tensors inside the loop.
4. Set `model.train()` / `model.eval()` correctly; use `torch.no_grad()` or
   `torch.inference_mode()` for eval and inference.
5. `optimizer.zero_grad(set_to_none=True)` before backward.
6. Aggregate losses/metrics weighted by batch size, not by step count.
7. Save checkpoints with model, optimizer, scheduler, epoch, best metric, and config.
8. Add shape comments/asserts where dimensions are likely to confuse a reader.
9. Make code deterministic where practical, but say so when determinism trades off
   performance.

## Device Handling

```python
import torch

if torch.cuda.is_available():
    device = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

model = model.to(device)  # once

# inside the loop:
inputs = inputs.to(device, non_blocking=True)
targets = targets.to(device, non_blocking=True)
```


## GPU Builds, Clusters and DDP

- **A torch CUDA build runs only on the compute capabilities it was compiled for.** Before submitting GPU jobs,
  compare the build's list with the GPU (`nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv`).
  Read the list with `torch._C._cuda_getArchFlags()`: it works without a GPU, whereas `torch.cuda.get_arch_list()`
  returns `[]` wherever CUDA is unavailable (a login node). Old and new GPUs may need different builds of the same
  torch version (observed with the torch 2.14.1 wheels, 2026-10: the CUDA 12.6 build stops at sm_90, the CUDA 13.0
  build starts at sm_75, so V100 and Blackwell need one each). The driver must also support the build's CUDA version.
  `<plugin root>/skills/physics-ml/scripts/check_pytorch_env.py` does this comparison on a GPU host and exits 3 when
  a visible GPU is not supported by the installed build; run it as the first step of a GPU job.
- **Mixed precision** (bf16 vs fp16, `GradScaler`, raw inputs in MeV or ADC counts overflowing fp16, emulated bf16
  on V100, when it is not faster): [mixed-precision.md](mixed-precision.md).
- **DDP with `torchrun`:** code that calls `torch.cuda.set_device(LOCAL_RANK)` needs at least `--nproc_per_node`
  visible GPUs; with fewer, the extra ranks fail with "invalid device ordinal". To run such a script as a CPU/gloo
  smoke test on a GPU host, hide the GPUs (`CUDA_VISIBLE_DEVICES=""`). With `NCCL_DEBUG=INFO` the log shows the
  transport chosen (P2P, SHM or network).
- On a batch cluster, ask for CPUs and memory next to each GPU deliberately (data loading needs cores), and keep the
  environment in a venv run with `PYTHONNOUSERSITE=1` so packages in `~/.local` cannot leak in.
- GPU tests for these assets: `tests/skills/physics_ml/test_gpu_real.py`, opt-in with `HEP_TORCH_GPU_TEST=1` on a
  GPU host (NCCL DDP needs two visible GPUs).

## Task -> Loss/Output Conventions

| Task | Output shape | Target | Loss | Notes |
|---|---|---|---|---|
| Multiclass classification | `[B, num_classes]` logits | `[B]` int class indices | `nn.CrossEntropyLoss()` | Don't apply softmax before this loss |
| Binary classification | `[B]` or `[B, 1]` logits | `[B]` float 0/1 | `nn.BCEWithLogitsLoss()` | Don't apply sigmoid before this loss |
| Multilabel classification | `[B, num_labels]` logits | `[B, num_labels]` multi-hot float | `nn.BCEWithLogitsLoss()` | |
| Regression | matches target shape | matches output | `nn.MSELoss` / `nn.L1Loss` / `nn.SmoothL1Loss` | normalize if scales differ wildly |

## Naming Conventions (Google Python Style / PEP 8)

- `snake_case` for variables/functions/modules; `PascalCase` for classes including
  `nn.Module` and `Dataset` subclasses; `UPPER_SNAKE_CASE` for module constants;
  `_leading_underscore` for private helpers.
- Use meaningful DL names: `inputs`, `targets`, `logits`, `predictions`, `loss`,
  `optimizer`, `scheduler`, `dataloader`, `batch_size`, `learning_rate`, `device`.
- For tensors, prefer descriptive names over bare type names: `image_batch`,
  `attention_mask`, `class_logits`, `sequence_lengths` rather than `tensor`/`data`/`output`.
- Conventional dim names: `batch_size`, `num_channels`, `height`, `width`,
  `sequence_length`, `embedding_dim`, `hidden_dim`, `num_classes`.

## Comments

Add comments only where they clarify something non-obvious: tensor shape
transformations, numerical-stability choices, device/dtype/precision constraints,
label-encoding assumptions, checkpoint compatibility. Don't comment what the code
already says (`# zero gradients`, `# move to device`).

## Code File Requirement

Every code file (`models.py`, `train.py`, `data.py`, config loaders, etc.) needs a
top-of-file intro block - module-level docstring in Python, equivalent comment syntax
elsewhere - covering:

- **Purpose** - why the file exists (e.g. "model definitions", "training entry point").
- **What the code does** - main behavior, plus expected input/output shapes and label
  formats where relevant.
- **Usage notes** - run/import command, required packages or CUDA/MPS, config keys,
  dataset layout, preconditions.

Add it to existing files if missing or outdated; keep it proportional and in sync with
the code. Distinct from inline comments above - this describes the file as a whole.

## When to Read a Reference

Physics first (the deliverable is a model or study for a physics result):

- **Classifier or regressor in an analysis: grouped splits, event weights (including negative ones), working points, mass decorrelation, systematic-aware training, simulation-to-data checks, weak supervision, deployment in experiment software and triggers** -> [ml-analysis.md](ml-analysis.md)
- **BDT vs NN, BDT practice (XGBoost, LightGBM, TMVA), regression targets** -> [multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md)
- **Jets, particle sets, hits, point clouds, graphs; padding and masks** -> [particle-and-jet-architectures.md](particle-and-jet-architectures.md)
- **Fast simulation: training generative models and validating them before use** -> [fast-simulation-validation.md](fast-simulation-validation.md) and [generative-models.md](generative-models.md)
- **Space or ground-based astroparticle detectors** -> [space-and-astroparticle-ml.md](space-and-astroparticle-ml.md)
- **Simulation-based inference: training the networks** -> [sbi-training.md](sbi-training.md); validity and coverage of the inference belong to `hep-statistics`

PyTorch engineering:

- **Training loop shape, grad clipping, accumulation** -> [references/training-loop.md](training-loop.md)
- **Training loss not decreasing, instability, plateaus, vanishing/exploding gradients, LR/weight-decay behavior** -> [references/optimization-and-training-dynamics.md](optimization-and-training-dynamics.md)
- **Debugging shape/device/dtype/NaN errors** -> [references/debugging-pytorch.md](debugging-pytorch.md)
  and [references/tensor-shapes.md](tensor-shapes.md)
- **Dataset/DataLoader design, collate functions, grouped splits** -> [references/data-loading.md](data-loading.md)
- **AMP / mixed precision (bf16, fp16 and GradScaler, fp16 overflow of raw inputs)** -> [references/mixed-precision.md](mixed-precision.md)
- **Checkpoint save/load/resume (RNG, scaler, data order, atomic writes)** -> [references/checkpointing.md](checkpointing.md)
- **DDP / multi-GPU, FSDP2 and distributed checkpoints** -> [references/distributed-training.md](distributed-training.md)
- **Choosing a parallelism strategy (DDP vs. FSDP/ZeRO vs. tensor/pipeline/sequence), the memory equation, what is binding** -> [references/parallelism-strategy.md](parallelism-strategy.md) (generic)
- **Metrics for classification/regression** -> [references/evaluation-metrics.md](evaluation-metrics.md); physics-weighted metrics are in [ml-analysis.md](ml-analysis.md)
- **Speed/memory tuning, `torch.compile` and variable particle multiplicity** -> [references/performance-memory.md](performance-memory.md)
- **Seeding and determinism caveats** -> [references/reproducibility.md](reproducibility.md)
- **Fine-tuning / freezing layers / pretrained backbones** -> [references/transfer-learning.md](transfer-learning.md)
- **Parameter-efficient fine-tuning (LoRA) of a large pretrained model, quantization** -> [references/efficient-finetuning.md](efficient-finetuning.md) (generic)
- **Attention, multi-head attention, positional encoding, encoder/decoder design** -> [references/transformer-architectures.md](transformer-architectures.md) (generic; particle transformers are in particle-and-jet-architectures.md)
- **RNN/LSTM/GRU, packed sequences, teacher forcing, seq2seq** -> [references/sequence-models.md](sequence-models.md) (generic)
- **VAE/GAN/diffusion/flow training loops and failure modes (posterior collapse, mode collapse)** -> [references/generative-models.md](generative-models.md)
- **Custom autograd.Function, hooks, activation/gradient checkpointing** -> [references/custom-autograd-and-hooks.md](custom-autograd-and-hooks.md)
- **ONNX, `torch.export` and AOTInductor export, TMVA SOFIE and hls4ml targets, `torch.compile` for inference** -> [references/export-and-deployment.md](export-and-deployment.md)
- **LibTorch, custom ops, CUDA/C++ extensions** -> [hep-computing's C++ design guidelines](../../hep-computing/references/cpp-balanced-design-guidelines.md)
- **Authoring a canonical worked example** (Contrast, Execution Trajectory,
  Gated Pipeline, Decision-Tree, Interactive Elicitation, Adversarial Audit,
  Test-First, or Postmortem archetype) for `examples/` ->
  `hep-computing`'s
  [references/example-authoring.md](../../hep-computing/references/example-authoring.md)

Architect-level references - decisions made before or around the code:

- **Choosing/sizing an architecture, inductive bias, scaling laws, reviewing a proposal** -> [references/architecture-selection.md](architecture-selection.md)
- **Proving a change helped: seed variance, matched budgets, ablations, confounds** -> [references/ablation-and-design-review.md](ablation-and-design-review.md)
- **MFU and throughput, compute/cost budgeting, batch-size and LR scaling, failure recovery, HP search** -> [references/training-at-scale.md](training-at-scale.md) (generic)
- **Inference latency and throughput budgets, batching, capacity planning for a service** -> [references/serving-architecture.md](serving-architecture.md) (generic; trigger deployment is in ml-analysis.md)
- **Monitoring a deployed model, regression suites, versioning, retraining triggers** -> [references/monitoring-and-lifecycle.md](monitoring-and-lifecycle.md) (generic)
- **Dataset design, label quality, splits, leakage, deduplication, imbalance** -> [references/data-strategy.md](data-strategy.md)
- **Eval harness design, slices, behavioral tests, offline-online gap, ship criteria** -> [references/evaluation-strategy.md](evaluation-strategy.md)
- **Training failure diagnosis: distinguishing implementation, optimization, capacity, data, generalization, numerical, and objective-mismatch failure; LR/batch-size/gradient interactions** -> [references/optimization-and-training-dynamics.md](optimization-and-training-dynamics.md)
- **Confidence, calibration, predictive uncertainty, aleatoric vs. epistemic** -> [references/uncertainty-and-calibration.md](uncertainty-and-calibration.md)
- **OOD behavior, domain/nuisance/simulation-to-data shift, robustness beyond IID** -> [references/robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)
- **Physics constraints, surrogate models/emulators, simulation-based inference, scientific ML** -> [references/scientific-machine-learning.md](scientific-machine-learning.md)
- **Symmetry, invariance/equivariance, sets/graphs/point clouds, Lorentz-aware modeling** -> [references/geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md)
- **Saliency/attribution/attention interpretation, representation learning, embeddings, scientific claims about learned structure** -> [references/interpretability-and-explainability.md](interpretability-and-explainability.md)

## Helper Scripts & Templates

Read `--help` first, and run diagnostics with `python3` before assuming a fix worked.

Scripts in `<plugin root>/skills/physics-ml/scripts/`:

- `check_pytorch_env.py` - verify torch version, CUDA/MPS availability, device count, and that the build supports the visible GPUs.
- `inspect_checkpoint.py <path>` - print checkpoint keys, shapes, epoch, config.
- `profile_dataloader.py` - time dataloader iteration to find I/O bottlenecks.
- `check_dataset_contract.py` - verify a `Dataset` returns consistent shapes/dtypes.
- `find_nan_batches.py` - scan a dataloader for non-finite inputs/targets.
- `benchmark_model.py` - time forward/backward passes for a model (`--amp` to compare mixed precision).
- `make_grouped_splits.py` - write a train/validation/test split manifest that keeps each group (run, period, event, simulation seed) in one split.
- `check_split_integrity.py` - train/val/test overlap, duplicates, group leakage, and temporal violations; exits nonzero so it can gate a pipeline.
- `check_surrogate_domain.py` - flag inputs outside a surrogate's declared training domain.
- `compare_model_runs.py` - paired comparison of two configurations across seeds, with a bootstrap interval on the difference and the seed-noise floor.
- `write_ml_artifact.py` - write the `ml-artifact` for a trained model (splits, weights, preprocessing, model hash, calibration).
- `estimate_training_memory.py` - per-GPU training memory (params, grads, optimizer states, activations) under a precision/optimizer/ZeRO/TP/PP configuration, with the binding term and what to change.
- `estimate_compute_budget.py` - training FLOPs, GPU-hours, wall-clock, cost and MFU (generic; its tokens-per-parameter regime applies to language-model-style training).
- `serving_capacity.py` - replicas, utilization, and estimated p99 latency for an inference service against a latency budget (generic).

When relaying output from these (profiler timings, NaN scan hits, training logs),
report the top ~5 offending items, not the raw dump.

The first six scripts import PyTorch and exit with a clear message when it is missing;
`check_split_integrity.py`, `check_surrogate_domain.py`, `compare_model_runs.py` and the
three estimators are standard library only. Tests:

- `<plugin root>/tests/skills/physics_ml/test_physics_ml_skill.py` - standard-library tests for the diagnostic
  scripts above, including their behavior when PyTorch is not installed. Run
  `python3 -m unittest discover -s tests -t .` from the plugin root.
- `<plugin root>/tests/skills/physics_ml/test_assets_smoke.py` - CPU smoke tests that run the
  `<plugin root>/skills/physics-ml/assets/` templates on tiny synthetic data (skipped when PyTorch is missing).

Starting points in `<plugin root>/skills/physics-ml/assets/` to copy and adapt:

- `hep_metrics.py` (signed-weight ROC, rejection at fixed signal efficiency, Asimov significance, distance correlation, mass-sculpting JSD; NumPy) and `hep_losses.py` (signed-weight BCE, DisCo penalty, NaN-safe masked softmax and mean).
- `models.py`, `dataset_template.py`, `train_classifier.py`, `inference.py`, `metrics.py`,
  `vision_transfer.py`, `ddp_train_skeleton.py`, `config.yaml`.
- `set_classifier.py` - a permutation-invariant classifier for particle sets with padding masks.
- `calibration.py` - post-hoc calibration of classifier scores on a held-out calibration split.
- `transformer_classifier.py` - a from-scratch Transformer encoder (multi-head attention,
  positional encoding, padding mask, mean-pooling) for sequence classification.
- `lora_finetune.py` - LoRA adapter wrapper and a fine-tuning loop that trains only the
  adapter parameters against a frozen pretrained model (for example a jet foundation model).
- `eval-runs.example.json` - synthetic per-seed scores for `compare_model_runs.py`.
- `dataset-splits.example.json` - synthetic split manifest of events grouped by run,
  deliberately containing a run in both train and test and a time-order violation, for
  `check_split_integrity.py`.

## Debugging Checklist

When something breaks, check in this order: tensor shapes -> dtypes -> devices ->
batch dimension present -> target format matches the loss -> logits vs. probabilities
-> `train()`/`eval()` mode set correctly -> gradients zeroed -> `backward()` called
exactly once per step -> optimizer has the right parameters -> normalization matches
model expectations -> label ranges valid -> NaN/inf in inputs/outputs/loss/grads ->
parameters `requires_grad` as expected -> checkpoint keys match the model.

```python
print("inputs", inputs.shape, inputs.dtype, inputs.device)
torch.isfinite(inputs).all()
with torch.autograd.set_detect_anomaly(True):  # debugging only, slow
    loss.backward()
```

Common NaN/explosion fixes: lower LR, clip gradients, normalize inputs, use
`BCEWithLogitsLoss` instead of sigmoid+BCE, avoid `log(0)`, check label ranges/dtypes.

## Code Review Checklist

Watch for: layers created inside `forward`, missing `.to(device)`, device/dtype
mismatch, softmax before `CrossEntropyLoss` or sigmoid before `BCEWithLogitsLoss`,
missing `train()`/`eval()`, missing `no_grad`/`inference_mode` in eval, missing
`zero_grad`, wrong loss averaging, wrong scheduler-step frequency, forgotten
`scaler.update()` with AMP, graph tensors stashed in lists (`.append(loss)` instead of
`.append(loss.item())`), optimizer state missing from checkpoints, checkpoints loaded
without `map_location`, train/val data leakage.

## Response Format

**When writing code**: state task + assumptions briefly -> complete runnable code ->
run command -> expected input shapes/label formats -> validation tips.

**When debugging**: likely cause -> PyTorch-specific reason -> minimal fix -> robust
corrected snippet -> a quick diagnostic print/assert to confirm the fix.

## Example Prompts This Skill Handles Well

- "Train a BDT for my event selection with negative generator weights, split by run."
- "Write a PyTorch training loop for a particle-set jet tagger with padding masks."
- "My loss goes to NaN after a few hundred steps - here's my training code."
- "Add mixed precision and gradient accumulation to this script."
- "Review this `Dataset`/`DataLoader` for correctness and performance."
- "Convert this single-GPU training script to DDP."
- "My generative shower model OOMs on one A100 - DDP, FSDP2, or a smaller micro-batch?"
- "Is this 0.4% accuracy gain real, or is it seed noise?"
- "Export this tagger to ONNX for the experiment's reconstruction software, with a variable number of particles."
- "Review how this dataset is split before we trust the eval numbers."
- "Is this classifier's 0.99 confidence actually a calibrated probability?"
- "This surrogate model is accurate in its training range but we're running it outside that range - is that OK?"
- "The latent space shows clusters that match a known physical category - does that mean the model learned the physics?"
- "Generate a canonical `examples/` entry for this skill contrasting a weak vs. expert
  DataLoader/training loop for an imbalanced dataset."

## Caveats

- Don't introduce `torch.compile`, AMP, or DDP unless asked or clearly needed - guard
  `torch.compile` behind `hasattr(torch, "compile")`.
- Deterministic mode (`cudnn.deterministic=True`) trades performance for
  reproducibility - mention this tradeoff when you enable it.
- For broader engineering process (scoping, testing, review), pair with
  `hep-computing` ([agile-development-guide.md](../../hep-computing/references/agile-development-guide.md)).
- For the scientific/statistical validity of conclusions drawn from model outputs -
  likelihoods, confidence intervals, discovery/exclusion claims - pair with
  `hep-statistics` (and `research-communication` for how the claim is written up); this guide covers whether the model itself is trained,
  evaluated, calibrated, and robust.
