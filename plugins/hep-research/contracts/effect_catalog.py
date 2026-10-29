#!/usr/bin/env python3
"""Effect catalog (v6.3 D04, C8): which class an effect belongs to and how a parent factor is composed under stated
conditions. The catalog is contracts/vocab/effects.json (schema effect_catalog.json); measurement scripts read its
compositions (for example collection_time.py). The legacy '<x>_efficiency' pattern is a classification adapter only.

The operator coverage contracts that once lived beside the catalog were part of the cross-artifact check and were
retired with it (docs/dev/cross-artifact-check/decision-retire.md).

Usage: python3 contracts/effect_catalog.py check
Exit 0 catalog consistent, 1 findings, 2 unreadable. Output: JSON with a status key.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "vocab" / "effects.json"
LEGACY_EFFICIENCY = re.compile(r"^(?:[a-z][a-z0-9-]*:)?[a-z][a-z0-9_]*_efficiency$")


def load_catalog(path: Path = CATALOG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _f(code: str, where: str, message: str) -> dict:
    return {"code": code, "where": where, "message": message}


def _schema(doc, name: str) -> list[dict]:
    return [_f(f.code, f.path, f.message) for f in validate(doc, name).errors]


def check_catalog(cat) -> list[dict]:
    out = _schema(cat, "effect_catalog.json")
    if out:
        return out
    ids = [e["effect_id"] for e in cat["effects"]]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        out.append(_f("catalog.duplicate_effect", "effects", f"effect '{d}' is defined twice"))
    by_id = {e["effect_id"]: e for e in cat["effects"]}
    classes = {c["class_id"]: c for c in cat["classes"]}
    for c in cat["classes"]:
        for m in c["members"]:
            if m not in by_id:
                out.append(_f("catalog.unknown_member", f"classes.{c['class_id']}", f"member '{m}' is not an effect"))
            elif by_id[m]["class"] != c["class_id"]:
                out.append(_f("catalog.member_class_mismatch", f"classes.{c['class_id']}",
                              f"'{m}' is listed as a member but its class is {by_id[m]['class']!r}"))
    for e in cat["effects"]:
        cls = e["class"]
        if cls is not None and cls not in classes:
            out.append(_f("catalog.unknown_class", f"effects.{e['effect_id']}", f"class '{cls}' is not defined"))
        elif cls is not None and e["effect_id"] != cls and e["effect_id"] not in classes[cls]["members"]:
            out.append(_f("catalog.member_unlisted", f"effects.{e['effect_id']}",
                          f"'{e['effect_id']}' claims class '{cls}' but the class does not list it"))
    for comp in cat["compositions"]:
        for name in [comp["parent"]] + [ch["effect"] for ch in comp["children"]]:
            if name not in by_id:
                out.append(_f("catalog.unknown_effect", f"compositions.{comp['composition_id']}", f"'{name}' is not an effect"))
        if any(ch["power"] == 0 for ch in comp["children"]):
            out.append(_f("catalog.zero_power", f"compositions.{comp['composition_id']}", "a child with power 0 is no factor"))
        if comp["parent"] in {ch["effect"] for ch in comp["children"]}:
            out.append(_f("catalog.composition_cycle", f"compositions.{comp['composition_id']}", "a parent cannot be its own child"))
    return out


def classify(cat, effect_id: str) -> dict:
    """{"class", "basis"}: the catalog's class, else the legacy '<x>_efficiency' adapter, else nothing."""
    for e in cat.get("effects", []):
        if e["effect_id"] == effect_id:
            return {"class": e["class"], "basis": "catalog"}
    if isinstance(effect_id, str) and LEGACY_EFFICIENCY.match(effect_id):
        return {"class": "efficiency", "basis": "legacy-pattern"}
    return {"class": None, "basis": None}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if args != ["check"]:
        print(json.dumps({"status": "usage", "error": "usage: effect_catalog.py check"}))
        return 2
    try:
        cat = load_catalog()
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    findings = check_catalog(cat)
    print(json.dumps({"status": "fail" if findings else "pass", "findings": findings}, indent=1))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
