"""Skill names a contract may record (contracts 3.0.0).

hep-research 0.11.0 renamed four skills (contracts 2.9.0) and 0.16.0 split the communication skill into hep-citations
and hep-authoring (contracts 2.13.0); through 0.16.x the old names were deprecated aliases. Contracts 3.0.0
(hep-research 0.17.0) retires them: a skill name that is not in SKILLS is an error, `skill.unknown_name`, in an
artifact (provenance.producer_skill, handoff.to_skill, an extension handoff) and in a profile's related_skills, with
one exception: an unknown name that is not a retired one under an extension 'handoff' key is a warning,
`skill.unknown_handoff` (in an ml-artifact under the ml rules of contracts 2.8.0 it is the error `ml.handoff_unknown`
instead), so artifacts that passed before keep their outcome. For a retired name the message says to migrate with
hep-research 0.16.x, whose contracts/migrate_skill_names.py rewrites them. The retired names are kept only as SHA-256
hashes (RETIRED_SHA256), so the maintained tree never spells them; tools/check_retired_names.py fails on any maintained
file that does.

This module and `contracts/schemas/skill_names.json` (its enum is SKILLS) are the only places that define the names;
tests/contracts/test_skill_names.py checks that they agree.
"""
from __future__ import annotations

import hashlib
from typing import Any

SKILLS = ("hep-measurement", "hep-detector", "hep-theory", "hep-statistics", "hep-computing", "hep-ml",
          "hep-citations", "hep-authoring")
# SHA-256 of the five names retired in contracts 3.0.0 (the four renamed in 0.11.0 and the one split in 0.16.0)
RETIRED_SHA256 = frozenset({
    "e57ccb9f1698d58cd4d0aba82fa54e14c8799f828060f1763db2889bdb80d55a",
    "36bb3054af3554092713f0db80534b1cf93207e69fe88a1d4593f5125f073a77",
    "32dc019263b6b3ebe7cc482c8d821031662a2e92c24cead48871798b79ade41e",
    "7b9795f0bb101a9bc93cad8d18771640ea200b4cd5cf068cce72acf673f4a67f",
    "c72c64c287c44783986b4f679da661c7dd58f47545112220bcdacf82ece01e0e",
})
RETIRED_IN = "0.17.0"  # the hep-research release that retired them (contracts 3.0.0)
CODE = "skill.unknown_name"
HANDOFF_CODE = "skill.unknown_handoff"  # warning: an unknown, not retired, extension handoff


def is_retired(name: Any) -> bool:
    """Whether a value is one of the retired skill names."""
    return isinstance(name, str) and hashlib.sha256(name.encode("utf-8")).hexdigest() in RETIRED_SHA256


def message(field: str, name: str) -> str:
    if is_retired(name):
        return (f"{field} '{name}' is a skill name retired in hep-research {RETIRED_IN} (contracts 3.0.0); migrate "
                "the file with hep-research 0.16.x (contracts/migrate_skill_names.py), then validate it here")
    return f"{field} '{name}' is not a skill of this plugin ({', '.join(SKILLS)})"


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


def check_artifact(doc: Any, rep: Any) -> None:
    """Report each skill name an artifact records that is not a current skill. producer_skill is also checked by the
    schema enum and ml-artifact extension handoffs by the ml rules (ml.handoff_unknown); this adds the error for a
    retired name anywhere and for any unknown handoff.to_skill, and a warning (HANDOFF_CODE) for another unknown
    extension handoff (triage T15); contracts.validate drops that warning when the ml rules report the same name."""
    for path, value in artifact_name_fields(doc):
        if value in SKILLS:
            continue
        if is_retired(value) or path == "$.handoff.to_skill":
            rep.add("error", path, CODE, message(path.rsplit(".", 1)[-1], value))
        elif path.startswith("$.extension"):
            rep.add("warning", path, HANDOFF_CODE, message(path.rsplit(".", 1)[-1], value))


def check_profile(prof: Any, rep: Any, where: str) -> None:
    """Report each retired name in a profile's related_skills (the schema enum reports any other unknown name)."""
    skills = prof.get("related_skills") if isinstance(prof, dict) else None
    for i, name in enumerate(skills if isinstance(skills, list) else []):
        if is_retired(name):
            rep.add("error", f"{where}.related_skills[{i}]", CODE, message("related_skills entry", name))
