#!/usr/bin/env python3
"""Reproduce published model-independent limits from an open full likelihood (hep-statistics audit T17).

Record: ATLAS-SUSY-2018-31 (JHEP 12 (2019) 060, arXiv:1908.03122), HEPData ins1748602 v3; likelihood pallet
doi:10.17182/hepdata.89408.v3/r2 (HEPData resource 1935437, CC0), checked against SHA256 below. Region SRB
(RegionB, channel SR_cuts: one bin, 3 events observed). OBSERVED public data; the comparison is a validation of the
tool chain, not a new physics result.

The comparison targets, tolerances, fit definition and negative control were fixed before the first computation
(PREREGISTRATION below; the same text with its time stamp is kept with the task evidence):
- fit: a signal sample of nominal yield 1 event in SR_cuts with a free normfactor (the POI is the signal count S),
  no signal systematics, validation channels pruned (the paper's fits use CRs and SRs only);
- construction: CLs with the one-sided profile likelihood ratio (qtilde); the paper does not state asymptotic or
  pseudo-experiments, so both are computed. The asymptotic construction is primary; the toy construction
  (--toys, default 5000 per hypothesis and scan point) is reported with its own verdict;
- reproduced: S95 observed and expected with +-1 and +-2 sigma (a full CLs scan in S, not CLs at one point), CLb at
  the observed limit, the discovery p0, the background-only post-fit SM yield in SRB, the best-fit S, and pulls of the
  nuisance parameters in the background-only fit;
- negative control: the same fit without the control region CRtt_cuts must fail at least one tolerance.

Post-hoc diagnosis (added after the 5,000-toy run, not preregistered; it changes no preregistered verdict): the toy
construction does not reproduce the observed and -1 sigma limits, so it is checked against the exact counting
construction of the one-bin SRB (toy_diagnosis), and pyhf's asymptotic formulae are run on the same bare model. The
toys are correct; the asymptotic formulae understate the limit at n = 3, and the published values follow them.

Usage (from the plugin root): python3 examples/stats-benchmarks/published-likelihood-sbottom/run.py
    --pallet PATH_TO_TGZ | --download CACHE_DIR   [--toys 5000] [--seed 20261012] [--out DIR]
Without the pallet (no file, no network) the result is not-run (exit 4), never a pass.
Exit codes: 0 the primary construction reproduces every value and the negative control fails; 1 otherwise; 2 bad
usage or pyhf missing; 4 not-run (pallet unavailable or its checksum differs). Needs pyhf 0.7.6 and NumPy.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import tarfile
import urllib.request
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))

SHA256 = "c425e741d8ab0adfbf8611ae86a92f24d7071ccaeb7bf3b2937bcc75a5712fa8"
URL = "https://www.hepdata.net/record/resource/1935437?view=true"
MEMBER = "RegionB/BkgOnly.json"
PREREGISTRATION = {
    "reference_values": {
        "S95_obs": {"value": 4.9, "digitization": 0.05, "source": "Table 7"},
        "S95_exp_median": {"value": 5.1, "digitization": 0.05, "source": "Table 7"},
        "S95_exp_plus1": {"value": 7.9, "digitization": 0.1, "source": "Table 7: 5.1 + 2.8"},
        "S95_exp_minus1": {"value": 3.4, "digitization": 0.1, "source": "Table 7: 5.1 - 1.7"},
        "CLb": {"value": 0.45, "digitization": 0.005, "source": "Table 7"},
        "postfit_SM_yield_SRB": {"value": 3.3, "digitization": 0.05, "source": "Table 6, SRB"},
    },
    "p0": {"published": 0.5, "truncated_at": 0.5, "pass_if_at_least": 0.45},
    "backend_allowance": {"relative": 0.05, "CLb_absolute": 0.05},
}
LEVEL = 0.05


def load_pallet(path: Path) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise FileNotFoundError(f"pallet sha256 {digest} differs from the recorded {SHA256}")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        member = tf.extractfile(MEMBER)
        if member is None:
            raise FileNotFoundError(f"{MEMBER} not in the pallet")
        return json.loads(member.read())


def build(bkg: dict, keep_cr: bool = True):
    import pyhf
    ws = pyhf.Workspace(bkg)
    drop = ["VRtt_cuts"] + ([] if keep_cr else ["CRtt_cuts"])
    ws = ws.prune(channels=drop)
    spec = json.loads(json.dumps(dict(ws)))
    poi = spec["measurements"][0]["config"]["poi"]
    for ch in spec["channels"]:
        if ch["name"] == "SR_cuts":
            ch["samples"].append({"name": "unit_signal", "data": [1.0],
                                  "modifiers": [{"name": poi, "type": "normfactor", "data": None}]})
    for p in spec["measurements"][0]["config"]["parameters"]:
        if p["name"] == poi:
            p["bounds"] = [[0.0, 40.0]]
    if not any(p["name"] == poi for p in spec["measurements"][0]["config"]["parameters"]):
        spec["measurements"][0]["config"]["parameters"].append({"name": poi, "bounds": [[0.0, 40.0]], "inits": [1.0]})
    ws = pyhf.Workspace(spec)
    model = ws.model(modifier_settings={"normsys": {"interpcode": "code4"}, "histosys": {"interpcode": "code4p"}})
    return model, ws.data(model), poi


def asymptotic(model, data):
    import numpy as np
    import pyhf
    obs, exp = pyhf.infer.intervals.upper_limits.upper_limit(data, model, scan=None, level=LEVEL, rtol=1e-6)
    cls_obs, (clsb, clb) = pyhf.infer.hypotest(float(obs), data, model, test_stat="qtilde", return_tail_probs=True)
    # with test_stat q0, hypotest returns p0 first (its tail-probability list holds the background tail, not p0)
    p0 = pyhf.infer.hypotest(0.0, data, model, test_stat="q0")
    scan = np.linspace(0.0, 15.0, 31)
    curve = [float(pyhf.infer.hypotest(float(s), data, model, test_stat="qtilde")) for s in scan]
    return {"S95_obs": float(obs), "S95_exp": [float(e) for e in exp], "CLb_at_S95_obs": float(clb),
            "CLsb_at_S95_obs": float(clsb), "p0": float(p0), "cls_scan": {"S": scan.tolist(), "CLs_obs": curve}}


def background_only(model, data, poi):
    import numpy as np
    import pyhf
    init = model.config.suggested_init()
    pars = pyhf.infer.mle.fixed_poi_fit(0.0, data, model)
    best = pyhf.infer.mle.fit(data, model)
    exp_main = model.expected_actualdata(pars)
    idx = model.config.channel_slices["SR_cuts"]
    sr = float(np.asarray(exp_main)[idx][0])
    labels = model.config.par_names
    pulls = {}
    for name in model.config.par_order:
        sl = model.config.par_slice(name)
        if model.config.param_set(name).constrained and name != poi:
            for k, i in enumerate(range(sl.start, sl.stop)):
                pulls[f"{name}[{k}]" if sl.stop - sl.start > 1 else name] = float(pars[i] - init[i])
    return {"postfit_SM_yield_SRB": sr, "best_fit_S": float(best[model.config.poi_index]),
            "largest_abs_pull_bkg_only": max(pulls.items(), key=lambda kv: abs(kv[1])) if pulls else None,
            "n_parameters": len(labels)}


TOY_GRID = [2.5, 3.5, 4.5, 5.5, 6.5, 8.0, 9.5]  # S values; fixed before the toy run (spans the published band)
NORMAL_PERCENTILES = [2.27501319, 15.86552539, 50.0, 84.13447461, 97.72498681]  # as pyhf's ToyCalculator


def _toy_point(args):
    """One grid point in a worker: pyhf ToyCalculator distributions, the observed CLs with exact-interval range, and
    the expected CLs band computed as pyhf 0.7.6 does (percentiles of CLs over the background-only toys), with
    numpy's current percentile API: pyhf 0.7.6 passes the removed `interpolation` keyword, so its own
    expected_pvalues fails with NumPy >= 2.4 (found here)."""
    bkg, s, toys, seed = args
    import numpy as np
    import pyhf
    from core.stats.tail_estimation import clopper_pearson
    model, data, _ = build(bkg)
    np.random.seed(seed)
    calc = pyhf.infer.calculators.ToyCalculator(data, model, test_stat="qtilde", ntoys=toys, track_progress=False)
    t_obs = calc.teststatistic(float(s))
    sb, b = calc.distributions(float(s))
    clsb, clb, cls = (float(x) for x in calc.pvalues(t_obs, sb, b))
    per_toy = np.array([float(calc.pvalues(t, sb, b)[2]) for t in b.samples])
    exp = np.percentile(per_toy, NORMAL_PERCENTILES, method="linear").tolist()
    k_sb, k_b = round(clsb * toys), round(clb * toys)
    lo_sb, hi_sb = clopper_pearson(k_sb, toys, 0.95)
    lo_b, hi_b = clopper_pearson(k_b, toys, 0.95)
    return {"S": float(s), "CLs_obs": cls, "CLsb": clsb, "CLb": clb, "k_sb": k_sb, "k_b": k_b, "toys": toys,
            "CLs_obs_range_95": [lo_sb / hi_b, hi_sb / lo_b if lo_b > 0 else None], "CLs_exp": exp, "seed": seed}


def _crossing(grid, vals, level=LEVEL):
    """S where CLs falls through the level between two grid points, interpolating log CLs linearly (CLs falls about
    exponentially in S; interpolating CLs itself put every crossing 0.06-0.12 too high on the 1.0-wide grid, a
    defect found after the 5,000-toy run that changed no verdict). Linear in CLs when the lower value is 0."""
    for (s0, v0), (s1, v1) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
        if v0 is not None and v1 is not None and v0 >= level > v1:
            if v1 > 0:
                return float(s0 + (s1 - s0) * (math.log(v0) - math.log(level)) / (math.log(v0) - math.log(v1)))
            return float(s0 + (s1 - s0) * (v0 - level) / (v0 - v1))
    return None


def toy_based(bkg, toys, seed, workers):
    from multiprocessing import get_context
    jobs = [(bkg, s, toys, seed + k) for k, s in enumerate(TOY_GRID)]
    with get_context("spawn").Pool(workers) as pool:
        rows = pool.map(_toy_point, jobs)

    def crossing(vals):
        return _crossing(TOY_GRID, vals)
    obs = crossing([r["CLs_obs"] for r in rows])
    rng = [crossing([r["CLs_obs_range_95"][0] for r in rows]), crossing([r["CLs_obs_range_95"][1] for r in rows])]
    exp = [crossing([r["CLs_exp"][k] for r in rows]) for k in range(5)]
    return {"toys_per_point": toys, "seed": seed, "grid": TOY_GRID, "rows": rows, "S95_obs": obs,
            "S95_obs_mc_range_95": rng, "S95_exp": exp, "CLb_at_S95_obs": None,
            "note": ("crossings interpolate log CLs linearly between grid points (grid step 1.0 near the limit); the observed range "
                     "propagates exact 95% intervals on CLs+b and CLb; CLb at the limit is reported by the asymptotic "
                     "construction only")}


MACHINERY = {"S": [4.0, 5.0, 5.5], "toys": 4000, "seed": 7, "cl": 0.99}  # seeds 7, 8, 9; added after the toy run (post hoc)


def _counting_limit(n: int, b: float) -> float:
    """Exact CLs upper limit on S for one Poisson bin with a known background: P(N <= n | S + b) / P(N <= n | b) = LEVEL."""
    from scipy import optimize, stats
    return float(optimize.brentq(lambda s: stats.poisson.cdf(n, s + b) / stats.poisson.cdf(n, b) - LEVEL, 0.0, 100.0))


def _bare_model(n: int, b: float):
    import pyhf
    spec = {"channels": [{"name": "SR", "samples": [
                {"name": "unit_signal", "data": [1.0], "modifiers": [{"name": "S", "type": "normfactor", "data": None}]},
                {"name": "background", "data": [b], "modifiers": []}]}],
            "observations": [{"name": "SR", "data": [float(n)]}], "version": "1.0.0",
            "measurements": [{"name": "bare", "config": {"poi": "S", "parameters": [{"name": "S", "bounds": [[0.0, 40.0]], "inits": [1.0]}]}}]}
    ws = pyhf.Workspace(spec)
    model = ws.model()
    return model, ws.data(model)


def toy_diagnosis(n_obs: int, b: float, toy: dict | None) -> dict:
    """Post-hoc diagnosis of the toy construction (added after the 5,000-toy run; not preregistered, and it changes no
    preregistered verdict). SRB is one bin with a handful of events, so the toy limits are compared with the exact
    counting construction (b fixed at the background-only post-fit SRB yield, no systematics), pyhf's ToyCalculator is
    checked against exact Poisson sums on that bare model, and pyhf's asymptotic formulae are run on the same bare
    model: if they fall short of the exact limit there, the asymptotic-vs-toy difference is the approximation at low
    counts, not the workspace or the toys."""
    import numpy as np
    import pyhf
    from scipy import stats
    from core.stats.tail_estimation import clopper_pearson
    quantiles = [stats.norm.cdf(z) for z in (-2, -1, 0, 1, 2)]
    n_q = [int(stats.poisson.ppf(q, b)) for q in quantiles]
    exact = {"model": "one Poisson bin, background fixed at the post-fit SRB yield, no systematics", "n_obs": n_obs,
             "b": b, "S95_obs": _counting_limit(n_obs, b), "S95_exp": [_counting_limit(k, b) for k in n_q],
             "n_at_expected_quantiles": n_q,
             "note": "expected limits are the exact limits at the background-only Poisson quantiles of the count"}
    model, data = _bare_model(n_obs, b)
    a_obs, a_exp = pyhf.infer.intervals.upper_limits.upper_limit(data, model, scan=None, level=LEVEL, rtol=1e-6)
    bare_asym = {"S95_obs": float(a_obs), "S95_exp": [float(e) for e in a_exp],
                 "shortfall_vs_exact_obs": 1 - float(a_obs) / exact["S95_obs"]}
    rows, ok = [], True
    for k, s in enumerate(MACHINERY["S"]):
        np.random.seed(MACHINERY["seed"] + k)             # independent toys per point
        calc = pyhf.infer.calculators.ToyCalculator(data, model, test_stat="qtilde", ntoys=MACHINERY["toys"], track_progress=False)
        sb, bb = calc.distributions(float(s))
        clsb, clb, _ = (float(x) for x in calc.pvalues(calc.teststatistic(float(s)), sb, bb))
        row = {"S": s}
        for name, toy_p, ref in (("CLsb", clsb, stats.poisson.cdf(n_obs, s + b)), ("CLb", clb, stats.poisson.cdf(n_obs, b))):
            k = round(toy_p * MACHINERY["toys"])
            lo, hi = clopper_pearson(k, MACHINERY["toys"], MACHINERY["cl"])
            inside = bool(lo <= ref <= hi)
            ok = ok and inside
            row[name] = {"toys": toy_p, "exact": float(ref), "interval": [lo, hi], "inside": inside}
        rows.append(row)
    out = {"post_hoc": True, "exact_counting": exact, "bare_asymptotic": bare_asym,
           "toy_machinery": {"settings": MACHINERY, "rows": rows, "pass": ok,
                             "rule": "the exact CLs+b and CLb inside the 99% Clopper-Pearson interval of the toy counts at every S"}}
    if toy is not None:
        lo, hi = toy["S95_obs_mc_range_95"]
        out["toy_obs_range_contains_exact_counting"] = bool(lo is not None and hi is not None and lo <= exact["S95_obs"] <= hi)
    return out


def compare(rep: dict) -> dict:
    ref, allow = PREREGISTRATION["reference_values"], PREREGISTRATION["backend_allowance"]
    got = {"S95_obs": rep.get("S95_obs"), "S95_exp_median": (rep.get("S95_exp") or [None] * 5)[2],
           "S95_exp_plus1": (rep.get("S95_exp") or [None] * 5)[3], "S95_exp_minus1": (rep.get("S95_exp") or [None] * 5)[1],
           "CLb": rep.get("CLb_at_S95_obs"), "postfit_SM_yield_SRB": rep.get("postfit_SM_yield_SRB")}
    rows = {}
    for k, r in ref.items():
        v = got.get(k)
        if v is None:
            rows[k] = {"reference": r["value"], "reproduced": None, "status": "not-run"}
            continue
        tol = r["digitization"] + (allow["CLb_absolute"] if k == "CLb" else allow["relative"] * r["value"])
        rows[k] = {"reference": r["value"], "reproduced": v, "tolerance": tol, "status": "pass" if abs(v - r["value"]) <= tol else "fail"}
    if "p0" in rep:
        rows["p0"] = {"reference": "0.50 (truncated)", "reproduced": rep["p0"],
                      "status": "pass" if rep["p0"] >= PREREGISTRATION["p0"]["pass_if_at_least"] else "fail"}
    return rows


def write_artifacts(res: dict, out: Path, argv: list, exit_status: int) -> dict:
    """computational-run and statistical-result artifacts of a run, validated; returns the validator and gate results.
    The data are OBSERVED (public); the reproduction is a tool-chain check, so the result carries 'unvalidated' and
    its coverage is not-checked: the publication gate is expected to say unresolved, never passed."""
    import hashlib
    import platform
    from contracts import CONTRACTS_VERSION
    from contracts.identity import plugin_release
    from contracts.validate import publication_gate, validate_artifact
    version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
    base = {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": version, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {}},
            "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-12", "evidence_ids": ["hepstats:S09"]},
            "outputs": [], "unresolved_inputs": []}
    rhash = hashlib.sha256((out / "results.json").read_bytes()).hexdigest()
    run = dict(base, artifact_id="atlas-susy-2018-31-srb-reproduction-run", artifact_type="computational-run",
               objective="Reproduce the SRB model-independent limits of ATLAS-SUSY-2018-31 from the public likelihood",
               inputs=[], status=["observed"] + (["failed"] if exit_status else []),
               extension={"input_manifest": [{"path": f"HEPData resource 1935437 ({MEMBER})", "sha256": SHA256}],
                          "tools": [{"name": "python", "version": platform.python_version()},
                                    {"name": "pyhf", "version": res["pyhf"]}, {"name": "numpy", "version": __import__("numpy").__version__}],
                          "commands": ["python3 examples/stats-benchmarks/published-likelihood-sbottom/run.py " + " ".join(argv)],
                          "environment": {"platform": platform.platform()},
                          "seeds": {"toys": res.get("toy_based", {}).get("values", {}).get("seed")},
                          "tolerances": PREREGISTRATION["backend_allowance"], "exit_status": exit_status,
                          "output_hashes": {"results.json": rhash}})
    a = res["asymptotic"]["values"]
    stat = dict(base, artifact_id="atlas-susy-2018-31-srb-model-independent-limit", artifact_type="statistical-result",
                objective="SRB model-independent 95% CLs upper limit on the signal count, reproduced from the public likelihood",
                inputs=[{"ref": "artifacts/computational_run.json", "artifact_type": "computational-run", "status": run["status"]}],
                status=sorted(set(run["status"]) | {"unvalidated"}), required_capabilities=["stats:result-semantics"],
                extension={"paradigm": "frequentist",
                           "likelihood": {"form": "HistFactory (pyhf JSON), RegionB without validation channels, unit signal in SR_cuts",
                                          "backend": "pyhf", "backend_version": res["pyhf"],
                                          "model_ref": f"HEPData resource 1935437:{MEMBER}", "model_sha256": SHA256},
                           "parameters_of_interest": ["S (signal events in SRB)"], "nuisances": ["the workspace's 59 parameters"],
                           "test_statistic": "q-tilde", "construction": "asymptotic",
                           "coverage": {"check": "not-checked", "method": "not studied; CLs over-covers by design"},
                           "expected": {"median": a["S95_exp"][2], "band_1sigma": [a["S95_exp"][1], a["S95_exp"][3]],
                                        "band_2sigma": [a["S95_exp"][0], a["S95_exp"][4]], "method": "asimov"},
                           "fit_status": "converged",
                           "results": {"S95_observed": a["S95_obs"], "CLb_at_S95_observed": a["CLb_at_S95_obs"], "p0": a["p0"],
                                       "cl": 0.95, "comparison_ref": "results.json#asymptotic.comparison"}})
    (out / "artifacts").mkdir(exist_ok=True)
    report = {}
    for name, doc in (("computational_run", run), ("statistical_result", stat)):
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
        rep = validate_artifact(doc)
        report[name] = {"ok": rep.ok, "findings": [f.as_dict() for f in rep.findings]}
    report["publication_gate"] = publication_gate(stat)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pallet")
    src.add_argument("--download")
    ap.add_argument("--toys", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--workers", type=int, default=7, help="processes for the toy grid points")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "output"))
    a = ap.parse_args(argv)
    try:
        import pyhf  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "rejected", "error": "pyhf is not installed (pip install 'pyhf>=0.7.6,<0.8')"}))
        return 2
    try:
        if a.pallet:
            path = Path(a.pallet)
        else:
            path = Path(a.download) / "ins1748602-pallet.tgz"
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                import subprocess
                if shutil.which("curl"):     # hepdata.net refuses Python's urllib (403); curl is accepted
                    subprocess.run(["curl", "-sSL", "--fail", "--max-time", "300", "-o", str(path), URL], check=True, timeout=330)
                else:
                    with urllib.request.urlopen(URL, timeout=120) as r:  # noqa: S310 (fixed https URL, checksum verified)
                        path.write_bytes(r.read())
        bkg = load_pallet(path)
    except (OSError, ValueError, __import__("subprocess").SubprocessError) as exc:
        print(json.dumps({"status": "not-run", "reason": str(exc)}))
        return 4
    model, data, poi = build(bkg)
    primary = {**asymptotic(model, data), **background_only(model, data, poi)}
    neg_model, neg_data, _ = build(bkg, keep_cr=False)
    negative = {**asymptotic(neg_model, neg_data), **background_only(neg_model, neg_data, poi)}
    toys = toy_based(bkg, a.toys, a.seed, a.workers) if a.toys else None
    res = {"label": "OBSERVED public likelihood (ATLAS-SUSY-2018-31, HEPData ins1748602 v3); tool-chain validation",
           "pallet_sha256": SHA256, "member": MEMBER, "pyhf": __import__("pyhf").__version__,
           "preregistration": PREREGISTRATION,
           "asymptotic": {"values": primary, "comparison": compare(primary)},
           "negative_control_without_CR": {"values": negative, "comparison": compare(negative)}}
    if toys:
        res["toy_based"] = {"values": toys, "comparison": compare({**toys, "postfit_SM_yield_SRB": primary["postfit_SM_yield_SRB"]})}
    res["verdict"] = {
        "asymptotic_reproduces": all(r["status"] == "pass" for r in res["asymptotic"]["comparison"].values()),
        "negative_control_fails": any(r["status"] == "fail" for r in res["negative_control_without_CR"]["comparison"].values()),
        "toy_based_reproduces": (all(r["status"] == "pass" for r in res["toy_based"]["comparison"].values()) if toys else None)}
    n_obs = int(round(float(data[model.config.channel_slices["SR_cuts"]][0])))
    diag = toy_diagnosis(n_obs, primary["postfit_SM_yield_SRB"], toys)
    explained = (diag["toy_machinery"]["pass"] and diag["bare_asymptotic"]["S95_obs"] < diag["exact_counting"]["S95_obs"]
                 and (toys is None or diag["toy_obs_range_contains_exact_counting"]))
    diag["conclusion"] = (
        ("The toy construction is correct: pyhf's toys match the exact Poisson sums on the bare one-bin model"
         + (", and the full-model toy limit agrees with the exact counting limit" if toys else "")
         + f". The asymptotic formulae understate the exact limit by {100 * diag['bare_asymptotic']['shortfall_vs_exact_obs']:.0f}% "
         f"at n = {n_obs} on the same bare model, so the difference between the two constructions is the asymptotic "
         "approximation at low counts. The published values agree with the asymptotic construction; that the paper used "
         "the asymptotic formulae is an inference, as it does not state its construction.")
        if explained else "Not explained: a diagnosis check failed; the toy-vs-paper difference is open.")
    res["toy_diagnosis"] = diag
    res["verdict"]["toy_difference_explained_post_hoc"] = explained
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["verdict"], indent=1))
    v = res["verdict"]
    code = 0 if v["asymptotic_reproduces"] and v["negative_control_fails"] else 1
    validation = write_artifacts(res, out, list(argv if argv is not None else sys.argv[1:]), code)
    (out / "artifact_validation.json").write_text(json.dumps(validation, indent=1) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
