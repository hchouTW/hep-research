"""The surrogate model of the simulator calibration workflow (Part B sections 6.4, 6.5, 6.6, 7.1, 8.1, 8.2 note 4, 14;
`calib_emulator.py` is its CLI; phase 3).

- Training set (D80): the Sobol design points and the P6 held-back set come from `design.design_points`; this module
  evaluates them through the ask/tell interface of section 7.1 (a state file records the `run_id` of each design point)
  and fits the surrogate on the training points. The same theta scan uses common random numbers (section 6.6): every
  design point and every held-back point is evaluated with the plan's nominal seed.
- The surrogate model: a linear smoother in the design-point values, mu-hat(theta) = sum_j w_j(theta) mu_j (the
  w_j(theta) of section 6.7 and Appendix A), here universal kriging with a squared-exponential correlation in the unit
  cube of the design box, a constant-plus-linear trend and one correlation shared by all observables (so the weights
  are the same for every observable; the correlation lengths by restricted maximum likelihood, with the kriging
  matrix's condition bounded). Mode `interpolate` passes through the design points (a numerical jitter only);
  mode `regression` fits a nugget and does not (the mode where the map varies with theta, section 6.4, D28). The
  observables' V_MC is interpolated with the same weights (projected onto the positive semi-definite cone); V_emu is
  the kriging variance times the observables' process covariance (section 6.4: V_MC and V_emu separately).
- Method combination (section 6.5, outside to inside): the surrogate is outermost; each design-point value at a query
  theta is that design point evaluated at the query's other parameters by the plan's inner methods (resimulation,
  rerun, reweighting), so mu-hat(theta) = sum_j w_j(theta_s) mu_j(theta_other). V_emu is the training-time value at
  theta_s.
- Queries outside the surrogate domain (the design box) are always rejected (`OutsideDomain`).
- P6 (section 8.2 note 4, section 8.1): |Delta m| <= 0.3 sqrt(V^unc_data) + z sigma_Delta with z = z_{1 - alpha/(2M)},
  M = held-out points x observables, alpha = 0.01 (D53; section 8.7 row 2004, uncalibrated: `provisional-thresholds`);
  the chi2 test of the pulls (alpha = 0.01) only with >= 30 held-out points. The spot-check points of section 5.4 must
  be among the held-out points (a missing one is rejected).
- G8 for resimulation-level parameters (approval A12, the reading of section 19-5): surrogate pseudo-data for the bulk
  of the ensemble, plus a full-simulation spot check at the section 8.4 injection points with seeds independent of the
  training set. This module provides the pseudo-data and the spot check's bookkeeping; its decision rule is not given
  by Part B or A12 and is left undecided here (`not-decided`).
- The theta-noise item of P5 (section 8.2 note 3, fifth item) is computed by calib_design.py; this module provides the
  weights and their first and second derivatives in theta (`Surrogate.weight_derivatives`).
"""
from __future__ import annotations

import math
from typing import Any, Protocol

import numpy as np
from scipy import linalg, optimize, stats

PHASE = 3
ALPHA_P6 = 0.01                 # section 8.7 row 2004 (design value)
DATA_FACTOR = 0.3               # |Delta m| <= 0.3 sqrt(V^unc_data) + z sigma_Delta (section 8.2, suggested default)
MIN_PULL_POINTS = 30            # the chi2 part of P6 needs >= 30 held-out points (section 8.1)
STATE_SCHEMA = "calibration-ask-tell/1"
MODES = ("interpolate", "regression")
JITTER = 1e-10
MAX_COND = 1e8                  # the kriging matrix's condition bound: the jitter then never smooths (interpolate mode)
LENGTH_BOUNDS = (0.05, 4.0)     # correlation lengths in units of the design box
NUGGET_BOUNDS = (1e-6, 1.0)     # regression mode, relative to the process variance


