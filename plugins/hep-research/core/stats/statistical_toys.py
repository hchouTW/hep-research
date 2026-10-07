#!/usr/bin/env python3
"""Small seeded toy diagnostics for low-statistics analysis decisions.

Purpose: give four statistical-validation rules an executable, labeled-as-approximation
form. This is not a statistics framework; each subcommand answers one narrow question
under stated simplifications and echoes its seed, toy count and configuration so a run is
reproducible. Output is labeled [General method]; nothing here is the performance of any experiment.

Subcommands:
  boundary       counting-experiment discovery statistic q0 at the s >= 0 boundary: fraction of
                 toys with q0 = 0 and the p-value by exact Poisson tail, by seeded toys, by the
                 half-chi2 asymptotic form and by naive Wilks (chi2, 1 dof); known background.
  template-stat  effect of finite template (Monte Carlo) statistics on a one-parameter template
                 fraction fit: seeded toys fit with the true templates and with templates built
                 from a finite MC sample, and compare bias and spread. It quantifies the effect
                 of ignoring MC statistics; it does not implement a Barlow-Beeston fit.
  unfold-scan    iterative (D'Agostini) unfolding scan: for each iteration count, bias and
                 statistical spread over seeded toys of a supplied response matrix and truth.
  template-bb    the same fit with a Barlow-Beeston-lite (Conway) per-bin nuisance for the template
                 statistics: bias, spread, pull width and interval coverage of the true-template, the
                 naive finite-template and the BB-lite fits.
  ratio-cov      per-bin ratios (for example across rigidity) with systematics correlated across bins
                 and between numerator and denominator, from a JSON file; the effect on a weighted
                 mean versus an independent-bins assumption.
  ratio-measured per-bin ratios of two measured vectors with a supplied joint covariance (numerator
                 and denominator blocks, including their cross-covariance): linear and toy
                 propagation, nonlinearity bias, and a constant-ratio fit with the full covariance
                 versus a diagonal-only treatment.
  ratio-toys     ratio of two quantities with Poisson statistics and multiplicative systematic
                 nuisances whose correlation between numerator and denominator is declared:
                 the ratio's spread versus the naive "cancels" and "independent" assumptions.

Usage (from the skill directory):
  python3 core/stats/statistical_toys.py boundary --n 12 --b 8 --toys 20000 --seed 1
  python3 core/stats/statistical_toys.py template-stat --sig 0.1,0.3,0.4,0.2 --bkg 0.4,0.3,0.2,0.1 \\
      --n-data 400 --f 0.2 --mc-sig 200 --mc-bkg 200 --toys 2000 --seed 1
  python3 core/stats/statistical_toys.py template-bb --sig 0.1,0.3,0.4,0.2 --bkg 0.4,0.3,0.2,0.1 \\
      --n-data 400 --f 0.2 --mc-sig 200 --mc-bkg 200 --toys 1000 --seed 1
  python3 core/stats/statistical_toys.py ratio-cov --input ratio_bins.json --toys 5000 --seed 1
  python3 core/stats/statistical_toys.py ratio-measured --input measured.json --toys 20000 --seed 1
  python3 core/stats/statistical_toys.py unfold-scan --input response_truth.json --toys 500 --seed 1
  python3 core/stats/statistical_toys.py ratio-toys --n1 400 --n2 900 --sys eff:0.03:0.03:0.8 --toys 20000 --seed 1
ratio-measured input: {"numerator": [x_1..x_n], "denominator": [y_1..y_n], "covariance": [[...]]} with
the covariance of the 2n vector (x_1..x_n, y_1..y_n), so its off-diagonal blocks carry the
numerator-denominator correlation.
ratio-cov input: {"numerator": [...], "denominator": [...] (expected counts per bin), "systematics": [{"name":
"eff", "sigma_num": 0.02 or [per-bin], "sigma_den": 0.02 or [per-bin], "num_den_rho": 0.8, "bin_correlation":
{"kind": "full" | "none" | "exponential", "length": 3}}]}.
unfold-scan input: {"response": [[...]], "truth": [...], "prior": [...] (optional), "max_iterations": 10,
"orientation": "rows_reco_cols_truth" (default) | "rows_truth_cols_reco"}; entries are the probability
that a truth bin is reconstructed in a reco bin; column sums are the efficiencies (inefficiency outside
the matrix), as in core/stats/validate_response.py.
Exit codes: 0 ok; 2 rejected input. Standard library only.
Importable: boundary, template_stat, template_bb, unfold_scan, ratio_toys, ratio_cov, ratio_measured, poisson_draw.
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
from typing import Any

from core.stats import _poisson, _validate
from core.stats._linalg import chol_solve, cholesky, golden_min, scan_then_golden
from core.stats._poisson import MAX_MEAN  # per-draw mean; a draw costs O(mean)

LABEL = "[General method]"
MAX_TOYS = 200000


class ToyError(ValueError):
    """Raised for invalid counts, probabilities, seeds, toy numbers or matrices."""


def _seed(seed) -> int:
    return _validate.seed(seed, error=ToyError)


def _toys(toys, low: int = 100) -> int:
    return _validate.toy_count(toys, low, MAX_TOYS, error=ToyError)


def _num(x, name, low=None, high=None, strict_low=False) -> float:
    return _validate.number(x, name, low, high, strict_low, error=ToyError)


def poisson_draw(rng: random.Random, mu: float) -> int:
    """Exact Poisson variate: sum of Poisson draws with mean <= 50 each (inversion); cost O(mu)."""
    return _poisson.draw_chunked(rng, _num(mu, "mean", 0.0, MAX_MEAN))


_golden_min, _scan_then_golden, _chol_solve = golden_min, scan_then_golden, chol_solve


def _std(values) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


# ----------------------------------------------------------------------------- boundary
def _q0(n: int, b: float) -> float:
    return 2.0 * (n * math.log(n / b) - n + b) if n > b else 0.0


def _sf_normal(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def boundary(n: int, b: float, toys: int, seed: int) -> dict:
    """q0 at the s >= 0 boundary for N ~ Poisson(s + b), known b > 0, testing s = 0."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ToyError(f"n must be a non-negative integer, got {n!r}")
    b = _num(b, "b", 0.0, MAX_MEAN, strict_low=True)
    toys, seed = _toys(toys), _seed(seed)
    rng = random.Random(seed)
    q_obs = _q0(n, b)
    draws = [poisson_draw(rng, b) for _ in range(toys)]
    q = [_q0(d, b) for d in draws]
    p_toy = sum(v >= q_obs - 1e-12 for v in q) / toys
    from core.stats.poisson_diagnostics import log_poisson_sf, z_from_log_p
    log_p = log_poisson_sf(n, b)  # exact P(N >= n | b), summed in the tail rather than as 1 - P(N <= n - 1 | b)
    p_exact = math.exp(log_p)
    z = math.sqrt(q_obs)
    return {"label": LABEL, "method": "q0 at the s >= 0 boundary, known background, seeded toys", "n_obs": n, "b": b,
            "toys": toys, "seed": seed, "q0_observed": q_obs,
            "p_value_exact_poisson": p_exact, "log_p_value_exact_poisson": log_p,
            "significance_exact_poisson_z": z_from_log_p(log_p), "p_value_toys": p_toy,
            "binomial_error_on_p_toys": math.sqrt(max(p_toy * (1 - p_toy), 0.0) / toys),
            "p_value_half_chi2_asymptotic": _sf_normal(z) if q_obs > 0 else 0.5,
            "p_value_naive_wilks_chi2_1dof": 2.0 * _sf_normal(z) if q_obs > 0 else 1.0,
            "fraction_toys_with_q0_zero": sum(v == 0.0 for v in q) / toys,
            "note": ("under the background-only hypothesis q0 is 0 whenever N <= b, so its distribution is a point mass "
                     "plus a continuous part (about half and half at large b), not chi2 with 1 dof: naive Wilks doubles "
                     "the p-value, the half-chi2 form is the asymptotic limit and is poor at small counts, and the exact "
                     "Poisson tail is the reference here; the background is exactly known, so an uncertain background "
                     "needs a profile-likelihood or toy construction with that nuisance included")}


