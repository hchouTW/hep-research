#!/usr/bin/env python3
"""Bayesian reweighting of a Monte Carlo replica set of PDFs (or nPDFs, FFs) with new data (S12).

Purpose: update a published replica set with a new measurement without refitting, with the effective number of
replicas that says when a refit is needed. See <plugin root>/skills/hep-statistics/references/pdf-fit-statistics.md.
Method (sources read 2026-10-23):
  chi2_k = (d - t_k)^T C^-1 (d - t_k) for replica k (n data points, N replicas, covariance C supplied by the user)
  NNPDF weights   w_k proportional to (chi2_k)^((n - 1)/2) exp(-chi2_k / 2)  (Ball et al., arXiv:1012.0836v4, Eqs. 8-9)
  Giele-Keller    w_k proportional to exp(-chi2_k / 2)                       (Giele, Keller, arXiv:hep-ph/9803393v1)
  normalized so that sum_k w_k = N;  N_eff = exp( (1/N) sum_k w_k ln(N / w_k) )   (Ball et al. 1012.0836, Eq. 10)
The choice between the two weight forms is debated (Ball et al. 1012.0836 call the Giele-Keller form an error;
Paukkunen and Zurita, arXiv:1402.6623v3, Sec. 4, find a conclusive answer still to be given) and is recorded as an
alternative-method object;
both are always reported, the requested one is the headline. Reweighted mean of an observable: sum_k w_k O_k / N;
standard deviation likewise. Optional unweighted replica indices (a midpoint variant of 1108.1758 Sec. 3, Eq. 24). The Kish
effective sample size (sum w)^2 / sum w^2 used by `bayes_diagnostics.py reweight` is reported as well; it is a
different quantity from N_eff.
Hessian sets: replicas generated from a Hessian set (Watt and Thorne, arXiv:1205.4024v2) may be reweighted only when
flagged (input "origin": "hessian-generated" and --allow-hessian-replicas), and then only with Giele-Keller weights
and chi2 / Delta chi^2 ("tolerance_delta_chi2"; Paukkunen and Zurita, Sec. 5, Eq. 5.2); a Hessian set itself (central + eigenvectors) is refused (use
`hessian_profiling.py`).
Input JSON: {"set": name, "kind": "replicas", "origin": "native-replicas" | "hessian-generated", "predictions": [[t_k for
each data point] for each replica k], "data": [...], "covariance": [[...]], "observables": {name: [O_k ...]}
(optional)}; replica 0 must not be included (pass replicas 1..N).
Exit codes (core/status.py): 0 ok (with a warning when N_eff is below --min-neff); 1 refused (a Hessian set, Hessian
replicas without the flag, fewer replicas than --min-replicas, a covariance that is not positive definite); 2 rejected
(unreadable or inconsistent input, non-finite values). Requires NumPy (core stack).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

SOURCES = {"nnpdf": "Ball et al., arXiv:1012.0836v4, Eqs. 8-10 (read 2026-10-23)",
           "giele-keller": "Giele and Keller, arXiv:hep-ph/9803393v1 (read 2026-10-23)"}


class RwError(ValueError):
    def __init__(self, msg, status="rejected"):
        super().__init__(msg)
        self.status = status


def weights(chi2, n_data: int, form: str):
    import numpy as np
    chi2 = np.asarray(chi2, dtype=float)
    if form == "nnpdf" and n_data > 1:
        logw = 0.5 * (n_data - 1) * np.log(np.maximum(chi2, 1e-300)) - 0.5 * chi2
    else:
        logw = -0.5 * chi2
    logw -= logw.max()
    w = np.exp(logw)
    return w * len(w) / w.sum()


def neff(w) -> float:
    import numpy as np
    w = np.asarray(w, dtype=float)
    n = len(w)
    nz = w[w > 0]
    return float(math.exp(float(np.sum(nz * np.log(n / nz))) / n))


def unweight(w, n_out: int) -> list[int]:
    """Deterministic unweighting by the cumulative weight, sampled at the midpoints (j + 0.5)/N' (a variant of Ball et
    al. 1108.1758, Sec. 3, Eq. 24, which uses the right edges j/N')."""
    import numpy as np
    p = np.cumsum(np.asarray(w, dtype=float) / np.sum(w))
    targets = (np.arange(n_out) + 0.5) / n_out
    return [int(np.searchsorted(p, t)) for t in targets]


