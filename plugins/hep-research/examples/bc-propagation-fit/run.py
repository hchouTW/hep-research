#!/usr/bin/env python3
"""End-to-end propagation-parameter fit: SYNTHETIC B/C points fitted on a (D0, L) grid of theory:cr-secondary-ratio
predictions with covariance_fit.py's tabulated-grid model.

SYNTHETIC. The data are generated here from the profile's own prediction at an ILLUSTRATIVE truth point; the profile's
cross sections and transport values are ILLUSTRATIVE placeholders. Nothing here is a statement about the Galaxy or
about any measurement.

Chain:
1. Grid: D0 from 1e28 to 1e29 cm^2/s and L from 1 to 10 kpc, 21 nodes each, equal log spacing (0.05 dex) on both
   axes. One prediction artifact per node and per cross-section set (ILLUSTRATIVE sets A and B), written by the
   profile's code (profiles/theory/cr-secondary-ratio/scripts/make_artifacts.py prediction(), which calls
   predict.bin_averaged at the node), relabelled for the grid fit: representation "grid", parameter_point keys D0 and
   L (the names the theory-spec's degenerate direction "D0/L" uses; units kept in D0_unit and L_unit), the derived
   D0/L key dropped (it varies along the grid and is not a condition of the data), one theory-spec per set (a model
   set needs each alternative to carry its own assumptions).
2. Binning and level: the synthetic data use the prediction's own variable (kinetic energy per nucleon, GeV/n), its
   12 bins (equal in log from 1 to 1000 GeV/n), its bin semantics (ratio averaged in ln(E/n), crsr:bin_average) and
   its level crsr:local-interstellar. Real data would be at the top of the instrument in rigidity bins: they would
   need solar modulation and a variable change, which the prediction does not allow and this example does not do.
   Two negative variants show the gate refusing a rigidity-binned and an unfolded-level measurement.
3. Data: truth D0 = 3e28 cm^2/s, L = 4 kpc (the profile's benchmark point; D0/L = 7.5e27 cm^2 s^-1 kpc^-1), set A.
   Covariance (one dataset-record component with correlation "covariance"): 3% uncorrelated statistical plus a 2%
   systematic with correlation exp(-|ln E_i - ln E_j| / 1.5); pseudo-data drawn once with numpy default_rng(seed)
   through the Cholesky factor.
4. Fits (covariance_fit.py fit, CLI): Asimov (data = truth) with set A; pseudo-data with sets A and B as a model set
   (min-max envelope, a hep-theory prescription); toys (in process, grid_fit) with set A.
5. Negative variants: no measurement (ungated), rigidity bins, unfolded level, a component with unknown correlation.

Pre-declared criteria (fixed before the first run):
- every node passes the comparison gate;
- Asimov: one degenerate direction, its eigenvector within 0.05 (1 - |cos|) of (1, 1)/sqrt(2) in (ln D0, ln L) and
  matched to the theory spec's "D0/L"; D0 and L reported unconstrained; ln(D0/L) within 0.25 sigma_ln of the truth;
- pseudo-data, set A: |ln(D0/L) - truth| < 3 sigma_ln, chi2 p-value > 0.001, the same degenerate direction matched;
- toys (set A): mean pull of ln(D0/L) within 4 standard errors of 0, standard deviation within 0.2 of 1;
- model set: cross_section_uncertainty mode "model-set", an envelope over D0/L that contains both sets' values;
- negatives: ungated exit 1; rigidity bins exit 1; unfolded level exit 1; unknown correlation exit 3, "incomplete".

Usage (from the plugin root): python3 examples/bc-propagation-fit/run.py [--toys 100] [--seed 20261015] [--out DIR]
Default output: examples/bc-propagation-fit/output/ (the grid/ subfolder of node artifacts is regenerated, not
committed). Exit 0 when every criterion passes, 1 otherwise, 3 when numpy or scipy is missing.
Validating the artifacts by hand: the level crsr:local-interstellar is a profile term; bind theory:cr-secondary-ratio
in a project config and pass --profiles-from to contracts/validate.py.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
PROFILE_DIR = PLUGIN / "profiles" / "theory" / "cr-secondary-ratio"
FIT_SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"
DEFAULT_OUT = Path(__file__).resolve().parent / "output"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PROFILE_DIR / "scripts"))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-statistics" / "scripts"))

D0_NODES_DEX = (28.0, 29.0)
L_NODES_DEX = (0.0, 1.0)
N_NODES = 21
TRUTH = {"D0": 3e28, "L": 4.0}
EDGES_DEX = (0.0, 3.0, 12)
STAT, SYST, CORR_LEN = 0.03, 0.02, 1.5
XS_SETS = {"A": "models/xs-illustrative-A.json", "B": "models/xs-illustrative-B.json"}
UNITS = {"D0_unit": "cm^2 s^-1", "L_unit": "kpc"}
FIXED_KEYS = ("h_kpc", "n_H_cm3", "delta", "R0_GV")
PRESCRIPTION = {"kind": "min-max", "owner": "hep-theory",
                "justification": "two ILLUSTRATIVE cross-section sets of the profile; their spread is a model "
                                 "alternative, not a Gaussian uncertainty"}


def _r(x: float) -> float:
    """Round to 12 significant digits for stable output across platforms."""
    return float(f"{x:.12g}")


def edges() -> list[float]:
    import numpy as np
    lo, hi, n = EDGES_DEX
    return [_r(v) for v in np.logspace(lo, hi, n + 1)]


def axis(dex: tuple[float, float]) -> list[float]:
    import numpy as np
    return [_r(v) for v in np.logspace(dex[0], dex[1], N_NODES)]


def profile_inputs() -> tuple[dict, dict]:
    import predict
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    conv = predict.load_json(PROFILE_DIR / "conventions.json")
    return dict(cfg, energy_bin_edges_gev_per_n=edges(), alternative_cross_section_sets=[]), conv


def node(cfg: dict, conv: dict, xs: str, d0: float, length: float) -> dict:
    """One grid-node prediction from the profile's code, relabelled for the grid fit (see the module doc)."""
    import make_artifacts
    doc = make_artifacts.prediction(dict(cfg, cross_section_set=XS_SETS[xs]), conv, {"D0_cm2_s": d0, "L_kpc": length})
    ext = doc["extension"]
    pp = ext["parameter_point"]
    ext["parameter_point"] = {"D0": pp["D0_cm2_s"], "L": pp["L_kpc"], **UNITS, **{k: pp[k] for k in FIXED_KEYS},
                              "cross_section_set": pp["cross_section_set"]}
    ext["representation"] = "grid"
    ext["theory_spec_ref"] = f"theory-spec-xs-{xs}.json"
    doc["artifact_id"] = f"bcfit-node-xs{xs}-D0_{d0:.6g}-L_{length:.6g}"
    doc["inputs"][0].update({"ref": ext["theory_spec_ref"], "artifact_id": f"crsr-theory-spec-thin-disc-1d-xs{xs}"})
    doc["objective"] = ("SYNTHETIC grid node: B/C in the 1D thin-disc model of theory:cr-secondary-ratio at one (D0, L) "
                        "point, ILLUSTRATIVE cross-section set " + xs)
    return doc


