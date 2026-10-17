#!/usr/bin/env python3
"""Example E-1: a SYNTHETIC boron-to-carbon measurement with carbon fragmenting into boron above the top layer.

SYNTHETIC and ILLUSTRATIVE. The material, the cross sections, the fluxes and the detector response are invented
round numbers; nothing describes an experiment, and no profile is loaded.

Chain (each step runs the plugin's tool, as a user would):
1. hep-measurement M4: the spec declares the boron background from carbon feed-down as a coupled background
   (`coupled_backgrounds`, treatment joint-fit); `review_measurement_spec.py` reviews it. A copy that subtracts the
   feed-down as a fixed amount is flagged `coupled.fixed_subtraction`.
2. hep-detector D4 `survival_feeddown.py`: survival probabilities of boron and carbon through 20 g/cm2 of
   carbon-like material above the top layer (invented), with the cross sections of
   skills/hep-detector/assets/survival-xs.example.json, and the carbon-to-boron fragmentation fraction.
3. hep-detector D2 `species_response.py`: blocks B->B = R P_B, C->C = R P_C and C->B = R (1 - P_C) f (R: a fixed
   rigidity response; straight-ahead: a fragment keeps the parent's bin), assembled and folded.
4. Forward folding: Poisson toys around the folded truth; a joint maximum-likelihood fit of the boron and carbon
   spectra through the four blocks. Over 400 toys the pulls of B/C per bin have |mean| < 0.2 and width 0.85-1.15.
5. Control: a fixed subtraction of the feed-down computed from a carbon model 15% below the truth (as an external,
   older carbon flux would be) biases B/C in every bin, with a combined significance above 5 sigma; the coupled fit
   does not.
The advisory analysis check (counting-chain/v1) is not run here: until forward folding and the new catalog entries
enter that suite it reports unsupported, and the example does not depend on it.

Usage (from the plugin root): python3 examples/bc-fragmentation/run.py [--toys 400] [--seed 20261017] [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
TOOLS = {
    "review": PLUGIN / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py",
    "survival": PLUGIN / "skills" / "hep-detector" / "scripts" / "survival_feeddown.py",
    "species": PLUGIN / "skills" / "hep-detector" / "scripts" / "species_response.py",
}
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets"
SPEC = PLUGIN / "skills" / "hep-measurement" / "assets" / "worked-spec.cosmic-ray.synthetic.json"
EDGES = [2.0, 4.0, 8.0, 16.0, 32.0]  # rigidity bins, GV
N_B = np.array([4000.0, 1500.0, 500.0, 160.0])  # arriving boron above the material per bin (invented)
N_C = np.array([12000.0, 4500.0, 1500.0, 480.0])  # arriving carbon (invented)
CARBON_MODEL_SCALE = 0.85  # the control's external carbon flux, 15% low
CRITERIA = {"pull_mean_abs_max": 0.2, "pull_width": [0.85, 1.15], "control_bias_combined_sigmas_min": 5.0}
LAYERS = {"layers": [{"name": "above the top layer", "grammage_g_cm2": 20.0,
                      "composition": [{"target": "C", "A": 12.011, "mass_fraction": 1.0}]}]}
LABEL = "SYNTHETIC and ILLUSTRATIVE: invented material, cross sections, fluxes and response; describes no experiment"


def tool(name: str, *args) -> dict:
    p = subprocess.run([sys.executable, "-B", str(TOOLS[name]), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=PLUGIN)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise SystemExit(f"{TOOLS[name].name}: no JSON (exit {p.returncode}): {p.stderr[-800:]}")
    out["_exit"] = p.returncode
    return out


def rnd(x, digits=6):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, digits) for v in x]
    return float(f"{float(x):.{digits}g}")


def response() -> np.ndarray:
    """A fixed rigidity response: 90% stay, 5% to each neighbour (column sums <= 1)."""
    n = len(EDGES) - 1
    r = np.zeros((n, n))
    for j in range(n):
        r[j, j] = 0.90
        if j > 0:
            r[j - 1, j] = 0.05
        if j < n - 1:
            r[j + 1, j] = 0.05
    return r


def fit(M: np.ndarray, n: np.ndarray, start: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Poisson maximum likelihood of mu = M theta (theta > 0), Newton steps in log theta; Fisher covariance."""
    theta = np.log(start)
    for _ in range(100):
        t = np.exp(theta)
        mu = M @ t
        grad = (M.T @ (n / mu - 1.0)) * t
        J = M * t
        H = J.T @ (J * (n / mu ** 2)[:, None])
        step = np.linalg.solve(H, grad)
        theta += step
        if np.max(np.abs(step)) < 1e-12:
            break
    t = np.exp(theta)
    return t, np.linalg.inv(M.T @ (M / (M @ t)[:, None]))


