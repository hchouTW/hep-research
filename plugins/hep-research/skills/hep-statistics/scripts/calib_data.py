#!/usr/bin/env python3
"""Data releases, raw-unit lineage, reads and failure records (simulator calibration workflow, Part B sections 2.1,
5.1, 9.5, Appendix C.1; the single writer of reads and failure records).

  calib_data.py init     --ledger FILE                              new empty ledger (refuses an existing file)
  calib_data.py ingest   --release FILE                             ingestion declarations (clause 8)
  calib_data.py units    --release FILE [--release FILE ...] --of HASH   raw units along the lineage
  calib_data.py draft    --ledger FILE --series NAME                register a contract draft (a read channel)
  calib_data.py fit-read --ledger FILE --release-hash H --units FILE --channel FILE [--kappa K]
  calib_data.py open     --ledger FILE --kappa K --vmode holdout|cross-validation --release FILE ...
                         --calibration H ... [--validation H ...] --channel FILE [--conditions FILE]
                                                                    validation reads and pending failure records;
                         the raw units come from the releases' lineage (unconfirmed lineage or a holdout sharing
                         raw units is refused, nothing is recorded); --conditions holds the opening conditions
  calib_data.py decide   --ledger FILE --decision FILE             apply a decision record (calib_validate's)
  calib_data.py provide  --ledger FILE --release FILE --channel FILE --calibration HASH ... --out FILE [--kappa K]
                         the one provider of calibration values to a fit (records the fit read, section 9.5)
  calib_data.py inputs   --ledger FILE --kappa K --vmode MODE --validation-units FILE --calibration-units FILE
                         [--no-validation-read]                    the reuse and failure-record inputs
--units files hold a JSON list of raw-unit ids; --channel files hold {"contract_sha256": H} or {"series": S,
"draft": N}. A release is identified by the canonical SHA-256 of its metadata (a declared release_sha256 must equal it).
Ledger writes are atomic under an exclusive lock file LEDGER.lock; a lock left by a killed writer is removed by a
person after checking that no calib_data.py runs (it is never broken automatically). Output: one JSON object; status ok/written (exit 0),
failed (exit 1: ingestion findings), rejected (exit 2: bad input, or a refused read or record, e.g. lineage not
confirmed). Phase 0 (section 17); the locking-stage checks that need model quantities come in phase 2.
Standard library only.
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

from core.calibration import data_release as data
from core.calibration import io


def _units(path):
    u = io.load(path)
    if not isinstance(u, list) or not all(isinstance(x, str) for x in u):
        raise io.InputError(f"{path}: a JSON list of raw-unit ids")
    return u


def _releases(paths):
    rels = {}
    for p in paths:
        r = io.load(p)
        if not isinstance(r, dict):
            raise io.InputError(f"{p}: a release is a JSON object")
        rels[data.release_hash(r)] = r
    return rels


def _ledger(path):
    return data.Ledger(io.load(path))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").add_argument("--ledger", required=True)
    sub.add_parser("ingest").add_argument("--release", required=True)
    u = sub.add_parser("units")
    u.add_argument("--release", action="append", required=True)
    u.add_argument("--of", required=True)
    d = sub.add_parser("draft")
    d.add_argument("--ledger", required=True)
    d.add_argument("--series", required=True)
    f = sub.add_parser("fit-read")
    for a in ("--ledger", "--release-hash", "--units", "--channel"):
        f.add_argument(a, required=True)
    f.add_argument("--kappa")
    o = sub.add_parser("open")
    for a in ("--ledger", "--kappa", "--channel"):
        o.add_argument(a, required=True)
    o.add_argument("--vmode", required=True, choices=("holdout", "cross-validation"))
    o.add_argument("--release", action="append", required=True)
    o.add_argument("--calibration", action="append", required=True)
    o.add_argument("--validation", action="append", default=[])
    o.add_argument("--conditions")
    de = sub.add_parser("decide")
    de.add_argument("--ledger", required=True)
    de.add_argument("--decision", required=True)
    pv = sub.add_parser("provide")
    for a in ("--ledger", "--release", "--channel", "--out"):
        pv.add_argument(a, required=True)
    pv.add_argument("--calibration", action="append", required=True,
                    help="hash of a calibration release declared by the contract")
    pv.add_argument("--kappa")
    i = sub.add_parser("inputs")
    for a in ("--ledger", "--kappa", "--validation-units", "--calibration-units"):
        i.add_argument(a, required=True)
    i.add_argument("--vmode", required=True, choices=("none", "holdout", "cross-validation"))
    i.add_argument("--no-validation-read", action="store_true")
    args = ap.parse_args(argv)

    def write(fn):
        with io.locked(args.ledger):
            led = _ledger(args.ledger)
            out = fn(led)
            io.write_json(args.ledger, led.state)
        return {"status": "written", "seq": led.state["seq"], **out}

    def go():
        try:
            if args.cmd == "init":
                if Path(args.ledger).exists():
                    raise io.InputError(f"{args.ledger} exists; a ledger is never reset")
                io.write_json(args.ledger, data.Ledger().state)
                return {"status": "written", "ledger": args.ledger}
            if args.cmd == "ingest":
                r = io.load(args.release)
                findings = data.ingestion_findings(r) if isinstance(r, dict) else [{"code": "ingestion.shape"}]
                return {"status": "failed" if findings else "ok", "findings": findings}
            if args.cmd == "units":
                rels = _releases(args.release)
                units = data.raw_units(args.of, rels)
                return {"status": "ok", "lineage_confirmed": units is not None,
                        "raw_units": sorted(units) if units is not None else None}
            if args.cmd == "draft":
                return write(lambda led: {"channel": led.register_draft(args.series)})
            if args.cmd == "fit-read":
                units, chan = _units(args.units), io.load(args.channel)
                return write(lambda led: {"read_seq": led.fit_read(args.release_hash, units, chan, args.kappa)})
            if args.cmd == "open":
                rels, chan = _releases(args.release), io.load(args.channel)
                cond = io.load(args.conditions) if args.conditions else None
                if args.vmode == "holdout" and not args.validation:
                    raise io.InputError("holdout opens its validation releases: give --validation")
                u = data.opening_units(args.vmode, args.calibration, args.validation, rels)
                read = args.validation if args.vmode == "holdout" else args.calibration
                return write(lambda led: {"opening_seq": led.open_validation(
                    args.kappa, read[0], u["validation_units"], u["calibration_units"], chan, cond),
                    "validation_units": len(u["validation_units"] or ()),
                    "calibration_units": len(u["calibration_units"] or ())})
            if args.cmd == "provide":
                rel, chan = io.load(args.release), io.load(args.channel)

                def prov(led):
                    values, seq = led.provide_values(rel, chan, args.calibration, args.kappa)
                    io.write_json(args.out, values)
                    return {"read_seq": seq, "values": args.out}
                return write(prov)
            if args.cmd == "decide":
                dec = io.load(args.decision)
                return write(lambda led: {"record_status": led.apply_decision(dec)})
            led = _ledger(args.ledger)
            v, c = _units(args.validation_units), _units(args.calibration_units)
            return {"status": "ok", **led.c1_inputs(args.kappa, args.vmode, v, c, not args.no_validation_read),
                    "waiting_records": led.waiting_records(args.kappa, c),
                    "concurrent_configurations": led.concurrent_configurations(args.kappa, c)}
        except data.DataError as exc:
            raise io.InputError(f"{exc.code}: {exc}") from None
        except (AttributeError, KeyError, TypeError) as exc:
            raise io.InputError(f"unexpected input structure: {exc}") from None
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
