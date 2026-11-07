"""Hit files of g4sim (plan, Section 9.2): the simulation-hits/1 index, and the checks that a hit file agrees with the scorers. Reads rows the caller got from `simroot hits`.

Pure computation apart from hashing the file named. simroot writes each ntuple as CSV; `columns_for_simreco` turns tracker hits into the crossing rows simreco reads.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

SCHEMA = "simulation-hits/1"
KINDS = ("mc_particle", "tracker_hit", "calorimeter_hit", "photon_hit")


def index(geometry_id: str, card: dict, path: Path, request_id: str = "") -> dict:
    run = card["run"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"schema": SCHEMA, "geometry_id": geometry_id, "request_id": request_id, "events": run["events"], "first_event": run.get("first_event", 0), "kinds": list(KINDS[:3]), "file_sha256": digest}


def sums_by_cell(rows: list, value: str = "edep_MeV") -> dict:
    """{(event, cell): correctly rounded sum} of dictionaries from one ntuple."""
    groups: dict = {}
    for row in rows:
        groups.setdefault((int(row["event_id"]), float(row["cell"])), []).append(float(row[value]))
    return {key: math.fsum(values) for key, values in groups.items()}


def closure(left: dict, right: dict, relative: float = 1e-12) -> dict:
    """Two {(event, cell): value} maps: what is missing on either side, and the worst relative difference."""
    missing = sorted(set(left) ^ set(right))
    worst = max((abs(left[key] - right[key]) / max(abs(left[key]), abs(right[key]), 1e-300) for key in set(left) & set(right)), default=0.0)
    return {"cells": len(left), "missing": missing[:10], "missing_count": len(missing), "worst_relative": worst, "ok": not missing and worst <= relative}


def owners_are_kept(particles: list, owned: list) -> list:
    """Track numbers that hits name but no kept particle has: attribution must end at a kept ancestor (Section 9.3)."""
    kept = {(int(row["event_id"]), int(row["track_id"])) for row in particles}
    return sorted({(int(row["event_id"]), int(row["track_id"])) for row in owned} - kept)[:10]


def columns_for_simreco(tracker_rows: list, planes: dict) -> list:
    """The first primary hit in each tracker plane, as simreco's crossing rows; `planes` maps a cell to a plane number."""
    seen: set = set()
    out = []
    for row in sorted(tracker_rows, key=lambda item: (int(item["event_id"]), int(item["step_index"]))):
        key = (int(row["event_id"]), float(row["cell"]))
        if int(row["track_id"]) != 1 or key in seen or float(row["cell"]) not in planes:
            continue
        seen.add(key)
        out.append({"event_id": key[0], "plane_id": planes[float(row["cell"])], "x_mm": float(row["x_mm"]), "y_mm": float(row["y_mm"]), "z_mm": float(row["z_mm"]), "time_ns": float(row["time_ns"])})
    return out
