"""Shift mode of phi: P8 and G9 (Part B sections 5.5, 8.2 notes 10, 7.5; phase 2, WP3). `calib_shift.py` is the CLI.

Shift-mode phi are fixed at their nominal values in the fit and enter through refits at phi_l = +-1, +-2 in their
unit-normal coordinates (section 5.5: they must already be whitened, block-independent of the profile-mode phi;
P8, G9 and the export use the same transformation). The problem supplies `h_shift(tp, phi_s)`: the link-space
predictor with the shift-mode phi set to phi_s (unit-normal coordinates) and `shift_names`.

- P8 (section 5.5 condition 1, at theta_ref with Asimov data): the conditional information of the data on the
  shift-mode phi with theta, nu, eta, the profile phi and the MC nuisances profiled, excluding the phi's own external
  constraint; the largest eigenvalue of Sigma_phi^1/2 I_phiphi.rest Sigma_phi^1/2 (= I in unit-normal coordinates)
  <= c = 0.1.
- G9 (section 5.5 condition 2, at theta-hat), decided only after P8 passed: D_il(k) = theta-hat_i(phi_l = k) -
  theta-hat_i(0), a, c2, c3, c1 and Delta_i <= t_lin = 0.06 (one-sided), s_i = sqrt(sigma_tot,i^2 + sum_l a_il^2);
  and condition 1 recomputed at theta-hat with 1.5c. A refit that does not converge fails G9 (section 7.3 Class 1).
- d_l and the export columns use the symmetric difference a_il; the interval widening uses max(|D(+1)|, |D(-1)|)
  (D52 (b), A8).
"""
from __future__ import annotations

import numpy as np
from scipy import linalg

from . import fit as F
from . import likelihood as L

C_INFO = 0.1
T_LIN = 0.06


