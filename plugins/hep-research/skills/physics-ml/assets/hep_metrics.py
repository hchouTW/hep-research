#!/usr/bin/env python3
"""Analysis metrics for physics classifiers, with signed event weights (NumPy only).

Functions:
  weighted_roc                  signal/background efficiency at every threshold, signed weights allowed
  weighted_auc                  area under the weighted ROC (trapezoid)
  efficiency_with_uncertainty   weighted efficiency and its MC-statistics uncertainty
  rejection_at_signal_efficiency  1/eps_B at a target eps_S (the tagger figure of merit)
  asimov_significance           expected discovery significance, optionally with a background uncertainty
  effective_entries             (sum w)^2 / sum w^2
  distance_correlation_sq       weighted dCor^2 (the DisCo penalty, NumPy reference implementation)
  mass_sculpting_jsd            Jensen-Shannon divergence of background mass passing vs failing a score cut
  undo_prior_shift              convert a classifier probability trained under one class prior to another

CLI: python3 hep_metrics.py events.csv --eff-s 0.3 0.5 0.7 [--mass-col m]
The CSV needs columns score,label (1 = signal) and optionally weight and a mass column. Output is JSON.
A successful run is a software check, not evidence that the classifier is valid for an analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys

import numpy as np


def _arrays(scores, labels, weights):
    s = np.asarray(scores, dtype=float).ravel()
    lab = np.asarray(labels).ravel()
    if lab.size and not np.all(np.isin(lab, (0, 1))):
        raise ValueError("labels must be 0 (background) or 1 (signal)")
    y = lab == 1
    w = np.ones_like(s) if weights is None else np.asarray(weights, dtype=float).ravel()
    if not (s.shape == y.shape == w.shape):
        raise ValueError(f"shape mismatch: scores {s.shape}, labels {y.shape}, weights {w.shape}")
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(w)):
        raise ValueError("non-finite scores or weights")
    return s, y, w


def weighted_roc(scores, labels, weights=None):
    """Return (thresholds, eff_s, eff_b) for cuts 'score >= threshold', from the highest threshold down.

    Signed weights are kept: the curve can be locally non-monotonic, which reflects MC statistics and is not
    clipped. Raises if the total signal or background weight is not positive.
    """
    s, y, w = _arrays(scores, labels, weights)
    order = np.argsort(-s, kind="mergesort")
    s, y, w = s[order], y[order], w[order]
    ws_tot, wb_tot = w[y].sum(), w[~y].sum()
    if ws_tot <= 0 or wb_tot <= 0:
        raise ValueError(f"total signal weight {ws_tot} and background weight {wb_tot} must be positive")
    cs = np.cumsum(np.where(y, w, 0.0))
    cb = np.cumsum(np.where(~y, w, 0.0))
    last = np.r_[s[1:] != s[:-1], True]          # keep one point per distinct score (ties cut together)
    thr = s[last]
    return thr, cs[last] / ws_tot, cb[last] / wb_tot


def weighted_auc(scores, labels, weights=None):
    """Area under (eff_b, eff_s); 0.5 = no separation. Ties are handled by the trapezoid rule."""
    _, es, eb = weighted_roc(scores, labels, weights)
    es, eb = np.r_[0.0, es], np.r_[0.0, eb]
    return float(np.sum(np.diff(eb) * (es[1:] + es[:-1]) / 2.0))


def efficiency_with_uncertainty(passed, weights=None):
    """Weighted efficiency W_pass/W_tot and its MC-statistics uncertainty.

    Var = [(1-eps)^2 sum_pass w^2 + eps^2 sum_fail w^2] / W_tot^2 (independent events). For unit weights this
    reduces to the binomial eps(1-eps)/N. It is a normal approximation: near 0 or 1 or with few effective
    entries, use an exact or bootstrap interval instead.
    """
    p = np.asarray(passed).astype(bool).ravel()
    w = np.ones(p.shape) if weights is None else np.asarray(weights, dtype=float).ravel()
    tot = w.sum()
    if tot <= 0:
        raise ValueError("total weight must be positive")
    eps = w[p].sum() / tot
    var = ((1 - eps) ** 2 * np.sum(w[p] ** 2) + eps ** 2 * np.sum(w[~p] ** 2)) / tot ** 2
    return float(eps), float(math.sqrt(max(var, 0.0)))


def rejection_at_signal_efficiency(scores, labels, weights=None, eff_s=0.5):
    """Background rejection 1/eps_B at the first (highest) threshold where eps_S >= eff_s.

    Returns a dict with threshold, achieved eps_S, eps_B with uncertainty, and rejection (inf if eps_B <= 0).
    The threshold is chosen on the sample given: choose it on a validation split and evaluate on a test split.
    """
    if not 0.0 < eff_s <= 1.0:
        raise ValueError(f"eff_s must be in (0, 1], got {eff_s}")
    s, y, w = _arrays(scores, labels, weights)
    thr, es, _ = weighted_roc(s, y, w)
    idx = np.flatnonzero(es >= eff_s - 1e-12)          # tolerance: the cumulative sum rounds below 1.0
    if idx.size == 0:
        raise ValueError(f"signal efficiency {eff_s} is never reached")
    t = thr[idx[0]]
    sel = s >= t
    es_val, es_unc = efficiency_with_uncertainty(sel[y], w[y])
    eb_val, eb_unc = efficiency_with_uncertainty(sel[~y], w[~y])
    out = {"target_eff_s": eff_s, "threshold": float(t), "eff_s": es_val, "eff_s_unc": es_unc,
           "eff_b": eb_val, "eff_b_unc": eb_unc, "rejection": None}
    if eb_val > 0:
        out["rejection"] = 1.0 / eb_val
        if eb_unc >= eb_val:
            out["warning"] = "eff_b uncertainty >= eff_b: the rejection is not measured at this working point"
    else:
        # No (or net negative) background weight passes. Report a lower bound, never infinity:
        # zero observed with ~N_eff effective events gives eff_b < 3/N_eff at about 95 % CL.
        n_eff = effective_entries(w[~y])
        out["warning"] = ("no net background weight passes the cut" if eb_val == 0
                          else "net negative background weight passes the cut (MC statistics)")
        out["rejection_lower_bound_95"] = n_eff / 3.0 if n_eff > 0 else None
    return out


def asimov_significance(s, b, sigma_b=None):
    """Median expected discovery significance in the Asimov approximation.

    Without sigma_b: Z = sqrt(2[(s+b) ln(1+s/b) - s]) (Cowan, Cranmer, Gross, Vitells, EPJC 71 (2011) 1554).
    With an absolute background uncertainty sigma_b (G. Cowan, "Discovery sensitivity for a counting experiment with
    background uncertainty", note, 2012, Eq. 20), which assumes sigma_b comes from an auxiliary Poisson control
    measurement (b_hat = m/tau, sigma_b^2 = b/tau):
    Z = sqrt(2[(s+b) ln((s+b)(b+sb2)/(b^2+(s+b)sb2)) - (b^2/sb2) ln(1 + sb2 s/(b(b+sb2)))]).
    """
    if b <= 0 or s < 0:
        raise ValueError("need b > 0 and s >= 0")
    if not sigma_b:
        return math.sqrt(2 * ((s + b) * math.log1p(s / b) - s))
    v = sigma_b ** 2
    t1 = (s + b) * math.log((s + b) * (b + v) / (b * b + (s + b) * v))
    t2 = (b * b / v) * math.log1p(v * s / (b * (b + v)))
    return math.sqrt(max(2 * (t1 - t2), 0.0))


def effective_entries(weights):
    w = np.asarray(weights, dtype=float)
    q = np.sum(w ** 2)
    return float(w.sum() ** 2 / q) if q > 0 else 0.0


def distance_correlation_sq(x, y, weights=None):
    """Weighted squared distance correlation dCor^2(x, y) in [0, 1] (0 iff independent, for large samples).

    Same estimator as the DisCo penalty (Kasieczka & Shih, arXiv:2001.05310): weights are normalized to mean one
    and enter like event multiplicities, so integer weights equal duplicated events. Use non-negative weights;
    distance correlation is not defined for signed weights. O(N^2) memory: subsample large inputs.
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    w = np.ones_like(x) if weights is None else np.asarray(weights, dtype=float).ravel()
    if np.any(w < 0):
        raise ValueError("distance correlation needs non-negative weights; pass |w|")
    if not w.sum() > 0:
        raise ValueError("weights sum to zero")
    w = w / w.mean()

    def centered(v):
        a = np.abs(v[:, None] - v[None, :])
        row = np.mean(a * w[None, :], axis=1)
        return a - row[None, :] - row[:, None] + np.mean(row * w)

    A, B = centered(x), centered(y)

    def dcov(P, Q):
        return np.mean(np.mean(P * Q * w[None, :], axis=1) * w)

    vx, vy = dcov(A, A), dcov(B, B)
    if vx <= 0 or vy <= 0:
        return 0.0
    return float(max(dcov(A, B), 0.0) / math.sqrt(vx * vy))


def _jsd(p, q):
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        nz = a > 0
        return np.sum(a[nz] * np.log2(a[nz] / b[nz]))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


def mass_sculpting_jsd(mass, scores, threshold, weights=None, bins=40, mass_range=None, baseline=False, seed=0):
    """JSD (base 2, in [0, 1]) between the background mass distributions passing and failing score >= threshold.

    Pass background events only. Report 1/JSD against background rejection at fixed signal efficiency; larger
    1/JSD = less sculpting. Histograms with negative bin contents are clipped to zero for the JSD only, and the
    number of clipped bins is returned so that the clipping is visible.

    The binned JSD is biased upward by statistical fluctuations (more bins, fewer passing events = larger bias).
    baseline=True adds "jsd_baseline": the JSD between a random subset of the failing events, of the same size as
    the passing set, and the remaining failing events, so the sculpting value can be compared with pure noise.
    """
    m = np.asarray(mass, dtype=float).ravel()
    sc = np.asarray(scores, dtype=float).ravel()
    w = np.ones_like(m) if weights is None else np.asarray(weights, dtype=float).ravel()
    rng = mass_range or (float(m.min()), float(m.max()))
    sel = sc >= threshold
    hp, _ = np.histogram(m[sel], bins=bins, range=rng, weights=w[sel])
    hf, _ = np.histogram(m[~sel], bins=bins, range=rng, weights=w[~sel])
    clipped = int(np.sum(hp < 0) + np.sum(hf < 0))
    hp, hf = np.clip(hp, 0, None), np.clip(hf, 0, None)
    if hp.sum() <= 0 or hf.sum() <= 0:
        raise ValueError("passing or failing histogram is empty")
    d = _jsd(hp, hf)
    out = {"jsd": d, "inverse_jsd": (1.0 / d) if d > 0 else math.inf, "clipped_bins": clipped,
           "n_pass": int(sel.sum()), "n_fail": int((~sel).sum())}
    if baseline:
        fail_idx = np.flatnonzero(~sel)
        k = min(int(sel.sum()), fail_idx.size // 2)
        if k > 0:
            pick = np.zeros(fail_idx.size, bool)
            pick[np.random.default_rng(seed).choice(fail_idx.size, k, replace=False)] = True
            a, b = fail_idx[pick], fail_idx[~pick]
            ha, _ = np.histogram(m[a], bins=bins, range=rng, weights=w[a])
            hb, _ = np.histogram(m[b], bins=bins, range=rng, weights=w[b])
            ha, hb = np.clip(ha, 0, None), np.clip(hb, 0, None)
            if ha.sum() > 0 and hb.sum() > 0:
                out["jsd_baseline"] = _jsd(ha, hb)
    return out


def undo_prior_shift(prob, prior_ratio_change):
    """Map p(s|x) learned with class-odds pi_s/pi_b = O_train to odds O_phys: r = O_phys / O_train."""
    p = np.asarray(prob, dtype=float)
    r = float(prior_ratio_change)
    return r * p / (r * p + 1.0 - p)


def _read_csv(path, mass_col):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "score" not in rows[0] or "label" not in rows[0]:
        raise ValueError("CSV needs columns 'score' and 'label'")
    s = np.array([float(r["score"]) for r in rows])
    y = np.array([int(float(r["label"])) for r in rows])
    w = np.array([float(r["weight"]) for r in rows]) if "weight" in rows[0] else None
    m = np.array([float(r[mass_col]) for r in rows]) if mass_col else None
    return s, y, w, m


def _sanitize(o):
    """Replace non-finite floats by None so the output is strict JSON."""
    if isinstance(o, dict):
        return {k: _sanitize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_sanitize(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", help="CSV with columns score,label[,weight][,mass]")
    ap.add_argument("--eff-s", type=float, nargs="+", default=[0.3, 0.5, 0.7], help="signal efficiencies")
    ap.add_argument("--mass-col", help="column for the mass-sculpting check (background only)")
    a = ap.parse_args(argv)
    try:
        s, y, w, m = _read_csv(a.csv, a.mass_col)
        out = {"n_events": int(s.size), "auc_weighted": weighted_auc(s, y, w),
               "n_eff_signal": effective_entries(w[y == 1]) if w is not None else int(np.sum(y == 1)),
               "n_eff_background": effective_entries(w[y == 0]) if w is not None else int(np.sum(y == 0)),
               "working_points": []}
        for e in a.eff_s:
            wp = rejection_at_signal_efficiency(s, y, w, e)
            if m is not None:
                b = y == 0
                try:
                    wp["sculpting"] = mass_sculpting_jsd(m[b], s[b], wp["threshold"], None if w is None else w[b],
                                                         baseline=True)
                except ValueError as exc:   # e.g. no background passes: report, keep the other numbers
                    wp["sculpting"] = {"error": str(exc)}
            out["working_points"].append(wp)
        if w is not None and np.any(w < 0):
            out["note"] = "signed weights present: curves may be locally non-monotonic; not clipped"
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_sanitize(out), indent=2, allow_nan=False, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
