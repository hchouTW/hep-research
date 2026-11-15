#!/usr/bin/env python3
"""Scoring side of T09, D4 build E1: t04-values-v4.md section 9.4's two negative checks [R7] (section 11: required, outside the
budget; section 10: a negative check that does not pass is fail). The recipe never imports this module.

relabel-dead (E1a, "the same 12,000 events, same fit, dead read as unhit"): rewrites a light-readout/1 with every dead channel written as
live-unhit (charge 0, no time, not saturated), touching nothing else, and writes a record (t09-dead-as-unhit/1) that links the source
readout and the relabelled one by their SHA-256. It reads the readout alone: no truth, no generator. The frozen recipe then fits the
relabelled readout unchanged (photon_likelihood.py fit, the main configuration): no recipe file changes for E1a.

fires: the two "fires" rules of section 9.4 as development readings, never a verdict (K09 is not frozen; the E6 harness, not this tool,
will compute the gate):
- dead-as-unhit: fires if at least one of x, y, z, t0 gives |centre| - 1.645 se > 0.10, on the main recipe's multistart product
  (light-likelihood-product/3) of the relabelled dead control;
- single-photon (E1b, "main B4 events, r/R_s [0.4, 0.7), refit with a single-photon density in place of first-arrival"): fires if the t0
  centre gives |centre| - 1.645 se > 0.10, on the variant's product (light-likelihood-product/3-single-photon, single_photon.py).
The centre is section 5.1's robust centre, the 10 % trimmed mean of the pulls (t09_readings.centre); the pull population is section
5.1's, every converged fit with its covariance; failed fits are counted beside it. se: section 5.1's gate se is an event bootstrap of
that statistic in that bin, B = 1,000, seeded from the bin's identity. Here the bootstrap is seeded by SeedSequence([fixture id, block,
stratum]) (fixture ids 9001 main, 9002 dead, as freeze-b-proposal.md section 8.1); E6 fixes the gate's own seeding. The design se
1.03 / sqrt(n) is printed beside it. The truth file must be the check's sample: the dead control (stratum 0), or main stratum 10
(B4, r/R_s [0.4, 0.7)) with every event's N_exp and radius inside that bin; the products must be made from the readouts the truth and
the relabel record name; for dead-as-unhit the tool also reads the source readout, checks its SHA-256 against the truth file's and
recomputes the relabelling from it, whose bytes must have the product's input SHA-256 (the record alone is not trusted). --baseline prints the same centres of the main recipe on the same events (dead masked for E1a; first arrival
for E1b), as context.
Usage: t09_negative_checks.py relabel-dead --readout R --out R2 --record J
       t09_negative_checks.py fires --check {dead-as-unhit,single-photon} --product P --truth T [--relabel-record J --source-readout R] [--baseline P0] --label L
Exit 0 written or read (whatever the reading), 2 refused input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy
from scipy import special

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from light_recipe import LABEL, configuration, multistart, product, readout, single_photon  # noqa: E402
import t09_fixture_files  # noqa: E402
import t09_readings  # noqa: E402

RECORD_FORMAT = "t09-dead-as-unhit/1"
RECORD_ROLE = "scoring-side relabelling: the dead channels of the source readout written as live-unhit, nothing else changed"
TOLERANCE = 0.10              # section 5.1's tolerance on the centre
Z = 1.645                     # 95 %, one-sided, as section 9.4's rules
DESIGN = 1.03                 # section 5.1: design se of the trimmed centre, 1.03 / sqrt(n)
BOOTSTRAP = 1000              # section 5.1: B = 1,000
FIXTURE_IDS = {"main": 9001, "dead": 9002, "saturation": 9003, "two-source": 9004}
B4 = (500.0, 2000.0)          # section 4.3: N_exp bin B4
RADIAL = (0.4, 0.7)           # section 4.3: r/R_s bin
CHECKS = {
    "dead-as-unhit": {"parameters": ("x", "y", "z", "t0"), "fixture": "dead", "stratum": 0, "product": product.FORMAT_MULTISTART,
                      "rule": "any of x, y, z, t0: |centre| - 1.645 se > 0.10", "baseline": "dead masked"},
    "single-photon": {"parameters": ("t0",), "fixture": "main", "stratum": 10, "product": product.FORMAT_SINGLE_PHOTON,
                      "rule": "t0: |centre| - 1.645 se > 0.10", "baseline": "first arrival"},
}


class Refused(ValueError):
    """An input of the check is not the one it reads."""


# --- the rules ----------------------------------------------------------------------------------------------------------------

def fires(centre: float, se: float) -> tuple[float, bool]:
    """Section 9.4: (|centre| - 1.645 se, whether it exceeds 0.10)."""
    value = abs(centre) - Z * se
    return value, bool(value > TOLERANCE)


def threshold_at(n: int) -> float:
    """The |centre| the rule needs at n events with the design se: 0.10 + 1.645 x 1.03 / sqrt(n)."""
    return TOLERANCE + Z * DESIGN / math.sqrt(n)


def first_arrival_shift(mean: float) -> float:
    """E[min of n standard normals | n >= 1] for n ~ Poisson(mean): the first arrival's mean offset, in time spreads (section 9.4's
    closed form: -0.28 at about 1 photon per channel)."""
    x = numpy.linspace(-12.0, 12.0, 24001)
    phi = numpy.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    sf = special.ndtr(-x)
    total, weight, n = 0.0, 0.0, 1
    p = math.exp(-mean) * mean
    while n < 200 and (n < mean or p > 1e-16):
        expect = float(numpy.trapezoid(x * n * phi * sf ** (n - 1), x))
        total += p * expect
        weight += p
        n += 1
        p *= mean / n
    return total / weight


def _trimmed(sorted_rows):
    k = int(0.1 * sorted_rows.shape[-1])
    return sorted_rows[..., k:sorted_rows.shape[-1] - k].mean(axis=-1)


def reading(pulls: dict, check: str, seed: tuple) -> dict:
    """The check's rows: per parameter n, centre, mean, rms, design and bootstrap se, |centre| - 1.645 se (bootstrap), fires; and
    whether any row fires. One event bootstrap for every parameter (the same resampled events), seeded by SeedSequence(seed)."""
    spec = CHECKS[check]
    rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(list(seed))))
    sizes = {numpy.asarray(pulls[name]).size for name in spec["parameters"]}
    if len(sizes) != 1 or 0 in sizes:
        raise Refused("every parameter of the check needs the same, non-zero number of pulls")
    n = sizes.pop()
    index = rng.integers(0, n, size=(BOOTSTRAP, n))
    rows = []
    for name in spec["parameters"]:
        v = numpy.asarray(pulls[name], float)
        boot = _trimmed(numpy.sort(v[index], axis=1))
        se_boot = float(boot.std(ddof=1)) if n > 1 else math.nan
        centre = t09_readings.centre(v)
        value, fired = fires(centre, se_boot)
        rows.append({"name": name, "n": int(n), "centre": centre, "mean": float(v.mean()), "rms": float(math.sqrt((v * v).mean())),
                     "se_design": DESIGN / math.sqrt(n), "se_bootstrap": se_boot, "value": value, "fires": fired})
    return {"check": check, "rows": rows, "fires": any(row["fires"] for row in rows)}


# --- E1a: dead read as unhit ----------------------------------------------------------------------------------------------------

def relabel_dead(rd):
    """(state, charge, time, saturated, relabelled) with every dead channel written live-unhit: charge 0, time NaN, not saturated.
    Every other entry is copied as it is."""
    relabelled = rd.state == readout.DEAD
    state = rd.state.copy()
    charge = rd.charge.copy()
    time_ = rd.time.copy()
    saturated = rd.saturated.copy()
    state[relabelled] = readout.LIVE_UNHIT
    charge[relabelled] = 0.0
    time_[relabelled] = numpy.nan
    saturated[relabelled] = False
    return state, charge, time_, saturated, relabelled


def relabelled_bytes(rd):
    """The relabelled readout's bytes and the relabelled mask; a readout with no dead channel is refused."""
    state, charge, time_, saturated, relabelled = relabel_dead(rd)
    if not relabelled.any():
        raise Refused("the readout has no dead channel: it is not the dead control")
    return readout.readout_bytes(state, charge, time_, saturated, rd.header["threshold"], rd.header["saturation_charge"]), relabelled


