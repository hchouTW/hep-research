#!/usr/bin/env python3
"""Multi-template extended Poisson fit with the full per-template Barlow-Beeston treatment.

Purpose: give the "put template statistics in the likelihood" rule an executable form for a
small fit with several templates and free yields. This is not a fitting framework: unweighted
Monte Carlo counts, one yield per template, no shape or normalization nuisances other than the
finite template statistics, at most 6 templates and 60 bins. Output is labeled [General
method]; nothing here is the performance of any experiment. Seed, toy count and configuration are echoed.

Model: data counts n_i are Poisson with mean nu_i = sum_j A_j a_ij, where the yield per
generated event is A_j = Y_j / M_j (M_j = generated MC events of template j) and a_ij is the
true expected MC count of template j in bin i, measured as the Poisson count m_ij. The
nuisances a_ij are profiled bin by bin through the single Lagrange multiplier of Barlow and
Beeston: a_ij = m_ij / (1 + A_j t_i) with t_i the root of (1 - t) sum_j A_j m_ij / (1 + A_j t)
= n_i. Yields are found with a Nelder-Mead search and their covariance from a numerical
Hessian of the profiled log-likelihood.

Subcommands:
  bb-fit    fit data with the naive (templates treated as exact) and the full Barlow-Beeston
            likelihood; report yields, errors and the error inflation.
  bb-toys   seeded toys: MC templates redrawn from the supplied ones, data drawn at given true
            yields; bias, spread, pull width and interval coverage per yield for each fit.
  wbb-fit   the same fit for weighted Monte Carlo (per-bin sums of weights and of squared
            weights; effective-count Barlow-Beeston) and with shape and normalization nuisances
            (Gaussian, vertical interpolation for shapes) fitted jointly with the yields.
  wbb-toys  seeded toys for the weighted, nuisance-carrying fit (naive versus full).

Input JSON: {"data": [counts per bin], "templates": {"sig": [MC counts per bin], "bkg": [...]},
"mc_events": {"sig": M, "bkg": M} (optional; default the sum of the template counts),
"true_yields": {"sig": Y, "bkg": Y} (bb-toys; default the Barlow-Beeston fit of the data)}.
wbb-fit input: the same, with a template given either as counts or as {"sumw": [...], "sumw2": [...]}
(sum of weights and sum of squared weights per bin; "mc_events" is then the total weight generated),
and an optional "nuisances": [{"name": "jes", "kind": "shape", "template": "sig", "up": [sumw per bin
at +1 sigma], "down": [...]}, {"name": "lumi", "kind": "norm", "template": "bkg", "sigma": 0.1}].

Usage (from the skill directory):
  python3 core/stats/template_fit.py bb-fit --input fit.json
  python3 core/stats/template_fit.py bb-toys --input fit.json --toys 200 --seed 1
  python3 core/stats/template_fit.py wbb-fit --input weighted.json
  python3 core/stats/template_fit.py wbb-toys --input weighted.json --toys 100 --seed 1
Fit outcome: every fit reports "diagnostics" (minimizer convergence and termination reason, whether the objective
is finite at the optimum, covariance quality, yields at the boundary) and an "outcome": converged,
converged-at-boundary, covariance-warning, not-converged or infeasible (a bin with data and no template support:
no yields can describe it). The result "status" is "failed" when any fit is not converged or infeasible;
"artifact_fit_status" (converged, converged-with-warnings, failed) and "artifact_status_labels" are what a
statistical-result artifact built from it must carry, so a failed fit stops inference downstream.
Exit codes: 0 ok; 1 fit failed (infeasible model or no convergence); 2 rejected input. Standard library only.
Importable: bb_fit, bb_toys, fit_yields, wbb_fit, wbb_toys.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

if __package__ in (None, ""):  # run as a script: put the plugin root on sys.path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

from core.stats._linalg import solve
from core.stats.statistical_toys import ToyError, _num, _seed, _std, _toys, poisson_draw


def _solve(a, b):
    return solve(a, b, error=ToyError, what="Hessian in the template fit")

LABEL = "[General method]"
NEG = -1e300
MAX_TEMPLATES, MAX_BINS = 6, 60


# --------------------------------------------------------------------------- minimizer
def _nelder_mead(f, x0, steps, max_iter: int = 600, tol: float = 1e-10, info: dict | None = None):
    """Minimize f; returns (x, f(x)). When `info` is a dict it receives converged, termination and iterations."""
    n = len(x0)
    converged, it = False, 0
    pts = [list(x0)] + [[x0[j] + (steps[j] if j == i else 0.0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for it in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol * (1.0 + abs(vals[0])):
            converged = True
            break
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        refl = [cen[j] + (cen[j] - pts[-1][j]) for j in range(n)]
        fr = f(refl)
        if fr < vals[0]:
            exp = [cen[j] + 2.0 * (cen[j] - pts[-1][j]) for j in range(n)]
            fe = f(exp)
            pts[-1], vals[-1] = (exp, fe) if fe < fr else (refl, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = refl, fr
        else:
            con = [cen[j] + 0.5 * (pts[-1][j] - cen[j]) for j in range(n)]
            fc = f(con)
            if fc < vals[-1]:
                pts[-1], vals[-1] = con, fc
            else:
                pts = [pts[0]] + [[pts[0][j] + 0.5 * (p[j] - pts[0][j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    best = min(range(n + 1), key=lambda i: vals[i])
    if info is not None:
        info.update(converged=converged, termination="tolerance" if converged else "max-iterations", iterations=it + 1)
    return pts[best], vals[best]


# ------------------------------------------------------------------------- likelihoods
def _ll_naive(data, m, mc, y) -> float:
    total = 0.0
    for i, n in enumerate(data):
        nu = sum(y[j] * m[j][i] / mc[j] for j in range(len(y)))
        if nu <= 0.0:
            if n > 0:
                return NEG
            continue
        total += (n * math.log(nu) if n > 0 else 0.0) - nu
    return total


def _ll_bb(data, m, mc, y) -> float:
    total = 0.0
    k = len(y)
    for i, n in enumerate(data):
        act = [j for j in range(k) if m[j][i] > 0 and y[j] > 0]
        if not act:
            if n > 0:
                return NEG
            continue
        a = [y[j] / mc[j] for j in act]
        mm = [m[j][i] for j in act]
        lo, hi = -1.0 / max(a) + 1e-12, 1.0
        for _ in range(60):
            t = 0.5 * (lo + hi)
            g = (1.0 - t) * sum(aj * mj / (1.0 + aj * t) for aj, mj in zip(a, mm)) - n
            lo, hi = (t, hi) if g > 0 else (lo, t)
        t = 0.5 * (lo + hi)
        nuis = [mj / (1.0 + aj * t) for aj, mj in zip(a, mm)]
        nu = sum(aj * x for aj, x in zip(a, nuis))
        if nu <= 0.0:
            if n > 0:
                return NEG
            continue
        total += (n * math.log(nu) if n > 0 else 0.0) - nu
        total += sum(mj * math.log(x) - x for mj, x in zip(mm, nuis) if x > 0)
    return total


def _hessian_cov(ll, y):
    k = len(y)
    h = [max(1e-3 * abs(v), 1e-3 * math.sqrt(abs(v) + 1.0), 1e-6) for v in y]
    hess = [[0.0] * k for _ in range(k)]
    f0 = ll(y)

    def shifted(da, db):
        z = list(y)
        for idx, d in da:
            z[idx] += d
        return ll(z)
    for a in range(k):
        hess[a][a] = (shifted([(a, h[a])], 0) - 2 * f0 + shifted([(a, -h[a])], 0)) / h[a] ** 2
        for b in range(a + 1, k):
            v = (shifted([(a, h[a]), (b, h[b])], 0) - shifted([(a, h[a]), (b, -h[b])], 0)
                 - shifted([(a, -h[a]), (b, h[b])], 0) + shifted([(a, -h[a]), (b, -h[b])], 0)) / (4 * h[a] * h[b])
            hess[a][b] = hess[b][a] = v
    try:
        inv = _solve([[-hess[i][j] for j in range(k)] for i in range(k)], [[1.0 if i == j else 0.0 for j in range(k)] for i in range(k)])
    except ToyError:
        return None
    return inv


def _unsupported_bins(data, m) -> list[int]:
    """Bins with data but no template support: no choice of yields can give them a positive mean."""
    return [i for i, n in enumerate(data) if n > 0 and all(row[i] <= 0 for row in m)]


def _covariance_quality(cov) -> str:
    if cov is None:
        return "singular"
    k = len(cov)
    if any(not math.isfinite(cov[i][j]) for i in range(k) for j in range(k)) or any(cov[i][i] <= 0 for i in range(k)):
        return "not-positive-definite"
    for i in range(k):
        for j in range(i + 1, k):
            if abs(cov[i][j]) / math.sqrt(cov[i][i] * cov[j][j]) > 1.0 - 1e-6:
                return "ill-conditioned"
    return "ok"


def _diagnostics(infos, ll_max, cov, y, unsupported) -> dict:
    converged = all(i.get("converged", False) for i in infos)
    valid = math.isfinite(ll_max) and ll_max > NEG / 2 and not unsupported
    covq = _covariance_quality(cov)
    boundary = [j for j, v in enumerate(y) if v <= 1e-6]
    if not valid:
        outcome = "infeasible"
    elif not converged:
        outcome = "not-converged"
    elif covq != "ok":
        outcome = "covariance-warning"
    elif boundary:
        outcome = "converged-at-boundary"
    else:
        outcome = "converged"
    return {"outcome": outcome, "converged": converged, "termination": [i.get("termination") for i in infos],
            "objective_valid": valid, "covariance": covq, "boundary_yields": boundary, "unsupported_bins": unsupported}


FAILED_OUTCOMES = {"infeasible", "not-converged"}


def _fit_yields_full(data, m, mc, kind: str, start=None):
    """(yields, covariance or None, ll_max, diagnostics) for kind 'naive' or 'bb'."""
    k = len(m)
    ll_fn = _ll_naive if kind == "naive" else _ll_bb
    total = max(sum(data), 1.0)
    x0 = list(start) if start else [total / k] * k
    steps = [0.3 * max(v, 1.0) for v in x0]

    def neg(x):
        y = [max(v, 1e-9) for v in x]
        return -ll_fn(data, m, mc, y)
    i1, i2 = {}, {}
    x, val = _nelder_mead(neg, x0, steps, info=i1)
    x, val = _nelder_mead(neg, x, [0.05 * max(v, 1.0) for v in x], info=i2)
    y = [max(v, 1e-9) for v in x]
    cov = _hessian_cov(lambda z: ll_fn(data, m, mc, [max(v, 1e-9) for v in z]), y)
    return y, cov, -val, _diagnostics([i1, i2], -val, cov, y, _unsupported_bins(data, m))


def fit_yields(data, m, mc, kind: str, start=None):
    """(yields, covariance or None, ll_max) for kind 'naive' or 'bb'; _fit_yields_full adds the diagnostics."""
    return _fit_yields_full(data, m, mc, kind, start)[:3]


# ----------------------------------------------------------------------------- input
def _load(doc):
    if not isinstance(doc, dict):
        raise ToyError("input must be a JSON object")
    data, tmpl = doc.get("data"), doc.get("templates")
    if not isinstance(data, list) or not 2 <= len(data) <= MAX_BINS:
        raise ToyError(f"data must be a list of 2 to {MAX_BINS} bin counts")
    data = [_num(v, "data", 0.0, 1e6) for v in data]
    if not isinstance(tmpl, dict) or not 1 <= len(tmpl) <= MAX_TEMPLATES:
        raise ToyError(f"templates must map 1 to {MAX_TEMPLATES} names to count lists")
    names = list(tmpl)
    m = []
    for nme in names:
        row = tmpl[nme]
        if not isinstance(row, list) or len(row) != len(data):
            raise ToyError(f"template {nme} must list {len(data)} counts")
        m.append([_num(v, f"template {nme}", 0.0, 1e7) for v in row])
        if sum(m[-1]) <= 0:
            raise ToyError(f"template {nme} is empty")
    mce = doc.get("mc_events", {})
    mc = []
    for nme, row in zip(names, m):
        v = _num(mce.get(nme, sum(row)), f"mc_events {nme}", 0.0, 1e9, strict_low=True)
        if v < sum(row) - 1e-9:
            raise ToyError(f"mc_events {nme} is below the sum of its template counts")
        mc.append(v)
    return names, data, m, mc


def _report(names, y, cov, diag=None):
    out = {}
    for j, nme in enumerate(names):
        err = math.sqrt(cov[j][j]) if cov is not None and cov[j][j] > 0 else None
        out[nme] = {"yield": y[j], "error": err, "at_boundary": y[j] <= 1e-6}
    if diag is not None:
        out["diagnostics"] = dict(diag, boundary_yields=[names[j] for j in diag["boundary_yields"]])
    return out


def _overall(result: dict, diags) -> dict:
    """Overall status of a fit result and the fit status a statistical-result artifact must carry."""
    outcomes = [d["outcome"] for d in diags]
    if any(o in FAILED_OUTCOMES for o in outcomes):
        result["status"], result["artifact_fit_status"], result["artifact_status_labels"] = "failed", "failed", ["failed"]
        why = []
        for d in diags:
            if d["outcome"] == "infeasible" and d["unsupported_bins"]:
                why.append("bins " + ", ".join(f"bin {i + 1}" for i in d["unsupported_bins"])
                           + " have data but no template support (infeasible model)")
            elif d["outcome"] == "infeasible":
                why.append("the likelihood is not finite at the optimum (infeasible model)")
            elif d["outcome"] == "not-converged":
                why.append(f"the minimizer stopped without converging ({', '.join(map(str, d['termination']))})")
        result["error"] = "; ".join(dict.fromkeys(why))
        result["note"] = "FIT FAILED: the yields and errors below are not a result and must not be used for inference. " + result.get("note", "")
    else:
        warn = any(o != "converged" for o in outcomes)
        result["status"] = "ok"
        result["artifact_fit_status"] = "converged-with-warnings" if warn else "converged"
        result["artifact_status_labels"] = []
    return result


def bb_fit(doc: dict) -> dict:
    names, data, m, mc = _load(doc)
    yn, cn, lln, dn = _fit_yields_full(data, m, mc, "naive")
    yb, cb, llb, db = _fit_yields_full(data, m, mc, "bb", yn)
    rn, rb = _report(names, yn, cn, dn), _report(names, yb, cb, db)
    infl = {nme: (rb[nme]["error"] / rn[nme]["error"] if rb[nme]["error"] and rn[nme]["error"] else None) for nme in names}
    return _overall({"label": LABEL, "method": "multi-template extended Poisson fit: naive versus full Barlow-Beeston",
            "bins": len(data), "templates": names, "naive": rn, "barlow_beeston": rb, "error_inflation_bb_over_naive": infl,
            "note": ("the naive fit treats the MC templates as exact; the Barlow-Beeston fit profiles one nuisance per bin "
                     "and template with a Poisson constraint from the MC count, so its errors include the template "
                     "statistics and are larger; errors are from a numerical Hessian (symmetric, unreliable at a boundary: "
                     "see at_boundary); templates are unweighted Poisson counts, a bin with no MC in any active template "
                     "cannot absorb data and makes that yield combination impossible, and the likelihood values of the two "
                     "fits are not comparable")}, [dn, db])


def _mad_width(v):
    if len(v) < 2:
        return None
    med = statistics.median(v)
    return 1.4826 * statistics.median([abs(x - med) for x in v])


def bb_toys(doc: dict, toys: int, seed: int) -> dict:
    names, data, m, mc = _load(doc)
    toys, seed = _toys(toys, 20), _seed(seed)
    true = doc.get("true_yields")
    if true is None:
        yb, _, _ = fit_yields(data, m, mc, "bb")
        true = {n: v for n, v in zip(names, yb)}
    if not isinstance(true, dict) or set(true) != set(names):
        raise ToyError("true_yields must give a yield for every template")
    y_true = [_num(true[n], f"true_yields {n}", 0.0, 1e6) for n in names]
    k, b = len(names), len(data)
    p = [[m[j][i] / mc[j] for i in range(b)] for j in range(k)]
    rng = random.Random(seed)
    res = {kind: [{"fits": [], "pulls": [], "cov": []} for _ in range(k)] for kind in ("naive", "barlow_beeston")}
    skipped = failed = 0
    for _ in range(toys):
        mt = [[poisson_draw(rng, mc[j] * p[j][i]) for i in range(b)] for j in range(k)]
        dt = [poisson_draw(rng, sum(y_true[j] * p[j][i] for j in range(k))) for i in range(b)]
        if any(sum(row) == 0 for row in mt) or sum(dt) == 0:
            skipped += 1
            continue
        yn, cn, _, dn = _fit_yields_full(dt, mt, mc, "naive")
        yb, cb, _, db = _fit_yields_full(dt, mt, mc, "bb", yn)
        if dn["outcome"] in FAILED_OUTCOMES or db["outcome"] in FAILED_OUTCOMES:
            failed += 1
            continue
        for kind, y, c in (("naive", yn, cn), ("barlow_beeston", yb, cb)):
            for j in range(k):
                res[kind][j]["fits"].append(y[j])
                if c is not None and c[j][j] > 0:
                    res[kind][j]["pulls"].append((y[j] - y_true[j]) / math.sqrt(c[j][j]))
    used = len(res["naive"][0]["fits"])
    if used < 10:
        raise ToyError("too few usable toys; increase the MC sizes or the data")
    out = {}
    for kind, rows in res.items():
        out[kind] = {names[j]: {"bias": statistics.fmean(r["fits"]) - y_true[j], "spread": _std(r["fits"]),
                                "mean_pull": statistics.fmean(r["pulls"]) if r["pulls"] else None,
                                "pull_width": _std(r["pulls"]) if len(r["pulls"]) > 1 else None,
                                "pull_width_robust_mad": _mad_width(r["pulls"]),
                                "fraction_without_error": 1.0 - len(r["pulls"]) / used,
                                "coverage_1sigma": (sum(abs(x) <= 1.0 for x in r["pulls"]) / len(r["pulls"])) if r["pulls"] else None}
                     for j, r in enumerate(rows)}
    return {"label": LABEL, "method": "multi-template fit toys: naive versus full Barlow-Beeston", "bins": b,
            "templates": names, "true_yields": dict(zip(names, y_true)), "toys_used": used, "toys_skipped_empty": skipped,
            "toys_failed_fit": failed, "seed": seed, "fits": out,
            "note": ("the supplied MC counts are taken as the true templates and redrawn each toy; a naive pull width above "
                     "1 with coverage below 0.68 and a Barlow-Beeston width and coverage near 1 and 0.68 are the evidence "
                     "that template statistics must be in the likelihood; pulls use the Hessian error, which is symmetric "
                     "and unreliable for a yield near zero (a few toys with a near-singular Hessian inflate the standard deviation of the pulls, so read the robust MAD width as well); a bias is not removed by the nuisances")}


# ------------------------------------------------------- weighted MC and nuisances
def _bfgs_min(f, x0, scales, max_iter: int = 200, info: dict | None = None):
    """BFGS with numerical central gradients in scaled variables u = x / scale; returns (x, f). When `info` is a
    dict it receives converged and termination (gradient, function-change, line-search-failed, max-iterations)."""
    n = len(x0)
    sc = list(scales)
    u = [x0[i] / sc[i] for i in range(n)]
    fu = lambda v: f([v[i] * sc[i] for i in range(n)])
    val = fu(u)
    hinv = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    def grad(v):
        g = []
        for i in range(n):
            h = 1e-5 * max(1.0, abs(v[i]))
            a, b = list(v), list(v)
            a[i] += h
            b[i] -= h
            g.append((fu(a) - fu(b)) / (2 * h))
        return g
    g = grad(u)
    term = "max-iterations"
    for _ in range(max_iter):
        if math.sqrt(sum(x * x for x in g)) < 1e-7:
            term = "gradient"
            break
        p = [-sum(hinv[i][j] * g[j] for j in range(n)) for i in range(n)]
        if sum(a * b for a, b in zip(p, g)) >= 0:
            hinv = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
            p = [-x for x in g]
        step, ok = 1.0, False
        for _t in range(60):
            cand = [u[i] + step * p[i] for i in range(n)]
            fc = fu(cand)
            if fc < val + 1e-4 * step * sum(a * b for a, b in zip(p, g)) and fc < 1e100:
                gn = grad(cand)
                if all(math.isfinite(x) and abs(x) < 1e50 for x in gn):
                    ok = True
                    break
            step *= 0.5
        if not ok:
            term = "line-search-failed"
            break
        s_ = [cand[i] - u[i] for i in range(n)]
        y_ = [gn[i] - g[i] for i in range(n)]
        sy = sum(a * b for a, b in zip(s_, y_))
        if sy > 1e-12:
            hy = [sum(hinv[i][j] * y_[j] for j in range(n)) for i in range(n)]
            yhy = sum(a * b for a, b in zip(y_, hy))
            hinv = [[hinv[i][j] + (sy + yhy) * s_[i] * s_[j] / sy ** 2 - (hy[i] * s_[j] + s_[i] * hy[j]) / sy for j in range(n)] for i in range(n)]
        done = abs(val - fc) < 1e-12 * (1.0 + abs(val))
        u, val, g = cand, fc, gn
        if done:
            term = "function-change"
            break
    if info is not None:
        ok = term in ("gradient", "function-change")
        if term == "line-search-failed":
            # the likelihood has kinks (piecewise-linear shape interpolation at theta = 0), where the line search stops at
            # a minimum with a non-zero one-sided gradient: accept it only if no coordinate step lowers the objective
            tol = 1e-9 * (1.0 + abs(val))
            ok = all(fu(u[:i] + [u[i] + d] + u[i + 1:]) >= val - tol for i in range(n) for d in (1e-4, -1e-4, 1e-2, -1e-2))
            term = "no-descent-direction" if ok else term
        info.update(converged=ok, termination=term)
    return [u[i] * sc[i] for i in range(n)], val


def _bb_bin_w(n, a, w, c, d=0.0):
    """Profiled per-bin log-likelihood of the weighted Barlow-Beeston model (constants dropped).
    nu = d + sum_j a_j * at_j with the profiled true weight sums at_j = w_j / (1 + c_j a_j t); d is the
    deterministic shape shift sum_j a_j * delta_j."""
    if not a:
        if d <= 0.0:
            return NEG if n > 0 else 0.0
        return (n * math.log(d) if n > 0 else 0.0) - d
    ca = max(c[j] * a[j] for j in range(len(a)))
    lo, hi = -1.0 / ca + 1e-12, 1.0
    t = 0.5 * (lo + hi)
    for _ in range(100):
        s = sum(a[j] * w[j] / (1.0 + c[j] * a[j] * t) for j in range(len(a))) + d
        sp = -sum(a[j] ** 2 * w[j] * c[j] / (1.0 + c[j] * a[j] * t) ** 2 for j in range(len(a)))
        g = (1.0 - t) * s - n
        gp = -s + (1.0 - t) * sp
        if g > 0:
            lo = t
        else:
            hi = t
        tn = t - g / gp if gp != 0 else 0.5 * (lo + hi)
        if not (lo < tn < hi):
            tn = 0.5 * (lo + hi)
        if abs(tn - t) < 1e-14 * (1.0 + abs(t)):
            t = tn
            break
        t = tn
    nuis = [w[j] / (1.0 + c[j] * a[j] * t) for j in range(len(a))]
    nu = d + sum(a[j] * nuis[j] for j in range(len(a)))
    if nu <= 0.0:
        return NEG if n > 0 else 0.0
    ll = (n * math.log(nu) if n > 0 else 0.0) - nu
    ll += sum((w[j] * math.log(nuis[j]) - nuis[j]) / c[j] for j in range(len(a)) if nuis[j] > 0)
    return ll


def _ll_w(data, w, t_tot, c, nuis, x, kind):
    """x = yields then nuisance values; kind 'naive' (templates exact) or 'bb' (finite-MC nuisances).
    The observed MC is the nominal sample w; a shape nuisance adds the deterministic shift
    theta * (up - w) (theta >= 0) or -theta * (down - w) (theta < 0) to the expected weight sum."""
    k, nth = len(w), len(nuis)
    y, th = x[:k], x[k:]
    if any(v <= 0 for v in y):
        return NEG
    a = [y[j] / t_tot[j] for j in range(k)]
    shift = [[0.0] * len(data) for _ in range(k)]
    for val, dsp in zip(th, nuis):
        j = dsp["j"]
        if dsp["kind"] == "shape":
            for i in range(len(data)):
                shift[j][i] += val * (dsp["up"][i] - w[j][i]) if val >= 0 else (-val) * (dsp["down"][i] - w[j][i])
        else:
            f = 1.0 + dsp["sigma"] * val
            if f <= 0:
                return NEG
            a[j] *= f
    total = -0.5 * sum(v * v for v in th)
    for i, n in enumerate(data):
        d = sum(a[j] * shift[j][i] for j in range(k))
        if kind == "naive":
            nu = d + sum(a[j] * w[j][i] for j in range(k))
            if nu <= 0:
                if n > 0:
                    return NEG
                continue
            total += (n * math.log(nu) if n > 0 else 0.0) - nu
        else:
            act = [j for j in range(k) if w[j][i] > 0 and a[j] > 0]
            val = _bb_bin_w(n, [a[j] for j in act], [w[j][i] for j in act], [c[j][i] for j in act], d)
            if val <= NEG / 2:
                return NEG
            total += val
    return total


def _load_w(doc):
    if not isinstance(doc, dict):
        raise ToyError("input must be a JSON object")
    data, tmpl = doc.get("data"), doc.get("templates")
    if not isinstance(data, list) or not 2 <= len(data) <= MAX_BINS:
        raise ToyError(f"data must be a list of 2 to {MAX_BINS} bin counts")
    data = [_num(v, "data", 0.0, 1e6) for v in data]
    if not isinstance(tmpl, dict) or not 1 <= len(tmpl) <= MAX_TEMPLATES:
        raise ToyError(f"templates must map 1 to {MAX_TEMPLATES} names to histograms")
    names, w, c = list(tmpl), [], []
    for nme in names:
        row = tmpl[nme]
        if isinstance(row, dict):
            sw, sw2 = row.get("sumw"), row.get("sumw2")
            if not isinstance(sw, list) or not isinstance(sw2, list) or len(sw) != len(data) or len(sw2) != len(data):
                raise ToyError(f"template {nme}: sumw and sumw2 must each list {len(data)} values")
            sw = [_num(v, f"{nme} sumw", 0.0, 1e9) for v in sw]
            sw2 = [_num(v, f"{nme} sumw2", 0.0, 1e12) for v in sw2]
            for a_, b_ in zip(sw, sw2):
                if (a_ > 0) != (b_ > 0):
                    raise ToyError(f"template {nme}: sumw2 must be positive exactly where sumw is")
        elif isinstance(row, list) and len(row) == len(data):
            sw = [_num(v, f"template {nme}", 0.0, 1e7) for v in row]
            sw2 = list(sw)
        else:
            raise ToyError(f"template {nme} must list {len(data)} counts or give sumw and sumw2")
        if sum(sw) <= 0:
            raise ToyError(f"template {nme} is empty")
        w.append(sw)
        c.append([(b_ / a_) if a_ > 0 else 1.0 for a_, b_ in zip(sw, sw2)])
    mce = doc.get("mc_events", {})
    t_tot = []
    for nme, row in zip(names, w):
        v = _num(mce.get(nme, sum(row)), f"mc_events {nme}", 0.0, 1e9, strict_low=True)
        if v < sum(row) - 1e-9 * max(1.0, v):
            raise ToyError(f"mc_events {nme} is below the sum of its template weights")
        t_tot.append(v)
    nuis = []
    raw = doc.get("nuisances", [])
    if not isinstance(raw, list) or len(raw) > 8:
        raise ToyError("nuisances must be a list of at most 8 entries")
    for k_, d in enumerate(raw):
        if not isinstance(d, dict) or d.get("kind") not in ("shape", "norm") or d.get("template") not in names:
            raise ToyError(f"nuisance {k_}: kind must be shape or norm and template one of {names}")
        j = names.index(d["template"])
        spec = {"kind": d["kind"], "j": j, "name": str(d.get("name", f"nuisance{k_}"))}
        if d["kind"] == "norm":
            spec["sigma"] = _num(d.get("sigma"), "sigma", 0.0, 0.9, strict_low=True)
        else:
            up, dn = d.get("up"), d.get("down")
            if not isinstance(up, list) or not isinstance(dn, list) or len(up) != len(data) or len(dn) != len(data):
                raise ToyError(f"nuisance {k_}: up and down must list {len(data)} per-bin weight sums")
            spec["up"] = [_num(v, "up", 0.0, 1e9) for v in up]
            spec["down"] = [_num(v, "down", 0.0, 1e9) for v in dn]
        nuis.append(spec)
    return names, data, w, c, t_tot, nuis


def _fit_w(data, w, t_tot, c, nuis, kind, start=None):
    """(yields, nuisance values, yield covariance or None, ll); _fit_w_full adds the diagnostics."""
    return _fit_w_full(data, w, t_tot, c, nuis, kind, start)[:4]


def _fit_w_full(data, w, t_tot, c, nuis, kind, start=None):
    k, nth = len(w), len(nuis)
    # nominal start: Nelder-Mead on the yields with the nuisances fixed at zero
    total = max(sum(data), 1.0)
    x0 = list(start) if start else [total / k] * k
    neg = lambda x: -_ll_w(data, w, t_tot, c, nuis, [max(v, 1e-9) for v in x] + [0.0] * nth, kind)
    i1, i2, i3 = {}, {}, {}
    x, _ = _nelder_mead(neg, x0, [0.3 * max(v, 1.0) for v in x0], info=i1)
    x, _ = _nelder_mead(neg, x, [0.05 * max(v, 1.0) for v in x], info=i2)
    y0 = [max(v, 1e-9) for v in x]
    full0 = y0 + [0.0] * nth
    infos = [i1, i2]
    if nth:
        fneg = lambda x: -_ll_w(data, w, t_tot, c, nuis, x, kind) if min(x[:k]) > 0 else 1e300
        full, _ = _bfgs_min(fneg, full0, [max(abs(v), 1.0) for v in y0] + [1.0] * nth, info=i3)
        # the yields-only search is a start for the joint fit; only the joint fit's convergence counts
        infos = [i3]
    else:
        full = full0
    ll = lambda z: _ll_w(data, w, t_tot, c, nuis, z, kind)
    inv = _hessian_cov(ll, full)
    cov = [row[:k] for row in inv[:k]] if inv is not None else None
    llv = ll(full)
    unsupported = [i for i, n in enumerate(data) if n > 0 and all(row[i] <= 0 for row in w)
                   and not any(d["kind"] == "shape" and d["up"][i] + d["down"][i] > 0 for d in nuis)]
    return full[:k], full[k:], cov, llv, _diagnostics(infos, llv, cov, full[:k], unsupported)


def wbb_fit(doc: dict) -> dict:
    names, data, w, c, t_tot, nuis = _load_w(doc)
    yn, thn, cn, _, dn = _fit_w_full(data, w, t_tot, c, nuis, "naive")
    yb, thb, cb, _, db = _fit_w_full(data, w, t_tot, c, nuis, "bb", yn)
    rn, rb = _report(names, yn, cn, dn), _report(names, yb, cb, db)
    infl = {nme: (rb[nme]["error"] / rn[nme]["error"] if rb[nme]["error"] and rn[nme]["error"] else None) for nme in names}
    return _overall({"label": LABEL, "method": "weighted-MC extended Poisson fit with shape and normalization nuisances: naive versus full Barlow-Beeston",
            "bins": len(data), "templates": names, "nuisances": [d["name"] for d in nuis],
            "naive": rn, "barlow_beeston": rb, "error_inflation_bb_over_naive": infl,
            "nuisance_values_naive": dict(zip([d["name"] for d in nuis], thn)),
            "nuisance_values_barlow_beeston": dict(zip([d["name"] for d in nuis], thb)),
            "note": ("weighted MC is treated by effective counts per bin and template (m_eff = (sum w)^2 / sum w^2, scale "
                     "c = sum w^2 / sum w), which is exact for equal weights in a bin and an approximation otherwise, and the "
                     "per-bin nuisance constraint is the matching scaled-Poisson term; shape nuisances morph the per-bin weight "
                     "sums linearly between the down, nominal and up templates with the squared-weight sums held at nominal; "
                     "normalization nuisances scale a template's yield per unit weight linearly; all nuisances have a unit "
                     "Gaussian constraint and are profiled with the yields; errors are the yield block of the inverse "
                     "numerical Hessian of the full parameter vector (symmetric, unreliable near a boundary)")}, [dn, db])


def wbb_toys(doc: dict, toys: int, seed: int) -> dict:
    names, data, w, c, t_tot, nuis = _load_w(doc)
    toys, seed = _toys(toys, 20), _seed(seed)
    true = doc.get("true_yields")
    if true is None:
        yb, _, _, _ = _fit_w(data, w, t_tot, c, nuis, "bb")
        true = dict(zip(names, yb))
    if not isinstance(true, dict) or set(true) != set(names):
        raise ToyError("true_yields must give a yield for every template")
    y_true = [_num(true[n], f"true_yields {n}", 0.0, 1e6) for n in names]
    k, b = len(names), len(data)
    eff = [[(w[j][i] / c[j][i]) if w[j][i] > 0 else 0.0 for i in range(b)] for j in range(k)]
    p = [[w[j][i] / t_tot[j] for i in range(b)] for j in range(k)]
    rng = random.Random(seed)
    res = {kind: [{"fits": [], "pulls": []} for _ in range(k)] for kind in ("naive", "barlow_beeston")}
    skipped = failed = 0
    for _ in range(toys):
        mt = [[c[j][i] * poisson_draw(rng, eff[j][i]) for i in range(b)] for j in range(k)]
        dt = [poisson_draw(rng, sum(y_true[j] * p[j][i] for j in range(k))) for i in range(b)]
        if any(sum(row) == 0 for row in mt) or sum(dt) == 0:
            skipped += 1
            continue
        w2 = [[c[j][i] * mt[j][i] for i in range(b)] for j in range(k)]  # sum of squared weights = c * sumw
        # the toy MC keeps the nominal c, so sumw2 / sumw = c and the total weight T is unchanged
        wt = mt
        yn, _, cn, _, dn = _fit_w_full(dt, wt, t_tot, c, nuis, "naive")
        yb, _, cb, _, db = _fit_w_full(dt, wt, t_tot, c, nuis, "bb", yn)
        if dn["outcome"] in FAILED_OUTCOMES or db["outcome"] in FAILED_OUTCOMES:
            failed += 1
            continue
        for kind, y, cv in (("naive", yn, cn), ("barlow_beeston", yb, cb)):
            for j in range(k):
                res[kind][j]["fits"].append(y[j])
                if cv is not None and cv[j][j] > 0:
                    res[kind][j]["pulls"].append((y[j] - y_true[j]) / math.sqrt(cv[j][j]))
    used = len(res["naive"][0]["fits"])
    if used < 10:
        raise ToyError("too few usable toys; increase the MC sizes or the data")
    out = {}
    for kind, rows in res.items():
        out[kind] = {names[j]: {"bias": statistics.fmean(r["fits"]) - y_true[j], "spread": _std(r["fits"]),
                                "mean_pull": statistics.fmean(r["pulls"]) if r["pulls"] else None,
                                "pull_width_robust_mad": _mad_width(r["pulls"]),
                                "coverage_1sigma": (sum(abs(x) <= 1.0 for x in r["pulls"]) / len(r["pulls"])) if r["pulls"] else None}
                     for j, r in enumerate(rows)}
    return {"label": LABEL, "method": "weighted-MC fit toys with nuisances: naive versus full Barlow-Beeston", "bins": b,
            "templates": names, "nuisances": [d["name"] for d in nuis], "true_yields": dict(zip(names, y_true)),
            "toys_used": used, "toys_skipped_empty": skipped, "toys_failed_fit": failed, "seed": seed, "fits": out,
            "note": ("toy MC is redrawn as scaled Poisson counts: the effective count of each bin and template is Poisson and "
                     "the scale c = sum w^2 / sum w is kept at its nominal value (so weight fluctuations inside a bin are not "
                     "simulated); data are drawn at the true yields with every nuisance at zero, so a pull width above 1 for "
                     "the fit with nuisances would indicate over-constraint rather than a missing systematic; the "
                     "robust MAD width is the one to read when a few toys have a near-singular Hessian")}


# --------------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("bb-fit", help="naive versus Barlow-Beeston fit of the supplied data")
    a.add_argument("--input", required=True)
    b = sub.add_parser("bb-toys", help="seeded toys comparing the two fits")
    b.add_argument("--input", required=True)
    b.add_argument("--toys", type=int, default=200)
    b.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    c = sub.add_parser("wbb-fit", help="weighted-MC fit with nuisances: naive versus full Barlow-Beeston")
    c.add_argument("--input", required=True)
    d = sub.add_parser("wbb-toys", help="seeded toys for the weighted-MC fit with nuisances")
    d.add_argument("--input", required=True)
    d.add_argument("--toys", type=int, default=100)
    d.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        try:
            doc = json.loads(Path(args.input).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ToyError(f"cannot read {args.input}: {exc}") from None
        if args.command == "wbb-fit":
            result = wbb_fit(doc)
        elif args.command == "wbb-toys":
            result = wbb_toys(doc, args.toys, args.seed)
        else:
            result = bb_fit(doc) if args.command == "bb-fit" else bb_toys(doc, args.toys, args.seed)
    except ToyError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    result.setdefault("status", "ok")  # the fits set ok or failed; toy studies report failed toys as a count
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