# --------------------------------------------------------------------------- template-stat
def _probs(text_or_list, name: str) -> list[float]:
    try:
        vals = [float(v) for v in (text_or_list.split(",") if isinstance(text_or_list, str) else text_or_list)]
    except (TypeError, ValueError):
        raise ToyError(f"{name} must be a comma-separated list of numbers") from None
    if len(vals) < 2 or not all(math.isfinite(v) and v >= 0 for v in vals) or sum(vals) <= 0:
        raise ToyError(f"{name} needs at least two finite non-negative entries with a positive sum")
    tot = sum(vals)
    return [v / tot for v in vals]


def _fit_fraction(counts: list[int], sig: list[float], bkg: list[float]) -> float:
    """Maximum-likelihood signal fraction in [0, 1] of a multinomial with p_i = f s_i + (1 - f) b_i."""
    idx = [i for i in range(len(counts)) if sig[i] > 0 or bkg[i] > 0]

    def score(f: float) -> float:
        tot = 0.0
        for i in idx:
            p = f * sig[i] + (1.0 - f) * bkg[i]
            tot += counts[i] * (sig[i] - bkg[i]) / max(p, 1e-300)
        return tot

    if score(0.0) <= 0.0:
        return 0.0
    if score(1.0) >= 0.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if score(mid) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


def template_stat(sig, bkg, n_data: float, f: float, mc_sig: float, mc_bkg: float, toys: int, seed: int) -> dict:
    s, b = _probs(sig, "sig"), _probs(bkg, "bkg")
    if len(s) != len(b):
        raise ToyError("sig and bkg must have the same number of bins")
    n_data = _num(n_data, "n_data", 1.0, MAX_MEAN)
    f = _num(f, "f", 0.0, 1.0)
    mc_sig, mc_bkg = _num(mc_sig, "mc_sig", 1.0, MAX_MEAN), _num(mc_bkg, "mc_bkg", 1.0, MAX_MEAN)
    toys, seed = _toys(toys), _seed(seed)
    rng = random.Random(seed)
    exact_fits, finite_fits, skipped = [], [], 0
    for _ in range(toys):
        mu = [n_data * (f * s[i] + (1.0 - f) * b[i]) for i in range(len(s))]
        counts = [poisson_draw(rng, m) for m in mu]
        ms = [poisson_draw(rng, mc_sig * p) for p in s]
        mb = [poisson_draw(rng, mc_bkg * p) for p in b]
        if sum(ms) == 0 or sum(mb) == 0 or sum(counts) == 0:
            skipped += 1
            continue
        s_hat, b_hat = [v / sum(ms) for v in ms], [v / sum(mb) for v in mb]
        exact_fits.append(_fit_fraction(counts, s, b))
        finite_fits.append(_fit_fraction(counts, s_hat, b_hat))
    if len(exact_fits) < 10:
        raise ToyError("too few usable toys; increase the MC sizes or n_data")
    sd_exact, sd_finite = _std(exact_fits), _std(finite_fits)
    return {"label": LABEL, "method": "finite-template effect on a one-parameter template fraction fit, seeded toys",
            "bins": len(s), "n_data": n_data, "true_fraction": f, "mc_sig_events": mc_sig, "mc_bkg_events": mc_bkg,
            "toys_used": len(exact_fits), "toys_skipped_empty": skipped, "seed": seed,
            "bias_true_templates": statistics.fmean(exact_fits) - f,
            "bias_finite_templates": statistics.fmean(finite_fits) - f,
            "spread_true_templates": sd_exact, "spread_finite_templates": sd_finite,
            "spread_ratio_finite_over_true": sd_finite / sd_exact if sd_exact > 0 else None,
            "fraction_at_boundary_true": sum(v in (0.0, 1.0) for v in exact_fits) / len(exact_fits),
            "fraction_at_boundary_finite": sum(v in (0.0, 1.0) for v in finite_fits) / len(finite_fits),
            "note": ("the fit uses the finite templates as if exact, so a spread ratio above 1 is the error the template "
                     "statistics add and a nonzero bias is not corrected by it; set a trigger (for example a ratio above "
                     "about 1.1 or a bias above a fraction of the statistical error) for a method with MC statistics in "
                     "the likelihood or a larger MC sample; the toy data are drawn from the true templates, bins are "
                     "Poisson, the template of a bin empty in both samples is dropped from the fit, and a two-template, "
                     "one-parameter model is far simpler than a real fit")}


