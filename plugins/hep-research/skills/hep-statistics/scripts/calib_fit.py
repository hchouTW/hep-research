#!/usr/bin/env python3
"""The fit (simulator calibration workflow, Part B sections 7.3, 7.4, 8.2; owner of the reference-point iteration and
multi-start, G1, G2, G3, G6, G7, locally linear toys and the linearity check, the non-convergence rules and the k* of
the ratio test; phase 2).

  calib_fit.py fit  --contract FILE --plan FILE --values FILE [--release FILE] [--seed S] [--sigma-noise X]
  calib_fit.py g6   --contract FILE --plan FILE --values FILE [--toys N]
  calib_fit.py g7   --theta-hats FILE --sigma-mc FILE [--alpha A]
  calib_fit.py g3   --region FILE --limits FILE
  calib_fit.py kstar --n N [--no-replacement]
The fit runs section 7.4 (max(2d, 16) Sobol starts, basins, ties, `multimodal`) and the section 7.3 iteration with
the ln det diagnostic; G1 per basin. Output: one JSON object; passed (exit 0), failed (exit 1), rejected (exit 2),
incomplete (exit 3). The engine (core/calibration) needs NumPy and SciPy. Phase 2 (section 17).
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
    from core.calibration import io, fit as F, problems, toy_problem
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
    _common(sub.add_parser("fit"))
    g6 = sub.add_parser("g6")
    _common(g6)
    g6.add_argument("--toys", type=int, default=1000)
    g7 = sub.add_parser("g7")
    g7.add_argument("--theta-hats", required=True)
    g7.add_argument("--sigma-mc", required=True)
    g7.add_argument("--alpha", type=float, default=0.01)
    g3 = sub.add_parser("g3")
    g3.add_argument("--region", required=True)
    g3.add_argument("--limits", required=True)
    k = sub.add_parser("kstar")
    k.add_argument("--n", type=int, required=True)
    k.add_argument("--no-replacement", action="store_true")
    args = ap.parse_args(argv)

    def go():
        if args.cmd == "kstar":
            return {"status": "ok", "n": args.n, "replacement": not args.no_replacement,
                    "k_star": F.k_star(args.n, not args.no_replacement)}
        if args.cmd == "g7":
            return io.jsonable(F.g7(np.asarray(io.load(args.theta_hats), float), np.asarray(io.load(args.sigma_mc),
                                                                                             float), alpha=args.alpha))
        if args.cmd == "g3":
            return F.g3(io.load(args.region), io.load(args.limits))
        try:
            _, _, p = _problem(args)
            fit = F.find_extremum(p, args.seed, p.initial_beta())
            if args.cmd == "fit":
                g1 = F.g1(fit, p)
                return io.jsonable({"status": g1["status"], "fit": fit.record(), "G1": g1,
                                    "sigma_noise": p.sigma_noise, "flags": ["provisional-thresholds", "synthetic"]})
            return io.jsonable(F.g6(p, fit, F.null_toys(p, fit, args.toys, args.seed + 1)))
        except (problems.ProblemError, F.FitError) as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
