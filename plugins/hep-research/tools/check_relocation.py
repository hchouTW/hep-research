#!/usr/bin/env python3
"""Relocation check (task M5.1, AC24): copy the plugin to a temporary path with spaces, outside the repository and
with no symlinks, then run every check from there with a different working directory.

Usage: python3 tools/check_relocation.py [--out DIR] [--keep]
Copies only what a package would contain: in a git checkout the files git lists (tracked, plus untracked files that
are not ignored, so a local venv or cache is never copied), else the tree; in both cases no __pycache__, *.pyc,
.pytest_cache or output-* directories. Fails if the copy contains a symlink or if any file in it names the source
checkout's absolute path. Runs tools/run_all_checks.py inside the copy with cwd set to an unrelated temporary
directory and records the summary.
Exit 0 when the relocated run passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("__pycache__", "*.pyc", ".pytest_cache", "output-*")
IGNORE = shutil.ignore_patterns(*PATTERNS)


def copy_package(dest: Path) -> None:
    """Copy the git-listed files (the scanner's view in a checkout); fall back to the whole tree outside git."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        listed = [f for f in out.split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        listed = []
    if not listed:
        shutil.copytree(ROOT, dest, symlinks=False, ignore=IGNORE)
        return
    for rel in listed:
        src = ROOT / rel
        if not src.is_file() or any(fnmatch.fnmatch(part, pat) for part in Path(rel).parts for pat in PATTERNS):
            continue
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / rel)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--keep", action="store_true", help="keep the relocated copy for inspection")
    args = ap.parse_args(argv)
    base = Path(tempfile.mkdtemp(prefix="hep research relocated "))
    dest = base / "plugin copy" / "hep-research"
    copy_package(dest)
    links = [str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_symlink()]
    repo = str(ROOT.parents[1])
    leaks = [str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md", ".csv", ".txt")
             and repo in p.read_text(encoding="utf-8", errors="replace")]
    cwd = Path(tempfile.mkdtemp(prefix="unrelated cwd "))
    out_dir = base / "runs"
    proc = subprocess.run([sys.executable, str(dest / "tools" / "run_all_checks.py"), "--out", str(out_dir)],
                          cwd=cwd, capture_output=True, text=True)
    runs = sorted(out_dir.glob("check-run-*.json"))
    summary = json.loads(runs[-1].read_text()) if runs else None
    result = {"relocated_to": str(dest), "path_has_spaces": " " in str(dest), "outside_repository": repo not in str(dest),
              "symlinks": links, "files_naming_source_path": leaks, "cwd": str(cwd), "exit_code": proc.returncode,
              "summary": {k: summary[k] for k in ("counts", "timestamp_utc")} if summary else None,
              "checks": [{"name": c["name"], "status": c["status"], "counts": c.get("counts")} for c in summary["checks"]] if summary else [],
              "stderr_tail": proc.stderr[-2000:] if proc.returncode else ""}
    result["pass"] = bool(proc.returncode == 0 and not links and not leaks and result["path_has_spaces"] and result["outside_repository"])
    text = json.dumps(result, indent=1)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        stamp = summary["timestamp_utc"].replace(":", "").replace("-", "") if summary else "failed"
        (args.out / f"relocation-{stamp}.json").write_text(text + "\n")
    print(text)
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(cwd, ignore_errors=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
