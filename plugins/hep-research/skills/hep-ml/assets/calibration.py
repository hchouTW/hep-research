#!/usr/bin/env python3
"""Post-hoc calibration of binary classifier scores, with event weights (NumPy; SciPy optional).

Functions:
  fit_temperature        T minimizing the weighted NLL of sigmoid(logit / T) (1-D bounded minimization)
  fit_platt              a, b minimizing the weighted NLL of sigmoid(a * logit + b) (Newton, damped)
  fit_isotonic           weighted pool-adjacent-violators; returns a monotone map with linear interpolation
  reliability_curve      per-bin weighted mean predicted vs observed, with a weighted binomial uncertainty
  expected_calibration_error / max_calibration_error   weighted ECE and MCE from a reliability table
  ece_noise_floor        expected ECE of a perfectly calibrated model with the same bins (finite-sample floor)
  sample_provenance      checks and records that calibration is fit and evaluated on disjoint samples

CLI: python3 calibration.py --fit fit.csv --eval eval.csv --method temperature [--bins 15 --binning equal-mass]
Inputs are CSV (columns score,label[,weight][,id]) or JSON ({"score": [...], "label": [...], "weight": [...]} or a
list of such records). Output is strict JSON with a top-level "calibration" block (copy it into the ml-artifact)
plus the reliability tables before and after. A successful run is a software check: it says the map was fit and
evaluated on the samples given, not that the calibration holds on data or under a domain shift.

Separate samples. The map is fit on --fit and judged on --eval. The CLI refuses identical files (same path or same
content hash) and overlapping event ids (--id-col, required unless --no-id-check) unless --allow-same-sample is
given; the override is recorded in the output. The record of that check ("sample_check": names, both sha256 values,
the id check, "disjoint") sits inside the "calibration" block, so the ml-artifact carries it and the validator refuses
a calibration evaluated on its fit sample. An ECE measured on the fit sample is optimistic, most of all for isotonic regression.

Negative weights (NLO generators, sWeights, subtraction):
  * temperature and Platt: signed weights are kept. A one- or two-parameter fit cannot isolate single events, so
    the weighted NLL stays a sensible ratio estimator. Each class needs positive net weight; otherwise ValueError.
  * isotonic: refused by default. PAV pools adjacent blocks and averages them with their weights; a block with net
    weight <= 0 has no defined mean and breaks the monotone pooling. negative_weights="merge" (CLI
    --isotonic-negative-weights merge) first merges events adjacent in score into cells whose net weight is at
    least half of their sum |w| (a one-dimensional cell resampling that keeps the local net weight), then runs PAV
    on the cells. Fitted values outside [0, 1] are clipped and counted. Clipping negative weights to zero is not
    offered: it is the same as dropping those events, which biases the result (ml-analysis.md, "Negative weights").
  * reliability/ECE: signed weights are kept per bin. Equal-mass edges use |w|. A bin with net weight <= 0 is
    reported with null values and left out of ECE and MCE; the count of such bins is in the table.

Prior shift. A classifier trained on class-balanced samples estimates p(s|x) under the training prior. Calibrate
against the prior that the probability will be used with: either undo the class balancing first
(hep_metrics.undo_prior_shift; the CLI option --prior-ratio-change r applies it to the fit and eval scores before
calibration) and calibrate on a sample weighted to the physics prior, or calibrate directly on a sample with
physics weights. Do not apply undo_prior_shift after a map that was already fit on physics-weighted data: the prior
would be corrected twice.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

_EPS = 1e-12


# --------------------------------------------------------------------------- helpers

def _arrays(scores, labels, weights=None):
    s = np.asarray(scores, dtype=float).ravel()
    lab = np.asarray(labels).ravel()
    if lab.size and not np.all(np.isin(lab, (0, 1))):
        raise ValueError("labels must be 0 or 1")
    y = (lab == 1).astype(float)
    w = np.ones_like(s) if weights is None else np.asarray(weights, dtype=float).ravel()
    if not (s.shape == y.shape == w.shape):
        raise ValueError(f"shape mismatch: scores {s.shape}, labels {y.shape}, weights {w.shape}")
    if s.size == 0:
        raise ValueError("empty input")
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(w)):
        raise ValueError("non-finite scores or weights")
    return s, y, w


def _check_class_weights(y, w):
    ws, wb = w[y == 1].sum(), w[y == 0].sum()
    if ws <= 0 or wb <= 0:
        raise ValueError(f"net signal weight {ws} and background weight {wb} must both be positive")


def sigmoid(z):
    z = np.asarray(z, dtype=float)
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-np.abs(z))), np.exp(-np.abs(z)) / (1.0 + np.exp(-np.abs(z))))


def logit(p, eps=_EPS):
    p = np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)
    return np.log(p) - np.log1p(-p)


def _nll_from_logits(z, y, w):
    """Weighted mean binary NLL on logits, normalized by sum(w); log(1+exp(-|z|)) form for stability."""
    per = np.maximum(z, 0) - z * y + np.log1p(np.exp(-np.abs(z)))
    return float(np.sum(w * per) / np.sum(w))


def weighted_nll(prob, labels, weights=None):
    p, y, w = _arrays(prob, labels, weights)
    return _nll_from_logits(logit(p), y, w)


def _golden_min(f, lo, hi, tol=1e-8, maxiter=200):
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(maxiter):
        if abs(b - a) < tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    return (a + b) / 2


# --------------------------------------------------------------------------- calibration maps

def fit_temperature(logits, labels, weights=None, bounds=(0.05, 20.0)):
    """Temperature T > 0 minimizing the weighted NLL of sigmoid(logits / T).

    One-dimensional bounded minimization in log T (scipy.optimize.minimize_scalar if available, else golden
    section). T > 1 softens an over-confident model; T = 1 is the identity. A result at a bound is reported as
    such (at_bound=True) and should not be trusted. Ranking, ROC and AUC are unchanged.
    """
    z, y, w = _arrays(logits, labels, weights)
    _check_class_weights(y, w)
    lo, hi = math.log(bounds[0]), math.log(bounds[1])

    def f(log_t):
        return _nll_from_logits(z / math.exp(log_t), y, w)

    try:
        from scipy.optimize import minimize_scalar
        res = minimize_scalar(f, bounds=(lo, hi), method="bounded", options={"xatol": 1e-9})
        log_t, backend = float(res.x), "scipy.minimize_scalar(bounded)"
    except ImportError:
        log_t, backend = _golden_min(f, lo, hi), "golden-section"
    t = math.exp(log_t)
    at_bound = abs(log_t - lo) < 1e-4 or abs(log_t - hi) < 1e-4
    return {"temperature": t, "nll": f(log_t), "at_bound": bool(at_bound), "backend": backend}


def apply_temperature(logits, temperature):
    return sigmoid(np.asarray(logits, dtype=float) / float(temperature))


def fit_platt(logits, labels, weights=None, max_iter=100, tol=1e-10):
    """Platt scaling: a, b minimizing the weighted NLL of sigmoid(a * logit + b). Damped Newton iterations.

    Without the target smoothing of Platt's original paper (the targets are 0 and 1). With signed weights the
    Hessian need not be positive definite; a Levenberg damping term is added until it is.
    """
    z, y, w = _arrays(logits, labels, weights)
    _check_class_weights(y, w)
    X = np.c_[z, np.ones_like(z)]
    theta = np.array([1.0, 0.0])
    W = w.sum()

    def loss(th):
        return _nll_from_logits(X @ th, y, w)

    cur = loss(theta)
    n_iter = 0
    for _ in range(max_iter):
        n_iter += 1
        p = sigmoid(X @ theta)
        grad = X.T @ (w * (p - y)) / W
        H = (X * (w * p * (1 - p))[:, None]).T @ X / W
        lam = 0.0
        while True:
            try:
                Hd = H + lam * np.eye(2)
                np.linalg.cholesky(Hd)
                break
            except np.linalg.LinAlgError:
                lam = max(1e-8, 10 * lam)
        step = np.linalg.solve(Hd, grad)
        alpha = 1.0
        while alpha > 1e-10:
            new = theta - alpha * step
            nl = loss(new)
            if nl <= cur:
                break
            alpha /= 2
        else:
            break
        theta, prev, cur = new, cur, nl
        if abs(prev - cur) < tol and np.max(np.abs(alpha * step)) < 1e-8:
            break
    return {"a": float(theta[0]), "b": float(theta[1]), "nll": cur, "iterations": n_iter}


def apply_platt(logits, a, b):
    return sigmoid(float(a) * np.asarray(logits, dtype=float) + float(b))


def _merge_to_positive_cells(x, w, wy, w_abs, min_net_fraction=0.5):
    """Merge score-adjacent points (sorted by x) into cells with sum(w) >= min_net_fraction * sum|w| > 0.

    Inputs are per-point net weight w, weighted label sum wy and sum |w|. Returns per-cell (lo, hi, value, weight)
    with value = sum(w y) / sum(w). A trailing remainder with too little net weight is merged into the last cell.
    """
    lo_l, hi_l, w_l, wy_l = [], [], [], []
    acc_w = acc_abs = acc_wy = 0.0
    lo = None
    for xi, wi, wyi, ai in zip(x, w, wy, w_abs):
        lo = xi if lo is None else lo
        acc_w += wi
        acc_abs += ai
        acc_wy += wyi
        if acc_w > 0 and acc_w >= min_net_fraction * acc_abs:
            lo_l.append(lo)
            hi_l.append(xi)
            w_l.append(acc_w)
            wy_l.append(acc_wy)
            acc_w = acc_abs = acc_wy = 0.0
            lo = None
    if lo is not None:
        if not w_l or w_l[-1] + acc_w <= 0:
            raise ValueError("negative weight at the high-score end cannot be merged into a positive cell")
        w_l[-1] += acc_w
        wy_l[-1] += acc_wy
        hi_l[-1] = x[-1]
    w_a = np.array(w_l)
    return np.array(lo_l), np.array(hi_l), np.array(wy_l) / w_a, w_a


def pav(values, weights):
    """Weighted pool-adjacent-violators for a non-decreasing fit. Weights must be positive.

    Returns (fitted values per input point, list of blocks as (start, stop) index ranges).
    """
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    if np.any(w <= 0):
        raise ValueError("PAV needs positive weights")
    means, wsum, starts = [], [], []
    for i in range(v.size):
        means.append(v[i])
        wsum.append(w[i])
        starts.append(i)
        while len(means) > 1 and means[-2] > means[-1]:
            m2, w2 = means.pop(), wsum.pop()
            starts.pop()
            m1, w1 = means[-1], wsum[-1]
            wsum[-1] = w1 + w2
            means[-1] = (m1 * w1 + m2 * w2) / (w1 + w2)
    fitted = np.empty_like(v)
    bounds = starts[1:] + [v.size]
    blocks = []
    for m, a, b in zip(means, starts, bounds):
        fitted[a:b] = m
        blocks.append((a, b))
    return fitted, blocks


class IsotonicMap:
    """Monotone non-decreasing map score -> probability: knots (x, y) with linear interpolation between them,
    constant outside the fitted range (the same convention as scikit-learn's IsotonicRegression)."""

    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)

    def __call__(self, scores):
        return np.interp(np.asarray(scores, dtype=float), self.x, self.y)

    def params(self):
        return {"x": [float(a) for a in self.x], "y": [float(b) for b in self.y], "interpolation": "linear"}


