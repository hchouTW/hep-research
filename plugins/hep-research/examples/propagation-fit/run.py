#!/usr/bin/env python3
"""End-to-end multi-dataset propagation fit through the closed-form provider: SYNTHETIC B/C datasets fitted with
skills/hep-statistics/scripts/propagation_fit.py (cr-propagation C2).

SYNTHETIC. The data are generated here from the provider cr-secondary-ratio-closed-form (profile
theory:cr-secondary-ratio, ILLUSTRATIVE cross sections and transport values) at an ILLUSTRATIVE truth point. Nothing
here is a statement about the Galaxy or about any measurement, and no real data are fitted.

Binning: the provider's values are the ratio averaged uniformly in ln(E/n) over each bin (bin_semantics bin-averaged,
convention crsr:bin_average), not the ratio of bin integrals of r3 P2. The synthetic datasets are generated and
declared with the same semantics; a dataset declared bin-integrated is refused by the fit (test_propagation_fit).

Chain:
1. Registry: tools/provider_registry.py --write <work>/registry.json (absolute paths, outside the repository).
2. Datasets (dataset-record artifacts with the provider's observable block): A, 12 bins 1-1000 GeV/n, 3% uncorrelated
   + 2% correlated with exp(-|ln E_i - ln E_j| / 1.5) (a covariance file); B, 8 bins 10^0.5-10^2.5 GeV/n, 5%
   uncorrelated + 3% fully correlated (two components). Truth: D0_cm2_s = 3e28, delta = 0.5, L_kpc = 4, R0_gv = 1,
   disc_halfwidth_pc = 100, production norms of C->B and O->B = 1. Asimov records (values = prediction) and one
   pseudo-data draw (numpy default_rng(seed) through the Cholesky factor of each covariance).
3. Fits (propagation_fit.py fit, CLI), each with its own configuration in <work>:
   asimov-interior   family diffusion (D0_cm2_s, delta free; L_kpc = 4), norms with 10% priors (P15)       C2-1
   asimov-boundary   the same at delta = 0.2, the lower edge of the provider domain; profile interval      C2-1
   degeneracy        L_kpc also free: Fisher screen and a profile scan over L_kpc (degeneracy.py); the
                     fit-derived theory-spec and the statistical-result; covariance alternatives (P9)     C2-4
   families          BIG and SLIM (literature parameters, not expressible by the closed form), diffusion,
                     kolmogorov (delta = 1/3), iroshnikov-kraichnan (delta = 1/2); toy-calibrated delta
                     chi2 (--family-toys); posterior of diffusion (bayes_diagnostics)                    C2-3
   coverage          --toys plug-in toys at the truth, C->B norm only; D0_cm2_s, delta, flattest          C2-2
Pre-declared criteria: VALIDATION.md, section CRPROP-C2 (written before the first fit).

Usage (from the plugin root): python3 examples/propagation-fit/run.py --out DIR [--toys 1000] [--family-toys 200]
    [--stages asimov-interior,asimov-boundary,degeneracy,families,coverage] [--seed 20261028] [--cache-dir DIR]
Writes into DIR: the inputs, one folder per stage (result.json and the artifacts), results.json and report.md.
Exit 0 when every criterion of the stages run passes, 1 otherwise, 3 when numpy or scipy is missing.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN))

FIT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "propagation_fit.py"
PROVIDER = "cr-secondary-ratio-closed-form"
SPEC = PLUGIN / "profiles" / "theory" / "cr-secondary-ratio" / "derivations" / "theory-spec.json"
TRUTH = {"D0_cm2_s": 3.0e28, "delta": 0.5}
FIXED = {"L_kpc": 4.0, "R0_gv": 1.0, "disc_halfwidth_pc": 100.0}
BOUNDARY_DELTA = 0.2
STAGES = ("asimov-interior", "asimov-boundary", "degeneracy", "families", "coverage")
NORMS = [{"name": "xs-C-B", "kind": "production-norm", "channel": "C->B", "prior_sigma": 0.1},
         {"name": "xs-O-B", "kind": "production-norm", "channel": "O->B", "prior_sigma": 0.1}]
PARAMS = {"D0_cm2_s": {"start": 2.5e28, "scale": "log"}, "delta": {"start": 0.45, "scale": "linear"},
          "L_kpc": {"start": 4.0, "scale": "log"}}
DATASETS = {"set-a": {"dex": (0.0, 3.0, 12), "stat": 0.03, "syst": 0.02, "length": 1.5},
            "set-b": {"dex": (0.5, 2.5, 8), "stat": 0.05, "norm": 0.03}}
TOL_SIGMA = 0.1                      # C2-1


def edges(dex):
    import numpy as np
    lo, hi, n = dex
    return [float(f"{v:.12g}") for v in np.logspace(lo, hi, n + 1)]


def predict(runner, point, edge_list):
    req = {"protocol": "cr-provider/1", "provider": PROVIDER, "provider_version": "0.1.0", "points": [point],
           "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n",
                            "bins": [[a, b] for a, b in zip(edge_list, edge_list[1:])]}],
           "want": ["lis"], "seed": None}
    resp = runner.evaluate(req)
    res = resp["results"][0]
    if res["status"] != "ok":
        raise RuntimeError(f"provider failed at {point}: {res}")
    return res["predictions"][0], res["labels"]


def covariance(name, y, edge_list):
    import numpy as np
    spec = DATASETS[name]
    y = np.asarray(y)
    if "length" in spec:
        e = np.asarray(edge_list)
        ln_c = np.log(np.sqrt(e[:-1] * e[1:]))
        rho = np.exp(-np.abs(ln_c[:, None] - ln_c[None, :]) / spec["length"])
        return np.diag((spec["stat"] * y) ** 2) + np.outer(spec["syst"] * y, spec["syst"] * y) * rho
    return np.diag((spec["stat"] * y) ** 2) + np.outer(spec["norm"] * y, spec["norm"] * y)


def record(name, pred, labels, values, work: Path, tag) -> str:
    """A SYNTHETIC dataset-record with the provider's observable block and its uncertainty components."""
    from contracts import CONTRACTS_VERSION
    spec = DATASETS[name]
    y_nom = pred["values"]["values"]
    comps = []
    if "length" in spec:
        cov_ref = f"covariance-{name}.json"
        cov = covariance(name, y_nom, pred["values"]["edges"])
        (work / cov_ref).write_text(json.dumps({"labels": [f"bin {i}" for i in range(len(y_nom))],
                                                "matrix": cov.tolist(), "kind": "absolute", "units": "1"}) + "\n")
        comps.append({"name": f"total ({spec['stat']:.0%} uncorrelated + {spec['syst']:.0%} with correlation length "
                              f"{spec['length']} in ln E)", "kind": "systematic", "correlation": "covariance",
                      "covariance_ref": cov_ref})
    else:
        comps.append({"name": "statistical", "kind": "statistical", "correlation": "uncorrelated",
                      "values": [spec["stat"] * v for v in y_nom]})
        comps.append({"name": "normalization", "kind": "systematic", "correlation": "fully-correlated",
                      "values": [spec["norm"] * v for v in y_nom]})
    status = ["synthetic"] + (["asimov"] if tag.startswith("asimov") else [])
    doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": f"propfit-{name}-{tag}", "artifact_type": "dataset-record",
           "objective": "SYNTHETIC B/C points generated from the closed-form provider at an ILLUSTRATIVE truth point",
           "bindings": {"experiments": [], "theory": [{"profile": "theory:cr-secondary-ratio", "version": "0.1.0"}]},
           "versions": {"plugin": "", "contracts": CONTRACTS_VERSION, "profiles": {"theory:cr-secondary-ratio": "0.1.0"}},
           "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-28", "evidence_ids": []},
           "inputs": [], "outputs": [], "status": status, "unresolved_inputs": [],
           "extension": {"dataset_id": f"synthetic:propfit-{name}-{tag}", "source_evidence_ids": [],
                         "observable": json.loads(json.dumps(pred["observable"])),
                         "data": {"edges": pred["values"]["edges"], "values": [float(v) for v in values], "unit": "1",
                                  "uncertainties": comps},
                         "covariance": {"status": "present"}, "status": "synthetic"}}
    path = f"{name}-{tag}.json"
    (work / path).write_text(json.dumps(doc, indent=1) + "\n")
    return path


