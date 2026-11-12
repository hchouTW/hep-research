"""The joint likelihood of Part B section 2.1 (phase 2): blocks, link functions, nuisances, V_model.

-2 ln L(theta, nu, eta, phi_P, gamma, omega) = sum_b -2 ln L_b(y_b | mu_b) + sum_b' -2 ln L^aux_b'(m_MC | gamma_b')
                                             + sum nu^2 + sum eta^2 + (phi_P - phi_P0)^T Sigma_phiP^-1 (...)

Prediction in link space (section 2.1 "Link functions"): g(mu_i) = g(m_i(theta, phi)) + sum_k nu_k u_ki + sum_j eta_j s_ji.
Blocks:

- `gaussian`: every Gaussian observable in one block, -2 ln L_G = r^T W r with W the projected inverse of V_G on
  N_d,c^perp in standardized coordinates (section 2.1 "Calibration-side constraints by construction"); scalar
  observables carry a link (identity, log, logit, fisher-z); a Gaussian shape summary statistic carries alr or ilr
  coordinates of n + 1/2 on the data side and of the model shape on the prediction side (section 2.1, 5.3).
- `poisson`: a count shape of K bins, free-omega (mu_k = omega p_k gamma_k, p = softmax(alr(p_model) + U nu + S eta))
  or absolute counts (log mu_k = log m_k + U nu + S eta, times gamma_k); BB-lite gamma_k with the auxiliary
  measurement m_k ~ Poisson(tau_k gamma_k), observed m_k = tau_k = (sum w)^2 / sum w^2 at theta_ref.
- `binomial`: one efficiency bin, k of N; the MC efficiency nuisance delta (on the logit scale) with the auxiliary
  binomial likelihood of the variance-matched effective counts (n_eff, k_eff) (section 2.1, D30); the data
  efficiency is logit^-1(logit eps_MC(theta, phi) + delta + U nu + S eta).

beta = (theta, phi_P, nu, eta, omega, gamma, delta, phi_map) in that order (phi_map: the efficiency-map term
U(theta) phi_map of section 6.7, `map_term.py`, N(0, I), profiled with theta). The engine minimizes by Fisher scoring
(`fit.py`): each block returns its deviance, the gradient and the expected information with respect to its
link-space predictor and its own nuisances; theta and phi columns of the predictor are central differences of
the evaluator with common random numbers.

All quantities are produced by the model at theta_ref (section 2.1 "Sources of errors"): `Reference` holds V_G,
tau, n_eff, the Gaussian data covariance and the nuisance columns at the current reference point; `fit.py`
recomputes it at every section 7.3 iteration.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import linalg, special, stats

LINKS = ("identity", "log", "logit", "fisher-z")
SHAPE_LINKS = ("alr", "ilr")


class LikelihoodError(ValueError):
    """A likelihood that cannot be built from the contract: `code` names the rule (exit 2 at the CLI)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ links (section 2.1)
def link(x, kind: str):
    x = np.asarray(x, dtype=float)
    if kind == "identity":
        return x.copy()
    if kind == "log":
        return np.log(x)
    if kind == "logit":
        return special.logit(x)
    if kind == "fisher-z":
        return np.arctanh(x)
    raise LikelihoodError("likelihood.link", f"unknown link {kind!r}")


def inv_link(z, kind: str):
    z = np.asarray(z, dtype=float)
    if kind == "identity":
        return z.copy()
    if kind == "log":
        return np.exp(z)
    if kind == "logit":
        return special.expit(z)
    if kind == "fisher-z":
        return np.tanh(z)
    raise LikelihoodError("likelihood.link", f"unknown link {kind!r}")


def dlink(x, kind: str):
    """dg/dmu at mu = x (the delta-method factor from natural to link space)."""
    x = np.asarray(x, dtype=float)
    if kind == "identity":
        return np.ones_like(x)
    if kind == "log":
        return 1.0 / x
    if kind == "logit":
        return 1.0 / (x * (1.0 - x))
    if kind == "fisher-z":
        return 1.0 / (1.0 - x * x)
    raise LikelihoodError("likelihood.link", f"unknown link {kind!r}")


# ------------------------------------------------------------------ log-ratio coordinates (sections 2.1, 5.4)
def helmert(K: int) -> np.ndarray:
    """An orthonormal K x (K-1) contrast basis (columns orthogonal to 1): the ilr basis."""
    H = np.zeros((K, K - 1))
    for j in range(1, K):
        H[:j, j - 1] = 1.0 / j
        H[j, j - 1] = -1.0
        H[:, j - 1] *= math.sqrt(j / (j + 1.0))
    return H


