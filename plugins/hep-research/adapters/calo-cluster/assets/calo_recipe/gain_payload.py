"""calo-gain-payload/1, the gain payload of the cell chain with its channel map (D2 stage 2; plan R32, R34, R37 CAI-T08).

A JSON object with exactly KEYS, written with sorted keys and one space of indent:

- format "calo-gain-payload/1", role "conditions", step "gain";
- operation: the gain's role in the chain, "multiply" (E = c (ADC - pedestal), unit MeV/adc) or "divide" (E = (ADC - pedestal) / g,
  unit adc/MeV);
- grid {nx, ny} and channel_map, the identity of the channel map the gains are keyed by: the SHA-256 of the text of
  calo-channel-map/1 for that grid (channel_map_text), whose rule is the product's stable channel ID, channel = ix * ny + iy;
- gains: [[channel, gain], ...], every channel of the map exactly once, ascending, each gain a finite number above zero;
- origin nominal or measured; producer {kind, source}: "external" for constants from outside the recipe, "derived" for a payload
  made from another one here;
- derived_against: the identities of the upstream payloads assumed, in chain order (the pedestal payload's);
- derived_from: null, or {payload_id, changed_channels} for a derived payload: the content identity of the payload it came from
  and the channels whose gain it changed, ascending. A derived payload is never nominal (R32: nominal is the ideal constant);
- round: null or a count (R36).

Its identity is the SHA-256 of its bytes (R32, by content). The reader refuses a malformed payload, a channel outside its map
(an unknown channel), a missing or repeated channel, and a channel map that is not its grid's; check_channel_map refuses it
against another channel map than the readout's or the product's. derive() writes a payload with some channels changed: it has
its own identity and records its source (R33's rule for alignment payloads, applied to gains). check_derived() checks a derived
payload against the parent it names. The stage 1 format calo-calibration-payload/1 stays readable (read_gain dispatches by
format), so earlier products and payloads are unchanged byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy

from .cell_input import InputError, Payload, read_payload

FORMAT = "calo-gain-payload/1"
CHANNEL_MAP_FORMAT = "calo-channel-map/1"
KEYS = {"format", "role", "step", "operation", "grid", "channel_map", "gains", "unit", "origin", "producer", "derived_against",
        "derived_from", "round"}
UNITS = {"multiply": "MeV/adc", "divide": "adc/MeV"}
PRODUCERS = {"external", "derived"}
HEX = set("0123456789abcdef")


def channel_map_text(nx: int, ny: int) -> str:
    return f"{CHANNEL_MAP_FORMAT}\nnx {nx}\nny {ny}\nchannel = ix * ny + iy, ix in [0, nx), iy in [0, ny)\n"


def channel_map_identity(nx: int, ny: int) -> str:
    return hashlib.sha256(channel_map_text(nx, ny).encode("utf-8")).hexdigest()


def _is_identity(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _is_count(value, minimum: int = 0) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _dumps(doc: dict) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")


def payload_bytes(operation: str, gains, nx: int, ny: int, origin: str, source: str, derived_against=(), round_=None) -> bytes:
    """A payload of external constants (synthetic here; R31: none is derived). gains: one number, or one per channel by flat index."""
    channels = nx * ny
    values = [float(gains)] * channels if _finite(gains) else [float(v) for v in gains]
    if len(values) != channels:
        raise InputError(f"gain payload: {len(values)} gains for {channels} channels")
    doc = {"format": FORMAT, "role": "conditions", "step": "gain", "operation": operation, "grid": {"nx": nx, "ny": ny},
           "channel_map": channel_map_identity(nx, ny), "gains": [[c, v] for c, v in enumerate(values)], "unit": UNITS.get(operation, "?"),
           "origin": origin, "producer": {"kind": "external", "source": source}, "derived_against": list(derived_against),
           "derived_from": None, "round": round_}
    content = _dumps(doc)
    read(content)
    return content


def _unique_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("a key twice")
    return dict(pairs)


def read(content: bytes, name: str = "gain payload") -> Payload:
    try:
        doc = json.loads(content.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
                         object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, ValueError) as exc:
        if str(exc) == "a key twice":
            raise InputError(f"{name}: an object holds a key twice; refused, never read as the last one") from None
        raise InputError(f"{name}: not a JSON payload of finite numbers") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise InputError(f"{name}: payload keys must be exactly {sorted(KEYS)}")
    if doc["format"] != FORMAT or doc["role"] != "conditions":
        raise InputError(f"{name}: not a {FORMAT} conditions payload (format {doc['format']!r})")
    if doc["step"] != "gain":
        raise InputError(f"{name}: step {doc['step']!r}: this format holds the gain step only")
    operation = doc["operation"]
    if not isinstance(operation, str) or operation not in UNITS:
        raise InputError(f"{name}: operation {operation!r}: the gain's role is multiply or divide")
    if doc["unit"] != UNITS[operation]:
        raise InputError(f"{name}: unit {doc['unit']!r} is not the {operation} role's ({UNITS[operation]})")
    grid = doc["grid"]
    if not isinstance(grid, dict) or set(grid) != {"nx", "ny"} or not _is_count(grid["nx"], 1) or not _is_count(grid["ny"], 1):
        raise InputError(f"{name}: grid must be {{nx, ny}}, both counts of at least 1")
    if not _is_identity(doc["channel_map"]):
        raise InputError(f"{name}: channel_map must be an identity (64 lowercase hex)")
    if doc["channel_map"] != channel_map_identity(grid["nx"], grid["ny"]):
        raise InputError(f"{name}: channel_map does not match its grid's {CHANNEL_MAP_FORMAT} identity")
    channels = grid["nx"] * grid["ny"]
    gains = doc["gains"]
    if not isinstance(gains, list):
        raise InputError(f"{name}: gains must be a list of [channel, gain]")
    values = numpy.empty(channels)
    previous = -1
    for pair in gains:
        if not isinstance(pair, list) or len(pair) != 2:
            raise InputError(f"{name}: each gain is [channel, gain]")
        channel, value = pair
        if isinstance(channel, bool) or not isinstance(channel, int):
            raise InputError(f"{name}: a channel must be an integer channel ID")
        if not 0 <= channel < channels:
            raise InputError(f"{name}: unknown channel {channel}: the channel map has 0 to {channels - 1}")
        if channel <= previous:
            raise InputError(f"{name}: channels must be ascending, each once (channel {channel})")
        if not _finite(value):
            raise InputError(f"{name}: the gain of channel {channel} is not a finite number")
        if value <= 0:
            raise InputError(f"{name}: the gain of channel {channel} must be positive")
        values[channel] = float(value)
        previous = channel
    if len(gains) != channels:
        raise InputError(f"{name}: {len(gains)} gains: every channel of the map needs one ({channels})")
    if doc["origin"] not in ("nominal", "measured"):
        raise InputError(f"{name}: origin must be nominal or measured")
    producer = doc["producer"]
    if not isinstance(producer, dict) or set(producer) != {"kind", "source"} or not isinstance(producer["kind"], str) \
            or producer["kind"] not in PRODUCERS \
            or not isinstance(producer["source"], str) or not producer["source"]:
        raise InputError(f"{name}: producer must be {{kind: external or derived, source}}")
    against = doc["derived_against"]
    if not isinstance(against, list) or not all(_is_identity(a) for a in against):
        raise InputError(f"{name}: derived_against must list payload identities (64 lowercase hex)")
    source = doc["derived_from"]
    changed = ()
    if source is not None:
        if not isinstance(source, dict) or set(source) != {"payload_id", "changed_channels"} or not _is_identity(source["payload_id"]):
            raise InputError(f"{name}: derived_from must be null or {{payload_id (64 lowercase hex), changed_channels}}")
        listed = source["changed_channels"]
        if not isinstance(listed, list) or not listed or not all(_is_count(c) for c in listed) or listed != sorted(set(listed)):
            raise InputError(f"{name}: derived_from.changed_channels must be ascending distinct channel IDs, at least one")
        if listed[-1] >= channels:
            raise InputError(f"{name}: derived_from names unknown channel {listed[-1]}")
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
    return Payload(step="gain", operation=operation, values=values, origin=doc["origin"], derived_against=tuple(against), round=round_,
                   identity=hashlib.sha256(content).hexdigest(), document=doc, format=FORMAT, channel_map=doc["channel_map"],
                   derived_from=None if source is None else source["payload_id"], changed_channels=changed)


def read_gain(content: bytes, name: str = "gain payload") -> Payload:
    """A gain payload in either format: calo-gain-payload/1, or the stage 1 calo-calibration-payload/1 with step gain."""
    try:
        doc = json.loads(content.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, ValueError):
        raise InputError(f"{name}: not a JSON payload of finite numbers") from None
    if isinstance(doc, dict) and doc.get("format") == FORMAT:
        return read(content, name)
    payload = read_payload(content, name)
    if payload.step != "gain":
        raise InputError(f"{name}: step {payload.step!r} is not a gain payload")
    return payload


def derive(parent_content: bytes, changes: dict, source: str) -> bytes:
    """A payload equal to the parent except the gains in `changes` ({channel: gain}); origin measured, producer derived, and
    derived_from naming the parent's content identity and the changed channels. Its own identity follows from its bytes."""
    parent = read(parent_content, "parent gain payload")
    channels = parent.values.size
    if not changes:
        raise InputError("derived gain payload: no channel changed")
    for channel, value in changes.items():
        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < channels:
            raise InputError(f"derived gain payload: unknown channel {channel}")
        if not _finite(value) or value <= 0:
            raise InputError(f"derived gain payload: the gain of channel {channel} must be positive and finite")
        if float(value) == float(parent.values[channel]):
            raise InputError(f"derived gain payload: channel {channel} keeps its gain: not a change")
    doc = json.loads(parent_content.decode("utf-8"))
    doc["gains"] = [[c, float(changes[c]) if c in changes else v] for c, v in doc["gains"]]
    doc["origin"] = "measured"
    doc["producer"] = {"kind": "derived", "source": source}
    doc["derived_from"] = {"payload_id": parent.identity, "changed_channels": sorted(changes)}
    doc["round"] = None
    content = _dumps(doc)
    read(content, "derived gain payload")
    return content


