#!/usr/bin/env python3
"""T10 stage 2 checks on seeded synthetic data (t10-timing-stage-plan.md section 6; tolerances in section 6.2). Scoring side: the
recipe never imports it. Synthetic data only; no PID, dE/dx, calibration or counting quality claim.

Operations:
  pid    --seed S --events N --out DIR [--plant P]   PID-T10a to d and R35-6: per event, a few tracks of two species hypotheses
         (fixture masses 0.14 and 0.94 GeV, not a source) through stage 1's chain; items hypotheses, shared-clock, wrong-bunch, path,
         missing-input, dedx (per event) and migration (over the run). Plants: llr-as-probability, clock-not-cancelled,
         purity-as-efficiency, zero-filled-missing, dedx-without-samples.
  a37    --t07-log PATH --expected-sha256 H --out DIR [--seed S] [--plant P]   A37-T10: items gxe, witness (T07's run record, read,
         its SHA-256 pinned in t10_a37.py; --expected-sha256 may only repeat it), card. Plants: holdout-as-proof, placeholder-witness,
         no-constraint, validation-is-constraint.
  counts --seed S --events N --out DIR [--plant P]   W6-T10: native counter channels through timing_recipe.counts; items contract
         (the T06 reader accepts the product) and recompute (counts, exposures and rates recomputed here). Plants: absent-as-zero,
         run-time-denominator.
With a plant it prints "PLANT <name> item <item> FAIL in <n> of <N> events" (or "... FAIL" for a run-level item).
Exit codes (core/status.py): 0 every item passed; 1 an item failed; 2 a rejected argument (an existing output, a missing log, an
event count below 1); 3 incomplete: the recipe cannot be imported, the record cannot be written, the recipe rejects the tool's own
generated fixture, or any other error (never read as a negative verdict).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # before any plugin or sibling import (tests/skills/test_no_bytecode.py)

import argparse  # noqa: E402
import copy  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
for _path in (HERE.parent, HERE.parents[3], HERE):     # the adapter assets, the plugin root (contracts), this folder
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

try:
    import numpy  # noqa: E402
    from timing_recipe import RECIPE, counts, dedx, event_time, method_card, pid, time_chain, timing_payload  # noqa: E402
    import t10_a37  # noqa: E402
except ImportError as _import_error:  # pragma: no cover - exercised only with a broken tree
    print(json.dumps({"status": "incomplete", "reason": f"cannot import the recipe: {_import_error}"}))
    sys.exit(3)

TIME_TOL = 1e-12
REL_TOL = 1e-12
LOG_LIKELIHOOD_TOL = 1e-12
SPECIES = [{"name": "hypothesis-a", "mass_gev": 0.14}, {"name": "hypothesis-b", "mass_gev": 0.94}]
SIGMA_T = 0.1
WORKING_POINT = {"select": "hypothesis-b", "over": "hypothesis-a", "threshold": 0.0}
COMPOSITIONS = ({"hypothesis-a": 0.5, "hypothesis-b": 0.5}, {"hypothesis-a": 0.95, "hypothesis-b": 0.05})
CLOCK_SHIFT_NS, BUNCH_NS, PATH_EPSILON = 0.25, 2.0, 0.01
NORMALIZATION = {"value_mev_per_cm": 3.0, "source": "fixture reference value (a MIP most probable value in a calibration)"}
TRUNCATION = 0.3
SOURCE = "T10 stage 2 synthetic fixture constants, seeded; no measurement (R31)"
PLANTS = {"pid": {"llr-as-probability": "hypotheses", "clock-not-cancelled": "shared-clock", "purity-as-efficiency": "migration",
                  "zero-filled-missing": "missing-input", "dedx-without-samples": "dedx"},
          "a37": {"holdout-as-proof": "gxe", "placeholder-witness": "witness", "no-constraint": "card", "validation-is-constraint": "card"},
          "counts": {"absent-as-zero": "contract", "run-time-denominator": "contract"}}


class Item:
    def __init__(self):
        self.checks, self.failed, self.largest = 0, 0, 0.0

    def near(self, observed, expected, tolerance):
        deviation = abs(observed - expected)
        self.checks += 1
        self.largest = max(self.largest, deviation)
        if not deviation <= tolerance:
            self.failed += 1

    def holds(self, condition):
        self.checks += 1
        if not condition:
            self.failed += 1

    @property
    def verdict(self):
        return "PASS" if self.checks and not self.failed else "FAIL"

    def report(self):
        return {"verdict": self.verdict, "checks": self.checks, "failed": self.failed, "largest_deviation": self.largest}


def _tof_change(after_record, after_start, after_event, before_record, before_start, before_event):
    """TOF(after) - TOF(before), or None when the recipe refuses a start against its event (fix round 1, I1)."""
    try:
        return (event_time.tof(after_record, after_start, after_event)["tof_ns"]
                - event_time.tof(before_record, before_start, before_event)["tof_ns"])
    except timing_payload.InputError:
        return None


def _rejects(check, record) -> bool:
    try:
        check(record)
    except timing_payload.InputError:
        return True
    return False


# --- pid ------------------------------------------------------------------------------------------------------------------

def _pid_event(rng):
    n = int(rng.integers(3, 7))
    offsets, walks, speeds = rng.uniform(-5, 5, n), rng.uniform(0.2, 1.0, n), rng.uniform(10, 20, n)
    t0 = float(rng.uniform(0, 5))
    tracks = []
    for c in range(n):
        species = SPECIES[int(rng.integers(0, 2))]
        p = float(rng.uniform(1.5, 4.0))       # above 1.5 GeV the beta = 1 internal event time keeps every TOF positive
        path = float(rng.uniform(200, 500))
        amplitude, position = float(rng.uniform(10, 500)), float(rng.uniform(0, 100))
        beta = p / math.sqrt(p * p + species["mass_gev"] ** 2)
        hit_time = t0 + path / (event_time.SPEED_OF_LIGHT_CM_PER_NS * beta) + float(rng.normal(0, SIGMA_T))
        raw = hit_time + position / speeds[c] + walks[c] / math.sqrt(amplitude) + offsets[c]
        layers = int(rng.integers(2, 9))
        samples = [{"sample_id": i, "layer": i, "deposit_mev": float(rng.lognormal(math.log(0.3), 0.3)),
                    "path_length_cm": float(rng.uniform(0.09, 0.15)), "saturated": bool(rng.random() < 0.1)} for i in range(layers)]
        tracks.append({"hit": {"hit_id": 100 + c, "track_id": c, "counter": c, "raw_time_ns": raw, "amplitude": amplitude,
                               "position_cm": position, "path_length_cm": path},
                       "species": species["name"], "momentum": p, "samples": samples})
    raw_weights = rng.uniform(0.5, 1.5, n)
    weights = {100 + c: float(w) for c, w in enumerate(raw_weights / raw_weights.sum())}
    payload_values = {"offset": offsets, "walk": walks, "propagation": speeds}
    return {"tracks": tracks, "weights": weights, "payload_values": payload_values, "external_t0": t0, "missing_track": n}


def _payloads(values: dict, shift: float = 0.0) -> dict:
    return {step: timing_payload.read(timing_payload.payload_bytes(step, [v + (shift if step == "offset" else 0.0) for v in vals],
                                                                   len(vals), 1, "nominal", SOURCE))
            for step, vals in values.items()}


def _expected_dedx(samples):
    values = sorted((s["deposit_mev"] / s["path_length_cm"], s["sample_id"], s["saturated"]) for s in samples)
    drop = math.floor(TRUNCATION * len(samples))
    kept = values[:len(samples) - drop]
    flags = sorted(({"few-samples"} if len(samples) < 4 else set()) | ({"saturated-in-kept"} if any(k[2] for k in kept) else set()))
    return sorted(k[1] for k in kept), math.fsum(k[0] for k in kept) / len(kept), flags


def run_pid(seed: int, events: int, plant: str | None) -> dict:
    rng = numpy.random.default_rng(seed)
    names = ("hypotheses", "shared-clock", "wrong-bunch", "path", "missing-input", "dedx")
    totals = {name: Item() for name in names}
    failed_events = {name: 0 for name in names}
    true_labels, selected_labels, within, outside, out = [], [], [], 0, []
    for index in range(events):
        event = _pid_event(rng)
        items = {name: Item() for name in names}
        hits = [t["hit"] for t in event["tracks"]]
        before = time_chain.correct(hits, _payloads(event["payload_values"]))
        after = time_chain.correct(hits, _payloads(event["payload_values"], CLOCK_SHIFT_NS))
        start = event_time.external(event["external_t0"], "fixture external start time")
        late = event_time.external(event["external_t0"] + BUNCH_NS, "fixture start time one bunch late (wrong bunch)")
        common_b = event_time.common_linear(before, event["weights"], 1.0)
        common_a = common_b if plant == "clock-not-cancelled" else event_time.common_linear(after, event["weights"], 1.0)
        for track, rb, ra in zip(event["tracks"], before, after):
            # shared clock: external -delta, common and leave-one-out 0
            items["shared-clock"].near(event_time.tof(ra, start, after)["tof_ns"] - event_time.tof(rb, start, before)["tof_ns"],
                                       -CLOCK_SHIFT_NS, TIME_TOL)
            lb = event_time.leave_one_out(before, event["weights"], 1.0, track_id=rb["track_id"])
            la = lb if plant == "clock-not-cancelled" else event_time.leave_one_out(after, event["weights"], 1.0, track_id=ra["track_id"])
            for start_b, start_a in ((common_b, common_a), (lb, la)):
                change = _tof_change(ra, start_a, after, rb, start_b, before)
                if change is None:          # a stale internal start is refused against its event (fix round 1, I1): the item fails
                    items["shared-clock"].holds(False)
                else:
                    items["shared-clock"].near(change, 0.0, TIME_TOL)
            # hypotheses
            momentum = {"value_gev": track["momentum"], "source": "fixture value (the T07 path stays open: R35-X)",
                        "unconstrained_modes": ["mode.curvature-offset"]}
            tof = event_time.tof(rb, start, before)
            record = pid.hypotheses(tof, momentum, SPECIES, SIGMA_T, WORKING_POINT)
            if plant == "llr-as-probability":
                total = sum(math.exp(h["log_likelihood"]) for h in record["hypotheses"])
                record["probabilities"] = {h["name"]: math.exp(h["log_likelihood"]) / total for h in record["hypotheses"]}
            items["hypotheses"].holds(not _rejects(pid.check, record))
            for h, s in zip(record["hypotheses"], SPECIES):
                beta = track["momentum"] / math.sqrt(track["momentum"] ** 2 + s["mass_gev"] ** 2)
                t_pred = tof["path_length_cm"] / (event_time.SPEED_OF_LIGHT_CM_PER_NS * beta)
                r = tof["tof_ns"] - t_pred
                items["hypotheses"].near(h["t_pred_ns"], t_pred, TIME_TOL)
                items["hypotheses"].near(h["log_likelihood"], -r * r / (2 * SIGMA_T ** 2) - math.log(SIGMA_T * math.sqrt(2 * math.pi)), LOG_LIKELIHOOD_TOL)
            items["hypotheses"].holds(all(x["meaning"] == pid.LIKELIHOOD_RATIO_MEANING for x in record["llr"]))
            priors = pid.hypotheses(tof, momentum, SPECIES, SIGMA_T, WORKING_POINT, priors={"hypothesis-a": 0.7, "hypothesis-b": 0.3})
            items["hypotheses"].near(sum(priors["probabilities"].values()), 1.0, 1e-12)
            true_labels.append(track["species"])
            selected_labels.append("hypothesis-b" if record["selected"] else "hypothesis-a")
            within.append(record["selected_within_support"])
            items["hypotheses"].holds(record["selected_within_support"] == record["support"][0]["within_support"])
            outside += not record["support"][0]["within_support"]
            # wrong bunch and wrong path
            wrong = pid.hypotheses(event_time.tof(rb, late, before), momentum, SPECIES, SIGMA_T, WORKING_POINT)
            path = tof["path_length_cm"] * (1 + PATH_EPSILON)
            longer = pid.hypotheses(dict(tof, path_length_cm=path, beta=path / (event_time.SPEED_OF_LIGHT_CM_PER_NS * tof["tof_ns"])),
                                    momentum, SPECIES, SIGMA_T, WORKING_POINT)
            for h, w, g in zip(record["hypotheses"], wrong["hypotheses"], longer["hypotheses"]):
                items["wrong-bunch"].near(w["residual_ns"] - h["residual_ns"], -BUNCH_NS, TIME_TOL)
                items["path"].near(g["t_pred_ns"], (1 + PATH_EPSILON) * h["t_pred_ns"], REL_TOL * h["t_pred_ns"])
                items["path"].near(g["residual_ns"] - h["residual_ns"], -PATH_EPSILON * h["t_pred_ns"], TIME_TOL)
            # dE/dx
            measured = dedx.measure(track["samples"], TRUNCATION, NORMALIZATION, track_id=rb["track_id"])
            if plant == "dedx-without-samples":
                measured["samples"] = []
            items["dedx"].holds(not _rejects(dedx.check, measured))
            kept, mean, flags = _expected_dedx(track["samples"])
            items["dedx"].holds(measured["kept"] == kept and measured["flags"] == flags)
            items["dedx"].near(measured["truncated_mean_mev_per_cm"], mean, REL_TOL * mean)
        # missing input: one more track without a TOF
        missing = pid.missing(None, event["missing_track"], "no timing hit on this track (fixture)")
        if plant == "zero-filled-missing":
            missing.update({"tof_ns": 0.0, "path_length_cm": 0.0, "llr": []})
        items["missing-input"].holds(not _rejects(pid.check, missing) and missing["status"] == "missing-input")
        for name in names:
            totals[name].checks += items[name].checks
            totals[name].failed += items[name].failed
            totals[name].largest = max(totals[name].largest, items[name].largest)
            failed_events[name] += items[name].verdict == "FAIL"
        out.append({"event": index, "items": {name: items[name].report() for name in names}})
        print(f"EVENT {index} " + " ".join(f"{name} {items[name].verdict}" for name in names))
    # migration over the run
    migration = Item()
    table = pid.migration(true_labels, selected_labels, [s["name"] for s in SPECIES])
    for a in table["counts"]:
        n_true = sum(1 for t in true_labels if t == a)
        for b, n in table["counts"][a].items():
            n_ab = sum(1 for t, s in zip(true_labels, selected_labels) if t == a and s == b)
            migration.holds(n == n_ab)
            if n_true:
                migration.near(table["p_selected_given_true"][a][b], n_ab / n_true, 1e-15)
    purities = []
    for composition in COMPOSITIONS:
        result = pid.purity(table, composition)
        if plant == "purity-as-efficiency":
            result["p_true_given_selected"] = {b: {a: table["p_selected_given_true"][a][b] for a in table["counts"]} for b in table["counts"]}
        eff = table["p_selected_given_true"]
        for b in table["counts"]:
            total = sum(eff[a][b] * composition[a] for a in table["counts"])
            for a in table["counts"]:
                migration.near(result["p_true_given_selected"][b][a], eff[a][b] * composition[a] / total, 1e-15)
        purities.append(result)
    # migration inside and outside the working-point pair's support, kept apart (fix round 1, M6; BP07 support domains)
    by_support = {}
    for label, keep in (("inside", True), ("outside", False)):
        true_part = [t for t, w in zip(true_labels, within) if w == keep]
        selected_part = [s for s, w in zip(selected_labels, within) if w == keep]
        by_support[label] = {"tracks": len(true_part),
                             "table": pid.migration(true_part, selected_part, [s["name"] for s in SPECIES]) if true_part else None}
        migration.holds(by_support[label]["table"] is None or sum(sum(row.values()) for row in by_support[label]["table"]["counts"].values())
                        == len(true_part))
    report = {name: dict(totals[name].report(), failed_events=failed_events[name]) for name in names}
    report["migration"] = migration.report()
    return {"format": "t10-pid-record/1", "recipe": RECIPE, "status_label": "synthetic", "seed": seed, "plant": plant,
            "fixture": {"species": SPECIES, "sigma_t_ns": SIGMA_T, "working_point": WORKING_POINT, "clock_shift_ns": CLOCK_SHIFT_NS,
                        "bunch_ns": BUNCH_NS, "path_epsilon": PATH_EPSILON, "truncation": TRUNCATION},
            "items": report, "migration": {"table": table, "purity": purities, "outside_support": outside, "tracks": len(true_labels),
                                            "by_support": by_support},
            "events": out}


# --- a37 ------------------------------------------------------------------------------------------------------------------

def run_a37(log_text: str, seed: int, plant: str | None) -> dict:
    rng = numpy.random.default_rng(seed)
    gains = [float(v) for v in rng.uniform(0.5, 2.0, 4)]
    energies = [float(v) for v in rng.uniform(1.0, 20.0, 6)]
    gxe = t10_a37.gxe_check(gains, energies, gauge=2.0, reference_event=0, plant=plant if plant == "holdout-as-proof" else None)
    witness = t10_a37.witness_check(log_text, plant=plant if plant == "placeholder-witness" else None)
    card = t10_a37.card_check(method_card.load(), plant=plant if plant in ("no-constraint", "validation-is-constraint") else None)
    items = {"gxe": gxe["verdict"], "witness": witness["verdict"], "card": card["verdict"]}
    return {"format": "t10-a37-record/1", "recipe": RECIPE, "status_label": "synthetic", "seed": seed, "plant": plant,
            "items": {k: {"verdict": v} for k, v in items.items()}, "gxe": gxe, "witness": witness, "card": card,
            "note": "A37 here is the g x E identifiability check and T07's run record of the weak mode; no placeholder check is used"}


# --- counts ---------------------------------------------------------------------------------------------------------------

def _counts_event(rng):
    channels = []
    for c in range(int(rng.integers(2, 5))):
        edges = numpy.cumsum(rng.uniform(5, 30, int(rng.integers(3, 6))))
        starts = numpy.concatenate([[0.0], edges[:-1]])
        intervals = []
        for i, (start, end) in enumerate(zip(starts, edges)):
            read = i == 0 or not (i == 1 or rng.random() < 0.15)    # interval 0 read (a valid zero), interval 1 never
            intervals.append({"interval_id": f"ch{c}-i{i}", "start_s": float(start), "end_s": float(end),
                              "dead_s": float(rng.uniform(0, 0.2) * (end - start)), "read": read})
        pulses = []
        for i, interval in enumerate(intervals):
            if not interval["read"] or i == 0:                       # interval 0 holds no pulse: a valid zero
                continue
            for _ in range(int(rng.poisson(4))):
                pulses.append({"time_s": float(rng.uniform(interval["start_s"], interval["end_s"])),
                               "amplitude": float(rng.uniform(0, 20))})
        channels.append({"channel": f"counter-{c}", "threshold": {"value": float(rng.uniform(2, 10)), "unit": "adc"},
                         "response_ref": f"native:response-counter-{c}", "intervals": intervals, "pulses": pulses})
    return channels


def run_counts(seed: int, events: int, plant: str | None) -> dict:
    rng = numpy.random.default_rng(seed)
    totals = {"contract": Item(), "recompute": Item()}
    failed_events = {"contract": 0, "recompute": 0}
    all_codes = set()
    out = []
    for index in range(events):
        channels = _counts_event(rng)
        product, readings = counts.build(channels, f"product.t10-counts-{index}")
        if plant == "absent-as-zero":
            for interval in product["counts"]["intervals"]:
                if interval["presence"] == "absent":
                    interval["count"] = 0
        elif plant == "run-time-denominator":
            for rate in product["counts"]["rates"]:
                rate["denominator"] = {"source": "run-time", **product["counts"]["run_time"]}
        items = {"contract": Item(), "recompute": Item()}
        codes = counts.check(product)
        items["contract"].holds(codes == [])
        by_id = {i["interval_id"]: i for i in product["counts"]["intervals"]}
        for channel in channels:
            total = 0
            exposure = math.fsum(i["end_s"] - i["start_s"] - i["dead_s"] for i in channel["intervals"] if i["read"])
            for interval in channel["intervals"]:
                entry = by_id[interval["interval_id"]]
                if interval["read"]:
                    n = sum(1 for p in channel["pulses"] if interval["start_s"] <= p["time_s"] < interval["end_s"]
                            and p["amplitude"] >= channel["threshold"]["value"])
                    items["recompute"].holds(entry["presence"] == "present" and entry.get("count") == n)
                    total += n
                else:
                    items["recompute"].holds(entry["presence"] == "absent")
            got = readings[channel["channel"]]
            items["recompute"].holds(got["count"] == total and got["valid_exposure_s"] == exposure and got["rate_per_s"] == total / exposure)
        for name in items:
            totals[name].checks += items[name].checks
            totals[name].failed += items[name].failed
            failed_events[name] += items[name].verdict == "FAIL"
        all_codes.update(codes)
        out.append({"event": index, "codes": codes, "product": product, "readings": readings,
                    "items": {name: items[name].report() for name in items}})
        print(f"EVENT {index} contract {items['contract'].verdict} recompute {items['recompute'].verdict}")
    return {"format": "t10-counts-record/1", "recipe": RECIPE, "status_label": "synthetic", "seed": seed, "plant": plant,
            "items": {name: dict(totals[name].report(), failed_events=failed_events[name]) for name in totals},
            "contract_codes": sorted(all_codes),
            "gaps": {"A20": "no coded or response image", "A21": "no multisite Compton", "A22": "no acoustic and optical association",
                     "A23": "no prompt-delayed counts", "A24": "no energy-resolving sensor"},
            "events": out}


# --- command line ---------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="T10 stage 2 checks on seeded synthetic data (t10-timing-stage-plan.md section 6).")
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("pid", "counts"):
        p = sub.add_parser(name)
        p.add_argument("--seed", type=int, required=True)
        p.add_argument("--events", type=int, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--plant", choices=sorted(PLANTS[name]))
    p = sub.add_parser("a37")
    p.add_argument("--t07-log", type=Path, required=True)
    p.add_argument("--expected-sha256", help="optional: if given, it must repeat the pinned SHA-256 of T07's record")
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--plant", choices=sorted(PLANTS["a37"]))
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "rejected", "reason": f"{args.out} exists: a record is never overwritten"}))
        return 2
    if args.operation in ("pid", "counts") and args.events < 1:
        print(json.dumps({"status": "rejected", "reason": "--events must be at least 1"}))
        return 2
    if args.operation == "a37":
        if args.expected_sha256 is not None and args.expected_sha256 != t10_a37.T07_LOG_SHA256:
            print(json.dumps({"status": "rejected", "reason": "--expected-sha256 is not the pinned SHA-256 of T07's record"}))
            return 2
        try:
            log_text = args.t07_log.read_text(encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"status": "rejected", "reason": f"cannot read the T07 log: {exc}"}))
            return 2
    try:
        if args.operation == "pid":
            record = run_pid(args.seed, args.events, args.plant)
        elif args.operation == "counts":
            record = run_counts(args.seed, args.events, args.plant)
        else:
            record = run_a37(log_text, args.seed, args.plant)
    except timing_payload.InputError as exc:   # the fixture is the tool's own: a rejection here is not the user's input
        print(json.dumps({"status": "incomplete", "reason": f"the recipe rejected the tool's own generated fixture: {exc}"}))
        return 3
    except Exception as exc:  # noqa: BLE001 - any other error is a crash, never a negative verdict
        print(json.dumps({"status": "incomplete", "reason": f"{type(exc).__name__}: {exc}"}))
        return 3
    try:
        args.out.mkdir(parents=True)
        (args.out / f"t10-{args.operation}.json").write_text(json.dumps(record, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "incomplete", "reason": f"cannot write the record: {exc}"}))
        return 3
    failed = sorted(name for name, item in record["items"].items() if item["verdict"] != "PASS")
    if args.plant:
        item = PLANTS[args.operation][args.plant]
        verdict = record["items"][item]["verdict"]
        if "failed_events" in record["items"][item]:
            n = len(record["events"])
            print(f"PLANT {args.plant} item {item} {verdict} in {record['items'][item]['failed_events']} of {n} events")
        else:
            print(f"PLANT {args.plant} item {item} {verdict}")
        if args.operation == "counts":
            print(f"PLANT-CODES {','.join(record['contract_codes']) or 'none'}")
    print(f"RESULT t10-{args.operation} {'FAIL' if failed else 'PASS'} failed items {','.join(failed) or 'none'} plant {args.plant or 'none'}")
    print(json.dumps({"status": "failed" if failed else "ok", "status_label": "synthetic", "failed_items": failed,
                      "record": str(args.out / f"t10-{args.operation}.json")}, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
