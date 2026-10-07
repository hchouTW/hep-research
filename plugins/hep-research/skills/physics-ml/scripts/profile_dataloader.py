#!/usr/bin/env python3
"""Template for timing DataLoader throughput. Edit create_dataset() for your project."""

import argparse
import sys
import time

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


def create_dataset(num_examples: int = 10000):
    x = torch.randn(num_examples, 3, 224, 224)
    y = torch.randint(0, 10, (num_examples,))
    return TensorDataset(x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--batches", type=int, default=100)
    args = parser.parse_args()

    if torch is None:
        sys.exit(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}")

    dataset = create_dataset()
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=args.num_workers > 0,
    )

    start = time.perf_counter()
    examples = 0
    for i, (x, y) in enumerate(loader):
        examples += x.size(0)
        if i + 1 >= args.batches:
            break
    elapsed = time.perf_counter() - start
    print(f"Loaded {examples} examples in {elapsed:.3f}s")
    print(f"Throughput: {examples / max(elapsed, 1e-9):.1f} examples/s")


if __name__ == "__main__":
    main()
