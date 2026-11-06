"""GDML export of the IR (decision M9): pure Python. GDML is derived from the IR and never read back into it.

Geant4's reader builds a rotation as Rz(z) Ry(y) Rx(x) and places the volume with its inverse as the object rotation, so that
product equals the passive matrix the IR holds. A live read with G4GDMLParser confirmed this (S1 task card).
"""
from __future__ import annotations

from decimal import Decimal

from xml.sax.saxutils import quoteattr

from core.geometry import rotation as rotations
from core.geometry.numbers import GeometryError, add, exact

_ANGLES = (0, 90, 180, 270)
_ELEMENT_PREFIX = "G4_"


def euler_angles(passive) -> tuple:
    """Angles (x, y, z) in degrees with Rz(z) Ry(y) Rx(x) equal to a passive matrix of multiples of 90 degrees."""
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


def export(ir: dict) -> str:
    """The GDML text of the IR; daughters are declared before their mothers, as GDML requires."""
    physical = ir["physical"]
    material_lines, refs = _materials(physical)
    solids, volumes = [], []
    placements = list(enumerate(physical["placements"]))
    for name, template in reversed(list(physical["templates"].items())):
        x, y, z = (add(exact(half), exact(half)) for half in template["half_mm"])
        solids.append(f"    <box {_attr('name', name + '_solid')} {_attr('x', x)} {_attr('y', y)} {_attr('z', z)} lunit=\"mm\"/>")
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
