#!/usr/bin/env python3
"""The contract checker (simulator calibration workflow, Part B section 5.2; owner of the contract rules).

  calib_contract.py check --contract FILE [--release FILE ...] [--series-graph FILE]
FILE is a calibration-contract/1; each --release is a calibration-data-release/1 metadata file (its lineage,
samples, observables and declarations; the release hash is its file's canonical SHA-256 unless it carries
"release_sha256"), read for the rules that look at metadata, lineage or totals, never at sealed values;
--series-graph maps contract series to the series of their upstream results (cycle check). Output: one JSON object
with the findings and the rules deferred to later phases; status accepted (exit 0) or rejected (exit 2: a contract
error, no result is produced). Phase 0 (section 17): the locking-stage checks that need model quantities are added
in phase 2 and the g4sim model identity in phase 3; preflight (A0) arrives in phase 1. Standard library only.
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
from core.calibration import io
from core.canonical import canonical_sha256


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--contract", required=True)
    p.add_argument("--release", action="append", default=[])
    p.add_argument("--series-graph")
    args = ap.parse_args(argv)

    def go():
        c = io.load(args.contract)
        rels = {}
        for path in args.release:
            r = io.load(path)
            if not isinstance(r, dict):
                raise io.InputError(f"{path}: a release is a JSON object")
            rels[r.get("release_sha256") or canonical_sha256(r)] = r
        graph = io.load(args.series_graph) if args.series_graph else None
        shape = [f.as_dict() for f in validate(c, "calibration_contract.json").errors]
        if shape:
            return {"status": "rejected", "findings": shape, "stage": "schema"}
        r = cc.check(c, rels, graph)
        return {"status": r["status"], "contract_sha256": cc.lock_hash(c), "findings": r["findings"],
                "deferred": r["deferred"]}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
