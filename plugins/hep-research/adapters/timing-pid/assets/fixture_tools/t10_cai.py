#!/usr/bin/env python3
"""T10's calibration-interface checks of plan R37: CAI-T10-1 (single-ended counters) and CAI-T10-2 (two-ended counters), on the
records of reco.timing.time-chain/1. Scoring side: it builds the changed offset payload, runs the recipe before and after, and
compares the changes with the R37 formulas; the recipe never imports it.

Rules, fixed before any run (t10-timing-stage-plan.md sections 2 and 3). K is the set of hits on the changed channel, Delta t_h the
change of hit h's fully corrected time (0 for h not in K); a track may have several hits, a channel several hits of different
tracks (fix round 1, I1 and M7); R37's formulas are the one-hit case of the general form below.
- The change: one channel's offset raised by the step D = 0.1 ns, then by D/2 = 0.05 ns, each in a payload derived from the
  nominal one (its own identity, derived_from naming the nominal payload).
- CAI-T10-1a: the offset-corrected time of every hit in K changes by -D (1e-12 ns), of every other hit by exactly 0; Delta t_h = -D
  for h in K and exactly 0 otherwise; the offset step appears once and first; every record passes the reader against its payloads
  (a record the reader refuses fails this item).
- CAI-T10-1b (external T_0): a TOF of a hit in K changes by Delta t_h (1e-12 ns) and its beta equals L / (c (TOF_old + Delta t_h))
  (1e-12 relative); every other TOF and beta exactly unchanged.
- CAI-T10-1c (common linear T_0, fixed weights): T_0 by sum_{k in K} w_k Delta t_k, each TOF by Delta t_h minus that (1e-12 ns).
- CAI-T10-1d (per-track leave-one-out, linear, every hit of the track excluded): for track j, T_0^(-j) by sum_{k in K, k not in j}
  w_k^(-j) Delta t_k, each TOF of track j by Delta t_h minus that (1e-12 ns).
- CAI-T10-1e (median T_0): the changes recorded, no assertion (R37: a non-linear estimator).
- CAI-T10-1f: every linear change of 1a to 1d divided by its step agrees between D and D/2 within 4 tol / D; for each hit in K,
  beta's forward-difference error ratio e(D/2) / e(D) is within [0.45, 0.55] with e(D) > 0.
- CAI-T10-2 (derived in the stage plan, not from a source): raising end 0's (end 1's) offset by D moves, for every hit of that
  counter, the mean time and the propagation-corrected time by -D/2 and the position by -vD/2 (+vD/2), its TOF under an external
  T_0 by -D/2; every other counter's values exactly 0; the same step halving (CAI-T10-2f).
Planted defects (--plant), controls that must FAIL their item (SINGLE_PLANTS, TWO_PLANTS). Check side: offset-twice and offset-sign
(the derived payload carries 2D or -D), external-uses-hits, stale-event-time, loo-keeps-own-hit, position-no-half, mean-one-end.
Recipe side (fix round 1, M4; the recipe's own function replaced for the run and restored after it): recipe-offset-twice (the
offset step applies its value twice), recipe-loo-common (the leave-one-out returns the common time), recipe-position-no-half (the
two-ended position without its 1/2).

Operation:
  run --seed S --events N --out DIR [--plant NAME]   N seeded synthetic events, each one single-ended and one two-ended case;
                                                     writes DIR/t10-cai.json (t10-cai-record/1), never over an existing DIR.
With a plant it prints "PLANT name item ID failed in n of N events".
Exit codes (core/status.py): 0 every check passed; 1 a check failed; 2 a rejected argument (the event count, an existing output);
3 incomplete: the recipe cannot be imported, the record cannot be written, the tool's own generated fixture is rejected by the
recipe, or any other error (never read as a negative verdict).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

try:
    from timing_recipe import RECIPE, event_time, time_chain, timing_payload  # noqa: E402
except ImportError as _import_error:  # pragma: no cover - exercised only with a broken tree
    if __name__ == "__main__":
        print(json.dumps({"status": "incomplete", "reason": f"cannot import the recipe: {_import_error}"}))
        sys.exit(3)
    raise

STEP_NS = 0.1
TIME_TOLERANCE_NS = 1e-12
POSITION_TOLERANCE_CM = 1e-10
BETA_RELATIVE_TOLERANCE = 1e-12
HALVING_FACTOR = 4.0
BETA_RATIO_WINDOW = (0.45, 0.55)
RECORD_FORMAT = "t10-cai-record/1"
SINGLE_PLANTS = {"offset-twice": "CAI-T10-1a", "offset-sign": "CAI-T10-1a", "external-uses-hits": "CAI-T10-1b",
                 "stale-event-time": "CAI-T10-1c", "loo-keeps-own-hit": "CAI-T10-1d",
                 "recipe-offset-twice": "CAI-T10-1a", "recipe-loo-common": "CAI-T10-1d"}
TWO_PLANTS = {"position-no-half": "CAI-T10-2", "mean-one-end": "CAI-T10-2", "recipe-position-no-half": "CAI-T10-2"}
# stage 2 fix round 1, I4: the exact failed items of each control, fixed from the rules above before the change. A plant that moves the
# affected TOF other than by -D also breaks beta's forward-difference derivative (1f), which presumes Delta t_k = -D.
# recipe-offset-twice: the reader refuses the records, so 1b to 1d are not formed from them and report FAIL with no checks
# (the stage 1 re-review's R3); corrected after its first run in fix round 1, which had predicted 1a and 1f only.
PLANT_FAILED_ITEMS = {"offset-twice": {"CAI-T10-1a", "CAI-T10-1f"}, "offset-sign": {"CAI-T10-1a", "CAI-T10-1f"},
                      "external-uses-hits": {"CAI-T10-1b", "CAI-T10-1f"}, "stale-event-time": {"CAI-T10-1c"},
                      "loo-keeps-own-hit": {"CAI-T10-1d"}, "recipe-offset-twice": {"CAI-T10-1a", "CAI-T10-1b", "CAI-T10-1c", "CAI-T10-1d", "CAI-T10-1f"},
                      "recipe-loo-common": {"CAI-T10-1d"}, "position-no-half": {"CAI-T10-2"}, "mean-one-end": {"CAI-T10-2"},
                      "recipe-position-no-half": {"CAI-T10-2"}}
CHANGE_SOURCE = "CAI-T10 synthetic offset change (t10-timing-stage-plan.md section 3); no measurement (R31)"
NOMINAL_SOURCE = "T10 timing lane synthetic fixture constants, seeded; no measurement (R31)"


class Item:
    """One checked item: the largest deviation over its checks, against its tolerance."""

    def __init__(self, tolerance: float, unit: str):
        self.tolerance, self.unit, self.largest, self.checks, self.failed = tolerance, unit, 0.0, 0, 0

    def near(self, observed: float, expected: float, tolerance: float | None = None) -> None:
        deviation = abs(observed - expected)
        self.checks += 1
        self.largest = max(self.largest, deviation)
        if not deviation <= (self.tolerance if tolerance is None else tolerance):
            self.failed += 1

    def exact(self, observed: float, expected: float) -> None:
        self.near(observed, expected, 0.0)

    def holds(self, condition: bool) -> None:
        self.checks += 1
        if not condition:
            self.failed += 1

    def report(self) -> dict:
        return {"verdict": "PASS" if self.failed == 0 and self.checks else "FAIL", "checks": self.checks, "failed": self.failed,
                "largest_deviation": self.largest, "tolerance": self.tolerance, "unit": self.unit}


@contextlib.contextmanager
def recipe_plant(plant: str | None):
    """A recipe-side planted defect: the recipe's own function is replaced for the run and restored after it."""
    saved = []

    def patch(module, name, replacement):
        saved.append((module, name, getattr(module, name)))
        setattr(module, name, replacement)

    if plant == "recipe-offset-twice":
        original_step = time_chain._step

        def offset_twice(order, step, payload, channel, before, applied):
            return original_step(order, step, payload, channel, before, 2 * applied if step == "offset" else applied)
        patch(time_chain, "_step", offset_twice)
    elif plant == "recipe-loo-common":
        common = event_time.common_linear
        patch(event_time, "leave_one_out", lambda records, weights, beta_hypothesis, track_id: common(records, weights, beta_hypothesis))
    elif plant == "recipe-position-no-half":
        original_propagation = time_chain._propagation

        def no_half(payload_id, speed, length, times):
            out = original_propagation(payload_id, speed, length, times)
            out["position_cm"] = speed * (times[0] - times[1])
            return out
        patch(time_chain, "_propagation", no_half)
    try:
        yield
    finally:
        for module, name, value in reversed(saved):
            setattr(module, name, value)


