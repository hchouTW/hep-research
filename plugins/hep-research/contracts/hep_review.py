"""hep-review kernel (pure; protocol hep-review/0, schema 0.x, experimental): strict JSON and the metadata encoding.

Specification: docs/dev/hep-review/ (task file and hep-review spec v9). This module is pure: no file, database,
network or clock access, and no import of a skill. Callers pass bytes and already-loaded objects.

Sections:
- strict JSON ingestion (spec 10.2) and the hep-review-metadata/1 encoding (spec 10.3);
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PROTOCOL = "hep-review/0"
SCHEMA_VERSION = "0.1.0"
METADATA_PROFILE = "hep-review-metadata/1"
RAW_PROFILE = "raw-bytes/1"

# ---------------------------------------------------------------------------------------------------------------------
# Strict JSON (spec 10.2) and the unique byte encoding (spec 10.3)
# ---------------------------------------------------------------------------------------------------------------------

SAFE_INT = 2 ** 53 - 1
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_DEPTH = 64
KEY_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")


class IngestError(ValueError):
    """Strict ingestion refused the input; `code` says why (json.*)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class EncodeError(ValueError):
    """A value outside the restricted domain of hep-review-metadata/1."""


def is_int(x: Any) -> bool:
    """An integer that is not a bool (spec 10.2: type checks use type(x) is int)."""
    return type(x) is int


def _max_depth(text: str) -> int:
    """Maximum nesting depth of [ and {, skipping string contents; non-recursive."""
    depth = best = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth > best:
                best = depth
        elif ch in "]}":
            depth -= 1
    return best


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    seen: set[str] = set()
    for k, _ in pairs:
        if k in seen:
            raise IngestError("json.duplicate_key", f"duplicate key {k!r} (after decoding escapes)")
        seen.add(k)
        if not KEY_NAME.match(k):
            raise IngestError("json.key_name", f"key {k!r} is not an ASCII name")
    return dict(pairs)


def _int(token: str) -> int:
    if token == "-0":
        raise IngestError("json.minus_zero", "the integer -0 is not allowed")
    value = int(token)
    if not -SAFE_INT <= value <= SAFE_INT:
        raise IngestError("json.int_range", f"integer {token} is outside +-(2^53-1)")
    return value


def _float(token: str):
    raise IngestError("json.float", f"floating-point number {token} is not allowed; use a decimal string")


def _constant(token: str):
    raise IngestError("json.constant", f"{token} is not allowed")


def _check_strings(value: Any) -> None:
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, str):
            if any(0xD800 <= ord(c) <= 0xDFFF for c in v):
                raise IngestError("json.lone_surrogate", "a string contains a lone surrogate")
        elif isinstance(v, dict):
            stack.extend(v.values())  # keys are ASCII names, checked in _pairs
        elif isinstance(v, list):
            stack.extend(v)


def ingest_json(raw: bytes, *, max_bytes: int = DEFAULT_MAX_BYTES, max_depth: int = DEFAULT_MAX_DEPTH) -> Any:
    """Parse metadata strictly (spec 10.2). Raises IngestError; never returns a value it would have to correct."""
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("ingest_json takes bytes; never decoded text from an unknown source")
    if len(raw) > max_bytes:
        raise IngestError("json.too_large", f"{len(raw)} bytes > limit {max_bytes}")
    try:
        text = bytes(raw).decode("utf-8")  # strict: rejects invalid UTF-8 and encoded surrogates
    except UnicodeDecodeError as e:
        raise IngestError("json.encoding", f"not UTF-8: {e.reason}") from None
    if text.startswith("﻿"):
        raise IngestError("json.bom", "a byte order mark is not allowed")
    if _max_depth(text) > max_depth:
        raise IngestError("json.too_deep", f"nesting deeper than {max_depth}")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_int, parse_float=_float,
                           parse_constant=_constant)
    except IngestError:
        raise
    except RecursionError:
        raise IngestError("json.too_deep", "nesting too deep") from None
    except json.JSONDecodeError as e:
        raise IngestError("json.syntax", e.msg) from None
    _check_strings(value)
    return value


def _check_domain(value: Any, depth: int = 0) -> None:
    if depth > 256:
        raise EncodeError("value nested too deeply")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if not -SAFE_INT <= value <= SAFE_INT:
            raise EncodeError(f"integer {value} outside +-(2^53-1)")
        return
    if type(value) is str:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise EncodeError("lone surrogate in a string")
        return
    if type(value) is list:
        for v in value:
            _check_domain(v, depth + 1)
        return
    if type(value) is dict:
        for k, v in value.items():
            if type(k) is not str or not KEY_NAME.match(k):
                raise EncodeError(f"key {k!r} is not an ASCII name")
            _check_domain(v, depth + 1)
        return
    raise EncodeError(f"{type(value).__name__} is outside the metadata value domain")


def encode(value: Any) -> bytes:
    """The unique byte encoding of hep-review-metadata/1 (spec 10.3). Within the restricted domain, json.dumps with
    these settings writes exactly the specified bytes; the gold vectors in contracts/fixtures/hep_review/ are the
    authority, not this implementation."""
    _check_domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def metadata_digest(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def raw_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
