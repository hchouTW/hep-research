#!/usr/bin/env python3
"""The translator (g4sim plan, Sections 7.4 and 18): splits layered_sim.spec/1 and element_sim.spec/1 into detector-spec/1,
simulation-request/1 and g4sim-run/1, and merges the three back into the original file. Kept permanently.

merge rebuilds the old specification from what split produced. A field split does not know is refused, never dropped, so nothing
can vanish in a round trip. Numbers become decimal strings of repr(float), which give the same double back.

Usage: g4sim_translate.py split SPEC.json --out DIR    writes detector.json, request.json and run.json
       g4sim_translate.py check SPEC.json              split, merge, and compare with the file byte for byte
Prints JSON with a status key. Exit 0 ok, 1 the round trip differs, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.canonical import normalize_decimal  # noqa: E402
from core.geometry.numbers import CONTEXT, add, divide, multiply, subtract  # noqa: E402

LAYERED, ELEMENT = "layered_sim.spec/1", "element_sim.spec/1"
SENSITIVE = "sensitive"
ROLE_PREFIX = "role:"
RUN_MODES = {"serial": "serial", "mt": "mt"}
MATERIAL_NUMBERS = ("a_g_mole", "density_g_cm3", "temperature_K", "pressure_Pa")


class TranslationError(ValueError):
    """An old specification the translator cannot carry over whole."""


def _text(value) -> str:
    if isinstance(value, bool) or not isinstance(value, float):
        raise TranslationError(f"{value!r} is not a floating-point number")
    return normalize_decimal(repr(value))


def _texts(values) -> list[str]:
    return [_text(value) for value in values]


def _number(text: str) -> float:
    return float(text)


def _numbers(texts) -> list[float]:
    return [_number(text) for text in texts]


def _only(document: dict, known: set, where: str) -> None:
    unknown = set(document) - known
    if unknown:
        raise TranslationError(f"{where}: {sorted(unknown)} is not carried by the translator")


def _material(material: dict) -> dict:
    _only(material, {"name", "z", "source", "components", "state", *MATERIAL_NUMBERS}, "material")
    out: dict = {}
    for key in ("z", "state"):
        if key in material:
            out[key] = material[key]
    for key in MATERIAL_NUMBERS:
        if key in material:
            out[key] = _text(material[key])
    if "components" in material:
        out["components"] = [{"material": item["material"], "mass_fraction": _text(item["mass_fraction"])}
                             for item in material["components"]]
    if "source" in material:
        out["facts"] = material["source"]
    return out


def _material_back(name: str, material: dict) -> dict:
    out: dict = {"name": name}
    for key in ("z", "state"):
        if key in material:
            out[key] = material[key]
    for key in MATERIAL_NUMBERS:
        if key in material:
            out[key] = _number(material[key])
    if "components" in material:
        out["components"] = [{"material": item["material"], "mass_fraction": _number(item["mass_fraction"])}
                             for item in material["components"]]
    if "facts" in material:
        out["source"] = material["facts"]
    return out


def _box(size: list[str], material: str) -> dict:
    return {"solid": {"box": {"size_mm": size}}, "material": material}


def _size(template: dict) -> list[str]:
    return template["solid"]["box"]["size_mm"]


def _run_card(physics: dict, run: dict, output_settings: dict, ui_commands, seeding: str, extra: dict) -> dict:
    card = {"schema": "g4sim-run/1", "physics": physics, "accounting": "legacy", "field_integration": extra.get("field"),
            "run": {"events": run["events"], "mode": RUN_MODES[run["run_manager"]], "seeding": seeding, "seeds": run["seeds"]},
            "output": output_settings}
    for key in ("first_event", "logical_run_seed", "threads"):
        if key in run:
            card["run"][key] = run[key]
    if ui_commands is not None:
        card["ui_commands"] = ui_commands
    return card


def _physics(physics: dict) -> dict:
    out: dict = {"cuts_mm": {"default": _text(physics["default_cut_mm"])}}
    for key in ("reference_list", "em_constructor", "decay"):
        if key in physics:
            out[key] = physics[key]
    if "regions" in physics:
        out["cuts_mm"]["regions"] = {region["name"]: _text(region["cut_mm"]) for region in physics["regions"]}
    return out


def _physics_back(physics: dict) -> dict:
    out: dict = {"default_cut_mm": _number(physics["cuts_mm"]["default"])}
    for key in ("reference_list", "em_constructor", "decay"):
        if key in physics:
            out[key] = physics[key]
    return out


def _split_layered(old: dict) -> tuple:
    _only(old, {"schema", "note", "source", "geometry", "gun", "materials", "output", "physics", "run", "ui_commands"}, "specification")
    geometry, gun = old["geometry"], old["gun"]
    _only(geometry, {"lateral_mm", "layers", "world"}, "geometry")
    _only(geometry["world"], {"material", "scale", "size_mm"}, "geometry.world")
    _only(gun, {"direction", "energy_MeV", "particle", "world_fraction"}, "gun")
    _only(old["physics"], {"decay", "default_cut_mm", "em_constructor", "reference_list", "regions"}, "physics")
    _only(old["run"], {"events", "run_manager", "seeds"}, "run")
    region_of = {slab: region["name"] for region in old["physics"].get("regions", []) for slab in region["slabs"]}
    lateral = _text(geometry["lateral_mm"])
    templates: dict = {}
    children, groups = [], []
    stack = Decimal(0)
    for layer in geometry["layers"]:
        _only(layer, {"repeat", "slabs"}, "layer")
        period = sum((Decimal(_text(slab["thickness_mm"])) for slab in layer["slabs"]), Decimal(0))
        stack = add(stack, multiply(period, Decimal(layer["repeat"])))
    cursor = CONTEXT.minus(divide(stack, Decimal(2)))
    for layer in geometry["layers"]:
        period = sum((Decimal(_text(slab["thickness_mm"])) for slab in layer["slabs"]), Decimal(0))
        start, names = cursor, []
        for slab in layer["slabs"]:
            _only(slab, {"material", "name", "sensitive", "thickness_mm"}, "slab")
            thickness = _text(slab["thickness_mm"])
            template = _box([thickness, lateral, lateral], slab["material"])
            if slab["sensitive"]:
                template["tags"] = [SENSITIVE]
            if slab["name"] in region_of:
                template["region"] = region_of[slab["name"]]
            if templates.setdefault(slab["name"], template) != template:
                raise TranslationError(f"slab {slab['name']!r} is defined twice with different values")
            centre = add(start, divide(Decimal(thickness), Decimal(2)))
            children.append({"template": slab["name"], "placement": {"linear": {
                "count": layer["repeat"], "pitch_mm": [normalize_decimal(str(period)), "0", "0"],
                "start_mm": [normalize_decimal(str(centre)), "0", "0"]}}})
            start = add(start, Decimal(thickness))
            names.append(slab["name"])
        cursor = add(cursor, multiply(period, Decimal(layer["repeat"])))
        groups.append({"repeat": layer["repeat"], "slabs": names})
    world = {"material": geometry["world"]["material"], "children": children}
    if "size_mm" in geometry["world"]:
        world["size_mm"] = _texts(geometry["world"]["size_mm"])
    else:
        scale = Decimal(_text(geometry["world"]["scale"]))
        world["size_mm"] = [normalize_decimal(str(multiply(scale, stack)))] + [normalize_decimal(str(multiply(scale, Decimal(lateral))))] * 2
    detector = {"schema": "detector-spec/1", "materials": {m["name"]: _material(m) for m in old["materials"]}, "templates": templates,
                "world": world, "legacy": {"format": LAYERED, "note": old["note"], "groups": groups,
                                           "material_order": [m["name"] for m in old["materials"]],
                                           "region_order": [r["name"] for r in old["physics"].get("regions", [])]}}
    if "scale" in geometry["world"]:
        detector["legacy"]["world_scale"] = _text(geometry["world"]["scale"])
    if "source" in old:
        detector["legacy"]["source"] = old["source"]
    request = {"schema": "simulation-request/1", "source": {
        "density": "analytic", "particle": gun["particle"], "energy": {"mono": {"energy_MeV": _text(gun["energy_MeV"])}},
        "position": {"world_fraction": _text(gun["world_fraction"])}, "direction": {"fixed": {"frame": "world", "vector": gun["direction"]}}}}
    return detector, request, _run_card(_physics(old["physics"]), old["run"], old["output"], old["ui_commands"], "stream", {})


def _merge_layered(detector: dict, request: dict, card: dict) -> dict:
    legacy, source, templates = detector["legacy"], request["source"], detector["templates"]
    layers = []
    for group in legacy["groups"]:
        slabs = [{"material": templates[name]["material"], "name": name, "sensitive": SENSITIVE in templates[name].get("tags", []),
                  "thickness_mm": _number(_size(templates[name])[0])} for name in group["slabs"]]
        layers.append({"repeat": group["repeat"], "slabs": slabs})
    first = templates[legacy["groups"][0]["slabs"][0]]
    physics = _physics_back(card["physics"])
    regions = card["physics"]["cuts_mm"].get("regions")
    if regions is not None:
        physics["regions"] = [{"cut_mm": _number(regions[name]), "name": name, "slabs": [
            slab for group in legacy["groups"] for slab in group["slabs"] if templates[slab].get("region") == name]}
            for name in legacy["region_order"]]
    world = {"material": detector["world"]["material"]}
    if "world_scale" in legacy:
        world["scale"] = _number(legacy["world_scale"])
    else:
        world["size_mm"] = _numbers(detector["world"]["size_mm"])
    document = {"geometry": {"lateral_mm": _number(_size(first)[1]), "layers": layers, "world": world},
            "gun": {"direction": source["direction"]["fixed"]["vector"], "energy_MeV": _number(source["energy"]["mono"]["energy_MeV"]),
                    "particle": source["particle"], "world_fraction": _number(source["position"]["world_fraction"])},
            "materials": [_material_back(name, detector["materials"][name]) for name in legacy["material_order"]],
            "note": legacy["note"], "output": card["output"], "physics": physics,
            "run": {"events": card["run"]["events"], "run_manager": card["run"]["mode"], "seeds": card["run"]["seeds"]},
            "schema": LAYERED, "ui_commands": card["ui_commands"]}
    if "source" in legacy:
        document["source"] = legacy["source"]
    return document


def _in_mother(centre: list[str], mother: list[str] | None) -> list[str]:
    """An old centre is in world coordinates, also for a daughter; a placement is in its mother's frame."""
    if mother is None:
        return centre
    return [normalize_decimal(str(subtract(Decimal(a), Decimal(b)))) for a, b in zip(centre, mother)]