def fit_isotonic(scores, labels, weights=None, negative_weights="refuse"):
    """Weighted isotonic regression of the label on the score (pool-adjacent-violators).

    Tied scores are pooled first. negative_weights: "refuse" (default) raises on any negative weight; "merge"
    merges score-adjacent events into positive-net-weight cells before PAV (see the module docstring). Returns
    (IsotonicMap, info dict).
    """
    s, y, w = _arrays(scores, labels, weights)
    _check_class_weights(y, w)
    if negative_weights not in ("refuse", "merge"):
        raise ValueError("negative_weights must be 'refuse' or 'merge'")
    n_neg = int(np.sum(w < 0))
    if n_neg and negative_weights == "refuse":
        raise ValueError(f"{n_neg} negative weights: isotonic regression refuses them by default; "
                         "use negative_weights='merge' (documented) or calibrate with temperature/Platt")
    keep = w != 0
    s, y, w = s[keep], y[keep], w[keep]
    order = np.argsort(s, kind="mergesort")
    s, y, w = s[order], y[order], w[order]
    # pool ties: one point per distinct score with its net weight
    ux, inv = np.unique(s, return_inverse=True)
    sw = np.bincount(inv, weights=w)
    swy = np.bincount(inv, weights=w * y)
    info = {"negative_weights": negative_weights, "n_negative": n_neg, "n_clipped": 0}
    if n_neg:
        lo, hi, vals, cw = _merge_to_positive_cells(ux, sw, swy, np.bincount(inv, weights=np.abs(w)))
        info["n_cells"] = int(cw.size)
    else:
        lo, hi, vals, cw = ux, ux, swy / sw, sw
    fitted, blocks = pav(vals, cw)
    xs, ys = [], []
    for a, b in blocks:
        xs += [lo[a], hi[b - 1]]
        ys += [fitted[a], fitted[a]]
    xs, ys = np.array(xs, dtype=float), np.array(ys, dtype=float)
    info["n_clipped"] = int(sum(1 for a, _ in blocks if not 0.0 <= fitted[a] <= 1.0))   # blocks out of [0, 1]
    ys = np.clip(ys, 0.0, 1.0)
    keep = np.r_[True, np.diff(xs) > 0]      # a block with one distinct score has lo == hi: keep one knot
    xs, ys = xs[keep], ys[keep]
    info["n_blocks"] = len(blocks)
    return IsotonicMap(xs, ys), info


