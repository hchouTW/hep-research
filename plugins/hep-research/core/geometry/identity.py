"""geometry_id, provenance_id and request_id (Section 7.2): canonical_sha256 of the two parts of the IR, the hash scope checked first."""
from __future__ import annotations

import hashlib
import json

from core.canonical import canonical_sha256, require_hash_scope


def _digest(part: dict) -> str:
    require_hash_scope(part)
    return canonical_sha256(part)


def geometry_id(ir: dict) -> str:
    return _digest(ir["physical"])


def field_configuration_sha256(ir: dict) -> str:
    """B2.8 condition 2's key on the g4sim path: the field of the IR's physical part, each template's field and the field definitions (g4sim plan, Section 19.2 S5)."""
    physical = ir["physical"]
    document = {"fields": physical.get("fields"), "templates": {name: node.get("field") for name, node in sorted(physical["templates"].items())}}
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


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


def selected_templates(select: dict, ir: dict) -> list:
    """The templates a scorer's `select` picks: tags that pick the same objects pick the same list."""
    tags = ir["marker"]["tags"]
    wanted = set(select.get("tags", []))
    return sorted(name for name, own in tags.items() if wanted <= set(own)) if wanted else sorted(select.get("templates", []))


def identified_request(request: dict, ir: dict) -> dict:
    """The request as `request_id` hashes it (Section 6.3): `select` expanded, so tags that pick the same objects give the same identity."""
    if "scorers" not in request:
        return request
    return {**request, "scorers": [{**{key: value for key, value in scorer.items() if key != "select"}, "templates": selected_templates(scorer["select"], ir)} for scorer in request["scorers"]]}


def request_id(request: dict, geometry_identity: str) -> str:
    return _digest(in_decimals({"request": request, "geometry_id": geometry_identity}))
