"""Shared input checks for core/stats (private; standard library only). Each takes the caller's error class, so a
module still raises its own named error (DiagnosticsError, LikelihoodError, ToyError)."""
from __future__ import annotations

import math


def number(x, name: str, low=None, high=None, strict_low: bool = False, *, error: type[Exception] = ValueError) -> float:
    """A finite number, optionally within [low, high] (or (low, high] with strict_low), as a float."""
    ok = isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    if not ok:
        raise error(f"{name} must be a finite number, got {x!r}")
    if low is not None and (x < low or (strict_low and x == low)):
        raise error(f"{name} must be {'>' if strict_low else '>='} {low}, got {x!r}")
    if high is not None and x > high:
        raise error(f"{name} must be <= {high}, got {x!r}")
    return float(x)


def seed(value, *, error: type[Exception] = ValueError) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise error("seed must be an integer and must be recorded")
    return value


def toy_count(value, low: int, high: int, *, error: type[Exception] = ValueError, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not ((allow_zero and value == 0) or low <= value <= high):
        raise error(f"toys must be an integer in [{low}, {high}]" + (" or 0" if allow_zero else ""))
    return value