class EmulatorError(ValueError):
    """Input the surrogate refuses (exit 2): code p6.spot_checks_missing, emulator.state, ..."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class OutsideDomain(EmulatorError):
    """A query outside the surrogate domain: always rejected (section 6.4)."""

    def __init__(self, message: str):
        super().__init__("emulator.outside_domain", message)


class SurrogateModel(Protocol):
    """What a surrogate model gives the engine (section 6.4)."""

    parameters: list

    def weights(self, theta: dict) -> np.ndarray: ...

    def predict(self, theta: dict, values=None, v_mc=None) -> dict: ...     # {pred, V_MC, V_emu, weights}

    def domain(self) -> dict: ...


# ------------------------------------------------------------------ the surrogate model
def _psd(M: np.ndarray) -> np.ndarray:
    M = 0.5 * (M + M.T)
    lam, U = np.linalg.eigh(M)
    return (U * np.clip(lam, 0.0, None)) @ U.T


class Surrogate:
    """Universal kriging over the design box (module docstring). points: the training design points ({parameter:
    value}); values: (n, k) observables; v_mc: (n, k, k) their V_MC; bounds: {parameter: [lo, hi]}."""

    def __init__(self, parameters, bounds: dict, points: list, values, v_mc=None, names=None,
                 mode: str = "interpolate", length=None, nugget=None):
        if mode not in MODES:
            raise EmulatorError("emulator.mode", f"mode {mode!r}: one of {MODES}")
        self.parameters = list(parameters)
        if not self.parameters:
            raise EmulatorError("emulator.parameters", "a surrogate needs at least one parameter")
        self.bounds = {p: [float(bounds[p][0]), float(bounds[p][1])] for p in self.parameters}
        for p, (lo, hi) in self.bounds.items():
            if not hi > lo:
                raise EmulatorError("emulator.bounds", f"parameter {p}: empty design box {self.bounds[p]}")
        self.points = [{p: float(pt[p]) for p in self.parameters} for pt in points]
        self.values = np.atleast_2d(np.asarray(values, float))
        n, k = self.values.shape
        if len(self.points) != n:
            raise EmulatorError("emulator.training", f"{len(self.points)} points and {n} value rows")
        self.v_mc = np.zeros((n, k, k)) if v_mc is None else np.asarray(v_mc, float).reshape(n, k, k)
        self.names = list(names) if names is not None else [f"o{i}" for i in range(k)]
        self.mode = mode
        d = len(self.parameters)
        self.X = np.array([[self._unit(p, pt[p]) for p in self.parameters] for pt in self.points])
        self.trend = "linear" if n >= d + 3 else "constant"
        if n < 2 + (d if self.trend == "linear" else 0):
            raise EmulatorError("emulator.too_few_points", f"{n} training points for {d} parameters")
        self.F = self._basis(self.X)
        self.mean = self.values.mean(axis=0)
        spread = self.values.std(axis=0)
        self.varying = spread > 1e-12 * np.maximum(1.0, np.abs(self.mean))
        self.scale = np.where(self.varying, spread, 1.0)
        self.Ys = (self.values - self.mean) / self.scale
        if length is None:
            length, nugget = self._fit()
        self.length = np.asarray(length, float)
        self.nugget = float(nugget if nugget is not None else JITTER)
        self._factor()

    # -- coordinates and basis
    def _unit(self, p, v):
        lo, hi = self.bounds[p]
        return (float(v) - lo) / (hi - lo)

    def _basis(self, X):
        X = np.atleast_2d(X)
        return np.c_[np.ones(len(X)), X] if self.trend == "linear" else np.ones((len(X), 1))

    def _corr(self, A, B, length):
        diff = (A[:, None, :] - B[None, :, :]) / length
        return np.exp(-0.5 * (diff ** 2).sum(-1))

    # -- hyperparameters: concentrated restricted likelihood, one correlation, one variance per observable
    def _nll(self, length, nugget):
        n = len(self.X)
        K = self._corr(self.X, self.X, length) + nugget * np.eye(n)
        lam = np.linalg.eigvalsh(K)
        if not lam[0] > lam[-1] / MAX_COND:
            return math.inf
        try:
            c = linalg.cho_factor(K, lower=True)
        except linalg.LinAlgError:
            return math.inf
        Fm = self.F
        KiF = linalg.cho_solve(c, Fm)
        A = Fm.T @ KiF
        try:
            ca = linalg.cho_factor(A, lower=True)
        except linalg.LinAlgError:
            return math.inf
        Y = self.Ys[:, self.varying]
        if Y.shape[1] == 0:
            return 0.0
        KiY = linalg.cho_solve(c, Y)
        beta = linalg.cho_solve(ca, Fm.T @ KiY)
        R = Y - Fm @ beta
        s2 = np.einsum("ik,ik->k", R, linalg.cho_solve(c, R)) / max(n - Fm.shape[1], 1)
        if np.any(s2 <= 0):
            return math.inf
        kk = Y.shape[1]
        logdet = 2 * np.log(np.diag(c[0])).sum()
        logdet_a = 2 * np.log(np.diag(ca[0])).sum()
        return float(kk * logdet + (n - Fm.shape[1]) * np.log(s2).sum() + kk * logdet_a)

    def _fit(self):
        d = len(self.parameters)
        lo_l, hi_l = np.log(LENGTH_BOUNDS)
        reg = self.mode == "regression"

        def unpack(x):
            return np.exp(x[:d]), (float(np.exp(x[d])) if reg else JITTER)

        def f(x):
            v = self._nll(*unpack(x))
            return v if np.isfinite(v) else 1e300
        bnds = [(lo_l, hi_l)] * d + ([tuple(np.log(NUGGET_BOUNDS))] if reg else [])
        best = None
        for l0 in (0.05, 0.1, 0.2, 0.5):
            x0 = np.r_[np.full(d, math.log(l0)), [math.log(1e-2)] if reg else []]
            r = optimize.minimize(f, x0, method="L-BFGS-B", bounds=bnds)
            if best is None or r.fun < best.fun:
                best = r
        assert best is not None
        if not best.fun < 1e299:
            raise EmulatorError("emulator.singular", f"no correlation length gives a kriging matrix with condition "
                                f"<= {MAX_COND:g} (coincident design points?)")
        return unpack(best.x)

    def _factor(self):
        n = len(self.X)
        self.K = self._corr(self.X, self.X, self.length) + self.nugget * np.eye(n)
        self._c = linalg.cho_factor(self.K, lower=True)
        self._KiF = linalg.cho_solve(self._c, self.F)
        self._A = self.F.T @ self._KiF
        self._ca = linalg.cho_factor(self._A, lower=True)
        KiY = linalg.cho_solve(self._c, self.Ys)
        beta = linalg.cho_solve(self._ca, self.F.T @ KiY)
        R = self.Ys - self.F @ beta
        B = R.T @ linalg.cho_solve(self._c, R) / max(n - self.F.shape[1], 1)
        B[~self.varying, :] = 0.0
        B[:, ~self.varying] = 0.0
        self.B = _psd(B)                                   # process covariance of the standardized observables

    # -- the linear smoother
    def _lam(self, r, f):
        """lambda = K^-1 r + K^-1 F A^-1 (f - F^T K^-1 r): linear in (r, f), so derivatives use the same map."""
        Kir = linalg.cho_solve(self._c, r)
        u = f - self.F.T @ Kir
        return Kir + self._KiF @ linalg.cho_solve(self._ca, u), u

    def _x(self, theta):
        return np.array([self._unit(p, theta[p]) for p in self.parameters])

    def in_domain(self, theta: dict) -> bool:
        return all(p in theta and self.bounds[p][0] - 1e-12 * (abs(self.bounds[p][0]) + 1) <= float(theta[p])
                   <= self.bounds[p][1] + 1e-12 * (abs(self.bounds[p][1]) + 1) for p in self.parameters)

    def check(self, theta: dict):
        if not self.in_domain(theta):
            raise OutsideDomain(f"query {({p: theta.get(p) for p in self.parameters})} outside the surrogate domain "
                                f"{self.bounds} (section 6.4: always rejected)")

    def weights(self, theta: dict) -> np.ndarray:
        """w_j(theta) of the training design points (sum_j w_j = 1; the trend is reproduced exactly)."""
        self.check(theta)
        x = self._x(theta)
        r = self._corr(x[None, :], self.X, self.length)[0]
        return self._lam(r, self._basis(x[None, :])[0])[0]

    def weight_derivatives(self, theta: dict, parameter: str) -> tuple[np.ndarray, np.ndarray]:
        """(d w_j / d theta_i, d^2 w_j / d theta_i^2) in the parameter's own units, analytic (the inputs of the
        theta-noise item s_i, kappa_i of P5, section 8.2 note 3, computed by calib_design.py)."""
        self.check(theta)
        i = self.parameters.index(parameter)
        width = self.bounds[parameter][1] - self.bounds[parameter][0]
        x = self._x(theta)
        r = self._corr(x[None, :], self.X, self.length)[0]
        a = (x[i] - self.X[:, i]) / self.length[i] ** 2
        dr = -r * a
        d2r = r * (a ** 2 - 1.0 / self.length[i] ** 2)
        df = np.zeros(self.F.shape[1])
        if self.trend == "linear":
            df[1 + i] = 1.0
        d1 = self._lam(dr, df)[0] / width
        d2 = self._lam(d2r, np.zeros_like(df))[0] / width ** 2
        return d1, d2

    def kriging_variance(self, theta: dict) -> float:
        self.check(theta)
        x = self._x(theta)
        r = self._corr(x[None, :], self.X, self.length)[0]
        u = self._basis(x[None, :])[0] - self.F.T @ linalg.cho_solve(self._c, r)
        s2 = 1.0 - r @ linalg.cho_solve(self._c, r) + u @ linalg.cho_solve(self._ca, u)
        return max(float(s2), 0.0)

    def v_emu(self, theta: dict) -> np.ndarray:
        """V_emu(theta): the interpolation variance (section 6.4), in observable units."""
        D = np.diag(self.scale)
        return self.kriging_variance(theta) * (D @ self.B @ D)

    @property
    def interpolates_exactly(self) -> bool:
        """True in mode `interpolate` (rejected by calib_design.py where the map varies with theta, section 15.3a)."""
        return self.mode == "interpolate"

    def predict(self, theta: dict, values=None, v_mc=None) -> dict:
        """mu-hat = sum_j w_j mu_j and V_MC = sum_j w_j V_MC,j (PSD-projected) with the training values, or with the
        design points' values at the query's other parameters (`values`, `v_mc`: section 6.5); V_emu separately."""
        w = self.weights(theta)
        vals = self.values if values is None else np.asarray(values, float)
        vm = self.v_mc if v_mc is None else np.asarray(v_mc, float)
        return {"pred": w @ vals, "V_MC": _psd(np.tensordot(w, vm, axes=1)), "V_emu": self.v_emu(theta),
                "weights": w, "names": list(self.names)}

    def domain(self) -> dict:
        return {"kind": "box", "bounds": dict(self.bounds)}

    def record(self) -> dict:
        """The trained surrogate as plain numbers (refit-free: the hyperparameters are stored)."""
        return {"parameters": self.parameters, "bounds": self.bounds, "mode": self.mode, "trend": self.trend,
                "length": self.length.tolist(), "nugget": self.nugget, "names": self.names,
                "points": self.points, "values": self.values.tolist(), "V_MC": self.v_mc.tolist(),
                "domain": self.domain(), "interpolates_exactly": self.interpolates_exactly}

    @classmethod
    def from_record(cls, rec: dict) -> Surrogate:
        return cls(rec["parameters"], rec["bounds"], rec["points"], rec["values"], rec.get("V_MC"), rec.get("names"),
                   rec.get("mode", "interpolate"), rec["length"], rec["nugget"])


# ------------------------------------------------------------------ ask/tell state file (section 7.1)
def new_state(points: list, purpose: str, base_theta: dict | None = None, seeds: dict | None = None,
              names=None, prefix: str | None = None) -> dict:
    """A state file for the evaluations of `points` (design points, held-back points, spot checks): one entry per
    point with its run_id, the full parameter point (base_theta overlaid by the point) and its seeds."""
    pre = prefix or purpose
    entries = [{"run_id": f"{pre}-{i:04d}", "point": dict(pt), "theta": {**(base_theta or {}), **pt},
                "seeds": dict(seeds or {}), "status": "pending"} for i, pt in enumerate(points)]
    return {"schema": STATE_SCHEMA, "purpose": purpose, "names": list(names) if names is not None else None,
            "entries": entries}


def _check_state(state):
    if not isinstance(state, dict) or state.get("schema") != STATE_SCHEMA or not isinstance(state.get("entries"),
                                                                                             list):
        raise EmulatorError("emulator.state", f"not a {STATE_SCHEMA} state")
    ids = [e.get("run_id") for e in state["entries"]]
    if len(set(ids)) != len(ids):
        raise EmulatorError("emulator.state", "duplicate run_id in the state")


def ask(state: dict, n: int | None = None) -> list[dict]:
    """The next pending evaluations (at most n), marked submitted: [{run_id, theta, seeds, names}]."""
    _check_state(state)
    out: list[dict] = []
    for e in state["entries"]:
        if e["status"] == "pending" and (n is None or len(out) < n):
            e["status"] = "submitted"
            out.append({"run_id": e["run_id"], "theta": dict(e["theta"]), "seeds": dict(e["seeds"]),
                        "names": state.get("names")})
    return out


def tell(state: dict, run_id: str, result: dict) -> dict:
    """Record the result of one evaluation ({names, pred, V_MC}); an unknown run_id, a result for an entry not
    submitted, a second different result or a result whose observables differ from the state's is refused."""
    _check_state(state)
    by = {e["run_id"]: e for e in state["entries"]}
    if run_id not in by:
        raise EmulatorError("emulator.unknown_run_id", f"no evaluation {run_id!r} in the state")
    e = by[run_id]
    try:
        pred = np.asarray(result["pred"], float)
        V = np.asarray(result["V_MC"], float).reshape(pred.size, pred.size)
    except (KeyError, TypeError, ValueError) as exc:
        raise EmulatorError("emulator.result", f"{run_id}: a result is {{names, pred, V_MC}} ({exc})") from None
    names = list(result.get("names") or state.get("names") or [])
    if state.get("names") is not None and names != list(state["names"]):
        raise EmulatorError("emulator.names", f"{run_id}: observables {names} differ from the state's")
    rec = {"names": names, "pred": pred.tolist(), "V_MC": V.tolist()}
    if e["status"] == "done":
        if e["result"] != rec:
            raise EmulatorError("emulator.second_result", f"{run_id}: a second, different result")
        return state
    if e["status"] != "submitted":
        raise EmulatorError("emulator.not_submitted", f"{run_id}: told before it was asked ({e['status']})")
    e.update(status="done", result=rec)
    e["_raw"] = result                                     # in memory only (influence values for sigma_Delta)
    return state