def check_derived(child: Payload, parent: Payload) -> None:
    """Refuses a payload that is not what it says: derived from `parent`, changed exactly in the channels it lists."""
    if child.derived_from is None or child.derived_from != parent.identity:
        raise InputError("gain payload: not derived from the parent payload given")
    if child.operation != parent.operation:
        raise InputError("gain payload: its role (multiply or divide) is not its parent's")
    if (child.channel_map, child.derived_against) != (parent.channel_map, parent.derived_against):
        raise InputError("gain payload: channel map or upstream chain differs from its parent's")
    differ = tuple(int(c) for c in numpy.flatnonzero(child.values != parent.values))
    if differ != child.changed_channels:
        raise InputError(f"gain payload: changed channels listed {list(child.changed_channels)}, changed in fact {list(differ)}")


def check_channel_map(payload: Payload, nx: int, ny: int, name: str) -> None:
    """Refuses a calo-gain-payload/1 keyed by another channel map than the grid's; a stage 1 payload has none and is checked
    by its channel count where it is applied."""
    if payload.channel_map is not None and payload.channel_map != channel_map_identity(nx, ny):
        raise InputError(f"{name}: made for another channel map than this {nx} x {ny} grid's ({CHANNEL_MAP_FORMAT}); refused, "
                         "never applied")
