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
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts import KNOWN_CAPABILITIES  # noqa: E402
from contracts.schema import SCHEMA_DIR, validate  # noqa: E402
from core.canonical import CanonicalError, load_json_strict, load_spec_json  # noqa: E402
from core.geometry import alignment, expand, fieldmap, identity, overlap  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

SPEC_SCHEMA = "detector_spec.json"
IR_SCHEMA = "geometry_ir.json"
OVERLAY_SCHEMA = "alignment_overlay.json"
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


def _positions_from_csv(spec: dict, folder: Path, protected: bool = False) -> list:
    """Reads each explicit placement's CSV, by its recorded hash, into its positions; core/geometry stays pure computation. Returns the sources.
    A CSV lies inside the specification's folder, and protected mode guards it like the specification itself."""
    sources = []
    base = folder.resolve()
    nodes = [*spec.get("templates", {}).values(), spec["world"]]
    for node in nodes:
        for child in node.get("children", []):
            body = child.get("placement", {}).get("explicit")
            if not body or "positions_csv" not in body:
                continue
            record = body.pop("positions_csv")
            target = (base / record["path"]).resolve()
            if Path(record["path"]).is_absolute() or not target.is_relative_to(base):
                raise GeometryError("explicit-path", "a position file lies inside the specification's folder")
            guard("contracts.geometry.check_file", paths=[str(target)], flag=protected, capabilities=KNOWN_CAPABILITIES)
            table = target.read_bytes()
            if hashlib.sha256(table).hexdigest() != record["sha256"]:
                raise GeometryError("explicit-hash", f"{record['path']} does not match its recorded hash")
            body["positions_mm"] = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(table.decode("utf-8"))) if row]
            sources.append(record)
    return sources


def _field_maps(spec: dict, folder: Path, protected: bool = False) -> dict:
    """Reads each field map by its recorded hash and adds its grid to the specification (Section 6.2.8, S7); core/geometry stays pure
    computation. A map lies inside the specification's folder, like a position file. Returns {field: (path record, file)}."""
    out = {}
    base = folder.resolve()
    for name, field in spec.get("fields", {}).items():
        if "map" not in field:
            continue
        record = field["map"]
        target = (base / record["path"]).resolve()
        if Path(record["path"]).is_absolute() or not target.is_relative_to(base):
            raise GeometryError("field-map-path", "a field map lies inside the specification's folder", f"/fields/{name}/map")
        guard("contracts.geometry.check_file", paths=[str(target)], flag=protected, capabilities=KNOWN_CAPABILITIES)
        map_bytes = target.read_bytes()
        if hashlib.sha256(map_bytes).hexdigest() != record["sha256"]:
            raise GeometryError("field-map-hash", f"{record['path']} does not match its recorded hash", f"/fields/{name}/map")
        try:
            text = map_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise GeometryError("field-map-format", f"{record['path']} is not UTF-8", f"/fields/{name}/map") from err
        field["map"] = {"sha256": record["sha256"], "grid": fieldmap.parse(text, f"/fields/{name}/map")["grid"]}
        out[name] = (record, target)
    return out


def check_spec(text, claims=(), folder: Path | None = None, protected: bool = False, overlay: dict | None = None) -> dict:
    """{status, findings, ir, geometry_id, provenance_id}: the whole reading and judging of one specification. folder holds its CSV files.
    An alignment-overlay/1 (S9) is applied to the expanded IR before the gap rule and the error bounds, so a misaligned geometry is judged
    as any other, and its geometry_id is the overlaid IR's."""
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
        sources = _positions_from_csv(spec, folder or Path("."), protected)
        maps = _field_maps(spec, folder or Path("."), protected)
        ir = expand.expand(spec)
        if overlay is not None:
            overlay_report = validate(overlay, OVERLAY_SCHEMA)
            overlay_findings = [_finding("overlay-schema", issue.path, issue.message) for issue in overlay_report.findings if issue.severity == "error"]
            if overlay_findings:
                return {"status": "rejected", "findings": [*findings, *overlay_findings]}
            ir = alignment.apply(ir, overlay)
        for record in sources:
            ir["marker"]["source_of_facts"][f"explicit:{record['path']}"] = record["sha256"]
        for record, _ in maps.values():
            ir["marker"]["source_of_facts"][f"field-map:{record['path']}"] = record["sha256"]
    except OSError as err:
        return {"status": "rejected", "findings": [*findings, _finding("explicit-file", "", str(err))]}  # a position file or a field map
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
    result = {"status": "ok", "findings": [], "ir": ir, "geometry_id": identity.geometry_id(ir), "provenance_id": identity.provenance_id(ir)}
    if maps:  # the files the program reads, by the hashes the IR holds
        result["field_map_files"] = {name: str(target) for name, (_, target) in maps.items()}
    return result


def check_file(path, claims=(), protected: bool = False, overlay_path=None) -> dict:
    """check_spec of a file, for callers: protected mode applies here too, so omitting the command line cannot avoid it. overlay_path names
    an alignment-overlay/1 file (S9), read strictly."""
    guard("contracts.geometry.check_file", paths=[str(path)] + ([str(overlay_path)] if overlay_path else []), flag=protected, capabilities=KNOWN_CAPABILITIES)
    overlay = None
    if overlay_path is not None:
        try:
            overlay = load_json_strict(Path(overlay_path).read_bytes())
        except CanonicalError as err:
            return {"status": "rejected", "findings": [_finding(err.code, "", f"overlay: {err}")]}
    return check_spec(Path(path).read_bytes(), claims, Path(path).parent, protected, overlay)


@protected_main("contracts.geometry", capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    parser.add_argument("--overlay", type=Path, help="an alignment-overlay/1 applied to the IR (S9)")
    args = parser.parse_args(argv)
    try:
        claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims else []
        result = check_file(args.spec, claims, args.protected, args.overlay)
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
