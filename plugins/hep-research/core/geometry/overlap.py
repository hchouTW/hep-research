"""Computation of the gap rule, containment, minimum feature and the error bound on the IR (Section 7.3). A placed volume with no arbitrary
rotation is an axis-aligned box in its mother, judged exactly; one with an arbitrary rotation goes through core/geometry/convex.py.

Returns findings; contracts/geometry.py judges them. Checks run per logical, so the cost follows the number of placements in
a mother, never the number of touchables (Section 16).
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from core.geometry import bound, convex
from core.geometry.numbers import BOUND_LIMIT_MM, CONTEXT, EPSILON_MM, MINIMUM_FEATURE_MM, MINIMUM_GAP_MM, add, exact, multiply, subtract
from core.geometry.rotation import transpose

WORLD = "world"


def _finding(code: str, where: str, message: str) -> dict:
    return {"code": code, "path": where, "message": message}


def _active(placement: dict):
    """The active matrix of a placement: the IR holds the passive one, whose entries are integers or decimal strings."""
    return transpose(tuple(tuple(value if isinstance(value, int) else exact(value) for value in row) for row in placement["rotation"]))


def _arbitrary(placement: dict) -> bool:
    return bool(placement["rotation"]) and any(isinstance(value, str) for row in placement["rotation"] for value in row)


def _template(ir: dict, placement: dict) -> dict:
    return ir["physical"]["templates"][placement["template"]]


def _polyhedron(ir: dict, placement: dict) -> convex.Polyhedron:
    active = _active(placement) if placement["rotation"] else ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    template = _template(ir, placement)
    shape, solid = template["shape"], template.get("solid")
    if shape == "trd":
        body = convex.trd(solid)
    elif shape == "polygon_prism":
        body = convex.prism(solid["sides"], exact(solid["circumradius_mm"]), exact(solid["dz_mm"]))
    elif shape == "tube":
        body = convex.circumscribed(exact(solid["rmax_mm"]), exact(solid["dz_mm"]))
    else:
        body = convex.box(_half(ir, placement["template"]))
    return body.placed(active, tuple(exact(text) for text in placement["centre_mm"]))


def _curved(ir: dict, placement: dict) -> bool:
    return _template(ir, placement)["shape"] == "tube"


def _about_own_axis(placement: dict) -> bool:
    """No rotation, or one about the tube's z axis alone."""
    if not placement["rotation"]:
        return True
    active = _active(placement)
    return Decimal(active[2][2]) == 1


def _tube_range(ir: dict, placement: dict) -> tuple:
    solid = _template(ir, placement)["solid"]
    z = exact(placement["centre_mm"][2])
    half = exact(solid["dz_mm"])
    return exact(solid["rmin_mm"]), exact(solid["rmax_mm"]), subtract(z, half), add(z, half), solid


def _coaxial(ir: dict, first: dict, second: dict) -> Decimal | None:
    """The gap of two tubes on one axis, by cylindrical coordinates (Section 7.3); None when they are not on one axis about their own axes."""
    if not (_curved(ir, first) and _curved(ir, second) and _about_own_axis(first) and _about_own_axis(second)):
        return None
    if any(exact(a) != exact(b) for a, b in zip(first["centre_mm"][:2], second["centre_mm"][:2])):
        return None
    r1, R1, z1, Z1, _ = _tube_range(ir, first)
    r2, R2, z2, Z2, _ = _tube_range(ir, second)
    return max(subtract(r2, R1), subtract(r1, R2), subtract(z2, Z1), subtract(z1, Z2))


UNJUDGED = Decimal(-2)  # a curved shape off its own axis too close to prove clear: rejected, not called an overlap


def _rotated_pair(ir: dict, first: dict, second: dict) -> Decimal:
    """Negative when the interiors overlap, otherwise the true minimum distance."""
    axial = _coaxial(ir, first, second)
    if axial is not None:
        return axial
    a, b = _polyhedron(ir, first), _polyhedron(ir, second)
    if not convex.disjoint(a, b):
        return UNJUDGED if _curved(ir, first) or _curved(ir, second) else Decimal(-1)
    gap = convex.distance(a, b)
    if (_curved(ir, first) or _curved(ir, second)) and gap < MINIMUM_GAP_MM:
        return UNJUDGED
    return gap


