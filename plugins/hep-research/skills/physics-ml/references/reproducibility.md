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

Split by the grouping key (run, detector period, event, simulation seed, parameter
point), never by row: the recipe is in [data-loading.md](data-loading.md) ("Grouped
split"), and `make_grouped_splits.py` / `check_split_integrity.py` in
`<plugin root>/skills/physics-ml/scripts/` write and check a split manifest. Seed the assignment, and persist the manifest (the list of groups in each
split) with the run when comparisons must be exact.

For distributed training, call `sampler.set_epoch(epoch)` so shuffling changes
between epochs but remains coordinated across ranks.

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
  (`cudnn.deterministic`, `torch.use_deterministic_algorithms`). `<plugin root>/skills/physics-ml/scripts/check_pytorch_env.py` prints most of
  these.
- Dataset version and split identifiers.
- Checkpoint with model, optimizer, scheduler, epoch, best metric, and config.

In this plugin the `ml-artifact` has no environment fields: record the training run as a `computational-run`
artifact (its `environment`, `tools`, `seeds` and `resources`, with the GPU) and list that artifact in the
`ml-artifact`'s `inputs`, so the model hash leads to the environment it was trained in.

## Reproducibility levels

"Reproducible" is not one property - distinguish what is actually being claimed:

- **Rerunning the same checkpoint** - only requires the checkpoint and inference code.
- **Reproducing evaluation** - requires the checkpoint plus the exact eval set,
  preprocessing, and metric code.
- **Reproducing training** - requires everything in Experiment records above: code
  revision, config, dataset and split version, preprocessing version, seed,
  environment.
- **Reproducing across seeds** - requires training reproducibility plus running
  multiple seeds and reporting the spread - see
  [ablation-and-design-review.md](ablation-and-design-review.md).
- **Reproducing across environments** - requires training reproducibility on
  different hardware/library versions; exact numerical reproduction is not
  guaranteed even then (see the determinism caveat above), so define what
  "reproduces" means (same conclusion, not bit-identical numbers) before claiming it.
- **Reproducing conclusions with an independent implementation** - the strongest
  level; requires someone else's separately-written code to reach the same
  qualitative conclusion.

Do not claim a stronger level than was actually demonstrated - "we reproduced the
result" after only reloading a checkpoint and reproducing evaluation is a narrower
claim than it sounds.

## Experiment provenance

For results that matter, every number should be traceable to:

```text
Result
├── code revision
├── configuration
├── dataset version
├── split version
├── preprocessing version
├── random seed
├── environment (library/hardware versions)
├── checkpoint
└── evaluation version (eval set + metric code version)
```

This is the same information as Experiment records above, organized as an explicit
traceability chain rather than a save-this-list - use whatever recording mechanism
already exists in the project (a config file, a flat log, a tracked spreadsheet); this
does not require adopting a specific experiment-tracking vendor. See
[training-at-scale.md](training-at-scale.md)'s "Experiment tracking" section for the
scale-specific version of the same requirement.

## Hyperparameter sweeps

A single held-out validation split reused across many configurations is itself a
form of overfitting - the configuration that wins is partly selected for beating
that specific split's noise. Keep sweep and reproducibility concerns tied together
rather than treating tuning as a separate, unrecorded step:

- Seed every run in a sweep with a value derived from a fixed base seed and the
  run index (e.g. `seed_everything(base_seed + run_index)`), not the same seed for
  every configuration and not an unseeded run - otherwise you cannot tell whether a
  result difference came from the hyperparameter or from run-to-run noise.
- For a small number of hyperparameters, prefer **random search** over grid search
  at equal budget - it explores each dimension more effectively when only a few
  hyperparameters actually matter, which is the common case.
- Record every trial's full config and result (not just the best one) in a flat,
  greppable format (one JSON object per line is enough; a dedicated experiment
  tracker is not required to get this benefit) - this is what makes "why did we
  pick these hyperparameters" answerable later, and what the Experiment records
  section above assumes exists.
- Use **early stopping within a trial** (stop a clearly-losing configuration early
  based on a validation-metric trend) to spend more of the sweep budget on
  promising regions, but record *why* a trial stopped early alongside its partial
  result - a trial killed early for looking bad is a different kind of data point
  than one that ran to completion and looked bad.
- Re-run the winning configuration with at least one additional seed before
  reporting a final number - a hyperparameter that wins by a margin comparable to
  seed-to-seed variance has not actually been shown to be better.
