#!/usr/bin/env python3
"""Global significance of a search by repeating the complete procedure in toys (audit T28). EXPERIMENTAL. Needs NumPy.

The procedure is what was done to the data, and the toys repeat all of it: a scan over signal hypotheses (a 1D grid in
position, or a 2D grid in position and width), the background normalization refitted at every scan point (free or
Gaussian-constrained) or held fixed, and the choice among several selection variants (cuts or catalogs: the best
variant is picked inside every toy, as it was on the data). A variant may be a subset of an earlier one
({"subset_of": "loose", "efficiency": [per bin]}): its toy counts are then a binomial thinning of the parent's toy
counts, so overlapping selections stay correlated in the toys. Toy t uses seeds derived from (seed, t, variant), so a
finer grid or an added variant sees the same toy data. Local statistic: q0 = 2 [ln L(mu_hat, k_hat) -
ln L(0, k_hat0)] for mu_hat > 0, else 0. Local p (asymptotic, half chi2) and, from the same background-only toys,
the toy-calibrated local p at the best point; global p = the fraction of toys whose maximum q0 over the whole
procedure reaches the observed maximum, with its exact binomial interval (a bound with zero exceedances). The toys are
generated at the background-only fit to the data (conditional ensemble), with the constraint's auxiliary measurement
redrawn when the normalization is constrained.

Gross-Vitells (1D, one degree of freedom, upcrossings counted at a reference level in the same toys) is reported only
as a check of the toys where it is valid: when it disagrees with the toys beyond their 99% interval, or the scan is 2D,
or the procedure selects among variants, it is flagged not validated here and never replaces the toys.

Input JSON: {"bin_centers": [...], "variants": [{"name": "loose", "background": [b_i], "observed": [n_i]}, ...],
  "scan": {"positions": [...], "widths": [w] (one width: 1D; several: 2D)},
  "background_normalization": {"kind": "fixed" | "free" | "constrained", "sigma": 0.1}}
Usage: global_significance.py run --input FILE --toys N --seed S
Exit codes: 0 ok; 2 bad input. Output JSON labelled [General method] EXPERIMENTAL.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.stats.tail_estimation import clopper_pearson, toy_tail  # noqa: E402

LABEL = "[General method] EXPERIMENTAL"


def templates(x, positions, widths):
    t = []
    for w in widths:
        for m in positions:
            s = np.exp(-0.5 * ((x - m) / w) ** 2)
            t.append(s / s.sum())
    return np.array(t), [(float(m), float(w)) for w in widths for m in positions]


def _fit(n, b, s, norm, aux, start=None, iters=40):
    """Max ln L over mu (>= 0 when s is given) and the background scale k for one template; returns (lnL, mu, k)."""
    def lnl(mu, k):
        nu = mu * s + k * b if s is not None else k * b
        nu = np.maximum(nu, 1e-300)
        val = float(np.sum(n * np.log(nu) - nu))
        if norm["kind"] == "constrained":
            val -= 0.5 * ((k - aux) / norm["sigma"]) ** 2
        return val
    if norm["kind"] == "fixed":
        if s is None:
            return lnl(0.0, 1.0), 0.0, 1.0
        mu = max(float(n @ s - s.sum()), 0.0) / max(s.sum(), 1e-12)
        for _ in range(iters):
            nu = mu * s + b
            g = float(np.sum(n * s / nu) - s.sum())
            h = -float(np.sum(n * s * s / nu ** 2)) - 1e-12
            new = max(mu - g / h, 0.0)
            if abs(new - mu) < 1e-10:
                mu = new
                break
            mu = new
        return lnl(mu, 1.0), mu, 1.0
    mu, k = (0.0, 1.0) if start is None else start
    free_mu = s is not None
    for _ in range(iters):
        nu = np.maximum(mu * s + k * b if free_mu else k * b, 1e-300)
        r = n / nu
        gk = float(np.sum(r * b) - b.sum())
        hkk = -float(np.sum(n * b * b / nu ** 2))
        if norm["kind"] == "constrained":
            gk -= (k - aux) / norm["sigma"] ** 2
            hkk -= 1.0 / norm["sigma"] ** 2
        if free_mu:
            gm = float(np.sum(r * s) - s.sum())
            hmm = -float(np.sum(n * s * s / nu ** 2))
            hmk = -float(np.sum(n * s * b / nu ** 2))
            det = hmm * hkk - hmk * hmk
            if det <= 0:
                break
            dm, dk = -(hkk * gm - hmk * gk) / det, -(hmm * gk - hmk * gm) / det
        else:
            dm, dk = 0.0, -gk / hkk
        new_mu, new_k = (max(mu + dm, 0.0) if free_mu else 0.0), max(k + dk, 1e-6)
        if abs(new_mu - mu) < 1e-10 and abs(new_k - k) < 1e-10:
            mu, k = new_mu, new_k
            break
        mu, k = new_mu, new_k
    return lnl(mu, k), mu, k


def q0_all(n, b, temps, norm, aux):
    l0, _, k0 = _fit(n, b, None, norm, aux)
    out = np.empty(len(temps))
    for j, s in enumerate(temps):
        l1, mu, _ = _fit(n, b, s, norm, aux, start=(0.0, k0))
        out[j] = 2.0 * (l1 - l0) if mu > 0 else 0.0
    return np.maximum(out, 0.0), k0


def run(doc: dict, toys: int, seed: int, gv_ref_level: float = 1.0) -> dict:
    x = np.asarray(doc["bin_centers"], float)
    variants = doc["variants"]
    if not variants:
        raise ValueError("at least one variant")
    seen = set()
    for v in variants:
        if "subset_of" in v and (v["subset_of"] not in seen or "efficiency" not in v):
            raise ValueError("a subset variant names an earlier variant in subset_of and gives its per-bin efficiency")
        seen.add(v["name"])
    norm = doc.get("background_normalization", {"kind": "fixed"})
    if norm["kind"] not in ("fixed", "free", "constrained") or (norm["kind"] == "constrained" and not norm.get("sigma", 0) > 0):
        raise ValueError("background_normalization.kind must be fixed, free or constrained (with sigma > 0)")
    widths = doc["scan"].get("widths", [1.0])
    temps, points = templates(x, doc["scan"]["positions"], widths)
    bs = [np.asarray(v["background"], float) for v in variants]
    ns = [np.asarray(v["observed"], float) for v in variants]
    obs = [q0_all(n, b, temps, norm, 1.0) for n, b in zip(ns, bs)]
    q_obs_v = [o[0] for o in obs]
    best_v = int(np.argmax([q.max() for q in q_obs_v]))
    best_j = int(np.argmax(q_obs_v[best_v]))
    q_max = float(q_obs_v[best_v][best_j])
    maxima, local_hits, upcross = np.empty(toys), 0, []
    for t in range(toys):
        rng = np.random.default_rng([seed, t])         # toy t's data do not depend on the grid or the other variants
        aux = 1.0 + norm["sigma"] * rng.standard_normal() if norm["kind"] == "constrained" else 1.0
        tq, drawn = [], {}
        for vi, (v, b, o) in enumerate(zip(variants, bs, obs)):
            if "subset_of" in v:                         # a tighter selection of another variant's events
                eff = np.asarray(v["efficiency"], float)
                n_t = np.random.default_rng([seed, t, vi]).binomial(drawn[v["subset_of"]].astype(int), eff)
            else:
                n_t = np.random.default_rng([seed, t, vi]).poisson(o[1] * b)
            drawn[v["name"]] = n_t
            tq.append(q0_all(n_t, b, temps, norm, aux)[0])
        maxima[t] = max(q.max() for q in tq)
        local_hits += tq[best_v][best_j] >= q_max - 1e-12
        if len(widths) == 1 and len(variants) == 1:
            above = tq[0] > gv_ref_level
            upcross.append(int(np.sum(above[1:] & ~above[:-1]) + above[0]))
    k_glob = int(np.sum(maxima >= q_max - 1e-12))
    tail = toy_tail(k_glob, toys)
    p_local = 0.5 * math.erfc(math.sqrt(q_max / 2)) if q_max > 0 else 0.5
    out = {"label": LABEL, "procedure": {"scan_points": len(points), "dimensions": 1 if len(widths) == 1 else 2,
                                         "variants": [v["name"] for v in variants], "background_normalization": norm},
           "observed": {"q0_max": q_max, "at": {"position": points[best_j][0], "width": points[best_j][1]},
                        "variant": variants[best_v]["name"]},
           "local_p_asymptotic": p_local, "local_p_toys": toy_tail(local_hits, toys),
           "global_p_toys": tail, "toys": toys, "seed": seed, "ensemble": "conditional (background-only fit to the data)",
           "global_not_below_local": tail["estimate"] is None or tail["interval"][1] >= min(p_local, 1.0) - 1e-12}
    if upcross:
        n0 = float(np.mean(upcross))
        gv = min(1.0, p_local + n0 * math.exp(-(q_max - gv_ref_level) / 2.0))
        lo, hi = clopper_pearson(k_glob, toys, 0.99)
        out["gross_vitells"] = {"p_global": gv, "mean_upcrossings": n0, "reference_level": gv_ref_level,
                                "validated_here": bool(lo <= gv <= hi), "toy_interval_99": [lo, hi]}
    else:
        out["gross_vitells"] = {"validated_here": False,
                                "reason": "a 2D scan or a choice among variants is outside the 1D chi2(1) upcrossing formula"}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--input", required=True)
    r.add_argument("--toys", type=int, default=1000)
    r.add_argument("--seed", type=int, required=True)
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy is required"}))
        return 2
    try:
        out = run(json.loads(Path(a.input).read_text()), a.toys, a.seed)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    out["status"] = "ok"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
