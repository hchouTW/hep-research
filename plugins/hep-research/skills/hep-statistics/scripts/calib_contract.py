#!/usr/bin/env python3
"""The contract checker (simulator calibration workflow, Part B section 5.2; owner of the contract rules).

  calib_contract.py check     --contract FILE [--release FILE ...] [--series-graph FILE] [--design FILE]
  calib_contract.py preflight --contract DRAFT --release FILE --ledger FILE [--write-draft OUT]
FILE is a calibration-contract/1; each --release is a calibration-data-release/1 metadata file (its lineage,
samples, observables and declarations; the release hash is the canonical SHA-256 of its metadata, and a declared
"release_sha256" must equal it), read for the rules that look at metadata, lineage or totals, never at sealed values;
--series-graph maps contract series to the series of their upstream results (cycle check). Output: one JSON object
with the findings and the rules deferred to later phases; status accepted (exit 0) or rejected (exit 2: a contract
error, no result is produced). --design is the output of `calib_design.py linearize`: with it the D37 rule (approval
A7) is applied, a psi whose effect on theta-hat via A exceeds 0.1 sigma_tot^design must be listed as phi. The
locking-stage checks that need model quantities are added in phase 2 and the g4sim model identity in phase 3.

preflight is A0 (pipeline stage A0, not a gate): the calibration values come from calib_data's provider, which records
a fit read with the contract draft's series as read channel in the ledger (written under its lock); for each declared
threshold with a smoothing model it decides whether the data can reach it. Output: the A0 summary (the names of the
unreachable thresholds only, never a data value) and one decision per threshold; status ok (exit 0). --write-draft
writes the draft with its a0_summary. Phase 1 (section 17). Standard library plus NumPy (preflight).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import sys

from contracts.schema import validate
from core.calibration import contract as cc
from core.calibration import data_release as data
from core.calibration import io


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--contract", required=True)
    p.add_argument("--release", action="append", default=[])
    p.add_argument("--series-graph")
    p.add_argument("--design")
    q = sub.add_parser("preflight")
    q.add_argument("--contract", required=True)
    q.add_argument("--release", required=True)
    q.add_argument("--ledger", required=True)
    q.add_argument("--write-draft")
    args = ap.parse_args(argv)

    def preflight():
        from core.calibration import preflight as a0
        c = io.load(args.contract)
        r = io.load(args.release)
        if not isinstance(c, dict) or not isinstance(r, dict) or not c.get("series"):
            raise io.InputError("--contract (a draft with its series) and --release are JSON objects")
        with io.locked(args.ledger):
            led = data.Ledger(io.load(args.ledger))
            try:
                values, seq = led.provide_values(r, {"series": c["series"]},
                                                 (c.get("data") or {}).get("calibration_releases"))
                out = a0.preflight(c, values)
            except data.DataError as exc:
                return {"status": "rejected", "code": exc.code, "error": str(exc)}
            except a0.PreflightError as exc:
                return {"status": "rejected", "code": exc.code, "error": str(exc)}
            io.write_json(args.ledger, led.state)
        if args.write_draft:
            io.write_json(args.write_draft, {**c, "a0_summary": out["a0_summary"]})
        return {"status": out["status"], "a0_summary": out["a0_summary"], "decisions": out["decisions"],
                "findings": out["findings"], "read_seq": seq}

    def go():
        if args.cmd == "preflight":
            return preflight()
        c = io.load(args.contract)
        rels = {}
        for path in args.release:
            r = io.load(path)
            if not isinstance(r, dict):
                raise io.InputError(f"{path}: a release is a JSON object")
            try:
                rels[data.release_hash(r)] = r
            except data.DataError as exc:
                raise io.InputError(f"{path}: {exc}") from None
        graph = io.load(args.series_graph) if args.series_graph else None
        shape = [f.as_dict() for f in validate(c, "calibration_contract.json").errors]
        if shape:
            return {"status": "rejected", "findings": shape, "stage": "schema"}
        design = io.load(args.design) if args.design else None
        r = cc.check(c, rels, graph, design)
        return {"status": r["status"], "contract_sha256": cc.lock_hash(c), "findings": r["findings"],
                "deferred": r["deferred"]}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
