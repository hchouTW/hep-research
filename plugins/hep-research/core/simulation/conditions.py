"""Condition snapshots (g4sim plan, Section 17, S9): conditions that do not change the geometry, for the response layer only.

A condition-snapshot/1 holds, for one readout system, versioned tables indexed by intervals of validity [start_ns, end_ns) of the run's
clock. A row names a cell as a dictionary of the readout's field values and gives what the response needs: gain_factor (multiplies the
sensor gain), threshold (replaces the electronics threshold), dead (the channel reads nothing), temperature_K (recorded, for a stage that
uses it). A cell no row names takes the snapshot's defaults. Events carry times, and the response looks conditions up by time (`at`).
IOVs may not overlap, and a time no IOV covers is an error, never a silent default. Pure computation: files are read by the caller.
"""
from __future__ import annotations

SCHEMA = "condition-snapshot/1"
QUANTITIES = ("gain_factor", "threshold", "dead", "temperature_K")
DEFAULTS = {"gain_factor": 1.0, "dead": False}


class ConditionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _cell_key(cell: dict) -> tuple:
    return tuple(sorted(cell.items()))


def check_snapshot(snapshot: dict, fields=None) -> None:
    """IOVs in order, non-empty and not overlapping (Section 15.1, S9); each row's cell names exactly the readout's fields, once per IOV."""
    if snapshot.get("schema") != SCHEMA:
        raise ConditionError("schema", f"{snapshot.get('schema')!r} is not {SCHEMA}")
    intervals = sorted((iov["start_ns"], iov["end_ns"], at) for at, iov in enumerate(snapshot["iovs"]))
    for start, end, at in intervals:
        if end <= start:
            raise ConditionError("iov-empty", f"IOV {at} is [{start}, {end}): empty")
    for (start_a, end_a, a), (start_b, _, b) in zip(intervals, intervals[1:]):
        if start_b < end_a:
            raise ConditionError("iov-overlap", f"IOVs {a} [{start_a}, {end_a}) and {b} from {start_b} overlap")
    wanted = set(fields) if fields is not None else None
    for at, iov in enumerate(snapshot["iovs"]):
        seen = set()
        for row in iov["rows"]:
            if wanted is not None and set(row["cell"]) != wanted:
                raise ConditionError("cell-fields", f"IOV {at}: a cell names {sorted(row['cell'])}, the readout's fields are {sorted(wanted)}")
            key = _cell_key(row["cell"])
            if key in seen:
                raise ConditionError("cell-twice", f"IOV {at}: cell {row['cell']} has two rows")
            seen.add(key)


def iov_at(snapshot: dict, time_ns: int) -> dict:
    for iov in snapshot["iovs"]:
        if iov["start_ns"] <= time_ns < iov["end_ns"]:
            return iov
    raise ConditionError("no-iov", f"no IOV covers time {time_ns} ns")


def at(snapshot: dict, time_ns: int, cell: dict) -> dict:
    """The conditions of a cell at a time: its row in the IOV that covers the time, over the snapshot's defaults and DEFAULTS."""
    values = {**DEFAULTS, **snapshot.get("defaults", {})}
    key = _cell_key(cell)
    for row in iov_at(snapshot, time_ns)["rows"]:
        if _cell_key(row["cell"]) == key:
            values.update({name: row[name] for name in QUANTITIES if name in row})
            break
    return values
