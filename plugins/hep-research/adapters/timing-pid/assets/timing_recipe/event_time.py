"""Event times and time of flight (plan R35, R37 CAI-T10; t10-timing-stage-plan.md section 2).

Each event time (timing-event-time/1) records its source, its estimator and the identifiers and weights of the hits that formed
it, so that a calibration can exclude a channel's own hit (R35):

- external: a supplied T_0, no hit used;
- internal, common, linear with fixed weights: each hit gives T_0,i = t_i - L_i / (c beta_hyp), T_0 = sum_i w_i T_0,i, the weights
  recorded, non-negative, summing to 1 (to 1e-12, else refused);
- internal, per-track leave-one-out, linear: for track j every hit of track j is excluded (keyed by track_id, so a track with
  several timing hits keeps none of them): T_0^(-j) = sum_{i not in j} w_i^(-j) T_0,i with w_i^(-j) = w_i / sum_{l not in j} w_l, the
  excluded track and its excluded hits recorded and given no weight;
- internal, median of the T_0,i: a non-linear estimator, recorded without weights.

The time of flight (timing-tof/1) of the track of a hit is TOF = t - T_0 and beta = L / (c TOF), with L the track's path length
to the hit as the hit record keeps it. A leave-one-out time is used only for a hit of the track it excludes. The TOF record names
its event time: value, hits used, excluded track and hits, and the SHA-256 of the event-time record's canonical JSON (identity()).
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics

from .time_chain import check_record
from .timing_payload import InputError

EVENT_TIME_FORMAT = "timing-event-time/1"
TOF_FORMAT = "timing-tof/1"
SPEED_OF_LIGHT_CM_PER_NS = 29.9792458
WEIGHT_SUM_TOLERANCE = 1e-12


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _estimates(records: list, beta_hypothesis: float) -> dict:
    if not records:
        raise InputError("event time: an internal event time needs at least one hit")
    if not _finite(beta_hypothesis) or not 0 < beta_hypothesis <= 1:
        raise InputError("event time: the beta hypothesis must be in (0, 1]")
    out = {}
    for record in records:
        check_record(record)
        out[record["hit_id"]] = record["corrected_time_ns"] - record["path_length_cm"] / (SPEED_OF_LIGHT_CM_PER_NS * beta_hypothesis)
    return dict(sorted(out.items()))


def _check_weights(weights: dict, hit_ids) -> None:
    if not isinstance(weights, dict) or set(weights) != set(hit_ids):
        raise InputError("event time: the fixed weights must name exactly the hits used, each once")
    if not all(_finite(w) and w >= 0 for w in weights.values()):
        raise InputError("event time: a weight is negative or not finite")
    if abs(math.fsum(weights.values()) - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise InputError(f"event time: the weights sum to {math.fsum(weights.values())!r}, not 1")


def external(value_ns: float, label: str) -> dict:
    if not _finite(value_ns) or not isinstance(label, str) or not label:
        raise InputError("event time: an external time needs a finite value and a label naming its source")
    return {"format": EVENT_TIME_FORMAT, "source": "external", "estimator": "external", "label": label, "beta_hypothesis": None,
            "excluded_track": None, "excluded_hits": [], "hits": [], "estimates_ns": [], "value_ns": float(value_ns)}


def _internal(estimator: str, beta_hypothesis: float, excluded_track, excluded_hits: list, hits: list, estimates: dict,
              value: float) -> dict:
    return {"format": EVENT_TIME_FORMAT, "source": "internal", "estimator": estimator, "label": None, "beta_hypothesis": beta_hypothesis,
            "excluded_track": excluded_track, "excluded_hits": excluded_hits, "hits": hits,
            "estimates_ns": [[h, t] for h, t in estimates.items()], "value_ns": value}


def identity(record: dict) -> str:
    """The SHA-256 of an event-time record's canonical JSON (sorted keys, no spaces)."""
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def common_linear(records: list, weights: dict, beta_hypothesis: float) -> dict:
    estimates = _estimates(records, beta_hypothesis)
    _check_weights(weights, estimates)
    value = math.fsum(weights[h] * t for h, t in estimates.items())
    return _internal("linear-fixed-weights", beta_hypothesis, None, [], [{"hit_id": h, "weight": weights[h]} for h in estimates],
                     estimates, value)


