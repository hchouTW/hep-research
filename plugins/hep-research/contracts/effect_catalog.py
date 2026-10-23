#!/usr/bin/env python3
"""Effect catalog and operator coverage contracts (v6.3 D04, C8): classification, conditional composition, which
listed members an operator covers, and the closure of a class's member set.

The catalog (contracts/vocab/effects.json, schema effect_catalog.json) says which class an effect belongs to and how a
parent factor is composed under stated conditions. A coverage contract (contracts/semantics/coverage/<table>.coverage.json,
schema operator_coverage.json) says, for one operator-semantics table bound by its canonical digest, which effects and
which listed class members each operator covers. Classification is not coverage: an effect of a class is covered only
when the operator's contract lists it; an undefined member set leaves every member unverified, and nothing is filled
in from class names (O09). The legacy '<x>_efficiency' pattern is a classification adapter only, and bare
'efficiency' keeps its legacy coverage (the table's own 'applies'). Old entry points do not read these files.

coverage_state(coverage, operator_id, effect_id, catalog) -> {"state", "basis"}: state is covered, not_covered,
unverified (a member set the contract leaves undefined) or unsupported (an unknown effect or operator).
resolve_members(catalog, class_id) -> {"class", "members", "strategy", "dependencies", "closure_digest"}: the member
set with the definitions it depends on; its digest changes with the class or a member and with nothing else.

Usage: python3 contracts/effect_catalog.py check
Exit 0 catalog and every coverage contract consistent, 1 findings, 2 unreadable. Output: JSON with a status key.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402


def _catalog_compatible(written_for, installed) -> bool:
    """A coverage contract written against catalog X.Y.Z reads under an installed catalog of the same major version
    that is not older: catalog minors only add (1.1.0 adds description_required)."""
    from contracts.semver import parse
    try:
        w, i = parse(str(written_for)), parse(str(installed))
    except ValueError:
        return False
    return w[0] == i[0] and w <= i

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "vocab" / "effects.json"
COVERAGE_DIR = ROOT / "contracts" / "semantics" / "coverage"
TABLE_DIR = ROOT / "contracts" / "semantics" / "tables"
LEGACY_EFFICIENCY = re.compile(r"^(?:[a-z][a-z0-9-]*:)?[a-z][a-z0-9_]*_efficiency$")


def load_catalog(path: Path = CATALOG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_coverage(table_id: str, directory: Path = COVERAGE_DIR) -> dict:
    return json.loads((Path(directory) / f"{table_id}.coverage.json").read_text(encoding="utf-8"))


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


def check_coverage(cov, cat, table) -> list[dict]:
    out = _schema(cov, "operator_coverage.json")
    if out:
        return out
    if cov["table_id"] != table.get("table_id"):
        out.append(_f("coverage.wrong_table", "table_id", f"the contract is for '{cov['table_id']}'"))
    if canonical_sha256(table) != cov["table_sha256"]:
        out.append(_f("coverage.table_changed", "table_sha256", "the table differs from the one the contract is bound to"))
    if not _catalog_compatible(cov["catalog_version"], cat.get("catalog_version")):
        out.append(_f("coverage.catalog_version", "catalog_version",
                      f"the contract names catalog {cov['catalog_version']}, not compatible with the installed {cat.get('catalog_version')} "
                      "(same major, not newer)"))
    effects = {e["effect_id"]: e for e in cat.get("effects", [])}
    classes = {c["class_id"]: c for c in cat.get("classes", [])}
    table_ops = {o["operator_id"] for o in table.get("operators", [])}
    seen = set()
    for op in cov["operators"]:
        oid, where = op["operator_id"], f"operators.{op['operator_id']}"
        if oid in seen:
            out.append(_f("coverage.duplicate_operator", where, f"'{oid}' is listed twice"))
        seen.add(oid)
        if oid not in table_ops:
            out.append(_f("coverage.unknown_operator", where, f"'{oid}' is not an operator of the table"))
        for e in op["covers"] + [f["effect"] for f in op.get("factors", [])]:
            if e not in effects:
                out.append(_f("coverage.unknown_effect", where, f"'{e}' is not a catalog effect"))
        for cls, cc in op["class_coverage"].items():
            if cls not in classes:
                out.append(_f("coverage.unknown_class", where, f"class '{cls}' is not in the catalog"))
                continue
            for m in cc["members"] or []:
                if m not in classes[cls]["members"]:
                    out.append(_f("coverage.unknown_member", where, f"'{m}' is not a listed member of '{cls}'"))
        if any(f["power"] == 0 for f in op.get("factors", [])):
            out.append(_f("coverage.zero_power", where, "a factor with power 0 is no factor"))
    return out


def classify(cat, effect_id: str) -> dict:
    """{"class", "basis"}: the catalog's class, else the legacy '<x>_efficiency' adapter, else nothing."""
    for e in cat.get("effects", []):
        if e["effect_id"] == effect_id:
            return {"class": e["class"], "basis": "catalog"}
    if isinstance(effect_id, str) and LEGACY_EFFICIENCY.match(effect_id):
        return {"class": "efficiency", "basis": "legacy-pattern"}
    return {"class": None, "basis": None}


