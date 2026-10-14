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



def _count(minimum):
    """argparse type: an integer >= minimum (a bad count is a usage error, exit 2, not a traceback)."""
    def parse(text):
        value = int(text)
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be an integer >= {minimum}, got {text}")
        return value
    return parse

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
    parser.add_argument("--batch-size", type=_count(1), default=8)
    parser.add_argument("--num-workers", type=_count(0), default=0)
    args = parser.parse_args()

    if torch is None:
        print(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}", file=sys.stderr)
        sys.exit(3)

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
