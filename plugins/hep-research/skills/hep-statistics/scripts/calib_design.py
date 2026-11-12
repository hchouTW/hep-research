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
                                [--declared-methods]
  calib_design.py methods       --contract FILE [--plan FILE]
Phase 2 (sections 2.1 (iii), 6.6, 8.2 notes 3 and 5, 9.3, 9.4; the engine in core/calibration/design_noise.py):
  calib_design.py sigma-boot    --contract FILE --plan FILE --values FILE [--release FILE] [--n-t 10] [--k-b 6]
                                [--seed S] [--sigma-data FILE]   Sigma_boot by toys; with --sigma-data its P5 item
  calib_design.py bj            --points FILE [--bound B]          P5's b_J item ({J, W, K: [K_l], sigma_tot} per point)
  calib_design.py p7            --input FILE                       P7 at the design stage (analytic or toy path)
  calib_design.py folds         --contract FILE --folds FILE [--plan FILE --values FILE]
                                                                   the fold-split rules, and P3 of each training fold
  calib_design.py practices     --plan FILE                        rejected toy, bootstrap and G8 practices
  calib_design.py seeds         --uses FILE                        independence of seeds across uses
Phase 3 (sections 6.1, 6.6, 14.1 with g4sim; the engine in core/calibration/design_g4sim.py):
  calib_design.py g4sim-support --contract FILE --plan FILE --documents FILE   support and recording levels (section 6.1)
  calib_design.py intervals     --plan FILE      event intervals, run_seed, replica 0, seed blocks, one digitization path
  calib_design.py digi-jobs     --plan FILE --documents FILE [--contract FILE] every g4sim-digi-job/1 of the plan
  calib_design.py pde-split     --contract FILE --plan FILE --documents FILE   the PDE split of section 6.7 (routes,
                                route 1, keys, EFFICIENCY > 0, photons.csv, energy grid, scan surfaces, split check)
--documents: {detector, request, run, pipeline, maps: {name: map}, conditions}, each an object or a path relative to it;
for pde-split {detector, detectors: {name}, maps: {name}, photons: {name}, primaries: {name}, pipelines: [..], readouts,
build_environment} (detector specs and CSV files read as text).
FILE is a calibration-contract/1 and a calibration-plan/1, or a calibration-fixture/1 with both; --release a
calibration data release whose `systematic` component gives the eta columns (the sealed components are never read).
Output: one JSON object; status passed/ok (exit 0), failed (exit 1: P2, P5 or support failed, remedy level in the
findings), rejected (exit 2: input error, e.g. a P5 request on a tail-type functional, approval A7), incomplete (exit
3: phase-2 or phase-3 content, or no evaluator of the plan's kind). p5 first decides the final method (section 3.6
step 2: an infeasible reweighting moves to the next tier) and judges the P5 items with it; --declared-methods judges
the plan's declared methods as they are. Results that use f = 0.1 or sigma_tot^design
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
import json
import sys

try:
    MISSING = None
    import numpy as np
    from core.calibration import design, design_g4sim as DG, design_noise as DN, evaluator, io, linear, problems
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)