# ----------------------------------------------------------------------------- unfold-scan
def _load_response(doc: dict) -> tuple[list[list[float]], list[float], list[float] | None, int]:
    if not isinstance(doc, dict):
        raise ToyError("input must be a JSON object")
    raw = doc.get("response")
    if not isinstance(raw, list) or not raw or not all(isinstance(r, list) and r for r in raw):
        raise ToyError("response must be a non-empty matrix (list of rows)")
    if len({len(r) for r in raw}) != 1:
        raise ToyError("response rows have different lengths")
    orient = doc.get("orientation", "rows_reco_cols_truth")
    if orient not in ("rows_reco_cols_truth", "rows_truth_cols_reco"):
        raise ToyError("orientation must be rows_reco_cols_truth or rows_truth_cols_reco")
    m = [[_num(v, "response entry", 0.0, 1.0) for v in row] for row in raw]
    if orient == "rows_truth_cols_reco":
        m = [list(c) for c in zip(*m)]
    n_reco, n_truth = len(m), len(m[0])
    if max(n_reco, n_truth) > 60:
        raise ToyError("at most 60 bins per axis")
    truth = doc.get("truth")
    if not isinstance(truth, list) or len(truth) != n_truth:
        raise ToyError(f"truth must list {n_truth} expected counts")
    truth = [_num(v, "truth", 0.0, MAX_MEAN) for v in truth]
    prior = doc.get("prior")
    if prior is not None:
        if not isinstance(prior, list) or len(prior) != n_truth:
            raise ToyError(f"prior must list {n_truth} values")
        prior = [_num(v, "prior", 0.0) for v in prior]
        if sum(prior) <= 0:
            raise ToyError("prior must have a positive sum")
    iters = doc.get("max_iterations", 10)
    if isinstance(iters, bool) or not isinstance(iters, int) or not 1 <= iters <= 100:
        raise ToyError("max_iterations must be an integer in [1, 100]")
    for j in range(n_truth):
        if sum(m[i][j] for i in range(n_reco)) > 1.0 + 1e-9:
            raise ToyError(f"truth bin {j}: column sum exceeds 1; entries must be probabilities")
        if truth[j] > 0 and sum(m[i][j] for i in range(n_reco)) == 0.0:
            raise ToyError(f"truth bin {j} has expected counts but zero efficiency")
    return m, truth, prior, iters


def _unfold(counts: list[int], m: list[list[float]], eff: list[float], prior: list[float], iters: int):
    t = list(prior)
    n_reco, n_truth = len(m), len(m[0])
    out = []
    for _ in range(iters):
        new = [0.0] * n_truth
        for i in range(n_reco):
            denom = sum(m[i][l] * t[l] for l in range(n_truth))
            if denom <= 0 or counts[i] == 0:
                continue
            for j in range(n_truth):
                new[j] += counts[i] * m[i][j] * t[j] / denom
        t = [new[j] / eff[j] if eff[j] > 0 else 0.0 for j in range(n_truth)]
        out.append(list(t))
    return out


def unfold_scan(doc: dict, toys: int, seed: int) -> dict:
    m, truth, prior, iters = _load_response(doc)
    toys, seed = _toys(toys, 20), _seed(seed)
    n_reco, n_truth = len(m), len(m[0])
    eff = [sum(m[i][j] for i in range(n_reco)) for j in range(n_truth)]
    start = prior if prior is not None else [1.0] * n_truth
    scale = sum(truth) / sum(start) if sum(start) > 0 else 1.0
    start = [v * scale for v in start]  # normalize the starting shape to the truth total
    mu = [sum(m[i][j] * truth[j] for j in range(n_truth)) for i in range(n_reco)]
    rng = random.Random(seed)
    per_iter: list[list[list[float]]] = [[[] for _ in range(n_truth)] for _ in range(iters)]
    for _ in range(toys):
        counts = [poisson_draw(rng, x) for x in mu]
        for k, vec in enumerate(_unfold(counts, m, eff, start, iters)):
            for j in range(n_truth):
                per_iter[k][j].append(vec[j])
    used = [j for j in range(n_truth) if truth[j] > 0]
    rows = []
    for k in range(iters):
        bias = [(statistics.fmean(per_iter[k][j]) - truth[j]) / truth[j] for j in used]
        spread = [_std(per_iter[k][j]) / truth[j] for j in used]
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        rows.append({"iterations": k + 1, "rms_relative_bias": rms(bias), "rms_relative_spread": rms(spread),
                     "rms_relative_total": math.sqrt(rms(bias) ** 2 + rms(spread) ** 2)})
    best = min(rows, key=lambda r: r["rms_relative_total"])
    return {"label": LABEL, "method": "iterative (D'Agostini) unfolding scan, seeded toys", "bins_truth": n_truth,
            "bins_reco": n_reco, "toys": toys, "seed": seed, "starting_shape": "supplied prior" if prior else "flat",
            "scan": rows, "minimum_total_at_iterations": best["iterations"],
            "note": ("bias is measured against the truth you supplied, which makes the scan circular: it shows the "
                     "bias-versus-variance trade-off for that truth and starting shape, not the best iteration count "
                     "for data; repeat with a different truth and prior (a model-dependence check), treat the "
                     "efficiency and the response as exactly known, and note that the toy spread ignores correlations "
                     "between bins and the response-matrix statistics; a stopping rule (such as the 0.1% agreement of "
                     "successive steps) is a separate documented choice")}


