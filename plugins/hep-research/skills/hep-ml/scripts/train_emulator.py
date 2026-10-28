#!/usr/bin/env python3
"""Train a Gaussian-process emulator of a vector-valued simulator output on a box of input parameters.

Purpose: stand in for an expensive deterministic simulation (one run per parameter point, a fixed vector of outputs,
for example a binned spectrum or ratio) inside a fit or a posterior, with an error estimate per prediction and a
declared training domain. The emulator is a surrogate: valid only where it was trained and validated; inputs
outside the training domain are flagged (DomainModel of check_surrogate_domain.py, stored in the model file).

What it does (train): maps every input to the unit cube of its declared box (a log axis for scale "log"), transforms
the outputs (natural log for transform "log", identity for "identity"), centres them and keeps the leading principal
components until the largest training reconstruction residual is at most --pca-tolerance; fits one Gaussian process per
component (zero mean on the standardized coefficient, Matern-5/2 kernel with one length scale per input, signal
variance and a small nugget for numerical jitter) by maximizing the log marginal likelihood (L-BFGS-B, analytic
gradient, --restarts seeded starts); fits a DomainModel on the training points in unit-cube coordinates; writes the
model file (format gp-pca-emulator/1: plain numbers, readable without this script) with self-check predictions at
reference points, and a run summary for write_ml_artifact.py (task surrogate). Leave-one-out residuals of each
component GP are reported (closed form). Prediction (predict, or the importable GaussianProcessEmulator) gives the
output, its 1-sigma error in output units, and per point the domain status (inside, sparse, outside).
Error model: per component the GP latent variance; in transformed units the variance of a bin is the sum over
components of (scale * basis)^2 * variance plus the mean-square training residual of the dropped components; for
transform "log" the output error is value * sigma (first order).

Input (--training-set JSON):
  {"features": [{"name": N, "min": lo, "max": hi, "scale": "log"|"linear", "unit": U?}, ...],
   "outputs": {"name": NAME, "count": m, "transform": "log"|"identity", "unit": U?, "labels": [m names]?},
   "points": [{N: value, ...}, ...], "values": [[m numbers], ...], "groups": [one label per point]?,
   "status": [artifact status labels of the training data], "context": {what the simulator was}?}
  "context" (any JSON object: simulator, version, fixed settings) is copied into the model unchanged. Every point
  inside its box, every value finite (positive for "log"); a point listed twice is refused.
Output: --out-dir/emulator-model.json and --out-dir/run_summary.json; a JSON summary on stdout.
  predict: --model M --points P.json (a list of points) -> JSON {predictions: [{values, sigma, domain}], ...}.
Exit codes: 0 done; 2 bad input (malformed JSON, a point outside its box, non-finite values, too few points);
  3 numerical failure (a covariance that cannot be factorized) or NumPy/SciPy missing.
Usage notes: NumPy and SciPy only (no PyTorch). Reproducible for a given input, seed and library version up to the
  last digits (threaded linear algebra can move the optimizer's stopping point; predictions then agree far below the
  emulator's error); a trained model file predicts identically wherever it is read. At least
  max(12, 2 x number of inputs) points; DomainModel needs at least 50 (it is skipped with fewer, and the summary says
  the domain is box-only). The model is validated on held-out simulator runs by its user, not by this script.
Run: python3 <plugin root>/skills/hep-ml/scripts/train_emulator.py train --training-set T.json --out-dir DIR
     python3 <plugin root>/skills/hep-ml/scripts/train_emulator.py predict --model DIR/emulator-model.json --points P.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True
for entry in (str(PLUGIN), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from core.status import add_status_argument  # noqa: E402

MODEL_FORMAT = "gp-pca-emulator/1"
KERNEL = "matern52-ard"
SCALES = ("linear", "log")
TRANSFORMS = ("log", "identity")
STATUSES = ("synthetic", "asimov", "observed", "preliminary", "unvalidated", "user-supplied")
LENGTH_BOUNDS = (1e-2, 1e2)      # length scales in unit-cube coordinates
SIGNAL_BOUNDS = (1e-4, 1e4)      # signal variance of a standardized coefficient
NUGGET_BOUNDS = (1e-12, 1e-1)    # nugget variance of a standardized coefficient (numerical jitter)
DOMAIN_MIN_POINTS = 50
SELF_CHECK_POINTS = 4
SQRT5 = math.sqrt(5.0)


class NumericalFailure(RuntimeError):
    """The calculation broke down on valid input (exit 3)."""


# ---------------------------------------------------------------------------------------------- coordinates
def unit_coordinates(points, features) -> list[list[float]]:
    """Each point (name -> value) in the unit cube of the declared boxes (log axis for scale log)."""
    rows = []
    for k, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError(f"points[{k}] must be an object name -> value")
        row = []
        for feat in features:
            value = point.get(feat["name"])
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"points[{k}].{feat['name']} must be a finite number")
            lo, hi = feat["min"], feat["max"]
            if feat["scale"] == "log":
                if value <= 0:
                    raise ValueError(f"points[{k}].{feat['name']} must be positive on a log axis")
                row.append((math.log(value) - math.log(lo)) / (math.log(hi) - math.log(lo)))
            else:
                row.append((value - lo) / (hi - lo))
        rows.append(row)
    return rows


def check_features(features) -> list[dict]:
    if not isinstance(features, list) or not features:
        raise ValueError("'features' must be a non-empty list of {name, min, max, scale}")
    out, names = [], set()
    for k, feat in enumerate(features):
        if not isinstance(feat, dict) or not isinstance(feat.get("name"), str) or not feat["name"]:
            raise ValueError(f"features[{k}] needs a name")
        if feat["name"] in names:
            raise ValueError(f"feature {feat['name']!r} is listed twice")
        names.add(feat["name"])
        lo, hi = feat.get("min"), feat.get("max")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lo, hi)) \
                or not lo < hi:
            raise ValueError(f"features[{k}] ({feat['name']}): min < max, both finite")
        scale = feat.get("scale", "linear")
        if scale not in SCALES:
            raise ValueError(f"features[{k}].scale must be one of {SCALES}")
        if scale == "log" and lo <= 0:
            raise ValueError(f"features[{k}] ({feat['name']}): a log axis needs min > 0")
        out.append({"name": feat["name"], "min": float(lo), "max": float(hi), "scale": scale,
                    **({"unit": feat["unit"]} if isinstance(feat.get("unit"), str) else {})})
    return out


# ---------------------------------------------------------------------------------------------- kernel and GP
def matern52(xa, xb, lengths, signal):
    """Matern-5/2 kernel matrix with one length scale per input."""
    import numpy as np

    diff = (xa[:, None, :] - xb[None, :, :]) / lengths
    r = np.sqrt(np.maximum((diff ** 2).sum(axis=2), 0.0))
    return signal * (1.0 + SQRT5 * r + 5.0 / 3.0 * r ** 2) * np.exp(-SQRT5 * r)


def _cholesky(k):
    import numpy as np

    try:
        return np.linalg.cholesky(k)
    except np.linalg.LinAlgError as exc:
        raise NumericalFailure(f"kernel matrix not positive definite: {exc}") from exc


def neg_log_marginal(theta, x, y):
    """(negative log marginal likelihood, gradient) for theta = (log lengths..., log signal, log nugget)."""
    import numpy as np
    from scipy.linalg import cho_solve

    d = x.shape[1]
    lengths, signal, nugget = np.exp(theta[:d]), math.exp(theta[d]), math.exp(theta[d + 1])
    diff2 = ((x[:, None, :] - x[None, :, :]) / lengths) ** 2
    r = np.sqrt(np.maximum(diff2.sum(axis=2), 0.0))
    expo = np.exp(-SQRT5 * r)
    kf = signal * (1.0 + SQRT5 * r + 5.0 / 3.0 * r ** 2) * expo
    k = kf + nugget * np.eye(len(x))
    try:
        chol = np.linalg.cholesky(k)
    except np.linalg.LinAlgError:
        return 1e25, np.zeros_like(theta)
    alpha = cho_solve((chol, True), y)
    nll = 0.5 * float(y @ alpha) + float(np.log(np.diag(chol)).sum()) + 0.5 * len(x) * math.log(2.0 * math.pi)
    inner = cho_solve((chol, True), np.eye(len(x))) - np.outer(alpha, alpha)
    common = 5.0 / 3.0 * signal * (1.0 + SQRT5 * r) * expo
    grad = np.empty_like(theta)
    for i in range(d):
        grad[i] = 0.5 * float((inner * (common * diff2[:, :, i])).sum())
    grad[d] = 0.5 * float((inner * kf).sum())
    grad[d + 1] = 0.5 * nugget * float(np.trace(inner))
    return nll, grad


def fit_component(x, y, restarts: int, seed: int) -> dict:
    """Hyperparameters of one GP by maximum marginal likelihood from `restarts` seeded starts (plus a default)."""
    import numpy as np
    from scipy.optimize import minimize

    d = x.shape[1]
    bounds = [tuple(math.log(b) for b in LENGTH_BOUNDS)] * d + [tuple(math.log(b) for b in SIGNAL_BOUNDS),
                                                                  tuple(math.log(b) for b in NUGGET_BOUNDS)]
    rng = np.random.default_rng(seed)
    starts = [np.r_[np.full(d, math.log(0.5)), 0.0, math.log(1e-8)]]
    for _ in range(max(0, restarts)):
        starts.append(np.r_[rng.uniform(math.log(0.1), math.log(3.0), d), rng.uniform(-1.0, 1.0),
                            rng.uniform(math.log(1e-10), math.log(1e-5))])
    best = None
    for start in starts:
        sol = minimize(neg_log_marginal, start, args=(x, y), jac=True, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": 500})
        if best is None or sol.fun < best.fun:
            best = sol
    theta = best.x
    lengths, signal, nugget = np.exp(theta[:d]), math.exp(theta[d]), math.exp(theta[d + 1])
    k = matern52(x, x, lengths, signal) + nugget * np.eye(len(x))
    chol = _cholesky(k)
    from scipy.linalg import cho_solve
    alpha = cho_solve((chol, True), y)
    kinv_diag = np.diag(cho_solve((chol, True), np.eye(len(x))))
    loo = alpha / kinv_diag  # closed-form leave-one-out residuals (y_i - mu_-i)
    at_bound = [i for i in range(d + 2) if min(abs(theta[i] - bounds[i][0]), abs(theta[i] - bounds[i][1])) < 1e-6]
    return {"lengths": [float(v) for v in lengths], "signal": signal, "nugget": nugget,
            "alpha": [float(v) for v in alpha], "neg_log_marginal": float(best.fun),
            "converged": bool(best.success), "hyperparameters_at_bound": at_bound,
            "loo_residual_rms": float(np.sqrt(np.mean(loo ** 2))), "loo_residual_max": float(np.max(np.abs(loo)))}


class GaussianProcessEmulator:
    """Prediction from a gp-pca-emulator/1 model document (see the module docstring)."""

    def __init__(self, model: dict):
        import numpy as np

        if model.get("format") != MODEL_FORMAT:
            raise ValueError(f"not a {MODEL_FORMAT} model")
        self.model = model
        self.features = model["features"]
        self.x = np.asarray(model["training_unit"], float)
        self.mean = np.asarray(model["output_mean"], float)
        self.basis = np.asarray(model["basis"], float)            # m x K
        self.residual_var = np.asarray(model["residual_variance"], float)
        self.components = []
        for comp in model["components"]:
            lengths, signal, nugget = np.asarray(comp["lengths"], float), float(comp["signal"]), float(comp["nugget"])
            chol = _cholesky(matern52(self.x, self.x, lengths, signal) + nugget * np.eye(len(self.x)))
            self.components.append((lengths, signal, float(comp["scale"]), np.asarray(comp["alpha"], float), chol))
        self.domain = None
        if model.get("domain_model") is not None:
            from check_surrogate_domain import DomainModel
            self.domain = DomainModel.from_dict(model["domain_model"])

    def predict_unit(self, u):
        """(transformed mean, transformed sigma) per point and output, for unit-cube rows u."""
        import numpy as np
        from scipy.linalg import solve_triangular

        u = np.atleast_2d(np.asarray(u, float))
        mean = np.repeat(self.mean[None, :], len(u), axis=0)
        var = np.repeat(self.residual_var[None, :], len(u), axis=0)
        for c, (lengths, signal, scale, alpha, chol) in enumerate(self.components):
            ks = matern52(u, self.x, lengths, signal)
            mu = ks @ alpha
            v = solve_triangular(chol, ks.T, lower=True)
            latent = np.maximum(signal - (v ** 2).sum(axis=0), 0.0)
            mean += np.outer(scale * mu, self.basis[:, c])
            var += np.outer(scale ** 2 * latent, self.basis[:, c] ** 2)
        return mean, np.sqrt(var)

    def predict(self, points):
        """List of {values, sigma, domain, domain_reasons} for points (name -> value), in output units."""
        import numpy as np

        u = np.asarray(unit_coordinates(points, self.features), float)
        mean, sigma = self.predict_unit(u)
        if self.model["outputs"]["transform"] == "log":
            values = np.exp(mean)
            sigma = values * sigma
        else:
            values = mean
        statuses, reasons = (self.domain.classify(u) if self.domain is not None else
                             (["inside" if ((row >= 0) & (row <= 1)).all() else "outside" for row in u],
                              [[] for _ in u]))
        return [{"values": [float(v) for v in values[i]], "sigma": [float(s) for s in sigma[i]],
                 "domain": statuses[i], "domain_reasons": reasons[i]} for i in range(len(u))]


# ---------------------------------------------------------------------------------------------- training
def load_training_set(doc: dict):
    import numpy as np

    if not isinstance(doc, dict):
        raise ValueError("the training set must be a JSON object")
    features = check_features(doc.get("features"))
    outputs = doc.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get("name"), str):
        raise ValueError("'outputs' must be {name, count, transform}")
    count = outputs.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("outputs.count must be a positive integer")
    transform = outputs.get("transform", "identity")
    if transform not in TRANSFORMS:
        raise ValueError(f"outputs.transform must be one of {TRANSFORMS}")
    points, values = doc.get("points"), doc.get("values")
    if not isinstance(points, list) or not isinstance(values, list) or len(points) != len(values):
        raise ValueError("'points' and 'values' must be lists of the same length")
    n, d = len(points), len(features)
    if n < max(12, 2 * d):
        raise ValueError(f"{n} training points are too few (at least {max(12, 2 * d)})")
    unit = np.asarray(unit_coordinates(points, features), float)
    outside = [k for k, row in enumerate(unit) if not ((row >= -1e-12) & (row <= 1 + 1e-12)).all()]
    if outside:
        raise ValueError(f"points {outside[:5]} lie outside the declared boxes")
    if len({tuple(row) for row in unit.round(12)}) != n:
        raise ValueError("a point is listed twice")
    rows = []
    for k, row in enumerate(values):
        if not isinstance(row, list) or len(row) != count or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in row):
            raise ValueError(f"values[{k}] must hold {count} finite numbers")
        if transform == "log" and min(row) <= 0:
            raise ValueError(f"values[{k}] must be positive for transform log")
        rows.append(row)
    y = np.asarray(rows, float)
    groups = doc.get("groups")
    if groups is not None and (not isinstance(groups, list) or len(groups) != n):
        raise ValueError("'groups' must give one label per point")
    status = doc.get("status") or []
    if not isinstance(status, list) or any(s not in STATUSES for s in status) or not status:
        raise ValueError(f"'status' must list the training data's artifact labels from {STATUSES}")
    context = doc.get("context")
    if context is not None and not isinstance(context, dict):
        raise ValueError("'context' must be a JSON object")
    return features, dict(outputs, transform=transform), unit, y, groups, status, context


def train(doc: dict, pca_tolerance: float = 1e-5, restarts: int = 4, seed: int = 0, domain_quantile: float = 0.99,
          domain_k: int = 5) -> dict:
    """The model document trained on a training-set document."""
    import numpy as np

    features, outputs, unit, values, groups, status, context = load_training_set(doc)
    y = np.log(values) if outputs["transform"] == "log" else values
    mean = y.mean(axis=0)
    centred = y - mean
    _, sing, vt = np.linalg.svd(centred, full_matrices=False)
    n_max = min(len(y) - 1, y.shape[1])
    keep = n_max
    for kk in range(1, n_max + 1):
        resid = centred - centred @ vt[:kk].T @ vt[:kk]
        if float(np.abs(resid).max()) <= pca_tolerance:
            keep = kk
            break
    basis = vt[:keep].T                                   # m x K
    coeff = centred @ basis                               # n x K
    resid = centred - coeff @ basis.T
    components = []
    for c in range(keep):
        scale = float(coeff[:, c].std()) or 1.0
        comp = fit_component(unit, coeff[:, c] / scale, restarts, seed + c)
        comp["scale"] = scale
        comp["explained_singular_value"] = float(sing[c])
        components.append(comp)
    domain = None
    if len(unit) >= DOMAIN_MIN_POINTS:
        from check_surrogate_domain import DomainModel
        domain = DomainModel.fit(unit, quantile=domain_quantile, k=domain_k, seed=seed,
                                 groups=[str(g) for g in groups] if groups else None).to_dict()
    model = {"format": MODEL_FORMAT, "kernel": KERNEL, "features": features, "outputs": outputs,
             "coordinates": "unit cube of the feature boxes (log axis for scale log)",
             "training_unit": [[float(v) for v in row] for row in unit], "n_training": int(len(unit)),
             "output_mean": [float(v) for v in mean], "basis": [[float(v) for v in row] for row in basis],
             "pca": {"components": keep, "tolerance": pca_tolerance,
                     "training_residual_max": float(np.abs(resid).max()) if keep else 0.0},
             "residual_variance": [float(v) for v in (resid ** 2).mean(axis=0)],
             "components": components, "domain_model": domain, "context": context,
             "training": {"seed": seed, "restarts": restarts, "status": status,
                          "groups": [str(g) for g in groups] if groups else None}}
    emu = GaussianProcessEmulator(model)
    rng = np.random.default_rng(seed)
    ref_unit = rng.uniform(0.25, 0.75, size=(SELF_CHECK_POINTS, len(features)))
    ref_mean, ref_sigma = emu.predict_unit(ref_unit)
    model["self_check"] = {"unit": ref_unit.tolist(), "transformed_mean": ref_mean.tolist(),
                           "transformed_sigma": ref_sigma.tolist(),
                           "note": "a reader recomputes these and refuses the model if they differ by more than 1e-9"}
    return model


def model_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_summary(model: dict, model_path: Path, training_set_path: Path) -> dict:
    """The run summary write_ml_artifact.py reads (task surrogate); the caller adds its validation blocks."""
    import numpy as np
    import scipy

    feats = model["features"]
    return {"task": "surrogate", "output_semantics": "regression-value",
            "features": [f["name"] for f in feats],
            "units": {f["name"]: f["unit"] for f in feats if "unit" in f},
            "labels": model["outputs"].get("labels") or [f"{model['outputs']['name']}[{i}]"
                                                         for i in range(model["outputs"]["count"])],
            "grouping_key": "parameter point (one simulator run per point)",
            "training_domain": {f["name"]: [f["min"], f["max"]] for f in feats},
            "preprocessing": [
                {"step": "unit-cube scaling of each input (log axis for scale log)", "fit_on": "training"},
                {"step": f"output transform {model['outputs']['transform']}, centring and principal components "
                         f"({model['pca']['components']} kept, residual <= {model['pca']['tolerance']})",
                 "fit_on": "training"}],
            "model_hash": "sha256:" + model_sha256(model_path),
            "checkpoint": str(model_path),
            "environment": {"framework": f"numpy {np.__version__}, scipy {scipy.__version__}", "device": "cpu",
                            "precision": "fp64", "seeds": {"hyperparameter_starts": model["training"]["seed"],
                                                           "domain_split": model["training"]["seed"]}},
            "metrics": {"training_points": model["n_training"],
                        "loo_residual_rms_per_component": [c["loo_residual_rms"] for c in model["components"]],
                        "pca_training_residual_max": model["pca"]["training_residual_max"]},
            "status": model["training"]["status"],
            "training_set": str(training_set_path)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog="Exit 0 done, 2 bad input, 3 numerical failure or NumPy/SciPy missing.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train", help="train on a training-set JSON")
    t.add_argument("--training-set", required=True, type=Path)
    t.add_argument("--out-dir", required=True, type=Path)
    t.add_argument("--pca-tolerance", type=float, default=1e-5,
                   help="largest training reconstruction residual of the kept components (transformed units)")
    t.add_argument("--restarts", type=int, default=4, help="seeded random starts per component (plus a default)")
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--domain-quantile", type=float, default=0.99, help="DomainModel quantile (default 0.99)")
    t.add_argument("--domain-k", type=int, default=5, help="DomainModel neighbour rank (default 5)")
    add_status_argument(t)
    p = sub.add_parser("predict", help="predict at points with a trained model")
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--points", required=True, type=Path, help="JSON list of points (name -> value)")
    add_status_argument(p)
    args = ap.parse_args(argv)
    head = {"status_label": args.status}
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", **head, "error": f"NumPy and SciPy are needed: {exc}"}))
        return 3
    try:
        if args.cmd == "predict":
            model = json.loads(args.model.read_text(encoding="utf-8"))
            points = json.loads(args.points.read_text(encoding="utf-8"))
            if not isinstance(points, list):
                raise ValueError("--points must hold a JSON list of points")
            print(json.dumps({"status": "ok", **head, "model_sha256": model_sha256(args.model),
                              "predictions": GaussianProcessEmulator(model).predict(points)}, indent=1))
            return 0
        if args.restarts < 0 or not 0 < args.pca_tolerance:
            raise ValueError("--restarts >= 0 and --pca-tolerance > 0")
        doc = json.loads(args.training_set.read_text(encoding="utf-8"))
        model = train(doc, args.pca_tolerance, args.restarts, args.seed, args.domain_quantile, args.domain_k)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        model_path = args.out_dir / "emulator-model.json"
        model_path.write_text(json.dumps(model, indent=None, separators=(",", ":")) + "\n", encoding="utf-8")
        summary = run_summary(model, model_path, args.training_set)
        (args.out_dir / "run_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    except NumericalFailure as exc:
        print(json.dumps({"status": "incomplete", **head, "error": f"numerical failure: {exc}"}))
        return 3
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", **head, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps({"status": "written", **head, "model": str(model_path), "model_hash": summary["model_hash"],
                      "components": model["pca"]["components"], "training_points": model["n_training"],
                      "domain": "DomainModel" if model["domain_model"] else "box-only",
                      "hyperparameters_at_bound": {c: comp["hyperparameters_at_bound"]
                                                   for c, comp in enumerate(model["components"])
                                                   if comp["hyperparameters_at_bound"]}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
