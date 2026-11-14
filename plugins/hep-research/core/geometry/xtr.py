"""Transition radiation in the specification (Section 6.2.9, S7): the XTR consistency rules check-spec applies to a radiator's envelope.

A transition_radiation requirement selects one envelope template and gives the radiator's structure ("regular" or "irregular") and its
physical parameters: foil and gas materials, foil thickness t, gap g, foil count n, the envelope axis the radiation runs along, and for an
irregular stack the Gamma parameters of foil and gap thicknesses. The Geant4 radiator class belongs to the run card (rule 6), whose
compatibility with the structure the adapter checks against xtr_radiators.json (rule 5).

Rules here: (1) no daughter inside the envelope; (2) the envelope material is the mixture of foil and gas in proportion to their volumes,
by density and mass fractions to MIXTURE_TOLERANCE (declared values are rounded text); (3) the envelope's thickness d along the axis keeps
n(t + g) - g <= d <= n(t + g); (6) no model kind in the specification. Foil and gas need declared densities: core holds no NIST table."""
from __future__ import annotations

from decimal import Decimal

from core.geometry.numbers import CONTEXT, GeometryError, as_text

NEED = "transition_radiation"
STRUCTURES = ("regular", "irregular")
MODEL_KEYS = ("model", "model_kind", "radiator_class")
MIXTURE_TOLERANCE = Decimal("1e-6")
UM = Decimal("0.001")


def _density(materials: dict, name: str, where: str) -> Decimal:
    declared = materials.get(name, {}).get("density_g_cm3")
    if declared is None:
        raise GeometryError("xtr-density", f"{name!r} needs a declared density_g_cm3 for the envelope's mixture (core holds no NIST table)", where)
    return Decimal(str(declared))


def mixture(materials: dict, foil: str, gas: str, foils: int, thickness_mm: Decimal, envelope_mm: Decimal, where: str) -> dict:
    """The envelope's equivalent mixture: density and mass fractions of foil and gas, by their volumes in the envelope."""
    foil_density, gas_density = _density(materials, foil, where), _density(materials, gas, where)
    foil_volume = CONTEXT.multiply(Decimal(foils), thickness_mm)
    gas_volume = CONTEXT.subtract(envelope_mm, foil_volume)
    foil_mass, gas_mass = CONTEXT.multiply(foil_volume, foil_density), CONTEXT.multiply(gas_volume, gas_density)
    total = CONTEXT.add(foil_mass, gas_mass)
    return {"density_g_cm3": CONTEXT.divide(total, envelope_mm), "fractions": {foil: CONTEXT.divide(foil_mass, total), gas: CONTEXT.divide(gas_mass, total)}}


def _close(declared, computed: Decimal) -> bool:
    value = Decimal(str(declared))
    return abs(value - computed) <= MIXTURE_TOLERANCE * abs(computed)


def check(spec: dict, templates: dict, requirements: list, tree: dict) -> None:
    """Rules 1, 2, 3 and 6 for every transition_radiation requirement of the expanded IR."""
    materials = spec.get("materials", {})
    for at, requirement in enumerate(requirements):
        if requirement.get("need") != NEED:
            continue
        where = f"/physics_requirements/{at}"
        model = [key for key in MODEL_KEYS if key in requirement]
        if model:
            raise GeometryError("xtr-model-in-spec", f"{model[0]} belongs to the run card's radiator class, not the specification (rule 6)", where)
        if requirement.get("structure") not in STRUCTURES:
            raise GeometryError("xtr-structure", f"structure {requirement.get('structure')!r} is not regular or irregular", where)
        missing = [key for key in ("foil_material", "gas_material", "foil_thickness_um", "gap_um", "foils", "axis") if key not in requirement]
        if requirement["structure"] == "irregular":
            missing += [key for key in ("alpha_foil", "alpha_gas") if key not in requirement]
        if missing:
            raise GeometryError("xtr-parameters", f"a {requirement['structure']} radiator needs {missing}", where)
        envelopes = requirement.get("templates", [])
        if len(envelopes) != 1:
            raise GeometryError("xtr-envelope", f"a radiator has one envelope template, not {envelopes}", where)
        envelope = envelopes[0]
        if tree.get(envelope):
            raise GeometryError("xtr-daughter", f"{len(tree[envelope])} volume(s) placed inside the envelope {envelope!r}; Geant4 builds the foils itself (rule 1)", where)
        node = templates[envelope]
        if node["shape"] != "box":
            raise GeometryError("xtr-envelope", f"the envelope {envelope!r} is a {node['shape']}; the thickness rule needs a box", where)
        foils = requirement["foils"]
        if isinstance(foils, bool) or not isinstance(foils, int) or foils < 1:
            raise GeometryError("xtr-parameters", f"foils {foils!r} is not a positive integer", where)
        t, g = CONTEXT.multiply(Decimal(str(requirement["foil_thickness_um"])), UM), CONTEXT.multiply(Decimal(str(requirement["gap_um"])), UM)
        if t <= 0 or g < 0:
            raise GeometryError("xtr-parameters", "the foil thickness must be positive and the gap not negative", where)
        axis = {"x": 0, "y": 1, "z": 2}.get(requirement["axis"])
        if axis is None:
            raise GeometryError("xtr-parameters", f"axis {requirement['axis']!r} is not x, y or z", where)
        d = CONTEXT.multiply(Decimal(node["half_mm"][axis]), Decimal(2))
        pitch = CONTEXT.multiply(Decimal(foils), CONTEXT.add(t, g))
        if not CONTEXT.subtract(pitch, g) <= d <= pitch:
            raise GeometryError("xtr-thickness", f"the envelope is {as_text(d)} mm along {requirement['axis']}; {foils} foils need "
                                f"{as_text(CONTEXT.subtract(pitch, g))} to {as_text(pitch)} mm (rule 3)", where)
        computed = mixture(materials, requirement["foil_material"], requirement["gas_material"], foils, t, d, where)
        declared = materials.get(node["material"], {})
        fractions = {item["material"]: item["mass_fraction"] for item in declared.get("components", [])}
        expected = ", ".join(f"{name} {as_text(value)}" for name, value in computed["fractions"].items())
        if set(fractions) != set(computed["fractions"]) or "density_g_cm3" not in declared or not _close(declared["density_g_cm3"], computed["density_g_cm3"]) \
                or not all(_close(fractions[name], value) for name, value in computed["fractions"].items()):
            raise GeometryError("xtr-mixture", f"the envelope material {node['material']!r} must be the foil-gas mixture: density "
                                f"{as_text(computed['density_g_cm3'])} g/cm3, mass fractions {expected} (rule 2)", where)
