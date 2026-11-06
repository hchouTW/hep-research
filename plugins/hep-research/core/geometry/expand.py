"""Expansion of detector-spec/1 into geometry-ir/1 (Sections 6.2, 7.1): templates, placements, copy numbers, regions, fields,
bitfields and the strides of volume IDs. The physical part fixes geometry_id and the marker part provenance_id.

Takes a specification whose numbers went through core.canonical.load_spec_json, so every quantity is a decimal/1 string or a
params expression. Expansion is pure computation: core.geometry.overlap computes the gap rule, contracts/geometry.py judges.
"""
from __future__ import annotations

import copy
from decimal import Decimal

from core.canonical import check_hash_scope
from core.geometry import bitfield, modules, params, rotation
from core.geometry.numbers import CONTEXT, EPSILON_MM, MINIMUM_GAP_MM, PRECISION, GeometryError, add, as_text, divide, multiply

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
    if shape != "box":
        return _other_solid(shape, parameters, values, f"{path}/solid/{shape}")[0]
    size = values.vector(parameters["size_mm"], f"{path}/solid/box/size_mm")
    if any(side <= 0 for side in size):
        raise GeometryError("solid-size", "a size is positive", path)
    return size


def _other_solid(shape: str, body: dict, values: _Values, path: str) -> tuple:
    """(bounding size, the IR's half-lengths) of a shape other than a box. A specification gives full lengths; the IR holds what G4 takes."""
    def length(key: str) -> Decimal:
        value = values.quantity(body[key], f"{path}/{key}")
        if value < _ZERO or (value == _ZERO and key not in ("rmin_mm",)):
            raise GeometryError("solid-size", f"{key} {value} is not positive", path)
        return value

    def half(value: Decimal) -> str:
        return as_text(divide(value, Decimal(2)))
    if shape == "trd":
        x1, x2, y1, y2, z = (length(key) for key in ("x1_mm", "x2_mm", "y1_mm", "y2_mm", "length_mm"))
        return (max(x1, x2), max(y1, y2), z), {"dx1_mm": half(x1), "dx2_mm": half(x2), "dy1_mm": half(y1), "dy2_mm": half(y2), "dz_mm": half(z)}
    if shape == "tube":
        rmin, rmax, z = length("rmin_mm"), length("rmax_mm"), length("length_mm")
        if rmin >= rmax:
            raise GeometryError("solid-size", f"rmin {rmin} is not below rmax {rmax}", path)
        start = values.quantity(body.get("phi_start_deg", "0"), f"{path}/phi_start_deg")
        span = values.quantity(body.get("phi_span_deg", "360"), f"{path}/phi_span_deg")
        if not _ZERO < span <= Decimal(360):
            raise GeometryError("solid-size", f"phi span {span} is outside (0, 360]", path)
        diameter = add(rmax, rmax)
        return (diameter, diameter, z), {"rmin_mm": as_text(rmin), "rmax_mm": as_text(rmax), "dz_mm": half(z), "phi_start_deg": as_text(start), "phi_span_deg": as_text(span)}
    sides = body["sides"]
    if isinstance(sides, bool) or not isinstance(sides, int) or sides < 3:
        raise GeometryError("solid-size", f"sides {sides!r} is not an integer of at least 3", path)
    radius, z = length("radius_mm"), length("length_mm")
    apothem = multiply(radius, rotation.cos_sin(divide(Decimal(180), Decimal(sides)))[0])  # G4Polyhedra's rOuter is the apothem (GB23)
    diameter = add(radius, radius)
    return (diameter, diameter, z), {"sides": sides, "circumradius_mm": as_text(radius), "apothem_mm": as_text(apothem), "dz_mm": half(z)}


def _shape_of(node: dict) -> str:
    return next(iter(node.get("solid", {"box": None})))


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


def _ring(child: dict, body: dict, values: _Values, path: str) -> list[dict]:
    """Copies around z at the same exact angles 360 k / n, so abutting faces come from one value. orientation radial turns local z outward."""
    count, name = body["n"], body.get("index")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise GeometryError("placement-count", f"n {count!r} is not a positive integer", path)
    radius = values.quantity(body["radius_mm"], f"{path}/radius_mm")
    first = values.quantity(body.get("phi0_deg", "0"), f"{path}/phi0_deg")
    tilt = values.quantity(body.get("tilt_deg", "0"), f"{path}/tilt_deg")
    stagger = values.quantity(body.get("stagger_mm", "0"), f"{path}/stagger_mm")  # outward on odd copies
    orientation = body.get("orientation", "radial")
    if orientation not in ("radial", "fixed"):
        raise GeometryError("ring-form", f"orientation {orientation!r} is neither radial nor fixed", path)
    z = values.quantity(body.get("z_mm", "0"), f"{path}/z_mm")
    out = []
    for k in range(count):
        angle = add(first, divide(multiply(Decimal(360), Decimal(k)), Decimal(count)))
        c, s = rotation.cos_sin(angle)
        reach = add(radius, stagger) if k % 2 else radius
        active = rotation.IDENTITY
        if orientation == "radial":
            active = rotation.product(rotation.active_matrix({"axis": "z", "angle_deg": angle}), rotation.active_matrix({"axis": "y", "angle_deg": Decimal(90)}))
            if tilt != _ZERO:
                active = rotation.product(active, rotation.active_matrix({"axis": "x", "angle_deg": tilt}))
        out.append({"template": child["template"], "centre": (multiply(reach, Decimal(c)), multiply(reach, Decimal(s)), z), "active": active,
                    "index": {name: k} if name else None})
    return out


