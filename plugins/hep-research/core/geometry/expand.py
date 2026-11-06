"""Expansion of detector-spec/1 into geometry-ir/1 (Sections 6.2, 7.1): templates, placements, copy numbers, regions, fields,
bitfields and the strides of volume IDs. The physical part fixes geometry_id and the marker part provenance_id.

Takes a specification whose numbers went through core.canonical.load_spec_json, so every quantity is a decimal/1 string or a
params expression. Expansion is pure computation: core.geometry.overlap computes the gap rule, contracts/geometry.py judges.
"""
from __future__ import annotations

from decimal import Decimal

from core.canonical import check_hash_scope
from core.geometry import bitfield, modules, params, rotation
from core.geometry.numbers import CONTEXT, EPSILON_MM, MINIMUM_GAP_MM, PRECISION, GeometryError, add, as_text, divide

WORLD = "world"
DEFAULT_REGION = "default"
NO_FIELD = "none"
NIST_PREFIX = "G4_"
_AXES = {"x": 0, "y": 1, "z": 2}
_ZERO = Decimal(0)


class _Values:
    def __init__(self, table: dict):
        self.values = params.resolve(table)

    def quantity(self, text, path: str) -> Decimal:
        def lookup(name):
            if name not in self.values:
                raise GeometryError("params-unknown", f"{name!r} is not in params", path)
            return self.values[name]
        return params.evaluate(text, lookup)

    def vector(self, items, path: str) -> tuple:
        if not isinstance(items, list) or len(items) != 3:
            raise GeometryError("vector-form", f"{items!r} is not three values", path)
        return tuple(self.quantity(item, f"{path}/{i}") for i, item in enumerate(items))


def _solid(template: dict, values: _Values, path: str) -> tuple:
    solid = template.get("solid")
    if not isinstance(solid, dict) or len(solid) != 1:
        raise GeometryError("solid-form", "a template has exactly one solid", path)
    (shape, parameters), = solid.items()
    modules.require_open(modules.SHAPES, shape, "shape", path)
    size = values.vector(parameters["size_mm"], f"{path}/solid/box/size_mm")
    if any(side <= 0 for side in size):
        raise GeometryError("solid-size", "a size is positive", path)
    return size


def _rotation(placement: dict, values: _Values, path: str):
    declared = placement.get("rotation")
    if declared is None:
        return rotation.IDENTITY
    resolved = dict(declared)
    if "zyx_deg" in resolved:
        resolved["zyx_deg"] = list(values.vector(resolved["zyx_deg"], f"{path}/rotation/zyx_deg"))
    if "angle_deg" in resolved:
        resolved["angle_deg"] = values.quantity(resolved["angle_deg"], f"{path}/rotation/angle_deg")
    return rotation.active_matrix(resolved, path)


def _single(child: dict, body: dict, values: _Values, path: str) -> list[dict]:
    return [{"template": child["template"], "centre": values.vector(body["centre_mm"], f"{path}/centre_mm"),
             "active": _rotation(body, values, path), "index": None}]


def _linear(child: dict, body: dict, values: _Values, path: str) -> list[dict]:
    count, name = body["count"], body.get("index")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise GeometryError("placement-count", f"count {count!r} is not a positive integer", path)
    pitch = values.vector(body["pitch_mm"], f"{path}/pitch_mm")
    centre = values.vector(body["start_mm"], f"{path}/start_mm")
    out = []
    for n in range(count):
        out.append({"template": child["template"], "centre": centre, "active": rotation.IDENTITY,
                    "index": {name: n} if name else None})
        centre = tuple(add(a, b) for a, b in zip(centre, pitch))
    return out


def _index_widths(names: list, counts: list, fields: dict, path: str) -> list[int]:
    """The field width of each index of a multi-index placement: the readout's, or the least that holds it. Together they fit a copy number."""
    widths = [fields.get(name, bitfield.width_for(count)) for name, count in zip(names, counts)]
    if sum(widths) > bitfield.COPY_FIELD_LIMIT:
        raise GeometryError("copy-width", f"fields {names} total {sum(widths)} bits; a copy number holds {bitfield.COPY_FIELD_LIMIT}", path)
    return widths