def _plain(ir: dict, placement: dict) -> bool:
    return _template(ir, placement)["shape"] == "box" and not _arbitrary(placement)


def _half(ir: dict, name: str) -> tuple:
    return tuple(exact(text) for text in ir["physical"]["templates"][name]["half_mm"])


def _extent(ir: dict, placement: dict) -> tuple:
    """Lower and upper corner of a placed box in its mother's frame."""
    half = _half(ir, placement["template"])
    if placement["rotation"] and (_arbitrary(placement) or _template(ir, placement)["shape"] != "box"):
        vertices = _polyhedron(ir, placement).vertices
        return (tuple(min(v[i] for v in vertices) for i in range(3)), tuple(max(v[i] for v in vertices) for i in range(3)))
    if placement["rotation"]:
        active = _active(placement)
        half = tuple(add(add(multiply(abs(Decimal(row[0])), half[0]), multiply(abs(Decimal(row[1])), half[1])), multiply(abs(Decimal(row[2])), half[2])) for row in active)
    centre = tuple(exact(text) for text in placement["centre_mm"])
    return (tuple(subtract(c, h) for c, h in zip(centre, half)), tuple(add(c, h) for c, h in zip(centre, half)))


def _face_gap(distance: Decimal) -> str | None:
    """None when a distance between faces is legal: they coincide within epsilon, or are at least c apart."""
    if abs(distance) < EPSILON_MM or distance >= MINIMUM_GAP_MM:
        return None
    return "outside" if distance < 0 else "too-close"


def _mother_body(ir: dict, name: str) -> convex.Polyhedron:
    template = ir["physical"]["templates"][name]
    if template["shape"] == "trd":
        return convex.trd(template["solid"])
    return convex.prism(template["solid"]["sides"], exact(template["solid"]["circumradius_mm"]), exact(template["solid"]["dz_mm"]))


def _gaps_in_tube(ir: dict, placement: dict) -> list:
    """Distances from a daughter to the surfaces of a tube mother, in cylindrical coordinates."""
    solid = ir["physical"]["templates"][placement["mother"]]["solid"]
    if exact(solid["phi_span_deg"]) != 360:
        return [None]
    rmin, rmax, half = exact(solid["rmin_mm"]), exact(solid["rmax_mm"]), exact(solid["dz_mm"])
    if _curved(ir, placement) and _about_own_axis(placement) and all(exact(value) == 0 for value in placement["centre_mm"][:2]):
        inner, outer, low, high, _ = _tube_range(ir, placement)
        return [subtract(rmax, outer), subtract(low, CONTEXT.minus(half)), subtract(half, high)] + ([subtract(inner, rmin)] if rmin > 0 else [])
    body = _polyhedron(ir, placement)
    reach = max(CONTEXT.sqrt(add(multiply(v[0], v[0]), multiply(v[1], v[1]))) for v in body.vertices)
    zs = [v[2] for v in body.vertices]
    gaps = [subtract(rmax, reach), subtract(min(zs), CONTEXT.minus(half)), subtract(half, max(zs))]
    return gaps + ([subtract(convex.nearest_to_axis(body), rmin)] if rmin > 0 else [])


def _gaps(ir: dict, placement: dict) -> list:
    """The distance from a daughter to each surface of its mother: negative outside, None when it cannot be judged."""
    shape = ir["physical"]["templates"][placement["mother"]]["shape"]
    if shape == "tube":
        return _gaps_in_tube(ir, placement)
    if shape != "box":
        return convex.face_gaps(_mother_body(ir, placement["mother"]), _polyhedron(ir, placement).vertices)
    low, high = _extent(ir, placement)
    half = _half(ir, placement["mother"])
    return [gap for axis in range(3) for gap in (subtract(low[axis], CONTEXT.minus(half[axis])), subtract(half[axis], high[axis]))]


def containment(ir: dict) -> list[dict]:
    out = []
    for placement in ir["physical"]["placements"]:
        where = f"{placement['mother']}/{placement['template']}[{placement['copy_number']}]"
        for gap in _gaps(ir, placement):
            if gap is None:
                out.append(_finding("containment-unjudged", where, "a daughter of a tube with a phi section cannot be judged yet"))
                continue
            problem = _face_gap(gap)
            if problem:
                out.append(_finding(f"containment-{problem}", where, f"a face lies {gap} mm from its mother's face"))
    return out


