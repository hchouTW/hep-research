# PyTorch Engineering (guide)

## When to read this file

Routing and rules for PyTorch engineering; it routes to the other references in this folder. For the physics side of
an ML task (splits by run, event weights, working points, decorrelation, simulation-to-data checks) start at
[ml-analysis.md](ml-analysis.md). The goal is runnable, maintainable PyTorch code with strong defaults for correctness,
reproducibility and debugging. Out of scope: non-PyTorch frameworks and C++ unrelated to LibTorch or custom ops,
unless porting into or out of PyTorch.

## Scope and proportion

- **BDTs and classical MVA in physics analyses are in scope** (XGBoost, LightGBM, TMVA, scikit-learn):
  [multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md) and [ml-analysis.md](ml-analysis.md). The
  PyTorch workflow and templates below do not apply to them.
- **Other stacks** (Keras, TensorFlow, JAX): answer in that stack's idioms, keep the physics rules of
  [ml-analysis.md](ml-analysis.md), skip the PyTorch references.
- **Size the answer to the request.** A one-line shape error gets a short diagnosis and fix, not the full template.
- **Vague requests** ("make it faster", "improve accuracy"): ask what is slow or which metric, or state the
  assumption. Measure first, name at most three ranked suspects, and do not recommend `torch.compile`, AMP or DDP
  before a measurement shows that they bind.

## Rules to apply even without opening a reference

- **Checkpoint config is plain data** (`vars(args)`, `dataclasses.asdict`): `torch.load` defaults to
  `weights_only=True` since PyTorch 2.6, so a custom-class config fails to load. `weights_only=False` only for files
  you trust.
- **Simulation is not data.** A metric on simulated test events says nothing about data. Ask for data-driven
  validation (control region, sideband, tag-and-probe), compare input and score distributions between data and
  simulation, and carry the mismodeling as a systematic on any efficiency taken from simulation. A score is not a
  probability until it is calibrated on held-out data separate from the test set.
- **Diagnose before prescribing regularization.** Check split leakage, duplicates, seed variance and data size first;
  change one thing at a time against the seed-noise baseline. For set, point-cloud or particle inputs, say whether the
  model is permutation invariant and whether an ordering is imposed; keep permutation invariance separate from
  rotation or Lorentz equivariance.
- **Do the memory equation before choosing a parallelism strategy**
  ([parallelism-strategy.md](parallelism-strategy.md), the one home of the equation;
  `<plugin root>/skills/hep-ml/scripts/estimate_training_memory.py` for numbers). Most HEP taggers and regressors
  (well under 100M parameters) fit one GPU: DDP, not sharding.
- **Comparisons need matched budgets and several seeds** before "better" or "state-of-the-art" goes into text.

## Workflow

1. Clarify the task shape (binary, multiclass, multilabel, regression; input and output shapes; label format); state
   assumptions.
2. Pick the smallest correct structure: one script for compact tasks; for larger ones `models.py`, `data.py`,
   `train.py`, `evaluate.py`, `infer.py`, `losses.py`, `metrics.py`, `config.yaml` (templates in [assets/](../assets/)).
3. Write the loops with deliberate device handling, `train()`/`eval()` modes, `no_grad`/`inference_mode`, the loss
   below, gradient zeroing and checkpointing.
4. Seed everything; add shape comments or asserts where dimensions confuse.
5. Validate before declaring done: `check_pytorch_env.py` on an unfamiliar environment, a forward/backward pass on
   dummy data, and for data pipelines `check_dataset_contract.py` and `profile_dataloader.py`.

Core conventions: move the model to the device once and batch tensors inside the loop
(`cuda`, then `mps`, then `cpu`); `optimizer.zero_grad(set_to_none=True)` before backward; aggregate losses and
metrics weighted by batch size; checkpoints hold model, optimizer, scheduler, epoch, best metric and config; say when
determinism costs performance. Naming, comments and file headers follow hep-computing's
[Python guidelines](../../hep-computing/references/python-balanced-design-guidelines.md) (use the deep-learning names
`inputs`, `targets`, `logits`, `batch_size`, `num_classes`, ... for tensors and dimensions).

## Task -> loss and output (the one home of the logits rule)

| Task | Output shape | Target | Loss | Notes |
|---|---|---|---|---|
| Multiclass classification | `[B, num_classes]` logits | `[B]` int class indices | `nn.CrossEntropyLoss()` | no softmax before this loss |
| Binary classification | `[B]` or `[B, 1]` logits | `[B]` float 0/1 | `nn.BCEWithLogitsLoss()` | no sigmoid before this loss |
| Multilabel classification | `[B, num_labels]` logits | `[B, num_labels]` multi-hot float | `nn.BCEWithLogitsLoss()` | |
| Regression | matches target | matches output | `nn.MSELoss` / `nn.L1Loss` / `nn.SmoothL1Loss` | the loss picks the summary learned ([multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md), "Regression targets") |

The losses apply log-softmax or log-sigmoid internally in a numerically stable form; feeding probabilities doubles the
squashing and loses precision. Signed event weights: `assets/hep_losses.py` (`weighted_bce`).

## GPU builds, clusters and DDP

- **A torch CUDA build runs only on the compute capabilities it was compiled for.** Compare the build's list
  (`torch._C._cuda_getArchFlags()`, which works without a GPU) with the GPU
  (`nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv`); old and new GPUs may need different builds
  of one torch version (observed with the torch 2.14.1 wheels, 2026-10: the CUDA 12.6 build stops at sm_90, the CUDA
  13.0 build starts at sm_75). `check_pytorch_env.py` exits 3 when a visible GPU is not supported; run it first in a
  GPU job.