def _in_world(local: list[str], mother: list[str] | None) -> list[float]:
    if mother is None:
        return _numbers(local)
    return [float(add(Decimal(a), Decimal(b))) for a, b in zip(local, mother)]


def _split_element(old: dict) -> tuple:
    _only(old, {"schema", "note", "elements", "field", "materials", "output", "physics", "provenance", "run", "source", "world"},
          "specification")
    source, field = old["source"], old.get("field")
    _only(source, {"direction", "energy_MeV", "particle", "position_mm", "type"}, "source")
    _only(old["physics"], {"default_cut_mm", "em_constructor", "reference_list"}, "physics")
    _only(old["run"], {"events", "first_event", "logical_run_seed", "run_manager", "seeding", "seeds", "threads"}, "run")
    _only(old["world"], {"half_mm", "material"}, "world")
    templates: dict = {}
    children: dict = {"world": []}
    centres = {element["name"]: _texts(element["centre_mm"]) for element in old["elements"]}
    for element in old["elements"]:
        _only(element, {"centre_mm", "half_mm", "material", "mother", "name", "repeat", "role"}, "element")
        local = _in_mother(centres[element["name"]], centres.get(element.get("mother")))
        size = [normalize_decimal(str(multiply(Decimal(_text(half)), Decimal(2)))) for half in element["half_mm"]]
        templates[element["name"]] = {**_box(size, element["material"]), "tags": [ROLE_PREFIX + element["role"]]}
        if "repeat" in element:
            _only(element["repeat"], {"count", "pitch_mm"}, "repeat")
            placement = {"linear": {"count": element["repeat"]["count"], "pitch_mm": _texts(element["repeat"]["pitch_mm"]),
                                    "start_mm": local}}
        else:
            placement = {"single": {"centre_mm": local}}
        children.setdefault(element.get("mother", "world"), []).append({"template": element["name"], "placement": placement})
    for name, placed in children.items():
        if name != "world":
            if name not in templates:
                raise TranslationError(f"mother {name!r} is not an element")
            templates[name]["children"] = placed
    fields = {}
    integration = None
    if field is not None:
        integration = {key: value for key, value in field.items() if key != "regions"}
        for at, region in enumerate(field["regions"]):
            _only(region, {"b_tesla", "element"}, "field region")
            fields[f"field_{at}"] = {"b_tesla": _texts(region["b_tesla"])}
            templates[region["element"]]["field"] = f"field_{at}"
    size = [normalize_decimal(str(multiply(Decimal(_text(half)), Decimal(2)))) for half in old["world"]["half_mm"]]
    legacy = {"format": ELEMENT, "element_order": [element["name"] for element in old["elements"]],
              "material_order": [m["name"] for m in old.get("materials", [])], "has_materials": "materials" in old,
              "field_order": [region["element"] for region in field["regions"]] if field else None}
    for key in ("note", "provenance"):
        if key in old:
            legacy[key] = old[key]
    detector = {"schema": "detector-spec/1", "materials": {m["name"]: _material(m) for m in old.get("materials", [])},
                "templates": templates, "fields": fields, "world": {"material": old["world"]["material"], "size_mm": size, "children": children["world"]},
                "legacy": legacy}
    request = {"schema": "simulation-request/1", "source": {
        "density": "analytic", "particle": source["particle"], "energy": {"mono": {"energy_MeV": _text(source["energy_MeV"])}},
        "position": {"point": {"frame": "world", "centre_mm": _texts(source["position_mm"])}},
        "direction": {"fixed": {"frame": "world", "vector": _texts(source["direction"])}}}}
    return detector, request, _run_card(_physics(old["physics"]), old["run"], old["output"], None, old["run"]["seeding"], {"field": integration})