def complete(state: dict) -> bool:
    return all(e["status"] == "done" for e in state["entries"])


def drive(evaluator, state: dict, max_rounds: int = 1000) -> dict:
    """Submit every pending evaluation to the evaluator's ask() and record what its tell() returns, until complete or
    nothing more arrives (status incomplete: the state lists what is outstanding)."""
    for _ in range(max_rounds):
        reqs = ask(state)
        if reqs:
            evaluator.ask(reqs)
        waiting = [e["run_id"] for e in state["entries"] if e["status"] == "submitted"]
        if not waiting:
            break
        got = evaluator.tell(waiting)
        for rid, res in got.items():
            tell(state, rid, res)
        if not got:
            break
    done = complete(state)
    return {"status": "ok" if done else "incomplete", "state": state,
            "outstanding": [e["run_id"] for e in state["entries"] if e["status"] != "done"]}


def _arrays(state):
    rows = [e for e in state["entries"] if e["status"] == "done"]
    return ([e["point"] for e in rows], np.array([e["result"]["pred"] for e in rows], float),
            np.array([e["result"]["V_MC"] for e in rows], float), rows)


def surrogate_from_state(state: dict, cfg: dict) -> Surrogate:
    """The surrogate fitted on a completed training state (the CLI's `train` after ask/tell outside the engine)."""
    _check_state(state)
    if not complete(state):
        raise EmulatorError("emulator.incomplete_state", "training evaluations outstanding")
    points, vals, vm, _ = _arrays(state)
    return Surrogate(cfg["parameters"], cfg["bounds"], points, vals, vm, state.get("names"), cfg["mode"])


