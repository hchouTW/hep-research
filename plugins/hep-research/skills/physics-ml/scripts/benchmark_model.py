#!/usr/bin/env python3
"""Benchmark forward/backward throughput for a small model.

Replace `build_model` and the synthetic input shape to benchmark project models.
"""

from __future__ import annotations

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
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--input-dim", type=int, default=1024)
    parser.add_argument("--num-classes", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    if torch is None:
        sys.exit(f"PyTorch is required to run this script but could not be imported: {_TORCH_IMPORT_ERROR}")

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
