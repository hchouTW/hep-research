#!/usr/bin/env python3
"""Template for timing DataLoader throughput. Edit create_dataset() for your project."""
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

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



def _count(minimum):
    """argparse type: an integer >= minimum (a bad count is a usage error, exit 2, not a traceback)."""
    def parse(text):
        value = int(text)
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be an integer >= {minimum}, got {text}")
        return value
    return parse

def create_dataset(num_examples: int = 10000):
    x = torch.randn(num_examples, 3, 224, 224)
    y = torch.randint(0, 10, (num_examples,))
    return TensorDataset(x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=_count(1), default=64)
    parser.add_argument("--num-workers", type=_count(0), default=4)
    parser.add_argument("--batches", type=_count(1), default=100)
    args = parser.parse_args()

    if torch is None:
        print(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}", file=sys.stderr)
        sys.exit(3)

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
