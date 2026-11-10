"""calo-cluster-product/1 and /2, the recipe's own product format (plan 8.3; T08 interfaces), with its writer and its reader.

/2 (D2 stage 2, ruling 2) is written exactly when the gain step consumed a calo-gain-payload/1: its gain step carries that
payload's format, channel map and source, all three. /1 is written for a stage 1 calo-calibration-payload/1 gain and never
carries them, so job 7552825's products are unchanged byte for byte; both are read. The two differ in nothing else.

JSON Lines, UTF-8, one object per line, keys sorted, numbers as Python writes them (shortest round-trip form, so the bytes
read back to the same values), no NaN or infinity anywhere. Line 1 is the header (HEADER_KEYS), then one line per event in
input order (EVENT_KEYS), then the end line {"end": <the header's format>, "events": N}. Nothing follows it.

Header: the product identity, recipe, named energy kind ("clustered deposited energy", t04-values-v4.md section 7; never
incident energy), units, frame and channel rule, grid, the input by format and SHA-256, the configuration by SHA-256, the
chain (each step's payload identity in chain order, the gain's role stated; a calo-gain-payload/1 gain adds its format, channel
map identity and the payload it was derived from, D2 stage 2), and the retention scope (plan 8.3, R34).

Event: the dead channels (no value, never zero); the input, clustered and unclustered sums of e_c and the unclustered count;
the event sum with its uncertainty and saturation flag; cells, one row per cell of a kept component, in CELL_FIELDS order:
stable channel ID (ix * ny + iy), raw value, pedestal applied, value after the pedestal, gain applied, e_c, the readout's
saturated flag and its component, so raw stays beside calibrated; components with their peak candidates, kept peaks and any
recorded failure (sharing-undefined, singular-fisher, non-positive-variance: that component has no objects, and its cells
stay in the event sum with fractions summing to 0, so v4 9.1's "fractions sum to 1 for clustered cells" does not hold for them;
failed_components lists them); objects with energy, position, their uncertainties and status, saturation flag and energy bound, and the
members as [channel, sharing fraction] (R34: sharing fractions kept per cluster).

read_product refuses, with a named reason, a product that is malformed (unknown or missing key, wrong type, a non-finite
number, an unknown energy kind, a cell row whose chain arithmetic does not reproduce its own values, a member outside its
component, a fraction outside [0, 1]) or incomplete (no end line, a wrong count, an event out of order, text after the end).
double_count_defects is the sheet's stop check: no cell counted twice.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy

from . import ENERGY_KIND, RECIPE
from .gain_payload import FORMAT as GAIN_FORMAT, channel_map_identity

FORMAT = "calo-cluster-product/1"
FORMAT_GAIN_PAYLOAD = "calo-cluster-product/2"     # the gain step consumed a calo-gain-payload/1
FORMATS = (FORMAT, FORMAT_GAIN_PAYLOAD)
ENERGY_KINDS = {ENERGY_KIND}
HEADER_KEYS = {"format", "recipe", "product_id", "energy_kind", "energy_unit", "position_unit", "frame", "grid", "input",
               "configuration", "chain", "retention", "cell_fields", "events"}
EVENT_KEYS = {"event", "dead_channels", "input_sum", "clustered_sum", "unclustered_sum", "unclustered_cells", "event_sum", "cells",
              "components", "objects"}
EVENT_SUM_KEYS = {"energy", "sigma", "cells", "saturated", "energy_bound"}
COMPONENT_KEYS = {"component", "candidates", "peaks", "failure"}
OBJECT_KEYS = {"object", "component", "kind", "peak_channel", "energy", "sigma_energy", "x", "y", "sigma_x", "sigma_y",
               "uncertainty_status", "saturated", "energy_bound", "members"}
CELL_FIELDS = ["channel", "raw", "pedestal", "after_pedestal", "gain", "energy", "saturated", "component"]
FRAME = "x_c = ix + 0.5, y_c = iy + 0.5 in cell units, the frame of truth x, y; channel = ix * ny + iy"
RETENTION = {
    "cells": "every cell of a kept component: channel, raw value, pedestal, value after pedestal, gain, e_c, saturated flag",
    "other_live_cells": "sum and count only; reproducible from the input file named by its SHA-256",
    "dead_cells": "listed per event; no value",
    "truth": "none: a data-side product",
    "lost_recalibrations": "from this product alone, a recalibration that moves a cell outside the kept components across T_c "
                           "cannot be redone; with the input file it can",
}
INPUT_KEYS = {"format", "role", "sha256", "events"}
CHAIN_STEP_KEYS = {"pedestal": {"order", "step", "operation", "payload_id", "origin", "round", "derived_against"},
                   "gain": {"order", "step", "operation", "role", "payload_id", "origin", "round", "derived_against"}}
# A calo-gain-payload/1 gain (D2 stage 2) adds its format, channel map and source to the gain step, and makes the product /2;
# a product made with a stage 1 payload stays /1, byte for byte as before. A reader before stage 2 refuses /2.
GAIN_PAYLOAD_KEYS = {"format", "channel_map", "derived_from"}
KINDS = {"one-peak", "two-peak"}
STATUSES = {"ok", "singular-fisher", "non-positive-variance"}
FAILURES = {None, "sharing-undefined", "singular-fisher", "non-positive-variance"}
BOUNDS = {"estimate", "lower-bound"}


class ProductError(ValueError):
    """The product is refused: malformed or incomplete."""


@dataclass
class Product:
    header: dict
    events: list


def dumps(doc) -> str:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False)


def header_document(product_id: str, nx: int, ny: int, input_sha256: str, events: int, configuration_sha256: str, chain: list) -> dict:
    product_format = FORMAT_GAIN_PAYLOAD if "channel_map" in chain[1] else FORMAT
    return {"format": product_format, "recipe": RECIPE, "product_id": product_id, "energy_kind": ENERGY_KIND, "energy_unit": "MeV",
            "position_unit": "cell", "frame": FRAME, "grid": {"nx": nx, "ny": ny},
            "input": {"format": "calo-cells/1", "role": "reconstruction-input", "sha256": input_sha256, "events": events},
            "configuration": {"format": "calo-cluster-configuration/1", "sha256": configuration_sha256}, "chain": chain,
            "retention": dict(RETENTION), "cell_fields": list(CELL_FIELDS), "events": events}


def event_document(index: int, chain, result, ny: int) -> dict:
    """One event line from a cell chain (cell_chain.CellChain) and a clustering result (clustering.EventResult)."""
    component_of = {}
    for comp in result.components:
        for c in comp.channels:
            component_of[c] = comp.index
    raw, ped, after, gain = (a.ravel() for a in (chain.raw, chain.pedestal, chain.after_pedestal, chain.gain))
    energy, sat = chain.energy.ravel(), chain.saturated.ravel()
    cells = [[c, float(raw[c]), float(ped[c]), float(after[c]), float(gain[c]), float(energy[c]), int(sat[c]), component_of[c]]
             for c in sorted(component_of)]
    objects = []
    for k, cluster in enumerate(result.objects):
        objects.append({"object": k, "component": cluster.component, "kind": cluster.kind, "peak_channel": cluster.peak_channel,
                        "energy": cluster.energy, "sigma_energy": cluster.sigma_energy, "x": cluster.x, "y": cluster.y, "sigma_x": cluster.sigma_x,
                        "sigma_y": cluster.sigma_y, "uncertainty_status": cluster.uncertainty_status, "saturated": cluster.saturated,
                        "energy_bound": cluster.energy_bound, "members": [[c, f] for c, f in cluster.members]})
    return {"event": index, "dead_channels": [int(c) for c in numpy.flatnonzero(~chain.live.ravel())],
            "input_sum": result.input_sum, "clustered_sum": result.clustered_sum, "unclustered_sum": result.unclustered_sum,
            "unclustered_cells": result.unclustered_cells,
            "event_sum": {"energy": result.clustered_sum, "sigma": result.event_sum_sigma, "cells": result.event_sum_cells,
                          "saturated": result.event_sum_saturated,
                          "energy_bound": "lower-bound" if result.event_sum_saturated else "estimate"},
            "cells": cells,
            "components": [{"component": comp.index, "candidates": comp.candidates, "peaks": comp.peaks, "failure": comp.failure}
                           for comp in result.components],
            "objects": objects}


class Writer:
    """Writes a product line by line; finish() writes the end line. A product without it is refused as incomplete."""

    def __init__(self, stream, header: dict):
        self.stream, self.expected, self.count, self.format = stream, header["events"], 0, header["format"]
        check_header(header)
        stream.write(dumps(header) + "\n")

    def event(self, doc: dict) -> None:
        if doc["event"] != self.count:
            raise ProductError(f"event {doc['event']} written out of order, expected {self.count}")
        self.stream.write(dumps(doc) + "\n")
        self.count += 1

    def finish(self) -> None:
        if self.count != self.expected:
            raise ProductError(f"{self.count} events written, the header says {self.expected}")
        self.stream.write(dumps({"end": self.format, "events": self.count}) + "\n")


def product_text(product: Product) -> str:
    lines = [dumps(product.header)] + [dumps(e) for e in product.events] + [dumps({"end": product.header["format"], "events": len(product.events)})]
    return "\n".join(lines) + "\n"


# --- reader -----------------------------------------------------------------------------------------------------------

def _refuse(where: str, why: str):
    raise ProductError(f"{where}: {why}")


def _keys(doc, keys, where):
    if not isinstance(doc, dict):
        _refuse(where, "not an object")
    if set(doc) != keys:
        missing, extra = sorted(keys - set(doc)), sorted(set(doc) - keys)
        _refuse(where, f"keys differ (missing {missing}, not allowed {extra})")


def _count(value, where, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _refuse(where, "not a count")
    return value


def _number(value, where, allow_none=False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _refuse(where, "not a finite number")
    return float(value)


def _hex64(value, where):
    if not (isinstance(value, str) and len(value) == 64 and set(value) <= set("0123456789abcdef")):
        _refuse(where, "not a SHA-256 identity")


def check_header(header: dict) -> None:
    _keys(header, HEADER_KEYS, "header")
    if header["format"] not in FORMATS:
        _refuse("header.format", f"{header['format']!r} is not one of {FORMATS}")
    if header["recipe"] != RECIPE:
        _refuse("header.recipe", f"{header['recipe']!r} is not {RECIPE}")
    if header["energy_kind"] not in ENERGY_KINDS:
        _refuse("header.energy_kind", f"{header['energy_kind']!r} refused: this recipe reports clustered deposited energy only, "
                                      "never incident energy")
    if header["energy_unit"] != "MeV" or header["position_unit"] != "cell" or header["frame"] != FRAME:
        _refuse("header", "units or frame are not this format's")
    if not isinstance(header["product_id"], str) or not header["product_id"]:
        _refuse("header.product_id", "a product needs its identity")
    _keys(header["grid"], {"nx", "ny"}, "header.grid")
    _count(header["grid"]["nx"], "header.grid.nx", 1)
    _count(header["grid"]["ny"], "header.grid.ny", 1)
    _keys(header["input"], INPUT_KEYS, "header.input")
    if header["input"]["format"] != "calo-cells/1" or header["input"]["role"] != "reconstruction-input":
        _refuse("header.input", "the input must be a calo-cells/1 reconstruction input")
    _hex64(header["input"]["sha256"], "header.input.sha256")
    _count(header["input"]["events"], "header.input.events")
    _keys(header["configuration"], {"format", "sha256"}, "header.configuration")
    _hex64(header["configuration"]["sha256"], "header.configuration.sha256")
    chain = header["chain"]
    if not isinstance(chain, list) or [s.get("step") if isinstance(s, dict) else None for s in chain] != ["pedestal", "gain"]:
        _refuse("header.chain", "the chain must be pedestal then gain, in that order")
    for order, step in enumerate(chain, 1):
        keys = CHAIN_STEP_KEYS[step["step"]]
        if step["step"] == "gain" and header["format"] == FORMAT_GAIN_PAYLOAD:
            keys = keys | GAIN_PAYLOAD_KEYS          # /2 carries all three; /1 none of them
        _keys(step, keys, f"header.chain[{order - 1}]")
        if step["order"] != order:
            _refuse(f"header.chain[{order - 1}].order", "chain order is not recorded in sequence")
        _hex64(step["payload_id"], f"header.chain[{order - 1}].payload_id")
    if header["format"] == FORMAT_GAIN_PAYLOAD:
        if chain[1]["format"] != GAIN_FORMAT:
            _refuse("header.chain[1].format", f"{chain[1]['format']!r} is not {GAIN_FORMAT}")
        _hex64(chain[1]["channel_map"], "header.chain[1].channel_map")
        if chain[1]["channel_map"] != channel_map_identity(header["grid"]["nx"], header["grid"]["ny"]):
            _refuse("header.chain[1].channel_map", "the gain payload's channel map is not this grid's")
        if chain[1]["derived_from"] is not None:
            _hex64(chain[1]["derived_from"], "header.chain[1].derived_from")
    if chain[0]["operation"] != "subtract" or chain[1]["operation"] not in ("multiply", "divide"):
        _refuse("header.chain", "pedestal subtracts; the gain multiplies or divides")
    if chain[1]["derived_against"] != [chain[0]["payload_id"]]:
        _refuse("header.chain[1].derived_against", "the gain was not derived against the pedestal this chain applied")
    if header["retention"] != RETENTION or header["cell_fields"] != CELL_FIELDS:
        _refuse("header", "retention or cell fields are not this format's")
    if _count(header["events"], "header.events") != header["input"]["events"]:
        _refuse("header.events", "the product does not cover every input event")


def check_event(doc: dict, index: int, header: dict) -> None:
    where = f"event {index}"
    _keys(doc, EVENT_KEYS, where)
    if doc["event"] != index:
        _refuse(where, f"out of order: it says {doc['event']!r}")
    channels = header["grid"]["nx"] * header["grid"]["ny"]
    multiply = header["chain"][1]["operation"] == "multiply"
    dead = doc["dead_channels"]
    if not isinstance(dead, list) or any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < channels for c in dead) \
            or dead != sorted(set(dead)):
        _refuse(f"{where}.dead_channels", "not ascending distinct channels")
    for key in ("input_sum", "clustered_sum", "unclustered_sum"):
        _number(doc[key], f"{where}.{key}")
    _count(doc["unclustered_cells"], f"{where}.unclustered_cells")
    comps = doc["components"]
    if not isinstance(comps, list):
        _refuse(f"{where}.components", "not a list")
    cells = doc["cells"]
    if not isinstance(cells, list):
        _refuse(f"{where}.cells", "not a list")
    cell_component, cell_saturated, cell_energy = {}, {}, {}
    dead_set = set(dead)
    previous = -1
    for row in cells:
        if not isinstance(row, list) or len(row) != len(CELL_FIELDS):
            _refuse(f"{where}.cells", "a row does not hold the cell fields")
        channel, raw, ped, after, gain, energy, sat, comp = row
        _count(channel, f"{where}.cells channel")
        if channel <= previous or channel >= channels:
            _refuse(f"{where}.cells", "channels must ascend, each once, inside the grid")
        if channel in dead_set:
            _refuse(f"{where}.cells", f"dead channel {channel} has a value")
        previous = channel
        raw, ped, after, gain, energy = (_number(v, f"{where}.cells[{channel}]") for v in (raw, ped, after, gain, energy))
        if after != raw - ped or energy != (after * gain if multiply else after / gain):
            _refuse(f"{where}.cells[{channel}]", "raw, pedestal, gain and e_c do not reproduce each other through the chain")
        if sat not in (0, 1) or isinstance(sat, bool):
            _refuse(f"{where}.cells[{channel}]", "saturated must be 0 or 1")
        if isinstance(comp, bool) or not isinstance(comp, int) or not 0 <= comp < len(comps):
            _refuse(f"{where}.cells[{channel}]", "component out of range")
        cell_component[channel], cell_saturated[channel], cell_energy[channel] = comp, sat, energy
    for j, comp in enumerate(comps):
        _keys(comp, COMPONENT_KEYS, f"{where}.components[{j}]")
        if comp["component"] != j:
            _refuse(f"{where}.components[{j}]", "out of order")
        own = {c for c, k in cell_component.items() if k == j}
        if not own:
            _refuse(f"{where}.components[{j}]", "has no cells")
        if not isinstance(comp["candidates"], list) or not set(comp["candidates"]) <= own or not isinstance(comp["peaks"], list) \
                or not set(comp["peaks"]) <= set(comp["candidates"]) or len(comp["peaks"]) > 2:
            _refuse(f"{where}.components[{j}]", "peaks must be candidates, and candidates cells of the component")
        if comp["failure"] not in FAILURES:
            _refuse(f"{where}.components[{j}].failure", "unknown failure")
    _keys(doc["event_sum"], EVENT_SUM_KEYS, f"{where}.event_sum")
    _number(doc["event_sum"]["energy"], f"{where}.event_sum.energy")
    if doc["event_sum"]["energy"] != doc["clustered_sum"]:
        _refuse(f"{where}.event_sum.energy", "differs from clustered_sum; the event sum is the sum over the kept components")
    total = doc["clustered_sum"] + doc["unclustered_sum"]
    if abs(total - doc["input_sum"]) > 1e-9 * max(abs(doc["input_sum"]), 1.0):
        _refuse(f"{where}", "clustered plus unclustered energy does not equal the input within 1e-9 relative (v4 9.1)")
    _number(doc["event_sum"]["sigma"], f"{where}.event_sum.sigma")
    if _count(doc["event_sum"]["cells"], f"{where}.event_sum.cells") != len(cells):
        _refuse(f"{where}.event_sum.cells", "differs from the cells of the kept components")
    flagged = any(cell_saturated.values())
    if doc["event_sum"]["saturated"] is not flagged or doc["event_sum"]["energy_bound"] != ("lower-bound" if flagged else "estimate"):
        _refuse(f"{where}.event_sum", "saturation flag or energy bound does not follow its cells")
    objects = doc["objects"]
    if not isinstance(objects, list):
        _refuse(f"{where}.objects", "not a list")
    for k, cluster in enumerate(objects):
        at = f"{where}.objects[{k}]"
        _keys(cluster, OBJECT_KEYS, at)
        if cluster["object"] != k:
            _refuse(at, "out of order")
        if isinstance(cluster["component"], bool) or not isinstance(cluster["component"], int) or not 0 <= cluster["component"] < len(comps):
            _refuse(at, "component out of range")
        if comps[cluster["component"]]["failure"] is not None:
            _refuse(at, "a failed component has no objects")
        if cluster["kind"] not in KINDS or cluster["uncertainty_status"] not in STATUSES or cluster["energy_bound"] not in BOUNDS:
            _refuse(at, "unknown kind, uncertainty status or energy bound")
        for key in ("energy", "x", "y"):
            _number(cluster[key], f"{at}.{key}")
        sigmas = [_number(cluster[key], f"{at}.{key}", allow_none=True) for key in ("sigma_energy", "sigma_x", "sigma_y")]
        if (cluster["uncertainty_status"] == "ok") != all(s is not None and s > 0 for s in sigmas) or \
                (cluster["uncertainty_status"] != "ok" and any(s is not None for s in sigmas)):
            _refuse(at, "uncertainties must be positive with status ok, and absent otherwise")
        members = cluster["members"]
        if not isinstance(members, list) or not members:
            _refuse(f"{at}.members", "an object needs members")
        last = -1
        saturated = False
        for member in members:
            if not isinstance(member, list) or len(member) != 2:
                _refuse(f"{at}.members", "a member is [channel, fraction]")
            channel, fraction = member
            if isinstance(channel, bool) or not isinstance(channel, int) or channel <= last:
                _refuse(f"{at}.members", "channels must ascend, each once")
            last = channel
            if cell_component.get(channel) != cluster["component"]:
                _refuse(f"{at}.members", f"channel {channel} is not a cell of component {cluster['component']}")
            fraction = _number(fraction, f"{at}.members[{channel}]")
            if not 0.0 <= fraction <= 1.0 or (cluster["kind"] == "one-peak" and fraction != 1.0):
                _refuse(f"{at}.members[{channel}]", "a sharing fraction lies in [0, 1], and is 1 in a one-peak object")
            saturated = saturated or (fraction > 0.0 and cell_saturated[channel] == 1)
        if cluster["saturated"] is not saturated or cluster["energy_bound"] != ("lower-bound" if saturated else "estimate"):
            _refuse(at, "saturation flag or energy bound does not follow its members")


def parse_line(line: str, where: str):
    try:
        return json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except ValueError:
        _refuse(where, "not a JSON line of finite numbers")


def read_text(text: str) -> Product:
    if not text.endswith("\n"):
        _refuse("product", "incomplete: the last line is unfinished")
    lines = text[:-1].split("\n")
    if not lines or not lines[0]:
        _refuse("product", "empty")
    header = parse_line(lines[0], "header")
    check_header(header)
    n = header["events"]
    if len(lines) < n + 2:
        _refuse("product", f"incomplete: {max(len(lines) - 1, 0)} lines after the header, expected {n} events and the end line")
    if len(lines) > n + 2:
        _refuse("product", "text after the end line")
    events = []
    for i in range(n):
        doc = parse_line(lines[1 + i], f"event {i}")
        if isinstance(doc, dict) and "end" in doc:
            _refuse("product", f"incomplete: end line after {i} of {n} events")
        check_event(doc, i, header)
        events.append(doc)
    end = parse_line(lines[n + 1], "end line")
    if end != {"end": header["format"], "events": n}:
        _refuse("end line", f"expected {{'end': {header['format']!r}, 'events': {n}}}")
    return Product(header=header, events=events)


def read_product(path) -> Product:
    try:
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
    except OSError as exc:
        raise ProductError(f"product cannot be read: {exc.strerror}") from None
    except UnicodeDecodeError:
        raise ProductError("product is not UTF-8") from None
    return read_text(text)


# --- the sheet's stop -------------------------------------------------------------------------------------------------

def double_count_defects(doc: dict, tolerance: float = 1e-12, relative: float = 1e-9) -> list:
    """Every way a cell could be counted twice in one event of a read product; an empty list when none is.

    A cell of a kept component belongs to that component only, and its sharing fractions over the component's objects sum to
    1 (to `tolerance`); a cell of a failed component has none. No object lists a cell twice (the reader refuses that). The
    objects' energies sum to the e_c of the cells they hold, each cell once, and the event sum equals the sum of e_c over
    the kept components, each cell once (to `relative`). Each object's energy equals sum_c f_kc e_c over its own members, so energy
    moved between the objects of a component is caught too. A failed component (no objects) is not a double count; see
    failed_components."""
    defects = []
    energy = {row[0]: row[5] for row in doc["cells"]}
    component = {row[0]: row[7] for row in doc["cells"]}
    failed = {c["component"] for c in doc["components"] if c["failure"] is not None}
    total = dict.fromkeys(energy, 0.0)
    seen_in = {}
    for cluster in doc["objects"]:
        for channel, fraction in cluster["members"]:
            total[channel] += fraction
            seen_in.setdefault(channel, set()).add(cluster["component"])
    for channel, comps in seen_in.items():
        if len(comps) > 1:
            defects.append(f"channel {channel} is a member of objects of components {sorted(comps)}")
    for channel, fraction in total.items():
        expected = 0.0 if component[channel] in failed else 1.0
        if abs(fraction - expected) > tolerance:
            defects.append(f"channel {channel}: fractions sum to {fraction!r}, expected {expected}")
    for k, cluster in enumerate(doc["objects"]):
        own = math.fsum(fraction * energy[channel] for channel, fraction in cluster["members"])
        if abs(cluster["energy"] - own) > relative * max(abs(own), 1.0):
            defects.append(f"object {k} holds {cluster['energy']!r} MeV, its shares of its cells {own!r} MeV")
    held = math.fsum(e for c, e in energy.items() if component[c] not in failed)
    objects = math.fsum(o["energy"] for o in doc["objects"])
    if abs(objects - held) > relative * max(abs(held), 1.0):
        defects.append(f"objects hold {objects!r} MeV, their cells {held!r} MeV")
    every = math.fsum(energy.values())
    if abs(doc["event_sum"]["energy"] - every) > relative * max(abs(every), 1.0):
        defects.append(f"event sum {doc['event_sum']['energy']!r} MeV, kept cells {every!r} MeV")
    return defects


def failed_components(doc: dict) -> list:
    """[(component, failure, cells)] of an event's components that have no objects: their cells count in the event sum with
    fractions summing to 0 (v4 9.1 asks 1 for clustered cells), reported apart from the double-count check."""
    cells = {}
    for row in doc["cells"]:
        cells[row[7]] = cells.get(row[7], 0) + 1
    return [(c["component"], c["failure"], cells.get(c["component"], 0)) for c in doc["components"] if c["failure"] is not None]
