"""The point hash of the provider protocol (cr-propagation plan r3 5.2) and the canonical JSON hash it is built on.

canonical_sha256(value) = sha256 of json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) in
UTF-8, byte for byte the definition of contracts/recipe_semantics.py canonical_sha256 (tests/core/test_provider.py
compares the two on random values; core does not import contracts).

point_hash(transport, provider, provider_version, point) hashes {"transport": <the fixed transport settings in
canonical units, or null>, "provider": <id>, "provider_version": <version>, "point": <canonical name -> repr(float)>}.
Writing every point value as repr(float(x)) makes 3e28, 3.0e28 and 30000000000000000000000000000 one key.
"""
from __future__ import annotations

import hashlib
import json
import math


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def point_key(point: dict) -> dict:
    """The point in hash form: sorted names, each value repr(float). A non-number or non-finite value is a ValueError."""
    key = {}
    for name in sorted(point):
        value = point[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"point value {name}={value!r} is not a finite number")
        key[name] = repr(float(value))
    return key


def point_hash_object(transport, provider: str, provider_version: str, point: dict) -> dict:
    return {"transport": transport, "provider": provider, "provider_version": provider_version,
            "point": point_key(point)}


def point_hash(transport, provider: str, provider_version: str, point: dict) -> str:
    return canonical_sha256(point_hash_object(transport, provider, provider_version, point))
