"""Computation of the gap rule, containment, minimum feature and the error bound on the IR (Section 7.3). S1 has boxes and
rotations by multiples of 90 degrees, so every placed volume is an axis-aligned box in its mother and the arithmetic is exact.

Returns findings; contracts/geometry.py judges them. Checks run per logical, so the cost follows the number of placements in
a mother, never the number of touchables (Section 16).
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from core.geometry import bound
from core.geometry.numbers import BOUND_LIMIT_MM, EPSILON_MM, MINIMUM_FEATURE_MM, MINIMUM_GAP_MM, add, exact, subtract
from core.geometry.rotation import rotate, transpose

WORLD = "world"


def _finding(code: str, where: str, message: str) -> dict:
    return {"code": code, "path": where, "message": message}


def _half(ir: dict, name: str) -> tuple:
    return tuple(exact(text) for text in ir["physical"]["templates"][name]["half_mm"])


def _extent(ir: dict, placement: dict) -> tuple:
    """Lower and upper corner of a placed box in its mother's frame."""
    half = _half(ir, placement["template"])
    if placement["rotation"]:
        half = tuple(abs(value) for value in rotate(transpose(placement["rotation"]), half))  # the IR holds the passive matrix
    centre = tuple(exact(text) for text in placement["centre_mm"])
    return (tuple(subtract(c, h) for c, h in zip(centre, half)), tuple(add(c, h) for c, h in zip(centre, half)))


def _face_gap(distance: Decimal) -> str | None:
    """None when a distance between faces is legal: they coincide within epsilon, or are at least c apart."""
    if abs(distance) < EPSILON_MM or distance >= MINIMUM_GAP_MM:
        return None
    return "outside" if distance < 0 else "too-close"


def containment(ir: dict) -> list[dict]:
    out = []
    for placement in ir["physical"]["placements"]:
        low, high = _extent(ir, placement)
        half = _half(ir, placement["mother"])
        for axis in range(3):
            for gap in (subtract(low[axis], -half[axis]), subtract(half[axis], high[axis])):
                problem = _face_gap(gap)
                if problem:
                    out.append(_finding(f"containment-{problem}", f"{placement['mother']}/{placement['template']}"
                                                                  f"[{placement['copy_number']}]",
                                        f"a face lies {gap} mm from its mother's face"))
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
                separation = _separation(a, b)
                if abs(separation) < EPSILON_MM or separation >= MINIMUM_GAP_MM:
                    continue
                code = "sibling-overlap" if separation < 0 else "sibling-too-close"
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
    reach = {WORLD: ((Decimal(0),) * 3, 0, False)}
    pending = [WORLD]
    while pending:
        mother = pending.pop()
        centre, depth, turned = reach[mother]
        for placement in daughters.get(mother, []):
            local = tuple(abs(exact(text)) for text in placement["centre_mm"])
            if turned:
                local = (max(local),) * 3
            sums = tuple(add(a, b) for a, b in zip(centre, local))
            name = placement["template"]
            known = reach.get(name, ((Decimal(0),) * 3, 0, False))
            merged = (tuple(max(a, b) for a, b in zip(known[0], sums)), max(known[1], depth + 1),
                      known[2] or turned or placement["rotation"] is not None)
            if merged != reach.get(name):
                reach[name] = merged
                pending.append(name)
    out = {}
    for name, (centre, depth, _) in reach.items():
        half = max(exact(text) for text in templates[name]["half_mm"])
        out[name] = (max(add(value, half) for value in centre), depth)
    return out


def chain_reach(ir: dict) -> dict:
    """X of each logical's chain, in mm."""
    return {name: value[0] for name, value in _chains(ir).items()}


def error_bounds(ir: dict) -> list[dict]:
    """The bound of every logical's chain; S1 has no arbitrary rotation, so every level counts k = 1."""
    out = []
    for name, (largest, depth) in _chains(ir).items():
        value = bound.error_bound(largest, [False] * depth)
        if value > Fraction(BOUND_LIMIT_MM):
            out.append(_finding("error-bound", name, f"B = {float(value):.3e} mm at X = {largest} mm, depth {depth}: rearrange "
                                                     "it in a local coordinate frame"))
    return out


def findings(ir: dict) -> list[dict]:
    return containment(ir) + siblings(ir) + minimum_feature(ir) + error_bounds(ir)
