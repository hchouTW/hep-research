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

from core.calibration import evaluator, io, reweight



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("weights")
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--theta", required=True)
    args = ap.parse_args(argv)

    def go():
        contract, plan, _ = io.contract_and_plan(args.contract, args.plan)
        theta = io.load(args.theta)
        if plan is None or not isinstance(theta, dict):
            raise io.InputError("--plan (or a fixture) and --theta (a JSON object) are needed")
        try:
            ev = evaluator.make(plan, contract)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        unknown = set(theta) - set(ev.parameters)
        if unknown:
            raise io.InputError(f"unknown parameters {sorted(unknown)}")
        target = {**ev.model.nominal, **theta}
        w = ev.weights(target, nodes=ev.reweighted_nodes(target))
        missing = w.pop("_missing_support", [])
        runs = reweight.summary(w)
        r = ev.evaluate(theta)
        return {"status": "failed" if missing else "ok", "runs": runs,
                "n_eff": dict(zip(r["names"], r["n_eff"])), "missing_support_runs": missing,
                "reweighted_nodes": ev.reweighted_nodes(target)}
    return io.run(lambda: io.jsonable(go()))


if __name__ == "__main__":
    sys.exit(main())
