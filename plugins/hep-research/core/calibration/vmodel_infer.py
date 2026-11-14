"""The inference form of V_model (Part B section 5.4, table row "Inferred"; phase 5, gap V6 read by A25 (7)).

f, ell of the correlation kernel are fitted by the marginal likelihood (integrated over nu) with a weakly informative
prior, only as a separate version, validated only by `holdout`. The fixed form (declared f, ell) is never changed.

Readings (phase 5, recorded in the card's execution log; decision sheet V1-V5):

- V1 (the separate version): a `vmodel-version` record of its own, hashed (`version_sha256`, canonical JSON) and
  linked to the fixed-form declaration by `fixed_sha256` = canonical_sha256(contract.model_discrepancy). The contract
  is not edited; `linear.vmodel_columns(contract, names, version=...)` uses the record only when it is passed and its
  link matches. A contract with `form: inferred` and no version is refused (`linear.incomplete`).
- V2 (what is integrated): at the linearization point the caller supplies (theta_ref or the fixed-form theta-hat):
  link-space residual r, V = V_data + V_MC (+ V_emu), the theta (and free phi) columns `flat` integrated with a flat
  prior (restricted marginal likelihood, as A25 (6) for tau), the eta and profile-mode phi columns `nuisance` with
  their N(0, 1) constraints integrated exactly (covariance N N^T). nu is integrated exactly: Gaussian blocks only;
  Poisson and binomial blocks and N_d,c are refused (`vmodel_infer.incomplete`).
- V3 (priors): per inferred component `infer: {f_scale: s, length_bounds: [lo, hi]}`, both required: f ~ Half-Normal(s);
  ell log-uniform on the declared physical bounds (line 1028: lengths come from physics; the fit only moves within
  them). The posterior mode and its Laplace errors are taken in (log f, log ell).
- V4 (use): empirical Bayes. f-hat, ell-hat are fixed in the main fit; their Laplace errors are reported, not
  propagated into sigma_tot. The holdout requirement is the guard (lines 896, 1009).
- V5 (coverage): only squared-exponential kernel components carrying `infer` are fitted; C stays 0 between components
  (as in `linear.vmodel_columns`), matrix and model-ensemble components stay fixed and enter the covariance.

The conditional likelihood of nu is refused (`vmodel_infer.conditional`, line 1017: f nu is not identifiable and
f runs off to infinity).
"""
from __future__ import annotations

import copy
import math

import numpy as np
from scipy import linalg, optimize

from core.canonical import canonical_sha256
from core.calibration import likelihood as L

KIND = "vmodel-version"
INFERABLE = ("squared-exponential",)
OBJECTIVE = ("restricted marginal likelihood: nu integrated exactly (Gaussian blocks), eta and profile-mode phi "
             "integrated with their N(0, 1) constraints, theta and free phi with a flat prior")
_BIG = 1e300


class VmodelInferError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fixed_sha256(contract: dict) -> str:
    """The hash of the fixed-form declaration the inferred version is linked to."""
    return canonical_sha256(contract.get("model_discrepancy") or {})


def _refuse_unsupported(contract: dict, names: list[str], likelihood: str) -> None:
    if likelihood == "conditional":
        raise VmodelInferError("vmodel_infer.conditional", "f is not fitted by the conditional likelihood of nu: f nu "
                               "is not identifiable and f runs off to infinity (section 5.4); use the marginal "
                               "likelihood")
    if likelihood != "marginal":
        raise VmodelInferError("vmodel_infer.input", f"likelihood {likelihood!r}: only 'marginal'")
    md = contract.get("model_discrepancy") or {}
    if md.get("form") != "inferred":
        raise VmodelInferError("vmodel_infer.not_inferred", "the contract declares the fixed form of V_model; the "
                               "inferred form is opt-in (model_discrepancy.form: inferred)")
    mode = (contract.get("validation") or {}).get("mode")
    if mode != "holdout":
        raise VmodelInferError("vmodel_infer.not_holdout", f"validation mode {mode!r}: the inferred form of V_model "
                               "is validated only by holdout (section 5.4)")
    if (contract.get("validation") or {}).get("N_dc"):
        raise VmodelInferError("vmodel_infer.incomplete", "N_d,c declared: the projected marginal likelihood is not "
                               "implemented for the inferred form")
    by = {o["name"]: o for o in contract.get("observables", [])}
    for nm in names:
        o = by.get(nm)
        if o is None:
            raise VmodelInferError("vmodel_infer.input", f"observable {nm} is not in the contract")
        if o.get("block") != "gaussian":
            raise VmodelInferError("vmodel_infer.incomplete", f"observable {nm}: {o.get('block')} block; nu is "
                                   "integrated exactly only for Gaussian blocks")


