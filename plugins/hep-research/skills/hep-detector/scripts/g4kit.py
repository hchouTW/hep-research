#!/usr/bin/env python3
"""A kit and a design geometry file to a detector-spec and its geometry derivation record (g4sim plan, Sections 12, 14.2).

Kits are data, in assets/g4kits/. A kit is a detector-spec in which `{"$input": NAME}` stands for an input, and whose expressions read the inputs through `params`; it adds no run-time function, and has geometric
defaults only: every physical value and every material comes from the design geometry file.

  g4kit.py list
  g4kit.py derive --geometry FILE --out-detector PATH --out-derivation PATH

Prints JSON with a status key. Exit 0 ok, 1 the specification fails its checks, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))

from contracts import KNOWN_CAPABILITIES, geometry  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

KITS = Path(__file__).resolve().parents[1] / "assets/g4kits"
NUMERIC = ("integer", "length", "physical")


class KitError(ValueError):
    pass


def kit_for(kind: str) -> tuple:
    """The kit of a geometry kind, with the hash of its file."""
    for path in sorted(KITS.glob("*.json")):
        content = path.read_bytes()
        kit = json.loads(content.decode("utf-8"))
        if kit["geometry_kind"] == kind:
            return kit, hashlib.sha256(content).hexdigest()
    raise KitError(f"no kit makes geometry kind {kind!r}")


def as_quantity(value) -> str:
    return format(Decimal(str(value)), "f")


def input_values(kit: dict, fields: dict) -> dict:
    """Every input of the kit, from the design geometry file, or a geometric default; nothing else may come in."""
    unknown = sorted(set(fields) - set(kit["inputs"]) - set(kit["geometric_defaults"]))
    missing = sorted(name for name, item in kit["inputs"].items() if name not in fields and not item.get("optional"))
    if unknown or missing:
        raise KitError(f"kit {kit['name']}: missing inputs {missing}, unknown fields {unknown}")
    values = {**kit["geometric_defaults"], "materials": {}, **fields}
    for name, item in kit["inputs"].items():
        value = values[name]
        if item["kind"] == "integer" and (isinstance(value, bool) or not isinstance(value, int) and not (isinstance(value, float) and value.is_integer())):
            raise KitError(f"input {name} is a whole number, not {value!r}")
        if item["kind"] == "material" and not isinstance(value, str):
            raise KitError(f"input {name} is a material name, not {value!r}")
    return values


def filled(node, values: dict, kit: dict):
    """The kit's specification with each `$input` replaced by its value."""
    if isinstance(node, dict):
        if set(node) == {"$input"}:
            value = values[node["$input"]]
            return int(value) if kit["inputs"].get(node["$input"], {}).get("kind") == "integer" else value
        return {key: filled(value, values, kit) for key, value in node.items()}
    if isinstance(node, list):
        return [filled(value, values, kit) for value in node]
    return node


def detector_spec(kit: dict, values: dict) -> dict:
    spec = filled(kit["detector"], values, kit)
    numbers = {name: as_quantity(values[name]) for name, item in kit["inputs"].items() if item["kind"] in NUMERIC}
    spec["params"] = {**numbers, **{name: as_quantity(value) for name, value in kit["geometric_defaults"].items() if name not in numbers}, **spec["params"]}
    return spec


def derive(args) -> tuple:
    guard("hep-detector.g4kit", paths=[str(args.geometry)], flag=args.protected, capabilities=KNOWN_CAPABILITIES)
    geometry_bytes = args.geometry.read_bytes()
    design = json.loads(geometry_bytes.decode("utf-8"))
    if design.get("schema") != "design-geometry/1":
        raise KitError(f"{args.geometry} is not a design-geometry/1 file")
    kind = design.get("geometry_kind", design.get("geometry"))
    kit, kit_hash = kit_for(kind)
    spec = detector_spec(kit, input_values(kit, design["fields"]))
    text = (json.dumps(spec, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    checked = geometry.check_spec(text, protected=args.protected)
    if checked["status"] != "ok":
        return 1, {"status": "failed", "error_kind": "specification", "findings": checked["findings"]}
    record = {"schema": "geometry-derivation/1", "design_geometry_sha256": hashlib.sha256(geometry_bytes).hexdigest(), "geometry_kind": kind, "kit": {"name": kit["name"], "version": kit["version"], "sha256": kit_hash},
              "detector_spec_sha256": hashlib.sha256(text).hexdigest(), "geometry_id": checked["geometry_id"]}
    args.out_detector.parent.mkdir(parents=True, exist_ok=True)
    args.out_derivation.parent.mkdir(parents=True, exist_ok=True)
    args.out_detector.write_bytes(text)
    args.out_derivation.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return 0, {"status": "ok", **record}


def listing() -> tuple:
    kits = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(KITS.glob("*.json"))]
    return 0, {"status": "ok", "kits": [{"name": kit["name"], "version": kit["version"], "geometry_kind": kit["geometry_kind"], "inputs": sorted(kit["inputs"])} for kit in kits]}


@protected_main("hep-detector.g4kit", capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    deriving = commands.add_parser("derive")
    deriving.add_argument("--geometry", type=Path, required=True)
    deriving.add_argument("--out-detector", type=Path, required=True)
    deriving.add_argument("--out-derivation", type=Path, required=True)
    deriving.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    args = parser.parse_args(argv)
    try:
        code, result = listing() if args.command == "list" else derive(args)
    except (KitError, OSError, ValueError, KeyError) as error:
        code, result = 2, {"status": "rejected", "error_kind": "invalid-input", "error": str(error)}
    print(json.dumps(result, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
