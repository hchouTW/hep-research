"""The learned density ratio of Part B section 6.2 (phase 5; A25 on section 19-9): a classifier-estimated ratio
p(y | x; theta') / p(y | x; theta_0) for ONE post-hoc correction node, used only to reweight stored MC events. It may
depend on theta (a theta-parameterized classifier); cross-fitting, probability calibration, the prior-ratio
correction, P0 and G4-L apply. SBI (learning the likelihood or posterior of theta from observables) is not a method of
this workflow: `check_spec` refuses it, and nothing here returns a theta estimate.

The classifier (NumPy/SciPy only, section 14): L2-regularized logistic regression on monomials (up to `degree`) of the
standardized node inputs x and outputs y, each multiplied by the theta terms (dtheta_a, dtheta_a dtheta_b) so that the
log ratio is exactly 0 at theta_0. Training MC: class 0 the stored (x, y) at the generation point, class 1 the same
stored x with y resampled at training points theta_t spanning the support box (paired x: the classifier learns the
conditional ratio, so it composes with weights on upstream nodes).

- Cross-fitting: the events are split into F folds; the weights of fold k come from a classifier trained on the other
  folds (F = 1 trains and applies on the same events: no cross-fitting, which G4-L refuses from the record).
- Probability calibration: Platt scaling (logit' = a logit + b) on a calibration split of the training events not used
  for fitting; `none` keeps the raw logit (G4-L refuses it from the record).
- Feature clamp (A30): each fold model keeps the box (per-feature min and max) of both classes' fitting rows and
  evaluates on features clipped to it, so the polynomial never extrapolates into the tails (calibration rows and
  applied events outside the box get the boundary value).
- Prior-ratio correction: log r = logit' - log(n_1 / n_0), the class sizes of the set the logit is calibrated on.
- V_learn = the variation between repeated trainings (independent training MC and a new initialization seed) + the
  square of the closure bias on held-out samples (section 6.2): `v_learn`, its two parts kept apart
  (V_learn^bias is sampled by the toys of section 6.6). Readings of the open details (L2): full matrices, the
  training part the sample covariance over R repeats, the bias part b b^T with b the fold-averaged held-out closure
  difference at the evaluation point minus the same difference at theta_0, where the ratio is 1 (a control variate
  that removes most of the closure comparison's own MC noise, A29; toy.ChainEvaluator.v_learn), and V_bias = b b^T
  minus the covariance of b's remaining MC noise, negative eigenvalues set to 0 (A29).

Everything is `synthetic` when it runs on the toy chain; results carry `provisional-thresholds` (no section 8.7 row
calibrates G4-L, ambiguity L8)."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import optimize, special
from scipy.stats import qmc

TARGET = "node-density-ratio"
USE = "reweight-stored-mc"
CALIBRATIONS = ("platt", "none")
DEFAULTS = {"folds": 5, "repeats": 5, "training_points": 8, "degree": 4, "l2": 1e-4, "calibration": "platt",
            "calibration_fraction": 0.2, "label_smoothing": 0.0, "prior_ratio": True, "max_iterations": 500}


class LearnedError(ValueError):
    """A learned-ratio specification or query the engine refuses (exit 2): code learned.sbi_refused,
    learned.not_post_hoc, learned.one_node, learned.spec, learned.outside_support."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class OutsideSupport(LearnedError):
    def __init__(self, message: str):
        super().__init__("learned.outside_support", message)


# ------------------------------------------------------------------ the specification and the SBI boundary
def settings(spec: dict) -> dict:
    return {**DEFAULTS, **{k: v for k, v in (spec or {}).items() if k in DEFAULTS}}


