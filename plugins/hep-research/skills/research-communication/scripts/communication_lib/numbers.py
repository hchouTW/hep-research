"""Number tokens in prose, Markdown and LaTeX text, shared by the occurrence, claim and adaptation checks (RC-A2, A3).

A token is a decimal number with an optional sign, thousands separators, fraction and exponent. Normalized first:
`\\pm` and `±` (to a spaced `±`, so the minus of `+/-` is never a sign), the Unicode minus, LaTeX `{,}` (decimal comma
in math mode is not used in HEP; `{,}` is read as a thousands separator), thin and narrow spaces and `\\,` between
digits, `$` and `~`. A sign counts only at the start or after a space, an opening bracket or a relation sign, so
`1.02-1.05` and dates give unsigned parts. A number touching CJK text or followed by sentence punctuation is a token;
one glued to Latin letters, digits or underscores (identifiers such as `C1`, `x86`, `2nd`) is not. Values compare as
`Decimal`; no rounding or tolerance is applied here.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_THIN = "\u2009\u202f\u200a"
TOKEN_RE = re.compile(
    r"(?P<sign>(?<![A-Za-z0-9_./)\]}\u00b1-])[-+](?=\d))?"
    r"(?<![A-Za-z0-9_.])"
    r"(?P<int>\d{1,3}(?:,\d{3})+(?!\d)|\d+)"
    r"(?:\.(?P<frac>\d+))?"
    r"(?:[eE](?P<exp>[-+]?\d+))?"
    r"(?![A-Za-z0-9_]|\.\d)")


def normalize_numeric_text(text: str) -> str:
    t = str(text)
    t = re.sub(r"\\pm\b|\+/-|\u00b1", " \u00b1 ", t)
    t = t.replace("\u2212", "-").replace("{,}", ",")
    t = re.sub(r"(?<=\d)(?:\\,|[" + _THIN + r"])(?=\d)", "", t)
    t = re.sub(r"[$~]", " ", t)
    return t


def tokens(text: str) -> list[str]:
    """Canonical number strings in reading order: sign kept, separators removed, exponent kept ('1.2e-3')."""
    out = []
    for m in TOKEN_RE.finditer(normalize_numeric_text(text)):
        s = (m.group("sign") or "").replace("+", "") + m.group("int").replace(",", "")
        if m.group("frac") is not None:
            s += "." + m.group("frac")
        if m.group("exp") is not None:
            s += "e" + m.group("exp")
        out.append(s)
    return out


def to_decimal(value) -> Decimal | None:
    try:
        d = Decimal(normalize_numeric_text(str(value)).strip().replace(",", ""))
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def same(a, b) -> bool:
    da, db = to_decimal(a), to_decimal(b)
    if da is None or db is None:
        return str(a).strip() == str(b).strip()
    return da == db


def contains_value(text: str, value) -> bool:
    """True when a number token of the text equals the value (as Decimal); '1.0' is not found in '1.02'."""
    d = to_decimal(value)
    if d is None:
        return False
    return any(to_decimal(t) == d for t in tokens(text))
