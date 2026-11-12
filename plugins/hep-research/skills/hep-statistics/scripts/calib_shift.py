#!/usr/bin/env python3
"""Shift mode of phi (simulator calibration workflow, Part B sections 5.5, 8.2 note 10; owner of P8, G9, the +-1 sigma
and +-2 sigma refits and d_l; phase 2).

  calib_shift.py p8 --contract FILE --plan FILE [--release FILE]           at theta_ref with Asimov data, c = 0.1
  calib_shift.py g9 --contract FILE --plan FILE --values FILE [--seed S]   Delta_i <= 0.06 and 1.5c at theta-hat
G9 is decided only after P8 passed. Not applicable without a shift-mode phi. Output: one JSON object; passed (exit 0),
not-applicable (exit 0), failed (exit 1, remedy level contract: profile mode), rejected (exit 2). Phase 2.
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
    from core.calibration import io, fit as F, problems, shift, toy_problem
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)


def _missing(argv):
    a = argv if argv is not None else sys.argv[1:]
    if MISSING and "-h" not in a and "--help" not in a:
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return True
    return False


def _problem(args):
    contract, plan, extras = io.contract_and_plan(args.contract, args.plan)
    if plan is None:
        raise io.InputError("--plan is needed (or a fixture with a plan)")
    values = io.load(args.values) if getattr(args, "values", None) else None
    p = problems.from_inputs(contract, plan, values, io.systematics(getattr(args, "release", None), extras))
    if getattr(args, "sigma_noise", None) is not None:
        p.sigma_noise = float(args.sigma_noise)
    elif values is not None:
        p.sigma_noise = toy_problem.estimate_sigma_noise(p, p.initial_beta())
    return contract, plan, p


def _common(p, values=True):
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--release")
    if values:
        p.add_argument("--values", required=True, help="calibration values (JSON {observable: value}) provided by "
                       "calib_data.py provide, which records the fit read")
    p.add_argument("--sigma-noise", type=float)
    p.add_argument("--seed", type=int, default=20261130)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if _missing(argv):
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    _common(sub.add_parser("p8"), values=False)
    _common(sub.add_parser("g9"))
    args = ap.parse_args(argv)

    def go():
        try:
            _, _, p = _problem(args)
            b = p.initial_beta()
            if args.cmd == "p8":
                p.observed = p.asimov(b)
                return io.jsonable(shift.p8(p, b))
            p8 = shift.p8(p, b)
            fit = F.find_extremum(p, args.seed, b)
            return io.jsonable(shift.g9(p, fit, p8, seed=args.seed))
        except (problems.ProblemError, F.FitError) as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
