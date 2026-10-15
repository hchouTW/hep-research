# Checkpointing Reference

A training checkpoint must be resumable, not only loadable: model, optimizer,
scheduler, `GradScaler`, step and epoch, the data-order state, and every random-number
generator. A resume that restarts the data order or the RNG silently trains on a
different sequence than the run it claims to continue. Write it atomically, so a job
killed mid-write (a batch-system time limit, a preemption) never leaves a truncated file
in place of the last good one. The scale-side requirements (checkpoint on a wall-clock
interval, stragglers) are in [training-at-scale.md](training-at-scale.md).

## Save and resume a training checkpoint

Verified with torch 2.14.1 (CPU), 2026-10-13: training 2 epochs, saving, rebuilding the
model and optimizer with different seeds, loading and training 2 more epochs gives
weights bit-identical to an uninterrupted 4-epoch run.

```python
import os
import random
import tempfile

import numpy as np
import torch


def rng_state() -> dict:
    np_state = np.random.get_state()
    return {
        "python": random.getstate(),
        # NumPy's key array stored as a tensor, so torch.load(weights_only=True) accepts it
        "numpy": (np_state[0], torch.from_numpy(np_state[1].astype(np.int64)), *np_state[2:]),
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def set_rng_state(state: dict) -> None:
    random.setstate(state["python"])
    kind, key, *rest = state["numpy"]
    np.random.set_state((kind, key.numpy().astype(np.uint32), *rest))
    torch.set_rng_state(state["torch"])
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


def save_checkpoint(path, *, model, optimizer, scheduler, scaler, epoch, step, best_metric, config):
    state = {
        "epoch": epoch,                      # last finished epoch
        "step": step,                        # global optimizer step
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "scaler_state_dict": scaler.state_dict() if scaler else None,
        "rng_state": rng_state(),
        "best_metric": best_metric,
        "config": config,                    # plain dict, not a custom class
    }
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")   # same filesystem as the target
    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)           # atomic rename: readers see the old or the new file
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_checkpoint(path, *, model, optimizer, scheduler, scaler, device):
    ckpt = torch.load(path, map_location=device)   # weights_only=True by default
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    if scheduler is not None and ckpt.get("scheduler_state_dict") is not None:
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    if scaler is not None and ckpt.get("scaler_state_dict"):
        scaler.load_state_dict(ckpt["scaler_state_dict"])
    set_rng_state(ckpt["rng_state"])
    return ckpt["epoch"] + 1, ckpt["step"], ckpt["best_metric"]
```

- **Data order.** With a `DistributedSampler`, call `sampler.set_epoch(start_epoch)`
  after resuming: the shuffle is a function of the seed and the epoch, so the order is
  restored. With a plain shuffled `DataLoader`, give it a seeded `generator` and save
  `generator.get_state()` at the start of each epoch, or rebuild it from
  `seed + epoch`. To resume in the middle of an epoch, save the batch index and skip
  that many batches (or use a stateful loader such as `torchdata`'s
  `StatefulDataLoader`); otherwise checkpoint only at epoch boundaries.
- **Workers.** Worker RNGs are reseeded from the loader's generator each epoch; restoring
  the generator state (above) restores them. See [reproducibility.md](reproducibility.md).
- **`GradScaler`.** Without its state a resumed fp16 run restarts the loss scale and
  skips steps until it settles ([mixed-precision.md](mixed-precision.md)).
- **Where to write.** `os.replace` is atomic only within one filesystem, which is why the
  temporary file is created next to the target. On shared filesystems (EOS, CephFS, NFS)
  keep the previous checkpoint until the new one has been loaded back once, and copy
  to remote storage only after the local write has completed.
- **Distributed runs.** Under DDP save on rank 0 only and `dist.barrier()` before other
  ranks read the file; for FSDP2 use distributed checkpoint (DCP), see
  [distributed-training.md](distributed-training.md).

## `weights_only` and the config

Since PyTorch 2.6, `torch.load` defaults to `weights_only=True`, which loads only
tensors and plain containers (dict, list, tuple, str, numbers). A checkpoint whose
`config` is a custom class instance (a dataclass, `argparse.Namespace`) fails with
`UnpicklingError` (verified with torch 2.14.1 (CPU), 2026-10-13, for an `argparse.Namespace`). Save
`config` as a plain dict, e.g. `vars(args)` or `dataclasses.asdict(cfg)`; store NumPy
arrays as tensors (as the RNG helper above does). Pass `weights_only=False` only for
files you produced yourself and trust, since it unpickles arbitrary code.

## Inference-only weights

```python
torch.save(model.state_dict(), "model_weights.pt")
```

Load:

```python
state_dict = torch.load("model_weights.pt", map_location=device)
model.load_state_dict(state_dict)
model.eval()
```

Record the hash of the weights file and the model code version in the `ml-artifact`;
`<plugin root>/skills/hep-ml/scripts/inspect_checkpoint.py` prints the keys,
shapes, epoch and config of a checkpoint.
