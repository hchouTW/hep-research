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

Use `shuffle=False` for validation and test loaders.

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

## Reproducible split

```python
generator = torch.Generator().manual_seed(42)
train_ds, val_ds = torch.utils.data.random_split(dataset, [n_train, n_val], generator=generator)
```
