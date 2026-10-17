#!/usr/bin/env python3
"""Unfolding through an external package (pyunfold, or RooUnfold through ROOT) with the plugin's own validation (S10).

Purpose: run iterative (D'Agostini) unfolding with a package the user already trusts, and validate the declared
regularization the same way the plugin validates its own: nominal closure, reweighted closure, stress tests and toy
coverage. The regularization (the number of iterations) is declared before running and is not tuned on the data.

Backends (optional; nothing is installed by this tool):
  pyunfold   pyunfold.iterative_unfold (MIT; pip install pyunfold), run for exactly --iterations iterations
             (ts_stopping disabled), uniform prior, multinomial covariance; statistical errors from pyunfold.
  roounfold  RooUnfoldBayes through PyROOT. RooUnfold is a separate package, not part of ROOT: build it from
             https://gitlab.cern.ch/RooUnfold/RooUnfold. Without it the run exits 3. This path is documented and has
             not been run in the plugin's test environments.
Conventions: response R[reco][truth] (rows reco, columns truth), column sums = efficiencies (inefficiency outside the
matrix, as core/stats/validate_response.py); data are counts per reco bin.

Subcommands:
  unfold        estimate, statistical errors and the backend version for measured data.
  validate      for a declared MC truth: nominal closure (unfold R t, compare with t), reweighted closure (a declared
                data-like reweighting), stress tests (more reweightings), each passing when every bin is within
                closure_tolerance (relative); toy coverage: Poisson toys of R t, the fraction of bins whose truth is
                inside estimate +- stat error, passing within coverage_tolerance of 0.6827. Any failure: exit 1.
  compare-core  pyunfold against the D'Agostini estimator of core/stats/unfolding_diagnostics.py for the same
                iterations (at most 60 bins, the core's limit): the largest relative difference; with at most 400
                response cells also the core's dagostini-unfold total uncertainty.

Input JSON: unfold / compare-core {"response": [[...]], "data": [...]}; validate {"response", "truth": [...],
"closure_tolerance": r, "coverage_tolerance": c, "reweighted_closure": {"name", "weights": [per truth bin]}
(optional), "stress_tests": [{"name", "weights"}, ...] (optional)}.
Output JSON: "status" (ok, failed, rejected, missing-dependency), "status_label", "inputs", "defaults_used",
"backend" {name, version}, "regularization" {iterations, rule}, and per subcommand "estimate", "stat_errors",
"checks" or "max_relative_difference"; "install" with a missing backend.
Exit codes: 0 ok; 1 a validation check failed; 2 bad input; 3 the backend (or NumPy) is missing.
Run: python3 <plugin root>/adapters/unfolding/assets/unfold.py unfold --input u.json --backend pyunfold --iterations 4
     python3 <plugin root>/adapters/unfolding/assets/unfold.py validate --input v.json --backend pyunfold
         --iterations 4 --toys 500 --seed 1
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
MAX_BINS_CORE = 60
COVERAGE = 0.6827
RULE = "the number of iterations is declared before the run and not tuned on the data being unfolded"
HINT = {"pyunfold": "pip install pyunfold (MIT license; https://github.com/jrbourbeau/pyunfold)",
        "roounfold": ("RooUnfold is not part of ROOT: build it from https://gitlab.cern.ch/RooUnfold/RooUnfold and run "
                      "with a Python whose PyROOT finds it")}


class InputError(ValueError):
    """A refused input (exit 2)."""


class MissingBackend(RuntimeError):
    def __init__(self, backend, detail):
        super().__init__(f"{backend} is not available: {detail}")
        self.backend = backend


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _response(np, doc):
    r = np.asarray(doc.get("response"), dtype=float)
    if r.ndim != 2 or min(r.shape) < 1 or not np.all(np.isfinite(r)) or np.any(r < 0):
        raise InputError("response must be a non-negative finite matrix [reco][truth]")
    eff = r.sum(axis=0)
    if np.any(eff <= 0) or np.any(eff > 1 + 1e-9):
        raise InputError("every truth column must have an efficiency (column sum) in (0, 1]")
    return r


def _counts(np, v, n, name):
    a = np.asarray(v, dtype=float)
    if a.shape != (n,) or not np.all(np.isfinite(a)) or np.any(a < 0):
        raise InputError(f"{name} must list {n} non-negative counts")
    return a


def unfold_pyunfold(np, r, data, iterations):
    try:
        import pyunfold
    except ImportError as exc:
        raise MissingBackend("pyunfold", str(exc)) from exc
    eff = r.sum(axis=0)
    res = pyunfold.iterative_unfold(data=data, data_err=np.sqrt(np.maximum(data, 0.0)), response=r,
                                    response_err=np.zeros_like(r), efficiencies=eff,
                                    efficiencies_err=np.zeros_like(eff), ts_stopping=-1.0, max_iter=iterations)
    return np.asarray(res["unfolded"]), np.asarray(res["stat_err"]), {"name": "pyunfold",
                                                                      "version": getattr(pyunfold, "__version__", "?")}


def unfold_roounfold(np, r, data, iterations):  # documented path; RooUnfold was not available where it was written
    try:
        import ROOT  # noqa: N811 (PyROOT)
        bayes = ROOT.RooUnfoldBayes
    except (ImportError, AttributeError) as exc:
        raise MissingBackend("roounfold", str(exc)) from exc
    n_reco, n_truth = r.shape
    resp = ROOT.RooUnfoldResponse(n_reco, 0.0, float(n_reco), n_truth, 0.0, float(n_truth))
    for j in range(n_truth):
        for i in range(n_reco):
            if r[i, j] > 0:
                resp.Fill(i + 0.5, j + 0.5, float(r[i, j]))
        miss = 1.0 - float(r[:, j].sum())
        if miss > 0:
            resp.Miss(j + 0.5, miss)
    meas = ROOT.TH1D("meas", "", n_reco, 0.0, float(n_reco))
    for i in range(n_reco):
        meas.SetBinContent(i + 1, float(data[i]))
        meas.SetBinError(i + 1, math.sqrt(max(float(data[i]), 0.0)))
    u = bayes(resp, meas, int(iterations))
    h = u.Hunfold()
    est = np.array([h.GetBinContent(j + 1) for j in range(n_truth)])
    err = np.array([h.GetBinError(j + 1) for j in range(n_truth)])
    return est, err, {"name": "roounfold", "version": f"ROOT {ROOT.gROOT.GetVersion()}"}


BACKENDS = {"pyunfold": unfold_pyunfold, "roounfold": unfold_roounfold}


def _closure(np, run, r, t, tol, name):
    est = run(r @ t)[0]
    rel = (est - t) / t
    return {"name": name, "max_relative_bias": float(np.max(np.abs(rel))), "relative_bias": rel.tolist(),
            "tolerance": tol, "pass": bool(np.max(np.abs(rel)) <= tol)}


def validate(np, doc, backend, iterations, toys, seed):
    r = _response(np, doc)
    t = _counts(np, doc.get("truth"), r.shape[1], "truth")
    if np.any(t <= 0):
        raise InputError("truth must be positive in every bin")
    tol, ctol = doc.get("closure_tolerance"), doc.get("coverage_tolerance")
    for v, k in ((tol, "closure_tolerance"), (ctol, "coverage_tolerance")):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v < 1:
            raise InputError(f"{k} must be a number in (0, 1) (no default)")

    def run(data):
        return BACKENDS[backend](np, r, data, iterations)[:2]
    checks = {"nominal_closure": _closure(np, run, r, t, tol, "nominal")}
    rw = doc.get("reweighted_closure")
    if rw is not None:
        w = _counts(np, rw.get("weights") if isinstance(rw, dict) else None, len(t), "reweighted_closure.weights")
        checks["reweighted_closure"] = _closure(np, run, r, t * w, tol, rw.get("name", "reweighted"))
    stress = []
    for s in doc.get("stress_tests") or []:
        w = _counts(np, s.get("weights") if isinstance(s, dict) else None, len(t), "stress_tests.weights")
        stress.append(_closure(np, run, r, t * w, tol, s.get("name", "stress")))
    checks["stress_tests"] = stress
    rng = np.random.default_rng(seed)
    mu = r @ t
    covered = total = 0
    for _ in range(toys):
        est, err = run(rng.poisson(mu).astype(float))
        covered += int(np.sum(np.abs(est - t) <= err))
        total += len(t)
    cov = covered / total
    checks["toy_coverage"] = {"coverage": cov, "target": COVERAGE, "tolerance": ctol, "toys": toys, "seed": seed,
                              "binomial_error": math.sqrt(COVERAGE * (1 - COVERAGE) / total),
                              "pass": bool(abs(cov - COVERAGE) <= ctol)}
    ok = all(c["pass"] for c in [checks["nominal_closure"], *stress, checks["toy_coverage"]]
             + ([checks["reweighted_closure"]] if "reweighted_closure" in checks else []))
    return ok, checks


def compare_core(np, doc, iterations):
    from core.stats import unfolding_diagnostics as ud
    r = _response(np, doc)
    if max(r.shape) > MAX_BINS_CORE:
        raise InputError(f"compare-core is limited to {MAX_BINS_CORE} bins (the core's limit)")
    data = _counts(np, doc.get("data"), r.shape[0], "data")
    est, err, info = unfold_pyunfold(np, r, data, iterations)
    # the core's D'Agostini estimator (the one behind closure and dagostini-unfold), uniform prior, same iterations
    run, _ = ud._estimator("dagostini", iterations, r.tolist(), None, None)
    ref = np.asarray(run(data.tolist()), dtype=float)
    diff = float(np.max(np.abs(est - ref) / np.maximum(np.abs(ref), 1e-300)))
    sigma = None
    if r.size <= 400:  # dagostini-unfold's covariance path is limited to 400 response cells
        sigma = ud.dagostini_unfold({"response": r.tolist(), "data": data.tolist()}, iterations).get("sigma_total")
    return info, {"estimate": est.tolist(), "core_estimate": ref.tolist(), "max_relative_difference": diff,
                  "core_sigma_total": sigma, "stat_errors": err.tolist()}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    u = sub.add_parser("unfold")
    v = sub.add_parser("validate")
    c = sub.add_parser("compare-core")
    for p in (u, v, c):
        p.add_argument("--input", required=True)
        p.add_argument("--iterations", type=int, required=True, help="declared before the run (no default)")
        add_status_argument(p)
    for p in (u, v):
        p.add_argument("--backend", required=True, choices=tuple(BACKENDS))
    v.add_argument("--toys", type=int, required=True)
    v.add_argument("--seed", type=int, required=True)
    args = ap.parse_args(argv)
    inputs = {k: val for k, val in vars(args).items() if k != "status"}
    given = {x.split("=")[0] for x in (sys.argv[1:] if argv is None else argv) if x.startswith("--")}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        if args.iterations < 1:
            raise InputError("--iterations must be >= 1")
        try:
            import numpy as np
        except ImportError as exc:
            raise MissingBackend("numpy", str(exc)) from exc
        doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise InputError("the input must be a JSON object")
        reg = {"iterations": args.iterations, "rule": RULE}
        if args.command == "unfold":
            r = _response(np, doc)
            data = _counts(np, doc.get("data"), r.shape[0], "data")
            est, err, info = BACKENDS[args.backend](np, r, data, args.iterations)
            body = {"backend": info, "regularization": reg, "estimate": est.tolist(), "stat_errors": err.tolist()}
        elif args.command == "validate":
            if args.toys < 1:
                raise InputError("--toys must be >= 1")
            ok, checks = validate(np, doc, args.backend, args.iterations, args.toys, args.seed)
            body = {"backend": {"name": args.backend}, "regularization": reg, "checks": checks}
            if not ok:
                status, body["reason"] = "failed", "a closure, stress or coverage check failed for the declared iterations"
        else:
            info, res = compare_core(np, doc, args.iterations)
            body = {"backend": info, "regularization": reg, **res}
        body["label"] = LABEL
    except MissingBackend as exc:
        status, body = "missing-dependency", {"error": str(exc), "install": HINT.get(exc.backend, "pip install numpy")}
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError, KeyError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **body}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
