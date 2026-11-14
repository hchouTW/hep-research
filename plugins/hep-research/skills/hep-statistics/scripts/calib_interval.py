#!/usr/bin/env python3
"""Intervals (simulator calibration workflow, Part B section 7.5; owner of profile likelihood intervals, the
Feldman-Cousins-style and toy-calibrated constructions, MCMC credible intervals, the interval widening of shift mode
and the inference flags of section 15.3a; phase 2).

  calib_interval.py profile --contract FILE --plan FILE --values FILE --parameter NAME [--level 0.68]
  calib_interval.py total   --sigma-q X --level L [--shift D1,D2,...] [--sigma-boot X --w W] [--toy-calibrated]
Profile scan points are not iterated (V fixed at the nominal fit's convergence) and a scan point that does not
converge stays inside the interval. Output: one JSON object; ok (exit 0), rejected (exit 2). Phase 2 (section 17).
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
    from core.calibration import io, fit as F, interval, problems, toy_problem
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
    pr = sub.add_parser("profile")
    _common(pr)
    pr.add_argument("--parameter", required=True)
    pr.add_argument("--level", type=float, default=0.68)
    t = sub.add_parser("total")
    t.add_argument("--sigma-q", type=float, required=True)
    t.add_argument("--level", type=float, default=0.68)
    t.add_argument("--shift", default="")
    t.add_argument("--sigma-boot", type=float, default=0.0)
    t.add_argument("--w", type=float, default=1.0)
    t.add_argument("--toy-calibrated", action="store_true")
    args = ap.parse_args(argv)

    def go():
        if args.cmd == "total":
            sh = [float(x) for x in args.shift.split(",") if x]
            return {"status": "ok", "half_width": interval.total_halfwidth(args.sigma_q, args.level, sh or None,
                                                                          args.sigma_boot, args.w,
                                                                          args.toy_calibrated)}
        try:
            _, _, p = _problem(args)
            if args.parameter not in p.layout.theta:
                raise io.InputError(f"--parameter {args.parameter} is not a theta of the contract")
            fit = F.find_extremum(p, args.seed, p.initial_beta())
            r = interval.profile_interval(p, fit, p.layout.theta.index(args.parameter), args.level, args.seed)
            return io.jsonable({"status": "ok", **r, "flags": interval.inference_flags(r)})
        except (problems.ProblemError, F.FitError) as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
