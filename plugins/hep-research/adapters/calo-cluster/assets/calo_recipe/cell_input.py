"""Inputs of the recipe: the calo-cells/1 readout (role reconstruction-input) and calo-calibration-payload/1 (role conditions).

calo-cells/1, little-endian: the magic CALOCEL1; a u32 header length and that many bytes of JSON; then, for N events on an
nx x ny grid in C order (array axis 0 is ix, so the flat index is ix * ny + iy, section 7.1), N*nx*ny float64 raw values,
N*nx*ny uint8 live flags and N*nx*ny uint8 saturated flags. The header holds exactly HEADER_KEYS. An event is its position in
the file. Nothing else is in the file: no truth, seed, stratum, block, fixture or generator name (t04-values-v4.md section 3.1).

A dead cell (live 0) has no value: its raw value must be NaN and its saturated flag 0, so absence is never read as zero
(t04-prereg.md, "Absent data reported as zero"). The readout kind must be "analog": any other kind is refused with a named
error, never read as analog (section 9.2, negative case "digital read as analog"). The saturated flag is the readout's own,
set before gain (section 4.2): the chain carries it and never sets it.

calo-calibration-payload/1 is a JSON object with exactly PAYLOAD_KEYS. Its identity is the SHA-256 of its bytes (by content,
not by tag; plan R32). `operation` states the role of the constant in the chain: the pedestal is subtracted; a gain multiplies
(E = c (ADC - pedestal)) or divides (E = (ADC - pedestal) / g). `value` is one number for every channel or a list of one
number per channel, by flat index. `derived_against` lists the identities of the upstream payloads assumed when it was made,
in chain order; the chain refuses a payload bound on top of another chain (R32).
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy

CELLS_MAGIC = b"CALOCEL1"
CELLS_FORMAT = "calo-cells/1"
CELLS_ROLE = "reconstruction-input"
READOUT_KIND = "analog"
HEADER_KEYS = {"format", "role", "readout", "nx", "ny", "events", "raw_unit"}

PAYLOAD_FORMAT = "calo-calibration-payload/1"
PAYLOAD_KEYS = {"format", "role", "step", "operation", "channels", "value", "unit", "origin", "producer", "derived_against", "round"}
STEP_OPERATIONS = {"pedestal": {"subtract"}, "gain": {"multiply", "divide"}}
ORIGINS = {"nominal", "measured"}


class InputError(ValueError):
    """An input is refused: the reason names the input and the defect."""


@dataclass(frozen=True)
class Readout:
    raw: numpy.ndarray        # (N, nx, ny) float64
    live: numpy.ndarray       # (N, nx, ny) bool
    saturated: numpy.ndarray  # (N, nx, ny) bool
    header: dict
    sha256: str

    @property
    def events(self) -> int:
        return self.raw.shape[0]


@dataclass(frozen=True)
class Payload:
    step: str
    operation: str
    values: numpy.ndarray     # one per channel, by flat index
    origin: str
    derived_against: tuple
    round: int | None
    identity: str
    document: dict


def cells_bytes(raw, live, saturated, raw_unit: str = "adc", readout: str = READOUT_KIND) -> bytes:
    """A calo-cells/1 file. raw, live, saturated: arrays of shape (N, nx, ny)."""
    raw = numpy.ascontiguousarray(raw, dtype="<f8")
    live = numpy.ascontiguousarray(live, dtype=bool)
    saturated = numpy.ascontiguousarray(saturated, dtype=bool)
    if raw.ndim != 3 or live.shape != raw.shape or saturated.shape != raw.shape:
        raise InputError("raw, live and saturated must share one shape (events, nx, ny)")
    header = {"format": CELLS_FORMAT, "role": CELLS_ROLE, "readout": readout, "nx": int(raw.shape[1]), "ny": int(raw.shape[2]),
              "events": int(raw.shape[0]), "raw_unit": raw_unit}
    text = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return (CELLS_MAGIC + struct.pack("<I", len(text)) + text + raw.tobytes() + live.astype("u1").tobytes()
            + saturated.astype("u1").tobytes())


def read_cells(content: bytes, name: str = "readout") -> Readout:
    if content[:8] != CELLS_MAGIC:
        raise InputError(f"{name}: not a {CELLS_FORMAT} file (magic)")
    if len(content) < 12:
        raise InputError(f"{name}: truncated header")
    (length,) = struct.unpack("<I", content[8:12])
    try:
        header = json.loads(content[12:12 + length].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise InputError(f"{name}: header is not JSON") from None
    if not isinstance(header, dict) or set(header) != HEADER_KEYS:
        raise InputError(f"{name}: header keys must be exactly {sorted(HEADER_KEYS)}")
    if header["format"] != CELLS_FORMAT:
        raise InputError(f"{name}: format {header['format']!r} is not {CELLS_FORMAT}")
    if header["role"] != CELLS_ROLE:
        raise InputError(f"{name}: role {header['role']!r} is not {CELLS_ROLE}; a truth or reference file is never read as data")
    if header["readout"] != READOUT_KIND:
        raise InputError(f"{name}: readout kind {header['readout']!r} refused: this recipe reads analog cells only and never reads "
                         "another kind as analog")
    for key in ("nx", "ny", "events"):
        if isinstance(header[key], bool) or not isinstance(header[key], int) or header[key] < (0 if key == "events" else 1):
            raise InputError(f"{name}: header {key} must be a count")
    n, nx, ny = header["events"], header["nx"], header["ny"]
    cells = n * nx * ny
    body = 12 + length
    if len(content) != body + cells * 10:
        raise InputError(f"{name}: {len(content)} bytes, expected {body + cells * 10} for {n} events of {nx} x {ny} cells")
    raw = numpy.frombuffer(content, dtype="<f8", count=cells, offset=body).reshape(n, nx, ny).astype(float)
    flags = numpy.frombuffer(content, dtype="u1", count=2 * cells, offset=body + 8 * cells)
    if numpy.any(flags > 1):
        raise InputError(f"{name}: a live or saturated flag is neither 0 nor 1")
    live = flags[:cells].reshape(n, nx, ny).astype(bool)
    saturated = flags[cells:].reshape(n, nx, ny).astype(bool)
    if not numpy.all(numpy.isfinite(raw[live])):
        raise InputError(f"{name}: a live cell has no finite raw value")
    if not numpy.all(numpy.isnan(raw[~live])):
        raise InputError(f"{name}: a dead cell carries a raw value; a dead cell has none (NaN), never zero")
    if numpy.any(saturated & ~live):
        raise InputError(f"{name}: a dead cell is flagged saturated")
    return Readout(raw=raw, live=live, saturated=saturated, header=header, sha256=hashlib.sha256(content).hexdigest())


def payload_bytes(step: str, operation: str, value, channels: int, unit: str, origin: str, source: str,
                  derived_against=(), round_=None) -> bytes:
    """A calo-calibration-payload/1 file from an external source (synthetic constants here; plan R31: none is derived)."""
    doc = {"format": PAYLOAD_FORMAT, "role": "conditions", "step": step, "operation": operation, "channels": channels,
           "value": value, "unit": unit, "origin": origin, "producer": {"kind": "external", "source": source},
           "derived_against": list(derived_against), "round": round_}
    return (json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")


def _finite_number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def read_payload(content: bytes, name: str = "payload") -> Payload:
    try:
        doc = json.loads(content.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, ValueError):
        raise InputError(f"{name}: not a JSON payload of finite numbers") from None
    if not isinstance(doc, dict) or set(doc) != PAYLOAD_KEYS:
        raise InputError(f"{name}: payload keys must be exactly {sorted(PAYLOAD_KEYS)}")
    if doc["format"] != PAYLOAD_FORMAT or doc["role"] != "conditions":
        raise InputError(f"{name}: not a {PAYLOAD_FORMAT} conditions payload")
    if doc["step"] not in STEP_OPERATIONS or doc["operation"] not in STEP_OPERATIONS[doc["step"]]:
        raise InputError(f"{name}: step {doc['step']!r} with operation {doc['operation']!r} is not a chain step this recipe knows")
    if doc["origin"] not in ORIGINS:
        raise InputError(f"{name}: origin must be nominal or measured")
    producer = doc["producer"]
    if not isinstance(producer, dict) or producer.get("kind") != "external" or not producer.get("source") or len(producer) != 2:
        raise InputError(f"{name}: producer must be external with its source named")
    channels = doc["channels"]
    if isinstance(channels, bool) or not isinstance(channels, int) or channels < 1:
        raise InputError(f"{name}: channels must be a count")
    value = doc["value"]
    if _finite_number(value):
        values = numpy.full(channels, float(value))
    elif isinstance(value, list) and len(value) == channels and all(_finite_number(v) for v in value):
        values = numpy.array(value, dtype=float)
    else:
        raise InputError(f"{name}: value must be one finite number or one per channel ({channels})")
    if doc["step"] == "gain" and not numpy.all(values > 0):
        raise InputError(f"{name}: a gain must be positive")
    against = doc["derived_against"]
    if not isinstance(against, list) or not all(isinstance(a, str) and len(a) == 64 and set(a) <= set("0123456789abcdef") for a in against):
        raise InputError(f"{name}: derived_against must list payload identities (64 lowercase hex)")
    round_ = doc["round"]
    if round_ is not None and (isinstance(round_, bool) or not isinstance(round_, int) or round_ < 0):
        raise InputError(f"{name}: round must be null or a count")
    return Payload(step=doc["step"], operation=doc["operation"], values=values, origin=doc["origin"],
                   derived_against=tuple(against), round=round_, identity=hashlib.sha256(content).hexdigest(), document=doc)


def read_file(path, reader, name: str):
    try:
        content = Path(path).read_bytes()
    except OSError as exc:
        raise InputError(f"{name}: cannot be read: {exc.strerror}") from None
    return reader(content, name)