def _grid(child: dict, body: dict, values: _Values, fields: dict, path: str) -> list[dict]:
    counts, names = body["n"], body.get("index", [])
    if len(counts) not in (2, 3) or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in counts):
        raise GeometryError("placement-count", f"n {counts!r} is not two or three positive integers", path)
    if len(names) != len(counts):
        raise GeometryError("grid-index", f"{len(counts)} dimensions need as many index names, not {names!r}", path)
    pitch = [values.quantity(item, f"{path}/pitch_mm/{i}") for i, item in enumerate(body["pitch_mm"])]
    if len(pitch) != len(counts):
        raise GeometryError("vector-form", f"{len(counts)} dimensions need as many pitches", path)
    pitch += [_ZERO] * (3 - len(pitch))
    centre = values.vector(body["centre_mm"], f"{path}/centre_mm")
    stagger = values.quantity(body["stagger_mm"], f"{path}/stagger_mm") if "stagger_mm" in body else _ZERO  # along x, on odd rows of j
    widths = _index_widths(names, counts, fields, path)
    sizes = list(counts) + [1] * (3 - len(counts))
    # the position given is the centre of the whole grid, not of its first cell (Section 6.2.2)
    first = [add(centre[a], CONTEXT.multiply(pitch[a], divide(Decimal(1 - sizes[a]), Decimal(2)))) for a in range(3)]
    out = []
    for k in range(sizes[2]):
        for j in range(sizes[1]):
            for i in range(sizes[0]):
                cell = [add(first[a], CONTEXT.multiply(pitch[a], Decimal((i, j, k)[a]))) for a in range(3)]
                if j % 2:
                    cell[0] = add(cell[0], stagger)
                at = (i, j, k)[:len(counts)]
                packed, shift = 0, 0
                for value, width in zip(at, widths):
                    packed += value << shift
                    shift += width
                out.append({"template": child["template"], "centre": tuple(cell), "active": rotation.IDENTITY,
                            "index": dict(zip(names, at)), "packed": packed})
    return out


def _explicit(child: dict, body: dict, values: _Values, path: str) -> list[dict]:
    name = body.get("index")
    positions = body["positions_mm"]
    if not positions:
        raise GeometryError("placement-count", "an explicit placement has at least one position", path)
    return [{"template": child["template"], "centre": values.vector(item, f"{path}/positions_mm/{n}"), "active": rotation.IDENTITY,
             "index": {name: n} if name else None} for n, item in enumerate(positions)]


def _stack(body: dict, mother_size: tuple, sizes: dict, values: _Values, path: str) -> list[dict]:
    axis, start = body["axis"], body["from"]
    if axis not in _AXES or start not in (f"-{axis}", f"+{axis}"):
        raise GeometryError("stack-form", f"axis {axis!r} from {start!r}", path)
    i, sign = _AXES[axis], (1 if start.startswith("-") else -1)
    repeat = body.get("repeat", 1)
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
        raise GeometryError("placement-count", f"repeat {repeat!r} is not a positive integer", path)
    face = CONTEXT.multiply(Decimal(-sign), divide(mother_size[i], Decimal(2)))  # exact accumulation from this face
    out = []
    for layer in range(repeat):
        for at, item in enumerate(body["sequence"]):
            where = f"{path}/sequence/{at}"
            if isinstance(item, dict) and "spacer_mm" in item:
                if "material" in item:
                    raise GeometryError("module-not-open", "a gap volume with a material opens with optical_scope", where)
                length = values.quantity(item["spacer_mm"], f"{where}/spacer_mm")
                face = add(face, CONTEXT.multiply(Decimal(sign), length))
                continue
            name = item if isinstance(item, str) else item["template"]
            index = None if isinstance(item, str) else item.get("index")
            if name not in sizes:
                raise GeometryError("template-unknown", f"{name!r} is not a template", where)
            thickness = sizes[name][i]
            far = add(face, CONTEXT.multiply(Decimal(sign), thickness))
            centre = [_ZERO, _ZERO, _ZERO]
            centre[i] = divide(add(face, far), Decimal(2))
            out.append({"template": name, "centre": tuple(centre), "active": rotation.IDENTITY,
                        "index": {index: layer} if index else None})
            face = far
    return out