def _read_all(contents: dict) -> dict:
    return {step: timing_payload.read(content) for step, content in contents.items()}


def _changed(contents: dict, channel: int, step: float) -> dict:
    nominal = timing_payload.read(contents["offset"])
    value = float(nominal.values[channel]) + step
    return {**contents, "offset": timing_payload.derive(contents["offset"], {channel: value}, CHANGE_SOURCE)}


def _tof_change(after_record, after_start, after_event, before_record, before_start, before_event):
    """TOF(after) - TOF(before), or None when the recipe refuses a start against its event (fix round 1, I1)."""
    try:
        return (event_time.tof(after_record, after_start, after_event)["tof_ns"]
                - event_time.tof(before_record, before_start, before_event)["tof_ns"])
    except event_time.InputError:
        return None


def _by_hit(records: list) -> dict:
    return {r["hit_id"]: r for r in records}


def _reader_accepts(record: dict, payloads: dict) -> bool:
    try:
        time_chain.check_record(record, payloads)
    except time_chain.InputError:
        return False
    return True


def check_single_ended(hits: list, contents: dict, channel: int, delta: float, weights: dict, beta_hypothesis: float,
                       external_t0: float, plant: str | None = None) -> dict:
    """CAI-T10-1a to f on one set of single-ended hits; a planted defect from SINGLE_PLANTS is a control that must FAIL."""
    if plant is not None and plant not in SINGLE_PLANTS:
        raise time_chain.InputError(f"unknown plant {plant!r}")
    with recipe_plant(plant):
        return _check_single_ended(hits, contents, channel, delta, weights, beta_hypothesis, external_t0, plant)


