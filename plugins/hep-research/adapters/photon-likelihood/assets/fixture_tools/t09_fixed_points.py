#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 2: t04-values-v4.md section 9.3's two deterministic checks at section 7's fixed likelihood points
(cases O-fixed-data, O-agreement and O-fixed-sum of the D3 stage 2 report). Gates, not readings; shared-model closure.

The 50 fixed points are the frozen generator's likelihood_points() (block 6, reserved stratum 100; freeze-a.md row 18); the
generator is loaded by t09_fixture_files.load_generator, which checks its SHA-256 against freeze-a.md's. At point k the data are
block 6 events of the generator, handed through the light-readout/1 format: main stratum k mod 12 (the point's own N_exp and
radial bin), event k; the dead control, stratum 0, event k; the saturation control, stratum 0, event k. Each is evaluated at the
point's (vertex, direction, E_vis, t0).

- GATE likelihood check, joint: |ln L_recipe - ln L_independent| <= 1e-9, absolute, for the joint charge-time ln L of every
  evaluation (150), the independent evaluation being t09_independent_likelihood, which shares no code with the recipe.
- GATE likelihood check, charge-only: the same for the charge-only ln L (the stage 1 path).
- GATE per-channel sum: at every point, every channel's mean count m_i (all 1,000; the sum depends on m_i alone) has
  |P(hit) + P(no hit) - 1| within stage 1's tolerance 64 eps (1 + m |ln m|). A failure is the T09 sheet's stop.

