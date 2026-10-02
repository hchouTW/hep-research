#!/usr/bin/env python3
"""Inspect a PyTorch checkpoint without loading it onto GPU."""

import argparse
import sys
from collections.abc import Mapping

try:
    import torch
except ModuleNotFoundError as exc:
    torch = None  # type: ignore[assignment]
    _TORCH_IMPORT_ERROR = exc
else:
    _TORCH_IMPORT_ERROR = None


def describe_value(value, indent=0):
    prefix = " " * indent
    if torch.is_tensor(value):
        print(f"{prefix}Tensor shape={tuple(value.shape)} dtype={value.dtype} device={value.device}")
    elif isinstance(value, Mapping):
        print(f"{prefix}dict with {len(value)} keys")
        for key, item in list(value.items())[:20]:
            print(f"{prefix}- {key}:", end=" ")
            describe_value(item, indent + 2)
        if len(value) > 20:
            print(f"{prefix}... {len(value) - 20} more keys")
    elif isinstance(value, (list, tuple)):
        print(f"{prefix}{type(value).__name__} length={len(value)}")
    else:
        print(f"{prefix}{type(value).__name__}: {value}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    args = parser.parse_args()

    if torch is None:
        sys.exit(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}")

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    describe_value(ckpt)


if __name__ == "__main__":
    main()