def _check_single_ended(hits, contents, channel, delta, weights, beta_hypothesis, external_t0, plant) -> dict:
    nominal = _read_all(contents)
    if nominal["offset"].ends != 1:
        raise time_chain.InputError("CAI-T10-1 uses single-ended counters only")
    affected = sorted(h["hit_id"] for h in hits if h["counter"] == channel)
    if not affected:
        raise time_chain.InputError(f"CAI-T10-1: channel {channel} holds no hit")
    track = {h["hit_id"]: h["track_id"] for h in hits}
    items = {name: Item(TIME_TOLERANCE_NS, "ns") for name in ("CAI-T10-1a", "CAI-T10-1b", "CAI-T10-1c", "CAI-T10-1d")}
    beta_item = Item(BETA_RELATIVE_TOLERANCE, "relative")
    halving = Item(HALVING_FACTOR * TIME_TOLERANCE_NS / delta, "ns/ns")
    recorded, quotients, beta_errors = {}, {}, {h: [] for h in affected}
    start = event_time.external(external_t0, "fixture external start time")
    before = time_chain.correct(hits, nominal)
    b = _by_hit(before)
    for h in b:
        items["CAI-T10-1a"].holds(_reader_accepts(b[h], nominal))
    for step in (delta, delta / 2):
        applied = {"offset-twice": 2 * step, "offset-sign": -step}.get(plant, step)
        changed_payloads = _read_all(_changed(contents, channel, applied))
        after = time_chain.correct(hits, changed_payloads)
        a = _by_hit(after)
        q = quotients.setdefault(step, {})
        # 1a; a record the reader refuses fails 1a, and the later items of this step are not formed from it
        dt, refused = {}, []
        for h in b:
            offset_change = a[h]["steps"][0]["after_ns"] - b[h]["steps"][0]["after_ns"]
            dt[h] = a[h]["corrected_time_ns"] - b[h]["corrected_time_ns"]
            if h in affected:
                items["CAI-T10-1a"].near(offset_change, -step)
                items["CAI-T10-1a"].near(dt[h], -step)
                q[("offset", h)] = offset_change / step
            else:
                items["CAI-T10-1a"].exact(offset_change, 0.0)
                items["CAI-T10-1a"].exact(dt[h], 0.0)
            if not _reader_accepts(a[h], changed_payloads):
                refused.append(h)
            items["CAI-T10-1a"].holds(h not in refused)
            items["CAI-T10-1a"].holds([s.get("step") for s in a[h]["steps"]].count("offset") == 1
                                      and a[h]["steps"][0]["step"] == "offset")
        if refused:
            recorded[str(step)] = {"reader_rejected_hits": refused}
            continue
        # 1b
        start_after = event_time.common_linear(after, weights, beta_hypothesis) if plant == "external-uses-hits" else start
        for h in b:
            tb, ta = event_time.tof(b[h], start, before), event_time.tof(a[h], start_after, after)
            if h in affected:
                items["CAI-T10-1b"].near(ta["tof_ns"] - tb["tof_ns"], dt[h])
                want = b[h]["path_length_cm"] / (event_time.SPEED_OF_LIGHT_CM_PER_NS * (tb["tof_ns"] + dt[h]))
                beta_item.near(ta["beta"] / want, 1.0)
                q[("external", h)] = (ta["tof_ns"] - tb["tof_ns"]) / step
                beta_errors[h].append(abs((ta["beta"] - tb["beta"]) / step - tb["beta"] / tb["tof_ns"]))
            else:
                items["CAI-T10-1b"].exact(ta["tof_ns"], tb["tof_ns"])
                items["CAI-T10-1b"].exact(ta["beta"], tb["beta"])
        # 1c
        eb = event_time.common_linear(before, weights, beta_hypothesis)
        ea = eb if plant == "stale-event-time" else event_time.common_linear(after, weights, beta_hypothesis)
        common_change = math.fsum(weights[k] * dt[k] for k in affected)
        items["CAI-T10-1c"].near(ea["value_ns"] - eb["value_ns"], common_change)
        for h in b:
            change = _tof_change(a[h], ea, after, b[h], eb, before)
            if change is None:                          # the recipe refused the start (a stale one is refused: fix round 1, I1)
                items["CAI-T10-1c"].holds(False)
                continue
            items["CAI-T10-1c"].near(change, dt[h] - common_change)
            q[("common", h)] = change / step
        # 1d
        for j in sorted(set(track.values())):
            if plant == "loo-keeps-own-hit":
                lb = event_time.common_linear(before, weights, beta_hypothesis)
                la = event_time.common_linear(after, weights, beta_hypothesis)
            else:
                lb = event_time.leave_one_out(before, weights, beta_hypothesis, track_id=j)
                la = event_time.leave_one_out(after, weights, beta_hypothesis, track_id=j)
            norm = math.fsum(w for i, w in weights.items() if track[i] != j)
            loo_change = math.fsum(weights[k] / norm * dt[k] for k in affected if track[k] != j)
            for h in (i for i in b if track[i] == j):
                change = _tof_change(a[h], la, after, b[h], lb, before)
                if change is None:
                    items["CAI-T10-1d"].holds(False)
                    continue
                items["CAI-T10-1d"].near(change, dt[h] - loo_change)
                q[("leave-one-out", h)] = change / step
        # 1e: recorded only
        mb, ma = event_time.median(before, beta_hypothesis), event_time.median(after, beta_hypothesis)
        recorded[str(step)] = {"event_time_change_ns": ma["value_ns"] - mb["value_ns"],
                               "delta_t_ns": {str(k): dt[k] for k in affected},
                               "tof_change_ns": {str(h): _tof_change(a[h], ma, after, b[h], mb, before) for h in b}}
    for key, value in quotients[delta].items():
        if key in quotients[delta / 2]:
            halving.near(value, quotients[delta / 2][key])
        else:
            halving.holds(False)
    ratios = {}
    for h, errors in beta_errors.items():
        ratio = errors[1] / errors[0] if len(errors) == 2 and errors[0] > 0 else math.nan
        ratios[str(h)] = ratio
        halving.holds(BETA_RATIO_WINDOW[0] <= ratio <= BETA_RATIO_WINDOW[1])
    out = {name: item.report() for name, item in items.items()}
    out["CAI-T10-1b"]["beta"] = beta_item.report()
    if beta_item.failed:
        out["CAI-T10-1b"]["verdict"] = "FAIL"
    out["CAI-T10-1f"] = {**halving.report(), "beta_error_ratio": min(ratios.values()), "beta_error_ratios": ratios,
                         "beta_ratio_window": list(BETA_RATIO_WINDOW)}
    verdict = "PASS" if all(v["verdict"] == "PASS" for v in out.values()) else "FAIL"
    return {"verdict": verdict, "plant": plant, "channel": channel, "affected_hits": affected,
            "weights_affected": {str(k): weights[k] for k in affected}, "tracks": len(set(track.values())), "hits": len(track),
            "steps_ns": [delta, delta / 2], "items": out, "recorded": {"CAI-T10-1e": recorded}}


