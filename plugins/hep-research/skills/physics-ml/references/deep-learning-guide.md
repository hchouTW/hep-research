# PyTorch Engineering (guide)

## When to read this file

This file holds the routing and rules for PyTorch engineering work and ML
engineering decisions; it routes to the other references in this folder.

Produce practical, runnable, maintainable PyTorch code with strong defaults for
correctness, reproducibility, debugging, and extensibility - code another engineer can
run, test, and modify without archaeology.

Out of scope: non-PyTorch DL frameworks, general C++ unrelated to LibTorch/custom ops -
unless porting code into/out of PyTorch.

## Scope and Proportion

- **Other stacks:** for Keras/TensorFlow/JAX or classical ML (scikit-learn, XGBoost, tabular
  trees), answer in that stack's own idioms. Do not apply this guide's Workflow, templates,
  naming conventions, file-header rule or Response Format, and do not read its references;
  at most one line noting that it is outside PyTorch scope. Porting to/from PyTorch is the
  exception.
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

- **Training loop shape, grad clipping, accumulation** -> [references/training-loop.md](training-loop.md)
- **Training loss not decreasing, instability, plateaus, vanishing/exploding gradients, LR/weight-decay behavior** -> [references/optimization-and-training-dynamics.md](optimization-and-training-dynamics.md)
- **Debugging shape/device/dtype/NaN errors** -> [references/debugging-pytorch.md](debugging-pytorch.md)
  and [references/tensor-shapes.md](tensor-shapes.md)
