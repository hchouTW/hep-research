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

Never split rows at random: candidates of one event, events of one run, period, simulation seed or parameter point are
correlated. The rule, the tools (`make_grouped_splits.py`, `check_split_integrity.py`) and k-fold by event number are
in [ml-analysis.md](ml-analysis.md), "Splits and leakage" (the one home of this rule). In code, select the manifest's
indices with `torch.utils.data.Subset`; `sklearn.model_selection.GroupShuffleSplit` or `GroupKFold` do the grouping
when scikit-learn is available. Fractions of groups are not fractions of events: check the event and class counts per
split.
