"""Material budget (Section 15.1): the path of a straight ray through the placement tree, computed analytically on the IR.

S1 has boxes and rotations by multiples of 90 degrees, so a ray meets each box in one interval. Intervals are half open, so a
ray along a shared face counts one of the two volumes, never both.
"""
from __future__ import annotations

from decimal import Decimal

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


class _Tree:
    def __init__(self, ir: dict):
        self.templates = ir["physical"]["templates"]
        self.daughters: dict[str, list] = {}
        for placement in ir["physical"]["placements"]:
            self.daughters.setdefault(placement["mother"], []).append(placement)

    def half(self, name: str) -> tuple:
        return tuple(exact(text) for text in self.templates[name]["half_mm"])

    def walk(self, name: str, origin: tuple, direction: tuple, start: Decimal, stop: Decimal, out: list) -> None:
        met = []
        for placement in self.daughters.get(name, []):
            centre = tuple(exact(text) for text in placement["centre_mm"])
            local = tuple(subtract(a, b) for a, b in zip(origin, centre))
            heading = direction
            if placement["rotation"]:
                local, heading = rotate(placement["rotation"], local), rotate(placement["rotation"], direction)
            stretch = _interval(local, heading, self.half(placement["template"]))
            if stretch and stretch[0] < stop and stretch[1] > start:
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
