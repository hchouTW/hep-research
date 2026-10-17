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
            See <plugin root>/skills/hep-statistics/references/roofit-and-roostats-methods.md.
  toys      --file W.root --workspace NAME --pdf PDF --observables x[,y] --nevents N --toys K --seed S [--extended]:
            a RooMCStudy pull study (generate K samples of N events from the PDF at its current parameter values, fit
            each); for every floating parameter the mean and width of its pulls with their uncertainties, and the
            fits that failed (status != 0 or covQual < 3), counted, never dropped. failed (exit 1) when a pull mean or
            width is more than 3 of its uncertainties from 0 or 1, or a fit failed. Slow: seconds per toy.
  crosscheck --input MODEL.json [--cl 0.95] [--cls-toys N --seed S]: on a small multi-bin counting model (the
            core/stats multibin-limit format: {"bins": [{"n", "b", "s"}], "background_uncertainty": {"kind": "none" |
            "common_scale", "sigma"}}) the same likelihood is built in RooFit (RooPoisson per bin, a RooGaussian
            constraint for the common scale) and compared with core/stats: the MLE of mu, the 68.27% MINOS interval
            against the core profile interval, the profile-likelihood scan, and the asymptotic CLs upper limit of
            RooStats (AsymptoticCalculator, one-sided q-tilde, HypoTestInverter) against core's. RooFit runs MIGRAD with
            a tight tolerance (RooMinimizer::setEps(1e-6)), so the comparison is about the likelihood. With --cls-toys the
            RooStats FrequentistCalculator toy CLs limit is compared with the asymptotic one (low counts). failed
            (exit 1) when RooFit and core differ beyond the stated tolerances.
Validity: RooFit results from ROOT 6 (RooFitResult::status, covQual, edm, statusCodeHistory); API names checked
against the ROOT 6.40 reference (root.cern/doc/v640, read 2026-10-17). `result` reads what the fit recorded; it does
not refit or test coverage.
Output JSON: "status" (run status, core/status.py), "status_label" (--status, default unvalidated), "inputs",
"defaults_used", and for result "fit_diagnostics", "parameters", "method_kind", "paradigm", "reasons"; for toys
"pulls", "fits"; for crosscheck "mle", "minos", "profile_scan", "asymptotic_cls", "toy_cls", "tolerances", "reasons".
Exit codes: 0 ok; 1 the fit is failed; 2 bad input (unreadable file, unknown object, bad threshold); 3 PyROOT
missing (install hint), or weighted data without --weighted-errors.
Run: python3 <plugin root>/skills/hep-statistics/scripts/roofit_fit_check.py result --file fit.root --name fitresult --edm-max 1e-3
     python3 <plugin root>/skills/hep-statistics/scripts/roofit_fit_check.py weighted --weighted --weighted-errors asymptotic
     python3 <plugin root>/skills/hep-statistics/scripts/roofit_fit_check.py crosscheck --input bins.json
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

TOL = {"mle_abs": 1e-3, "interval_abs": 2e-3, "scan_abs": 2e-3, "asymptotic_cls_rel": 0.01}

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


def _quiet(ROOT):
    ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.FATAL)
    ROOT.Math.MinimizerOptions.SetDefaultPrintLevel(-1)
    ROOT.RooStats.AsymptoticCalculator.SetPrintLevel(-1)


class _CStdoutToStderr:
    """ROOT and Minuit print to the C-level stdout; while they run it goes to stderr, so stdout carries only JSON."""

    def __enter__(self):
        import os
        sys.stdout.flush()
        self._saved = os.dup(1)
        os.dup2(2, 1)
        return self

    def __exit__(self, *exc):
        import os
        sys.stdout.flush()
        os.dup2(self._saved, 1)
        os.close(self._saved)
        return False