def check_spec(spec: dict, param_nodes: dict | None = None, node_io: tuple | None = None,
               contract: dict | None = None, methods: dict | None = None) -> list[dict]:
    """Findings against a plan's learned-ratio specification (plan.evaluator.learned):
    {node, parameters, features: {inputs, outputs, degree}, target, use, folds, repeats, calibration, ...}.

    Refused (A25, section 19-9): a target other than the node density ratio or a use other than reweighting stored MC
    events (learning the likelihood or posterior of theta is SBI, `learned.sbi_refused`); features other than the
    node's stored inputs and outputs (observables as features are SBI); more than one node, or a parameter acting on
    another node (`learned.one_node`); a node the contract does not declare `post_hoc_correction`
    (`learned.not_post_hoc`, section 6.2). node_io = (input variables, output variables) of the node."""
    out: list[dict] = []

    def bad(code, msg):
        out.append({"code": code, "message": msg})
    if not isinstance(spec, dict):
        return [{"code": "learned.spec", "message": "plan.evaluator.learned is an object"}]
    target, use = spec.get("target", TARGET), spec.get("use", USE)
    if target != TARGET:
        bad("learned.sbi_refused", f"target {target!r}: a learned ratio is the density ratio of one post-hoc "
            "correction node; learning the likelihood or posterior of theta (SBI) is not a method of this workflow "
            "(A25, section 19-9)")
    if use != USE:
        bad("learned.sbi_refused", f"use {use!r}: a learned ratio is used only to reweight stored MC events (A25)")
    for k in spec:
        if any(w in str(k).lower() for w in ("posterior", "likelihood", "sbi", "summary_statistic")):
            bad("learned.sbi_refused", f"field {k!r}: SBI is not a method of this workflow (A25, section 19-9)")
    node = spec.get("node")
    if spec.get("nodes") is not None or not isinstance(node, str):
        bad("learned.one_node", "a learned ratio is for exactly one post-hoc correction node (`node`, a string)")
    feats = spec.get("features") or {}
    if not isinstance(feats, dict) or not feats.get("outputs"):
        bad("learned.spec", "features: {inputs: [...], outputs: [...], degree}, the node's stored inputs and outputs")
    else:
        extra = set(feats) - {"inputs", "outputs", "degree"}
        if extra:
            bad("learned.sbi_refused", f"features {sorted(extra)}: only the node's stored inputs and outputs are "
                "features (observables or theta as classifier targets are SBI, A25)")
        if node_io is not None:
            ins, outs = (set(v) for v in node_io)
            wrong = sorted(set(feats.get("inputs") or []) - ins) + sorted(set(feats.get("outputs") or []) - outs)
            if wrong:
                bad("learned.sbi_refused", f"features {wrong} are not stored inputs or outputs of node {node!r}: "
                    "a learned ratio reads only that node (observables as features are SBI, A25)")
    pars = spec.get("parameters")
    if not pars or not isinstance(pars, list):
        bad("learned.spec", "parameters: the theta the ratio depends on (non-empty list)")
    elif param_nodes is not None:
        for p in pars:
            if list(param_nodes.get(p, [])) != [node]:
                bad("learned.one_node", f"parameter {p!r} acts on {param_nodes.get(p)}, not only on node {node!r}")
    if methods is not None:
        lp = sorted(p for p, m in methods.items() if m == "learned-density-ratio")
        if isinstance(pars, list) and lp != sorted(pars):
            bad("learned.spec", f"the plan's learned-density-ratio parameters {lp} are not the spec's {sorted(pars)}")
    s = settings(spec)
    if s["calibration"] not in CALIBRATIONS:
        bad("learned.spec", f"calibration {s['calibration']!r} (Platt scaling, or none, which G4-L refuses)")
    if not (isinstance(s["folds"], int) and s["folds"] >= 1 and isinstance(s["repeats"], int) and s["repeats"] >= 2):
        bad("learned.spec", "folds >= 1 and repeats >= 2 (V_learn needs repeated trainings)")
    if contract is not None and isinstance(node, str):
        gn = {n["id"]: n for n in (contract.get("stage_graph") or {}).get("nodes", [])}
        if not (gn.get(node) or {}).get("post_hoc_correction"):
            bad("learned.not_post_hoc", f"node {node!r} is not declared post_hoc_correction in the contract: a learned "
                "density ratio is used only for post-hoc correction models (section 6.2)")
        if (gn.get(node) or {}).get("kernel") == "density":
            bad("learned.not_post_hoc", f"node {node!r} has a density kernel: analytic reweighting applies, not a "
                "learned ratio (section 3.6)")
    return out


# ------------------------------------------------------------------ features
def _exponents(m: int, degree: int) -> list[tuple]:
    return [e for t in range(1, degree + 1) for e in itertools.combinations_with_replacement(range(m), t)]


def _theta_terms(dz: np.ndarray) -> np.ndarray:
    """(dtheta_a, dtheta_a dtheta_b for a <= b) per row of dz (n, d): zero at theta_0."""
    d = dz.shape[1]
    cols = [dz[:, a] for a in range(d)] + [dz[:, a] * dz[:, b] for a in range(d) for b in range(a, d)]
    return np.stack(cols, axis=1)


