#!/usr/bin/env python3
"""S8 gate 1: check-spec at 10^6 touchables within the performance budget (g4sim-performance-budget.md: at most 300 s).

Two specifications of 10^6 touchables: nested, 10^3 modules of 10^3 cells each (2,000 IR placements; the checks run per logical, Section 16),
and flat, 10^6 cells in one mother (10^6 IR placements: the sibling check meets every cell). check-spec is contracts/geometry.check_file, the
reading, expansion, gap rule, IR validation and identities of a specification; each is timed once, in the process that runs it, on the
environment that runs the gate. Peak memory is reported; the budget sets no limit on it for check-spec.
Usage: scale.py --work DIR   Prints JSON with a status key. Exit 0 both within the limit, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from contracts import geometry  # noqa: E402

LIMIT_S = 300.0  # g4sim-performance-budget.md, check-spec for 10^6 touchables


def cell(size: str) -> dict:
    return {"solid": {"box": {"size_mm": [size, size, size]}}, "material": "G4_PbWO4", "tags": ["cell"]}


def nested() -> dict:
    return {"schema": "detector-spec/1", "params": {},
            "templates": {"module": {"solid": {"box": {"size_mm": ["99", "99", "99"]}}, "material": "G4_AIR",
                                     "children": [{"template": "cell", "placement": {"grid": {"n": [10, 10, 10], "pitch_mm": ["9.9", "9.9", "9.9"], "centre_mm": ["0", "0", "0"], "index": ["i", "j", "k"]}}}]},
                          "cell": cell("9")},
            "world": {"material": "G4_Galactic", "size_mm": ["2000", "2000", "2000"],
                      "children": [{"template": "module", "placement": {"grid": {"n": [10, 10, 10], "pitch_mm": ["100", "100", "100"], "centre_mm": ["0", "0", "0"], "index": ["a", "b", "c"]}}}]}}


def flat() -> dict:
    return {"schema": "detector-spec/1", "params": {}, "templates": {"cell": cell("9")},
            "world": {"material": "G4_Galactic", "size_mm": ["2000", "2000", "2000"],
                      "children": [{"template": "cell", "placement": {"grid": {"n": [100, 100, 100], "pitch_mm": ["10", "10", "10"], "centre_mm": ["0", "0", "0"], "index": ["i", "j", "k"]}}}]}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, document in (("nested", nested()), ("flat", flat())):
        path = args.work / f"{name}.json"
        path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        start = time.perf_counter()
        result = geometry.check_file(path)
        seconds = time.perf_counter() - start
        placements = len(result.get("ir", {}).get("physical", {}).get("placements", []))
        rows.append({"spec": name, "touchables": 10 ** 6, "ir_placements": placements, "status": result["status"], "findings": [item["code"] for item in result["findings"]][:3],
                     "seconds": seconds, "limit_s": LIMIT_S, "within": result["status"] == "ok" and seconds <= LIMIT_S,
                     "peak_memory_MB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024})
    status = "ok" if all(row["within"] for row in rows) else "failed"
    print(json.dumps({"status": status, "rows": rows}, indent=1))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
