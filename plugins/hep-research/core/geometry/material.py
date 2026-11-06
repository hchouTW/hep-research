"""Material budget (Section 15.1): the path of a straight ray through the placement tree, computed analytically on the IR.

S1 has boxes and rotations by multiples of 90 degrees, so a ray meets each box in one interval. Intervals are half open, so a
ray along a shared face counts one of the two volumes, never both.
"""
from __future__ import annotations

from decimal import Decimal

from core.geometry import convex
from core.geometry.numbers import CONTEXT, GeometryError, add, divide, exact, multiply, subtract
from core.geometry.rotation import rotate

WORLD = "world"


def _unit(direction: tuple) -> tuple:
    length = CONTEXT.sqrt(sum((multiply(value, value) for value in direction), Decimal(0)))
    if length == 0:
        raise GeometryError("ray-direction", "a ray has a direction")
    return tuple(divide(value, length) for value in direction)


def _interval(origin: tuple, direction: tuple, half: tuple):
    """The stretch of the ray inside a box centred on the origin, or None."""
    enter, leave = None, None
    for axis in range(3):
        if direction[axis] == 0:
            if not -half[axis] <= origin[axis] < half[axis]:
                return None
            continue
        ends = sorted(divide(subtract(side, origin[axis]), direction[axis]) for side in (-half[axis], half[axis]))
        enter = ends[0] if enter is None else max(enter, ends[0])
        leave = ends[1] if leave is None else min(leave, ends[1])
    if enter is None or leave is None:
        return None
    return (enter, leave) if enter < leave else None


def _dot(a: tuple, b: tuple) -> Decimal:
    return add(add(multiply(a[0], b[0]), multiply(a[1], b[1])), multiply(a[2], b[2]))


def _in_convex(origin: tuple, heading: tuple, body) -> list:
    """The stretch of a ray inside a convex polyhedron: the planes clip it one by one."""
    enter, leave = None, None
    for unit, anchor in convex.planes(body):
        rate = _dot(unit, heading)
        height = _dot(unit, tuple(subtract(a, b) for a, b in zip(anchor, origin)))
        if rate == 0:
            if height < 0:
                return []
            continue
        at = divide(height, rate)
        if rate > 0:
            leave = at if leave is None else min(leave, at)
        else:
            enter = at if enter is None else max(enter, at)
    return [(enter, leave)] if enter is not None and leave is not None and enter < leave else []


def _circle(origin: tuple, heading: tuple, radius: Decimal):
    """Where a ray crosses a cylinder about z, or None."""
    a = add(multiply(heading[0], heading[0]), multiply(heading[1], heading[1]))
    if a == 0:
        return None
    b = add(multiply(origin[0], heading[0]), multiply(origin[1], heading[1]))
    c = subtract(add(multiply(origin[0], origin[0]), multiply(origin[1], origin[1])), multiply(radius, radius))
    disc = subtract(multiply(b, b), multiply(a, c))
    if disc <= 0:
        return None
    root = CONTEXT.sqrt(disc)
    return divide(subtract(CONTEXT.minus(b), root), a), divide(add(CONTEXT.minus(b), root), a)


def _in_tube(origin: tuple, heading: tuple, solid: dict) -> list:
    if exact(solid["phi_span_deg"]) != 360:
        raise GeometryError("ray-shape", "a ray through a tube with a phi section is not computed yet")
    half, rmin, rmax = exact(solid["dz_mm"]), exact(solid["rmin_mm"]), exact(solid["rmax_mm"])
    span = _interval((Decimal(0), Decimal(0), origin[2]), (Decimal(0), Decimal(0), heading[2]), (Decimal(1), Decimal(1), half))
    outer = _circle(origin, heading, rmax)
    if heading[0] == 0 and heading[1] == 0:  # along the axis: inside or outside for its whole length
        r2 = add(multiply(origin[0], origin[0]), multiply(origin[1], origin[1]))
        return [span] if span and multiply(rmin, rmin) <= r2 < multiply(rmax, rmax) else []
    if outer is None:
        return []
    low, high = outer
    if heading[2] != 0:
        if span is None:
            return []
        low, high = max(low, span[0]), min(high, span[1])
    elif abs(origin[2]) >= half:
        return []
    if low >= high:
        return []
    inner = _circle(origin, heading, rmin) if rmin > 0 else None
    if inner is None:
        return [(low, high)]
    parts = [(low, min(high, inner[0])), (max(low, inner[1]), high)]
    return [part for part in parts if part[0] < part[1]]


