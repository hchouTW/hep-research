"""Propagation by the principal components of the joint posterior (Part B section 10.4; phase 2, WP6).
`calib_propagate.py` is its CLI; the conflict rules over packages are `deps.py`'s (calib_deps).

Export: theta = theta-hat + G_xi xi + G_zeta (zeta - zeta-hat) + G_s (phi_s - phi_s0) / sigma_phi_s, xi ~ N(0, I),
G_zeta = Sigma_theta_zeta Sigma_zeta_zeta^-1 (one joint regression over zeta = (eta, phi_shared)), G_xi from the
eigendecomposition of Sigma_theta|zeta = Sigma_theta_theta - Sigma_theta_zeta Sigma_zeta_zeta^-1 Sigma_zeta_theta; all blocks
from Sigma_beta + Sigma_boot / w (w with eps-hat+); G_s the symmetric +-1 sigma refit responses of the shift-mode phi
(D52 (b)). Var theta = G_xi G_xi^T + G_zeta Sigma_zeta_zeta G_zeta^T + G_s G_s^T = Sigma_theta_theta + G_s G_s^T. nu is not
exported separately, nor theta and nu apart.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np
from scipy import linalg

from core.geometry import alignment
from core.geometry.numbers import GeometryError
from core.simulation import conditions

from . import chain, deps, design_g4sim


class PropagationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def export(theta_hat: np.ndarray, zeta_hat: np.ndarray, Sigma: np.ndarray, i_theta, i_zeta,
           boot_cov: np.ndarray | None = None, w: float = 1.0, G_s: np.ndarray | None = None,
           zeta_keys: list | None = None) -> dict:
    """The export of one result: `Sigma` over beta, `Sigma_boot` over the same beta (or None), indices of theta and of
    zeta = (eta, phi_shared) in beta; `zeta_keys` their global keys (data release hash, source of phi, map hash)."""
    S = np.array(Sigma, float, copy=True)
    if boot_cov is not None:
        S = S + np.asarray(boot_cov, float) / w
    it, iz = np.asarray(i_theta, dtype=int), np.asarray(i_zeta, dtype=int)       # an empty zeta stays an index
    Stt, Stz, Szz = S[np.ix_(it, it)], S[np.ix_(it, iz)], S[np.ix_(iz, iz)]
    Gz = Stz @ linalg.inv(Szz) if iz.size else np.zeros((it.size, 0))
    cond = Stt - Gz @ Stz.T
    lam, E = np.linalg.eigh(0.5 * (cond + cond.T))
    lam = np.clip(lam, 0.0, None)
    order = np.argsort(lam)[::-1]
    Gx = E[:, order] * np.sqrt(lam[order])
    Gs = np.zeros((it.size, 0)) if G_s is None else np.asarray(G_s, float)
    return {"theta_hat": np.asarray(theta_hat, float), "zeta_hat": np.asarray(zeta_hat, float), "G_xi": Gx,
            "G_zeta": Gz, "Sigma_zeta": 0.5 * (Szz + Szz.T), "G_s": Gs, "Sigma_theta": 0.5 * (Stt + Stt.T),
            "zeta_keys": list(zeta_keys or []), "label": "local-gaussian-constraint-summary"}


def variance(pkg: dict) -> np.ndarray:
    """Var theta implied by the package."""
    Gx, Gz, Sz, Gs = pkg["G_xi"], pkg["G_zeta"], pkg["Sigma_zeta"], pkg["G_s"]
    return Gx @ Gx.T + Gz @ Sz @ Gz.T + Gs @ Gs.T


def theta_of(pkg: dict, xi, zeta, phi_s=None) -> np.ndarray:
    """theta = theta-hat + G_xi xi + G_zeta (zeta - zeta-hat) + G_s phi_s (phi_s in unit-normal coordinates)."""
    th = pkg["theta_hat"] + pkg["G_xi"] @ np.asarray(xi, float)
    if pkg["G_zeta"].size:
        th = th + pkg["G_zeta"] @ (np.asarray(zeta, float) - pkg["zeta_hat"])
    if phi_s is not None and pkg["G_s"].size:
        th = th + pkg["G_s"] @ np.asarray(phi_s, float)
    return th


def downstream_constraint(pkg: dict) -> dict:
    """How a citer uses the package: xi ~ N(0, I); zeta constrained by the joint posterior N(zeta-hat, Sigma_zeta) of
    that version (not a newer version, not the prior N(0, 1), not separate marginals); the zeta prior is already in it
    and must not be multiplied in again (section 10.4)."""
    return {"xi": {"mean": np.zeros(pkg["G_xi"].shape[1]), "cov": np.eye(pkg["G_xi"].shape[1])},
            "zeta": {"mean": pkg["zeta_hat"], "cov": pkg["Sigma_zeta"], "keys": pkg["zeta_keys"]},
            "no_extra_zeta_prior": True}


def version(payload: dict) -> dict:
    """The version of the exported shared-nuisance summary: update_digest and version id (deps), never defined by the
    result hash (no content-hash cycle)."""
    return {"update_digest": deps.update_digest(payload), "version_id": deps.version_id(payload)}


def marginal_regressions(Sigma: np.ndarray, i_theta, i_eta, i_phi) -> np.ndarray:
    """The rejected construction (counterexample of section 10.4): separate regressions Sigma_theta_eta Sigma_eta_eta^-1 and
    Sigma_theta_phi Sigma_phi_phi^-1 instead of the single joint regression."""
    it, ie, ip = map(np.asarray, (i_theta, i_eta, i_phi))
    Ge = Sigma[np.ix_(it, ie)] @ linalg.inv(Sigma[np.ix_(ie, ie)])
    Gp = Sigma[np.ix_(it, ip)] @ linalg.inv(Sigma[np.ix_(ip, ip)])
    return np.concatenate([Ge, Gp], axis=1)


# ------------------------------------------------------------------ feeding back to g4sim (section 10.4, A21 19-g6)
# A calibration result is written back into a g4sim condition-snapshot/1 (per-channel conditions) or alignment-overlay/1
# (shifts and small rotations) at the fields its theta parameters are bound to (contract parameters[].bindings). Both
# S9 schemas leave source_of_facts optional, so the export writes it itself (accepted 2026-11-09): the key
# `calibration_result` holds the result's hash, effective grade, uses, flags and the stated use of the record (A21:
# "exported records state the effective grade and use"); each written pointer maps to "calibration-result:<hash>", the
# template's own entries stay for the values not written. calib_use.py checks it offline (use.check_export).
EXPORT_SCHEMAS = {"condition-snapshot/1": "condition-snapshot", "alignment-overlay/1": "alignment-overlay"}
SOURCE_KEY = "calibration_result"
SOURCE_PREFIX = "calibration-result:"


def _decimal_text(value: float) -> str:
    """A decimal string without an exponent (alignment-overlay/1 holds delta_mm and zyx_deg as decimal strings)."""
    if not np.isfinite(value):
        raise PropagationError("export.value", f"value {value!r} is not finite")
    text = format(Decimal(repr(float(value))), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def export_g4sim(template: dict, result: dict, contract: dict, use: str, values: dict | None = None) -> dict:
    """The g4sim record of a calibration result: `template` (the condition-snapshot/1 or alignment-overlay/1 the
    contract's bindings point into) with the theta-hat of every theta bound to it written at its pointer, and
    source_of_facts carrying the result's hash, effective grade, uses, flags and `use` (the use the record is exported
    for). `values` maps a parameter name to its value; default the result's `beta_hat`. Refuses (PropagationError) a
    result without its hash or with no grade (incomplete cannot be cited), a binding outside Table 2 or a pointer that
    does not resolve, a missing value, a template with no theta bound to it, and a use the result's grade and flags do
    not allow (section 10.2; calib_use.py export checks the written record again)."""
    kind = EXPORT_SCHEMAS.get(str(template.get("schema")))
    if kind is None:
        raise PropagationError("export.schema", f"exports are {sorted(EXPORT_SCHEMAS)}, not {template.get('schema')!r}")
    sha = result.get("result_sha256")
    if not deps.is_hash_reference(sha):
        raise PropagationError("export.no_hash", "the result has no result_sha256: an exported record cites the "
                               "result by its hash (section 10.4)")
    grade = result.get("grade") or {}
    if grade.get("effective_grade") not in ("failed", "projection", "calibrated-unvalidated", "validated-in-scope"):
        raise PropagationError("export.no_grade", "the result has no effective grade (incomplete results cannot be "
                               "cited, section 10.2 rule 0)")
    from . import use as use_mod                           # review F8: never write a use the result does not allow
    allowed = use_mod.allowed_uses(grade["effective_grade"], set(grade.get("flags") or ()))
    if use not in allowed:
        raise PropagationError("export.use", f"use {use!r} is not allowed for {grade['effective_grade']} with flags "
                               f"{sorted(grade.get('flags') or ())}; allowed {sorted(allowed)} (section 10.2)")
    values = result.get("beta_hat") if values is None else values
    if not isinstance(values, dict):
        raise PropagationError("export.values", "values (or the result's beta_hat) map parameter names to values")
    out = dict(template)
    written: dict[str, str] = {}
    for par in contract.get("parameters", []):
        if par.get("role") != "theta":
            continue
        for b in par.get("bindings") or []:
            if b.get("document") != kind:
                continue
            row, why = chain.binding_row(b)
            if row is None:
                raise PropagationError("export.binding", f"{par.get('name')!r} at {b.get('pointer')}: {why}")
            if par.get("name") not in values:
                raise PropagationError("export.values", f"no value for the theta {par.get('name')!r}")
            v = float(values[par["name"]])
            written_value = _decimal_text(v) if kind == "alignment-overlay" else v
            try:
                out = design_g4sim.pointer_set(out, b["pointer"], written_value)
            except design_g4sim.CheckError as exc:
                raise PropagationError("export.pointer", str(exc)) from None
            written[b["pointer"]] = par["name"]
    if not written:
        raise PropagationError("export.nothing", f"no theta of the contract is bound to the {kind}")
    sof = {k: v for k, v in (template.get("source_of_facts") or {}).items() if k != SOURCE_KEY}
    sof.update({p: SOURCE_PREFIX + str(sha) for p in sorted(written)})
    sof[SOURCE_KEY] = {"result_sha256": sha, "effective_grade": grade["effective_grade"],
                       "uses": sorted(grade.get("uses") or []), "flags": sorted(grade.get("flags") or []),
                       "variation_flags": sorted(grade.get("variation_flags") or []), "use": use,
                       "parameters": {p: written[p] for p in sorted(written)}}
    out["source_of_facts"] = sof
    try:
        if kind == "condition-snapshot":
            conditions.check_snapshot(out)
        else:
            alignment.check_overlay(out)
    except (conditions.ConditionError, GeometryError) as exc:
        raise PropagationError("export.record", f"{kind}: {exc}") from None
    return out
