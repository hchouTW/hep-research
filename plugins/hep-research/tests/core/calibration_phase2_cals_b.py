"""The deferred section 8.7 calibrations of phase 2, batch B (task card `docs/dev/simulator-calibration/simcal-tasks/
phase-2.md`): calibration 10 (n_min and B, note 3) and the remaining items of calibration 12 (note 4) that this engine
can test, as Slurm job array tasks (raw per-repetition records) and local runs. Not a unit test module.

  python3 calibration_phase2_cals_b.py --task N --out DIR          one task of the array
  python3 calibration_phase2_cals_b.py --merge DIR --out FILE      merge and judge the array (exit 0 passed, 1 failed)
  python3 calibration_phase2_cals_b.py --local NAME --out FILE     a local item
  python3 calibration_phase2_cals_b.py --smoke NAME --out FILE     the code path at tiny sizes (not evidence)

Seeds: default_rng([cal_seed(c, r), j, ...]) for calibration c, repetition r and configuration j. The G8 items wait (the
user's decision of 2026-11-12).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calibration_phase2_gates as G  # noqa: E402

from core.calibration import design_noise as DN  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import interval as IV  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402
from core.calibration import validate as V  # noqa: E402

cal_seed = G.cal_seed
ALPHA_TV = 0.05
ALPHA_G = 0.01
LEVEL_THREE_SIGMA = 0.0027                          # the two-sided 3-sigma level


def _rng(c, r, j, *more):
    return np.random.default_rng([cal_seed(c, r), j, *more])


# ------------------------------------------------------------------ shapes at their worst evaluation point
def shape_lambdas(K: int) -> np.ndarray:
    """Expected counts of a K-bin shape: the smallest bin at n_min = 20 (the worst condition just holds), rising
    geometrically to the reference category at 200 (Part B's example lambda_K = 200)."""
    return 20.0 * 10.0 ** (np.arange(K) / (K - 1))


def alr_half(n) -> np.ndarray:
    """The data-side summary of a shape: alr of n_k + 1/2 over all K bins, the last the reference category (section
    2.1)."""
    n = np.asarray(n, float)
    return np.log(n[..., :-1] + 0.5) - np.log(n[..., -1:] + 0.5)


def expected_log_half(N: int, p: np.ndarray) -> np.ndarray:
    """E[ln(n_k + 1/2)] for n_k ~ Binomial(N, p_k), summed over the support within 14 standard deviations."""
    out = np.empty(p.size)
    for k, pk in enumerate(p):
        m, s = N * pk, math.sqrt(N * pk * (1 - pk))
        x = np.arange(max(0, int(m - 14 * s) - 1), min(N, int(m + 14 * s) + 2) + 1)
        w = stats.binom.pmf(x, N, pk)
        out[k] = float(np.sum(w * np.log(x + 0.5)) / np.sum(w))
    return out


def expected_alr(N: int, p: np.ndarray) -> np.ndarray:
    """The prediction-side summary, method 1 of section 2.1: E[alr(n + 1/2)] under Multinomial(N, p) (exact: alr is a
    difference of the bins' logs, each with its binomial marginal)."""
    e = expected_log_half(N, p)
    return e[:-1] - e[-1]


class ShapeProblem(T.LinearProblem):
    """A fit problem over one K-bin shape of N events, p_k(theta) proportional to lambda_k exp(theta_0 z_k +
    theta_1 z_k^2): observed as alr(n + 1/2) (K - 1 Gaussian rows, identity link), predicted by the exact expectation
    E[alr(n + 1/2)], V_data a parametric bootstrap of B = max(500, 50 (K - 1)) sets at theta_ref with common random
    numbers (the same seed at every theta_ref), no MC noise. Label `synthetic`."""

    def __init__(self, K: int, B: int | None = None, mc_seed=1, observed=None, boot_seed=None):
        lam = shape_lambdas(K)
        self.K, self.N = K, int(round(lam.sum()))
        self.base = lam / lam.sum()
        self.z = np.linspace(-1.0, 1.0, K)
        cfg = T.Config(np.zeros((K - 1, 2)), np.zeros(K - 1), np.eye(K - 1), np.zeros((K - 1, K - 1)),
                       [(-1.0, 1.0)] * 2, [(-0.3, 0.3)] * 2)
        cfg.bootstrap_B = int(B or max(500, 50 * (K - 1)))
        super().__init__(cfg, mc_seed, observed)
        self._mc_seed = mc_seed
        if boot_seed is not None:
            self.boot_seed = boot_seed
        self.V_depends_on_theta = True
        self._mean_cache = {}

    def probs(self, theta) -> np.ndarray:
        t = np.asarray(theta, float)[:2]
        w = self.base * np.exp(t[0] * self.z + t[1] * self.z ** 2)
        return w / w.sum()

    def mean(self, theta):
        key = tuple(np.round(np.asarray(theta, float)[:2], 13))
        if key not in self._mean_cache:
            if len(self._mean_cache) > 2048:
                self._mean_cache.clear()
            self._mean_cache[key] = expected_alr(self.N, self.probs(theta))
        return self._mean_cache[key]

    def simulate(self, beta_truth, rng, phis=None, nominal: bool = True):
        return L.Observations(y_gauss=alr_half(rng.multinomial(self.N, self.probs(beta_truth[:2]))))

    def bootstrap_vhat(self, tp, seed) -> np.ndarray:
        rng = np.random.default_rng([T.F_seed(seed), 4242])
        sets = alr_half(rng.multinomial(self.N, self.probs(tp), size=self.cfg.bootstrap_B))
        return L.bootstrap_covariance(sets)

    def V_data_at(self, theta):
        p = self.probs(theta)
        lam = self.N * p
        D = np.c_[np.diag(1.0 / lam[:-1]), -np.ones((self.K - 1, 1)) / lam[-1]]
        return D @ (self.N * (np.diag(p) - np.outer(p, p))) @ D.T

    def with_data(self, observed, mc_seed=None):
        q = ShapeProblem(self.K, self.cfg.bootstrap_B, self.mc_seed if mc_seed is None else mc_seed, observed,
                         self.boot_seed)
        q.truth = self.truth
        return q


def shape_problem(K, r, j, c=10):
    p = ShapeProblem(K, mc_seed=(cal_seed(c, r), j, 1), boot_seed=(cal_seed(c, r), j, 2))
    truth = np.r_[0.0, 0.0, np.zeros(p.layout.n_beta - 2)]
    truth[p.layout.slices()["gamma"]] = 1.0
    p.observed = p.simulate(truth, _rng(c, r, j, 3))
    p.truth = truth
    return p, truth


# ------------------------------------------------------------------ 10 (a): the +1/2 estimator (local)
def cal10_plus_half(reps: int = 10_000, M_factor: int = 1000) -> dict:
    """Residual means of alr(n + 1/2) against method 1 (exact expectation) and method 2 (the same estimator on the
    unnormalized counts of an MC of M = 1000 N events), and the negative control (MC normalized to the data size,
    then + 1/2), for K = 3, 5, 50. The mean vector is judged jointly at the two-sided 3-sigma level (Hotelling T^2
    against chi2_{K-1}): methods 1 and 2 pass (p > 0.0027), the control is caught (p < 0.0027)."""
    out, ok = {}, True
    for j, K in enumerate((3, 5, 50)):
        lam = shape_lambdas(K)
        N = int(round(lam.sum()))
        p = lam / lam.sum()
        rng = _rng(10, 0, j, 1)
        n = rng.multinomial(N, p, size=reps)
        m = rng.multinomial(M_factor * N, p, size=reps)
        y = alr_half(n)
        res = {"method1": y - expected_alr(N, p), "method2": y - alr_half(m),
               "control_normalize_then_half": y - alr_half(m * (N / (M_factor * N)))}
        rec = {"K": K, "N": N, "lambda_min": float(lam.min()), "lambda_ref": float(lam[-1])}
        for key, R in res.items():
            mb = R.mean(0)
            S = np.cov(R, rowvar=False).reshape(K - 1, K - 1)
            t2 = float(reps * mb @ np.linalg.solve(S, mb))
            pv = float(stats.chi2.sf(t2, K - 1))
            rec[key] = {"p": pv, "max_abs_z": float(np.max(np.abs(mb) / np.sqrt(np.diag(S) / reps))),
                        "mean_smallest_bin": float(mb[0]), "sd_smallest_bin": float(math.sqrt(S[0, 0]))}
        rec["passed"] = rec["method1"]["p"] > LEVEL_THREE_SIGMA and rec["method2"]["p"] > LEVEL_THREE_SIGMA and \
            rec["control_normalize_then_half"]["p"] < LEVEL_THREE_SIGMA
        ok = ok and rec["passed"]
        out[f"K={K}"] = rec
    return {"calibration": 10, "item": "plus-half estimator", "results": out, "passed": bool(ok), "reps": reps}


# ------------------------------------------------------------------ 10 (b): toy-calibrated T_v with the bootstrap
TV_CONFIGS = ["shape K=3", "shape K=5", "shape K=50", "shared p=10", "shared p=30", "shared p=50"]
TV_NREF = 500
EPSILONS = (0.005, 0.01)
INJECT = ("independent", "largest", "smallest")


def _tv_model(config: str):
    kind, v = config.split()
    size = int(v.split("=")[1])
    if kind == "shape":
        lam = shape_lambdas(size)
        N = int(round(lam.sum()))
        p = lam / lam.sum()
        return N, p, alr_half, expected_alr(N, p), max(500, 50 * (size - 1))
    # summaries of shared events: the fractions of N = 1000 events above p thresholds at probabilities 0.02..0.98
    # (the smallest expected count 20), from the multinomial counts in the p + 1 cells between the thresholds
    c = np.linspace(0.02, 0.98, size)
    q = np.diff(np.r_[0.0, c, 1.0])
    N = 1000

    def summary(n):
        cum = np.cumsum(np.asarray(n, float), axis=-1)[..., :-1]
        return 1.0 - cum / N
    return N, q, summary, 1.0 - c, max(500, 50 * size)


def _tv_stat(rng, N, p, summary, mu, B):
    y = summary(rng.multinomial(N, p))
    S = L.bootstrap_covariance(summary(rng.multinomial(N, p, size=B)))
    r = y - mu
    return float(r @ np.linalg.solve(S, r))


def tv_block(config: str, r0: int, reps: int) -> list:
    """Per repetition: T on data with its own bootstrap covariance, the reference of 500 toys with their own bootstrap
    each, the p-value without injection and with injected non-convergence (eps 0.5%, 1%; independent of the outcome,
    or the toys with the largest or smallest statistic), counted per section 7.3 (testing ensemble, no replacement:
    a non-converged toy counts as T >= T_obs), and the ratio test of the independent injection."""
    j = TV_CONFIGS.index(config)
    N, p, summary, mu, B = _tv_model(config)
    kst = F.k_star(TV_NREF, replacement=False)
    rows = []
    for r in range(r0, r0 + reps):
        rng = _rng(10, r, 100 + j)
        T_obs = _tv_stat(rng, N, p, summary, mu, B)
        Tr = np.array([_tv_stat(rng, N, p, summary, mu, B) for _ in range(TV_NREF)])
        row = {"r": r, "p": F.testing_pvalue(T_obs, Tr, 0)}
        irng = _rng(10, r, 100 + j, 9)
        order = np.argsort(Tr)
        for eps in EPSILONS:
            nx = int(math.ceil(eps * TV_NREF))
            for mode in INJECT:
                if mode == "independent":
                    bad = irng.random(TV_NREF) < eps
                elif mode == "largest":
                    bad = np.zeros(TV_NREF, bool)
                    bad[order[-nx:]] = True
                else:
                    bad = np.zeros(TV_NREF, bool)
                    bad[order[:nx]] = True
                X = int(bad.sum())
                row[f"p|{eps}|{mode}"] = F.testing_pvalue(T_obs, Tr[~bad], X)
                if mode == "independent":
                    row[f"ratio|{eps}"] = bool(X >= kst)
        rows.append(row)
    return rows


def tv_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for cfg, rows in rows_by.items():
        n = len(rows)
        rate = float(np.mean([x["p"] <= ALPHA_TV for x in rows]))
        rec = {"reps": n, "rate": rate, "ok_no_injection": abs(rate - ALPHA_TV) < 0.10 * ALPHA_TV}
        inj_ok = True
        for eps in EPSILONS:
            for mode in INJECT:
                ri = float(np.mean([x[f"p|{eps}|{mode}"] <= ALPHA_TV for x in rows]))
                rec[f"rate|{eps}|{mode}"] = ri
                inj_ok = inj_ok and ri <= 1.1 * ALPHA_TV
            rec[f"ratio_trigger|{eps}"] = float(np.mean([x[f"ratio|{eps}"] for x in rows]))
        rec["ok_injection"] = inj_ok
        rec["ok_ratio_trigger"] = all(rec[f"ratio_trigger|{eps}"] < 1e-3 for eps in EPSILONS)
        rec["passed"] = bool(rec["ok_no_injection"] and inj_ok and rec["ok_ratio_trigger"])
        ok = ok and rec["passed"]
        out[cfg] = rec
    return {"item": "toy-calibrated T_v with the bootstrap covariance", "configurations": out, "passed": bool(ok),
            "rule": "without injection the rejection rate within alpha +- 10% (alpha = 0.05); with injected "
                    "non-convergence (0.5%, 1%; independent, largest, smallest) <= 1.1 alpha; the ratio test's "
                    "trigger rate at eps <= eps_max < 1e-3 per ensemble"}


# ------------------------------------------------------------------ 10 (c, d): G6 under the null, convergence
G6_K = (3, 5, 50)
G6_TOYS = 500


def g6_block(K: int, r0: int, reps: int) -> list:
    j = G6_K.index(K)
    rows = []
    for r in range(r0, r0 + reps):
        p, truth = shape_problem(K, r, 200 + j)
        f = F.iterate(p, T.initial_beta(p))
        row = {"r": r, "converged": bool(f.converged), "iterations": int(f.iterations)}
        if f.converged:
            g = F.g6(p, f, F.null_toys(p, f, G6_TOYS, (cal_seed(10, r), 200 + j, 4)), alpha=ALPHA_G)
            row.update(p=g["p"], X=g["X"], n_toys=g["n_toys"], lin_ok=g["linearity_ok"],
                       lin_fraction=g["linearity_fraction"])
        rows.append(row)
    return rows


def g6_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for key, rows in rows_by.items():
        conv = [x for x in rows if x["converged"]]
        rate = float(np.mean([x["p"] <= ALPHA_G for x in conv])) if conv else None
        fit_frac = len(conv) / max(len(rows), 1)
        toy_frac = 1 - sum(x["X"] for x in conv) / max(sum(x["n_toys"] for x in conv), 1)
        rec = {"reps": len(rows), "fits_converged_fraction": fit_frac, "toys_converged_fraction": toy_frac,
               "g6_rejection": rate, "linearity_check_passes": float(np.mean([x["lin_ok"] for x in conv])),
               "ok_g6": bool(rate is not None and rate <= 1.5 * ALPHA_G),
               "ok_convergence": bool(fit_frac >= 0.99 and toy_frac >= 0.99)}
        rec["passed"] = rec["ok_g6"] and rec["ok_convergence"]
        ok = ok and rec["passed"]
        out[key] = rec
    return {"item": "G6 under the null with the bootstrap covariance; convergence fractions", "configurations": out,
            "passed": bool(ok), "rule": "G6 rejection <= 1.5 alpha (alpha = 0.01); fits and toys converged >= 99%"}


# ------------------------------------------------------------------ 10 (e): G7 with injected non-convergence
G7_MODES = ("none",) + tuple(f"{m}|{e}" for e in EPSILONS for m in ("independent", "closest", "farthest"))
G7_K = 10


def g7_block(mode: str, r0: int, reps: int) -> list:
    """Calibration 5's configuration (d = 3, K = 10, V_MC correct): refits declared non-converged independently of the
    outcome, or when among the eps closest to (farthest from) the data fit in the Mahalanobis distance of Sigma_MC
    (its chi2_3 quantile), are replaced by the next MC seed (section 7.3, with replacement); G7 on the K kept."""
    j = G7_MODES.index(mode)
    cfg = T.linear_config(n=20, d=3, mc_ratio=0.1, seed=cal_seed(5, 0) % 2 ** 31)
    kind, eps = (mode.split("|")[0], float(mode.split("|")[1])) if mode != "none" else ("none", 0.0)
    lo, hi = stats.chi2.ppf(eps, 3) if eps else 0.0, stats.chi2.ppf(1 - eps, 3) if eps else math.inf
    rows = []
    for r in range(r0, r0 + reps):
        rng = _rng(10, r, 300 + j)
        p0 = T.make(cfg, [0.5, -0.3, 1.0], data_seed=int(rng.integers(2 ** 62)), mc_seed=int(rng.integers(2 ** 62)))
        f0 = F.iterate(p0, T.initial_beta(p0), lndet=False)
        S = F.sigma_mc(p0, f0, cfg.V_MC)
        Si = np.linalg.pinv(S)
        th, X, k = [], 0, 0
        while len(th) < G7_K and k < 10 * G7_K:
            p = T.LinearProblem(cfg, mc_seed=int(np.random.SeedSequence([cal_seed(10, r), 300 + j, 5, k])
                                                 .generate_state(1)[0]), observed=p0.observed)
            k += 1
            t = F.iterate(p, T.initial_beta(p), lndet=False).beta[:3]
            dd = float((t - f0.beta[:3]) @ Si @ (t - f0.beta[:3]))
            bad = (kind == "independent" and rng.random() < eps) or (kind == "closest" and dd < lo) or \
                (kind == "farthest" and dd > hi)
            if bad:
                X += 1
                continue
            th.append(t)
        g = F.g7(np.array(th), S)
        rows.append({"r": r, "failed": g["status"] == "failed", "X": X})
    return rows


def g7_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for mode, rows in rows_by.items():
        n = len(rows)
        fa = int(sum(x["failed"] for x in rows))
        rec = {"reps": n, "false_alarms": fa, "X_total": int(sum(x["X"] for x in rows)),
               "passed": bool(fa <= 34 * n / 1000)}
        ok = ok and rec["passed"]
        out[mode] = rec
    return {"item": "G7 false alarms under injected non-convergence", "configurations": out, "passed": bool(ok),
            "rule": "false alarms with a correct V_MC <= 2 alpha (<= 34 of 1000 refit sets, alpha = 0.01) for every mode"}


# ------------------------------------------------------------------ 10 (e'): replacement bias of Sigma_boot, C-hat_r
def _drop(x, u, mode, eps, sd):
    if mode == "independent":
        return None
    a = abs(float(x @ u)) / sd
    q = stats.norm.ppf(1 - eps / 2)
    return a > q if mode == "largest" else a < stats.norm.ppf(0.5 + eps / 2)


def cal10_replacement(reps: int = 4000) -> dict:
    """Synthetic Gaussian ensembles (section 7.3): C-hat_r from n = 500 toy residuals (k = 5) with replacement, and
    Sigma_boot from N_t = 10 toys x K_b = 6 realizations (d = 3), with non-convergence of eps = 0.5% and 1% injected
    independently of the outcome or concentrated on the realizations with the largest or smallest projection on a
    direction u. After the w correction (C-hat_r / w(eps-hat), Sigma_boot / w(eps-hat+)), one-sided acceptance: the
    variance in any direction not underestimated by more than 1% (the smallest generalized eigenvalue of the mean
    corrected estimate against the truth >= 0.99) and lambda-hat_a not overestimated by more than 1%; the conservative
    bias reported."""
    out, ok = {}, True
    rng0 = np.random.default_rng([cal_seed(10, 0), 400])
    k, d = 5, 3
    C = G._spd(k, rng0)
    e = rng0.normal(size=k)
    lam_true = float(e @ np.linalg.solve(C, e))
    Lc = np.linalg.cholesky(C)
    u_c = np.linalg.solve(C, e)
    u_c /= np.linalg.norm(u_c)
    sd_c = math.sqrt(u_c @ C @ u_c)
    Sb = G._spd(d, rng0) * 0.1
    Lb = np.linalg.cholesky(Sb)
    u_b = np.linalg.eigh(Sb)[1][:, -1]
    sd_b = math.sqrt(u_b @ Sb @ u_b)
    for j, (eps, mode) in enumerate([(0.0, "none")] + [(e_, m) for e_ in EPSILONS for m in INJECT]):
        rng = np.random.default_rng([cal_seed(10, 0), 401, j])
        Cs, lams, Bs = [], [], []
        for _ in range(reps):
            kept, X = [], 0
            while len(kept) < 500:
                x = Lc @ rng.normal(size=k)
                bad = (rng.random() < eps) if mode == "independent" else (_drop(x, u_c, mode, eps, sd_c) if eps
                                                                         else False)
                if bad:
                    X += 1
                    continue
                kept.append(x)
            R = np.array(kept)
            Ch = np.cov(R, rowvar=False) / F.w_factor(F.eps_hat(X, 500))
            Cs.append(Ch)
            lams.append(float(e @ np.linalg.solve(Ch, e)) * V.chat_factor(500, k))
            groups, Xb = [], 0
            for t in range(10):
                g = []
                mu_t = rng.normal(size=d)
                while len(g) < 6:
                    b = Lb @ rng.normal(size=d)
                    bad = (rng.random() < eps) if mode == "independent" else (_drop(b, u_b, mode, eps, sd_b) if eps
                                                                             else False)
                    if bad:
                        Xb += 1
                        continue
                    g.append(mu_t + b)
                groups.append(np.array(g))
            within = sum(np.cov(g_, rowvar=False) * 5 for g_ in groups) / 50
            Bs.append(within / F.w_factor(F.eps_hat(Xb, 60, plus=True)))
        Cm, Bm = np.mean(Cs, 0), np.mean(Bs, 0)
        gc = float(np.linalg.eigvals(np.linalg.solve(C, Cm)).real.min())
        gb = float(np.linalg.eigvals(np.linalg.solve(Sb, Bm)).real.min())
        lam_bias = float(np.mean(lams) / lam_true - 1)
        rec = {"C_r_min_variance_ratio": gc, "lambda_bias": lam_bias, "Sigma_boot_min_variance_ratio": gb,
               "Sigma_boot_max_variance_ratio": float(np.linalg.eigvals(np.linalg.solve(Sb, Bm)).real.max()),
               "passed": bool(gc >= 0.99 and gb >= 0.99 and lam_bias <= 0.01)}
        ok = ok and rec["passed"]
        out[f"{mode}|{eps}"] = rec
    return {"calibration": 10, "item": "replacement bias after the w correction", "results": out, "passed": bool(ok),
            "reps": reps}


# ------------------------------------------------------------------ 10 (f): the toy estimate of Sigma_boot
SIGMA_BOOT_K = 5
SIGMA_BOOT_RUNS_PER_TASK, SIGMA_BOOT_TASKS = 50, 10
SIGMA_BOOT_TRUTH_TASKS, SIGMA_BOOT_TRUTH_TOYS, SIGMA_BOOT_TRUTH_REALIZATIONS = 4, 50, 30


def _sb_problem(seed):
    p = ShapeProblem(SIGMA_BOOT_K, mc_seed=seed, boot_seed=(seed, 2))
    truth = np.r_[0.0, 0.0, np.zeros(p.layout.n_beta - 2)]
    truth[p.layout.slices()["gamma"]] = 1.0
    p.observed = p.simulate(truth, np.random.default_rng([T.F_seed(seed), 3]))
    p.truth = truth
    return p, truth


def sigma_boot_block(part: str, r0: int, reps: int) -> list:
    """part "estimate": runs of design_noise.sigma_boot (N_t = 10, K_b = 6) on the shape problem (K = 5) at the truth;
    part "truth": toys at the truth each refitted with 30 bootstrap realizations (pooled within-toy covariance, the
    many-toys-times-many-bootstraps truth); part "asimov": the within covariance on Asimov data (always 0)."""
    rows = []
    for r in range(r0, r0 + reps):
        seed = (cal_seed(10, r), 500 + ["estimate", "truth", "asimov"].index(part))
        p, truth = _sb_problem(seed)
        if part == "estimate":
            s = DN.sigma_boot(p, truth, seed, N_t=10, K_b=6)
            rows.append({"r": r, "status": s["status"], "X": s.get("X"),
                         "Sigma_boot": None if s["status"] != "ok" else np.asarray(s["Sigma_boot"])[:2, :2].tolist()})
            continue
        rng = np.random.default_rng([T.F_seed(seed), 7])
        obs = L.Observations(y_gauss=p.mean(truth[:2])) if part == "asimov" else p.simulate(truth, rng)
        toy = p.with_data(obs)
        vals, X = [], 0
        for b in range(SIGMA_BOOT_TRUTH_REALIZATIONS if part == "truth" else 6):
            bs = (T.F_seed(seed), 8, b)
            view = F.view(toy, reference=lambda tp, be, frozen, bf, _bs=bs, _t=toy:
                          _t.reference(tp, be, frozen if bf else None, bootstrap_seed=_bs))
            f = F.iterate(view, truth)
            if not f.converged:
                X += 1
                continue
            vals.append(f.beta[:2].tolist())
        rows.append({"r": r, "values": vals, "X": X})
    return rows


def sigma_boot_judge(rows_by: dict) -> dict:
    tr = rows_by.get("truth", [])
    within = [np.cov(np.array(x["values"]), rowvar=False) for x in tr if len(x["values"]) > 2]
    truth = np.mean(within, 0) if within else None
    est = [np.array(x["Sigma_boot"]) for x in rows_by.get("estimate", []) if x["status"] == "ok"]
    traces = np.array([np.trace(s) for s in est])
    asi = [np.cov(np.array(x["values"]), rowvar=False) for x in rows_by.get("asimov", []) if len(x["values"]) > 2]
    rec = {"runs": len(est), "truth_trace": None if truth is None else float(np.trace(truth))}
    if truth is not None and len(est):
        rec["mean_bias"] = float(traces.mean() / np.trace(truth) - 1)
        rec["relative_sd_trace"] = float(traces.std(ddof=1) / traces.mean())
        rec["asimov_max_abs"] = float(max(np.max(np.abs(a)) for a in asi)) if asi else None
        rec["asimov_relative"] = None if not asi else rec["asimov_max_abs"] / float(np.max(np.abs(truth)))
        rec["passed"] = bool(abs(rec["mean_bias"]) < 0.10 and rec["relative_sd_trace"] <= 0.3 and
                             asi and rec["asimov_relative"] < 1e-6)
    else:
        rec["passed"] = False
    try:
        DN.sigma_boot(None, None, 0, source="asimov")
        rec["asimov_source_refused"] = False
    except DN.DesignError as exc:
        rec["asimov_source_refused"] = exc.code == "design.sigma_boot_source" if hasattr(exc, "code") else True
    rec["passed"] = bool(rec["passed"] and rec["asimov_source_refused"])
    return {"item": "toy estimate of Sigma_boot (K = 5 shape problem)", **rec,
            "rule": "mean bias of the trace < 10% against many toys x many bootstraps; relative sd of the trace <= 0.3; "
                    "Asimov gives 0 (negative control) and is refused as a source"}


# ------------------------------------------------------------------ 10 (g): V-hat with common random numbers (local)
def cal10_vhat(reps: int = 4000) -> dict:
    """At theta_ref = (0.2, -0.1) of the K = 5 shape problem: V-hat regenerated with common random numbers (the seed
    used at theta_0 = 0, regenerated at theta_ref) and V-hat generated independently agree in expectation with V (the
    mean over 20000 independent seeds): max |(E V-hat - V)_ij| / sqrt(V_ii V_jj) < 0.05; a V-hat carried over from
    theta_0 by reweighting the counts deviates (negative control; cells too high and too low counted)."""
    p = ShapeProblem(SIGMA_BOOT_K)
    t0, tr = np.zeros(2), np.array([0.2, -0.1])
    p0, pr = p.probs(t0), p.probs(tr)
    B = p.cfg.bootstrap_B

    def vh(seed, at):
        return p.bootstrap_vhat(at, seed)
    Vref = np.mean([vh((cal_seed(10, 1), 601, s), tr) for s in range(5 * reps)], 0)
    crn = np.mean([vh((cal_seed(10, 1), 602, s), tr) for s in range(reps)], 0)
    ind = np.mean([vh((cal_seed(10, 1), 603, s), tr) for s in range(reps)], 0)
    rw = []
    for s in range(reps):
        rng = np.random.default_rng([T.F_seed((cal_seed(10, 1), 602, s)), 4242])
        n = rng.multinomial(p.N, p0, size=B).astype(float) * (pr / p0)       # counts at theta_0, reweighted
        rw.append(L.bootstrap_covariance(alr_half(n)))
    rw = np.mean(rw, 0)
    sd = np.sqrt(np.outer(np.diag(Vref), np.diag(Vref)))

    def stdz(Mx):
        return (Mx - Vref) / sd
    zc, zi, zr = stdz(crn), stdz(ind), stdz(rw)
    rec = {"crn_max": float(np.max(np.abs(zc))), "independent_max": float(np.max(np.abs(zi))),
           "reweighted_max": float(np.max(np.abs(zr))), "reweighted_cells_high": int(np.sum(zr > 0.05)),
           "reweighted_cells_low": int(np.sum(zr < -0.05))}
    rec["passed"] = bool(rec["crn_max"] < 0.05 and rec["independent_max"] < 0.05 and rec["reweighted_max"] >= 0.05)
    return {"calibration": 10, "item": "V-hat with common random numbers", **rec, "seeds": reps}


# ------------------------------------------------------------------ 12: interval-toy coverage, negative controls
IT_LEVELS = (0.68, 0.95)
IT_TOYS = 200


def interval_block(r0: int, reps: int) -> list:
    """Toy-calibrated intervals (section 7.5) of theta_0 on the K = 5 shape problem: per repetition the construction at
    the scan point equal to the truth (coverage: the truth inside), 200 toys, at 68% and 95%."""
    rows = []
    for r in range(r0, r0 + reps):
        p, truth = shape_problem(5, r, 700, c=12)
        f = F.find_extremum(p, (cal_seed(12, r), 700, 4), T.initial_beta(p), n_start=2)
        row = {"r": r, "converged": bool(f.converged)}
        if f.converged:
            for lev in IT_LEVELS:
                iv = IV.toy_calibrated(p, f, 0, [0.0], IT_TOYS, (cal_seed(12, r), 700, 5, int(lev * 100)), lev,
                                       n_start=2)
                row[str(lev)] = {"status": iv["status"], "covered": bool(iv["status"] == "ok" and iv["inside"][0]),
                                 "X": iv.get("X")}
        rows.append(row)
    return rows


def interval_judge(rows_by: dict) -> dict:
    rows = rows_by.get("coverage", [])
    conv = [x for x in rows if x["converged"]]
    rec = {"reps": len(rows), "converged": len(conv)}
    ok = bool(conv)
    for lev in IT_LEVELS:
        ok_ = [x[str(lev)] for x in conv if x[str(lev)]["status"] == "ok"]
        cov = float(np.mean([x["covered"] for x in ok_])) if ok_ else None
        n = len(ok_)
        rec[str(lev)] = {"coverage": cov, "n": n, "incomplete": len(conv) - n,
                         "ok": bool(cov is not None and abs(cov - lev) <= 3 * math.sqrt(lev * (1 - lev) / n))}
        ok = ok and rec[str(lev)]["ok"]
    return {"item": "coverage of toy-calibrated intervals (truth at the scan point)", **rec, "passed": bool(ok),
            "rule": "coverage within 3 binomial se of nominal at 68% and 95%"}


def cal12_controls(reps: int = 10_000, n_ref: int = 20_000) -> dict:
    """The negative controls of note 4 on calibration 12's linear configuration (k = 5, V_MC/V_data = 1, correlated MC noise): toys
    reusing the nominal MC without perturbation (size too large), toys perturbed by N(0, V_MC') with the direction of
    V_MC wrong, and re-digitization changing only Philox
    (refused by the plan check `design.toy_philox_only`)."""
    k, ratio, n, d = 5, 1.0, 12, 2
    rng0 = np.random.default_rng([cal_seed(12, 0), 900])
    J = rng0.normal(size=(n, d))
    Jv = rng0.normal(size=(k, d))
    A0 = rng0.normal(size=(n, n))
    Vm = A0 @ A0.T
    Vm *= ratio * n / np.trace(Vm)                          # correlated MC noise, trace ratio 1
    A1 = rng0.normal(size=(k, k))
    Vmv = A1 @ A1.T
    Vmv *= ratio * k / np.trace(Vmv)
    Vd, Vdv = np.eye(n), np.eye(k)
    W = np.linalg.inv(Vd + Vm)
    Sig = np.linalg.inv(J.T @ W @ J)
    A = Sig @ J.T @ W
    Cr = Vdv + Vmv + Jv @ Sig @ Jv.T
    Cp, _ = V.c_r_plus(Cr, np.ones(k), [])

    # the direction wrong: the toys' MC noise, with its trace kept, along the directions T_v is least sensitive to:
    # the validation side along C_r's largest eigenvector (C_r^+ smallest), the calibration side in the null space of
    # the propagation J_v A, so the toys understate the residual's MC term (size too large)
    u_v = np.linalg.eigh(Cr)[1][:, -1]
    u_c = np.linalg.svd(Jv @ A)[2][-1]
    vm_wrong, vmv_wrong = np.trace(Vm) * np.outer(u_c, u_c), np.trace(Vmv) * np.outer(u_v, u_v)

    def tv(rv):
        return float(rv @ Cp @ rv)
    refs = {"replica-difference": [], "no-perturbation": [], "wrong-direction": []}
    rng = np.random.default_rng([cal_seed(12, 1), 900])
    for _ in range(n_ref):
        yc = rng.multivariate_normal(np.zeros(n), Vd)
        yv = rng.multivariate_normal(np.zeros(k), Vdv)
        pc = (rng.multivariate_normal(np.zeros(n), Vm) - rng.multivariate_normal(np.zeros(n), Vm)) / np.sqrt(2)
        pv = (rng.multivariate_normal(np.zeros(k), Vmv) - rng.multivariate_normal(np.zeros(k), Vmv)) / np.sqrt(2)
        refs["replica-difference"].append(tv(yv - pv - Jv @ (A @ (yc - pc))))
        refs["no-perturbation"].append(tv(yv - Jv @ (A @ yc)))
        wc = rng.multivariate_normal(np.zeros(n), vm_wrong)
        wv = rng.multivariate_normal(np.zeros(k), vmv_wrong)
        refs["wrong-direction"].append(tv(yv - wv - Jv @ (A @ (yc - wc))))
    refs = {kk: np.sort(v) for kk, v in refs.items()}
    rej = {kk: 0 for kk in refs}
    rng = np.random.default_rng([cal_seed(12, 2), 900])
    for _ in range(reps):
        yc = rng.multivariate_normal(np.zeros(n), Vd)
        yv = rng.multivariate_normal(np.zeros(k), Vdv)
        e_c = rng.multivariate_normal(np.zeros(n), Vm)
        e_v = rng.multivariate_normal(np.zeros(k), Vmv)
        T_obs = tv(yv - e_v - Jv @ (A @ (yc - e_c)))
        for kk, ref in refs.items():
            rej[kk] += (ref.size - np.searchsorted(ref, T_obs, "left") + 1) / (ref.size + 1) <= ALPHA_TV
    size = {kk: v / reps for kk, v in rej.items()}
    plan_codes = {c: [x["code"] for x in DN.practice_findings({"toys": {"construction": c}})]
                  for c in ("philox-only", "nominal-reuse", "parametric-gaussian")}
    rec = {"size": size, "plan_check_codes": plan_codes,
           "passed": bool(abs(size["replica-difference"] - ALPHA_TV) <= 0.25 * ALPHA_TV
                          and size["no-perturbation"] > 1.25 * ALPHA_TV
                          and size["wrong-direction"] > ALPHA_TV + 3 * math.sqrt(ALPHA_TV * (1 - ALPHA_TV) / reps)
                          and plan_codes["philox-only"] == ["design.toy_philox_only"]
                          and plan_codes["nominal-reuse"] == ["design.toy_nominal_reuse"]
                          and plan_codes["parametric-gaussian"] == ["design.toy_parametric_mc"])}
    return {"calibration": 12, "item": "negative controls of note 4", **rec, "reps": reps, "n_ref": n_ref}


# ------------------------------------------------------------------ task table, tasks, merge
def _tasks() -> list:
    t = []
    for c in TV_CONFIGS:
        t += [("tv", {"config": c, "r0": 500 * i, "reps": 500}) for i in range(20)]
    for K in G6_K:
        t += [("g6", {"K": K, "r0": 200 * i, "reps": 200}) for i in range(10)]
    for m in G7_MODES:
        t += [("g7", {"mode": m, "r0": 500 * i, "reps": 500}) for i in range(2)]
    t += [("sigma_boot", {"part": "estimate", "r0": SIGMA_BOOT_RUNS_PER_TASK * i, "reps": SIGMA_BOOT_RUNS_PER_TASK})
          for i in range(SIGMA_BOOT_TASKS)]
    t += [("sigma_boot", {"part": "truth", "r0": SIGMA_BOOT_TRUTH_TOYS * i, "reps": SIGMA_BOOT_TRUTH_TOYS})
          for i in range(SIGMA_BOOT_TRUTH_TASKS)]
    t += [("sigma_boot", {"part": "asimov", "r0": 0, "reps": 3})]
    t += [("interval", {"r0": 100 * i, "reps": 100}) for i in range(20)]
    return t


TASKS = _tasks()
BLOCKS = {"tv": tv_block, "g6": g6_block, "g7": g7_block, "sigma_boot": sigma_boot_block, "interval": interval_block}


def _key(name, kw):
    return {"tv": lambda: kw["config"], "g6": lambda: f"K={kw['K']}", "g7": lambda: kw["mode"],
            "sigma_boot": lambda: kw["part"], "interval": lambda: "coverage"}[name]()


def run_task(i: int, out_dir: Path) -> dict:
    name, kw = TASKS[i]
    t0 = time.time()
    rows = BLOCKS[name](**kw)
    rec = {"task": i, "block": name, "kwargs": kw, "key": _key(name, kw), "rows": rows, "seconds": time.time() - t0,
           "provenance": G.provenance(), "label": "synthetic"}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


JUDGES = {"tv": tv_judge, "g6": g6_judge, "g7": g7_judge, "sigma_boot": sigma_boot_judge, "interval": interval_judge}


def merge(out_dir: Path, out: Path) -> dict:
    recs = {}
    for i in range(len(TASKS)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    by = {}
    for r in recs.values():
        if r:
            by.setdefault(r["block"], {}).setdefault(r["key"], []).extend(r["rows"])
    results = {b: JUDGES[b](v) for b, v in by.items()}
    complete = not missing and len(commits) == 1 and not dirty
    rep = {"array": "deferred section 8.7 calibrations, batch B (10, 12)", "complete": complete,
           "missing_tasks": missing, "commits": sorted(commits), "dirty": dirty, "results": results,
           "passed": {k: v["passed"] for k, v in results.items()}, "provenance": G.provenance(), "label": "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


LOCAL = {"plus_half": cal10_plus_half, "replacement": cal10_replacement, "vhat": cal10_vhat,
         "controls": cal12_controls}
SMOKE = {"tv": ("tv", {"config": "shape K=50", "r0": 900000, "reps": 2}),
         "tv_shared": ("tv", {"config": "shared p=50", "r0": 900000, "reps": 2}),
         "g6": ("g6", {"K": 50, "r0": 900000, "reps": 2}),
         "g7": ("g7", {"mode": "farthest|0.01", "r0": 900000, "reps": 5}),
         "sigma_boot": ("sigma_boot", {"part": "estimate", "r0": 900000, "reps": 1}),
         "sigma_boot_truth": ("sigma_boot", {"part": "truth", "r0": 900000, "reps": 1}),
         "interval": ("interval", {"r0": 900000, "reps": 1})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", choices=sorted(LOCAL))
    ap.add_argument("--smoke", choices=sorted(SMOKE))
    ap.add_argument("--reps", type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.task is not None:
        r = run_task(a.task, Path(a.out))
        print(json.dumps({"task": r["task"], "block": r["block"], "key": r["key"], "seconds": r["seconds"]}))
        return 0
    if a.merge:
        r = merge(Path(a.merge), Path(a.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if a.local:
        t0 = time.time()
        r = LOCAL[a.local](**({"reps": a.reps} if a.reps else {}))
        r.update(seconds=time.time() - t0, provenance=G.provenance(), label="synthetic")
        io.write_json(a.out, io.jsonable(r))
        print(json.dumps({"item": r.get("item"), "passed": r["passed"], "seconds": r["seconds"]}))
        return 0 if r["passed"] else 1
    if a.smoke:
        name, kw = SMOKE[a.smoke]
        t0 = time.time()
        rows = BLOCKS[name](**kw)
        rec = {"block": name, "kwargs": kw, "rows": rows, "seconds": time.time() - t0, "label": "smoke"}
        io.write_json(a.out, io.jsonable(rec))
        print(json.dumps({"block": name, "seconds": rec["seconds"], "rows": len(rows)}))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
