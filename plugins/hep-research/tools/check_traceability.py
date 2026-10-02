#!/usr/bin/env python3
"""Traceability audit (AC01): every plugin file comes from a mapped legacy source or is registered as new.

Checks:
1. Every file tracked in the legacy repository at the pinned commit has a row in docs/migration-map.csv
   (needs a checkout passed with --legacy; skipped and reported as such without one).
2. Every reuse/adapt/merge row names concrete destinations that exist in the plugin; every row names the pinned commit.
3. Every distributable plugin file that is no migration destination is listed in docs/provenance-new.csv
   (path, commit that added it, milestone), and every listed file exists.
4. With --legacy: the legacy checkout is at the pinned commit with no local modification (legacy untouched).

  check_traceability.py [--legacy DIR] [--write-new]   (--write-new regenerates provenance-new.csv from git history)
Exit 0 ok, 1 problems. Standard library and git.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = "3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9"
MAP = ROOT / "docs" / "migration-map.csv"
NEW = ROOT / "docs" / "provenance-new.csv"
CARRIED = {"reuse", "adapt", "merge"}


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def plugin_files() -> list[str]:
    out = _git(["ls-files", "--cached", "--others", "--exclude-standard", "."], ROOT)
    return sorted(f for f in out.splitlines() if f and "__pycache__" not in f)


def read_map():
    return list(csv.DictReader(io.StringIO(MAP.read_text(encoding="utf-8"), newline="")))


def destinations(rows):
    return {d.strip() for r in rows if r["disposition"] in CARRIED for d in r["destination"].split(";") if d.strip()}


def first_commit(path: str):
    out = _git(["log", "--diff-filter=A", "--follow", "--format=%h%x09%s", "--", path], ROOT).strip().splitlines()
    if not out:
        return "uncommitted", ""
    h, subj = out[-1].split("\t", 1)
    m = re.search(r"hep-research\((M\d)\)", subj)
    return h, m.group(1) if m else ""


def write_new(rows):
    dest = destinations(rows)
    new = [f for f in plugin_files() if f not in dest]
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["path", "added_in_commit", "milestone", "origin"])
    for f in new:
        h, ms = first_commit(f)
        w.writerow([f, h, ms, "new in hep-research (no legacy source)"])
    NEW.write_text(buf.getvalue(), encoding="utf-8")
    return len(new)


def audit(legacy: Path | None) -> dict:
    rows = read_map()
    problems, skipped = [], []
    for r in rows:
        if r["source_commit"] != PINNED:
            problems.append({"code": "map.commit", "source": r["source_path"], "message": "source commit is not the pinned legacy commit"})
        if r["disposition"] in CARRIED:
            for d in [x.strip() for x in r["destination"].split(";") if x.strip()]:
                if not (ROOT / d).is_file():
                    problems.append({"code": "map.destination_missing", "source": r["source_path"], "destination": d,
                                     "message": "a carried file needs a concrete destination file"})
        elif not r["rationale"].strip():
            problems.append({"code": "map.no_reason", "source": r["source_path"], "message": f"{r['disposition']} needs a rationale"})
    files = plugin_files()
    dest = destinations(rows)
    listed = {}
    if NEW.exists():
        listed = {r["path"]: r for r in csv.DictReader(io.StringIO(NEW.read_text(encoding="utf-8"), newline=""))}
    for f in files:
        if f not in dest and f not in listed:
            problems.append({"code": "provenance.unregistered", "path": f, "message": "not a migration destination and not in provenance-new.csv"})
    for f in listed:
        if not (ROOT / f).exists():
            problems.append({"code": "provenance.stale", "path": f})
    if legacy:
        tracked = set(_git(["ls-files"], legacy).split("\n")) - {""}
        mapped = {r["source_path"] for r in rows}
        for f in sorted(tracked - mapped):
            problems.append({"code": "map.legacy_unmapped", "source": f})
        head = _git(["rev-parse", "HEAD"], legacy).strip()
        dirty = _git(["status", "--porcelain", "--untracked-files=no"], legacy).strip()
        if head != PINNED or dirty:
            problems.append({"code": "legacy.modified", "message": f"legacy checkout at {head[:9]}, local changes: {bool(dirty)}"})
        legacy_count = len(tracked)
    else:
        skipped.append("legacy coverage and untouched check: no --legacy checkout given")
        legacy_count = None
    return {"ok": not problems, "problems": problems, "skipped": skipped, "map_rows": len(rows),
            "legacy_tracked_files": legacy_count, "plugin_files": len(files),
            "from_legacy": sum(f in dest for f in files), "registered_new": sum(f in listed for f in files)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--legacy", type=Path)
    ap.add_argument("--write-new", action="store_true")
    a = ap.parse_args(argv)
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True).returncode != 0:
        print(json.dumps({"status": "skip", "reason": "not inside the source repository (provenance comes from git history)"}))
        return 1
    if a.write_new:
        print(json.dumps({"written": write_new(read_map())}))
    res = audit(a.legacy)
    print(json.dumps(res, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
