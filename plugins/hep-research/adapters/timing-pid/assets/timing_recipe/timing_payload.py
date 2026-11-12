"""timing-payload/1, one conditions payload per step of the time chain (T10 timing lane stage 1; plan R32, R35, R37 CAI-T10).

The shape follows calo-gain-payload/1 (calibration-alignment-interfaces.md). A JSON object with exactly KEYS, sorted keys, one
space of indent:

- format "timing-payload/1", role "conditions", step one of STEPS, unit the step's (UNITS);
- grid {counters, ends} and channel_map, the SHA-256 of the text of timing-channel-map/1 for that grid (channel_map_text),
  whose rule is channel = counter * ends + end; ends is 1 (single-ended counters) or 2 (two-ended);
- values: [[channel, value], ...], every channel exactly once, ascending, each finite; walk coefficients and propagation speeds
  are above zero, an offset may have any sign;
- origin nominal or measured; producer {kind external or derived, source}; derived_against: identities of the upstream payloads
  assumed, in chain order; derived_from: null or {payload_id, changed_channels}; a derived payload is never nominal (R32);
- round: null or a count (R36).

Its identity is the SHA-256 of its bytes (R32, by content). derive() writes a payload with some channels changed: its own
identity, and the payload it came from (R33's rule for alignment payloads, applied to time constants). No constant here is
derived from data (R31): every payload of this stage is synthetic.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy

FORMAT = "timing-payload/1"
CHANNEL_MAP_FORMAT = "timing-channel-map/1"
STEPS = ("offset", "walk", "propagation")
UNITS = {"offset": "ns", "walk": "ns", "propagation": "cm/ns"}
POSITIVE_STEPS = {"walk", "propagation"}
KEYS = {"format", "role", "step", "unit", "grid", "channel_map", "values", "origin", "producer", "derived_against", "derived_from",
        "round"}
HEX = set("0123456789abcdef")


class InputError(ValueError):
    """An input of the timing recipe is rejected (core/status.py: "rejected", exit 2 in a script)."""


@dataclass(frozen=True)
class TimingPayload:
    step: str
    unit: str
    values: numpy.ndarray
    counters: int
    ends: int
    channel_map: str
    origin: str
    derived_against: tuple
    derived_from: str | None
    changed_channels: tuple
    round: int | None
    identity: str
    document: dict


def channel_map_text(counters: int, ends: int) -> str:
    return (f"{CHANNEL_MAP_FORMAT}\ncounters {counters}\nends {ends}\n"
            "channel = counter * E + end, counter in [0, N), end in [0, E)\n")


def channel_map_identity(counters: int, ends: int) -> str:
    return hashlib.sha256(channel_map_text(counters, ends).encode("utf-8")).hexdigest()


def _is_identity(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _is_count(value, minimum: int = 0) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _dumps(doc: dict) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")


def payload_bytes(step: str, values, counters: int, ends: int, origin: str, source: str, derived_against=(), round_=None) -> bytes:
    """A payload of external constants (synthetic here). values: one number per channel, by channel ID."""
    numbers = [float(v) for v in values]
    doc = {"format": FORMAT, "role": "conditions", "step": step, "unit": UNITS.get(step, "?"),
           "grid": {"counters": counters, "ends": ends}, "channel_map": channel_map_identity(counters, ends),
           "values": [[c, v] for c, v in enumerate(numbers)], "origin": origin, "producer": {"kind": "external", "source": source},
           "derived_against": list(derived_against), "derived_from": None, "round": round_}
    try:
        content = _dumps(doc)
    except ValueError:
        raise InputError("timing payload: values must be finite numbers") from None
    read(content)
    return content


def _unique_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("a key twice")
    return dict(pairs)


def _reject_constant(token):
    raise ValueError(token)


def read(content: bytes, name: str = "timing payload") -> TimingPayload:
    try:
        doc = json.loads(content.decode("utf-8"), parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, ValueError) as exc:
        if str(exc) == "a key twice":
            raise InputError(f"{name}: an object holds a key twice; refused, never read as the last one") from None
        raise InputError(f"{name}: not a JSON payload of finite numbers") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise InputError(f"{name}: payload keys must be exactly {sorted(KEYS)}")
    if doc["format"] != FORMAT or doc["role"] != "conditions":
        raise InputError(f"{name}: not a {FORMAT} conditions payload (format {doc['format']!r})")
    step = doc["step"]
    if not isinstance(step, str) or step not in STEPS:
        raise InputError(f"{name}: step {step!r}: the time chain's steps are {', '.join(STEPS)}")
    if doc["unit"] != UNITS[step]:
        raise InputError(f"{name}: unit {doc['unit']!r} is not the {step} step's ({UNITS[step]})")
    grid = doc["grid"]
    if not isinstance(grid, dict) or set(grid) != {"counters", "ends"} or not _is_count(grid["counters"], 1) \
            or not _is_count(grid["ends"], 1) or grid["ends"] > 2:
        raise InputError(f"{name}: grid must be {{counters (at least 1), ends (1 or 2)}}")
    counters, ends = grid["counters"], grid["ends"]
    if doc["channel_map"] != channel_map_identity(counters, ends):
        raise InputError(f"{name}: channel_map does not match its grid's {CHANNEL_MAP_FORMAT} identity")
    channels = counters * ends
    pairs = doc["values"]
    if not isinstance(pairs, list):
        raise InputError(f"{name}: values must be a list of [channel, value]")
    values = numpy.empty(channels)
    previous = -1
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise InputError(f"{name}: each value is [channel, value]")
        channel, value = pair
        if not _is_count(channel):
            raise InputError(f"{name}: a channel must be a non-negative integer channel ID")
        if channel >= channels:
            raise InputError(f"{name}: unknown channel {channel}: the channel map has 0 to {channels - 1}")
        if channel <= previous:
            raise InputError(f"{name}: channels must be ascending, each once (channel {channel})")
        if not _finite(value):
            raise InputError(f"{name}: the value of channel {channel} is not a finite number")
        if step in POSITIVE_STEPS and value <= 0:
            raise InputError(f"{name}: the {step} value of channel {channel} must be positive")
        values[channel] = float(value)
        previous = channel
    if len(pairs) != channels:
        raise InputError(f"{name}: {len(pairs)} values: every channel of the map needs one ({channels})")
    if doc["origin"] not in ("nominal", "measured"):
        raise InputError(f"{name}: origin must be nominal or measured")
    producer = doc["producer"]
    if not isinstance(producer, dict) or set(producer) != {"kind", "source"} or producer["kind"] not in ("external", "derived") \
            or not isinstance(producer["source"], str) or not producer["source"]:
        raise InputError(f"{name}: producer must be {{kind: external or derived, source}}")
    against = doc["derived_against"]
    if not isinstance(against, list) or not all(_is_identity(a) for a in against):
        raise InputError(f"{name}: derived_against must list payload identities (64 lowercase hex)")
    source = doc["derived_from"]
    changed = ()
    if source is not None:
        if not isinstance(source, dict) or set(source) != {"payload_id", "changed_channels"} or not _is_identity(source["payload_id"]):
            raise InputError(f"{name}: derived_from must be null or {{payload_id, changed_channels}}")
        listed = source["changed_channels"]
        if not isinstance(listed, list) or not listed or not all(_is_count(c) for c in listed) or listed != sorted(set(listed)) \
                or listed[-1] >= channels:
            raise InputError(f"{name}: derived_from.changed_channels must be ascending distinct known channels, at least one")
        if doc["origin"] == "nominal":
            raise InputError(f"{name}: a derived payload is never nominal (R32: nominal is the ideal constant)")
        if producer["kind"] != "derived":
            raise InputError(f"{name}: a payload with derived_from is made here: producer kind must be derived")
        changed = tuple(listed)
    elif producer["kind"] == "derived":
        raise InputError(f"{name}: producer derived needs derived_from, the payload it came from")
    round_ = doc["round"]
    if round_ is not None and not _is_count(round_):
        raise InputError(f"{name}: round must be null or a count")
    return TimingPayload(step=step, unit=doc["unit"], values=values, counters=counters, ends=ends, channel_map=doc["channel_map"],
                         origin=doc["origin"], derived_against=tuple(against),
                         derived_from=None if source is None else source["payload_id"], changed_channels=changed, round=round_,
                         identity=hashlib.sha256(content).hexdigest(), document=doc)


def derive(parent_content: bytes, changes: dict, source: str) -> bytes:
    """A payload equal to the parent except the values in `changes` ({channel: value}); origin measured, producer derived,
    derived_from naming the parent's identity and the changed channels."""
    parent = read(parent_content, "parent timing payload")
    if not changes:
        raise InputError("derived timing payload: no channel changed")
    doc = json.loads(parent_content.decode("utf-8"))
    values = dict((c, v) for c, v in doc["values"])
    for channel, value in changes.items():
        if not _is_count(channel) or channel not in values:
            raise InputError(f"derived timing payload: unknown channel {channel}")
        if not _finite(value):
            raise InputError(f"derived timing payload: the value of channel {channel} is not finite")
        values[channel] = float(value)
    doc.update({"values": [[c, values[c]] for c in sorted(values)], "origin": "measured",
                "producer": {"kind": "derived", "source": source},
                "derived_from": {"payload_id": parent.identity, "changed_channels": sorted(changes)}})
    content = _dumps(doc)
    read(content, "derived timing payload")
    return content