def check_toys(ROOT, args) -> tuple[str, dict]:
    if args.toys < 20 or args.nevents < 1:
        raise InputError("--toys must be >= 20 and --nevents >= 1")
    f, w = get_object(ROOT, args.file, args.workspace, "RooWorkspace")
    pdf = w.pdf(args.pdf)
    if not pdf:
        f.Close()
        raise InputError(f"workspace {args.workspace} has no pdf {args.pdf!r}")
    obs = ROOT.RooArgSet()
    for name in args.observables.split(","):
        v = w.var(name.strip())
        if not v:
            f.Close()
            raise InputError(f"workspace {args.workspace} has no observable {name!r}")
        obs.add(v)
    _quiet(ROOT)
    ROOT.RooRandom.randomGenerator().SetSeed(args.seed)
    opts = [ROOT.RooFit.Silence(), ROOT.RooFit.FitOptions(ROOT.RooFit.Save(True), ROOT.RooFit.PrintLevel(-1),
                                                          ROOT.RooFit.PrintEvalErrors(-1))]
    if args.extended:
        opts.append(ROOT.RooFit.Extended(True))
    mcs = ROOT.RooMCStudy(pdf, obs, *opts)
    mcs.generateAndFit(args.toys, args.nevents)
    failed = 0
    for i in range(args.toys):
        r = mcs.fitResult(i)
        if not r or r.status() != 0 or r.covQual() < 3:
            failed += 1
    pars = pdf.getParameters(obs)
    pulls, reasons = {}, []
    data = mcs.fitParDataSet()
    for i in range(pars.getSize()):
        par = pars[i]
        if par.isConstant():
            continue
        name = str(par.GetName())
        vals = []
        for k in range(data.numEntries()):
            row = data.get(k)
            v = row.find(f"{name}pull")
            if v:
                vals.append(float(v.getVal()))
        n = len(vals)
        if n < 2:
            continue
        mean = sum(vals) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x in vals) / (n - 1))
        rec = {"n": n, "mean": mean, "mean_error": sd / math.sqrt(n), "width": sd, "width_error": sd / math.sqrt(2 * (n - 1))}
        rec["consistent_with_unit_normal"] = (abs(mean) <= 3 * rec["mean_error"] and abs(sd - 1) <= 3 * rec["width_error"])
        if not rec["consistent_with_unit_normal"]:
            reasons.append(f"{name}: pull mean {mean:.3g} +- {rec['mean_error']:.2g}, width {sd:.3g} +- {rec['width_error']:.2g}")
        pulls[name] = rec
    f.Close()
    if failed:
        reasons.append(f"{failed} of {args.toys} toy fits failed (status != 0 or covQual < 3); counted, not dropped")
    out = {"pulls": pulls, "fits": {"toys": args.toys, "failed": failed, "nevents": args.nevents, "seed": args.seed},
           "reasons": reasons, "method": "RooMCStudy generateAndFit; pull = (fitted - generated) / error",
           "note": "pulls are N(0, 1) only when the asymptotic approximation holds; at low counts compare with the toys "
                   "of the same model, not with N(0, 1)"}
    return ("failed" if reasons else "ok"), out


def _core_profile(model, ns, aux):
    """Core profile likelihood of mu: (mu_hat, ll_max, f(mu) = 2 (ll_max - profiled lnL))."""
    mu_hat, ll_max = model.fit(ns, aux)
    return mu_hat, ll_max, (lambda m: 2.0 * (ll_max - model._prof_nu(ns, aux, m)[0]))


def _solve(f, lo, hi, target):
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) < target else (lo, mid)
    return 0.5 * (lo + hi)


def parse_crosscheck(args) -> tuple:
    """Read and check the model before ROOT is loaded, so a bad input is exit 2 with or without ROOT."""
    from core.stats import likelihood_limits as ll
    try:
        doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {args.input}: {exc}") from None
    try:
        bins, kind, sigma, mc = ll._load_model(doc)
    except ll.LikelihoodError as exc:
        raise InputError(str(exc)) from None
    if kind not in ("none", "common_scale") or mc is not None:
        raise InputError("crosscheck supports background_uncertainty none or common_scale, without mc_stat")
    if len(bins) > 20:
        raise InputError("crosscheck is for small models: at most 20 bins")
    if not 0 < args.cl < 1:
        raise InputError("--cl must lie in (0, 1)")
    if args.cls_toys < 0 or (args.cls_toys and args.seed is None):
        raise InputError("--cls-toys must be >= 0 and needs --seed")
    return doc, bins, kind, sigma, mc


