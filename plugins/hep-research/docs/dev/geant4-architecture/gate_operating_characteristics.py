"""Operating characteristics of the convergence gate (architecture.md section 5.5).

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
# se drawn from the two-stage design: se_actual = target * sqrt(F / f)
f = stats.f.ppf(0.9, 15, 15)
Fr = rng.f(15, 15, N)
seA = se * np.sqrt(Fr / f)
for d in (0, 0.5, 1, 2):
    D = rng.normal(d, seA)
    S = seA * np.sqrt(rng.chisquare(nu, N) / nu)
    print("two-stage d", d, "pass", (np.abs(D) + qp * S <= tol).mean(),
          "fail30", (np.abs(D) - qf(30) * S > tol).mean(), "E[se]/tol", seA.mean())
# Welch degrees of freedom with unequal variances (K = 16 each)
for r in (1, 2, 4, 10):
    v1, v2 = 1.0, r
    print("welch ratio", r, (v1 + v2) ** 2 / (v1 ** 2 / 15 + v2 ** 2 / 15))