def relabel_file(readout_path, out_path, record_path) -> dict:
    out_path, record_path = Path(out_path), Path(record_path)
    for path in (out_path, record_path):
        if path.exists():
            raise Refused(f"{path} exists, never overwritten")
    try:
        rd = readout.read_file(readout_path)
    except readout.ReadoutError as exc:
        raise Refused(f"readout refused: {exc}") from None
    content, relabelled = relabelled_bytes(rd)
    every = numpy.flatnonzero(relabelled.all(axis=0))
    record = {"format": RECORD_FORMAT, "role": RECORD_ROLE, "source_sha256": rd.sha256,
              "relabelled_sha256": hashlib.sha256(content).hexdigest(), "events": rd.events, "channels": rd.channels,
              "relabelled_per_event": [int(c) for c in relabelled.sum(axis=1)], "channels_every_event": [int(c) for c in every],
              "label": LABEL}
    out_path.write_bytes(content)
    record_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return record


def read_record(path) -> dict:
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"relabel record cannot be read: {exc}") from None
    if not isinstance(record, dict) or record.get("format") != RECORD_FORMAT:
        raise Refused(f"not a {RECORD_FORMAT} record")
    return record


# --- the fires readings -------------------------------------------------------------------------------------------------------

def _product(path, check_format, cfg):
    model = single_photon.model_for(cfg)
    try:
        read = product.read_product(path, model, cfg, multistart.load())
    except product.ProductError as exc:
        raise Refused(f"{path}: {exc}") from None
    if read.header["format"] != check_format:
        raise Refused(f"{path} is {read.header['format']}, the check reads {check_format}")
    return read