- **Mixed precision:** [mixed-precision.md](mixed-precision.md).
- **DDP with `torchrun`:** code that calls `torch.cuda.set_device(LOCAL_RANK)` needs `--nproc_per_node` visible GPUs;
  for a CPU/gloo smoke test on a GPU host set `CUDA_VISIBLE_DEVICES=""`. `NCCL_DEBUG=INFO` shows the transport.
- On a batch cluster request CPUs and memory next to each GPU (data loading needs cores) and run the venv with
  `PYTHONNOUSERSITE=1`. GPU tests: `tests/skills/hep_ml/test_gpu_real.py` with `HEP_TORCH_GPU_TEST=1`.

## When to read a reference

Physics first:

- Classifier or regressor in an analysis (grouped splits, event weights, working points, decorrelation,
  systematic-aware training, simulation-to-data, weak supervision, deployment) -> [ml-analysis.md](ml-analysis.md);
  its Task routes index lists the rest
- BDT vs NN, BDT practice, regression targets -> [multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md)
- Jets, particle sets, hits, point clouds, graphs -> [particle-and-jet-architectures.md](particle-and-jet-architectures.md)
- Fast simulation -> [fast-simulation-validation.md](fast-simulation-validation.md), [generative-models.md](generative-models.md)
- Astroparticle detectors -> [space-and-astroparticle-ml.md](space-and-astroparticle-ml.md)
- SBI training -> [sbi-training.md](sbi-training.md) (validity and coverage: `hep-statistics`)
- Calibration, uncertainty, systematics -> [uncertainty-and-calibration.md](uncertainty-and-calibration.md); shift
  and OOD -> [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md); surrogates and physics
  constraints -> [scientific-machine-learning.md](scientific-machine-learning.md); symmetries ->
  [geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md); interpretation ->
  [interpretability-and-explainability.md](interpretability-and-explainability.md)

PyTorch engineering:

- Training loop, clipping, accumulation -> [training-loop.md](training-loop.md); loss not decreasing, instability,
  LR -> [optimization-and-training-dynamics.md](optimization-and-training-dynamics.md)
- Shape, device, dtype, NaN errors -> [debugging-pytorch.md](debugging-pytorch.md), [tensor-shapes.md](tensor-shapes.md)
- Datasets and loaders -> [data-loading.md](data-loading.md); AMP -> [mixed-precision.md](mixed-precision.md);
  checkpoints -> [checkpointing.md](checkpointing.md); DDP and FSDP2 -> [distributed-training.md](distributed-training.md);
  parallelism choice and memory -> [parallelism-strategy.md](parallelism-strategy.md)
- Metrics -> [evaluation-metrics.md](evaluation-metrics.md) (physics-weighted ones in ml-analysis.md); speed, memory,
  `torch.compile` -> [performance-memory.md](performance-memory.md); seeding -> [reproducibility.md](reproducibility.md)
- Fine-tuning and LoRA -> [transfer-learning.md](transfer-learning.md), [efficient-finetuning.md](efficient-finetuning.md);
  attention -> [transformer-architectures.md](transformer-architectures.md); RNNs -> [sequence-models.md](sequence-models.md);
  generative training -> [generative-models.md](generative-models.md); custom autograd and hooks ->
  [custom-autograd-and-hooks.md](custom-autograd-and-hooks.md); export (ONNX, `torch.export`, SOFIE, hls4ml) ->
  [export-and-deployment.md](export-and-deployment.md); LibTorch and C++ extensions ->
  [hep-computing's C++ guidelines](../../hep-computing/references/cpp-balanced-design-guidelines.md)
- Architecture choice -> [architecture-selection.md](architecture-selection.md); "did the change help?" ->
  [ablation-and-design-review.md](ablation-and-design-review.md); budgets, throughput, HP search at scale ->
  [training-at-scale.md](training-at-scale.md); serving and monitoring (generic) ->
  [serving-architecture.md](serving-architecture.md), [monitoring-and-lifecycle.md](monitoring-and-lifecycle.md);
  data and evaluation design -> [data-strategy.md](data-strategy.md), [evaluation-strategy.md](evaluation-strategy.md)
- Worked `examples/` entries -> hep-computing's [example-authoring.md](../../hep-computing/references/example-authoring.md)

Scripts and assets are listed in the skill's [README.md](../README.md); read `--help` first and report the top few
offending items of a diagnostic, not the raw dump.

## Debugging and review checklists

When something breaks, check in this order: shapes -> dtypes -> devices -> batch dimension -> target format against
the loss -> logits vs probabilities -> `train()`/`eval()` -> gradients zeroed -> one `backward()` per step -> the
optimizer holds the right parameters -> input normalization -> label ranges -> NaN or inf in inputs, outputs, loss,
gradients -> `requires_grad` -> checkpoint keys. `torch.autograd.set_detect_anomaly(True)` locates the first NaN
(slow; debugging only). Common NaN fixes: lower LR, clip gradients, normalize inputs, avoid `log(0)`.

In review, watch for: layers created inside `forward`, device or dtype mismatch, a squashing function before the loss
(table above), missing `no_grad` in evaluation, wrong loss averaging or scheduler-step frequency, a forgotten
`scaler.update()`, graph tensors kept in lists (`loss` instead of `loss.item()`), optimizer state missing from
checkpoints, `torch.load` without `map_location`, train/validation leakage.

## Caveats

- Guard `torch.compile` behind `hasattr(torch, "compile")`; deterministic cuDNN trades speed for reproducibility.
- Engineering process (scoping, testing, review): hep-computing
  ([agile-development-guide.md](../../hep-computing/references/agile-development-guide.md)).
- Statistical validity of conclusions drawn from model outputs: `hep-statistics` (and `hep-communication` for the
  write-up); this guide covers whether the model is trained, evaluated, calibrated and robust.
