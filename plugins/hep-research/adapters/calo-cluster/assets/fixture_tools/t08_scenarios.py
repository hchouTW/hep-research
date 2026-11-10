#!/usr/bin/env python3
"""Scenario checks of T08 (D2 stage 4; plan section 13, A15, A32, A38) on products of reco.calo.cell-cluster/1. Harness side:
it reads a readout, its payloads, a product and a configuration, never truth, and the recipe never imports it.

The section 7.1 selection, checked from the input and not from the recipe's own code. selection_defects forms the 8-connected
components of {live cells with e_c >= T_c} from the readout and the payloads (scipy.ndimage.label, 3 x 3 structure), keeps those
that hold a cell with e_c >= T_s, and requires, for one event of a product:
- the kept cells are exactly the union of the seeded components: a kept cell below T_c, or in a component without a seed, is a
  defect, and so is a cell of a seeded component left out;
- each product component (the cells sharing one label) is exactly one seeded component: two labels on one component (touching
  labels) and one label over two components are defects;
- the product's dead channels are the readout's.
With them, the hit and unhit accounting (A38): each kept cell's raw value is the readout's and its e_c the payloads' arithmetic
on it; kept, unclustered and dead cells add up to the grid; and the input, clustered and unclustered sums equal the readout's
sums over those cells within 1e-9 relative (v4 9.1's tolerance). e_c is formed here as (raw - pedestal) x c, or / g, from the
payloads, the chain's definition (cell_chain). What it does not check: peaks, sharing, positions and uncertainties (the
recipe's own tests and CAI-T08-1 cover those).

Operations:
  accounting          selection_defects on every event of a product against its readout, payloads and configuration. The
                      configuration is the product's own: a product made with another configuration file than the one given
                      (default t08-grid/1's) is refused, as is a product of other cells or payloads. Exit 0 no defect, 1 an
                      event with a defect (GATE ... FAIL), 2 refused.
  reference-selection the reference clusterer's constants against the configuration's: round5/calc-t08-reference.py (SHA-256
                      REFERENCE_SCRIPT_SHA256, job 7479146's script, t04-values-v4.md section 18) holds W, SN, Q, TC, TS and
                      ITERS as literal lines; each must equal the configuration's shower width, noise, quantum, T_c, T_s and
                      sharing iterations, so the targets b carry the recipe's selection (v4 9.2). The script is read as text,
                      never run. Exit 0 equal, 1 a constant differs, 2 refused (another script).
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

import numpy  # noqa: E402

from calo_recipe import cell_input, configuration, gain_payload, product  # noqa: E402

REFERENCE_SCRIPT_SHA256 = "5f096622f3bbe1b3dd16fd5d9630d09fda8f6a736a0c075c63f839fafd59aee9"
RELATIVE = 1e-9
REFERENCE_NAMES = {"W": "shower_width", "SN": "noise_sigma", "Q": "quantum", "TC": "cell_threshold", "TS": "seed_threshold"}


class Refused(ValueError):
    """An input of the scenario checks is refused."""


def cell_energies(raw, live, pedestal_values, gain_values, operation: str):
    """e_c of one event, (nx, ny), NaN where dead: (raw - pedestal) x c when the gain multiplies, / g when it divides."""
    shape = raw.shape
    ped = numpy.asarray(pedestal_values, dtype=float).reshape(shape)
    gain = numpy.asarray(gain_values, dtype=float).reshape(shape)
    with numpy.errstate(invalid="ignore"):
        after = numpy.where(live, raw - ped, numpy.nan)
        return numpy.where(live, after * gain if operation == "multiply" else after / gain, numpy.nan)


def _neighbours(channel: int, nx: int, ny: int):
    ix, iy = divmod(channel, ny)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            jx, jy = ix + dx, iy + dy
            if (dx or dy) and 0 <= jx < nx and 0 <= jy < ny:
                yield jx * ny + jy


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= RELATIVE * max(abs(a), abs(b), 1.0)


def section_7_1_components(energy, live, cfg):
    """The 8-connected components of {live, e_c >= T_c}: (labels array flat, {label: channels}, set of seeded labels)."""
    from scipy import ndimage
    with numpy.errstate(invalid="ignore"):
        above = live & numpy.isfinite(energy) & (energy >= cfg.cell_threshold)
    labels, count = ndimage.label(above, structure=numpy.ones((3, 3), int))
    flat_labels, flat_e = labels.ravel(), energy.ravel()
    members = {k: [int(c) for c in numpy.flatnonzero(flat_labels == k)] for k in range(1, count + 1)}
    seeded = {k for k, cells in members.items() if any(flat_e[c] >= cfg.seed_threshold for c in cells)}
    return flat_labels, members, seeded


def selection_defects(doc: dict, raw, live, energy, cfg) -> list:
    """Every way one event of a read product departs from section 7.1's selection of its input under cfg, or from the hit and
    unhit accounting; an empty list when it does not (module text)."""
    nx, ny = raw.shape
    raw_f, live_f, e_f = raw.ravel(), live.ravel(), energy.ravel()
    defects = []
    dead = [int(c) for c in numpy.flatnonzero(~live_f)]
    if doc["dead_channels"] != dead:
        defects.append(f"dead channels {doc['dead_channels'][:5]} are not the readout's {dead[:5]}")
    flat_labels, members, seeded = section_7_1_components(energy, live, cfg)
    expected = {c for k in seeded for c in members[k]}
    kept = {}
    for row in doc["cells"]:
        channel, raw_value, _ped, _after, _gain, value, _sat, comp = row
        kept[channel] = comp
        if not live_f[channel]:
            continue                                   # the reader refuses a dead cell with a value; reported above
        if raw_value != raw_f[channel]:
            defects.append(f"channel {channel}: raw value {raw_value!r} is not the readout's {float(raw_f[channel])!r}")
        elif value != e_f[channel]:
            defects.append(f"channel {channel}: e_c {value!r} is not the payloads' {float(e_f[channel])!r} on its raw value")
        if e_f[channel] < cfg.cell_threshold:
            defects.append(f"channel {channel}: kept with e_c {float(e_f[channel])!r} below T_c {cfg.cell_threshold}")
        elif channel not in expected:
            defects.append(f"channel {channel}: kept, but its section 7.1 component has no cell at or above T_s {cfg.seed_threshold}")
    for channel in sorted(expected - set(kept)):
        near = any(n in kept for n in _neighbours(channel, nx, ny))
        if e_f[channel] >= cfg.seed_threshold:
            defects.append(f"channel {channel}: e_c {float(e_f[channel])!r} at or above T_s {cfg.seed_threshold} left unclustered")
        else:
            defects.append(f"channel {channel}: e_c {float(e_f[channel])!r} at or above T_c in a seeded component"
                           f"{', adjacent to a kept component,' if near else ''} left out")
    by_component = {}
    for channel, comp in kept.items():
        by_component.setdefault(comp, []).append(channel)
    seen = {}
    for comp, channels in sorted(by_component.items()):
        if not any(live_f[c] and e_f[c] >= cfg.seed_threshold for c in channels):
            defects.append(f"component {comp}: no cell at or above T_s {cfg.seed_threshold}")
        labels = {int(flat_labels[c]) for c in channels}
        if len(labels) != 1 or 0 in labels or set(channels) != set(members[labels.pop()]):
            defects.append(f"component {comp} is not one of section 7.1's components (its cells span or split them)")
            continue
        k = int(flat_labels[channels[0]])
        if k in seen:
            defects.append(f"components {seen[k]} and {comp} are one section 7.1 component: two labels touch")
        seen[k] = comp
    unkept = [int(c) for c in numpy.flatnonzero(live_f) if int(c) not in kept]
    if len(kept) + doc["unclustered_cells"] + len(dead) != nx * ny or doc["unclustered_cells"] != len(unkept):
        defects.append(f"kept {len(kept)}, unclustered {doc['unclustered_cells']} and dead {len(dead)} cells do not account for the "
                       f"{nx * ny} channels ({len(unkept)} live cells are outside the kept components)")
    sums = {"input_sum": math.fsum(float(e_f[c]) for c in numpy.flatnonzero(live_f)),
            "clustered_sum": math.fsum(float(e_f[c]) for c in kept if live_f[c]),
            "unclustered_sum": math.fsum(float(e_f[c]) for c in unkept)}
    for key, value in sums.items():
        if not _close(doc[key], value):
            defects.append(f"{key} {doc[key]!r} MeV is not the readout's {value!r} MeV over those cells (1e-9 relative)")
    return defects


def reference_selection_defects(text: str, cfg) -> list:
    """The reference clusterer's literal constants against the configuration's; an empty list when every one is equal."""
    defects = []
    m = re.search(r"^W, SN, Q, TC, TS = ([^\n]+)$", text, re.MULTILINE)
    values = {}
    if m is None:
        defects.append("the line 'W, SN, Q, TC, TS = ...' is not in the script")
    else:
        try:
            numbers = [float(v) for v in m.group(1).split(",")]
        except ValueError:
            numbers = []
        if len(numbers) != 5:
            defects.append(f"'W, SN, Q, TC, TS = {m.group(1)}' does not hold five numbers")
        else:
            values = dict(zip(("W", "SN", "Q", "TC", "TS"), numbers))
    m = re.search(r"^ITERS = (\d+)$", text, re.MULTILINE)
    if m is None:
        defects.append("the line 'ITERS = ...' is not in the script")
    elif int(m.group(1)) != cfg.sharing_iterations:
        defects.append(f"ITERS {m.group(1)} is not the configuration's sharing iterations {cfg.sharing_iterations}")
    for name, value in values.items():
        own = getattr(cfg, REFERENCE_NAMES[name])
        if own is None or value != own:
            defects.append(f"{name} {value!r} is not the configuration's {REFERENCE_NAMES[name]} {own!r}")
    return defects


def accounting(args) -> int:
    cfg = configuration.load(args.configuration)
    readout = cell_input.read_file(args.cells, cell_input.read_cells, "cells")
    pedestal = cell_input.read_file(args.pedestal_payload, cell_input.read_payload, "pedestal payload")
    gain = cell_input.read_file(args.gain_payload, gain_payload.read_gain, "gain payload")
    read = product.read_product(args.product)
    header = read.header
    if header["input"]["sha256"] != readout.sha256:
        raise Refused("the product was not made from this cells file")
    if (header["chain"][0]["payload_id"], header["chain"][1]["payload_id"]) != (pedestal.identity, gain.identity):
        raise Refused("the product's chain names other pedestal or gain payloads than the ones given")
    if header["configuration"]["sha256"] != cfg.sha256:
        raise Refused(f"the product was made with configuration {header['configuration']['sha256']}, not the one given "
                      f"({cfg.sha256}): its selection is checked against its own configuration only")
    bad, first, kept, unclustered, dead = 0, [], 0, 0, 0
    for i, doc in enumerate(read.events):
        energy = cell_energies(readout.raw[i], readout.live[i], pedestal.values, gain.values, gain.operation)
        found = selection_defects(doc, readout.raw[i], readout.live[i], energy, cfg)
        kept += len(doc["cells"])
        unclustered += doc["unclustered_cells"]
        dead += len(doc["dead_channels"])
        if found:
            bad += 1
            first.extend(f"event {i}: {d}" for d in found[:3])
    n = len(read.events)
    print(f"A38 {args.label} events {n} kept cells {kept} unclustered cells {unclustered} dead cells {dead} "
          f"(T_c {cfg.cell_threshold:g}, T_s {cfg.seed_threshold:g} MeV, configuration {cfg.sha256})")
    print(f"GATE {args.label} selection-and-accounting {'PASS' if bad == 0 else 'FAIL'}: {bad} of {n} events with a defect")
    for line in first[:10]:
        print(f"DEFECT {args.label} {line}")
    return 1 if bad else 0


def reference_selection(args) -> int:
    content = Path(args.script).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != REFERENCE_SCRIPT_SHA256:
        raise Refused(f"script SHA-256 {digest} is not job 7479146's reference clusterer {REFERENCE_SCRIPT_SHA256}")
    cfg = configuration.load(args.configuration)
    defects = reference_selection_defects(content.decode("utf-8"), cfg)
    for d in defects:
        print(f"DEFECT reference-selection {d}")
    print(f"GATE reference-selection {'PASS' if not defects else 'FAIL'}: the reference clusterer's W, SN, Q, TC, TS and ITERS "
          f"{'equal' if not defects else 'differ from'} configuration {cfg.sha256}'s")
    return 1 if defects else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    acc = sub.add_parser("accounting", help="section 7.1's selection and the hit and unhit accounting of every event")
    acc.add_argument("--cells", required=True)
    acc.add_argument("--pedestal-payload", required=True)
    acc.add_argument("--gain-payload", required=True)
    acc.add_argument("--product", required=True)
    acc.add_argument("--label", required=True)
    ref = sub.add_parser("reference-selection", help="the reference clusterer's constants against the configuration's")
    ref.add_argument("--script", required=True, help="round5/calc-t08-reference.py (SHA-256 checked), read as text")
    for p in (acc, ref):
        p.add_argument("--configuration", help="calo-cluster-configuration/1; default the t08-grid/1 configuration")
    args = ap.parse_args(argv)
    try:
        return accounting(args) if args.operation == "accounting" else reference_selection(args)
    except (OSError, Refused, cell_input.InputError, product.ProductError, configuration.ConfigurationError) as exc:
        print(f"REFUSED {getattr(args, 'label', args.operation)} {args.operation}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