# ------------------------------------------------------------------ settings and the training set (D80)
def settings(contract: dict, plan: dict, parameters=None) -> dict:
    """The plan's surrogate settings (plan.design.surrogate): parameters (default: those whose method is
    surrogate-model), n_design (training points, default 24), held_back (default 8), seed, mode, spot_checks (the
    section 5.4 points, always held back and evaluated with full simulation)."""
    s = dict(((plan.get("design") or {}).get("surrogate")) or {})
    methods = plan.get("methods") or {}
    pars = list(parameters or s.get("parameters") or [p for p, m in methods.items() if m == "surrogate-model"])
    if not pars:
        raise EmulatorError("emulator.parameters", "no surrogate-model parameter in the plan")
    cpar = {p["name"]: p for p in contract.get("parameters", [])}
    bounds = {}
    for p in pars:
        sb = (cpar.get(p) or {}).get("sampling_bounds")
        if not sb:
            raise EmulatorError("emulator.bounds", f"parameter {p}: no sampling bounds for the design box")
        bounds[p] = [float(sb[0]), float(sb[1])]
    theta_ref = {q: 0.5 * sum(v["sampling_bounds"]) for q, v in cpar.items()
                 if v.get("role") == "theta" and v.get("sampling_bounds")}
    mode = s.get("mode", "interpolate")
    if mode not in MODES:
        raise EmulatorError("emulator.mode", f"mode {mode!r}: one of {MODES}")
    return {"parameters": pars, "bounds": bounds, "n_design": int(s.get("n_design", 24)),
            "held_back": int(s.get("held_back", 8)), "seed": int(s.get("seed", 20261201)),
            "mode": mode, "spot_checks": list(s.get("spot_checks") or []), "theta_ref": theta_ref}


def design(cfg: dict) -> dict:
    """The Sobol design points and the P6 held-back set of the settings (generated by calib_design.py's engine)."""
    from core.calibration import design as D
    n = cfg["n_design"] + cfg["held_back"]
    return D.design_points(cfg["bounds"], n, cfg["seed"], cfg["held_back"], cfg["spot_checks"])


def _names(contract, names):
    if names is not None:
        return list(names)
    from core.calibration import linear
    return [o["name"] for o in linear.calibration_observables(contract)]


def common_seeds(evaluator) -> dict:
    """The theta scan's common random numbers (section 6.6): the evaluator's nominal seed."""
    return {"nominal": (getattr(evaluator, "seeds", None) or {}).get("nominal")}


def training_set(evaluator, contract: dict, plan: dict, parameters=None, names=None) -> dict:
    """The surrogate's training set (D80): the training design points evaluated through ask/tell with the scan's
    common random numbers, the other parameters at theta_ref; then the fitted surrogate."""
    cfg = settings(contract, plan, parameters)
    pts = design(cfg)
    nm = _names(contract, names)
    st = new_state(pts["training"], "training", cfg["theta_ref"], common_seeds(evaluator), nm)
    run = drive(evaluator, st)
    if run["status"] != "ok":
        return {"status": "incomplete", "reason": "training evaluations outstanding", **run}
    sur = surrogate_from_state(st, cfg)
    return {"status": "ok", "state": st, "surrogate": sur, "design": pts, "settings": cfg}


# ------------------------------------------------------------------ P6 (section 8.2 note 4)
def bonferroni_z(M: int, alpha: float = ALPHA_P6) -> float:
    """z_{1 - alpha / (2M)}, two-sided Bonferroni (D53)."""
    return float(stats.norm.ppf(1.0 - alpha / (2.0 * M)))


