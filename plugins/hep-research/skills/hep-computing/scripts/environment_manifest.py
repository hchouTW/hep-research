#!/usr/bin/env python3
"""Record the software environment of a run as a pinned manifest, and check a later environment against it.

`record` writes JSON with an `environment` block and a `tools` list in the shape of a computational-run artifact:
Python version and executable, platform, the versions of the named packages (or of every installed distribution with
--all-packages), the git commit and dirty state of a project folder, and where the environment comes from: an LCG
view on CVMFS (LCG_VERSION, BINARY_TAG or a /cvmfs prefix), an Apptainer or Singularity container, a conda
environment or a virtual environment. Environment variables are recorded only by name from a fixed list, never all of
them (they can hold credentials). `check` compares the current environment with a manifest and lists every drift.

Usage:
  environment_manifest.py record [--packages numpy,scipy] [--all-packages] [--project DIR] [--out FILE]
  environment_manifest.py check --manifest FILE [--packages numpy,scipy]
Exit codes: 0 written or no drift, 1 drift found, 2 bad input. Standard library only.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ENV_VARS = ("LCG_VERSION", "BINARY_TAG", "CMTCONFIG", "ROOTSYS", "APPTAINER_CONTAINER", "SINGULARITY_CONTAINER",
            "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "VIRTUAL_ENV", "HEP_CONTAINER_IMAGE")
DEFAULT_PACKAGES = ("numpy", "scipy", "matplotlib", "sympy", "uproot", "awkward", "pyhf", "torch", "coffea")


def _origin(env: dict) -> str:
    if env.get("APPTAINER_CONTAINER") or env.get("SINGULARITY_CONTAINER"):
        return "container"
    if env.get("LCG_VERSION") or sys.prefix.startswith("/cvmfs/"):
        return "lcg-view"
    if env.get("CONDA_PREFIX") and sys.prefix == env["CONDA_PREFIX"]:
        return "conda"
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "venv"
    return "system"


def _git(project: Path) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, capture_output=True, text=True, timeout=60)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=project, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"path": str(project), "error": str(exc)}
    if commit.returncode:
        return {"path": str(project), "error": "not a git repository"}
    return {"path": str(project), "commit": commit.stdout.strip(), "dirty": bool(dirty.stdout.strip())}


def packages(names, all_packages: bool) -> dict:
    if all_packages:
        return dict(sorted({d.metadata["Name"].lower(): d.version for d in md.distributions() if d.metadata["Name"]}.items()))
    out = {}
    for name in names:
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = None  # recorded as absent, so a later install is a drift
    return out


def record(names, all_packages: bool = False, project: Path | None = None) -> dict:
    env = {k: os.environ[k] for k in ENV_VARS if k in os.environ}
    pkgs = packages(names, all_packages)
    manifest = {"environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                                "executable": sys.executable, "platform": platform.platform(), "machine": platform.machine(),
                                "origin": _origin(env), "variables": env, "packages": pkgs},
                "tools": [{"name": "python", "version": platform.python_version()}]
                         + [{"name": n, "version": v} for n, v in pkgs.items() if v is not None]}
    if project is not None:
        manifest["environment"]["project"] = _git(project)
    return manifest


def drift(saved: dict, current: dict) -> list[str]:
    a, b = saved.get("environment", {}), current.get("environment", {})
    out = [f"{k}: {a.get(k)!r} -> {b.get(k)!r}" for k in ("python", "implementation", "platform", "origin") if a.get(k) != b.get(k)]
    pa, pb = a.get("packages", {}), b.get("packages", {})
    out += [f"package {n}: {pa.get(n)!r} -> {pb.get(n)!r}" for n in sorted(set(pa) | set(pb)) if pa.get(n) != pb.get(n)]
    va, vb = a.get("variables", {}), b.get("variables", {})
    out += [f"variable {n}: {va.get(n)!r} -> {vb.get(n)!r}" for n in sorted(set(va) | set(vb)) if va.get(n) != vb.get(n)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record", help="write a manifest of the current environment")
    c = sub.add_parser("check", help="compare the current environment with a manifest")
    for p in (r, c):
        p.add_argument("--packages", default=",".join(DEFAULT_PACKAGES), help="comma-separated distribution names")
    r.add_argument("--all-packages", action="store_true", help="every installed distribution instead of --packages")
    r.add_argument("--project", type=Path, help="a git checkout whose commit and dirty state to record")
    r.add_argument("--out", type=Path)
    c.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args(argv)
    names = [n.strip() for n in args.packages.split(",") if n.strip()]
    if args.command == "record":
        m = record(names, args.all_packages, args.project)
        text = json.dumps(m, indent=1)
        if args.out:
            args.out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    try:
        saved = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"environment_manifest.py: error: {exc}", file=sys.stderr)
        return 2
    saved_pkgs = (saved.get("environment") or {}).get("packages") or {}
    current = record(sorted(saved_pkgs) or names, False)
    found = drift(saved, current)
    print(json.dumps({"status": "drift" if found else "same", "drift": found}, indent=1))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
