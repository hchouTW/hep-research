#!/usr/bin/env python3
"""Example E-2: a SYNTHETIC antiproton-to-proton ratio with a curvature offset in one era, from the residual to its
effect on the ratio, its systematic ledger entry, and its recovery by a likelihood fit.

SYNTHETIC and ILLUSTRATIVE. Two power-law spectra of opposite charge sign (index 2.8, an invented ratio of 1%) are
measured in two eras of a fictional magnetic spectrometer; the second era carries an offset of the signed curvature,
1/R_m = 1/R + q delta (for example a misalignment after a detector change). Every number is invented; no experiment
and no profile is used.

Chain (each step runs the plugin's tool, as a user would):
1. hep-detector D1 `propagate_scale_distortion.py response --mode inverse-offset`: the per-bin yield shifts of both
   species for the injected delta and the shift of the ratio. Check: the ratio shift equals the difference of the
   signed shifts, r (1 + s_p) = s_pbar - s_p, exactly (the two shifts have opposite signs, so they add in magnitude).
2. hep-measurement M5: the residual enters the systematics ledger as a measurement-spec systematic with its scaling
   class (statistical-like: the alignment sample that sets delta grows with the exposure) and its era correlation;
   the entry validates against the spec schema.
3. Synthetic counts: Poisson draws of both species in both eras (era e1 without offset, e2 with it).
4. hep-statistics `covariance_fit.py fit` (model plugin, with --allow-plugin): the double ratio
   D_i = (pbar/p)_e2 / (pbar/p)_e1 per bin, with its Poisson covariance, is fitted with the exact bin-integrated model
   D_i(delta) = int x^-g (1 + x delta)^(g-2) / int x^-g (1 - x delta)^(g-2); the injected delta is recovered
   within 3 sigma.
Advisory (not run here): the ratio-subset/v1 analysis check of D1's validation record needs a frozen chain bundle;
its expected state is `unverified` until a test shows how r-ratio.cancellation treats per-sign factor tables, and
nothing here depends on it.

Usage (from the plugin root): python3 examples/pbar-p-curvature-offset/run.py [--seed 20261017] [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy and scipy.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.schema import validate  # noqa: E402

D1 = PLUGIN / "skills" / "hep-detector" / "scripts" / "propagate_scale_distortion.py"
FIT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"
EDGES = [round(20.0 * 20.0 ** (i / 8), 6) for i in range(9)]  # 20 to 400 GV, eight log bins
INDEX = 2.8
NORM_P, RATIO = 1.0e11, 0.01  # invented: protons per unit of the power law, antiproton-to-proton ratio
DELTA_TRUE = 2.0e-4  # GV^-1, the injected curvature offset of era e2
CRITERIA = {"ratio_identity_abs": 1e-12, "delta_pull_abs_max": 3.0}
LABEL = "SYNTHETIC and ILLUSTRATIVE: invented spectra and offset; describes no experiment"

PLUGIN_MODEL = '''import numpy as np
EDGES = {edges!r}
G = {index!r}


def _integral(sign_delta, lo, hi):
    x = np.geomspace(lo, hi, 401)
    f = x ** -G * (1.0 + sign_delta * x) ** (G - 2.0)
    return np.trapezoid(f * x, np.log(x))  # integrate in ln x: smooth for a power law


def double_ratio(theta, x):
    """(pbar/p) with the offset over (pbar/p) without it, per bin: q = -1 for pbar, +1 for p."""
    d = float(theta[0])
    if abs(d) * EDGES[-1] >= 0.9:  # outside the one-to-one domain of the mapping: a far, finite prediction
        return np.full(len(EDGES) - 1, 1.0e3)
    out = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        out.append(_integral(+d, lo, hi) / _integral(-d, lo, hi))
    return np.array(out)
'''


def tool(script, *args, cwd=None) -> dict:
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=cwd or PLUGIN)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise SystemExit(f"{Path(script).name}: no JSON (exit {p.returncode}): {p.stderr[-800:]}")
    out["_exit"] = p.returncode
    return out


def rnd(x, digits=6):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, digits) for v in x]
    return float(f"{float(x):.{digits}g}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    work_dir = tempfile.TemporaryDirectory()
    work = Path(work_dir.name)
    checks: dict = {}

    # 1. D1: the residual on both species and on the ratio
    model = {"variable": "rigidity", "unit": "GV", "edges": EDGES,
             "components": [{"name": "protons", "charge_sign": 1,
                             "spectrum": {"kind": "power-law", "index": INDEX, "norm": NORM_P}},
                            {"name": "antiprotons", "charge_sign": -1,
                             "spectrum": {"kind": "power-law", "index": INDEX, "norm": NORM_P * RATIO}}],
             "ratio": {"numerator": "antiprotons", "denominator": "protons"}}
    (work / "d1.json").write_text(json.dumps(model), encoding="utf-8")
    d1 = tool(D1, "response", work / "d1.json", "--mode", "inverse-offset", "--delta", DELTA_TRUE, "--status", "synthetic")
    assert d1["status"] == "ok", d1
    s_p = np.array(d1["components"]["protons"]["relative_shift_up"])
    s_a = np.array(d1["components"]["antiprotons"]["relative_shift_up"])
    r = np.array(d1["ratio"]["relative_shift_up"])
    identity = float(np.max(np.abs(r * (1.0 + s_p) - (s_a - s_p))))
    checks["d1"] = {"delta": DELTA_TRUE, "proton_shift": rnd(s_p, 5), "antiproton_shift": rnd(s_a, 5),
                    "ratio_shift": rnd(r, 5), "signed_shift_difference": rnd(s_a - s_p, 5),
                    "max_abs_r(1+s_p)-(s_pbar-s_p)": rnd(identity, 3)}

    # 2. M5: the systematics ledger entry, validated against the measurement-spec schema
    spec_schema = json.loads((PLUGIN / "contracts" / "schemas" / "ext_measurement_spec.json").read_text(encoding="utf-8"))
    entry = {"name": "curvature offset, era e2", "source": "alignment residual (signed curvature offset delta)",
             "effect": "shape", "applied_via": "propagate_scale_distortion.py inverse-offset variations",
             "scaling": "statistical-like", "era_correlation": "uncorrelated",
             "notes": "the alignment sample that sets delta grows with the exposure; e1 carries no offset"}
    rep = validate(entry, spec_schema["properties"]["systematics"]["items"])
    ledger_ok = not any(f.severity == "error" for f in rep.findings)
    ledger = {"label": LABEL, "systematics": [dict(entry, ratio_relative_shift_up=rnd(r, 5),
                                                    ratio_relative_shift_down=rnd(d1["ratio"]["relative_shift_down"], 5))]}
    (out / "systematics_ledger.json").write_text(json.dumps(ledger, indent=1) + "\n", encoding="utf-8")

    # 3. synthetic counts in both eras
    rng = np.random.default_rng(a.seed)
    mu = {("e1", "p"): np.array(d1["components"]["protons"]["nominal"]),
          ("e1", "pbar"): np.array(d1["components"]["antiprotons"]["nominal"]),
          ("e2", "p"): np.array(d1["components"]["protons"]["up"]),
          ("e2", "pbar"): np.array(d1["components"]["antiprotons"]["up"])}
    n = {k: rng.poisson(v).astype(float) for k, v in mu.items()}

    # 4. covariance_fit.py with the bin-integrated double-ratio model
    dr = (n["e2", "pbar"] / n["e2", "p"]) / (n["e1", "pbar"] / n["e1", "p"])
    rel_var = 1 / n["e2", "pbar"] + 1 / n["e2", "p"] + 1 / n["e1", "pbar"] + 1 / n["e1", "p"]
    cov = np.diag(dr * dr * rel_var)
    (work / "model_plugin.py").write_text(PLUGIN_MODEL.format(edges=EDGES, index=INDEX), encoding="utf-8")
    centers = [math.sqrt(lo * hi) for lo, hi in zip(EDGES[:-1], EDGES[1:])]
    fit_in = {"y": dr.tolist(), "cov": cov.tolist(), "x": centers, "model": "plugin", "start": [0.0],
              "model_options": {"plugin": {"path": "model_plugin.py", "function": "double_ratio", "n_params": 1}}}
    (work / "fit.json").write_text(json.dumps(fit_in), encoding="utf-8")
    fit = tool(FIT, "fit", "--input", work / "fit.json", "--allow-plugin")
    assert fit["status"] == "ok", fit
    par, err = fit["theta"], fit["theta_errors"]
    delta_hat, delta_err = float(par[0]), float(err[0])
    pull = (delta_hat - DELTA_TRUE) / delta_err
    checks["fit"] = {"delta_hat": rnd(delta_hat), "delta_error": rnd(delta_err, 4), "pull": rnd(pull, 4),
                     "chi2": rnd(fit["chi2"], 5), "dof": fit["dof"], "p_value": rnd(fit["p_value"], 4)}
    checks["advisory_ratio_subset_v1"] = ("not run: it needs a frozen chain bundle; expected unverified until a test "
                                          "shows how r-ratio.cancellation treats per-sign factor tables")

    checks["delta_significance"] = rnd(delta_hat / delta_err, 4)
    passed = {
        "ratio_shift_equals_difference_of_signed_shifts": identity <= CRITERIA["ratio_identity_abs"],
        "shifts_have_opposite_signs_and_magnitudes_add": bool(np.all(s_p < 0) and np.all(s_a > 0)
                                                              and np.all(np.abs(r) > np.abs(s_a))),
        "m5_ledger_entry_validates": ledger_ok,
        "injected_delta_recovered_within_3_sigma": abs(pull) < CRITERIA["delta_pull_abs_max"],
        "delta_measured_at_5_sigma_or_more": abs(delta_hat / delta_err) >= 5.0,
    }
    results = {"label": LABEL, "seed": a.seed, "edges_gv": EDGES, "index": INDEX, "ratio_true": RATIO,
               "delta_true": DELTA_TRUE, "checks": checks, "criteria": CRITERIA, "pass": passed}
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    lines = [f"# Antiproton-to-proton ratio with a curvature offset (E-2)\n\n{LABEL}.\n",
             "| Check | Result |", "|---|---|"] + [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in passed.items()]
    lines += ["", f"Injected delta {DELTA_TRUE:g} GV^-1, fitted {delta_hat:.4g} +- {delta_err:.2g} (pull {pull:.2f}).",
              f"Ratio shift in the top bin {r[-1]:.4f} = proton {s_p[-1]:.4f} vs antiproton {s_a[-1]:.4f}.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    work_dir.cleanup()
    print(json.dumps({"pass": passed, "delta_hat": delta_hat, "pull": pull}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
