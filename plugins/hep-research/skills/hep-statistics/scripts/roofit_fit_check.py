#!/usr/bin/env python3
"""RooFit fit checks: map a saved RooFitResult to the statistical-result status, and require a declared error
treatment for weighted data (S11, status mapping).

Purpose: a RooFit fit that returned is not a fit that converged. This reads what MINUIT reported and refuses to call
a fit ok unless every criterion holds, so a RooFit result enters result_artifact.py with an honest status.

Subcommands:
  result    --file F.root --name NAME --edm-max X: reads the RooFitResult NAME (fitTo(..., Save(true)) written to a
            TFile). ok only when the minimizer status is 0, covQual is 3 (full, accurate covariance) and the EDM is at
            most --edm-max (no default: state the threshold your minimizer settings imply; MINUIT's own stopping rule
            depends on the tolerance and the error definition). Otherwise failed, with every reason, never ok.
            Reports the status history (MIGRAD/MINIMIZE, HESSE, MINOS codes), covQual, EDM, minimum NLL, the final
            parameters with their errors (asymmetric when MINOS ran), method_kind (minos when a floating parameter
            has an asymmetric error, else hesse) and paradigm (frequentist) for result_artifact.py.
  weighted  [--file F.root --dataset NAME | --weighted] [--weighted-errors sumw2|asymptotic|sweights]: weighted data
            need a declared treatment of the weights in the uncertainties; without one the run is incomplete (exit 3).
            asymptotic -> RooFit AsymptoticError(true) (the sandwich estimate; weights treated as known constants);
            sumw2 -> SumW2Error(true) (same caveat; only for known, constant per-event weights); sweights -> the fit
            needs the sPlot correction: use <plugin root>/skills/hep-statistics/scripts/sweighted_fit.py.
            See <plugin root>/skills/hep-statistics/references/likelihood-fitting.md.
Validity: RooFit results from ROOT 6 (RooFitResult::status, covQual, edm, statusCodeHistory). The check reads what the
fit recorded; it does not refit or test coverage.
Output JSON: "status" (run status, core/status.py), "status_label" (--status, default unvalidated), "inputs",
"defaults_used", and for result "fit_diagnostics", "parameters", "method_kind", "paradigm", "reasons".
Exit codes: 0 ok; 1 the fit is failed; 2 bad input (unreadable file, unknown object, bad threshold); 3 PyROOT
missing (install hint), or weighted data without --weighted-errors.
Run: python3 <plugin root>/skills/hep-statistics/scripts/roofit_fit_check.py result --file fit.root --name fitresult --edm-max 1e-3
     python3 <plugin root>/skills/hep-statistics/scripts/roofit_fit_check.py weighted --weighted --weighted-errors asymptotic
Standard library only (PyROOT for reading ROOT files).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

ROOT_HINT = ("PyROOT is needed to read ROOT files: install ROOT (conda install -c conda-forge root, or LCG/Homebrew) and "
             "run with a Python that can `import ROOT`")
ERRORS = {
    "sumw2": {"roofit_option": "SumW2Error(true)",
              "caveat": "treats the weights as known constants; correct only for known, constant per-event weights "
                        "(see likelihood-fitting.md)"},
    "asymptotic": {"roofit_option": "AsymptoticError(true)",
                   "caveat": "the sandwich estimate; treats the weights as known constants, so weights estimated from "
                             "data (sWeights) need the sPlot correction instead"},
    "sweights": {"roofit_option": None,
                 "caveat": "sWeights are estimated from data: the fit uncertainty needs the sPlot correction",
                 "next": "use <plugin root>/skills/hep-statistics/scripts/sweighted_fit.py"},
}


class InputError(ValueError):
    """Bad input: exit 2."""


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def load_root():
    try:
        import ROOT  # noqa: N811 (PyROOT)
    except ImportError as exc:
        return None, str(exc)
    ROOT.gErrorIgnoreLevel = ROOT.kError
    return ROOT, None


def get_object(ROOT, path: str, name: str, kind: str):
    if not Path(path).is_file():
        raise InputError(f"no such file: {path}")
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        raise InputError(f"cannot open {path} as a ROOT file")
    obj = f.Get(name)
    if not obj or not obj.InheritsFrom(kind):
        f.Close()
        raise InputError(f"{path} has no {kind} named {name!r}")
    return f, obj


def check_result(ROOT, args) -> tuple[str, dict]:
    f, r = get_object(ROOT, args.file, args.name, "RooFitResult")
    history = [{"step": str(r.statusLabelHistory(i)), "code": int(r.statusCodeHistory(i))}
               for i in range(r.numStatusHistory())]
    status, cov_qual, edm = int(r.status()), int(r.covQual()), float(r.edm())
    params, minos = {}, False
    pars = r.floatParsFinal()
    for i in range(pars.getSize()):
        p = pars.at(i)
        rec = {"value": float(p.getVal()), "error": float(p.getError())}
        if p.hasAsymError():
            minos = True
            rec["error_lo"], rec["error_hi"] = float(p.getAsymErrorLo()), float(p.getAsymErrorHi())
        params[str(p.GetName())] = rec
    min_nll = float(r.minNll())
    f.Close()
    reasons = []
    if status != 0:
        reasons.append(f"minimizer status {status} (0 required); history {history}")
    if cov_qual < 3:
        meaning = {-1: "not available", 0: "not calculated", 1: "approximate", 2: "forced positive-definite"}
        reasons.append(f"covQual {cov_qual} ({meaning.get(cov_qual, 'unknown')}); 3 (full, accurate) required")
    if not math.isfinite(edm) or edm > args.edm_max:
        reasons.append(f"EDM {edm:.3g} above the declared threshold {args.edm_max:g}")
    bad_steps = [h for h in history if h["code"] != 0]
    if bad_steps and status == 0:
        reasons.append(f"a step of the fit reported a nonzero code: {bad_steps}")
    run_status = "failed" if reasons else "ok"
    out = {"fit_diagnostics": {"minimizer_status": status, "cov_qual": cov_qual, "edm": edm, "edm_max": args.edm_max,
                               "min_nll": min_nll, "status_history": history, "backend": "RooFit",
                               "root_version": str(ROOT.gROOT.GetVersion())},
           "parameters": params, "method_kind": "minos" if minos else "hesse", "paradigm": "frequentist",
           "reasons": reasons,
           "criteria": "ok only when status == 0, covQual == 3, EDM <= edm_max and every step code is 0"}
    return run_status, out


def check_weighted(ROOT, args) -> tuple[str, dict]:
    if args.file:
        if not args.dataset:
            raise InputError("--file needs --dataset NAME")
        f, d = get_object(ROOT, args.file, args.dataset, "RooAbsData")
        weighted = bool(d.isWeighted())
        f.Close()
    else:
        weighted = bool(args.weighted)
    out: dict = {"weighted": weighted}
    if not weighted:
        out["note"] = "unweighted data: the default (inverse-Hessian) errors apply"
        return "ok", out
    if not args.weighted_errors:
        out["reason"] = ("weighted data need a declared error treatment: pass --weighted-errors sumw2, asymptotic "
                         "or sweights (see likelihood-fitting.md); without it the fit errors are those of unweighted "
                         "events and wrong")
        return "incomplete", out
    out.update({"weighted_errors": args.weighted_errors, **ERRORS[args.weighted_errors]})
    return "ok", out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("result", help="map a saved RooFitResult to a status")
    p.add_argument("--file", required=True)
    p.add_argument("--name", required=True, help="name of the RooFitResult in the file")
    p.add_argument("--edm-max", type=float, required=True, help="EDM threshold (no default)")
    p = sub.add_parser("weighted", help="weighted data need a declared error treatment")
    p.add_argument("--file")
    p.add_argument("--dataset", help="name of the RooDataSet or RooDataHist in --file")
    p.add_argument("--weighted", action="store_true", help="the data are weighted (when no file is given)")
    p.add_argument("--weighted-errors", choices=sorted(ERRORS))
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    given = {tok.split("=")[0] for tok in (sys.argv[1:] if argv is None else argv) if tok.startswith("--")}
    head = {"status_label": args.status, "inputs": {k: v for k, v in vars(args).items() if k != "status"},
            "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    try:
        if args.command == "result" and not (math.isfinite(args.edm_max) and args.edm_max > 0):
            raise InputError("--edm-max must be a finite number > 0")
        if args.command == "weighted" and not args.file and args.dataset:
            raise InputError("--dataset needs --file")
        if args.file and not Path(args.file).is_file():
            raise InputError(f"no such file: {args.file}")
        needs_root = args.command == "result" or bool(args.file)
        ROOT = None
        if needs_root:
            ROOT, err = load_root()
            if ROOT is None:
                print(json.dumps({"status": "missing-dependency", **head, "error": f"PyROOT not available ({err})",
                                  "install": ROOT_HINT}, indent=1))
                return exit_code("missing-dependency")
        status, out = (check_result if args.command == "result" else check_weighted)(ROOT, args)
    except InputError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": status, **head, **out}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
