#!/usr/bin/env python3
"""Seeded unfolding diagnostics for small response matrices (approximations).

Purpose: give the "regularization is a bias-variance choice, validate it" rules an executable
form: regularized (Tikhonov, truncated-SVD) scans, closure and pull tests, a forward-folding
versus unfold-then-fit comparison, and the effect of finite Monte Carlo statistics in the
response matrix. This is not an unfolding package: matrices are small (at most 60 bins), the
data are independent Poisson counts, the response is a probability matrix with inefficiency
outside it (the convention of core/stats/validate_response.py), and no systematic is modeled.
Output is labeled [General method]; nothing here is the performance of any experiment. Seed, toy count and
configuration are echoed.

Methods (--method, --param): `dagostini` (iterations; nonlinear, so spread comes from toys),
`tikhonov` (second-difference penalty; strength relative to the mean diagonal of R^T W^2 R)
and `tsvd` (number of retained singular values of the Poisson-weighted response). The linear
methods have analytic bias and covariance (bias = A mu - truth, cov = A diag(mu) A^T).

Subcommands:
  regularized-scan  bias, spread and adjacent-bin correlation per regularization setting.
  closure           noise-free closure (model dependence) and seeded pulls for one setting.
  fold-compare      power-law spectrum fit by forward folding versus unfold-then-fit.
  response-stat     spread from data statistics, from finite response (MC) statistics, both.
  choose-regularization
                    L-curve corner and cross-validation (leave-one-bin-out and generalized) choice of
                    the strength or truncation for given data, with a seeded-toy check of how well each
                    criterion picks a setting compared with the best fixed one.
  response-measured
                    first-order propagation of a supplied (measured) response-matrix covariance, or of
                    response replicas (for example a bootstrap of the MC), with a direct replica check.
  response-covariance
                    first-order (analytic) propagation of the finite-MC response uncertainty and of
                    the data statistics into the unfolded covariance, cross-checked against toys.
  compare-fold-priors
                    compare forward-folding smoothness priors (log_curvature, log_slope, entropy,
                    curvature, none) on the same seeded toys.
  choose-penalty-poisson
                    Poisson-exact leave-one-bin-out cross-validation of the forward-fold penalty
                    strength, with a toy comparison against the best fixed strength.
  nonparam-fold     non-parametric forward folding: penalized Poisson maximum likelihood of the
                    truth bins (log-curvature penalty) with a Laplace covariance, against a Tikhonov
                    unfolding.

Input JSON (shared): {"response": [[...]], "orientation": "rows_reco_cols_truth" (default) |
"rows_truth_cols_reco", "truth": [expected truth counts], "prior": [...] (optional start shape for
dagostini)}; closure also "test_truth": [...]; fold-compare also "truth_edges": [n_truth + 1
increasing positive edges] and "model": {"gamma": 2.7}  (the truth is then the power law with
the total of "truth"); response-stat also "mc_events_per_truth_bin": [...]; choose-regularization also "data": [measured counts] (else a seeded
pseudo-dataset from the truth is used and said so); response-covariance also "efficiency_uncertainty":
{"sigma": 0.02 or [per truth bin], "correlation": {"kind": "full" | "none" | "exponential", "length": 2}};
response-measured needs "response_covariance" (cells x cells, row-major (reco, truth) order) or
"response_replicas" (a list of response matrices in the same orientation as "response").

Usage (from the skill directory):
  python3 core/stats/unfolding_diagnostics.py regularized-scan --input u.json --method tikhonov --seed 1
  python3 core/stats/unfolding_diagnostics.py closure --input u.json --method tsvd --param 3 --toys 500 --seed 1
  python3 core/stats/unfolding_diagnostics.py fold-compare --input u.json --method tikhonov --param 0.01 --toys 300 --seed 1
  python3 core/stats/unfolding_diagnostics.py response-stat --input u.json --method dagostini --param 4 --toys 300 --seed 1
  python3 core/stats/unfolding_diagnostics.py choose-regularization --input u.json --method tikhonov --toys 200 --seed 1
  python3 core/stats/unfolding_diagnostics.py response-covariance --input u.json --method tikhonov --param 0.001 --response-model multinomial --toys 200 --seed 1
  python3 core/stats/unfolding_diagnostics.py response-measured --input u_cov.json --method tikhonov --param 0.001
  python3 core/stats/unfolding_diagnostics.py nonparam-fold --input u.json --tau 0.1 --prior entropy --toys 100 --seed 1
  python3 core/stats/unfolding_diagnostics.py compare-fold-priors --input u.json --priors log_curvature:0.1,entropy:0.01 --toys 100 --seed 1
  python3 core/stats/unfolding_diagnostics.py choose-penalty-poisson --input u.json --toys 40 --seed 1
Exit codes: 0 ok; 2 rejected input. Standard library only.
Importable: regularized_scan, closure, fold_compare, response_stat, linear_matrix, choose_regularization,
response_covariance, nonparam_fold, compare_fold_priors, choose_penalty_poisson, response_measured.
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
import sys
from pathlib import Path

from core.stats._linalg import cholesky, jacobi_eigh, matmul, solve, transpose
from core.stats.statistical_toys import (ToyError, _load_response, _num, _scan_then_golden, _seed, _std, _toys, _unfold,
                              poisson_draw)

LABEL = "[General method]"
METHODS = ("dagostini", "tikhonov", "tsvd")


# ------------------------------------------------------------------ small linear algebra (core/stats/_linalg.py)
_matmul, _transpose = matmul, transpose


def _solve(a, b):
    return solve(a, b, error=ToyError, what="matrix in the regularized solve")


def _jacobi(a, sweeps: int = 80):
    """Eigen-decomposition of a symmetric matrix: (eigenvalues, eigenvector columns); refuses an unconverged one."""
    info: dict = {}
    vals, vecs = jacobi_eigh(a, sweeps, criterion="diagonal", sort=False, info=info)
    if not info["converged"]:
        raise ToyError(f"the eigen-decomposition did not converge in {sweeps} sweeps (off-diagonal norm "
                       f"{info['off_diagonal']:.3e}); the singular values would be wrong")
    return vals, vecs


# -------------------------------------------------------------------------------- methods
def _check_method(method, param, n_truth):
    if method not in METHODS:
        raise ToyError(f"method must be one of {METHODS}")
    p = _num(param, "param", 0.0)
    if method == "dagostini":
        if p != int(p) or not 1 <= p <= 200:
            raise ToyError("dagostini param is an iteration count in [1, 200]")
    elif method == "tsvd":
        if p != int(p) or not 1 <= p <= n_truth:
            raise ToyError(f"tsvd param is a number of singular values in [1, {n_truth}]")
    elif p <= 0:
        raise ToyError("tikhonov param (relative strength) must be > 0")
    return int(p) if method != "tikhonov" else p


def linear_matrix(method: str, param, r, mu_w) -> list[list[float]]:
    """Unfolding matrix A (n_truth x n_reco) of a linear method; weights W^2 = 1 / max(mu_w, 1)."""
    n_reco, n_truth = len(r), len(r[0])
    w = [1.0 / math.sqrt(max(m, 1.0)) for m in mu_w]
    b = [[w[i] * r[i][j] for j in range(n_truth)] for i in range(n_reco)]  # W R
    bt = _transpose(b)
    btb = _matmul(bt, b)
    wt = [[w[i] if k == i else 0.0 for k in range(n_reco)] for i in range(n_reco)]
    if method == "tikhonov":
        scale = param * sum(btb[j][j] for j in range(n_truth)) / n_truth
        if n_truth >= 3:
            rows = [[(1.0 if j == i else -2.0 if j == i + 1 else 1.0 if j == i + 2 else 0.0) for j in range(n_truth)]
                    for i in range(n_truth - 2)]
            ltl = _matmul(_transpose(rows), rows)
        else:
            ltl = [[1.0 if i == j else 0.0 for j in range(n_truth)] for i in range(n_truth)]
        m = [[btb[i][j] + scale * ltl[i][j] for j in range(n_truth)] for i in range(n_truth)]
        return _matmul(_solve(m, bt), wt)
    vals, vecs = _jacobi(btb)
    order = sorted(range(n_truth), key=lambda i: -vals[i])
    a = [[0.0] * n_reco for _ in range(n_truth)]
    kept = 0
    for idx in order[:param]:
        if vals[idx] <= 1e-12 * vals[order[0]]:
            continue
        sigma = math.sqrt(vals[idx])
        vk = [vecs[j][idx] for j in range(n_truth)]
        uk = [sum(b[i][j] * vk[j] for j in range(n_truth)) / sigma for i in range(n_reco)]
        for j in range(n_truth):
            for i in range(n_reco):
                a[j][i] += vk[j] * uk[i] / sigma
        kept += 1
    if kept == 0:
        raise ToyError("no usable singular values")
    return _matmul(a, wt)


def _estimator(method, param, r, mu_w, prior):
    """counts -> unfolded truth estimate."""
    n_reco, n_truth = len(r), len(r[0])
    if method == "dagostini":
        eff = [sum(r[i][j] for i in range(n_reco)) for j in range(n_truth)]
        base = prior if prior is not None else [1.0] * n_truth
        norm = sum(sum(r[i][j] * base[j] for j in range(n_truth)) for i in range(n_reco))

        def run(counts):
            scale = sum(counts) / norm if norm > 0 else 1.0
            return _unfold(counts, r, eff, [v * scale for v in base], param)[-1]
        return run, None
    a = linear_matrix(method, param, r, mu_w)
    return (lambda counts: [sum(a[j][i] * counts[i] for i in range(n_reco)) for j in range(n_truth)]), a


def _mu(r, t):
    return [sum(row[j] * t[j] for j in range(len(t))) for row in r]


def _cov(a, mu):
    n_t, n_r = len(a), len(a[0])
    return [[sum(a[j][i] * a[k][i] * mu[i] for i in range(n_r)) for k in range(n_t)] for j in range(n_t)]


def _rms(v):
    return math.sqrt(sum(x * x for x in v) / len(v)) if v else 0.0


def _unpack(doc, method, param):
    r, truth, prior, _ = _load_response(dict(doc, max_iterations=doc.get("max_iterations", 1)))
    return r, truth, prior, _check_method(method, param, len(r[0]))


# ------------------------------------------------------------------ regularized-scan
def regularized_scan(doc: dict, method: str, values, toys: int, seed: int) -> dict:
    if method not in ("tikhonov", "tsvd"):
        raise ToyError("regularized-scan supports tikhonov and tsvd (use unfold-scan in statistical_toys.py for dagostini)")
    r, truth, prior, _ = _unpack(doc, method, 1.0 if method == "tikhonov" else 1)
    n_truth = len(truth)
    if values is None:
        values = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0] if method == "tikhonov" else list(range(1, n_truth + 1))
    if not isinstance(values, list) or not 1 <= len(values) <= 60:
        raise ToyError("values must be a list of 1 to 60 settings")
    toys, seed = _toys(toys, 20), _seed(seed)
    mu = _mu(r, truth)
    used = [j for j in range(n_truth) if truth[j] > 0]
    rows = []
    for v in values:
        p = _check_method(method, v, n_truth)
        a = linear_matrix(method, p, r, mu)
        est = [sum(a[j][i] * mu[i] for i in range(len(mu))) for j in range(n_truth)]
        cov = _cov(a, mu)
        bias = [(est[j] - truth[j]) / truth[j] for j in used]
        spread = [math.sqrt(max(cov[j][j], 0.0)) / truth[j] for j in used]
        adj = [cov[j][j + 1] / math.sqrt(cov[j][j] * cov[j + 1][j + 1]) for j in range(n_truth - 1)
               if cov[j][j] > 0 and cov[j + 1][j + 1] > 0]
        rng = random.Random(seed)
        neg = 0
        for _ in range(toys):
            n = [poisson_draw(rng, m) for m in mu]
            neg += any(sum(a[j][i] * n[i] for i in range(len(n))) < 0 for j in range(n_truth))
        rows.append({"setting": p, "rms_relative_bias": _rms(bias), "rms_relative_spread": _rms(spread),
                     "rms_relative_total": math.sqrt(_rms(bias) ** 2 + _rms(spread) ** 2),
                     "min_adjacent_correlation": min(adj) if adj else None,
                     "fraction_toys_with_a_negative_bin": neg / toys})
    best = min(rows, key=lambda x: x["rms_relative_total"])
    return {"label": LABEL, "method": f"{method} regularized unfolding scan (analytic bias and covariance)",
            "bins_truth": n_truth, "bins_reco": len(r), "toys": toys, "seed": seed, "scan": rows,
            "minimum_total_at_setting": best["setting"],
            "note": ("bias is against the truth you supplied, which also sets the weights, so the scan is circular: "
                     "repeat with a different truth (closure) before choosing a strength; a strong negative adjacent "
                     "correlation is the signature of too weak a regularization; linear solutions can be negative "
                     "in a bin; the covariance is the Poisson propagation only (no response statistics, no "
                     "systematics), and the regularization strength is relative to the mean diagonal of R^T W^2 R")}


# -------------------------------------------------------------------------------- closure
def closure(doc: dict, method: str, param, toys: int, seed: int) -> dict:
    r, truth, prior, p = _unpack(doc, method, param)
    test = doc.get("test_truth", truth)
    if not isinstance(test, list) or len(test) != len(truth):
        raise ToyError(f"test_truth must list {len(truth)} expected counts")
    test = [_num(v, "test_truth", 0.0, 1e5) for v in test]
    toys, seed = _toys(toys, 50), _seed(seed)
    n_truth = len(truth)
    mu_model, mu_test = _mu(r, truth), _mu(r, test)
    est, a = _estimator(method, p, r, mu_model, prior)
    closure_x = est([float(m) for m in mu_test])
    rng = random.Random(seed)
    draws = [est([poisson_draw(rng, m) for m in mu_test]) for _ in range(toys)]
    used = [j for j in range(n_truth) if test[j] > 0]
    if a is not None:
        cov = _cov(a, mu_test)
        sigma = [math.sqrt(max(cov[j][j], 0.0)) for j in range(n_truth)]
        sigma_kind = "analytic Poisson propagation"
    else:
        sigma = [_std([d[j] for d in draws]) for j in range(n_truth)]
        sigma_kind = "spread of the toys (so the pull width is 1 by construction; read the mean pull)"
    bias = [closure_x[j] - test[j] for j in range(n_truth)]
    means = [sum(d[j] for d in draws) / toys for j in range(n_truth)]
    pull_mean = [(means[j] - test[j]) / sigma[j] if sigma[j] > 0 else 0.0 for j in used]
    pull_width = [_std([(d[j] - test[j]) / sigma[j] for d in draws]) for j in used if sigma[j] > 0]
    chi2 = sum((bias[j] / sigma[j]) ** 2 for j in used if sigma[j] > 0)
    return {"label": LABEL, "method": f"{method} closure and pull test (param {p})", "bins_truth": n_truth, "toys": toys,
            "seed": seed, "test_truth_differs_from_model": test != truth, "sigma_source": sigma_kind,
            "closure_relative_bias_per_bin": [bias[j] / test[j] for j in used],
            "closure_rms_relative_bias": _rms([bias[j] / test[j] for j in used]),
            "closure_bias_significance_chi2_over_bins": chi2 / len(used),
            "statistical_sigma_per_bin": [sigma[j] for j in used],
            "mean_pull_per_bin": pull_mean, "max_abs_mean_pull": max(abs(x) for x in pull_mean),
            "mean_pull_standard_error": 1.0 / math.sqrt(toys),
            "mean_pull_width": sum(pull_width) / len(pull_width) if pull_width else None,
            "note": ("the noise-free closure unfolds the expected measurement of test_truth with the response, prior and "
                     "weights of the model truth: a nonzero bias is model dependence, to be compared with the "
                     "statistical sigma (chi2 over bins near 0 means it is negligible, well above 1 means it is a "
                     "systematic to assign); the mean pull is the toy mean minus truth in units of the statistical "
                     "sigma, with standard error 1/sqrt(toys), so a mean pull beyond about 3 standard errors flags a bias, "
                     "and a bias of a few tenths of a sigma is a systematic to assign; a pull width above 1 means the quoted errors are too "
                     "small; the response is assumed exactly known and the efficiency exactly applied")}


# --------------------------------------------------------------------------- fold-compare
def _pl_weights(edges, gamma):
    def integral(lo, hi):
        return math.log(hi / lo) if abs(gamma - 1.0) < 1e-9 else (hi ** (1 - gamma) - lo ** (1 - gamma)) / (1 - gamma)
    w = [integral(edges[j], edges[j + 1]) for j in range(len(edges) - 1)]
    tot = sum(w)
    return [x / tot for x in w]


def fold_compare(doc: dict, method: str, param, toys: int, seed: int) -> dict:
    if method == "dagostini":
        raise ToyError("fold-compare supports tikhonov and tsvd (the covariance of the unfolded result must be known)")
    r, truth, prior, p = _unpack(doc, method, param)
    edges = doc.get("truth_edges")
    model = doc.get("model")
    if not isinstance(edges, list) or len(edges) != len(truth) + 1:
        raise ToyError(f"truth_edges must list {len(truth) + 1} edges")
    edges = [_num(e, "edge", 0.0, 1e9, strict_low=True) for e in edges]
    if any(edges[k + 1] <= edges[k] for k in range(len(edges) - 1)):
        raise ToyError("truth_edges must be increasing")
    if not isinstance(model, dict):
        raise ToyError('model must be {"gamma": value}')
    g_true = _num(model.get("gamma"), "model.gamma", -5.0, 12.0)
    toys, seed = _toys(toys, 20), _seed(seed)
    total = sum(truth)
    n_t = len(truth)
    t_true = [total * w for w in _pl_weights(edges, g_true)]
    mu = _mu(r, t_true)
    a = linear_matrix(method, p, r, mu)
    rng = random.Random(seed)
    fold_fit, unf_fit = [], []
    g_lo, g_hi = g_true - 3.0, g_true + 3.0
    for _ in range(toys):
        n = [poisson_draw(rng, m) for m in mu]
        if sum(n) == 0:
            continue
        cache = {}

        def u_of(g):
            if g not in cache:
                w = _pl_weights(edges, g)
                cache[g] = [sum(r[i][j] * w[j] for j in range(n_t)) for i in range(len(r))]
            return cache[g]

        def nll(g):
            u = u_of(g)
            if any(x <= 0 for x, c in zip(u, n) if c > 0):
                return 1e300
            return -(sum(c * math.log(x) for x, c in zip(u, n) if c > 0) - sum(n) * math.log(sum(u)))
        fold_fit.append(_scan_then_golden(nll, g_lo, g_hi))
        x = [sum(a[j][i] * n[i] for i in range(len(n))) for j in range(n_t)]
        cov = _cov(a, [max(c, 1) for c in n])
        ridge = 1e-9 * sum(cov[j][j] for j in range(n_t)) / n_t
        cinv = _solve([[cov[j][k] + (ridge if j == k else 0.0) for k in range(n_t)] for j in range(n_t)],
                      [[1.0 if j == k else 0.0 for k in range(n_t)] for j in range(n_t)])

        def chi2(g):
            w = _pl_weights(edges, g)
            cw = [sum(cinv[j][k] * w[k] for k in range(n_t)) for j in range(n_t)]
            num, den = sum(x[j] * cw[j] for j in range(n_t)), sum(w[j] * cw[j] for j in range(n_t))
            norm = num / den if den > 0 else 0.0
            res = [x[j] - norm * w[j] for j in range(n_t)]
            return sum(res[j] * sum(cinv[j][k] * res[k] for k in range(n_t)) for j in range(n_t))
        unf_fit.append(_scan_then_golden(chi2, g_lo, g_hi))
    if len(fold_fit) < 10:
        raise ToyError("too few usable toys; increase the counts")
    mean = lambda v: sum(v) / len(v)
    sf, su = _std(fold_fit), _std(unf_fit)
    return {"label": LABEL, "method": f"power-law index: forward folding versus {method} unfolding then chi2 fit (param {p})",
            "true_gamma": g_true, "toys_used": len(fold_fit), "seed": seed,
            "forward_fold_bias": mean(fold_fit) - g_true, "forward_fold_spread": sf,
            "unfold_then_fit_bias": mean(unf_fit) - g_true, "unfold_then_fit_spread": su,
            "spread_ratio_unfold_over_fold": su / sf if sf > 0 else None,
            "note": ("the forward fit maximizes the Poisson likelihood of the measured counts (normalization profiled) and "
                     "is the reference here; the unfold-then-fit result uses the unfolded vector and its Poisson "
                     "covariance (estimated from the observed counts) in a generalized chi2 fit; a bias or a spread "
                     "ratio above 1 for the unfolded route is the cost of regularization and of the covariance "
                     "estimate; the model is a pure power law whose true form is assumed known, so this isolates the "
                     "statistical and regularization cost and says nothing about model misspecification")}


# --------------------------------------------------------------------------- response-stat
RESPONSE_MODELS = ("poisson_cells", "multinomial")


def _binomial_draw(rng: random.Random, n: int, p: float) -> int:
    """Binomial variate: exact for n <= 2000, a rounded normal approximation above (small error when n p (1 - p) is large)."""
    if n <= 0 or p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    if n <= 2000:
        return sum(rng.random() < p for _ in range(n))
    return min(n, max(0, round(rng.gauss(n * p, math.sqrt(n * p * (1.0 - p))))))


def _multinomial_column(rng, n_events: int, probs):
    """Counts of n_events over the cells with probabilities probs plus a lost class (1 - sum)."""
    left, mass, out = n_events, 1.0, []
    for pr in probs:
        k = _binomial_draw(rng, left, min(pr / mass, 1.0)) if mass > 0 else 0
        out.append(k)
        left -= k
        mass -= pr
    return out


def _check_model(model):
    if model not in RESPONSE_MODELS:
        raise ToyError(f"response_model must be one of {RESPONSE_MODELS}")
    return model


def response_stat(doc: dict, method: str, param, toys: int, seed: int, response_model: str = "poisson_cells") -> dict:
    r, truth, prior, p = _unpack(doc, method, param)
    n_truth, n_reco = len(truth), len(r)
    if method == "tsvd" and n_truth > 20:
        raise ToyError("response-stat with tsvd is limited to 20 truth bins (a decomposition per toy)")
    gen = doc.get("mc_events_per_truth_bin")
    if not isinstance(gen, list) or len(gen) != n_truth:
        raise ToyError(f"mc_events_per_truth_bin must list {n_truth} generated-event counts")
    gen = [_num(g, "mc_events", 1.0, 1e5) for g in gen]
    toys, seed = _toys(toys, 20), _seed(seed)
    response_model = _check_model(response_model)
    mu = _mu(r, truth)
    est0, _ = _estimator(method, p, r, mu, prior)
    rng = random.Random(seed)
    data_only, resp_only, both = [], [], []
    for _ in range(toys):
        r2 = [[0.0] * n_truth for _ in range(n_reco)]
        for j in range(n_truth):
            if response_model == "multinomial":
                ks = _multinomial_column(rng, int(round(gen[j])), [r[i][j] for i in range(n_reco)])
                for i in range(n_reco):
                    r2[i][j] = ks[i] / round(gen[j])
            else:
                for i in range(n_reco):
                    r2[i][j] = poisson_draw(rng, gen[j] * r[i][j]) / gen[j]
        if any(sum(r2[i][j] for i in range(n_reco)) <= 0 for j in range(n_truth) if truth[j] > 0):
            continue
        est2, _ = _estimator(method, p, r2, mu, prior)
        n = [poisson_draw(rng, m) for m in mu]
        data_only.append(est0(n))
        resp_only.append(est2([float(m) for m in mu]))
        both.append(est2(n))
    if len(both) < 10:
        raise ToyError("too few usable toys; increase mc_events_per_truth_bin")
    used = [j for j in range(n_truth) if truth[j] > 0]

    def rel(vs):
        return _rms([_std([v[j] for v in vs]) / truth[j] for j in used])
    d, rs, b = rel(data_only), rel(resp_only), rel(both)
    return {"label": LABEL, "method": f"finite response statistics in {method} unfolding (param {p}), {response_model} model, seeded toys",
            "response_model": response_model, "toys_used": len(both), "seed": seed, "rms_relative_spread_data_only": d,
            "rms_relative_spread_response_only": rs, "rms_relative_spread_both": b,
            "quadrature_of_data_and_response": math.sqrt(d * d + rs * rs),
            "response_share_of_total_variance": rs * rs / (b * b) if b > 0 else None,
            "note": ("the response matrix is redrawn from the stated generated-event counts, either with independent Poisson "
                     "cells (poisson_cells, an approximation) or as a multinomial over the reco cells and a lost-event class "
                     "(multinomial, exact in the sampling and a rounded normal approximation for a column above 2000 events), "
                     "the unfolding then uses the "
                     "redrawn matrix as if it were exact; data-only and response-only spreads add in quadrature only "
                     "approximately because the two sources interact in the unfolding; a response share above a few "
                     "percent of the variance is the trigger to put response statistics in the uncertainty "
                     "(for example by repeating the unfolding with a bootstrap of the MC) or to enlarge the MC")}


# ------------------------------------------------------------------ choose-regularization
def _corner(values, rho, eta):
    """Index of maximum curvature of the log-log L-curve (discrete circle through three neighbors)."""
    pts = [(math.log(max(r, 1e-300)), math.log(max(e, 1e-300))) for r, e in zip(rho, eta)]
    best, kbest = None, None
    for k in range(1, len(pts) - 1):
        (x1, y1), (x2, y2), (x3, y3) = pts[k - 1], pts[k], pts[k + 1]
        area2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        d = math.dist(pts[k - 1], pts[k]) * math.dist(pts[k], pts[k + 1]) * math.dist(pts[k - 1], pts[k + 1])
        if d == 0:
            continue
        curv = abs(2.0 * area2) / d
        if best is None or curv > best:
            best, kbest = curv, k
    return kbest


def _criteria(a, r, mu_w, counts):
    """(residual norm, solution norm, GCV, leave-one-out CV) of a linear estimator A for given counts."""
    n_r, n_t = len(r), len(r[0])
    w = [1.0 / math.sqrt(max(m, 1.0)) for m in mu_w]
    x = [sum(a[j][i] * counts[i] for i in range(n_r)) for j in range(n_t)]
    fit = [sum(r[i][j] * x[j] for j in range(n_t)) for i in range(n_r)]
    res = [w[i] * (counts[i] - fit[i]) for i in range(n_r)]
    hat = [[sum(r[i][j] * a[j][k] for j in range(n_t)) for k in range(n_r)] for i in range(n_r)]
    tr = sum(hat[i][i] for i in range(n_r))
    rho = math.sqrt(sum(v * v for v in res))
    if n_t >= 3:
        eta = math.sqrt(sum((x[j] - 2 * x[j + 1] + x[j + 2]) ** 2 for j in range(n_t - 2)))
    else:
        eta = math.sqrt(sum(v * v for v in x))
    gcv = n_r * rho * rho / max(n_r - tr, 1e-9) ** 2
    loo = sum((res[i] / max(1.0 - hat[i][i], 1e-9)) ** 2 for i in range(n_r)) / n_r
    return rho, eta, gcv, loo, tr


def choose_regularization(doc: dict, method: str, values, toys: int, seed: int) -> dict:
    if method not in ("tikhonov", "tsvd"):
        raise ToyError("choose-regularization supports tikhonov and tsvd")
    r, truth, prior, _ = _unpack(doc, method, 1.0 if method == "tikhonov" else 1)
    n_truth, n_reco = len(truth), len(r)
    if values is None:
        values = [10.0 ** e for e in range(-6, 2)] if method == "tikhonov" else list(range(1, n_truth + 1))
    if not isinstance(values, list) or not 3 <= len(values) <= 60:
        raise ToyError("values must list 3 to 60 settings")
    toys, seed = _toys(toys, 20), _seed(seed)
    mu = _mu(r, truth)
    settings = [_check_method(method, v, n_truth) for v in values]
    mats = [linear_matrix(method, v, r, mu) for v in settings]
    data = doc.get("data")
    rng = random.Random(seed)
    if data is None:
        counts, data_kind = [poisson_draw(rng, m) for m in mu], "seeded pseudo-dataset drawn from the truth"
    else:
        if not isinstance(data, list) or len(data) != n_reco:
            raise ToyError(f"data must list {n_reco} counts")
        counts, data_kind = [_num(v, "data", 0.0, 1e6) for v in data], "supplied"
    rows = [_criteria(a, r, mu, counts) for a in mats]
    corner = _corner(settings, [x[0] for x in rows], [x[1] for x in rows])
    picks = {"gcv": min(range(len(rows)), key=lambda k: rows[k][2]), "loo_cv": min(range(len(rows)), key=lambda k: rows[k][3])}
    if corner is not None:
        picks["l_curve_corner"] = corner
    used = [j for j in range(n_truth) if truth[j] > 0]

    def err_of(a, cnt):
        x = [sum(a[j][i] * cnt[i] for i in range(n_reco)) for j in range(n_truth)]
        return _rms([(x[j] - truth[j]) / truth[j] for j in used])
    analytic = []
    for a in mats:
        est = [sum(a[j][i] * mu[i] for i in range(n_reco)) for j in range(n_truth)]
        cov = _cov(a, mu)
        analytic.append(math.sqrt(_rms([(est[j] - truth[j]) / truth[j] for j in used]) ** 2 +
                                  _rms([math.sqrt(max(cov[j][j], 0)) / truth[j] for j in used]) ** 2))
    best_fixed = min(range(len(settings)), key=lambda k: analytic[k])
    chosen = {name: [] for name in picks}
    errs = {name: [] for name in picks}
    fixed_errs = [[] for _ in mats]
    for _ in range(toys):
        cnt = [poisson_draw(rng, m) for m in mu]
        for k, a_k in enumerate(mats):
            fixed_errs[k].append(err_of(a_k, cnt))
        crit = [_criteria(a, r, mu, cnt) for a in mats]
        sel = {"gcv": min(range(len(crit)), key=lambda k: crit[k][2]), "loo_cv": min(range(len(crit)), key=lambda k: crit[k][3])}
        cn = _corner(settings, [x[0] for x in crit], [x[1] for x in crit])
        if cn is not None:
            sel["l_curve_corner"] = cn
        for name, k in sel.items():
            chosen[name].append(k)
            errs[name].append(err_of(mats[k], cnt))
    table = [{"setting": settings[k], "residual_norm": rows[k][0], "solution_roughness": rows[k][1],
              "gcv": rows[k][2], "loo_cv": rows[k][3], "effective_dof_trace_hat": rows[k][4],
              "analytic_rms_relative_error_vs_truth": analytic[k]} for k in range(len(settings))]
    fixed_mean = [sum(v) / len(v) for v in fixed_errs]
    best_toy = min(range(len(settings)), key=lambda k: fixed_mean[k])
    summary = {}
    for name in picks:
        if not chosen[name]:
            continue
        mean_err = sum(errs[name]) / len(errs[name])
        summary[name] = {"chosen_on_these_data": settings[picks[name]],
                         "toy_median_chosen_index": sorted(chosen[name])[len(chosen[name]) // 2],
                         "toy_median_chosen_setting": settings[sorted(chosen[name])[len(chosen[name]) // 2]],
                         "toy_mean_rms_relative_error": mean_err,
                         "excess_over_best_fixed_setting": mean_err / fixed_mean[best_toy] - 1.0}
    return {"label": LABEL, "method": f"{method} regularization choice by L-curve corner, GCV and leave-one-out CV",
            "bins_truth": n_truth, "bins_reco": n_reco, "data": data_kind, "toys": toys, "seed": seed,
            "settings": table, "best_fixed_setting_by_analytic_error": settings[best_fixed],
            "best_fixed_setting_by_toys": settings[best_toy], "toy_mean_rms_relative_error_best_fixed": fixed_mean[best_toy],
            "criteria": summary,
            "note": ("GCV and leave-one-out CV use the hat matrix of the Poisson-weighted linear estimator (exact leave-one-out "
                     "residuals for a linear smoother), the L-curve corner is the maximum curvature of log residual norm "
                     "against log curvature of the solution (a heuristic: it can pick no corner or a wrong one); the "
                     "'best fixed setting' and the excess error use the truth you supplied, which is circular for the "
                     "table but fair for the toy comparison of criteria on fresh data; weights are Gaussian (1/sqrt(mu)) "
                     "approximations to Poisson noise, and a criterion that systematically picks too weak a "
                     "regularization (large excess error, many negative bins) is the evidence to prefer another")}


# ------------------------------------------------------------------ response-covariance
def _numeric_jacobian(fn, x0, rel=1e-3, floor=1e-6):
    base = fn(x0)
    jac = []
    for i in range(len(x0)):
        h = rel * max(abs(x0[i]), floor)
        up, dn = list(x0), list(x0)
        up[i] += h
        dn[i] -= h
        fu, fd = fn(up), fn(dn)
        jac.append([(fu[k] - fd[k]) / (2 * h) for k in range(len(base))])
    return jac  # jac[param][output]


def _corr_matrix(spec, n):
    if spec is None:
        spec = {"kind": "full"}
    kind = spec.get("kind") if isinstance(spec, dict) else None
    if kind == "full":
        return [[1.0] * n for _ in range(n)]
    if kind == "none":
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    if kind == "exponential":
        length = _num(spec.get("length"), "correlation.length", 0.0, 1000.0, strict_low=True)
        return [[math.exp(-abs(i - j) / length) for j in range(n)] for i in range(n)]
    raise ToyError("correlation.kind must be full, none or exponential")


def _setup_response(doc, method, param, need_gen=True):
    r, truth, prior, p = _unpack(doc, method, param)
    n_truth, n_reco = len(truth), len(r)
    if method == "tsvd" and max(n_truth, n_reco) > 15:
        raise ToyError("this diagnostic with tsvd is limited to 15 bins (a decomposition per Jacobian column)")
    if n_truth * n_reco > 400:
        raise ToyError("this diagnostic is limited to 400 response cells")
    gen = None
    if need_gen:
        gen = doc.get("mc_events_per_truth_bin")
        if not isinstance(gen, list) or len(gen) != n_truth:
            raise ToyError(f"mc_events_per_truth_bin must list {n_truth} generated-event counts")
        gen = [_num(g, "mc_events", 1.0, 1e5) for g in gen]
    mu = _mu(r, truth)
    flat = [r[i][j] for i in range(n_reco) for j in range(n_truth)]

    def est_from_R(vec, counts):
        rr = [[vec[i * n_truth + j] for j in range(n_truth)] for i in range(n_reco)]
        est, _ = _estimator(method, p, rr, mu, prior)
        return est(counts)
    return r, truth, prior, p, gen, mu, flat, est_from_R


def _data_cov(r, truth, method, p, mu, prior):
    n_truth, n_reco = len(truth), len(r)
    est0, a_lin = _estimator(method, p, r, mu, prior)
    if a_lin is not None:
        return _cov(a_lin, mu)
    jac_n = _numeric_jacobian(est0, [float(m) for m in mu], 1e-3, 1.0)
    return [[sum(jac_n[i][a] * jac_n[i][b] * mu[i] for i in range(n_reco)) for b in range(n_truth)] for a in range(n_truth)]


def _quad(jac, cov_cells, n_truth):
    """J^T C J for a full cell covariance: jac[cell][truth]."""
    n_c = len(jac)
    tmp = [[sum(cov_cells[c][d] * jac[d][b] for d in range(n_c)) for b in range(n_truth)] for c in range(n_c)]
    return [[sum(jac[c][a] * tmp[c][b] for c in range(n_c)) for b in range(n_truth)] for a in range(n_truth)]


def response_covariance(doc: dict, method: str, param, toys: int, seed: int, response_model: str = "poisson_cells") -> dict:
    r, truth, prior, p, gen, mu, flat, est_from_R = _setup_response(doc, method, param)
    n_truth, n_reco = len(truth), len(r)
    response_model = _check_model(response_model)
    toys, seed = _toys(toys, 20), _seed(seed)
    jac_r = _numeric_jacobian(lambda v: est_from_R(v, [float(m) for m in mu]), flat, 1e-3, 1e-3)
    cov_resp = [[0.0] * n_truth for _ in range(n_truth)]
    for j in range(n_truth):
        cells = [i * n_truth + j for i in range(n_reco)]
        for ii, c in enumerate(cells):
            for kk, d in enumerate(cells):
                if response_model == "poisson_cells":
                    cv = flat[c] / gen[j] if ii == kk else 0.0
                else:
                    cv = ((flat[c] if ii == kk else 0.0) - flat[c] * flat[d]) / gen[j]
                if cv == 0.0:
                    continue
                for a in range(n_truth):
                    for b in range(n_truth):
                        cov_resp[a][b] += cv * jac_r[c][a] * jac_r[d][b]
    spec = doc.get("efficiency_uncertainty")
    cov_eff = None
    if spec is not None:
        if not isinstance(spec, dict):
            raise ToyError("efficiency_uncertainty must be an object with sigma and optional correlation")
        sg = spec.get("sigma")
        sg = [sg] * n_truth if isinstance(sg, (int, float)) and not isinstance(sg, bool) else sg
        if not isinstance(sg, list) or len(sg) != n_truth:
            raise ToyError(f"efficiency_uncertainty.sigma must be a number or a list of {n_truth} fractional values")
        sg = [_num(v, "efficiency sigma", 0.0, 0.9) for v in sg]
        rho = _corr_matrix(spec.get("correlation"), n_truth)
        jac_e = []
        for j in range(n_truth):
            up, dn = list(flat), list(flat)
            for i in range(n_reco):
                up[i * n_truth + j] *= 1.001
                dn[i * n_truth + j] *= 0.999
            fu, fd = est_from_R(up, [float(m) for m in mu]), est_from_R(dn, [float(m) for m in mu])
            jac_e.append([(fu[k] - fd[k]) / 0.002 for k in range(n_truth)])
        cov_eff = [[sum(sg[c] * sg[d] * rho[c][d] * jac_e[c][a] * jac_e[d][b] for c in range(n_truth) for d in range(n_truth))
                    for b in range(n_truth)] for a in range(n_truth)]
    cov_data = _data_cov(r, truth, method, p, mu, prior)
    used = [j for j in range(n_truth) if truth[j] > 0]
    rel = lambda cv: [math.sqrt(max(cv[j][j], 0.0)) / truth[j] for j in used]
    d_a, r_a = rel(cov_data), rel(cov_resp)
    parts = [cov_data, cov_resp] + ([cov_eff] if cov_eff is not None else [])
    tot = [[sum(pc[a][b] for pc in parts) for b in range(n_truth)] for a in range(n_truth)]
    t_a = rel(tot)
    toy = response_stat(doc, method, param, toys, seed, response_model)
    corr = [[cov_resp[a][b] / math.sqrt(cov_resp[a][a] * cov_resp[b][b]) if cov_resp[a][a] > 0 and cov_resp[b][b] > 0 else None
             for b in range(n_truth)] for a in range(n_truth)]
    out = {"label": LABEL, "method": f"first-order propagation of data and finite-response statistics ({response_model}) into {method} unfolding (param {p})",
           "response_model": response_model, "bins_truth": n_truth, "bins_reco": n_reco, "toys": toys, "seed": seed,
           "relative_sigma_data_per_bin": d_a, "relative_sigma_response_per_bin": r_a, "relative_sigma_total_per_bin": t_a,
           "rms_relative_data": _rms(d_a), "rms_relative_response": _rms(r_a), "rms_relative_total": _rms(t_a),
           "response_share_of_total_variance": _rms(r_a) ** 2 / _rms(t_a) ** 2 if _rms(t_a) > 0 else None,
           "response_covariance_correlation": corr,
           "toy_check": {"rms_relative_data_only": toy["rms_relative_spread_data_only"],
                         "rms_relative_response_only": toy["rms_relative_spread_response_only"],
                         "rms_relative_both": toy["rms_relative_spread_both"],
                         "analytic_over_toy_response": (_rms(r_a) / toy["rms_relative_spread_response_only"]
                                                        if toy["rms_relative_spread_response_only"] > 0 else None)}}
    if cov_eff is not None:
        e_a = rel(cov_eff)
        out["relative_sigma_efficiency_systematic_per_bin"] = e_a
        out["rms_relative_efficiency_systematic"] = _rms(e_a)
    out["note"] = ("the response statistical covariance is the first-order propagation, through a numerical Jacobian of the "
                   "estimator at the expected data, of either independent Poisson cells (Var R_ij = R_ij / gen_j) or the "
                   "exact multinomial with a lost-event class (Var R_ij = R_ij (1 - R_ij) / gen_j and, within one truth "
                   "column, Cov(R_ij, R_kj) = -R_ij R_kj / gen_j, so the efficiency fluctuation is included and the "
                   "independent-cell model overstates the variance of a column with a high efficiency); the nonlinear "
                   "D'Agostini estimator is supported, with its data covariance from the Jacobian with respect to the "
                   "counts; the weights of the linear methods are held fixed as in response-stat; an efficiency systematic "
                   "(efficiency_uncertainty: a fractional sigma per truth bin and a bin-to-bin correlation full, none or "
                   "exponential) scales whole response columns and is a declared input, not a statistical effect, added to "
                   "the total covariance; the analytic-over-toy ratio should be near 1 when response errors are small; use "
                   "the full covariance among truth bins, not only the diagonal, when fitting the unfolded result")
    return out


def response_measured(doc: dict, method: str, param) -> dict:
    r, truth, prior, p, _, mu, flat, est_from_R = _setup_response(doc, method, param, need_gen=False)
    n_truth, n_reco = len(truth), len(r)
    n_cells = n_truth * n_reco
    if n_cells > 225:
        raise ToyError("response-measured is limited to 225 response cells")
    cov_in, reps = doc.get("response_covariance"), doc.get("response_replicas")
    if (cov_in is None) == (reps is None):
        raise ToyError("give exactly one of response_covariance (cells x cells) or response_replicas (a list of response matrices)")
    replica_x, reg = None, None
    if reps is not None:
        if not isinstance(reps, list) or not 10 <= len(reps) <= 2000:
            raise ToyError("response_replicas must list 10 to 2000 response matrices")
        flats = []
        for k, m in enumerate(reps):
            if not isinstance(m, list) or len(m) != n_reco or any(not isinstance(row, list) or len(row) != n_truth for row in m):
                raise ToyError(f"replica {k} must be a {n_reco} x {n_truth} matrix")
            flats.append([_num(m[i][j], "replica entry", 0.0, 1.0) for i in range(n_reco) for j in range(n_truth)])
        n_rep = len(flats)
        means = [sum(f[c] for f in flats) / n_rep for c in range(n_cells)]
        cov_cells = [[sum((f[c] - means[c]) * (f[d] - means[d]) for f in flats) / (n_rep - 1) for d in range(n_cells)] for c in range(n_cells)]
        mu_f = [float(m) for m in mu]
        replica_x = [est_from_R(f, mu_f) for f in flats]
        source = f"{n_rep} response replicas"
    else:
        if not isinstance(cov_in, list) or len(cov_in) != n_cells or any(not isinstance(row, list) or len(row) != n_cells for row in cov_in):
            raise ToyError(f"response_covariance must be a {n_cells} x {n_cells} matrix over cells in row-major (reco, truth) order")
        cov_cells = [[_num(v, "response_covariance", -1e12, 1e12) for v in row] for row in cov_in]
        for c in range(n_cells):
            if cov_cells[c][c] < 0:
                raise ToyError("response_covariance must have non-negative diagonal entries")
            for d in range(c):
                if abs(cov_cells[c][d] - cov_cells[d][c]) > 1e-8 * math.sqrt(max(cov_cells[c][c] * cov_cells[d][d], 1e-300)) + 1e-14:
                    raise ToyError("response_covariance must be symmetric")
        reg = cholesky(cov_cells, "response_covariance", semidefinite=True, error=ToyError)[1]
        source = "supplied covariance"
    jac = _numeric_jacobian(lambda v: est_from_R(v, [float(m) for m in mu]), flat, 1e-3, 1e-3)
    cov_resp = _quad(jac, cov_cells, n_truth)
    cov_data = _data_cov(r, truth, method, p, mu, prior)
    used = [j for j in range(n_truth) if truth[j] > 0]
    rel = lambda cv: [math.sqrt(max(cv[j][j], 0.0)) / truth[j] for j in used]
    d_a, r_a = rel(cov_data), rel(cov_resp)
    tot = [[cov_data[a][b] + cov_resp[a][b] for b in range(n_truth)] for a in range(n_truth)]
    corr = [[cov_resp[a][b] / math.sqrt(cov_resp[a][a] * cov_resp[b][b]) if cov_resp[a][a] > 0 and cov_resp[b][b] > 0 else None
             for b in range(n_truth)] for a in range(n_truth)]
    out = {"label": LABEL, "method": f"propagation of a measured response-matrix covariance ({source}) into {method} unfolding (param {p})",
           "bins_truth": n_truth, "bins_reco": n_reco, "source": source,
           "relative_sigma_data_per_bin": d_a, "relative_sigma_response_per_bin": r_a, "relative_sigma_total_per_bin": rel(tot),
           "rms_relative_data": _rms(d_a), "rms_relative_response": _rms(r_a), "rms_relative_total": _rms(rel(tot)),
           "response_share_of_total_variance": _rms(r_a) ** 2 / _rms(rel(tot)) ** 2 if _rms(rel(tot)) > 0 else None,
           "response_covariance_correlation": corr}
    if reg:  # checked only, never factorized here: say it is singular, not that it was shifted
        out["response_covariance_check"] = {"positive_semi_definite": True, "singular_directions": reg["pivots_shifted"],
                                            "rel_tol": reg["rel_tol"]}
    if replica_x is not None:
        n_rep = len(replica_x)
        spread = [_std([x[j] for x in replica_x]) / truth[j] for j in used]
        nominal = est_from_R(flat, [float(m) for m in mu])
        shift = [(sum(x[j] for x in replica_x) / n_rep - nominal[j]) / truth[j] for j in used]
        out["replica_check"] = {"rms_relative_spread_replicas_direct": _rms(spread),
                                "analytic_over_replica": _rms(r_a) / _rms(spread) if _rms(spread) > 0 else None,
                                "rms_relative_shift_of_replica_mean_from_nominal": _rms(shift)}
    out["note"] = ("the covariance is propagated at first order through a numerical Jacobian of the estimator at the "
                   "expected data (the weights of the linear methods held fixed); a supplied covariance is checked only "
                   "for symmetry and positive semi-definiteness, over cells in row-major (reco, truth) order, and replicas "
                   "(for example from a bootstrap of the MC) give the covariance as their sample covariance and the "
                   "direct unfolding of every replica as a nonlinear cross-check (analytic over replica near 1 when the "
                   "response errors are small); a shift of the replica mean from the nominal result is a bias of the "
                   "nominal response, not a covariance; the data covariance is the Poisson propagation; no efficiency "
                   "systematic is added (see response-covariance)")
    return out


# ----------------------------------------------------------------------- nonparam-fold
PRIORS = ("log_curvature", "log_slope", "entropy", "curvature", "none")


def _diff_ltl(n, order):
    rows = ([[(1.0 if j == i else -2.0 if j == i + 1 else 1.0 if j == i + 2 else 0.0) for j in range(n)] for i in range(max(n - 2, 0))]
            if order == 2 else
            [[(-1.0 if j == i else 1.0 if j == i + 1 else 0.0) for j in range(n)] for i in range(max(n - 1, 0))])
    return _matmul(_transpose(rows), rows) if rows else [[0.0] * n for _ in range(n)]


def _penalty(kind, tau, phi, ltl1, ltl2, lnm, tbar):
    """(value, gradient, Hessian) of the penalty with respect to phi = ln t."""
    n = len(phi)
    zero = [[0.0] * n for _ in range(n)]
    if kind == "none":
        return 0.0, [0.0] * n, zero
    if kind in ("log_curvature", "log_slope"):
        a = ltl2 if kind == "log_curvature" else ltl1
        ap = [sum(a[i][j] * phi[j] for j in range(n)) for i in range(n)]
        return 0.5 * tau * sum(phi[i] * ap[i] for i in range(n)), [tau * v for v in ap], [[tau * a[i][j] for j in range(n)] for i in range(n)]
    t = [math.exp(v) for v in phi]
    if kind == "entropy":
        d = [phi[j] - lnm[j] for j in range(n)]
        val = tau * sum(t[j] * d[j] - t[j] + math.exp(lnm[j]) for j in range(n))
        h = [[(tau * t[j] * (d[j] + 1.0) if j == k else 0.0) for k in range(n)] for j in range(n)]
        return val, [tau * t[j] * d[j] for j in range(n)], h
    # curvature on the linear scale: tau/2 |L2 t|^2 / tbar^2
    sc = tau / (tbar * tbar)
    at = [sum(ltl2[i][j] * t[j] for j in range(n)) for i in range(n)]
    gt = [sc * v for v in at]
    h = [[t[j] * t[k] * sc * ltl2[j][k] + (t[j] * gt[j] if j == k else 0.0) for k in range(n)] for j in range(n)]
    return 0.5 * sc * sum(t[i] * at[i] for i in range(n)), [t[j] * gt[j] for j in range(n)], h


def _fold_fit(counts, r, tau, start=None, max_iter: int = 80, prior: str = "log_curvature", model=None, want_cov: bool = True):
    """Maximize sum(n ln nu - nu) - penalty over phi = ln t (Newton, Levenberg damping); returns (t, cov_t, ok)."""
    n_r, n_t = len(r), len(r[0])
    ltl1, ltl2 = _diff_ltl(n_t, 1), _diff_ltl(n_t, 2)
    tot_n = sum(counts)
    col = [sum(r[i][j] for i in range(n_r)) for j in range(n_t)]
    t0 = tot_n / max(sum(col), 1e-12)
    phi = [math.log(max(t0, 1e-6))] * n_t if start is None else [math.log(max(v, 1e-6)) for v in start]
    lnm = [math.log(max(v, 1e-12)) for v in (model if model is not None else [t0] * n_t)]

    def state(ph, need_hess=True):
        t = [math.exp(v) for v in ph]
        nu = [sum(r[i][j] * t[j] for j in range(n_t)) for i in range(n_r)]
        if any(v <= 0 for v in nu):
            return -1e300, None, None
        val_p, g_p, h_p = _penalty(prior, tau, ph, ltl1, ltl2, lnm, max(t0, 1e-12))
        ll = sum((c * math.log(v) if c > 0 else 0.0) - v for c, v in zip(counts, nu)) - val_p
        if not need_hess:
            return ll, None, None
        gj = [sum(r[i][j] * (counts[i] / nu[i] - 1.0) for i in range(n_r)) for j in range(n_t)]
        grad = [t[j] * gj[j] - g_p[j] for j in range(n_t)]
        hess = [[(t[j] * gj[j] if j == k else 0.0) - t[j] * t[k] * sum(r[i][j] * r[i][k] * counts[i] / nu[i] ** 2 for i in range(n_r))
                 - h_p[j][k] for k in range(n_t)] for j in range(n_t)]
        return ll, grad, hess
    lam = 1e-3
    f, grad, hess = state(phi)
    for _ in range(max_iter):
        done = False
        for _try in range(15):
            try:
                step = _solve([[-hess[a][b] + (lam * (1.0 + abs(hess[a][a])) if a == b else 0.0) for b in range(n_t)] for a in range(n_t)],
                              [[g] for g in grad])
            except ToyError:
                lam *= 10.0
                continue
            cand = [phi[a] + step[a][0] for a in range(n_t)]
            fc, gc, hc = state(cand)
            if fc > f:
                dx = max(abs(step[a][0]) for a in range(n_t))
                phi, f, grad, hess, lam, done = cand, fc, gc, hc, max(lam / 5.0, 1e-9), True
                break
            lam *= 10.0
        if not done or dx < 1e-9:
            break
    t = [math.exp(v) for v in phi]
    if not want_cov:
        return t, None, True
    try:
        cphi = _solve([[-hess[a][b] for b in range(n_t)] for a in range(n_t)], [[1.0 if a == b else 0.0 for b in range(n_t)] for a in range(n_t)])
        cov = [[t[a] * cphi[a][b] * t[b] for b in range(n_t)] for a in range(n_t)]
        ok = all(cov[a][a] > 0 for a in range(n_t))
    except ToyError:
        cov, ok = None, False
    return t, cov, ok


def _prior_args(doc, prior, truth):
    if prior not in PRIORS:
        raise ToyError(f"prior must be one of {PRIORS}")
    shape = doc.get("prior")
    if shape is not None and prior == "entropy":
        if not isinstance(shape, list) or len(shape) != len(truth) or min(shape) <= 0:
            raise ToyError("prior must list positive default-model values for the entropy penalty")
        return shape
    return None


def nonparam_fold(doc: dict, tau, compare_tau, toys: int, seed: int, prior: str = "log_curvature") -> dict:
    r, truth, prior_shape, _ = _unpack(doc, "tikhonov", 1.0)
    tau = _num(tau, "tau", 0.0, 1e6, strict_low=True)
    compare_tau = _check_method("tikhonov", compare_tau, len(truth))
    toys, seed = _toys(toys, 20), _seed(seed)
    n_t, n_r = len(truth), len(r)
    model_raw = _prior_args(doc, prior, truth)
    mu = _mu(r, truth)
    a = linear_matrix("tikhonov", compare_tau, r, mu)
    rng = random.Random(seed)
    fits, unf, laplace, fails = [], [], [], 0
    for _ in range(toys):
        n = [poisson_draw(rng, m) for m in mu]
        if sum(n) == 0:
            continue
        model = None if model_raw is None else [v * sum(n) / max(sum(sum(r[i][j] * model_raw[j] for j in range(n_t)) for i in range(n_r)), 1e-12) for v in model_raw]
        t, cov, ok = _fold_fit(n, r, tau, prior=prior, model=model)
        if not ok:
            fails += 1
            continue
        fits.append(t)
        laplace.append([math.sqrt(cov[j][j]) for j in range(n_t)])
        unf.append([sum(a[j][i] * n[i] for i in range(n_r)) for j in range(n_t)])
    if len(fits) < 10:
        raise ToyError("too few usable fits; increase the counts or the penalty strength")
    used = [j for j in range(n_t) if truth[j] > 0]
    mean = lambda v, j: sum(x[j] for x in v) / len(v)

    def summary(v):
        bias = [(mean(v, j) - truth[j]) / truth[j] for j in used]
        spread = [_std([x[j] for x in v]) / truth[j] for j in used]
        return _rms(bias), _rms(spread), math.sqrt(_rms(bias) ** 2 + _rms(spread) ** 2)
    fb, fs, ft = summary(fits)
    ub, us, ut = summary(unf)
    lap = [sum(x[j] for x in laplace) / len(laplace) / truth[j] for j in used]
    return {"label": LABEL, "method": f"non-parametric forward folding (penalized Poisson likelihood of the truth bins, prior {prior}) versus Tikhonov unfolding",
            "bins_truth": n_t, "bins_reco": n_r, "prior": prior, "tau": tau, "tikhonov_compare_strength": compare_tau, "toys_used": len(fits),
            "toys_failed": fails, "seed": seed,
            "forward_fold": {"rms_relative_bias": fb, "rms_relative_spread": fs, "rms_relative_total": ft,
                             "fraction_negative_bins": 0.0, "mean_laplace_relative_sigma": _rms(lap),
                             "laplace_over_toy_spread": _rms(lap) / fs if fs > 0 else None},
            "tikhonov_unfolding": {"rms_relative_bias": ub, "rms_relative_spread": us, "rms_relative_total": ut,
                                   "fraction_toys_with_a_negative_bin": sum(any(v < 0 for v in x) for x in unf) / len(unf)},
            "note": ("the truth bins are the parameters (log-parametrized so they stay positive); priors: log_curvature "
                     "(second difference of log t; exact for a power law, so it favors falling spectra), log_slope (first "
                     "difference of log t; favors a flat log spectrum, so it biases a steep one toward flatness), entropy "
                     "(tau sum t ln(t/m) - t + m toward a default model m, flat or the supplied prior shape rescaled to the "
                     "data total; biases toward m), curvature (second difference of t on the linear scale over the mean "
                     "level; favors a straight line in t), and none (an unpenalized maximum likelihood, which can be "
                     "unstable); tau is not comparable across priors or with the Tikhonov strength; the Laplace covariance "
                     "is the inverse penalized Hessian, a Gaussian approximation that the toy spread tests; bias is against "
                     "the supplied truth, so the comparison is circular for the penalty choice (see choose-penalty-poisson, "
                     "choose-regularization and closure); the response is exactly known and no systematic is modeled")}


def compare_fold_priors(doc: dict, specs, toys: int, seed: int) -> dict:
    if not isinstance(specs, list) or not 2 <= len(specs) <= 10:
        raise ToyError("priors must list 2 to 10 name:tau entries")
    rows = []
    for name, tau in specs:
        res = nonparam_fold(doc, tau, 0.01, toys, seed, name)
        ff = res["forward_fold"]
        rows.append({"prior": name, "tau": tau, "rms_relative_bias": ff["rms_relative_bias"], "rms_relative_spread": ff["rms_relative_spread"],
                     "rms_relative_total": ff["rms_relative_total"], "laplace_over_toy_spread": ff["laplace_over_toy_spread"],
                     "toys_failed": res["toys_failed"]})
    best = min(rows, key=lambda x: x["rms_relative_total"])
    return {"label": LABEL, "method": "comparison of forward-folding smoothness priors on the same toys", "toys": toys, "seed": seed,
            "priors": rows, "minimum_total": {"prior": best["prior"], "tau": best["tau"]},
            "note": ("every prior is run on the same seeded toys with the strength you give it, so the comparison mixes the "
                     "prior and its strength (strengths are not comparable across priors); bias is against the supplied "
                     "truth, which makes the ranking circular and favors the prior that matches the truth's shape; repeat "
                     "with a different truth and choose by closure or Poisson cross-validation rather than by this table")}


def choose_penalty_poisson(doc: dict, prior: str, taus, toys: int, seed: int) -> dict:
    r, truth, prior_shape, _ = _unpack(doc, "tikhonov", 1.0)
    n_t, n_r = len(truth), len(r)
    if n_r > 30:
        raise ToyError("choose-penalty-poisson is limited to 30 reco bins (a refit per left-out bin)")
    if taus is None:
        taus = [10.0 ** e for e in range(-4, 4)]
    if not isinstance(taus, list) or not 3 <= len(taus) <= 20:
        raise ToyError("taus must list 3 to 20 strengths")
    taus = [_num(v, "tau", 0.0, 1e6, strict_low=True) for v in taus]
    toys, seed = _toys(toys, 20), _seed(seed)
    model_raw = _prior_args(doc, prior, truth)
    mu = _mu(r, truth)
    rng = random.Random(seed)
    data = doc.get("data")
    if data is None:
        counts, data_kind = [poisson_draw(rng, m) for m in mu], "seeded pseudo-dataset drawn from the truth"
    else:
        if not isinstance(data, list) or len(data) != n_r:
            raise ToyError(f"data must list {n_r} counts")
        counts, data_kind = [_num(v, "data", 0.0, 1e6) for v in data], "supplied"
    used = [j for j in range(n_t) if truth[j] > 0]

    def model_for(cnt):
        if model_raw is None:
            return None
        return [v * sum(cnt) / max(sum(sum(r[i][j] * model_raw[j] for j in range(n_t)) for i in range(n_r)), 1e-12) for v in model_raw]

    def cv_score(cnt, tau, t_full):
        model = model_for(cnt)
        total = 0.0
        for i in range(n_r):
            r_sub = r[:i] + r[i + 1:]
            c_sub = cnt[:i] + cnt[i + 1:]
            t, _, _ = _fold_fit(c_sub, r_sub, tau, start=t_full, prior=prior, model=model, want_cov=False)
            nu = sum(r[i][j] * t[j] for j in range(n_t))
            if nu <= 0:
                return float("inf")
            total -= (cnt[i] * math.log(nu) if cnt[i] > 0 else 0.0) - nu - math.lgamma(cnt[i] + 1.0)
        return total

    def fit_all(cnt):
        out = []
        for tau in taus:
            t, _, _ = _fold_fit(cnt, r, tau, prior=prior, model=model_for(cnt), want_cov=False)
            out.append(t)
        return out
    fulls = fit_all(counts)
    scores = [cv_score(counts, tau, t) for tau, t in zip(taus, fulls)]
    err_of = lambda t: _rms([(t[j] - truth[j]) / truth[j] for j in used])
    chosen_idx, chosen_err = [], []
    fixed_err = [[] for _ in taus]
    for _ in range(toys):
        cnt = [poisson_draw(rng, m) for m in mu]
        if sum(cnt) == 0:
            continue
        fl = fit_all(cnt)
        sc = [cv_score(cnt, tau, t) for tau, t in zip(taus, fl)]
        k = min(range(len(taus)), key=lambda q: sc[q])
        chosen_idx.append(k)
        chosen_err.append(err_of(fl[k]))
        for q, t in enumerate(fl):
            fixed_err[q].append(err_of(t))
    if len(chosen_idx) < 10:
        raise ToyError("too few usable toys")
    fixed_mean = [sum(v) / len(v) for v in fixed_err]
    best_fixed = min(range(len(taus)), key=lambda q: fixed_mean[q])
    mean_err = sum(chosen_err) / len(chosen_err)
    srt = sorted(chosen_idx)
    return {"label": LABEL, "method": f"Poisson-exact leave-one-bin-out cross-validation of the {prior} penalty strength",
            "bins_truth": n_t, "bins_reco": n_r, "prior": prior, "data": data_kind, "toys_used": len(chosen_idx), "seed": seed,
            "scan": [{"tau": tau, "cv_negative_log_likelihood": sc, "full_fit_rms_relative_error_vs_truth": err_of(t)}
                     for tau, sc, t in zip(taus, scores, fulls)],
            "chosen_on_these_data": taus[min(range(len(taus)), key=lambda q: scores[q])],
            "toy_median_chosen_tau": taus[srt[len(srt) // 2]], "toy_mean_rms_relative_error_chosen": mean_err,
            "best_fixed_tau_by_toys": taus[best_fixed], "toy_mean_rms_relative_error_best_fixed": fixed_mean[best_fixed],
            "excess_over_best_fixed": mean_err / fixed_mean[best_fixed] - 1.0,
            "note": ("each reco bin is left out in turn, the penalized Poisson likelihood is refitted to the rest, and the "
                     "left-out count is scored by its exact Poisson log-probability at the predicted mean (no Gaussian "
                     "weights and no hat-matrix shortcut); the penalty must make the truth identifiable without the left-out "
                     "bin, and a very weak penalty can score badly for that reason; the excess over the best fixed strength "
                     "uses the supplied truth and is a like-for-like toy comparison, not a property of one dataset; "
                     "leave-one-out CV can still favor too weak a penalty for strongly correlated neighboring bins")}


# ------------------------------------------------------------------------------ CLI
def _read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ToyError(f"cannot read {path}: {exc}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, toys, method_default=None, param=True):
        p.add_argument("--input", required=True, help="JSON file (see the module docstring)")
        p.add_argument("--method", choices=METHODS, default=method_default, required=method_default is None)
        if param:
            p.add_argument("--param", type=float, required=True, help="iterations, strength or singular values")
        p.add_argument("--toys", type=int, default=toys)
        p.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")

    s = sub.add_parser("regularized-scan", help="bias/spread scan over regularization settings")
    common(s, 200, param=False)
    s.add_argument("--values", help="comma-separated settings (default: a built-in list)")
    common_c = sub.add_parser("closure", help="closure and pull test")
    common(common_c, 500)
    f = sub.add_parser("fold-compare", help="forward folding versus unfold-then-fit")
    common(f, 300)
    r = sub.add_parser("response-stat", help="effect of finite response statistics")
    common(r, 300)
    r.add_argument("--response-model", choices=RESPONSE_MODELS, default="poisson_cells", help="statistical model of the response cells")
    cr = sub.add_parser("choose-regularization", help="L-curve, GCV and leave-one-out CV choice")
    common(cr, 200, param=False)
    cr.add_argument("--values", help="comma-separated settings (default: a built-in list)")
    rc = sub.add_parser("response-covariance", help="analytic propagation of response statistics")
    common(rc, 200)
    rc.add_argument("--response-model", choices=RESPONSE_MODELS, default="poisson_cells", help="statistical model of the response cells")
    rm = sub.add_parser("response-measured", help="propagate a measured response covariance or replicas")
    rm.add_argument("--input", required=True)
    rm.add_argument("--method", choices=METHODS, required=True)
    rm.add_argument("--param", type=float, required=True, help="iterations, strength or singular values")
    nf = sub.add_parser("nonparam-fold", help="penalized non-parametric forward folding")
    nf.add_argument("--input", required=True)
    nf.add_argument("--tau", type=float, required=True, help="log-curvature penalty strength")
    nf.add_argument("--compare-tau", type=float, default=0.01, help="Tikhonov strength for the comparison")
    nf.add_argument("--prior", choices=PRIORS, default="log_curvature", help="smoothness prior of the forward fold")
    nf.add_argument("--toys", type=int, default=100)
    nf.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    cp = sub.add_parser("compare-fold-priors", help="compare forward-folding smoothness priors on the same toys")
    cp.add_argument("--input", required=True)
    cp.add_argument("--priors", required=True, help="comma-separated name:tau entries, e.g. log_curvature:0.1,entropy:0.01")
    cp.add_argument("--toys", type=int, default=100)
    cp.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    pc = sub.add_parser("choose-penalty-poisson", help="Poisson-exact leave-one-out CV of the forward-fold penalty")
    pc.add_argument("--input", required=True)
    pc.add_argument("--prior", choices=PRIORS, default="log_curvature")
    pc.add_argument("--taus", help="comma-separated strengths (default: 1e-4 to 1e3)")
    pc.add_argument("--toys", type=int, default=40)
    pc.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        doc = _read(args.input)
        if args.command == "choose-regularization":
            try:
                values = [float(v) for v in args.values.split(",")] if args.values else None
            except ValueError:
                raise ToyError("--values must be comma-separated numbers") from None
            result = choose_regularization(doc, args.method, values, args.toys, args.seed)
        elif args.command == "response-covariance":
            result = response_covariance(doc, args.method, args.param, args.toys, args.seed, args.response_model)
        elif args.command == "response-measured":
            result = response_measured(doc, args.method, args.param)
        elif args.command == "nonparam-fold":
            result = nonparam_fold(doc, args.tau, args.compare_tau, args.toys, args.seed, args.prior)
        elif args.command == "compare-fold-priors":
            try:
                specs = [(e.split(":")[0], float(e.split(":")[1])) for e in args.priors.split(",")]
            except (IndexError, ValueError):
                raise ToyError("--priors must be comma-separated name:tau entries") from None
            result = compare_fold_priors(doc, specs, args.toys, args.seed)
        elif args.command == "choose-penalty-poisson":
            try:
                taus = [float(v) for v in args.taus.split(",")] if args.taus else None
            except ValueError:
                raise ToyError("--taus must be comma-separated numbers") from None
            result = choose_penalty_poisson(doc, args.prior, taus, args.toys, args.seed)
        elif args.command == "regularized-scan":
            try:
                values = [float(v) for v in args.values.split(",")] if args.values else None
            except ValueError:
                raise ToyError("--values must be comma-separated numbers") from None
            result = regularized_scan(doc, args.method, values, args.toys, args.seed)
        elif args.command == "closure":
            result = closure(doc, args.method, args.param, args.toys, args.seed)
        elif args.command == "fold-compare":
            result = fold_compare(doc, args.method, args.param, args.toys, args.seed)
        else:
            result = response_stat(doc, args.method, args.param, args.toys, args.seed, args.response_model)
    except ToyError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    result["status"] = "ok"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