- **Dataset/DataLoader design, collate functions** -> [references/data-loading.md](data-loading.md)
- **AMP / mixed precision** -> [references/mixed-precision.md](mixed-precision.md)
- **Checkpoint save/load/resume** -> [references/checkpointing.md](checkpointing.md)
- **DDP / multi-GPU** -> [references/distributed-training.md](distributed-training.md)
- **Choosing a parallelism strategy (DDP vs. FSDP/ZeRO vs. tensor/pipeline/sequence), the memory equation, what is binding** -> [references/parallelism-strategy.md](parallelism-strategy.md)
- **Metrics for classification/regression** -> [references/evaluation-metrics.md](evaluation-metrics.md)
- **Speed/memory tuning** -> [references/performance-memory.md](performance-memory.md)
- **Seeding and determinism caveats** -> [references/reproducibility.md](reproducibility.md)
- **Fine-tuning / freezing layers / vision backbones** -> [references/transfer-learning.md](transfer-learning.md)
- **Parameter-efficient fine-tuning (LoRA), quantization** -> [references/efficient-finetuning.md](efficient-finetuning.md)
- **Attention, multi-head attention, positional encoding, encoder/decoder design, KV caching** -> [references/transformer-architectures.md](transformer-architectures.md)
- **RNN/LSTM/GRU, packed sequences, teacher forcing, seq2seq** -> [references/sequence-models.md](sequence-models.md)
- **VAE/GAN/diffusion training loops and failure modes (posterior collapse, mode collapse)** -> [references/generative-models.md](generative-models.md)
- **Custom autograd.Function, hooks, activation/gradient checkpointing** -> [references/custom-autograd-and-hooks.md](custom-autograd-and-hooks.md)
- **TorchScript/ONNX export, torch.compile deployment modes, inference serving** -> [references/export-and-deployment.md](export-and-deployment.md)
- **LibTorch, custom ops, CUDA/C++ extensions** -> [hep-computing's C++ design guidelines](../../hep-computing/references/cpp-balanced-design-guidelines.md)
- **Authoring a canonical worked example** (Contrast, Execution Trajectory,
  Gated Pipeline, Decision-Tree, Interactive Elicitation, Adversarial Audit,
  Test-First, or Postmortem archetype) for `examples/` ->
  `hep-computing`'s
  [references/example-authoring.md](../../hep-computing/references/example-authoring.md)

Architect-level references - decisions made before or around the code:

- **Choosing/sizing an architecture, inductive bias, scaling laws, reviewing a proposal** -> [references/architecture-selection.md](architecture-selection.md)
- **Proving a change helped: seed variance, matched budgets, ablations, confounds** -> [references/ablation-and-design-review.md](ablation-and-design-review.md)
- **MFU and throughput, compute/cost budgeting, batch-size and LR scaling, failure recovery, HP search** -> [references/training-at-scale.md](training-at-scale.md)
- **Serving latency/throughput/cost budgets, batching, KV cache limits, capacity planning** -> [references/serving-architecture.md](serving-architecture.md)
- **Drift and monitoring, regression suites, shadow/canary rollout, versioning, retraining triggers** -> [references/monitoring-and-lifecycle.md](monitoring-and-lifecycle.md)
- **Dataset design, label quality, splits, leakage, deduplication, imbalance** -> [references/data-strategy.md](data-strategy.md)
- **Eval harness design, slices, behavioral tests, offline-online gap, ship criteria** -> [references/evaluation-strategy.md](evaluation-strategy.md)
- **Training failure diagnosis: distinguishing implementation, optimization, capacity, data, generalization, numerical, and objective-mismatch failure; LR/batch-size/gradient interactions** -> [references/optimization-and-training-dynamics.md](optimization-and-training-dynamics.md)
- **Confidence, calibration, predictive uncertainty, aleatoric vs. epistemic** -> [references/uncertainty-and-calibration.md](uncertainty-and-calibration.md)
- **OOD behavior, domain/nuisance/simulation-to-data shift, robustness beyond IID** -> [references/robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)
- **Physics constraints, surrogate models/emulators, simulation-based inference, scientific ML** -> [references/scientific-machine-learning.md](scientific-machine-learning.md)
- **Symmetry, invariance/equivariance, sets/graphs/point clouds, Lorentz-aware modeling** -> [references/geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md)
- **Saliency/attribution/attention interpretation, representation learning, embeddings, scientific claims about learned structure** -> [references/interpretability-and-explainability.md](interpretability-and-explainability.md)

## Helper Scripts & Templates

Run diagnostics with `python3` before assuming a fix worked:

- `<plugin root>/skills/physics-ml/scripts/check_pytorch_env.py` - verify torch version, CUDA/MPS availability, device count.
- `<plugin root>/skills/physics-ml/scripts/inspect_checkpoint.py <path>` - print checkpoint keys, shapes, epoch, config.
- `<plugin root>/skills/physics-ml/scripts/profile_dataloader.py` - time dataloader iteration to find I/O bottlenecks.
- `<plugin root>/skills/physics-ml/scripts/check_dataset_contract.py` - verify a `Dataset` returns consistent shapes/dtypes.
- `<plugin root>/skills/physics-ml/scripts/find_nan_batches.py` - scan a dataloader for non-finite inputs/targets.
- `<plugin root>/skills/physics-ml/scripts/benchmark_model.py` - time forward/backward passes for a model.
- `<plugin root>/skills/physics-ml/scripts/estimate_training_memory.py` - per-GPU training memory (params, grads,
  optimizer states, activations) under a precision/optimizer/ZeRO/TP/PP configuration,
  with the binding term and what to change.
- `<plugin root>/skills/physics-ml/scripts/estimate_compute_budget.py` - training FLOPs, GPU-hours, wall-clock, cost,
  and MFU, plus the tokens-per-parameter sizing regime.
- `<plugin root>/skills/physics-ml/scripts/compare_model_runs.py` - paired comparison of two configurations across
  seeds, with a bootstrap interval on the difference and the seed-noise floor.
- `<plugin root>/skills/physics-ml/scripts/serving_capacity.py` - replicas, utilization, and estimated p99 latency for
  an inference service against a latency budget.
- `<plugin root>/skills/physics-ml/scripts/check_split_integrity.py` - train/val/test overlap, duplicates, group
  leakage, and temporal violations; exits nonzero so it can gate a pipeline.

When relaying output from these (profiler timings, NaN scan hits, training logs),
report the top ~5 offending items, not the raw dump.

The five scripts above are standard library only and do not require PyTorch.
- `<plugin root>/tests/skills/physics_ml/test_physics_ml_skill.py` - standard-library tests for the diagnostic
  scripts above, including their behavior when PyTorch is not installed. Run
  `python3 -m unittest discover -s tests -t .` from the plugin root.
- `<plugin root>/tests/skills/physics_ml/test_assets_smoke.py` - CPU smoke tests that run the `<plugin root>/skills/physics-ml/assets/` templates on tiny
  synthetic data (skipped when PyTorch is missing).

Starting points to copy and adapt:

- `<plugin root>/skills/physics-ml/assets/models.py`, `<plugin root>/skills/physics-ml/assets/dataset_template.py`, `<plugin root>/skills/physics-ml/assets/train_classifier.py`,
  `<plugin root>/skills/physics-ml/assets/inference.py`, `<plugin root>/skills/physics-ml/assets/metrics.py`, `<plugin root>/skills/physics-ml/assets/vision_transfer.py`,
  `<plugin root>/skills/physics-ml/assets/ddp_train_skeleton.py`, `<plugin root>/skills/physics-ml/assets/config.yaml`.
- `<plugin root>/skills/physics-ml/assets/transformer_classifier.py` - a from-scratch Transformer encoder
  (multi-head attention, positional encoding, padding mask, mean-pooling) for
  sequence classification.
- `<plugin root>/skills/physics-ml/assets/lora_finetune.py` - LoRA adapter wrapper and a fine-tuning loop that
  trains only the adapter parameters against a frozen base model.
- `<plugin root>/skills/physics-ml/assets/scaling-plan.example.json` - synthetic 7B-class training plan for
  `<plugin root>/skills/physics-ml/scripts/estimate_training_memory.py`.
- `<plugin root>/skills/physics-ml/assets/eval-runs.example.json` - synthetic per-seed scores for
  `<plugin root>/skills/physics-ml/scripts/compare_model_runs.py`.
- `<plugin root>/skills/physics-ml/assets/dataset-splits.example.json` - synthetic split manifest, deliberately
  containing a group leak and a temporal violation, for
  `<plugin root>/skills/physics-ml/scripts/check_split_integrity.py`.

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

- "Write a training loop for a ResNet18 fine-tune on a custom image dataset."
- "My loss goes to NaN after a few hundred steps - here's my training code."
- "Add mixed precision and gradient accumulation to this script."
- "Review this `Dataset`/`DataLoader` for correctness and performance."
- "Convert this single-GPU training script to DDP."
- "This 7B model OOMs on 8 A100s - should I use FSDP, tensor parallel, or something else?"
- "How long and how much would it cost to train this model, and is it the right size?"
- "Is this 0.4% accuracy gain real, or is it seed noise?"
- "How many replicas do we need to serve 500 QPS under a 250 ms p99 budget?"
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
