#!/usr/bin/env python3
"""Design-stage checks of the simulator calibration workflow (Part B sections 3.6, 6.1, 6.4, 6.7, 8.1, 8.2; owner of
the Sobol design points and the P6 held-back set, P2, P5 with feasibility and the final method, the support condition
and the applicability of the mandatory gates).

  calib_design.py points        --contract FILE [--plan FILE] --n N --seed S [--held-back H]
  calib_design.py p2            --contract FILE
  calib_design.py applicability --plan FILE [--held-back H] [--shift-phi]
  calib_design.py linearize     --contract FILE [--plan FILE] [--release FILE]
  calib_design.py support       --contract FILE [--plan FILE] [--parameter P ...]
  calib_design.py p5            --contract FILE [--plan FILE] [--release FILE] [--items ess,v_mc_diagonal,...]
  calib_design.py methods       --contract FILE [--plan FILE]
FILE is a calibration-contract/1 and a calibration-plan/1, or a calibration-fixture/1 with both; --release a
calibration data release whose `systematic` component gives the eta columns (the sealed components are never read).
Output: one JSON object; status passed/ok (exit 0), failed (exit 1: P2, P5 or support failed, remedy level in the
findings), rejected (exit 2: input error, e.g. a P5 request on a tail-type functional, approval A7), incomplete (exit
3: phase-2 or phase-3 content, or no evaluator of the plan's kind). Results that use f = 0.1 or sigma_tot^design
carry provisional-thresholds. The engine (core/calibration) needs NumPy and SciPy. Phase 1
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

from core.calibration import design, evaluator, io, linear


def linearization_summary(d):
    return {"theta": d["theta"], "theta_ref": d["theta_ref"], "observables": d["names"], "links": d["links"],
            "sigma_tot": d["sigma_tot"], "lambda_max": d["lambda_max"], "n_nu": d["n_nu"], "n_eta": d["n_eta"],
            "n_phi": d["n_phi"], "psi_effect": d["psi_effect"], "A_theta": d["A_theta"], "mu": d["mu"],
            "flags": d["flags"], "note": d["sigma_tot_note"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("points", "p2", "applicability", "linearize", "support", "p5", "methods"):
        p = sub.add_parser(name)
        if name != "applicability":
            p.add_argument("--contract", required=True)
        p.add_argument("--plan")
        if name == "points":
            p.add_argument("--n", type=int, required=True)
            p.add_argument("--seed", type=int, required=True)
            p.add_argument("--held-back", type=int, default=0)
        if name == "applicability":
            p.add_argument("--held-back", type=int, default=0)
            p.add_argument("--shift-phi", action="store_true")
        if name in ("linearize", "p5"):
            p.add_argument("--release")
        if name == "support":
            p.add_argument("--parameter", action="append", default=[])
        if name == "p5":
            p.add_argument("--items", default="ess,v_mc_diagonal,matrix_condition")
    args = ap.parse_args(argv)

    def go():
        if args.cmd == "applicability":
            plan = io.load(args.plan) if args.plan else None
            if not isinstance(plan, dict):
                raise io.InputError("--plan: a calibration-plan/1 object")
            return {"status": "ok", **design.applicability(plan.get("methods") or {}, args.held_back, args.shift_phi)}
        contract, plan, extras = io.contract_and_plan(args.contract, args.plan)
        try:
            if args.cmd == "points":
                bounds = {p["name"]: p["sampling_bounds"] for p in contract.get("parameters", [])
                          if p["role"] == "theta" and p.get("sampling_bounds")}
                return {"status": "ok", **design.design_points(bounds, args.n, args.seed, args.held_back)}
            if args.cmd == "p2":
                return design.p2(contract)
            if plan is None:
                raise io.InputError("--plan is needed (or a fixture with a plan)")
            ev = evaluator.make(plan, contract)
            if args.cmd == "linearize":
                d = linear.design(ev, contract, plan, systematics=io.systematics(getattr(args, 'release', None), extras))
                return {"status": "ok", **linearization_summary(d)}
            if args.cmd == "support":
                pars = args.parameter or [p for p in ev.parameters if ev.default_method(p) in design.REWEIGHTING]
                return design.support_check(ev, contract, plan, pars)
            if args.cmd == "p5":
                items = tuple(x for x in args.items.split(",") if x)
                unknown = set(items) - {"ess", "v_mc_diagonal", "matrix_condition"}
                if unknown:
                    raise io.InputError(f"unknown P5 items {sorted(unknown)}")
                r = design.p5(ev, contract, plan, io.systematics(getattr(args, 'release', None), extras), items=items)
                r.pop("per_point", None)
                return r
            if args.cmd == "methods":
                return design.final_methods(ev, contract, plan)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except linear.DesignError as exc:
            if exc.code in ("linear.incomplete", "linear.singular"):
                return {"status": "incomplete", "code": exc.code, "reason": str(exc)}
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except design.CheckError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except (KeyError, TypeError, ValueError) as exc:
            raise io.InputError(f"malformed contract or plan: {exc!r}") from None
        raise io.InputError(f"unknown command {args.cmd}")
    return io.run(lambda: io.jsonable(go()))


if __name__ == "__main__":
    sys.exit(main())
