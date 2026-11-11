#!/usr/bin/env python3
"""reco.light.channel-likelihood/1, the T09 development binding (decisions.md, U12 A): the all-channel photon likelihood and its
fit on a light-readout/1 readout, labelled shared-model closure. --likelihood charge-only (the default: stage 1's charge-only
likelihood, light-likelihood-product/1, unchanged) or charge-time (stage 2's joint charge and first-arrival-time likelihood with
t0, light-likelihood-product/2). A development binding in Python, not a native backend.

Operations (contracts/tool_contracts/photon_likelihood.json):
  fit            readout -> product. Data side: it reads no truth and imports no generator.
  check-product  read a product back, refusing a malformed or incomplete one, recompute ln L and the per-channel probability
                 check of every event from the product alone.

Output: one JSON object on stdout with the status and the reason. Exit 0 ok (fit failures are recorded outcomes, counted in
fit_failures); 1 failed: a live channel's hit and no-hit probabilities do not sum to one at its reported point (the T09 sheet's
stop, and nothing else; status failed with probability_failures above 0; the product is still written and records it);
2 rejected input (status rejected) or an internal error (status error: an unexpected exception, a defect of the recipe, never
the stop), with no product and no partial file written; 3 a missing dependency. The codes are core/status.py's (exit_code of
the status); the JSON status tells the two meanings of exit 2 apart (fix round 2).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
for _entry in (str(PLUGIN), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from core.status import exit_code  # noqa: E402


def report(operation: str, status: str, reason: str, **fields) -> int:
    """Print the run's JSON and return its exit code, core/status.py's for the status."""
    code = exit_code(status)
    print(json.dumps({"operation": operation, "status": status, "reason": reason, "exit_code": code, **fields}, sort_keys=True))
    return code


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    rec = sub.add_parser("fit", help="all-channel likelihood fit of every event of a readout")
    rec.add_argument("--readout", required=True, help="light-readout/1 file, role reconstruction-input")
    rec.add_argument("--product", required=True, help="light-likelihood-product/1 (charge-only) or /2 (charge-time) to write; not written on refusal, never overwritten")
    rec.add_argument("--product-id", required=True, help="the product's identity")
    rec.add_argument("--configuration", help="light-likelihood-configuration/1; default the t09-sphere/1 configuration beside this script")
    rec.add_argument("--likelihood", choices=("charge-only", "charge-time"), default="charge-only",
                     help="charge-only (default; light-likelihood-product/1) or charge-time (joint with the first-arrival time, t0 "
                          "fitted; light-likelihood-product/2)")
    chk = sub.add_parser("check-product", help="read a product back and recompute ln L and the per-channel probability check")
    chk.add_argument("--product", required=True, help="light-likelihood-product/1 or /2 to read")
    chk.add_argument("--configuration", help="the configuration the product was made with; default as for fit")
    return ap


def fit_readout(args) -> int:
    from light_recipe import LABEL, configuration, fit, joint, likelihood, product, readout
    started = time.perf_counter()
    if not Path(args.readout).is_file():
        return report("fit", "rejected", f"no such input file: readout {args.readout}")
    if not args.product_id:
        return report("fit", "rejected", "product id must not be empty")
    target = Path(args.product)
    if target.exists():
        return report("fit", "rejected", f"product file already exists, never overwritten: {target}")
    try:
        cfg = configuration.load(args.configuration)
        rd = readout.read_file(args.readout)
        model = likelihood.Model(cfg)
        if rd.header["threshold"] != cfg.charge_threshold:
            raise readout.ReadoutError(f"the readout's threshold {rd.header['threshold']} is not the configuration's "
                                       f"{cfg.charge_threshold}: hit flag and likelihood must share one threshold model")
        if rd.channels != model.geometry.channels:
            raise readout.ReadoutError(f"{rd.channels} channels in the readout, {model.geometry.channels} in the configuration")
        hit = rd.state == readout.LIVE_HIT
        if (rd.charge[hit] > likelihood.CHARGE_DOMAIN).any():
            raise readout.ReadoutError(f"a hit charge above {likelihood.CHARGE_DOMAIN:g} is outside the model's domain")
        if args.likelihood == "charge-time" and (abs(rd.time[hit]) > joint.TIME_DOMAIN).any():
            raise readout.ReadoutError(f"a hit time beyond +-{joint.TIME_DOMAIN:g} ns is outside the model's domain")
    except (configuration.ConfigurationError, readout.ReadoutError) as exc:
        return report("fit", "rejected", str(exc))
    partial = target.with_name(target.name + ".partial")
    converged = probability_failures = 0
    failures: dict = {}
    try:
        with open(partial, "w", encoding="utf-8") as stream:
            writer = product.Writer(stream, product.header_document(args.product_id, rd, cfg, likelihood=args.likelihood))
            for i in range(rd.events):
                if args.likelihood == "charge-only":
                    event = likelihood.EventData.from_readout(rd, i)
                    start = fit.seed(model, event)
                    res = fit.fit_event(model, event, start)
                    check = product.check_at(model, event, start, res)
                    doc = product.event_document(i, event, start, res, check)
                else:
                    tev = joint.TimedEvent.from_readout(rd, i)
                    start, prefit, origin = fit.joint_seed(model, tev)
                    res = fit.fit_joint_event(model, tev, start)
                    check = product.check_at(model, tev.event, start, res)
                    doc = product.joint_event_document(i, tev, start, origin, prefit, res, check)
                converged += res.status == "converged"
                if res.failure:
                    failures[res.failure] = failures.get(res.failure, 0) + 1
                probability_failures += check["failures"] > 0
                writer.event(doc)
            writer.finish()
        os.replace(partial, target)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        return report("fit", "rejected", f"product cannot be written: {exc.strerror}")
    except Exception as exc:  # noqa: BLE001 - a defect of the recipe: status error, never the stop
        partial.unlink(missing_ok=True)
        return report("fit", "error", f"unexpected {type(exc).__name__}: {exc}")
    fields = {"likelihood": args.likelihood, "events": rd.events, "converged": converged, "fit_failures": dict(sorted(failures.items())),
              "probability_failures": probability_failures, "label": LABEL, "product": str(target), "input_sha256": rd.sha256,
              "configuration_sha256": cfg.sha256, "seconds": round(time.perf_counter() - started, 3)}
    if probability_failures:
        return report("fit", "failed", f"{probability_failures} event(s) with a live channel whose hit and no-hit probabilities "
                                       "do not sum to one (t07-t09-task-sheets.md, T09 stop; recorded in the product)", **fields)
    return report("fit", "ok", "", **fields)


def check_product(args) -> int:
    from light_recipe import configuration, likelihood, product
    if not Path(args.product).is_file():
        return report("check-product", "rejected", f"no such input file: {args.product}")
    try:
        cfg = configuration.load(args.configuration)
        read = product.read_product(args.product, likelihood.Model(cfg), cfg)
    except (configuration.ConfigurationError, product.ProductError) as exc:
        return report("check-product", "rejected", str(exc))
    bad = [doc["event"] for doc in read.events if doc["probability_check"]["failures"] > 0]
    fields = {"format": read.header["format"], "events": len(read.events), "converged": sum(doc["fit"]["status"] == "converged" for doc in read.events),
              "label": read.header["label"], "probability_failures": len(bad), "first_failures": bad[:10]}
    if bad:
        return report("check-product", "failed", "a live channel's hit and no-hit probabilities do not sum to one "
                                                 "(t07-t09-task-sheets.md, T09 stop)", **fields)
    return report("check-product", "ok", "", **fields)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        return report(args.operation, "missing-dependency", f"{exc.name} is not installed")
    try:
        return fit_readout(args) if args.operation == "fit" else check_product(args)
    except Exception as exc:  # noqa: BLE001 - anything the operations did not classify: status error (exit 2), never exit 1
        return report(args.operation, "error", f"unexpected {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main())
