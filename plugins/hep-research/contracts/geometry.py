#!/usr/bin/env python3
"""Validation of specifications and the IR (g4sim plan, Section 5.2): schema, units and claim resolution, and judging the
geometric legality that core/geometry computes. Writes nothing unless --out is given.

The type table of core.canonical.load_spec_json is generated here from contracts/schemas/detector_spec.json, so the schema is
the one place that says which fields are quantities and which are integers.

Usage: python3 contracts/geometry.py SPEC.json [--out IR.json] [--claims CLAIMS.json] [--protected]
--claims names a JSON list of the claim ids of the profiles the specification depends on; a source_of_facts value "claim:<id>"
must be one of them. Prints JSON with a status key. Exit 0 valid, 1 refused with findings, 2 bad input, 3 refused by protected mode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts import KNOWN_CAPABILITIES  # noqa: E402
from contracts.schema import SCHEMA_DIR, validate  # noqa: E402
from core.canonical import CanonicalError, load_spec_json  # noqa: E402
from core.geometry import expand, identity, overlap  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

SPEC_SCHEMA = "detector_spec.json"
IR_SCHEMA = "geometry_ir.json"
CLAIM_PREFIX = "claim:"
UNHASHED = ("legacy",)  # what the translator keeps for the round trip; expansion never reads it, so no identity depends on it


def _walk(node: dict, pointer: str, defs: dict, table: dict) -> None:
    reference = node.get("$ref", "")
    if reference in ("#/$defs/quantity", "#/$defs/integer"):
        table[pointer] = reference.rsplit("/", 1)[1]
        return
    if reference.startswith("#/$defs/"):
        _walk(defs[reference.rsplit("/", 1)[1]], pointer, defs, table)
        return
    for key, child in node.get("properties", {}).items():
        _walk(child, f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}", defs, table)
    if isinstance(node.get("additionalProperties"), dict):
        _walk(node["additionalProperties"], f"{pointer}/*", defs, table)
    if isinstance(node.get("items"), dict):
        _walk(node["items"], f"{pointer}/*", defs, table)
    for form in node.get("anyOf", []):
        _walk(form, pointer, defs, table)


def field_types() -> dict:
    """{JSON Pointer: "quantity" or "integer"}, from the schema."""
    schema = json.loads((SCHEMA_DIR / SPEC_SCHEMA).read_text(encoding="utf-8"))
    table: dict = {}
    _walk(schema, "", schema["$defs"], table)
    return table


def _finding(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _pointer_target(document, pointer: str) -> bool:
    node = document
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return False
    return True


def claim_findings(spec: dict, claims) -> list[dict]:
    """Every source_of_facts entry points at a value, and every claim it names resolves in a profile depended on."""
    out = []
    for pointer, source in spec.get("source_of_facts", {}).items():
        if not pointer.startswith("/") or not _pointer_target(spec, pointer):
            out.append(_finding("facts-pointer", pointer, "source_of_facts names no value of the specification"))
        if source.startswith(CLAIM_PREFIX) and source[len(CLAIM_PREFIX):] not in claims:
            out.append(_finding("facts-claim", pointer, f"{source!r} resolves in no profile depended on"))
    return out


def check_spec(text, claims=()) -> dict:
    """{status, findings, ir, geometry_id, provenance_id}: the whole reading and judging of one specification."""
    try:
        spec = load_spec_json(text, field_types(), unhashed=UNHASHED)
    except CanonicalError as err:
        return {"status": "rejected", "findings": [_finding(err.code, "", str(err))]}
    report = validate(spec, SPEC_SCHEMA)
    findings = [_finding("schema", issue.path, issue.message) for issue in report.findings if issue.severity == "error"]
    if findings:
        return {"status": "rejected", "findings": findings}
    findings = claim_findings(spec, set(claims))
    try:
        ir = expand.expand(spec)
    except GeometryError as err:
        return {"status": "rejected", "findings": [*findings, _finding(err.code, err.path, str(err))]}
    if "legacy" not in spec:  # legacy mode does not apply the gap rule: the old geometries passed G4's overlap test (Section 7.4)
        findings += overlap.findings(ir)
    if findings:
        return {"status": "rejected", "findings": findings}
    report = validate(ir, IR_SCHEMA)
    findings = [_finding("ir-schema", issue.path, issue.message) for issue in report.findings if issue.severity == "error"]
    if findings:
        return {"status": "rejected", "findings": findings}
    return {"status": "ok", "findings": [], "ir": ir, "geometry_id": identity.geometry_id(ir),
            "provenance_id": identity.provenance_id(ir)}


def check_file(path, claims=(), protected: bool = False) -> dict:
    """check_spec of a file, for callers: protected mode applies here too, so omitting the command line cannot avoid it."""
    guard("contracts.geometry.check_file", paths=[str(path)], flag=protected, capabilities=KNOWN_CAPABILITIES)
    return check_spec(Path(path).read_bytes(), claims)


@protected_main("contracts.geometry", capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    args = parser.parse_args(argv)
    try:
        claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims else []
        result = check_file(args.spec, claims, args.protected)
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    if result["status"] == "ok" and args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result["ir"], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "ir"}, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
