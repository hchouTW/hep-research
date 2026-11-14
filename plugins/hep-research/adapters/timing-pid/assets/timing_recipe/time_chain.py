"""The time chain of a counter hit (plan R35, in the chain order of R34; t10-timing-stage-plan.md section 2).

Chain order, fixed: (1) offset, t_1 = t_raw - o_c; (2) amplitude-dependent time walk, t_2 = t_1 - a_c / sqrt(A); (3) propagation
along the counter. Raising channel c's offset by D lowers its offset-corrected times by D (the sign convention of the stage plan).
The 1/sqrt(A) walk is a fixture choice of an amplitude-dependent walk, no physical shape is claimed.

- Single-ended counter (one channel per counter): t_3 = t_2 - d / v_c, with d the distance from the hit to the read-out end,
  taken from the track and recorded with source "track". Without that position the hit is refused: none is invented.
- Two-ended counter (channels 2 counter and 2 counter + 1, end 0 at -L/2, end 1 at +L/2): offset and walk per end, then the
  propagation step gives the mean (t_e0 + t_e1) / 2, the position x = v (t_e0 - t_e1) / 2 and the propagation-corrected time
  t_0 = mean - L / (2 v) (derived in the stage plan, not from a source). Both ends' times are kept; a missing end is refused,
  never zero-filled. Both ends must carry the same speed v.

Every hit record (timing-hit-record/1) keeps, per step in chain order, the value before and after, the value the step applied,
the step's parameter and the identity of its payload; the amplitude; the position with its source; and the track's path length
to the hit (R35). check_record() refuses a record whose steps are out of order, repeated, missing or discontinuous, whose
applied values do not follow from their parameters, whose single-ended position is not the track's, or (given the payloads) whose
payload identities or parameters are not the payloads'; a malformed record raises InputError, never another exception.
"""
from __future__ import annotations

import math

from .timing_payload import STEPS, InputError, TimingPayload

RECORD_FORMAT = "timing-hit-record/1"
END_STEPS = ("offset", "walk")
HEX = set("0123456789abcdef")


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _positive(value) -> bool:
    return _finite(value) and value > 0


def _check_payloads(payloads: dict) -> tuple:
    if not isinstance(payloads, dict) or set(payloads) != set(STEPS):
        raise InputError(f"time chain: one payload per step is needed: {', '.join(STEPS)}")
    maps = set()
    for step in STEPS:
        payload = payloads[step]
        if not isinstance(payload, TimingPayload) or payload.step != step:
            raise InputError(f"time chain: the {step} payload is not a {step} step's timing payload")
        maps.add((payload.channel_map, payload.counters, payload.ends))
    if len(maps) != 1:
        raise InputError("time chain: the payloads are keyed by different channel maps")
    (_, counters, ends), = maps
    return counters, ends


def _step(order: int, step: str, payload: TimingPayload, channel: int, before: float, applied: float) -> dict:
    return {"order": order, "step": step, "payload_id": payload.identity, "parameter": float(payload.values[channel]),
            "parameter_unit": payload.unit, "applied_ns": applied, "before_ns": before, "after_ns": before - applied}


def _end_steps(payloads: dict, channel: int, raw: float, amplitude: float) -> list:
    offset = _step(1, "offset", payloads["offset"], channel, raw, float(payloads["offset"].values[channel]))
    walk = _step(2, "walk", payloads["walk"], channel, offset["after_ns"],
                 float(payloads["walk"].values[channel]) / math.sqrt(amplitude))
    return [offset, walk]


def _common(hit: dict, counters: int) -> None:
    for key in ("hit_id", "track_id", "counter"):
        if isinstance(hit.get(key), bool) or not isinstance(hit.get(key), int) or hit[key] < 0:
            raise InputError(f"time chain: {key} must be a non-negative integer")
    if hit["counter"] >= counters:
        raise InputError(f"time chain: unknown counter {hit['counter']}: the channel map has {counters}")
    if not _positive(hit.get("path_length_cm")):
        raise InputError(f"time chain: hit {hit['hit_id']} has no path length (R35 keeps it): refused")


def _single(hit: dict, payloads: dict, counters: int) -> dict:
    _common(hit, counters)
    if not _finite(hit.get("raw_time_ns")):
        raise InputError(f"time chain: hit {hit['hit_id']} has no raw time")
    if not _positive(hit.get("amplitude")):
        raise InputError(f"time chain: hit {hit['hit_id']} has no positive amplitude: the walk is never corrected with an invented one")
    if not _finite(hit.get("position_cm")) or hit["position_cm"] < 0:
        raise InputError(f"time chain: hit {hit['hit_id']} on a single-ended counter has no track position: none is invented")
    channel = hit["counter"]
    steps = _end_steps(payloads, channel, float(hit["raw_time_ns"]), float(hit["amplitude"]))
    speed = float(payloads["propagation"].values[channel])
    steps.append(_step(3, "propagation", payloads["propagation"], channel, steps[-1]["after_ns"], hit["position_cm"] / speed))
    return {"format": RECORD_FORMAT, "readout": "single-ended", "hit_id": hit["hit_id"], "track_id": hit["track_id"],
            "counter": hit["counter"], "channel": channel, "raw_time_ns": float(hit["raw_time_ns"]), "amplitude": hit["amplitude"],
            "position": {"value_cm": hit["position_cm"], "source": "track", "measured_from": "read-out end"},
            "path_length_cm": hit["path_length_cm"], "steps": steps, "corrected_time_ns": steps[-1]["after_ns"]}


