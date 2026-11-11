"""The readout light-readout/1 (role reconstruction-input): per event and channel the state, the summed charge, the first-arrival
time and the readout's saturated flag, side by side.

Little-endian: the magic LIGHTRD1; a u32 header length and that many bytes of JSON (sorted keys); then for N events of C
channels: N*C int8 states, N*C float64 charges, N*C float64 times, N*C uint8 saturated flags. The header holds exactly
HEADER_KEYS: no truth, seed, stratum, block, fixture or generator name (t04-values-v4.md section 3.1). An event is its position
in the file; a channel is its position in the event (the stable channel ID, the lattice index of section 4.3).

States (case O-states of the D3 stage 1 report): LIVE_HIT, LIVE_UNHIT, DEAD and DISABLED. Live channels are hit or unhit by the
one threshold the header states (`threshold`): a hit has a charge at or above it and a finite time; an unhit live channel has
charge 0 and no time (NaN). A dead or disabled channel has no value (NaN charge and time), so absence is never read as zero
(t04-prereg.md, "Absent data reported as zero"), and it is never unhit. `saturation_charge` is the readout's clip value C, or
null for a readout that does not saturate: a flagged channel reads exactly C, an unflagged hit reads below C, and no flag is
allowed without C (case O-saturation). The charge unit is the single-photoelectron mean charge, the time unit ns.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy

MAGIC = b"LIGHTRD1"
FORMAT = "light-readout/1"
ROLE = "reconstruction-input"
CHARGE_UNIT = "single-photoelectron mean charge"
TIME_UNIT = "ns"
HEADER_KEYS = {"format", "role", "channels", "events", "charge_unit", "time_unit", "threshold", "saturation_charge"}
LIVE_UNHIT, LIVE_HIT, DEAD, DISABLED = 0, 1, 2, 3
STATE_NAMES = {LIVE_UNHIT: "live-unhit", LIVE_HIT: "live-hit", DEAD: "dead", DISABLED: "disabled"}


class ReadoutError(ValueError):
    """The readout is refused: the reason names the defect."""


@dataclass(frozen=True)
class Readout:
    state: numpy.ndarray      # (N, C) int8
    charge: numpy.ndarray     # (N, C) float64
    time: numpy.ndarray       # (N, C) float64
    saturated: numpy.ndarray  # (N, C) bool
    header: dict
    sha256: str

    @property
    def events(self) -> int:
        return self.state.shape[0]

    @property
    def channels(self) -> int:
        return self.state.shape[1]


def check_arrays(state, charge, time, saturated, threshold, saturation_charge) -> None:
    """Every rule of the format on one block of events (any leading shape). time None: the charge rules only (an event as the
    charge-only likelihood sees it)."""
    state = numpy.asarray(state)
    known = numpy.isin(state, list(STATE_NAMES))
    if not known.all():
        raise ReadoutError(f"unknown channel state {sorted(set(state[~known].tolist()))}")
    hit = state == LIVE_HIT
    unhit = state == LIVE_UNHIT
    absent = (state == DEAD) | (state == DISABLED)
    if not numpy.all(numpy.isnan(charge[absent])) or (time is not None and not numpy.all(numpy.isnan(time[absent]))):
        raise ReadoutError("a dead or disabled channel carries a charge or a time; it has no value")
    if numpy.any(saturated[absent]):
        raise ReadoutError("a dead or disabled channel is flagged saturated")
    if not numpy.all(charge[unhit] == 0.0) or (time is not None and not numpy.all(numpy.isnan(time[unhit]))):
        raise ReadoutError("a live unhit channel must read charge 0 and no time")
    if numpy.any(saturated[unhit]):
        raise ReadoutError("a live unhit channel is flagged saturated")
    hit_charge = charge[hit]
    if not numpy.all(numpy.isfinite(hit_charge)) or (time is not None and not numpy.all(numpy.isfinite(time[hit]))):
        raise ReadoutError("a hit channel needs a finite charge and time")
    if numpy.any(hit_charge < threshold):
        raise ReadoutError(f"a hit channel reads below the threshold {threshold}")
    if saturation_charge is None:
        if numpy.any(saturated):
            raise ReadoutError("a channel is flagged saturated in a readout with no saturation value")
        return
    flagged = saturated[hit]
    if numpy.any(hit_charge[flagged] != saturation_charge):
        raise ReadoutError(f"a saturated channel must read the saturation value {saturation_charge}")
    if numpy.any(hit_charge[~flagged] >= saturation_charge):
        raise ReadoutError(f"an unflagged channel reads at or above the saturation value {saturation_charge}")


def _check_scalars(threshold, saturation_charge) -> None:
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
        raise ReadoutError("threshold must be a positive finite number")
    if saturation_charge is not None:
        if isinstance(saturation_charge, bool) or not isinstance(saturation_charge, (int, float)) \
                or not math.isfinite(saturation_charge) or saturation_charge <= threshold:
            raise ReadoutError("saturation_charge must be null or a finite number above the threshold")


def readout_bytes(state, charge, time, saturated, threshold, saturation_charge, check: bool = True) -> bytes:
    """Encode N events. check=False writes a defective file, for tests of the reader only."""
    state = numpy.ascontiguousarray(state, numpy.int8)
    charge = numpy.ascontiguousarray(charge, "<f8")
    time = numpy.ascontiguousarray(time, "<f8")
    saturated = numpy.ascontiguousarray(saturated, numpy.uint8)
    if state.ndim != 2 or not (state.shape == charge.shape == time.shape == saturated.shape):
        raise ReadoutError("state, charge, time and saturated must share one (events, channels) shape")
    if check:
        _check_scalars(threshold, saturation_charge)
        check_arrays(state, charge, time, saturated.astype(bool), threshold, saturation_charge)
    header = {"format": FORMAT, "role": ROLE, "channels": int(state.shape[1]), "events": int(state.shape[0]),
              "charge_unit": CHARGE_UNIT, "time_unit": TIME_UNIT, "threshold": float(threshold),
              "saturation_charge": None if saturation_charge is None else float(saturation_charge)}
    text = json.dumps(header, sort_keys=True).encode("utf-8")
    return MAGIC + struct.pack("<I", len(text)) + text + state.tobytes() + charge.tobytes() + time.tobytes() + saturated.tobytes()


def read_bytes(content: bytes) -> Readout:
    if len(content) < 12 or content[:8] != MAGIC:
        raise ReadoutError(f"not a {FORMAT} file (magic)")
    (length,) = struct.unpack("<I", content[8:12])
    try:
        header = json.loads(content[12:12 + length].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ReadoutError("header is not JSON") from None
    if not isinstance(header, dict) or set(header) != HEADER_KEYS:
        raise ReadoutError(f"header keys must be exactly {sorted(HEADER_KEYS)}")
    if header["format"] != FORMAT or header["role"] != ROLE:
        raise ReadoutError(f"format must be {FORMAT} and role {ROLE}")
    if header["charge_unit"] != CHARGE_UNIT or header["time_unit"] != TIME_UNIT:
        raise ReadoutError("charge or time unit is not the format's")
    events, channels = header["events"], header["channels"]
    for name, value in (("events", events), ("channels", channels)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ReadoutError(f"{name} must be a positive integer")
    _check_scalars(header["threshold"], header["saturation_charge"])
    size = events * channels
    body = content[12 + length:]
    if len(body) != size * 18:
        raise ReadoutError(f"body holds {len(body)} bytes, {size * 18} expected for {events} events of {channels} channels")
    shape = (events, channels)
    state = numpy.frombuffer(body, numpy.int8, size, 0).reshape(shape).copy()
    charge = numpy.frombuffer(body, "<f8", size, size).reshape(shape).astype(float)
    time = numpy.frombuffer(body, "<f8", size, 9 * size).reshape(shape).astype(float)
    flags = numpy.frombuffer(body, numpy.uint8, size, 17 * size).reshape(shape)
    if numpy.any(flags > 1):
        raise ReadoutError("a saturated flag is neither 0 nor 1")
    saturated = flags.astype(bool)
    check_arrays(state, charge, time, saturated, header["threshold"], header["saturation_charge"])
    return Readout(state, charge, time, saturated, header, hashlib.sha256(content).hexdigest())


def read_file(path) -> Readout:
    try:
        content = Path(path).read_bytes()
    except OSError as exc:
        raise ReadoutError(f"readout cannot be read: {exc.strerror}") from None
    return read_bytes(content)