def _children(mother: str, node: dict, sizes: dict, values: _Values, path: str, fields: dict | None = None) -> list[dict]:
    placed = []
    for at, child in enumerate(node.get("children", [])):
        where = f"{path}/children/{at}"
        placement = child.get("placement")
        if not isinstance(placement, dict) or len(placement) != 1:
            raise GeometryError("placement-form", "a child has exactly one placement", where)
        (kind, body), = placement.items()
        modules.require_open(modules.PLACEMENTS, kind, "placement", where)
        if kind == "stack":
            items = _stack(body, sizes[mother], sizes, values, f"{where}/placement/stack")
        else:
            if child.get("template") not in sizes:
                raise GeometryError("template-unknown", f"{child.get('template')!r} is not a template", where)
            at = f"{where}/placement/{kind}"
            if kind == "grid":
                items = _grid(child, body, values, fields or {}, at)
            elif kind == "explicit":
                items = _explicit(child, body, values, at)
            else:
                items = (_single if kind == "single" else _linear)(child, body, values, at)
        placed.extend(items)
    return _number_copies(placed, path)


def _number_copies(placed: list[dict], path: str) -> list[dict]:
    """Indexed placements keep their index; the others take the next free numbers, in order (g4sim-approvals.md)."""
    taken: dict[int, str] = {}
    for item in placed:
        if item["index"]:
            value = item["packed"] if "packed" in item else next(iter(item["index"].values()))
            if value in taken:
                raise GeometryError("copy-collision", f"copy number {value} is used twice in one mother ({taken[value]!r} and "
                                                      f"{item['template']!r}); wrap one in its own template", path)
            taken[value] = item["template"]
            item["copy_number"] = value
    free = max(taken, default=-1) + 1
    for item in placed:
        if not item["index"]:
            item["copy_number"] = free
            free += 1
    return placed


def _order(tree: dict) -> list[str]:
    """Templates reachable from the world, mothers before daughters; a template inside itself is refused."""
    state: dict[str, int] = {}
    order: list[str] = []

    def visit(name: str, trail: list[str]) -> None:
        if state.get(name) == 1:
            raise GeometryError("template-cycle", " -> ".join([*trail, name]))
        if state.get(name) == 2:
            return
        state[name] = 1
        for daughter in dict.fromkeys(item["template"] for item in tree[name]):
            visit(daughter, [*trail, name])
        state[name] = 2
        order.append(name)

    visit(WORLD, [])
    return order[::-1]


def _inherited(key: str, default: str, nodes: dict, tree: dict, order: list[str]) -> dict:
    """What each logical actually belongs to: its own declaration, else its mother's value; no value is also a value."""
    resolved: dict[str, str] = {WORLD: nodes[WORLD].get(key) or default}
    for mother in order:
        for item in tree[mother]:
            daughter = item["template"]
            value = nodes[daughter].get(key) or resolved[mother]
            if resolved.setdefault(daughter, value) != value:
                raise GeometryError(f"{key}-conflict", f"template {daughter!r} falls into {resolved[daughter]!r} and {value!r} "
                                                       "through different mothers")
    return resolved


def _level_strides(tree: dict) -> list[int]:
    """Strides of the placement levels: the widest value (copy number + 1) of any placement at each depth."""
    widest: dict[int, int] = {}

    def walk(name: str, depth: int, seen: set) -> None:
        if (name, depth) in seen:
            return
        seen.add((name, depth))
        for item in tree[name]:
            widest[depth] = max(widest.get(depth, 0), item["copy_number"] + 1)
            walk(item["template"], depth + 1, seen)

    walk(WORLD, 0, set())
    return bitfield.level_strides([value.bit_length() for _, value in sorted(widest.items())])


def _selected(tags: dict, select: dict) -> list[str]:
    wanted = set(select.get("tags", []))
    return sorted(name for name, own in tags.items() if wanted <= set(own))


def _requirements(spec: dict, tags: dict) -> list[dict]:
    out = []
    for at, requirement in enumerate(spec.get("physics_requirements", [])):
        expanded = {key: value for key, value in requirement.items() if key != "select"}
        if "select" in requirement:
            expanded["templates"] = _selected(tags, requirement["select"])
            if not expanded["templates"]:
                raise GeometryError("select-empty", "the selection matches no template", f"/physics_requirements/{at}")
        out.append(expanded)
    return out


def _readout(spec: dict, tree: dict) -> dict:
    counts: dict[str, int] = {}
    for placed in tree.values():
        for item in placed:
            for name, value in (item["index"] or {}).items():
                counts[name] = max(counts.get(name, 0), value + 1)
    out = {}
    for name, readout in spec.get("readout", {}).items():
        where = f"/readout/{name}"
        layout = bitfield.layout(readout["fields"], set(counts) & set(readout["fields"]), where)
        bitfield.check_range(layout, {key: value for key, value in counts.items() if key in readout["fields"]}, where)
        out[name] = {"fields": layout}
    return out