def _half(text: str) -> float:
    return float(divide(Decimal(text), Decimal(2)))


def _mother_centre(placed: dict, mother: str) -> list[str] | None:
    """A mother is placed once in the world (element_sim's rule), so its placement holds its world centre."""
    if mother == "world":
        return None
    body = placed[mother][1]["placement"]
    return (body.get("single") or body["linear"]).get("centre_mm") or body["linear"]["start_mm"]


def _merge_element(detector: dict, request: dict, card: dict) -> dict:
    legacy, source, templates = detector["legacy"], request["source"], detector["templates"]
    placed = {item["template"]: ("world", item) for item in detector["world"]["children"]}
    for name, template in templates.items():
        for item in template.get("children", []):
            placed[item["template"]] = (name, item)
    elements = []
    for name in legacy["element_order"]:
        template = templates[name]
        mother, item = placed[name]
        body = item["placement"].get("single") or item["placement"]["linear"]
        element = {"centre_mm": _in_world(body.get("centre_mm") or body["start_mm"], _mother_centre(placed, mother)),
                   "half_mm": [_half(text) for text in _size(template)],
                   "material": template["material"], "name": name, "role": template["tags"][0].removeprefix(ROLE_PREFIX)}
        if mother != "world":
            element["mother"] = mother
        if "linear" in item["placement"]:
            element["repeat"] = {"count": body["count"], "pitch_mm": _numbers(body["pitch_mm"])}
        elements.append(element)
    run = {key: card["run"][key] for key in ("events", "first_event", "logical_run_seed", "seeding", "seeds", "threads")}
    run["run_manager"] = card["run"]["mode"]
    out = {"elements": elements, "output": card["output"], "physics": _physics_back(card["physics"]), "run": run, "schema": ELEMENT,
           "source": {"direction": _numbers(source["direction"]["fixed"]["vector"]), "energy_MeV": _number(source["energy"]["mono"]["energy_MeV"]),
                      "particle": source["particle"], "position_mm": _numbers(source["position"]["point"]["centre_mm"]), "type": "gun"},
           "world": {"half_mm": [_half(text) for text in detector["world"]["size_mm"]], "material": detector["world"]["material"]}}
    if legacy["has_materials"]:
        out["materials"] = [_material_back(name, detector["materials"][name]) for name in legacy["material_order"]]
    if legacy["field_order"] is not None:
        out["field"] = {**card["field_integration"], "regions": [
            {"b_tesla": _numbers(detector["fields"][templates[name]["field"]]["b_tesla"]), "element": name} for name in legacy["field_order"]]}
    for key in ("note", "provenance"):
        if key in legacy:
            out[key] = legacy[key]
    return out


