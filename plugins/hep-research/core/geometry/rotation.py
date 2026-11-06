"""Rotations (Section 6.2.5). Specifications give active rotations; G4PVPlacement needs the passive matrix, its transpose.

Multiples of 90 degrees stay exact integer matrices, so their geometry_id does not change. Any other angle (S3) has its sine and
cosine computed with 40 digits and rounded to 34 (Section 7.3, item 6); core/geometry/convex.py judges such placements.
"""
from __future__ import annotations

import decimal
from decimal import Decimal

from core.geometry.numbers import CONTEXT, GeometryError

IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
_QUARTER = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}  # quarter turns: cos, sin
_WIDE = decimal.Context(prec=45, rounding=decimal.ROUND_HALF_EVEN, Emin=-999999, Emax=999999, traps=[decimal.InvalidOperation, decimal.DivisionByZero])
_PI = Decimal("3.14159265358979323846264338327950288419716939937510582097494")


def _series(radians: Decimal, start: Decimal, power: int) -> Decimal:
    """The Taylor series of sin (power 1) or cos (power 0), in 45 digits, with |radians| at most pi / 4 after reduction."""
    term, total, n = start, start, power
    while abs(term) > Decimal("1e-50"):
        term = _WIDE.divide(_WIDE.minus(_WIDE.multiply(_WIDE.multiply(term, radians), radians)), Decimal((n + 1) * (n + 2)))
        total = _WIDE.add(total, term)
        n += 2
    return total


def cos_sin(angle_deg: Decimal) -> tuple:
    """Cosine and sine of an angle, rounded to 34 digits; multiples of 90 degrees are exact."""
    turns = _WIDE.divide(angle_deg, Decimal(90))
    nearest = int(turns.to_integral_value(rounding=decimal.ROUND_HALF_EVEN))
    rest = _WIDE.multiply(_WIDE.subtract(turns, Decimal(nearest)), _WIDE.divide(_PI, Decimal(2)))
    c, s = _series(rest, Decimal(1), 0), _series(rest, rest, 1)
    c, s = {0: (c, s), 1: (_WIDE.minus(s), c), 2: (_WIDE.minus(c), _WIDE.minus(s)), 3: (s, _WIDE.minus(c))}[nearest % 4]
    return CONTEXT.plus(c), CONTEXT.plus(s)


def _turn(angle_deg: Decimal):
    """(cos, sin): integers for a multiple of 90 degrees, Decimals for any other angle."""
    turns = CONTEXT.divide(angle_deg, Decimal(90))
    if turns == turns.to_integral_value():
        return _QUARTER[int(turns) % 4]
    return cos_sin(angle_deg)


def is_exact(matrix) -> bool:
    """True for a matrix of 0 and +-1: a rotation by multiples of 90 degrees."""
    return all(isinstance(value, int) for row in matrix for value in row)


def _about(axis: str, angle_deg: Decimal):
    c, s = _turn(angle_deg)
    return {"x": ((1, 0, 0), (0, c, -s), (0, s, c)), "y": ((c, 0, s), (0, 1, 0), (-s, 0, c)),
            "z": ((c, -s, 0), (s, c, 0), (0, 0, 1))}[axis]


def _times(a, b):
    return a * b if isinstance(a, int) and isinstance(b, int) else CONTEXT.multiply(Decimal(a), Decimal(b))


def _plus(a, b):
    return a + b if isinstance(a, int) and isinstance(b, int) else CONTEXT.add(Decimal(a), Decimal(b))


def product(a, b):
    out = []
    for i in range(3):
        row = []
        for j in range(3):
            value = 0
            for k in range(3):
                value = _plus(value, _times(a[i][k], b[k][j]))
            row.append(value)
        out.append(tuple(row))
    return tuple(out)


def transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def active_matrix(rotation, path: str = ""):
    """The matrix of an active rotation: {"zyx_deg": [z, y, x]} applied as Rz Ry Rx, or {"axis": "x"|"y"|"z",
    "angle_deg": a}; None is the identity. The angles are exact Decimals."""
    if rotation is None:
        return IDENTITY
    if set(rotation) == {"zyx_deg"}:
        z, y, x = rotation["zyx_deg"]
        return product(product(_about("z", z), _about("y", y)), _about("x", x))
    if set(rotation) == {"axis", "angle_deg"}:
        if rotation["axis"] not in ("x", "y", "z"):
            raise GeometryError("rotation-axis", f"axis {rotation['axis']!r}: S1 accepts a coordinate axis", path)
        return _about(rotation["axis"], rotation["angle_deg"])
    raise GeometryError("rotation-form", f"{sorted(rotation)} is not a rotation", path)


def passive_matrix(active):
    return transpose(active)


def rotate(matrix, vector):
    """matrix applied to a vector of Decimals, in 34 digits; exact when the matrix holds 0 and +-1 only."""
    out = []
    for row in matrix:
        value = Decimal(0)
        for i in range(3):
            value = CONTEXT.add(value, CONTEXT.multiply(Decimal(row[i]), vector[i]))
        out.append(value)
    return tuple(out)
