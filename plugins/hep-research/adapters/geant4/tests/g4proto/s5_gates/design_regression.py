#!/usr/bin/env python3
"""S5 gates 1 and 2: J15 and the existing layered-spectrometer candidates are exactly the same with the modified design loop (g4sim plan, Sections 14.3, 19.2).

  capture --plugin ROOT --out DIR     replay the design examples of a plugin tree, write their outputs and, from every design geometry file, the specification from-geometry derives
  compare BEFORE AFTER                every file of the two captures, byte for byte, apart from the versions and times that name the writer

The capture of the code before any S5 change comes from a clean export of that commit, so the comparison does not rest on the tree under test. Prints JSON with a status key. Exit 0 same, 1 different.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXAMPLES = ("design-minimal-spectrometer", "design-search-j16", "design-space-spectrometer", "design-collider-tracker")
WRITER_KEYS = {"plugin_version", "contract_version", "contracts", "plugin", "plugin_release", "created", "created_utc", "generated_at", "timestamp", "timestamp_utc", "core", "tool_version"}
PROFILES = {"design-minimal-spectrometer": "j15.realization.json", "design-search-j16": "space.realization.json"}


def capture(plugin: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in EXAMPLES:
        target = out / name
        done = subprocess.run([sys.executable, "-B", str(plugin / "examples" / name / "run.py"), "--out", str(target)], capture_output=True, text=True, check=False, timeout=1800, cwd=plugin)
        report[name] = {"exit": done.returncode, "tail": done.stdout.strip()[-200:] if done.returncode else ""}
        if name in PROFILES:
            specs = target / "from-geometry"
            specs.mkdir(exist_ok=True)
            for geometry in sorted(target.rglob("*.geometry.json")):
                derived = subprocess.run([sys.executable, "-B", str(plugin / "adapters/geant4/assets/geant4_run.py"), "from-geometry", "--geometry", str(geometry), "--profile", str(plugin / "examples" / name / PROFILES[name]), "--out", str(specs / geometry.name)],
                                         capture_output=True, text=True, check=False, timeout=120, cwd=plugin)
                report[name][geometry.name] = derived.returncode
    return report


def without_writer(node):
    if isinstance(node, dict):
        return {key: without_writer(value) for key, value in node.items() if key not in WRITER_KEYS}
    if isinstance(node, list):
        return [without_writer(value) for value in node]
    return node


def same(left: Path, right: Path) -> bool:
    if left.read_bytes() == right.read_bytes():
        return True
    if left.suffix != ".json":
        return False
    try:
        return without_writer(json.loads(left.read_text(encoding="utf-8"))) == without_writer(json.loads(right.read_text(encoding="utf-8")))
    except ValueError:
        return False


def compare(before: Path, after: Path) -> dict:
    first = {path.relative_to(before) for path in before.rglob("*") if path.is_file()}
    second = {path.relative_to(after) for path in after.rglob("*") if path.is_file()}
    differing = sorted(str(path) for path in first & second if not same(before / path, after / path))
    return {"files": len(first & second), "only_before": sorted(map(str, first - second))[:20], "only_after": sorted(map(str, second - first))[:20], "differing": differing[:40], "differing_count": len(differing)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    taking = commands.add_parser("capture")
    taking.add_argument("--plugin", type=Path, required=True)
    taking.add_argument("--out", type=Path, required=True)
    judging = commands.add_parser("compare")
    judging.add_argument("before", type=Path)
    judging.add_argument("after", type=Path)
    args = parser.parse_args()
    if args.command == "capture":
        report = capture(args.plugin.resolve(), args.out.resolve())
        passed = all(item["exit"] == 0 for item in report.values())
        print(json.dumps({"status": "ok" if passed else "failed", **report}, indent=1))
        return 0 if passed else 1
    report = compare(args.before.resolve(), args.after.resolve())
    passed = report["files"] > 0 and not report["only_before"] and not report["only_after"] and not report["differing"]
    print(json.dumps({"status": "ok" if passed else "failed", **report}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