def theory_spec(cfg: dict, conv: dict, xs: str) -> dict:
    import make_artifacts
    spec = make_artifacts.theory_spec(dict(cfg, cross_section_set=XS_SETS[xs]), conv)
    spec["artifact_id"] += f"-xs{xs}"
    return spec


def covariance(y: list[float]) -> list[list[float]]:
    import numpy as np
    e = np.array(edges())
    ln_c = np.log(np.sqrt(e[:-1] * e[1:]))
    y = np.asarray(y)
    rho = np.exp(-np.abs(ln_c[:, None] - ln_c[None, :]) / CORR_LEN)
    cov = np.diag((STAT * y) ** 2) + np.outer(SYST * y, SYST * y) * rho
    return cov.tolist()


def measurement(template: dict, values: list[float], name: str, components: list[dict]) -> dict:
    """A SYNTHETIC dataset-record with the prediction's observable (variable, bins, level, conventions)."""
    doc = copy.deepcopy(template)
    doc["artifact_type"] = "dataset-record"
    doc["artifact_id"] = f"bcfit-synthetic-data-{name}"
    doc["objective"] = "SYNTHETIC B/C points generated from the profile's prediction at an ILLUSTRATIVE truth point"
    doc["provenance"]["producer_skill"] = "hep-statistics"
    doc["inputs"] = []
    doc["extension"] = {"dataset_id": f"synthetic:bcfit-{name}", "source_evidence_ids": [],
                        "observable": copy.deepcopy(template["extension"]["observable"]),
                        "data": {"edges": edges(), "values": [_r(v) for v in values], "unit": "1",
                                 "uncertainties": components},
                        "covariance": {"status": "present", "ref": "covariance.json"}, "status": "synthetic"}
    return doc


