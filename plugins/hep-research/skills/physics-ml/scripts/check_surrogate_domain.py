#!/usr/bin/env python3
"""Flag surrogate-model queries that leave the training domain (extrapolation).

Purpose: a surrogate (an ML model standing in for a simulation or a calculation) is only validated where it was
trained. Its output looks equally confident everywhere, so extrapolation has to be detected from the inputs. A
per-feature box is not enough: in many dimensions, or with correlated features, a point can sit inside every
feature's range and still be far from all training data, while a typical training-like point can leave the box in
one coordinate.

What it does: splits the training points (seeded) into a fit part and a held-out calibration part. On the fit part it
whitens the features (mean and covariance, eigen-decomposition; directions with near-zero variance are dropped and
reported, constant features are set aside and reported without dividing by zero). For every point it computes
  (a) the Mahalanobis distance (norm in whitened space): far from the bulk of the training cloud;
  (b) the distance to the k-th nearest fit point in whitened space (scipy.spatial.cKDTree): in a hole of the cloud;
  (c) the residual along the dropped near-zero-variance directions: off a linear constraint the training obeys.
Thresholds are empirical quantiles of these statistics on the held-out training points (split-conformal ranks), each
at 1 - (1 - q)/2 so that the combined in-distribution false-positive rate is about 1 - q; the report gives a
two-fold cross-fitted estimate of that rate on the held-out part. Status per query:
  outside  Mahalanobis or subspace residual above threshold, or a constant training feature has another value;
  sparse   within the Mahalanobis envelope but the k-NN distance is above threshold (a hole or thin region);
  inside   otherwise.
The per-feature box is reported as a diagnostic ("outside_features"); a coordinate outside the box makes the query
'outside' only with --box-strict. With "training_domain" instead of points, only the box can be checked: the report
says method "box-only" and a query outside the box is 'outside'.

Input JSON: {"features": ["a", "b"], "training": [[...], ...], "queries": [[...], ...]}
  or "training_domain": {"a": [lo, hi], ...} instead of "training". Every row must have len(features) finite numbers;
  a dimension mismatch is an input error, never truncated.
Output: JSON report (strict JSON, no NaN or Infinity) on stdout.
Exit codes: 0 every query inside, 1 any query outside or sparse, 2 bad input (malformed JSON, wrong dimensions,
  too few training points to calibrate), 3 numerical failure (for example a covariance that cannot be decomposed).
Usage notes / assumptions: requires numpy and scipy (core dependencies of the plugin); PyTorch is not required.
  Needs at least 50 training points at the default --holdout-fraction 0.2 (10 held out). Calibration assumes the
  held-out points are exchangeable with in-distribution queries (an i.i.d. training design); for a grid or Latin
  hypercube design, read the thresholds as a guide. Inside the domain is necessary, not sufficient: validate the
  surrogate on held-out points there.
Run: python3 <plugin root>/skills/physics-ml/scripts/check_surrogate_domain.py domain.json [--quantile 0.99] [--k 5]
"""
from __future__ import annotations

import argparse
import json
import math
import sys

MIN_HELD_OUT = 10
EIGEN_RTOL = 1e-10  # eigenvalues below this fraction of the largest are treated as zero variance
CONSTANT_RTOL = 1e-12  # a feature whose spread is below this (relative to its magnitude) is constant


class NumericalFailure(RuntimeError):
    """The calculation broke down on valid input (exit 3, not 1)."""


def _matrix(rows, width, name):
    import numpy as np

    if not isinstance(rows, list) or not rows:
        raise ValueError(f"'{name}' must be a non-empty list of rows")
    for i, row in enumerate(rows):
        if not isinstance(row, list):
            raise ValueError(f"{name}[{i}] must be a list of numbers")
        if len(row) != width:
            raise ValueError(f"{name}[{i}] has {len(row)} values but there are {width} features")
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name}[{i}][{j}] must be a finite number")
    return np.asarray(rows, dtype=float)