def _two_ended(hit: dict, payloads: dict, counters: int) -> dict:
    _common(hit, counters)
    if not _positive(hit.get("counter_length_cm")):
        raise InputError(f"time chain: hit {hit['hit_id']} has no counter length")
    ends = hit.get("ends")
    if not isinstance(ends, list) or sorted(e.get("end") for e in ends if isinstance(e, dict)) != [0, 1] or len(ends) != 2:
        raise InputError(f"time chain: hit {hit['hit_id']} on a two-ended counter needs both ends 0 and 1: a missing end is refused, "
                         "never zero-filled")
    counter = hit["counter"]
    speeds = {float(payloads["propagation"].values[2 * counter + e]) for e in (0, 1)}
    if len(speeds) != 1:
        raise InputError(f"time chain: counter {counter}: its two ends carry different propagation speeds")
    speed, = speeds
    kept = []
    for end in sorted(ends, key=lambda e: e["end"]):
        if not _finite(end.get("raw_time_ns")):
            raise InputError(f"time chain: hit {hit['hit_id']} end {end['end']} has no raw time")
        if not _positive(end.get("amplitude")):
            raise InputError(f"time chain: hit {hit['hit_id']} end {end['end']} has no positive amplitude")
        channel = 2 * counter + end["end"]
        kept.append({"end": end["end"], "channel": channel, "raw_time_ns": float(end["raw_time_ns"]), "amplitude": end["amplitude"],
                     "steps": _end_steps(payloads, channel, float(end["raw_time_ns"]), float(end["amplitude"]))})
    times = [e["steps"][-1]["after_ns"] for e in kept]
    propagation = _propagation(payloads["propagation"].identity, speed, hit["counter_length_cm"], times)
    return {"format": RECORD_FORMAT, "readout": "two-ended", "hit_id": hit["hit_id"], "track_id": hit["track_id"], "counter": counter,
            "ends": kept, "propagation": propagation,
            "position": {"value_cm": propagation["position_cm"], "source": "two-ended",
                         "convention": "x = v (t_end0 - t_end1) / 2, end 0 at -L/2, end 1 at +L/2"},
            "path_length_cm": hit["path_length_cm"], "corrected_time_ns": propagation["after_ns"]}


def _propagation(payload_id: str, speed: float, length: float, times: list) -> dict:
    mean = 0.5 * (times[0] + times[1])
    return {"order": 3, "step": "propagation", "payload_id": payload_id, "parameter": speed, "parameter_unit": "cm/ns",
            "counter_length_cm": length, "end_times_ns": list(times), "mean_time_ns": mean, "position_cm": 0.5 * speed * (times[0] - times[1]),
            "applied_ns": length / (2.0 * speed), "before_ns": mean, "after_ns": mean - length / (2.0 * speed)}


def correct(hits: list, payloads: dict) -> list:
    """The hit records of `hits` under `payloads` ({step: TimingPayload}), in input order."""
    counters, ends = _check_payloads(payloads)
    out = []
    for hit in hits:
        if not isinstance(hit, dict):
            raise InputError("time chain: a hit is an object")
        out.append(_single(hit, payloads, counters) if ends == 1 else _two_ended(hit, payloads, counters))
    if len({r["hit_id"] for r in out}) != len(out):
        raise InputError("time chain: a hit identifier is used twice")
    return out


def _expected_applied(step: str, parameter: float, amplitude, position) -> float:
    """The value a step applies, from its recorded parameter: offset o_c, walk a_c / sqrt(A), propagation d / v."""
    if step == "offset":
        return parameter
    if step == "walk":
        return parameter / math.sqrt(amplitude)
    return position / parameter


