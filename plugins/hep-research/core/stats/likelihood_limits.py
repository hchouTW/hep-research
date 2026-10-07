#!/usr/bin/env python3
"""Profile-likelihood limits and significance for counting experiments (approximations).

Purpose: give the "treat the background as a nuisance, do not assume Wilks near a boundary"
rule an executable form for small counting problems. This is not a statistics framework:
it covers a single-bin or multi-bin counting model with one signal strength mu >= 0, a
Gaussian-constrained background, the one-sided boundary statistic q-tilde, an asymptotic
result and a seeded toy calibration. Output is labeled [General method]; nothing here is
the performance of any experiment. Seed, toy count and configuration are echoed.

Subcommands:
  profile-limit         single bin: n events, background b +- sigma_b (Gaussian constraint).
                        Asymptotic upper limit (q-tilde = z^2) and a toy-calibrated limit
                        (seeded, common random numbers across the scan); for sigma_b = 0 the toy
                        limit is compared with the exact classical limit.
  profile-significance  single bin: q0 with the nuisance profiled; asymptotic half-chi2 p-value,
                        seeded-toy p-value, naive Wilks (chi2, 1 dof) and, for sigma_b = 0, the
                        exact Poisson tail.
  multibin-limit        several bins sharing one mu, from a JSON file: asymptotic observed
                        limit, Asimov median expected limit, and a seeded-toy p-value at the
                        asymptotic limit (the calibration check). Background nuisance: none,
                        independent per bin (Gaussian), or one common multiplicative scale.

  profile-fc            Feldman-Cousins-style interval with the nuisance profiled: for each s the
                        critical value of the two-sided profile-likelihood ratio comes from seeded
                        toys generated at the profiled background (a profile construction).
  profile-cls           CLs limit from seeded toys of the one-sided profile statistic, with the
                        background nuisance profiled; observed limit plus expected median and
                        1/2-sigma limits from seeded background-only pseudo-experiments.
  shape-limit           multi-bin limit with several nuisances (background and signal normalization,
                        background and signal shape by vertical interpolation), all Gaussian with
                        unit constraint; asymptotic observed and Asimov expected limits, optional
                        seeded-toy calibration at the asymptotic limit.
  multibin-limit and shape-limit also give the asymptotic CLs limit and the expected median and 1/2-sigma limits
  (CLs and CLs+b) from the background-only Asimov data set (Cowan, Cranmer, Gross, Vitells 2011, sec. 4.3).

  neyman-limit          upper limit from the Berger-Boos construction over the background nuisance
                        (supremum over a confidence set of the nuisance, with a seeded-toy p-value at each
                        point), compared with the plug-in profile limit. The construction guarantees coverage
                        in theory; this implementation (finite nuisance grid, finite toys) approximates it,
                        and its coverage is validated only by seeded scans in BB_VALIDATED_RANGE.
  neyman-coverage       seeded coverage check at a true signal and background: the plug-in profile
                        construction versus the Berger-Boos supremum, per pseudo-experiment, with the outer
                        binomial and inner toy errors (neyman_coverage_scan runs it over several true points).

shape-limit input: {"bins": [{"n": 5, "b": 3.2, "s": 1.0}, ...], "cl": 0.95, "nuisances": [
  {"name": "bkg_norm", "kind": "background_norm", "sigma": 0.2},
  {"name": "sig_norm", "kind": "signal_norm", "sigma": 0.1},
  {"name": "bkg_shape", "kind": "background_shape", "up": [per-bin b at +1 sigma], "down": [...]},
  {"name": "sig_shape", "kind": "signal_shape", "up": [per-bin s at +1 sigma], "down": [...]}]}.
Interpolation (HistFactory codes, as in pyhf): a shape nuisance may carry "interpolation": "code0" (default,
piecewise linear, with a kink at theta = 0) or "code4p" (a sixth-order polynomial for |theta| < 1 that matches the
linear extrapolation in value, slope and curvature at |theta| = 1, smooth at 0). A normalization nuisance may give
asymmetric factors {"hi": 1.12, "lo": 0.92} (at theta = +1 and -1) instead of "sigma", with "interpolation": "code4"
(default: polynomial inside |theta| < 1, exponential hi^theta / lo^-theta outside, smooth everywhere), "code1"
(piecewise exponential, kinked at 0) or "code0" (piecewise linear); such a nuisance has the Gaussian constraint.
A normalization nuisance may carry "prior": "gaussian" (default, factor 1 + sigma theta), "lognormal"
(factor exp(sigma theta), theta unit normal) or "gamma" (factor f = 1 + sigma theta with a Poisson
auxiliary measurement of tau = 1/sigma^2, a gamma prior of mean 1 and relative width sigma). An optional
"correlation": [[1, rho, ...], ...] (K x K, unit diagonal, positive definite) correlates the Gaussian and
lognormal nuisances' unit-normal constraints; gamma nuisances cannot be correlated.
multibin-limit input: {"bins": [{"n": 5, "b": 3.2, "s": 1.0}, ...], "cl": 0.95,
  "background_uncertainty": {"kind": "none" | "independent" | "common_scale", "sigma": [per-bin
  absolute sigma_b] (independent) | fractional scalar (common_scale)}}; "s" is the signal
  expected in the bin per unit mu.

Usage (from the skill directory):
  python3 core/stats/likelihood_limits.py profile-limit --n 5 --b 3 --sigma-b 1 --cl 0.95 --toys 4000 --seed 1
  python3 core/stats/likelihood_limits.py profile-significance --n 15 --b 8 --sigma-b 2 --toys 20000 --seed 1
  python3 core/stats/likelihood_limits.py multibin-limit --input bins.json --toys 500 --seed 1
  python3 core/stats/likelihood_limits.py profile-fc --n 3 --b 3 --sigma-b 1 --cl 0.90 --toys 1000 --seed 1
  python3 core/stats/likelihood_limits.py profile-cls --n 3 --b 3 --sigma-b 1 --toys 1000 --expected-toys 60 --seed 1
  python3 core/stats/likelihood_limits.py shape-limit --input shapes.json --toys 100 --seed 1
  python3 core/stats/likelihood_limits.py neyman-limit --n 3 --b 3 --sigma-b 2 --cl 0.95 --beta 0.01 --toys 1000 --seed 1
  python3 core/stats/likelihood_limits.py neyman-coverage --s 2 --b 3 --sigma-b 2 --cl 0.95 --outer 300 --inner 200 --seed 1
Exit codes: 0 ok; 2 rejected input. Standard library only.
Importable: profile_limit, profile_significance, multibin_limit, profile_fc, profile_cls, shape_limit, neyman_limit, neyman_coverage,
neyman_coverage_scan.
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
from statistics import NormalDist
from typing import Any

from core.stats import _validate
from core.stats._linalg import bisect, cholesky, solve
from core.stats._poisson import MAX_MEAN, ppf

LABEL = "[General method]"
NEG = -1e300


class LikelihoodError(ValueError):
    """Raised for invalid counts, backgrounds, seeds, toy numbers or model files."""


def _num(x, name, low=None, high=None, strict_low=False) -> float:
    return _validate.number(x, name, low, high, strict_low, error=LikelihoodError)


def _solve(a, b):
    return solve(a, b, error=LikelihoodError, what="matrix in the profile fit")


def _seed_toys(toys, seed, allow_zero=False) -> tuple[int, int]:
    seed = _validate.seed(seed, error=LikelihoodError)
    return _validate.toy_count(toys, 100, 100000, error=LikelihoodError, allow_zero=allow_zero), seed


def _ppf(u: float, mu: float) -> int:
    """Poisson quantile (inversion of one uniform; exact up to MAX_MEAN)."""
    return ppf(u, mu)


def _lnl(n: float, mu: float) -> float:
    if mu <= 0.0:
        return 0.0 if n == 0 else NEG
    return (n * math.log(mu) if n > 0 else 0.0) - mu


# ------------------------------------------------------------------- single bin
def _b_hat(n: float, s: float, b0: float, sig: float) -> float:
    """Profiled background for Poisson(n | s + b) x Normal(b0 | b, sig)."""
    if sig == 0.0:
        return b0
    a = sig * sig + s - b0
    c = s * (sig * sig - b0) - n * sig * sig
    return max((-a + math.sqrt(max(a * a - 4.0 * c, 0.0))) / 2.0, 0.0)


def _ll1(n: float, s: float, b: float, b0: float, sig: float) -> float:
    return _lnl(n, s + b) - ((b - b0) ** 2 / (2.0 * sig * sig) if sig > 0 else 0.0)


def _q1(n: float, b0: float, sig: float, s: float) -> float:
    """One-sided boundary statistic q-tilde_s (0 when the best-fit signal exceeds s). The maximum is over s >= 0 and
    b >= 0, so an auxiliary observation b0 < 0 (possible under its Gaussian model) gives s_hat = n, b_hat = 0."""
    b_pos = max(b0, 0.0)
    s_hat = n - b_pos if n >= b_pos else 0.0
    if s_hat > s:
        return 0.0
    ll_max = _ll1(n, s_hat, _b_hat(n, s_hat, b0, sig), b0, sig)
    return max(0.0, 2.0 * (ll_max - _ll1(n, s, _b_hat(n, s, b0, sig), b0, sig)))


def _q0(n: float, b0: float, sig: float) -> float:
    """Discovery statistic q0 (0 when the best-fit signal is not positive)."""
    s_hat = n - b0
    if s_hat <= 0.0:
        return 0.0
    ll_max = _ll1(n, s_hat, b0, b0, sig)
    return max(0.0, 2.0 * (ll_max - _ll1(n, 0.0, _b_hat(n, 0.0, b0, sig), b0, sig)))


def _inputs1(n, b, sigma_b):
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise LikelihoodError(f"n must be a non-negative integer, got {n!r}")
    return n, _num(b, "b", 0.0, 200.0), _num(sigma_b, "sigma_b", 0.0, 100.0)


def _bisect(f, lo: float, hi: float, iters: int = 80) -> float:
    """Root of an increasing f on [lo, hi]; a root beyond hi is refused, not reported as hi."""
    return bisect(f, lo, hi, iters, increasing=True, error=LikelihoodError, what="the limit")


def _toy_p1(n_obs, b0, sig, s, uniforms, gauss) -> float:
    q_obs = _q1(n_obs, b0, sig, s)
    bh = _b_hat(n_obs, s, b0, sig)
    hits = 0
    for u, z in zip(uniforms, gauss):
        nn = _ppf(u, s + bh)
        bb = max(bh + sig * z, 0.0) if sig > 0 else bh
        hits += _q1(nn, bb, sig, s) >= q_obs - 1e-12
    return hits / len(uniforms)


def profile_limit(n: int, b: float, sigma_b: float, cl: float, toys: int, seed: int) -> dict:
    n, b, sig = _inputs1(n, b, sigma_b)
    cl = _num(cl, "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    toys, seed = _seed_toys(toys, seed)
    z = NormalDist().inv_cdf(cl)
    s_hat = max(n - b, 0.0)
    hi = s_hat + 20.0 * (math.sqrt(n + 1.0) + sig) + 20.0
    if hi + b + 6.0 * sig > MAX_MEAN:
        raise LikelihoodError(f"inputs reach a mean above the script's range ({MAX_MEAN:g})")
    s_asym = _bisect(lambda s: _q1(n, b, sig, s) - z * z, s_hat, hi)
    rng = random.Random(seed)
    uniforms = [rng.random() for _ in range(toys)]
    gauss = [rng.gauss(0.0, 1.0) for _ in range(toys)]
    alpha = 1.0 - cl
    s_toy = _bisect(lambda s: alpha - _toy_p1(n, b, sig, s, uniforms, gauss), s_hat, hi, 30)
    out = {"label": LABEL, "method": "profile-likelihood upper limit on s, single bin, Gaussian-constrained background",
           "n_obs": n, "b": b, "sigma_b": sig, "cl": cl, "toys": toys, "seed": seed,
           "asymptotic_upper_limit": s_asym, "toy_calibrated_upper_limit": s_toy,
           "asymptotic_over_toy": s_asym / s_toy if s_toy > 0 else None}
    if sig == 0.0:
        from core.stats.poisson_diagnostics import upper_limit
        exact = upper_limit(n, b, cl)["upper_limit_on_signal"]
        out["exact_classical_upper_limit"] = exact
    out["note"] = ("the asymptotic limit uses q-tilde = z^2 (z = Phi^-1(cl)) and is poor at small counts; the toy limit "
                   "calibrates q-tilde with seeded toys generated at the conditional (profiled) background and a "
                   "Gaussian auxiliary measurement, uses common random numbers across the scan (a step-wise, "
                   "toy-noise-limited estimate), and is a profile construction without CLs protection: a downward "
                   "fluctuation can give a limit that excludes signals the experiment cannot test, so also "
                   "report the expected sensitivity (cls-limit in poisson_diagnostics.py for a counting experiment)")
    return out


def profile_significance(n: int, b: float, sigma_b: float, toys: int, seed: int) -> dict:
    n, b, sig = _inputs1(n, b, sigma_b)
    if b <= 0.0:
        raise LikelihoodError("b must be > 0 for the discovery statistic")
    toys, seed = _seed_toys(toys, seed)
    q_obs = _q0(n, b, sig)
    bh = _b_hat(n, 0.0, b, sig)
    rng = random.Random(seed)
    hits = zero = 0
    for _ in range(toys):
        nn = _ppf(rng.random(), bh)
        bb = max(bh + sig * rng.gauss(0.0, 1.0), 0.0) if sig > 0 else bh
        q = _q0(nn, bb, sig)
        hits += q >= q_obs - 1e-12
        zero += q == 0.0
    z = math.sqrt(q_obs)
    out = {"label": LABEL, "method": "profile-likelihood q0 with a Gaussian-constrained background, seeded toys",
           "n_obs": n, "b": b, "sigma_b": sig, "toys": toys, "seed": seed, "q0_observed": q_obs,
           "p_value_toys": hits / toys, "binomial_error_on_p_toys": math.sqrt(max(hits / toys * (1 - hits / toys), 0) / toys),
           "p_value_half_chi2_asymptotic": 0.5 * math.erfc(z / math.sqrt(2.0)) if q_obs > 0 else 0.5,
           "p_value_naive_wilks_chi2_1dof": math.erfc(z / math.sqrt(2.0)) if q_obs > 0 else 1.0,
           "fraction_toys_with_q0_zero": zero / toys}
    if sig == 0.0:
        from core.stats.poisson_diagnostics import log_poisson_sf, z_from_log_p
        log_p = log_poisson_sf(n, b)  # summed in the tail: 1 - P(N <= n - 1) cancels to 0 below about 1e-16
        out["p_value_exact_poisson"] = math.exp(log_p)
        out["log_p_value_exact_poisson"] = log_p
        out["significance_exact_poisson_z"] = z_from_log_p(log_p)
    out["note"] = ("toys are generated at s = 0 with the profiled background and a Gaussian auxiliary measurement; the "
                   "p-value is local, with no trial factor; a significance quoted from naive Wilks is wrong near the "
                   "boundary; the Gaussian constraint treats the background uncertainty as symmetric and unbounded, "
                   "which is a poor model for a large sigma_b/b (use a gamma or log-normal constraint then)")
    return out


# ------------------------------------------------------------- asymptotic CLs and expected bands
BANDS = (("-2sigma", -2), ("-1sigma", -1), ("median", 0), ("+1sigma", 1), ("+2sigma", 2))


def _cls_asymptotic(q: float, qa: float) -> float:
    """Asymptotic CLs = p_mu / (1 - p_b) for the one-sided q-tilde (Cowan, Cranmer, Gross, Vitells 2011, eqs. 65-66):
    q is q-tilde on the data, qa on the background-only Asimov data set."""
    nd = NormalDist()
    if qa <= 0.0:
        return 1.0
    ra = math.sqrt(qa)
    if q <= qa:
        r = math.sqrt(max(q, 0.0))
        p_mu, one_minus_pb = 1.0 - nd.cdf(r), nd.cdf(ra - r)
    else:
        p_mu, one_minus_pb = 1.0 - nd.cdf((q + qa) / (2.0 * ra)), 1.0 - nd.cdf((q - qa) / (2.0 * ra))
    return p_mu / one_minus_pb if one_minus_pb > 0.0 else 1.0


def _root_increasing(f, lo: float, hi: float, tol: float = 1e-7, max_iter: int = 100) -> float:
    """Root of an increasing f with f(lo) < 0 by the Illinois method; hi is doubled until f(hi) > 0 (at most 20 times)."""
    flo, fhi = f(lo), f(hi)
    for _ in range(20):
        if fhi > 0.0:
            break
        lo, flo, hi = hi, fhi, 2.0 * hi
        fhi = f(hi)
    else:
        raise LikelihoodError("the expected limit lies beyond the scan range")
    side = 0
    for _ in range(max_iter):
        x = hi - fhi * (hi - lo) / (fhi - flo)
        fx = f(x)
        if abs(fx) < 1e-12 or (hi - lo) < tol * max(1.0, abs(x)):
            return x
        if fx > 0.0:
            hi, fhi = x, fx
            if side == 1:
                flo *= 0.5
            side = 1
        else:
            lo, flo = x, fx
            if side == -1:
                fhi *= 0.5
            side = -1
    return 0.5 * (lo + hi)


def _asymptotic_cls_results(q_obs, q_asimov, cl: float, hi: float) -> dict:
    """Observed asymptotic CLs limit and the expected limits under background only from the Asimov data set.
    q_obs(mu) and q_asimov(mu) give q-tilde at mu on the data and on the Asimov data. The expected limit of band N
    solves sqrt(q_asimov(mu)) = Phi^-1(1 - alpha Phi(N)) + N for CLs (Cowan et al. 2011, sec. 4.3, with
    sigma = mu / sqrt(q_asimov(mu)) taken at the band's own mu). For CLs+b with q-tilde it is z + N for N >= 0 and, below
    the median, where the band's mu-hat = N sigma is negative and q-tilde = (mu^2 - 2 mu mu-hat) / sigma^2 (their eq. 16),
    N + sqrt(N^2 + z^2) with z = Phi^-1(cl); the plain z + N would reach 0, which a q-tilde limit never does. For CLs
    the q-tilde and q forms agree for every N."""
    nd, alpha = NormalDist(), 1.0 - cl
    obs = _root_increasing(lambda m: alpha - _cls_asymptotic(q_obs(m), q_asimov(m)), 0.0, hi)
    bands: dict[str, dict[str, float]] = {"cls": {}, "clsb": {}}
    for name, k in BANDS:
        z = nd.inv_cdf(cl)
        for kind, target in (("cls", nd.inv_cdf(1.0 - alpha * nd.cdf(k)) + k),
                             ("clsb", z + k if k >= 0 else k + math.sqrt(k * k + z * z))):
            bands[kind][name] = _root_increasing(lambda m: math.sqrt(q_asimov(m)) - target, 0.0, hi)
    return {"asymptotic_observed_cls_upper_limit": obs, "asymptotic_expected_limits": bands}


# --------------------------------------------------------------------- multibin
class _Model:
    def __init__(self, bins, kind, sigma):
        self.n_bins = len(bins)
        self.s = [x["s"] for x in bins]
        self.b = [x["b"] for x in bins]
        self.kind, self.sigma = kind, sigma

    def aux_obs(self):
        return list(self.b) if self.kind == "independent" else ([1.0] if self.kind == "common_scale" else [])

    def _prof_nu(self, ns, aux, mu):
        """Profiled lnL at fixed mu, and the profiled nuisance values."""
        if self.kind == "none":
            return sum(_lnl(n, mu * s + b) for n, s, b in zip(ns, self.s, self.b)), []
        if self.kind == "independent":
            tot, hats = 0.0, []
            for n, s, b0, sg in zip(ns, self.s, aux, self.sigma):
                bh = _b_hat(n, mu * s, b0, sg)
                hats.append(bh)
                tot += _ll1(n, mu * s, bh, b0, sg)
            return tot, hats
        sg, th0 = self.sigma, aux[0]

        def deriv(t):
            return sum((n * b / (mu * s + t * b) - b) if (mu * s + t * b) > 0 else (-b if n == 0 else 1e12)
                       for n, s, b in zip(ns, self.s, self.b)) - (t - th0) / (sg * sg)

        lo, hi = 0.0, th0 + 12.0 * sg + 5.0
        if deriv(lo) <= 0:
            t = 0.0
        else:
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if deriv(mid) > 0 else (lo, mid)
            t = 0.5 * (lo + hi)
        tot = sum(_lnl(n, mu * s + t * b) for n, s, b in zip(ns, self.s, self.b)) - (t - th0) ** 2 / (2 * sg * sg)
        return tot, [t]

    def fit(self, ns, aux):
        """Global maximum over mu >= 0 (golden section of the profiled lnL)."""
        mu_max = (sum(ns) + 10.0 * math.sqrt(sum(ns) + 1.0) + 20.0) / max(sum(self.s), 1e-12) * 5.0
        lo, hi, g = 0.0, mu_max, (math.sqrt(5) - 1) / 2
        x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
        f1, f2 = self._prof_nu(ns, aux, x1)[0], self._prof_nu(ns, aux, x2)[0]
        for _ in range(70):
            if f1 < f2:
                lo, x1, f1 = x1, x2, f2
                x2 = lo + g * (hi - lo)
                f2 = self._prof_nu(ns, aux, x2)[0]
            else:
                hi, x2, f2 = x2, x1, f1
                x1 = hi - g * (hi - lo)
                f1 = self._prof_nu(ns, aux, x1)[0]
        mu_hat = 0.5 * (lo + hi)
        f0 = self._prof_nu(ns, aux, 0.0)[0]
        fm = self._prof_nu(ns, aux, mu_hat)[0]
        return (0.0, f0) if f0 >= fm else (mu_hat, fm)

    def q(self, ns, aux, mu, fit=None):
        mu_hat, ll_max = fit if fit else self.fit(ns, aux)
        if mu_hat > mu:
            return 0.0
        return max(0.0, 2.0 * (ll_max - self._prof_nu(ns, aux, mu)[0]))


def _load_model(doc):
    if not isinstance(doc, dict):
        raise LikelihoodError("input must be a JSON object")
    raw = doc.get("bins")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise LikelihoodError("bins must be a list of 1 to 50 bins")
    bins = []
    for i, x in enumerate(raw):
        if not isinstance(x, dict):
            raise LikelihoodError(f"bin {i} must be an object with n, b, s")
        n = x.get("n")
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 or n != int(n):
            raise LikelihoodError(f"bin {i}: n must be a non-negative integer")
        bins.append({"n": int(n), "b": _num(x.get("b"), f"bin {i} b", 0.0, 200.0), "s": _num(x.get("s"), f"bin {i} s", 0.0, 1e6)})
    if sum(x["s"] for x in bins) <= 0:
        raise LikelihoodError("at least one bin needs a positive signal expectation s")
    if sum(x["n"] for x in bins) > 400:
        raise LikelihoodError("total counts above 400 are outside this script's range")
    unc = doc.get("background_uncertainty", {"kind": "none"})
    kind = unc.get("kind") if isinstance(unc, dict) else None
    if kind not in ("none", "independent", "common_scale"):
        raise LikelihoodError("background_uncertainty.kind must be none, independent or common_scale")
    sigma = None
    if kind == "independent":
        sg = unc.get("sigma")
        if not isinstance(sg, list) or len(sg) != len(bins):
            raise LikelihoodError("independent needs one sigma per bin")
        sigma = [_num(v, "sigma", 0.0, 100.0) for v in sg]
    elif kind == "common_scale":
        sigma = _num(unc.get("sigma"), "sigma", 0.0, 2.0, strict_low=True)
    return bins, kind, sigma


def _limit_model(model, ns, aux, z):
    mu_hat, _ = fit = model.fit(ns, aux)
    hi = mu_hat + 30.0 * (math.sqrt(sum(ns) + 1.0) + 1.0) / max(sum(model.s), 1e-12) + 20.0 / max(sum(model.s), 1e-12)
    return _bisect(lambda m: model.q(ns, aux, m, fit) - z * z, mu_hat, hi, 70)


def multibin_limit(doc: dict, cl: float, toys: int, seed: int) -> dict:
    bins, kind, sigma = _load_model(doc)
    cl = _num(doc.get("cl", cl), "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    toys, seed = _seed_toys(toys, seed, allow_zero=True)
    model = _Model(bins, kind, sigma)
    ns = [x["n"] for x in bins]
    aux = model.aux_obs()
    z = NormalDist().inv_cdf(cl)
    obs = _limit_model(model, ns, aux, z)
    asimov = _limit_model(model, [x["b"] for x in bins], aux, z)
    mu_hat, _ = fit_obs = model.fit(ns, aux)
    asimov_ns = [x["b"] for x in bins]
    fit_a = model.fit(asimov_ns, aux)
    out = {"label": LABEL, "method": "multi-bin profile-likelihood upper limit on mu, shared signal strength",
           "bins": len(bins), "background_uncertainty": kind, "cl": cl, "seed": seed, "toys": toys,
           "best_fit_mu": mu_hat, "asymptotic_observed_upper_limit": obs,
           "asymptotic_asimov_median_expected_limit": asimov}
    out.update(_asymptotic_cls_results(lambda m: model.q(ns, aux, m, fit_obs), lambda m: model.q(asimov_ns, aux, m, fit_a),
                                       cl, max(obs, asimov, 1e-6) * 2.0))
    if toys:
        q_obs = model.q(ns, aux, obs)
        _, cond = model._prof_nu(ns, aux, obs)
        rng = random.Random(seed)
        hits = 0
        for _ in range(toys):
            if kind == "none":
                means = [obs * s + b for s, b in zip(model.s, model.b)]
                a = []
            elif kind == "independent":
                means = [obs * s + c for s, c in zip(model.s, cond)]
                a = [max(c + sg * rng.gauss(0, 1), 0.0) for c, sg in zip(cond, sigma)]
            else:
                means = [obs * s + cond[0] * b for s, b in zip(model.s, model.b)]
                a = [max(cond[0] + sigma * rng.gauss(0, 1), 0.0)]
            nn = [_ppf(rng.random(), m) for m in means]
            hits += model.q(nn, a, obs) >= q_obs - 1e-12
        p = hits / toys
        out["toy_p_value_at_asymptotic_limit"] = p
        out["binomial_error_on_p"] = math.sqrt(max(p * (1 - p), 0.0) / toys)
        out["target_p_value"] = 1.0 - cl
    out["note"] = ("asymptotic results rely on q-tilde ~ half-chi2; the toy p-value at the asymptotic limit is the "
                   "calibration check (it should be near 1 - cl; a p-value far from it means the asymptotic limit "
                   "is mis-calibrated here); asymptotic_observed_upper_limit is the CLs+b-type limit (q-tilde = z^2) and "
                   "asymptotic_observed_cls_upper_limit the asymptotic CLs limit; asymptotic_expected_limits gives the "
                   "median and 1/2-sigma expected limits under background only for both, from the Asimov data set; the Gaussian nuisances are symmetric, a common-scale nuisance multiplies the "
                   "nominal backgrounds, bins are independent Poisson, and shape uncertainties are not modeled")
    return out


# ---------------------------------------------------------------- profile FC and CLs
def _t1(n: float, b0: float, sig: float, s: float) -> float:
    """Two-sided profile-likelihood-ratio statistic t_s (boundary s >= 0 respected)."""
    s_hat = n - b0 if n >= b0 else 0.0
    ll_max = _ll1(n, s_hat, _b_hat(n, s_hat, b0, sig), b0, sig)
    return max(0.0, 2.0 * (ll_max - _ll1(n, s, _b_hat(n, s, b0, sig), b0, sig)))


def _draws(rng, toys):
    return [rng.random() for _ in range(toys)], [rng.gauss(0.0, 1.0) for _ in range(toys)]


def profile_fc(n: int, b: float, sigma_b: float, cl: float, toys: int, seed: int, step: float | None = None) -> dict:
    n, b, sig = _inputs1(n, b, sigma_b)
    cl = _num(cl, "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    toys, seed = _seed_toys(toys, seed)
    s_max = max(n - b, 0.0) + 6.0 * (math.sqrt(n + 1.0) + sig) + 8.0
    step = max(s_max / 150.0, 0.02) if step is None else _num(step, "step", 0.0, 5.0, strict_low=True)
    if s_max + b + 6.0 * sig > MAX_MEAN:
        raise LikelihoodError(f"inputs reach a mean above the script's range ({MAX_MEAN:g})")
    rng = random.Random(seed)
    uniforms, gauss = _draws(rng, toys)
    idx = min(toys - 1, int(math.ceil(cl * toys)) - 1)
    accepted, k = [], 0
    while k * step <= s_max:
        s = k * step
        t_obs = _t1(n, b, sig, s)
        bh = _b_hat(n, s, b, sig)
        ts = sorted(_t1(_ppf(u, s + bh), max(bh + sig * z, 0.0) if sig > 0 else bh, sig, s) for u, z in zip(uniforms, gauss))
        if t_obs <= ts[idx] + 1e-12:
            accepted.append(s)
        k += 1
    if not accepted:
        raise LikelihoodError("no signal value was accepted in the scan range; check inputs")
    gaps = sum(1 for a, c in zip(accepted, accepted[1:]) if c - a > 1.5 * step)
    return {"label": LABEL, "method": "Feldman-Cousins-style interval with the nuisance profiled (profile construction), seeded toys",
            "n_obs": n, "b": b, "sigma_b": sig, "cl": cl, "toys": toys, "seed": seed, "grid_step": step,
            "lower": accepted[0], "upper": accepted[-1], "lower_is_zero": accepted[0] == 0.0,
            "disjoint_segments": gaps + 1,
            "note": ("for each s the critical value of the two-sided profile-likelihood ratio is the CL quantile of toys "
                     "generated at the background profiled on the observed data (a profile construction, which does not "
                     "guarantee coverage over all true backgrounds), with the Gaussian auxiliary measurement redrawn; "
                     "common random numbers keep the scan smooth, the interval is toy-noise limited by about "
                     "1/sqrt(toys) in the quantile and one grid step in the edges; for sigma_b = 0 it reduces to the "
                     "Feldman-Cousins construction; a lower edge of 0 is expected behavior; more than one disjoint "
                     "segment signals toy noise, a coarse grid or more toys needed")}


def _cls_at(n_obs, b0, sig, s, q_pool_b_uniforms, q_pool_gauss, uniforms, gauss) -> tuple[float, float, float]:
    q_obs = _q1(n_obs, b0, sig, s)
    bh_s, bh_0 = _b_hat(n_obs, s, b0, sig), _b_hat(n_obs, 0.0, b0, sig)
    sb = sum(_q1(_ppf(u, s + bh_s), max(bh_s + sig * z, 0.0) if sig > 0 else bh_s, sig, s) >= q_obs - 1e-12
             for u, z in zip(uniforms, gauss)) / len(uniforms)
    bo = sum(_q1(_ppf(u, bh_0), max(bh_0 + sig * z, 0.0) if sig > 0 else bh_0, sig, s) >= q_obs - 1e-12
             for u, z in zip(q_pool_b_uniforms, q_pool_gauss)) / len(q_pool_b_uniforms)
    return sb, bo, (sb / max(bo, 1.0 / len(q_pool_b_uniforms)))


def _cls_limit(n_obs, b0, sig, cl, u1, g1, u2, g2, hi, iters=18):
    lo, up = max(n_obs - b0, 0.0), hi
    for _ in range(iters):
        mid = 0.5 * (lo + up)
        lo, up = (mid, up) if _cls_at(n_obs, b0, sig, mid, u2, g2, u1, g1)[2] > 1.0 - cl else (lo, mid)
    return 0.5 * (lo + up)


def profile_cls(n: int, b: float, sigma_b: float, cl: float, toys: int, expected_toys: int, seed: int) -> dict:
    n, b, sig = _inputs1(n, b, sigma_b)
    cl = _num(cl, "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    toys, seed = _seed_toys(toys, seed)
    if isinstance(expected_toys, bool) or not isinstance(expected_toys, int) or not (expected_toys == 0 or 10 <= expected_toys <= 2000):
        raise LikelihoodError("expected_toys must be 0 or an integer in [10, 2000]")
    hi = max(n - b, 0.0) + 8.0 * (math.sqrt(n + 1.0) + sig) + 10.0
    if hi + b + 6.0 * sig > MAX_MEAN:
        raise LikelihoodError(f"inputs reach a mean above the script's range ({MAX_MEAN:g})")
    rng = random.Random(seed)
    u1, g1 = _draws(rng, toys)
    u2, g2 = _draws(rng, toys)
    obs = _cls_limit(n, b, sig, cl, u1, g1, u2, g2, hi)
    expected = {}
    if expected_toys:
        inner = min(toys, 300)
        ui1, gi1, ui2, gi2 = u1[:inner], g1[:inner], u2[:inner], g2[:inner]
        limits = []
        for _ in range(expected_toys):
            nn = _ppf(rng.random(), b)
            bb0 = max(b + sig * rng.gauss(0.0, 1.0), 0.0) if sig > 0 else b
            h = max(nn - bb0, 0.0) + 8.0 * (math.sqrt(nn + 1.0) + sig) + 10.0
            limits.append(_cls_limit(nn, bb0, sig, cl, ui1, gi1, ui2, gi2, h))
        limits.sort()
        q = lambda f: limits[min(len(limits) - 1, max(0, int(round(f * len(limits))) - 1))]
        expected = {"-2sigma": q(0.025), "-1sigma": q(0.16), "median": q(0.5), "+1sigma": q(0.84), "+2sigma": q(0.975),
                    "pseudo_experiments": expected_toys, "inner_toys": inner}
    out = {"label": LABEL, "method": "CLs upper limit with the background nuisance profiled, seeded toys of q-tilde",
           "n_obs": n, "b": b, "sigma_b": sig, "cl": cl, "toys": toys, "seed": seed, "observed_upper_limit": obs}
    if expected:
        out["expected_under_background_only"] = expected
    out["note"] = ("both CLs+b and CLb come from toys of the one-sided profile statistic with the nuisance fixed at its "
                   "profiled value for the observed data (a profile construction, not a coverage guarantee); the observed "
                   "limit is a toy-noise-limited estimate from common random numbers and an 18-step scan; the expected "
                   "limits come from background-only pseudo-experiments drawn at the stated b with the auxiliary "
                   "measurement redrawn and use at most 300 inner toys each, so they are coarser than the observed "
                   "limit; CLs over-covers by design; the background is modeled as Gaussian-constrained and bins are "
                   "single (use shape-limit for several nuisances)")
    return out


# ------------------------------------------------------------- shape and multi-nuisance
def _newton_min(f, x0, fixed_first: bool = False, max_iter: int = 60):
    """Minimize f over x (damped Newton, numerical derivatives). With fixed_first the first coordinate is held."""
    x = list(x0)
    free = list(range(1 if fixed_first else 0, len(x)))
    fx = f(x)
    lam = 1e-3
    for _ in range(max_iter):
        h = {i: 1e-4 * max(1.0, abs(x[i])) for i in free}

        def at(d):
            z = list(x)
            for i, v in d.items():
                z[i] += v
            return f(z)
        g = [(at({i: h[i]}) - at({i: -h[i]})) / (2 * h[i]) for i in free]
        hess = [[0.0] * len(free) for _ in free]
        for a, i in enumerate(free):
            hess[a][a] = (at({i: h[i]}) - 2 * fx + at({i: -h[i]})) / h[i] ** 2
            for b2 in range(a + 1, len(free)):
                j = free[b2]
                v = (at({i: h[i], j: h[j]}) - at({i: h[i], j: -h[j]}) - at({i: -h[i], j: h[j]}) + at({i: -h[i], j: -h[j]})) / (4 * h[i] * h[j])
                hess[a][b2] = hess[b2][a] = v
        improved = False
        for _try in range(12):
            try:
                step = _solve([[hess[a][c] + (lam * (1 + abs(hess[a][a])) if a == c else 0.0) for c in range(len(free))] for a in range(len(free))],
                              [[-v] for v in g])
            except Exception:
                lam *= 10.0
                continue
            z = list(x)
            for a, i in enumerate(free):
                z[i] += step[a][0]
            fz = f(z)
            if fz < fx:
                dx = max(abs(step[a][0]) for a in range(len(free)))
                x, fx, lam, improved = z, fz, max(lam / 5.0, 1e-9), True
                break
            lam *= 10.0
        if not improved or dx < 1e-9:
            break
    return x, fx


def _code4_coefficients(hi: float, lo: float) -> list[float]:
    """a_1..a_6 of f(theta) = 1 + sum a_i theta^i, matching hi^theta and lo^-theta with their first and second
    derivatives at theta = +1 and -1 (HistFactory interpolation code 4)."""
    lh, ll_ = math.log(hi), math.log(lo)
    rows = [[1.0] * 6, [(-1.0) ** i for i in range(1, 7)], [float(i) for i in range(1, 7)],
            [i * (-1.0) ** (i - 1) for i in range(1, 7)], [float(i * (i - 1)) for i in range(1, 7)],
            [i * (i - 1) * (-1.0) ** (i - 2) for i in range(1, 7)]]
    rhs = [hi - 1.0, lo - 1.0, hi * lh, -lo * ll_, hi * lh * lh, lo * ll_ * ll_]
    return [r[0] for r in _solve(rows, [[v] for v in rhs])]


def _interp_norm(theta: float, d: dict) -> float:
    """Normalization factor at theta for asymmetric factors hi (theta = +1) and lo (theta = -1)."""
    hi, lo, code = d["hi"], d["lo"], d["interpolation"]
    if code == "code0":
        return 1.0 + theta * ((hi - 1.0) if theta >= 0 else (1.0 - lo))
    if code == "code1" or abs(theta) >= 1.0:
        return hi ** theta if theta >= 0 else lo ** (-theta)
    return 1.0 + sum(a * theta ** (i + 1) for i, a in enumerate(d["c4"]))


def _interp_shape(theta: float, nom: float, up: float, down: float, code: str) -> float:
    """Additive shift of one bin at theta (code0: piecewise linear; code4p: polynomial inside |theta| < 1)."""
    if code == "code4p" and abs(theta) < 1.0:
        s, a = 0.5 * ((up - nom) + (nom - down)), 0.0625 * ((up - nom) - (nom - down))
        t2 = theta * theta
        return theta * s + t2 * (t2 * (3.0 * t2 - 10.0) + 15.0) * a
    return theta * ((up - nom) if theta >= 0 else (nom - down))


def _load_shape(doc):
    if not isinstance(doc, dict):
        raise LikelihoodError("input must be a JSON object")
    raw = doc.get("bins")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 40:
        raise LikelihoodError("bins must be a list of 1 to 40 bins")
    bins = []
    for i, x in enumerate(raw):
        if not isinstance(x, dict):
            raise LikelihoodError(f"bin {i} must be an object with n, b, s")
        n = x.get("n")
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 or n != int(n):
            raise LikelihoodError(f"bin {i}: n must be a non-negative integer")
        bins.append({"n": int(n), "b": _num(x.get("b"), f"bin {i} b", 0.0, 200.0), "s": _num(x.get("s"), f"bin {i} s", 0.0, 1e6)})
    if sum(x["s"] for x in bins) <= 0:
        raise LikelihoodError("at least one bin needs a positive signal expectation s")
    if sum(x["n"] for x in bins) > 400:
        raise LikelihoodError("total counts above 400 are outside this script's range")
    nuis = doc.get("nuisances", [])
    if not isinstance(nuis, list) or len(nuis) > 8:
        raise LikelihoodError("nuisances must be a list of at most 8 entries")
    parsed = []
    for k, d in enumerate(nuis):
        if not isinstance(d, dict) or d.get("kind") not in ("background_norm", "signal_norm", "background_shape", "signal_shape"):
            raise LikelihoodError(f"nuisance {k}: kind must be background_norm, signal_norm, background_shape or signal_shape")
        if d["kind"].endswith("_norm") and ("hi" in d or "lo" in d):
            code = d.get("interpolation", "code4")
            if code not in ("code0", "code1", "code4"):
                raise LikelihoodError(f"nuisance {k}: interpolation of hi/lo factors must be code0, code1 or code4")
            if d.get("prior", "gaussian") != "gaussian" or "sigma" in d:
                raise LikelihoodError(f"nuisance {k}: hi/lo factors take the Gaussian constraint and no sigma")
            hi, lo = _num(d.get("hi"), "hi", 0.0, 10.0, strict_low=True), _num(d.get("lo"), "lo", 0.0, 10.0, strict_low=True)
            parsed.append({"kind": d["kind"], "prior": "gaussian", "hi": hi, "lo": lo, "interpolation": code,
                           "c4": _code4_coefficients(hi, lo)})
        elif d["kind"].endswith("_norm"):
            prior = d.get("prior", "gaussian")
            if prior not in ("gaussian", "lognormal", "gamma"):
                raise LikelihoodError(f"nuisance {k}: prior must be gaussian, lognormal or gamma")
            if "interpolation" in d:
                raise LikelihoodError(f"nuisance {k}: interpolation applies to hi/lo factors, not to sigma")
            parsed.append({"kind": d["kind"], "prior": prior, "sigma": _num(d.get("sigma"), "sigma", 0.0, 0.9, strict_low=True)})
        else:
            up, dn = d.get("up"), d.get("down")
            if not isinstance(up, list) or not isinstance(dn, list) or len(up) != len(bins) or len(dn) != len(bins):
                raise LikelihoodError(f"nuisance {k}: up and down must list {len(bins)} per-bin values")
            code = d.get("interpolation", "code0")
            if code not in ("code0", "code4p"):
                raise LikelihoodError(f"nuisance {k}: shape interpolation must be code0 or code4p")
            parsed.append({"kind": d["kind"], "up": [_num(v, "up", 0.0, 1e6) for v in up], "down": [_num(v, "down", 0.0, 1e6) for v in dn],
                           "interpolation": code})
        parsed[-1]["name"] = str(d.get("name", f"nuisance{k}"))
    corr = doc.get("correlation")
    corr_chol = None
    if corr is not None:
        kk = len(parsed)
        if not isinstance(corr, list) or len(corr) != kk or any(not isinstance(r, list) or len(r) != kk for r in corr):
            raise LikelihoodError(f"correlation must be a {kk} x {kk} matrix")
        corr = [[_num(v, "correlation", -1.0, 1.0) for v in r] for r in corr]
        for i in range(kk):
            if abs(corr[i][i] - 1.0) > 1e-9:
                raise LikelihoodError("correlation must have a unit diagonal")
            for j in range(i):
                if abs(corr[i][j] - corr[j][i]) > 1e-9:
                    raise LikelihoodError("correlation must be symmetric")
        if any(d.get("prior") == "gamma" for d in parsed):
            raise LikelihoodError("gamma nuisances cannot be correlated; remove the correlation or the gamma prior")
        corr_chol = _chol_pd(corr)
    return bins, parsed, corr_chol


def _chol_pd(c):
    return cholesky(c, "correlation matrix of the nuisances", error=LikelihoodError)[0]


class _ShapeModel:
    def __init__(self, bins, nuis, corr_chol=None):
        self.n = [x["n"] for x in bins]
        self.b = [x["b"] for x in bins]
        self.s = [x["s"] for x in bins]
        self.nuis = nuis
        self.k = len(nuis)
        self.chol = corr_chol
        self.gamma = [d["kind"].endswith("_norm") and d.get("prior") == "gamma" for d in nuis]
        self.tau = [1.0 / d["sigma"] ** 2 if g else 0.0 for d, g in zip(nuis, self.gamma)]

    def aux_obs(self):
        return [t if g else 0.0 for g, t in zip(self.gamma, self.tau)]

    def _factor(self, d, t):
        if "hi" in d:
            return _interp_norm(t, d)
        if d["kind"].endswith("_norm") and d.get("prior") == "lognormal":
            return math.exp(d["sigma"] * t)
        return 1.0 + d["sigma"] * t

    def constraint(self, th, aux):
        if self.k == 0:
            return 0.0
        total = 0.0
        gauss_idx = [i for i in range(self.k) if not self.gamma[i]]
        if self.chol is not None:
            r = [th[i] - aux[i] for i in range(self.k)]
            # solve L y = r, then 0.5 |y|^2 = 0.5 r^T C^-1 r
            y = []
            for i in range(self.k):
                y.append((r[i] - sum(self.chol[i][j] * y[j] for j in range(i))) / self.chol[i][i])
            total += 0.5 * sum(v * v for v in y)
        else:
            total += 0.5 * sum((th[i] - aux[i]) ** 2 for i in gauss_idx)
        for i in range(self.k):
            if self.gamma[i]:
                f = self._factor(self.nuis[i], th[i])
                if f <= 0.0:
                    return -NEG
                total -= aux[i] * math.log(f) - self.tau[i] * f
        return total

    def expected(self, mu, th):
        bs, ss = list(self.b), list(self.s)
        for t, d in zip(th, self.nuis):
            if d["kind"].endswith("_shape"):
                base = self.b if d["kind"] == "background_shape" else self.s
                tgt = bs if d["kind"] == "background_shape" else ss
                for i in range(len(base)):
                    tgt[i] += _interp_shape(t, base[i], d["up"][i], d["down"][i], d["interpolation"])
        for t, d in zip(th, self.nuis):
            if d["kind"] == "background_norm":
                f = self._factor(d, t)
                bs = [v * f for v in bs]
            elif d["kind"] == "signal_norm":
                f = self._factor(d, t)
                ss = [v * f for v in ss]
        return [mu * a + c for a, c in zip(ss, bs)]

    def nll(self, mu, th, ns, aux):
        total = 0.0
        if any(d["kind"].endswith("_norm") and self._factor(d, t) <= 0.0 for t, d in zip(th, self.nuis)):
            return -NEG
        for n, nu in zip(ns, self.expected(mu, th)):
            if nu <= 0.0:
                if n > 0:
                    return -NEG
                continue
            total -= (n * math.log(nu) if n > 0 else 0.0) - nu
        return total + self.constraint(th, aux)

    def cond(self, mu, ns, aux, start=None):
        th0 = list(start) if start else [0.0] * self.k
        if self.k == 0:
            return [], self.nll(mu, [], ns, aux)
        th, val = _newton_min(lambda x: self.nll(mu, x, ns, aux), th0)
        return th, val

    def glob(self, ns, aux):
        mu0 = max((sum(ns) - sum(self.b)) / max(sum(self.s), 1e-12), 0.1)
        x, val = _newton_min(lambda v: self.nll(v[0], v[1:], ns, aux), [mu0] + [0.0] * self.k)
        if x[0] < 0.0:
            th, val = self.cond(0.0, ns, aux, x[1:])
            return 0.0, th, val
        return x[0], x[1:], val

    def q(self, mu, ns, aux, g=None):
        mu_hat, _, val = g if g else self.glob(ns, aux)
        if mu_hat > mu:
            return 0.0
        return max(0.0, 2.0 * (self.cond(mu, ns, aux)[1] - val))


def _draw_aux(model, th_c, rng):
    """Auxiliary measurements at the conditional nuisance values: correlated normals, Poisson counts for gamma priors."""
    z = [rng.gauss(0.0, 1.0) for _ in range(model.k)]
    if model.chol is not None:
        z = [sum(model.chol[i][j] * z[j] for j in range(i + 1)) for i in range(model.k)]
    aux = []
    for i in range(model.k):
        if model.gamma[i]:
            aux.append(float(_ppf(rng.random(), model.tau[i] * model._factor(model.nuis[i], th_c[i]))))
        else:
            aux.append(th_c[i] + z[i])
    return aux


def shape_limit(doc: dict, cl: float, toys: int, seed: int) -> dict:
    bins, nuis, corr_chol = _load_shape(doc)
    cl = _num(doc.get("cl", cl), "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    toys, seed = _seed_toys(toys, seed, allow_zero=True)
    model = _ShapeModel(bins, nuis, corr_chol)
    z = NormalDist().inv_cdf(cl)
    aux0 = model.aux_obs()

    def limit(ns):
        g = model.glob(ns, aux0)
        hi = g[0] + 30.0 * (math.sqrt(sum(ns) + 1.0) + 1.0) / max(sum(model.s), 1e-12) + 20.0 / max(sum(model.s), 1e-12)
        return _bisect(lambda m: model.q(m, ns, aux0, g) - z * z, g[0], hi, 45), g
    obs, g_obs = limit(model.n)
    asimov_ns = [float(v) for v in model.b]
    asimov, g_a = limit(asimov_ns)
    out = {"label": LABEL, "method": "multi-bin profile-likelihood upper limit with normalization and shape nuisances",
           "bins": len(bins), "nuisances": [d["name"] for d in nuis], "cl": cl, "seed": seed, "toys": toys,
           "best_fit_mu": g_obs[0], "best_fit_nuisances": dict(zip([d["name"] for d in nuis], g_obs[1])),
           "asymptotic_observed_upper_limit": obs, "asymptotic_asimov_median_expected_limit": asimov}
    out.update(_asymptotic_cls_results(lambda m: model.q(m, model.n, aux0, g_obs), lambda m: model.q(m, asimov_ns, aux0, g_a),
                                       cl, max(obs, asimov, 1e-6) * 2.0))
    if toys:
        q_obs = model.q(obs, model.n, aux0, g_obs)
        th_c, _ = model.cond(obs, model.n, aux0)
        mean = model.expected(obs, th_c)
        rng = random.Random(seed)
        hits = 0
        for _ in range(toys):
            ns = [_ppf(rng.random(), m) for m in mean]
            aux = _draw_aux(model, th_c, rng)
            hits += model.q(obs, ns, aux) >= q_obs - 1e-12
        p = hits / toys
        out.update({"toy_p_value_at_asymptotic_limit": p, "binomial_error_on_p": math.sqrt(max(p * (1 - p), 0.0) / toys),
                    "target_p_value": 1.0 - cl})
    out["priors"] = {d["name"]: d.get("prior", "gaussian") for d in nuis}
    out["interpolation"] = {d["name"]: d["interpolation"] for d in nuis if "interpolation" in d}
    out["correlated_nuisances"] = corr_chol is not None
    out["note"] = ("every nuisance has a unit-width constraint on its parameter theta observed at 0 (Gaussian by default; a "
                   "normalization may be log-normal or gamma with a Poisson auxiliary measurement, and Gaussian-type "
                   "nuisances may carry a correlation matrix; toys redraw the auxiliary measurements, correlated for the "
                   "Gaussian ones and Poisson for gamma), "
                   "shapes use vertical interpolation between the down, nominal and up templates (piecewise linear by default, "
                   "smooth code4p on request; no bin-to-bin correlation beyond what the templates carry), normalizations "
                   "are linear (1 + sigma theta) unless log-normal, gamma or given as hi/lo factors (code4 by default), "
                   "and shape and normalization effects are applied additively then multiplicatively; the asymptotic result "
                   "relies on q-tilde ~ half-chi2, so check the toy p-value at the limit (it should be near 1 - cl); "
                   "asymptotic_observed_upper_limit is the CLs+b-type limit and asymptotic_observed_cls_upper_limit the "
                   "asymptotic CLs limit, with median and 1/2-sigma expected limits for both from the Asimov data set "
                   "(asymptotic_expected_limits); the profile is a "
                   "damped Newton search with numerical derivatives and is slow for many nuisances (toys cost a global "
                   "and a conditional fit each)")
    return out


# ------------------------------------------------------------ Berger-Boos construction (approximate implementation)
# Seeded coverage scans that passed (tests/core/test_stats_likelihood_limits.py, HEP_SLOW_TESTS=1; VALIDATION.md):
# every combination of these true values, with the outer/inner toy counts and grid points given here.
BB_VALIDATED_RANGE: dict[str, Any] = {"s": [0.0, 2.0, 5.0], "b": [1.0, 3.0, 8.0], "sigma_b": [0.5, 2.0], "cl": [0.9, 0.95], "beta": 0.01,
                      "outer": 600, "inner": 300, "points": 9}


def _in_validated_range(b, sig, cl, s=None) -> bool:
    r = BB_VALIDATED_RANGE
    ok = min(r["b"]) <= b <= max(r["b"]) and min(r["sigma_b"]) <= sig <= max(r["sigma_b"]) and cl in r["cl"]
    return ok and (s is None or min(r["s"]) <= s <= max(r["s"]))


def _coverage_claim(within: bool) -> dict:
    return {"construction": "Berger-Boos: coverage >= cl for every true background if the supremum is exact",
            "implementation": "approximate",
            "reason": "the supremum is taken over a finite grid of the nuisance and each p-value is estimated with finite toys",
            "validated": ("seeded coverage scan passed in BB_VALIDATED_RANGE" if within else
                          "outside BB_VALIDATED_RANGE: coverage of this implementation is not validated here; run neyman-coverage")}


def _aux_draw(b: float, sig: float, z: float) -> float:
    """Auxiliary measurement drawn from the constraint term of the likelihood, Normal(b0 | b, sig) on the real line
    (no truncation at zero: the likelihood and _q1 accept b0 < 0)."""
    return b + sig * z if sig > 0 else b


def _p_at(n_obs, b0_obs, sig, s, b_true, uniforms, gauss) -> float:
    q_obs = _q1(n_obs, b0_obs, sig, s)
    hits = 0
    for u, z in zip(uniforms, gauss):
        nn = _ppf(u, s + b_true)
        hits += _q1(nn, _aux_draw(b_true, sig, z), sig, s) >= q_obs - 1e-12
    return hits / len(uniforms)


def _bb_grid(b0, sig, beta, points):
    if sig == 0.0:
        return [b0], 0.0
    zb = NormalDist().inv_cdf(1.0 - beta / 2.0)
    lo, hi = max(b0 - zb * sig, 0.0), max(b0 + zb * sig, 0.0)
    if hi <= lo:  # the confidence set lies below b = 0 (b0 far below zero): only the boundary is allowed
        return [lo], beta
    return [lo + (hi - lo) * k / (points - 1) for k in range(points)], beta


def _p_sup(n_obs, b0_obs, sig, s, grid, uniforms, gauss) -> float:
    return max(_p_at(n_obs, b0_obs, sig, s, b, uniforms, gauss) for b in grid)


def _neyman_checks(n, b, sigma_b, cl, beta, toys, seed, points):
    n, b, sig = _inputs1(n, b, sigma_b)
    cl = _num(cl, "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    beta = _num(beta, "beta", 0.0, 0.5, strict_low=True)
    if sig > 0 and beta >= 1.0 - cl:
        raise LikelihoodError("beta must be smaller than 1 - cl")
    if isinstance(points, bool) or not isinstance(points, int) or not 3 <= points <= 41:
        raise LikelihoodError("grid points must be an integer in [3, 41]")
    return n, b, sig, cl, beta


def neyman_limit(n: int, b: float, sigma_b: float, cl: float, beta: float, toys: int, seed: int, points: int = 15) -> dict:
    n, b, sig, cl, beta = _neyman_checks(n, b, sigma_b, cl, beta, toys, seed, points)
    toys, seed = _seed_toys(toys, seed)
    grid, used_beta = _bb_grid(b, sig, beta, points)
    rng = random.Random(seed)
    uniforms, gauss = _draws(rng, toys)
    alpha = 1.0 - cl
    lo, hi = max(n - b, 0.0), max(n - b, 0.0) + 8.0 * (math.sqrt(n + 1.0) + sig) + 10.0
    if hi + max(grid) + 6.0 * sig > MAX_MEAN:
        raise LikelihoodError(f"inputs reach a mean above the script's range ({MAX_MEAN:g})")
    target = alpha - used_beta
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if _p_sup(n, b, sig, mid, grid, uniforms, gauss) > target else (lo, mid)
    s_bb = 0.5 * (lo + hi)
    s_plug = profile_limit(n, b, sig, cl, toys, seed)["toy_calibrated_upper_limit"]
    within = _in_validated_range(b, sig, cl)
    out = {"label": LABEL, "method": ("upper limit from the Berger-Boos construction over the background nuisance, approximated "
                                      "with a finite nuisance grid and seeded toys"),
           "n_obs": n, "b": b, "sigma_b": sig, "cl": cl, "beta": used_beta, "toys": toys, "seed": seed,
           "nuisance_grid_points": len(grid), "nuisance_range": [min(grid), max(grid)],
           "berger_boos_upper_limit": s_bb, "plug_in_profile_upper_limit": s_plug,
           "ratio_berger_boos_over_plug_in": s_bb / s_plug if s_plug > 0 else None,
           "toy_p_value_error_at_threshold": math.sqrt(max(target * (1.0 - target), 0.0) / toys),
           "bisection_width": hi - lo,
           "coverage_claim": _coverage_claim(within), "within_validated_range": within, "validated_range": BB_VALIDATED_RANGE,
           "note": ("a signal s is excluded when sup over b in the (1 - beta) confidence set of the background of the "
                    "toy p-value of the one-sided profile statistic, plus beta, is at most 1 - cl; with an exact "
                    "supremum and exact p-values the construction covers at least cl for every true background (Berger "
                    "and Boos 1994); this implementation approximates both (a grid over the nuisance, toy p-values with "
                    "the binomial error toy_p_value_error_at_threshold, common random numbers, 16 bisection steps), so "
                    "its coverage is an approximation, checked by seeded scans only within validated_range; it "
                    "over-covers in those scans (a longer limit than the plug-in profile); the auxiliary measurement "
                    "in the toys is drawn from the same Gaussian constraint as the likelihood (not truncated at zero); "
                    "the construction has no CLs protection against a downward fluctuation (report the expected sensitivity)")}
    return out


def neyman_coverage(s_true: float, b_true: float, sigma_b: float, cl: float, beta: float, outer: int, inner: int,
                    seed: int, points: int = 9) -> dict:
    s_true = _num(s_true, "s", 0.0, 100.0)
    b_true = _num(b_true, "b", 0.0, 200.0)
    sig = _num(sigma_b, "sigma_b", 0.0, 100.0)
    cl = _num(cl, "cl", 0.0, 1.0, strict_low=True)
    if cl >= 1.0:
        raise LikelihoodError("cl must lie strictly between 0 and 1")
    beta = _num(beta, "beta", 0.0, 0.5, strict_low=True)
    if sig > 0 and beta >= 1.0 - cl:
        raise LikelihoodError("beta must be smaller than 1 - cl")
    if isinstance(points, bool) or not isinstance(points, int) or not 3 <= points <= 41:
        raise LikelihoodError("grid points must be an integer in [3, 41]")
    for name, v, lo_, hi_ in (("outer", outer, 50, 5000), ("inner", inner, 50, 5000)):
        if isinstance(v, bool) or not isinstance(v, int) or not lo_ <= v <= hi_:
            raise LikelihoodError(f"{name} must be an integer in [{lo_}, {hi_}]")
    _, seed = _seed_toys(100, seed)
    if s_true + b_true + 6.0 * sig > MAX_MEAN:
        raise LikelihoodError(f"inputs reach a mean above the script's range ({MAX_MEAN:g})")
    rng = random.Random(seed)
    uniforms, gauss = _draws(rng, inner)
    alpha = 1.0 - cl
    rej_plug = rej_bb = 0
    for _ in range(outer):
        n = _ppf(rng.random(), s_true + b_true)
        b0 = _aux_draw(b_true, sig, rng.gauss(0.0, 1.0))
        bh = _b_hat(n, s_true, b0, sig)
        rej_plug += _p_at(n, b0, sig, s_true, bh, uniforms, gauss) <= alpha
        grid, ub = _bb_grid(b0, sig, beta, points)
        rej_bb += _p_sup(n, b0, sig, s_true, grid, uniforms, gauss) + ub <= alpha
    cov = lambda r: 1.0 - r / outer
    err = lambda r: math.sqrt(max((r / outer) * (1 - r / outer), 0.0) / outer)
    within = _in_validated_range(b_true, sig, cl, s_true)
    return {"label": LABEL, "method": ("coverage of an upper limit at a true (s, b): plug-in profile versus the approximate "
                                       "Berger-Boos supremum (finite grid, seeded toys)"),
            "true_signal": s_true, "true_background": b_true, "sigma_b": sig, "cl": cl, "beta": beta if sig > 0 else 0.0,
            "outer_pseudo_experiments": outer, "inner_toys": inner, "seed": seed,
            "coverage_plug_in_profile": cov(rej_plug), "binomial_error_plug_in": err(rej_plug),
            "coverage_berger_boos": cov(rej_bb), "binomial_error_berger_boos": err(rej_bb),
            "inner_toy_p_value_error_at_threshold": math.sqrt(alpha * (1.0 - alpha) / inner),
            "grid_points": points, "coverage_claim": _coverage_claim(within), "within_validated_range": within,
            "validated_range": BB_VALIDATED_RANGE,
            "note": ("coverage here is the probability that the true signal is not excluded, that is that the upper limit is "
                     "at least the true signal; a plug-in profile construction may fall below the nominal cl for some "
                     "(s, b, sigma_b) and above it for others, so scan the true values you care about; the approximate "
                     "Berger-Boos supremum is expected at or above cl within the Monte Carlo errors shown (binomial error "
                     "of the outer count; inner_toy_p_value_error_at_threshold is the toy error of each p-value near the "
                     "exclusion threshold); this is a check at one point, not a proof over the parameter space")}


def neyman_coverage_scan(true_points, cl: float, beta: float, outer: int, inner: int, seed: int, points: int = 9) -> dict:
    """neyman_coverage at each (s, b, sigma_b) in true_points (seed + index per point); rows keep the MC errors."""
    if not isinstance(true_points, (list, tuple)) or not 1 <= len(true_points) <= 200:
        raise LikelihoodError("true_points must list 1 to 200 (s, b, sigma_b) triples")
    rows = []
    for i, pt in enumerate(true_points):
        if not isinstance(pt, (list, tuple)) or len(pt) != 3:
            raise LikelihoodError("each true point is (s, b, sigma_b)")
        r = neyman_coverage(pt[0], pt[1], pt[2], cl, beta, outer, inner, None if seed is None else seed + i, points)
        rows.append({k: r[k] for k in ("true_signal", "true_background", "sigma_b", "coverage_plug_in_profile", "binomial_error_plug_in",
                                       "coverage_berger_boos", "binomial_error_berger_boos", "inner_toy_p_value_error_at_threshold",
                                       "within_validated_range", "seed")})
    return {"label": LABEL, "method": "coverage scan over true (s, b, sigma_b): plug-in profile versus approximate Berger-Boos",
            "cl": cl, "beta": beta, "outer_pseudo_experiments": outer, "inner_toys": inner, "grid_points": points, "points": rows,
            "note": "each row is a seeded check at one true point with its Monte Carlo errors; the scan validates only the points listed"}


# -------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, toys):
        p.add_argument("--toys", type=int, default=toys)
        p.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")

    a = sub.add_parser("profile-limit", help="single-bin profile-likelihood upper limit")
    a.add_argument("--n", type=int, required=True)
    a.add_argument("--b", type=float, required=True)
    a.add_argument("--sigma-b", type=float, default=0.0)
    a.add_argument("--cl", type=float, default=0.95)
    common(a, 4000)
    c = sub.add_parser("profile-significance", help="single-bin profile-likelihood q0")
    c.add_argument("--n", type=int, required=True)
    c.add_argument("--b", type=float, required=True)
    c.add_argument("--sigma-b", type=float, default=0.0)
    common(c, 20000)
    m = sub.add_parser("multibin-limit", help="multi-bin profile-likelihood upper limit")
    m.add_argument("--input", required=True)
    m.add_argument("--cl", type=float, default=0.95, help="used when the file has no cl")
    common(m, 500)
    f = sub.add_parser("profile-fc", help="Feldman-Cousins-style interval with a profiled nuisance")
    f.add_argument("--n", type=int, required=True)
    f.add_argument("--b", type=float, required=True)
    f.add_argument("--sigma-b", type=float, default=0.0)
    f.add_argument("--cl", type=float, default=0.90)
    f.add_argument("--step", type=float, default=None, help="signal grid step (default: scan range / 150)")
    common(f, 1000)
    k = sub.add_parser("profile-cls", help="CLs limit with a profiled nuisance and an expected band")
    k.add_argument("--n", type=int, required=True)
    k.add_argument("--b", type=float, required=True)
    k.add_argument("--sigma-b", type=float, default=0.0)
    k.add_argument("--cl", type=float, default=0.95)
    k.add_argument("--expected-toys", type=int, default=60, help="background-only pseudo-experiments for the expected band (0 to skip)")
    common(k, 1000)
    ny = sub.add_parser("neyman-limit", help="Berger-Boos upper limit (finite-grid, seeded-toy approximation)")
    ny.add_argument("--n", type=int, required=True)
    ny.add_argument("--b", type=float, required=True)
    ny.add_argument("--sigma-b", type=float, default=0.0)
    ny.add_argument("--cl", type=float, default=0.95)
    ny.add_argument("--beta", type=float, default=0.01, help="confidence-set error for the nuisance (< 1 - cl)")
    ny.add_argument("--points", type=int, default=15, help="grid points over the nuisance set")
    common(ny, 1000)
    nc = sub.add_parser("neyman-coverage", help="coverage check: plug-in profile versus Berger-Boos")
    nc.add_argument("--s", type=float, required=True, help="true signal")
    nc.add_argument("--b", type=float, required=True, help="true background")
    nc.add_argument("--sigma-b", type=float, default=0.0)
    nc.add_argument("--cl", type=float, default=0.95)
    nc.add_argument("--beta", type=float, default=0.01)
    nc.add_argument("--outer", type=int, default=300, help="pseudo-experiments")
    nc.add_argument("--inner", type=int, default=200, help="toys per p-value")
    nc.add_argument("--points", type=int, default=9)
    nc.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    h = sub.add_parser("shape-limit", help="multi-bin limit with shape and normalization nuisances")
    h.add_argument("--input", required=True)
    h.add_argument("--cl", type=float, default=0.95, help="used when the file has no cl")
    common(h, 0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "neyman-limit":
            result = neyman_limit(args.n, args.b, args.sigma_b, args.cl, args.beta, args.toys, args.seed, args.points)
        elif args.command == "neyman-coverage":
            result = neyman_coverage(args.s, args.b, args.sigma_b, args.cl, args.beta, args.outer, args.inner, args.seed, args.points)
        elif args.command == "profile-fc":
            result = profile_fc(args.n, args.b, args.sigma_b, args.cl, args.toys, args.seed, args.step)
        elif args.command == "profile-cls":
            result = profile_cls(args.n, args.b, args.sigma_b, args.cl, args.toys, args.expected_toys, args.seed)
        elif args.command == "shape-limit":
            try:
                doc = json.loads(Path(args.input).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise LikelihoodError(f"cannot read {args.input}: {exc}") from None
            result = shape_limit(doc, args.cl, args.toys, args.seed)
        elif args.command == "profile-limit":
            result = profile_limit(args.n, args.b, args.sigma_b, args.cl, args.toys, args.seed)
        elif args.command == "profile-significance":
            result = profile_significance(args.n, args.b, args.sigma_b, args.toys, args.seed)
        else:
            try:
                doc = json.loads(Path(args.input).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise LikelihoodError(f"cannot read {args.input}: {exc}") from None
            result = multibin_limit(doc, args.cl, args.toys, args.seed)
    except LikelihoodError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    result["status"] = "ok"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