def logratio_matrix(K: int, kind: str, reference: int | None = None, basis=None) -> np.ndarray:
    """The (K-1) x K matrix L with coordinates = L @ log(p): alr with the declared reference category (default the
    last), or ilr with the declared contrast basis (default Helmert). L annihilates the constant vector, so the
    coordinates do not depend on the normalization of p (sections 2.1, 5.3)."""
    if kind == "alr":
        ref = K - 1 if reference is None else int(reference)
        L = np.zeros((K - 1, K))
        others = [k for k in range(K) if k != ref]
        for i, k in enumerate(others):
            L[i, k] = 1.0
            L[i, ref] = -1.0
        return L
    if kind == "ilr":
        B = helmert(K) if basis is None else np.asarray(basis, dtype=float)
        if B.shape != (K, K - 1) or np.abs(B.sum(axis=0)).max() > 1e-9:
            raise LikelihoodError("likelihood.ilr_basis", "the ilr contrast basis must be K x (K-1) with zero-sum "
                                  "columns")
        return B.T
    raise LikelihoodError("likelihood.link", f"unknown shape link {kind!r}")


def logratio_inverse(a: np.ndarray, L: np.ndarray) -> np.ndarray:
    """p = softmax(x) with L x = a and x orthogonal to 1: always inside the simplex and summing to 1."""
    x = np.linalg.pinv(L) @ a
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()


def centered_log_ratio_to(L: np.ndarray) -> np.ndarray:
    """H with coordinates = H clr(p) (H = L, since L annihilates 1 and clr = log p - mean log p): the map of the
    clr-declared correlation kernels into the contract's coordinates, R = H R_clr H^T (section 5.4)."""
    return L.copy()


def shape_summary(counts, L: np.ndarray) -> np.ndarray:
    """The data-side Gaussian summary statistic of a normalized shape: the log-ratio coordinates of n_k + 1/2 over
    all K bins (Jeffreys correction), defined for any counts (section 2.1)."""
    return L @ np.log(np.asarray(counts, dtype=float) + 0.5)


