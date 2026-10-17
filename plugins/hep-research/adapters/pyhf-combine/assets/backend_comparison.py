#!/usr/bin/env python3
"""Compare the same likelihood in core/stats (shape-limit model) and pyhf: model-aligned NLL differences, profiled
test statistics on a POI grid, and limits (hep-statistics audit T16).

The core model is mapped to a one-channel pyhf workspace only where the two parametrizations are the same function:
signal with a normfactor (mu); a normalization nuisance given as hi/lo factors with code4 -> normsys code4 (the
mapping fails for the code0 and code1 variants of hi/lo factors only if pyhf lacks them: code1 is mapped, code0 is
refused); a Gaussian sigma normalization (factor 1 + sigma theta) -> histosys code0 with up = (1 + sigma) x nominal and
down = (1 - sigma) x nominal, allowed only on a sample with no other shape nuisance (in pyhf histosys adds, in core a
normalization multiplies); shapes code0 / code4p -> histosys code0 / code4p; mc_stat -> staterror. Log-normal and
gamma priors and correlation matrices have no pyhf equivalent here and are refused, not approximated.

Checks and tolerances (fixed here before any comparison; model scale: total counts below 400):
- pointwise: Delta NLL(p) = NLL(p) - NLL(nominal) at the nominal point, every nuisance at +-0.5 (inside the
  interpolation polynomials, where code1 and code4 differ), +-1 and +-2.5 sigma (extrapolation) and a mu grid;
  |core - pyhf| <= 1e-9 + 1e-9 |Delta NLL|. The comparison involves no optimizer, so the tolerance is floating point:
  the audit's starting value (1e-4 + 1e-3 |Delta NLL|) could not resolve a wrong interpolation code (pyhf normsys
  code1 for a code4 factor changes Delta NLL by 3e-4 inside |theta| < 1); this was found with the negative control and
  the tolerance was tightened, never loosened. Absolute NLLs differ by constants
  (log n!, Gaussian normalizations) and are never compared. Models with mc_stat are not compared pointwise, since
  core profiles the MC-statistics factors in closed form inside its NLL;
- profiled: q-tilde_mu on the mu grid, core (damped Newton, EDM <= 1e-5) against pyhf (scipy, tolerance 1e-10);
  |Delta q| <= 2e-3 + 2e-3 q;
- limits: the observed asymptotic CLs limits are reported with their relative difference and are not called the
  same oracle: pyhf builds its Asimov data set from the conditional fit to the data at mu = 0, core from the
  nominal model, so they agree only where the nuisances are not pulled.
Combine: not run by this script (no Combine in the environment checked); its comparison is a release-gate item.

Size: the conversion runs no toys, so it takes the core asymptotic path and its caps (SHAPE_ASYMPTOTIC_CAPS: up to 100
bins), not the toy caps (S7).

Usage: backend_comparison.py --model SHAPE_MODEL.json [--mu-grid 0,0.5,1,2,3] [--out REPORT.json]
Exit codes: 0 every pointwise and profiled check within tolerance; 1 a check outside tolerance; 2 the model cannot be
mapped (refused, with the reason) or pyhf is not installed. Needs pyhf (tested with 0.7.6) and NumPy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))

from core.stats import likelihood_limits as ll  # noqa: E402

TOL = {"pointwise_abs": 1e-9, "pointwise_rel": 1e-9, "q_abs": 2e-3, "q_rel": 2e-3}


class MappingRefused(ValueError):
    """The core model has a feature without an equal pyhf parametrization."""


def to_pyhf(doc: dict, normsys_code: str = "code4") -> tuple[dict, list[str]]:
    """pyhf workspace spec and the pyhf parameter name of each core nuisance (in core order)."""
    bins, nuis, chol = ll._load_shape(doc, asymptotic=True)  # S7: no toys here, so the asymptotic caps
    if chol is not None:
        raise MappingRefused("a correlation matrix between nuisances has no pyhf equivalent here")
    sig = {"name": "signal", "data": [x["s"] for x in bins], "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]}
    bkg = {"name": "background", "data": [x["b"] for x in bins], "modifiers": []}
    names = []
    shapes_on = {"signal": sum(d["kind"] == "signal_shape" for d in nuis), "background": sum(d["kind"] == "background_shape" for d in nuis)}
    for k, d in enumerate(nuis):
        name = f"np_{k}_{d['name']}"
        names.append(name)
        target = sig if d["kind"].startswith("signal") else bkg
        if d["kind"].endswith("_norm"):
            if d.get("prior", "gaussian") != "gaussian":
                raise MappingRefused(f"nuisance {d['name']}: a {d['prior']} prior has no pyhf equivalent here")
            if "hi" in d:
                if d["interpolation"] == "code0":
                    raise MappingRefused(f"nuisance {d['name']}: pyhf normsys has no code0")
                target["modifiers"].append({"name": name, "type": "normsys", "data": {"hi": d["hi"], "lo": d["lo"]}})
                if d["interpolation"] != normsys_code:
                    raise MappingRefused(f"nuisance {d['name']}: interpolation {d['interpolation']} differs from the "
                                         f"workspace's normsys {normsys_code}")
            else:
                if shapes_on[target["name"]]:
                    raise MappingRefused(f"nuisance {d['name']}: a linear normalization on a sample with a shape "
                                         "nuisance would add in pyhf and multiply in core")
                nom = target["data"]
                target["modifiers"].append({"name": name, "type": "histosys",
                                            "data": {"hi_data": [v * (1 + d["sigma"]) for v in nom],
                                                     "lo_data": [v * (1 - d["sigma"]) for v in nom]}})
        else:
            target["modifiers"].append({"name": name, "type": "histosys",
                                        "data": {"hi_data": list(d["up"]), "lo_data": list(d["down"])}})
    if any("mc_stat" in x for x in bins):
        bkg["modifiers"].append({"name": "mc_stat", "type": "staterror", "data": [x.get("mc_stat", 0.0) for x in bins]})
    spec = {"channels": [{"name": "ch", "samples": [sig, bkg]}],
            "observations": [{"name": "ch", "data": [float(x["n"]) for x in bins]}],
            "measurements": [{"name": "meas", "config": {"poi": "mu", "parameters": [{"name": "mu", "bounds": [[0.0, 50.0]]}]}}],
            "version": "1.0.0"}
    shape_codes = {d["interpolation"] for d in nuis if d["kind"].endswith("_shape")}
    if len(shape_codes) > 1:
        raise MappingRefused("pyhf sets one histosys interpolation per model; the core model mixes code0 and code4p")
    spec["_histosys_code"] = shape_codes.pop() if shape_codes else "code0"
    spec["_normsys_code"] = normsys_code
    return spec, names


def _model(spec):
    import pyhf
    ws = pyhf.Workspace({k: v for k, v in spec.items() if not k.startswith("_")})
    m = ws.model(modifier_settings={"normsys": {"interpcode": spec["_normsys_code"]},
                                    "histosys": {"interpcode": spec["_histosys_code"]}})
    return m, ws.data(m)


def compare(doc: dict, mu_grid=(0.0, 0.5, 1.0, 2.0, 3.0), normsys_code: str = "code4") -> dict:
    import numpy as np
    import pyhf
    spec, names = to_pyhf(doc, normsys_code)
    pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=1e-10))
    try:
        model, data = _model(spec)
        core = ll._ShapeModel(*ll._load_shape(doc, asymptotic=True))
        aux = core.aux_obs()
        idx = {n: model.config.par_slice(n).start for n in model.config.par_order}
        init = np.asarray(model.config.suggested_init(), dtype=float)

        def pyhf_nll(mu, th):
            p = init.copy()
            p[idx["mu"]] = mu
            for n, t in zip(names, th):
                p[idx[n]] = t
            return -float(model.logpdf(p, data)[0])
        rows, worst = [], 0.0
        if not core.mc_rel:
            points = [(m, [0.0] * core.k) for m in mu_grid]
            for k in range(core.k):
                for t in (-2.5, -1.0, -0.5, 0.5, 1.0, 2.5):
                    th = [0.0] * core.k
                    th[k] = t
                    points.append((1.0, th))
            c0, p0 = core.nll(0.0, [0.0] * core.k, core.n, aux), pyhf_nll(0.0, [0.0] * core.k)
            for mu, th in points:
                dc, dp = core.nll(mu, th, core.n, aux) - c0, pyhf_nll(mu, th) - p0
                tol = TOL["pointwise_abs"] + TOL["pointwise_rel"] * abs(dp)
                ok = abs(dc - dp) <= tol
                worst = max(worst, abs(dc - dp) / tol)
                rows.append({"mu": mu, "theta": th, "core": dc, "pyhf": dp, "diff": dc - dp, "tolerance": tol, "ok": ok})
        g = core.glob(core.n, aux)
        qrows = []
        for mu in mu_grid:
            if mu == 0.0:
                continue
            qc = core.q(mu, core.n, aux, g)
            qp = float(pyhf.infer.test_statistics.qmu_tilde(mu, data, model, model.config.suggested_init(),
                                                            model.config.suggested_bounds(), model.config.suggested_fixed()))
            tol = TOL["q_abs"] + TOL["q_rel"] * abs(qp)
            qrows.append({"mu": mu, "core": qc, "pyhf": qp, "diff": qc - qp, "tolerance": tol, "ok": abs(qc - qp) <= tol})
        lim_core = ll.shape_limit(doc, 0.95, 0, 1)
        obs_p, _ = pyhf.infer.intervals.upper_limits.upper_limit(data, model, scan=None, level=0.05, rtol=1e-6)
        fits = core.log.summary()["observed"]
    finally:
        pyhf.set_backend("numpy", "scipy")
    ok = all(r["ok"] for r in rows) and all(r["ok"] for r in qrows) and fits["failed"] == 0
    return {"status": "equivalent" if ok else "not-equivalent", "tolerances": TOL, "pyhf": pyhf.__version__,
            "mapping": {"nuisances": names, "normsys_interpcode": spec["_normsys_code"], "histosys_interpcode": spec["_histosys_code"],
                        "mc_stat": bool(core.mc_rel)},
            "pointwise": rows, "pointwise_compared": bool(rows), "profiled": qrows, "core_fit_diagnostics": fits,
            "limits": {"core_asymptotic_cls": lim_core["asymptotic_observed_cls_upper_limit"], "pyhf_asymptotic_cls": float(obs_p),
                       "relative_difference": lim_core["asymptotic_observed_cls_upper_limit"] / float(obs_p) - 1.0,
                       "same_oracle": False,
                       "note": "Asimov data differ (pyhf: conditional fit to data at mu = 0; core: nominal model)"},
            "combine": {"status": "not-run", "reason": "Combine is not run by this script; see the release gate"}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--mu-grid", default="0,0.5,1,2,3")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        import pyhf  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "refused", "reason": "pyhf is not installed"}))
        return 2
    try:
        doc = json.loads(Path(a.model).read_text())
        grid = [float(x) for x in a.mu_grid.split(",") if x.strip()]
        rep = compare(doc, grid)
    except (OSError, ValueError, ll.LikelihoodError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 2
    text = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0 if rep["status"] == "equivalent" else 1


if __name__ == "__main__":
    sys.exit(main())
