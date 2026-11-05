"""geometry_id and provenance_id (Section 7.2): canonical_sha256 of the two parts of the IR, the hash scope checked first."""
from __future__ import annotations

from core.canonical import canonical_sha256, require_hash_scope


def _digest(part: dict) -> str:
    require_hash_scope(part)
    return canonical_sha256(part)


def geometry_id(ir: dict) -> str:
    return _digest(ir["physical"])


def provenance_id(ir: dict) -> str:
    return _digest(ir["marker"])