def ratio_and_sigma(theta, cov, nb):
    b, c = theta[:nb], theta[nb:]
    r = b / c
    var = np.array([(cov[j, j] / c[j] ** 2 + b[j] ** 2 * cov[nb + j, nb + j] / c[j] ** 4
                     - 2 * b[j] * cov[j, nb + j] / c[j] ** 3) for j in range(nb)])
    return r, np.sqrt(var)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toys", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    out = a.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    tmp = tempfile.TemporaryDirectory()
    work = Path(tmp.name)
    checks: dict = {}

    # 1. M4: the coupled background in the spec, and the fixed-subtraction copy
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    ext = spec["extension"]
    spec["artifact_id"] = "bc-fragmentation-spec"
    spec["objective"] = "SYNTHETIC: boron with carbon feed-down from fragmentation above the top layer (example E-1)"
    ext["species_or_process"] = "boron, carbon (synthetic)"
    ext["backgrounds"] = ext["backgrounds"] + [{
        "name": "carbon feed-down into boron", "estimator": "joint forward-folded fit of boron and carbon",
        "constraint": "carbon measured in the same data", "closure": "toys with known feed-down (this example)"}]
    ext["coupled_backgrounds"] = [{"background": "carbon feed-down into boron", "species": "carbon (same data)",
                                   "treatment": "joint-fit", "source": "SYNTHETIC: survival_feeddown.py on invented "
                                                                       "cross sections"}]
    fixed = copy.deepcopy(spec)
    fixed["artifact_id"] = "bc-fragmentation-spec-fixed-subtraction"
    fixed["extension"]["coupled_backgrounds"][0]["treatment"] = "fixed-subtraction"
    for doc, name in ((spec, "spec_joint_fit.json"), (fixed, "spec_fixed_subtraction.json")):
        (out / "artifacts" / name).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    rev = {k: tool("review", out / "artifacts" / k) for k in ("spec_joint_fit.json", "spec_fixed_subtraction.json")}
    warn = {k: sorted({w["code"] for w in v["warnings"]} & {"coupled.fixed_subtraction"}) for k, v in rev.items()}
    checks["m4_review"] = {k: {"verdict": v["verdict"], "coupled_warnings": warn[k]} for k, v in rev.items()}

    # 2. D4: survival and feed-down
    species = work / "species.json"
    species.write_text(json.dumps({"species": [{"name": "B"}, {"name": "C"}]}), encoding="utf-8")
    layers = work / "layers.json"
    layers.write_text(json.dumps(LAYERS), encoding="utf-8")
    sf = tool("survival", "compute", "--layers", layers, "--species", species,
              "--xs", ASSETS / "survival-xs.example.json", "--status", "synthetic")
    assert sf["status"] == "ok", sf
    P = {r["species"]: r["survival_probability"] for r in sf["species"]}
    fd = sf["feeddown"][0]
    p_b, p_c, frac = P["B"], P["C"], fd["fraction"]
    checks["d4"] = {"P_B": rnd(p_b), "P_C": rnd(p_c), "fraction_C_to_B": frac,
                    "recipe_effects": sorted({e for s in sf["recipe_steps"] for e in s["effect_keys"]})}

    # 3. D2: blocks, assemble, fold
    R = response()
    blocks = {("B", "B"): R * p_b, ("C", "C"): R * p_c, ("C", "B"): R * (1 - p_c) * frac}
    manifest = {"manifest_version": "0.1.0", "species": ["B", "C"], "variable": {"name": "rigidity", "unit": "GV"},
                "inefficiency_location": "outside",
                "blocks": [{"true": t, "reco": r, "source": "SYNTHETIC: response x survival_feeddown.py",
                            "effects": ["fragmentation_feeddown"] if t != r else ["migration", "survival"],
                            "response": {"matrix": m.tolist(), "truth_edges": EDGES, "reco_edges": EDGES}}
                           for (t, r), m in blocks.items()]}
    (out / "artifacts" / "species_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    asm = tool("species", "assemble", "--manifest", out / "artifacts" / "species_manifest.json")
    truth = work / "truth.json"
    truth.write_text(json.dumps({"truth": {"B": N_B.tolist(), "C": N_C.tolist()}}), encoding="utf-8")
    fo = tool("species", "fold", "--manifest", out / "artifacts" / "species_manifest.json", "--truth", truth)
    assert asm["status"] == "ok" and fo["status"] == "ok", (asm, fo)
    nb = len(N_B)
    M = np.zeros((2 * nb, 2 * nb))
    M[:nb, :nb], M[nb:, nb:], M[:nb, nb:] = blocks[("B", "B")], blocks[("C", "C")], blocks[("C", "B")]
    theta_true = np.concatenate([N_B, N_C])
    mu = M @ theta_true
    fold_gap = float(np.max(np.abs(np.array(fo["reco"]["B"] + fo["reco"]["C"]) - mu)) / float(np.max(mu)))
    checks["d2_fold_vs_matrix_rel"] = rnd(fold_gap, 3)
    # a planted double count: the chain also subtracts the feed-down the block models
    chain = work / "chain.json"
    chain.write_text(json.dumps({"recipe_steps": sf["recipe_steps"]}), encoding="utf-8")
    dc = tool("species", "check", "--manifest", out / "artifacts" / "species_manifest.json", "--chain", chain)
    checks["d2_double_count_check"] = {"exit": dc["_exit"], "effects": sorted({d["effect"] for d in dc["double_counted"]})}

    # 4. toys: joint fit pulls of B/C; 5. fixed-subtraction control
    rng = np.random.default_rng(a.seed)
    r_true = N_B / N_C
    pulls, ctrl = [], []
    RBB_inv = np.linalg.inv(blocks[("B", "B")])
    for _ in range(a.toys):
        n = rng.poisson(mu).astype(float)
        th, cov = fit(M, n, theta_true)
        r, s = ratio_and_sigma(th, cov, nb)
        pulls.append((r - r_true) / s)
        # control: carbon from the same toy's carbon fit, but the feed-down from a fixed external carbon model
        feed_fixed = blocks[("C", "B")] @ (CARBON_MODEL_SCALE * N_C)
        b_fixed = RBB_inv @ (n[:nb] - feed_fixed)
        ctrl.append((b_fixed / th[nb:]) / r_true - 1.0)
    pulls, ctrl = np.array(pulls), np.array(ctrl)
    mean, width = pulls.mean(axis=0), pulls.std(axis=0, ddof=1)
    c_mean, c_err = ctrl.mean(axis=0), ctrl.std(axis=0, ddof=1) / np.sqrt(len(ctrl))
    w = 1.0 / c_err ** 2
    z_comb = float(abs(np.sum(w * c_mean)) / np.sqrt(np.sum(w)))  # the bins' toys share nothing across bins

    passed = {
        "m4_joint_fit_spec_not_flagged": warn["spec_joint_fit.json"] == [],
        "m4_fixed_subtraction_flagged": warn["spec_fixed_subtraction.json"] == ["coupled.fixed_subtraction"],
        "d2_fold_equals_block_matrix": fold_gap < 1e-12,
        "d2_planted_double_count_caught": dc["_exit"] == 1,
        "pull_mean_abs_below_0p2": bool(np.all(np.abs(mean) < CRITERIA["pull_mean_abs_max"])),
        "pull_width_0p85_to_1p15": bool(np.all((width > CRITERIA["pull_width"][0]) & (width < CRITERIA["pull_width"][1]))),
        "fixed_subtraction_bias_measurable": bool(np.all(np.sign(c_mean) == np.sign(c_mean[0]))
                                                  and z_comb > CRITERIA["control_bias_combined_sigmas_min"]),
    }
    results = {"label": LABEL, "seed": a.seed, "toys": a.toys, "edges_gv": EDGES, "checks": checks,
               "bc_true": rnd(r_true), "pull_mean": rnd(mean, 4), "pull_width": rnd(width, 4),
               "fixed_subtraction_relative_bias": rnd(c_mean, 4), "fixed_subtraction_bias_error": rnd(c_err, 3),
               "fixed_subtraction_bias_combined_sigmas": rnd(z_comb, 3),
               "criteria": CRITERIA, "pass": passed,
               "advisory_analysis_check": "not run: counting-chain/v1 reports unsupported until forward folding and the "
                                          "new catalog effects enter the suite"}
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    lines = [f"# B/C with fragmentation feed-down (E-1)\n\n{LABEL}.\n", "| Check | Result |", "|---|---|"]
    lines += [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in passed.items()]
    lines += ["", f"B/C pulls over {a.toys} toys: mean {rnd(mean, 3)}, width {rnd(width, 3)}.",
              f"Fixed subtraction with a carbon model {1 - CARBON_MODEL_SCALE:.0%} low: relative bias of B/C "
              f"{rnd(c_mean, 3)}.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    tmp.cleanup()
    print(json.dumps({"pass": passed}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
