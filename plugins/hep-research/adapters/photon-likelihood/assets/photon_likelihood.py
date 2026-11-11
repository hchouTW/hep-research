#!/usr/bin/env python3
"""reco.light.channel-likelihood/1, the T09 development binding (decisions.md, U12 A): the all-channel photon likelihood and its
fit on a light-readout/1 readout, labelled shared-model closure. --likelihood charge-only (the default: stage 1's charge-only
likelihood, light-likelihood-product/1, unchanged) or charge-time (stage 2's joint charge and first-arrival-time likelihood with
t0, light-likelihood-product/2). --starts one (the default: stage 2's one joint start) or multistart (charge-time only, D3
stage 3: the budget file's starts, the best converged one reported, every start recorded, light-likelihood-product/3; --budget,
default the t09-multistart-1 budget beside this script). topology (D3 stage 4): from a readout and its multistart product /3, the two-source hypothesis H2
(both sources' light summed per channel, each source its own t0, the starts of the topology budget) and the choice of t04-values-v4.md
section 7 (H2 if and only if 2 (lnL_2 - lnL_1) >= 30), light-likelihood-product/4; H1 is read from the /3, never refitted. A
development binding in Python, not a native backend.

Operations (contracts/tool_contracts/photon_likelihood.json):
  fit            readout -> product. Data side: it reads no truth and imports no generator.
  check-product  read a product back, refusing a malformed or incomplete one, recompute ln L and the per-channel probability
                 check of every event from the product alone.
  topology       readout and its /3 product -> product /4. Data side: it reads the readout and the recipe's own product only.

Output: one JSON object on stdout with the status and the reason. Exit 0 ok (fit failures are recorded outcomes, counted in
fit_failures); 1 failed: a live channel's hit and no-hit probabilities do not sum to one at its reported point (the T09 sheet's
stop, and nothing else, at an H1 or, for topology, an H2 point; status failed with probability_failures above 0; the product
is still written and records it);
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
    rec.add_argument("--starts", choices=("one", "multistart"), default="one",
                     help="one (default; stage 2's one joint start) or multistart (charge-time only: the budget's starts, every one "
                          "recorded; light-likelihood-product/3)")
    rec.add_argument("--budget", help="light-likelihood-multistart/1 budget for --starts multistart; default the t09-multistart-1 "
                                      "budget beside this script")
    chk = sub.add_parser("check-product", help="read a product back and recompute ln L and the per-channel probability check")
    chk.add_argument("--product", required=True, help="light-likelihood-product/1, /2, /3 or /4 to read")
    chk.add_argument("--configuration", help="the configuration the product was made with; default as for fit")
    chk.add_argument("--budget", help="the multistart budget a /3 or /4 product was made with (read for /3 and /4 only); default as for fit")
    chk.add_argument("--topology-budget", help="the topology budget a /4 product was made with (read for /4 only); default the "
                                               "t09-topology-2 budget beside this script")
    top = sub.add_parser("topology", help="the two-source hypothesis H2 and the topology choice of every event of a readout, H1 from its /3")
    top.add_argument("--readout", required=True, help="light-readout/1 file, role reconstruction-input, the one the /3 was made from")
    top.add_argument("--h1-product", required=True, help="the light-likelihood-product/3 (multistart) of that readout")
    top.add_argument("--product", required=True, help="light-likelihood-product/4 to write; not written on refusal, never overwritten")
    top.add_argument("--product-id", required=True, help="the product's identity")
    top.add_argument("--configuration", help="as for fit")
    top.add_argument("--budget", help="the multistart budget the /3 was made with; default as for fit")
    top.add_argument("--topology-budget", help="light-likelihood-topology/1 budget of H2's starts; default the t09-topology-2 budget "
                                               "beside this script")
    return ap


def fit_readout(args) -> int:
    from light_recipe import LABEL, configuration, fit, joint, likelihood, multistart, product, readout
    started = time.perf_counter()
    if not Path(args.readout).is_file():
        return report("fit", "rejected", f"no such input file: readout {args.readout}")
    if not args.product_id:
        return report("fit", "rejected", "product id must not be empty")
    target = Path(args.product)
    if target.exists():
        return report("fit", "rejected", f"product file already exists, never overwritten: {target}")
    if args.starts == "multistart" and args.likelihood != "charge-time":
        return report("fit", "rejected", "--starts multistart needs --likelihood charge-time")
    try:
        cfg = configuration.load(args.configuration)
        budget = multistart.load(args.budget) if args.starts == "multistart" else None
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
    except (configuration.ConfigurationError, multistart.BudgetError, readout.ReadoutError) as exc:
        return report("fit", "rejected", str(exc))
    partial = target.with_name(target.name + ".partial")
    converged = probability_failures = 0
    failures: dict = {}
    try:
        with open(partial, "w", encoding="utf-8") as stream:
            writer = product.Writer(stream, product.header_document(args.product_id, rd, cfg, likelihood=args.likelihood, budget=budget))
            for i in range(rd.events):
                if args.likelihood == "charge-only":
                    event = likelihood.EventData.from_readout(rd, i)
                    start = fit.seed(model, event)
                    res = fit.fit_event(model, event, start)
                    check = product.check_at(model, event, start, res)
                    doc = product.event_document(i, event, start, res, check)
                elif budget is not None:
                    tev = joint.TimedEvent.from_readout(rd, i)
                    ms = multistart.fit_multistart(model, tev, budget)
                    res = ms.result
                    check = product.check_at(model, tev.event, ms.anchor, res)
                    doc = product.multistart_event_document(i, tev, ms, check)
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
    fields = {"likelihood": args.likelihood, "starts": args.starts, "budget_sha256": None if budget is None else budget.sha256,
              "events": rd.events, "converged": converged, "fit_failures": dict(sorted(failures.items())),
              "probability_failures": probability_failures, "label": LABEL, "product": str(target), "input_sha256": rd.sha256,
              "configuration_sha256": cfg.sha256, "seconds": round(time.perf_counter() - started, 3)}
    if probability_failures:
        return report("fit", "failed", f"{probability_failures} event(s) with a live channel whose hit and no-hit probabilities "
                                       "do not sum to one (t07-t09-task-sheets.md, T09 stop; recorded in the product)", **fields)
    return report("fit", "ok", "", **fields)


def _event_probability_failure(doc) -> bool:
    """A live channel off the sum at the event's H1 point or, in /4, at its H2 point."""
    h2 = doc.get("topology", {}).get("probability_check") if isinstance(doc.get("topology"), dict) else None
    return doc["probability_check"]["failures"] > 0 or (h2 is not None and h2["failures"] > 0)


