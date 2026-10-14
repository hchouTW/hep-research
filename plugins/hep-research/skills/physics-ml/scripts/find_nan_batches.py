#!/usr/bin/env python3
"""Find non-finite tensors in a DataLoader-like dataset.

Edit `create_dataset` for the target project, then run this script to identify
the first batches containing NaNs or infinities. Exits 1 if any non-finite batch is
found (0 if none), so it can gate a pipeline.
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
    x = torch.randn(1024, 8)
    y = torch.randint(0, 2, (1024,))
    return TensorDataset(x, y)


def iter_tensors(value):
    if torch.is_tensor(value):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from iter_tensors(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            yield from iter_tensors(item)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=_count(1), default=64)
    parser.add_argument("--num-workers", type=_count(0), default=0)
    parser.add_argument("--max-batches", type=_count(1), default=100)
    args = parser.parse_args()

    if torch is None:
        print(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}", file=sys.stderr)
        sys.exit(3)

    loader = DataLoader(create_dataset(), batch_size=args.batch_size, num_workers=args.num_workers)
    bad_batches = 0
    for batch_idx, batch in enumerate(loader):
        if batch_idx >= args.max_batches:
            break
        for tensor_idx, tensor in enumerate(iter_tensors(batch)):
            if tensor.is_floating_point() or tensor.is_complex():
                if not torch.isfinite(tensor).all():
                    bad_batches += 1
                    print(f"batch={batch_idx} tensor={tensor_idx} shape={tuple(tensor.shape)} has non-finite values")
                    break
    if bad_batches == 0:
        print("No non-finite tensors found in checked batches.")
    else:
        sys.exit(f"{bad_batches} batch(es) with non-finite values.")


if __name__ == "__main__":
    main()
