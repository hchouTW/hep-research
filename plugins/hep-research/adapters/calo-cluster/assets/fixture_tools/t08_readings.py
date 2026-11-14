#!/usr/bin/env python3
"""Scoring side of T08: development readings of one stratum's calo-cluster-product/1 (or /2) against its t08-truth/1 file.

Development readings only (K09 not frozen, Freeze B not reached): nothing here is compared with a gate of t04-values-v4.md,
and no line is a pass or fail of a quality gate. One check is a gate of this job: the sheet's stop, no cell counted twice
(product.double_count_defects on every event); exit 1 if any event has a defect, exit 2 if the input is refused.

Definitions, from t04-values-v4.md sections 4.2, 5.1, 7 and 7.1, with the scoring choices this code makes:
- Shower energy in an object: sum_c f_kc d_sc over its members, d_sc the truth deposit, noise excluded. A cluster matches the
  shower supplying more than 50 % of the shower energy it holds (the denominator is the sum over showers of that energy).
  Primary: highest share of that shower, then higher cluster energy, then lower index. A primary whose uncertainty status is
  not ok leaves the shower with no primary (section 7.1). Efficiency: showers with a primary over showers.
- Split: showers with more than one matched cluster. Merge: a two-shower event in which both showers give their largest
  energy share to one object; a shower no object holds has no largest share and makes no merge.
- Which sum enters (section 7.1): iso, edge, dead, near and saturation, the event sum, in every event with a non-empty event
  sum; far, the shower's primary object. Position: iso, the largest object; far, the primary object.
- Targets (section 4.2): iso E - b_iso; far E - b_far(E, d); near 2E - b_near(E, d); edge E Phi(t) - b_edge(t); dead
  E (1 - f) - b_dead; saturation sum_c min(E g_c, 400 MeV) - b_sat, with the uncertainty over unclipped cells (section 9.2,
  reported, ungated). Constants and node tables are read from job 7479146's frozen log; b_far and b_near are linear in ln E
  and in d between its nodes, never extrapolated. Pulls below 0.25 GeV have no target and are not formed.
- Statistics (section 5.1): trimmed centre (10 % from each side), sigma_68 (half the central 68.27 % interval), tail
  P(|pull| > 3), mean, rms (the standard deviation about the mean, numpy std, as job 7479146's log prints it); design se
  1.03/sqrt(n) and 0.962/sqrt(n), labelled design.
- Reported, not gated (v4 9.1, 9.2; fix round 1): position pulls of the largest object for edge (a truncated centroid is
  biased by design), dead and saturation; for near, per-shower energy, x and y pulls of each primary against E and the
  truth axis (no closure meaning: v4 9.1).
- Same selection as the response (v4 9.2; scenarios A15, A32, A38): only a product made with the t08-grid/1 configuration file
  (REFERENCE_CONFIGURATION_SHA256) is read; any other configuration, a cheaper variant included, is refused (exit 2).
- Exit codes: 0 no double count; 1 a cell counted twice (the sheet's stop, GATE ... FAIL); 2 the readings refused their input
  (REFUSED line), which is not a double-count verdict.

Usage: t08_readings.py --product P --truth T --reference-log LOG --label LABEL
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from bisect import bisect_right
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE_LOG_SHA256 = "325e070b5a929a8d77d2cb88d00767e2ab5daa985a2d567c096486249835d0c8"
# The configuration whose selection job 7479146's constants b were made with (T_c 0.6, T_s 10 MeV, W 1, q and sigma_n 0.2 MeV,
# 30 iterations: round5/calc-t08-reference.py, the same constants as t08-grid-1.configuration.json, compared in the stage 4 job).
# A product of any other configuration file is refused: its selection is not the one the targets carry (v4 9.2, "same selection
# as the response"; scenarios A15, A32 and A38, D2 stage 4).
REFERENCE_CONFIGURATION_SHA256 = "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723"
GATED_FROM_MEV = 250.0
CLIP_MEV = 400.0
Q_MEV, SIGMA_N_MEV = 0.2, 0.2   # t04-values-v4.md section 4.2, for the saturation reading's unclipped-cell uncertainty


class ReadingError(ValueError):
    """Refused input of the readings."""


# --- the reference constants of job 7479146 ----------------------------------------------------------------------------

def parse_reference(text: str) -> dict:
    ref = {"far": {}, "near": {}, "edge": {}}
    node = None
    for line in text.splitlines():
        m = re.match(r"^CONST b_(iso|dead|sat) ([-0-9.]+)$", line)
        if m:
            ref[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"^CONST b_edge\(([0-9.]+)\) ([-0-9.]+)$", line)
        if m:
            ref["edge"][float(m.group(1))] = float(m.group(2))
            continue
        m = re.match(r"^pair d +([0-9.]+) E +([0-9.]+) .* b_near +([-0-9.]+) se", line)
        if m:
            node = (float(m.group(2)), float(m.group(1)))
            ref["near"][node] = float(m.group(3))
            continue
        m = re.match(r"^ +b_far +([-0-9.]+) se", line)
        if m and node is not None:
            ref["far"][node] = float(m.group(1))
    for key in ("iso", "dead", "sat"):
        if key not in ref:
            raise ReadingError(f"reference log has no CONST b_{key}")
    if sorted(ref["edge"]) != [0.5, 1.0, 1.5, 2.0]:
        raise ReadingError("reference log lacks the four b_edge constants")
    return ref


def bilinear(table: dict, energy: float, d: float) -> float:
    """Linear in ln E and in d on a full rectangle of nodes; refuses to extrapolate."""
    es = sorted({e for e, _ in table})
    ds = sorted({x for _, x in table})
    if not (es[0] <= energy <= es[-1] and ds[0] <= d <= ds[-1]):
        raise ReadingError(f"E {energy} MeV, d {d} lies outside the nodes: no extrapolation")
    i = min(bisect_right(es, energy) - 1, len(es) - 2)
    j = min(bisect_right(ds, d) - 1, len(ds) - 2)
    e0, e1, d0, d1 = es[i], es[i + 1], ds[j], ds[j + 1]
    try:
        v00, v01, v10, v11 = table[(e0, d0)], table[(e0, d1)], table[(e1, d0)], table[(e1, d1)]
    except KeyError:
        raise ReadingError(f"node rectangle around E {energy}, d {d} is incomplete") from None
    u = (math.log(energy) - math.log(e0)) / (math.log(e1) - math.log(e0))
    w = (d - d0) / (d1 - d0)
    return (1 - u) * (1 - w) * v00 + (1 - u) * w * v01 + u * (1 - w) * v10 + u * w * v11


def far_table(ref: dict) -> dict:
    """b_far on the gated nodes, d from 3 (the far stratum's lower edge)."""
    return {k: v for k, v in ref["far"].items() if k[1] >= 3.0}


def near_table(ref: dict) -> dict:
    return {k: v for k, v in ref["near"].items() if k[1] <= 3.0}


# --- statistics -----------------------------------------------------------------------------------------------------

def summary(pulls) -> str:
    import numpy
    from scipy import stats
    p = numpy.asarray(pulls, dtype=float)
    n = p.size
    if n == 0:
        return "n 0"
    centre = float(stats.trim_mean(p, 0.1))
    lo, hi = numpy.quantile(p, [0.5 - 0.6827 / 2, 0.5 + 0.6827 / 2])
    s68 = float((hi - lo) / 2)
    tail = float(numpy.mean(numpy.abs(p) > 3))
    return (f"n {n} centre {centre:+.4f} s68 {s68:.4f} tail {tail:.5f} mean {float(p.mean()):+.4f} "
            f"rms {float(p.std()):.4f} design-se centre {1.03 / math.sqrt(n):.4f} s68 {0.962 / math.sqrt(n):.4f}")


# --- matching -------------------------------------------------------------------------------------------------------

def shower_energies(event: dict, deposit, n_showers: int):
    """E[s][k]: the truth energy of shower s in object k (sum_c f_kc d_sc)."""
    flat = deposit.reshape(deposit.shape[0], -1)
    out = [[0.0] * len(event["objects"]) for _ in range(n_showers)]
    for k, cluster in enumerate(event["objects"]):
        for channel, fraction in cluster["members"]:
            for s in range(n_showers):
                out[s][k] += fraction * flat[s, channel]
    return out


def match_event(event: dict, deposit, n_showers: int) -> dict:
    energies = shower_energies(event, deposit, n_showers)
    objects = event["objects"]
    matched = [[] for _ in range(n_showers)]
    for k in range(len(objects)):
        held = sum(energies[s][k] for s in range(n_showers))
        for s in range(n_showers):
            if held > 0 and energies[s][k] > 0.5 * held:
                matched[s].append(k)
    primary = []
    for s in range(n_showers):
        if not matched[s]:
            primary.append(None)
            continue
        best = sorted(matched[s], key=lambda k: (-energies[s][k], -objects[k]["energy"], k))[0]
        primary.append(best if objects[best]["uncertainty_status"] == "ok" else None)
    largest = []
    for s in range(n_showers):
        shares = energies[s]
        largest.append(max(range(len(shares)), key=lambda k: (shares[k], -k)) if shares and max(shares) > 0 else None)
    merged = n_showers == 2 and largest[0] is not None and largest[0] == largest[1]
    return {"matched": matched, "primary": primary, "merged": merged}


# --- one stratum -----------------------------------------------------------------------------------------------------

PULL_KEYS = ("energy", "x", "y", "near_shower_energy", "near_shower_x", "near_shower_y")


def event_pulls(ev: dict, fixture: str, separation, i: int, truth: dict, ref: dict, match: dict) -> dict:
    """The pulls one event contributes, by key; empty below 0.25 GeV. Edge energy pulls are keyed ("edge", t)."""
    from scipy import special
    out = {}

    def add(key, value):
        out.setdefault(key, []).append(value)

    energy = float(truth["energy_mev"][i])
    if energy < GATED_FROM_MEV:
        return out
    objects = ev["objects"]
    total_sum, sigma = ev["event_sum"]["energy"], ev["event_sum"]["sigma"]
    has_sum = ev["event_sum"]["cells"] > 0 and sigma > 0

    def largest_position(s=0):
        if not objects:
            return
        k = max(range(len(objects)), key=lambda j: (objects[j]["energy"], -j))
        cluster = objects[k]
        if cluster["uncertainty_status"] == "ok":
            sx, sy = truth["showers"][i, s]
            add("x", (cluster["x"] - sx) / cluster["sigma_x"])
            add("y", (cluster["y"] - sy) / cluster["sigma_y"])

    if fixture == "main" and separation == "iso":
        if match["primary"][0] is not None and has_sum:
            add("energy", (total_sum - (energy - ref["iso"])) / sigma)
            largest_position()
    elif fixture == "main" and separation == "far":
        target = energy - bilinear(far_table(ref), energy, float(truth["d"][i]))
        for s, k in enumerate(match["primary"]):
            if k is None:
                continue
            cluster = objects[k]
            sx, sy = truth["showers"][i, s]
            add("energy", (cluster["energy"] - target) / cluster["sigma_energy"])
            add("x", (cluster["x"] - sx) / cluster["sigma_x"])
            add("y", (cluster["y"] - sy) / cluster["sigma_y"])
    elif fixture == "main" and separation == "near":
        if has_sum:
            add("energy", (total_sum - (2 * energy - bilinear(near_table(ref), energy, float(truth["d"][i])))) / sigma)
        for s, k in enumerate(match["primary"]):
            if k is None:
                continue
            cluster = objects[k]
            sx, sy = truth["showers"][i, s]
            add("near_shower_energy", (cluster["energy"] - energy) / cluster["sigma_energy"])
            add("near_shower_x", (cluster["x"] - sx) / cluster["sigma_x"])
            add("near_shower_y", (cluster["y"] - sy) / cluster["sigma_y"])
    elif fixture == "edge":
        if has_sum:
            t = float(truth["t"][i])
            add(("edge", t), (total_sum - (energy * float(special.ndtr(t)) - ref["edge"][t])) / sigma)
        largest_position()
    elif fixture == "dead":
        if has_sum:
            add("energy", (total_sum - (energy * (1.0 - float(truth["f_dead"][i])) - ref["dead"])) / sigma)
        largest_position()
    elif fixture == "saturation":
        if has_sum:
            unclipped = [row[5] for row in ev["cells"] if row[6] == 0]
            s_u = math.fsum(unclipped)
            sigma_u = math.sqrt(Q_MEV * max(s_u, 0.0) + len(unclipped) * SIGMA_N_MEV ** 2)
            if sigma_u > 0:
                add("energy", (total_sum - (float(truth["clip_reference_mev"][i]) - ref["sat"])) / sigma_u)
        largest_position()
    return out


def readings(product, truth_header: dict, truth: dict, ref: dict, label: str) -> tuple[list, int]:
    """Lines to print and the count of events with a double-count defect."""
    sys.path.insert(0, str(HERE.parent))
    from calo_recipe import product as product_format

    events = product.events
    if product.header["input"]["sha256"] != truth_header["cells_sha256"]:
        raise ReadingError("the product was not made from the cells file this truth file belongs to")
    if len(events) != truth_header["events"]:
        raise ReadingError("product and truth cover different event counts")
    if product.header["configuration"]["sha256"] != REFERENCE_CONFIGURATION_SHA256:
        raise ReadingError(f"the product was made with configuration {product.header['configuration']['sha256']}, not t08-grid/1's "
                           f"{REFERENCE_CONFIGURATION_SHA256}, whose selection job 7479146's reference constants carry: a product of "
                           "another configuration is never scored against them (v4 9.2, same selection as the response)")
    fixture, separation = truth_header["fixture"], truth_header["separation"]
    lines, first = [], []
    defects = 0
    histogram, kinds, statuses, failed = {}, {}, {}, {}
    showers = with_primary = split = merges = two_shower_events = 0
    conservation = 0.0
    pulls = {}
    flagged_objects = lower_bound_sums = 0
    for i, ev in enumerate(events):
        found = product_format.double_count_defects(ev)
        if found:
            defects += 1
            first.extend(f"event {i}: {d}" for d in found[:3])
        n_obj = len(ev["objects"])
        histogram[min(n_obj, 3)] = histogram.get(min(n_obj, 3), 0) + 1
        for cluster in ev["objects"]:
            kinds[cluster["kind"]] = kinds.get(cluster["kind"], 0) + 1
            statuses[cluster["uncertainty_status"]] = statuses.get(cluster["uncertainty_status"], 0) + 1
            flagged_objects += cluster["saturated"]
        for _, failure, _ in product_format.failed_components(ev):
            failed[failure] = failed.get(failure, 0) + 1
        lower_bound_sums += ev["event_sum"]["energy_bound"] == "lower-bound"
        total = ev["clustered_sum"] + ev["unclustered_sum"]
        conservation = max(conservation, abs(total - ev["input_sum"]) / max(abs(ev["input_sum"]), 1.0))
        n_sh = int(truth["n_showers"][i])
        match = match_event(ev, truth["deposit"][i], n_sh)
        showers += n_sh
        with_primary += sum(p is not None for p in match["primary"])
        split += sum(len(m) > 1 for m in match["matched"])
        if n_sh == 2:
            two_shower_events += 1
            merges += match["merged"]
        for key, values in event_pulls(ev, fixture, separation, i, truth, ref, match).items():
            pulls.setdefault(key, []).extend(values)
    n = len(events)
    lines.append(f"READING {label} events {n} objects per event "
                 + " ".join(f"{k if k < 3 else '3+'}:{histogram.get(k, 0)}" for k in range(4))
                 + f" kinds {json.dumps(kinds, sort_keys=True)} uncertainty {json.dumps(statuses, sort_keys=True)}"
                 + f" components without objects {json.dumps(failed, sort_keys=True)}")
    lines.append(f"READING {label} efficiency {with_primary}/{showers} = {with_primary / max(showers, 1):.5f} "
                 f"split {split} merge {merges}/{two_shower_events}")
    lines.append(f"READING {label} conservation largest relative |clustered + unclustered - input| {conservation:.3e}; "
                 f"objects flagged saturated {flagged_objects}, event sums marked lower bound {lower_bound_sums}")
    none = "none formed: below 0.25 GeV no target, or no object"
    if fixture == "edge":
        for t in (0.5, 1.0, 1.5, 2.0):
            lines.append(f"READING {label} energy pull t {t} (event sum, target E Phi(t) - b_edge(t)) {summary(pulls.get(('edge', t), []))}")
        lines.append(f"READING {label} energy pull pooled over t "
                     f"{summary([p for t in (0.5, 1.0, 1.5, 2.0) for p in pulls.get(('edge', t), [])])}")
    else:
        what = {"iso": "event sum, target E - b_iso", "far": "primary object, target E - b_far(E, d)",
                "near": "event sum, target 2E - b_near(E, d)"}.get(separation, "event sum")
        if fixture == "dead":
            what = "event sum, target E (1 - f) - b_dead"
        if fixture == "saturation":
            what = "event sum, target sum min(E g_c, 400) - b_sat, sigma over unclipped cells, ungated (section 9.2)"
        lines.append(f"READING {label} energy pull ({what}) " + (summary(pulls["energy"]) if pulls.get("energy") else none))
    position_note = {("main", "iso"): "largest object", ("main", "far"): "primary object",
                     ("edge", None): "largest object, reported, not gated; a truncated centroid is biased by design (v4 9.2)",
                     ("dead", None): "largest object, reported, not gated (v4 9.2)",
                     ("saturation", None): "largest object, reported, not gated"}
    key = (fixture, separation if fixture == "main" else None)
    if key in position_note:
        for axis in ("x", "y"):
            lines.append(f"READING {label} position pull {axis} ({position_note[key]}) "
                         + (summary(pulls[axis]) if pulls.get(axis) else none))
    if fixture == "main" and separation == "near":
        for name, what in (("near_shower_energy", "energy, target E"), ("near_shower_x", "x"), ("near_shower_y", "y")):
            lines.append(f"READING {label} per-shower {what} pull of primaries, reported, no closure meaning (v4 9.1) "
                         + (summary(pulls[name]) if pulls.get(name) else none))
    verdict = "PASS" if defects == 0 else "FAIL"
    lines.append(f"GATE {label} double-count {verdict}: {defects} of {n} events with a cell counted twice")
    lines.extend(f"DEFECT {label} {d}" for d in first[:10])
    return lines, defects


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--product", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--reference-log", required=True, help="job 7479146's calc-t08-reference.log (SHA-256 checked)")
    ap.add_argument("--label", required=True)
    args = ap.parse_args(argv)
    import hashlib
    sys.path.insert(0, str(HERE.parent))
    sys.path.insert(0, str(HERE))
    from calo_recipe import product as product_format
    import t08_fixture_files
    try:
        log_bytes = Path(args.reference_log).read_bytes()
        if hashlib.sha256(log_bytes).hexdigest() != REFERENCE_LOG_SHA256:
            raise ReadingError("reference log is not job 7479146's frozen log")
        ref = parse_reference(log_bytes.decode("utf-8"))
        product = product_format.read_product(args.product)
        header, truth = t08_fixture_files.read_truth(args.truth)
        lines, defects = readings(product, header, truth, ref, args.label)
    except (OSError, ReadingError, product_format.ProductError, t08_fixture_files.FixtureError) as exc:
        print(f"REFUSED {args.label} the readings refused their input, no double-count verdict: {exc}")
        return 2
    print("\n".join(lines))
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