def generalized_chi2_sf(t: float, lam) -> float:
    """P(sum_i lam_i X_i > t), X_i independent chi2_1 (Imhof 1961, by numerical integration); lam >= 0."""
    from scipy import integrate
    lam = np.asarray(lam, float)
    lam = lam[lam > 1e-12 * max(float(lam.max(initial=0.0)), 1e-300)]
    if lam.size == 0:
        return 1.0 if t > 0 else 0.0

    def f(u):
        th = 0.5 * float(np.sum(np.arctan(lam * u))) - 0.5 * t * u
        rho = float(np.prod((1.0 + (lam * u) ** 2) ** 0.25))
        return np.sin(th) / (u * rho)
    v, _ = integrate.quad(f, 0.0, np.inf, limit=500)
    return float(min(max(0.5 + v / np.pi, 0.0), 1.0))


def joint_delta_covariance(fulls: list, design_results: list, weights, k: int, paired: bool = True) -> np.ndarray:
    """The (Hk, Hk) MC covariance of surrogate - full simulation over all H held-out points, the B -> infinity limit of
    the event bootstrap: held-out points share events through common random numbers, and every surrogate prediction
    draws on the same design-point runs, so the differences are correlated across points (WP-G calibration of row
    2004, 2026-11-12). weights (H, J): the surrogate's w_j at each held-out point. A run whose event count differs
    between points contributes within each point only (no cross-point term)."""
    W = np.atleast_2d(np.asarray(weights, float))
    H = len(fulls)
    fi = [_influence(f, k) for f in fulls]
    di = [_influence(r, k) for r in design_results]
    if any(not x for x in fi) or any(not x for x in di):
        raise EmulatorError("p6.no_influence", "the joint covariance needs the evaluator's per-event contributions")
    C = np.zeros((H * k, H * k))

    def add(blocks):                              # blocks: list over h of (N_h, k) contributions of one source
        if len({b.shape[0] for b in blocks}) == 1:
            M = np.concatenate(blocks, axis=1)
            C[:] += M.T @ M
        else:
            for h, b in enumerate(blocks):
                s = slice(h * k, (h + 1) * k)
                C[s, s] += b.T @ b
    for run in fi[0]:
        sur = [sum(W[h, j] * di[j][run] for j in range(len(di))) for h in range(H)]
        full = [fi[h][run] for h in range(H)]
        if paired:
            add([s - f for s, f in zip(sur, full)])
        else:
            add(full)
            add(sur)
    return C


def p6(delta_m, cov_delta, v_emu, v_data, alpha: float = ALPHA_P6, factor: float = DATA_FACTOR,
       points=None, names=None, cov_joint=None, independent_points: bool = False) -> dict:
    """P6 on H held-out points and k observables: delta_m (H, k) = surrogate - full simulation; cov_delta (H, k, k) the
    MC covariance of the difference (sigma_Delta its root diagonal, by bootstrap); v_emu (H, k, k); v_data (k,) or
    (H, k) the V^unc_data diagonal. |Delta m| part always; the pull chi2 (with cov_delta + V_emu) only for H >= 30.
    The pull statistic is the sum over points of the per-point chi2; its reference is the exact null distribution
    under the joint covariance cov_joint (Hk, Hk) of the differences (a weighted sum of chi2_1, generalized_chi2_sf),
    because held-out points are correlated (common random numbers, shared design-point runs): the plain chi2 reference
    is valid only for independent_points. Without either, the pull part is incomplete."""
    dm = np.atleast_2d(np.asarray(delta_m, float))
    H, k = dm.shape
    if H == 0 or k == 0:
        raise EmulatorError("p6.no_held_back", "P6 needs held-out design points")
    try:
        cd = np.asarray(cov_delta, float).reshape(H, k, k)
        ve = np.asarray(v_emu, float).reshape(H, k, k)
        vd = np.broadcast_to(np.asarray(v_data, float), (H, k))
    except ValueError as exc:
        raise EmulatorError("p6.input", f"P6 input shapes: {exc}") from None
    if not (np.all(np.isfinite(dm)) and np.all(np.isfinite(cd)) and np.all(np.isfinite(ve)) and
            np.all(np.isfinite(vd))):
        raise EmulatorError("p6.input", "non-finite P6 input")
    M = H * k
    z = bonferroni_z(M, alpha)
    sig = np.sqrt(np.clip(np.einsum("hkk->hk", cd), 0.0, None))
    bound = factor * np.sqrt(np.clip(vd, 0.0, None)) + z * sig
    with np.errstate(divide="ignore", invalid="ignore"):
        excess = np.where(bound > 0, np.abs(dm) / bound, np.where(dm == 0, 0.0, np.inf))
    bad = np.abs(dm) > bound
    nm = list(names) if names is not None else [f"o{i}" for i in range(k)]
    worst = np.unravel_index(int(np.argmax(excess)), (H, k))
    findings = []
    if bad.any():
        h, j = map(int, np.argwhere(bad)[0])
        findings.append({"code": "p6.delta_m", "message": f"{int(bad.sum())} of {M} |Delta m| exceed 0.3 sqrt(V_data) "
                         f"+ z sigma_Delta (z = {z:.3f}); first {nm[j]} at held-out point {h}"
                         f"{'' if points is None else ' ' + str(points[h])}: surrogate model not accurate enough "
                         "(remedy: plan; more design points or another surrogate)"})
    parts: dict[str, Any] = {"delta_m": {"status": "failed" if bad.any() else "passed", "z": z, "M": M,
                                         "n_exceeding": int(bad.sum()), "max_ratio": float(excess.max()),
                                         "worst": {"point": int(worst[0]), "observable": nm[int(worst[1])]}}}
    if H >= MIN_PULL_POINTS:
        chi2, dof = 0.0, 0
        for h in range(H):
            C = 0.5 * (cd[h] + cd[h].T) + 0.5 * (ve[h] + ve[h].T)
            Ci = np.linalg.pinv(C, rcond=1e-12, hermitian=True)
            chi2 += float(dm[h] @ Ci @ dm[h])
            dof += int(np.linalg.matrix_rank(C, tol=1e-12 * max(float(np.abs(C).max()), 1e-300), hermitian=True))
        ref = None
        if cov_joint is not None:
            try:
                Cj = np.asarray(cov_joint, float).reshape(H * k, H * k)
            except ValueError as exc:
                raise EmulatorError("p6.input", f"cov_joint shape: {exc}") from None
            Cj = 0.5 * (Cj + Cj.T)
            B = np.zeros_like(Cj)
            for h in range(H):
                s = slice(h * k, (h + 1) * k)
                Cj[s, s] += 0.5 * (ve[h] + ve[h].T)          # V_emu per point (its cross-point part is not modelled)
                B[s, s] = Cj[s, s]
            wb, Vb = np.linalg.eigh(B)
            Bh = (Vb * np.where(wb > 1e-12 * max(float(wb.max()), 1e-300), wb, np.inf) ** -0.5) @ Vb.T
            lam = np.clip(np.linalg.eigvalsh(Bh @ Cj @ Bh), 0.0, None)
            p, ref = generalized_chi2_sf(chi2, lam), {"reference": "generalized chi2 under the joint covariance",
                                                      "lambda_max": float(lam.max()), "lambda_sum": float(lam.sum())}
        elif independent_points:
            p, ref = (float(stats.chi2.sf(chi2, dof)) if dof else 1.0), {"reference": "chi2 (independent points)"}
        else:
            parts["pull_chi2"] = {"status": "incomplete", "chi2": chi2, "dof": dof, "reason": "the held-out points' "
                                  "cross-point covariance is not given (cov_joint) and independence is not declared: "
                                  "the chi2 reference would be invalid"}
            p = None
        if p is not None:
            ok = p >= alpha
            parts["pull_chi2"] = {"status": "passed" if ok else "failed", "chi2": chi2, "dof": dof, "p_value": p,
                                  "alpha": alpha, "tail": "upper", **(ref or {})}
        if p is not None and not ok:
            findings.append({"code": "p6.pull_chi2", "message": f"pull chi2 = {chi2:.1f} on {dof} (p = {p:.2g} < "
                             f"{alpha}): the surrogate's errors exceed sigma_Delta and V_emu (remedy: plan)"})
    else:
        parts["pull_chi2"] = {"status": "not-executed", "reason": f"{H} < {MIN_PULL_POINTS} held-out points: only "
                              "the |Delta m| part is decided (section 8.1; not incomplete)"}
    incomplete = any(v.get("status") == "incomplete" for v in parts.values())
    status = "failed" if findings else ("incomplete" if incomplete else "passed")
    return {"gate": "P6", "status": status, "parts": parts, "findings": findings,
            "alpha": alpha, "n_held_out": H, "n_observables": k, "remedy": "plan" if findings else None,
            "flags": ["provisional-thresholds"]}


