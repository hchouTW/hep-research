#!/usr/bin/env python3
"""The surrogate model of the simulator calibration workflow (Part B sections 6.4, 6.5, 7.1, 8.2 note 4; owner of the
training set, P6, V_emu, the surrogate domain and the ask/tell state file; the engine is core/calibration/emulator.py).

  calib_emulator.py init    --contract FILE [--plan FILE] --purpose training|held-back --out STATE
  calib_emulator.py ask     --state STATE [--n N]            the next evaluations to submit (marked submitted)
  calib_emulator.py tell    --state STATE --results FILE     record {run_id: {names, pred, V_MC}}
  calib_emulator.py train   --contract FILE [--plan FILE] [--state STATE] [--out MODEL]
  calib_emulator.py p6      --contract FILE [--plan FILE] [--names a,b]  |  p6 --input FILE
  calib_emulator.py domain  --model MODEL
  calib_emulator.py spot-check-plan --training-state STATE --points FILE --seeds FILE --out STATE
  calib_emulator.py spot-check      --state STATE --model MODEL --v-data FILE
FILE is a calibration-contract/1 and a calibration-plan/1, or a calibration-fixture/1 with both; the surrogate settings
are the plan's design.surrogate (parameters, n_design, held_back, seed, mode interpolate|regression, spot_checks). The
design points and the held-back set are calib_design.py's (D80). STATE is a calibration-ask-tell/1 state file: one
entry per evaluation with its run_id, parameter point and seeds (common random numbers of the scan, section 6.6).
train without --state evaluates the training points with the plan's evaluator through ask/tell; with --state it fits
the completed state. p6 with --contract trains, evaluates the held-back points with full simulation and decides P6
(|Delta m| <= 0.3 sqrt(V^unc_data) + z sigma_Delta, z = z_{1-alpha/(2M)}, alpha = 0.01; the pull chi2 only with >= 30
held-out points); with --input it decides P6 on given arrays ({v_data, points: [{delta_m, cov_delta | delta_replicas,
V_emu}]}). spot-check-plan and spot-check are the G8 hook of approval A12 (section 19-5): a full-simulation spot check
at the injection points with seeds independent of the training set; its decision rule is the author's, so spot-check
answers not-decided (exit 3) with the P6-form statistics. Output: one JSON object; status passed/ok/written (exit 0),
failed (exit 1, remedy level plan), rejected (exit 2: bad input, a query outside the surrogate domain, a missing
spot-check point), incomplete/not-decided (exit 3). Results using alpha = 0.01 carry provisional-thresholds. Needs
NumPy and SciPy.
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
    from core.calibration import emulator as EM, evaluator, io, linear
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)

MODEL_KEYS = ("parameters", "bounds", "points", "values", "length", "nugget")


def _contract_plan(args):
    contract, plan, _ = io.contract_and_plan(args.contract, args.plan)
    if not isinstance(plan, dict):
        raise io.InputError("no plan: give --plan or a calibration-fixture/1 with one")
    return contract, plan


def _summary(sur):
    return {"parameters": sur.parameters, "mode": sur.mode, "trend": sur.trend, "length": sur.length.tolist(),
            "nugget": sur.nugget, "n_training": len(sur.points), "observables": sur.names, "domain": sur.domain(),
            "interpolates_exactly": sur.interpolates_exactly}


def _model(path):
    rec = io.load_object(path, MODEL_KEYS)
    try:
        return EM.Surrogate.from_record(rec)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        if isinstance(exc, EM.EmulatorError):
            raise
        raise io.InputError(f"{path}: not a surrogate record ({exc})") from None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if MISSING and "-h" not in (argv or sys.argv[1:]) and "--help" not in (argv or sys.argv[1:]):
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--purpose", choices=("training", "held-back"), required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("ask")
    p.add_argument("--state", required=True)
    p.add_argument("--n", type=int)
    p = sub.add_parser("tell")
    p.add_argument("--state", required=True)
    p.add_argument("--results", required=True)
    p = sub.add_parser("train")
    p.add_argument("--contract", required=True)
    p.add_argument("--plan")
    p.add_argument("--state")
    p.add_argument("--out")
    p = sub.add_parser("p6")
    p.add_argument("--contract")
    p.add_argument("--plan")
    p.add_argument("--names")
    p.add_argument("--input")
    sub.add_parser("domain").add_argument("--model", required=True)
    p = sub.add_parser("spot-check-plan")
    for a in ("--training-state", "--points", "--seeds", "--out"):
        p.add_argument(a, required=True)
    p = sub.add_parser("spot-check")
    for a in ("--state", "--model", "--v-data"):
        p.add_argument(a, required=True)
    args = ap.parse_args(argv)

    def go():
        try:
            return dispatch(args)
        except EM.EmulatorError as exc:
            raise io.InputError(f"{exc.code}: {exc}") from None
        except linear.DesignError as exc:
            if exc.code == "linear.incomplete":
                return {"status": "incomplete", "code": exc.code, "reason": str(exc)}
            raise io.InputError(f"{exc.code}: {exc}") from None
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except io.InputError:
            raise
        except (KeyError, TypeError, IndexError, AttributeError, ValueError) as exc:   # malformed input, no traceback
            raise io.InputError(f"malformed input: {type(exc).__name__}: {exc}") from None
    return io.run(lambda: io.jsonable(go()))


def dispatch(args) -> dict:
    if args.cmd == "init":
        contract, plan = _contract_plan(args)
        cfg = EM.settings(contract, plan)
        pts = EM.design(cfg)
        names = [o["name"] for o in linear.calibration_observables(contract)]
        seeds = {"nominal": (plan.get("seeds") or {}).get("nominal")}
        key = "training" if args.purpose == "training" else "held_back"
        st = EM.new_state(pts[key], args.purpose, cfg["theta_ref"], seeds, names)
        io.write_json(args.out, st)
        return {"status": "written", "state": args.out, "n": len(st["entries"]), "purpose": args.purpose}
    if args.cmd == "ask":
        st = io.load_object(args.state, ("schema", "entries"))
        reqs = EM.ask(st, args.n)
        io.write_json(args.state, io.jsonable(st))
        return {"status": "ok", "requests": reqs}
    if args.cmd == "tell":
        st = io.load_object(args.state, ("schema", "entries"))
        res = io.load_object(args.results)
        for rid, r in res.items():
            if not isinstance(r, dict):
                raise io.InputError(f"--results: {rid}: a result object {{names, pred, V_MC}}")
            EM.tell(st, rid, r)
        io.write_json(args.state, io.jsonable(st))
        return {"status": "ok", "recorded": sorted(res), "complete": EM.complete(st)}
    if args.cmd == "train":
        contract, plan = _contract_plan(args)
        cfg = EM.settings(contract, plan)
        if args.state:
            sur = EM.surrogate_from_state(io.load_object(args.state, ("schema", "entries")), cfg)
        else:
            tr = EM.training_set(evaluator.make(plan, contract), contract, plan)
            if tr["status"] != "ok":
                return {"status": "incomplete", "reason": tr["reason"], "outstanding": tr["outstanding"]}
            sur = tr["surrogate"]
        if args.out:
            io.write_json(args.out, io.jsonable(sur.record()))
        return {"status": "ok", "surrogate": _summary(sur), "model": args.out}
    if args.cmd == "p6":
        if args.input:
            return EM.p6_from_input(io.load_object(args.input, ("points", "v_data")))
        if not args.contract:
            raise io.InputError("p6: --contract (with the plan's evaluator) or --input")
        contract, plan = _contract_plan(args)
        names = args.names.split(",") if args.names else None
        r = EM.p6_from_evaluator(evaluator.make(plan, contract), contract, plan, names=names)
        r.pop("state", None)
        return r
    if args.cmd == "domain":
        sur = _model(args.model)
        return {"status": "ok", "domain": sur.domain(), "interpolates_exactly": sur.interpolates_exactly}
    if args.cmd == "spot-check-plan":
        tr = io.load_object(args.training_state, ("schema", "entries"))
        pts = io.load(args.points)
        seeds = io.load(args.seeds)
        if not isinstance(pts, list) or not isinstance(seeds, list):
            raise io.InputError("--points and --seeds: lists (one seed block per injection point)")
        st = EM.spot_check_plan(pts, tr, seeds, names=tr.get("names"))
        io.write_json(args.out, st)
        return {"status": "written", "state": args.out, "n": len(st["entries"])}
    if args.cmd == "spot-check":
        return EM.spot_check_record(io.load_object(args.state, ("schema", "entries")), _model(args.model),
                                    v_data=io.load(args.v_data))
    raise io.InputError(f"unknown command {args.cmd}")


if __name__ == "__main__":
    sys.exit(main())
