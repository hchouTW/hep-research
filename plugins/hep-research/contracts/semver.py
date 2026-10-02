"""Tiny SemVer helpers: parse 'MAJOR.MINOR.PATCH' and check ranges like '>=1.0,<2.0'."""
from __future__ import annotations

import re

_V = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_C = re.compile(r"^(>=|<=|>|<|==)?\s*(\d+(?:\.\d+){0,2})$")


def parse(v: str) -> tuple[int, int, int]:
    m = _V.match(str(v).strip())
    if not m:
        raise ValueError(f"not a version: {v!r}")
    return tuple(int(x or 0) for x in m.groups())  # type: ignore[return-value]


def satisfies(version: str, spec: str) -> bool:
    v = parse(version)
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        m = _C.match(part)
        if not m:
            raise ValueError(f"bad version constraint: {part!r}")
        op, ref = m.group(1) or "==", parse(m.group(2))
        if not {">=": v >= ref, "<=": v <= ref, ">": v > ref, "<": v < ref, "==": v == ref}[op]:
            return False
    return True


def valid_spec(spec: str) -> bool:
    try:
        satisfies("0.0.0", spec)
        return True
    except ValueError:
        return False