# --------------------------------------------------------------------------- reliability and ECE

def _weighted_quantile_edges(p, w_abs, n_bins):
    order = np.argsort(p, kind="mergesort")
    ps, ws = p[order], w_abs[order]
    c = np.cumsum(ws)
    tot = c[-1]
    edges = []
    for k in range(1, n_bins):
        i = int(np.searchsorted(c, k / n_bins * tot - 1e-12 * tot, side="left"))
        edges.append(ps[min(i, ps.size - 1)])
    return np.unique(np.array(edges))


def reliability_curve(prob, labels, weights=None, n_bins=15, binning="equal-width"):
    """Weighted reliability table on predicted probabilities in [0, 1].

    Per bin: net weight W = sum w, mean predicted sum(w p)/W, observed fraction f = sum(w y)/W and its uncertainty
    sqrt([(1-f)^2 sum_{y=1} w^2 + f^2 sum_{y=0} w^2]) / W, which is the binomial sqrt(f(1-f)/N) for unit weights
    (the same formula as hep_metrics.efficiency_with_uncertainty). Equal-width bins split [0, 1]; equal-mass bins
    put the same sum |w| in each bin (tied probabilities can merge bins: n_bins_effective says how many remain).
    """
    p, y, w = _arrays(prob, labels, weights)
    if np.any(p < 0) or np.any(p > 1):
        raise ValueError("predicted probabilities must lie in [0, 1]")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    if binning == "equal-width":
        idx = np.minimum((p * n_bins).astype(int), n_bins - 1)
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        nb = n_bins
    elif binning == "equal-mass":
        inner = _weighted_quantile_edges(p, np.abs(w), n_bins)
        idx = np.searchsorted(inner, p, side="left")
        edges = np.r_[0.0, inner, 1.0]
        nb = inner.size + 1
    else:
        raise ValueError("binning must be 'equal-width' or 'equal-mass'")
    rows = []
    for b in range(nb):
        sel = idx == b
        wb = w[sel]
        W = float(wb.sum())
        row = {"bin": b, "lo": float(edges[b]), "hi": float(edges[b + 1]), "n": int(sel.sum()), "sum_w": W,
               "sum_w2": float(np.sum(wb ** 2)), "mean_pred": None, "observed": None, "observed_unc": None}
        if sel.any() and W > 0:
            f = float(np.sum(wb * y[sel]) / W)
            var = ((1 - f) ** 2 * np.sum(wb[y[sel] == 1] ** 2) + f ** 2 * np.sum(wb[y[sel] == 0] ** 2)) / W ** 2
            row.update(mean_pred=float(np.sum(wb * p[sel]) / W), observed=f, observed_unc=float(math.sqrt(var)))
        rows.append(row)
    n_bad = sum(1 for r in rows if r["n"] > 0 and r["sum_w"] <= 0)
    return {"binning": binning, "n_bins": n_bins, "n_bins_effective": nb, "n_nonpositive_weight_bins": n_bad,
            "bins": rows}


