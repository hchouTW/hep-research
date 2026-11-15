"""A native non-hit input through a recipe: counts with thresholds and exposure (plan section 3.3, W6, BP12, A19;
t10-timing-stage-plan.md section 6.1, row W6-T10).

Native input, per channel: a threshold selection, readout intervals each read or not read with start, end and dead time [s], and
pulse times [s] and amplitudes (in the threshold's unit). The recipe counts the pulses at or above the channel's threshold in each
read interval (a zero is a count), marks an interval that was not read absent with no count, sets each channel's valid exposure to the
sum over its read intervals of (end - start - dead time), the run time to the span of all intervals, and each rate's denominator to
the channel's own valid exposure. It delivers counts only, never a per-event energy (A19). The product (reconstruction-product/1 with
reconstruction:counts-v1) is checked by the T06 contract reader; rate readings, sum of counts over valid exposure, are kept beside it.
Synthetic inputs only; no counting or rate quality is claimed.
"""
from __future__ import annotations

import math

from contracts.reconstruction import read_sidecar

from .timing_payload import InputError

EXTENSION = "reconstruction:counts-v1"
COUNT_MODEL = {"kind": "declared-sampling", "premises": ["fixed window", "dead time inside the valid exposure"], "inferred_from": None}


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _channel(item: dict) -> tuple:
    name = item.get("channel")
    threshold = item.get("threshold")
    if not isinstance(name, str) or not name:
        raise InputError("counts: each channel has a name")
    if not isinstance(threshold, dict) or set(threshold) != {"value", "unit"} or not _finite(threshold["value"]) or not threshold["unit"]:
        raise InputError(f"counts: {name} has no threshold {{value, unit}}")
    intervals = sorted(item.get("intervals") or [], key=lambda i: i.get("start_s", math.nan))
    if not intervals:
        raise InputError(f"counts: {name} has no readout interval")
    previous_end = -math.inf
    for interval in intervals:
        start, end, dead = interval.get("start_s"), interval.get("end_s"), interval.get("dead_s")
        if not all(_finite(v) for v in (start, end, dead)) or not end > start or not 0 <= dead <= end - start \
                or not isinstance(interval.get("read"), bool) or not interval.get("interval_id"):
            raise InputError(f"counts: {name}: an interval is {{interval_id, start_s < end_s, 0 <= dead_s <= end - start, read}}")
        if start < previous_end:
            raise InputError(f"counts: {name}: intervals overlap at {start} s")
        previous_end = end
    counted = {i["interval_id"]: 0 for i in intervals if i["read"]}
    for pulse in item.get("pulses") or []:
        time, amplitude = pulse.get("time_s"), pulse.get("amplitude")
        if not _finite(time) or not _finite(amplitude):
            raise InputError(f"counts: {name}: a pulse is {{time_s, amplitude}}")
        home = [i for i in intervals if i["start_s"] <= time < i["end_s"]]
        if not home:
            raise InputError(f"counts: {name}: a pulse at {time} s lies outside every interval")
        if not home[0]["read"]:
            raise InputError(f"counts: {name}: a pulse at {time} s lies in an interval that was not read")
        if amplitude >= threshold["value"]:
            counted[home[0]["interval_id"]] += 1
    exposure = math.fsum(i["end_s"] - i["start_s"] - i["dead_s"] for i in intervals if i["read"])
    return name, threshold, intervals, counted, exposure


def build(channels: list, product_id: str) -> tuple:
    """(product, readings) from native channels; the product is the T06 count block in a reconstruction product."""
    if not isinstance(channels, list) or not channels:
        raise InputError("counts: no channel")
    parsed = [_channel(item) for item in channels]
    names = [p[0] for p in parsed]
    if len(set(names)) != len(names):
        raise InputError("counts: a channel name is used twice")
    starts = [i["start_s"] for p in parsed for i in p[2]]
    ends = [i["end_s"] for p in parsed for i in p[2]]
    block = {"capability": "counting", "observables": ["count"], "per_event_energy": False, "count_model": dict(COUNT_MODEL),
             "run_time": {"value": max(ends) - min(starts), "unit": "s"}, "selections": [], "channels": [], "intervals": [], "rates": []}
    readings = {}
    for item, (name, threshold, intervals, counted, exposure) in zip(channels, parsed):
        selection = f"selection.threshold-{name}"
        block["selections"].append({"selection_id": selection, "kind": "threshold", "threshold": dict(threshold)})
        block["channels"].append({"channel": name, "valid_exposure": {"value": exposure, "unit": "s"}, "response_ref": item["response_ref"],
                                  "selection_ref": selection})
        for interval in intervals:
            entry = {"interval_id": interval["interval_id"], "channel": name, "presence": "present" if interval["read"] else "absent"}
            if interval["read"]:
                entry["count"] = counted[interval["interval_id"]]
            block["intervals"].append(entry)
        block["rates"].append({"channel": name, "denominator": {"source": "valid-exposure", "value": exposure, "unit": "s"},
                               "response_ref": item["response_ref"], "selection_ref": selection})
        total = sum(counted.values())
        readings[name] = {"count": total, "valid_exposure_s": exposure, "rate_per_s": total / exposure if exposure > 0 else None}
    product = {"schema": "reconstruction-product/1", "product_id": product_id, "revision": 1, "collection": "counts",
               "native": {"type": "timing-pid::CounterCounts"}, "presence": "present", "role": "reconstruction-input",
               "conditions_used": [], "required_extensions": [EXTENSION], "counts": block}
    return product, readings


def check(product: dict) -> list:
    """The T06 contract reader's error codes for a count product (an empty list: accepted)."""
    return [finding.code for finding in read_sidecar(product).errors]