def make_datasets(registry, work: Path, cache, seed):
    import numpy as np
    from core.provider.runner import ProviderRunner
    out = {}
    rng = np.random.default_rng(seed)
    with ProviderRunner(str(registry), cache_dir=cache, session="serve") as runner:
        for tag, delta in (("asimov", TRUTH["delta"]), ("asimov-boundary", BOUNDARY_DELTA), ("pseudo", TRUTH["delta"])):
            point = {**FIXED, "D0_cm2_s": TRUTH["D0_cm2_s"], "delta": delta}
            for name, spec in DATASETS.items():
                pred, labels = predict(runner, point, edges(spec["dex"]))
                y = np.asarray(pred["values"]["values"])
                if tag == "pseudo":
                    y = y + np.linalg.cholesky(covariance(name, y, pred["values"]["edges"])) @ rng.normal(size=len(y))
                out[(tag, name)] = record(name, pred, labels, y, work, tag)
        stats = dict(runner.stats)
    return out, stats


def config(records, tag, families, **extra):
    cfg = {"provider": {"id": PROVIDER, "version": "0.1.0"},
           "datasets": [{"name": n, "measurement": records[(tag, n)], "observable": "B/C"} for n in DATASETS],
           "parameters": PARAMS, "fixed": {"R0_gv": FIXED["R0_gv"], "disc_halfwidth_pc": FIXED["disc_halfwidth_pc"]},
           "nuisances": NORMS, "families": families}
    cfg.update(extra)
    return cfg