def _box_from_domain(feats, domain):
    if not isinstance(domain, dict):
        raise ValueError("'training_domain' must map each feature to [lo, hi]")
    box = {}
    for f in feats:
        bounds = domain.get(f)
        if (not isinstance(bounds, list) or len(bounds) != 2
                or any(isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b) for b in bounds)
                or bounds[0] > bounds[1]):
            raise ValueError(f"training_domain[{f!r}] must be [lo, hi] with finite lo <= hi")
        box[f] = [float(bounds[0]), float(bounds[1])]
    return box


def _rank_threshold(values, level):
    """Split-conformal threshold: the ceil((n+1)*level)-th smallest value (the maximum if that rank exceeds n)."""
    import numpy as np

    ordered = np.sort(values)
    n = len(ordered)
    rank = math.ceil((n + 1) * level)
    return float(ordered[min(rank, n) - 1]), rank > n


class _Whitener:
    """Mean/covariance whitening fitted on one sample, robust to constant features and rank deficiency."""

    def __init__(self, x):
        import numpy as np

        self.mean = x.mean(axis=0)
        spread = x.max(axis=0) - x.min(axis=0)
        magnitude = np.maximum(np.abs(self.mean), 1.0)
        self.constant = spread <= CONSTANT_RTOL * magnitude
        self.active = ~self.constant
        self.constant_tol = 1e-9 * magnitude
        self.dropped = 0
        self.dim = 0
        if not self.active.any():
            return
        xa = x[:, self.active] - self.mean[self.active]
        cov = np.atleast_2d(np.cov(xa, rowvar=False))
        if not np.all(np.isfinite(cov)):
            raise NumericalFailure("training covariance is not finite")
        try:
            evals, evecs = np.linalg.eigh(cov)
        except np.linalg.LinAlgError as exc:
            raise NumericalFailure(f"covariance eigen-decomposition failed: {exc}") from exc
        keep = evals > EIGEN_RTOL * max(float(evals.max()), 0.0)
        if not keep.any():
            raise NumericalFailure("covariance has no direction with positive variance")
        self.basis = evecs[:, keep] / np.sqrt(evals[keep])
        self.null = evecs[:, ~keep]
        self.dim = int(keep.sum())
        self.dropped = int((~keep).sum())
        self.scale = math.sqrt(float(evals[keep].sum()))  # overall spread, for the residual floor

    def transform(self, x):
        """Whitened coordinates, residual along dropped directions, and constant-feature mismatch per row."""
        import numpy as np

        mismatch = np.abs(x[:, self.constant] - self.mean[self.constant]) > self.constant_tol[self.constant]
        if not self.active.any():
            return np.zeros((len(x), 0)), np.zeros(len(x)), mismatch
        xa = x[:, self.active] - self.mean[self.active]
        z = xa @ self.basis
        resid = np.linalg.norm(xa @ self.null, axis=1) if self.dropped else np.zeros(len(x))
        return z, resid, mismatch


