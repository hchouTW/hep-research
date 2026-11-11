#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 1: development readings of a light-likelihood-product/1 against its t09-truth/1 file. Readings
only: no reading is compared with a gate of t04-values-v4.md, and none is a quality verdict (K09 is not frozen; Freeze B is
not reached). Every line is labelled shared-model closure.

Two gates, each a property the T09 sheet requires of every channel, not a quality limit:
- the per-channel probability sum (the sheet's stop): every live channel of every event has |P(hit) + P(no hit) - 1| within
  its tolerance, 64 eps (1 + m |ln m|), at its reported point, recomputed from the product (the reader does it);
- dead channels excluded, never unhit: each event's dead channels are exactly the fixture's (the truth file's list; none outside
  the dead control), and no channel is disabled.

Readings: fit counts by failure kind; pulls of the converged fits with an ok covariance, centre (10 % trimmed mean, as
t04-values-v4.md section 5 uses) and width (half the 15.87 % to 84.13 % quantile range), for x, y, z, E_vis and the two
direction components. Direction: residual (d_fit - d_true) . e_k at the truth frame (section 7), its variance from the fitted
tangent covariance projected with J_kj = e_k(truth) . e_j(fit) (case O-direction of the D3 stage 1 report). For a
light-likelihood-product/2 (the joint charge-time fit, D3 stage 2) or /3 (its multistart fit, D3 stage 3) the t0 pull too,
(t0_fit - t0_true) / sigma(t0).
Usage: t09_readings.py --product P --truth T --label L. Exit 0 both gates pass, 1 a gate fails, 2 refused input.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from light_recipe import LABEL, configuration, likelihood, product  # noqa: E402
from light_recipe.likelihood import frame  # noqa: E402
import t09_fixture_files  # noqa: E402

PULL_NAMES = ("x", "y", "z", "u1", "u2", "e_vis")
PULL_NAMES_JOINT = PULL_NAMES + ("t0",)
QUANTILES = (0.158655, 0.841345)


def centre(values) -> float:
    v = numpy.sort(numpy.asarray(values, float))
    k = int(0.1 * v.size)
    return float(v[k:v.size - k].mean())


def width(values) -> float:
    lo, hi = numpy.quantile(numpy.asarray(values, float), QUANTILES)
    return float((hi - lo) / 2)


def event_pulls(fit_doc: dict, truth_vertex, truth_direction, truth_e_vis, truth_t0=None) -> dict:
    cov = numpy.array(fit_doc["covariance"], float)
    sigma = numpy.sqrt(numpy.diag(cov))
    vertex = numpy.array(fit_doc["vertex"], float)
    out = {name: float((vertex[k] - truth_vertex[k]) / sigma[k]) for k, name in enumerate(("x", "y", "z"))}
    out["e_vis"] = float((fit_doc["e_vis"] - truth_e_vis) / sigma[5])
    d_fit = numpy.array(fit_doc["direction"], float)
    t1, t2 = frame(numpy.asarray(truth_direction, float))
    f1, f2 = numpy.array(fit_doc["frame"]["e1"]), numpy.array(fit_doc["frame"]["e2"])
    jac = numpy.array([[t1 @ f1, t1 @ f2], [t2 @ f1, t2 @ f2]])
    tangent = jac @ cov[3:5, 3:5] @ jac.T
    for name, axis, k in (("u1", t1, 0), ("u2", t2, 1)):
        out[name] = float((d_fit - truth_direction) @ axis / math.sqrt(tangent[k, k]))
    if truth_t0 is not None:
        out["t0"] = float((fit_doc["t0"] - truth_t0) / sigma[6])
    return out


def dead_state_defects(event_docs, dead_channels) -> list:
    want = sorted(int(c) for c in dead_channels)
    defects = []
    for doc in event_docs:
        states = doc["states"]
        dead = [i for i, s in enumerate(states) if s == "D"]
        if dead != want:
            missing = sorted(set(want) - set(dead))
            defects.append(f"event {doc['event']}: dead channels {len(dead)}, the fixture's {len(want)}; "
                           f"fixture-dead read as {sorted({states[i] for i in missing})}" if missing else
                           f"event {doc['event']}: {len(dead)} dead channels, the fixture's {len(want)}")
        if "X" in states:
            defects.append(f"event {doc['event']}: a disabled channel, which this fixture does not define")
    return defects


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--product", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--label", required=True)
    args = ap.parse_args(argv)
    label = args.label
    try:
        cfg = configuration.load()
        read = product.read_product(args.product, likelihood.Model(cfg), cfg)
        head, truth = t09_fixture_files.read_truth(args.truth)
    except (product.ProductError, t09_fixture_files.FixtureError, configuration.ConfigurationError) as exc:
        print(f"REFUSED {label}: {exc}")
        return 2
    if head["readout_sha256"] != read.header["input"]["sha256"] or head["events"] != len(read.events):
        print(f"REFUSED {label}: the truth file belongs to another readout")
        return 2
    events = read.events
    timed = read.header["format"] in (product.FORMAT_JOINT, product.FORMAT_MULTISTART)
    names = PULL_NAMES_JOINT if timed else PULL_NAMES
    print(f"READING {label} format {read.header['format']}")
    print(f"READING {label} label {LABEL}; development reading, no gate of t04-values-v4.md, no quality verdict")
    failures: dict = {}
    pulls = {name: [] for name in names}
    for doc in events:
        fit_doc = doc["fit"]
        if fit_doc["status"] != "converged":
            failures[fit_doc["failure"]] = failures.get(fit_doc["failure"], 0) + 1
            continue
        i = doc["event"]
        for name, value in event_pulls(fit_doc, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i],
                                       float(truth["t0"][i]) if timed else None).items():
            pulls[name].append(value)
    converged = len(events) - sum(failures.values())
    print(f"READING {label} fits events {len(events)} converged {converged} failed {sum(failures.values())} "
          f"by kind {dict(sorted(failures.items()))}")
    for name in names:
        v = numpy.array(pulls[name])
        if v.size:
            print(f"READING {label} pull {name} centre {centre(v):+.4f} width {width(v):.4f} n {v.size} "
                  f"largest |pull| {numpy.abs(v).max():.2f}")
        else:
            print(f"READING {label} pull {name} no converged fit")
    iterations = [doc["fit"]["iterations"] for doc in events]
    print(f"READING {label} iterations median {numpy.median(iterations):.0f} largest {max(iterations)}; hit channels median "
          f"{numpy.median([doc['counts']['hit'] for doc in events]):.0f}; saturated channels mean "
          f"{numpy.mean([doc['counts']['saturated'] for doc in events]):.3f}")
    channels = sum(doc["probability_check"]["channels"] for doc in events)
    bad = sum(doc["probability_check"]["failures"] for doc in events)
    largest = max(doc["probability_check"]["max_abs_deviation"] for doc in events)
    ratio = max(doc["probability_check"]["largest_ratio"] for doc in events)
    ok_sum = bad == 0
    print(f"GATE {label} per-channel probability sum (T09 stop): channels {channels}, failures {bad}, largest deviation "
          f"{largest:.3e}, largest deviation over tolerance {ratio:.3e}, tolerance {read.header['probability_check']['tolerance']}: "
          f"{'PASS' if ok_sum else 'FAIL'}")
    defects = dead_state_defects(events, truth["dead_channels"])
    for line in defects[:10]:
        print(f"DEFECT {label} {line}")
    print(f"GATE {label} dead channels excluded, never unhit: events {len(events)}, fixture dead channels "
          f"{len(truth['dead_channels'])}, defects {len(defects)}: {'PASS' if not defects else 'FAIL'}")
    return 0 if ok_sum and not defects else 1


if __name__ == "__main__":
    sys.exit(main())
