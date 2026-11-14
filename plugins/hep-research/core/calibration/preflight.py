"""A0, the pre-check of pipeline stage A0 (Part B sections 4.2, 5.1, 14; calib_contract.py preflight). Not a gate.

On the calibration data, with the smoothing model the contract declares for each acceptance threshold, decide whether
the data themselves can reach the threshold. The data come only through calib_data.py, which records the read as a fit
read with the contract draft as read channel (section 9.5). The summary written into the contract draft records only
which thresholds are unreachable, never a data value (section 5.1).

A threshold (contract `thresholds`, one entry per name):
    {"observables": [names, in the order of the control values], "control": [x_1, ...],
     "quantity": "max_relative_deviation_from_proportionality" | "max_relative_deviation_from_line",
     "threshold": 0.02, "smoothing_model": {"kind": "polynomial", "degree": 2}, "alpha": 0.05}
Decision (execution-log reading; Part B fixes no level): unreachable when the one-sided lower confidence limit, at
level 1 - alpha (default 0.05), of the quantity of the smoothed data exceeds the threshold. The uncertainty is the
residual scatter about the smoothing model (the sealed `observed` and `expected` components are never used, section
2.1), propagated by a parametric bootstrap with a fixed seed."""
from __future__ import annotations

import numpy as np

QUANTITIES = ("max_relative_deviation_from_proportionality", "max_relative_deviation_from_line")
B_DEFAULT = 2000
SEED = 20261110


class PreflightError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _design(x, degree):
    return np.vander(x, degree + 1, increasing=True)


def quantity(x: np.ndarray, y: np.ndarray, kind: str, degree: int, grid: int = 201) -> float:
    """The declared quantity of the smoothed data: max over the control range of |s(x) / L(x) - 1|, s the least-squares
    polynomial of the declared degree, L the least-squares line (through the origin for 'proportionality')."""
    X = _design(x, degree)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    g = np.linspace(x.min(), x.max(), grid)
    s = _design(g, degree) @ coef
    if kind == "max_relative_deviation_from_proportionality":
        b = float(x @ y / (x @ x))
        line = b * g
    else:
        a1, b1 = np.linalg.lstsq(_design(x, 1), y, rcond=None)[0]
        line = a1 + b1 * g
    return float(np.max(np.abs(s / line - 1.0)))


def check_threshold(name: str, t: dict, values: dict, B: int = B_DEFAULT, seed: int = SEED) -> dict:
    for k in ("observables", "control", "quantity", "threshold", "smoothing_model"):
        if k not in t:
            raise PreflightError("a0.declaration", f"threshold {name}: `{k}` is not declared")
    if t["quantity"] not in QUANTITIES:
        raise PreflightError("a0.declaration", f"threshold {name}: quantity {t['quantity']!r} is not one of {QUANTITIES}")
    sm = t["smoothing_model"]
    if sm.get("kind") != "polynomial":
        raise PreflightError("a0.declaration", f"threshold {name}: smoothing model {sm.get('kind')!r} (phase 1 has "
                             "polynomials)")
    deg = int(sm.get("degree", 2))
    x = np.asarray(t["control"], dtype=float)
    missing = [o for o in t["observables"] if o not in values]
    if missing:
        raise PreflightError("a0.no_value", f"threshold {name}: no calibration value for {missing}")
    y = np.array([float(values[o]) for o in t["observables"]])
    n, p = len(x), deg + 1
    if n <= p:
        raise PreflightError("a0.declaration", f"threshold {name}: {n} points for a degree-{deg} smoothing model")
    X = _design(x, deg)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ coef
    sigma = float(np.sqrt(((y - fit) ** 2).sum() / (n - p)))
    q = quantity(x, y, t["quantity"], deg)
    rng = np.random.default_rng(seed)
    boot = np.array([quantity(x, fit + sigma * rng.standard_normal(n), t["quantity"], deg) for _ in range(B)])
    alpha = float(t.get("alpha", 0.05))
    lower = float(np.quantile(boot, alpha))
    reachable = lower <= float(t["threshold"])
    return {"threshold": name, "reachable": bool(reachable), "alpha": alpha, "n_points": n, "degree": deg,
            "_quantity": q, "_lower": lower}


def preflight(contract: dict, values: dict, B: int = B_DEFAULT) -> dict:
    """A0 over every declared threshold with a smoothing model. Returns the summary to write into the contract draft
    ({"unreachable_thresholds": [...]}, names only) and per-threshold decisions; the values behind them (quantity,
    lower limit) are kept out of the summary, and the script prints them only on request."""
    out, unreachable = [], []
    for name, t in sorted((contract.get("thresholds") or {}).items()):
        if not isinstance(t, dict) or "smoothing_model" not in t:
            continue
        r = check_threshold(name, t, values, B)
        out.append(r)
        if not r["reachable"]:
            unreachable.append(name)
    status = "ok"
    return {"status": status, "a0_summary": {"unreachable_thresholds": unreachable},
            "decisions": [{k: v for k, v in r.items() if not k.startswith("_")} for r in out],
            "findings": [{"code": "a0.unreachable", "threshold": n, "message": f"threshold {n} is not reachable on the "
                          "calibration data with the declared smoothing model"} for n in unreachable],
            "_detail": out}

