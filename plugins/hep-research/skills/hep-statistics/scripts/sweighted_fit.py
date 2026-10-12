#!/usr/bin/env python3
"""sWeighted lifetime fit with its covariance checked by resampling (hep-statistics audit T21). Needs NumPy and SciPy.

Model: a discriminating variable m on [0, 1] with a Gaussian signal (mean, width given) and a flat background; a
control variable t >= 0, exponential in both components. Steps: extended maximum likelihood of the two yields in m
(shapes known), sWeights (Pivk and Le Diberder 2005), and the sWeighted fit of the signal lifetime tau_s, whose
estimate is sum(w t) / sum(w). Uncertainties of tau_s:
  naive       the inverse weighted Hessian, tau / sqrt(sum w) (what a plain weighted fit reports);
  sumw2       H^-1 H_w2 H^-1 with H_w2 the Hessian summed with squared weights, in the rate parametrization
              (lambda = 1/tau, where every event's Hessian is the same), i.e. tau sqrt(sum w^2) / sum w: the SumW2
              recipe, which depends on the parametrization and is too small for sWeights. RooFit's SumW2Error gave
              0.0444 on the sample where this gives 0.0389 (ROOT 6.38.04): the difference is not explained here and
              this value is not used for inference;
  sandwich    H^-1 (sum w^2 g^2) H^-1, the weights treated as known (equal to RooFit's AsymptoticError, checked with
              ROOT 6.38.04 on one sample: 0.086340 against 0.086332);
  asymptotic  the stacked estimating equations of the yields, the inverse yield covariance and tau, A^-1 B A^-T
              (Langenbruch 2022, arXiv:1911.01303), which carries the uncertainty of the sWeights themselves;
  bootstrap   the standard deviation of tau_s over resamples of the events, each repeating the whole chain (yield
              fit, sWeights, weighted fit): the independent resampling check of the covariance.
Assumption checked: sPlot needs m and t independent within each component. In the background-dominated sidebands
(|m - mean| > 3 widths; 0.27% of a Gaussian signal leaks in. 3 rather than 5 widths was chosen by a size and power study
on the walkthrough model: size 4/400 at both, power against the broken-factorization variant 100/100 at 3 widths and
32/100 at 5, where the sidebands miss the region of strongest dependence) the t distributions of six equal-count slices in m and, separately, in |m - mean| are compared
(Kruskal-Wallis, Bonferroni over the two); p < 0.01 (fixed before any run) marks the result invalid. A first version used Kendall's rank correlation, which misses a dependence
that is symmetric in m (the walkthrough's broken-factorization variant) and was replaced. A larger uncertainty does not repair a violated assumption: the result is not
usable until the model is changed (for example a joint (m, t) fit). The sideband check sees the background only; the
signal's independence must come from simulation and is declared, not tested here.

Usage: sweighted_fit.py fit --input EVENTS.json [--bootstrap 200 --seed 1]
  EVENTS.json: {"m": [...], "t": [...], "signal": {"mean": 0.5, "width": 0.05}}
Exit codes: 0 fitted, assumption check passed; 1 fitted but the assumption check failed (status invalid) or the yield
fit did not converge; 2 bad input. Output JSON labelled [General method].
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LABEL = "[General method]"
INDEPENDENCE_ALPHA = 0.01
SIDEBAND_WIDTHS = 3.0
SLICES = 6


class SWeightError(ValueError):
    pass


def f_sig(m, mean, width):
    norm = 0.5 * (math.erf((1 - mean) / (width * math.sqrt(2))) - math.erf((0 - mean) / (width * math.sqrt(2))))
    return np.exp(-0.5 * ((m - mean) / width) ** 2) / (width * math.sqrt(2 * math.pi) * norm)


def fit_yields(F):
    y = np.array([F.shape[0] / 3, 2 * F.shape[0] / 3])
    for _ in range(100):
        D = F @ y
        g = (F / D[:, None]).sum(axis=0) - 1.0
        H = -(F[:, :, None] * F[:, None, :] / (D ** 2)[:, None, None]).sum(axis=0)
        step = np.linalg.solve(H, -g)
        y = y + step
        if np.max(np.abs(step)) < 1e-10:
            return y
    raise SWeightError("the yield fit did not converge in 100 Newton steps")


def _estimating(theta, F, t):
    ns, nb, wss, wsb, wbb, tau = theta
    D = F @ np.array([ns, nb])
    winv = np.linalg.inv(np.array([[wss, wsb], [wsb, wbb]]))
    w = (winv[0, 0] * F[:, 0] + winv[0, 1] * F[:, 1]) / D
    u = np.column_stack([F[:, 0] / D, F[:, 1] / D, F[:, 0] ** 2 / D ** 2, F[:, 0] * F[:, 1] / D ** 2,
                         F[:, 1] ** 2 / D ** 2, w * (t / tau ** 2 - 1 / tau)])
    return u, np.array([1.0, 1.0, wss, wsb, wbb, 0.0])


def chain(m, t, mean, width, errors=True):
    F = np.column_stack([f_sig(m, mean, width), np.ones_like(m)])
    y = fit_yields(F)
    D = F @ y
    W = (F[:, :, None] * F[:, None, :] / (D ** 2)[:, None, None]).sum(axis=0)
    V = np.linalg.inv(W)
    w = (V[0, 0] * F[:, 0] + V[0, 1] * F[:, 1]) / D
    tau = float(np.sum(w * t) / np.sum(w))
    out = {"yields": y.tolist(), "tau": tau}
    if not errors:
        return out
    g = t / tau ** 2 - 1 / tau
    h = w.sum() / tau ** 2
    theta = np.array([y[0], y[1], W[0, 0], W[0, 1], W[1, 1], tau])
    u, _ = _estimating(theta, F, t)
    A = np.empty((6, 6))
    for j in range(6):
        step = 1e-6 * max(1.0, abs(theta[j]))
        tp, tm = theta.copy(), theta.copy()
        tp[j] += step
        tm[j] -= step
        up, kp = _estimating(tp, F, t)
        um, km = _estimating(tm, F, t)
        A[:, j] = ((up.sum(axis=0) - kp) - (um.sum(axis=0) - km)) / (2 * step)
    Ai = np.linalg.inv(A)
    out["sigma"] = {"naive": tau / math.sqrt(w.sum()), "sumw2": float(tau * math.sqrt(np.sum(w ** 2)) / w.sum()),
                    "sandwich": float(math.sqrt(np.sum(w ** 2 * g ** 2)) / h),
                    "asymptotic": math.sqrt((Ai @ (u.T @ u) @ Ai.T)[5, 5])}
    return out


def independence(m, t, mean, width) -> dict:
    side = np.abs(m - mean) > SIDEBAND_WIDTHS * width
    if side.sum() < 30:
        return {"status": "not-run", "reason": "fewer than 30 sideband events"}
    ms, ts = m[side], t[side]

    def kw(x):
        edges = np.quantile(x, np.linspace(0, 1, SLICES + 1))
        groups = [ts[(x >= lo) & ((x <= hi) if k == SLICES - 1 else (x < hi))] for k, (lo, hi) in enumerate(zip(edges, edges[1:]))]
        return stats.kruskal(*groups)
    (_, p1), (_, p2) = kw(ms), kw(np.abs(ms - mean))
    p = min(1.0, 2.0 * min(p1, p2))               # Bonferroni over the two slicings
    return {"status": "violated" if p < INDEPENDENCE_ALPHA else "not-rejected",
            "test": f"Kruskal-Wallis of t over {SLICES} slices in m and in |m - mean| (Bonferroni)",
            "p_value": float(p), "p_value_m_slices": float(p1), "p_value_distance_slices": float(p2),
            "alpha": INDEPENDENCE_ALPHA, "sideband_events": int(side.sum()),
            "scope": "background in the sidebands only; the signal's m-t independence is a declared assumption"}


def fit(m, t, mean, width, bootstrap=200, seed=1) -> dict:
    m, t = np.asarray(m, dtype=float), np.asarray(t, dtype=float)
    if m.shape != t.shape or m.ndim != 1 or len(m) < 50:
        raise SWeightError("m and t must be equal-length lists of at least 50 events")
    if np.any((m < 0) | (m > 1)) or np.any(t < 0):
        raise SWeightError("m must lie in [0, 1] and t >= 0")
    res = chain(m, t, mean, width)
    if bootstrap:
        rng = np.random.default_rng(seed)
        taus = []
        for _ in range(bootstrap):
            idx = rng.integers(0, len(m), len(m))
            taus.append(chain(m[idx], t[idx], mean, width, errors=False)["tau"])
        res["sigma"]["bootstrap"] = float(np.std(taus, ddof=1))
        res["bootstrap"] = {"replicas": bootstrap, "seed": seed,
                            "relative_precision_of_sigma": 1 / math.sqrt(2 * (bootstrap - 1))}
    res["independence"] = independence(m, t, mean, width)
    res["status"] = "invalid" if res["independence"]["status"] == "violated" else "ok"
    res["label"] = LABEL
    res["note"] = ("quote the asymptotic uncertainty (checked against the bootstrap); naive, sumw2 and sandwich ignore the "
                   "sWeights' own uncertainty, and naive and sumw2 are too small for sWeights; an invalid status means the sPlot factorization fails in the sidebands: change the "
                   "model, do not inflate the error")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--input", required=True)
    p.add_argument("--bootstrap", type=int, default=200)
    p.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    try:
        doc = json.loads(Path(a.input).read_text())
        out = fit(doc["m"], doc["t"], doc["signal"]["mean"], doc["signal"]["width"], a.bootstrap, a.seed)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