def _separation(a: tuple, b: tuple) -> Decimal:
    """The largest gap along an axis: negative when the interiors overlap."""
    return max(max(subtract(b[0][i], a[1][i]), subtract(a[0][i], b[1][i])) for i in range(3))


def siblings(ir: dict) -> list[dict]:
    by_mother: dict[str, list] = {}
    for placement in ir["physical"]["placements"]:
        by_mother.setdefault(placement["mother"], []).append((_extent(ir, placement), placement))
    out = []
    for mother, placed in by_mother.items():
        placed.sort(key=lambda item: item[0][0][0])
        for at, (a, first) in enumerate(placed):
            for later in range(at + 1, len(placed)):  # by index: a slice would copy the rest for every placement
                b, second = placed[later]
                if subtract(b[0][0], a[1][0]) >= MINIMUM_GAP_MM:
                    break
                separation = _separation(a, b) if _plain(ir, first) and _plain(ir, second) else _rotated_pair(ir, first, second)
                if abs(separation) < EPSILON_MM or separation >= MINIMUM_GAP_MM:
                    continue
                code = "sibling-unjudged" if separation == UNJUDGED else "sibling-overlap" if separation < 0 else "sibling-too-close"
                out.append(_finding(code, f"{mother}/{first['template']}[{first['copy_number']}]",
                                    f"{second['template']}[{second['copy_number']}] is {separation} mm away"))
    return out


def minimum_feature(ir: dict) -> list[dict]:
    return [_finding("minimum-feature", name, f"a half length of {half} mm is below the minimum feature")
            for name, template in ir["physical"]["templates"].items() for half in template["half_mm"]
            if add(exact(half), exact(half)) < MINIMUM_FEATURE_MM]


def _chains(ir: dict) -> dict:
    """Each logical's (largest coordinate, deepest level). Coordinates add up axis by axis; below a rotated placement the axes
    no longer line up, so from there each level adds its largest component to every axis, which stays an upper bound."""
    templates = ir["physical"]["templates"]
    daughters: dict[str, list] = {}
    for placement in ir["physical"]["placements"]:
        daughters.setdefault(placement["mother"], []).append(placement)
    reach: dict[str, tuple] = {WORLD: ((Decimal(0),) * 3, 0, False, 0)}
    pending = [WORLD]
    while pending:
        mother = pending.pop()
        centre, depth, turned, arbitrary = reach[mother]
        for placement in daughters.get(mother, []):
            local = tuple(abs(exact(text)) for text in placement["centre_mm"])
            if turned:
                local = (max(local),) * 3
            sums = tuple(add(a, b) for a, b in zip(centre, local))
            name = placement["template"]
            known = reach.get(name, ((Decimal(0),) * 3, 0, False, 0))
            merged = (tuple(max(a, b) for a, b in zip(known[0], sums)), max(known[1], depth + 1),
                      known[2] or turned or placement["rotation"] is not None, max(known[3], arbitrary + _arbitrary(placement)))
            if merged != reach.get(name):
                reach[name] = merged
                pending.append(name)
    out = {}
    for name, (centre, depth, _, arbitrary) in reach.items():
        half = max(exact(text) for text in templates[name]["half_mm"])
        out[name] = (max(add(value, half) for value in centre), depth, arbitrary)
    return out


def chain_reach(ir: dict) -> dict:
    """X of each logical's chain, in mm."""
    return {name: value[0] for name, value in _chains(ir).items()}


def error_bounds(ir: dict) -> list[dict]:
    """The bound of every logical's chain: a level with an arbitrary rotation counts k = 10, any other k = 1."""
    out = []
    for name, (largest, depth, arbitrary) in _chains(ir).items():
        value = bound.error_bound(largest, [True] * arbitrary + [False] * (depth - arbitrary))
        if value > Fraction(BOUND_LIMIT_MM):
            out.append(_finding("error-bound", name, f"B = {float(value):.3e} mm at X = {largest} mm, depth {depth}: rearrange "
                                                     "it in a local coordinate frame"))
    return out


def findings(ir: dict) -> list[dict]:
    return containment(ir) + siblings(ir) + minimum_feature(ir) + error_bounds(ir)