def _same_point(a: dict, b: dict, pars) -> bool:
    try:
        return all(abs(float(a[p]) - float(b[p])) <= 1e-12 * max(1.0, abs(float(b[p]))) for p in pars)
    except (KeyError, TypeError, ValueError):
        return False


def check_spot_checks(held_back: list, required: list, parameters) -> None:
    """The section 5.4 spot-check points are mandatory among P6's held-out points (section 6.4, 8.1)."""
    missing = [r for r in required if not any(_same_point(h, r, parameters) for h in held_back)]
    if missing:
        raise EmulatorError("p6.spot_checks_missing", f"the spot-check points {missing} of section 5.4 are not among "
                            "the held-out points of P6 (evaluated with full simulation; they cannot be omitted)")


def extreme_points(bounds: dict, parameter: str, theta_ref: dict | None = None) -> list[dict]:
    """The two extreme points of `parameter` within its prior (the k_B spot checks of section 5.4), the other
    surrogate parameters at the box centre (or theta_ref)."""
    centre = {p: 0.5 * (lo + hi) for p, (lo, hi) in bounds.items()}
    centre.update({p: v for p, v in (theta_ref or {}).items() if p in bounds})
    return [{**centre, parameter: bounds[parameter][0]}, {**centre, parameter: bounds[parameter][1]}]


def _influence(result: dict, k: int) -> dict:
    """Per run, the (N_run, k) matrix of per-event contributions c_ik (the evaluator's `influence`)."""
    out = {}
    for run, cols in (result.get("influence") or {}).items():
        n = len(next(iter(cols.values()))[0])
        M = np.zeros((n, k))
        for j, (col, _w) in cols.items():
            M[:, j] = col
        out[run] = M
    return out


def delta_covariance(full: dict, design_results: list, w: np.ndarray, k: int, paired: bool = True) -> np.ndarray:
    """The MC covariance of surrogate - full simulation at one point, the B -> infinity limit of the event bootstrap
    (the same convention as P5's ESS item): with common random numbers the events are paired, so the per-event
    contribution of the difference is sum_j w_j c_i(j) - c_i(full); with independent seeds the two add."""
    fi = _influence(full, k)
    di = [_influence(r, k) for r in design_results]
    if not fi or any(not d for d in di):
        raise EmulatorError("p6.no_influence", "sigma_Delta needs the evaluator's per-event contributions; give "
                            "cov_delta (or bootstrap replicas of the difference) instead")
    C = np.zeros((k, k))
    for run, Mf in fi.items():
        Ms = sum(wj * d[run] for wj, d in zip(w, di))
        if paired:
            D = Ms - Mf
            C += D.T @ D
        else:
            C += Mf.T @ Mf + Ms.T @ Ms
    return C


def cov_from_replicas(replicas) -> np.ndarray:
    """sigma_Delta's covariance from bootstrap replicas of the difference (B, k)."""
    R = np.atleast_2d(np.asarray(replicas, float))
    if R.shape[0] < 2:
        raise EmulatorError("p6.replicas", "at least two bootstrap replicas")
    return np.atleast_2d(np.cov(R, rowvar=False))


