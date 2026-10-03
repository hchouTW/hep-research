#!/usr/bin/env python3
"""Check the local PyTorch environment."""

import argparse
import platform
import sys

argparse.ArgumentParser(
    description="Check the local PyTorch environment: versions, CUDA/MPS availability and a CPU autograd smoke test.",
    epilog="Exit codes: 0 OK, 1 torch cannot be imported, 2 smoke test failed.",
).parse_args()

try:
    import torch
except Exception as exc:
    print("ERROR: Could not import torch")
    print(exc)
    sys.exit(1)

print("Python:", sys.version.replace("\n", " "))
print("Platform:", platform.platform())
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA version:", torch.version.cuda)
    print("cuDNN version:", torch.backends.cudnn.version())
    print("GPU count:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}:", torch.cuda.get_device_name(i))

mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
print("MPS available:", mps_available)

try:
    x = torch.randn(4, 3)
    layer = torch.nn.Linear(3, 2)
    y = layer(x)
    loss = y.sum()
    loss.backward()
    print("CPU autograd smoke test: OK")
except Exception as exc:
    print("ERROR: CPU autograd smoke test failed")
    print(exc)
    sys.exit(2)