def _valid_rows(table):
    return [r for r in table["bins"] if r["observed"] is not None]


def expected_calibration_error(table):
    """Weighted ECE = sum_b (W_b / W) |observed_b - mean_pred_b| over bins with positive net weight."""
    rows = _valid_rows(table)
    tot = sum(r["sum_w"] for r in rows)
    if tot <= 0:
        raise ValueError("no bin with positive net weight")
    return float(sum(r["sum_w"] / tot * abs(r["observed"] - r["mean_pred"]) for r in rows))


def max_calibration_error(table):
    rows = _valid_rows(table)
    if not rows:
        raise ValueError("no bin with positive net weight")
    return float(max(abs(r["observed"] - r["mean_pred"]) for r in rows))


def ece_noise_floor(table):
    """Expected ECE of a perfectly calibrated model with these bins: sum_b (W_b/W) sqrt(2/pi) sigma_b, with
    sigma_b the binomial spread at the bin's mean prediction and its effective entries (sum w)^2/sum w^2."""
    rows = _valid_rows(table)
    tot = sum(r["sum_w"] for r in rows)
    out = 0.0
    for r in rows:
        n_eff = r["sum_w"] ** 2 / r["sum_w2"] if r["sum_w2"] > 0 else 0.0
        if n_eff > 0:
            p = r["mean_pred"]
            out += r["sum_w"] / tot * math.sqrt(2 / math.pi) * math.sqrt(max(p * (1 - p), 0.0) / n_eff)
    return float(out)


