"""Tiny SemVer helpers: parse 'MAJOR.MINOR.PATCH' and check ranges like '>=1.0,<2.0'.

parse and satisfies read release versions only (a range never admits a pre-release). parse_full, is_prerelease and
precedence read full SemVer 2.0.0 versions with a pre-release ('1.1.0-dev.1'; build metadata is not accepted), for
the cross-artifact check's rule and suite versions (architecture section 8.1, release R2)."""
from __future__ import annotations

import re

_V = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_C = re.compile(r"^(>=|<=|>|<|==)?\s*(\d+(?:\.\d+){0,2})$")
_ID = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
_FULL = re.compile(rf"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-({_ID}(?:\.{_ID})*))?$")


def parse(v: str) -> tuple[int, int, int]:
    m = _V.match(str(v).strip())
    if not m:
        raise ValueError(f"not a version: {v!r}")
    return tuple(int(x or 0) for x in m.groups())  # type: ignore[return-value]


def parse_full(v: str) -> tuple:
    """(major, minor, patch, pre) with pre a tuple of identifiers (numeric ones as int), () for a release."""
    m = _FULL.match(str(v).strip())
    if not m:
        raise ValueError(f"not a version: {v!r}")
    pre = tuple(int(p) if p.isdigit() else p for p in m.group(4).split(".")) if m.group(4) else ()
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), pre


def is_prerelease(v: str) -> bool:
    return bool(parse_full(v)[3])


def precedence(v: str) -> tuple:
    """A sort key in SemVer precedence: a pre-release sorts before its release; numeric identifiers sort before
    alphanumeric ones and numerically among themselves; a shorter identifier list sorts first."""
    major, minor, patch, pre = parse_full(v)
    return (major, minor, patch, 0 if pre else 1, tuple((0, p, "") if isinstance(p, int) else (1, 0, p) for p in pre))


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
    if not str(spec).replace(",", "").strip():
        return False    # an empty range would accept every version
    try:
        satisfies("0.0.0", spec)
        return True
    except ValueError:
        return False