def leave_one_out(records: list, weights: dict, beta_hypothesis: float, track_id: int) -> dict:
    """The event time for track `track_id`, from the hits of the other tracks with their weights renormalised."""
    estimates = _estimates(records, beta_hypothesis)
    _check_weights(weights, estimates)
    excluded = sorted(r["hit_id"] for r in records if r["track_id"] == track_id)
    if not excluded:
        raise InputError(f"event time: track {track_id} has no hit here")
    others = {h: t for h, t in estimates.items() if h not in excluded}
    norm = math.fsum(weights[h] for h in others)
    if not others or norm <= 0:
        raise InputError(f"event time: no weighted hit is left once track {track_id} is excluded")
    renormalised = {h: weights[h] / norm for h in others}
    value = math.fsum(renormalised[h] * t for h, t in others.items())
    return _internal("linear-fixed-weights", beta_hypothesis, track_id, excluded,
                     [{"hit_id": h, "weight": w} for h, w in renormalised.items()], others, value)


def median(records: list, beta_hypothesis: float) -> dict:
    estimates = _estimates(records, beta_hypothesis)
    return _internal("median", beta_hypothesis, None, [], [{"hit_id": h, "weight": None} for h in estimates], estimates,
                     float(statistics.median(estimates.values())))


def check(record: dict) -> None:
    """Refuses an event-time record that does not say how it was formed (raises InputError, never another exception)."""
    try:
        _check(record)
    except InputError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError) as exc:
        raise InputError(f"event time: malformed record ({type(exc).__name__}: {exc})") from None


def _check(record: dict) -> None:
    if not isinstance(record, dict) or record.get("format") != EVENT_TIME_FORMAT or not _finite(record.get("value_ns")):
        raise InputError(f"event time: not a {EVENT_TIME_FORMAT} record with a finite value")
    hits = record.get("hits")
    if not isinstance(hits, list) or not all(isinstance(h, dict) and set(h) == {"hit_id", "weight"} for h in hits):
        raise InputError("event time: hits must list {hit_id, weight}")
    ids = [h["hit_id"] for h in hits]
    if len(ids) != len(set(ids)):
        raise InputError("event time: a hit is listed twice")
    excluded_track, excluded_hits = record.get("excluded_track"), record.get("excluded_hits")
    if not isinstance(excluded_hits, list) or (excluded_track is None) != (not excluded_hits):
        raise InputError("event time: excluded_hits lists the excluded track's hits, and only a leave-one-out time has them")
    if record.get("source") == "external":
        if record.get("estimator") != "external" or hits or excluded_track is not None or not record.get("label"):
            raise InputError("event time: an external time uses no hit and names its source")
        return
    if record.get("source") != "internal" or not hits:
        raise InputError("event time: source must be external or internal, and an internal time lists its hits")
    used = sorted(set(ids) & set(excluded_hits))
    if used:
        raise InputError(f"event time: the leave-one-out time of track {excluded_track} uses its own track's hits {used}")
    if record.get("estimator") == "median":
        if any(h["weight"] is not None for h in hits):
            raise InputError("event time: a median has no weights")
        return
    if record.get("estimator") != "linear-fixed-weights":
        raise InputError(f"event time: unknown estimator {record.get('estimator')!r}")
    _check_weights({h["hit_id"]: h["weight"] for h in hits}, ids)


def tof(record: dict, start: dict) -> dict:
    """The time of flight and beta of the track of hit `record` against the event time `start`."""
    check_record(record)
    check(start)
    if start["excluded_track"] is not None and start["excluded_track"] != record["track_id"]:
        raise InputError(f"tof: the leave-one-out time of track {start['excluded_track']} is not track {record['track_id']}'s")
    flight = record["corrected_time_ns"] - start["value_ns"]
    if not flight > 0:
        raise InputError(f"tof: hit {record['hit_id']}: the time of flight {flight!r} ns is not positive")
    return {"format": TOF_FORMAT, "hit_id": record["hit_id"], "track_id": record["track_id"],
            "event_time": {"source": start["source"], "estimator": start["estimator"], "excluded_track": start["excluded_track"],
                           "excluded_hits": list(start["excluded_hits"]), "value_ns": start["value_ns"],
                           "hit_ids": [h["hit_id"] for h in start["hits"]], "identity": identity(start)},
            "path_length_cm": record["path_length_cm"], "tof_ns": flight,
            "beta": record["path_length_cm"] / (SPEED_OF_LIGHT_CM_PER_NS * flight)}
