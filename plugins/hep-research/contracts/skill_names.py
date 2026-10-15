"""Skill names a contract may record, and the deprecated aliases kept after the rename (contracts 2.9.0).

hep-research 0.11.0 renamed four skills. Artifacts and profiles written before the rename keep validating: an old name
is a deprecated alias of the new one, reported as `skill.deprecated_name` (artifacts) or `profile.deprecated_skill_name`
(profiles), a warning by default and an error under the version and name policy (`--strict-versions`, and protected
use). `contracts/migrate_skill_names.py` rewrites an artifact's `provenance.producer_skill` and `handoff.to_skill`.

This module and `contracts/schemas/skill_names.json` are the only places that define the aliases; the schema's enum is
SKILLS followed by the deprecated names (tests/contracts/test_skill_name_aliases.py checks that they agree). The aliases
are removed one or two releases after the rename.
"""
from __future__ import annotations

from typing import Any

SKILLS = ("hep-measurement", "hep-detector", "hep-theory", "hep-statistics", "hep-computing", "hep-ml",
          "hep-communication")
DEPRECATED_SKILL_ALIASES = {
    "hep-analysis": "hep-measurement",
    "detector-response": "hep-detector",
    "research-communication": "hep-communication",
    "physics-ml": "hep-ml",
}
RENAMED_IN = "0.11.0"  # the hep-research release that renamed the skills
ALL_SKILL_NAMES = frozenset(SKILLS) | frozenset(DEPRECATED_SKILL_ALIASES)
CODE = "skill.deprecated_name"
PROFILE_CODE = "profile.deprecated_skill_name"


def canonical(name: Any) -> Any:
    """The current name for a skill name; any other value unchanged."""
    return DEPRECATED_SKILL_ALIASES.get(name, name) if isinstance(name, str) else name


def message(field: str, old: str, hint: str = "rewrite it with contracts/migrate_skill_names.py") -> str:
    return (f"{field} '{old}' is the deprecated name of '{DEPRECATED_SKILL_ALIASES[old]}' (renamed in hep-research "
            f"{RENAMED_IN}); {hint}")


def _ext_handoffs(value: Any, path: str):
    """(path, value) of every string stored under a 'handoff' key inside the extension."""
    if isinstance(value, dict):
        for k, v in value.items():
            sub = f"{path}.{k}"
            if k == "handoff" and isinstance(v, str):
                yield sub, v
            else:
                yield from _ext_handoffs(v, sub)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _ext_handoffs(v, f"{path}[{i}]")


def artifact_name_fields(doc: Any):
    """(JSON path, value) of every skill name an artifact records: provenance.producer_skill, handoff.to_skill and the
    extension's handoff strings (ml-artifact validation blocks)."""
    if not isinstance(doc, dict):
        return
    prov = doc.get("provenance")
    if isinstance(prov, dict) and isinstance(prov.get("producer_skill"), str):
        yield "$.provenance.producer_skill", prov["producer_skill"]
    hand = doc.get("handoff")
    if isinstance(hand, dict) and isinstance(hand.get("to_skill"), str):
        yield "$.handoff.to_skill", hand["to_skill"]
    yield from _ext_handoffs(doc.get("extension"), "$.extension")


def check_artifact(doc: Any, rep: Any, strict: bool = False) -> None:
    """Report each deprecated skill name in an artifact: a warning, or an error under the version and name policy."""
    for path, value in artifact_name_fields(doc):
        if value in DEPRECATED_SKILL_ALIASES:
            rep.add("error" if strict else "warning", path, CODE, message(path.rsplit(".", 1)[-1], value))


def check_profile(prof: Any, rep: Any, where: str, strict: bool = False) -> None:
    """Report each deprecated name in a profile's related_skills: a warning, or an error under the name policy."""
    skills = prof.get("related_skills") if isinstance(prof, dict) else None
    for i, name in enumerate(skills if isinstance(skills, list) else []):
        if name in DEPRECATED_SKILL_ALIASES:
            rep.add("error" if strict else "warning", f"{where}.related_skills[{i}]", PROFILE_CODE,
                    message("related_skills entry", name, "write the new name in profile.json"))
