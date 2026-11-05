#!/usr/bin/env python3
"""S1 gates 4 and 5 from the records of the reproduction job: every T1 run's legacy block equals its ProbeV2 record, every old
specification round-trips, and the inventory table has every recorded run in exactly one class.

Usage: check_records.py RECORDS_DIR --facts FACTS.json [--out INVENTORY.json]   RECORDS_DIR holds results.json, inventory.json and
runs/<run>/probe-v2.json.gz. Prints JSON with a status key. Exit 0 ok, 1 a problem found, 2 bad input.
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = _module("g4sim_inventory", PLUGIN / "adapters/geant4/assets/g4sim_inventory.py")
translate = _module("g4sim_translate", PLUGIN / "adapters/geant4/assets/g4sim_translate.py")
sampler = _module("g4proto_cost_sample", HERE / "cost_sample.py")


def check_run(row: dict, record: dict) -> list[str]:
    """What is wrong with one run's legacy block: nothing, for a T1 run that passes."""
    old = sampler.spec_of(row)
    problems = []
    parts = translate.split(old)
    if translate.merge(*parts) != old:
        problems.append("the old specification does not round-trip")
    block = translate.legacy_block(record, old, parts[2]["run"]["seeding"])
    problems += [f"block differs from the record: {key}" for key in translate.block_differences(block, record)]
    problems += [f"position of {name} differs from the old specification" for name in translate.position_differences(block, old)]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("records", type=Path)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        table = json.loads((args.records / "inventory.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    classes = {row["run"]: row["class"] for row in table}
    found: dict = {}
    checked = 0
    for row in facts:
        if not str(classes.get(row["run"])).startswith("T1"):
            continue
        try:
            with gzip.open(args.records / "runs" / row["run"] / "probe-v2.json.gz", "rt", encoding="utf-8") as stream:
                problems = check_run(row, json.load(stream))
        except (OSError, ValueError, KeyError) as err:
            problems = [f"{type(err).__name__}: {err}"]
        checked += 1
        if problems:
            found[row["run"]] = problems
    table_problems = inventory.table_problems(table, facts)
    if args.out:
        args.out.write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    clean = not found and not table_problems
    print(json.dumps({"status": "ok" if clean else "failed", "t1_runs_checked": checked, "runs_with_problems": len(found),
                      "first": dict(list(found.items())[:4]), "table_problems": table_problems[:6]}, indent=1))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