@dataclass
class FoldModel:
    """One fitted, calibrated classifier: log r(x, y; theta) = a (B(x, y) beta) . tau(theta) + b - log_prior."""
    beta: np.ndarray                  # (n_base, n_tau)
    a: float
    b: float
    log_prior: float
    z_mean: np.ndarray
    z_scale: np.ndarray
    col_mean: np.ndarray
    col_scale: np.ndarray
    train: np.ndarray                 # the event indices it was trained (fitted or calibrated) on
    converged: bool
    iterations: int
    lo: np.ndarray | None = None      # the training box of the features (A30): evaluation features are clipped to it
    hi: np.ndarray | None = None


@dataclass
class TrainedRatio:
    """F fold models of one training, the fold of each event, and the support box."""
    folds: list
    fold_of: np.ndarray
    names: list                       # theta order
    theta0: np.ndarray
    scale: np.ndarray
    support: dict
    degree: int
    exps: list
    spec: dict
    seed: list
    feature_range: tuple = field(default=(None, None))
    offsets: dict = field(default_factory=dict)       # the evaluator's run -> (first, end) event index

    # ---- evaluation
    def base(self, F: np.ndarray, fm: FoldModel) -> np.ndarray:
        F = np.asarray(F, float)
        if fm.lo is not None:             # never extrapolate the polynomial beyond the training rows (A30)
            F = np.clip(F, fm.lo, fm.hi)
        Z = (F - fm.z_mean) / fm.z_scale
        cols = [np.prod(Z[:, list(e)], axis=1) for e in self.exps]
        B = (np.stack(cols, axis=1) - fm.col_mean) / fm.col_scale if cols else np.zeros((len(Z), 0))
        return np.concatenate([np.ones((len(Z), 1)), B], axis=1)

    def tau(self, theta: dict) -> np.ndarray:
        self.check_support(theta)
        dz = np.array([[(float(theta[p]) - t0) / s for p, t0, s in zip(self.names, self.theta0, self.scale)]])
        return _theta_terms(dz)[0]

    def check_support(self, theta: dict) -> None:
        for p in self.names:
            lo, hi = self.support[p]
            v = float(theta[p])
            tol = 1e-9 * max(1.0, abs(hi - lo))
            if not lo - tol <= v <= hi + tol:
                raise OutsideSupport(f"{p} = {v} is outside the learned ratio's training support [{lo}, {hi}]: the "
                                     "classifier was trained only there (refused, never extrapolated)")

    def log_weights(self, F: np.ndarray, theta: dict, fold=None, fold_of=None) -> np.ndarray:
        """log r per event (rows of F, the node's features). fold: one fold's classifier for every event (the
        held-out closure); else each event's own out-of-fold classifier (fold_of, default this training's)."""
        t = self.tau(theta)
        if fold is not None:
            fm = self.folds[int(fold)]
            return self._logr(fm, F, t)
        fo = self.fold_of if fold_of is None else np.asarray(fold_of)
        out = np.empty(len(F))
        for k, fm in enumerate(self.folds):
            sel = fo == k
            if sel.any():
                out[sel] = self._logr(fm, F[sel], t)
        return out

    def _logr(self, fm: FoldModel, F, t) -> np.ndarray:
        if not np.any(t):
            return np.zeros(len(F))                   # theta_0: the ratio is 1 by construction
        s = self.base(F, fm) @ fm.beta @ t
        return fm.a * s + fm.b - fm.log_prior

    def record(self) -> dict:
        """The structural record G4-L checks: folds, and whether every fold's training events are disjoint from the
        events its weights are applied to (computed from the index sets, not declared)."""
        disjoint = [bool(not np.isin(np.where(self.fold_of == k)[0], fm.train).any())
                    for k, fm in enumerate(self.folds)]
        s = self.spec
        return {"target": TARGET, "use": USE, "folds": len(self.folds), "cross_fitted": all(disjoint),
                "train_apply_disjoint": disjoint, "calibration": s["calibration"],
                "prior_ratio_corrected": bool(s["prior_ratio"]), "label_smoothing": s["label_smoothing"],
                "support": {p: list(v) for p, v in self.support.items()}, "degree": self.degree,
                "training_points": s["training_points"], "converged": all(fm.converged for fm in self.folds),
                "calibration_slopes": [fm.a for fm in self.folds], "seed": list(self.seed)}


# ------------------------------------------------------------------ training
def training_points(support: dict, names: list, n: int, seed: int) -> list[dict]:
    """n points spanning the support box: an even grid for one parameter, scrambled Sobol plus the vertices else."""
    if len(names) == 1:
        p = names[0]
        return [{p: float(v)} for v in np.linspace(support[p][0], support[p][1], n)]
    u = qmc.Sobol(len(names), scramble=True, seed=int(seed)).random(n)
    lo = np.array([support[p][0] for p in names])
    hi = np.array([support[p][1] for p in names])
    pts = [dict(zip(names, map(float, lo + r * (hi - lo)))) for r in u]
    pts += [dict(zip(names, map(float, v))) for v in itertools.product(*[support[p] for p in names])]
    return pts


