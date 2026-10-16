# Reproducibility Reference

## Seed helper

Verified with torch 2.14.1 (CPU), 2026-10-13: two runs with the same seed give identical
batches through a two-worker `DataLoader`.

```python
import os
import random

import numpy as np
import torch


def seed_everything(seed: int, deterministic: bool = True) -> None:
    """Seed Python, NumPy and torch (all devices); optionally force deterministic kernels."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)  # also seeds every CUDA device
    if deterministic:
        # cuBLAS reads this at the first CUDA matmul; set it in the job environment to be safe.
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)  # raises on ops with no deterministic implementation
```

- `PYTHONHASHSEED` only takes effect when the interpreter starts; setting it inside
  the running process changes nothing for that process (it only reaches subprocesses).
  Set it in the launcher or batch script (`PYTHONHASHSEED=0 python train.py`) if string
  hashing order matters, for example iteration over a `set` of strings.
- Likewise export `CUBLAS_WORKSPACE_CONFIG=:4096:8` in the job script; the `setdefault`
  above only helps if it runs before CUDA is first used.
- `torch.use_deterministic_algorithms(True)` raises a `RuntimeError` naming the op when
  an operation has no deterministic implementation (some scatter/index-add backward
  passes used by graph networks on CUDA). Either replace the op or pass
  `warn_only=True` and record that the run is not fully deterministic.

Deterministic settings can reduce performance and still may not guarantee exact
reproducibility across hardware, drivers, PyTorch versions, or nondeterministic
operators.

## Data splits

Split by the grouping key, never by row ([ml-analysis.md](ml-analysis.md), "Splits and leakage"); seed the assignment
and persist the manifest with the run. In distributed training call `sampler.set_epoch(epoch)`.

## Worker seeds

Each `DataLoader` worker gets a distinct torch seed derived from the loader's generator,
but Python's `random` and NumPy's global generator are not reseeded per worker. Use a
`worker_init_fn` when dataset code draws random numbers (augmentation, smearing,
sub-sampling of constituents), and pass a seeded `torch.Generator`:

```python
def seed_worker(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % 2**32  # differs per worker
    np.random.seed(worker_seed)
    random.seed(worker_seed)


loader = DataLoader(
    train_ds, batch_size=256, shuffle=True, num_workers=4,
    worker_init_fn=seed_worker, generator=torch.Generator().manual_seed(seed),
)
```

## Experiment records

Save enough information to reproduce or compare runs:

- Config and command-line arguments.
- Git commit or code version when available.
- PyTorch, CUDA, cuDNN, Python, and platform versions.
- For GPU runs: the torch build's CUDA variant (for example `2.14.1+cu126`), GPU model and compute capability,
  driver version, precision (fp32, or AMP with its dtype) and the determinism settings actually used
  (`cudnn.deterministic`, `torch.use_deterministic_algorithms`). `<plugin root>/skills/hep-ml/scripts/check_pytorch_env.py` prints most of
  these.
- Dataset version and split identifiers.
- Checkpoint with model, optimizer, scheduler, epoch, best metric, and config.

Since contracts 2.5.0 the `ml-artifact` has an `environment` field (framework version, device, precision, seeds;
`write_ml_artifact.py` fills it from the training run summary, and a missing seed is a warning). For the full
software stack and the GPU, also record the run as a `computational-run` artifact and list it in the `ml-artifact`'s
`inputs`, so the model hash leads to the environment it was trained in.

## Reproducibility levels

Say which level was shown: rerunning a checkpoint; reproducing evaluation (checkpoint, eval set, preprocessing, metric
code); reproducing training (everything in Experiment records); across seeds (with the spread,
[ablation-and-design-review.md](ablation-and-design-review.md)); across environments (define "reproduces": the same
conclusion, not bit-identical numbers); and with an independent implementation, the strongest, where the shared parts
(inputs, calibration, model assumptions, libraries, algorithms) are stated, because agreement is evidence, not proof.
Every number of a result should trace to code revision, configuration, dataset, split and preprocessing versions,
seed, environment, checkpoint and evaluation version.

## Hyperparameter sweeps

Seed every trial from a base seed and its index, record every trial's config and result (one JSON line each), record
why a trial was stopped early, and rerun the winner with another seed before reporting it. A single validation split
reused across many configurations is overfit by the selection: use grouped (or nested) cross-validation
([ml-analysis-training-and-data.md](ml-analysis-training-and-data.md), "Hyperparameter search").