def _inside_envelope(centre: tuple, half: tuple, envelope: dict, mode: str, values: _Values, path: str) -> bool:
    """Whether a cell stays: a circular envelope in x and y, by its centre or by its whole footprint."""
    radius = values.quantity(envelope["radius_mm"], f"{path}/radius_mm")
    x, y = abs(centre[0]), abs(centre[1])
    if mode == "fully_inside":
        x, y = add(x, half[0]), add(y, half[1])
    elif mode != "centre_inside":
        raise GeometryError("clip-form", f"mode {mode!r} is neither centre_inside nor fully_inside", path)
    return add(multiply(x, x), multiply(y, y)) <= multiply(radius, radius)


def _modified(items: list, child: dict, sizes: dict, values: _Values, path: str) -> list:
    """clip and absent remove cells; the indices of those left keep their values, so removed ones stay vacant numbers (Section 6.2.3)."""
    for at, modifier in enumerate(child.get("modifiers", [])):
        (kind, body), = modifier.items()
        where = f"{path}/modifiers/{at}"
        modules.require_open(modules.MODIFIERS, kind, "modifier", where)
        if kind == "shell":
            raise GeometryError("modifier-form", "shell belongs to a template, not to a placement", where)
        if kind == "absent":
            removed = [dict(cell) for cell in body["cells"]]
            for cell in removed:
                if not any(item["index"] == cell for item in items):
                    raise GeometryError("absent-unknown", f"{cell!r} is not a cell of this placement", where)
            items = [item for item in items if item["index"] not in removed]
        else:
            half = tuple(divide(side, Decimal(2)) for side in sizes[child["template"]])
            items = [item for item in items if _inside_envelope(item["centre"], half, body["envelope"], body["mode"], values, where)]
    return items


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
            elif kind == "ring":
                items = _ring(child, body, values, at)
            else:
                items = (_single if kind == "single" else _linear)(child, body, values, at)
            items = _modified(items, child, sizes, values, where)
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


def _shell_size(size: list, thickness: str, faces: list) -> list:
    """The wrapper's size from the template's, in the specification's own expressions."""
    wide = f"2*({thickness})" if "sides" in faces else "0"
    deep = f"{('front' in faces) + ('back' in faces)}*({thickness})"
    return [f"({size[0]})+{wide}", f"({size[1]})+{wide}", f"({size[2]})+{deep}"]


def _renamed(children: list, replaced: str, wrapper: str) -> list:
    out = []
    for child in children:
        child = copy.deepcopy(child)
        if child.get("template") == replaced:
            child["template"] = wrapper
        stack = child.get("placement", {}).get("stack")
        if stack:
            stack["sequence"] = [wrapper if item == replaced else {**item, "template": wrapper} if isinstance(item, dict) and item.get("template") == replaced else item
                                 for item in stack["sequence"]]
        out.append(child)
    return out


def _with_shells(spec: dict) -> dict:
    """shell (Section 6.2.3): a wrapper template of the shell's material takes the template's place, with the template inside it, offset by the
    active faces. A wrapper that does not fit where it is placed fails containment: that is the error for insufficient space."""
    templates = spec.get("templates", {})
    if not any(node.get("modifiers") for node in templates.values()):
        return spec
    spec = copy.deepcopy(spec)
    for name in list(spec["templates"]):
        node = spec["templates"][name]
        modifiers = node.pop("modifiers", [])
        for at, modifier in enumerate(modifiers):
            where = f"/templates/{name}/modifiers/{at}"
            if set(modifier) != {"shell"}:
                raise GeometryError("modifier-form", f"{sorted(modifier)} is not a template modifier", where)
            modules.require_open(modules.MODIFIERS, "shell", "modifier", where)
            shell = modifier["shell"]
            if "box" not in node["solid"]:
                raise GeometryError("shell-shape", "a shell wraps a box", where)
            faces, thickness = shell["faces"], shell["thickness_mm"]
            if not set(faces) <= {"sides", "front", "back"} or not faces:
                raise GeometryError("shell-form", f"faces {faces!r}", where)
            front, back = "front" in faces, "back" in faces
            shift = "0" if front == back else f"({thickness})/2" if front else f"-({thickness})/2"  # the front face is -z
            wrapper = f"{name}_shell"
            spec["templates"][wrapper] = {"solid": {"box": {"size_mm": _shell_size(node["solid"]["box"]["size_mm"], thickness, faces)}}, "material": shell["material"],
                                          "children": [{"template": name, "placement": {"single": {"centre_mm": ["0", "0", shift]}}}]}
            for other, holder in [*spec["templates"].items(), ("world", spec["world"])]:
                if other != wrapper and holder.get("children"):
                    holder["children"] = _renamed(holder["children"], name, wrapper)
    return spec


def expand(spec: dict) -> dict:
    """The geometry-ir/1 document of a specification."""
    if spec.get("schema") != "detector-spec/1":
        raise GeometryError("schema", f"{spec.get('schema')!r} is not detector-spec/1")
    spec = _with_shells(spec)
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
    templates = {name: {"half_mm": [as_text(divide(side, Decimal(2))) for side in sizes[name]], "shape": _shape_of(nodes[name]),
                        "material": nodes[name]["material"], "region": regions[name], "field": fields[name]} for name in order}
    for name in order:
        if templates[name]["shape"] != "box":
            shape = templates[name]["shape"]
            templates[name]["solid"] = _other_solid(shape, nodes[name]["solid"][shape], values, f"/templates/{name}/solid/{shape}")[1]
    placements = [{"mother": mother, "template": item["template"], "copy_number": item["copy_number"],
                   "index": item["index"] or {}, "centre_mm": [as_text(v) for v in item["centre"]],
                   "rotation": None if item["active"] == rotation.IDENTITY
                   else [[value if isinstance(value, int) else as_text(value) for value in row] for row in rotation.passive_matrix(item["active"])]}
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
