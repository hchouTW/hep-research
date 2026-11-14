#!/usr/bin/env python3
"""S9 gate 3: each negative test of Section 15.1 for S9 as a real change, which a test must then catch (g4sim plan, Section 19.2).

Section 15.1, S9 (Specification): alignment overlay layers, condition snapshots. Negative tests: an overlay referencing a non-existent
placement; condition snapshots with overlapping IOVs. A test that merely exists proves nothing, so a scratch copy of the code is first run
unchanged, and must pass, then with one change at a time, and must fail.
Usage: negatives.py --work DIR   Prints JSON with a status key. Exit 0 every change caught, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
COPIED = ("core", "contracts", "adapters/geant4/assets", "profiles", "tests/__init__.py", "tests/core", "tests/adapters")
ALIGNMENT, CONDITIONS = "core/geometry/alignment.py", "core/simulation/conditions.py"
T_ALIGNMENT, T_CONDITIONS = ("tests.core.test_geometry_alignment",), ("tests.core.test_simulation_conditions",)

# Section 15.1 row, change, file, [(text replaced, replacement)], tests that must fail
CHANGES = (
    ("Alignment overlay layers", "an overlay referencing a non-existent placement accepted (the shift skipped)", ALIGNMENT,
     [("        if not found:\n", "        if not found:\n            continue\n        if False:\n")], T_ALIGNMENT),
    ("Condition snapshots", "condition snapshots with overlapping IOVs accepted", CONDITIONS,
     [("        if start_b < end_a:", "        if False:")], T_CONDITIONS),
)

def run_tests(root: Path, modules: tuple) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, "-m", "unittest", *modules], cwd=root, capture_output=True, text=True, timeout=1200, check=False, env=environment)


def copy_plugin(work: Path) -> Path:
    root = work / "plugin"
    if root.exists():
        shutil.rmtree(root)
    for name in COPIED:
        source, target = PLUGIN / name, root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target)
    return root


def code_changes(work: Path) -> list:
    root = copy_plugin(work)
    modules = tuple(sorted({module for *_, tests in CHANGES for module in tests}))
    baseline = run_tests(root, modules)
    if baseline.returncode != 0:
        raise RuntimeError("the unchanged copy fails its tests: " + baseline.stderr[-800:])
    rows = []
    for row, change, name, replacements, tests in CHANGES:
        path = root / name
        original = path.read_text(encoding="utf-8")
        changed, missing = original, [old for old, _ in replacements if original.count(old) != 1]
        if missing:
            rows.append({"row": row, "change": change, "caught": False, "why": f"the text to change does not occur once in {name}: {missing[0][:60]!r}"})
            continue
        for old, replacement in replacements:
            changed = changed.replace(old, replacement)
        path.write_text(changed, encoding="utf-8")
        done = run_tests(root, tests)
        path.write_text(original, encoding="utf-8")
        failed = [line for line in done.stderr.splitlines() if line.startswith(("FAIL:", "ERROR:"))]
        rows.append({"row": row, "change": change, "file": name, "caught": done.returncode != 0, "failing_tests": failed[:4]})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        rows = code_changes(args.work)
    except (OSError, RuntimeError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    status = "ok" if all(row["caught"] for row in rows) else "failed"
    print(json.dumps({"status": status, "caught": sum(row["caught"] for row in rows), "of": len(rows), "rows": rows}, indent=1))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
