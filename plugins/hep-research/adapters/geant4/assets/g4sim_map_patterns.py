#!/usr/bin/env python3
"""The joint-pattern input of a shared-seed theta scan (simulator calibration Part B section 6.7, D28; phase 3, WP-D): join each mapping
run's primaries.csv and photons.csv into {event: bin} and {event: channel}, the arguments of core/calibration/map_basis.pattern_table.

The CSV layouts are those g4sim_efficiency_map.py build reads (g4sim S7): a primaries.csv row is (event, energy, x, y, z, ...) with the
emission point in world mm; a photons.csv row is (event, detector, copy, ..., transit_ns at column 4, ...), the channel being
"detector/copy". Header rows (first field "event") and comment rows ("#") are skipped. The emission point is binned as the map builder bins
it: into the template's frame (g4sim_simulate.to_local), then efficiency_map.bin_of with the production segmentation. A mapping run emits
one photon per event, so an event has at most one detection.

Rejected (MapPatternError, exit 2 from the caller): a malformed row; an event emitted twice; a detection in an event with no emission
point; two detections in one event. Across the scan: primaries that do not agree event by event (design_map.primaries_findings), and a
pattern table whose counts are not the maps' (map_basis.pattern_findings) are returned as findings. Usage from Python only; no Geant4.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import g4sim_efficiency_map as builder  # noqa: E402
import g4sim_simulate as simulate_new  # noqa: E402
from core.calibration import design_map, map_basis  # noqa: E402
from core.simulation import efficiency_map  # noqa: E402


class MapPatternError(ValueError):
    pass


def _rows(path: Path) -> list:
    try:
        return builder._csv(path)
    except OSError as err:
        raise MapPatternError(f"cannot read {path}: {err.strerror or err}") from None


def run_patterns(work: Path, template: str, segmentation: dict, ir: dict | None = None) -> dict:
    """One mapping run: {bins: {event: bin}, detections: {event: channel}, primaries: rows as read}."""
    work = Path(work)
    if ir is None:
        try:
            ir = json.loads((work / "ir.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            raise MapPatternError(f"{work}: no readable ir.json ({err})") from None
    try:
        _, half = builder.template_box(ir, template)
    except (builder.InputError, KeyError, ValueError, StopIteration) as err:
        raise MapPatternError(f"template {template}: {err}") from None
    primaries = _rows(work / "primaries.csv")
    bins: dict = {}
    for row in primaries:
        try:
            event, point = int(row[0]), [float(value) for value in row[2:5]]
        except (ValueError, IndexError):
            raise MapPatternError(f"{work / 'primaries.csv'}: malformed row {row}") from None
        if len(point) != 3:
            raise MapPatternError(f"{work / 'primaries.csv'}: malformed row {row}")
        if event in bins:
            raise MapPatternError(f"{work / 'primaries.csv'}: event {event} emitted twice")
        bins[event] = efficiency_map.bin_of(segmentation, half, simulate_new.to_local(ir, template, point))
    detections: dict = {}
    for row in _rows(work / "photons.csv"):
        try:
            event, channel = int(row[0]), f"{row[1]}/{row[2]}"
            float(row[4])
        except (ValueError, IndexError):
            raise MapPatternError(f"{work / 'photons.csv'}: malformed row {row}") from None
        if event not in bins:
            raise MapPatternError(f"{work}: a detection in event {event}, which has no emission point in primaries.csv")
        if event in detections:
            raise MapPatternError(f"{work}: event {event} has two detections; a mapping run emits one photon per event")
        detections[event] = channel
    return {"bins": bins, "detections": detections, "primaries": primaries}


def scan_patterns(works: list, template: str, segmentation: dict, maps: list | None = None, irs: list | None = None) -> dict:
    """The pattern table of a shared-seed scan, design points in plan order: works[j] the mapping-run directory of design point j, maps[j]
    its built map (whose `channels` order the categories; default: the sorted detecting channels, as the builder lists them)."""
    runs = [run_patterns(w, template, segmentation, None if irs is None else irs[j]) for j, w in enumerate(works)]
    findings = design_map.primaries_findings({str(w): r["primaries"] for w, r in zip(works, runs)})
    if findings:
        return {"status": "failed", "findings": findings}
    if any(r["bins"] != runs[0]["bins"] for r in runs[1:]):
        return {"status": "failed", "findings": [{"code": "design.map_primaries", "remedy": "plan",
                                                  "message": "the emission points bin differently across the scan"}]}
    channels = [m["channels"] for m in maps] if maps is not None else [sorted(set(r["detections"].values())) for r in runs]
    try:
        table = map_basis.pattern_table(runs[0]["bins"], [r["detections"] for r in runs], channels)
    except map_basis.BasisError as err:
        raise MapPatternError(str(err)) from None
    findings = map_basis.pattern_findings(table, maps) if maps is not None else []
    return {"status": "failed" if findings else "ok", "findings": findings, "pattern_table": table, "channels": channels,
            "pattern_table_sha256": map_basis.pattern_sha256(table), "bins": runs[0]["bins"],
            "detections": [r["detections"] for r in runs]}


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    print(json.dumps({"status": "rejected", "message": "a library: call run_patterns or scan_patterns from Python"}))
    sys.exit(2)
