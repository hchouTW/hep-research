#!/usr/bin/env python3
"""Record the software environment of a run as a pinned manifest, and check a later environment against it.

`record` writes JSON with an `environment` block, a `tools` list and (with --inputs) an `input_manifest` list in the
shape of a computational-run artifact: Python version and executable, the system (OS family, architecture, libc
version, and the kernel release for information), the versions of the named packages (or of every installed
distribution with --all-packages), the git commit and dirty state of a project folder, the path, SHA-256 and size of
each input file, and where the environment comes from: an LCG view on CVMFS (LCG_VERSION, BINARY_TAG or a /cvmfs
prefix), an Apptainer or Singularity container, a conda environment or a virtual environment. Environment variables
are recorded only by name from a fixed list, never all of them (they can hold credentials). `check` compares the
current environment with a manifest and lists every drift: Python, implementation, executable, OS family,
architecture, libc, origin, packages, variables, changed or missing inputs, and with --project a changed commit or a
dirty checkout. A different kernel release (or the old free-form platform string) is a note, not a drift.
`pairs` (C2) compares, for each era, the software versions declared for data and for simulation (reconstruction,
calibration, conditions, ...): a component whose versions differ is a mismatch (status failed), a component declared
on one side only is undeclared (status incomplete); matching versions are no proof that the two chains agree, only
that the declared versions do.

Usage:
  environment_manifest.py record [--packages numpy,scipy] [--all-packages] [--project DIR] [--inputs FILE ...]
                                 [--out FILE]
  environment_manifest.py check --manifest FILE [--project DIR]
  environment_manifest.py pairs --pairs PAIRS.json [--status LABEL]
    PAIRS.json: {"eras": [{"id": ERA, "data": {COMPONENT: VERSION, ...}, "mc": {COMPONENT: VERSION, ...}}, ...]}
Output: JSON with a "status" key: "recorded" (record; with --out the manifest goes to FILE, whose parent folders are
created, else it is printed under "manifest"), "same" or "drift" (check), "error" (bad input); pairs: "ok",
"failed" (a mismatch), "incomplete" (an undeclared version) or "rejected" (bad input), with "status_label" (--status,
default unvalidated), "inputs", "defaults_used" and per-era verdicts.
Exit codes: 0 written, no drift or every pair matching; 1 drift found or a version mismatch; 2 bad input or
unwritable output; 3 a version undeclared (pairs). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.protected.guard import guard, protected_main  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

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


def system() -> dict:
    """OS family, architecture and libc (compared) and kernel release (information only). The libc of macOS is the
    system library of the OS release, so its version is the macOS version."""
    osname = platform.system()
    if osname == "Darwin":
        libc = f"macOS {platform.mac_ver()[0]}"
    else:
        lib, ver = platform.libc_ver()
        libc = f"{lib} {ver}".strip() or "unknown"
    return {"os": osname, "arch": platform.machine(), "libc": libc, "kernel": platform.release()}


def file_entry(path: Path) -> dict:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return {"path": str(path), "sha256": h.hexdigest(), "size": path.stat().st_size}


def record(names, all_packages: bool = False, project: Path | None = None, inputs=()) -> dict:
    guard("environment_manifest.record", paths=[project, *inputs] if project else list(inputs))
    env = {k: os.environ[k] for k in ENV_VARS if k in os.environ}
    pkgs = packages(names, all_packages)
    manifest = {"environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                                "executable": sys.executable, "platform": platform.platform(), "machine": platform.machine(),
                                "system": system(), "origin": _origin(env), "variables": env, "packages": pkgs},
                "tools": [{"name": "python", "version": platform.python_version()}]
                         + [{"name": n, "version": v} for n, v in pkgs.items() if v is not None]}
    if project is not None:
        manifest["environment"]["project"] = _git(project)
    if inputs:
        manifest["input_manifest"] = [file_entry(Path(p)) for p in inputs]
    return manifest


COMPARED = ("python", "implementation", "executable", "machine", "origin")
SYSTEM_COMPARED = ("os", "arch", "libc")


def drift(saved: dict, current: dict) -> list[str]:
    """Every compared difference. Keys absent from an older manifest are not compared (see notes())."""
    a, b = saved.get("environment", {}), current.get("environment", {})
    out = [f"{k}: {a.get(k)!r} -> {b.get(k)!r}" for k in COMPARED if k in a and a.get(k) != b.get(k)]
    sa, sb = a.get("system") or {}, b.get("system") or {}
    out += [f"system {k}: {sa.get(k)!r} -> {sb.get(k)!r}" for k in SYSTEM_COMPARED if k in sa and sa.get(k) != sb.get(k)]
    pa, pb = a.get("packages", {}), b.get("packages", {})
    out += [f"package {n}: {pa.get(n)!r} -> {pb.get(n)!r}" for n in sorted(set(pa) | set(pb)) if pa.get(n) != pb.get(n)]
    va, vb = a.get("variables", {}), b.get("variables", {})
    out += [f"variable {n}: {va.get(n)!r} -> {vb.get(n)!r}" for n in sorted(set(va) | set(vb)) if va.get(n) != vb.get(n)]
    if "project" in b:
        ga, gb = a.get("project") or {}, b["project"]
        if "error" in gb:
            out.append(f"project: {gb['error']}")
        else:
            if ga.get("commit") != gb.get("commit"):
                out.append(f"project commit: {ga.get('commit')!r} -> {gb.get('commit')!r}")
            if gb.get("dirty"):
                out.append("project dirty: the checkout has uncommitted changes")
    for entry in saved.get("input_manifest") or []:
        p = Path(entry.get("path", ""))
        if not p.is_file():
            out.append(f"input missing: {p}")
        elif file_entry(p)["sha256"] != entry.get("sha256"):
            out.append(f"input changed: {p}")
    return out


def notes(saved: dict, current: dict, project_checked: bool) -> list[str]:
    """Differences that are reported but are not drift."""
    a, b = saved.get("environment", {}), current.get("environment", {})
    out = []
    ka, kb = (a.get("system") or {}).get("kernel"), (b.get("system") or {}).get("kernel")
    if ka is not None and ka != kb:
        out.append(f"kernel release (information only): {ka!r} -> {kb!r}")
    if "system" not in a and a.get("platform") != b.get("platform"):
        out.append(f"platform string (older manifest, information only): {a.get('platform')!r} -> {b.get('platform')!r}")
    if "project" in a and not project_checked:
        out.append("the manifest records a project; pass --project to check its commit and dirty state")
    return out


def version_pairs(doc: dict) -> dict:
    """Per-era comparison of data and simulation versions (C2)."""
    eras = doc.get("eras") if isinstance(doc, dict) else None
    if not isinstance(eras, list) or not eras:
        raise ValueError("pairs file needs a non-empty 'eras' list")
    out, worst = [], "ok"
    for i, era in enumerate(eras):
        if not isinstance(era, dict) or not isinstance(era.get("id"), str) or not era["id"]:
            raise ValueError(f"era {i} needs a non-empty string 'id'")
        sides = {k: era.get(k) for k in ("data", "mc")}
        for k, v in sides.items():
            if not isinstance(v, dict) or not all(isinstance(x, str) for x in v.values()):
                raise ValueError(f"era {era['id']}: '{k}' must map component names to version strings")
        comps = sorted(set(sides["data"]) | set(sides["mc"]))
        mism = [{"component": c, "data": sides["data"][c], "mc": sides["mc"][c]} for c in comps
                if c in sides["data"] and c in sides["mc"] and sides["data"][c] != sides["mc"][c]]
        undeclared = [{"component": c, "missing_in": "mc" if c in sides["data"] else "data"} for c in comps
                      if (c in sides["data"]) != (c in sides["mc"])]
        verdict = "mismatch" if mism else ("undeclared" if undeclared or not comps else "match")
        if not comps:
            undeclared = [{"component": None, "missing_in": "both"}]
        out.append({"id": era["id"], "verdict": verdict, "components": comps, "mismatches": mism,
                    "undeclared": undeclared})
        if verdict == "mismatch":
            worst = "failed"
        elif verdict == "undeclared" and worst == "ok":
            worst = "incomplete"
    return {"status": worst, "eras": out,
            "note": "matching declared versions are not proof that the data and simulation chains agree"}


def _load(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, dict) and isinstance(doc.get("manifest"), dict):  # the printed form of `record` without --out
        doc = doc["manifest"]
    if not isinstance(doc, dict) or not isinstance(doc.get("environment"), dict):
        raise ValueError("not an environment manifest (no 'environment' object)")
    return doc


@protected_main("environment_manifest")
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record", help="write a manifest of the current environment")
    c = sub.add_parser("check", help="compare the current environment with a manifest")
    for p in (r, c):
        p.add_argument("--packages", default=",".join(DEFAULT_PACKAGES), help="comma-separated distribution names")
    r.add_argument("--all-packages", action="store_true", help="every installed distribution instead of --packages")
    r.add_argument("--project", type=Path, help="a git checkout whose commit and dirty state to record")
    r.add_argument("--inputs", nargs="+", type=Path, default=[], metavar="FILE",
                   help="input files whose path, SHA-256 and size go into input_manifest")
    r.add_argument("--out", type=Path, help="write the manifest here (parent folders are created)")
    c.add_argument("--manifest", type=Path, required=True)
    c.add_argument("--project", type=Path, help="the git checkout to compare with the recorded commit (dirty is drift)")
    pr = sub.add_parser("pairs", help="compare data and simulation software versions per era (C2)")
    pr.add_argument("--pairs", type=Path, required=True, help="JSON {eras: [{id, data: {...}, mc: {...}}]}")
    add_status_argument(pr)
    args = ap.parse_args(argv)
    if args.command == "pairs":
        given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
        base = {"status_label": args.status, "inputs": {"pairs": str(args.pairs)},
                "defaults_used": [] if "--status" in given else ["status"]}
        try:
            res = version_pairs(json.loads(args.pairs.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            print(json.dumps({"status": "rejected", **base, "error": f"{type(exc).__name__}: {exc}"}, indent=1))
            return 2
        print(json.dumps({**res, **base}, indent=1))
        return exit_code(res["status"])
    names = [n.strip() for n in args.packages.split(",") if n.strip()]
    try:
        if args.command == "record":
            for f in args.inputs:
                if not f.is_file():
                    raise ValueError(f"input file does not exist: {f}")
            m = record(names, args.all_packages, args.project, args.inputs)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
                print(json.dumps({"status": "recorded", "out": str(args.out), "inputs": len(m.get("input_manifest", []))}))
            else:
                print(json.dumps({"status": "recorded", "manifest": m}, indent=1))
            return 0
        saved = _load(args.manifest)
        saved_pkgs = (saved.get("environment") or {}).get("packages") or {}
        current = record(sorted(saved_pkgs) or names, False, args.project)
        found = drift(saved, current)
        print(json.dumps({"status": "drift" if found else "same", "drift": found,
                          "notes": notes(saved, current, args.project is not None)}, indent=1))
        return 1 if found else 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"}))
        return 2

if __name__ == "__main__":
    sys.exit(main())
