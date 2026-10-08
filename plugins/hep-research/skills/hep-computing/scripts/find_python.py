#!/usr/bin/env python3
"""Find a Python interpreter that has the packages a task needs (default: SymPy), before symbolic work.

Candidates, in this order; the first that qualifies wins:
  1. --python PATH
  2. the HEP_RESEARCH_PYTHON environment variable
  3. the interpreter running this script
  4. python3 on PATH
Nothing else is searched: conda environments and virtual environments are used only when named through 1 or 2.
Each candidate is probed in a subprocess (from an empty temporary directory) that imports the required packages and
reports its version; it qualifies if it is Python >= --min-python and every package imports. Point the plugin at an
interpreter with, for example, `export HEP_RESEARCH_PYTHON=~/miniconda3/envs/sympy-py313/bin/python`.

Usage: python3 find_python.py [--require PKG ...] [--python PATH] [--min-python 3.11] [--timeout SECONDS]
Exit 0 found, 1 no candidate qualifies (status failed), 2 bad usage.
Output: JSON with status, python (path), python_version, modules (package -> version), source, and every candidate
tried with its reason. Record python, python_version and the module versions with the result that uses them.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENV_VAR = "HEP_RESEARCH_PYTHON"
MIN_PYTHON = "3.11"  # pyproject.toml requires-python
# runs inside the candidate, possibly an old Python: keep it to syntax every Python 3 parses
PROBE = """
import json, sys
from importlib import import_module
try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    version = None
mods, missing = {}, []
for name in sys.argv[1:]:
    try:
        mod = import_module(name)
    except Exception:
        missing.append(name)
        continue
    try:
        mods[name] = version(name) if version else None
    except PackageNotFoundError:
        mods[name] = None
    if mods[name] is None:
        mods[name] = getattr(mod, "__version__", None)
print(json.dumps({"version": list(sys.version_info[:3]), "executable": sys.executable, "modules": mods,
                  "missing": missing}))
"""


def candidates(explicit: str | None) -> list[tuple[str, str]]:
    found = []
    if explicit:
        found.append(("--python", explicit))
    if os.environ.get(ENV_VAR):
        found.append((ENV_VAR, os.environ[ENV_VAR]))
    found.append(("caller", sys.executable))
    on_path = shutil.which("python3")
    if on_path:
        found.append(("PATH", on_path))
    return found


def probe(path: str, required: list[str], min_python: tuple[int, ...], timeout: float) -> dict:
    """Return {"accepted": bool, "reason": str, ...} for one interpreter."""
    exe = Path(path).expanduser()
    if not (exe.is_file() and os.access(exe, os.X_OK)):
        return {"accepted": False, "reason": "not an executable file"}
    with tempfile.TemporaryDirectory() as empty:  # nothing in the cwd can shadow a package
        try:
            proc = subprocess.run([str(exe), "-c", PROBE, *required], capture_output=True, text=True, cwd=empty,
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"accepted": False, "reason": f"probe timed out after {timeout:g} s"}
        except OSError as exc:
            return {"accepted": False, "reason": f"probe failed: {exc}"}
    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        got = tuple(int(x) for x in info["version"])
    except (IndexError, KeyError, TypeError, ValueError):
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or [f"exit {proc.returncode}"]
        return {"accepted": False, "reason": f"probe failed: {tail[0][:200]}"}
    out = {"python_version": ".".join(map(str, got)), "executable": info.get("executable")}
    if got < min_python:
        want = ".".join(map(str, min_python))
        return {**out, "accepted": False, "reason": f"Python {out['python_version']} < {want}"}
    if info.get("missing"):
        return {**out, "accepted": False, "reason": ", ".join(f"{m} missing" for m in info["missing"])}
    return {**out, "accepted": True, "reason": "ok", "modules": info.get("modules", {})}


def find(required: list[str], explicit: str | None = None, min_python: str = MIN_PYTHON, timeout: float = 60.0) -> dict:
    minimum = tuple(int(x) for x in min_python.split("."))
    tried, seen = [], {}
    for source, path in candidates(explicit):
        key = os.path.realpath(os.path.expanduser(path))
        if key in seen:
            tried.append({"source": source, "path": path, "accepted": False, "reason": f"duplicate of {seen[key]}"})
            continue
        seen[key] = source
        result = probe(path, required, minimum, timeout)
        modules = result.pop("modules", None)
        tried.append({"source": source, "path": path, **result})
        if result["accepted"]:
            return {"status": "found", "required": required, "min_python": min_python, "python": path,
                    "python_version": result["python_version"], "modules": modules, "source": source,
                    "candidates": tried}
    return {"status": "failed", "required": required, "min_python": min_python, "python": None,
            "python_version": None, "modules": None, "source": None, "candidates": tried,
            "hint": f"no candidate has Python >= {min_python} with {', '.join(required)}; set {ENV_VAR} (or pass "
                    "--python) to an interpreter that has them, or install requirements-core.txt into a project "
                    "virtual environment (installing needs the user's approval)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 epilog=f"Candidates: --python, ${ENV_VAR}, this interpreter, python3 on PATH.")
    ap.add_argument("--require", action="append", metavar="PKG",
                    help="importable package the interpreter must have (repeatable; default: sympy)")
    ap.add_argument("--python", help="interpreter to try first")
    ap.add_argument("--min-python", default=MIN_PYTHON, help=f"minimum Python version (default {MIN_PYTHON})")
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds allowed per probe (default 60)")
    args = ap.parse_args(argv)
    try:
        tuple(int(x) for x in args.min_python.split("."))
    except ValueError:
        ap.error(f"--min-python must look like 3.11, got {args.min_python!r}")
    out = find(args.require or ["sympy"], args.python, args.min_python, args.timeout)
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "found" else 1


if __name__ == "__main__":
    sys.exit(main())
