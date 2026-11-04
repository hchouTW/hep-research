"""Rotations (Section 6.2.5). Specifications give active rotations; G4PVPlacement needs the passive matrix, its transpose.

S1 and S2 accept multiples of 90 degrees only, as exact integer matrices; every other angle is refused here until S3 opens it
together with the checks for rotated placements.
"""
from __future__ import annotations

from decimal import Decimal

from core.geometry.numbers import CONTEXT, GeometryError

IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
_QUARTER = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}  # quarter turns: cos, sin


def _quarter_turns(angle_deg: Decimal, path: str) -> int:
    turns = CONTEXT.divide(angle_deg, Decimal(90))
    if turns != turns.to_integral_value():
        raise GeometryError("rotation-angle", f"{angle_deg} degrees is not a multiple of 90; other angles open in S3", path)
    return int(turns) % 4


def _about(axis: str, turns: int):
    c, s = _QUARTER[turns]
    return {"x": ((1, 0, 0), (0, c, -s), (0, s, c)), "y": ((c, 0, s), (0, 1, 0), (-s, 0, c)),
            "z": ((c, -s, 0), (s, c, 0), (0, 0, 1))}[axis]


def product(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def active_matrix(rotation, path: str = ""):
    """The integer matrix of an active rotation: {"zyx_deg": [z, y, x]} applied as Rz Ry Rx, or {"axis": "x"|"y"|"z",
    "angle_deg": a}; None is the identity. The angles are exact Decimals."""
    if rotation is None:
        return IDENTITY
    if set(rotation) == {"zyx_deg"}:
        z, y, x = (_quarter_turns(angle, path) for angle in rotation["zyx_deg"])
        return product(product(_about("z", z), _about("y", y)), _about("x", x))
    if set(rotation) == {"axis", "angle_deg"}:
        if rotation["axis"] not in ("x", "y", "z"):
            raise GeometryError("rotation-axis", f"axis {rotation['axis']!r}: S1 accepts a coordinate axis", path)
        return _about(rotation["axis"], _quarter_turns(rotation["angle_deg"], path))
    raise GeometryError("rotation-form", f"{sorted(rotation)} is not a rotation", path)


def passive_matrix(active):
    return transpose(active)


def rotate(matrix, vector):
    """matrix applied to a vector of Decimals: exact, because the matrix holds 0 and +-1 only."""
    return tuple(sum((row[i] * vector[i] for i in range(3)), Decimal(0)) for row in matrix)