def _without_sources(value):
    """A material's physical content: its source labels ("facts") belong to the marker part."""
    if isinstance(value, dict):
        return {key: _without_sources(item) for key, item in value.items() if key != "facts"}
    return [_without_sources(item) for item in value] if isinstance(value, list) else value


def _sources(value, path: str = "") -> dict:
    out: dict = {}
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "facts":
                out[path] = item
            else:
                out.update(_sources(item, f"{path}/{key}"))
    return out


def _frames(spec: dict, values: _Values, templates: dict) -> dict:
    out = {}
    for name, frame in spec.get("frames", {}).items():
        where = f"/frames/{name}"
        if frame["in"] not in templates:
            raise GeometryError("template-unknown", f"{frame['in']!r} is not a template", where)
        out[name] = {"in": frame["in"], "origin_mm": [as_text(v) for v in values.vector(frame["origin_mm"], f"{where}/origin_mm")]}
    return out


def expand(spec: dict) -> dict:
    """The geometry-ir/1 document of a specification."""
    if spec.get("schema") != "detector-spec/1":
        raise GeometryError("schema", f"{spec.get('schema')!r} is not detector-spec/1")
    if WORLD in spec.get("templates", {}):
        raise GeometryError("template-name", f"{WORLD!r} is reserved", "/templates")
    values = _Values(spec.get("params", {}))
    nodes = {**spec.get("templates", {}), WORLD: spec["world"]}
    sizes = {name: _solid(node, values, f"/templates/{name}") for name, node in spec.get("templates", {}).items()}
    sizes[WORLD] = values.vector(spec["world"]["size_mm"], "/world/size_mm")
    for name, node in nodes.items():
        if not node["material"].startswith(NIST_PREFIX) and node["material"] not in spec.get("materials", {}):
            raise GeometryError("material-unknown", f"{node['material']!r} is neither a NIST name nor declared", f"/templates/{name}")
    fields = {name: width for readout in spec.get("readout", {}).values() for name, width in readout["fields"].items()}
    tree = {name: _children(name, node, sizes, values, f"/templates/{name}", fields) for name, node in nodes.items()}
    order = _order(tree)
    regions = _inherited("region", DEFAULT_REGION, nodes, tree, order)
    fields = _inherited("field", NO_FIELD, nodes, tree, order)
    tags = {name: nodes[name].get("tags", []) for name in order}
    templates = {name: {"half_mm": [as_text(divide(side, Decimal(2))) for side in sizes[name]], "shape": "box",
                        "material": nodes[name]["material"], "region": regions[name], "field": fields[name]} for name in order}
    placements = [{"mother": mother, "template": item["template"], "copy_number": item["copy_number"],
                   "index": item["index"] or {}, "centre_mm": [as_text(v) for v in item["centre"]],
                   "rotation": None if item["active"] == rotation.IDENTITY
                   else [list(row) for row in rotation.passive_matrix(item["active"])]}
                  for mother in order for item in tree[mother]]
    physical = {"numerics": {"precision": PRECISION, "rounding": "half-even", "epsilon_mm": as_text(EPSILON_MM),
                             "minimum_gap_mm": as_text(MINIMUM_GAP_MM), "decimal": "decimal/1"},
                "templates": templates, "placements": placements, "frames": _frames(spec, values, templates),
                "readout": _readout(spec, tree), "volume_id": {"rule": "sum of (copy_number + 1) * stride",
                                                               "strides": _level_strides(tree)},
                "materials": _without_sources(spec.get("materials", {})), "physics_requirements": _requirements(spec, tags)}
    if spec.get("fields"):  # optional: a specification with no field keeps its geometry_id (Section 7.1)
        physical["fields"] = spec["fields"]
    marker = {"tags": {name: sorted(own) for name, own in tags.items() if own}, "derivations": spec.get("params", {}),
              "source_of_facts": spec.get("source_of_facts", {}), "material_sources": _sources(spec.get("materials", {}))}
    document = {"schema": "geometry-ir/1", "physical": physical, "marker": marker}
    issues = check_hash_scope(document)
    if issues:
        raise GeometryError("hash-scope", f"{issues[0]['code']} at {issues[0]['path']}: {issues[0]['message']}")
    return document