def check_two_ended(hits: list, contents: dict, channel: int, delta: float, external_t0: float, plant: str | None = None) -> dict:
    """CAI-T10-2 on one set of two-ended hits; a planted defect from TWO_PLANTS is a control that must FAIL."""
    if plant is not None and plant not in TWO_PLANTS:
        raise time_chain.InputError(f"unknown plant {plant!r}")
    with recipe_plant(plant):
        return _check_two_ended(hits, contents, channel, delta, external_t0, plant)


def _check_two_ended(hits, contents, channel, delta, external_t0, plant) -> dict:
    nominal = _read_all(contents)
    if nominal["offset"].ends != 2:
        raise time_chain.InputError("CAI-T10-2 uses two-ended counters")
    counter, end = divmod(channel, 2)
    affected = sorted(h["hit_id"] for h in hits if h["counter"] == counter)
    if not affected:
        raise time_chain.InputError(f"CAI-T10-2: counter {counter} holds no hit")
    sign = -1.0 if end == 0 else 1.0
    speed = float(nominal["propagation"].values[channel])
    time_item, position_item = Item(TIME_TOLERANCE_NS, "ns"), Item(POSITION_TOLERANCE_CM, "cm")
    halving_time = Item(HALVING_FACTOR * TIME_TOLERANCE_NS / delta, "ns/ns")
    halving_position = Item(HALVING_FACTOR * POSITION_TOLERANCE_CM / delta, "cm/ns")
    start = event_time.external(external_t0, "fixture external start time")
    b = _by_hit(time_chain.correct(hits, nominal))
    quotients = {}
    for step in (delta, delta / 2):
        changed_payloads = _read_all(_changed(contents, channel, step))
        a = _by_hit(time_chain.correct(hits, changed_payloads))
        q = quotients.setdefault(step, {})
        rejected = [h for h in b if not _reader_accepts(a[h], changed_payloads)]
        time_item.holds(not rejected)
        if rejected:
            continue
        for h in b:
            mean_change = a[h]["propagation"]["mean_time_ns"] - b[h]["propagation"]["mean_time_ns"]
            if plant == "mean-one-end":
                mean_change = a[h]["ends"][0]["steps"][-1]["after_ns"] - b[h]["ends"][0]["steps"][-1]["after_ns"]
            position_change = a[h]["position"]["value_cm"] - b[h]["position"]["value_cm"]
            if plant == "position-no-half":
                position_change *= 2.0
            time_change = a[h]["corrected_time_ns"] - b[h]["corrected_time_ns"]
            tof_change = event_time.tof(a[h], start, None)["tof_ns"] - event_time.tof(b[h], start, None)["tof_ns"]
            if h in affected:
                for value in (mean_change, time_change, tof_change):
                    time_item.near(value, -step / 2)
                position_item.near(position_change, sign * speed * step / 2)
                q.update({("mean", h): mean_change / step, ("time", h): time_change / step, ("tof", h): tof_change / step,
                          ("position", h): position_change / step})
            else:
                for value in (mean_change, time_change, tof_change, position_change):
                    time_item.exact(value, 0.0)
    for key, value in quotients[delta].items():
        target = halving_position if key[0] == "position" else halving_time
        if key in quotients[delta / 2]:
            target.near(value, quotients[delta / 2][key])
        else:
            target.holds(False)
    out = {"CAI-T10-2": {"time": time_item.report(), "position": position_item.report()},
           "CAI-T10-2f": {"time": halving_time.report(), "position": halving_position.report()}}
    for item in out.values():
        item["verdict"] = "PASS" if all(part["verdict"] == "PASS" for part in item.values()) else "FAIL"
    verdict = "PASS" if all(v["verdict"] == "PASS" for v in out.values()) else "FAIL"
    return {"verdict": verdict, "plant": plant, "channel": channel, "end": end, "affected_hits": affected, "speed_cm_per_ns": speed,
            "steps_ns": [delta, delta / 2], "items": out}


