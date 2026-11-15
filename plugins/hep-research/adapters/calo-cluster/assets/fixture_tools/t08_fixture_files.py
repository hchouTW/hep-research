#!/usr/bin/env python3
"""Scoring side of T08: hands out t08-grid/1 events as files (t04-values-v4.md section 3.1, Freeze A amendment 1: the scoring
harness hands out files, so bins and truth stay on its side). The recipe never imports this module or the generator.

The frozen generator gen_t08_grid.py is called, never edited or copied: its path is given at run time, its SHA-256 must be the
one freeze-a.md records (FROZEN_GENERATOR_SHA256), and it is loaded from that file by importlib. Per stratum this writes:

- <stem>.cells: calo-cells/1, role reconstruction-input, built from event["data"] only: raw, live, saturated. No truth,
  seed, block, stratum, fixture or generator field (the format's header has a fixed key set).
- <stem>.pedestal.json and <stem>.gain.json: calo-calibration-payload/1, from event["data"]'s pedestal and gain, which the
  fixture holds as separate fields (section 4.2). Their role in the chain is the generator's: raw = value / gain + pedestal, so
  e_c = gain (raw - pedestal) and the gain multiplies (freeze-a.md, choices, row 11). The gain payload is derived against the
  pedestal payload. Origin nominal: these are the fixture's constants, not a measurement (R31).
- <stem>.truth.npz: role truth, the event's truth fields and, per event, the saturation control's truth-side reference
  sum_c min(E g_c(x, y), 400 MeV) (section 9.2), with the SHA-256 of the cells file it belongs to.

Usage: t08_fixture_files.py --generator GEN --fixture F --block B --stratum S --count N --out-dir DIR --stem STEM
Exit 0 written, 2 refused input (a wrong generator hash included), 3 numpy missing.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN_GENERATOR_SHA256 = "d901362c62431282ce37eeaac88efb864339aec9eb6915aa9e7d69808f7946f9"
TRUTH_FORMAT = "t08-truth/1"
TRUTH_ROLE = "truth"
MAX_SHOWERS = 2
PEDESTAL_SOURCE = "t08-grid/1 fixture constant: pedestal, kept as its own field (t04-values-v4.md section 4.2)"
GAIN_SOURCE = "t08-grid/1 fixture constant: gain, kept as its own field; raw = value / gain + pedestal, so the gain multiplies"


class FixtureError(ValueError):
    """Refused: the generator or a fixture argument."""


def load_generator(path):
    path = Path(path)
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise FixtureError(f"generator cannot be read: {exc.strerror}") from None
    digest = hashlib.sha256(content).hexdigest()
    if digest != FROZEN_GENERATOR_SHA256:
        raise FixtureError(f"generator SHA-256 {digest} is not the frozen {FROZEN_GENERATOR_SHA256} (freeze-a.md)")
    spec = importlib.util.spec_from_file_location("gen_t08_grid_frozen", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stratum_files(generator, fixture: str, block: int, stratum: int, count: int, out_dir, stem: str) -> dict:
    """Generate `count` events of one stratum and write its four files. Returns their paths and SHA-256."""
    import numpy
    sys.path.insert(0, str(HERE.parent))
    from calo_recipe import cell_input

    if count < 1:
        raise FixtureError("count must be at least 1")
    shape = (count, generator.N_CELLS, generator.N_CELLS)
    raw = numpy.empty(shape)
    live = numpy.empty(shape, bool)
    saturated = numpy.empty(shape, bool)
    truth = {"energy_mev": numpy.empty(count), "n_showers": numpy.empty(count, int),
             "showers": numpy.full((count, MAX_SHOWERS, 2), numpy.nan), "d": numpy.full(count, numpy.nan),
             "azimuth": numpy.full(count, numpy.nan), "t": numpy.full(count, numpy.nan), "f_dead": numpy.full(count, numpy.nan),
             "deposit": numpy.zeros((count, MAX_SHOWERS, generator.N_CELLS, generator.N_CELLS)),
             "clip_reference_mev": numpy.full(count, numpy.nan), "energy_bin": numpy.empty(count, int)}
    separation = None
    pedestal = gain = None
    for i in range(count):
        ev = generator.event(fixture, block, stratum, i)
        readout, tr = ev["data"], ev["truth"]
        if set(readout) != {"raw", "pedestal", "gain", "live", "saturated"}:
            raise FixtureError(f"event {i}: data fields {sorted(readout)} are not the five this harness hands out")
        if pedestal is None:
            pedestal, gain = float(readout["pedestal"]), float(readout["gain"])
        elif (float(readout["pedestal"]), float(readout["gain"])) != (pedestal, gain):
            raise FixtureError("pedestal or gain differs between events of one stratum; one payload per file assumes they do not")
        raw[i], live[i], saturated[i] = readout["raw"], readout["live"], readout["saturated"]
        separation = tr["separation"]
        n = len(tr["showers"])
        truth["energy_mev"][i], truth["n_showers"][i], truth["energy_bin"][i] = tr["energy_mev"], n, tr["energy_bin"]
        truth["showers"][i, :n] = tr["showers"]
        truth["deposit"][i, :n] = tr["deposit"]
        for key in ("d", "azimuth", "t", "f_dead"):
            if tr[key] is not None:
                truth[key][i] = tr[key]
        if fixture == "saturation":
            x, y = tr["showers"][0]
            truth["clip_reference_mev"][i] = float(numpy.minimum(tr["energy_mev"] * generator.cell_profile(x, y), generator.CLIP_MEV).sum())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cells_path = out_dir / f"{stem}.cells"
    cells = cell_input.cells_bytes(raw, live, saturated)
    cells_path.write_bytes(cells)
    channels = generator.N_CELLS * generator.N_CELLS
    ped_bytes = cell_input.payload_bytes("pedestal", "subtract", pedestal, channels, "adc", "nominal", PEDESTAL_SOURCE)
    ped_path = out_dir / f"{stem}.pedestal.json"
    ped_path.write_bytes(ped_bytes)
    gain_bytes = cell_input.payload_bytes("gain", "multiply", gain, channels, "MeV/adc", "nominal", GAIN_SOURCE,
                                          derived_against=[hashlib.sha256(ped_bytes).hexdigest()])
    gain_path = out_dir / f"{stem}.gain.json"
    gain_path.write_bytes(gain_bytes)
    header = {"format": TRUTH_FORMAT, "role": TRUTH_ROLE, "generator": generator.GENERATOR, "fixture": fixture, "block": block,
              "stratum": stratum, "separation": separation, "events": count, "cells_sha256": hashlib.sha256(cells).hexdigest()}
    truth_path = out_dir / f"{stem}.truth.npz"
    with open(truth_path, "wb") as stream:
        numpy.savez(stream, header=numpy.array(json.dumps(header, sort_keys=True)), **truth)
    return {name: {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for name, p in (("cells", cells_path), ("pedestal", ped_path), ("gain", gain_path), ("truth", truth_path))}


def read_truth(path) -> tuple[dict, dict]:
    """A t08-truth/1 file: (header, arrays). Refuses any other role, so a data file is never read as truth or the reverse."""
    import numpy
    try:
        with numpy.load(path, allow_pickle=False) as npz:
            arrays = {k: npz[k] for k in npz.files}
    except (OSError, ValueError) as exc:
        raise FixtureError(f"truth file cannot be read: {exc}") from None
    header = json.loads(str(arrays.pop("header")))
    if header.get("format") != TRUTH_FORMAT or header.get("role") != TRUTH_ROLE:
        raise FixtureError("not a t08-truth/1 file of role truth")
    return header, arrays


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--generator", required=True, help="the frozen gen_t08_grid.py (SHA-256 as freeze-a.md)")
    ap.add_argument("--fixture", required=True, choices=("main", "edge", "dead", "saturation"))
    ap.add_argument("--block", required=True, type=int)
    ap.add_argument("--stratum", required=True, type=int)
    ap.add_argument("--count", required=True, type=int)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--stem", required=True)
    args = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "missing-dependency", "reason": "numpy is not installed"}))
        return 3
    try:
        generator = load_generator(args.generator)
        files = stratum_files(generator, args.fixture, args.block, args.stratum, args.count, args.out_dir, args.stem)
    except (FixtureError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2
    print(json.dumps({"status": "ok", "fixture": args.fixture, "block": args.block, "stratum": args.stratum, "events": args.count,
                      "files": files}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
