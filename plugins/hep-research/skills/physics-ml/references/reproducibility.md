# Reproducibility Reference

## Seed helper

```python
import os
import random

import numpy as np
import torch


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
```

Deterministic settings can reduce performance and still may not guarantee exact
reproducibility across hardware, drivers, PyTorch versions, or nondeterministic
operators.

## Data splits

Use a seeded generator and persist the split when comparisons must be exact.

```python
generator = torch.Generator().manual_seed(seed)
train_ds, val_ds = torch.utils.data.random_split(dataset, [n_train, n_val], generator=generator)
```

For distributed training, call `sampler.set_epoch(epoch)` so shuffling changes
between epochs but remains coordinated across ranks.

## Worker seeds

Use `worker_init_fn` when dataset code uses Python, NumPy, or other random
generators in workers.

```python
def seed_worker(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)
```

Pass a seeded `torch.Generator` to the `DataLoader` as well.

## Experiment records

Save enough information to reproduce or compare runs:

- Config and command-line arguments.
- Git commit or code version when available.
- PyTorch, CUDA, cuDNN, Python, and platform versions.
- Dataset version and split identifiers.
- Checkpoint with model, optimizer, scheduler, epoch, best metric, and config.

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
