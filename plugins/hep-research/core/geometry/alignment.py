"""Alignment overlay layers (g4sim plan, Section 17, S9): conditions that change the geometry, layered on a detector-spec.

An alignment-overlay/1 lists placements of the expanded IR by (mother, template, copy_number), each with a shift of its centre in the
mother's frame (delta_mm) and optionally a small rotation (zyx_deg, active, about the placement's centre, applied after its own rotation).
Applying it changes those placements' centre_mm and rotation in exact decimal arithmetic, then records the overlay in the IR's optional
`alignment` field (its canonical SHA-256 and the placements it moved), so an applied overlay always yields a new geometry_id, even one
whose shifts are all zero (Section 17). The gap rule and the error bound (GB10) then run on the moved placements as on any other.
An IR placement belongs to a logical: shifting (M, T, c) moves that daughter in every touchable of M. A touchable of its own needs a
logical of its own in the specification.

`diff` lists the placements in which two IRs differ (centre or rotation), those only one of them holds, and the placements each IR's
overlay names (a shift of zero moves nothing but is recorded): the diff tool of S9 gate 2.
"""
from __future__ import annotations

from decimal import Decimal

from core.canonical import canonical_sha256
from core.geometry import rotation
from core.geometry.numbers import GeometryError, add, as_text, exact

SCHEMA = "alignment-overlay/1"


def _key(placement: dict) -> tuple:
    return placement["mother"], placement["template"], placement["copy_number"]


def _active(placement: dict):
    rows = placement["rotation"]
    if rows is None:
        return rotation.IDENTITY
    return rotation.transpose(tuple(tuple(value if isinstance(value, int) else exact(value) for value in row) for row in rows))


def _stored(active):
    """The IR's form of a rotation, as expand.py writes it: None for the identity, else the passive matrix of integers and decimal strings."""
    if active == rotation.IDENTITY:
        return None
    return [[value if isinstance(value, int) else as_text(value) for value in row] for row in rotation.passive_matrix(active)]


def check_overlay(overlay: dict) -> None:
    if overlay.get("schema") != SCHEMA:
        raise GeometryError("overlay-schema", f"{overlay.get('schema')!r} is not {SCHEMA}")
    seen = set()
    for at, shift in enumerate(overlay.get("shifts", [])):
        where = f"/shifts/{at}"
        key = (shift.get("mother"), shift.get("template"), shift.get("copy_number"))
        if key in seen:
            raise GeometryError("overlay-twice", f"placement {key} is shifted twice", where)
        seen.add(key)
        if len(shift.get("delta_mm", [])) != 3:
            raise GeometryError("overlay-shift", "delta_mm has three components", where)


def apply(ir: dict, overlay: dict) -> dict:
    """The IR with the overlay applied. Refuses a shift whose placement the IR does not hold (Section 15.1, S9)."""
    check_overlay(overlay)
    physical = ir["physical"]
    if "alignment" in physical:
        raise GeometryError("overlay-again", "the IR already carries an overlay: apply one overlay to the specification's own IR")
    index: dict = {}
    for at, placement in enumerate(physical["placements"]):
        index.setdefault(_key(placement), []).append(at)
    placements = [dict(item) for item in physical["placements"]]
    moved = []
    for at, shift in enumerate(overlay.get("shifts", [])):
        where = f"/shifts/{at}"
        key = (shift["mother"], shift["template"], shift["copy_number"])
        found = index.get(key, [])
        if not found:
            raise GeometryError("overlay-placement", f"the IR places no {key[1]} with copy number {key[2]} in {key[0]}", where)
        if len(found) > 1:
            raise GeometryError("overlay-ambiguous", f"{len(found)} placements of {key[1]} in {key[0]} share copy number {key[2]}", where)
        placement = placements[found[0]]
        delta = [exact(value) for value in shift["delta_mm"]]
        placement["centre_mm"] = [as_text(add(exact(value), step)) for value, step in zip(placement["centre_mm"], delta)]
        if shift.get("rotation"):
            turn = rotation.active_matrix({"zyx_deg": [Decimal(value) for value in shift["rotation"]["zyx_deg"]]}, f"{where}/rotation")
            placement["rotation"] = _stored(rotation.product(turn, _active(placement)))
        moved.append(list(key))
    out = {**ir, "physical": {**physical, "placements": placements,
                              "alignment": {"overlay_sha256": canonical_sha256(overlay), "placements": sorted(moved)}}}
    if overlay.get("source_of_facts"):
        out["marker"] = {**ir["marker"], "source_of_facts": {**ir["marker"]["source_of_facts"], "alignment": overlay["source_of_facts"]}}
    return out


def diff(first: dict, second: dict) -> dict:
    """{moved, only_first, only_second}: placement keys, sorted, whose centre or rotation differ, or which one IR alone holds."""
    def table(ir):
        return {_key(item): (item["centre_mm"], item["rotation"]) for item in ir["physical"]["placements"]}
    a, b = table(first), table(second)
    recorded = [ir["physical"].get("alignment", {}).get("placements", []) for ir in (first, second)]
    return {"moved": sorted(list(key) for key in a.keys() & b.keys() if a[key] != b[key]),
            "only_first": sorted(list(key) for key in a.keys() - b.keys()), "only_second": sorted(list(key) for key in b.keys() - a.keys()),
            "overlaid": {"first": recorded[0], "second": recorded[1]}}  # what each IR's overlay named, a shift of zero included
