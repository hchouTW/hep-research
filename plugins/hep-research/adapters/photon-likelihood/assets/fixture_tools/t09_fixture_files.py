#!/usr/bin/env python3
"""Scoring side of T09: hands out t09-sphere/1 events as files (t04-values-v4.md section 3.1, Freeze A amendment 1: the scoring
harness hands out files, so bins and truth stay on its side). The recipe never imports this module or the generator.

The frozen generator gen_t09_sphere.py is called, never edited or copied: its path is given at run time, its SHA-256 must be
the one freeze-a.md records (FROZEN_GENERATOR_SHA256), and it is loaded from that file by importlib. Per stratum this writes:

- <stem>.readout: light-readout/1, role reconstruction-input, built from event["data"] only: state, charge, first time and the
  saturated flag. The header carries the readout's threshold (the generator's THRESHOLD) and its saturation value (the
  generator's CLIP in the saturation control, null otherwise): readout properties, no truth, seed, block, stratum, fixture or
  generator name.
- <stem>.truth.npz: role truth: per event N_exp, vertex, direction, t0 and E_vis, the fixture's dead channels (the generator's
  DEAD_CHANNELS in the dead control, none otherwise), and the SHA-256 of the readout it belongs to.

The main fixture and the dead and saturation controls only: the two-source control waits for the topology stage.
Usage: t09_fixture_files.py --generator GEN --fixture F --block B --stratum S --count N --out-dir DIR --stem STEM
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
FROZEN_GENERATOR_SHA256 = "2657f56bfc1fc7f68a93e205b2c66f80b52018494a78346bcd4e955a9be7da76"
TRUTH_FORMAT = "t09-truth/1"
TRUTH_ROLE = "truth"
FIXTURES = ("main", "dead", "saturation")
DATA_FIELDS = {"state", "charge", "time", "saturated"}


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
    spec = importlib.util.spec_from_file_location("gen_t09_sphere_frozen", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stratum_files(generator, fixture: str, block: int, stratum: int, count: int, out_dir, stem: str) -> dict:
    """Generate `count` events of one stratum and write its readout and truth files. Returns their paths and SHA-256."""
    import numpy
    sys.path.insert(0, str(HERE.parent))
    from light_recipe import readout

    if fixture not in FIXTURES:
        raise FixtureError(f"fixture {fixture!r} is not handed out in this stage ({', '.join(FIXTURES)})")
    if count < 1:
        raise FixtureError("count must be at least 1")
    channels = generator.N_SENSORS
    state = numpy.empty((count, channels), numpy.int8)
    charge = numpy.empty((count, channels))
    time_ = numpy.empty((count, channels))
    saturated = numpy.empty((count, channels), bool)
    truth = {"n_exp": numpy.empty(count), "vertex": numpy.empty((count, 3)), "direction": numpy.empty((count, 3)),
             "t0": numpy.empty(count), "e_vis": numpy.empty(count)}
    for i in range(count):
        ev = generator.event(fixture, block, stratum, i)
        fields, tr = ev["data"], ev["truth"]
        if set(fields) != DATA_FIELDS:
            raise FixtureError(f"event {i}: data fields {sorted(fields)} are not the four this harness hands out")
        if len(tr["n_exp"]) != 1:
            raise FixtureError(f"event {i}: {len(tr['n_exp'])} sources; one source is handed out in this stage")
        # The generator's state codes (UNHIT 0, HIT 1, DEAD 2) are the format's LIVE_UNHIT, LIVE_HIT, DEAD.
        state[i] = numpy.select([fields["state"] == generator.UNHIT, fields["state"] == generator.HIT, fields["state"] == generator.DEAD],
                                [readout.LIVE_UNHIT, readout.LIVE_HIT, readout.DEAD], -1)
        charge[i], time_[i], saturated[i] = fields["charge"], fields["time"], fields["saturated"]
        truth["n_exp"][i], truth["vertex"][i], truth["direction"][i] = tr["n_exp"][0], tr["vertex"][0], tr["direction"][0]
        truth["t0"][i], truth["e_vis"][i] = tr["t0"], tr["e_vis"][0]
    clip = float(generator.CLIP) if fixture == "saturation" else None
    try:
        content = readout.readout_bytes(state, charge, time_, saturated, float(generator.THRESHOLD), clip)
    except readout.ReadoutError as exc:
        raise FixtureError(f"the generator's events do not make a {readout.FORMAT} readout: {exc}") from None
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    readout_path = out_dir / f"{stem}.readout"
    readout_path.write_bytes(content)
    dead = numpy.asarray(generator.DEAD_CHANNELS, numpy.int64) if fixture == "dead" else numpy.zeros(0, numpy.int64)
    header = {"format": TRUTH_FORMAT, "role": TRUTH_ROLE, "generator": generator.GENERATOR, "fixture": fixture, "block": block,
              "stratum": stratum, "events": count, "readout_sha256": hashlib.sha256(content).hexdigest()}
    truth_path = out_dir / f"{stem}.truth.npz"
    with open(truth_path, "wb") as stream:
        numpy.savez(stream, header=numpy.array(json.dumps(header, sort_keys=True)), dead_channels=dead, **truth)
    return {name: {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for name, p in (("readout", readout_path), ("truth", truth_path))}


def read_truth(path) -> tuple[dict, dict]:
    """A t09-truth/1 file: (header, arrays). Refuses any other role, so a data file is never read as truth or the reverse."""
    import numpy
    try:
        with numpy.load(path, allow_pickle=False) as npz:
            arrays = {k: npz[k] for k in npz.files}
    except (OSError, ValueError) as exc:
        raise FixtureError(f"truth file cannot be read: {exc}") from None
    header = json.loads(str(arrays.pop("header")))
    if header.get("format") != TRUTH_FORMAT or header.get("role") != TRUTH_ROLE:
        raise FixtureError("not a t09-truth/1 file of role truth")
    return header, arrays


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--generator", required=True, help="the frozen gen_t09_sphere.py (SHA-256 as freeze-a.md)")
    ap.add_argument("--fixture", required=True, choices=FIXTURES)
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