class _Tree:
    def __init__(self, ir: dict):
        self.templates = ir["physical"]["templates"]
        self.daughters: dict[str, list] = {}
        for placement in ir["physical"]["placements"]:
            self.daughters.setdefault(placement["mother"], []).append(placement)

    def half(self, name: str) -> tuple:
        return tuple(exact(text) for text in self.templates[name]["half_mm"])

    def stretches(self, name: str, origin: tuple, heading: tuple) -> list:
        """The stretches of a ray inside a template, in its own frame: a tube with a hole can give two."""
        template = self.templates[name]
        shape = template["shape"]
        if shape == "box":
            found = _interval(origin, heading, self.half(name))
            return [found] if found else []
        if shape == "tube":
            return _in_tube(origin, heading, template["solid"])
        solid = template["solid"]
        body = convex.trd(solid) if shape == "trd" else convex.prism(solid["sides"], exact(solid["circumradius_mm"]), exact(solid["dz_mm"]))
        return _in_convex(origin, heading, body)

    def walk(self, name: str, origin: tuple, direction: tuple, start: Decimal, stop: Decimal, out: list) -> None:
        met = []
        for placement in self.daughters.get(name, []):
            centre = tuple(exact(text) for text in placement["centre_mm"])
            local = tuple(subtract(a, b) for a, b in zip(origin, centre))
            heading = direction
            if placement["rotation"]:
                local, heading = rotate(placement["rotation"], local), rotate(placement["rotation"], direction)
            for stretch in self.stretches(placement["template"], local, heading):
                if stretch[0] < stop and stretch[1] > start:
                    met.append((max(stretch[0], start), min(stretch[1], stop), placement["template"], local, heading))
        cursor = start
        for enter, leave, template, local, heading in sorted(met, key=lambda item: item[0]):
            self.add(name, cursor, enter, out)
            self.walk(template, local, heading, enter, leave, out)
            cursor = leave
        self.add(name, cursor, stop, out)

    def add(self, name: str, start: Decimal, stop: Decimal, out: list) -> None:
        if stop > start:
            out.append({"template": name, "material": self.templates[name]["material"], "length_mm": subtract(stop, start)})


def ray_segments(ir: dict, origin: tuple, direction: tuple) -> list[dict]:
    """The volumes a ray from origin crosses inside the world, in order, each with its length in mm."""
    tree = _Tree(ir)
    heading = _unit(direction)
    stretch = _interval(origin, heading, tree.half(WORLD))
    if stretch is None or stretch[1] <= 0:
        return []
    out: list[dict] = []
    tree.walk(WORLD, origin, heading, max(stretch[0], Decimal(0)), stretch[1], out)
    return out


def path_by_material(ir: dict, origin: tuple, direction: tuple) -> dict:
    """Length in mm through each material along a ray."""
    totals: dict[str, Decimal] = {}
    for segment in ray_segments(ir, origin, direction):
        totals[segment["material"]] = add(totals.get(segment["material"], Decimal(0)), segment["length_mm"])
    return totals


def budget(ir: dict, origin: tuple, direction: tuple, radiation_length_mm: dict) -> Decimal:
    """x / X0 along a ray; radiation_length_mm gives X0 of every material met."""
    total = Decimal(0)
    for name, length in path_by_material(ir, origin, direction).items():
        if name not in radiation_length_mm:
            raise GeometryError("material-unknown", f"no radiation length for {name!r}")
        total = add(total, divide(length, radiation_length_mm[name]))
    return total