def _pulls(read, truth, names):
    pulls = {name: [] for name in names}
    failures: dict = {}
    for doc in read.events:
        fit_doc = doc["fit"]
        if fit_doc["status"] != "converged" or fit_doc["uncertainty_status"] != "ok":
            key = fit_doc["failure"] or fit_doc["uncertainty_status"]
            failures[key] = failures.get(key, 0) + 1
            continue
        i = doc["event"]
        values = t09_readings.event_pulls(fit_doc, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i], float(truth["t0"][i]))
        for name in names:
            pulls[name].append(values[name])
    return pulls, failures


def fires_reading(args) -> list:
    spec = CHECKS[args.check]
    try:
        head, truth = t09_fixture_files.read_truth(args.truth)
    except t09_fixture_files.FixtureError as exc:
        raise Refused(str(exc)) from None
    if (head.get("fixture"), head.get("stratum")) != (spec["fixture"], spec["stratum"]):
        raise Refused(f"the truth file is {head.get('fixture')} stratum {head.get('stratum')}; the check reads {spec['fixture']} "
                      f"stratum {spec['stratum']}")
    main_cfg = configuration.load()
    cfg = single_photon.load() if args.check == "single-photon" else main_cfg
    read = _product(args.product, spec["product"], cfg)
    if len(read.events) != head["events"]:
        raise Refused("the product and the truth file hold different event counts")
    source = read.header["input"]["sha256"]
    if args.check == "dead-as-unhit":
        if args.relabel_record is None or args.source_readout is None:
            raise Refused("dead-as-unhit reads the relabel record and the source readout (--relabel-record, --source-readout)")
        record = read_record(args.relabel_record)
        dead = sorted(int(c) for c in truth["dead_channels"])
        if record["source_sha256"] != head["readout_sha256"] or record["relabelled_sha256"] != source:
            raise Refused("the product is not the fit of the relabelled readout of this truth file's readout")
        if record["channels_every_event"] != dead or record["relabelled_per_event"] != [len(dead)] * head["events"]:
            raise Refused("the relabelled channels are not the fixture's dead channels in every event")
        if any(doc["counts"]["dead"] for doc in read.events):
            raise Refused("the product still holds dead channels")
        try:
            source_rd = readout.read_file(args.source_readout)
        except readout.ReadoutError as exc:
            raise Refused(f"source readout refused: {exc}") from None
        if source_rd.sha256 != head["readout_sha256"]:
            raise Refused("the source readout is not this truth file's readout")
        if hashlib.sha256(relabelled_bytes(source_rd)[0]).hexdigest() != source:
            raise Refused("the product's input is not the relabelling of the source readout, recomputed here")
        baseline_source = head["readout_sha256"]
    else:
        if source != head["readout_sha256"]:
            raise Refused("the product was not made from this truth file's readout")
        radius = numpy.linalg.norm(numpy.asarray(truth["vertex"], float), axis=1) / main_cfg.sphere_radius_m
        n_exp = numpy.asarray(truth["n_exp"], float)
        if not (numpy.all((n_exp >= B4[0]) & (n_exp < B4[1])) and numpy.all((radius >= RADIAL[0]) & (radius < RADIAL[1]))):
            raise Refused("an event lies outside main B4, r/R_s [0.4, 0.7)")
        baseline_source = source
    seed = (FIXTURE_IDS[head["fixture"]], int(head["block"]), int(head["stratum"]))
    label, check = args.label, args.check
    pulls, failures = _pulls(read, truth, spec["parameters"])
    out = [f"READING {label} {check} label {LABEL}; development reading on block {head['block']}, not a gate of t04-values-v4.md, no "
           "verdict before K09",
           f"READING {label} {check} format {read.header['format']} configuration {read.header['configuration']['sha256']} input "
           f"{source} events {len(read.events)} with pulls {len(pulls[spec['parameters'][0]])} failed or no covariance "
           f"{sum(failures.values())} by kind {dict(sorted(failures.items()))}"]
    result = reading(pulls, check, seed)
    for row in result["rows"]:
        out.append(f"READING {label} {check} pull {row['name']} centre {row['centre']:+.4f} mean {row['mean']:+.4f} rms {row['rms']:.4f} "
                   f"n {row['n']} se bootstrap {row['se_bootstrap']:.4f} (B {BOOTSTRAP}, SeedSequence({list(seed)})) se design "
                   f"{row['se_design']:.4f} |centre| - 1.645 se {row['value']:+.4f}")
    out.append(f"READING {label} {check} fires rule ({spec['rule']}): {'fires' if result['fires'] else 'does not fire'} on this "
               f"reading; no verdict before K09")
    if args.baseline is not None:
        base = _product(args.baseline, product.FORMAT_MULTISTART, main_cfg)
        if base.header["input"]["sha256"] != baseline_source:
            raise Refused("the baseline was not made from the check's source readout")
        base_pulls, base_failures = _pulls(base, truth, spec["parameters"])
        base_result = reading(base_pulls, check, seed)
        for row in base_result["rows"]:
            out.append(f"READING {label} {check} baseline ({spec['baseline']}) pull {row['name']} centre {row['centre']:+.4f} n {row['n']} "
                       f"se bootstrap {row['se_bootstrap']:.4f} |centre| - 1.645 se {row['value']:+.4f}")
        out.append(f"READING {label} {check} baseline ({spec['baseline']}) failed or no covariance {sum(base_failures.values())}; the rule "
                   f"read on it: {'fires' if base_result['fires'] else 'does not fire'} (context only)")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    rel = sub.add_parser("relabel-dead")
    rel.add_argument("--readout", required=True)
    rel.add_argument("--out", required=True)
    rel.add_argument("--record", required=True)
    fir = sub.add_parser("fires")
    fir.add_argument("--check", required=True, choices=sorted(CHECKS))
    fir.add_argument("--product", required=True)
    fir.add_argument("--truth", required=True)
    fir.add_argument("--relabel-record")
    fir.add_argument("--source-readout")
    fir.add_argument("--baseline")
    fir.add_argument("--label", required=True)
    args = ap.parse_args(argv)
    try:
        if args.operation == "relabel-dead":
            record = relabel_file(args.readout, args.out, args.record)
            print(json.dumps({"status": "ok", **record}, sort_keys=True))
            return 0
        for line in fires_reading(args):
            print(line)
        return 0
    except Refused as exc:
        label = getattr(args, "label", "relabel-dead")
        print(f"REFUSED {label}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