# ------------------------------------------------------------------------------ ratio-toys
def _parse_sys(text: str) -> tuple[str, float, float, float]:
    parts = text.split(":")
    if len(parts) != 4:
        raise ToyError(f"--sys must be name:sigma_num:sigma_den:rho, got {text!r}")
    try:
        s1, s2, rho = float(parts[1]), float(parts[2]), float(parts[3])
    except ValueError:
        raise ToyError(f"--sys numbers must be numeric, got {text!r}") from None
    if not (math.isfinite(s1) and math.isfinite(s2) and math.isfinite(rho)) or s1 < 0 or s2 < 0 or s1 > 1 or s2 > 1 \
            or not -1.0 <= rho <= 1.0:
        raise ToyError("--sys needs fractional sigmas in [0, 1] and rho in [-1, 1]")
    return parts[0], s1, s2, rho


def ratio_toys(n1: float, n2: float, systematics: list[str], toys: int, seed: int) -> dict:
    n1, n2 = _num(n1, "n1", 0.0, MAX_MEAN), _num(n2, "n2", 0.0, MAX_MEAN, strict_low=True)
    toys, seed = _toys(toys), _seed(seed)
    sysd = [_parse_sys(t) for t in systematics]
    rng = random.Random(seed)
    nominal = n1 / n2

    def draw_sys():
        e1 = e2 = 0.0
        for _, s1, s2, rho in sysd:
            z1, z2 = rng.gauss(0, 1), rng.gauss(0, 1)
            e1 += s1 * z1
            e2 += s2 * (rho * z1 + math.sqrt(1 - rho * rho) * z2)
        return math.exp(e1 - e2)

    full, stat_only, sys_only, lost = [], [], [], 0
    for _ in range(toys):
        a, d = poisson_draw(rng, n1), poisson_draw(rng, n2)
        g = draw_sys()
        sys_only.append(nominal * g)
        if d == 0:
            lost += 1
            continue
        full.append(a / d * g)
        stat_only.append(a / d)
    if len(full) < 10:
        raise ToyError("too few toys with a nonzero denominator; increase n2")
    per = [{"name": name, "sigma_numerator": s1, "sigma_denominator": s2, "rho": rho,
            "fractional_effect_on_ratio_analytic": math.sqrt(max(s1 * s1 + s2 * s2 - 2 * rho * s1 * s2, 0.0)),
            "fractional_effect_if_assumed_to_cancel": 0.0,
            "fractional_effect_if_assumed_independent": math.sqrt(s1 * s1 + s2 * s2)} for name, s1, s2, rho in sysd]
    return {"label": LABEL, "method": "ratio of two Poisson counts with correlated multiplicative systematics, seeded toys",
            "n1": n1, "n2": n2, "nominal_ratio": nominal, "toys": toys, "toys_lost_zero_denominator": lost, "seed": seed,
            "mean_ratio_toys": statistics.fmean(full), "fractional_bias_of_mean": statistics.fmean(full) / nominal - 1.0,
            "fractional_spread_total": _std(full) / nominal, "fractional_spread_statistical_only": _std(stat_only) / nominal,
            "fractional_spread_systematic_only": _std(sys_only) / nominal, "systematics": per,
            "note": ("each systematic is a multiplicative log-normal-like nuisance with fractional sigmas for numerator and "
                     "denominator and a declared correlation rho; rho = 1 with equal sigmas cancels, rho = 0 adds in "
                     "quadrature, and a partial rho leaves a residual that must be argued, not assumed away; the "
                     "correlation is your input, not something this script can determine; the ratio of Poisson counts is "
                     "biased at low denominators (see the bias field), and systematics that depend on rigidity or time "
                     "need a full covariance, not one number per effect")}


# ------------------------------------------------------------------------------ template-bb
def _ll_poisson(counts, nu, var=None) -> float:
    """Poisson log-likelihood (constants dropped); with `var`, the Barlow-Beeston-lite (Conway) profile:
    one Gaussian-constrained scale beta per bin on the expected count nu, with relative variance var / nu^2."""
    total = 0.0
    for n, v, w in zip(counts, nu, var if var is not None else [0.0] * len(nu)):
        if v <= 0.0:
            if n > 0:
                return -1e300
            continue
        beta, pen = 1.0, 0.0
        if w > 0.0:
            d2 = w / (v * v)
            beta = ((1.0 - v * d2) + math.sqrt((1.0 - v * d2) ** 2 + 4.0 * n * d2)) / 2.0
            pen = (beta - 1.0) ** 2 / (2.0 * d2)
        mu = v * beta
        total += (n * math.log(mu) if n > 0 else 0.0) - mu - pen
    return total


