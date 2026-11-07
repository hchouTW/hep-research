"""The data side of the T07 fixture files, as numpy layouts: the mirror of native/t07_data_file.*. Truth readers are in
t07_truth_files.py, which data-side code may not import (tests/adapters/test_acts_tracking.py).

A data file has role reconstruction-input and holds measurements only, on one grid, sorted by plane and position. Its promise (A09;
t04-prereg.md, "Truth reaches a data-side recipe") is that no field and no bit shortens the accepted search of section 3.2's four
integers: ALLOWED_DATA_FIELDS names every field, and data_file_defects refuses any other, and any coordinate off the grid. An event's
identity is its position in the file. Little-endian and packed. Each reader stops at a wrong magic, a wrong role and a short or
over-long file. Standard library and numpy only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy

DATA_MAGIC = b"T07HITS1"
DATA_ROLE = "reconstruction-input"
TRUTH_SUFFIX = ".t07truth"
HIT_GRID_STEPS_PER_MM = 2.0 ** 30  # t07_generation_constants.hpp states why

DATA_HEADER = numpy.dtype([("magic", "S8"), ("role", "S24"), ("event_count", "<u4"), ("sigma_loc0_mm", "<f8"), ("sigma_loc1_mm", "<f8")])
DATA_EVENT = numpy.dtype([("hit_count", "<u4")])
HIT = numpy.dtype([("hit_key", "<u4"), ("plane", "<u4"), ("loc0_mm", "<f8"), ("loc1_mm", "<f8")])
# Each allowed field and why a recipe may see it. Nothing else: no generator name, fixture id, block, stratum, event index, digest.
ALLOWED_DATA_FIELDS = {"header": {"magic": "format", "role": "reconstruction-input, a constant", "event_count": "file length",
                                  "sigma_loc0_mm": "measurement covariance (R33)", "sigma_loc1_mm": "measurement covariance (R33)"},
                       "event": {"hit_count": "file length"},
                       "hit": {"hit_key": "position in the event", "plane": "the measurement's surface", "loc0_mm": "the measurement",
                               "loc1_mm": "the measurement"}}


class FixtureFileError(ValueError):
    """The file is not what its reader accepts."""


def take_records(stream, layout: numpy.dtype, count: int, path) -> numpy.ndarray:
    raw = stream.read(layout.itemsize * count)
    if len(raw) != layout.itemsize * count:
        raise FixtureFileError(f"{path} ends inside a record")
    return numpy.frombuffer(raw, dtype=layout, count=count)


def on_hit_grid(coordinates):
    """The native rounding: to the nearest grid point, ties away from zero."""
    coordinates = numpy.asarray(coordinates, float)
    return numpy.sign(coordinates) * numpy.floor(numpy.abs(coordinates) * HIT_GRID_STEPS_PER_MM + 0.5) / HIT_GRID_STEPS_PER_MM + 0.0


def off_hit_grid(coordinates) -> int:
    """How many coordinates are not grid points."""
    steps = numpy.asarray(coordinates, float) * HIT_GRID_STEPS_PER_MM
    return int((steps != numpy.rint(steps)).sum())


def check_identity(fields, magic: bytes, role: str, path) -> None:
    if bytes(fields["magic"]) != magic:
        raise FixtureFileError(f"{path}: wrong magic")
    found_role = bytes(fields["role"]).decode()
    if found_role != role:
        raise FixtureFileError(f"{path}: role {found_role}, expected {role}")


def _data_header(stream, path) -> dict:
    fields = take_records(stream, DATA_HEADER, 1, path)[0]
    check_identity(fields, DATA_MAGIC, DATA_ROLE, path)
    return {"role": DATA_ROLE, "event_count": int(fields["event_count"]), "sigma_loc0_mm": float(fields["sigma_loc0_mm"]),
            "sigma_loc1_mm": float(fields["sigma_loc1_mm"])}


def assert_finished(stream, path) -> None:
    if stream.read(1):
        raise FixtureFileError(f"{path}: bytes after the last event")


def read_data_header(path) -> dict:
    with open(path, "rb") as stream:
        return _data_header(stream, path)


def iter_data_events(path):
    """Each event as {hits}, one at a time: a noise file does not fit in memory at full size."""
    with open(path, "rb") as stream:
        header = _data_header(stream, path)
        for _ in range(header["event_count"]):
            head = take_records(stream, DATA_EVENT, 1, path)[0]
            yield {"hits": take_records(stream, HIT, int(head["hit_count"]), path)}
        assert_finished(stream, path)


def data_file_defects(path, header_layout=DATA_HEADER, event_layout=DATA_EVENT, hit_layout=HIT) -> list:
    """Every way a data file holds more than ALLOWED_DATA_FIELDS. A layout with a new field is a defect, so is a byte outside the
    allowed fields: unused role padding, a hit key that is not a position, a coordinate off the grid, anything after the last event."""
    defects = [f"{name}: field {field} is not allowed" for name, layout in (("header", header_layout), ("event", event_layout), ("hit", hit_layout))
               for field in layout.names if field not in ALLOWED_DATA_FIELDS[name]]
    if defects:
        return defects
    raw = Path(path).read_bytes()
    if len(raw) < DATA_HEADER.itemsize:
        return ["the file is shorter than its header"]
    header = numpy.frombuffer(raw, dtype=DATA_HEADER, count=1)[0]
    if raw[8:32] != DATA_ROLE.encode().ljust(24, b"\0"):
        defects.append("role field holds more than the role")
    cursor = DATA_HEADER.itemsize
    for _ in range(int(header["event_count"])):
        if cursor + DATA_EVENT.itemsize > len(raw):
            return defects + ["the file ends inside an event"]
        hit_count = int(numpy.frombuffer(raw, dtype=DATA_EVENT, count=1, offset=cursor)[0]["hit_count"])
        cursor += DATA_EVENT.itemsize
        if cursor + hit_count * HIT.itemsize > len(raw):
            return defects + ["the file ends inside an event"]
        hits = numpy.frombuffer(raw, dtype=HIT, count=hit_count, offset=cursor)
        if not numpy.array_equal(hits["hit_key"], numpy.arange(hit_count)):
            defects.append("a hit key is not its position")
        if off_hit_grid(hits["loc0_mm"]) or off_hit_grid(hits["loc1_mm"]):
            defects.append("a coordinate is off the hit grid")
        cursor += hit_count * HIT.itemsize
    if cursor != len(raw):
        defects.append("bytes after the last event")
    return defects


def encode_data_file(sigma_mm: float, events) -> bytes:
    """A data file from a list of events, each a list of hits (plane, loc0, loc1) in file order. Tests use it."""
    header = numpy.zeros(1, dtype=DATA_HEADER)
    header["magic"], header["role"], header["event_count"] = DATA_MAGIC, DATA_ROLE.encode(), len(events)
    header["sigma_loc0_mm"] = header["sigma_loc1_mm"] = sigma_mm
    pieces = [header.tobytes()]
    for hits in events:
        head = numpy.zeros(1, dtype=DATA_EVENT)
        head["hit_count"] = len(hits)
        rows = numpy.zeros(len(hits), dtype=HIT)
        for hit_key, (plane, loc0_mm, loc1_mm) in enumerate(hits):
            rows[hit_key] = (hit_key, plane, loc0_mm, loc1_mm)
        pieces += [head.tobytes(), rows.tobytes()]
    return b"".join(pieces)


def hit_sets_text(data_sha256: str, hit_sets) -> str:
    """acts-tracking-hit-sets/1 from [(track_key, event_ordinal, assumed_q_over_p, hit_keys)]. Role truth-assisted."""
    lines = ["acts-tracking-hit-sets/1", "role truth-assisted", f"data_sha256 {data_sha256}"]
    for track_key, event_ordinal, assumed_q_over_p, hit_keys in hit_sets:
        keys = " ".join(str(key) for key in hit_keys)
        lines.append(f"hit_set {track_key} {event_ordinal} {assumed_q_over_p!r} {len(hit_keys)} {keys}")
    return "\n".join(lines) + "\n"


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