def v_data_unc(contract: dict, result: dict) -> np.ndarray:
    """V^unc_data,kk = per-event variance / exposure of each observable's sample (as linear.design)."""
    from core.calibration import linear
    obs = {o["name"]: o for o in contract.get("observables", [])}
    exposure = contract.get("exposure") or {}
    n = np.array([linear._exposure(exposure, obs[nm], result["runs"][j]) for j, nm in enumerate(result["names"])],
                 float)
    return np.diag(np.asarray(result["s2"], float)) / n


def p6_from_evaluator(evaluator, contract: dict, plan: dict, parameters=None, names=None, trained=None,
                      required_spot_checks=None) -> dict:
    """P6 on the plan's held-back points: each evaluated with full simulation through ask/tell (the scan's common
    random numbers), compared with the surrogate trained on the training points. required_spot_checks: the section 5.4
    points the caller derives (e.g. extreme_points for k_B); missing ones are rejected."""
    tr = trained or training_set(evaluator, contract, plan, parameters, names)
    if tr["status"] != "ok":
        return {"gate": "P6", **{k: v for k, v in tr.items() if k != "surrogate"}}
    sur, cfg = tr["surrogate"], tr["settings"]
    held = tr["design"]["held_back"]
    check_spot_checks(held, list(required_spot_checks or []) + cfg["spot_checks"], sur.parameters)
    st = new_state(held, "held-back", cfg["theta_ref"], common_seeds(evaluator), sur.names)
    run = drive(evaluator, st)
    if run["status"] != "ok":
        return {"gate": "P6", "status": "incomplete", "reason": "held-back evaluations outstanding", **run}
    raws = [e["_raw"] for e in tr["state"]["entries"]]
    k = len(sur.names)
    dms, cds, ves, vds, ws, fulls = [], [], [], [], [], []
    for e in st["entries"]:
        full = e["_raw"]
        pr = sur.predict(e["point"])
        dms.append(pr["pred"] - np.asarray(full["pred"], float))
        cds.append(delta_covariance(full, raws, pr["weights"], k))
        ves.append(pr["V_emu"])
        vds.append(v_data_unc(contract, full))
        ws.append(pr["weights"])
        fulls.append(full)
    cj = joint_delta_covariance(fulls, raws, np.array(ws), k) if len(held) >= MIN_PULL_POINTS else None
    out = p6(np.array(dms), np.array(cds), np.array(ves), np.array(vds), points=held, names=sur.names, cov_joint=cj)
    out.update({"surrogate": {"parameters": sur.parameters, "mode": sur.mode, "trend": sur.trend,
                              "length": sur.length.tolist(), "nugget": sur.nugget, "n_training": len(sur.points),
                              "domain": sur.domain()},
                "held_back": held, "sigma_delta": "event bootstrap, B -> infinity limit (paired events, common "
                "random numbers)"})
    return out


def feasibility(evaluator, contract: dict, plan: dict, parameter: str) -> dict:
    """The surrogate-model tier of section 3.6 step 2 for one parameter (the others at theta_ref): feasible when P6
    passes (calib_design.py final methods)."""
    if not hasattr(evaluator, "ask"):
        return {"status": "incomplete", "feasible": None, "reason": "the evaluator has no ask/tell"}
    methods = dict(getattr(evaluator, "methods", {}) or {})
    evaluator.methods = {**methods, parameter: "surrogate-model"}
    try:
        r = p6_from_evaluator(evaluator, contract, plan, parameters=[parameter])
    except EmulatorError as exc:
        return {"status": "rejected", "feasible": False, "reason": f"{exc.code}: {exc}"}
    finally:
        evaluator.methods = methods
    return {"status": r["status"], "feasible": r["status"] == "passed", "P6": r}


# ------------------------------------------------------------------ G8 with surrogate pseudo-data (A12, section 19-5)
def surrogate_pseudo_data(center, v_data, n_sets: int, seed) -> np.ndarray:
    """The bulk of a G8 ensemble for resimulation-level parameters (A12): n_sets Gaussian summary vectors around the
    surrogate's prediction at the injection point with the data covariance (Philox keyed by the seed). The
    surrogate's error at the point is a fixed shift, gated by the full-simulation spot check (no V_emu draw)."""
    key = [int(x) for x in seed] if isinstance(seed, (list, tuple)) else [int(seed)]
    rng = np.random.Generator(np.random.Philox(np.random.SeedSequence(key)))
    c = np.asarray(center, float)
    V = _psd(np.atleast_2d(np.asarray(v_data, float)))
    lam, U = np.linalg.eigh(V)
    L = U * np.sqrt(np.clip(lam, 0.0, None))
    return c + rng.standard_normal((int(n_sets), len(c))) @ L.T


def _seed_values(seeds) -> set:
    out: set = set()
    for s in seeds:
        if isinstance(s, dict):
            out |= {repr(v) for v in s.values() if v is not None}
        elif s is not None:
            out.add(repr(s))
    return out


def spot_check_plan(injection_points: list, training_state: dict, seeds: list, base_theta: dict | None = None,
                    names=None, intervals=None, training_intervals=None) -> dict:
    """The full-simulation spot check of G8 at the section 8.4 injection points (A12): one evaluation per point with
    its own seeds, which must be independent of the surrogate's training set (no seed value shared with any training
    evaluation; with Geant4 event intervals [first, last), none overlapping a training interval). Returns its ask/tell
    state (purpose g8-spot-check)."""
    _check_state(training_state)
    if len(seeds) != len(injection_points):
        raise EmulatorError("g8.spot_check_seeds", "one seed block per injection point")
    trained = _seed_values(e.get("seeds") for e in training_state["entries"])
    shared = [s for s in seeds if _seed_values([s]) & trained]
    if shared:
        raise EmulatorError("g8.spot_check_not_independent", f"spot-check seeds {shared} are used by the surrogate's "
                            "training set (A12: independent seeds)")
    if len(_seed_values(seeds)) < len(seeds):
        raise EmulatorError("g8.spot_check_not_independent", "two spot checks share a seed")
    for a in intervals or []:
        for b in training_intervals or []:
            if a[0] < b[1] and b[0] < a[1]:
                raise EmulatorError("g8.spot_check_not_independent", f"event interval {a} overlaps the training "
                                    f"interval {b}")
    st = new_state(injection_points, "g8-spot-check", base_theta, None, names)
    for e, s in zip(st["entries"], seeds):
        e["seeds"] = dict(s) if isinstance(s, dict) else {"nominal": s}
    return st