def _check_steps(steps, names, raw, where: str, amplitude, position, channel: int, payloads) -> None:
    if not isinstance(steps, list) or not all(isinstance(s, dict) for s in steps) or [s.get("step") for s in steps] != list(names):
        raise InputError(f"{where}: steps must be exactly {', '.join(names)}, in chain order, each once")
    if not _finite(raw):
        raise InputError(f"{where}: no raw time")
    before = raw
    for order, step in enumerate(steps, start=1):
        name = step["step"]
        if step.get("order") != order:
            raise InputError(f"{where}: step {name} has order {step.get('order')}, not {order}")
        payload_id = step.get("payload_id")
        if not isinstance(payload_id, str) or len(payload_id) != 64 or not set(payload_id) <= HEX:
            raise InputError(f"{where}: step {name} records no payload identity")
        parameter = step.get("parameter")
        if not _finite(parameter) or (name != "offset" and parameter <= 0):
            raise InputError(f"{where}: step {name} records no valid parameter")
        for key in ("applied_ns", "before_ns", "after_ns"):
            if not _finite(step.get(key)):
                raise InputError(f"{where}: step {name}: {key} is not a finite number")
        if step["applied_ns"] != _expected_applied(name, parameter, amplitude, position):
            raise InputError(f"{where}: step {name}: the applied value does not follow from its parameter")
        if step["before_ns"] != before:
            raise InputError(f"{where}: step {name} does not start from the previous step's value")
        if step["after_ns"] != step["before_ns"] - step["applied_ns"]:
            raise InputError(f"{where}: step {name}: after is not before minus the applied value")
        if payloads is not None:
            payload = payloads[name]
            if payload_id != payload.identity or parameter != float(payload.values[channel]):
                raise InputError(f"{where}: step {name}: its payload identity or parameter is not the {name} payload's for channel "
                                 f"{channel}")
        before = step["after_ns"]


def check_record(record: dict, payloads: dict | None = None) -> None:
    """Refuses a hit record that does not keep the chain as R35 asks (raises InputError, never another exception). Every applied
    value is recomputed from its step's parameter; given the payloads ({step: TimingPayload}), each step's payload identity and
    parameter must also be that payload's for the hit's channel."""
    try:
        _check_record(record, payloads)
    except InputError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError, IndexError) as exc:
        raise InputError(f"hit record: malformed ({type(exc).__name__}: {exc})") from None


def _check_record(record: dict, payloads) -> None:
    if not isinstance(record, dict) or record.get("format") != RECORD_FORMAT:
        raise InputError(f"hit record: not a {RECORD_FORMAT} record")
    if payloads is not None:
        _check_payloads(payloads)
    where = f"hit record {record.get('hit_id')}"
    if not _positive(record.get("path_length_cm")):
        raise InputError(f"{where}: no path length")
    if record.get("readout") == "single-ended":
        position = record.get("position")
        if not _positive(record.get("amplitude")) or not isinstance(position, dict):
            raise InputError(f"{where}: amplitude and position are kept")
        if position != {"value_cm": position.get("value_cm"), "source": "track", "measured_from": "read-out end"} \
                or not _finite(position["value_cm"]) or position["value_cm"] < 0:
            raise InputError(f"{where}: a single-ended hit's position is the track's, measured from the read-out end")
        if record.get("channel") != record.get("counter"):
            raise InputError(f"{where}: a single-ended counter's channel is its counter")
        _check_steps(record.get("steps"), STEPS, record.get("raw_time_ns"), where, record["amplitude"], position["value_cm"],
                     record["channel"], payloads)
        if record.get("corrected_time_ns") != record["steps"][-1]["after_ns"]:
            raise InputError(f"{where}: the corrected time is not the last step's value")
        return
    if record.get("readout") != "two-ended":
        raise InputError(f"{where}: readout must be single-ended or two-ended")
    ends = record.get("ends")
    if not isinstance(ends, list) or not all(isinstance(e, dict) for e in ends) or [e.get("end") for e in ends] != [0, 1]:
        raise InputError(f"{where}: a two-ended record keeps both ends, 0 then 1")
    counter = record.get("counter")
    for end in ends:
        if not _positive(end.get("amplitude")):
            raise InputError(f"{where}: end {end['end']} keeps no amplitude")
        if end.get("channel") != 2 * counter + end["end"]:
            raise InputError(f"{where}: end {end['end']}'s channel is not 2 counter + end")
        _check_steps(end.get("steps"), END_STEPS, end.get("raw_time_ns"), f"{where} end {end['end']}", end["amplitude"], None,
                     end["channel"], payloads)
    prop = record.get("propagation")
    times = [e["steps"][-1]["after_ns"] for e in ends]
    if not isinstance(prop, dict) or prop.get("order") != 3 or prop.get("step") != "propagation":
        raise InputError(f"{where}: the propagation step is step 3")
    payload_id = prop.get("payload_id")
    if not isinstance(payload_id, str) or len(payload_id) != 64 or not set(payload_id) <= HEX:
        raise InputError(f"{where}: the propagation step records no payload identity")
    if not _positive(prop.get("parameter")) or not _positive(prop.get("counter_length_cm")):
        raise InputError(f"{where}: the propagation step records no positive speed and counter length")
    if payloads is not None:
        payload = payloads["propagation"]
        if payload_id != payload.identity or any(prop["parameter"] != float(payload.values[e["channel"]]) for e in ends):
            raise InputError(f"{where}: the propagation step's payload identity or speed is not the propagation payload's")
    expected = _propagation(payload_id, prop["parameter"], prop["counter_length_cm"], times)
    if prop != expected or record.get("corrected_time_ns") != expected["after_ns"] \
            or record.get("position") != {"value_cm": expected["position_cm"], "source": "two-ended",
                                          "convention": "x = v (t_end0 - t_end1) / 2, end 0 at -L/2, end 1 at +L/2"}:
        raise InputError(f"{where}: the propagation step does not follow from the two ends' times")
