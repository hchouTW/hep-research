"""Optics in the specification (Sections 6.2.7 and 6.2.9, S7): property tables, gap volumes, optical_scope and optical surfaces.

G4OpticalPhysics is global and SetActiveVolume cannot restrict light production by volume (GB16, S3), so the scope is a rule on
the specification: only templates inside optical_scope may have a material with optical property tables, and an optical photon
that leaves the scope is killed by KillProcess. Materials are shared by name, so the two ways to write light inside the scope
are a separately named material (for example AIR_optical, based on G4_AIR) and a gap volume ({"spacer_mm": ..., "material": ...})."""
from __future__ import annotations

import copy
from decimal import Decimal

from core.geometry.numbers import GeometryError

SCOPE_NEED = "optical_scope"
HOW_TO_WRITE = ("materials are shared by name, so give the light-carrying use its own material (for example AIR_optical with base G4_AIR), "
                "and write a gap that needs optical properties as a gap volume: {\"spacer_mm\": ..., \"material\": ...}")
GAP_TAG = "gap"


def _number(text, path: str) -> Decimal:
    try:
        value = Decimal(str(text))
    except ArithmeticError as err:
        raise GeometryError("optical-table", f"{text!r} is not a number", path) from err
    if not value.is_finite():
        raise GeometryError("optical-table", f"{text!r} is not finite", path)
    return value


def _spectrum(table: dict, path: str, low=None, high=None) -> None:
    """Energies positive and rising, one value per energy, values within [low, high]."""
    energies = [_number(value, f"{path}/energy_eV") for value in table["energy_eV"]]
    values = [_number(value, f"{path}/value") for value in table["value"]]
    if len(energies) != len(values):
        raise GeometryError("optical-table", f"{len(energies)} energies for {len(values)} values", path)
    if energies[0] <= 0 or any(b <= a for a, b in zip(energies, energies[1:])):
        raise GeometryError("optical-table", f"the energies {energies} eV are not positive and rising", path)
    if any((low is not None and value < low) or (high is not None and value > high) for value in values):
        raise GeometryError("optical-table", f"a value lies outside [{low}, {high}]", path)


def check_material(name: str, material: dict) -> None:
    """The ranges a property table must keep; Geant4 itself accepts any number."""
    where = f"/materials/{name}"
    optical = material.get("optical")
    if optical:
        _spectrum(optical["rindex"], f"{where}/optical/rindex", low=Decimal(1))
        for key in ("absorption_length_mm", "rayleigh_length_mm"):
            if key in optical:
                _spectrum(optical[key], f"{where}/optical/{key}", low=Decimal(0))
        if "mie" in optical:
            mie = optical["mie"]
            _spectrum(mie["length_mm"], f"{where}/optical/mie/length_mm", low=Decimal(0))
            for key, low, high in (("forward_g", -1, 1), ("backward_g", -1, 1), ("forward_ratio", 0, 1)):
                if not low <= _number(mie[key], f"{where}/optical/mie/{key}") <= high:
                    raise GeometryError("optical-table", f"mie {key} lies outside [{low}, {high}]", f"{where}/optical/mie")
        if "wls" in optical:
            wls = optical["wls"]
            _spectrum(wls["absorption_length_mm"], f"{where}/optical/wls/absorption_length_mm", low=Decimal(0))
            _spectrum(wls["emission"], f"{where}/optical/wls/emission", low=Decimal(0))
            if _number(wls["time_constant_ns"], f"{where}/optical/wls") < 0:
                raise GeometryError("optical-table", "a negative WLS time constant", f"{where}/optical/wls")
    components = material.get("scintillation", {}).get("components")
    if components:
        if not optical:
            raise GeometryError("optical-table", "scintillation components emit optical photons, so the material needs optical.rindex", where)
        total = Decimal(0)
        for at, component in enumerate(components):
            path = f"{where}/scintillation/components/{at}"
            fraction = _number(component["fraction"], path)
            if not 0 < fraction <= 1 or _number(component["rise_ns"], path) < 0 or _number(component["decay_ns"], path) <= 0:
                raise GeometryError("optical-table", "a component needs 0 < fraction <= 1, rise >= 0 and decay > 0 ns", path)
            _spectrum(component["spectrum"], f"{path}/spectrum", low=Decimal(0))
            total += fraction
        if total != 1:
            raise GeometryError("optical-table", f"the component fractions add to {total}, not 1", f"{where}/scintillation/components")


def has_tables(material: dict | None) -> bool:
    """Whether Geant4 would give this material an optical property table."""
    return bool(material) and ("optical" in material or bool(material.get("scintillation", {}).get("components")))


