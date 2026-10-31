"""The ROOT C++ toolchain workaround the tests share: vdt_include() is the folder holding vdt/vdtMath.h when ROOT's
headers include it but `root-config --cflags` does not name it (Homebrew ROOT 6.40 with a separate vdt;
skills/hep-computing/scripts/check_root_cpp_env.sh reports the same and recommends -I or CPATH), else None.
with_vdt(env) adds that folder to CPATH, the workaround the checker recommends."""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path


@functools.cache
def vdt_include(root_config: str | None = None) -> str | None:
    root_config = root_config or shutil.which("root-config")
    if not root_config:
        return None
    try:
        incdir = subprocess.run([root_config, "--incdir"], capture_output=True, text=True, timeout=60).stdout.strip()
        cflags = subprocess.run([root_config, "--cflags"], capture_output=True, text=True, timeout=60).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    rvec = Path(incdir) / "ROOT" / "RVec.hxx"
    if not incdir or not rvec.is_file() or "vdt/vdtMath.h" not in rvec.read_text(encoding="utf-8", errors="replace"):
        return None
    for d in (Path(incdir).parent, Path("/opt/homebrew/include"), Path("/usr/local/include"), Path("/usr/include")):
        if (d / "vdt" / "vdtMath.h").is_file():
            return None if f"-I{d}" in cflags or d == Path(incdir) else str(d)
    return None


def with_vdt(env: dict, root_config: str | None = None) -> dict:
    """env with vdt_include() prepended to CPATH when it is needed."""
    d = vdt_include(root_config)
    if d:
        env = dict(env, CPATH=os.pathsep.join(p for p in (d, env.get("CPATH")) if p))
    return env
