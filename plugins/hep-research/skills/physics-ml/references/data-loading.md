# Data Loading Reference

## Dataset contract

A `Dataset` must implement:

```python
def __len__(self):
    ...

def __getitem__(self, idx):
    ...
```

## DataLoader defaults

```python
DataLoader(
    dataset,
    batch_size=64,
    shuffle=True,
    num_workers=4,
    pin_memory=torch.cuda.is_available(),
)
```

Use `shuffle=False` for validation and test loaders. For reproducible shuffling and
worker-side randomness, pass a seeded `generator` and a `worker_init_fn`
([reproducibility.md](reproducibility.md)).

## Variable-length sequences

Use a `collate_fn` with padding.

```python
from torch.nn.utils.rnn import pad_sequence


def collate_batch(batch):
    xs, ys = zip(*batch)
    lengths = torch.tensor([len(x) for x in xs])
    xs = pad_sequence(xs, batch_first=True)
    ys = torch.tensor(ys)
    return xs, lengths, ys
```

For particle sets, return a boolean mask with the padded tensor and keep padded entries out
of pooling, attention and the loss ([particle-and-jet-architectures.md](particle-and-jet-architectures.md)).
A padded axis that changes size every batch also forces `torch.compile` to recompile; see
[performance-memory.md](performance-memory.md).

## Grouped split

Do not split rows at random. Candidates or jets from one event, events from one run or
detector period, and events from one simulation seed or parameter point are correlated;
a row-level `random_split` puts them on both sides and the test metric measures
memorization. Assign whole groups to one split each (the invariant in
[ml-analysis.md](ml-analysis.md), "Splits and leakage"):

```python
import numpy as np
from torch.utils.data import Subset


def grouped_split(groups, fractions=(0.7, 0.15, 0.15), seed=42):
    """Index arrays for train/val/test; every group (run, period, seed) lands in exactly one split."""
    groups = np.asarray(groups)
    unique = np.unique(groups)
    np.random.default_rng(seed).shuffle(unique)
    cuts = np.round(np.cumsum(fractions[:-1]) * len(unique)).astype(int)
    return [np.flatnonzero(np.isin(groups, part)) for part in np.split(unique, cuts)]


train_idx, val_idx, test_idx = grouped_split(run_numbers)   # one grouping key per event
train_ds, val_ds, test_ds = (Subset(dataset, idx.tolist()) for idx in (train_idx, val_idx, test_idx))
```

Verified with torch 2.14.1 (CPU), 2026-10-13, on 20 synthetic runs (no run in two splits).

- The fractions are fractions of groups, not of events: with few or unequal groups, check
  the event counts (and the signal and background counts) in each split.
- `sklearn.model_selection.GroupShuffleSplit` or `GroupKFold` do the same when
  scikit-learn is available; k-fold by event number is in [ml-analysis.md](ml-analysis.md).
- In `<plugin root>/skills/physics-ml/scripts/`, `make_grouped_splits.py` writes a split
  manifest from a grouping key, and `check_split_integrity.py` checks a manifest for
  overlap, duplicates, group leakage and time order (read `--help` first). Save the manifest with the run so the split can be reproduced and audited.