COV_COMPONENT = [{"name": "total (3% statistical uncorrelated + 2% systematic, correlation length 1.5 in ln E)",
                  "kind": "systematic", "correlation": "covariance", "covariance_ref": "covariance.json"}]


def write(path: Path, doc) -> str:
    text = json.dumps(doc, indent=1) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def fit_cli(input_path: Path) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(FIT_SCRIPT), "fit", "--input", str(input_path)], capture_output=True,
                          text=True, timeout=600)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, {"stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}


def fit_input(meas_ref, nodes: list[str], xs_sets: list[str], node_example: dict) -> dict:
    pp = node_example["extension"]["parameter_point"]
    cond = {**UNITS, **{k: pp[k] for k in FIXED_KEYS}}
    doc = {"model": "tabulated-grid", "measurement": meas_ref, "predictions": nodes,
           "grid": {"parameters": [{"name": "D0", "scale": "log"}, {"name": "L", "scale": "log"}]},
           "theory_spec": "theory-spec-xs-A.json", "combinations": ["D0/L"],
           "gate_plan": {"measurement_conditions": cond}}
    if len(xs_sets) > 1:
        doc["model_set"] = {"alternative_key": "cross_section_set", "prescription": PRESCRIPTION}
    else:
        cond["cross_section_set"] = XS_SETS[xs_sets[0]]
    return doc


def summarize(fit: dict) -> dict:
    comb = next(c for c in fit["combinations"] if c["name"] == "D0/L")
    deg = fit["degenerate_directions"]
    out = {"alternative": fit.get("alternative"), "chi2": _r(fit["chi2"]), "dof": fit["dof"],
           "D0_over_L": _r(comb["value"]), "ln_D0_over_L": _r(comb["ln_value"]), "sigma_ln_D0_over_L": _r(comb["sigma_ln"]),
           "D0_over_L_constrained": comb["constrained"],
           "parameters": {p["name"]: {"best_fit": _r(p["best_fit"]), "constrained": p["constrained"]}
                          for p in fit["parameters"]},
           "degenerate_directions": [{"eigenvector": {k: _r(v) for k, v in d["eigenvector"].items()},
                                      "matches_theory_spec": d["matches_theory_spec"],
                                      "condition_number_log10": round(math.log10(d["condition_number"]), 1)
                                      if d.get("condition_number") else None} for d in deg]}
    return out


def chi2_p(chi2: float, dof: int) -> float:
    from scipy.stats import chi2 as chi2_dist
    return float(chi2_dist.sf(chi2, dof))


def direction_ok(summary: dict) -> bool:
    d = summary["degenerate_directions"]
    if len(d) != 1:
        return False
    v = d[0]["eigenvector"]
    cos = abs(v["D0"] + v["L"]) / math.sqrt(2.0) / math.hypot(v["D0"], v["L"])
    return 1.0 - cos < 0.05 and d[0]["matches_theory_spec"] == "D0/L"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toys", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    opts = ap.parse_args(argv)
    try:
        import numpy as np
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}"}))
        return 3
    import covariance_fit as cf
    import predict

    out, art, grid_dir = opts.out, opts.out / "artifacts", opts.out / "grid"
    for d in (art, grid_dir):
        d.mkdir(parents=True, exist_ok=True)
    cfg, conv = profile_inputs()

    # 1. grid of predictions, one artifact per node and cross-section set
    d0_axis, l_axis = axis(D0_NODES_DEX), axis(L_NODES_DEX)
    manifest, node_refs = [], {xs: [] for xs in XS_SETS}
    for xs in XS_SETS:
        write(art / f"theory-spec-xs-{xs}.json", theory_spec(cfg, conv, xs))
        for d0 in d0_axis:
            for length in l_axis:
                doc = node(cfg, conv, xs, d0, length)
                name = f"node-xs{xs}-D0_{d0:.6g}-L_{length:.6g}.json"
                digest = write(grid_dir / name, doc)
                node_refs[xs].append(f"../grid/{name}")
                manifest.append({"file": f"grid/{name}", "D0": d0, "L": length, "cross_section_set": XS_SETS[xs],
                                 "sha256": digest})
    example_node = json.loads((grid_dir / Path(node_refs["A"][0]).name).read_text(encoding="utf-8"))
    combined = hashlib.sha256("".join(m["sha256"] for m in manifest).encode()).hexdigest()
    write(art / "grid-manifest.json", {"note": "node artifacts are regenerated by run.py into grid/ (not committed); "
                                               "combined_sha256 is the sha256 of the concatenated per-file sha256 "
                                               "digests in the order of fit-input.json",
                                       "D0_cm2_s": d0_axis, "L_kpc": l_axis, "cross_section_sets": XS_SETS,
                                       "nodes": len(manifest), "combined_sha256": combined})

    # 2-3. synthetic data at the truth point, with its covariance
    truth = predict.bin_averaged(dict(cfg, cross_section_set=XS_SETS["A"]), edges(),
                                 {"D0_cm2_s": TRUTH["D0"], "L_kpc": TRUTH["L"]})
    cov = covariance(truth)
    write(art / "covariance.json", {"label": "SYNTHETIC covariance of the B/C points (3% statistical uncorrelated, 2% "
                                              "systematic with correlation exp(-|d ln E| / 1.5))",
                                    "matrix": [[_r(v) for v in row] for row in cov]})
    chol = np.linalg.cholesky(np.array(json.loads((art / "covariance.json").read_text())["matrix"]))
    rng = np.random.default_rng(opts.seed)
    pseudo = (np.array(truth) + chol @ rng.standard_normal(len(truth))).tolist()
    write(art / "measurement-asimov.json", measurement(example_node, truth, "asimov", COV_COMPONENT))
    write(art / "measurement.json", measurement(example_node, pseudo, "pseudo", COV_COMPONENT))

    # 4. fits through the CLI
    write(art / "fit-input-asimov.json", fit_input("measurement-asimov.json", node_refs["A"], ["A"], example_node))
    write(art / "fit-input.json", fit_input("measurement.json", node_refs["A"] + node_refs["B"], ["A", "B"],
                                            example_node))
    code_a, res_a = fit_cli(art / "fit-input-asimov.json")
    code_p, res_p = fit_cli(art / "fit-input.json")
    if code_a != 0 or code_p != 0:
        write(out / "fit_failure.json", {"asimov": [code_a, res_a], "pseudo": [code_p, res_p]})
        print(json.dumps({"status": "failed", "asimov_exit": code_a, "pseudo_exit": code_p}))
        return 1
    asimov = summarize(res_a["fits"][0])
    fits_p = {f["alternative"]: summarize(f) for f in res_p["fits"]}
    pseudo_a = fits_p[XS_SETS["A"]]
    ln_truth = math.log(TRUTH["D0"] / TRUTH["L"])

    # toys (set A), in process; the same gated input with fresh data each time
    base = json.loads((art / "fit-input-asimov.json").read_text(encoding="utf-8"))
    base["predictions"] = [json.loads((art / r).read_text(encoding="utf-8")) for r in node_refs["A"]]
    pulls = []
    for _ in range(opts.toys):
        data = (np.array(truth) + chol @ rng.standard_normal(len(truth))).tolist()
        doc = dict(base, measurement=measurement(example_node, data, "toy", COV_COMPONENT))
        comb = next(c for c in cf.grid_fit(doc, art)["fits"][0]["combinations"] if c["name"] == "D0/L")
        pulls.append((comb["ln_value"] - ln_truth) / comb["sigma_ln"])
    pulls_arr = np.array(pulls)
    toy = {"n": len(pulls), "seed": opts.seed, "mean_pull": _r(pulls_arr.mean()) if pulls else None,
           "sd_pull": _r(pulls_arr.std(ddof=1)) if len(pulls) > 1 else None,
           "standard_error_of_mean": _r(pulls_arr.std(ddof=1) / math.sqrt(len(pulls))) if len(pulls) > 1 else None}

    # 5. negative variants (each must be refused)
    negatives = []

    def negative(name, doc, expect_code, files=None):
        p = art / f"negative-{name}.json"
        for fname, content in (files or {}).items():
            write(art / fname, content)
        write(p, doc)
        code, res = fit_cli(p)
        negatives.append({"name": name, "exit": code, "expected_exit": expect_code, "refused": code == expect_code,
                          "status": res.get("status"), "error": (res.get("error") or "")[:300],
                          "missing": res.get("missing")})
        for fname in [p.name, *(files or {})]:
            (art / fname).unlink()

    ungated = fit_input(None, node_refs["A"], ["A"], example_node)
    negative("ungated-no-measurement", ungated, 1)
    rig = measurement(example_node, pseudo, "rigidity", COV_COMPONENT)
    rig["extension"]["observable"]["variables"] = [{"name": "rigidity", "unit": "GV",
                                                    "edges": [_r(2 * e) for e in edges()]}]
    rig["extension"]["data"]["edges"] = [_r(2 * e) for e in edges()]
    negative("rigidity-bins", fit_input("m-rig.json", node_refs["A"], ["A"], example_node), 1, {"m-rig.json": rig})
    unf = measurement(example_node, pseudo, "unfolded", COV_COMPONENT)
    unf["extension"]["observable"]["level"] = "unfolded"
    negative("unfolded-level", fit_input("m-unf.json", node_refs["A"], ["A"], example_node), 1, {"m-unf.json": unf})
    unk = measurement(example_node, pseudo, "unknown-corr",
                      [{"name": "systematic of unknown correlation", "kind": "systematic", "correlation": "unknown",
                        "values": [_r(SYST * v) for v in pseudo]}])
    negative("unknown-correlation", fit_input("m-unk.json", node_refs["A"], ["A"], example_node), 3,
             {"m-unk.json": unk})

    env = res_p.get("envelope") or {}
    col = (env.get("columns") or []).index("D0/L") if "D0/L" in (env.get("columns") or []) else None
    envelope = ({"D0_over_L_lower": _r(env["lower"][col]), "D0_over_L_upper": _r(env["upper"][col]),
                 "kind": env.get("kind"), "gaussian": env.get("gaussian"), "prescription": env.get("prescription")}
                if col is not None else None)
    crit = {
        "all_nodes_gated_comparable": res_p["gate"]["comparable"] == res_p["gate"]["predictions_gated"] == 2 * N_NODES ** 2,
        "asimov_one_degenerate_direction_along_1_1_matched_D0_over_L": direction_ok(asimov),
        "asimov_D0_and_L_unconstrained": not any(p["constrained"] for p in asimov["parameters"].values()),
        "asimov_ln_D0_over_L_within_0.25_sigma": abs(asimov["ln_D0_over_L"] - ln_truth) < 0.25 * asimov["sigma_ln_D0_over_L"],
        "pseudo_ln_D0_over_L_within_3_sigma": abs(pseudo_a["ln_D0_over_L"] - ln_truth) < 3 * pseudo_a["sigma_ln_D0_over_L"],
        "pseudo_chi2_p_above_0.001": chi2_p(pseudo_a["chi2"], pseudo_a["dof"]) > 1e-3,
        "pseudo_degenerate_direction_matched": direction_ok(pseudo_a),
        "toys_mean_pull_within_4_standard_errors": bool(pulls) and abs(toy["mean_pull"]) < 4 * toy["standard_error_of_mean"],
        "toys_pull_sd_within_0.2_of_1": bool(pulls) and abs(toy["sd_pull"] - 1.0) < 0.2,
        "model_set_mode_and_envelope": (res_p["cross_section_uncertainty"]["mode"] == "model-set" and envelope is not None
                                        and all(envelope["D0_over_L_lower"] <= f["D0_over_L"] <= envelope["D0_over_L_upper"]
                                                for f in fits_p.values())),
        "negatives_refused_with_expected_exit": all(n["refused"] for n in negatives),
        "unknown_correlation_incomplete": any(n["name"] == "unknown-correlation" and n["status"] == "incomplete"
                                              for n in negatives),
    }
    crit = {k: bool(v) for k, v in crit.items()}
    results = {
        "label": "SYNTHETIC end-to-end B/C grid fit with theory:cr-secondary-ratio (ILLUSTRATIVE inputs)",
        "profile": {"id": "theory:cr-secondary-ratio", "version": json.loads((PROFILE_DIR / "profile.json").read_text())["version"]},
        "grid": {"D0_cm2_s": [d0_axis[0], d0_axis[-1]], "L_kpc": [l_axis[0], l_axis[-1]], "nodes_per_axis": N_NODES,
                 "log_step_dex": _r((D0_NODES_DEX[1] - D0_NODES_DEX[0]) / (N_NODES - 1)),
                 "cross_section_sets": list(XS_SETS.values()), "nodes_total": len(manifest),
                 "combined_sha256": combined},
        "data": {"edges_gev_per_n": edges(), "truth": dict(TRUTH, D0_over_L=TRUTH["D0"] / TRUTH["L"],
                                                           cross_section_set=XS_SETS["A"]),
                 "truth_values": [_r(v) for v in truth], "pseudo_values": [_r(v) for v in pseudo], "seed": opts.seed,
                 "level": example_node["extension"]["observable"]["level"],
                 "covariance": "3% uncorrelated + 2% correlated (exp(-|d ln E| / 1.5))"},
        "asimov": asimov,
        "pseudo_data": {"fits": fits_p, "chi2_p_set_A": _r(chi2_p(pseudo_a["chi2"], pseudo_a["dof"])),
                        "pull_ln_D0_over_L_set_A": _r((pseudo_a["ln_D0_over_L"] - ln_truth) / pseudo_a["sigma_ln_D0_over_L"]),
                        "cross_section_uncertainty": res_p["cross_section_uncertainty"], "envelope": envelope,
                        "theory_spec_degenerate_directions": res_p["theory_spec_degenerate_directions"],
                        "warnings": res_p["warnings"], "carried_statuses": res_p["carried_statuses"]},
        "toys": toy,
        "negative_variants": negatives,
        "criteria": crit,
        "pass": all(crit.values()),
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": __import__("scipy").__version__},
    }
    write(out / "results.json", results)
    (out / "report.md").write_text(report(results), encoding="utf-8")
    print(json.dumps({"status": "ok" if results["pass"] else "criteria failed", "criteria": crit}, indent=1))
    return 0 if results["pass"] else 1


