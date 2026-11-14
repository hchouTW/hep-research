"""Re-evaluation of a product's objects under another gain payload, with the membership held fixed (plan R37, CAI-T08-1).

Data side: it reads a calo-cluster-product/1 event (as product.read_text or read_product return it) and gain payloads, never
truth. The cells of a kept component are retained in the product with their full chain (R34), so each member's energy under a
new gain follows from its retained value after the pedestal and the shared gain step of cell_chain:
E_new = (ADC - pedestal) c' when the gain multiplies, (ADC - pedestal) / g' when it divides.

Membership fixed means: the object's members and their sharing fractions f_kc, both read from the product, are held as they
are; only the gain payload changes. Then A_k,new = sum_c f_kc E_c,new over the object's members, and its change against the
energy the product recorded, A_k,new - A_k, is compared by the caller with R37's formula, which this module also forms from
the product's own E_c,old and the two payloads' gains: sum_c f_kc E_c,old (c'/c - 1) (multiply) or (g/g' - 1) (divide).
For a one-peak object f = 1 and this is the recipe's own energy rule (section 7.1: A = sum e_c over the component) on the same
cells. For a two-peak object the recipe's own path would re-derive the fractions from the new energies; holding them at the
product's values is the plan's "f_cell held fixed" by construction, and reshare() gives the recipe's own re-shared energies
on the same cells and peaks, whose change R37 has recorded without an exact assertion.

No cell-level step follows the gain in this chain (cell_chain), so no nonlinear step enters the expectation; the cell and
seed thresholds are clustering's membership rules, held fixed here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy

from .cell_chain import gain_step
from .cell_input import InputError, Payload
from .clustering import share_two_peaks
from .gain_payload import channel_map_identity


@dataclass(frozen=True)
class ObjectChange:
    object: int
    component: int
    kind: str
    members: int
    changed_members: int          # members whose gain differs between the two payloads
    lowest_changed: float | None  # min over changed members of min(E_old, E_new); None without a changed member
    energy_product: float         # A_k as the product recorded it
    energy_new: float             # sum_c f_kc E_c,new, fractions held fixed
    change: float                 # energy_new - energy_product
    formula: float                # sum_c f_kc E_c,old (ratio_c - 1), R37
    scale: float                  # max(sum f |E_old|, sum f |E_new|, 1 MeV), the tolerance's scale


def ratio_minus_one(operation: str, gain_old: float, gain_new: float) -> float:
    """c'/c - 1 when the gain multiplies, g/g' - 1 when it divides (R37)."""
    return gain_new / gain_old - 1.0 if operation == "multiply" else gain_old / gain_new - 1.0


def check_payloads(header: dict, old_gain: Payload, new_gain: Payload) -> None:
    """Refuses a pair of gain payloads that is not 'only the gain payload changed' for this product."""
    chain = header["chain"]
    if old_gain.identity != chain[1]["payload_id"]:
        raise InputError("old gain payload: the product did not consume it (its chain names another gain payload)")
    if new_gain.operation != old_gain.operation or new_gain.operation != chain[1]["operation"]:
        raise InputError("new gain payload: its role (multiply or divide) is not the one the product applied; the role is part "
                         "of the constant's definition")
    if new_gain.derived_against != (chain[0]["payload_id"],):
        raise InputError("new gain payload: derived against another pedestal payload than the product's chain applied")
    nx, ny = header["grid"]["nx"], header["grid"]["ny"]
    for name, gain in (("old gain payload", old_gain), ("new gain payload", new_gain)):
        if gain.channel_map is not None and gain.channel_map != channel_map_identity(nx, ny):
            raise InputError(f"{name}: made for another channel map than the product's {nx} x {ny} grid")
        if gain.values.size != nx * ny:
            raise InputError(f"{name}: covers {gain.values.size} channels, the product's grid has {nx * ny}")


def cell_energies(event: dict, header: dict, old_gain: Payload, new_gain: Payload) -> dict:
    """{channel: (E_old as the product recorded it, E_new from the retained value after the pedestal and the new gain)}."""
    operation = header["chain"][1]["operation"]
    out = {}
    for channel, _raw, _pedestal, after, gain, energy, _saturated, _component in event["cells"]:
        if gain != float(old_gain.values[channel]):
            raise InputError(f"event {event['event']}, channel {channel}: the product applied gain {gain!r}, not the gain payload's "
                             f"{float(old_gain.values[channel])!r}")
        out[channel] = (energy, float(gain_step(after, float(new_gain.values[channel]), operation)))
    return out


def fixed_membership(event: dict, header: dict, old_gain: Payload, new_gain: Payload) -> list:
    """One ObjectChange per object of the event, in object order; membership and fractions as the product holds them."""
    check_payloads(header, old_gain, new_gain)
    operation = header["chain"][1]["operation"]
    energies = cell_energies(event, header, old_gain, new_gain)
    out = []
    for k, cluster in enumerate(event["objects"]):
        new_terms, formula_terms, scale_old, scale_new = [], [], [], []
        changed, lowest = 0, None
        for channel, fraction in cluster["members"]:
            e_old, e_new = energies[channel]
            c_old, c_new = float(old_gain.values[channel]), float(new_gain.values[channel])
            new_terms.append(fraction * e_new)
            formula_terms.append(fraction * e_old * ratio_minus_one(operation, c_old, c_new))
            scale_old.append(fraction * abs(e_old))
            scale_new.append(fraction * abs(e_new))
            if c_new != c_old:
                changed += 1
                low = min(e_old, e_new)
                lowest = low if lowest is None else min(lowest, low)
        energy_new = math.fsum(new_terms)
        out.append(ObjectChange(object=k, component=cluster["component"], kind=cluster["kind"], members=len(cluster["members"]),
                                changed_members=changed, lowest_changed=lowest, energy_product=cluster["energy"], energy_new=energy_new,
                                change=energy_new - cluster["energy"], formula=math.fsum(formula_terms),
                                scale=max(math.fsum(scale_old), math.fsum(scale_new), 1.0)))
    return out


def reshare(event: dict, header: dict, old_gain: Payload, new_gain: Payload, cfg) -> dict:
    """{object: A_k} for each two-peak object: the recipe's own 30-iteration sharing (section 7.1) on the same component cells
    and the same kept peaks, from the new cell energies, so the fractions follow the new e_c. A component whose sharing is
    undefined under the new energies gives no entry."""
    check_payloads(header, old_gain, new_gain)
    energies = cell_energies(event, header, old_gain, new_gain)
    ny = header["grid"]["ny"]
    out = {}
    for comp in event["components"]:
        objects = [k for k, o in enumerate(event["objects"]) if o["component"] == comp["component"] and o["kind"] == "two-peak"]
        if len(objects) != 2:
            continue
        cells = numpy.array(sorted(row[0] for row in event["cells"] if row[7] == comp["component"]))
        cells_ix, cells_iy = numpy.divmod(cells, ny)
        e_new = numpy.array([energies[int(c)][1] for c in cells])
        peaks_ix, peaks_iy = numpy.divmod(numpy.array(comp["peaks"]), ny)
        shared = share_two_peaks(cells_ix, cells_iy, e_new, peaks_ix, peaks_iy, cfg)
        if shared is None:
            continue
        amplitude = shared[0]
        for k in objects:
            out[k] = float(amplitude[comp["peaks"].index(event["objects"][k]["peak_channel"])])
    return out