def _components(contract: dict, names: list[str]) -> tuple[list[dict], list[dict]]:
    """(inferred, fixed) components; each inferred one with its indices, control values and prior."""
    comps = (contract.get("model_discrepancy") or {}).get("components") or []
    idx = {nm: i for i, nm in enumerate(names)}
    inferred, fixed = [], []
    for k, c in enumerate(comps):
        if "infer" not in c:
            fixed.append(c)
            continue
        if c.get("kind") not in INFERABLE:
            raise VmodelInferError("vmodel_infer.kind", f"component {k} ({c.get('kind')!r}): only the correlation "
                                   f"kernel's f and ell are inferred ({INFERABLE})")
        pr = c["infer"] or {}
        s, b = pr.get("f_scale"), pr.get("length_bounds")
        if not (isinstance(s, (int, float)) and s > 0 and isinstance(b, list) and len(b) == 2
                and 0 < float(b[0]) < float(b[1])):
            raise VmodelInferError("vmodel_infer.prior", f"component {k}: infer needs f_scale > 0 (the Half-Normal "
                                   "scale of f) and length_bounds [lo, hi] with 0 < lo < hi (declared from physics)")
        obs = [o for o in c.get("observables", []) if o in idx]
        if not obs:
            raise VmodelInferError("vmodel_infer.input", f"component {k}: none of its observables is fitted")
        inferred.append({"index": k, "observables": obs, "rows": np.array([idx[o] for o in obs]),
                         "z": np.array([float(c["control"][o]) for o in obs]), "f_scale": float(s),
                         "bounds": (float(b[0]), float(b[1])), "f0": float(c["f"]), "l0": float(c["length"])})
    if not inferred:
        raise VmodelInferError("vmodel_infer.no_component", "form inferred, but no component carries `infer`")
    return inferred, fixed


def kernel_block(z: np.ndarray, f: float, ell: float) -> np.ndarray:
    """One group's correlation kernel via `likelihood.kernel_component` (squared-exponential, one group)."""
    return L.kernel_component(z, np.zeros(len(z), dtype=int), {0: f}, {0: ell}, None)


class Objective:
    """-ln p(f, ell | r) up to a constant, in x = (log f_1, log ell_1, log f_2, ...)."""

    def __init__(self, residual, V, inferred, base, flat):
        self.r, self.V, self.inferred, self.flat = residual, V, inferred, flat
        self.base = V + base
        n = len(residual)
        self.n = n

    def covariance(self, x) -> np.ndarray:
        S = self.base.copy()
        for k, c in enumerate(self.inferred):
            f, ell = math.exp(x[2 * k]), math.exp(x[2 * k + 1])
            S[np.ix_(c["rows"], c["rows"])] += kernel_block(c["z"], f, ell)
        return S

    def nll(self, x) -> float:
        """-ln of the restricted marginal likelihood (theta integrated with a flat prior)."""
        try:
            cf = linalg.cho_factor(self.covariance(x), lower=True)
        except (linalg.LinAlgError, ValueError):
            return _BIG
        a = linalg.cho_solve(cf, self.r)
        logdet = 2.0 * float(np.log(np.diag(cf[0])).sum())
        quad = float(self.r @ a)
        X = self.flat
        if X.shape[1]:
            B = linalg.cho_solve(cf, X)
            M = X.T @ B
            try:
                cm = linalg.cho_factor(M, lower=True)
            except (linalg.LinAlgError, ValueError):
                return _BIG
            xa = X.T @ a
            quad -= float(xa @ linalg.cho_solve(cm, xa))
            logdet += 2.0 * float(np.log(np.diag(cm[0])).sum())
        return 0.5 * (logdet + quad)

    def __call__(self, x) -> float:
        v = self.nll(x)
        for k, c in enumerate(self.inferred):           # Half-Normal(f; s) in log f: + f^2 / 2 s^2 - log f
            f = math.exp(x[2 * k])
            v += 0.5 * (f / c["f_scale"]) ** 2 - x[2 * k]
        return v                                        # ell: log-uniform on its bounds (flat in log ell)

    def bounds(self) -> list:
        out = []
        for c in self.inferred:
            out += [(math.log(c["f_scale"] * 1e-6), math.log(c["f_scale"] * 1e2)),
                    (math.log(c["bounds"][0]), math.log(c["bounds"][1]))]
        return out