def with_gap_volumes(spec: dict) -> dict:
    """Each {"spacer_mm": L, "material": m} of a stack becomes a gap template: the mother's cross-section, L thick along the stack's axis,
    of material m, tagged like its mother plus "gap", so a scope selected by tags holds it. Its name is <mother>_gap<position>."""
    holders = [*spec.get("templates", {}).items(), ("world", spec["world"])]
    if not any(isinstance(item, dict) and "material" in item for _, node in holders for child in node.get("children", [])
               for item in child.get("placement", {}).get("stack", {}).get("sequence", [])):
        return spec
    spec = copy.deepcopy(spec)
    axes = {"x": 0, "y": 1, "z": 2}
    for mother, node in [*spec.get("templates", {}).items(), ("world", spec["world"])]:
        for c, child in enumerate(node.get("children", [])):
            stack = child.get("placement", {}).get("stack")
            if not stack:
                continue
            for at, item in enumerate(stack["sequence"]):
                if not (isinstance(item, dict) and "material" in item):
                    continue
                where = f"/templates/{mother}/children/{c}/placement/stack/sequence/{at}"
                size = node.get("size_mm") if mother == "world" else node["solid"].get("box", {}).get("size_mm")
                if size is None:
                    raise GeometryError("gap-mother-shape", "a gap volume fills a box mother's cross-section", where)
                name = f"{mother}_gap{at}"
                if name in spec["templates"]:
                    raise GeometryError("template-name", f"{name!r} is taken; the gap volume needs it", where)
                axis = axes[stack["axis"]]
                gap_size = [item["spacer_mm"] if i == axis else size[i] for i in range(3)]
                spec["templates"][name] = {"solid": {"box": {"size_mm": gap_size}}, "material": item["material"],
                                           "tags": sorted({*node.get("tags", []), GAP_TAG})}
                stack["sequence"][at] = name
    return spec


def scope(requirements: list[dict]) -> set[str] | None:
    """The templates of every optical_scope requirement, or None when the specification declares none."""
    found = [requirement for requirement in requirements if requirement["need"] == SCOPE_NEED]
    return {name for requirement in found for name in requirement.get("templates", [])} if found else None


def scope_findings(spec: dict, templates: dict, requirements: list[dict], tree: dict, placed_once) -> None:
    """Section 15.1 (S7): no material with optical tables outside the scope; no bare spacer inside the scope whose mother's material has
    no tables (its photons would die there unseen); a surface only on templates inside the scope, a border's templates placed once."""
    materials = spec.get("materials", {})
    inside = scope(requirements) or set()
    for name, node in templates.items():
        if has_tables(materials.get(node["material"])) and name not in inside:
            raise GeometryError("optical-outside-scope", f"template {name!r} is outside optical_scope but its material {node['material']!r} has optical tables; {HOW_TO_WRITE}", f"/templates/{name}")
    nodes = {**spec.get("templates", {}), "world": spec["world"]}
    for mother in inside:
        for c, child in enumerate(nodes[mother].get("children", [])):
            for at, item in enumerate(child.get("placement", {}).get("stack", {}).get("sequence", [])):
                if isinstance(item, dict) and "spacer_mm" in item and not has_tables(materials.get(nodes[mother]["material"])):
                    raise GeometryError("optical-spacer", f"a spacer inside optical_scope is {nodes[mother]['material']!r}, which has no optical tables; {HOW_TO_WRITE}",
                                        f"/templates/{mother}/children/{c}/placement/stack/sequence/{at}")
    for name, surface in spec.get("optical_surfaces", {}).items():
        where = f"/optical_surfaces/{name}"
        named = [surface["skin"]] if "skin" in surface else list(surface["border"])
        for template in named:
            if template not in templates:
                raise GeometryError("template-unknown", f"{template!r} is not a placed template", where)
            if template not in inside:
                raise GeometryError("optical-surface-scope", f"template {template!r} is outside optical_scope", where)
        if "border" in surface:
            if not all(placed_once(template) for template in named):
                raise GeometryError("optical-surface-border", "a border surface lies between two templates each placed once in the tree", where)
            first, second = named
            touching = any(item["template"] == second for item in tree.get(first, [])) or any(item["template"] == first for item in tree.get(second, [])) \
                or any({first, second} <= {item["template"] for item in placed} for placed in tree.values())
            if not touching:
                raise GeometryError("optical-surface-border", f"{first!r} and {second!r} are neither mother and daughter nor siblings", where)
        for key, low, high in (("reflectivity", 0, 1), ("efficiency", 0, 1)):
            if key in surface:
                _spectrum(surface[key], f"{where}/{key}", low=Decimal(low), high=Decimal(high))
        if "sigma_alpha_deg" in surface and not 0 <= _number(surface["sigma_alpha_deg"], where) <= 90:
            raise GeometryError("optical-table", "sigma_alpha_deg lies outside [0, 90]", where)