def coverage_state(cov, operator_id: str, effect_id: str, cat, table: dict | None = None) -> dict:
    op = next((o for o in cov.get("operators", []) if o["operator_id"] == operator_id), None)
    effect = next((e for e in cat.get("effects", []) if e["effect_id"] == effect_id), None)
    if op is None:
        return {"state": "unsupported", "basis": f"no coverage contract entry for operator '{operator_id}'"}
    if effect is None:
        return {"state": "unsupported", "basis": f"'{effect_id}' is not a catalog effect"}
    if effect_id in op["covers"]:
        return {"state": "covered", "basis": "listed"}
    cls = effect["class"]
    if cls is not None and effect_id == cls:  # bare class term (legacy 'efficiency'): the table's own applies decide
        tab = table if table is not None else _table(cov["table_id"])
        applies: list = next((o.get("applies", []) for o in (tab or {}).get("operators", []) if o["operator_id"] == operator_id), [])
        return {"state": "covered" if cls in applies else "not_covered", "basis": "legacy-table"}
    if cls is not None and cls in op["class_coverage"]:
        members = op["class_coverage"][cls]["members"]
        if members is None:
            return {"state": "unverified", "basis": f"the contract leaves the '{cls}' members of '{operator_id}' undefined"}
        return {"state": "covered" if effect_id in members else "not_covered", "basis": "listed"}
    return {"state": "not_covered", "basis": "listed"}


def _table(table_id: str) -> dict | None:
    for p in sorted(TABLE_DIR.glob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(t, dict) and t.get("table_id") == table_id:
            return t
    return None


def resolve_members(cat, class_id: str) -> dict:
    """The listed members of a class with the definitions the resolution depends on and their closure digest."""
    cls = next((c for c in cat.get("classes", []) if c["class_id"] == class_id), None)
    if cls is None:
        return {"class": class_id, "members": None, "strategy": None, "dependencies": [], "closure_digest": None}
    members = sorted(cls["members"])
    defs = {e["effect_id"]: e for e in cat.get("effects", []) if e["effect_id"] in set(members) | {class_id}}
    closure = {"class": cls, "effects": [defs[k] for k in sorted(defs)], "catalog_version": cat.get("catalog_version")}
    return {"class": class_id, "members": members, "strategy": cls["member_set"],
            "dependencies": sorted({class_id, *members}), "closure_digest": canonical_sha256(closure)}


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
        covs = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(COVERAGE_DIR.glob("*.coverage.json"))}
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    findings = {"catalog": check_catalog(cat)}
    for name, cov in covs.items():
        table = _table(cov.get("table_id", "")) if isinstance(cov, dict) else None
        findings[name] = (check_coverage(cov, cat, table) if table is not None
                          else [_f("coverage.table_missing", "table_id", "no table with this id")])
    ok = not any(findings.values())
    print(json.dumps({"status": "pass" if ok else "fail", "findings": findings,
                      "note": "definition consistency only: which members an operator covers is a reviewed scientific "
                              "statement, not something this check establishes"}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