DIFFUSION = {"name": "diffusion", "free": ["D0_cm2_s", "delta"], "fixed": {"L_kpc": 4.0}}


def run_fit(work: Path, stage, cfg, registry, cache, max_evaluations=2000):
    path = work / f"{stage}.config.json"
    path.write_text(json.dumps(cfg, indent=1) + "\n")
    out = work / stage
    cmd = [sys.executable, str(FIT), "fit", "--input", str(path), "--provider-registry", str(registry), "--out",
           str(out), "--max-evaluations", str(max_evaluations)]
    if cache:
        cmd += ["--cache-dir", str(cache)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"status": "unparsable", "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    return proc.returncode, doc


def recovery(fit, truth_coords, nu_truth):
    """|best - truth| / sigma per free parameter (fit coordinates) and multiplier."""
    rows = {}
    for p in fit["parameters"]:
        t = truth_coords[p["name"]]
        rows[p["name"]] = {"best_fit": p["best_fit"], "truth": t, "sigma_coordinate": p["sigma_coordinate"],
                           "pull": None if not p["sigma_coordinate"] else
                           abs(p["best_fit_coordinate"] - (math.log(t) if p["scale"] == "log" else t))
                           / p["sigma_coordinate"]}
    for n in fit["nuisances"]:
        rows[n["name"]] = {"best_fit": n["value"], "truth": nu_truth, "sigma_coordinate": n["sigma"],
                           "pull": abs(n["value"] - nu_truth) / n["sigma"]}
    return rows


def validate(paths):
    proc = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), *map(str, paths)],
                          capture_output=True, text=True, timeout=600)
    return proc.returncode, proc.stdout[-3000:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="working folder (outside the repository)")
    ap.add_argument("--toys", type=int, default=1000)
    ap.add_argument("--family-toys", type=int, default=200)
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--cache-dir", help="provider cache folder (default <out>/cache)")
    a = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "missing-dependency", "error": "needs numpy and scipy"}))
        return 3
    stages = [s for s in a.stages.split(",") if s]
    unknown = sorted(set(stages) - set(STAGES))
    if unknown:
        ap.error(f"unknown stages {unknown}; choose from {list(STAGES)}")
    work = Path(a.out).resolve()
    work.mkdir(parents=True, exist_ok=True)
    cache = Path(a.cache_dir).resolve() if a.cache_dir else work / "cache"
    registry = work / "registry.json"
    reg = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write", str(registry)],
                         capture_output=True, text=True, timeout=300)
    if reg.returncode != 0:
        print(reg.stdout, reg.stderr)
        return 1
    records, gen_stats = make_datasets(registry, work, cache, a.seed)
    results = {"label": "SYNTHETIC", "provider": PROVIDER, "truth": {**TRUTH, **FIXED}, "seed": a.seed,
               "generation_provider_evaluations": gen_stats, "stages": {}, "criteria": {}}
    evals = gen_stats["points_sent"]
    crit = results["criteria"]

    def note(stage, code, doc):
        nonlocal evals
        evals += (doc.get("provider_evaluations") or {}).get("points_sent", 0)
        results["stages"][stage] = {"exit": code, "status": doc.get("status"), "reason": doc.get("reason"),
                                    "detail": doc.get("detail") or doc.get("error"),
                                    "provider_evaluations": doc.get("provider_evaluations")}

    if "asimov-interior" in stages:
        code, doc = run_fit(work, "asimov-interior", config(records, "asimov", [DIFFUSION]), registry, cache)
        note("asimov-interior", code, doc)
        fit = (doc.get("fits") or [{}])[0]
        rec = recovery(fit, TRUTH, 1.0) if fit.get("status") == "converged" else {}
        results["stages"]["asimov-interior"]["recovery"] = rec
        crit["C2-1 interior: converged, every pull <= 0.1"] = bool(rec) and code == 0 and all(
            r["pull"] is not None and r["pull"] <= TOL_SIGMA for r in rec.values())
    if "asimov-boundary" in stages:
        cfg = config(records, "asimov-boundary", [DIFFUSION], intervals=["delta"])
        code, doc = run_fit(work, "asimov-boundary", cfg, registry, cache)
        note("asimov-boundary", code, doc)
        fit = (doc.get("fits") or [{}])[0]
        ok = code == 0 and fit.get("status") == "converged"
        detail = {}
        if ok:
            p = {q["name"]: q for q in fit["parameters"]}
            iv = {i["parameter"]: i for i in fit.get("profile_intervals") or []}.get("delta", {})
            w = (iv.get("upper") or {}).get("width_coordinate")
            kkt = fit["convergence"]["kkt"]
            detail = {"delta_best_fit": p["delta"]["best_fit"], "at_bound": p["delta"]["at_bound"], "kkt": kkt,
                      "interval": iv, "sigma_one_sided": w,
                      "pull_one_sided": None if not w else abs(p["delta"]["best_fit"] - BOUNDARY_DELTA) / w,
                      "others": {k: v for k, v in recovery(fit, {**TRUTH, "delta": BOUNDARY_DELTA}, 1.0).items()
                                 if k != "delta"}}
            ok = (p["delta"]["at_bound"] and all(k["ok"] for k in kkt) and (iv.get("lower") or {}).get("kind") == "bound"
                  and w is not None and detail["pull_one_sided"] <= TOL_SIGMA
                  and all(r["pull"] is not None and r["pull"] <= TOL_SIGMA for r in detail["others"].values()))
        results["stages"]["asimov-boundary"]["recovery"] = detail
        crit["C2-1 boundary: on the bound, KKT ok, within 0.1 one-sided sigma, others within 0.1 sigma"] = bool(ok)
    if "degeneracy" in stages:
        fam = {"name": "diffusion-halo", "free": ["D0_cm2_s", "delta", "L_kpc"], "fixed": {}}
        cfg = config(records, "pseudo", [fam], theory_spec=str(SPEC),
                     degeneracy_scan={"family": "diffusion-halo", "parameter": "L_kpc", "points": 7},
                     covariance_alternatives={"family": "diffusion", "dataset": "set-a",
                                              "model": {"sources": [{"name": "stat", "model": "none", "relative": 0.03},
                                                                    {"name": "syst", "model": "length",
                                                                     "relative": 0.02, "length": 1.5}]},
                                              "source": "syst", "lengths": [0.5, 1.5, 4.0]})
        cfg["families"].append(DIFFUSION)
        code, doc = run_fit(work, "degeneracy", cfg, registry, cache)
        note("degeneracy", code, doc)
        st = work / "degeneracy"
        arts = [st / "theory-spec.json", st / "statistical-result.json"]
        have = all(p.is_file() for p in arts)
        vcode, vout = validate(arts) if have else (None, "artifacts missing")
        entries = json.loads(arts[0].read_text())["extension"]["degenerate_directions"] if have else []
        results["stages"]["degeneracy"].update(
            degeneracies=doc.get("degeneracies"), validate_exit=vcode,
            theory_spec_entries=entries, covariance_alternatives=doc.get("covariance_alternatives"),
            fits=[{k: f.get(k) for k in ("family", "status", "chi2", "dof", "p_value", "parameters", "convergence")}
                  for f in doc.get("fits") or []])
        crit["C2-4 degenerate_directions are objects (profile-scan, valid_range); artifacts validate"] = (
            code == 0 and have and vcode == 0 and bool(entries)
            and all(isinstance(e, dict) and e.get("evidence") == "profile-scan" and e.get("valid_range") for e in entries)
            and any(e.get("combination") == "D0_cm2_s/L_kpc" for e in entries))
        alts = (doc.get("covariance_alternatives") or {}).get("alternatives") or []
        crit["P9 covariance alternatives fitted one by one"] = len(alts) == 3 and all(r["status"] == "converged"
                                                                                       for r in alts)
    if "families" in stages:
        lit = ["D0_cm2_s", "delta", "L_kpc"]
        fams = [{"name": "BIG", "free": lit + ["V_A_kms", "V_c_kms", "R_break_gv", "delta_below", "s"], "fixed": {}},
                {"name": "SLIM", "free": lit + ["R_break_gv", "delta_below", "s"], "fixed": {}},
                DIFFUSION,
                {"name": "kolmogorov", "free": ["D0_cm2_s"], "fixed": {"L_kpc": 4.0, "delta": 1.0 / 3.0}},
                {"name": "iroshnikov-kraichnan", "free": ["D0_cm2_s"], "fixed": {"L_kpc": 4.0, "delta": 0.5}}]
        cfg = config(records, "pseudo", fams, family_toys={"n": a.family_toys, "seed": a.seed % 100000 + 3,
                                                           "alpha": 0.05},
                     posterior={"family": "diffusion", "chains": 4, "steps": 20000, "seed": 5})
        code, doc = run_fit(work, "families", cfg, registry, cache)
        note("families", code, doc)
        cal = doc.get("family_calibration") or {}
        results["stages"]["families"].update(families=doc.get("families"),
                                             not_expressible=doc.get("families_not_expressible"),
                                             calibration=[{k: e.get(k) for k in ("family", "chi2", "delta_chi2", "toys",
                                                                                  "failed", "p_toys", "surviving")}
                                                          for e in cal.get("families") or []],
                                             posterior={k: (doc.get("posterior") or {}).get(k) for k in
                                                        ("status", "reason", "rhat_max_seen", "ess_min_seen",
                                                         "acceptance", "proposals_outside_box", "intervals_68")})
        ne = {f["family"] for f in doc.get("families_not_expressible") or []}
        listed = cal.get("families") or []
        crit["C2-3 BIG, SLIM listed as not expressible; every surviving family listed with its toy-calibrated delta "
             "chi2"] = (code == 0 and ne == {"BIG", "SLIM"} and len(listed) == 3
                        and all(e.get("p_toys") is not None and e.get("delta_chi2") is not None for e in listed)
                        and set(cal.get("surviving") or []) == {e["family"] for e in listed if e.get("surviving")})
    if "coverage" in stages:
        cfg = config(records, "asimov", [DIFFUSION],
                     toys={"family": "diffusion", "n": a.toys, "seed": a.seed % 100000 + 1,
                           "truth": {**TRUTH, "xs-C-B": 1.0}, "test": ["D0_cm2_s", "delta", "flattest"]})
        cfg["nuisances"] = NORMS[:1]
        code, doc = run_fit(work, "coverage", cfg, registry, cache)
        note("coverage", code, doc)
        toys = doc.get("toys") or {}
        results["stages"]["coverage"].update(
            generated=toys.get("generated"), failed=toys.get("failed"),
            eigenvalue_ratio_min_max=toys.get("eigenvalue_ratio_min_max"),
            flattest_direction=toys.get("flattest_direction"),
            response_model_validation=(toys.get("response_model") or {}).get("validation"),
            tests={k: {"coverage": v["coverage_wilks"]["headline"]["value"], "deviation": v["deviation"],
                       "band_bonferroni": v["band_bonferroni"], "band_3sigma": v["band_3sigma"],
                       "pass_bonferroni": v["pass_bonferroni"], "pass_3sigma": v["pass_3sigma"],
                       "critical_value_toys": v["critical_value_toys"]} for k, v in (toys.get("tests") or {}).items()})
        crit[f"C2-2 coverage of D0_cm2_s, delta, flattest within the Bonferroni band (n = {a.toys})"] = (
            code == 0 and toys.get("status") == "ok" and a.toys >= 1000 and bool(toys.get("coverage_pass")))
    results["provider_point_evaluations_total"] = evals
    results["all_pass"] = all(crit.values())
    (work / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    (work / "report.md").write_text(report(results))
    print(json.dumps({"all_pass": results["all_pass"], "criteria": crit, "provider_point_evaluations": evals,
                      "out": str(work)}, indent=1))
    return 0 if results["all_pass"] else 1


def report(r) -> str:
    lines = ["# Propagation fit through the closed-form provider (SYNTHETIC)", "",
             f"Provider {r['provider']}; truth {r['truth']}; seed {r['seed']}. All inputs ILLUSTRATIVE.", "",
             "| Criterion | Result |", "|---|---|"]
    lines += [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in r["criteria"].items()]
    lines += ["", f"Provider point evaluations: {r['provider_point_evaluations_total']}.", ""]
    for stage, s in r["stages"].items():
        lines.append(f"- {stage}: exit {s['exit']}, status {s['status']}"
                     + (f", reason {s['reason']}" if s.get("reason") else ""))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