def check_product(args) -> int:
    from light_recipe import configuration, likelihood, multistart, product, topology
    if not Path(args.product).is_file():
        return report("check-product", "rejected", f"no such input file: {args.product}")
    try:
        cfg = configuration.load(args.configuration)
        kind = product.format_of(args.product)
        budget = multistart.load(args.budget) if kind in (product.FORMAT_MULTISTART, product.FORMAT_TOPOLOGY) else None
        topology_budget = topology.load(args.topology_budget) if kind == product.FORMAT_TOPOLOGY else None
        read = product.read_product(args.product, likelihood.Model(cfg), cfg, budget, topology_budget)
    except (configuration.ConfigurationError, multistart.BudgetError, topology.BudgetError, product.ProductError) as exc:
        return report("check-product", "rejected", str(exc))
    bad = [doc["event"] for doc in read.events if _event_probability_failure(doc)]
    fields = {"format": read.header["format"], "events": len(read.events), "converged": sum(doc["fit"]["status"] == "converged" for doc in read.events),
              "label": read.header["label"], "probability_failures": len(bad), "first_failures": bad[:10]}
    if bad:
        return report("check-product", "failed", "a live channel's hit and no-hit probabilities do not sum to one "
                                                 "(t07-t09-task-sheets.md, T09 stop)", **fields)
    return report("check-product", "ok", "", **fields)


