#!/usr/bin/env python3
"""T08's calibration-interface checks of plan R37 (D2 stage 2): CAI-T08-1, fixed membership, and CAI-T08-2, full
re-reconstruction, on products of reco.calo.cell-cluster/1. Harness side: it reads products and gain payloads, never truth,
and the recipe never imports it.

Rules, fixed before any run (D2 stage 2 report):
- The changed gain: a payload derived from the nominal one, with the gain of the channels ix % 8 == 3 and iy % 8 == 3 (25
  channels of a 40 x 40 grid, a lattice 8 cells apart, so a shower usually holds one of them) set to 1.25 times its nominal
  value, in both roles: E rises by 25 % when the gain multiplies (c' = 1.25 c) and falls by 20 % when it divides (g' = 1.25 g).
- Well above threshold: a changed member is well above threshold when min(E_old, E_new) >= 2 T_c. With membership fixed this
  is R37's precondition "cells well above threshold", taken as twice the cell threshold before and after the change; it needs
  no further margin argument (review N3). An object enters CAI-T08-1's exact assertion if every changed member is well above threshold; an object
  with a changed member below it is recorded, not asserted (R37's condition "cells well above threshold" does not hold).
- CAI-T08-1, asserted: |(A_new - A_product) - formula| <= 1e-12 max(sum f |E_old|, sum f |E_new|, 1 MeV) for every asserted
  object, with A_new and the formula from recalibration.fixed_membership (fractions held at the product's values), and at
  least 100 asserted objects with a changed member in the run (--min-asserted); an object with no changed member has a formula
  of exactly 0 and the same bound on its change. The tolerance is floating-point arithmetic: about 100 terms each rounded a few
  times (relative 1.1e-16 each) give at most about 1e-15 of the scale, so 1e-12 leaves a margin of 1,000. A planted fraction
  change delta on member c moves (change - formula) by exactly delta E_old,c, so it fails the bound by delta E_c / scale over
  1e-12: with delta 1e-6, a changed member of at least 1.2 MeV and a scale of at most about 8 GeV at E3, at least about 150
  times the bound (review m6).
- What the assertion can detect (review F2): on a product that passed its reader and the double-count check, a failure can only
  come from the formula, the retained values (raw, pedestal, gain, e_c and the fractions) or a discrepancy in A = sum f e between
  1e-12 and 1e-9. It is a retention-and-formula check (R34, R37). It does not run cell_chain.apply and clustering under the
  changed payload; that is CAI-T08-2's rerun, whose one-peak objects with unchanged membership are read by kind there.
- Recorded, not asserted: objects below the rule; the two-peak re-shared energies (recalibration.reshare: the recipe's own
  sharing on the same cells and peaks, the fractions following the new e_c; R37: "recorded without an exact assertion");
  everything of CAI-T08-2.

Operations:
  payloads          write the nominal and derived calo-gain-payload/1 files of both roles, and two refusal cases (another
                    channel map; an unknown channel), from a calo-cells/1 file's grid and its pedestal payload.
  fixed-membership  CAI-T08-1 on a product and the derived payload; writes t08-cai-fixed-membership/1; exit 0 PASS, 1 FAIL.
                    --plant-fraction-defect raises one asserted object's fraction by 1e-6 first: a control that must FAIL.
  rereco            CAI-T08-2 on the nominal product and the product re-reconstructed under the derived payload; writes
                    t08-cai-rereco/1 and reading lines, no numeric assertion; exit 0.
Exit 2: an input refused (REFUSED line), including an output file that exists: a record is never overwritten, and a product made
with another configuration file than the one given (default t08-grid/1's), whose thresholds the checks would use (D2 stage 4).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from calo_recipe import cell_input, configuration, gain_payload, product, recalibration  # noqa: E402

CHANGE_FACTOR = 1.25
LATTICE_STEP, LATTICE_OFFSET = 8, 3
WELL_ABOVE_FACTOR = 2.0
TOLERANCE = 1e-12
MIN_ASSERTED = 100
PLANTED_FRACTION_STEP = 1e-6
FIXED_FORMAT = "t08-cai-fixed-membership/1"
REREC_FORMAT = "t08-cai-rereco/1"
NOMINAL_SOURCE = ("t08-grid/1 fixture constant gain in calo-gain-payload/1 (D2 stage 2), the harness's calo-calibration-payload/1 "
                  "gain: raw = value / gain + pedestal, so the gain multiplies")
DIVIDE_SOURCE = ("t08-grid/1 fixture constant gain declared as dividing, g = 1 / c = 1: an interface construct for CAI-T08-1's "
                 "divide role; E = (ADC - pedestal) / 1 equals (ADC - pedestal) x 1 bit for bit")
DERIVED_SOURCE = ("CAI-T08-1 and -2 synthetic change (D2 stage 2): gain x 1.25 on the channels ix % 8 == 3 and iy % 8 == 3; "
                  "no measurement (R31)")


class Refused(ValueError):
    """An input of the CAI checks is refused."""


def changed_channels(nx: int, ny: int) -> list:
    return [ix * ny + iy for ix in range(nx) for iy in range(ny) if ix % LATTICE_STEP == LATTICE_OFFSET and iy % LATTICE_STEP == LATTICE_OFFSET]


def well_above(lowest, cfg) -> bool:
    """None: no changed member. Otherwise min over changed members of min(E_old, E_new) against 2 T_c."""
    return lowest is None or lowest >= WELL_ABOVE_FACTOR * cfg.cell_threshold


def payload_summary(gain) -> dict:
    return {"payload_id": gain.identity, "format": gain.format, "operation": gain.operation, "channel_map": gain.channel_map,
            "derived_from": gain.derived_from, "changed_channels": list(gain.changed_channels), "origin": gain.origin}


# --- CAI-T08-1 -----------------------------------------------------------------------------------------------------------------

@dataclass
class Outcome:
    passed: bool
    lines: list
    records: list = field(default_factory=list)
    asserted: int = 0
    recorded: int = 0


def assess(read, old_gain, new_gain, cfg, label: str, min_asserted: int = MIN_ASSERTED, plant: bool = False) -> Outcome:
    """CAI-T08-1 over every object of a read product. With plant, the first asserted object with a changed member gets one
    fraction raised by 1e-6 before its re-evaluation: the exact assertion must then fail."""
    header = read.header
    operation = header["chain"][1]["operation"]
    events = read.events
    planted = None
    changes = [recalibration.fixed_membership(ev, header, old_gain, new_gain) for ev in events]
    if plant:
        for i, per_event in enumerate(changes):
            k = next((c.object for c in per_event if c.changed_members and well_above(c.lowest_changed, cfg)), None)
            if k is None:
                continue
            event = copy.deepcopy(events[i])
            member = next(m for m in event["objects"][k]["members"] if new_gain.values[m[0]] != old_gain.values[m[0]])
            member[1] += PLANTED_FRACTION_STEP
            changes[i] = recalibration.fixed_membership(event, header, old_gain, new_gain)
            planted = (i, k, member[0])
            break
    asserted_worst = unchanged_worst = recorded_worst = 0.0
    counts = {"objects": 0, "with": 0, "asserted": 0, "one": 0, "two": 0, "recorded": 0, "without": 0}
    unchanged_ok = True
    relative = {"one-peak": [], "two-peak": []}
    reshare_diffs, reshare_rel = [], []
    reshare_skipped = set()
    records = []
    for i, per_event in enumerate(changes):
        reshared = None
        row = []
        for c in per_event:
            counts["objects"] += 1
            difference = abs(c.change - c.formula) / c.scale
            status = "unchanged"
            if not c.changed_members:
                counts["without"] += 1
                unchanged_ok &= c.formula == 0.0
                unchanged_worst = max(unchanged_worst, difference)
            elif well_above(c.lowest_changed, cfg):
                status = "asserted"
                counts["with"] += 1
                counts["asserted"] += 1
                counts["one" if c.kind == "one-peak" else "two"] += 1
                asserted_worst = max(asserted_worst, difference)
                relative[c.kind].append(c.change / c.energy_product)
            else:
                status = "recorded"
                counts["with"] += 1
                counts["recorded"] += 1
                recorded_worst = max(recorded_worst, difference)
            entry = {"object": c.object, "kind": c.kind, "members": c.members, "changed_members": c.changed_members,
                     "lowest_changed": c.lowest_changed, "energy_product": c.energy_product, "energy_new": c.energy_new, "change": c.change,
                     "formula": c.formula, "scale": c.scale, "status": status}
            if c.kind == "two-peak" and c.changed_members:
                if reshared is None:
                    reshared = recalibration.reshare(events[i], header, old_gain, new_gain, cfg)
                if c.object in reshared:
                    entry["reshared_energy"] = reshared[c.object]
                    gap = (reshared[c.object] - c.energy_product) - c.formula
                    reshare_diffs.append(abs(gap))
                    if c.formula != 0.0:
                        reshare_rel.append(abs(gap / c.formula))
                else:
                    reshare_skipped.add((i, c.component))
            row.append(entry)
        records.append({"event": events[i]["event"], "objects": row})
    exact_ok = asserted_worst <= TOLERANCE and counts["asserted"] >= min_asserted
    unchanged_ok &= unchanged_worst <= TOLERANCE
    verdict = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    mean = lambda values: f"{statistics.fmean(values):+.5f}" if values else "none"  # noqa: E731
    lines = [f"CAI-T08-1 {label} role {operation}: {counts['objects']} objects in {len(events)} events; with a changed member "
             f"{counts['with']} (well above threshold, asserted, {counts['asserted']}; below it, recorded, {counts['recorded']}); "
             f"without {counts['without']}"]
    if planted:
        lines.append(f"CAI-T08-1 {label} CONTROL planted: fraction of channel {planted[2]} in object {planted[1]} of event "
                     f"{events[planted[0]]['event']} raised by {PLANTED_FRACTION_STEP}; the exact assertion must fail")
    lines += [
        f"CAI-T08-1 {label} exact formula on {counts['asserted']} objects (one-peak {counts['one']}, two-peak with fractions held "
        f"fixed {counts['two']}): largest |change - formula| / scale {asserted_worst:.3e}, tolerance {TOLERANCE:g}, at least "
        f"{min_asserted} objects: {verdict(exact_ok)}",
        f"CAI-T08-1 {label} no changed member, {counts['without']} objects: formula exactly 0, largest |change| / scale "
        f"{unchanged_worst:.3e} within {TOLERANCE:g}: {verdict(unchanged_ok)}",
        f"CAI-T08-1 {label} RECORD below the well-above-threshold rule, {counts['recorded']} objects: largest |change - formula| / "
        f"scale {recorded_worst:.3e} (not asserted)",
        f"CAI-T08-1 {label} RECORD mean relative change of asserted objects: one-peak {mean(relative['one-peak'])}, two-peak "
        f"{mean(relative['two-peak'])}",
        f"CAI-T08-1 {label} RECORD two-peak re-shared (same cells and peaks, fractions from the new e_c), {len(reshare_diffs)} objects: "
        f"largest |change - formula| {max(reshare_diffs, default=0.0):.4g} MeV, median relative to |formula| "
        f"{statistics.median(reshare_rel) if reshare_rel else 0.0:.4g}; components skipped {len(reshare_skipped)} (sharing undefined under "
        f"the new e_c, or not two two-peak objects) (not asserted: the fractions depend on e_c)",
        f"CAI-T08-1 {label} RESULT {verdict(exact_ok and unchanged_ok)}",
    ]
    return Outcome(passed=exact_ok and unchanged_ok, lines=lines, records=records, asserted=counts["asserted"], recorded=counts["recorded"])


# --- CAI-T08-2 -----------------------------------------------------------------------------------------------------------------

def members_of(cluster) -> dict:
    return {c: f for c, f in cluster["members"]}


def match_objects(nominal: dict, changed: dict) -> list:
    """[(nominal object, changed object or None, how)]: the changed object with the same peak channel, else the one with the
    largest sum over common members of min(f_nominal, f_changed) above 0 (ties to the lower index), else none."""
    by_peak = {o["peak_channel"]: j for j, o in enumerate(changed["objects"])}
    out = []
    for k, cluster in enumerate(nominal["objects"]):
        if cluster["peak_channel"] in by_peak:
            out.append((k, by_peak[cluster["peak_channel"]], "peak"))
            continue
        mine = members_of(cluster)
        best, best_overlap = None, 0.0
        for j, other in enumerate(changed["objects"]):
            overlap = sum(min(mine[c], f) for c, f in other["members"] if c in mine)
            if overlap > best_overlap:
                best, best_overlap = j, overlap
        out.append((k, best, "overlap" if best is not None else "none"))
    return out


def appeared(matches: list, changed: dict) -> list:
    taken = {j for _, j, _ in matches if j is not None}
    return [j for j in range(len(changed["objects"])) if j not in taken]


def check_configuration(header: dict, cfg) -> None:
    """The thresholds these checks use (2 T_c, the well-above rule) are the configuration's given here: the product must have been
    made with that configuration file, so a product of another working point is never checked with this one's cuts (D2 stage 4,
    scenarios A15 and A32)."""
    if header["configuration"]["sha256"] != cfg.sha256:
        raise Refused(f"the product was made with configuration {header['configuration']['sha256']}, not the configuration given "
                      f"here ({cfg.sha256}), whose thresholds these checks would use")


def membership_changes(members_a, members_b) -> int:
    return len({c for c, _ in members_a} ^ {c for c, _ in members_b})


def rereco(nominal, changed, old_gain, new_gain, cfg, label: str):
    """CAI-T08-2: lines and per-event records. Refuses products that differ in anything but the gain payload."""
    hn, hc = nominal.header, changed.header
    if hn["format"] != hc["format"]:
        raise Refused(f"the nominal product ({hn['format']}) and the changed product ({hc['format']}) have different formats")
    if hn["chain"][1]["payload_id"] != old_gain.identity or hc["chain"][1]["payload_id"] != new_gain.identity:
        raise Refused("the nominal product must have consumed the old gain payload and the changed product the new one")
    if (hn["input"], hn["configuration"], hn["grid"], hn["chain"][0]) != (hc["input"], hc["configuration"], hc["grid"], hc["chain"][0]):
        raise Refused("the two products differ in input, configuration, grid or pedestal payload: not only the gain changed")
    check_configuration(hn, cfg)
    operation = hn["chain"][1]["operation"]
    lattice = {c for c in range(new_gain.values.size) if new_gain.values[c] != old_gain.values[c]}
    histogram, histogram_changed = [0, 0, 0, 0], [0, 0, 0, 0]
    how_counts = {"peak": 0, "overlap": 0, "none": 0}
    largest_membership = 0
    new_objects = 0
    entered = entered_lattice = left = left_lattice = 0
    with_changes, without_changes = [], []
    gap_one, gap_two, gap_other = [], [], []
    event_gaps = []
    comps = [0, 0]
    failed = [0, 0]
    objects = [0, 0]
    records = []
    for ev_n, ev_c in zip(nominal.events, changed.events):
        fixed = recalibration.fixed_membership(ev_n, hn, old_gain, new_gain)
        matches = match_objects(ev_n, ev_c)
        fresh = appeared(matches, ev_c)
        new_objects += len(fresh)
        objects[0] += len(ev_n["objects"])
        objects[1] += len(ev_c["objects"])
        comps[0] += len(ev_n["components"])
        comps[1] += len(ev_c["components"])
        failed[0] += sum(c["failure"] is not None for c in ev_n["components"])
        failed[1] += sum(c["failure"] is not None for c in ev_c["components"])
        kept_n = {row[0]: row[5] for row in ev_n["cells"]}
        kept_c = {row[0] for row in ev_c["cells"]}
        came, went = kept_c - set(kept_n), set(kept_n) - kept_c
        entered += len(came)
        entered_lattice += len(came & lattice)
        left += len(went)
        left_lattice += len(went & lattice)
        formula_event = math.fsum(e * recalibration.ratio_minus_one(operation, float(old_gain.values[c]), float(new_gain.values[c]))
                                  for c, e in kept_n.items())
        clustered_change = ev_c["clustered_sum"] - ev_n["clustered_sum"]
        event_gaps.append((clustered_change - formula_event, TOLERANCE * max(abs(ev_n["clustered_sum"]), 1.0)))
        rows = []
        for (k, j, how), change in zip(matches, fixed):
            how_counts[how] += 1
            count = membership_changes(ev_n["objects"][k]["members"], ev_c["objects"][j]["members"]) if j is not None else None
            energy_c = ev_c["objects"][j]["energy"] if j is not None else None
            if count is not None:
                histogram[min(count, 3)] += 1
                if change.changed_members:
                    histogram_changed[min(count, 3)] += 1
                largest_membership = max(largest_membership, count)
                delta = energy_c - ev_n["objects"][k]["energy"]
                (with_changes if change.changed_members else without_changes).append((delta, ev_n["objects"][k]["energy"]))
                if count != 0:
                    gap_other.append(abs(delta - change.formula))
                elif change.kind == "one-peak":
                    gap_one.append(abs(delta - change.formula) / change.scale)
                else:
                    gap_two.append(abs(delta - change.formula))
            rows.append({"object": k, "counterpart": j, "how": how, "membership_changes": count, "changed_members": change.changed_members,
                         "energy_nominal": ev_n["objects"][k]["energy"], "energy_changed": energy_c, "formula_fixed": change.formula})
        records.append({"event": ev_n["event"], "objects": rows, "appeared": fresh, "entered": sorted(came), "left": sorted(went),
                        "clustered_change": clustered_change, "formula_event": formula_event})
    n_events = len(nominal.events)
    deltas = [d for d, _ in with_changes]
    rel = [d / a for d, a in with_changes if a]
    lines = [
        f"CAI-T08-2 {label} role {operation}: {n_events} events; objects nominal {objects[0]}, changed {objects[1]}; components "
        f"nominal {comps[0]}, changed {comps[1]}; components without objects nominal {failed[0]}, changed {failed[1]}",
        f"CAI-T08-2 {label} kept cells: entered {entered} (changed-gain channels {entered_lattice}), left {left} (changed-gain "
        f"channels {left_lattice})",
        f"CAI-T08-2 {label} counterparts of nominal objects: by peak channel {how_counts['peak']}, by overlap {how_counts['overlap']}, "
        f"none {how_counts['none']}; changed objects with no nominal counterpart {new_objects}",
        f"CAI-T08-2 {label} membership changes per object (channels in one member set only) 0:{histogram[0]} 1:{histogram[1]} "
        f"2:{histogram[2]} 3+:{histogram[3]}, largest {largest_membership}; of objects with a changed member 0:{histogram_changed[0]} "
        f"1:{histogram_changed[1]} 2:{histogram_changed[2]} 3+:{histogram_changed[3]}",
        f"CAI-T08-2 {label} energy change of objects with a changed member: n {len(deltas)} mean "
        f"{statistics.fmean(deltas) if deltas else 0.0:+.4f} MeV, min {min(deltas, default=0.0):+.4f}, max {max(deltas, default=0.0):+.4f}, "
        f"mean relative {statistics.fmean(rel) if rel else 0.0:+.5f}; without a changed member: n {len(without_changes)}, largest "
        f"|change| {max((abs(d) for d, _ in without_changes), default=0.0):.4g} MeV",
        f"CAI-T08-2 {label} change minus the fixed-membership formula: one-peak, membership unchanged n {len(gap_one)} largest "
        f"{max(gap_one, default=0.0):.3e} of the scale; two-peak, membership unchanged n {len(gap_two)} largest "
        f"{max(gap_two, default=0.0):.4g} MeV (the re-sharing); membership changed n {len(gap_other)} largest "
        f"{max(gap_other, default=0.0):.4g} MeV (a reading, no assertion: R37)",
        f"CAI-T08-2 {label} event clustered-sum change minus the formula over the nominal kept cells: min "
        f"{min((g for g, _ in event_gaps), default=0.0):+.4g} max {max((g for g, _ in event_gaps), default=0.0):+.4g} MeV; "
        f">= 0 in {sum(g >= -t for g, t in event_gaps)} of {n_events} events, <= 0 in {sum(g <= t for g, t in event_gaps)} of "
        f"{n_events} (to rounding: {TOLERANCE:g} of the nominal sum)",
        f"CAI-T08-2 {label} RECORD recorded without a numeric assertion (R37)",
    ]
    return lines, records


# --- files -------------------------------------------------------------------------------------------------------------------

def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path: Path, content: bytes) -> None:
    """Writes a file that does not exist yet; an existing one is never overwritten."""
    try:
        with open(path, "xb") as stream:
            stream.write(content)
    except FileExistsError:
        raise Refused(f"{path} exists: a record or payload is never overwritten") from None


def write_payloads(cells_path, pedestal_path, gain_path, out_dir, stem: str) -> dict:
    readout = cell_input.read_file(cells_path, cell_input.read_cells, "cells")
    nx, ny = readout.header["nx"], readout.header["ny"]
    pedestal = cell_input.read_file(pedestal_path, cell_input.read_payload, "pedestal payload")
    if pedestal.step != "pedestal":
        raise Refused("the pedestal payload is not a pedestal step")
    if gain_path is None:
        nominal_values = [1.0] * (nx * ny)
    else:
        stage1 = cell_input.read_file(gain_path, gain_payload.read_gain, "gain payload")
        if stage1.operation != "multiply" or stage1.derived_against != (pedestal.identity,):
            raise Refused("the harness's gain payload must multiply and be derived against the pedestal payload given")
        nominal_values = [float(v) for v in stage1.values]
    if any(v != 1.0 for v in nominal_values):
        raise Refused("a divide-role equivalent of a multiplying gain is exact only for gain 1; this fixture's gain is 1")
    lattice = changed_channels(nx, ny)
    contents = {}
    for operation, source in (("multiply", NOMINAL_SOURCE), ("divide", DIVIDE_SOURCE)):
        nominal = gain_payload.payload_bytes(operation, nominal_values, nx, ny, "nominal", source, derived_against=[pedestal.identity])
        values = gain_payload.read(nominal).values
        contents[f"nominal-{operation}"] = nominal
        contents[f"derived-{operation}"] = gain_payload.derive(nominal, {c: float(values[c]) * CHANGE_FACTOR for c in lattice},
                                                                DERIVED_SOURCE)
    other_nx, other_ny = (nx // 2, ny * 2) if nx % 2 == 0 else (nx * 2, ny // 2)
    contents["other-map"] = gain_payload.payload_bytes("multiply", 1.0, other_nx, other_ny, "nominal",
                                                       f"refusal case: a {other_nx} x {other_ny} channel map, same channel count",
                                                       derived_against=[pedestal.identity])
    doc = json.loads(contents["derived-multiply"])
    doc["gains"][-1][0] = nx * ny
    contents["unknown-channel"] = (json.dumps(doc, sort_keys=True, indent=1) + "\n").encode("utf-8")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, content in contents.items():
        path = out_dir / f"{stem}.{key}.gain.json"
        write_new(path, content)
        files[key] = {"path": str(path), "sha256": hashlib.sha256(content).hexdigest()}
    return {"files": files, "changed_channels": lattice, "factor": CHANGE_FACTOR}


def record_text(header: dict, records: list) -> bytes:
    lines = [json.dumps(header, sort_keys=True, allow_nan=False)] + [json.dumps(r, sort_keys=True, allow_nan=False) for r in records]
    lines.append(json.dumps({"end": header["format"], "events": len(records)}, sort_keys=True))
    return ("\n".join(lines) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    pay = sub.add_parser("payloads", help="write the nominal and derived gain payloads of both roles and two refusal cases")
    pay.add_argument("--cells", required=True)
    pay.add_argument("--pedestal-payload", required=True)
    pay.add_argument("--gain-payload", help="the harness's calo-calibration-payload/1 gain; default gain 1 on every channel")
    pay.add_argument("--out-dir", required=True)
    pay.add_argument("--stem", required=True)
    fix = sub.add_parser("fixed-membership", help="CAI-T08-1")
    rer = sub.add_parser("rereco", help="CAI-T08-2")
    for p in (fix, rer):
        p.add_argument("--old-gain", required=True, help="the gain payload the nominal product consumed")
        p.add_argument("--new-gain", required=True, help="the payload derived from it")
        p.add_argument("--out", required=True, help="the record to write; never an existing file")
        p.add_argument("--label", required=True)
        p.add_argument("--configuration", help="calo-cluster-configuration/1; default the t08-grid/1 configuration")
    fix.add_argument("--product", required=True)
    fix.add_argument("--min-asserted", type=int, default=MIN_ASSERTED)
    fix.add_argument("--plant-fraction-defect", action="store_true")
    rer.add_argument("--nominal", required=True)
    rer.add_argument("--changed", required=True)
    args = ap.parse_args(argv)
    try:
        if args.operation == "payloads":
            written = write_payloads(args.cells, args.pedestal_payload, args.gain_payload, args.out_dir, args.stem)
            print(json.dumps({"status": "ok", **written}, sort_keys=True))
            return 0
        out = Path(args.out)
        if out.exists():
            raise Refused(f"{out} exists: a record is never overwritten")
        cfg = configuration.load(args.configuration)
        old_gain = cell_input.read_file(args.old_gain, gain_payload.read_gain, "old gain payload")
        new_gain = cell_input.read_file(args.new_gain, gain_payload.read_gain, "new gain payload")
        gain_payload.check_derived(new_gain, old_gain)
        common = {"label": args.label, "old_gain": payload_summary(old_gain), "new_gain": payload_summary(new_gain)}
        if args.operation == "fixed-membership":
            read = product.read_product(args.product)
            check_configuration(read.header, cfg)
            outcome = assess(read, old_gain, new_gain, cfg, args.label, args.min_asserted, args.plant_fraction_defect)
            header = {"format": FIXED_FORMAT, **common,
                      "product": {"product_id": read.header["product_id"], "format": read.header["format"], "sha256": file_sha256(args.product),
                                  "chain": read.header["chain"]},
                      "rule": {"changed": f"gain x {CHANGE_FACTOR} on ix % {LATTICE_STEP} == {LATTICE_OFFSET} and iy % {LATTICE_STEP} == "
                                          f"{LATTICE_OFFSET}", "well_above": f"min(E_old, E_new) >= {WELL_ABOVE_FACTOR:g} T_c",
                               "tolerance": f"|change - formula| <= {TOLERANCE:g} max(sum f |E_old|, sum f |E_new|, 1 MeV)",
                               "min_asserted": args.min_asserted, "planted_control": bool(args.plant_fraction_defect)},
                      "result": "PASS" if outcome.passed else "FAIL"}
            write_new(out, record_text(header, outcome.records))
            print("\n".join(outcome.lines))
            return 0 if outcome.passed else 1
        nominal, changed = product.read_product(args.nominal), product.read_product(args.changed)
        if len(nominal.events) != len(changed.events):
            raise Refused("the two products hold different event counts")
        lines, records = rereco(nominal, changed, old_gain, new_gain, cfg, args.label)
        header = {"format": REREC_FORMAT, **common,
                  "nominal": {"product_id": nominal.header["product_id"], "format": nominal.header["format"], "sha256": file_sha256(args.nominal)},
                  "changed": {"product_id": changed.header["product_id"], "format": changed.header["format"], "sha256": file_sha256(args.changed)}}
        write_new(out, record_text(header, records))
        print("\n".join(lines))
        return 0
    except (Refused, cell_input.InputError, product.ProductError, configuration.ConfigurationError) as exc:
        print(f"REFUSED {getattr(args, 'label', args.operation)} {args.operation}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
