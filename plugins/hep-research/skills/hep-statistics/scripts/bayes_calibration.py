#!/usr/bin/env python3
"""Calibration checks of a Bayesian computation (hep-statistics audit T25). Needs NumPy and SciPy.

check-quantiles  posterior draws (chains) against an analytic posterior: each requested quantile must agree within
                 K_MCSE (4) Monte Carlo standard errors (MCSE from bayes_diagnostics.py, Vehtari et al. 2021). Chains
                 that do not pass the convergence diagnostics give status not-run: their quantiles are not evidence.
                 Analytic posteriors: poisson-gamma (rate lambda, prior Gamma(a, b) in shape-rate, n events in
                 exposure T: posterior Gamma(a + n, b + T)) and normal-normal (mean mu, prior Normal(m0, s0), N
                 draws of known sd sigma with mean xbar). A sampler that leaves out the Jacobian of a transformation
                 (for example sampling log lambda with the prior written on lambda) fails this check.
sbc              simulation-based calibration (Talts et al. 2018, arXiv:1804.06788) of the conjugate Poisson-Gamma
                 model: theta from the prior, data from the model, L posterior draws, the rank of theta among them;
                 ranks are uniform if and only if the posterior computation is correct for data generated from the
                 prior predictive. The test (chi-square over bins) and its power are fixed before any run: 1000
                 replications, L = 99, 20 bins, alpha = 0.01; power against a posterior too narrow by a factor 0.7
                 is estimated by simulation and must be at least 0.9, otherwise the run is underpowered (status
                 inconclusive, not pass). SBC checks the computation averaged over the prior; it is not frequentist
                 coverage at a fixed theta, and it is not a posterior predictive check (which compares replicated data
                 with the observed data of one fit).

Usage: bayes_calibration.py check-quantiles --input DRAWS.json   ({"chains": [[...], ...], "posterior": {...},
                                             "quantiles": [0.05, 0.5, 0.95]})
       bayes_calibration.py sbc [--reps 1000 --draws 99 --bins 20 --seed 1 --width-factor 1.0 --power-runs 50]
Exit codes: 0 pass; 1 fail; 2 bad input; 3 not-run or inconclusive (chains not converged, or an underpowered SBC).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
    from scipy import stats
except ImportError:  # pragma: no cover
    np = stats = None  # type: ignore[assignment]

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bayes_diagnostics as bd  # noqa: E402

K_MCSE = 4.0
SBC = {"reps": 1000, "draws": 99, "bins": 20, "alpha": 0.01, "power_alternative_width_factor": 0.7, "power_min": 0.9}


def posterior(spec: dict):
    kind = spec.get("kind")
    if kind == "poisson-gamma":
        a, b, n, t = (float(spec[k]) for k in ("a", "b", "n", "T"))
        if a <= 0 or b <= 0 or n < 0 or t <= 0:
            raise ValueError("poisson-gamma needs a > 0, b > 0 (a proper prior), n >= 0, T > 0")
        return stats.gamma(a + n, scale=1.0 / (b + t))
    if kind == "normal-normal":
        m0, s0, xbar, sigma, n = (float(spec[k]) for k in ("m0", "s0", "xbar", "sigma", "N"))
        if s0 <= 0 or sigma <= 0 or n < 1:
            raise ValueError("normal-normal needs s0 > 0 (a proper prior), sigma > 0, N >= 1")
        prec = 1 / s0 ** 2 + n / sigma ** 2
        return stats.norm((m0 / s0 ** 2 + n * xbar / sigma ** 2) / prec, 1 / math.sqrt(prec))
    raise ValueError("posterior.kind must be poisson-gamma or normal-normal")


def check_quantiles(chains, spec: dict, probs=(0.05, 0.5, 0.95)) -> dict:
    x = np.asarray(chains, dtype=float)
    diag = bd.diagnose_param(x, tuple(probs))
    status = bd.classify(diag)
    exact = posterior(spec)
    rows = {}
    for p in probs:
        q = diag.get("quantiles", {}).get(str(p))
        if not q or q["mcse"] in (None, 0.0):
            rows[str(p)] = {"status": "not-run", "reason": "MCSE undefined"}
            continue
        ref = float(exact.ppf(p))
        z = (q["value"] - ref) / q["mcse"]
        rows[str(p)] = {"estimate": q["value"], "exact": ref, "mcse": q["mcse"], "z": z,
                        "status": "pass" if abs(z) <= K_MCSE else "fail"}
    if status != "converged":
        overall = "not-run"
    elif any(r["status"] == "fail" for r in rows.values()):
        overall = "fail"
    elif any(r["status"] == "not-run" for r in rows.values()):
        overall = "not-run"
    else:
        overall = "pass"
    return {"status": overall, "convergence": status, "rhat": diag.get("rhat"), "ess_bulk": diag.get("ess_bulk"),
            "quantiles": rows, "rule": f"|estimate - exact| <= {K_MCSE:g} MCSE per quantile, chains converged"}


def _sbc_once(rng, reps, draws, bins, width_factor, a=3.0, b=1.0, t=2.0):
    ranks = np.empty(reps, dtype=int)
    for r in range(reps):
        lam = rng.gamma(a, 1.0 / b)
        n = rng.poisson(lam * t)
        post = rng.gamma(a + n, 1.0 / (b + t), size=draws)
        if width_factor != 1.0:
            mean = (a + n) / (b + t)
            post = mean + width_factor * (post - mean)       # a deliberately mis-scaled posterior
        ranks[r] = int(np.sum(post < lam))
    counts = np.bincount(ranks * bins // (draws + 1), minlength=bins)
    chi2 = float(np.sum((counts - reps / bins) ** 2 / (reps / bins)))
    return counts, chi2, float(stats.chi2.sf(chi2, bins - 1))


def sbc(seed=1, width_factor=1.0, power_runs=50, reps=SBC["reps"], draws=SBC["draws"], bins=SBC["bins"]) -> dict:
    if not (isinstance(bins, int) and bins >= 2 and reps >= 1 and draws >= 1 and power_runs >= 0):
        raise ValueError("need bins >= 2, reps >= 1, draws >= 1 and power_runs >= 0")
    if not (math.isfinite(width_factor) and width_factor > 0):
        raise ValueError("width_factor must be a finite positive number")
    if (draws + 1) % bins:
        raise ValueError("bins must divide draws + 1 (equal rank bins)")
    rng = np.random.default_rng(seed)
    counts, chi2, p = _sbc_once(rng, reps, draws, bins, width_factor)
    power = None
    if power_runs:
        prng = np.random.default_rng(seed + 1)
        rejections = sum(_sbc_once(prng, reps, draws, bins, SBC["power_alternative_width_factor"])[2] < SBC["alpha"]
                         for _ in range(power_runs))
        power = rejections / power_runs
    underpowered = power is not None and power < SBC["power_min"]
    if p < SBC["alpha"]:
        status = "fail"
    elif underpowered or power is None:
        status = "inconclusive"
    else:
        status = "pass"
    return {"status": status, "model": "poisson-gamma (prior Gamma(3, 1), exposure 2)", "settings": dict(SBC, reps=reps, draws=draws, bins=bins),
            "width_factor": width_factor, "rank_counts": counts.tolist(), "chi2": chi2, "p_value": p,
            "power_against_width_0.7": power, "power_runs": power_runs, "seed": seed,
            "note": ("uniform ranks check the posterior computation averaged over the prior predictive; this is not "
                     "frequentist coverage at a fixed parameter and not a posterior predictive check")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check-quantiles")
    c.add_argument("--input", required=True)
    s = sub.add_parser("sbc")
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--width-factor", type=float, default=1.0)
    s.add_argument("--power-runs", type=int, default=50)
    s.add_argument("--reps", type=int, default=SBC["reps"])
    s.add_argument("--draws", type=int, default=SBC["draws"])
    s.add_argument("--bins", type=int, default=SBC["bins"])
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy and SciPy are required"}))
        return 2
    try:
        if a.command == "check-quantiles":
            doc = json.loads(Path(a.input).read_text())
            out = check_quantiles(doc["chains"], doc["posterior"], tuple(doc.get("quantiles", (0.05, 0.5, 0.95))))
        else:
            out = sbc(a.seed, a.width_factor, a.power_runs, a.reps, a.draws, a.bins)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(out, indent=1))
    return {"pass": 0, "fail": 1, "not-run": 3, "inconclusive": 3}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
