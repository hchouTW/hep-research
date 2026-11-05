#!/usr/bin/env python3
"""Judge GB4 and GB10 (g4sim plan, Section 23) from the two files gb4_gb10 writes. Exact: every placement is rebuilt from
its decimal strings and rational rotations with fractions.Fraction, so the reference has no rounding of its own.

Usage: judge.py T.json R.json EXTENT.json   Prints JSON with a status key; exit 0 confirmed, 1 not confirmed, 2 bad input.
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction

X_MM = 20000
EXPECTED_REGIONS = {"World": "DefaultRegionForTheWorld", "G1": "RegionOuter", "G2": "RegionOuter", "G3": "RegionInner",
                    "G4": "RegionInner", "G5": "DefaultRegionForTheWorld"}
LEVEL_COEFFICIENT = {False: 1, True: 10}  # k of Section 7.3: a translation level, a level with an arbitrary rotation


def exact(hex_text: str) -> Fraction:
    return Fraction(float.fromhex(hex_text))


def matrix(rotation):
    axis, c, s, h = rotation
    c, s = Fraction(c, h), Fraction(s, h)
    return {"x": [[1, 0, 0], [0, c, -s], [0, s, c]], "y": [[c, 0, s], [0, 1, 0], [-s, 0, c]],
            "z": [[c, -s, 0], [s, c, 0], [0, 0, 1]]}[axis]


def apply(m, v):
    return [sum(row[i] * v[i] for i in range(3)) for row in m]


def transpose(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def into_level(point, level):
    """A point in the mother's frame, in the frame of a placed volume: R (p - t)."""
    t = [Fraction(text) for text in level["t"]]
    shifted = [p - q for p, q in zip(point, t)]
    return apply(matrix(level["rotation"]), shifted) if level["rotation"] else shifted


def end_level(chain, name):
    offset = Fraction(chain["end_half"]) + Fraction(chain["gap_half"])
    side = offset if name.endswith("B") else -offset
    rotation = chain["end_rotation"] if chain["rotated_end"] else None
    shift = [side, 0, 0]
    if rotation:
        shift = apply(transpose(matrix(rotation)), shift)
    return {"t": [str(value) for value in shift], "rotation": rotation}


def true_local(chain, volume, global_point):
    point = global_point
    for level in chain["mothers"]:
        point = into_level(point, level)
        if level["name"] == volume:
            return point
    if volume in (chain["key"] + "A", chain["key"] + "B"):
        return into_level(point, end_level(chain, volume))
    raise ValueError(f"{volume} is not on chain {chain['key']}")


def bound_mm(chain) -> float:
    levels = [level["rotation"] is not None for level in chain["mothers"]] + [chain["rotated_end"]]
    return (1 + sum(LEVEL_COEFFICIENT[rotated] for rotated in levels)) * math.ulp(X_MM)


def expected_path(chain):
    key, names = chain["key"], [level["name"] for level in chain["mothers"]]
    return [key + "A", names[-1], key + "B", *reversed(names), "World"]


def judge(translated: dict, rotated: dict, extent: dict) -> dict:
    run = {**rotated, "chains": translated["chains"] + rotated["chains"], "samples": translated["samples"] + rotated["samples"],
           "shots": translated["shots"] + rotated["shots"]}
    chains = {chain["key"]: chain for chain in run["chains"]}
    result: dict = {"geant4": run["geant4"], "overlaps": translated["overlaps"] + rotated["overlaps"]}
    wrong = {k: v for k, v in EXPECTED_REGIONS.items() if run["regions"].get(k) != v}
    result["GB4"] = {"logicals": len(run["regions"]), "disagreements": wrong,
                     "confirmed": not wrong and set(run["regions"]) == set(EXPECTED_REGIONS)}
    tolerance = float.fromhex(run["surface_tolerance"])
    after, world = float.fromhex(extent["after"]), float.fromhex(extent["extent_mm"])
    checks = {"default_tolerance_1e-9": tolerance == 1e-9, "before_extent_1e-9": float.fromhex(extent["before"]) == 1e-9,
              "inside_half_tolerance": run["inside_at_0p4e-9"] == run["kSurface"]
              and run["inside_at_0p6e-9"] == run["kOutside"],
              "extent_x_1e-11": math.isclose(after, world * 1e-11, rel_tol=1e-12), "no_overlaps": result["overlaps"] == 0}
    per_chain = {}
    for key, chain in chains.items():
        samples = [s for s in run["samples"] if s["chain"] == key]
        worst, reach, volumes = Fraction(0), Fraction(0), {}
        for sample in samples:
            point = [exact(v) for v in sample["global"]]
            truth = true_local(chain, sample["volume"], point)
            worst = max(worst, *(abs(exact(a) - b) for a, b in zip(sample["local"], truth)))
            reach = max(reach, *(abs(p) for p in point))
            volumes[sample["volume"]] = volumes.get(sample["volume"], 0) + 1
        shots = [s for s in run["shots"] if s["chain"] == key]
        expected = expected_path(chain)
        bad = [s["path"] for s in shots if s["path"] != expected]
        bound = bound_mm(chain)
        per_chain[key] = {"levels": len(chain["mothers"]) + 1, "samples": len(samples), "volumes": volumes,
                          "max_error_mm": float(worst), "max_error_ulp": float(worst) / math.ulp(X_MM), "bound_mm": bound,
                          "largest_global_coordinate_mm": float(reach), "shots": len(shots),
                          "expected_steps": len(expected), "wrong_paths": len(bad), "first_wrong_path": bad[0] if bad else None,
                          "within_bound": float(worst) <= bound and bound <= 1e-10, "crossings_ok": bool(shots) and not bad}
    both_sides = all({k + "A", k + "B"} <= set(per_chain[k]["volumes"]) for k in per_chain)
    confirmed = all(checks.values()) and both_sides and all(c["within_bound"] and c["crossings_ok"] for c in per_chain.values())
    result["GB10"] = {"checks": checks, "chains": per_chain, "both_sides_sampled": both_sides, "confirmed": confirmed}
    result["status"] = "ok" if result["GB4"]["confirmed"] and confirmed else "failed"
    return result


def main(argv) -> int:
    if len(argv) != 4:
        print(json.dumps({"status": "rejected", "message": __doc__.splitlines()[-1]}))
        return 2
    documents = []
    for path in argv[1:]:
        with open(path, encoding="utf-8") as stream:
            documents.append(json.load(stream))
    result = judge(*documents)
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
