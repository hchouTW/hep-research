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
  a dimension mismatch is an input error, never truncated. Optional: "groups" (one label per training point: design
  point, run, seed; the held-out part and the two cross-fit halves are split by group, so replicas never sit on both
  sides and the false-positive estimate is not optimistic) and "categorical" (feature names whose query value must be
  one seen in training; they are not whitened).
The fitted method is the importable class DomainModel (fit, classify, to_dict, from_dict), which
assets/train_classifier.py stores in its checkpoint and assets/inference.py applies: one domain method for training,
inference and surrogates. The false-positive estimate comes with a Clopper-Pearson 68.27% interval.
Output: JSON report (strict JSON, no NaN or Infinity) on stdout, with "status" (passed, failed, rejected, incomplete,
  missing-dependency; core/status.py) and "status_label" (--status, the inputs' artifact label).
Exit codes: 0 every query inside, 1 any query outside or sparse, 2 bad input (malformed JSON, wrong dimensions,
  too few training points to calibrate), 3 numerical failure (for example a covariance that cannot be decomposed) or
  NumPy/SciPy missing.
Usage notes / assumptions: requires numpy and scipy (core dependencies of the plugin); PyTorch is not required.
  Needs at least 50 training points at the default --holdout-fraction 0.2 (10 held out). Calibration assumes the
  held-out points are exchangeable with in-distribution queries (an i.i.d. training design); for a grid or Latin
  hypercube design, read the thresholds as a guide. Inside the domain is necessary, not sufficient: validate the
  surrogate on held-out points there.
Run: python3 <plugin root>/skills/hep-ml/scripts/check_surrogate_domain.py domain.json [--quantile 0.99] [--k 5]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # plugin root: core.stats for the interval

STATUSES = ("synthetic", "asimov", "observed", "preliminary", "failed", "unvalidated", "user-supplied",
            "validated-in-scope", "projection")  # contracts/vocab/core.json artifact_statuses
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

    def __init__(self, x=None):
        import numpy as np

        if x is None:  # filled by from_dict
            return
        self.mean = x.mean(axis=0)
        spread = x.max(axis=0) - x.min(axis=0)
        magnitude = np.maximum(np.abs(self.mean), 1.0)
        self.constant = spread <= CONSTANT_RTOL * magnitude
        self.active = ~self.constant
        self.constant_tol = 1e-9 * magnitude
        self.dropped = 0
        self.dim = 0
        self.scale = 1.0
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

    def to_dict(self) -> dict:
        out = {"mean": self.mean.tolist(), "constant": self.constant.tolist(), "constant_tol": self.constant_tol.tolist(),
               "dim": self.dim, "dropped": self.dropped, "scale": self.scale}
        if self.active.any():
            out.update(basis=self.basis.tolist(), null=self.null.tolist())
        return out

    @classmethod
    def from_dict(cls, d: dict) -> "_Whitener":
        import numpy as np

        w = cls()
        w.mean, w.constant = np.asarray(d["mean"], float), np.asarray(d["constant"], bool)
        w.active, w.constant_tol = ~w.constant, np.asarray(d["constant_tol"], float)
        w.dim, w.dropped, w.scale = int(d["dim"]), int(d["dropped"]), float(d["scale"])
        if w.active.any():
            n_active = int(w.active.sum())
            w.basis = np.asarray(d["basis"], float).reshape(n_active, w.dim)
            w.null = np.asarray(d["null"], float).reshape(n_active, w.dropped)
        return w


class DomainModel:
    """The training-domain method shared by this script, assets/train_classifier.py and assets/inference.py.

    fit() splits the training points into a fit part and a held-out calibration part (at random, or by group so that
    replicas of one design point, or events of one run, never sit on both sides), whitens the continuous features on
    the fit part and calibrates the Mahalanobis, k-NN and subspace-residual thresholds on the held-out part.
    Categorical features (column indices) are set aside: a query value never seen in training is outside.
    classify() returns a status (inside, sparse, outside) and reasons per query; a non-finite query is outside.
    to_dict()/from_dict() store the fitted model as plain lists (a checkpoint's metadata)."""

    METHOD = "whitened Mahalanobis + k-NN (cKDTree) + subspace residual, thresholds calibrated on held-out training points"

    @classmethod
    def fit(cls, x, quantile: float = 0.99, k: int = 5, holdout_fraction: float = 0.2, seed: int = 0, groups=None,
            categorical=()):
        import numpy as np

        if not 0.5 <= quantile < 1.0:
            raise ValueError("quantile must be in [0.5, 1)")
        if not isinstance(k, int) or k < 1:
            raise ValueError("k must be a positive integer")
        if not 0.0 < holdout_fraction < 1.0:
            raise ValueError("holdout_fraction must be strictly between 0 and 1")
        x = np.asarray(x, dtype=float)
        n, d = x.shape
        if not np.all(np.isfinite(x)):
            raise ValueError("training points must be finite")
        cat = sorted({int(j) for j in categorical})
        if any(not 0 <= j < d for j in cat):
            raise ValueError("categorical feature index out of range")
        self = cls()
        self.d, self.quantile, self.k, self.seed = d, quantile, k, seed
        self.categorical = {j: sorted({float(v) for v in x[:, j]}) for j in cat}
        self.continuous = [j for j in range(d) if j not in cat]
        n_held = int(round(holdout_fraction * n))
        if groups is None:
            perm = np.random.default_rng(seed).permutation(n)
            held_idx, fit_idx = perm[:n_held], perm[n_held:]
            self.holdout = "random"
        else:
            labels = np.asarray([str(g) for g in groups])
            if len(labels) != n:
                raise ValueError(f"groups has {len(labels)} entries for {n} training points")
            unique = np.unique(labels)
            held, n_groups = [], 0
            for gi in np.random.default_rng(seed).permutation(len(unique)):
                if len(held) >= n_held:
                    break
                held += np.flatnonzero(labels == unique[gi]).tolist()
                n_groups += 1
            held_idx = np.array(sorted(held), dtype=int)
            fit_idx = np.setdiff1d(np.arange(n), held_idx)
            n_held = len(held_idx)
            self.holdout = f"grouped ({n_groups} of {len(unique)} groups held out)"
        self.n_training, self.n_fit, self.n_held = n, len(fit_idx), n_held
        if n_held < MIN_HELD_OUT or len(fit_idx) < k + 1:
            raise ValueError(f"{n} training points are too few to calibrate: need at least {MIN_HELD_OUT} held out "
                             f"(holdout_fraction {holdout_fraction}) and more than k={k} in the fit part")
        xc = x[:, self.continuous]
        self.white = _Whitener(xc[fit_idx])
        self.z_fit, _, _ = self.white.transform(xc[fit_idx])
        self._tree = None
        stats_held = self._stats(xc[held_idx])
        self.level = 1.0 - (1.0 - quantile) / 2.0
        self.residual_floor = 1e-6 * self.white.scale
        self.thresholds, self.capped = self._thresholds(stats_held)
        # Two-fold cross-fitted false-positive estimate on the held-out part: calibrate on one half, test on the other.
        # With groups the halves are split by group too: replicas of one group in both halves would make each half
        # predict the other perfectly and the estimate would be far below the rate on new queries.
        half = n_held // 2
        order = np.random.default_rng(seed + 1).permutation(n_held)
        if groups is not None:
            held_groups = labels[held_idx]
            ug = np.unique(held_groups)
            gorder = np.random.default_rng(seed + 1).permutation(len(ug))
            first = set(ug[gorder[: len(ug) // 2]].tolist())
            in_first = np.array([g in first for g in held_groups])
            order = np.r_[np.flatnonzero(in_first), np.flatnonzero(~in_first)]
            half = int(in_first.sum())
        fp, tested = 0, 0
        for cal, test in ((order[:half], order[half:]), (order[half:], order[:half])):
            t_cal, _ = self._thresholds({key: v[cal] for key, v in stats_held.items()})
            o, sp = self._flagged(stats_held, t_cal, test)
            fp += int((o | sp).sum())
            tested += len(test)
        self.fp_count, self.fp_tested = fp, tested
        self.estimated_false_positive_rate = fp / tested if tested else None
        return self

    def _knn(self, z):
        import numpy as np

        if not self.white.dim:
            return np.zeros(len(z))
        if self._tree is None:
            from scipy.spatial import cKDTree
            self._tree = cKDTree(self.z_fit)
        dist, _ = self._tree.query(z, k=[self.k])
        return dist[:, 0]

    def _stats(self, xc):
        import numpy as np

        z, resid, mismatch = self.white.transform(xc)
        stats = {"mahalanobis": np.linalg.norm(z, axis=1), "knn": self._knn(z), "residual": resid}
        for name, values in stats.items():
            if not np.all(np.isfinite(values)):
                raise NumericalFailure(f"non-finite {name} distance")
        stats["mismatch"] = mismatch
        return stats

    def _thresholds(self, sample):
        t, capped = {}, False
        for name in ("mahalanobis", "knn"):
            t[name], c = _rank_threshold(sample[name], self.level)
            capped = capped or c
        t["residual"] = (max(_rank_threshold(sample["residual"], self.level)[0], self.residual_floor)
                         if self.white.dropped else None)
        return t, capped

    @staticmethod
    def _flagged(stats, t, idx=slice(None)):
        out = stats["mahalanobis"][idx] > t["mahalanobis"]
        if t["residual"] is not None:
            out = out | (stats["residual"][idx] > t["residual"])
        return out, ~out & (stats["knn"][idx] > t["knn"])

    def details(self, queries):
        """Per-query (status, reasons, stats); non-finite rows are outside with reason 'non-finite'."""
        import numpy as np

        q = np.asarray(queries, dtype=float)
        if q.ndim != 2 or q.shape[1] != self.d:
            raise ValueError(f"queries must have {self.d} columns")
        finite = np.all(np.isfinite(q), axis=1)
        safe = np.where(np.isfinite(q), q, 0.0)
        stats = self._stats(safe[:, self.continuous])
        outside, sparse = self._flagged(stats, self.thresholds)
        rows = []
        for i in range(len(q)):
            reasons = []
            if not finite[i]:
                rows.append(("outside", ["non-finite"], stats))
                continue
            const_bad = bool(stats["mismatch"][i].any()) if stats["mismatch"].size else False
            cat_bad = [j for j, allowed in self.categorical.items() if float(q[i, j]) not in allowed]
            if stats["mahalanobis"][i] > self.thresholds["mahalanobis"]:
                reasons.append("Mahalanobis distance above threshold (far from the training cloud)")
            if self.thresholds["residual"] is not None and stats["residual"][i] > self.thresholds["residual"]:
                reasons.append("off a near-zero-variance direction of the training data (a constraint it obeys)")
            if const_bad:
                reasons.append("a feature constant in training has another value")
            if cat_bad:
                reasons.append(f"categorical value not seen in training (feature index {cat_bad})")
            if sparse[i] and not const_bad:
                reasons.append("k-NN distance above threshold (in a hole or thin region of the training data)")
            if outside[i] or const_bad or cat_bad:
                status = "outside"
            elif sparse[i]:
                status = "sparse"
            else:
                status = "inside"
            rows.append((status, reasons, stats))
        return rows

    def white_constant_indices(self):
        return [self.continuous[j] for j, c in enumerate(self.white.constant) if c]

    def classify(self, queries):
        """(statuses, reasons) per query."""
        rows = self.details(queries)
        return [r[0] for r in rows], [r[1] for r in rows]

    def to_dict(self) -> dict:
        return {"method": self.METHOD, "d": self.d, "quantile": self.quantile, "k": self.k, "seed": self.seed,
                "level": self.level, "holdout": self.holdout, "n_training": self.n_training, "n_fit": self.n_fit,
                "n_held_out": self.n_held, "continuous": self.continuous,
                "categorical": {str(j): v for j, v in self.categorical.items()},
                "whitener": self.white.to_dict(), "z_fit": self.z_fit.tolist(),
                "thresholds": dict(self.thresholds), "residual_floor": self.residual_floor,
                "threshold_capped_at_held_out_max": self.capped,
                "estimated_false_positive_rate": self.estimated_false_positive_rate,
                "false_positive_count": self.fp_count, "false_positive_tested": self.fp_tested}

    @classmethod
    def from_dict(cls, d: dict) -> "DomainModel":
        import numpy as np

        self = cls()
        self.d, self.quantile, self.k, self.seed = int(d["d"]), float(d["quantile"]), int(d["k"]), int(d["seed"])
        self.level, self.holdout = float(d["level"]), d["holdout"]
        self.n_training, self.n_fit, self.n_held = int(d["n_training"]), int(d["n_fit"]), int(d["n_held_out"])
        self.continuous = [int(j) for j in d["continuous"]]
        self.categorical = {int(j): [float(v) for v in vals] for j, vals in d["categorical"].items()}
        self.white = _Whitener.from_dict(d["whitener"])
        self.z_fit = np.asarray(d["z_fit"], dtype=float).reshape(self.n_fit, self.white.dim)
        self._tree = None
        self.thresholds, self.residual_floor = dict(d["thresholds"]), float(d["residual_floor"])
        self.capped = bool(d["threshold_capped_at_held_out_max"])
        self.estimated_false_positive_rate = d["estimated_false_positive_rate"]
        self.fp_count, self.fp_tested = int(d["false_positive_count"]), int(d["false_positive_tested"])
        return self


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
    groups = payload.get("groups")
    if groups is not None and (not isinstance(groups, list) or len(groups) != len(x)):
        raise ValueError(f"'groups' must list one group per training point ({len(x)})")
    categorical = payload.get("categorical") or []
    if not isinstance(categorical, list) or any(c not in feats for c in categorical):
        raise ValueError("'categorical' must list feature names")
    model = DomainModel.fit(x, quantile, k, holdout_fraction, seed, groups=groups,
                            categorical=[feats.index(c) for c in categorical])
    box = {f: [float(x[:, j].min()), float(x[:, j].max())] for j, f in enumerate(feats)}
    details = model.details(queries)
    stats_q = details[0][2] if details else {}
    const_names = [feats[j] for j in model.white_constant_indices()]
    rows = []
    for i, q in enumerate(queries):
        status, reasons, _ = details[i]
        out_feats = [f for j, f in enumerate(feats) if not box[f][0] <= q[j] <= box[f][1]]
        if out_feats:
            reasons = reasons + ["outside the per-feature training box" + ("" if box_strict else " (diagnostic only)")]
        if box_strict and out_feats:
            status = "outside"
        row = {"query": i, "status": status, "reasons": reasons,
               "mahalanobis": round(float(stats_q["mahalanobis"][i]), 6),
               "knn_distance": round(float(stats_q["knn"][i]), 6),
               "outside_features": out_feats}
        if model.white.dropped:
            row["subspace_residual"] = float(stats_q["residual"][i])
        bad = [f for f, m in zip(const_names, stats_q["mismatch"][i]) if m] if stats_q["mismatch"].size else []
        if bad:
            row["constant_feature_mismatch"] = bad
        rows.append(row)

    from core.stats.tail_estimation import clopper_pearson
    interval = (list(clopper_pearson(model.fp_count, model.fp_tested, 0.6827)) if model.fp_tested else None)
    return {
        "method": DomainModel.METHOD,
        "features": feats,
        "n_training": model.n_training, "n_fit": model.n_fit, "n_held_out": model.n_held, "seed": seed,
        "holdout": model.holdout,
        "quantile": quantile, "per_statistic_level": model.level, "k": k,
        "thresholds": {"mahalanobis": model.thresholds["mahalanobis"], "knn_distance": model.thresholds["knn"],
                       "subspace_residual": model.thresholds["residual"]},
        "threshold_capped_at_held_out_max": model.capped,
        "estimated_false_positive_rate": model.estimated_false_positive_rate,
        "false_positive_rate_interval_68": interval,
        "false_positive_estimate": f"two-fold cross-fit on {model.fp_tested} held-out training points "
                                   "(Clopper-Pearson 68.27% interval)",
        "effective_dimension": model.white.dim,
        "dropped_directions": model.white.dropped,
        "constant_features": const_names,
        "categorical_features": categorical,
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
    ap.add_argument("--status", default="unvalidated", choices=STATUSES,
                    help="status label of the input data, echoed as status_label in the output (default unvalidated)")
    ap.add_argument("--box-strict", action="store_true",
                    help="also mark a query 'outside' when any single coordinate leaves the training box")
    args = ap.parse_args(argv)
    try:
        with open(args.path, encoding="utf-8") as fh:
            payload = json.load(fh)
        import numpy as np

        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):  # overflow is caught as exit 3
            rep = check(payload, args.quantile, args.k, args.holdout_fraction, args.seed, args.box_strict)
            rep["status_label"] = args.status
            rep["status"] = "passed" if rep["passed"] else "failed"
        try:
            text = json.dumps(rep, indent=1, allow_nan=False)
        except ValueError as exc:  # a non-finite number reached the report
            raise NumericalFailure(str(exc)) from exc
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", "error": f"this check needs numpy and scipy: {exc}"}))
        return 3
    except NumericalFailure as exc:
        print(json.dumps({"status": "incomplete", "error": f"numerical failure: {exc}"}))
        return 3
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:  # malformed input is a JSON error
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(text)
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
