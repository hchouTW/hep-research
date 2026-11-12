"""The efficiency-map term of the likelihood (Part B section 6.7 "Two efficiency map modes", D28; section 14
`calib_likelihood.py`; phase 3, WP-D).

In link space the predictor gains U(theta) phi_map with phi_map ~ N(0, I), profiled with theta in every minimization:
`likelihood.Likelihood` evaluates U at the theta of each step and adds (d U / d theta_i) phi_map to the Jacobian, so the
term is never held fixed within a minimization (holding it fixed left an errors-in-variables bias of 0.12-0.52 sigma
with independent seeds on the synthetic fixture).

Modes:
- `fixed`: the fixed-map mode, U constant (U = M V from digitizations at the replicas, or J B_map for observables linear
  in eps; `map_basis`). One phi_map of the map's native basis.
- `shared`: map varies with theta, shared seed with joint-pattern replicas (or the analytic covariance):
  U(theta) = sum_j w_j(theta) U_j, E_j = I, one phi_map shared by the scan.
- `independent`: independent seeds (allowed when the theta-noise item of P5 passes with Sigma_jl = 0): E_j selects
  design point j's block, phi = (phi_1, ..., phi_J), U(theta) = [w_1 U_1, ..., w_J U_J].
- Fallback without a pattern table (`fallback_covariance`): no profiled phi_map; the covariance U_j* U_j*^T of the design
  point j* nearest the reference point is added to V_G and held fixed in each minimization (section 7.3 fixed point);
  the plan records that this assumes full correlation between design points, and nothing is exported (section 10.4).

w_j(theta) and their theta derivatives are the surrogate model's (`emulator.Surrogate.weights`,
`weight_derivatives`); U_j are over `rows` of the link-space predictor (the observables the map affects; the caller
converts prediction-space replica differences to link space with the link's derivative at the nominal prediction).
"""
from __future__ import annotations

import numpy as np

MODES = ("fixed", "shared", "independent")


class MapTermError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class MapTerm:
    """U(theta) over the link rows `rows` of an n_link predictor; `surrogate` gives w_j(theta) (modes shared and
    independent); `theta_names` the layout's theta (and phi_P) order, for the derivatives."""

    def __init__(self, U_list, rows, n_link: int, mode: str = "fixed", surrogate=None, theta_names=()):
        if mode not in MODES:
            raise MapTermError("map_term.mode", f"mode {mode!r}: one of {MODES}")
        self.mode = mode
        self.U_list = [np.atleast_2d(np.asarray(u, float)) for u in U_list]
        self.rows = np.asarray(rows, int)
        self.n_link = int(n_link)
        self.surrogate = surrogate
        self.theta_names = list(theta_names)
        if not self.U_list or any(u.shape[0] != self.rows.size for u in self.U_list):
            raise MapTermError("map_term.shape", "every U_j has one row per affected link row")
        if mode == "fixed":
            if len(self.U_list) != 1 or surrogate is not None:
                raise MapTermError("map_term.fixed", "the fixed-map mode has one U and no surrogate weights")
        else:
            if surrogate is None:
                raise MapTermError("map_term.surrogate", f"mode {mode}: U(theta) needs the surrogate's weights")
            if len(self.U_list) != len(surrogate.points):
                raise MapTermError("map_term.points", f"{len(self.U_list)} U_j for {len(surrogate.points)} design "
                                   "points")
            if mode == "shared" and len({u.shape[1] for u in self.U_list}) != 1:
                raise MapTermError("map_term.shared", "shared phi_map: every U_j has the same columns (replicas r)")
            missing = [p for p in surrogate.parameters if p not in self.theta_names]
            if missing:
                raise MapTermError("map_term.parameters", f"surrogate parameters {missing} are not fit parameters")
        self._cols = [u.shape[1] for u in self.U_list]

    @property
    def n_phi(self) -> int:
        return self._cols[0] if self.mode in ("fixed", "shared") else int(sum(self._cols))

    def _full(self, blocks) -> np.ndarray:
        out = np.zeros((self.n_link, self.n_phi))
        out[self.rows] = blocks
        return out

    def _combine(self, w) -> np.ndarray:
        if self.mode == "shared":
            return np.sum([float(wj) * u for wj, u in zip(w, self.U_list)], axis=0)
        return np.hstack([float(wj) * u for wj, u in zip(w, self.U_list)])

    def U(self, theta: dict) -> np.ndarray:
        """U(theta) (n_link x n_phi)."""
        if self.mode == "fixed":
            return self._full(self.U_list[0])
        return self._full(self._combine(self.surrogate.weights(theta)))

    def derivatives(self, theta: dict) -> list:
        """d U / d theta_i for every name of theta_names (zero for parameters the surrogate does not hold)."""
        out = []
        for name in self.theta_names:
            if self.mode == "fixed" or name not in self.surrogate.parameters:
                out.append(np.zeros((self.n_link, self.n_phi)))
            else:
                dw, _ = self.surrogate.weight_derivatives(theta, name)
                out.append(self._full(self._combine(dw)))
        return out

    def covariance(self, theta: dict) -> np.ndarray:
        """U(theta) U(theta)^T over the affected rows (diagnostic; R_map, section 6.7)."""
        u = self.U(theta)[self.rows]
        return u @ u.T

    def record(self) -> dict:
        return {"mode": self.mode, "n_phi": self.n_phi, "rows": self.rows.tolist(), "columns": self._cols,
                "profiled": True}


def nearest_point(surrogate, theta: dict) -> int:
    """j* nearest theta among the surrogate's design points, in the unit cube of the design box (fallback)."""
    x = surrogate._x(theta)
    return int(np.argmin(np.sum((surrogate.X - x[None, :]) ** 2, axis=1)))


def fallback_covariance(U_list, surrogate, theta_ref: dict) -> dict:
    """The fallback of section 6.7: U_j* U_j*^T of the design point j* nearest theta_ref (g4sim's own replicas of map
    j*), added to V_G and held fixed in the minimization; no phi_map, nothing exported, full correlation assumed."""
    j = nearest_point(surrogate, theta_ref)
    U = np.atleast_2d(np.asarray(U_list[j], float))
    return {"point": j, "V_add": U @ U.T, "profiled": False, "exported": False,
            "record": "assumes full correlation of the map errors between design points (section 6.7 fallback)"}