def _fit_with_error(ll, tol_up: float = 0.5):
    """(f_hat, f_lo, f_hi) of a likelihood on [0, 1]; the bounds are None where the interval hits 0 or 1."""
    f_hat = _scan_then_golden(lambda f: -ll(f), 0.0, 1.0)
    top = ll(f_hat)
    out: list[float | None] = []
    for edge, sign in ((0.0, -1), (1.0, 1)):
        if top - ll(edge) < tol_up:
            out.append(None)
            continue
        lo, hi = (f_hat, edge) if sign > 0 else (edge, f_hat)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            inside = top - ll(mid) < tol_up
            if sign > 0:
                lo, hi = (mid, hi) if inside else (lo, mid)
            else:
                lo, hi = (lo, mid) if inside else (mid, hi)
        out.append(0.5 * (lo + hi))
    return f_hat, out[0], out[1]


def template_bb(sig, bkg, n_data: float, f: float, mc_sig: float, mc_bkg: float, toys: int, seed: int) -> dict:
    s_true, b_true = _probs(sig, "sig"), _probs(bkg, "bkg")
    if len(s_true) != len(b_true):
        raise ToyError("sig and bkg must have the same number of bins")
    n_data = _num(n_data, "n_data", 1.0, MAX_MEAN)
    f = _num(f, "f", 0.0, 1.0)
    mc_sig, mc_bkg = _num(mc_sig, "mc_sig", 1.0, MAX_MEAN), _num(mc_bkg, "mc_bkg", 1.0, MAX_MEAN)
    toys, seed = _toys(toys), _seed(seed)
    k = len(s_true)
    rng = random.Random(seed)
    names = ("true_templates", "naive_finite_templates", "barlow_beeston_lite")
    res: dict[str, dict[str, Any]] = {n: {"fits": [], "pulls": [], "covered": [], "no_pull": 0} for n in names}
    skipped = 0
    for _ in range(toys):
        counts = [poisson_draw(rng, n_data * (f * s_true[i] + (1.0 - f) * b_true[i])) for i in range(k)]
        ms = [poisson_draw(rng, mc_sig * p) for p in s_true]
        mb = [poisson_draw(rng, mc_bkg * p) for p in b_true]
        if sum(ms) == 0 or sum(mb) == 0:
            skipped += 1
            continue
        s_hat, b_hat = [v / sum(ms) for v in ms], [v / sum(mb) for v in mb]
        keep = [i for i in range(k) if s_hat[i] > 0 or b_hat[i] > 0]
        cn = [counts[i] for i in keep]

        def nu_of(sv, bv):
            return lambda x: [n_data * (x * sv[i] + (1.0 - x) * bv[i]) for i in keep]

        def var_of(x):
            return [n_data ** 2 * (x * x * ms[i] / sum(ms) ** 2 + (1.0 - x) ** 2 * mb[i] / sum(mb) ** 2) for i in keep]
        variants = {
            "true_templates": lambda x: _ll_poisson(cn, nu_of(s_true, b_true)(x)),
            "naive_finite_templates": lambda x: _ll_poisson(cn, nu_of(s_hat, b_hat)(x)),
            "barlow_beeston_lite": lambda x: _ll_poisson(cn, nu_of(s_hat, b_hat)(x), var_of(x)),
        }
        for name, ll in variants.items():
            f_hat, lo, hi = _fit_with_error(ll)
            r = res[name]
            r["fits"].append(f_hat)
            if lo is None or hi is None:
                r["no_pull"] += 1
                continue
            r["pulls"].append((f_hat - f) / (0.5 * (hi - lo)))
            r["covered"].append(lo <= f <= hi)
    used = len(res[names[0]]["fits"])
    if used < 10:
        raise ToyError("too few usable toys; increase the MC sizes or n_data")
    variants_out = {}
    for name, r in res.items():
        variants_out[name] = {"bias": statistics.fmean(r["fits"]) - f, "spread": _std(r["fits"]),
                              "mean_pull": statistics.fmean(r["pulls"]) if r["pulls"] else None,
                              "pull_width": _std(r["pulls"]) if len(r["pulls"]) > 1 else None,
                              "coverage_of_delta_lnL_interval": sum(r["covered"]) / len(r["covered"]) if r["covered"] else None,
                              "fraction_without_two_sided_interval": r["no_pull"] / used}
    return {"label": LABEL, "method": "template-fraction fit: true, naive finite and Barlow-Beeston-lite templates, seeded toys",
            "bins": k, "n_data": n_data, "true_fraction": f, "mc_sig_events": mc_sig, "mc_bkg_events": mc_bkg,
            "toys_used": used, "toys_skipped_empty": skipped, "seed": seed, "variants": variants_out,
            "note": ("pull = (f_hat - f) / half-width of the delta-lnL = 0.5 interval; a pull width near 1 and coverage "
                     "near 0.68 mean the quoted error is right, and the naive fit typically shows a width above 1 "
                     "(too-small errors) that the Barlow-Beeston-lite profile reduces; Barlow-Beeston-lite (Conway) "
                     "puts one nuisance per bin on the total expected count, an approximation to the full per-template "
                     "treatment, with the MC variance taken at the fitted fraction; toy data come from the true "
                     "templates with Poisson bins, the normalization is fixed, a bin empty in both templates is "
                     "dropped, and pulls exist only for toys whose interval is two-sided (the fraction without one "
                     "is reported); a nonzero bias is not removed by the nuisance")}


# ------------------------------------------------------------------------------- ratio-cov
def _vec(x, n, name) -> list[float]:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        x = [x] * n
    if not isinstance(x, list) or len(x) != n:
        raise ToyError(f"{name} must be a number or a list of {n} numbers")
    return [_num(v, name, 0.0, 1.0) for v in x]