def check(payload: dict, quantile: float = 0.99, k: int = 5, holdout_fraction: float = 0.2, seed: int = 0,
          box_strict: bool = False) -> dict:
    """Classify each query as inside / sparse / outside the training domain; see the module docstring."""
    import numpy as np

    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    if not 0.5 <= quantile < 1.0:
        raise ValueError("quantile must be in [0.5, 1)")
    if not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be strictly between 0 and 1")
    feats = payload.get("features")
    if not isinstance(feats, list) or not feats or not all(isinstance(f, str) for f in feats):
        raise ValueError("'features' must be a non-empty list of names")
    if len(set(feats)) != len(feats):
        raise ValueError("'features' contains duplicate names")
    d = len(feats)
    queries = _matrix(payload.get("queries"), d, "queries")
    training = payload.get("training")
    note = "inside the domain is necessary, not sufficient: validate the surrogate on held-out points there"

    if training is None:
        if payload.get("training_domain") is None:
            raise ValueError("need 'training' points or a 'training_domain'")
        box = _box_from_domain(feats, payload["training_domain"])
        rows = []
        for i, q in enumerate(queries):
            out = [f for j, f in enumerate(feats) if not box[f][0] <= q[j] <= box[f][1]]
            rows.append({"query": i, "status": "outside" if out else "inside", "outside_features": out,
                         "reasons": ["outside the training box"] if out else []})
        return {"method": "box-only", "features": feats, "training_box": box, "box_strict": True,
                "queries": rows, "counts": _counts(rows), "passed": all(r["status"] == "inside" for r in rows),
                "note": "box-only: only per-feature ranges were given, so correlations, holes and distance from the "
                        "training cloud are not checked. " + note}

    x = _matrix(training, d, "training")
    n = len(x)
    n_held = int(round(holdout_fraction * n))
    n_fit = n - n_held
    if n_held < MIN_HELD_OUT or n_fit < k + 1:
        raise ValueError(f"{n} training points are too few to calibrate: need at least {MIN_HELD_OUT} held out "
                         f"(holdout_fraction {holdout_fraction}) and more than k={k} in the fit part")
    box = {f: [float(x[:, j].min()), float(x[:, j].max())] for j, f in enumerate(feats)}

    from scipy.spatial import cKDTree

    perm = np.random.default_rng(seed).permutation(n)
    fit, held = x[perm[n_held:]], x[perm[:n_held]]
    white = _Whitener(fit)
    z_fit, _, _ = white.transform(fit)
    z_held, r_held, _ = white.transform(held)
    z_q, r_q, mismatch_q = white.transform(queries)
    tree = cKDTree(z_fit) if white.dim else None

    def knn(z):
        if tree is None:
            return np.zeros(len(z))
        dist, _ = tree.query(z, k=[k])
        return dist[:, 0]

    stats_held = {"mahalanobis": np.linalg.norm(z_held, axis=1), "knn": knn(z_held), "residual": r_held}
    stats_q = {"mahalanobis": np.linalg.norm(z_q, axis=1), "knn": knn(z_q), "residual": r_q}
    for name, values in list(stats_held.items()) + list(stats_q.items()):
        if not np.all(np.isfinite(values)):
            raise NumericalFailure(f"non-finite {name} distance")

    level = 1.0 - (1.0 - quantile) / 2.0
    residual_floor = 1e-6 * getattr(white, "scale", 1.0)

    def thresholds(sample):
        t = {}
        capped = False
        for name in ("mahalanobis", "knn"):
            t[name], c = _rank_threshold(sample[name], level)
            capped = capped or c
        t["residual"] = max(_rank_threshold(sample["residual"], level)[0], residual_floor) if white.dropped else None
        return t, capped

    def flagged(stats, t, idx=slice(None)):
        out = stats["mahalanobis"][idx] > t["mahalanobis"]
        if t["residual"] is not None:
            out = out | (stats["residual"][idx] > t["residual"])
        return out, ~out & (stats["knn"][idx] > t["knn"])

    thr, capped = thresholds(stats_held)

    # Two-fold cross-fitted false-positive estimate on the held-out part: calibrate on one half, test on the other.
    half = n_held // 2
    order = np.random.default_rng(seed + 1).permutation(n_held)
    fp, tested = 0, 0
    for cal, test in ((order[:half], order[half:]), (order[half:], order[:half])):
        t_cal, _ = thresholds({key: v[cal] for key, v in stats_held.items()})
        o, s = flagged(stats_held, t_cal, test)
        fp += int((o | s).sum())
        tested += len(test)

    outside, sparse = flagged(stats_q, thr)
    rows = []
    for i, q in enumerate(queries):
        out_feats = [f for j, f in enumerate(feats) if not box[f][0] <= q[j] <= box[f][1]]
        const_bad = [f for f, bad in zip(np.array(feats)[white.constant], mismatch_q[i]) if bad]
        reasons = []
        if stats_q["mahalanobis"][i] > thr["mahalanobis"]:
            reasons.append("Mahalanobis distance above threshold (far from the training cloud)")
        if thr["residual"] is not None and stats_q["residual"][i] > thr["residual"]:
            reasons.append("off a near-zero-variance direction of the training data (a constraint it obeys)")
        if const_bad:
            reasons.append("a feature constant in training has another value")
        if sparse[i] and not const_bad:
            reasons.append("k-NN distance above threshold (in a hole or thin region of the training data)")
        if out_feats:
            reasons.append("outside the per-feature training box" + ("" if box_strict else " (diagnostic only)"))
        if outside[i] or const_bad or (box_strict and out_feats):
            status = "outside"
        elif sparse[i]:
            status = "sparse"
        else:
            status = "inside"
        row = {"query": i, "status": status, "reasons": reasons,
               "mahalanobis": round(float(stats_q["mahalanobis"][i]), 6),
               "knn_distance": round(float(stats_q["knn"][i]), 6),
               "outside_features": out_feats}
        if white.dropped:
            row["subspace_residual"] = float(stats_q["residual"][i])
        if const_bad:
            row["constant_feature_mismatch"] = const_bad
        rows.append(row)

    return {
        "method": "whitened Mahalanobis + k-NN (cKDTree), thresholds calibrated on held-out training points",
        "features": feats,
        "n_training": n, "n_fit": n_fit, "n_held_out": n_held, "seed": seed,
        "quantile": quantile, "per_statistic_level": level, "k": k,
        "thresholds": {"mahalanobis": thr["mahalanobis"], "knn_distance": thr["knn"],
                       "subspace_residual": thr["residual"]},
        "threshold_capped_at_held_out_max": capped,
        "estimated_false_positive_rate": fp / tested if tested else None,
        "false_positive_estimate": f"two-fold cross-fit on {tested} held-out training points",
        "effective_dimension": white.dim,
        "dropped_directions": white.dropped,
        "constant_features": [f for f, c in zip(feats, white.constant) if c],
        "training_box": box, "box_strict": box_strict,
        "queries": rows, "counts": _counts(rows),
        "passed": all(r["status"] == "inside" for r in rows),
        "note": note,
    }


