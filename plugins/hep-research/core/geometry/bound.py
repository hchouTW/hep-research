"""The double-precision error bound of a placement chain (Section 7.3, item 7): B = (1 + sum k_i) ulp(X).

k_i is 1 for a translation level and for a rotation by a multiple of 90 degrees, and 10 for an arbitrary rotation. X is the
largest absolute coordinate on the chain, solid half-lengths included. GB10 measures the coefficients.
"""
from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction

TRANSLATION_COEFFICIENT = 1
ROTATION_COEFFICIENT = 10


def error_bound(largest_coordinate_mm: Decimal, arbitrary_rotation_levels: list[bool]) -> Fraction:
    """B in mm, exactly; one entry per level of the chain, true for a level with an arbitrary rotation."""
    total = 1 + sum(ROTATION_COEFFICIENT if rotated else TRANSLATION_COEFFICIENT for rotated in arbitrary_rotation_levels)
    return total * Fraction(math.ulp(float(abs(largest_coordinate_mm))))
