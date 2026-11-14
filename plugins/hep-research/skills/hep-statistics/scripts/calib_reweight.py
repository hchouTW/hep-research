#!/usr/bin/env python3
"""Event weights of the simulator calibration workflow (Part B sections 3.6, 6.1; owner of the weights; G4 is
phase 2 and G4-L phase 5).

  calib_reweight.py weights --contract FILE [--plan FILE] --theta FILE
The weights of the section 3.6 formula at theta' (a JSON object of parameter values; the others at the generation
point) for the plan's reweighted parameters, with its proposal mixture: per run the Kish effective sample size, per
observable the N_eff over the events entering it (D41), the largest weight fraction, and the runs with missing support
(events not recorded at a reweighted node: zero suppression, filtering). With S_q empty and theta' at the generation
point every weight is 1. Output: one JSON object; ok (exit 0), failed (exit 1: missing support), rejected (exit 2),
incomplete (exit 3). The engine (core/calibration) needs NumPy and SciPy. Phase 1 (section 17).

  calib_reweight.py g4l --contract FILE [--plan FILE] [--points FILE] [--alpha A]
G4-L (phase 5, section 8.2): for a plan with a learned density ratio (one post-hoc correction node, section 6.2),
the held-out closure of every fold at >= 3 theta' (default P0's points), propagated to theta with A, in the form of P0;
the structural record (cross-fitting, probability calibration, prior-ratio correction) and the contract's alpha
declaration first. not-applicable without a learned ratio; passed (0), failed (1), rejected (2), incomplete (3).
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
    from core.calibration import design, evaluator, io, reweight
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if MISSING and "-h" not in (argv or sys.argv[1:]) and "--help" not in (argv or sys.argv[1:]):
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("weights")
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--theta", required=True)
    g = sub.add_parser("g4", help="G4 at a parameter point: N_eff,k >= N_req,k and Pareto k (section 6.7, D41)")
    g.add_argument("--contract", required=True)
    g.add_argument("--plan")
    g.add_argument("--theta", required=True)
    g.add_argument("--smoothed", action="store_true", help="PSIS-smoothed weights (Pareto k < 0.7)")
    gl = sub.add_parser("g4l", help="G4-L: the held-out closure of the learned density ratio (section 8.2, phase 5)")
    gl.add_argument("--contract", required=True)
    gl.add_argument("--plan")
    gl.add_argument("--points", help="JSON list of theta' objects (default: P0's points)")
    gl.add_argument("--alpha", type=float, help="tighter than the contract's alpha (never looser than 0.01)")
    args = ap.parse_args(argv)

    def go():
        contract, plan, _ = io.contract_and_plan(args.contract, args.plan)
        theta = io.load(args.theta) if args.cmd != "g4l" else {}
        if plan is None or not isinstance(theta, dict):
            raise io.InputError("--plan (or a fixture) and --theta (a JSON object) are needed")
        try:
            ev = evaluator.make(plan, contract)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except (KeyError, TypeError, ValueError) as exc:
            raise io.InputError(f"malformed plan: {exc!r}") from None
        if args.cmd == "g4l":
            return _g4l(ev, contract, plan, args)
        unknown = set(theta) - set(ev.parameters)
        if unknown:
            raise io.InputError(f"unknown parameters {sorted(unknown)}")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in theta.values()):
            raise io.InputError("--theta: every value is a number")
        if args.cmd == "g4":
            try:
                w, n_req, missing = design.g4_inputs(ev, contract, theta)
            except (KeyError, TypeError, ValueError) as exc:
                raise io.InputError(f"malformed contract: {exc!r}") from None
            r = reweight.g4(w, n_req, smoothed=args.smoothed)
            if missing:                                   # an event not recorded at a reweighted node fails G4
                r.update(status="failed", finding="g4.missing_support", missing_support_runs=missing)
            return r
        target = {**ev.model.nominal, **theta}
        w = ev.weights(target, nodes=ev.reweighted_nodes(target))
        missing = w.pop("_missing_support", [])
        runs = reweight.summary(w)
        r = ev.evaluate(theta)
        out = {"status": "failed" if missing else "ok", "runs": runs,
               "n_eff": dict(zip(r["names"], r["n_eff"])), "missing_support_runs": missing,
               "reweighted_nodes": ev.reweighted_nodes(target)}
        if getattr(ev, "_learned_spec", None) is not None:      # phase 5: n_eff includes the learned ratio
            out["learned_record"] = ev.learned_record()
        return out
    return io.run(lambda: io.jsonable(go()))


def _g4l(ev, contract, plan, args):
    from core.calibration import design as design_mod
    from core.calibration import kernel_check, learned, linear
    methods = {p: ev.default_method(p) for p in ev.parameters}
    if design_mod.applicability(methods)["gates"]["G4-L"] != "applicable":
        return {"gate": "G4-L", "status": "not-applicable", "reason": "the plan has no learned density ratio "
                "(section 8.1)"}
    if args.alpha is not None and not 0 < args.alpha <= reweight.G4L_ALPHA:
        raise io.InputError(f"--alpha {args.alpha}: 0 < alpha <= {reweight.G4L_ALPHA}")
    try:
        d = linear.design(ev, contract, plan)
        if args.points:
            pts = io.load(args.points)
            if not isinstance(pts, list) or not all(isinstance(p, dict) for p in pts):
                raise io.InputError("--points: a JSON list of theta' objects")
        else:
            pts = kernel_check.default_points(ev, contract, plan)
        alpha = None if args.alpha is None else min(args.alpha, reweight.g4l_alpha(contract))
        return reweight.g4l_run(ev, contract, d, pts, alpha)
    except learned.LearnedError as exc:
        return {"gate": "G4-L", "status": "rejected", "finding": exc.code, "findings": [{"code": exc.code,
                "message": str(exc)}]}
    except (linear.DesignError, KeyError, TypeError) as exc:
        raise io.InputError(f"malformed contract or plan: {exc!r}") from None


if __name__ == "__main__":
    sys.exit(main())
