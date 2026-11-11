#!/usr/bin/env python3
"""Validation (simulator calibration workflow, Part B section 9; owner of the validation statistics, C_r^+ on N_d,
the declaration checks (a)(b)(c), the minimum numbers of toys, the G5 proportion, cross-validation, power and its
lower bound, and the records: kappa, decision records, abandonment and power abandonment; phase 2).

  calib_validate.py kappa         --contract-sha256 H --plan FILE --engine V --book FILE
  calib_validate.py statistic     --input FILE          {r, C_r, sigma0, constraints}: T_v, k (chi2_k when allowed)
  calib_validate.py declaration   --input FILE          {C_r0, sigma0, constraints, expectations}: (a)(b)(c)
  calib_validate.py holdout       --contract FILE --plan FILE --values FILE --validation-values FILE
                                  [--release FILE] [--validation-release FILE] --kappa K --book FILE --ledger FILE
                                  [--path analytic|toys] [--toys N] [--seed S]
                                  the fit, T_v with C_r^+ and its reference, the data-side constraint check, and the
                                  decision record computed from them (pass / fail / no-testable-direction)
  calib_validate.py cv            --contract FILE --plan FILE --values FILE --folds FILE --kappa K --book FILE
                                  --ledger FILE [--toys N] [--seed S]       T_cv with C-hat_{r,f}, its reference, the record
  calib_validate.py power         --book FILE --kappa K --input FILE        the analytic power lower bound (cross
                                  products per alternative), recorded for kappa
  calib_validate.py abandon       --book FILE --ledger FILE --kappa K
  calib_validate.py abandon-power --book FILE --kappa K
  calib_validate.py required-lambda --k K [--alpha A]
No outcome is ever given by hand: a decision record exists only from a statistic computed here (review F4).
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
    from core.calibration import io, data_release, validate as V, problems, fit as F, data_checks as DC
    from core.calibration import toy_problem as TP
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


def _data_side(contract, values: dict, decl: dict) -> bool:
    """The data-side constraint check on the opened validation values (section 9.2): |n^T y - c| beyond the rounding
    bound triggers it; formats from the validation release's declarations (float64 when none)."""
    for nd in (contract.get("validation") or {}).get("N_d", []):
        obs = [o for o, v in nd["n"].items() if v]
        if not obs or not all(o in values for o in obs):
            continue
        fm = DC._formats(decl or {}, obs)
        y = np.array([float(values[o]) for o in obs])
        half = np.array([DC.unit(v, fm[o]) / 2 for v, o in zip(y, obs)])
        if DC.constraint_check(np.array([float(nd["n"][o]) for o in obs]), float(nd.get("c", 0.0)), y,
                               half)["triggered"]:
            return True
    return False


def computed_decision(args) -> dict:
    """Compute the statistic and write its decision record (book, then the ledger's failure records)."""
    contract, plan, extras = io.contract_and_plan(args.contract, args.plan)
    p = problems.from_inputs(contract, plan, io.load(args.values), io.systematics(args.release, extras))
    p.sigma_noise = TP.estimate_sigma_noise(p, p.initial_beta())
    with io.locked(args.book):
        book = _book(args.book)
        kap = book.state["kappas"].get(args.kappa)
        if kap is None:
            raise V.ValidationError("validate.kappa_unregistered", "write kappa before computing any statistic")
        alpha = float(kap.get("alpha", 0.05))
        if args.cmd == "holdout":
            vals = io.load(args.validation_values)
            missing = [n for n in p.val_names if n not in vals]
            if missing or not p.val_names:
                raise io.InputError(f"--validation-values: values for the validation observables {p.val_names}")
            from core.calibration import likelihood as L
            yv = np.array([L.link(np.array([float(vals[n])]), p.val_links[n])[0] for n in p.val_names])
            fit = F.find_extremum(p, args.seed, p.initial_beta())
            if not fit.converged:
                return {"status": "incomplete", "finding": "validate.fit_not_converged", "reason": fit.reason}
            decl = (io.load(args.validation_release).get("declarations") if args.validation_release else None) or {}
            ev = V.holdout_evidence(p, fit, yv, args.kappa, alpha, args.path, args.toys, args.seed + 1,
                                    data_side_check_triggered=_data_side(contract, vals, decl))
        else:
            fl = io.load(args.folds)
            folds = [[p.names.index(o) for o in f] for f in fl]
            ev = V.cv_evidence(p, folds, args.kappa, alpha, args.seed + 2, n_ref=args.toys)
        if V.outcome_of(ev) is None:
            return {"status": "incomplete", "evidence": io.jsonable(ev), "finding": ev.get("finding")}
        with io.locked(args.ledger):
            ledger = data_release.Ledger(io.load(args.ledger))
            rec = book.decide_computed(ev, ledger)
            io.write_json(args.ledger, ledger.state)
        io.write_json(args.book, io.jsonable(book.state))
    return {"status": "written", "outcome": rec["outcome"], "evidence": io.jsonable(ev), "record": io.jsonable(rec)}


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
    for name in ("holdout", "cv"):
        d = sub.add_parser(name)
        for a in ("--contract", "--plan", "--values", "--book", "--ledger", "--kappa"):
            d.add_argument(a, required=True)
        d.add_argument("--release")
        d.add_argument("--toys", type=int, default=500)
        d.add_argument("--seed", type=int, default=20261170)
        if name == "holdout":
            d.add_argument("--validation-values", required=True)
            d.add_argument("--validation-release")
            d.add_argument("--path", choices=("analytic", "toys"), default="analytic")
        else:
            d.add_argument("--folds", required=True, help="[[observable, ...], ...]: the validation folds")
    pw = sub.add_parser("power")
    for a in ("--book", "--kappa", "--input"):
        pw.add_argument(a, required=True)
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
            if args.cmd in ("holdout", "cv"):
                return computed_decision(args)
            if args.cmd == "power":
                with io.locked(args.book):
                    book = _book(args.book)
                    if args.kappa not in book.state["kappas"]:
                        raise V.ValidationError("validate.kappa_unregistered", "write kappa first")
                    x = io.load(args.input)
                    reps = {a: (None if v is None else np.asarray(v, float)) for a, v in x["cross_reps"].items()}
                    alpha = book.state["kappas"][args.kappa].get("alpha", 0.05)
                    r = V.power_analytic(reps, int(x["k"]), alpha)
                    rec = book.record_power(args.kappa, {k_: v for k_, v in r.items()})
                    io.write_json(args.book, io.jsonable(book.state))
                return {**io.jsonable(rec), "status": r["status"]}
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
                        rec = book.abandon(args.kappa, ledger)
                        io.write_json(args.ledger, ledger.state)
                    out = {"status": "written", **rec}
                io.write_json(args.book, book.state)
                return out
        except V.ValidationError as exc:
            return {"status": "refused", "code": exc.code, "error": str(exc)}
        except data_release.DataError as exc:
            return {"status": "refused", "code": exc.code, "error": str(exc)}
        except (problems.ProblemError, F.FitError) as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
