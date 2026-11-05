#!/usr/bin/env python3
"""Judge GB1 and GB22 (g4sim plan, Section 23) from the files of one re-acquisition run: probe-v2.json, store-dump.txt and the
two engine states, written by ProbeHook.hh.

GB1: every position and rotation in the probe record equals, bit for bit, the double the store dump printed with %a, and the
engine state is the same before and after the probe. GB22: the run used the master-and-workers run manager, the probe ran on
the master, and no logical volume's field record is `declared`.

Usage: judge.py FOLDER [--mt] [--uninitialized PROBE.json]   --uninitialized names the record of a probe that ran after
/run/initialize, which must say recorded: false. Prints JSON with a status key; exit 0 confirmed, 1 not confirmed, 2 bad input.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def store_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        fields = line.rsplit(" ", 13)
        name, copy = fields[0], int(fields[1])
        rows.append({"name": name, "copy_number": copy, "translation": [float.fromhex(v) for v in fields[2:5]],
                     "rotation": [float.fromhex(v) for v in fields[5:14]]})
    return rows


def _probe_rotation(placement: dict) -> list[float]:
    if placement["rotation"] is None:
        return [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    return [float.fromhex(v) for v in placement["rotation"]]


def bit_disagreements(probe: dict, rows: list[dict]) -> int:
    """Doubles of the probe that differ from the store dump; a different count of placements counts each one missing."""
    placements = probe["base"]["geometry"]["placements"]
    count = abs(len(placements) - len(rows))
    for placement, row in zip(placements, rows):
        if (placement["name"], placement["copy_number"]) != (row["name"], row["copy_number"]):
            count += 1
            continue
        pairs = list(zip([float.fromhex(v) for v in placement["translation_mm"]], row["translation"]))
        pairs += list(zip(_probe_rotation(placement), row["rotation"]))
        count += sum(a.hex() != b.hex() and not (a == 0 and b == 0) for a, b in pairs)
    return count


def judge(probe: dict, rows: list[dict], before: bytes, after: bytes, multi_threaded: bool, uninitialized: dict | None) -> dict:
    disagreements = bit_disagreements(probe, rows)
    result: dict = {"placements": len(rows), "recorded": probe["recorded"], "disagreements": disagreements,
                    "engine_state_same": before == after, "random_state_unchanged": probe["random_state_unchanged"],
                    "processes": len(probe.get("processes", [])), "regions": len(probe.get("regions", []))}
    fields = probe.get("logical_fields", [])
    gb1 = (probe["recorded"] and bool(rows) and disagreements == 0 and before == after and probe["random_state_unchanged"]
           and result["processes"] > 0)
    if uninitialized is not None:
        result["after_initialize_recorded"] = uninitialized["recorded"]
        gb1 = gb1 and uninitialized["recorded"] is False
    result["GB1"] = gb1
    if multi_threaded:
        run_record = probe["base"].get("run_manager", {})
        declared = [row["logical"] for row in fields if row["source"] == "declared"]
        result["run_manager"] = run_record.get("class")
        result["declared"] = declared
        result["logicals_with_field"] = sum(row["field_manager"] is not None for row in fields)
        result["GB22"] = (probe["recorded"] and bool(fields) and not declared and run_record.get("type") == "master"
                          and "MT" in str(run_record.get("class")))
    result["status"] = "ok" if gb1 and result.get("GB22", True) else "failed"
    return result


def main(argv) -> int:
    args = list(argv[1:])
    multi_threaded = "--mt" in args
    args = [a for a in args if a != "--mt"]
    uninitialized_path = None
    if "--uninitialized" in args:
        at = args.index("--uninitialized")
        uninitialized_path = args[at + 1]
        del args[at:at + 2]
    if len(args) != 1:
        print(json.dumps({"status": "rejected", "message": "usage: judge.py FOLDER [--mt] [--uninitialized PROBE.json]"}))
        return 2
    folder = Path(args[0])
    try:
        probe = json.loads((folder / "probe-v2.json").read_text(encoding="utf-8"))
        rows = store_rows((folder / "store-dump.txt").read_text(encoding="utf-8"))
        before, after = (folder / "rng-before.txt").read_bytes(), (folder / "rng-after.txt").read_bytes()
        uninitialized = json.loads(Path(uninitialized_path).read_text(encoding="utf-8")) if uninitialized_path else None
    except (OSError, ValueError, IndexError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    result = judge(probe, rows, before, after, multi_threaded, uninitialized)
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