def _counts(rows):
    return {s: sum(r["status"] == s for r in rows) for s in ("inside", "sparse", "outside")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="input JSON (see above)")
    ap.add_argument("--quantile", type=float, default=0.99,
                    help="target in-distribution acceptance; about 1 - quantile of typical queries are flagged")
    ap.add_argument("--k", type=int, default=5, help="neighbour rank for the k-NN distance (default 5)")
    ap.add_argument("--holdout-fraction", type=float, default=0.2,
                    help="fraction of training points held out to calibrate the thresholds (default 0.2)")
    ap.add_argument("--seed", type=int, default=0, help="seed for the fit/held-out split (default 0)")
    ap.add_argument("--box-strict", action="store_true",
                    help="also mark a query 'outside' when any single coordinate leaves the training box")
    args = ap.parse_args(argv)
    try:
        with open(args.path, encoding="utf-8") as fh:
            payload = json.load(fh)
        import numpy as np

        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):  # overflow is caught as exit 3
            rep = check(payload, args.quantile, args.k, args.holdout_fraction, args.seed, args.box_strict)
        try:
            text = json.dumps(rep, indent=1, allow_nan=False)
        except ValueError as exc:  # a non-finite number reached the report
            raise NumericalFailure(str(exc)) from exc
    except ImportError as exc:
        print(json.dumps({"error": f"this check needs numpy and scipy: {exc}"}))
        return 2
    except NumericalFailure as exc:
        print(json.dumps({"error": f"numerical failure: {exc}"}))
        return 3
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:  # malformed input is a JSON error
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(text)
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