Usage: t09_fixed_points.py --generator GEN. Exit codes are core/status.py's: 0 every gate passes (ok), 1 a gate fails (failed),
2 refused input, a generator that is not the frozen one included (rejected), or an unexpected exception (error: an ERROR line,
never read as a gate failing; review F5).
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
for _entry in (str(PLUGIN), str(HERE.parent), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import numpy  # noqa: E402

from core.status import exit_code  # noqa: E402

from light_recipe import LABEL, configuration, joint, light_model, likelihood, readout  # noqa: E402
import t09_fixture_files  # noqa: E402
import t09_independent_likelihood as independent  # noqa: E402

AGREEMENT = 1e-9
BLOCK = 6
CONTROLS = ("dead", "saturation")


def timed_event(generator, fixture: str, stratum: int, index: int):
    """One block 6 event through the readout format (its own refusing writer and reader), as the recipe sees an input."""
    fields = generator.event(fixture, BLOCK, stratum, index)["data"]
    state = numpy.select([fields["state"] == generator.UNHIT, fields["state"] == generator.HIT, fields["state"] == generator.DEAD],
                         [readout.LIVE_UNHIT, readout.LIVE_HIT, readout.DEAD], -1).astype(numpy.int8)
    clip = float(generator.CLIP) if fixture == "saturation" else None
    content = readout.readout_bytes(state[None, :], numpy.asarray(fields["charge"], float)[None, :],
                                    numpy.asarray(fields["time"], float)[None, :], numpy.asarray(fields["saturated"], bool)[None, :],
                                    float(generator.THRESHOLD), clip)
    return joint.TimedEvent.from_readout(readout.read_bytes(content), 0)


def run(generator, out=sys.stdout) -> int:
    cfg = configuration.load()
    model = likelihood.Model(cfg)
    points = generator.likelihood_points()
    worst_joint = worst_charge = worst_channel = 0.0
    bad_joint = bad_charge = 0
    sum_channels = sum_failures = 0
    largest_ratio = 0.0
    evaluations = 0
    started = time.perf_counter()
    for k, point in enumerate(points):
        vertex, direction = numpy.asarray(point["vertex"], float), numpy.asarray(point["direction"], float)
        e_vis, t0 = float(point["e_vis"]), float(point["t0"])
        m = model.scale * e_vis * light_model.shape(model, vertex, direction / numpy.linalg.norm(direction)) + model.dark
        p_hit, p_no = model.response.probability_sums(m)
        ratio = numpy.abs(p_hit + p_no - 1.0) / likelihood.sum_tolerance(m)
        sum_channels += m.size
        sum_failures += int((~(ratio <= 1.0)).sum())
        largest_ratio = max(largest_ratio, float(ratio.max()))
        for fixture, stratum in (("main", k % 12),) + tuple((c, 0) for c in CONTROLS):
            tev = timed_event(generator, fixture, stratum, k)
            ev = tev.event
            recipe_joint = joint.log_likelihood(model, tev, vertex, direction, e_vis, t0)
            recipe_charge = likelihood.log_likelihood(model, ev, vertex, direction, e_vis)
            ind = independent.evaluate([int(s) for s in ev.state], [float(c) for c in ev.charge], [float(t) for t in tev.time],
                                       [bool(s) for s in ev.saturated], ev.saturation_charge, [float(c) for c in vertex],
                                       [float(c) for c in direction], e_vis, t0)
            delay, _, _ = joint.arrival_delays(model, vertex)
            mu = model.scale * e_vis * light_model.shape(model, vertex, direction / numpy.linalg.norm(direction))
            terms = joint.channel_terms(model, tev, mu, t0 + delay)[0]
            channel_gap = float(numpy.abs(terms - numpy.array(ind["joint_terms"])).max())
            d_joint, d_charge = abs(recipe_joint - ind["joint"]), abs(recipe_charge - ind["charge_only"])
            if not (math.isfinite(recipe_joint) and d_joint <= AGREEMENT):
                bad_joint += 1
            if not (math.isfinite(recipe_charge) and d_charge <= AGREEMENT):
                bad_charge += 1
            worst_joint, worst_charge, worst_channel = max(worst_joint, d_joint), max(worst_charge, d_charge), max(worst_channel, channel_gap)
            evaluations += 1
            print(f"POINT {k} {fixture} stratum {stratum} event {k}: ln L joint {recipe_joint:.12e} independent {ind['joint']:.12e} "
                  f"|diff| {d_joint:.3e}; charge-only {recipe_charge:.12e} |diff| {d_charge:.3e}; largest per-channel |diff| "
                  f"{channel_gap:.3e}; hit {int(ev.hit.sum())} saturated {int(ev.saturated.sum())} dead {int(ev.dead.sum())}",
                  file=out, flush=True)
    print(f"READING fixed points {len(points)}, evaluations {evaluations}, label {LABEL}, {time.perf_counter() - started:.1f} s", file=out)
    print(f"GATE likelihood check, joint (v4 9.3): evaluations {evaluations}, failures {bad_joint}, largest |diff| {worst_joint:.3e}, "
          f"largest per-channel |diff| {worst_channel:.3e}, limit {AGREEMENT:g} absolute: {'PASS' if bad_joint == 0 else 'FAIL'}", file=out)
    print(f"GATE likelihood check, charge-only (v4 9.3): evaluations {evaluations}, failures {bad_charge}, largest |diff| "
          f"{worst_charge:.3e}, limit {AGREEMENT:g} absolute: {'PASS' if bad_charge == 0 else 'FAIL'}", file=out)
    print(f"GATE per-channel sum at the fixed points (v4 9.3, the T09 stop): points {len(points)}, channels {sum_channels}, failures "
          f"{sum_failures}, largest deviation over tolerance {largest_ratio:.3e}: {'PASS' if sum_failures == 0 else 'FAIL'}", file=out)
    return exit_code("ok" if bad_joint == 0 and bad_charge == 0 and sum_failures == 0 else "failed")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--generator", required=True, help="the frozen gen_t09_sphere.py (SHA-256 as freeze-a.md)")
    args = ap.parse_args(argv)
    try:
        generator = t09_fixture_files.load_generator(args.generator)
    except t09_fixture_files.FixtureError as exc:
        print(f"REFUSED fixed points: {exc}")
        return exit_code("rejected")
    try:
        return run(generator)
    except Exception as exc:  # noqa: BLE001 - a defect of the recipe or the driver: status error, never a gate failing
        print(f"ERROR fixed points: unexpected {type(exc).__name__}: {exc}", flush=True)
        return exit_code("error")


if __name__ == "__main__":
    sys.exit(main())
