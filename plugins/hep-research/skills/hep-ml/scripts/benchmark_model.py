#!/usr/bin/env python3
"""Benchmark forward/backward throughput for a small model.

Replace `build_model` and the synthetic input shape to benchmark project models.
"""

from __future__ import annotations
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
    from torch import nn
except ModuleNotFoundError as exc:
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
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

def get_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_model(input_dim: int, num_classes: int) -> nn.Module:
    return nn.Sequential(nn.Linear(input_dim, 512), nn.ReLU(), nn.Linear(512, num_classes))


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        torch.mps.synchronize()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=_count(1), default=256)
    parser.add_argument("--input-dim", type=_count(1), default=1024)
    parser.add_argument("--num-classes", type=_count(1), default=10)
    parser.add_argument("--warmup", type=_count(0), default=10)
    parser.add_argument("--steps", type=_count(1), default=100)
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    if torch is None:
        print(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}", file=sys.stderr)
        sys.exit(3)

    device = get_device(args.device)
    model = build_model(args.input_dim, args.num_classes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=(args.amp and device.type == "cuda"))

    inputs = torch.randn(args.batch_size, args.input_dim, device=device)
    targets = torch.randint(0, args.num_classes, (args.batch_size,), device=device)

    for _ in range(args.warmup):
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=(args.amp and device.type == "cuda")):
            loss = criterion(model(inputs), targets)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

    synchronize(device)
    start = time.perf_counter()
    for _ in range(args.steps):
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=(args.amp and device.type == "cuda")):
            loss = criterion(model(inputs), targets)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
    synchronize(device)

    elapsed = time.perf_counter() - start
    examples = args.steps * args.batch_size
    print(f"device={device} amp={args.amp and device.type == 'cuda'}")
    print(f"steps={args.steps} examples={examples} elapsed={elapsed:.3f}s")
    print(f"throughput={examples / max(elapsed, 1e-9):.1f} examples/s")


if __name__ == "__main__":
    main()