def ratio_cov(doc: dict, toys: int, seed: int) -> dict:
    if not isinstance(doc, dict):
        raise ToyError("input must be a JSON object")
    num, den = doc.get("numerator"), doc.get("denominator")
    if not isinstance(num, list) or not isinstance(den, list) or len(num) != len(den) or not 2 <= len(num) <= 30:
        raise ToyError("numerator and denominator must be lists of equal length, 2 to 30 bins")
    num = [_num(v, "numerator", 0.0, MAX_MEAN, strict_low=True) for v in num]
    den = [_num(v, "denominator", 0.0, MAX_MEAN, strict_low=True) for v in den]
    n = len(num)
    toys, seed = _toys(toys), _seed(seed)
    specs, regularized = [], []
    for d in doc.get("systematics", []):
        if not isinstance(d, dict) or "name" not in d:
            raise ToyError("each systematic needs a name")
        rho = _num(d.get("num_den_rho", 0.0), "num_den_rho", -1.0, 1.0)
        bc = d.get("bin_correlation", {"kind": "full"})
        kind = bc.get("kind") if isinstance(bc, dict) else None
        if kind not in ("full", "none", "exponential"):
            raise ToyError("bin_correlation.kind must be full, none or exponential")
        chol = None
        if kind == "exponential":
            length = _num(bc.get("length"), "bin_correlation.length", 0.0, 1000.0, strict_low=True)
            chol, reg = cholesky([[math.exp(-abs(i - j) / length) for j in range(n)] for i in range(n)],
                                 f"bin-correlation matrix of systematic {d['name']}", semidefinite=True, error=ToyError)
            if reg:
                regularized.append(reg)
        specs.append({"name": d["name"], "sn": _vec(d.get("sigma_num", 0.0), n, "sigma_num"),
                      "sd": _vec(d.get("sigma_den", 0.0), n, "sigma_den"), "rho": rho, "kind": kind, "chol": chol})
    rng = random.Random(seed)

    def across_bins(spec):
        if spec["kind"] == "full":
            g = rng.gauss(0, 1)
            return [g] * n
        z = [rng.gauss(0, 1) for _ in range(n)]
        if spec["kind"] == "none":
            return z
        return [sum(spec["chol"][i][j] * z[j] for j in range(i + 1)) for i in range(n)]

    log_sys, full, stat_only, lost = [], [], [], 0
    for _ in range(toys):
        e = [0.0] * n
        for sp in specs:
            z1, z2 = across_bins(sp), across_bins(sp)
            for i in range(n):
                e[i] += sp["sn"][i] * z1[i] - sp["sd"][i] * (sp["rho"] * z1[i] + math.sqrt(1 - sp["rho"] ** 2) * z2[i])
        log_sys.append(e)
        a, d = [poisson_draw(rng, m) for m in num], [poisson_draw(rng, m) for m in den]
        if min(d) == 0:
            lost += 1
            continue
        r = [a[i] / d[i] for i in range(n)]
        stat_only.append(r)
        full.append([r[i] * math.exp(e[i]) for i in range(n)])
    if len(full) < 10:
        raise ToyError("too few toys with nonzero denominators; increase the denominators")
    nominal = [num[i] / den[i] for i in range(n)]
    sys_spread = [_std([math.exp(row[i]) for row in log_sys]) for i in range(n)]
    means = [statistics.fmean(row[i] for row in log_sys) for i in range(n)]
    corr = [[(statistics.fmean((row[i] - means[i]) * (row[j] - means[j]) for row in log_sys)
              / (_std([row[i] for row in log_sys]) * _std([row[j] for row in log_sys])))
             if sys_spread[i] > 0 and sys_spread[j] > 0 else None for j in range(n)] for i in range(n)]
    w = [1.0 / (nominal[i] ** 2 * (1.0 / num[i] + 1.0 / den[i])) for i in range(n)]
    sw = sum(w)
    w = [x / sw for x in w]
    mean_of = lambda rows: [sum(w[i] * row[i] for i in range(n)) for row in rows]
    rbar = sum(w[i] * nominal[i] for i in range(n))
    tot, sta = _std(mean_of(full)) / rbar, _std(mean_of(stat_only)) / rbar
    sys_only = _std(mean_of([[nominal[i] * math.exp(row[i]) for i in range(n)] for row in log_sys])) / rbar
    naive = math.sqrt(sum((w[i] * nominal[i] * sys_spread[i]) ** 2 for i in range(n))) / rbar
    out = {"label": LABEL, "method": "ratio per bin with systematics correlated across bins and between numerator and denominator, seeded toys",
            "bins": n, "toys": toys, "toys_lost_zero_denominator": lost, "seed": seed, "nominal_ratio": nominal,
            "fractional_spread_per_bin_systematic_only": sys_spread,
            "fractional_spread_per_bin_statistical_only": [_std([row[i] for row in stat_only]) / nominal[i] for i in range(n)],
            "systematic_correlation_between_bins": corr,
            "weighted_mean_ratio": rbar,
            "weighted_mean_fractional_spread": {"statistical_only": sta, "systematic_only": sys_only, "total": tot,
                                                "systematic_if_bins_assumed_independent": naive,
                                                "underestimate_factor_if_independent": sys_only / naive if naive > 0 else None},
            "note": ("each systematic is a multiplicative nuisance with a per-bin fractional sigma for numerator and "
                     "denominator, a numerator-denominator correlation rho and a declared correlation across bins "
                     "(full, none or exponential with a length in bins); the weights are statistical inverse variances "
                     "of the nominal ratio; the declared correlations are your inputs, not something this script can "
                     "determine; the underestimate factor shows what is lost by treating bins as independent when they "
                     "share a systematic; rigidity- or time-dependent shapes beyond these three structures are not "
                     "modeled")}
    if regularized:
        out["regularization"] = regularized
    return out


