#!/usr/bin/env python3
"""S3 gate 1: the volume tree of g4sim against zdcsim's (g4sim plan, Section 19.2). Positions within 1e-6 mm, the same materials, masses within 1e-9.

Volumes are matched by the logical names along the mother path plus copy number, through MATCHING below; an unmatched volume fails the gate. zdcsim places the
crystal and its wrap side by side, with a G4SubtractionSolid wrap; g4sim's `shell` puts the crystal inside a wrapper box. Both fill the same space with the same matter.
Usage: volume_tree.py ZDCSIM_PROBE.json G4SIM_PROBE.json GEOMETRY.yaml   Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

POSITION_LIMIT_MM, MASS_LIMIT = 1e-6, 1e-9
MATERIAL_LIMIT = 1e-12
MATCHING = {"World": "world", "Crystal": "crystal", "Wrap": "crystal_shell", "SiPM": "sipm", "PCB": "pcb", "BM": "beam_monitor", "Window": "window"}
PACKED_WIDTH = 3  # the readout's ix field
SORTED_BY_ORDER = ("SiPM", "BM")  # zdcsim's copy numbers rise in the order of the positions; g4sim's take the next free numbers in that order


def hexes(values: list) -> tuple:
    return tuple(float.fromhex(value) for value in values) if values else (0.0, 0.0, 0.0)


def placed(record: dict) -> dict:
    """{logical name: [(copy chain, world position)]}, walking every daughter under every copy of its mother; no rotation occurs in these trees."""
    geometry = record["base"]["geometry"]
    names = {item["id"]: item["name"] for item in geometry["logical_volumes"]}
    children: dict = {}
    for row in geometry["placements"]:
        if row["mother_logical"] is not None:
            if row.get("rotation"):
                raise ValueError(f"{row['name']} is rotated, which this comparison does not cover")
            children.setdefault(row["mother_logical"], []).append(row)
    root = next(row for row in geometry["placements"] if row["mother_logical"] is None)
    out: dict = {}

    def visit(logical: int, chain: tuple, position: tuple) -> None:
        out.setdefault(names[logical], []).append((chain, position))
        for row in children.get(logical, []):
            step = hexes(row["translation_mm"])
            visit(row["logical"], (*chain, row["copy_number"]), tuple(a + b for a, b in zip(position, step)))
    visit(root["logical"], (), (0.0, 0.0, 0.0))
    return out


def paired(left: dict, right: dict, count: int) -> tuple:
    """Pairs of (left, right) volumes by MATCHING, and what stayed unmatched."""
    pairs, unmatched = [], []
    for name, rows in left.items():
        target = MATCHING.get(name)
        others = right.get(target, [])
        if target is None or len(others) != len(rows):
            unmatched.append(f"{name}: {len(rows)} here, {len(others)} as {target}")
            continue
        if name in ("Crystal", "Wrap"):
            by_chain = {row[0][0]: row for row in others}  # the wrapper's copy: ix + 2^3 iy
            for chain, position in rows:
                iy, ix = divmod(chain[-1], count)
                other = by_chain.get(ix + (iy << PACKED_WIDTH))
                if other is None:
                    unmatched.append(f"{name} {chain}")
                else:
                    pairs.append((name, chain, position, other[1]))
        else:
            for (chain, position), other in zip(sorted(rows), sorted(others)):
                pairs.append((name, chain, position, other[1]))
    unmatched += [f"{name} has no counterpart" for name in right if name not in MATCHING.values()]
    return pairs, unmatched


def box_volume(item: dict) -> float:
    half = item["solid"]["parameters"]
    return 8 * float.fromhex(half["half_x_mm"]) * float.fromhex(half["half_y_mm"]) * float.fromhex(half["half_z_mm"])


def density_of(record: dict, name: str) -> float:
    return float.fromhex(next(item for item in record["base"]["geometry"]["materials"] if item["name"] == name)["density_g_cm3"])


def masses(record: dict, config: dict) -> dict:
    """Mass of each logical, net of its daughters, in g; the wrap, a subtraction solid whose G4 volume is a Monte Carlo estimate (GB24), analytically."""
    geometry = record["base"]["geometry"]
    wrap = float(config.get("wrap_um", 65)) * 1e-3
    x, y, z = (float(config.get(key, default)) for key, default in (("crystal_x_mm", 20), ("crystal_y_mm", 20), ("crystal_z_mm", 53)))
    shell = (x + 2 * wrap) * (y + 2 * wrap) * (z + wrap) - x * y * z
    volumes = {}
    for item in geometry["logical_volumes"]:
        volumes[item["id"]] = shell if item["name"] == "Wrap" else box_volume(item)
    gross = dict(volumes)
    for row in geometry["placements"]:
        if row["mother_logical"] is not None:
            volumes[row["mother_logical"]] -= gross[row["logical"]]
    return {item["name"]: volumes[item["id"]] * density_of(record, item["material"]) * 1e-3 for item in geometry["logical_volumes"]}


def read_flat(path: Path) -> dict:
    pairs = (line.split("#")[0].split(":", 1) for line in path.read_text(encoding="utf-8").splitlines() if ":" in line.split("#")[0])
    return {key.strip(): value.strip() for key, value in pairs if value.strip()}


def materials_of(record: dict) -> dict:
    out = {}
    for item in record["base"]["geometry"]["materials"]:
        out[item["name"]] = {"density": float.fromhex(item["density_g_cm3"]), "elements": {row["symbol"]: float.fromhex(row["mass_fraction"]) for row in item["elements"]}}
    return out


def material_differences(left: dict, right: dict, logical_left: dict, logical_right: dict) -> list:
    problems = []
    for name, material in logical_left.items():
        other = logical_right.get(MATCHING.get(name))
        if other is None:
            continue
        a, b = left[material], right[other]
        if material != other and not (material == "FR4" and other == "FR4"):
            problems.append(f"{name}: {material} against {other}")
        if abs(a["density"] / b["density"] - 1) > MATERIAL_LIMIT or set(a["elements"]) != set(b["elements"]) or any(abs(a["elements"][key] - b["elements"][key]) > MATERIAL_LIMIT for key in a["elements"]):
            problems.append(f"{name}: composition of {material} differs")
    return problems


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"status": "rejected", "message": "usage: volume_tree.py ZDCSIM_PROBE.json G4SIM_PROBE.json GEOMETRY.yaml"}))
        return 2
    zdcsim, g4sim = (json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:3])
    config = read_flat(Path(sys.argv[3]))
    pairs, unmatched = paired(placed(zdcsim), placed(g4sim), int(config.get("n_crystals", 8)))
    worst = max((max(abs(a - b) for a, b in zip(left, right)) for _, _, left, right in pairs), default=math.inf)
    where = max(pairs, key=lambda row: max(abs(a - b) for a, b in zip(row[2], row[3])))[:2] if pairs else None
    logical = [{item["name"]: item["material"] for item in record["base"]["geometry"]["logical_volumes"]} for record in (zdcsim, g4sim)]
    problems = material_differences(materials_of(zdcsim), materials_of(g4sim), *logical)
    left, right = masses(zdcsim, config), masses(g4sim, config)
    relative = {name: abs(value / right[MATCHING[name]] - 1) for name, value in left.items() if MATCHING.get(name) in right}
    passed = not unmatched and worst <= POSITION_LIMIT_MM and not problems and max(relative.values()) <= MASS_LIMIT
    print(json.dumps({"status": "ok" if passed else "failed", "volumes_matched": len(pairs), "unmatched": unmatched[:20], "worst_position_mm": worst, "worst_at": where, "material_problems": problems,
                      "mass_relative": relative, "masses_g": left}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
