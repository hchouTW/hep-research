"""Data model of the semantic naming engine (spec §6): NamedEntity, Finding and ChangeSet as plain dicts in their
JSON form (schemas contracts/schemas/naming_inventory.json, naming_report.json, naming_change_set.json).

entity_id: "<surface>:<relative path>#<container>/<name>@<declaration start line>", so two same-name declarations in
one container differ. The extractor fills everything but tokens, references_status, contract_level and
contract_basis, which the engine computes. Standard library only.
"""
from __future__ import annotations

import hashlib

STATES = ("satisfied", "violated", "not_applicable", "unverified", "unsupported")
LEVELS = ("C0", "C1", "C2", "C3", "C4")
SOURCES = ("project", "external")
CHANGES = ("added", "modified", "removed", "unchanged")
REFERENCE_STATUSES = ("complete", "partial", "not_searched")
CONFIDENCES = ("high", "medium", "low")
RENAME_POLICIES = ("matrix", "dedup-only", "deprecate", "never")
SURFACES = tuple(f"N{k}" for k in range(1, 18))
ACTIONS = ("none", "report-missing", "gather-evidence", "fix", "fix-with-change-set", "propose",
           "propose-then-change-set-after-approval", "propose-alias", "report-only")
INVENTORY_VERSION = "1.0.0"
ENGINE_FIELDS = ("tokens", "references_status", "contract_level", "contract_basis")


def entity_id(surface: str, file: str, container: str, name: str, line: int) -> str:
    return f"{surface}:{file}#{container}/{name}@{line}"


def stable_key(eid: str) -> str:
    """The entity id without its line: what a known-gaps baseline keys on, so edits above a name do not move it."""
    return eid.rsplit("@", 1)[0]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_entity(surface: str, kind: str, name: str, file: str, container: str, span, *, source: str = "project",
               content: str = "", extractor: dict, references=(), search_coverage=(), change: str = "unchanged",
               meaning: dict | None = None) -> dict:
    return {"entity_id": entity_id(surface, file, container, name, span[0]), "surface": surface, "entity_kind": kind,
            "name": name, "scope": {"file": file, "container": container, "span": [span[0], span[1]]},
            "source": source,
            "meaning": {"concept_id": None, "unit": None, "status_label": None, "source": "extractor", **(meaning or {})},
            "references": list(references), "search_coverage": list(search_coverage), "change": change,
            "content_sha256": sha256_text(content), "extractor": dict(extractor)}


def new_inventory(surface: str, scope_roots, inputs_scanned: int, entities, generated_at: str, **extra) -> dict:
    inv = {"inventory_version": INVENTORY_VERSION, "surface": surface, "scope_roots": list(scope_roots),
           "inputs_scanned": inputs_scanned, "generated_at": generated_at, "entities": list(entities)}
    inv.update({k: v for k, v in extra.items() if v is not None})
    return inv


def level_index(level: str) -> int:
    return LEVELS.index(level)


def max_level(*levels: str) -> str:
    return max(levels, key=level_index)