def _fit_logistic(B0, B1s, taus, l2, smooth, x0, max_iter):
    """beta (n_base x n_tau) minimizing the mean log loss of class 0 (B0 at every training point, label 0) and class
    1 (B1s[t] at point t, label 1), with label smoothing and an L2 penalty, by a trust-region Newton method (the
    loss is convex; gradient and Hessian accumulated per training point, never materializing the Kronecker design)."""
    nb, nt = B0.shape[1], taus.shape[1]
    y0, y1 = smooth / 2.0, 1.0 - smooth / 2.0
    n_tot = B0.shape[0] * len(B1s) + sum(b.shape[0] for b in B1s)
    cache: dict = {}

    def parts(v):
        k = v.tobytes()
        if k in cache:
            return cache[k]
        beta = v.reshape(nb, nt)
        M0 = B0 @ beta
        loss, g, H = 0.0, np.zeros((nb, nt)), np.zeros((nb * nt, nb * nt))
        for t, B1 in enumerate(B1s):
            tau = taus[t]
            s0 = M0 @ tau
            s1 = (B1 @ beta) @ tau
            loss += float(np.logaddexp(0.0, s0).sum() - y0 * s0.sum() + np.logaddexp(0.0, s1).sum() - y1 * s1.sum())
            p0, p1 = special.expit(s0), special.expit(s1)
            g += np.outer(B0.T @ (p0 - y0) + B1.T @ (p1 - y1), tau)
            G = (B0.T * (p0 * (1 - p0))) @ B0 + (B1.T * (p1 * (1 - p1))) @ B1
            H += np.kron(G, np.outer(tau, tau))
        out = (loss / n_tot + 0.5 * l2 * float(v @ v), g.ravel() / n_tot + l2 * v,
               H / n_tot + l2 * np.eye(nb * nt))
        cache.clear()
        cache[k] = out
        return out
    res = optimize.minimize(lambda v: parts(v)[0], x0, jac=lambda v: parts(v)[1], hess=lambda v: parts(v)[2],
                            method="trust-exact", options={"maxiter": int(max_iter), "gtol": 1e-10})
    ok = bool(res.success) or float(np.abs(res.jac).max()) <= 1e-8   # converged to rounding (trust-exact's message)
    return res.x.reshape(nb, nt), ok, int(res.nit)


def _platt(s0: np.ndarray, s1: np.ndarray) -> tuple[float, float]:
    """(a, b) of p = expit(a s + b) by maximum likelihood on the calibration rows (true labels)."""
    s = np.concatenate([s0, s1])
    y = np.concatenate([np.zeros(len(s0)), np.ones(len(s1))])

    def fun(v):
        z = v[0] * s + v[1]
        r = special.expit(z) - y
        return float(np.logaddexp(0.0, z).sum() - (y * z).sum()), np.array([r @ s, r.sum()])
    res = optimize.minimize(fun, np.array([1.0, 0.0]), jac=True, method="L-BFGS-B")
    return float(res.x[0]), float(res.x[1])