def report(r: dict) -> str:
    a, p, t = r["asimov"], r["pseudo_data"], r["toys"]
    fa = p["fits"][r["grid"]["cross_section_sets"][0]]
    env = p["envelope"] or {}
    lines = [
        "# B/C propagation-parameter grid fit (SYNTHETIC)", "",
        "SYNTHETIC data from theory:cr-secondary-ratio at an ILLUSTRATIVE truth point; ILLUSTRATIVE cross sections. "
        "No statement about the Galaxy or any measurement.", "",
        f"Grid: D0 {r['grid']['D0_cm2_s'][0]:.3g}-{r['grid']['D0_cm2_s'][1]:.3g} cm^2/s x L {r['grid']['L_kpc'][0]:.3g}-"
        f"{r['grid']['L_kpc'][1]:.3g} kpc, {r['grid']['nodes_per_axis']} nodes per axis, {r['grid']['log_step_dex']} dex "
        f"steps on both axes, two cross-section sets ({r['grid']['nodes_total']} gated prediction artifacts).", "",
        f"Truth D0/L = {r['data']['truth']['D0_over_L']:.4g} cm^2 s^-1 kpc^-1 (D0 = {r['data']['truth']['D0']:.3g}, "
        f"L = {r['data']['truth']['L']:.3g}); {len(r['data']['edges_gev_per_n']) - 1} E/n bins at level "
        f"{r['data']['level']}.", "",
        "| Fit | D0/L | sigma(ln D0/L) | chi2 / dof | degenerate direction (ln D0, ln L) | matches |",
        "|---|---|---|---|---|---|",
    ]
    for name, f in (("Asimov, set A", a), ("pseudo-data, set A", fa),
                    *((f"pseudo-data, {Path(k).stem}", v) for k, v in p["fits"].items() if v is not fa)):
        d = f["degenerate_directions"][0] if f["degenerate_directions"] else {"eigenvector": {}, "matches_theory_spec": None}
        vec = ", ".join(f"{v:.3f}" for v in d["eigenvector"].values())
        lines.append(f"| {name} | {f['D0_over_L']:.4g} | {f['sigma_ln_D0_over_L']:.4f} | {f['chi2']:.2f} / {f['dof']} | "
                     f"({vec}) | {d['matches_theory_spec']} |")
    lines += ["",
              f"D0 and L separately: unconstrained (best-fit positions along the flat direction are not measurements).",
              f"Pull of ln(D0/L), pseudo-data set A: {p['pull_ln_D0_over_L_set_A']:.2f}; chi2 p-value {p['chi2_p_set_A']:.3g}.",
              f"Cross-section model set (min-max, never Gaussian): D0/L in [{env.get('D0_over_L_lower', float('nan')):.4g}, "
              f"{env.get('D0_over_L_upper', float('nan')):.4g}].",
              f"Toys (set A, {t['n']}, seed {t['seed']}): mean pull {t['mean_pull']}, sd {t['sd_pull']}.", "",
              "Negative variants (each refused):", ""]
    lines += [f"- {n['name']}: exit {n['exit']} (expected {n['expected_exit']})" for n in r["negative_variants"]]
    lines += ["", "Criteria: " + ("all pass" if r["pass"] else "FAILED: " + ", ".join(k for k, v in r["criteria"].items() if not v)), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
