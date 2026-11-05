"""Exact decimal arithmetic of the geometry (Section 7.3): 34 significant digits, round-half-even, the same on every
platform, and the limits every rule is written against. All arithmetic runs in CONTEXT, never in the ambient context."""
from __future__ import annotations

import decimal
from decimal import Decimal

from core.canonical import normalize_decimal

PRECISION = 34
CONTEXT = decimal.Context(prec=PRECISION, rounding=decimal.ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals=1, clamp=0,
                          flags=[], traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow])
EPSILON_MM = Decimal("1e-20")  # arithmetic floor: closer faces are the same face
MINIMUM_GAP_MM = Decimal("1e-6")  # c: faces that do not coincide are at least this far apart
MINIMUM_FEATURE_MM = Decimal("1e-5")  # 10 c
BOUND_LIMIT_MM = Decimal("1e-10")  # B: one fifth of the half tolerance


class GeometryError(ValueError):
    """A geometry refused by a rule; code is a stable name and path says where."""

    def __init__(self, code: str, message: str, path: str = ""):
        super().__init__(f"{path}: {message}" if path else message)
        self.code = code
        self.path = path


def exact(text) -> Decimal:
    """A decimal/1 string as a Decimal, every digit kept."""
    return Decimal(text)


def as_text(value: Decimal) -> str:
    """The decimal/1 string of a computed value, written directly with no quantization."""
    return normalize_decimal(str(value))


def add(a: Decimal, b: Decimal) -> Decimal:
    return CONTEXT.add(a, b)


def subtract(a: Decimal, b: Decimal) -> Decimal:
    return CONTEXT.subtract(a, b)


def multiply(a: Decimal, b: Decimal) -> Decimal:
    return CONTEXT.multiply(a, b)


def divide(a: Decimal, b: Decimal) -> Decimal:
    return CONTEXT.divide(a, b)