def key_layout(value):
    """The key order of a document where it is not alphabetical: key names only, never a value; None when all is sorted."""
    if isinstance(value, dict):
        below = {key: layout for key, item in value.items() if (layout := key_layout(item)) is not None}
        keys = list(value)
        return {"keys": keys, "below": below} if keys != sorted(keys) or below else None
    if isinstance(value, list):
        below = {str(at): layout for at, item in enumerate(value) if (layout := key_layout(item)) is not None}
        return {"below": below} if below else None
    return None


def _ordered(value, layout):
    if isinstance(value, dict):
        layout = layout or {}
        keys = layout.get("keys") or sorted(value)
        return {key: _ordered(value[key], layout.get("below", {}).get(key)) for key in keys}
    if isinstance(value, list):
        below = (layout or {}).get("below", {})
        return [_ordered(item, below.get(str(at))) for at, item in enumerate(value)]
    return value


def split(old: dict) -> tuple:
    """(detector-spec/1, simulation-request/1, g4sim-run/1) of an old specification."""
    if old.get("schema") == LAYERED:
        parts = _split_layered(old)
    elif old.get("schema") == ELEMENT:
        parts = _split_element(old)
    else:
        raise TranslationError(f"{old.get('schema')!r} is not an old specification")
    layout = key_layout(old)
    if layout is not None:
        parts[0]["legacy"]["key_layout"] = layout
    return parts


