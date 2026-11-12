#!/usr/bin/env python3
"""The contract checker (simulator calibration workflow, Part B section 5.2; owner of the contract rules).

  calib_contract.py check     --contract FILE [--release FILE ...] [--series-graph FILE] [--design FILE]
                              [--locking FILE] [--model-documents FILE]
  calib_contract.py identity  --contract FILE --model-documents FILE
  calib_contract.py preflight --contract DRAFT --release FILE --ledger FILE [--write-draft OUT]
FILE is a calibration-contract/1; each --release is a calibration-data-release/1 metadata file (its lineage,
samples, observables and declarations; the release hash is the canonical SHA-256 of its metadata, and a declared
"release_sha256" must equal it), read for the rules that look at metadata, lineage or totals, never at sealed values;
--series-graph maps contract series to the series of their upstream results (cycle check). Output: one JSON object
with the findings and the rules deferred to later phases; status accepted (exit 0) or rejected (exit 2: a contract
error, no result is produced). --design is the output of `calib_design.py linearize`: with it the D37 rule (approval
A7) is applied, a psi whose effect on theta-hat via A exceeds 0.1 sigma_tot^design must be listed as phi. --locking
is the report of `calib_data.py locking` (phase 2): its failures (rounding, sigma^(0) = 0, the N_d,c declaration
check, value conventions) reject the contract and the rules it decides leave `deferred`.

With g4sim (phase 3): each model carries the five identity items of section 5.1 and each theta/phi its field bindings
(section 11.4). --model-documents names a JSON object {model id: {detector_spec, alignment_overlay, simulation_request,
run_card, response_pipeline, efficiency_map, condition_snapshot: file paths relative to it; event_time_rule, mapping,
pde, build_environment: objects}}; with it the five items are recomputed (detector-spec/1 read by g4sim's procedure,
the other documents normalized with type tables from their schemas, theta/phi fields masked) and must equal the
declared ones. `identity` prints the recomputed items (status ok), to be written into the contract.

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

from pathlib import Path

from contracts.geometry import field_types
from contracts.schema import load_schema, validate
from core.calibration import contract as cc
from core.calibration import model_identity as mi
from core.calibration import data_release as data
from core.calibration import io


ROOT = Path(__file__).resolve().parents[3]
RUN_CARD_SCHEMA = ROOT / "adapters" / "geant4" / "assets" / "g4sim_run.schema.json"   # g4sim's run card schema
TEXT_DOCUMENTS = ("detector_spec", "alignment_overlay", "simulation_request", "run_card", "response_pipeline",
                  "condition_snapshot")
INLINE = ("event_time_rule", "mapping", "pde", "build_environment")


def type_tables() -> dict:
    out = {"detector-spec": field_types(),
           "run-card": mi.type_table(io.load_object(str(RUN_CARD_SCHEMA)))}
    for kind, name in (("alignment-overlay", "alignment_overlay.json"), ("simulation-request", "simulation_request.json"),
                       ("response-pipeline", "response_pipeline.json"), ("condition-snapshot", "condition_snapshot.json")):
        out[kind] = mi.type_table(load_schema(name))
    return out


def identities(contract: dict, path: str) -> dict:
    """{model id: the five recomputed items, or {"error": {code, message}}} from the --model-documents file."""
    spec = io.load_object(path)
    base = Path(path).resolve().parent
    tables, masks = type_tables(), mi.masks(contract)
    out = {}
    for mid, entry in spec.items():
        if not isinstance(entry, dict):
            raise io.InputError(f"--model-documents: model {mid!r} maps to an object of documents")
        docs = {}
        for key, value in entry.items():
            if key in TEXT_DOCUMENTS:
                try:
                    docs[key] = (base / str(value)).read_bytes()
                except OSError as exc:
                    raise io.InputError(f"--model-documents: {key} of {mid!r}: {exc.strerror or exc}") from None
            elif key == "efficiency_map":
                docs[key] = io.load_object(str(base / str(value)))
            elif key in INLINE:
                docs[key] = value
            else:
                raise io.InputError(f"--model-documents: unknown entry {key!r} of model {mid!r}")
        missing = [k for k in ("detector_spec", "simulation_request", "run_card", "response_pipeline",
                               "build_environment") if k not in docs]
        if missing:
            out[mid] = {"error": {"code": "identity.documents", "message": f"model {mid!r} lacks {missing}"}}
            continue
        try:
            out[mid] = mi.identity(docs, masks, tables)
        except mi.IdentityError as err:
            out[mid] = {"error": {"code": err.code, "message": str(err)}}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--contract", required=True)
    p.add_argument("--release", action="append", default=[])
    p.add_argument("--series-graph")
    p.add_argument("--design")
    p.add_argument("--locking", help="the locking report of calib_data.py locking (phase 2)")
    p.add_argument("--model-documents", help="the g4sim documents of each model (section 5.1)")
    t = sub.add_parser("identity")
    t.add_argument("--contract", required=True)
    t.add_argument("--model-documents", required=True)
    q = sub.add_parser("preflight")
    q.add_argument("--contract", required=True)
    q.add_argument("--release", required=True)
    q.add_argument("--ledger", required=True)
    q.add_argument("--write-draft")
    args = ap.parse_args(argv)

    def preflight():
        try:
            from core.calibration import preflight as a0
        except ImportError as exc:                # A0 needs NumPy
            return {"status": "rejected", "error": f"preflight needs NumPy ({exc})"}
        c = io.load(args.contract)
        r = io.load(args.release)
        if not isinstance(c, dict) or not isinstance(r, dict) or not c.get("series"):
            raise io.InputError("--contract (a draft with its series) and --release are JSON objects")
        with io.locked(args.ledger):
            led = data.Ledger(io.load(args.ledger))
            try:
                values, seq = led.provide_values(r, {"series": c["series"]},
                                                 (c.get("data") or {}).get("calibration_releases"))
            except data.DataError as exc:
                return {"status": "rejected", "code": exc.code, "error": str(exc)}
            io.write_json(args.ledger, led.state)       # the values were provided: the read is recorded (section 9.5)
        try:
            out = a0.preflight(c, values)
        except a0.PreflightError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc), "read_seq": seq}
        except (KeyError, TypeError, ValueError) as exc:
            return {"status": "rejected", "code": "a0.declaration", "error": f"malformed threshold: {exc!r}",
                    "read_seq": seq}
        if args.write_draft:
            io.write_json(args.write_draft, {**c, "a0_summary": out["a0_summary"]})
        return {"status": out["status"], "a0_summary": out["a0_summary"], "decisions": out["decisions"],
                "findings": out["findings"], "read_seq": seq}

    def go():
        if args.cmd == "preflight":
            return preflight()
        if args.cmd == "identity":
            c = io.load_object(args.contract)
            ids = identities(c, args.model_documents)
            bad = {k: v["error"] for k, v in ids.items() if "error" in v}
            return {"status": "rejected" if bad else "ok", "identities": ids}
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
        locking = io.load(args.locking) if args.locking else None
        ids = identities(c, args.model_documents) if args.model_documents else None
        try:
            r = cc.check(c, rels, graph, design, locking, ids)
        except (TypeError, ValueError) as exc:
            raise io.InputError(f"--design: {exc}") from None
        return {"status": r["status"], "contract_sha256": cc.lock_hash(c), "findings": r["findings"],
                "deferred": r["deferred"]}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