def _hessian(fun, x, h=1e-3) -> np.ndarray:
    n = len(x)
    H = np.zeros((n, n))
    f0 = fun(x)
    for i in range(n):
        for j in range(i, n):
            if i == j:
                e = np.zeros(n)
                e[i] = h
                H[i, i] = (fun(x + e) - 2 * f0 + fun(x - e)) / h ** 2
            else:
                ei, ej = np.zeros(n), np.zeros(n)
                ei[i], ej[j] = h, h
                H[i, j] = H[j, i] = (fun(x + ei + ej) - fun(x + ei - ej) - fun(x - ei + ej)
                                     + fun(x - ei - ej)) / (4 * h * h)
    return H


def _starts(inferred, bounds) -> list:
    x0 = []
    for k, c in enumerate(inferred):
        x0 += [float(np.clip(math.log(c["f0"]) if c["f0"] > 0 else math.log(c["f_scale"]), *bounds[2 * k])),
               float(np.clip(math.log(c["l0"]) if c["l0"] > 0 else 0.0, *bounds[2 * k + 1]))]
    out = [np.array(x0)]
    for q in (0.25, 0.5, 0.75):
        x = np.array(x0)
        for k in range(len(inferred)):
            lo, hi = bounds[2 * k + 1]
            x[2 * k + 1] = lo + q * (hi - lo)
        out.append(x)
    return out


