"""GDML export of the IR (decision M9): pure Python. GDML is derived from the IR and never read back into it.

Geant4's reader builds a rotation as Rz(z) Ry(y) Rx(x) and places the volume with its inverse as the object rotation, so that
product equals the passive matrix the IR holds. A live read with G4GDMLParser confirmed this (S1 task card).
"""
from __future__ import annotations

from decimal import Decimal

from xml.sax.saxutils import quoteattr

from core.geometry import rotation as rotations
from core.geometry.numbers import CONTEXT, GeometryError, add, exact, multiply

_ANGLES = (0, 90, 180, 270)
_ELEMENT_PREFIX = "G4_"


def _general_angles(passive) -> tuple:
    """Rz(z) Ry(y) Rx(x) read off an arbitrary passive matrix."""
    m = [[Decimal(value) for value in row] for row in passive]
    y = rotations.atan2_deg(CONTEXT.minus(m[2][0]), CONTEXT.sqrt(add(multiply(m[0][0], m[0][0]), multiply(m[1][0], m[1][0]))))
    if abs(m[0][0]) < Decimal("1e-30") and abs(m[1][0]) < Decimal("1e-30"):  # gimbal lock: z is free
        return rotations.atan2_deg(CONTEXT.minus(m[1][2]), m[1][1]), y, Decimal(0)
    return rotations.atan2_deg(m[2][1], m[2][2]), y, rotations.atan2_deg(m[1][0], m[0][0])


def euler_angles(passive) -> tuple:
    """Angles (x, y, z) in degrees with Rz(z) Ry(y) Rx(x) equal to a passive matrix."""
    if any(isinstance(value, str) for row in passive for value in row):
        return _general_angles(passive)
    wanted = tuple(tuple(row) for row in passive)
    for x in _ANGLES:
        for y in _ANGLES:
            for z in _ANGLES:
                turns = (Decimal(x), Decimal(y), Decimal(z))
                built = rotations.product(rotations.product(rotations._about("z", turns[2]), rotations._about("y", turns[1])),
                                          rotations._about("x", turns[0]))
                if built == wanted:
                    return x, y, z
    raise GeometryError("rotation-form", f"{passive} is not a rotation by multiples of 90 degrees")


def _attr(name: str, value) -> str:
    return f"{name}={quoteattr(str(value))}"


def _materials(physical: dict) -> tuple:
    lines, refs = [], {}
    for name, material in physical["materials"].items():
        if "base" in material:
            refs[name] = material["base"]
            continue
        lines.append(f"    <material {_attr('name', name)}>")
        lines.append(f"      <D {_attr('value', material['density_g_cm3'])} unit=\"g/cm3\"/>")
        for element, fraction in material["composition"].items():
            lines.append(f"      <fraction {_attr('n', fraction)} {_attr('ref', _ELEMENT_PREFIX + element)}/>")
        lines.append("    </material>")
        refs[name] = name
    return lines, refs


def _physvol(placement: dict, serial: int) -> list[str]:
    x, y, z = placement["centre_mm"]
    lines = [f"      <physvol {_attr('name', placement['template'] + '_' + str(placement['copy_number']))} "
             f"{_attr('copynumber', placement['copy_number'])}>",
             f"        <volumeref {_attr('ref', placement['template'])}/>",
             f"        <position {_attr('name', 'position_' + str(serial))} {_attr('x', x)} {_attr('y', y)} {_attr('z', z)} unit=\"mm\"/>"]
    if placement["rotation"]:
        ax, ay, az = euler_angles(placement["rotation"])
        lines.append(f"        <rotation {_attr('name', 'rotation_' + str(serial))} {_attr('x', ax)} {_attr('y', ay)} {_attr('z', az)} "
                     "unit=\"deg\"/>")
    return [*lines, "      </physvol>"]


def _twice(text: str) -> Decimal:
    return add(exact(text), exact(text))


def _solid(name: str, template: dict) -> list[str]:
    label, solid = _attr("name", name + "_solid"), template.get("solid")
    if template["shape"] == "trd":
        sizes = " ".join(_attr(key, _twice(solid[source])) for key, source in (("x1", "dx1_mm"), ("x2", "dx2_mm"), ("y1", "dy1_mm"), ("y2", "dy2_mm"), ("z", "dz_mm")))
        return [f"    <trd {label} {sizes} lunit=\"mm\"/>"]
    if template["shape"] == "tube":
        return [f"    <tube {label} {_attr('rmin', solid['rmin_mm'])} {_attr('rmax', solid['rmax_mm'])} {_attr('z', _twice(solid['dz_mm']))} "
                f"{_attr('startphi', solid['phi_start_deg'])} {_attr('deltaphi', solid['phi_span_deg'])} aunit=\"deg\" lunit=\"mm\"/>"]
    if template["shape"] == "polygon_prism":  # G4Polyhedra's rmax is the apothem (GB23)
        planes = [f"      <zplane {_attr('rmin', 0)} {_attr('rmax', solid['apothem_mm'])} {_attr('z', z)}/>" for z in (CONTEXT.minus(exact(solid["dz_mm"])), exact(solid["dz_mm"]))]
        return [f"    <polyhedra {label} {_attr('numsides', solid['sides'])} {_attr('startphi', 0)} {_attr('deltaphi', 360)} aunit=\"deg\" lunit=\"mm\">", *planes, "    </polyhedra>"]
    x, y, z = (_twice(half) for half in template["half_mm"])
    return [f"    <box {label} {_attr('x', x)} {_attr('y', y)} {_attr('z', z)} lunit=\"mm\"/>"]


def export(ir: dict) -> str:
    """The GDML text of the IR; daughters are declared before their mothers, as GDML requires."""
    physical = ir["physical"]
    material_lines, refs = _materials(physical)
    solids, volumes = [], []
    placements = list(enumerate(physical["placements"]))
    for name, template in reversed(list(physical["templates"].items())):
        solids.extend(_solid(name, template))
        volumes.append(f"    <volume {_attr('name', name)}>")
        volumes.append(f"      <materialref {_attr('ref', refs.get(template['material'], template['material']))}/>")
        volumes.append(f"      <solidref {_attr('ref', name + '_solid')}/>")
        for serial, placement in placements:
            if placement["mother"] == name:
                volumes.extend(_physvol(placement, serial))
        volumes.append("    </volume>")
    return "\n".join(['<?xml version="1.0" encoding="UTF-8"?>', "<gdml>", "  <define/>", "  <materials>", *material_lines,
                      "  </materials>", "  <solids>", *solids, "  </solids>", "  <structure>", *volumes, "  </structure>",
                      '  <setup name="Default" version="1.0">', '    <world ref="world"/>', "  </setup>", "</gdml>", ""])
