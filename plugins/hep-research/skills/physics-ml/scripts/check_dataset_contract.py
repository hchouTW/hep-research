#!/usr/bin/env python3
"""Smoke-test Dataset outputs for shape, dtype, and collation.

Edit `create_dataset` to return the project dataset, then run this script before
debugging the training loop. Exits 1 with a message if the samples cannot be collated
into a batch (for example ragged shapes without a `collate_fn`).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence

try:
    import torch
    from torch.utils.data import DataLoader, TensorDataset
except ModuleNotFoundError as exc:
    torch = None  # type: ignore[assignment]
    DataLoader = None  # type: ignore[assignment]
    TensorDataset = None  # type: ignore[assignment]
    _TORCH_IMPORT_ERROR = exc
else:
    _TORCH_IMPORT_ERROR = None


def create_dataset():
    x = torch.randn(128, 3, 32, 32)
    y = torch.randint(0, 10, (128,))
    return TensorDataset(x, y)


def describe(value, prefix: str = "batch") -> None:
    if torch.is_tensor(value):
        print(f"{prefix}: tensor shape={tuple(value.shape)} dtype={value.dtype} device={value.device}")
    elif isinstance(value, Mapping):
        print(f"{prefix}: mapping keys={list(value.keys())}")
        for key, item in value.items():
            describe(item, f"{prefix}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        print(f"{prefix}: {type(value).__name__} len={len(value)}")
        for idx, item in enumerate(value):
            describe(item, f"{prefix}[{idx}]")
    else:
        print(f"{prefix}: {type(value).__name__} value={value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=0)
    args = parser.parse_args()

    if torch is None:
        sys.exit(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}")

    dataset = create_dataset()
    print(f"dataset={type(dataset).__name__} length={len(dataset)}")
    describe(dataset[0], "sample")

    loader = DataLoader(dataset, batch_size=args.batch_size, num_workers=args.num_workers)
    try:
        batch = next(iter(loader))
    except Exception as exc:  # collate errors surface as RuntimeError, TypeError, ...
        sys.exit(
            f"Could not collate a batch of {args.batch_size} samples: {type(exc).__name__}: {exc}\n"
            "Samples may differ in shape or type; add a collate_fn (padding or a list) or fix the dataset."
        )
    describe(batch)


if __name__ == "__main__":
    main()
