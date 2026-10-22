"""Operating characteristics of the convergence gate (geant4-program.md §A.8 and §R.6.6).

Recomputes pass and fail probabilities of the intersection-union gate with t quantiles and an estimated se
(se_hat^2 = se^2 chi2_nu / nu), the same with the se distribution of the two-stage design, the two-stage
factor F_0.90(K-1, K-1) and Welch degrees of freedom. Needs numpy and scipy. Design aid, not plugin code.
Written by the independent statistics review of 2026-10-22.
"""
import numpy as np
from scipy import stats

print("F0.90(15,15)", stats.f.ppf(0.9, 15, 15), " F0.95(15,15)", stats.f.ppf(0.95, 15, 15))
for K in (16, 32):
    print(K, stats.f.ppf(0.9, K - 1, K - 1))
nu = 30
tol = 1.0
se = tol / 4
qp = stats.t.ppf(0.95, nu)


def qf(m):
    return stats.t.ppf(1 - 0.05 / m, nu)


print("qp", qp, "qf1", qf(1), "qf30", qf(30))
# known se, normal quantiles (how the earlier table was computed)
for d in (0, 0.5, 1):
    p = stats.norm.cdf((tol - qp * se - d) / se) - stats.norm.cdf((-tol + qp * se - d) / se)
    print("pass known-se d=", d, p)
for m in (1, 30):
    d = 2
    p = 1 - stats.norm.cdf((tol + qf(m) * se - d) / se) + stats.norm.cdf((-tol - qf(m) * se - d) / se)
    print("fail known-se m", m, p)
# estimated se: se_hat^2 = se^2 chi2_nu / nu
rng = np.random.default_rng(1)
N = 2_000_000
for d in (0, 0.5, 1, 2):
    D = rng.normal(d, se, N)
    S = se * np.sqrt(rng.chisquare(nu, N) / nu)
    P = (np.abs(D) + qp * S <= tol).mean()
    F1 = (np.abs(D) - qf(1) * S > tol).mean()
    F30 = (np.abs(D) - qf(30) * S > tol).mean()
    print("est-se d", d, "pass", P, "fail m1", F1, "fail m30", F30, "unres", 1 - P - F1)
# Two-stage design, modelled per point (two points a, b; K = K_trial = 16):
#   trial: estimated SE_trial^2 = sigma^2/N_trial * X_t, X_t ~ chi2_15/15
#   N = N_trial (SE_trial/target)^2 f  ->  true se = target / sqrt(f X_t)
#   final estimated se = true se * sqrt(chi2_15/15), independent of X_t
#   a point whose estimated se exceeds its target is incomplete (no top-up)
# The gate uses se_diff = sqrt(se_a^2 + se_b^2) and Welch nu from the estimated se.
# (Revised 2026-10-23: the earlier version drew the true se as target*sqrt(F/f),
# which double-counted the trial chi2 factor.)
f = stats.f.ppf(0.9, 15, 15)
tgt = tol / (4 * np.sqrt(2))
Kd = 15


def point():
    true = tgt / np.sqrt(f * rng.chisquare(Kd, N) / Kd)
    est = true * np.sqrt(rng.chisquare(Kd, N) / Kd)
    return true, est


for d in (0, 0.5, 1, 2):
    ta, ea = point()
    tb, eb = point()
    D = rng.normal(d, np.sqrt(ta ** 2 + tb ** 2))
    S = np.sqrt(ea ** 2 + eb ** 2)
    nuw = S ** 4 / (ea ** 4 / Kd + eb ** 4 / Kd)
    met = (ea <= tgt) & (eb <= tgt)
    qpw = stats.t.ppf(0.95, nuw)
    qfw = stats.t.ppf(1 - 0.05 / 30, nuw)
    passed = np.abs(D) + qpw * S <= tol
    failed = np.abs(D) - qfw * S > tol
    print("two-stage d", d,
          "pass(both met)", (passed & met).mean(),
          "pass|met", passed[met].mean(),
          "fail30(both met)", (failed & met).mean(),
          "fail30 any", failed.mean(),
          "pair incomplete (target)", 1 - met.mean(),
          "E[se_diff]/tol", np.sqrt(ta ** 2 + tb ** 2).mean())
# Welch degrees of freedom with unequal variances (K = 16 each)
for r in (1, 2, 4, 10):
    v1, v2 = 1.0, r
    print("welch ratio", r, (v1 + v2) ** 2 / (v1 ** 2 / 15 + v2 ** 2 / 15))