def run(doc: dict, form: str, min_replicas: int, min_neff: float | None, n_unweight: int | None,
        allow_hessian: bool = False) -> dict:
    import numpy as np
    if doc.get("kind") != "replicas":
        raise RwError("only replica sets are reweighted here; a Hessian set goes to hessian_profiling.py",
                      status="refused")
    origin = doc.get("origin")
    if origin not in ("native-replicas", "hessian-generated"):
        raise RwError('"origin" must be "native-replicas" or "hessian-generated"')
    if origin == "hessian-generated" and not allow_hessian:
        raise RwError("replicas generated from a Hessian set (Watt and Thorne) need --allow-hessian-replicas",
                      status="refused")
    tol = None
    if origin == "hessian-generated":
        if form != "giele-keller":
            raise RwError("replicas generated from a Hessian set are reweighted with Giele-Keller weights and chi2 / "
                          "Delta chi^2 (Paukkunen and Zurita, arXiv:1402.6623v3, Sec. 5, Eq. 5.2; NNPDF weights fail "
                          "there, their Sec. 6)", status="refused")
        tol = doc.get("tolerance_delta_chi2")
        if not isinstance(tol, (int, float)) or isinstance(tol, bool) or not (math.isfinite(tol) and tol > 0):
            raise RwError("Hessian-generated replicas need tolerance_delta_chi2 (the set's Delta chi^2)")
    try:
        t = np.asarray(doc["predictions"], dtype=float)
        d = np.asarray(doc["data"], dtype=float)
        c = np.asarray(doc["covariance"], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise RwError(f"input needs numeric predictions, data, covariance: {exc}") from exc
    if t.ndim != 2 or d.ndim != 1 or t.shape[1] != d.size or c.shape != (d.size, d.size):
        raise RwError("predictions must be N x n, data n, covariance n x n")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(d)) and np.all(np.isfinite(c))):
        raise RwError("non-finite values in the input")
    if t.shape[0] < min_replicas:
        raise RwError(f"{t.shape[0]} replicas are fewer than --min-replicas {min_replicas}", status="refused")
    if not np.allclose(c, c.T, rtol=1e-12, atol=0):
        raise RwError("the covariance is not symmetric")
    try:
        L = np.linalg.cholesky(c)
    except np.linalg.LinAlgError as exc:
        raise RwError("the covariance is not positive definite", status="refused") from exc
    r = np.linalg.solve(L, (d[None, :] - t).T)
    chi2 = np.sum(r * r, axis=0)
    n = d.size
    chi2_w = chi2 / tol if tol else chi2
    w_main = weights(chi2_w, n, form)
    other = "giele-keller" if form == "nnpdf" else "nnpdf"
    w_alt = weights(chi2_w, n, other)
    out = {"n_data": n, "n_replicas": int(t.shape[0]), "chi2": chi2.tolist(), "weight_form": form,
           "chi2_rescaled_by_delta_chi2": tol, "weights": w_main.tolist(), "N_eff": neff(w_main), "kish_ess": float(w_main.sum() ** 2 / np.sum(w_main ** 2)),
           "alternative_method": {"weight_form": other, "N_eff": neff(w_alt),
                                  "note": "the choice of weight form is debated; an alternative-method object"}}
    obs = doc.get("observables") or {}
    res = {}
    for name, vals in obs.items():
        o = np.asarray(vals, dtype=float)
        if o.shape != (t.shape[0],) or not np.all(np.isfinite(o)):
            raise RwError(f"observable {name} needs one finite value per replica")
        for key, w in (("reweighted", w_main), ("alternative", w_alt), ("prior", np.ones_like(w_main))):
            m = float(np.sum(w * o) / len(w))
            sd = float(math.sqrt(max(np.sum(w * (o - m) ** 2) / len(w), 0.0)))
            res.setdefault(name, {})[key] = {"mean": m, "std": sd}
    out["observables"] = res
    if n_unweight:
        out["unweighted_indices"] = unweight(w_main, n_unweight)
    warnings = []
    if min_neff is not None and out["N_eff"] < min_neff:
        warnings.append(f"N_eff = {out['N_eff']:.1f} is below {min_neff}: refit rather than reweight further")
    out["warnings"] = warnings
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
    ap.add_argument("--weights", choices=("nnpdf", "giele-keller"), required=True)
    ap.add_argument("--min-replicas", type=int, required=True, help="the user's minimum replica count")
    ap.add_argument("--min-neff", type=float, help="warn when N_eff falls below this (the user's threshold)")
    ap.add_argument("--unweight", type=int, help="also return this many unweighted replica indices")
    ap.add_argument("--allow-hessian-replicas", action="store_true", help="accept replicas generated from a Hessian set")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    base = {"status_label": a.status, "inputs": {k: v for k, v in vars(a).items() if k != "status"}}
    try:
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise RwError(f"NumPy is needed: {exc}", status="missing-dependency") from exc
        try:
            doc = json.loads(Path(a.input).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RwError(f"cannot read {a.input}: {exc}") from exc
        if not isinstance(doc, dict):
            raise RwError("the input must be a JSON object")
        if a.min_replicas < 2 or (a.unweight is not None and a.unweight < 1):
            raise RwError("--min-replicas must be >= 2 and --unweight >= 1")
        out = run(doc, a.weights, a.min_replicas, a.min_neff, a.unweight, a.allow_hessian_replicas)
    except RwError as exc:
        print(json.dumps({"status": exc.status, **base, "reason": str(exc)}, indent=1))
        return exit_code(exc.status)
    print(json.dumps({"status": "ok", **base, "method": SOURCES[a.weights], "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
