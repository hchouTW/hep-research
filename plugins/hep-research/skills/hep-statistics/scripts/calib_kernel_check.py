#!/usr/bin/env python3
"""P0, kernel consistency (simulator calibration workflow, Part B section 8.2 note 1, D53; owner of P0).

  calib_kernel_check.py p0 --contract FILE [--plan FILE] [--release FILE] [--points FILE] [--seed S]
At >= 3 theta' (the worst-ESS point of the P5 scan and the next two scan points unless --points gives a JSON list of
theta' objects), the plan's non-full-resimulation prediction is compared with resample + evaluate_from, propagated to
theta with the design-stage A: |Delta theta_i| <= 0.1 sigma_tot,i^design + z sigma_MC(Delta theta_i), z two-sided
Bonferroni over d x (number of theta') at alpha = 0.01. Output: one JSON object; passed (exit 0), not-applicable
(exit 0: the plan uses no P0 method, section 8.1), failed (exit 1, remedy level plan, contract if the kernel semantics
are wrong), rejected (exit 2), incomplete (exit 3). Results carry provisional-thresholds (sigma_tot^design without
Sigma_boot, phase 2). The engine (core/calibration) needs NumPy and SciPy. Phase 1
(section 17).
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

from core.calibration import design, evaluator, io, kernel_check, linear



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("p0")
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--release")
    p.add_argument("--points")
    p.add_argument("--seed", type=int)
    args = ap.parse_args(argv)

    def go():
        contract, plan, extras = io.contract_and_plan(args.contract, args.plan)
        if plan is None:
            raise io.InputError("--plan is needed (or a fixture with a plan)")
        try:
            ev = evaluator.make(plan, contract)
            d = linear.design(ev, contract, plan, systematics=io.systematics(args.release, extras))
            if args.points:
                pts = io.load(args.points)
                if not isinstance(pts, list) or not all(isinstance(x, dict) for x in pts):
                    raise io.InputError("--points: a JSON list of theta' objects")
            else:
                pts = kernel_check.worst_ess_and_next(design.p5(ev, contract, plan, items=("ess",)))
            seed = args.seed if args.seed is not None else int((plan.get("seeds") or {}).get("resample", 20261111))
            return kernel_check.p0(ev, contract, plan, d, pts, seed)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except linear.DesignError as exc:
            st = "incomplete" if exc.code in ("linear.incomplete", "linear.singular") else "rejected"
            return {"status": st, "code": exc.code, "reason": str(exc)}
        except design.CheckError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except (KeyError, TypeError, ValueError) as exc:
            raise io.InputError(f"malformed contract, plan or points: {exc!r}") from None
    return io.run(lambda: io.jsonable(go()))


if __name__ == "__main__":
    sys.exit(main())
