"""The registered gate runs and section 8.7 calibrations of phase 1 of the simulator calibration workflow (task card
`docs/dev/simulator-calibration/simcal-tasks/phase-1.md`, "Thresholds and test designs"). Not a unit test module.

  python3 calibration_phase1_gates.py --gate agreement --out FILE            gate 2: reweighting and rerun agree
  python3 calibration_phase1_gates.py --calibration p0-z --reps A:B --out FILE    calibration 1, repetitions A..B-1
  python3 calibration_phase1_gates.py --summarize-p0-z FILE ... --out FILE   calibration 1 over all its shards

Every output records the commit and the SHA-256 of the files that decide it. Gate 1 (the negative tests of A0, P0, P2,
P5) is the unit tests listed in the card; calibration 2 (A0 on the ZDC linearity example) is
tests.core.test_calibration_preflight.A0.test_linearity_example."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import design, kernel_check, linear  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration.toy import observe  # noqa: E402

SEED_NOMINAL, SEED_RERUN, SEED_SCAN = 20261110, 20261111, 20261112
N_MC = 40_000
N_SCAN = 64
ALPHA = 0.01
FILES = ["core/calibration/toy.py", "core/calibration/reweight.py", "core/calibration/linear.py",
         "core/calibration/design.py", "core/calibration/kernel_check.py", "core/calibration/evaluator.py",
         "core/calibration/chain.py", "core/calibration/data/toy_detector_design.json",
         "tests/core/calibration_phase1.py", "tests/core/calibration_phase1_gates.py",
         "docs/dev/simulator-calibration/simcal-tasks/phase-1.md"]
# gate 2 item 1: one case per non-generator density node, with the parameters acting entirely through its density
NODE_CASES = [("photon_generation", ["light_yield"]), ("pde", ["pde"]), ("gain", ["gain", "enf"]),
              ("electronics", ["noise_width"])]
NO_SUPPRESSION_RUNS = ["beam1", "beam2", "beam3", "beam4", "light", "track5", "track2", "eop"]


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}}


def toy_case(events=None, seed=None, runs=None, methods=None, proposal=None, drop=()):
    events = N_MC if events is None else events
    seed = SEED_NOMINAL if seed is None else seed
    fx = H.toy_design()
    contract, plan = copy.deepcopy(fx["contract"]), copy.deepcopy(fx["plan"])
    plan["evaluator"]["events"] = events
    plan["seeds"] = {"nominal": seed, "resample": seed + 1}
    if runs is not None:
        plan["evaluator"]["runs"] = list(runs)
        contract["observables"] = [o for o in contract["observables"] if o["sample"] in runs]
    if drop:
        contract["parameters"] = [p for p in contract["parameters"] if p["name"] not in drop]
    plan["methods"].update(methods or {})
    if proposal:
        plan["proposal"] = proposal
    return contract, plan, fx["release"]["content"]["systematic"]


def chi2_affected(rw: dict, rr: dict, ev, node: str, pars: list[str]) -> tuple[float, int]:
    """Gate 2 criterion (ii): chi2 of the difference over the observables of the runs in which the node acts (its
    kernel there reads the case's parameters; an injected reference does not), with the paired MC covariance of the
    difference (tightened from V_MC,reweighted + V_MC,rerun after the review, F3, before the rerun of the gate)."""
    runs = {rid for rid, run in ev.model.runs.items() if node in run.kernels and set(run.kernels[node].params) & set(pars)}
    keep = np.array([r in runs for r in rw["runs"]])
    d = (rw["pred"] - rr["pred"])[keep]
    V = kernel_check.paired_covariance(rw, rr, rr.get("independent_runs", ()))[np.ix_(keep, keep)]
    chi2 = float(d @ np.linalg.solve(V, d))
    return float(stats.chi2.sf(chi2, len(d))), int(len(d))


def agreement() -> dict:
    """Gate 2 as registered: items 1-3 and the criteria (i)-(iii)."""
    t0 = time.time()
    cases = []
    for node, pars in NODE_CASES:
        if node == "electronics":
            c = toy_case(runs=NO_SUPPRESSION_RUNS, drop=("threshold",), methods={"noise_width": "analytic-reweighting"})
            c[1]["kernels"]["electronics"]["filter_ignorable"] = True   # the plan's recorded decision (section 6.1)
            cases.append((node, pars, c))
        else:
            cases.append((node, pars, toy_case()))
    mix = {"nodes": ["pde"], "components": [{"theta": {"pde": v}} for v in (0.245, 0.25, 0.255)]}
    cases.append(("photon_generation+pde", ["light_yield", "pde"], toy_case(proposal=mix)))
    m2 = 3 * len(cases)
    out_cases, ok = [], True
    for label, pars, (contract, plan, syst) in cases:
        ev = E.make(plan)
        node = label.split("+")[0]
        sup = design.support_check(ev, contract, plan, pars)
        d = linear.design(ev, contract, plan, systematics=syst)
        # the worst-ESS point of 64 Sobol points over this case's parameters, and the next two Sobol points
        scan = design.p5(ev, contract, plan, items=("ess",), n_scan=N_SCAN, seed=SEED_SCAN, scan_parameters=pars)
        pts = kernel_check.worst_ess_and_next(scan)
        p0 = kernel_check.p0(ev, contract, plan, d, pts, SEED_RERUN)
        rows = []
        for k, pt in enumerate(pts):
            theta = {**d["theta_ref"], **pt}
            rw = ev.evaluate(theta, names=d["names"])
            rr = ev.rerun(sorted({n for p in pars for n in ev.model.param_nodes[p]}, key=ev.model.order.index),
                          theta, (SEED_RERUN, k), names=d["names"], params=pars)
            pval, ndf = chi2_affected(rw, rr, ev, node, pars)
            rows.append({"point": pt, "chi2_p": pval, "ndf": ndf, "chi2_pass": pval >= ALPHA / m2,
                         "methods": rw["methods"]})
        case_ok = (sup["status"] == "passed" and p0["status"] == "passed" and all(r["chi2_pass"] for r in rows))
        ok &= case_ok
        out_cases.append({"case": label, "parameters": pars, "support": sup["status"], "p0": p0["status"],
                          "p0_max_ratio": max(x["max_ratio"] for x in p0["points"]), "points": rows,
                          "worst_ess": scan["items"]["ess"], "pass": case_ok})
    det = deterministic_rerun()
    ok &= det["pass"]
    return {"gate": "phase-1 gate 2: reweighting and rerun agree", "status": "passed" if ok else "failed",
            "cases": out_cases, "deterministic_rerun": det, "M2": m2, "alpha": ALPHA,
            "seeds": {"nominal": SEED_NOMINAL, "rerun": SEED_RERUN, "scan": SEED_SCAN}, "n_mc": N_MC,
            "seconds": round(time.time() - t0, 1), "provenance": provenance(), "status_label": "synthetic"}


def deterministic_rerun() -> dict:
    """Gate 2 item 3: module b's relative gain and layer b's offset and sum term, rerun from stored inputs, equal the
    events generated at the new values with the same random numbers, to a relative 1e-12."""
    contract, plan, _ = toy_case()
    ev = E.make(plan)
    rows, ok = [], True
    for th in ({"relative_gain_b": 1.02}, {"layer_b_offset": 0.1}, {"sum_term_b": 0.55},
               {"relative_gain_b": 0.98, "layer_b_offset": -0.15, "sum_term_b": 0.45}):
        rerun = ev.evaluate(th)
        fresh = ev.generate(ev.seeds["nominal"], th)           # the same random numbers as the nominal events
        full = observe(ev.model, {r: fresh["runs"][r]["events"] for r in fresh["runs"]},
                       {r: np.ones(ev.model.runs[r].n) for r in ev.model.runs})
        rel = float(np.max(np.abs(rerun["pred"] - full["pred"]) / np.maximum(np.abs(full["pred"]), 1e-300)))
        rows.append({"theta": th, "max_relative_difference": rel, "methods": rerun["methods"]})
        ok &= rel <= 1e-12 and set(rerun["methods"].values()) == {"rerun"}
    return {"pass": bool(ok), "rows": rows}


def p0_z(reps: range) -> dict:
    """Calibration 1 (phase-1 part of the section 8.7 row 'Bonferroni z of P0, P6'): P0 with correct kernels, the
    light-yield, PDE, gain and ENF parameters by analytic reweighting at the worst-ESS and two further Sobol points,
    seeds 20261110 + 2r (nominal) and 20261110 + 2r + 1 (resample)."""
    pars = ["light_yield", "pde", "gain", "enf"]
    rows = []
    for r in reps:
        t = time.time()
        contract, plan, syst = toy_case(seed=SEED_NOMINAL + 2 * r)
        ev = E.make(plan)
        d = linear.design(ev, contract, plan, systematics=syst)
        scan = design.p5(ev, contract, plan, items=("ess",), n_scan=N_SCAN, seed=SEED_SCAN, scan_parameters=pars)
        pts = kernel_check.worst_ess_and_next(scan)
        res = kernel_check.p0(ev, contract, plan, d, pts, SEED_NOMINAL + 2 * r + 1)
        rows.append({"rep": r, "status": res["status"], "max_ratio": max(x["max_ratio"] for x in res["points"]),
                     "seconds": round(time.time() - t, 1)})
    return {"calibration": "P0 z (phase 1)", "reps": [reps.start, reps.stop], "rows": rows,
            "false_alarms": sum(x["status"] != "passed" for x in rows), "provenance": provenance()}


def summarize_p0_z(paths: list[str]) -> dict:
    """Calibration 1 over its shards: every repetition 0..999 present once, the same provenance, false alarms
    <= 16 of 1000 confirms alpha = 0.01 (registered rule); the observed rate and its one-sided 95% upper limit."""
    rows, prov = {}, set()
    for p in paths:
        d = json.loads(Path(p).read_text())
        prov.add(json.dumps({k: v for k, v in d["provenance"].items() if k != "python"}, sort_keys=True))
        for x in d["rows"]:
            if x["rep"] in rows:
                return {"status": "failed", "reason": f"repetition {x['rep']} twice"}
            rows[x["rep"]] = x
    missing = sorted(set(range(1000)) - set(rows))
    if missing:
        return {"status": "incomplete", "missing": missing[:20], "n_missing": len(missing)}
    if len(prov) != 1:
        return {"status": "failed", "reason": "shards with different provenance"}
    fa = sum(x["status"] != "passed" for x in rows.values())
    upper = float(stats.beta.ppf(0.95, fa + 1, 1000 - fa)) if fa < 1000 else 1.0
    return {"status": "passed" if fa <= 16 else "failed", "false_alarms": fa, "repetitions": 1000,
            "rate": fa / 1000, "upper_95": upper, "rule": "false alarms <= 16 of 1000 confirms alpha = 0.01",
            "max_ratio_quantiles": np.quantile([x["max_ratio"] for x in rows.values()], [0.5, 0.9, 0.99, 1.0]).tolist(),
            "provenance": json.loads(prov.pop())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate", choices=["agreement"])
    ap.add_argument("--calibration", choices=["p0-z"])
    ap.add_argument("--reps", help="A:B, the repetitions of calibration 1 in this shard")
    ap.add_argument("--summarize-p0-z", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.gate == "agreement":
        out = agreement()
    elif args.calibration == "p0-z":
        a, b = (int(x) for x in args.reps.split(":"))
        out = p0_z(range(a, b))
    elif args.summarize_p0_z:
        out = summarize_p0_z(args.summarize_p0_z)
    else:
        ap.error("nothing to do")
    Path(args.out).write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({k: out.get(k) for k in ("status", "false_alarms", "seconds")}, default=float))
    return 0 if out.get("status", "passed") in ("passed", None) or args.calibration else 1


if __name__ == "__main__":
    sys.exit(main())