def train(stored: np.ndarray, sampler, spec: dict, theta0: dict, support: dict, seed) -> TrainedRatio:
    """One training (F fold models). stored: (n, m) features [inputs, outputs] at the generation point; sampler(theta,
    idx, key) -> (len(idx), m) features of the events idx with the outputs resampled at theta from their stored inputs
    (new random numbers per key). seed: a list of ints (training MC and initialization streams)."""
    s = settings(spec)
    names = list(spec["parameters"])
    key = [int(v) for v in (seed if isinstance(seed, (list, tuple)) else [seed])]
    stored = np.asarray(stored, float)
    n, m = stored.shape
    F_ = int(s["folds"])
    rng = np.random.default_rng(np.random.SeedSequence([*key, 0]))
    fold_of = rng.permutation(n) % F_
    t0 = np.array([float(theta0[p]) for p in names])
    scale = np.array([max(abs(support[p][1] - support[p][0]) / 2.0, 1e-12) for p in names])
    pts = training_points(support, names, int(s["training_points"]), key[0] % (2 ** 31))
    pts = [p for p in pts if any(abs(p[q] - theta0[q]) > 1e-12 for q in names)]
    taus = _theta_terms(np.array([[(pt[q] - theta0[q]) / sc for q, sc in zip(names, scale)] for pt in pts]))
    exps = _exponents(m, int(s["degree"]))
    tr = TrainedRatio([], fold_of, names, t0, scale, {p: tuple(map(float, support[p])) for p in names},
                      int(s["degree"]), exps, s, key, (stored.min(axis=0).tolist(), stored.max(axis=0).tolist()))
    for k in range(F_):
        idx = np.where(fold_of != k)[0] if F_ > 1 else np.arange(n)
        r = np.random.default_rng(np.random.SeedSequence([*key, 1, k]))
        idx = r.permutation(idx)
        n_cal = int(round(float(s["calibration_fraction"]) * len(idx))) if s["calibration"] == "platt" else 0
        fit_idx, cal_idx = idx[n_cal:], idx[:n_cal]
        z_mean, z_scale = stored[fit_idx].mean(axis=0), stored[fit_idx].std(axis=0)
        z_scale = np.where(z_scale > 0, z_scale, 1.0)
        Z = (stored[fit_idx] - z_mean) / z_scale
        raw = np.stack([np.prod(Z[:, list(e)], axis=1) for e in exps], axis=1)
        col_mean, col_scale = raw.mean(axis=0), raw.std(axis=0)
        col_scale = np.where(col_scale > 0, col_scale, 1.0)
        fm = FoldModel(np.zeros((1 + len(exps), taus.shape[1])), 1.0, 0.0, 0.0, z_mean, z_scale, col_mean, col_scale,
                       idx, True, 0)
        F1s = [sampler(pt, fit_idx, [*key, 2, k, t]) for t, pt in enumerate(pts)]
        rows = np.concatenate([stored[fit_idx], *F1s])          # both classes' fitting rows (A30)
        fm.lo, fm.hi = rows.min(axis=0), rows.max(axis=0)
        B0 = tr.base(stored[fit_idx], fm)
        B1s = [tr.base(F1, fm) for F1 in F1s]
        x0 = r.normal(0.0, 1e-3, B0.shape[1] * taus.shape[1])            # the initialization seed (section 6.6)
        beta, ok, nit = _fit_logistic(B0, B1s, taus, float(s["l2"]), float(s["label_smoothing"]), x0,
                                      s["max_iterations"])
        fm.beta, fm.converged, fm.iterations = beta, ok, nit
        n0 = n1 = len(fit_idx) * len(pts)
        if n_cal:
            C0 = tr.base(stored[cal_idx], fm) @ beta
            s0 = np.concatenate([C0 @ tau for tau in taus])
            s1 = np.concatenate([(tr.base(sampler(pt, cal_idx, [*key, 3, k, t]), fm) @ beta) @ taus[t]
                                 for t, pt in enumerate(pts)])
            fm.a, fm.b = _platt(s0, s1)
            n0, n1 = len(s0), len(s1)
        fm.log_prior = math.log(n1 / n0) if s["prior_ratio"] else 0.0
        tr.folds.append(fm)
    return tr


# ------------------------------------------------------------------ V_learn (section 6.2)
def v_learn(preds: list, bias, bias_noise=None) -> dict:
    """V_learn = the variation between repeated trainings + the square of the closure bias on held-out samples.
    preds: the predictions of R >= 2 repeated trainings at one point (observable space); bias: the held-out closure
    difference there. Full matrices (reading L2): V_train the sample covariance; V_bias = b b^T, or, with bias_noise
    (the covariance of b's own MC noise, A29), b b^T - bias_noise with negative eigenvalues set to 0 (E[b b^T] =
    bias bias^T + bias_noise: the subtraction removes the noise, the clipping keeps V_bias positive semi-definite)."""
    P = np.atleast_2d(np.asarray(preds, float))
    if P.shape[0] < 2:
        raise LearnedError("learned.spec", "V_learn needs >= 2 repeated trainings")
    Vt = np.atleast_2d(np.cov(P, rowvar=False, ddof=1))
    b = np.asarray(bias, float).reshape(-1)
    Vb = np.outer(b, b)
    out: dict = {"repeats": int(P.shape[0])}
    if bias_noise is not None:
        N = np.asarray(bias_noise, float).reshape(b.size, b.size)
        lam, U = np.linalg.eigh(0.5 * ((Vb - N) + (Vb - N).T))
        Vb = (U * np.clip(lam, 0.0, None)) @ U.T
        out["V_learn_bias_noise"] = N
    return {"V_learn": Vt + Vb, "V_learn_train": Vt, "V_learn_bias": Vb, "bias": b, **out}
