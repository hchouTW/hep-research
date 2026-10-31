#!/usr/bin/env python3
"""Inspect a PyTorch checkpoint without loading it onto GPU.

Prints the checkpoint's structure as text. A refused run prints one JSON object with a "status" key on stdout.
Exit codes: 0 listed; 2 missing or unreadable checkpoint, or refused by weights_only loading; 3 PyTorch not available.
"""
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
import json
import pickle
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("--unsafe-full-unpickle", action="store_true",
                        help="load with weights_only=False (full pickle, can run arbitrary code); only for files you trust")
    args = parser.parse_args()

    if torch is None:
        print(json.dumps({"status": "missing-dependency",
                          "error": f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}"}))
        sys.exit(3)

    try:
        ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=not args.unsafe_full_unpickle)
    except pickle.UnpicklingError as exc:
        print(json.dumps({"status": "rejected", "error": f"Refused to load {args.checkpoint} with weights_only=True: {exc}. "
                          "Re-run with --unsafe-full-unpickle only if you trust this file."}))
        sys.exit(2)
    except OSError as exc:  # a missing or unreadable input
        print(json.dumps({"status": "rejected", "error": f"cannot read {args.checkpoint}: {exc}"}))
        sys.exit(2)
    describe_value(ckpt)


if __name__ == "__main__":
    main()
