"""Partial pooling (Part B section 3.7 line 788, section 11.3 line 2771, section 15.3.18 line 3465; phase 5, WP-Q).

Part B names the fourth conditioning structure but does not specify it (gap P1). The model is the author's reading of
approval A25 (6): per segment s and pooled parameter j, theta_s,j ~ N(theta_bar_j, tau_pool_j^2) in the parameter's
link space; tau_pool_j >= 0 is estimated by the restricted (REML) marginal likelihood; the pooled theta_s and the
estimate enter sigma_tot through the joint fit. The symbol is `tau_pool` here and in the JSON (Appendix A's tau is
the effective event count; D14 asks for a section-qualified name: ambiguity P3).

- Declaration (ambiguity P5): a theta whose `index.conditioning` is `partial-pooling` is pooled; the contract's
  optional `pooling` object lists the segments ({name, conditions}: a scope is a region in the condition space,
  line 792) and, per pooled parameter, the link (identity, log, logit; default identity) and `tau_bound`, the upper
  end of the tau_pool search range in link units (default: the link-space width of the sampling range). Every other
  theta and every profile phi is common to all segments. `contract_findings` is called by `contract.check`;
  contracts without either field are not touched (default-off).
- `Segmented`: the joint fit as a fit.py Problem (a wrapper, as fit.view is; nothing in likelihood.py or fit.py
  changes). theta_joint = (theta_bar in link space, the common theta, z_s,j) with theta_s,j = theta_bar_j +
  tau_pool_j z_s,j (non-centred: tau_pool = 0 is the exact common-value model) and the N(0, 1) term of each z as a
  Gaussian pseudo-row with value 0 and variance 1, so `fit.find_extremum` / `fit.iterate` run unchanged and sigma_tot
  of theta_s comes from the joint curvature (`PooledFit.segments`).
- `reml`: the restricted log-likelihood of tau_pool^2 for the model linearized at a point (y_w = X b + Z u + e, u ~
  N(0, I_S (x) diag(tau_pool^2)), e ~ N(0, V_G + U U^T + S S^T + J_phi Sigma_phi J_phi^T): nuisances and profile phi
  marginalized with their constraints); projected Fisher scoring, so tau_pool_hat = 0 is exact at the boundary.
  The confidence set of tau_pool_j is {t : q_j(t) <= chi2_1(0.90) = 2.706}, q_j the profile REML likelihood ratio;
  its upper end is the one-sided 95% upper limit and "covers 0" is q_j(0) <= 2.706 (asymptotic boundary coverage
  0.5 + 0.5 x 0.90 = 0.95).
- `fit_pooled`: linearize, REML, joint fit with tau_pool_hat plugged in, re-linearize at the joint fit point until
  tau_pool_hat moves by < 0.01 of max(tau_pool_hat, the segment standard error) (exact after one round for a linear
  model whose V does not depend on theta). The uncertainty of tau_pool_hat itself is not added to sigma_tot.
- `frequency_decision`: section 15.3.18 as A25 reads it: tau_pool_hat = 0 in at least half of the replicas under
  equal truth, and 0 inside the 95% set in at least 95%.

Grade and gates of a pooled result (approval A26 (1), WP-Q2):
- `grade` / `grade_report`: the Appendix C rules as for any result (`use.aggregate`, `use.judge`); `partial-pooling`
  is an information flag (no effect on grade or use).
- `holdout_evidence`: the holdout validates the pooled model jointly, one V test over the held-out units of all
  segments (`Segmented.val`, `h_val`, `val_columns`), the joint Sigma_beta in C_r.
- G1 on the joint fit (`fit_pooled`); `p2` and `g2` count only the real observation rows and the real parameters'
  bounds, never the pseudo-rows or the numerical z bounds; `p3` (Asimov at the prior centre, so tau_pool = 0) and
  `g6` on the joint problem; `g5` per pooled parameter on theta_bar (identify.py with `block` = the fixed effects,
  the z_s,j profiled); G8 with segment-level pseudo-data (`segment_truths`: a common truth or spread truths,
  `closure_point`, then `closure.g8`), judged on the fixed effects. Joint toys: `Segmented.simulate` draws each
  pseudo-row from N(z, 1), the random-effects bootstrap in the linear model.

Scope of this phase: Gaussian blocks only (no Poisson or binomial blocks, no N_d,c constraints, no efficiency-map
term), the same model and theta names in every segment; anything else is rejected with a `pooling.*` code.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import linalg, optimize, stats

from . import fit as F
from . import likelihood as L

POOL_LINKS = ("identity", "log", "logit")
TAU_POOL_C = float(stats.chi2.ppf(0.90, 1))      # 2.706: the one-sided 95% construction at the boundary
Z_BOUND = 10.0
ROUNDS = 10
TAU_TOL = 0.01


class PoolingError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ declaration (ambiguity P5)
@dataclass
class Spec:
    segments: list
    pooled: list
    links: dict
    tau_bound: dict
    conditions: dict = field(default_factory=dict)


def _pooled_names(contract: dict) -> list[tuple[int, dict]]:
    pars = contract.get("parameters") if isinstance(contract, dict) else None
    return [(i, p) for i, p in enumerate(pars if isinstance(pars, list) else [])
            if isinstance(p, dict) and isinstance(p.get("index"), dict)
            and p["index"].get("conditioning") == "partial-pooling"]


def uses_pooling(contract: dict) -> bool:
    return isinstance(contract, dict) and (contract.get("pooling") is not None or bool(_pooled_names(contract)))


def contract_findings(contract: dict) -> list[dict]:
    """The declaration rules: pooled parameters are theta; a pooled theta needs `pooling.segments` (>= 2, unique
    names); `pooling` needs a pooled theta; per-parameter entries name pooled thetas, with a known link."""
    out: list[dict] = []

    def add(code, path, msg):
        out.append({"code": code, "path": path, "message": msg})
    pooled = _pooled_names(contract)
    pool = contract.get("pooling")
    for i, p in pooled:
        if p.get("role") != "theta":
            add("pooling.role", f"$.parameters[{i}]", f"{p.get('name')!r}: only a theta is pooled (section 3.7)")
    names = {str(p.get("name")) for _, p in pooled if p.get("role") == "theta"}
    if names and pool is None:
        add("pooling.no_segments", "$.pooling", f"partial pooling of {sorted(names)} needs the segments declared in "
            "`pooling.segments` (a scope is a region in the condition space, section 3.7)")
        return out
    if pool is None:
        return out
    if not names:
        add("pooling.no_pooled_parameter", "$.pooling", "`pooling` is declared but no theta has index.conditioning "
            "partial-pooling")
    if not isinstance(pool, dict):
        add("pooling.segments", "$.pooling", "`pooling` is an object with `segments`")
        return out
    raw = pool.get("segments")
    segs: list = raw if isinstance(raw, list) else []
    seg_names = [s.get("name") for s in segs if isinstance(s, dict)]
    if len(seg_names) < 2 or len(seg_names) != len(segs):
        add("pooling.segments", "$.pooling.segments", "at least two segments are declared")
    elif not all(isinstance(n, str) and n for n in seg_names) or len(set(seg_names)) != len(seg_names):
        add("pooling.segments", "$.pooling.segments", "segment names are non-empty and unique")
    per = pool.get("parameters") or {}
    items: list = list(per.items()) if isinstance(per, dict) else [("$", None)]
    for k, v in items:
        entry: Any = v if v is not None else {}
        if k not in names:
            add("pooling.parameter_unknown", f"$.pooling.parameters.{k}", f"{k!r} is not a pooled theta")
        elif not isinstance(entry, dict) or entry.get("link", "identity") not in POOL_LINKS:
            add("pooling.link", f"$.pooling.parameters.{k}", f"link one of {POOL_LINKS}")
        elif "tau_bound" in entry and not (isinstance(entry["tau_bound"], (int, float))
                                           and not isinstance(entry["tau_bound"], bool)
                                           and 0 < entry["tau_bound"] < math.inf):
            add("pooling.tau_bound", f"$.pooling.parameters.{k}", "tau_bound is a positive finite number (link units)")
    return out


def declaration(contract: dict) -> Spec:
    """The pooling Spec of a contract; PoolingError (exit 2) on the first finding, or when nothing is pooled."""
    f = contract_findings(contract)
    if f:
        raise PoolingError(f[0]["code"], f[0]["message"])
    if contract.get("pooling") is None:
        raise PoolingError("pooling.no_segments", "the contract declares no partial pooling")
    pool = contract["pooling"]
    pooled = [p["name"] for _, p in _pooled_names(contract)]
    per = pool.get("parameters") or {}
    return Spec([s["name"] for s in pool["segments"]], pooled,
                {n: (per.get(n) or {}).get("link", "identity") for n in pooled},
                {n: (per.get(n) or {}).get("tau_bound") for n in pooled},
                {s["name"]: s.get("conditions") or {} for s in pool["segments"]})


# ------------------------------------------------------------------ the joint problem
def _block_diag(mats, shape=None):
    mats = [np.asarray(m, float) for m in mats]
    if shape is None:
        return linalg.block_diag(*mats) if mats else np.zeros((0, 0))
    out = np.zeros(shape)
    r = c = 0
    for m in mats:
        out[r:r + m.shape[0], c:c + m.shape[1]] = m
        r, c = r + m.shape[0], c + m.shape[1]
    return out


class Segmented:
    """The pooled joint fit of S segment problems (fit.py Problems with the same theta and phi_P names, Gaussian
    blocks only) as one fit.py Problem; `tau_pool` is set by `set_tau` (REML) before a fit."""

    def __init__(self, segments: list, names: list, pooled: list, links: dict | None = None,
                 tau_bound: dict | None = None):
        if len(segments) < 2 or len(segments) != len(names):
            raise PoolingError("pooling.segments", "at least two segments, one problem per segment name")
        lay0 = segments[0].layout
        self.seg, self.names = list(segments), list(names)
        self.theta_seg, self.phi = list(lay0.theta), list(lay0.phi_P)
        for s, p in zip(names, segments):
            lay = p.layout
            if lay.theta != self.theta_seg or lay.phi_P != self.phi:
                raise PoolingError("pooling.model", f"segment {s}: the theta and phi_P names differ")
            if lay.omega or lay.gamma or lay.delta or lay.n_phi_map or any(
                    not b.kind.startswith("gaussian") for b in lay.blocks):
                raise PoolingError("pooling.blocks", f"segment {s}: phase-5 pooling covers Gaussian blocks only")
            if p.observed is None:
                raise PoolingError("pooling.values", f"segment {s}: no observed values")
        unknown = [n for n in pooled if n not in self.theta_seg]
        if not pooled or unknown:
            raise PoolingError("pooling.parameter_unknown", f"pooled parameters {unknown or pooled} are not theta")
        self.pooled = list(pooled)
        self.links = {n: (links or {}).get(n, "identity") for n in self.pooled}
        if any(k not in POOL_LINKS for k in self.links.values()):
            raise PoolingError("pooling.link", f"link one of {POOL_LINKS}")
        self.pooled_idx = [self.theta_seg.index(n) for n in self.pooled]
        self.common_idx = [i for i, n in enumerate(self.theta_seg) if n not in self.pooled]
        self.S, self.P, self.Q, self.d0 = len(segments), len(self.pooled_idx), len(self.common_idx), len(self.theta_seg)
        self.n_link = [p.layout.n_link for p in segments]
        self.n_nu = [p.layout.n_nu for p in segments]
        self.n_eta = [p.layout.n_eta for p in segments]
        theta = self.pooled + [self.theta_seg[i] for i in self.common_idx] + \
            [f"{n}@{s}:z" for s in self.names for n in self.pooled]
        obs = [{"name": f"{s}/{k}", "block": "gaussian", "link": "identity"}
               for s, n in zip(self.names, self.n_link) for k in range(n)]
        obs += [{"name": f"pool:{s}:{n}", "block": "gaussian", "link": "identity"} for s in self.names
                for n in self.pooled]
        self.layout = L.build_layout(obs, theta, self.phi, sum(self.n_nu), sum(self.n_eta))
        o0 = segments[0].observed
        self.observed = L.Observations(
            y_gauss=np.concatenate([np.asarray(p.observed.y_gauss, float) for p in segments]
                                   + [np.zeros(self.S * self.P)]),
            phi0=o0.phi0, phi_cov=o0.phi_cov,
            nu0=self._stack("nu0", self.n_nu), eta0=self._stack("eta0", self.n_eta))
        self.sigma_noise = max(float(getattr(p, "sigma_noise", 0.0)) for p in segments)
        self.edm_tol = min(float(getattr(p, "edm_tol", 0.1)) for p in segments)
        self.V_depends_on_theta = any(getattr(p, "V_depends_on_theta", True) for p in segments)
        b0, pb0 = segments[0].bounds(), segments[0].prior_box()
        with np.errstate(divide="ignore", invalid="ignore"):
            self._lb = [tuple(np.nan_to_num(L.link(np.array(b0[i], float), self.links[n]), nan=-np.inf,
                                            posinf=np.inf, neginf=-np.inf)) for i, n in zip(self.pooled_idx, self.pooled)]
            self._lp = [tuple(L.link(np.array(pb0[i], float), self.links[n])) for i, n in zip(self.pooled_idx, self.pooled)]
        self._qb = [tuple(b0[i]) for i in self.common_idx]
        self._qp = [tuple(pb0[i]) for i in self.common_idx]
        tb = tau_bound or {}
        self.tau_bound = np.array([float(tb.get(n) or (hi - lo)) for n, (lo, hi) in zip(self.pooled, self._lp)])
        if not np.all(np.isfinite(self.tau_bound) & (self.tau_bound > 0)):
            raise PoolingError("pooling.tau_bound", "the link-space sampling range of a pooled parameter is not finite: "
                               "declare pooling.parameters.<name>.tau_bound")
        self.tau = np.zeros(self.P)
        st = np.asarray(F.fd_steps(segments[0]), float)
        mid = np.array([0.5 * (a + b) for a, b in pb0], float)
        self._seg_steps = st
        self._bar_steps = np.array([st[i] * abs(float(L.dlink(np.array([mid[i]]), self.links[n])[0]))
                                    for i, n in zip(self.pooled_idx, self.pooled)])

    def _stack(self, key, sizes):
        if not sum(sizes):
            return None
        return np.concatenate([np.asarray(getattr(p.observed, key), float) if getattr(p.observed, key) is not None
                               else np.zeros(n) for p, n in zip(self.seg, sizes)])

    def set_tau(self, tau) -> None:
        self.tau = np.asarray(tau, float).copy()

    @property
    def d(self):
        return self.P + self.Q + self.S * self.P

    # -- the parameter map
    def segment_theta(self, tp) -> list[np.ndarray]:
        """The physical theta of each segment (and the common phi_P appended) at a joint theta-phi point."""
        tp = np.asarray(tp, float)
        mean_link, q = tp[:self.P], tp[self.P:self.P + self.Q]
        z = tp[self.P + self.Q:self.d].reshape(self.S, self.P)
        phi = tp[self.d:]
        out = []
        for s in range(self.S):
            th = np.zeros(self.d0)
            for k, (i, n) in enumerate(zip(self.pooled_idx, self.pooled)):
                th[i] = L.inv_link(np.array([mean_link[k] + self.tau[k] * z[s, k]]), self.links[n])[0]
            th[self.common_idx] = q
            out.append(np.r_[th, phi])
        return out

    def joint_point(self, bar_link, common, z=None, phi=None) -> np.ndarray:
        z = np.zeros(self.S * self.P) if z is None else np.ravel(z)
        phi = np.zeros(0) if phi is None else np.asarray(phi, float)
        return np.r_[np.asarray(bar_link, float), np.asarray(common, float), z, phi]

    # -- the fit.py Problem interface
    def h(self, tp):
        tp = np.asarray(tp, float)
        return np.concatenate([p.h(t) for p, t in zip(self.seg, self.segment_theta(tp))]
                              + [tp[self.P + self.Q:self.d]])

    def _seg_beta(self, s, tp_s, beta):
        lay = self.seg[s].layout
        b = np.zeros(lay.n_beta)
        b[:tp_s.size] = tp_s
        if beta is not None:
            sl, js = lay.slices(), self.layout.slices()
            a = js["nu"].start + sum(self.n_nu[:s])
            b[sl["nu"]] = beta[a:a + self.n_nu[s]]
            a = js["eta"].start + sum(self.n_eta[:s])
            b[sl["eta"]] = beta[a:a + self.n_eta[s]]
        return b

    def _split(self, ref: L.Reference, s: int) -> L.Reference:
        r0 = sum(self.n_link[:s])
        rows = slice(r0, r0 + self.n_link[s])
        nu = slice(sum(self.n_nu[:s]), sum(self.n_nu[:s + 1]))
        eta = slice(sum(self.n_eta[:s]), sum(self.n_eta[:s + 1]))
        return L.Reference(V_G=ref.V_G[rows, rows], V_std=ref.V_std[rows, rows], U=ref.U[rows, nu],
                           S=ref.S[rows, eta])

    def reference(self, tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
        refs = []
        for s, (p, t) in enumerate(zip(self.seg, self.segment_theta(tp))):
            fr = None if frozen is None else self._split(frozen, s)
            refs.append(p.reference(t, self._seg_beta(s, t, beta), fr, bootstrap_frozen=bootstrap_frozen,
                                    bootstrap_seed=bootstrap_seed))
        if any(r.constraints for r in refs):
            raise PoolingError("pooling.constraints", "phase-5 pooling does not cover N_d,c constraints")
        k = self.S * self.P
        n = sum(self.n_link) + k
        return L.Reference(V_G=_block_diag([r.V_G for r in refs] + [np.eye(k)]),
                           V_std=_block_diag([r.V_std for r in refs] + [np.eye(k)]),
                           U=_block_diag([r.U for r in refs], (n, sum(self.n_nu))),
                           S=_block_diag([r.S for r in refs], (n, sum(self.n_eta)))).finalize()

    def bounds(self):
        return self._lb + self._qb + [(-Z_BOUND, Z_BOUND)] * (self.S * self.P)

    def prior_box(self):
        return self._lp + self._qp + [(-3.0, 3.0)] * (self.S * self.P)

    def sigma_prior(self):
        return [(b - a) / math.sqrt(12.0) for a, b in self.prior_box()]

    @property
    def fd_steps(self):
        zst = [self._bar_steps[k] / self.tau[k] if self.tau[k] > 0 else 1e-3
               for _ in range(self.S) for k in range(self.P)]
        zst = [min(max(v, 1e-6), 1e-2) for v in zst]
        return np.r_[self._bar_steps, self._seg_steps[self.common_idx], zst, self._seg_steps[self.d0:]]

    def initial_beta(self) -> np.ndarray:
        b = np.zeros(self.layout.n_beta)
        b[:self.P + self.Q] = [0.5 * (a + c) for a, c in self._lp + self._qp]
        if self.phi:
            b[self.layout.slices()["phi_P"]] = self.observed.phi0
        return b

    # -- the gates on pooled fits (A26): the real rows, the fixed effects, toys and the held-out units
    @property
    def n_real(self) -> int:
        """The real observation rows (every segment's); the S x P N(0, 1) pseudo-rows follow them."""
        return sum(self.n_link)

    def fixed_block(self) -> list[int]:
        """The theta indices of the fixed effects (theta_bar in link space, the common theta): the block P3, G5 and
        G8 judge. The z_s,j are random effects, profiled with their N(0, 1) term like constrained nuisances."""
        return list(range(self.P + self.Q))

    def z_block(self) -> list[int]:
        return list(range(self.P + self.Q, self.d))

    def segment_beta(self, s: int, beta) -> np.ndarray:
        """Segment s's beta (its physical theta, the common phi_P, its nu and eta) at a joint beta."""
        tp = np.asarray(beta, float)[:self.d + len(self.phi)]
        return self._seg_beta(s, self.segment_theta(tp)[s], np.asarray(beta, float))

    def simulate(self, beta_truth, rng, phis=None, nominal: bool = True) -> L.Observations:
        """Toy data of the joint problem (G2, G6): each segment's data at its theta_s and nuisances, and each pseudo-row
        drawn from N(z_s,j, 1). In the linear model this is the parametric bootstrap of the random-effects model
        (z* ~ N(0, 1), pseudo-rows 0): -2 ln L at the minimum depends on the noise only, and the pseudo-row noise has the
        same N(0, 1) law as -z*."""
        b = np.asarray(beta_truth, float)
        obs = [p.simulate(self.segment_beta(s, b), rng) if nominal else
               p.simulate(self.segment_beta(s, b), rng, nominal=False) for s, p in enumerate(self.seg)]
        z = b[self.P + self.Q:self.d]
        phi0 = self.observed.phi0
        if self.phi:
            phi0 = rng.multivariate_normal(b[self.layout.slices()["phi_P"]], np.asarray(self.observed.phi_cov, float))
        cat = (lambda key, sizes: np.concatenate([np.asarray(getattr(o, key), float) for o in obs])
               if sum(sizes) else None)
        return L.Observations(y_gauss=np.concatenate([np.asarray(o.y_gauss, float) for o in obs]
                                                     + [z + rng.normal(size=z.size)]),
                              phi0=phi0, phi_cov=self.observed.phi_cov, nu0=cat("nu0", self.n_nu),
                              eta0=cat("eta0", self.n_eta))

    def replica_pert(self, rng, tp=None) -> np.ndarray:
        """Each segment's replica-difference MC perturbation; none on the pseudo-rows (they carry no MC)."""
        ths = self.segment_theta(tp) if tp is not None else [None] * self.S
        return np.concatenate([np.asarray(p.replica_pert(rng, t), float)[:n]
                               for p, t, n in zip(self.seg, ths, self.n_link)] + [np.zeros(self.S * self.P)])

    @property
    def has_bootstrap(self) -> bool:
        return any(getattr(p, "has_bootstrap", False) for p in self.seg)

    def _vals(self) -> list:
        vs = [p.cfg.val if hasattr(p, "cfg") else getattr(p, "val", None) for p in self.seg]
        if any(v is None for v in vs):
            raise PoolingError("pooling.validation", "every segment needs its held-out units for the joint V test")
        return vs

    @property
    def val(self) -> dict:
        """The held-out units of all segments as one validation set (A26: one V test over them): V_data and V_MC
        block-diagonal, each segment's deterministic constraints padded to the joint coordinates."""
        vs = self._vals()
        nv = [len(v["m0"]) for v in vs]
        cons = []
        for s, v in enumerate(vs):
            for c in v.get("constraints") or []:
                full = np.zeros(sum(nv))
                full[sum(nv[:s]):sum(nv[:s + 1])] = np.asarray(c, float)
                cons.append(full)
        return {"m0": np.concatenate([np.asarray(v["m0"], float) for v in vs]),
                "V_data": _block_diag([v["V_data"] for v in vs]), "V_MC": _block_diag([v["V_MC"] for v in vs]),
                "constraints": cons, "units": dict(zip(self.names, nv))}

    def h_val(self, tp, phis=None):
        return np.concatenate([p.h_val(t) for p, t in zip(self.seg, self.segment_theta(tp))])

    def val_columns(self):
        nv = [len(v["m0"]) for v in self._vals()]
        cols = [p.val_columns() for p in self.seg]
        return (_block_diag([u for u, _ in cols], (sum(nv), sum(self.n_nu))),
                _block_diag([e for _, e in cols], (sum(nv), sum(self.n_eta))))

    def set_val_point(self, tp) -> None:
        for p, t in zip(self.seg, self.segment_theta(tp)):
            if hasattr(p, "set_val_point"):
                p.set_val_point(t)

    # -- the REML linearization
    def linearize(self, tp) -> Lin:
        """The linear model at a joint point: fixed effects (theta_bar, common theta), random effects u_s,j =
        theta_s,j - theta_bar_j (link space), nuisances and profile phi marginalized with their constraints."""
        tp = np.asarray(tp, float)
        nphi = len(self.phi)
        rows, X, Z, Jphi, Vb, y_work = [], [], [], [], [], []
        N = sum(self.n_link)
        r0 = 0
        for s, (p, t) in enumerate(zip(self.seg, self.segment_theta(tp))):
            n = self.n_link[s]
            hs = p.h(t)
            J = F.jacobian(p, t, F.fd_steps(p))
            ref = p.reference(t, self._seg_beta(s, t, None))
            if ref.constraints:
                raise PoolingError("pooling.constraints", "phase-5 pooling does not cover N_d,c constraints")
            dl = np.array([float(L.dlink(np.array([t[i]]), self.links[nm])[0]) for i, nm in zip(self.pooled_idx, self.pooled)])
            Jl = J[:, self.pooled_idx] / dl
            ell = np.array([float(L.link(np.array([t[i]]), self.links[nm])[0]) for i, nm in zip(self.pooled_idx, self.pooled)])
            x = np.zeros((n, self.P + self.Q))
            x[:, :self.P] = Jl
            x[:, self.P:] = J[:, self.common_idx]
            z = np.zeros((n, self.S * self.P))
            z[:, s * self.P:(s + 1) * self.P] = Jl
            V = ref.V_G.copy()
            off = np.zeros(n)
            o = p.observed
            if p.layout.n_nu:
                V += ref.U[:n] @ ref.U[:n].T
                off += ref.U[:n] @ (o.nu0 if o.nu0 is not None else np.zeros(p.layout.n_nu))
            if p.layout.n_eta:
                V += ref.S[:n] @ ref.S[:n].T
                off += ref.S[:n] @ (o.eta0 if o.eta0 is not None else np.zeros(p.layout.n_eta))
            Jp = J[:, self.d0:]
            if nphi:
                off += Jp @ (np.asarray(self.observed.phi0, float) - t[self.d0:])
            y_work.append(np.asarray(o.y_gauss, float) - hs - off + Jl @ ell + J[:, self.common_idx] @ t[self.common_idx])
            X.append(x)
            Z.append(z)
            Jphi.append(Jp)
            Vb.append(V)
            rows.append(slice(r0, r0 + n))
            r0 += n
        V0 = _block_diag(Vb)
        if nphi:
            Jp = np.vstack(Jphi)
            V0 = V0 + Jp @ np.asarray(self.observed.phi_cov, float) @ Jp.T
        Zm = np.vstack(Z)
        cols = [Zm[:, [s * self.P + k for s in range(self.S)]] for k in range(self.P)]
        return Lin(np.concatenate(y_work), np.vstack(X), Zm, cols, 0.5 * (V0 + V0.T), N, self.tau_bound.copy())


@dataclass
class Lin:
    y_work: np.ndarray
    X: np.ndarray
    Z: np.ndarray
    cols: list                 # per pooled parameter: the N x S random-effect columns
    V0: np.ndarray
    N: int
    tau_bound: np.ndarray

    def segment_sigma(self) -> np.ndarray:
        """A per-parameter scale: the median over segments of the GLS standard error of u_s,j alone."""
        Vi = linalg.inv(self.V0)
        return np.array([math.sqrt(float(np.median([1.0 / max(float(c[:, s] @ Vi @ c[:, s]), 1e-300)
                                                    for s in range(c.shape[1])]))) for c in self.cols])


# ------------------------------------------------------------------ REML (A25 (6))
def _reml_parts(lin: Lin, v: np.ndarray):
    V = lin.V0 + sum(vk * (c @ c.T) for vk, c in zip(v, lin.cols))
    try:
        cf = linalg.cho_factor(V)
    except linalg.LinAlgError:
        return -math.inf, None
    ViX = linalg.cho_solve(cf, lin.X)
    A = lin.X.T @ ViX
    try:
        ca = linalg.cho_factor(A)
    except linalg.LinAlgError:
        raise PoolingError("pooling.not_identified", "theta_bar and the common theta are not identified by the "
                           "segments together") from None
    Viy = linalg.cho_solve(cf, lin.y_work)
    Py = Viy - ViX @ linalg.cho_solve(ca, ViX.T @ lin.y_work)
    ld = 2.0 * float(np.sum(np.log(np.diag(cf[0])))) + 2.0 * float(np.sum(np.log(np.diag(ca[0]))))
    ll = -0.5 * (ld + float(lin.y_work @ Py))
    PC = []
    for c in lin.cols:
        ViC = linalg.cho_solve(cf, c)
        PC.append(ViC - ViX @ linalg.cho_solve(ca, ViX.T @ c))
    score = np.array([-0.5 * float(np.sum(pc * c)) + 0.5 * float(np.sum((c.T @ Py) ** 2))
                      for pc, c in zip(PC, lin.cols)])
    info = np.array([[0.5 * float(np.sum((ci.T @ pk) ** 2)) for pk in PC] for ci in lin.cols])
    return ll, (score, info)


def reml_loglik(lin: Lin, tau) -> float:
    return _reml_parts(lin, np.asarray(tau, float) ** 2)[0]


def _maximize(lin: Lin, v0: np.ndarray, fixed: dict | None = None, iters: int = 200) -> tuple[np.ndarray, float]:
    """Projected Fisher scoring on v = tau_pool^2 in [0, tau_bound^2] with step halving; `fixed` {j: v_j}."""
    fixed = fixed or {}
    hi = lin.tau_bound ** 2
    v = np.clip(np.asarray(v0, float).copy(), 0.0, hi)
    for j, x in fixed.items():
        v[j] = x
    ll, parts = _reml_parts(lin, v)
    for _ in range(iters):
        if parts is None:
            break
        g, info = parts
        free = np.array([j not in fixed and not (v[j] <= 0.0 and g[j] <= 0.0) and not (v[j] >= hi[j] and g[j] >= 0.0)
                         for j in range(v.size)])
        if not free.any():
            break
        fi = np.flatnonzero(free)
        try:
            step = np.zeros(v.size)
            step[fi] = linalg.solve(info[np.ix_(fi, fi)] + 1e-12 * np.eye(fi.size), g[fi], assume_a="pos")
        except (linalg.LinAlgError, ValueError):
            step = np.zeros(v.size)
            step[fi] = g[fi] / np.maximum(np.diag(info)[fi], 1e-300)
        t = 1.0
        moved = False
        while t > 1e-8:
            nv = np.clip(v + t * step, 0.0, hi)
            nll, nparts = _reml_parts(lin, nv)
            if nll >= ll - 1e-12 * max(1.0, abs(ll)):
                moved = np.max(np.abs(nv - v)) > 0
                v, ll, parts = nv, nll, nparts
                break
            t *= 0.5
        if not moved or np.max(np.abs(t * step)) <= 1e-10 * max(1.0, float(np.max(v))):
            break
    return v, ll


@dataclass
class TauEstimate:
    tau_pool_hat: np.ndarray
    loglik: float
    lower: np.ndarray
    upper: np.ndarray
    covers0: np.ndarray
    q0: np.ndarray
    at_bound: list
    segment_sigma: np.ndarray

    def record(self, names):
        return {n: {"tau_pool_hat": float(self.tau_pool_hat[k]), "lower": float(self.lower[k]),
                    "upper_95": float(self.upper[k]), "covers_0": bool(self.covers0[k]), "q_0": float(self.q0[k]),
                    "upper_at_bound": k in self.at_bound, "segment_sigma": float(self.segment_sigma[k])}
                for k, n in enumerate(names)}


def reml(lin: Lin, intervals: bool = True) -> TauEstimate:
    """tau_pool_hat by the REML marginal likelihood (two starts: 0 and the segment-scale variance; the higher wins)
    and, per parameter, the profile likelihood-ratio set {t : q(t) <= 2.706}."""
    se = lin.segment_sigma()
    P = len(lin.cols)
    cands = [_maximize(lin, np.zeros(P)), _maximize(lin, se ** 2)]
    v, ll = max(cands, key=lambda c: c[1])
    v[v < 1e-14 * np.maximum(se ** 2, 1e-300)] = 0.0
    if v.any():
        ll = _reml_parts(lin, v)[0]
    tau = np.sqrt(v)
    lower, upper, cov, q0, atb = np.zeros(P), np.zeros(P), np.ones(P, bool), np.zeros(P), []
    if intervals:
        for j in range(P):
            def q(t, j=j):
                if P == 1:
                    return 2.0 * (ll - _reml_parts(lin, np.array([t * t]))[0])
                return 2.0 * (ll - _maximize(lin, v, {j: t * t})[1])
            q0[j] = max(q(0.0), 0.0)
            cov[j] = q0[j] <= TAU_POOL_C
            b = float(lin.tau_bound[j])
            if q(b) <= TAU_POOL_C:
                upper[j] = b
                atb.append(j)
            else:
                upper[j] = optimize.brentq(lambda t: q(t) - TAU_POOL_C, tau[j], b, xtol=1e-6 * max(se[j], 1e-12))
            lower[j] = 0.0 if cov[j] else optimize.brentq(lambda t: q(t) - TAU_POOL_C, 0.0, tau[j],
                                                          xtol=1e-6 * max(se[j], 1e-12))
    return TauEstimate(tau, ll, lower, upper, cov, q0, atb, se)


# ------------------------------------------------------------------ the joint fit
@dataclass
class PooledFit:
    tau: TauEstimate
    fit: Any
    rounds: int
    converged: bool
    reason: str
    segments: dict
    theta_bar: dict
    common: dict
    flags: list

    def record(self, names):
        return {"tau_pool": self.tau.record(names), "rounds": self.rounds, "converged": self.converged,
                "reason": self.reason, "theta_bar": self.theta_bar, "common": self.common,
                "segments": self.segments, "fit": self.fit.record() if self.fit is not None else None,
                "flags": list(self.flags)}


def _summaries(joint: Segmented, fit) -> tuple[dict, dict, dict]:
    C = fit.cov_beta
    P, Q = joint.P, joint.Q
    mean_link = {n: {"link": joint.links[n], "value_link": float(fit.beta[k]), "sigma_tot_link": float(fit.sigma_tot[k])}
           for k, n in enumerate(joint.pooled)}
    common = {joint.theta_seg[i]: {"value": float(fit.beta[P + m]), "sigma_tot": float(fit.sigma_tot[P + m])}
              for m, i in enumerate(joint.common_idx)}
    seg: dict[str, dict] = {}
    for s, nm in enumerate(joint.names):
        seg[nm] = {}
        for k, n in enumerate(joint.pooled):
            a, b, t = k, P + Q + s * P + k, joint.tau[k]
            val = float(fit.beta[a] + t * fit.beta[b])
            var = float(C[a, a] + t * t * C[b, b] + 2 * t * C[a, b])
            seg[nm][n] = {"value_link": val, "value": float(L.inv_link(np.array([val]), joint.links[n])[0]),
                          "sigma_tot_link": math.sqrt(max(var, 0.0))}
    return mean_link, common, seg


def fit_pooled(joint: Segmented, seed, rounds: int = ROUNDS, multistart: bool = True) -> PooledFit:
    """Linearize, REML, the joint fit at tau_pool_hat (section 7.4 multi-start through fit.find_extremum unless
    `multistart` is False), re-linearize at the joint fit point until tau_pool_hat is stable."""
    point = joint.initial_beta()
    nt = joint.d + len(joint.phi)
    est: Any = None
    fit: Any = None
    prev: Any = None
    lin: Any = None
    for r in range(1, rounds + 1):
        lin = joint.linearize(point[:nt])
        est = reml(lin, intervals=False)
        if prev is not None and fit is not None and np.all(
                np.abs(est.tau_pool_hat - prev.tau_pool_hat) <= TAU_TOL * np.maximum(prev.tau_pool_hat, est.segment_sigma)):
            break
        prev = est
        joint.set_tau(est.tau_pool_hat)
        if multistart:
            fit = F.find_extremum(joint, (F._seed_int(seed), r), point)
        else:
            fit = F.iterate(joint, point)
        if not fit.converged:
            return PooledFit(reml(lin), fit, r, False, f"joint fit: {fit.reason}", {}, {}, {}, ["partial-pooling"])
        point = fit.beta.copy()
    else:
        return PooledFit(reml(lin), fit, rounds, False, f"tau_pool_hat not stable within {rounds} rounds", {}, {}, {},
                         ["partial-pooling"])
    joint.set_tau(prev.tau_pool_hat)
    last = reml(lin)                                  # at the joint fit point (the last linearization)
    last.tau_pool_hat = prev.tau_pool_hat
    mean_link, common, seg = _summaries(joint, fit)
    flags = ["partial-pooling"] + (["tau-pool-upper-at-bound"] if last.at_bound else [])
    return PooledFit(last, fit, r, True, "", seg, mean_link, common, flags)


# ------------------------------------------------------------------ section 15.3.18 as A25 reads it
def frequency_decision(tau_hats, covers0, zero_fraction_min: float = 0.5, cover_min: float = 0.95) -> dict:
    """Equal truth in all segments: tau_pool_hat = 0 (exactly) in >= half of the replicas, and the 95% set covers
    0 in >= 95% (A25 (6)); per pooled parameter when the arrays are (replicas, P)."""
    t = np.atleast_2d(np.asarray(tau_hats, float).T).T
    c = np.atleast_2d(np.asarray(covers0, bool).T).T
    zf = np.mean(t == 0.0, axis=0)
    cf = np.mean(c, axis=0)
    ok = bool(np.all(zf >= zero_fraction_min) and np.all(cf >= cover_min))
    return {"test": "section 15.3.18 partial pooling (A25 (6))", "replicas": int(t.shape[0]),
            "zero_fraction": zf.tolist(), "cover_fraction": cf.tolist(), "zero_fraction_min": zero_fraction_min,
            "cover_min": cover_min, "status": "passed" if ok else "failed"}


def planned_power(S: int, lam: float, c: float = TAU_POOL_C) -> float:
    """The planned power of excluding tau_pool = 0 for S segments of equal standard error sigma and fixed truths
    with sum (theta_s - mean)^2 / sigma^2 = lam: the REML set excludes 0 iff (S - 1)(x - 1 - ln x) > c with
    x = s^2 / sigma^2 > 1, and (S - 1) x is noncentral chi^2_(S-1)(lam)."""
    k = S - 1
    xs = optimize.brentq(lambda x: k * (x - 1.0 - math.log(x)) - c, 1.0 + 1e-12, 1e6)
    return float(stats.ncx2.sf(k * xs, k, lam)) if lam > 0 else float(stats.chi2.sf(k * xs, k))


# ------------------------------------------------------------------ the gates on pooled fits (A26)
def p2(contract: dict) -> dict:
    """P2 of a pooled contract (A26: only real observation rows count, never the N(0, 1) pseudo-rows): every segment
    brings its own calibration data, so n_c and dim N_d,c are S times one segment's; d_free is the fixed effects
    (theta_bar for a pooled theta, the common theta, an unconstrained profile phi): each z_s,j comes with its
    pseudo-row (a constraint term and a parameter) and, as a constrained nuisance does, leaves ndf unchanged."""
    from . import design as D
    spec = declaration(contract)
    one = D.p2(contract)
    S = len(spec.segments)
    n_c, dim, d_free = S * one["n_c"], S * one["dim_N_dc"], one["d_free"]
    ndf = n_c - dim - d_free
    need = max(3, d_free)
    ok = ndf >= need
    return {"gate": "P2", "status": "passed" if ok else "failed", "n_c": n_c, "dim_N_dc": dim, "d_free": d_free,
            "ndf": ndf, "required": need, "segments": S, "pseudo_rows_excluded": S * len(spec.pooled),
            "findings": [] if ok else [{"code": "p2.insufficient_ndf", "message": f"ndf = {ndf} < max(3, d_free) = "
                                        f"{need} over the real rows of {S} segments: G6 cannot test; add calibration "
                                        "observables (remedy: contract)"}]}


def _block_names(joint: Segmented) -> list:
    return [joint.layout.theta[i] for i in joint.fixed_block()]


def p3(joint: Segmented, ref: L.Reference | None = None) -> dict:
    """P3 on the joint problem (A26): at the prior centre with Asimov data, which are equal-truth data (REML gives
    tau_pool_hat = 0 on them), so tau_pool = 0; lambda_min and sigma_post / sigma_prior over the fixed effects
    (`fixed_block`), the z_s,j profiled with their N(0, 1) terms; the information sums the segments."""
    from . import identify as I
    saved = joint.tau.copy()
    joint.set_tau(np.zeros(joint.P))
    try:
        out = I.p3(joint, joint.initial_beta(), ref, block=joint.fixed_block())
    finally:
        joint.set_tau(saved)
    return {**out, "pooled": {"tau_pool": 0.0, "judged": _block_names(joint), "segments": joint.S}}


def g5(joint: Segmented, fit, seed=None, profile: bool = True) -> dict:
    """G5 on a pooled fit (A26): per pooled parameter on theta_bar (and on each common theta) at the joint fit point
    with tau_pool_hat; the profile scans move theta_bar with the z_s,j and the rest minimized."""
    from . import identify as I
    out = I.g5(joint, fit, seed, profile, block=joint.fixed_block())
    return {**out, "pooled": {"tau_pool": joint.tau.tolist(), "judged": _block_names(joint)}}


def g2(joint: Segmented, fit, n_toys: int, seed, alpha: float = 0.01) -> dict:
    """G2 on a pooled fit (A26): the physical bounds of the real parameters only; a z_s,j at its numerical bound
    (+-Z_BOUND) is not a constraint of the model and never enters the active set or the chi-bar^2 components. The
    weight toys are joint toys (`Segmented.simulate`) at the restricted fit."""
    z = set(joint.z_block())
    real = [i for i in fit.active if i not in z]
    f = dataclasses.replace(fit, active=real)
    out = F.g2(joint, f, F.null_toys(joint, f, n_toys, seed), alpha=alpha)
    return {**out, "z_at_bound_excluded": [joint.layout.theta[i] for i in fit.active if i in z]}


def g6(joint: Segmented, fit, n_toys: int, seed, alpha: float = 0.01) -> dict:
    """G6 on the joint problem (A26): T_obs = -2 ln L of the joint fit (real rows and pseudo-rows), locally linear joint
    toys at the fit point (pseudo-rows drawn around z-hat: the random-effects bootstrap, `Segmented.simulate`)."""
    out = F.g6(joint, fit, F.null_toys(joint, fit, n_toys, seed), alpha=alpha)
    return {**out, "rows": {"real": joint.n_real, "pseudo": joint.S * joint.P}}


def holdout_evidence(joint: Segmented, fit, y_v: dict, kappa: str, alpha: float, omit=()) -> dict:
    """The holdout of a pooled result (A26): one V test over the held-out units of all segments (`y_v` = {segment:
    values}), validating the pooled model jointly; the residual covariance carries the joint Sigma_beta, so units of
    different segments are coupled through theta_bar and the common theta. Analytic path (chi2_k, k the sum over the
    segments' units). Returns {evidence (validate.holdout_evidence's sealed record, for DecisionBook), segments,
    units}. `omit` is for negative controls only."""
    from . import validate as VV
    missing = [s for s in joint.names if s not in y_v]
    if missing:
        raise PoolingError("pooling.validation", f"no held-out units for segments {missing}: one V test covers all "
                           "segments")
    yv = np.concatenate([np.asarray(y_v[s], float) for s in joint.names])
    if not omit:
        ev = VV.holdout_evidence(joint, fit, yv, kappa, alpha)
    else:
        joint.set_val_point(fit.beta[:joint.d + len(joint.phi)])
        pc = VV.holdout_pieces(joint, fit, yv, omit=omit)
        Cp, k = VV.c_r_plus(pc["C_r"], pc["s"], pc["constraints"])
        T = VV.t_v(pc["r"], Cp)
        ev = {"kind": "holdout", "T": T, "k": int(k), "p": float(stats.chi2.sf(T, k)) if k else None, "omit": list(omit)}
    return {"evidence": ev, "segments": list(joint.names), "units": joint.val["units"]}


def segment_truths(joint: Segmented, bar_link, common, tau_true=None, rng=None) -> list:
    """The physical theta of each segment for G8 pseudo-data (A26): a common truth (tau_true None or 0: theta_s =
    theta_bar) or spread truths theta_s,j = theta_bar_j + tau_true_j x_s,j in link space with x ~ N(0, 1) from rng."""
    bar_link = np.asarray(bar_link, float)
    t = np.zeros(joint.P) if tau_true is None else np.asarray(tau_true, float)
    out = []
    for _ in range(joint.S):
        x = rng.normal(size=joint.P) if (rng is not None and np.any(t > 0)) else np.zeros(joint.P)
        th = np.zeros(joint.d0)
        for k, (i, n) in enumerate(zip(joint.pooled_idx, joint.pooled)):
            th[i] = L.inv_link(np.array([bar_link[k] + t[k] * x[k]]), joint.links[n])[0]
        th[joint.common_idx] = np.asarray(common, float)
        out.append(th)
    return out


def closure_point(make_joint, truth_fixed, n_req: int, seeds, fitter=None) -> dict:
    """One G8 injection point of a pooled fit (A26: segment-level pseudo-data): `make_joint(seed)` returns a Segmented
    whose segments hold pseudo-data drawn per segment (from a common truth or spread truths, `segment_truths`);
    `fitter(joint, seed)` (default fit_pooled) returns a PooledFit. The error and the 68%/95% coverage are judged on
    the fixed effects against `truth_fixed` (theta_bar in link space, the common theta); then `closure.g8`."""
    from . import closure as C
    truth = np.asarray(truth_fixed, float)
    fitter = fitter or fit_pooled

    def fit_and_cover(joint, s):
        res = fitter(joint, s)
        if not res.converged:
            return False, None, None, None, {"n": 0, "X": 0}, True
        k = joint.P + joint.Q
        err = np.asarray(res.fit.beta[:k], float) - truth
        st = np.asarray(res.fit.sigma_tot[:k], float)
        return True, err, np.abs(err) <= st, np.abs(err) <= 1.96 * st, {"n": 0, "X": 0}, True
    return C.run_point(make_joint, fit_and_cover, n_req, seeds)


def grade(gates: dict, p7: str, v: str, vmode: str, real_data: bool, design_only: bool = False,
          validation_data_reuse: str = "none", earlier_failure_record: str = "none",
          validation_data_simulated: bool = False, own_flags=(), upstreams=()) -> dict:
    """The grade and use of a pooled result (A26): the same Appendix C rules as any calibration result. The recorded
    gate states (G1 on the joint fit, the others as A26 applies them) give the rule-0 inputs (`use.aggregate`), the
    flags `partial-pooling` (informational) and any C.1 flag are added, and `use.judge` grades the result."""
    from . import use as U
    agg = U.aggregate(gates, p7, v, vmode)
    flags = sorted((set(own_flags) & U.FLAGS) | set(agg["flags"]) | {"partial-pooling"})
    inputs = {**agg["inputs"], "real_data": bool(real_data), "design_only": bool(design_only), "vmode": vmode,
              "validation_data_reuse": validation_data_reuse, "earlier_failure_record": earlier_failure_record,
              "validation_data_simulated": bool(validation_data_simulated), "own_flags": flags}
    ups = list(upstreams)
    return {"inputs": inputs, "upstreams": ups, "undecided": agg["undecided"], "reasons": agg["reasons"],
            "judgment": U.judge(inputs, ups)}


GRADE_KEYS = ("gates", "p7", "v", "vmode", "real_data", "design_only", "validation_data_reuse",
              "earlier_failure_record", "validation_data_simulated", "own_flags", "upstreams")
GRADE_REQUIRED = ("gates", "p7", "v", "vmode", "real_data")


def check_grade_inputs(given) -> None:
    """The grade inputs a caller supplies for a pooled result (`simcal_fit.py pool --grade`): the recorded states of
    the gates decided elsewhere, P7, V, the validation mode and the data kind; PoolingError (exit 2) otherwise."""
    if not isinstance(given, dict) or set(given) - set(GRADE_KEYS) or any(k not in given for k in GRADE_REQUIRED) \
            or not isinstance(given["gates"], dict):
        raise PoolingError("pooling.grade", f"--grade holds {{{', '.join(GRADE_REQUIRED)}}} (and optionally the other "
                           f"Appendix C.1 inputs {[k for k in GRADE_KEYS if k not in GRADE_REQUIRED]})")


def grade_report(decided: dict, given: dict | None = None) -> dict:
    """What the pooled run can say about its grade (A26): without `given`, the gate states it decided and the inputs
    still needed (`status` inputs-needed); with `given` (check_grade_inputs), the states decided here replace the
    given ones for the same gate and `grade` judges the result."""
    from . import use as U
    if given is None:
        return {"status": "inputs-needed", "decided": dict(decided),
                "needed": [g for g in U.MANDATORY if g not in decided] + ["p7", "v", "vmode", "real_data"],
                "rule": "A26: Appendix C (use.aggregate, use.judge); partial-pooling is informational"}
    check_grade_inputs(given)
    gates = {**given["gates"], **decided}
    try:
        g = grade(gates, given["p7"], given["v"], given["vmode"], given["real_data"],
                  **{k: given[k] for k in GRADE_KEYS if k in given and k not in GRADE_REQUIRED})
    except (ValueError, KeyError, TypeError) as exc:
        raise PoolingError("pooling.grade", f"grade inputs: {exc}") from None
    return {"status": "graded", "decided": dict(decided), **g}


# ------------------------------------------------------------------ a segmented linear toy (synthetic)
def segmented_linear(cfg, truths, data_seed, mc_seed: int = 1) -> list:
    """One toys_linear problem per segment (same configuration, segment truths `truths` (S x d)), data seeds
    derived from (data_seed, s)."""
    from . import toys_linear as TL
    base = [int(x) for x in np.atleast_1d(data_seed)]
    return [TL.make(cfg, np.asarray(t, float), TL.F_seed(base + [s]), TL.F_seed((int(mc_seed), s)))
            for s, t in enumerate(truths)]