def infer(contract: dict, names: list[str], residual, V, flat=None, nuisance=None, likelihood: str = "marginal",
          calibration_rows=None) -> dict:
    """The inferred V_model version: the posterior mode of (f, ell) of every component carrying `infer`, with Laplace
    errors in (log f, log ell), and the fitted components (contract order; f and length replaced). Inputs in link
    space at the caller's linearization point (V2): residual r (n), V (n x n), `flat` (n x p) columns integrated with
    a flat prior, `nuisance` (n x q) columns with N(0, 1) constraints."""
    _refuse_unsupported(contract, names, likelihood)
    r = np.asarray(residual, float)
    n = len(names)
    Vm = np.asarray(V, float)
    if r.shape != (n,) or Vm.shape != (n, n):
        raise VmodelInferError("vmodel_infer.input", f"residual must have {n} entries and V must be {n} x {n}")
    X = np.zeros((n, 0)) if flat is None else np.asarray(flat, float).reshape(n, -1)
    N = np.zeros((n, 0)) if nuisance is None else np.asarray(nuisance, float).reshape(n, -1)
    if not (np.isfinite(r).all() and np.isfinite(Vm).all() and np.isfinite(X).all() and np.isfinite(N).all()):
        raise VmodelInferError("vmodel_infer.input", "non-finite input")
    inferred, fixed = _components(contract, names)
    from core.calibration import linear      # noqa: PLC0415 (linear imports this module lazily)
    base = N @ N.T + linear.vmodel_matrix(fixed, names)
    posterior = Objective(r, Vm, inferred, base, X)
    bnds = posterior.bounds()
    best = None
    for x0 in _starts(inferred, bnds):
        res = optimize.minimize(posterior, x0, method="L-BFGS-B", bounds=bnds)
        if best is None or res.fun < best.fun:
            best = res
    assert best is not None
    x = np.asarray(best.x, float)
    if best.fun >= _BIG:
        raise VmodelInferError("vmodel_infer.singular", "the marginal covariance is not positive definite at any start")
    H = _hessian(posterior, x)
    try:
        cov = np.linalg.inv(H)
        laplace_ok = bool(np.all(np.linalg.eigvalsh(0.5 * (H + H.T)) > 0))
    except np.linalg.LinAlgError:
        cov, laplace_ok = np.full_like(H, np.nan), False
    md = contract.get("model_discrepancy") or {}
    fitted = copy.deepcopy(md.get("components") or [])
    est = []
    for k, c in enumerate(inferred):
        u, w = float(x[2 * k]), float(x[2 * k + 1])
        at = [name for name, val, (lo, hi) in (("f", u, bnds[2 * k]), ("length", w, bnds[2 * k + 1]))
              if min(val - lo, hi - val) < 1e-6]
        sd = [math.sqrt(cov[i, i]) if laplace_ok and cov[i, i] > 0 else None for i in (2 * k, 2 * k + 1)]
        f_hat, l_hat = math.exp(u), math.exp(w)
        fitted[c["index"]]["f"], fitted[c["index"]]["length"] = f_hat, l_hat
        est.append({"component": c["index"], "observables": c["observables"], "f": f_hat, "length": l_hat,
                    "sd_log_f": sd[0], "sd_log_length": sd[1], "f_declared": c["f0"], "length_declared": c["l0"],
                    "at_bound": at, "prior": {"f": f"half-normal(scale={c['f_scale']})",
                                              "length": f"log-uniform{list(c['bounds'])}"}})
    R_hat = posterior.covariance(x) - posterior.base
    rows = np.arange(n) if calibration_rows is None else np.asarray(calibration_rows, int)
    pc = L.principal_components(R_hat + linear.vmodel_matrix(fixed, names), rows, np.linalg.inv(Vm))
    body = {"kind": KIND, "form": "inferred", "fixed_sha256": fixed_sha256(contract), "names": list(names),
            "validation": "holdout", "objective": OBJECTIVE, "use": "empirical Bayes: fixed in the main fit, errors "
            "reported, not propagated", "estimates": est, "components": fitted,
            "neg_log_posterior": float(best.fun), "converged": bool(best.success), "laplace_ok": laplace_ok,
            "principal_components": {"K": pc["K"], "trace_fraction": pc["trace_fraction"],
                                     "tr_VGinv_Vperp": pc["tr_VGinv_Vperp"]},
            "inputs_sha256": canonical_sha256({"residual": r.tolist(), "V": Vm.tolist(), "flat": X.tolist(),
                                               "nuisance": N.tolist()})}
    return {**body, "version_sha256": canonical_sha256(body)}


def version_components(contract: dict, version: dict) -> list[dict]:
    """The fitted components of an inferred version, after checking that it is a version of this contract's
    declaration, that its hash holds, and that the contract validates by holdout."""
    if not isinstance(version, dict) or version.get("kind") != KIND or version.get("form") != "inferred":
        raise VmodelInferError("vmodel_infer.version", "not an inferred V_model version record")
    body = {k: v for k, v in version.items() if k != "version_sha256"}
    if canonical_sha256(body) != version.get("version_sha256"):
        raise VmodelInferError("vmodel_infer.version", "the version's hash does not match its content")
    if version.get("fixed_sha256") != fixed_sha256(contract):
        raise VmodelInferError("vmodel_infer.version_mismatch", "the version was inferred for another V_model "
                               "declaration (fixed_sha256 differs)")
    if (contract.get("model_discrepancy") or {}).get("form") != "inferred":
        raise VmodelInferError("vmodel_infer.not_inferred", "the contract declares the fixed form of V_model")
    if (contract.get("validation") or {}).get("mode") != "holdout" or version.get("validation") != "holdout":
        raise VmodelInferError("vmodel_infer.not_holdout", "the inferred form of V_model is validated only by holdout")
    return version["components"]
