#!/usr/bin/env python3
"""T08's second input (t07-t09-task-sheets.md, T08, "Input, second"): the cell deposits of the user's zdcsim program, converted to
the recipe's labelled readout calo-cells/2 with the label simulated-unvalidated. That study's model passed 1 of 5 measurable
gates: this input exercises the format only and supports no performance number (plan R31: no quality claim).

zdcsim.cc is user-supplied material, built and run outside the repository in an approved job; it is never copied here, and no
code of it is: its rules below are written from its text and checked by the tests. Its SHA-256 must be the supplied file's
(ZDCSIM_SOURCE_SHA256). Its ROOT tree "events" has, per event, sparse deposits in three columns: cell (crystal id iy * n + ix),
zbin (1 mm longitudinal bin inside the crystal, 0 to ceil(crystal_z_mm) - 1) and edep (MeV, float). This tool reads those three
columns only, never the tree's truth columns (the primary's energy, position and direction, entry point, other deposits).

Operations:
  convert   ROOT file -> <stem>.cells (calo-cells/2), <stem>.pedestal.json and <stem>.gain.json (calo-calibration-payload/1,
            the identity readout), <stem>.conversion.json (t08-zdcsim-conversion/1: per event the entries, the cells with a
            deposit and the input deposit sum, with the same label and provenance). Per crystal, edep is summed over zbin in
            double precision with math.fsum (exactly rounded, independent of entry order). zdcsim's cell iy * n + ix becomes the
            recipe's cell (ix, iy), channel ix * ny + iy (section 7.1's stable channel ID). Refused, with nothing written: another
            zdcsim source, a configuration of type other than prototype, a file without the tree or any of the three columns,
            columns of unequal length in an event, an unknown cell ID (outside 0 to n * n - 1, HCAL ids included), a z bin outside
            the crystal, a negative or non-finite deposit, a (cell, zbin) given twice in an event, integer columns that are not
            integers, and a number of entries other than the run's events.
  check-layout  the same reading and checks as convert on an existing file, writing nothing (the job reads S3's 1-event file
            with it before any compute, to check zdcsim's std::vector layout).
  readings  a calo-cluster-product/3 made from that readout, with its conversion record: format and bookkeeping readings
            only (events, entries, cells, components, objects per event, object kinds, conservation, double counting) and four
            gates (label, events, double count, conservation within 1e-9 relative, v4 9.1's tolerance). No energy, position,
            pull, resolution or efficiency is printed: none is a performance number on this input.

The identity readout: zdcsim gives deposited energy, not ADC. So the raw value of a crystal is its summed deposit in MeV (unit
"MeV"), the pedestal payload is 0 (subtract), the gain payload is 1 (multiply, MeV/MeV), every live, none saturated, no dead
cell, no noise and no ADC model: none is invented from that study's numbers. Both steps are still applied and recorded in chain
order (plan R34). The energy kind stays clustered deposited energy, never incident energy.

Exit 0 written or every gate passed; 1 a gate failed (readings); 2 refused input; 3 a missing dependency (uproot, numpy).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

import numpy

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from calo_recipe import cell_input  # noqa: E402

ZDCSIM_SOURCE_SHA256 = "28018224c1419a87e0da7f6b24b3557d93b878269f32f8d5aaedecf0d51ec203"   # the supplied zdcsim.cc
LABEL = "simulated-unvalidated"
INPUT_FORMAT = "zdcsim-events-root"
TREE = "events"
COLUMNS = ("cell", "zbin", "edep")
Z_BIN_MM = 1.0                                   # zdcsim.cc: dz = 1.0 mm
RAW_UNIT = "MeV"
CONVERSION_FORMAT = "t08-zdcsim-conversion/1"
CONVERSION_KEYS = {"format", "label", "provenance", "cells_sha256", "pedestal_sha256", "gain_sha256", "events"}
EVENT_KEYS = {"event", "entries", "cells_hit", "deposit_sum_mev"}
CONVERSION_RULE = ("per crystal, edep summed over zbin with math.fsum in double precision; zdcsim cell iy * n + ix -> recipe cell "
                   "(ix, iy), channel ix * ny + iy; crystal cells only; event index = row index of the tree (the run uses one thread)")
BUILD_RECORD_FORMAT = "zdcsim-build-record/1"
BUILD_RECORD_KEYS = {"format", "compiler", "geant4_version", "route", "command"}
SYMBOLS = {"cell_threshold_mev": "T_c", "seed_threshold_mev": "T_s", "shower_width_cells": "W", "cell_quantum_mev": "q",
           "noise_sigma_mev": "sigma_n", "grid": "grid", "sharing_iterations": "sharing_iterations", "peaks_kept": "peaks_kept"}
READOUT_RULE = ("identity readout of deposited energy: raw = summed deposit in MeV, pedestal 0, gain 1 (multiply), all cells live, "
                "none saturated, no noise, no ADC model")
PEDESTAL_SOURCE = "identity readout of zdcsim deposits: no pedestal (deposited energy, not ADC); D2 stage 3, simulated-unvalidated"
GAIN_SOURCE = ("identity readout of zdcsim deposits: gain 1, raw is deposited energy in MeV, so e_c = raw; D2 stage 3, "
               "simulated-unvalidated")
CONSERVATION_RELATIVE = 1e-9                     # t04-values-v4.md section 9.1, conservation
READING_NAMES = {"label", "configuration", "events", "entries_per_event", "cells_with_deposit_per_event", "live_cells_per_event",
                 "unclustered_cells_per_event", "components_per_event", "objects_per_event", "object_kinds",
                 "components_with_two_kept_peaks", "failed_components", "double_count_defects", "conservation_max_relative"}
EXIT_FAILED, EXIT_INVALID, EXIT_MISSING = 1, 2, 3


class ConversionError(ValueError):
    """Refused: the reason names the input and the defect."""


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def recipe_cell(cell: int, n: int) -> tuple:
    """zdcsim's crystal id iy * n + ix -> the recipe's (ix, iy)."""
    return cell % n, cell // n


def check_source(path, expected: str = ZDCSIM_SOURCE_SHA256) -> str:
    try:
        digest = sha256_file(path)
    except OSError as exc:
        raise ConversionError(f"zdcsim source cannot be read: {exc.strerror}") from None
    if digest != expected:
        raise ConversionError(f"zdcsim source SHA-256 {digest} is not the supplied file's {expected}")
    return digest


# --- zdcsim's configuration rules (Cfg::load and its d, i, s readers, written from zdcsim.cc's text) ---------------------

_NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def _trim(text: str) -> str:
    return text.strip(" \t\r\n\"'")


def zdcsim_keys(paths) -> dict:
    """'key: value' lines; '#' starts a comment; the first ':' splits; key and value trimmed of blanks and quotes; a line with
    either empty is skipped; later files override earlier ones."""
    keys = {}
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ConversionError(f"zdcsim configuration {Path(path).name} cannot be read: {exc}") from None
        for line in text.splitlines():
            line = line.split("#", 1)[0]
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key, value = _trim(key), _trim(value)
            if key and value:
                keys[key] = value
    return keys


def _number(keys: dict, key: str, default: float) -> float:
    if key not in keys:
        return default
    m = _NUMBER.match(keys[key].lstrip())
    if not m:
        raise ConversionError(f"zdcsim configuration: {key} {keys[key]!r} is not a number (zdcsim's std::stod would throw)")
    return float(m.group(0))


def _lround(value: float) -> int:
    return int(math.floor(value + 0.5)) if value >= 0 else -int(math.floor(-value + 0.5))


def zdcsim_geometry(paths) -> dict:
    """The crystal grid zdcsim builds from these configuration files (geometry, then sample, as the job passes them)."""
    keys = zdcsim_keys(paths)
    kind = keys.get("type", "prototype")
    if kind != "prototype":
        raise ConversionError(f"zdcsim configuration type {kind!r}: only the prototype's crystal cells are read here")
    n = _lround(_number(keys, "n_crystals", 8))
    length = _number(keys, "crystal_z_mm", 53)
    if n < 1 or not length > 0:
        raise ConversionError("zdcsim configuration: n_crystals and crystal_z_mm must be positive")
    cx, cy = _number(keys, "crystal_x_mm", 20), _number(keys, "crystal_y_mm", 20)
    wrap, gap = _number(keys, "wrap_um", 65) * 1e-3, _number(keys, "gap_mm", 0.2)
    return {"type": kind, "n_crystals": n, "crystal_x_mm": cx, "crystal_y_mm": cy, "crystal_z_mm": length,
            "wrap_um": wrap * 1e3, "gap_mm": gap, "pitch_x_mm": cx + 2 * wrap + gap, "pitch_y_mm": cy + 2 * wrap + gap,
            "z_bin_mm": Z_BIN_MM, "z_bins": int(math.ceil(length / Z_BIN_MM))}


# --- deposits to cells ----------------------------------------------------------------------------------------------------

def deposits_to_cells(events, n: int, nz: int):
    """events: per event (cell, zbin, edep) arrays. Returns raw (N, n, n) float64 with array axis 0 = ix, and the per-event
    record [{event, entries, cells_hit, deposit_sum_mev}]."""
    events = list(events)
    raw = numpy.zeros((len(events), n, n))
    record = []
    for i, (cell, zbin, edep) in enumerate(events):
        cell, zbin, edep = numpy.asarray(cell), numpy.asarray(zbin), numpy.asarray(edep)
        if not (cell.ndim == zbin.ndim == edep.ndim == 1) or not (len(cell) == len(zbin) == len(edep)):
            raise ConversionError(f"event {i}: the cell, zbin and edep columns have different lengths")
        if len(cell) and not (numpy.issubdtype(cell.dtype, numpy.integer) and numpy.issubdtype(zbin.dtype, numpy.integer)):
            raise ConversionError(f"event {i}: cell and zbin must be integers")
        bad = (cell < 0) | (cell >= n * n)
        if bad.any():
            raise ConversionError(f"event {i}: unknown cell {int(cell[bad][0])}: the prototype grid has cells 0 to {n * n - 1} "
                                  "(HCAL and any other id refused)")
        bad = (zbin < 0) | (zbin >= nz)
        if bad.any():
            raise ConversionError(f"event {i}: z bin {int(zbin[bad][0])} outside the crystal's 0 to {nz - 1}")
        values = edep.astype(numpy.float64)
        if not numpy.all(numpy.isfinite(values)) or numpy.any(values < 0.0):
            raise ConversionError(f"event {i}: a negative or non-finite deposit")
        pairs = cell.astype(numpy.int64) * nz + zbin.astype(numpy.int64)
        ordered = numpy.sort(pairs)
        repeats = ordered[1:][ordered[1:] == ordered[:-1]]
        if len(repeats):
            repeated = int(repeats[0])
            raise ConversionError(f"event {i}: cell {repeated // nz}, z bin {repeated % nz} given twice")
        hit = sorted(set(int(c) for c in cell))
        for c in hit:
            ix, iy = recipe_cell(c, n)
            raw[i, ix, iy] = math.fsum(float(v) for v in values[cell == c])
        record.append({"event": i, "entries": int(len(cell)), "cells_hit": len(hit),
                       "deposit_sum_mev": math.fsum(float(v) for v in values)})
    return raw, record


def _dumps(doc) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")


def write_files(raw, record, provenance: dict, out_dir, stem: str) -> dict:
    """The labelled readout, the identity payloads and the conversion record. Everything is checked before a file is written."""
    raw = numpy.asarray(raw, dtype=float)
    live, saturated = numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)
    try:
        cells = cell_input.cells_bytes(raw, live, saturated, raw_unit=RAW_UNIT, label=LABEL, provenance=provenance)
    except cell_input.InputError as exc:
        raise ConversionError(str(exc)) from None
    if len(record) != raw.shape[0]:
        raise ConversionError("the event record does not cover every event")
    channels = raw.shape[1] * raw.shape[2]
    ped = cell_input.payload_bytes("pedestal", "subtract", 0.0, channels, RAW_UNIT, "nominal", PEDESTAL_SOURCE)
    gain = cell_input.payload_bytes("gain", "multiply", 1.0, channels, "MeV/MeV", "nominal", GAIN_SOURCE,
                                    derived_against=[hashlib.sha256(ped).hexdigest()])
    conversion = {"format": CONVERSION_FORMAT, "label": LABEL, "provenance": provenance,
                  "cells_sha256": hashlib.sha256(cells).hexdigest(), "pedestal_sha256": hashlib.sha256(ped).hexdigest(),
                  "gain_sha256": hashlib.sha256(gain).hexdigest(), "events": record}
    content = _dumps(conversion)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, suffix, file_bytes in (("cells", "cells", cells), ("pedestal", "pedestal.json", ped), ("gain", "gain.json", gain),
                                     ("conversion", "conversion.json", content)):
        path = out_dir / f"{stem}.{suffix}"
        path.write_bytes(file_bytes)
        files[name] = {"path": str(path), "sha256": hashlib.sha256(file_bytes).hexdigest()}
    return files


def read_conversion(path) -> dict:
    """A t08-zdcsim-conversion/1 record; refused without its label or provenance, or with a malformed event list."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"),
                         parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ConversionError(f"conversion record cannot be read: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != CONVERSION_KEYS or doc.get("format") != CONVERSION_FORMAT:
        raise ConversionError(f"conversion record: not {CONVERSION_FORMAT} with exactly {sorted(CONVERSION_KEYS)}")
    events = doc["events"]
    if not isinstance(events, list) or any(not isinstance(e, dict) or set(e) != EVENT_KEYS or e["event"] != k for k, e in enumerate(events)):
        raise ConversionError("conversion record: events must be in order, each with exactly " + str(sorted(EVENT_KEYS)))
    try:
        cell_input.check_label(doc["label"], "conversion record")
        cell_input.check_provenance(doc["provenance"], len(events), "conversion record")
    except cell_input.InputError as exc:
        raise ConversionError(str(exc)) from None
    return doc


# --- the ROOT file --------------------------------------------------------------------------------------------------------

def read_root_deposits(path):
    """The three columns of tree "events", one (cell, zbin, edep) triple of arrays per entry, in file order; and the columns
    read. Nothing else in the tree is read."""
    import uproot
    try:
        handle = uproot.open(path)
    except ImportError:
        raise                     # a missing codec or module is a missing dependency (exit 3), never a refusal of the input
    except Exception as exc:  # uproot raises several types for a file that is not ROOT
        raise ConversionError(f"{Path(path).name}: not a readable ROOT file ({type(exc).__name__})") from None
    with handle as f:
        try:
            tree = f[TREE]
            names = set(tree.keys())
        except ImportError:
            raise
        except Exception:
            raise ConversionError(f"{Path(path).name}: no tree {TREE!r}") from None
        missing = [c for c in COLUMNS if c not in names]
        if missing:
            raise ConversionError(f"{Path(path).name}: tree {TREE!r} lacks column(s) {', '.join(missing)}")
        try:
            arrays = tree.arrays(list(COLUMNS), library="np")
        except ImportError:
            raise
        except Exception as exc:
            raise ConversionError(f"{Path(path).name}: columns {', '.join(COLUMNS)} cannot be decoded ({type(exc).__name__})") from None
    events = [tuple(numpy.asarray(arrays[c][k]) for c in COLUMNS) for k in range(len(arrays[COLUMNS[0]]))]
    return events, list(COLUMNS)


def read_build_record(path) -> dict:
    """A zdcsim-build-record/1 file written by the job's build step: the compiler, the Geant4 version, the route and the command.
    Returns its fields and its SHA-256."""
    try:
        content = Path(path).read_bytes()
        doc = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ConversionError(f"build record cannot be read: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != BUILD_RECORD_KEYS or doc["format"] != BUILD_RECORD_FORMAT or \
            not all(isinstance(doc[k], str) and doc[k] for k in BUILD_RECORD_KEYS):
        raise ConversionError(f"build record: not {BUILD_RECORD_FORMAT} with exactly {sorted(BUILD_RECORD_KEYS)}, each a non-empty text")
    return {"sha256": hashlib.sha256(content).hexdigest(), **{k: doc[k] for k in BUILD_RECORD_KEYS - {"format"}}}


def check_layout(*, root, geometry, sample, events: int) -> dict:
    """Read an existing zdcsim file as convert does, with every refusal, and write nothing: the entries, the deposit entries and
    the dtypes uproot gives the three columns."""
    grid = zdcsim_geometry([geometry, sample])
    deposits, _ = read_root_deposits(root)
    if len(deposits) != events:
        raise ConversionError(f"the file has {len(deposits)} entries; expected {events}")
    _, record = deposits_to_cells(deposits, grid["n_crystals"], grid["z_bins"])
    first = next((d for d in deposits if len(d[0])), deposits[0] if deposits else None)
    dtypes = {c: (str(first[k].dtype) if first is not None else None) for k, c in enumerate(COLUMNS)}
    return {"entries": len(deposits), "deposit_entries": sum(r["entries"] for r in record), "dtypes": dtypes,
            "cells_hit": [r["cells_hit"] for r in record]}


def convert(*, root, source, geometry, sample, seed: int, events: int, physics: str, threads, executable, out_dir, stem: str,
            expected_source: str = ZDCSIM_SOURCE_SHA256, build_record=None) -> dict:
    source_sha = check_source(source, expected_source)
    grid = zdcsim_geometry([geometry, sample])
    try:
        input_sha = sha256_file(root)
    except OSError as exc:
        raise ConversionError(f"ROOT file cannot be read: {exc.strerror}") from None
    deposits, _ = read_root_deposits(root)
    if len(deposits) != events:
        raise ConversionError(f"the file has {len(deposits)} entries; the run asked for {events} events")
    raw, record = deposits_to_cells(deposits, grid["n_crystals"], grid["z_bins"])
    build = {"executable_sha256": sha256_file(executable) if executable else None, "record_sha256": None, "compiler": None,
             "geant4_version": None, "route": None, "command": None}
    if build_record is not None:
        built = read_build_record(build_record)
        build.update(record_sha256=built["sha256"], **{k: built[k] for k in ("compiler", "geant4_version", "route", "command")})
    provenance = {
        "producer": {"name": "zdcsim", "source_sha256": source_sha, "label": "user-supplied",
                     "build": build},
        "configuration": [{"role": "geometry", "name": Path(geometry).name, "sha256": sha256_file(geometry)},
                          {"role": "sample", "name": Path(sample).name, "sha256": sha256_file(sample)}],
        "run": {"seed": seed, "events": events, "physics": physics, "threads": threads},
        "input": {"format": INPUT_FORMAT, "tree": TREE, "sha256": input_sha, "entries": len(deposits)},
        "conversion": {"tool_sha256": sha256_file(__file__), "rule": CONVERSION_RULE, "readout": READOUT_RULE, "geometry": grid},
    }
    return write_files(raw, record, provenance, out_dir, stem)


# --- readings -------------------------------------------------------------------------------------------------------------

def _spread(values) -> str:
    return f"min {min(values)} median {statistics.median(values)} max {max(values)}" if values else "none"


def _histogram(values) -> dict:
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def configuration_line(h: dict) -> str:
    """The configuration by SHA-256, with its unresolved constants and their plan 1.1 record (F1: the user's decision on T_c, T_s)."""
    unresolved = h["configuration"].get("unresolved", {})
    text = f"sha256 {h['configuration']['sha256']}"
    if not unresolved:
        return text + "; nothing unresolved"
    first = next(iter(unresolved.values()))
    names = ", ".join(SYMBOLS.get(k, k) for k in unresolved)
    return f"{text}; {names} {first['status']}, owner {first['owner']}, exit: {first['exit']}"


def evaluate(h: dict, events: list, conv: dict):
    """The four gates and the bookkeeping lines of a labelled product against its conversion record."""
    from calo_recipe import product
    record = conv["events"]
    gates = {"label": h["label"] == conv["label"] == LABEL,
             "events": len(events) == len(record) == h["provenance"]["run"]["events"]}
    defects = sum(len(product.double_count_defects(doc)) for doc in events)
    failed = sum(len(product.failed_components(doc)) for doc in events)
    worst_input = worst_total = 0.0
    for doc, rec in zip(events, record):
        scale = max(abs(rec["deposit_sum_mev"]), 1.0)
        worst_input = max(worst_input, abs(doc["input_sum"] - rec["deposit_sum_mev"]) / scale)
        worst_total = max(worst_total, abs(doc["clustered_sum"] + doc["unclustered_sum"] - rec["deposit_sum_mev"]) / scale)
    gates["double-count"] = defects == 0
    gates["conservation"] = worst_input <= CONSERVATION_RELATIVE and worst_total <= CONSERVATION_RELATIVE
    channels = h["grid"]["nx"] * h["grid"]["ny"]
    kinds = _histogram(o["kind"] for doc in events for o in doc["objects"])
    lines = {
        "label": h["label"],
        "configuration": configuration_line(h),
        "events": len(events),
        "entries_per_event": _spread([r["entries"] for r in record]),
        "cells_with_deposit_per_event": _spread([r["cells_hit"] for r in record]),
        "live_cells_per_event": _spread([channels - len(doc["dead_channels"]) for doc in events]),
        "unclustered_cells_per_event": _spread([doc["unclustered_cells"] for doc in events]),
        "components_per_event": _histogram(len(doc["components"]) for doc in events),
        "objects_per_event": _histogram(len(doc["objects"]) for doc in events),
        "object_kinds": kinds,
        "components_with_two_kept_peaks": sum(len(c["peaks"]) >= 2 for doc in events for c in doc["components"]),
        "failed_components": failed,
        "double_count_defects": defects,
        "conservation_max_relative": f"input_sum {worst_input!r} clustered_plus_unclustered {worst_total!r} (against the deposit sum)",
    }
    return gates, lines


def readings(product_path, conversion_path, label: str) -> int:
    from calo_recipe import product
    try:
        read = product.read_product(product_path)
        conv = read_conversion(conversion_path)
    except (product.ProductError, ConversionError) as exc:
        print(f"REFUSED {label} {exc}")
        return EXIT_INVALID
    h = read.header
    if h["format"] != product.FORMAT_LABELLED or h["input"]["sha256"] != conv["cells_sha256"] or h["provenance"] != conv["provenance"]:
        print(f"REFUSED {label} the product is not calo-cluster-product/3 of the readout this conversion record names, with its provenance")
        return EXIT_INVALID
    gates, lines = evaluate(h, read.events, conv)
    for name in sorted(lines):
        print(f"READING {label} {name} {lines[name]}")
    for name in ("label", "events", "double-count", "conservation"):
        print(f"GATE {label} {name} {'PASS' if gates[name] else 'FAIL'}")
    return 0 if all(gates.values()) else EXIT_FAILED


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    c = sub.add_parser("convert", help="zdcsim ROOT file -> labelled readout, identity payloads, conversion record")
    c.add_argument("--root", required=True)
    c.add_argument("--zdcsim-source", required=True, help="the supplied zdcsim.cc, hashed and checked, never copied")
    c.add_argument("--geometry", required=True, help="the geometry file the run used")
    c.add_argument("--sample", required=True, help="the sample file the run used (read after the geometry, as zdcsim does)")
    c.add_argument("--seed", required=True, type=int)
    c.add_argument("--events", required=True, type=int)
    c.add_argument("--physics", required=True)
    c.add_argument("--threads", type=int)
    c.add_argument("--executable", help="the zdcsim binary that ran, hashed into the provenance")
    c.add_argument("--build-record", help="the job's zdcsim-build-record/1 (compiler, Geant4 version, route, command), into the provenance")
    c.add_argument("--out-dir", required=True)
    c.add_argument("--stem", required=True)
    k = sub.add_parser("check-layout", help="read an existing zdcsim file as convert does, writing nothing")
    k.add_argument("--root", required=True)
    k.add_argument("--geometry", required=True)
    k.add_argument("--sample", required=True)
    k.add_argument("--events", required=True, type=int)
    r = sub.add_parser("readings", help="format and bookkeeping readings of a product made from such a readout")
    r.add_argument("--product", required=True)
    r.add_argument("--conversion", required=True)
    r.add_argument("--label", required=True, help="a name for the printed lines")
    args = ap.parse_args(argv)
    if args.operation == "readings":
        return readings(args.product, args.conversion, args.label)
    if args.operation == "check-layout":
        try:
            result = check_layout(root=args.root, geometry=args.geometry, sample=args.sample, events=args.events)
        except ImportError as exc:
            print(json.dumps({"status": "missing-dependency", "reason": f"{exc.name} is not installed"}))
            return EXIT_MISSING
        except ConversionError as exc:
            print(json.dumps({"status": "rejected", "reason": str(exc)}))
            return EXIT_INVALID
        print(json.dumps({"status": "ok", **result}, sort_keys=True))
        return 0
    try:
        files = convert(root=args.root, source=args.zdcsim_source, geometry=args.geometry, sample=args.sample, seed=args.seed,
                        events=args.events, physics=args.physics, threads=args.threads, executable=args.executable,
                        out_dir=args.out_dir, stem=args.stem, build_record=args.build_record)
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", "reason": f"{exc.name} is not installed"}))
        return EXIT_MISSING
    except ConversionError as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return EXIT_INVALID
    print(json.dumps({"status": "ok", "label": LABEL, "events": args.events, "files": files}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