def calibration_report(prob, labels, weights=None, n_bins=15, binning="equal-width"):
    t = reliability_curve(prob, labels, weights, n_bins, binning)
    return {"ece": expected_calibration_error(t), "mce": max_calibration_error(t), "ece_floor": ece_noise_floor(t),
            "table": t}


# --------------------------------------------------------------------------- sample provenance

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_provenance(fit_sample, eval_sample, fit_ids=None, eval_ids=None, allow_same_sample=False):
    """Check that the calibration fit and evaluation samples are disjoint, and return a record of the check.

    fit_sample / eval_sample are names or file paths. Files are compared by path and by content hash; event ids,
    when given, are compared for overlap. Raises ValueError when the samples are the same or overlap, unless
    allow_same_sample=True, in which case the record says so ("disjoint": false, "same_sample_allowed": true).
    """
    rec = {"fit_sample": str(fit_sample), "eval_sample": str(eval_sample), "checks": [], "disjoint": None,
           "same_sample_allowed": bool(allow_same_sample)}
    same = str(fit_sample) == str(eval_sample)
    rec["checks"].append("name")
    if os.path.isfile(str(fit_sample)) and os.path.isfile(str(eval_sample)):
        rec["fit_sha256"], rec["eval_sha256"] = _sha256(fit_sample), _sha256(eval_sample)
        same = same or os.path.samefile(fit_sample, eval_sample) or rec["fit_sha256"] == rec["eval_sha256"]
        rec["checks"].append("sha256")
    overlap = 0
    if fit_ids is not None and eval_ids is not None:
        overlap = len(set(map(str, fit_ids)) & set(map(str, eval_ids)))
        rec["checks"].append("event-id")
        rec["id_overlap"] = overlap
    rec["disjoint"] = not same and overlap == 0
    if not rec["disjoint"] and not allow_same_sample:
        why = "the same sample" if same else f"{overlap} shared event ids"
        raise ValueError(f"calibration fit and evaluation samples are not disjoint ({why}); give a separate "
                         "evaluation sample, or pass --allow-same-sample / allow_same_sample=True (recorded)")
    return rec


