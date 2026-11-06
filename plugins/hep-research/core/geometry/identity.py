"""geometry_id, provenance_id and request_id (Section 7.2): canonical_sha256 of the two parts of the IR, the hash scope checked first."""
from __future__ import annotations

from core.canonical import canonical_sha256, require_hash_scope


def _digest(part: dict) -> str:
    require_hash_scope(part)
    return canonical_sha256(part)


def geometry_id(ir: dict) -> str:
    return _digest(ir["physical"])


def provenance_id(ir: dict) -> str:
    return _digest(ir["marker"])


def in_decimals(value):
    """A translated document for hashing: a float becomes its repr, the decimal string the translator writes (no binary float in the hash scope)."""
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, dict):
        return {key: in_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [in_decimals(item) for item in value]
    return value


def request_id(request: dict, geometry_identity: str) -> str:
    return _digest(in_decimals({"request": request, "geometry_id": geometry_identity}))
