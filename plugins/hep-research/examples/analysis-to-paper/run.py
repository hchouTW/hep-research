#!/usr/bin/env python3
"""Example E-4: from analysis to paper on SYNTHETIC signal plus background, with every number in the draft traced to
an artifact.

SYNTHETIC and ILLUSTRATIVE: two Gaussian discriminating features, a Gaussian mass peak on an exponential background;
every number is invented and describes no experiment. No profile is loaded.

Chain:
1. Score (hep-ml): by default the Bayes-optimal score, the exact log-likelihood ratio of the two generated classes (a
   labelled fallback that needs no ML backend, so the committed output reproduces everywhere); with --with-bdt the
   cross-trained BDT of skills/hep-ml/scripts/train_bdt.py (xgboost or scikit-learn, optional extra `bdt`). The AUC
   on held-out events is compared with the Bayes limit Phi(|d| / sqrt 2) within its statistical spread.
2. Cut at score > 0 and histogram the mass of the selected events (simulation templates and pseudo-data).
3. Fit (hep-statistics): core/stats/template_fit.py bb-fit gives the signal yield; mu = yield / expected yield. With
   --root-python PY (a Python with PyROOT) a RooFit extended template fit runs too and roofit_fit_check.py maps its
   saved RooFitResult; without it the RooFit step exits 3 (missing dependency) and the rest completes.
4. result_artifact.py writes the statistical-result (signal strength); a binned dataset-record holds the selected
   mass spectrum.
5. render_results.py (hep-communication, Com7) writes the macros, the result table and a one-bin dataset-record of
   mu; a draft (draft/main.tex) uses only the macros; check_manuscript.py --numbers checks the draft.
6. hepdata_export.py writes the HEPData tables from both records; their values are compared with the artifacts.
results.json holds only environment-independent numbers; the RooFit and LaTeX outcomes, which vary with the
installation, are printed on stdout (the draft builds; a final build, which defines \\hepfinalbuild, stops on the
synthetic watermark).

Usage (from the plugin root): python3 examples/analysis-to-paper/run.py [--seed 20261017] [--out DIR]
       [--with-bdt] [--root-python PYTHON]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

SC = {"bdt": PLUGIN / "skills/hep-ml/scripts/train_bdt.py", "fit": PLUGIN / "core/stats/template_fit.py",
      "result": PLUGIN / "skills/hep-statistics/scripts/result_artifact.py",
      "roofit": PLUGIN / "skills/hep-statistics/scripts/roofit_fit_check.py",
      "render": PLUGIN / "skills/hep-communication/scripts/render_results.py",
      "manuscript": PLUGIN / "skills/hep-communication/scripts/check_manuscript.py",
      "hepdata": PLUGIN / "adapters/hepdata/assets/hepdata_export.py"}
D = (1.2, 0.8)  # class separation of the two features (in units of their width)
MASS_EDGES = np.linspace(100.0, 150.0, 26)
N_SIG_MC, N_BKG_MC, N_SIG_DATA, N_BKG_DATA = 20000, 200000, 600, 6000  # expected data yields before the cut
CRITERIA = {"auc_pull_abs": 3.0, "mu_pull_abs": 3.0}
LABEL = "SYNTHETIC and ILLUSTRATIVE: invented signal and background; describes no experiment"
ROOFIT = r'''
import json, sys, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.WARNING)
d = json.load(open(sys.argv[1]))
edges = d["edges"]
x = ROOT.RooRealVar("m", "m", edges[0], edges[-1])
x.setBins(len(edges) - 1)
def hist(name, counts):
    h = ROOT.TH1D(name, name, len(edges) - 1, edges[0], edges[-1])
    for i, c in enumerate(counts):
        h.SetBinContent(i + 1, c)
    return h
hs, hb, hd = hist("hs", d["sig"]), hist("hb", d["bkg"]), hist("hd", d["data"])
ds, db = ROOT.RooDataHist("ds", "", ROOT.RooArgList(x), hs), ROOT.RooDataHist("db", "", ROOT.RooArgList(x), hb)
data = ROOT.RooDataHist("data", "", ROOT.RooArgList(x), hd)
ps, pb = ROOT.RooHistPdf("ps", "", ROOT.RooArgSet(x), ds), ROOT.RooHistPdf("pb", "", ROOT.RooArgSet(x), db)
ns = ROOT.RooRealVar("nsig", "", 300, -1000, 5000)
nb = ROOT.RooRealVar("nbkg", "", 3000, 0, 50000)
model = ROOT.RooAddPdf("model", "", ROOT.RooArgList(ps, pb), ROOT.RooArgList(ns, nb))
r = model.fitTo(data, ROOT.RooFit.Extended(True), ROOT.RooFit.Save(True), ROOT.RooFit.PrintLevel(-1))
f = ROOT.TFile(sys.argv[2], "RECREATE"); r.Write("fitresult"); f.Close()
print(json.dumps({"nsig": ns.getVal(), "nsig_err": ns.getError(), "status": r.status(), "covQual": r.covQual()}))
'''


def tool(name, *args, python=None, cwd=None):
    p = subprocess.run([python or sys.executable, "-B", str(SC[name]), *map(str, args)], capture_output=True,
                       text=True, timeout=900, cwd=cwd)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"raw": p.stdout[-500:]}
    return p.returncode, out, p.stderr


def rnd(x, digits=6):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, digits) for v in x]
    return float(f"{float(x):.{digits}g}")


def generate(rng, n, cls):
    feats = np.column_stack([rng.normal((d / 2) if cls else (-d / 2), 1.0, n) for d in D])
    if cls:
        mass = rng.normal(125.0, 2.0, n)
    else:
        mass = 100.0 + rng.exponential(25.0, n)
    keep = (mass >= MASS_EDGES[0]) & (mass < MASS_EDGES[-1])
    return feats[keep], mass[keep]


def bayes_score(x):
    """Exact log-likelihood ratio of N(+d/2, 1) vs N(-d/2, 1) per feature: sum_k d_k x_k."""
    return x @ np.array(D)


def auc(score_s, score_b):
    s = np.concatenate([score_s, score_b])
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    rs = ranks[:len(score_s)].sum()
    return float((rs - len(score_s) * (len(score_s) + 1) / 2) / (len(score_s) * len(score_b)))


def dataset_record(path, counts, label, created):
    rec = {"contract_version": CONTRACTS_VERSION, "artifact_id": "synthetic-e4-selected-mass",
           "artifact_type": "dataset-record", "objective": "SYNTHETIC selected mass spectrum (score > 0)",
           "bindings": {"experiments": [], "theory": []},
           "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["version"],
                        "contracts": CONTRACTS_VERSION, "profiles": {}},
           "provenance": {"producer_skill": "hep-measurement", "created": created, "evidence_ids": []},
           "inputs": [], "outputs": [], "unresolved_inputs": [], "status": [label],
           "extension": {"dataset_id": "synthetic:e4-selected-mass", "source_evidence_ids": [],
                         "observable": {"quantity": "event-count", "process": "SYNTHETIC signal plus background",
                                        "variables": [{"name": "m", "unit": "GeV", "edges": MASS_EDGES.tolist()}],
                                        "phase_space": {"definition": "SYNTHETIC: score > 0", "fiducial": False},
                                        "level": "detector",
                                        "normalization": {"kind": "integrated-luminosity", "value": 1.0, "unit": "fb^-1",
                                                          "convention": "SYNTHETIC: one invented data set"},
                                        "bin_semantics": "bin-integrated", "unit": "1"},
                         "data": {"edges": MASS_EDGES.tolist(), "values": [int(c) for c in counts], "unit": "1",
                                  "uncertainties": [{"name": "stat", "kind": "statistical", "correlation": "uncorrelated",
                                                     "values": [math.sqrt(c) for c in counts]}]},
                         "covariance": {"status": "present", "ref": "selected_mass.json#extension.data.uncertainties",
                                        "note": "Poisson, bins independent"},
                         "period": "not-applicable", "status": label}}
    rep = validate_artifact(rec)
    if not rep.ok:
        raise SystemExit(f"dataset-record invalid: {rep.as_dict()['findings'][:3]}")
    Path(path).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")


DRAFT = r"""\documentclass{article}
\begin{document}
\input{numbers.tex}
\begin{abstract}A SYNTHETIC search finds a signal strength $\mu = \Mu$.\end{abstract}
\section{Introduction}
SYNTHETIC illustration of numbers taken from artifacts.
\section{Results}
The template fit gives $\mu = \Mu$.
\begin{table}\caption{Selected events (SYNTHETIC).}\MassTable\end{table}
\section{Conclusion}
The signal strength is $\mu = \Mu$.
\end{document}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    ap.add_argument("--with-bdt", action="store_true")
    ap.add_argument("--root-python", help="a Python that can import ROOT (for the RooFit step)")
    a = ap.parse_args(argv)
    out = a.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    (out / "draft").mkdir(exist_ok=True)
    work_dir = tempfile.TemporaryDirectory()
    work = Path(work_dir.name)
    rng = np.random.default_rng(a.seed)
    created = "2026-10-17"

    # 1. score and AUC (held-out events)
    xs, ms = generate(rng, N_SIG_MC, 1)
    xb, mb = generate(rng, N_BKG_MC, 0)
    bayes = 0.5 * (1 + math.erf(math.hypot(*D) / math.sqrt(2) / math.sqrt(2)))
    if a.with_bdt:
        n = min(len(xs), 6000)
        rows = [{"id": i, "event": 100000 + i, "label": 1, "weight": 1.0, "x0": f[0], "x1": f[1]}
                for i, f in enumerate(xs[:n])]
        rows += [{"id": n + i, "event": 100000 + n + i, "label": 0, "weight": 1.0, "x0": f[0], "x1": f[1]}
                 for i, f in enumerate(xb[:n])]
        with open(work / "bdt.csv", "w", encoding="utf-8") as fh:
            fh.write("id,event,label,weight,x0,x1\n" + "".join(
                f"{r['id']},{r['event']},{r['label']},{r['weight']},{float(r['x0'])!r},{float(r['x1'])!r}\n" for r in rows))
        (work / "bdt.json").write_text(json.dumps({"features": ["x0", "x1"], "label": "label", "weight": "weight",
                                                    "id": "id", "event_number": "event", "folds": 3,
                                                    "backend": "xgboost", "seed": a.seed % 1000,
                                                    "hyperparameters": {"max_depth": [2], "learning_rate": [0.2],
                                                                        "n_estimators": [80]},
                                                    "objective": "auc"}), encoding="utf-8")
        code, bdt, err = tool("bdt", "--data", work / "bdt.csv", "--config", work / "bdt.json", "--negative-weights",
                              "reject", "--out-dir", work / "bdt")
        if code != 0:
            raise SystemExit(f"train_bdt.py failed ({code}): {bdt.get('error') or err[-400:]}")
        measured, n_s, n_b = bdt["metrics"]["test"]["auc_weighted"], n, n
        score_kind = f"train_bdt.py ({bdt['backend']}), out-of-fold"
    else:
        hs, hb_ = xs[len(xs) // 2:], xb[len(xb) // 2:]  # held-out half
        measured, n_s, n_b = auc(bayes_score(hs), bayes_score(hb_)), len(hs), len(hb_)
        score_kind = "Bayes-optimal log-likelihood ratio (fallback: no ML backend used; --with-bdt runs train_bdt.py)"
    q1, q2 = measured / (2 - measured), 2 * measured ** 2 / (1 + measured)
    sigma_auc = math.sqrt((measured * (1 - measured) + (n_s - 1) * (q1 - measured ** 2)
                           + (n_b - 1) * (q2 - measured ** 2)) / (n_s * n_b))  # Hanley-McNeil
    auc_pull = (measured - bayes) / sigma_auc

    # 2. cut and histograms (the score of the fallback; the same cut for the BDT run)
    sel_s, sel_b = bayes_score(xs) > 0, bayes_score(xb) > 0
    tmpl_s, _ = np.histogram(ms[sel_s], MASS_EDGES)
    tmpl_b, _ = np.histogram(mb[sel_b], MASS_EDGES)
    xs_d, ms_d = generate(rng, rng.poisson(N_SIG_DATA), 1)
    xb_d, mb_d = generate(rng, rng.poisson(N_BKG_DATA), 0)
    data, _ = np.histogram(np.concatenate([ms_d[bayes_score(xs_d) > 0], mb_d[bayes_score(xb_d) > 0]]), MASS_EDGES)
    eff_s = sel_s.mean() * len(xs) / N_SIG_MC  # selection x mass window, per generated signal event
    expected_sig = N_SIG_DATA * eff_s  # expected selected signal events for mu = 1 (reported)

    # 3. core fit -> mu
    (work / "fit.json").write_text(json.dumps({"data": data.tolist(), "templates": {"sig": tmpl_s.tolist(),
                                                                                   "bkg": tmpl_b.tolist()},
                                               "mc_events": {"sig": N_SIG_MC, "bkg": N_BKG_MC}}), encoding="utf-8")
    code, fit, err = tool("fit", "bb-fit", "--input", work / "fit.json")
    if code != 0:
        raise SystemExit(f"template_fit.py failed ({code}): {err[-400:]}")
    y_sig, y_err = fit["barlow_beeston"]["sig"]["yield"], fit["barlow_beeston"]["sig"]["error"]
    naive_sig = fit["naive"]["sig"]["yield"]
    # bb-fit yields count generated events (A_j = Y_j / M_j with M_j the generated MC events), so mu compares the
    # fitted yield with the generated signal yield of the data set
    mu, sigma_mu = y_sig / N_SIG_DATA, y_err / N_SIG_DATA
    cli = {"status": fit["status"], "mu_hat": mu, "sigma_mu": sigma_mu, "cl": 0.68,
           "note": "mu = Barlow-Beeston signal yield (generated events) / generated signal yield of the data set "
                   "(template_fit.py bb-fit)"}
    (work / "cli.json").write_text(json.dumps(cli), encoding="utf-8")

    # 3b. RooFit (optional)
    roofit = {"step": "RooFit extended template fit and roofit_fit_check.py result"}
    if a.root_python:
        (work / "roofit.py").write_text(ROOFIT, encoding="utf-8")
        (work / "roofit_in.json").write_text(json.dumps({"edges": MASS_EDGES.tolist(), "sig": tmpl_s.tolist(),
                                                         "bkg": tmpl_b.tolist(), "data": data.tolist()}),
                                             encoding="utf-8")
        p = subprocess.run([a.root_python, str(work / "roofit.py"), str(work / "roofit_in.json"), str(work / "fit.root")],
                           capture_output=True, text=True, timeout=900)
        if p.returncode == 0:
            rf = json.loads(p.stdout.strip().splitlines()[-1])
            code, chk, _ = tool("roofit", "result", "--file", work / "fit.root", "--name", "fitresult", "--edm-max",
                                "0.001", python=a.root_python)
            # RooFit's nsig counts selected events; the core yield counts generated events: scale it by the
            # selected fraction of the signal templates. Both fits treat the templates as exact (core: naive fit).
            core_selected = naive_sig * tmpl_s.sum() / N_SIG_MC
            roofit.update(ran=True, nsig=rf["nsig"], nsig_err=rf["nsig_err"], check_exit=code,
                          check_status=chk.get("status"), core_naive_nsig_selected=float(core_selected),
                          mu_roofit=float(rf["nsig"] / (N_SIG_DATA * tmpl_s.sum() / N_SIG_MC)),
                          agree=bool(abs(rf["nsig"] - core_selected) <= 0.01 * abs(core_selected) + 0.05 * rf["nsig_err"]))
        else:
            roofit.update(ran=False, error=p.stderr[-400:])
    else:
        (work / "absent.root").write_bytes(b"")  # a file to check; without PyROOT the tool stops before reading it
        code, chk, _ = tool("roofit", "result", "--file", work / "absent.root", "--name", "fitresult", "--edm-max",
                            "0.001")
        roofit.update(ran=False, exit_code=code, status=chk.get("status"),
                      note="no --root-python: the RooFit step exits 3 (missing dependency); the rest completes")

    # 4. artifacts
    res_path = out / "artifacts" / "signal_strength.json"
    code, res, err = tool("result", "--cli-output", work / "cli.json", "--poi", "mu", "--construction", "asymptotic",
                          "--test-statistic", "q_mu", "--label", "synthetic", "--artifact-id", "synthetic-e4-mu",
                          "--objective", "SYNTHETIC signal strength from a Barlow-Beeston template fit",
                          "--created", created, "--out", res_path)
    if code != 0:
        raise SystemExit(f"result_artifact.py failed ({code}): {res}")
    rec_path = out / "artifacts" / "selected_mass.json"
    dataset_record(rec_path, data, "synthetic", created)

    # 5. render and draft
    mu_rec = out / "artifacts" / "signal_strength_record.json"
    code, ren, err = tool("render", "--quantity", f"Mu={res_path}:mu_hat:sigma_mu", "--table", f"Mass={rec_path}",
                          "--out", out / "draft" / "numbers.tex", "--manifest", work / "manifest.json",
                          "--hepdata-record", f"Mu={mu_rec}", "--record-quantity", "Mu=parameter",
                          "--record-level", "detector", "--record-normalization",
                          json.dumps({"kind": "integrated-luminosity", "value": 1.0, "unit": "fb^-1"}),
                          "--record-process", "SYNTHETIC signal plus background", "--record-uncertainty-kind",
                          "statistical")
    if code != 0:
        raise SystemExit(f"render_results.py failed ({code}): {ren}")
    manifest = json.loads((work / "manifest.json").read_text())
    (out / "draft" / "main.tex").write_text(DRAFT, encoding="utf-8")
    ncode, nrep, _ = tool("manuscript", out / "draft", "--numbers", "--format", "json")
    # the numbers.tex comments carry absolute artifact paths: rewrite them relative to the output folder
    tex = (out / "draft" / "numbers.tex").read_text(encoding="utf-8").replace(str(out) + "/", "")
    (out / "draft" / "numbers.tex").write_text(tex, encoding="utf-8")

    # 6. HEPData
    same = True
    for rec, name in ((rec_path, "mass"), (mu_rec, "mu")):
        code, hd, err = tool("hepdata", "--artifact", rec, "--out", work / f"hepdata-{name}")
        if code != 0:
            raise SystemExit(f"hepdata_export.py failed on {rec.name} ({code}): {hd}")
        tables = sorted(p for p in (work / f"hepdata-{name}").glob("*.yaml") if p.name != "submission.yaml"
                        and "covariance" not in p.name)
        values = [float(v) for v in re.findall(r'"value":\s*([-+0-9.eE]+)', tables[0].read_text())
                  + re.findall(r"^\s*- value: ([-+0-9.eE]+)", tables[0].read_text(), re.M)]
        expect = (data.tolist() if name == "mass" else [manifest["quantities"]["Mu"]["source_value"]])
        same &= all(any(math.isclose(v, e, rel_tol=1e-12) for v in values) for e in expect)
    q = manifest["quantities"]["Mu"]
    table_values = [r["source_value"] for r in manifest["tables"]["Mass"]["rows"]]

    # latex (environment-dependent: not in results.json)
    latex = {"pdflatex": bool(shutil.which("pdflatex"))}
    if latex["pdflatex"]:
        for name, final in (("draft", False), ("final", True)):
            src = DRAFT if not final else DRAFT.replace(r"\begin{document}", r"\def\hepfinalbuild{}\begin{document}")
            (work / f"{name}.tex").write_text(src, encoding="utf-8")
            shutil.copy(out / "draft" / "numbers.tex", work / "numbers.tex")
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"], cwd=work,
                               capture_output=True, text=True, timeout=600)
            latex[f"{name}_build_ok"] = p.returncode == 0

    passed = {
        "auc_within_statistical_range_of_bayes_limit": bool(abs(auc_pull) <= CRITERIA["auc_pull_abs"]),
        "mu_consistent_with_injected_1": bool(abs(mu - 1.0) <= CRITERIA["mu_pull_abs"] * sigma_mu),
        "macros_round_trip_to_the_artifact": (q["source_value"] == mu and q["source_uncertainty"] == sigma_mu),
        "table_equals_the_record": table_values == data.tolist(),
        "hepdata_values_equal_the_artifacts": bool(same),
        "draft_numbers_consistent": ncode == 0 and not nrep.get("numbers", {}).get("mismatches"),
        "roofit_step_ran_or_exited_3": roofit.get("ran") is True or roofit.get("exit_code") == 3,
        "synthetic_watermark_in_macros": "\\hepSynthetic{" in tex,
    }
    passed = {k: bool(v) for k, v in passed.items()}
    results = {"label": LABEL, "seed": a.seed, "score": score_kind, "bayes_auc": rnd(bayes), "auc": rnd(measured),
               "auc_sigma": rnd(sigma_auc), "auc_pull": rnd(auc_pull, 4), "selected_data_events": int(data.sum()),
               "generated_signal_in_data": N_SIG_DATA,
               "expected_signal_after_cut": rnd(expected_sig), "signal_yield": rnd(y_sig), "mu": rnd(mu),
               "sigma_mu": rnd(sigma_mu), "macros": {"MuValue": q["value"], "MuUnc": q["uncertainty"],
                                                     "rounding": q["rounding"]},
               "numbers_check_exit": ncode, "criteria": CRITERIA, "pass": passed}
    if not a.with_bdt:  # the default run is the committed, byte-reproducible one
        (out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    else:
        (out / "results_bdt.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    (out / "report.md").write_text(
        f"# Analysis to paper (E-4)\n\n{LABEL}.\n\nScore: {score_kind}. AUC {measured:.4f} vs Bayes {bayes:.4f} "
        f"(pull {auc_pull:.2f}). mu = {q['value']} +- {q['uncertainty']} (PDG rounding of {mu:.6g} +- {sigma_mu:.6g}).\n\n"
        + "\n".join(f"- {k}: {'pass' if v else 'FAIL'}" for k, v in passed.items()) + "\n", encoding="utf-8")
    work_dir.cleanup()
    print(json.dumps({"pass": passed, "roofit": roofit, "latex": latex}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