# ------------------------------------------------------------------------- ratio-measured
def _gammaq(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x) (series and continued fraction)."""
    if x <= 0.0:
        return 1.0
    if x < a + 1.0:
        term = total = 1.0 / a
        ap = a
        for _ in range(500):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    b, c, d = x + 1.0 - a, 1e300, 1.0 / (x + 1.0 - a)
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return min(1.0, math.exp(-x + a * math.log(x) - math.lgamma(a)) * h)


def chi2_sf(chi2: float, ndf: int) -> float:
    """P(chi2_ndf > chi2); chi2 must be >= 0 (an infinite value gives 0) and ndf a positive integer."""
    if isinstance(ndf, bool) or not isinstance(ndf, int) or ndf < 1:
        raise ToyError(f"ndf must be a positive integer, got {ndf!r}")
    if isinstance(chi2, bool) or not isinstance(chi2, (int, float)) or math.isnan(chi2) or chi2 < 0:
        raise ToyError(f"chi2 must be a non-negative number, got {chi2!r}")
    if math.isinf(chi2):
        return 0.0
    return _gammaq(ndf / 2.0, chi2 / 2.0)


def _gls_constant(r, cov, name="ratio covariance", l=None):
    """(mean, sigma, chi2) of a constant fitted to r with covariance cov (Cholesky; pass l to reuse a factor)."""
    if l is None:
        l = cholesky(cov, name, error=ToyError)[0]  # strict: a fit needs a positive-definite matrix
    ones = [1.0] * len(r)
    ci1 = _chol_solve(l, ones)
    ci_r = _chol_solve(l, r)
    den = sum(ci1)
    mean = sum(ci_r) / den
    res = [v - mean for v in r]
    chi2 = sum(a * b for a, b in zip(res, _chol_solve(l, res)))
    return mean, 1.0 / math.sqrt(den), chi2


def ratio_measured(doc: dict, toys: int, seed: int) -> dict:
    if not isinstance(doc, dict):
        raise ToyError("input must be a JSON object")
    x, y, c = doc.get("numerator"), doc.get("denominator"), doc.get("covariance")
    if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y) or not 2 <= len(x) <= 30:
        raise ToyError("numerator and denominator must be lists of equal length, 2 to 30 bins")
    n = len(x)
    x = [_num(v, "numerator", -1e12, 1e12) for v in x]
    y = [_num(v, "denominator", 0.0, 1e12, strict_low=True) for v in y]
    if not isinstance(c, list) or len(c) != 2 * n or any(not isinstance(r, list) or len(r) != 2 * n for r in c):
        raise ToyError(f"covariance must be a {2 * n} x {2 * n} matrix (numerator block first)")
    c = [[_num(v, "covariance", -1e24, 1e24) for v in row] for row in c]
    for i in range(2 * n):
        if c[i][i] <= 0:
            raise ToyError("covariance diagonal entries must be positive")
        for j in range(i):
            if abs(c[i][j] - c[j][i]) > 1e-8 * math.sqrt(c[i][i] * c[j][j]):
                raise ToyError("covariance must be symmetric")
    toys, seed = _toys(toys), _seed(seed)
    chol, reg = cholesky(c, "covariance", semidefinite=True, error=ToyError)  # raises if not positive semi-definite
    r0 = [x[i] / y[i] for i in range(n)]
    jac = [[(1.0 / y[i] if k == i else 0.0) if k < n else (-x[i] / y[i] ** 2 if k - n == i else 0.0) for k in range(2 * n)] for i in range(n)]
    cr = [[sum(jac[a][k] * c[k][m] * jac[b][m] for k in range(2 * n) for m in range(2 * n)) for b in range(n)] for a in range(n)]
    rng = random.Random(seed)
    base = x + y
    draws, bad = [], 0
    for _ in range(toys):
        z = [rng.gauss(0, 1) for _ in range(2 * n)]
        v = [base[i] + sum(chol[i][j] * z[j] for j in range(i + 1)) for i in range(2 * n)]
        if min(v[n:]) <= 0:
            bad += 1
            continue
        draws.append([v[i] / v[n + i] for i in range(n)])
    if len(draws) < 10:
        raise ToyError("too many toys with a non-positive denominator; the denominator is not well measured")
    m = len(draws)
    means = [sum(d[i] for d in draws) / m for i in range(n)]
    sd = [_std([d[i] for d in draws]) for i in range(n)]
    srt = [sorted(d[i] for d in draws) for i in range(n)]
    lin = [math.sqrt(max(cr[i][i], 0.0)) for i in range(n)]
    l_cr = cholesky(cr, "linearized ratio covariance", error=ToyError)[0]
    mean_g, sig_g, chi2_g = _gls_constant(r0, cr, l=l_cr)
    diag = [[cr[i][j] if i == j else 0.0 for j in range(n)] for i in range(n)]
    mean_d, sig_d, chi2_d = _gls_constant(r0, diag, "diagonal of the linearized ratio covariance")
    null = [mean_g * y[i] for i in range(n)]
    hits = 0
    for _ in range(toys):
        z = [rng.gauss(0, 1) for _ in range(2 * n)]
        v = [(null + y)[i] + sum(chol[i][j] * z[j] for j in range(i + 1)) for i in range(2 * n)]
        if min(v[n:]) <= 0:
            continue
        r = [v[i] / v[n + i] for i in range(n)]
        hits += _gls_constant(r, cr, l=l_cr)[2] >= chi2_g - 1e-12
    corr = [[cr[i][j] / math.sqrt(cr[i][i] * cr[j][j]) if cr[i][i] > 0 and cr[j][j] > 0 else None for j in range(n)] for i in range(n)]
    out = {"label": LABEL, "method": "per-bin ratios with a supplied joint covariance, linear and seeded-toy propagation",
            "bins": n, "toys": toys, "toys_discarded_nonpositive_denominator": bad, "seed": seed, "ratio": r0,
            "linear_sigma": lin, "toy_sigma": sd, "toy_over_linear_sigma": [sd[i] / lin[i] if lin[i] > 0 else None for i in range(n)],
            "toy_fractional_bias_of_mean": [means[i] / r0[i] - 1.0 if r0[i] != 0 else None for i in range(n)],
            "toy_16_84_percentile": [[srt[i][int(0.16 * m)], srt[i][min(int(0.84 * m), m - 1)]] for i in range(n)],
            "ratio_correlation_matrix_linear": corr,
            "constant_ratio_fit_full_covariance": {"value": mean_g, "sigma": sig_g, "chi2": chi2_g, "ndf": n - 1,
                                                    "p_value_chi2": chi2_sf(max(chi2_g, 0.0), n - 1), "p_value_toys": hits / toys,
                                                    "binomial_error_on_p_toys": math.sqrt(max(hits / toys * (1 - hits / toys), 0) / toys)},
            "constant_ratio_fit_diagonal_only": {"value": mean_d, "sigma": sig_d, "chi2": chi2_d, "ndf": n - 1,
                                                  "p_value_chi2": chi2_sf(max(chi2_d, 0.0), n - 1)},
            "sigma_ratio_diagonal_over_full": sig_d / sig_g,
            "note": ("the covariance is a user-supplied measured joint covariance of the numerator then denominator vector "
                     "(for example from a published or internal analysis), not something this script can check beyond "
                     "symmetry and positive semi-definiteness; the linear propagation is first order and the toys draw a "
                     "multivariate normal, so a toy-over-linear sigma ratio or a bias away from 1 and 0 marks a "
                     "nonlinear regime (a poorly measured denominator); the constant-ratio fit uses the linearized ratio "
                     "covariance; its p-value by chi2 and by toys (drawn at the fitted constant) should agree for "
                     "well-measured quantities; a diagonal-only treatment of a correlated covariance mis-states the "
                     "fitted sigma and the chi2 (see sigma_ratio_diagonal_over_full) and is the wrong way to compare a "
                     "model with the ratio; supplying only uncertainties is not enough, the correlations are the point")}
    if reg:
        out["regularization"] = [reg]
    return out


# ---------------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, toys=20000):
        p.add_argument("--toys", type=int, default=toys)
        p.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")

    b = sub.add_parser("boundary", help="q0 at the s >= 0 boundary")
    b.add_argument("--n", type=int, required=True)
    b.add_argument("--b", type=float, required=True, help="known background mean (> 0)")
    common(b)
    t = sub.add_parser("template-stat", help="finite-template effect on a template-fraction fit")
    t.add_argument("--sig", required=True, help="signal template, comma-separated bin contents (normalized internally)")
    t.add_argument("--bkg", required=True, help="background template, comma-separated bin contents")
    t.add_argument("--n-data", type=float, required=True)
    t.add_argument("--f", type=float, required=True, help="true signal fraction in [0, 1]")
    t.add_argument("--mc-sig", type=float, required=True, help="MC events behind the signal template")
    t.add_argument("--mc-bkg", type=float, required=True, help="MC events behind the background template")
    common(t, 2000)
    bb = sub.add_parser("template-bb", help="finite-template fit with a Barlow-Beeston-lite nuisance")
    kw: Any
    for name, kw in (("--sig", {"required": True}), ("--bkg", {"required": True})):
        bb.add_argument(name, **kw)
    bb.add_argument("--n-data", type=float, required=True)
    bb.add_argument("--f", type=float, required=True)
    bb.add_argument("--mc-sig", type=float, required=True)
    bb.add_argument("--mc-bkg", type=float, required=True)
    common(bb, 1000)
    rc = sub.add_parser("ratio-cov", help="ratios with across-bin correlated systematics")
    rc.add_argument("--input", required=True, help="JSON file: numerator, denominator, systematics")
    common(rc, 5000)
    rm = sub.add_parser("ratio-measured", help="ratios with a supplied measured joint covariance")
    rm.add_argument("--input", required=True, help="JSON file: numerator, denominator, covariance (2n x 2n)")
    common(rm, 20000)
    u = sub.add_parser("unfold-scan", help="iterative unfolding bias/spread scan")
    u.add_argument("--input", required=True, help="JSON file with response, truth, optional prior and max_iterations")
    common(u, 500)
    r = sub.add_parser("ratio-toys", help="ratio with correlated systematics")
    r.add_argument("--n1", type=float, required=True, help="expected numerator counts")
    r.add_argument("--n2", type=float, required=True, help="expected denominator counts")
    r.add_argument("--sys", action="append", default=[], metavar="NAME:SIG_NUM:SIG_DEN:RHO")
    common(r)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "boundary":
            result = boundary(args.n, args.b, args.toys, args.seed)
        elif args.command == "template-stat":
            result = template_stat(args.sig, args.bkg, args.n_data, args.f, args.mc_sig, args.mc_bkg, args.toys, args.seed)
        elif args.command == "template-bb":
            result = template_bb(args.sig, args.bkg, args.n_data, args.f, args.mc_sig, args.mc_bkg, args.toys, args.seed)
        elif args.command == "ratio-cov":
            try:
                doc = json.loads(Path(args.input).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ToyError(f"cannot read {args.input}: {exc}") from None
            result = ratio_cov(doc, args.toys, args.seed)
        elif args.command == "ratio-measured":
            try:
                doc = json.loads(Path(args.input).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ToyError(f"cannot read {args.input}: {exc}") from None
            result = ratio_measured(doc, args.toys, args.seed)
        elif args.command == "unfold-scan":
            try:
                doc = json.loads(Path(args.input).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ToyError(f"cannot read {args.input}: {exc}") from None
            result = unfold_scan(doc, args.toys, args.seed)
        else:
            result = ratio_toys(args.n1, args.n2, args.sys, args.toys, args.seed)
    except ToyError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    result["status"] = "ok"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
