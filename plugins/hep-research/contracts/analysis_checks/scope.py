"""Bounded scope grammar (v6.3 C5): 'axis:value/axis:value' over a finite value domain per axis.

parse_scope checks the syntax, unknown axes, values outside the domain and repeated axes; axes are compared after
sorting. A missing axis is insufficient information, never a wildcard: compare_scopes returns 'unknown' when one side
names an axis the other lacks, 'invalid' when either side does not parse."""
from __future__ import annotations

import re

PART = re.compile(r"^([a-z][a-z0-9_-]*):([A-Za-z0-9][A-Za-z0-9_.+-]*)$")


def parse_scope(text, axes: dict) -> dict:
    """{"ok", "axes": {axis: value}, "errors": [codes]} for one scope string."""
    errors: list[str] = []
    out: dict[str, str] = {}
    if not isinstance(text, str) or not text:
        return {"ok": False, "axes": {}, "errors": ["scope.bad_syntax"]}
    for part in text.split("/"):
        m = PART.match(part)
        if not m:
            errors.append("scope.bad_syntax")
            continue
        axis, value = m.groups()
        if axis in out:
            errors.append("scope.repeated_axis")
        elif axis not in axes:
            errors.append("scope.unknown_axis")
        elif value not in axes[axis]:
            errors.append("scope.unknown_value")
        out.setdefault(axis, value)
    return {"ok": not errors, "axes": dict(sorted(out.items())) if not errors else {}, "errors": sorted(set(errors))}


def canonical_scope(text, axes: dict) -> str | None:
    res = parse_scope(text, axes)
    return "/".join(f"{k}:{v}" for k, v in res["axes"].items()) if res["ok"] else None


def compare_scopes(a, b, axes: dict) -> str:
    """'equal', 'different' (some shared axis differs), 'unknown' (an axis present on one side only) or 'invalid'."""
    pa, pb = parse_scope(a, axes), parse_scope(b, axes)
    if not (pa["ok"] and pb["ok"]):
        return "invalid"
    xa, xb = pa["axes"], pb["axes"]
    if any(xa[k] != xb[k] for k in set(xa) & set(xb)):
        return "different"
    return "equal" if set(xa) == set(xb) else "unknown"
