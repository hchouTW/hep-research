#!/usr/bin/env python3
"""Linear Hessian profiling (Hessian reweighting) of a published Hessian PDF set with new data (S12).

Purpose: the effect of new data on a Hessian set, its consistency with the set (the penalty term), the updated central
prediction and uncertainties, without refitting. See <plugin root>/skills/hep-statistics/references/pdf-fit-statistics.md.
Method (Paukkunen and Zurita, arXiv:1402.6623v3, Sec. 3, Eqs. 3.1-3.12; read 2026-10-23), linear version:
  D_ik = (y_i[S_k+] - y_i[S_k-]) / 2,   tbar_k = (t_k+ + t_k-) / 2 (tolerance; sqrt(Delta chi^2) for a fixed tolerance)
  B = D^T C^-1 D + diag(tbar_k^2),   a = D^T C^-1 (y[S_0] - y),   w_min = -B^-1 a              (Eqs. 3.5-3.7)
  penalty P = sum_k (tbar_k w_k,min)^2  (Eq. 3.8; P << Delta chi^2: consistent; P >~ Delta chi^2: tension)
  profiled prediction O_new = O[S_0] + sum_k D^O_k w_k,min                                   (Eqs. 3.2, 3.9)
  profiled uncertainty: new error sets along the eigenvectors of B with tolerance t^ (Eq. 3.12), so
  delta O_new = t^ sqrt(D^O^T B^-1 D^O), t^ = sqrt(Delta chi^2) of the original set (--tolerance)
The linearity check (this script's heuristic) compares each member's prediction with the linear model: the asymmetry
|(y[S_k+] + y[S_k-]) / 2 - y[S_0]| relative to |D_k| (0 for a linear dependence, and always 0 for a symmhessian set);
a large value warns that the linear approximation may not hold (their Sec. 3 gives a non-linear extension, not
implemented). With a dynamic tolerance the penalty is not interpreted and the profiled uncertainty is not given (the
Eq. 3.12 construction uses one tolerance).
Input JSON: {"set": name, "error_type": "hessian" (asymmetric pairs) | "symmhessian", "tolerance_delta_chi2": value
from the set's documentation, "members": [[y_i for each data point] for S_0, S_1+, S_1-, ...] (hessian) or
[S_0, S_1, ...] (symmhessian, S_k- taken as 2 S_0 - S_k+), "data": [...], "covariance": [[...]], "observables":
{name: [O for each member]} (optional), "dynamic_tolerance": [[t_k+, t_k-] ...] (optional)}.
Exit codes (core/status.py): 0 ok; 1 refused (not a Hessian set; an asymmetric set whose eigenvector-member count,
central excluded, is odd; a covariance that is not positive definite); 2 rejected (unreadable or inconsistent input).
Requires NumPy (core stack).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

SOURCE = "Paukkunen and Zurita, arXiv:1402.6623v3, Sec. 3, Eqs. 3.1-3.12 (read 2026-10-23)"


class ProfError(ValueError):
    def __init__(self, msg, status="rejected"):
        super().__init__(msg)
        self.status = status


def split_members(arr, error_type):
    """central y0 (n), plus and minus arrays (K x n)."""
    import numpy as np
    y0, rest = arr[0], arr[1:]
    if error_type == "hessian":
        if len(rest) % 2:
            raise ProfError(f"an asymmetric Hessian set has pairs of eigenvector members; {len(rest)} members after the "
                            "central one is odd (LHAPDF counts the central member: 1 + 2N in total)", status="refused")
        return y0, rest[0::2], rest[1::2]
    return y0, rest, 2 * y0[None, :] - rest


def profile(doc: dict) -> dict:
    import numpy as np
    et = doc.get("error_type")
    if et not in ("hessian", "symmhessian"):
        raise ProfError(f"error_type {et!r} is not a Hessian set (replica sets go to pdf_reweighting.py)",
                        status="refused")
    try:
        mem = np.asarray(doc["members"], dtype=float)
        y = np.asarray(doc["data"], dtype=float)
        c = np.asarray(doc["covariance"], dtype=float)
        tol = float(doc["tolerance_delta_chi2"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfError(f"input needs members, data, covariance, tolerance_delta_chi2: {exc}") from exc
    if mem.ndim != 2 or mem.shape[1] != y.size or c.shape != (y.size, y.size) or mem.shape[0] < 2:
        raise ProfError("members must be M x n (central first), data n, covariance n x n")
    if not (np.all(np.isfinite(mem)) and np.all(np.isfinite(y)) and np.all(np.isfinite(c))) or not (
            math.isfinite(tol) and tol > 0):
        raise ProfError("non-finite input or a non-positive tolerance")
    if not np.allclose(c, c.T, rtol=1e-12, atol=0):
        raise ProfError("the covariance is not symmetric")
    try:
        np.linalg.cholesky(c)
    except np.linalg.LinAlgError as exc:
        raise ProfError("the covariance is not positive definite", status="refused") from exc
    y0, yp, ym = split_members(mem, et)
    K = yp.shape[0]
    D = ((yp - ym) / 2.0).T  # n x K
    if doc.get("dynamic_tolerance") is not None:
        tt = np.asarray(doc["dynamic_tolerance"], dtype=float)
        if tt.shape != (K, 2) or not np.all(tt > 0):
            raise ProfError("dynamic_tolerance must be K pairs of positive [t+, t-]")
        tbar = tt.mean(axis=1)
    else:
        tbar = np.full(K, math.sqrt(tol))
    ci = np.linalg.inv(c)
    B = D.T @ ci @ D + np.diag(tbar ** 2)
    a = D.T @ ci @ (y0 - y)
    w = -np.linalg.solve(B, a)
    penalty = float(np.sum((tbar * w) ** 2))
    chi2_before = float((y0 - y) @ ci @ (y0 - y))
    ynew = y0 + D @ w
    chi2_after = float((ynew - y) @ ci @ (ynew - y))
    scale = np.maximum(np.abs(D.T), 1e-300)
    nonlin = np.abs((yp + ym) / 2.0 - y0[None, :]) / scale
    out = {"n_eigenvectors": int(K), "w_min": w.tolist(), "penalty_P": penalty, "tolerance_delta_chi2": tol,
           "consistency": ("not interpreted: with a dynamic tolerance the single-Delta chi^2 reading is lost "
                           "(Paukkunen and Zurita, Sec. 3); check that each z_k = tbar_k w_k stays within its tolerance"
                           if doc.get("dynamic_tolerance") is not None else
                           "P << Delta chi^2 (here P < 0.1 Delta chi^2, this script's convention): consistent with the set"
                           if penalty < 0.1 * tol else
                           "P comparable to or above Delta chi^2: tension with the set" if penalty >= tol else
                           "P below Delta chi^2"),
           "chi2_new_data_before": chi2_before, "chi2_new_data_after": chi2_after,
           "linearity_max_relative_asymmetry": float(np.max(nonlin)) if nonlin.size else 0.0}
    binv = np.linalg.inv(B)
    obs = {}
    for name, vals in (doc.get("observables") or {}).items():
        o = np.asarray(vals, dtype=float)
        if o.shape != (mem.shape[0],) or not np.all(np.isfinite(o)):
            raise ProfError(f"observable {name} needs one finite value per member")
        o0, op, om = split_members(o[:, None], et)
        dO = ((op - om) / 2.0)[:, 0]
        obs[name] = {"central_before": float(o0[0]), "central_after": float(o0[0] + dO @ w),
                     "symmetric_uncertainty_before": float(np.sqrt(np.sum(dO ** 2))),
                     "uncertainty_after": (None if doc.get("dynamic_tolerance") is not None else
                                           math.sqrt(tol) * float(np.sqrt(dO @ binv @ dO))),
                     "note": "before: the set's symmetric Hessian sum at its own tolerance; after: Eq. 3.12 with "
                             "t^ = sqrt(Delta chi^2)"}
    out["observables"] = obs
    return out


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="JSON input (see the module docstring)")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    base = {"status_label": a.status, "inputs": {"input": a.input}}
    try:
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ProfError(f"NumPy is needed: {exc}", status="missing-dependency") from exc
        try:
            doc = json.loads(Path(a.input).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProfError(f"cannot read {a.input}: {exc}") from exc
        if not isinstance(doc, dict):
            raise ProfError("the input must be a JSON object")
        out = profile(doc)
    except ProfError as exc:
        print(json.dumps({"status": exc.status, **base, "reason": str(exc)}, indent=1))
        return exit_code(exc.status)
    print(json.dumps({"status": "ok", **base, "method": SOURCE, "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