def calibration_outcome(before, after, floor):
    """improved, no-op-within-floor (both ECEs within the finite-sample floor of each other) or worse."""
    if before is None or after is None:
        return "not-evaluated"
    if after < before - (floor or 0.0):
        return "improved"
    if after <= before + (floor or 0.0):
        return "no-op-within-floor"
    return "worse"


# --------------------------------------------------------------------------- CLI

def _read(path, id_col=None):
    if path.lower().endswith(".json"):
        with open(path) as fh:
            d = json.load(fh)
        if isinstance(d, list):
            d = {k: [r[k] for r in d] for k in d[0]} if d else {}
    else:
        with open(path, newline="") as fh:
            rows = list(csv.DictReader(fh))
        d = {k: [r[k] for r in rows] for k in rows[0]} if rows else {}
    if "score" not in d or "label" not in d:
        raise ValueError(f"{path}: needs 'score' and 'label'")
    s = np.array([float(v) for v in d["score"]])
    y = np.array([_label(v, path) for v in d["label"]])
    w = np.array([float(v) for v in d["weight"]]) if "weight" in d else None
    if id_col and id_col not in d:
        raise ValueError(f"{path}: id column {id_col!r} missing")
    ids = list(d[id_col]) if id_col else None
    return s, y, w, ids


def _label(value, path):
    """0/1 class label; a fractional label is refused, never truncated (the same rule as hep_metrics.py)."""
    x = float(value)
    if x not in (0.0, 1.0):
        raise ValueError(f"{path}: label {value!r} is not 0 or 1 (a fractional label is not truncated)")
    return int(x)


