#!/usr/bin/env python3
"""Check the local PyTorch environment."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import warnings


def cuda_arch_supports(capability: tuple[int, int], arch_list: list[str]) -> bool:
    """Whether a build compiled for ``arch_list`` can run on a GPU of compute capability ``capability``.

    NVIDIA's binary compatibility rules: a cubin for ``sm_XY`` runs on capability X.Z with Z >= Y (same major);
    an arch-specific cubin (``sm_90a``) only on exactly X.Y; PTX (``compute_XY``) is compiled at load time for any
    capability >= X.Y. ``arch_list`` is ``torch.cuda.get_arch_list()``, or ``torch._C._cuda_getArchFlags().split()``
    where CUDA is unavailable.
    """
    major, minor = capability
    for arch in arch_list:
        kind, _, code = arch.partition("_")
        if not code[:2].isdigit():
            continue
        suffix = code.lstrip("0123456789")
        number = int(code[: len(code) - len(suffix)])
        code_major, code_minor = divmod(number, 10)
        if kind == "sm" and suffix == "a":
            if (major, minor) == (code_major, code_minor):
                return True
        elif kind == "sm":
            if major == code_major and minor >= code_minor:
                return True
        elif kind == "compute":
            if (major, minor) >= (code_major, code_minor):
                return True
    return False


def visible_nvidia_gpus() -> int:
    """GPUs this process can see according to ``nvidia-smi -L`` (0 without the tool, on error, or when hidden).

    Device files alone are not enough: a CPU job on a GPU node has them, while the scheduler's cgroup hides the GPUs.
    """
    if os.environ.get("CUDA_VISIBLE_DEVICES") == "" or not shutil.which("nvidia-smi"):
        return 0
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    return sum(line.startswith("GPU ") for line in out.splitlines())


def main() -> int:
    argparse.ArgumentParser(
        description="Check the local PyTorch environment: versions, CUDA/MPS availability, whether the installed "
        "build supports each visible GPU's compute capability, and a CPU autograd smoke test.",
        epilog="Exit codes: 0 OK, 1 torch cannot be imported, 2 smoke test failed, "
        "3 a visible GPU is not supported by this torch build, or the node has NVIDIA GPUs but this CUDA build "
        "cannot use them (for example a driver too old for its CUDA version).",
    ).parse_args()

    try:
        import torch
    except Exception as exc:
        print("ERROR: Could not import torch")
        print(exc)
        return 1

    print("Python:", sys.version.replace("\n", " "))
    print("Platform:", platform.platform())
    print("PyTorch:", torch.__version__)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cuda_available = torch.cuda.is_available()
    print("CUDA available:", cuda_available)
    unsupported = []
    # the node has NVIDIA GPUs, but this CUDA build cannot reach them: say why instead of passing silently
    gpu_unreachable = not cuda_available and bool(torch.version.cuda) and visible_nvidia_gpus() > 0
    if gpu_unreachable:
        for warning in caught:
            print("CUDA initialisation warning:", " ".join(str(warning.message).split()))
    if cuda_available:
        arch_list = torch.cuda.get_arch_list()
        print("CUDA version:", torch.version.cuda)
        print("cuDNN version:", torch.backends.cudnn.version())
        print("Compiled for:", " ".join(arch_list))
        print("GPU count:", torch.cuda.device_count())
        for i in range(torch.cuda.device_count()):
            capability = torch.cuda.get_device_capability(i)
            ok = cuda_arch_supports(capability, arch_list)
            print(f"GPU {i}:", torch.cuda.get_device_name(i),
                  f"(compute capability {capability[0]}.{capability[1]}, {'supported' if ok else 'NOT supported'} by this build)")
            if not ok:
                unsupported.append(i)
    elif torch.version.cuda and hasattr(torch._C, "_cuda_getArchFlags"):
        # get_arch_list() is empty without CUDA (a login node); the compiled list is still readable
        print("CUDA build:", torch.version.cuda, "compiled for:", torch._C._cuda_getArchFlags())

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
        return 2

    if gpu_unreachable:
        print(f"ERROR: nvidia-smi sees GPUs but the CUDA {torch.version.cuda} build of torch cannot use them; "
              "check the driver version against the build's CUDA version, or install a build for this node")
        return 3
    if unsupported:
        print(f"ERROR: GPU(s) {unsupported} not supported by this torch build (compiled for "
              f"{' '.join(torch.cuda.get_arch_list())}); install a build compiled for their compute capability")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
