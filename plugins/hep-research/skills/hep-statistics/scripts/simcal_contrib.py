#!/usr/bin/env python3
"""Contribution decomposition (simulator calibration workflow, Part B section 10.5; phase 4).

  calib_contrib.py decompose --contract FILE [--plan FILE] --theta FILE --observable NAME
                   --object variance|resolution [--effects NAME ...] [--bootstrap B] [--bootstrap-seed S]
                   [--permutations M] [--permutation-seed S]
One term per effect declared in the contract (`effects`: [{name, removal: {parameter: value after removal}}]),
removed through the evaluator's effects_off: Shapley terms over all 2^n subsets for n <= 10, permutation sampling
with its sampling error for n > 10; the terms sum to the total on every ordering. Every evaluated subset must pass
the ESS threshold of G4 (N_eff,k >= N_req,k), else no decomposition is output (status failed, finding contrib.ess).
Bootstrap covariances between the terms; the object (variance or resolution) is required and stated. Output: one JSON
object; ok (exit 0), failed (exit 1), rejected (exit 2), incomplete (exit 3: the evaluator cannot remove effects or
gives no per-event influence values). The engine (core/calibration/contrib.py) needs NumPy and SciPy.
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
    from core.calibration import contrib, evaluator, io
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if MISSING and "-h" not in (argv or sys.argv[1:]) and "--help" not in (argv or sys.argv[1:]):
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decompose", help="the section 10.5 decomposition at a parameter point")
    d.add_argument("--contract", required=True)
    d.add_argument("--plan")
    d.add_argument("--theta", required=True)
    d.add_argument("--observable", required=True)
    d.add_argument("--object", help="variance | resolution (required: section 10.5)")
    d.add_argument("--effects", nargs="+", help="a subset of the declared effects (default: all)")
    d.add_argument("--bootstrap", type=int, default=contrib.BOOTSTRAP_DEFAULT if not MISSING else 500)
    d.add_argument("--bootstrap-seed", type=int, default=contrib.SEED_DEFAULT if not MISSING else 0)
    d.add_argument("--permutations", type=int, default=contrib.PERMUTATIONS_DEFAULT if not MISSING else 200)
    d.add_argument("--permutation-seed", type=int, default=contrib.SEED_DEFAULT if not MISSING else 0)
    args = ap.parse_args(argv)

    def go():
        contract, plan, _ = io.contract_and_plan(args.contract, args.plan)
        theta = io.load(args.theta)
        if plan is None or not isinstance(theta, dict):
            raise io.InputError("--plan (or a fixture) and --theta (a JSON object) are needed")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in theta.values()):
            raise io.InputError("--theta: every value is a number")
        try:
            ev = evaluator.make(plan, contract)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except (KeyError, TypeError, ValueError) as exc:
            raise io.InputError(f"malformed plan: {exc!r}") from None
        unknown = set(theta) - set(ev.parameters)
        if unknown:
            raise io.InputError(f"unknown parameters {sorted(unknown)}")
        try:
            return contrib.decompose(ev, contract, theta, args.observable, args.object, args.effects,
                                     bootstrap=args.bootstrap, bootstrap_seed=args.bootstrap_seed,
                                     permutations=args.permutations, permutation_seed=args.permutation_seed)
        except contrib.ContribError as exc:
            if exc.status == "incomplete":
                return {"status": "incomplete", "finding": exc.code, "reason": str(exc)}
            raise io.InputError(f"{exc.code}: {exc}") from None
        except (KeyError, TypeError) as exc:
            raise io.InputError(f"malformed contract: {exc!r}") from None
    return io.run(lambda: io.jsonable(go()))


if __name__ == "__main__":
    sys.exit(main())