def check_crosscheck(ROOT, args) -> tuple[str, dict]:
    from core.stats import likelihood_limits as ll
    doc, bins, kind, sigma, mc = parse_crosscheck(args)
    model = ll._Model(bins, kind, sigma, mc)
    ns, aux = [x["n"] for x in bins], model.aux_obs()
    mu_hat, _, prof = _core_profile(model, ns, aux)
    lo_c = 0.0 if prof(0.0) <= 1.0 else _solve(lambda m: -prof(m), 0.0, mu_hat, -1.0)
    hi_c = _solve(prof, mu_hat, mu_hat + 50.0 * (math.sqrt(sum(ns) + 1.0) + 1.0) / max(sum(model.s), 1e-12), 1.0)
    core_cls = ll.multibin_limit(doc, args.cl, 0, 1)["asymptotic_observed_cls_upper_limit"]
    _quiet(ROOT)
    mu_max = max(10.0 * hi_c, 10.0)
    mu = ROOT.RooRealVar("mu", "mu", max(mu_hat, 1e-3), 0.0, mu_max)
    obs, terms, keep = ROOT.RooArgSet(), ROOT.RooArgList(), []
    theta = gobs = None
    if kind == "common_scale":
        theta = ROOT.RooRealVar("theta", "theta", 1.0, 0.0, 1.0 + 12.0 * sigma + 5.0)
        gobs = ROOT.RooRealVar("theta_obs", "theta_obs", 1.0, -10.0, 10.0)
        gobs.setConstant(True)
        sg = ROOT.RooRealVar("theta_sigma", "theta_sigma", sigma)
        cons = ROOT.RooGaussian("theta_constraint", "theta_constraint", gobs, theta, sg)
        keep += [sg, cons]
        terms.add(cons)
    for i, x in enumerate(bins):
        n = ROOT.RooRealVar(f"n{i}", f"n{i}", x["n"], 0.0, 10.0 * x["n"] + 100.0)
        sv, bv = ROOT.RooRealVar(f"s{i}", "s", x["s"]), ROOT.RooRealVar(f"b{i}", "b", x["b"])
        lst = ROOT.RooArgList(mu, sv, bv) if theta is None else ROOT.RooArgList(mu, sv, bv, theta)
        lam = ROOT.RooFormulaVar(f"lam{i}", "@0*@1 + @2" if theta is None else "@0*@1 + @3*@2", lst)
        pois = ROOT.RooPoisson(f"pois{i}", f"pois{i}", n, lam, True)  # noRounding: n is a real variable here
        keep += [n, sv, bv, lam, pois]
        obs.add(n)
        terms.add(pois)
    pdf = ROOT.RooProdPdf("model", "model", terms)
    data = ROOT.RooDataSet("data", "data", obs)
    data.add(obs)
    nll_opts = [ROOT.RooFit.GlobalObservables(ROOT.RooArgSet(gobs))] if gobs is not None else []
    nll = pdf.createNLL(data, *nll_opts)
    minim = ROOT.RooMinimizer(nll)  # a tight tolerance: the comparison is about the likelihood, not MIGRAD's stop
    minim.setPrintLevel(-1)
    minim.setStrategy(2)
    minim.setEps(1e-6)
    minim.migrad()
    minim.hesse()
    minim.minos(ROOT.RooArgSet(mu))
    res = minim.save()
    rf_hat, rf_lo, rf_hi = float(mu.getVal()), float(mu.getVal() + mu.getAsymErrorLo()), float(mu.getVal() + mu.getAsymErrorHi())
    nll_min = float(res.minNll())
    grid = [hi_c * k / 8.0 for k in range(1, 9)]
    scan = []
    for m in grid:
        mu.setVal(m)
        mu.setConstant(True)
        if theta is not None:
            prof_min = ROOT.RooMinimizer(nll)
            prof_min.setPrintLevel(-1)
            prof_min.setStrategy(2)
            prof_min.setEps(1e-6)
            prof_min.migrad()
        rf_q = 2.0 * (float(nll.getVal()) - nll_min)
        scan.append({"mu": m, "roofit": rf_q, "core": prof(m), "diff": rf_q - prof(m)})
        mu.setConstant(False)
    # RooStats asymptotic CLs (one-sided q-tilde)
    w = ROOT.RooWorkspace("w")
    w.Import(pdf)
    w.Import(data)
    mc_sb = ROOT.RooStats.ModelConfig("sb", w)
    mc_sb.SetPdf("model")
    mc_sb.SetParametersOfInterest("mu")
    mc_sb.SetObservables(",".join(f"n{i}" for i in range(len(bins))))
    if theta is not None:
        mc_sb.SetNuisanceParameters("theta")
        mc_sb.SetGlobalObservables("theta_obs")
    w.var("mu").setVal(max(rf_hat, 1e-3))
    mc_sb.SetSnapshot(ROOT.RooArgSet(w.var("mu")))
    mc_b = mc_sb.Clone("b")
    w.var("mu").setVal(0.0)
    mc_b.SetSnapshot(ROOT.RooArgSet(w.var("mu")))
    wdata = w.data("data")
    calc = ROOT.RooStats.AsymptoticCalculator(wdata, mc_b, mc_sb)
    calc.SetOneSided(True)
    calc.SetQTilde(True)
    inv = ROOT.RooStats.HypoTestInverter(calc)
    inv.SetConfidenceLevel(args.cl)
    inv.UseCLs(True)
    inv.SetFixedScan(60, 0.0, 3.0 * max(core_cls, 1e-3))
    rf_cls = float(inv.GetInterval().UpperLimit())
    toy = None
    if args.cls_toys:
        ROOT.RooRandom.randomGenerator().SetSeed(args.seed)
        fcalc = ROOT.RooStats.FrequentistCalculator(wdata, mc_b, mc_sb)
        fcalc.SetToys(args.cls_toys, max(args.cls_toys // 2, 1))
        ts = ROOT.RooStats.ProfileLikelihoodTestStat(mc_sb.GetPdf())
        ts.SetOneSided(True)
        fcalc.GetTestStatSampler().SetTestStatistic(ts)
        finv = ROOT.RooStats.HypoTestInverter(fcalc)
        finv.SetConfidenceLevel(args.cl)
        finv.UseCLs(True)
        finv.SetFixedScan(12, 0.0, 3.0 * max(core_cls, 1e-3))
        toy_lim = float(finv.GetInterval().UpperLimit())
        toy = {"roostats_toy_cls_upper_limit": toy_lim, "toys": args.cls_toys, "seed": args.seed,
               "relative_difference_to_asymptotic": toy_lim / rf_cls - 1.0 if rf_cls else None,
               "note": "at low counts the asymptotic limit can differ from the toy limit; the toy limit is the reference"}
    reasons = []
    if abs(rf_hat - mu_hat) > TOL["mle_abs"]:
        reasons.append(f"MLE differs: RooFit {rf_hat:.6g}, core {mu_hat:.6g}")
    if abs(rf_hi - hi_c) > TOL["interval_abs"] or abs(rf_lo - lo_c) > TOL["interval_abs"]:
        reasons.append(f"MINOS interval [{rf_lo:.6g}, {rf_hi:.6g}] differs from the core profile interval [{lo_c:.6g}, {hi_c:.6g}]")
    worst = max(abs(r["diff"]) for r in scan)
    if worst > TOL["scan_abs"]:
        reasons.append(f"profile scan differs by up to {worst:.3g}")
    if abs(rf_cls / core_cls - 1.0) > TOL["asymptotic_cls_rel"]:
        reasons.append(f"asymptotic CLs limit: RooStats {rf_cls:.6g}, core {core_cls:.6g}")
    out = {"mle": {"roofit": rf_hat, "core": mu_hat, "roofit_fit_status": int(res.status()), "cov_qual": int(res.covQual())},
           "minos": {"roofit": [rf_lo, rf_hi], "core_profile": [lo_c, hi_c], "cl": 0.6827},
           "profile_scan": scan, "asymptotic_cls": {"roostats": rf_cls, "core": core_cls, "cl": args.cl},
           "toy_cls": toy, "tolerances": TOL, "reasons": reasons, "root_version": str(ROOT.gROOT.GetVersion()),
           "paradigm": "frequentist", "method_kind": "profile likelihood, asymptotic"}
    return ("failed" if reasons else "ok"), out


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
    p = sub.add_parser("toys", help="RooMCStudy pull study of a workspace PDF (slow)")
    p.add_argument("--file", required=True)
    p.add_argument("--workspace", required=True)
    p.add_argument("--pdf", required=True)
    p.add_argument("--observables", required=True, help="comma-separated observable names")
    p.add_argument("--nevents", type=int, required=True)
    p.add_argument("--toys", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--extended", action="store_true", help="Poisson-fluctuate the number of events (extended PDF)")
    p = sub.add_parser("crosscheck", help="RooFit/RooStats against core/stats on a small multi-bin model")
    p.add_argument("--input", required=True, help='JSON file: {"bins": [{"n", "b", "s"}], "background_uncertainty"?: '
                   '{"kind": "none" | "common_scale", "sigma"}} (core/stats multibin-limit format)')
    p.add_argument("--cl", type=float, default=0.95)
    p.add_argument("--cls-toys", type=int, default=0, help="RooStats FrequentistCalculator toys (slow; 0: none)")
    p.add_argument("--seed", type=int)
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
        if getattr(args, "file", None) and not Path(args.file).is_file():
            raise InputError(f"no such file: {args.file}")
        if args.command == "crosscheck":
            parse_crosscheck(args)
        needs_root = args.command in ("result", "toys", "crosscheck") or bool(getattr(args, "file", None))
        ROOT = None
        if needs_root:
            ROOT, err = load_root()
            if ROOT is None:
                print(json.dumps({"status": "missing-dependency", **head, "error": f"PyROOT not available ({err})",
                                  "install": ROOT_HINT}, indent=1))
                return exit_code("missing-dependency")
        with _CStdoutToStderr():
            status, out = {"result": check_result, "weighted": check_weighted, "toys": check_toys,
                           "crosscheck": check_crosscheck}[args.command](ROOT, args)
    except InputError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": status, **head, **out}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