# --- the seeded synthetic fixture of the run operation --------------------------------------------------------------------

def _single_event(rng) -> dict:
    n = int(rng.integers(3, 7))
    offsets, walks, speeds = rng.uniform(-5, 5, n), rng.uniform(0.2, 1.0, n), rng.uniform(10, 20, n)
    t0 = float(rng.uniform(0, 5))
    channel = int(rng.integers(0, n))
    placements = [(c, c) for c in range(n)]                    # (track, counter): one track per counter
    if rng.random() < 0.5:                                     # a track crossing a second plane (I1)
        placements.append((int(rng.integers(0, n)), None))
    if rng.random() < 0.5:                                     # a second hit, of a new track, on the changed channel (M7)
        placements.append((n, channel))
    hits = []
    for index, (track, counter) in enumerate(placements):
        if counter is None:
            counter = int((track + 1 + rng.integers(0, n - 1)) % n)
        amplitude, position, path = float(rng.uniform(10, 500)), float(rng.uniform(0, 100)), float(rng.uniform(200, 500))
        beta = float(rng.uniform(0.8, 1.0))
        hit_time = t0 + path / (event_time.SPEED_OF_LIGHT_CM_PER_NS * beta) + float(rng.normal(0, 0.05))
        raw = hit_time + position / speeds[counter] + walks[counter] / math.sqrt(amplitude) + offsets[counter]
        hits.append({"hit_id": 100 + index, "track_id": track, "counter": counter, "raw_time_ns": raw, "amplitude": amplitude,
                     "position_cm": position, "path_length_cm": path})
    raw_weights = rng.uniform(0.5, 1.5, len(hits))
    weights = {h["hit_id"]: float(w) for h, w in zip(hits, raw_weights / raw_weights.sum())}
    contents = {step: timing_payload.payload_bytes(step, values, n, 1, "nominal", NOMINAL_SOURCE)
                for step, values in (("offset", offsets), ("walk", walks), ("propagation", speeds))}
    return {"hits": hits, "contents": contents, "channel": channel, "weights": weights, "external_t0": t0 + float(rng.normal(0, 0.05))}