def _sanitize(o):
    if isinstance(o, dict):
        return {k: _sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sanitize(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def _summary(path, s, y, w):
    ww = np.ones_like(s) if w is None else w
    return {"path": path, "n_events": int(s.size), "n_signal": int(np.sum(y == 1)), "sum_w": float(ww.sum()),
            "n_negative_weights": int(np.sum(ww < 0)),
            "sha256": _sha256(path) if os.path.isfile(path) else None}


def main(argv=None):
    sys.dont_write_bytecode = True  # the import below leaves no __pycache__ (F-10)
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
    from core.status import add_status_argument
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog="Fit and evaluation samples must be disjoint; see the module docstring.")
    add_status_argument(ap)
    ap.add_argument("--fit", required=True, help="sample to fit the calibration map on (CSV or JSON)")
    ap.add_argument("--eval", required=True, help="separate sample to evaluate it on (CSV or JSON)")
    ap.add_argument("--method", choices=("temperature", "isotonic", "platt"), default="temperature")
    ap.add_argument("--score-kind", choices=("prob", "logit"), default="prob",
                    help="whether 'score' is a probability in [0, 1] or a logit")
    ap.add_argument("--bins", type=int, default=15)
    ap.add_argument("--binning", choices=("equal-width", "equal-mass"), default="equal-width")
    ap.add_argument("--id-col", help="event-id column to check that fit and eval do not overlap (required unless "
                    "--no-id-check: a file hash alone misses a copy with one byte changed)")
    ap.add_argument("--no-id-check", action="store_true",
                    help="samples have no event ids; disjointness rests on names and hashes only (recorded)")
    ap.add_argument("--allow-same-sample", action="store_true",
                    help="allow fit == eval (optimistic ECE); recorded in the output")
    ap.add_argument("--isotonic-negative-weights", choices=("refuse", "merge"), default="refuse")
    ap.add_argument("--prior-ratio-change", type=float,
                    help="apply hep_metrics.undo_prior_shift with this r to the scores before calibration")
    a = ap.parse_args(argv)
    try:
        if a.bins < 1:
            raise ValueError("--bins must be >= 1")
        if not a.id_col and not a.no_id_check:
            raise ValueError("--id-col is required to check that fit and eval share no event (pass --no-id-check "
                             "when the samples have no ids; it is recorded)")
        fs, fy, fw, fid = _read(a.fit, a.id_col)
        es, ey, ew, eid = _read(a.eval, a.id_col)
        prov = sample_provenance(a.fit, a.eval, fid, eid, a.allow_same_sample)
        prov["id_check"] = f"column {a.id_col}" if a.id_col else "skipped (--no-id-check)"

        def to_logit(s):
            return s if a.score_kind == "logit" else logit(s)

        fz, ez = to_logit(fs), to_logit(es)
        prior = None
        if a.prior_ratio_change is not None:
            r = a.prior_ratio_change
            if not math.isfinite(r) or r <= 0:
                raise ValueError("--prior-ratio-change must be a finite positive odds ratio")
            fz, ez = fz + math.log(r), ez + math.log(r)     # r p/(r p + 1 - p) == sigmoid(logit p + ln r)
            prior = {"applied": "hep_metrics.undo_prior_shift", "prior_ratio_change": r,
                     "note": "applied to fit and eval scores before calibration"}
        before_p = sigmoid(ez)
        extra = {}
        if a.method == "temperature":
            res = fit_temperature(fz, fy, fw)
            params = {"temperature": res["temperature"]}
            after_p = apply_temperature(ez, res["temperature"])
            extra = {k: res[k] for k in ("nll", "at_bound", "backend")}
        elif a.method == "platt":
            res = fit_platt(fz, fy, fw)
            params = {"a": res["a"], "b": res["b"], "input": "logit"}
            after_p = apply_platt(ez, res["a"], res["b"])
            extra = {k: res[k] for k in ("nll", "iterations")}
        else:
            fmap, info = fit_isotonic(sigmoid(fz), fy, fw, a.isotonic_negative_weights)
            params = dict(fmap.params(), input="probability")
            after_p = fmap(sigmoid(ez))
            extra = info
        warnings = []
        if a.method == "temperature":
            if extra.get("at_bound"):
                warnings.append(f"the temperature {params['temperature']:.4g} sits at its search bound: the map is "
                                "not a minimum of the loss; check the scores or use Platt")
            if prior is None:
                warnings.append("temperature scaling rescales the logit only: it cannot correct a prior (class-ratio) "
                                "shift; give --prior-ratio-change or use Platt, which also fits an offset")
        rb = calibration_report(before_p, ey, ew, a.bins, a.binning)
        ra = calibration_report(after_p, ey, ew, a.bins, a.binning)
        out = {
            "calibration": {
                "method": a.method, "params": params, "fit_sample": a.fit,
                "validation": {"metric": "ece", "sample": a.eval, "before": rb["ece"], "after": ra["ece"],
                               "bins": a.bins, "binning": a.binning, "floor": ra["ece_floor"]},
                "sample_check": prov,
                "outcome": calibration_outcome(rb["ece"], ra["ece"], ra["ece_floor"]),
                "warnings": warnings,
            },
            "fit_details": extra,
            "sample_check": prov,
            "inputs": {"fit": _summary(a.fit, fs, fy, fw), "eval": _summary(a.eval, es, ey, ew)},
            "prior_shift": prior,
            "metrics": {"ece_before": rb["ece"], "ece_after": ra["ece"], "mce_before": rb["mce"],
                        "mce_after": ra["mce"], "ece_floor_after": ra["ece_floor"],
                        "nll_before": weighted_nll(before_p, ey, ew), "nll_after": weighted_nll(after_p, ey, ew)},
            "reliability": {"before": rb["table"], "after": ra["table"]},
            "note": "software check on the samples given; re-check calibration per slice and under the "
                    "deployment shift",
        }
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(_sanitize({"status": "ok", "status_label": a.status, **out}), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
