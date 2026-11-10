#!/usr/bin/env python3
"""reco.calo.cell-cluster/1, the T08 development binding (decisions.md, U12 A): cell chain and section 7.1 clustering on a
calo-cells/1 readout, written as calo-cluster-product/1 (stage 1 gain payload) or /2 (calo-gain-payload/1). A development
binding in Python, not a native backend.

Operations (contracts/tool_contracts/calo_cluster.json):
  reconstruct    readout + pedestal and gain payloads -> product. Data side: it reads no truth and imports no generator. The gain
                 payload is calo-calibration-payload/1 (stage 1) or calo-gain-payload/1, which carries its channel map and is
                 refused against another one, and makes the product calo-cluster-product/2 (D2 stage 2; /1 otherwise, as in
                 stage 1). A product is never overwritten: an existing target is refused, so a
                 product made with one payload is never replaced by another's.
  check-product  read a product back, refusing a malformed or incomplete one, and run the double-count check on every event.

A labelled readout, calo-cells/2 (D2 stage 3: another simulation's deposits, label simulated-unvalidated), needs a
calo-cluster-configuration/2 written for its label, and a stage 1 gain payload; it makes calo-cluster-product/3, which carries
the input's label and provenance. A labelled input with a /1 configuration, an unlabelled one with a /2 configuration, and a
labelled one with a calo-gain-payload/1 gain are refused, with no product written.

Output: one JSON object on stdout with the status and the reason. Exit 0 ok; 1 failed (check-product found a cell counted
twice, or a component's sharing was undefined; the product is still written and records it). A component whose two-peak
uncertainty is undefined (singular Fisher matrix, non-positive variance) keeps no object, as section 7.1's reference does: a
recorded outcome, counted in uncertainty_failures, exit 0; 2 rejected input (core/status.py), with no product written; 3 a missing
dependency. The named energy is clustered deposited energy, never incident energy.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXIT_FAILED, EXIT_INVALID, EXIT_MISSING = 1, 2, 3


def report(operation: str, status: str, reason: str, code: int, **fields) -> int:
    print(json.dumps({"operation": operation, "status": status, "reason": reason, "exit_code": code, **fields}, sort_keys=True))
    return code


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    rec = sub.add_parser("reconstruct", help="cell chain and section 7.1 clustering of every event of a readout")
    rec.add_argument("--cells", required=True, help="calo-cells/1 readout, role reconstruction-input")
    rec.add_argument("--pedestal-payload", required=True, help="calo-calibration-payload/1, step pedestal (chain step 1)")
    rec.add_argument("--gain-payload", required=True,
                     help="calo-gain-payload/1, or calo-calibration-payload/1 with step gain (chain step 2)")
    rec.add_argument("--product", required=True, help="calo-cluster-product/1, or /2 for a calo-gain-payload/1 gain, to write; not written on refusal; never an existing file")
    rec.add_argument("--product-id", required=True, help="the product's identity")
    rec.add_argument("--configuration", help="calo-cluster-configuration/1; default the t08-grid/1 configuration beside this script")
    chk = sub.add_parser("check-product", help="read a product back and check that no cell is counted twice")
    chk.add_argument("--product", required=True, help="calo-cluster-product/1 or /2 to read")
    return ap


def reconstruct(args) -> int:
    from calo_recipe import ENERGY_KIND, cell_chain, cell_input, clustering, configuration, gain_payload, product
    started = time.perf_counter()
    for name, path in (("cells", args.cells), ("pedestal payload", args.pedestal_payload), ("gain payload", args.gain_payload)):
        if not Path(path).is_file():
            return report("reconstruct", "rejected", f"no such input file: {name} {path}", EXIT_INVALID)
    target = Path(args.product)
    if target.exists():
        return report("reconstruct", "rejected", f"a product is never overwritten: {target} exists ({existing_gain(target)}); "
                      "a product made with one payload is never replaced by another's", EXIT_INVALID)
    try:
        cfg = configuration.load(args.configuration)
        readout = cell_input.read_file(args.cells, cell_input.read_cells, "cells")
        pedestal = cell_input.read_file(args.pedestal_payload, cell_input.read_payload, "pedestal payload")
        gain = cell_input.read_file(args.gain_payload, gain_payload.read_gain, "gain payload")
        chain = cell_chain.chain_record(pedestal, gain)
        if (readout.header["nx"], readout.header["ny"]) != (cfg.cells_x, cfg.cells_y):
            raise cell_input.InputError(f"readout grid {readout.header['nx']} x {readout.header['ny']} is not the configuration's")
        gain_payload.check_channel_map(gain, readout.header["nx"], readout.header["ny"], "gain payload")
        check_label(readout, cfg, gain)
    except (configuration.ConfigurationError, cell_input.InputError) as exc:
        return report("reconstruct", "rejected", str(exc), EXIT_INVALID)
    header = product.header_document(args.product_id, cfg.cells_x, cfg.cells_y, readout.sha256, readout.events, cfg.sha256, chain,
                                     label=readout.label, provenance=readout.header.get("provenance"),
                                     unresolved=cfg.unresolved if readout.label is not None else None)
    partial = target.with_name(target.name + ".partial")
    objects = failures = fisher_failures = 0
    try:
        with open(partial, "w", encoding="utf-8") as stream:
            writer = product.Writer(stream, header)
            for i in range(readout.events):
                cells = cell_chain.apply(readout.raw[i], readout.live[i], readout.saturated[i], pedestal, gain)
                result = clustering.cluster_event(cells.energy, cells.live, cells.saturated, cfg)
                objects += len(result.objects)
                failures += sum(c.failure == "sharing-undefined" for c in result.components)
                fisher_failures += sum(c.failure in ("singular-fisher", "non-positive-variance") for c in result.components)
                writer.event(product.event_document(i, cells, result, cfg.cells_y))
            writer.finish()
        os.replace(partial, target)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        return report("reconstruct", "rejected", f"product cannot be written: {exc.strerror}", EXIT_INVALID)
    except cell_input.InputError as exc:
        partial.unlink(missing_ok=True)
        return report("reconstruct", "rejected", str(exc), EXIT_INVALID)
    fields = {"events": readout.events, "objects": objects, "sharing_failures": failures, "uncertainty_failures": fisher_failures, "energy_kind": ENERGY_KIND,
              "product": str(target), "input_sha256": readout.sha256, "configuration_sha256": cfg.sha256,
              "chain": [step["payload_id"] for step in chain], "seconds": round(time.perf_counter() - started, 3)}
    if readout.label is not None:      # only a labelled product reports it, so the fields of a t08-grid/1 run are unchanged
        fields["label"] = readout.label
    if failures:
        return report("reconstruct", "failed", f"{failures} component(s) with undefined sharing (recorded in the product)", EXIT_FAILED, **fields)
    return report("reconstruct", "ok", "", 0, **fields)


def check_label(readout, cfg, gain) -> None:
    """A labelled input goes with a configuration written for its label and a stage 1 gain payload; an unlabelled one with a
    /1 configuration. Raises cell_input.InputError otherwise."""
    from calo_recipe import cell_input
    if readout.label is not None:
        if cfg.label != readout.label:
            raise cell_input.InputError(f"readout labelled {readout.label!r}: it needs a calo-cluster-configuration/2 written for its "
                                        f"label; this configuration is {cfg.format} for label {cfg.label!r} (t08-grid/1's constants "
                                        "are not this input's)")
        if gain.channel_map is not None:
            raise cell_input.InputError("a labelled readout with a calo-gain-payload/1 gain is not supported in this stage: give its "
                                        "gain as calo-calibration-payload/1")
    elif cfg.label is not None:
        raise cell_input.InputError(f"configuration {cfg.format} is for a labelled input ({cfg.label!r}); this readout has no label")


def existing_gain(path: Path) -> str:
    """The gain payload an existing product names, for the refusal's reason; it is never read further."""
    try:
        with open(path, encoding="utf-8") as stream:
            header = json.loads(stream.readline())
        return f"made with gain payload {header['chain'][1]['payload_id']}"
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return "not a readable calo-cluster product"


def check_product(args) -> int:
    from calo_recipe import product
    if not Path(args.product).is_file():
        return report("check-product", "rejected", f"no such input file: {args.product}", EXIT_INVALID)
    try:
        read = product.read_product(args.product)
    except product.ProductError as exc:
        return report("check-product", "rejected", str(exc), EXIT_INVALID)
    defects = [(doc["event"], d) for doc in read.events for d in product.double_count_defects(doc)]
    fields = {"events": len(read.events), "objects": sum(len(e["objects"]) for e in read.events),
              "energy_kind": read.header["energy_kind"], "double_count_defects": len(defects),
              "first_defects": [f"event {e}: {d}" for e, d in defects[:10]]}
    if defects:
        return report("check-product", "failed", "a cell is counted twice (t07-t09-task-sheets.md, T08 stop)", EXIT_FAILED, **fields)
    return report("check-product", "ok", "", 0, **fields)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        return report(args.operation, "missing-dependency", f"{exc.name} is not installed", EXIT_MISSING)
    return reconstruct(args) if args.operation == "reconstruct" else check_product(args)


if __name__ == "__main__":
    sys.exit(main())