def merge(detector: dict, request: dict, card: dict) -> dict:
    document = (_merge_layered if detector["legacy"]["format"] == LAYERED else _merge_element)(detector, request, card)
    return _ordered(document, detector["legacy"].get("key_layout"))


def _material_record(base: dict, derived: dict) -> dict:
    keys = ("name", "density_g_cm3", "state", "temperature_K", "pressure_Pa", "mean_excitation_energy_eV", "elements")
    return {**{key: base[key] for key in keys}, **{key: value for key, value in derived.items() if key != "name"}}


def _old_roles(old: dict) -> dict:
    return {element["name"]: {"role": element["role"], "mother": element.get("mother")} for element in old.get("elements", [])}


def legacy_block(record: dict, old: dict, seeding: str) -> dict:
    """The legacy block of a T1-class run (Section 7.1): every value from a ProbeV2 record, as float.hex() strings, plus what only
    the old specification knows. A record that did not record, or changed the random state, cannot be used."""
    if record.get("recorded") is not True or record.get("random_state_unchanged") is not True:
        raise TranslationError("the re-acquisition record did not record, or changed the random state")
    geometry = record["base"]["geometry"]
    derived = {item["name"]: item for item in record["materials"]}
    return {"source": "probe", "seeding": seeding, "positions": geometry["placements"], "logical_volumes": geometry["logical_volumes"],
            "materials": [_material_record(item, derived[item["name"]]) for item in geometry["materials"]],
            "regions": record["regions"], "fields": record["logical_fields"], "processes": record["processes"], "roles": _old_roles(old)}


def _hex_equal(text: str, value: float) -> bool:
    return float.fromhex(text) == value


def block_differences(block: dict, record: dict) -> list[str]:
    """Where a legacy block differs from the record it must equal (S1 gate 4)."""
    expected = legacy_block(record, {"elements": []}, block["seeding"])
    return [key for key in expected if key != "roles" and block.get(key) != expected[key]]


def position_differences(block: dict, old: dict) -> list[str]:
    """Placements of an element_sim record whose translation is not, bit for bit, what the old program computes from the old
    specification: the world centre less the mother's, in double precision."""
    elements = {element["name"]: element for element in old.get("elements", [])}
    out = []
    for placement in block["positions"]:
        element = elements.get(placement["name"])
        if element is None or placement["copy_number"] != 0:
            continue
        origin = elements[element["mother"]]["centre_mm"] if element.get("mother", "world") != "world" else [0.0, 0.0, 0.0]
        wanted = [a - b for a, b in zip(element["centre_mm"], origin)]
        if not all(_hex_equal(text, value) for text, value in zip(placement["translation_mm"], wanted)):
            out.append(placement["name"])
    return out


def as_file(document: dict) -> str:
    """The text of a specification as the recorded files hold it: merge has already put its keys in the file's order."""
    return json.dumps(document, indent=1) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("split", "check"))
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        original = args.spec.read_text(encoding="utf-8")
        parts = split(json.loads(original))
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    if args.command == "split":
        if args.out is None:
            print(json.dumps({"status": "error", "message": "split needs --out"}))
            return 2
        args.out.mkdir(parents=True, exist_ok=True)
        for name, part in zip(("detector", "request", "run"), parts):
            (args.out / f"{name}.json").write_text(json.dumps(part, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok"}))
        return 0
    same = as_file(merge(*parts)) == original
    print(json.dumps({"status": "ok" if same else "failed", "round_trip": same}))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