def _both_ends(values) -> list:
    """Each counter's speed for both of its ends (channels 2c and 2c + 1)."""
    return [float(v) for v in values for _ in (0, 1)]


def _two_event(rng) -> dict:
    n = int(rng.integers(2, 5))
    offsets, walks = rng.uniform(-5, 5, 2 * n), rng.uniform(0.2, 1.0, 2 * n)
    counter_speeds = rng.uniform(10, 20, n)
    t0 = float(rng.uniform(0, 5))
    hits = []
    for c in range(n):
        length, path = float(rng.uniform(120, 200)), float(rng.uniform(200, 500))
        x = float(rng.uniform(-0.45, 0.45)) * length
        hit_time = t0 + path / (event_time.SPEED_OF_LIGHT_CM_PER_NS * float(rng.uniform(0.8, 1.0)))
        ends = []
        for e, distance in ((0, length / 2 + x), (1, length / 2 - x)):
            channel, amplitude = 2 * c + e, float(rng.uniform(10, 500))
            raw = hit_time + distance / counter_speeds[c] + walks[channel] / math.sqrt(amplitude) + offsets[channel] + float(rng.normal(0, 0.05))
            ends.append({"end": e, "raw_time_ns": raw, "amplitude": amplitude})
        hits.append({"hit_id": 200 + c, "track_id": c, "counter": c, "path_length_cm": path, "counter_length_cm": length, "ends": ends})
    contents = {step: timing_payload.payload_bytes(step, values, n, 2, "nominal", NOMINAL_SOURCE)
                for step, values in (("offset", offsets), ("walk", walks), ("propagation", _both_ends(counter_speeds)))}
    return {"hits": hits, "contents": contents, "channel": int(rng.integers(0, 2 * n)), "external_t0": t0 + float(rng.normal(0, 0.05))}