def linearization_summary(d):
    return {"theta": d["theta"], "theta_ref": d["theta_ref"], "observables": d["names"], "links": d["links"],
            "sigma_tot": d["sigma_tot"], "lambda_max": d["lambda_max"], "n_nu": d["n_nu"], "n_eta": d["n_eta"],
            "n_phi": d["n_phi"], "psi_effect": d["psi_effect"], "A_theta": d["A_theta"], "mu": d["mu"],
            "flags": d["flags"], "note": d["sigma_tot_note"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if MISSING and "-h" not in (argv or sys.argv[1:]) and "--help" not in (argv or sys.argv[1:]):
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    sb = sub.add_parser("sigma-boot")
    for a in ("--contract", "--plan", "--values"):
        sb.add_argument(a, required=True)
    sb.add_argument("--release")
    sb.add_argument("--n-t", type=int, default=10)
    sb.add_argument("--k-b", type=int, default=6)
    sb.add_argument("--seed", type=int, default=20261160)
    sb.add_argument("--sigma-data")
    bj = sub.add_parser("bj")
    bj.add_argument("--points", required=True)
    bj.add_argument("--bound", type=float, default=None)
    sub.add_parser("p7").add_argument("--input", required=True)
    fo = sub.add_parser("folds")
    fo.add_argument("--contract", required=True)
    fo.add_argument("--folds", required=True)
    fo.add_argument("--plan")
    fo.add_argument("--values")
    sub.add_parser("practices").add_argument("--plan", required=True)
    sub.add_parser("seeds").add_argument("--uses", required=True)
    gs = sub.add_parser("g4sim-support")
    for a in ("--contract", "--plan", "--documents"):
        gs.add_argument(a, required=True)
    sub.add_parser("intervals").add_argument("--plan", required=True)
    pd = sub.add_parser("pde-split")
    for a in ("--contract", "--plan", "--documents"):
        pd.add_argument(a, required=True)
    dj = sub.add_parser("digi-jobs")
    dj.add_argument("--plan", required=True)
    dj.add_argument("--documents", required=True)
    dj.add_argument("--contract", help="the contract whose locked bindings the plan must agree with")
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
            p.add_argument("--declared-methods", action="store_true")
    args = ap.parse_args(argv)

    def phase2():
        try:
            if args.cmd == "bj":
                pts = io.load(args.points)
                if not isinstance(pts, list):
                    raise io.InputError("--points: a list of {J, W, K, sigma_tot}")
                arr = [{"J": np.asarray(p["J"], float), "W": np.asarray(p["W"], float),
                        "K": [np.asarray(k, float) for k in p["K"]], "sigma_tot": np.asarray(p["sigma_tot"], float)}
                       for p in pts]
                if args.bound is not None and args.bound > DN.JACOBIAN_BIAS_BOUND:
                    raise io.InputError(f"--bound may only tighten {DN.JACOBIAN_BIAS_BOUND} (approval A9)")
                r = DN.p5_b_J(arr, **({} if args.bound is None else {"bound": args.bound}))
                return {"status": "passed" if r["passed"] else "failed", **r}
            if args.cmd == "p7":
                x = io.load(args.input)
                if not isinstance(x, dict) or "mode" not in x or "path" not in x:
                    raise io.InputError("--input: {mode, k0, path, alternatives | toy_results, k?, alpha?}")
                alts = {a: (None if v is None else np.asarray(v, float)) for a, v in (x.get("alternatives") or {}).items()}
                return DN.p7(x["mode"], int(x.get("k0", 0)), alts, x["path"], x.get("k"), float(x.get("alpha", 0.05)),
                             x.get("toy_results"))
            if args.cmd == "practices":
                f = DN.practice_findings(io.load(args.plan))
                return {"status": "failed" if f else "ok", "findings": f}
            if args.cmd == "seeds":
                f = DN.seed_independence(io.load(args.uses))
                return {"status": "failed" if f else "ok", "findings": f}
            contract, plan, extras = io.contract_and_plan(args.contract, args.plan)
            if args.cmd == "folds":
                folds = io.load(args.folds)
                if not isinstance(folds, dict):
                    raise io.InputError("--folds: {observable: fold}")
                f = DN.fold_split_check(contract, folds)
                if args.values:
                    p = problems.from_inputs(contract, plan, io.load(args.values), None)
                    names = p.names if hasattr(p, "names") else list(folds)
                    by = {}
                    for o, fi in folds.items():
                        if o in names:
                            by.setdefault(fi, []).append(names.index(o))
                    f += DN.fold_p3(p, [np.array(v) for _, v in sorted(by.items())], p.initial_beta())
                return {"status": "failed" if f else "ok", "findings": f}
            # sigma-boot
            p = problems.from_inputs(contract, plan, io.load(args.values), io.systematics(args.release, extras))
            r = DN.sigma_boot(p, p.initial_beta(), args.seed, N_t=args.n_t, K_b=args.k_b)
            if r["status"] == "ok":
                d = len(p.layout.theta)
                r["Sigma_boot_theta"] = np.asarray(r["Sigma_boot"])[:d, :d]
                if args.sigma_data:
                    it = DN.p5_sigma_boot(r["Sigma_boot_theta"], r["w"], np.asarray(io.load(args.sigma_data), float))
                    r.update(status="passed" if it["passed"] else "failed", p5=it)
                else:
                    r["p5"] = {"item": "sigma_boot", "status": "not-decided", "reason": "no --sigma-data"}
            return {**r, "flags": ["provisional-thresholds"]}
        except DN.DesignError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except problems.ProblemError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except (KeyError, TypeError, ValueError) as exc:
            raise io.InputError(f"malformed input: {exc!r}") from None

    def documents(path):
        from pathlib import Path
        docs = io.load_object(path)
        base = Path(path).resolve().parent
        out = {}
        for k, v in docs.items():
            if k == "maps":
                if not isinstance(v, dict):
                    raise io.InputError("--documents: maps is {name: map}")
                out[k] = {m: io.load(str(base / x)) if isinstance(x, str) else x for m, x in v.items()}
            else:
                out[k] = io.load(str(base / v)) if isinstance(v, str) else v
        return out

    def phase3():
        try:
            plan = io.load_object(args.plan)
            if args.cmd == "intervals":
                return DG.interval_findings(plan)
            docs = documents(args.documents)
            if args.cmd == "digi-jobs":
                f = DG.digi_job_findings(plan, docs, io.load_object(args.contract) if args.contract else None)
                return {"status": "failed" if f else "passed", "findings": f, "jobs": len(plan.get("digi_jobs") or [])}
            contract = io.load_object(args.contract)
            return DG.support_g4sim(contract, plan, docs)
        except DG.CheckError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise io.InputError(f"malformed input: {exc!r}") from None

    def pde():
        from pathlib import Path
        from contracts.geometry import field_types
        from core.calibration import pde_split
        spec = io.load_object(args.documents)
        base = Path(args.documents).resolve().parent

        def text(x):
            try:
                return (base / str(x)).read_text(encoding="utf-8")
            except OSError as exc:
                raise io.InputError(f"--documents: {x}: {exc.strerror or exc}") from None
        docs = {"readouts": spec.get("readouts") or [], "build_environment": spec.get("build_environment")}
        if spec.get("detector"):
            docs["detector"] = text(spec["detector"])
        for k in ("detectors", "photons", "primaries"):
            docs[k] = {n: text(v) for n, v in (spec.get(k) or {}).items()}
        docs["maps"] = {n: io.load_object(str(base / v)) for n, v in (spec.get("maps") or {}).items()}
        docs["pipelines"] = [io.load_object(str(base / v)) for v in spec.get("pipelines") or []]
        try:
            return pde_split.design_findings(io.load_object(args.contract), io.load_object(args.plan), docs,
                                             field_types())
        except pde_split.SplitError as exc:
            return {"status": "rejected", "code": "pde_split." + exc.code, "error": str(exc)}
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise io.InputError(f"malformed input: {exc!r}") from None

    def go():
        if args.cmd == "pde-split":
            return pde()
        if args.cmd in ("g4sim-support", "intervals", "digi-jobs"):
            return phase3()
        if args.cmd in ("sigma-boot", "bj", "p7", "folds", "practices", "seeds"):
            return phase2()
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
                syst = io.systematics(getattr(args, 'release', None), extras)
                r = (design.p5(ev, contract, plan, syst, items=items) if args.declared_methods else
                     design.p5_with_final_methods(ev, contract, plan, syst, items=items))
                r.pop("per_point", None)
                return r
            if args.cmd == "methods":
                return design.final_methods(ev, contract, plan)
        except evaluator.EvaluatorUnavailable as exc:
            return {"status": "incomplete", "reason": str(exc)}
        except linear.DesignError as exc:
            if exc.code == "linear.missing_support":
                return {"status": "failed", "findings": [{"code": exc.code, "message": str(exc)}]}
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
