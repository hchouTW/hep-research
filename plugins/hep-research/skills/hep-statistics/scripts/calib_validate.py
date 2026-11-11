#!/usr/bin/env python3
"""Validation (simulator calibration workflow, Part B section 9; owner of the validation statistics, C_r^+ on N_d,
the declaration checks (a)(b)(c), the minimum numbers of toys, the G5 proportion, cross-validation, power and its
lower bound, and the records: kappa, decision records, abandonment and power abandonment; phase 2).

  calib_validate.py kappa         --contract-sha256 H --plan FILE --engine V --book FILE
  calib_validate.py statistic     --input FILE          {r, C_r, sigma0, constraints}: T_v, k (chi2_k when allowed)
  calib_validate.py declaration   --input FILE          {C_r0, sigma0, constraints, expectations}: (a)(b)(c)
  calib_validate.py decide        --book FILE --ledger FILE --kappa K --outcome pass|fail|no-testable-direction
                                  [--data-side-check-triggered]
  calib_validate.py abandon       --book FILE --ledger FILE --kappa K
  calib_validate.py abandon-power --book FILE --kappa K
  calib_validate.py required-lambda --k K [--alpha A]
The decision records drive the failure records of calib_data (pending -> withdrawn / final). Output: one JSON
object; ok/passed (exit 0), failed or refused (exit 1), rejected (exit 2), incomplete (exit 3). Phase 2.
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
import json
import sys

try:
    MISSING = None
    import numpy as np
    from core.calibration import io, data_release, validate as V
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)


def _missing(argv):
    a = argv if argv is not None else sys.argv[1:]
    if MISSING and "-h" not in a and "--help" not in a:
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return True
    return False


def _book(path):
    import os
    return V.DecisionBook(io.load(path)) if os.path.exists(path) else V.DecisionBook()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if _missing(argv):
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kappa")
    k.add_argument("--contract-sha256", required=True)
    k.add_argument("--plan", required=True)
    k.add_argument("--engine", required=True)
    k.add_argument("--book", required=True)
    sub.add_parser("statistic").add_argument("--input", required=True)
    sub.add_parser("declaration").add_argument("--input", required=True)
    d = sub.add_parser("decide")
    for a in ("--book", "--ledger", "--kappa"):
        d.add_argument(a, required=True)
    d.add_argument("--outcome", choices=("pass", "fail", "no-testable-direction"), required=True)
    d.add_argument("--data-side-check-triggered", action="store_true")
    a_ = sub.add_parser("abandon")
    for a in ("--book", "--ledger", "--kappa"):
        a_.add_argument(a, required=True)
    ap_ = sub.add_parser("abandon-power")
    ap_.add_argument("--book", required=True)
    ap_.add_argument("--kappa", required=True)
    r = sub.add_parser("required-lambda")
    r.add_argument("--k", type=int, required=True)
    r.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args(argv)

    def go():
        try:
            if args.cmd == "required-lambda":
                return {"status": "ok", "lambda": V.required_lambda(args.k, args.alpha)}
            if args.cmd == "statistic":
                x = io.load(args.input)
                Cp, kk = V.c_r_plus(np.asarray(x["C_r"], float), np.asarray(x["sigma0"], float),
                                    [np.asarray(c, float) for c in x.get("constraints", [])])
                return {"status": "ok", "T_v": V.t_v(np.asarray(x["r"], float), Cp), "k": kk}
            if args.cmd == "declaration":
                x = io.load(args.input)
                res = V.declaration_check(np.asarray(x["C_r0"], float), np.asarray(x["sigma0"], float),
                                          [np.asarray(c, float) for c in x.get("constraints", [])],
                                          [np.asarray(e, float) for e in x.get("expectations", [])])
                if res["status"] == "failed":
                    return {**res, "status": "rejected", "code": res["failures"][0]}
                return res
            with io.locked(args.book):
                book = _book(args.book)                          # read inside the lock (single writer, F21)
                if args.cmd == "kappa":
                    rec = V.kappa_record(args.contract_sha256, io.load(args.plan), args.engine)
                    book.register(rec)
                    out = {"status": "written", **rec}
                elif args.cmd == "abandon-power":
                    out = {"status": "written", **book.abandon_power(args.kappa)}
                else:
                    with io.locked(args.ledger):
                        ledger = data_release.Ledger(io.load(args.ledger))
                        if args.cmd == "decide":
                            rec = book.decide(args.kappa, args.outcome, ledger, args.data_side_check_triggered)
                        else:
                            rec = book.abandon(args.kappa, ledger)
                        io.write_json(args.ledger, ledger.state)
                    out = {"status": "written", **rec}
                io.write_json(args.book, book.state)
                return out
        except V.ValidationError as exc:
            return {"status": "refused", "code": exc.code, "error": str(exc)}
        except data_release.DataError as exc:
            return {"status": "refused", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