def run(seed: int, events: int, plant: str | None) -> dict:
    import numpy
    rng = numpy.random.default_rng(seed)
    out = []
    for index in range(events):
        single, two = _single_event(rng), _two_event(rng)
        s = check_single_ended(single["hits"], single["contents"], single["channel"], STEP_NS, single["weights"], 1.0,
                               single["external_t0"], plant if plant in SINGLE_PLANTS else None)
        t = check_two_ended(two["hits"], two["contents"], two["channel"], STEP_NS, two["external_t0"], plant if plant in TWO_PLANTS else None)
        out.append({"event": index, "single_ended": s, "two_ended": t})
        print(f"EVENT {index} CAI-T10-1 {s['verdict']} CAI-T10-2 {t['verdict']}")
    return {"format": RECORD_FORMAT, "recipe": RECIPE, "status_label": "synthetic", "seed": seed, "plant": plant, "step_ns": STEP_NS,
            "tolerances": {"time_ns": TIME_TOLERANCE_NS, "position_cm": POSITION_TOLERANCE_CM, "beta_relative": BETA_RELATIVE_TOLERANCE,
                           "halving_factor": HALVING_FACTOR, "beta_ratio_window": list(BETA_RATIO_WINDOW)},
            "events": out}


def plant_reading(record: dict) -> tuple:
    """(item, events in which the planted item failed, events) for a run with a plant."""
    plant = record["plant"]
    side, item = ("single_ended", SINGLE_PLANTS[plant]) if plant in SINGLE_PLANTS else ("two_ended", TWO_PLANTS[plant])
    failed = sum(e[side]["items"][item]["verdict"] == "FAIL" for e in record["events"])
    return item, failed, len(record["events"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CAI-T10-1 and CAI-T10-2 on seeded synthetic events (plan R37).")
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("run", help="run both checks on N seeded synthetic events")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--events", type=int, required=True)
    p.add_argument("--out", type=Path, required=True, help="a folder that must not exist yet")
    p.add_argument("--plant", choices=sorted({**SINGLE_PLANTS, **TWO_PLANTS}), help="a planted defect: a control that must FAIL")
    args = parser.parse_args(argv)
    if args.events < 1:
        print(json.dumps({"status": "rejected", "reason": "--events must be at least 1"}))
        return 2
    if args.out.exists():
        print(json.dumps({"status": "rejected", "reason": f"{args.out} exists: a record is never overwritten"}))
        return 2
    try:
        record = run(args.seed, args.events, args.plant)
    except timing_payload.InputError as exc:   # the fixture is the tool's own: a rejection here is not the user's input
        print(json.dumps({"status": "incomplete", "reason": f"the recipe rejected the tool's own generated fixture: {exc}"}))
        return 3
    except Exception as exc:  # noqa: BLE001 - any other error is a crash, never a negative verdict
        print(json.dumps({"status": "incomplete", "reason": f"{type(exc).__name__}: {exc}"}))
        return 3
    try:
        args.out.mkdir(parents=True)
        (args.out / "t10-cai.json").write_text(json.dumps(record, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    except OSError as exc:
        print(json.dumps({"status": "incomplete", "reason": f"cannot write the record: {exc}"}))
        return 3
    failed = [e["event"] for e in record["events"] if e["single_ended"]["verdict"] != "PASS" or e["two_ended"]["verdict"] != "PASS"]
    verdict = "FAIL" if failed else "PASS"
    if args.plant:
        item, item_failed, total = plant_reading(record)
        print(f"PLANT {args.plant} item {item} failed in {item_failed} of {total} events")
    failed_items = sorted({name for e in record["events"] for side in ("single_ended", "two_ended")
                           for name, item in e[side]["items"].items() if item["verdict"] != "PASS"})
    print(f"RESULT t10-cai {verdict} events {args.events} failed {len(failed)} plant {args.plant or 'none'} "
          f"items {','.join(failed_items) or 'none'}")
    print(json.dumps({"status": "failed" if failed else "ok", "status_label": "synthetic", "events": args.events, "failed_events": len(failed),
                      "record": str(args.out / "t10-cai.json")}, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