# ------------------------------------------------------------------ MC statistics in non-Gaussian blocks (section 2.1)
def bb_tau(sumw, sumw2) -> np.ndarray:
    """BB-lite effective MC counts tau = (sum w)^2 / sum w^2 (0 for a bin without MC events)."""
    sumw, sumw2 = np.asarray(sumw, float), np.asarray(sumw2, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(sumw2 > 0, sumw * sumw / np.where(sumw2 > 0, sumw2, 1.0), 0.0)


def binomial_effective(WP, SP, WF, SF, VPF=0.0) -> tuple[float, float]:
    """The variance-matched effective counts (n_eff, k_eff) of a weighted binomial bin (section 2.1, D30):
    n_eff = eps(1-eps) W^2 / [(1-eps)^2 S_P - 2 eps(1-eps) V_PF + eps^2 S_F], k_eff = n_eff eps, eps = W_P / W;
    at eps = 0 or 1, n_eff = W^2 / (S_P + S_F)."""
    W = WP + WF
    if W <= 0:
        return 0.0, 0.0
    eps = WP / W
    if eps <= 0.0 or eps >= 1.0:
        n = W * W / (SP + SF)
        return n, n * eps
    den = (1 - eps) ** 2 * SP - 2 * eps * (1 - eps) * VPF + eps ** 2 * SF
    if den <= 0:
        raise LikelihoodError("likelihood.weights", "the pass/fail weight moments give a non-positive variance")
    n = eps * (1 - eps) * W * W / den
    return n, n * eps


def binomial_scope(eps, n_eff, SP, SF, TP, TF) -> dict:
    """The acceptance scope of the effective-count approximation (section 2.1): k_exp = n_eff min(eps, 1-eps) >= 30
    and Delta_sk = |gamma_1 - gamma_1,bin| <= 0.1, computed from expected values."""
    k_exp = n_eff * min(eps, 1 - eps)
    g1 = ((1 - eps) ** 3 * TP - eps ** 3 * TF) / ((1 - eps) ** 2 * SP + eps ** 2 * SF) ** 1.5
    g1_bin = (1 - 2 * eps) / math.sqrt(n_eff * eps * (1 - eps))
    d = abs(g1 - g1_bin)
    return {"k_exp": k_exp, "delta_sk": d, "in_scope": bool(k_exp >= 30 and d <= 0.1)}


def _xlogy(x, y):
    return special.xlogy(x, y)


def poisson_deviance(n, mu) -> float:
    n, mu = np.asarray(n, float), np.asarray(mu, float)
    return float(2.0 * np.sum(mu - n + _xlogy(n, n) - _xlogy(n, mu)))


def binomial_deviance(k, N, eps) -> float:
    """-2 ln L of k of N at efficiency eps relative to the saturated model (real k, N allowed)."""
    k, N, eps = np.asarray(k, float), np.asarray(N, float), np.asarray(eps, float)
    return float(2.0 * np.sum(_xlogy(k, k) - _xlogy(k, N * eps) + _xlogy(N - k, N - k) - _xlogy(N - k, N * (1 - eps))))


# ------------------------------------------------------------------ layout
@dataclass
class Block:
    """One block of the likelihood. kind: gaussian-scalar, gaussian-shape, poisson, binomial. `index` are the rows
    of the block in the stacked link-space predictor (K-1 for alr/ilr shapes, K for absolute counts, 1 otherwise)."""
    name: str
    kind: str
    link: str
    index: np.ndarray
    K: int = 1
    L: np.ndarray | None = None          # log-ratio matrix of a shape
    free_omega: bool = False
    bb: bool = False                      # BB-lite gamma per bin (poisson)
    role: str = "calibration"


@dataclass
class Layout:
    """The stacked link-space predictor of the calibration observables and the order of beta."""
    blocks: list
    n_link: int
    theta: list
    phi_P: list
    n_nu: int
    n_eta: int
    omega: list = field(default_factory=list)     # block names with a free omega
    gamma: list = field(default_factory=list)     # (block name, bin) with a BB-lite gamma
    delta: list = field(default_factory=list)     # block names with an MC efficiency nuisance
    n_phi_map: int = 0                            # the efficiency-map term's phi_map (map_term.py, section 6.7)

    @property
    def sizes(self):
        return {"theta": len(self.theta), "phi_P": len(self.phi_P), "nu": self.n_nu, "eta": self.n_eta,
                "omega": len(self.omega), "gamma": len(self.gamma), "delta": len(self.delta),
                "phi_map": self.n_phi_map}

    def slices(self):
        out, a = {}, 0
        for k, n in self.sizes.items():
            out[k] = slice(a, a + n)
            a += n
        return out

    @property
    def n_beta(self):
        return sum(self.sizes.values())

    def gaussian_rows(self):
        rows = [b.index for b in self.blocks if b.kind.startswith("gaussian")]
        return np.concatenate(rows) if rows else np.zeros(0, dtype=int)


def build_layout(observables: list[dict], theta: list[str], phi_P: list[str], n_nu: int, n_eta: int) -> Layout:
    """Observables: {name, block (gaussian|poisson|binomial), link, bins (K, shapes), shape_link (alr|ilr),
    reference, basis, free_omega, bb}. The block rules of section 2.1 are the contract checker's; here only the
    representation is built."""
    blocks, row = [], 0
    omega, gamma, delta = [], [], []
    for o in observables:
        kind = o.get("block", "gaussian")
        if kind == "gaussian" and int(o.get("bins", 1)) > 1:
            K = int(o["bins"])
            L = logratio_matrix(K, o.get("shape_link", "alr"), o.get("reference"), o.get("basis"))
            blocks.append(Block(o["name"], "gaussian-shape", o.get("shape_link", "alr"), np.arange(row, row + K - 1),
                                K, L, role=o.get("role", "calibration")))
            row += K - 1
        elif kind == "gaussian":
            lk = o.get("link", "identity")
            if lk not in LINKS:
                raise LikelihoodError("likelihood.link", f"observable {o['name']}: unknown link {lk!r}")
            blocks.append(Block(o["name"], "gaussian-scalar", lk, np.arange(row, row + 1), role=o.get("role",
                                                                                                      "calibration")))
            row += 1
        elif kind == "poisson":
            K = int(o.get("bins", 1))
            free = bool(o.get("free_omega", K > 1))
            if free and K < 2:
                raise LikelihoodError("likelihood.shape", f"observable {o['name']}: a free-omega shape needs K >= 2")
            if free:
                L = logratio_matrix(K, o.get("shape_link", "alr"), o.get("reference"), o.get("basis"))
                blocks.append(Block(o["name"], "poisson", "alr", np.arange(row, row + K - 1), K, L, True,
                                    bool(o.get("bb", False)), o.get("role", "calibration")))
                row += K - 1
                omega.append(o["name"])
            else:
                blocks.append(Block(o["name"], "poisson", "log", np.arange(row, row + K), K, None, False,
                                    bool(o.get("bb", False)), o.get("role", "calibration")))
                row += K
            if o.get("bb", False):
                gamma += [(o["name"], k) for k in range(K)]
        elif kind == "binomial":
            blocks.append(Block(o["name"], "binomial", "logit", np.arange(row, row + 1), role=o.get("role",
                                                                                                  "calibration")))
            row += 1
            if o.get("mc_nuisance", True):
                delta.append(o["name"])
        else:
            raise LikelihoodError("likelihood.block", f"observable {o['name']}: unknown block {kind!r}")
    return Layout(blocks, row, list(theta), list(phi_P), int(n_nu), int(n_eta), omega, gamma, delta)


# ------------------------------------------------------------------ reference quantities and data
@dataclass
class Reference:
    """Model-produced quantities at theta_ref (section 2.1 "Sources of errors"; section 7.3 step 1): fixed while the
    likelihood is minimized, recomputed at each reference-point iteration.

    V_G: covariance of the Gaussian rows in link space (V_data^unc + V_MC + V_emu + V_learn); V_std: the data part
    used to standardize (s_i = sigma_i^(0)); U, S: nu and eta columns over all link rows; tau: BB-lite effective
    counts per (block, bin); n_eff: effective MC counts per binomial block; constraints: N_d,c vectors over the
    Gaussian rows (link space)."""
    V_G: np.ndarray
    V_std: np.ndarray
    U: np.ndarray
    S: np.ndarray
    tau: dict = field(default_factory=dict)
    n_eff: dict = field(default_factory=dict)
    constraints: list = field(default_factory=list)
    W: np.ndarray | None = None
    ln_det: float = 0.0
    map_term: Any = None                  # map_term.MapTerm: U(theta) phi_map, profiled with theta (section 6.7)

    def finalize(self):
        """The projected inverse W on N_d,c^perp (section 2.1) and ln det of the projected V_G (for the section 7.3
        ln det diagnostic)."""
        W, ld = projected_inverse(self.V_G, self.constraints, self.V_std, with_logdet=True)
        self.W, self.ln_det = W, ld
        return self


def projected_inverse(V, constraints, V_std=None, with_logdet=False):
    """S^-1 U_perp (U_perp^T V~ U_perp)^-1 U_perp^T S^-1 with S = diag(sqrt(V_std,kk)) and U_perp an orthonormal basis
    of the complement of the standardized constraints S n (sections 2.1, 9.2). ln det is that of
    U_perp^T V~ U_perp plus 2 sum ln s (the ln det of the projected V_G in the original units)."""
    V = np.asarray(V, float)
    n = V.shape[0]
    if n == 0:
        return (np.zeros((0, 0)), 0.0) if with_logdet else np.zeros((0, 0))
    s = np.sqrt(np.diag(V if V_std is None else V_std))
    if np.any(s <= 0):
        raise LikelihoodError("likelihood.sigma0", "a Gaussian observable has sigma^(0) = 0 (section 5.2: express its "
                              "error as a constraint on eta)")
    Si = 1.0 / s
    Vt = V * np.outer(Si, Si)
    U = complement_basis([s * np.asarray(c, float) for c in constraints], n)
    M = U.T @ Vt @ U
    c, low = linalg.cho_factor(0.5 * (M + M.T))
    Minv = linalg.cho_solve((c, low), np.eye(M.shape[0]))
    SU = U * Si[:, None]
    W = SU @ Minv @ SU.T
    if not with_logdet:
        return W
    ld = 2.0 * float(np.sum(np.log(np.diag(c)))) + 2.0 * float(np.sum(np.log(s)))
    return W, ld


def complement_basis(vectors, n: int) -> np.ndarray:
    """An orthonormal basis of the orthogonal complement of span(vectors) in R^n (QR with a rank check: linearly
    dependent declared constraints are a contract error, section 15.3.4)."""
    if not vectors:
        return np.eye(n)
    N = np.stack([v / np.linalg.norm(v) for v in vectors], axis=1)
    sv = np.linalg.svd(N, compute_uv=False)
    if sv.min() < 1e-8 * sv.max():
        raise LikelihoodError("contract.nd_dependent", "the declared constraint vectors are linearly dependent or "
                              "nearly duplicate (standardized singular-value ratio < 1e-8, section 5.2)")
    q, _ = np.linalg.qr(N, mode="complete")
    return q[:, N.shape[1]:]


@dataclass
class Observations:
    """Observed calibration data: gaussian rows (link space; shapes already as log-ratios of n + 1/2), Poisson counts
    per block, binomial (k, N) per block."""
    y_gauss: np.ndarray
    counts: dict = field(default_factory=dict)
    binom: dict = field(default_factory=dict)
    phi0: np.ndarray | None = None        # constraint centres of phi_P (auxiliary measurements)
    phi_cov: np.ndarray | None = None
    aux_m: dict = field(default_factory=dict)   # BB-lite auxiliary counts per block (default tau)
    aux_k: dict = field(default_factory=dict)   # auxiliary binomial (k*, n*) per block (default (k_eff, n_eff))
    nu0: np.ndarray | None = None         # constraint centres of nu and eta (0 except in toys of section 6.6)
    eta0: np.ndarray | None = None


def gaussian_data(layout: Layout, observed: dict) -> np.ndarray:
    """Stack the observed Gaussian values in link space: a scalar g(y); a shape the log-ratios of n + 1/2 (or the
    given coordinates)."""
    out = []
    for b in layout.blocks:
        if b.kind == "gaussian-scalar":
            out.append(link(np.atleast_1d(float(observed[b.name])), b.link))
        elif b.kind == "gaussian-shape":
            v = observed[b.name]
            v = np.asarray(v, float)
            out.append(shape_summary(v, b.L) if v.size == b.K else v)
    return np.concatenate(out) if out else np.zeros(0)


# ------------------------------------------------------------------ the likelihood
class Likelihood:
    """-2 ln L(beta) for a layout, data and reference. `predictor(theta_phi: dict) -> dict` returns natural-space
    predictions per block name: a scalar for gaussian-scalar and binomial blocks, the model shape (K values,
    any normalization) for gaussian-shape and free-omega poisson blocks, expected counts for absolute poisson."""

    def __init__(self, layout: Layout, observed: Observations, ref: Reference):
        self.layout, self.observed, self.ref = layout, observed, ref
        if ref.W is None:
            ref.finalize()
        self.map_term = ref.map_term
        if (self.map_term.n_phi if self.map_term is not None else 0) != layout.n_phi_map:
            raise LikelihoodError("likelihood.map_term", "the layout's n_phi_map and the reference's map term differ")
        if self.map_term is not None and self.map_term.theta_names \
                and self.map_term.theta_names != list(layout.theta) + list(layout.phi_P):
            raise LikelihoodError("likelihood.map_term", "the map term's theta_names are the layout's theta and phi_P")
        self.layout_slices = layout.slices()
        self._g_rows = layout.gaussian_rows()

    # -- the link-space predictor h(theta, phi) from natural-space predictions
    def model_link(self, pred: dict) -> np.ndarray:
        h = np.zeros(self.layout.n_link)
        for b in self.layout.blocks:
            m = np.asarray(pred[b.name], float)
            if b.kind == "gaussian-scalar" or b.kind == "binomial":
                h[b.index] = link(np.atleast_1d(m), b.link)
            elif b.kind == "gaussian-shape" or (b.kind == "poisson" and b.free_omega):
                h[b.index] = b.L @ np.log(m)
            else:
                h[b.index] = np.log(m)
        return h

    def unpack(self, beta):
        return {k: np.asarray(beta[s]) for k, s in self.layout_slices.items()}

    def theta_phi(self, beta) -> dict:
        p = self.unpack(beta)
        return {**dict(zip(self.layout.theta, p["theta"])), **dict(zip(self.layout.phi_P, p["phi_P"]))}

    def eta_link(self, h, beta) -> np.ndarray:
        p = self.unpack(beta)
        z = h.copy()
        if self.layout.n_nu:
            z = z + self.ref.U @ p["nu"]
        if self.layout.n_eta:
            z = z + self.ref.S @ p["eta"]
        if self.map_term is not None:
            z = z + self.map_term.U(self.theta_phi(beta)) @ p["phi_map"]
        return z

    def deviance(self, beta, h, parts=False):
        """-2 ln L at beta with link-space model predictor h (= model_link(predictor(theta_phi(beta))))."""
        p = self.unpack(beta)
        z = self.eta_link(h, beta)
        D = {}
        r = self.observed.y_gauss - z[self._g_rows] if self._g_rows.size else np.zeros(0)
        D["gaussian"] = float(r @ self.ref.W @ r) if r.size else 0.0
        D["poisson"] = D["aux"] = D["binomial"] = 0.0
        gi = {key: i for i, key in enumerate(self.layout.gamma)}
        oi = {nm: i for i, nm in enumerate(self.layout.omega)}
        di = {nm: i for i, nm in enumerate(self.layout.delta)}
        for b in self.layout.blocks:
            if b.kind == "poisson":
                mu = self._poisson_mu(b, z, p, oi, gi)
                D["poisson"] += poisson_deviance(self.observed.counts[b.name], mu)
                if b.bb:
                    g = np.array([p["gamma"][gi[(b.name, k)]] for k in range(b.K)])
                    tau = np.asarray(self.ref.tau[b.name], float)
                    m = np.asarray(self.observed.aux_m.get(b.name, tau), float)
                    keep = tau > 0
                    D["aux"] += poisson_deviance(m[keep], tau[keep] * g[keep])
            elif b.kind == "binomial":
                dl = p["delta"][di[b.name]] if b.name in di else 0.0
                eps = special.expit(z[b.index[0]] + dl)
                k, N = self.observed.binom[b.name]
                D["binomial"] += binomial_deviance(k, N, eps)
                if b.name in di:
                    D["aux"] += self._aux_binomial(b, h, dl)[0]
        nu0 = self.observed.nu0 if self.observed.nu0 is not None else np.zeros(self.layout.n_nu)
        eta0 = self.observed.eta0 if self.observed.eta0 is not None else np.zeros(self.layout.n_eta)
        D["constraints"] = float(np.sum((p["nu"] - nu0) ** 2) + np.sum((p["eta"] - eta0) ** 2)
                                 + np.sum(p["phi_map"] ** 2))
        if self.layout.phi_P:
            dphi = p["phi_P"] - self.observed.phi0
            D["constraints"] += float(dphi @ linalg.solve(self.observed.phi_cov, dphi, assume_a="pos"))
        total = sum(D.values())
        return (total, D) if parts else total

    def _aux_binomial(self, b, h, dl):
        """The auxiliary binomial term of the MC efficiency nuisance delta (section 2.1): the auxiliary measurement
        (k_a, n_a) = (k_eff, n_eff) of theta_ref ((k*, n*) in a toy, section 6.6) centred at logit^-1(c + delta), c the
        logit of the theta_ref MC estimate k_eff / n_eff. delta is a logit offset of the MC efficiency reused at every
        theta (as BB-lite's gamma, and as section 6.6 reuses f), so the term depends on delta only."""
        n_eff, k_eff = self.ref.n_eff[b.name]
        ka, na = self.observed.aux_k.get(b.name, (k_eff, n_eff))
        c = float(special.logit(k_eff / n_eff))
        em = float(special.expit(c + dl))
        return binomial_deviance(ka, na, em), float(ka), float(na), em

    def _poisson_mu(self, b, z, p, oi, gi):
        if b.free_omega:
            pk = logratio_inverse(z[b.index], b.L)
            mu = p["omega"][oi[b.name]] * pk
        else:
            mu = np.exp(z[b.index])
        if b.bb:
            mu = mu * np.array([p["gamma"][gi[(b.name, k)]] for k in range(b.K)])
        return mu

    # -- gradient and expected information (Fisher scoring)
    def score_fisher(self, beta, h, H_theta):
        """Gradient of -2 ln L and the expected information 2 E[...]: H_theta is d h / d(theta, phi_P) (n_link x
        (d + q)) from central differences of the evaluator; every other derivative is exact. Returns (g, F) for
        D = -2 ln L, with F the expected Hessian of D (Gauss-Newton for the Gaussian block)."""
        lay, p = self.layout, self.unpack(beta)
        nb = lay.n_beta
        layout_slices = self.layout_slices
        z = self.eta_link(h, beta)
        # d z / d beta for the link rows
        Jz = np.zeros((lay.n_link, nb))
        tp = np.r_[layout_slices["theta"].start:layout_slices["phi_P"].stop]
        Jz[:, tp] = H_theta
        if lay.n_nu:
            Jz[:, layout_slices["nu"]] = self.ref.U
        if lay.n_eta:
            Jz[:, layout_slices["eta"]] = self.ref.S
        if self.map_term is not None:                  # U(theta) phi_map: its columns and its theta derivative
            th = self.theta_phi(beta)
            Jz[:, layout_slices["phi_map"]] = self.map_term.U(th)
            for i, du in zip(tp, self.map_term.derivatives(th)):
                Jz[:, i] += du @ p["phi_map"]
        g = np.zeros(nb)
        F = np.zeros((nb, nb))
        if self._g_rows.size:
            Jg = Jz[self._g_rows]
            r = self.observed.y_gauss - z[self._g_rows]
            WJ = self.ref.W @ Jg
            g += -2.0 * WJ.T @ r
            F += 2.0 * Jg.T @ WJ
        gi = {key: i for i, key in enumerate(lay.gamma)}
        oi = {nm: i for i, nm in enumerate(lay.omega)}
        di = {nm: i for i, nm in enumerate(lay.delta)}
        for b in lay.blocks:
            if b.kind == "poisson":
                n = np.asarray(self.observed.counts[b.name], float)
                mu = self._poisson_mu(b, z, p, oi, gi)
                # d mu / d beta
                dmu = np.zeros((b.K, nb))
                if b.free_omega:
                    pk = mu / (p["omega"][oi[b.name]] * (np.array([p["gamma"][gi[(b.name, k)]] for k in range(b.K)])
                                                       if b.bb else 1.0))
                    Lp = np.linalg.pinv(b.L)                       # dx/da
                    dlogp_da = (np.eye(b.K) - pk[None, :].repeat(b.K, 0)) @ Lp
                    dmu += (mu[:, None] * dlogp_da) @ Jz[b.index]
                    dmu[:, layout_slices["omega"].start + oi[b.name]] = mu / p["omega"][oi[b.name]]
                else:
                    dmu += mu[:, None] * Jz[b.index]
                if b.bb:
                    for k in range(b.K):
                        j = layout_slices["gamma"].start + gi[(b.name, k)]
                        dmu[k, j] = mu[k] / p["gamma"][gi[(b.name, k)]]
                g += 2.0 * dmu.T @ (1.0 - n / mu)
                F += 2.0 * dmu.T @ (dmu / mu[:, None])
                if b.bb:
                    tau = np.asarray(self.ref.tau[b.name], float)
                    m = np.asarray(self.observed.aux_m.get(b.name, tau), float)
                    for k in range(b.K):
                        if tau[k] <= 0:
                            continue
                        j = layout_slices["gamma"].start + gi[(b.name, k)]
                        gk = p["gamma"][gi[(b.name, k)]]
                        g[j] += 2.0 * (tau[k] - m[k] / gk)
                        F[j, j] += 2.0 * tau[k] / gk
            elif b.kind == "binomial":
                k, N = self.observed.binom[b.name]
                dl = p["delta"][di[b.name]] if b.name in di else 0.0
                eta = z[b.index[0]] + dl
                eps = special.expit(eta)
                row = Jz[b.index[0]].copy()
                if b.name in di:
                    row[layout_slices["delta"].start + di[b.name]] = 1.0
                g += -2.0 * (k - N * eps) * row
                F += 2.0 * N * eps * (1 - eps) * np.outer(row, row)
                if b.name in di:
                    _, ka, na, em = self._aux_binomial(b, h, dl)
                    j = layout_slices["delta"].start + di[b.name]
                    g[j] += -2.0 * (ka - na * em)
                    F[j, j] += 2.0 * na * em * (1 - em)
        nu0 = self.observed.nu0 if self.observed.nu0 is not None else np.zeros(lay.n_nu)
        eta0 = self.observed.eta0 if self.observed.eta0 is not None else np.zeros(lay.n_eta)
        if lay.n_nu:
            g[layout_slices["nu"]] += 2.0 * (p["nu"] - nu0)
            F[layout_slices["nu"], layout_slices["nu"]] += 2.0 * np.eye(lay.n_nu)
        if lay.n_eta:
            g[layout_slices["eta"]] += 2.0 * (p["eta"] - eta0)
            F[layout_slices["eta"], layout_slices["eta"]] += 2.0 * np.eye(lay.n_eta)
        if lay.n_phi_map:
            g[layout_slices["phi_map"]] += 2.0 * p["phi_map"]
            F[layout_slices["phi_map"], layout_slices["phi_map"]] += 2.0 * np.eye(lay.n_phi_map)
        if lay.phi_P:
            Ci = linalg.inv(self.observed.phi_cov)
            g[layout_slices["phi_P"]] += 2.0 * Ci @ (p["phi_P"] - self.observed.phi0)
            F[layout_slices["phi_P"], layout_slices["phi_P"]] += 2.0 * Ci
        return g, 0.5 * (F + F.T)

    def gaussian_full(self, beta, h) -> float:
        """The full Gaussian -2 ln L including ln det of the projected V_G (the section 7.3 diagnostic)."""
        return self.deviance(beta, h) + self.ref.ln_det

    def initial_beta(self, theta0: dict, phi0: dict | None = None) -> np.ndarray:
        lay = self.layout
        b = np.zeros(lay.n_beta)
        b[self.layout_slices["theta"]] = [float(theta0[t]) for t in lay.theta]
        if lay.phi_P:
            b[self.layout_slices["phi_P"]] = self.observed.phi0 if phi0 is None else [float(phi0[q]) for q in lay.phi_P]
        for i, nm in enumerate(lay.omega):
            b[self.layout_slices["omega"].start + i] = max(float(np.sum(self.observed.counts[nm])), 1.0)
        b[self.layout_slices["gamma"]] = 1.0
        return b

    def bounds(self):
        """Positivity of omega and gamma (free otherwise; theta bounds are the physical ones of fit.py)."""
        lo = np.full(self.layout.n_beta, -np.inf)
        lo[self.layout_slices["omega"]] = 1e-12
        lo[self.layout_slices["gamma"]] = 1e-12
        return lo


# ------------------------------------------------------------------ V_model (section 5.4)
def _rho(kind: str, r):
    r = np.asarray(r, float)
    if kind == "squared-exponential":
        return np.exp(-0.5 * r * r)
    if kind == "matern32":
        a = math.sqrt(3.0) * r
        return (1 + a) * np.exp(-a)
    if kind == "matern52":
        a = math.sqrt(5.0) * r
        return (1 + a + a * a / 3.0) * np.exp(-a)
    raise LikelihoodError("vmodel.kernel", f"correlation family {kind!r}: D39 (A8) allows squared-exponential and "
                          "Matern")


def kernel_component(z: np.ndarray, group: np.ndarray, f: dict, ell: dict, C: np.ndarray | None,
                     family: str = "squared-exponential", cross: str = "convolution") -> np.ndarray:
    """R_ij = f_ci f_cj C_cicj rho_cicj(z_i, z_j) (section 5.4) with one-dimensional control variable z and groups c.
    Within a group rho(|z_i - z_j| / ell_c). Across groups C defaults to 0; with C != 0 and different ell the
    cross kernel is the Paciorek-Schervish convolution (D39 (a), A8): for the squared-exponential
    sqrt(2 l_i l_j / (l_i^2 + l_j^2)) exp(-(z_i - z_j)^2 / (l_i^2 + l_j^2)); `cross="zero"` is the interim (c),
    C = 0 when ell differs. Matern families use the same prefactor with the scaled distance
    |z_i - z_j| / sqrt((l_i^2 + l_j^2) / 2) (the Paciorek-Schervish non-stationary Matern form). Positive
    definiteness is checked numerically by `check_psd`."""
    z = np.asarray(z, float)
    groups = list(dict.fromkeys(group.tolist()))
    gi = np.array([groups.index(c) for c in group])
    li = np.array([float(ell[c]) for c in group])
    fi = np.array([float(f[c]) for c in group])
    Cm = np.eye(len(groups)) if C is None else np.asarray(C, float)
    if Cm.shape != (len(groups), len(groups)):
        raise LikelihoodError("vmodel.kernel", "C must be a matrix over the observable groups")
    same_l = np.isclose(li[:, None], li[None, :])
    dz = np.abs(z[:, None] - z[None, :])
    lsq = 0.5 * (li[:, None] ** 2 + li[None, :] ** 2)
    if family == "squared-exponential":
        rho = np.sqrt(li[:, None] * li[None, :] / lsq) * np.exp(-0.5 * dz ** 2 / lsq)
    else:
        rho = np.sqrt(li[:, None] * li[None, :] / lsq) * _rho(family, dz / np.sqrt(lsq))
    if cross == "zero":
        rho = np.where(same_l | (gi[:, None] == gi[None, :]), rho, 0.0)
    elif cross != "convolution":
        raise LikelihoodError("vmodel.kernel", f"cross-kernel {cross!r}")
    R = np.outer(fi, fi) * Cm[np.ix_(gi, gi)] * rho
    return 0.5 * (R + R.T)


def ensemble_component(diffs: list[np.ndarray]) -> np.ndarray:
    """The model-ensemble component R = (1/A) sum_a d_a d_a^T (the second moment, not the sample covariance;
    one model: d d^T) of the link-space differences of the absorbed models from the nominal (section 5.4)."""
    if not diffs:
        raise LikelihoodError("vmodel.ensemble", "no absorbed models")
    D = np.stack([np.asarray(d, float) for d in diffs], axis=1)
    return D @ D.T / D.shape[1]


def check_psd(R: np.ndarray, tol: float = 1e-10) -> None:
    w = np.linalg.eigvalsh(0.5 * (R + R.T))
    if w.min() < -tol * max(1.0, abs(w.max())):
        raise LikelihoodError("vmodel.not_psd", f"V_model is not positive semidefinite (smallest eigenvalue "
                              f"{w.min():.3g}, section 5.4)")


def principal_components(R: np.ndarray, calib_rows: np.ndarray, V_G_inv: np.ndarray | None = None,
                         fisher_rows: dict | None = None, frac: float = 0.99, tr_bound: float = 0.05,
                         keep_all: bool = False) -> dict:
    """u_k = sqrt(lambda_k) e_k in decreasing lambda, the smallest K with (1) cumulative eigenvalues >= 99% of tr R
    and (2) tr(V_G^-1 V_perp) <= 0.05 on the calibration rows (Gaussian rows with V_G^-1; Poisson and binomial rows
    with their expected Fisher in link space, `fisher_rows`) (section 5.4, en/compute-19-3.md). `keep_all` keeps every
    component (always allowed)."""
    check_psd(R)
    lam, E = np.linalg.eigh(0.5 * (R + R.T))
    order = np.argsort(lam)[::-1]
    lam, E = np.clip(lam[order], 0.0, None), E[:, order]
    pos = lam > lam.max() * 1e-14 if lam.max() > 0 else np.zeros_like(lam, dtype=bool)
    lam, E = lam[pos], E[:, pos]
    if lam.size == 0:
        return {"U": np.zeros((R.shape[0], 0)), "K": 0, "trace_fraction": 1.0, "tr_VGinv_Vperp": 0.0}
    if keep_all:
        Kc = lam.size
    else:
        cum = np.cumsum(lam) / lam.sum()
        Kc = None
        for K in range(1, lam.size + 1):
            if cum[K - 1] < frac:
                continue
            Vp = (E[:, K:] * lam[K:]) @ E[:, K:].T
            if _tr_info(Vp, calib_rows, V_G_inv, fisher_rows) <= tr_bound:
                Kc = K
                break
        Kc = lam.size if Kc is None else Kc
    Vp = (E[:, Kc:] * lam[Kc:]) @ E[:, Kc:].T
    return {"U": E[:, :Kc] * np.sqrt(lam[:Kc]), "K": int(Kc), "trace_fraction": float(lam[:Kc].sum() / lam.sum()),
            "tr_VGinv_Vperp": _tr_info(Vp, calib_rows, V_G_inv, fisher_rows)}


def _tr_info(Vp, rows, V_G_inv, fisher_rows):
    t = 0.0
    if V_G_inv is not None and len(rows):
        t += float(np.trace(V_G_inv @ Vp[np.ix_(rows, rows)]))
    for r, I in (fisher_rows or {}).items():
        rr = np.atleast_1d(r)
        t += float(np.trace(np.atleast_2d(I) @ Vp[np.ix_(rr, rr)]))
    return t


# ------------------------------------------------------------------ the event-level parametric bootstrap (section 2.1)
def bootstrap_size(p: int) -> int:
    """B >= max(500, 50 p) (section 2.1)."""
    return max(500, 50 * int(p))


def bootstrap_covariance(sets: np.ndarray) -> np.ndarray:
    """The sample covariance of B sets of shared-event summary statistics (B x p), generated from the model at theta_ref
    (never resampled from the observed events)."""
    sets = np.asarray(sets, float)
    B, p = sets.shape
    if B < bootstrap_size(p):
        raise LikelihoodError("likelihood.bootstrap_size", f"B = {B} < max(500, 50p) = {bootstrap_size(p)}")
    return np.cov(sets, rowvar=False).reshape(p, p)


def bootstrap_report_factor(B: int, p: int) -> float:
    """(B - p - 2) / (B - 1): multiplies reported quadratic-form effect sizes when the inverted matrix is entirely the
    bootstrap covariance; never a decision input (section 2.1)."""
    return (B - p - 2.0) / (B - 1.0)


def chi2_quantile(level: float, k: int) -> float:
    return float(stats.chi2.ppf(level, k))