def topology_readout(args) -> int:
    import hashlib
    from light_recipe import LABEL, configuration, joint, likelihood, multistart, product, readout, topology
    started = time.perf_counter()
    for name, path in (("readout", args.readout), ("H1 product", args.h1_product)):
        if not Path(path).is_file():
            return report("topology", "rejected", f"no such input file: {name} {path}")
    if not args.product_id:
        return report("topology", "rejected", "product id must not be empty")
    target = Path(args.product)
    if target.exists():
        return report("topology", "rejected", f"product file already exists, never overwritten: {target}")
    try:
        cfg = configuration.load(args.configuration)
        budget = multistart.load(args.budget)
        topology_budget = topology.load(args.topology_budget)
        rd = readout.read_file(args.readout)
        model = likelihood.Model(cfg)
        if rd.header["threshold"] != cfg.charge_threshold:
            raise readout.ReadoutError(f"the readout's threshold {rd.header['threshold']} is not the configuration's "
                                       f"{cfg.charge_threshold}: hit flag and likelihood must share one threshold model")
        if rd.channels != model.geometry.channels:
            raise readout.ReadoutError(f"{rd.channels} channels in the readout, {model.geometry.channels} in the configuration")
        if product.format_of(args.h1_product) != product.FORMAT_MULTISTART:
            raise product.ProductError(f"the H1 product must be {product.FORMAT_MULTISTART}, the multistart fit")
        content = Path(args.h1_product).read_bytes()
        h1 = product.read_text(content.decode("utf-8"), model, cfg, budget)
        if h1.header["input"]["sha256"] != rd.sha256 or len(h1.events) != rd.events:
            raise product.ProductError("the H1 product was made from another readout")
    except (configuration.ConfigurationError, multistart.BudgetError, topology.BudgetError, readout.ReadoutError,
            product.ProductError, UnicodeDecodeError) as exc:
        return report("topology", "rejected", str(exc))
    h1_sha256 = hashlib.sha256(content).hexdigest()
    partial = target.with_name(target.name + ".partial")
    choices: dict = {}
    h2_outcomes: dict = {}
    probability_failures = 0
    try:
        with open(partial, "w", encoding="utf-8") as stream:
            writer = product.Writer(stream, product.topology_header_document(h1.header, h1_sha256, args.product_id, topology_budget))
            for i, doc in enumerate(h1.events):
                tev = joint.TimedEvent.from_readout(rd, i)
                topo = topology.fit_topology(model, tev, topology_budget, product.fit_result_of(doc["fit"]))
                check = topology.check_at(model, tev.event, topo)
                event = product.topology_event_document(doc, topo, check)
                key = "none" if topo.choice is None else topo.choice
                choices[key] = choices.get(key, 0) + 1
                for rec in topo.records:
                    outcome = rec.result.failure or "converged"
                    h2_outcomes[outcome] = h2_outcomes.get(outcome, 0) + 1
                probability_failures += _event_probability_failure(event)
                writer.event(event)
            writer.finish()
        os.replace(partial, target)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        return report("topology", "rejected", f"product cannot be written: {exc.strerror}")
    except Exception as exc:  # noqa: BLE001 - a defect of the recipe: status error, never the stop
        partial.unlink(missing_ok=True)
        return report("topology", "error", f"unexpected {type(exc).__name__}: {exc}")
    fields = {"events": rd.events, "choices": dict(sorted(choices.items())), "h2_starts": dict(sorted(h2_outcomes.items())),
              "penalty": topology.PENALTY, "topology_budget_sha256": topology_budget.sha256, "h1_product_sha256": h1_sha256,
              "probability_failures": probability_failures, "label": LABEL, "product": str(target), "input_sha256": rd.sha256,
              "configuration_sha256": cfg.sha256, "seconds": round(time.perf_counter() - started, 3)}
    if probability_failures:
        return report("topology", "failed", f"{probability_failures} event(s) with a live channel whose hit and no-hit probabilities "
                                            "do not sum to one (t07-t09-task-sheets.md, T09 stop; recorded in the product)", **fields)
    return report("topology", "ok", "", **fields)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        return report(args.operation, "missing-dependency", f"{exc.name} is not installed")
    try:
        return {"fit": fit_readout, "check-product": check_product, "topology": topology_readout}[args.operation](args)
    except Exception as exc:  # noqa: BLE001 - anything the operations did not classify: status error (exit 2), never exit 1
        return report(args.operation, "error", f"unexpected {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main())