class _Extended:
    """The problem with the shift-mode phi as free columns (no constraint): used only for the information of P8."""

    def __init__(self, base, center: np.ndarray):
        self.b = base
        lay = base.layout
        q = len(base.shift_names)
        self.q = q
        self.layout = L.Layout(lay.blocks, lay.n_link, lay.theta, list(lay.phi_P) + list(base.shift_names), lay.n_nu,
                               lay.n_eta, lay.omega, lay.gamma, lay.delta)
        self.n0 = len(lay.theta) + len(lay.phi_P)
        d = base.observed
        phi0 = np.r_[np.zeros(0) if d.phi0 is None else d.phi0, np.zeros(q)]
        cov = np.zeros((len(phi0), len(phi0)))
        if d.phi_cov is not None:
            k = d.phi_cov.shape[0]
            cov[:k, :k] = d.phi_cov
        cov[len(phi0) - q:, len(phi0) - q:] = np.eye(q)
        self.observed = L.Observations(d.y_gauss, d.counts, d.binom, phi0, cov, d.aux_m, d.aux_k, d.nu0, d.eta0)
        self.center = center

    def h(self, tp):
        return self.b.h_shift(tp[:self.n0], tp[self.n0:])

    def reference(self, tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
        return self.b.reference(tp[:self.n0], beta, frozen, bootstrap_frozen=bootstrap_frozen)

    def __getattr__(self, k):
        return getattr(self.b, k)


def conditional_information(problem, beta: np.ndarray, ref: L.Reference | None = None) -> np.ndarray:
    """I_phiphi.rest of the data for the shift-mode phi (lnL units), the phi's own constraint excluded."""
    ext = _Extended(problem, beta)
    lay = problem.layout
    n0 = len(lay.theta) + len(lay.phi_P)
    q = ext.q
    lk_e = L.Likelihood(ext.layout, ext.observed, ref or problem.reference(beta[:n0], beta))
    be = np.r_[beta[:n0], np.zeros(q), beta[n0:]]
    tpi = F._tp_index(lk_e)
    steps = np.r_[F.fd_steps(problem), np.full(q, 1e-3)]
    cols = []
    for i, s in enumerate(steps):
        a, c = be[tpi].copy(), be[tpi].copy()
        a[i] += s
        c[i] -= s
        cols.append((ext.h(a) - ext.h(c)) / (2 * s))
    link_jacobian = np.stack(cols, axis=1)
    _, Fm = lk_e.score_fisher(be, ext.h(be[tpi]), link_jacobian)
    Fm = 0.5 * Fm                                        # information of ln L
    ph = np.arange(n0, n0 + q)
    Fm[np.ix_(ph, ph)] -= np.eye(q)                      # exclude the phi's own external constraint
    rest = np.setdiff1d(np.arange(Fm.shape[0]), ph)
    I = Fm[np.ix_(ph, ph)] - Fm[np.ix_(ph, rest)] @ linalg.solve(Fm[np.ix_(rest, rest)], Fm[np.ix_(rest, ph)],
                                                               assume_a="pos")
    return 0.5 * (I + I.T)


def p8(problem, beta_ref: np.ndarray, c: float = C_INFO) -> dict:
    """P8 at theta_ref with Asimov data (section 8.2): largest eigenvalue <= c; not applicable without shift phi."""
    if not getattr(problem, "shift_names", None):
        return {"gate": "P8", "status": "not-applicable"}
    I = conditional_information(problem, beta_ref)
    lam = float(np.linalg.eigvalsh(I).max())
    ok = lam <= c
    return {"gate": "P8", "status": "passed" if ok else "failed", "lambda_max": lam, "c": c,
            "finding": None if ok else "p8.information", "remedy": "contract"}


class _Shifted:
    def __init__(self, base, phis):
        self.b, self.phis = base, np.asarray(phis, float)

    def h(self, tp):
        return self.b.h_shift(tp, self.phis)

    def __getattr__(self, k):
        return getattr(self.b, k)


def refits(problem, fit: F.Fit, seed=None, multistart: bool = True) -> dict:
    """The four refits per shift-mode phi at theta-hat (data unchanged, phi_l in the model moved, the other shift phi
    nominal), using the fit's event intervals (the same evaluator) and the section 7.4 multi-start."""
    q = len(problem.shift_names)
    d = len(problem.layout.theta)
    out = {}
    for l in range(q):
        for k in (-2, -1, 1, 2):
            ph = np.zeros(q)
            ph[l] = k
            v = _Shifted(problem, ph)
            r = (F.find_extremum(v, (F._seed_int(seed or 0), l, k + 10), fit.beta, frozen=fit.ref)
                 if multistart else F.iterate(v, fit.beta, frozen=fit.ref))
            out[(l, k)] = {"converged": r.converged, "theta": r.beta[:d].copy(), "beta": r.beta.copy(),
                           "reason": r.reason}
    return out


def linearity(D: dict, sigma_tot: np.ndarray, q: int) -> dict:
    """Delta_i of section 5.5 from the refit differences D[(l, k)] (theta-hat(phi_l = k) - theta-hat(0))."""
    d = sigma_tot.size
    a = np.zeros((d, q))
    c2 = np.zeros((d, q))
    c3 = np.zeros((d, q))
    for l in range(q):
        Dp1, Dm1, Dp2, Dm2 = D[(l, 1)], D[(l, -1)], D[(l, 2)], D[(l, -2)]
        a[:, l] = 0.5 * (Dp1 - Dm1)
        c2[:, l] = 0.5 * (Dp1 + Dm1)
        c3[:, l] = (0.5 * (Dp2 - Dm2) - (Dp1 - Dm1)) / 6.0
    c1 = a - c3
    s2 = sigma_tot ** 2 + np.sum(a ** 2, axis=1)
    num = np.sum(c2, axis=1) ** 2 + np.sum(2 * c2 ** 2 + 4 * c1 * c3 + 14 * c3 ** 2, axis=1)
    return {"Delta": (num / s2).tolist(), "a": a, "s": np.sqrt(s2)}


def g9(problem, fit: F.Fit, p8_result: dict, seed=None, c: float = C_INFO, t_lin: float = T_LIN,
       multistart: bool = True) -> dict:
    """G9 at theta-hat (section 8.2 note 10): decided only after P8 passed; any refit not converged fails;
    Delta_i <= t_lin for every i; condition 1 at theta-hat with 1.5c."""
    if not getattr(problem, "shift_names", None):
        return {"gate": "G9", "status": "not-applicable"}
    if p8_result.get("status") != "passed":
        return {"gate": "G9", "status": "not-decided", "reason": "P8 did not pass (G9 is decided only after P8)"}
    q = len(problem.shift_names)
    rf = refits(problem, fit, seed, multistart)
    bad = [k for k, v in rf.items() if not v["converged"]]
    if bad:
        return {"gate": "G9", "status": "failed", "finding": "g9.refit_not_converged", "refits": [list(k) for k in bad],
                "remedy": "contract"}
    d = len(problem.layout.theta)
    D = {k: v["theta"] - fit.beta[:d] for k, v in rf.items()}
    lin = linearity(D, fit.sigma_tot, q)
    lam = float(np.linalg.eigvalsh(conditional_information(problem, fit.beta, fit.ref)).max())
    findings = []
    if max(lin["Delta"]) > t_lin:
        findings.append("g9.linearity")
    if lam > 1.5 * c:
        findings.append("g9.information")
    ok = not findings
    plus = np.stack([D[(l, 1)] for l in range(q)], axis=1)
    minus = np.stack([D[(l, -1)] for l in range(q)], axis=1)
    return {"gate": "G9", "status": "passed" if ok else "failed", "Delta": lin["Delta"], "t_lin": t_lin,
            "lambda_max_at_fit": lam, "threshold": 1.5 * c, "findings": findings,
            "finding": findings[0] if findings else None, "remedy": "contract",
            "symmetric": lin["a"].tolist(),                                   # a_il: d_l, G_s (D52 (b))
            "widening": np.maximum(np.abs(plus), np.abs(minus)).tolist(),    # interval widening (D52 (b))
            "refits": {f"{l},{k}": rf[(l, k)]["theta"].tolist() for (l, k) in rf}}


def d_columns(problem, fit: F.Fit, rf: dict, mu_v, sigma: float = 1.0, sign: float = 1.0,
              direct: bool = True) -> np.ndarray:
    """d_l = (d mu_v / d phi_l + J_v d beta-hat / d phi_l |refit) sigma_phi_l (section 9.2), from the symmetric
    differences of the +-1 sigma refits (D52 (b)). `mu_v(beta, phis)` is the validation prediction at the full beta
    (theta, phi_P, nu, eta) with the shift phi at `phis`. The sign is a plus (a refit is "data unchanged, phi in the
    model moved"); `sign=-1` and `direct=False` (only the indirect effect) are the negative controls of section
    15.3.1."""
    q = len(problem.shift_names)
    cols = []
    zero = np.zeros(q)
    for l in range(q):
        e = np.zeros(q)
        e[l] = 1.0
        dmu = 0.5 * (mu_v(fit.beta, e) - mu_v(fit.beta, -e)) if direct else 0.0
        resp = 0.5 * (mu_v(rf[(l, 1)]["beta"], zero) - mu_v(rf[(l, -1)]["beta"], zero))
        cols.append((dmu + sign * resp) * sigma)
    return np.stack(cols, axis=1)