def spot_check_record(state: dict, surrogate, contract: dict | None = None, v_data=None, predict=None) -> dict:
    """The spot check's comparison at each injection point: Delta m = surrogate - full simulation, its MC covariance
    (independent seeds: V_MC of the full simulation plus the surrogate's interpolated V_MC) and V_emu. `predict`
    (point -> {pred, V_MC, V_emu}; default the surrogate with its training values) lets an evaluator combine inner
    methods (section 6.5). Decision (A16 (i)): the spot check passes when its P6-form statistics pass P6's rule (the
    |Delta m| bound with the Bonferroni z, and the pull chi2 under its reference when there are >= 30 points); its
    status is P6's."""
    _check_state(state)
    if not complete(state):
        return {"gate": "G8-spot-check", "status": "incomplete",
                "outstanding": [e["run_id"] for e in state["entries"] if e["status"] != "done"]}
    pred_fn = predict or surrogate.predict
    dms, cds, ves, vds, rows = [], [], [], [], []
    for e in state["entries"]:
        full = e.get("_raw") or e["result"]
        pr = pred_fn(e["point"])
        dm = np.asarray(pr["pred"], float) - np.asarray(full["pred"], float)
        cd = np.asarray(full["V_MC"], float) + np.asarray(pr["V_MC"], float)
        if v_data is not None:
            vd = np.asarray(v_data, float)
        elif contract is not None and "s2" in full:
            vd = v_data_unc(contract, full)
        else:
            raise EmulatorError("g8.spot_check_v_data", "V^unc_data: give v_data, or a contract and full results with "
                                "their per-event covariance")
        dms.append(dm)
        cds.append(cd)
        ves.append(np.asarray(pr["V_emu"], float))
        vds.append(vd)
        rows.append({"run_id": e["run_id"], "point": e["point"], "seeds": e["seeds"], "delta_m": dm,
                     "sigma_delta": np.sqrt(np.clip(np.diag(cd), 0.0, None)),
                     "sqrt_v_emu": np.sqrt(np.clip(np.diag(ves[-1]), 0.0, None))})
    form = p6(np.array(dms), np.array(cds), np.array(ves), np.array(vds), names=surrogate.names)
    return {"gate": "G8-spot-check", "status": form["status"], "points": rows,
            "reason": "the spot check is the gate for the surrogate's error (A12, section 19-5), decided by P6's rule "
            "(A16 (i))", "p6_form": form, "flags": ["provisional-thresholds"]}


# ------------------------------------------------------------------ CLI helper
def p6_from_input(doc: dict) -> dict:
    """P6 from arrays (calib_emulator.py p6 --input): {names?, v_data, points: [{theta?, delta_m | (surrogate, full),
    cov_delta | delta_replicas, V_emu?}], alpha?, required_spot_checks?, parameters?, cov_joint? (Hk x Hk, the
    differences' covariance across points) | independent_points? (true only for independently seeded points)}."""
    pts = doc.get("points")
    if not isinstance(pts, list) or not pts or not all(isinstance(p, dict) for p in pts):
        raise EmulatorError("p6.input", "points: a non-empty list of objects")
    if "v_data" not in doc:
        raise EmulatorError("p6.input", "v_data: the V^unc_data diagonal")
    dms, cds, ves = [], [], []
    try:
        for i, p in enumerate(pts):
            if "delta_m" in p:
                dm = np.atleast_1d(np.asarray(p["delta_m"], float))
            elif "surrogate" in p and "full" in p:
                dm = np.atleast_1d(np.asarray(p["surrogate"], float) - np.asarray(p["full"], float))
            else:
                raise EmulatorError("p6.input", f"point {i}: delta_m, or surrogate and full")
            k = dm.size
            if "cov_delta" in p:
                cd = np.asarray(p["cov_delta"], float).reshape(k, k)
            elif "delta_replicas" in p:
                cd = cov_from_replicas(p["delta_replicas"]).reshape(k, k)
            else:
                raise EmulatorError("p6.input", f"point {i}: cov_delta or delta_replicas (sigma_Delta by bootstrap)")
            dms.append(dm)
            cds.append(cd)
            ves.append(np.asarray(p.get("V_emu", np.zeros((k, k))), float).reshape(k, k))
    except (TypeError, ValueError) as exc:
        if isinstance(exc, EmulatorError):
            raise
        raise EmulatorError("p6.input", f"P6 input: {exc}") from None
    if len({d.size for d in dms}) != 1:
        raise EmulatorError("p6.input", "every point has the same observables")
    req = doc.get("required_spot_checks") or []
    if req:
        pars = doc.get("parameters") or sorted(req[0])
        check_spot_checks([p.get("theta") or {} for p in pts], req, pars)
    try:
        alpha = float(doc.get("alpha", ALPHA_P6))
    except (TypeError, ValueError):
        raise EmulatorError("p6.input", "alpha: a number") from None
    if not 0 < alpha < 1:
        raise EmulatorError("p6.input", "alpha in (0, 1)")
    cj = doc.get("cov_joint")
    ind = doc.get("independent_points", False)
    if not isinstance(ind, bool):
        raise EmulatorError("p6.input", "independent_points: true or false")
    return p6(np.array(dms), np.array(cds), np.array(ves), doc["v_data"], alpha=alpha, names=doc.get("names"),
              cov_joint=None if cj is None else np.asarray(cj, float), independent_points=ind)
