#!/usr/bin/env python3
"""Likelihood scans of quadratic (EFT-like) signal models with disconnected allowed sets (audit T26). EXPERIMENTAL.
Needs NumPy and SciPy.

Model: Poisson bins with mean nu_i(c) = b_i + sum_k c_k I_ki + sum_kl c_k c_l Q_kli (one or two coefficients c;
interference I, quadratic Q), no nuisance parameters. The negative log-likelihood is evaluated on a complete grid, so
no optimizer can miss a second minimum: q(c) = 2 (NLL(c) - min over the grid and a local refinement).

What it reports, and what it refuses to do:
- 1D: every interval of {c: q(c) <= threshold}, in order; an allowed set made of two disjoint intervals is reported as
  two intervals, never as their convex hull [min, max]; an interval that reaches the end of the grid is flagged
  (reaches_grid_edge): the set is then cut by the grid, not by the data;
- 2D: the joint region {q(c1, c2) <= chi2_2dof quantile} as a grid mask with its connected components, and, separately,
  the profiled 1D intervals of each coefficient (threshold chi2_1dof): joint and profiled thresholds are different
  questions and are labelled;
- toy belt (1D): at each grid point the critical value of q from seeded toys generated at that point (a Neyman belt);
  the toy allowed set may differ from the Wilks one where the model is degenerate (two values of c give the same
  rate) or near the physical edge. Coverage of a stated construction is checked by toys at true points.
Validity: Wilks thresholds hold only where the quadratic model is locally regular; near a degenerate minimum or a
second solution they do not, and the toy belt is the reference. Results stay labelled experimental.

Usage: eft_scan.py scan --input MODEL.json [--cl 0.95] [--toys 0 --seed 1]
  MODEL.json: {"b": [...], "n": [...], "I": [[...] per c], "Q": [[[...] per c, c]] , "grid": [[lo, hi, points] per c]}
Exit codes: 0 ok; 2 bad input. Output JSON labelled [General method] EXPERIMENTAL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage, stats

LABEL = "[General method] EXPERIMENTAL"


def expected(model: dict, c: np.ndarray) -> np.ndarray:
    """nu(c) for c of shape (..., k); returns (..., bins)."""
    b = np.asarray(model["b"], float)
    I = np.asarray(model["I"], float)          # (k, bins)
    Q = np.asarray(model["Q"], float)          # (k, k, bins)
    nu = b + np.einsum("...k,kb->...b", c, I) + np.einsum("...k,...l,klb->...b", c, c, Q)
    return nu


def nll(model: dict, c: np.ndarray, n=None) -> np.ndarray:
    n = np.asarray(model["n"] if n is None else n, float)
    nu = expected(model, c)
    with np.errstate(divide="ignore", invalid="ignore"):
        val = np.where(nu > 0, nu - n * np.log(np.where(nu > 0, nu, 1.0)), np.where(n > 0, np.inf, 0.0))
    return val.sum(axis=-1)


def _grid(model):
    axes = [np.linspace(lo, hi, int(p)) for lo, hi, p in model["grid"]]
    mesh = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    return axes, mesh


def intervals(axis, mask) -> list[list[float]]:
    """Maximal runs of True in mask, as [first, last] grid values."""
    out, start = [], None
    for k, m in enumerate(mask):
        if m and start is None:
            start = k
        if start is not None and (not m or k == len(mask) - 1):
            end = k if m else k - 1
            out.append([float(axis[start]), float(axis[end])])
            start = None
    return out


def scan(model: dict, cl: float = 0.95, toys: int = 0, seed: int = 1) -> dict:
    k = len(model["I"])
    if k not in (1, 2) or len(model["grid"]) != k:
        raise ValueError("one or two coefficients, with one grid per coefficient")
    axes, mesh = _grid(model)
    nl = nll(model, mesh)
    if not np.any(np.isfinite(nl)):
        raise ValueError("no grid point gives a valid Poisson mean for the data")
    q = 2.0 * (nl - np.nanmin(nl[np.isfinite(nl)]))
    out = {"label": LABEL, "coefficients": k, "cl": cl, "grid_points": [len(a) for a in axes],
           "best_fit": mesh[np.unravel_index(np.nanargmin(np.where(np.isfinite(nl), nl, np.inf)), nl.shape)].tolist()}
    t1 = stats.chi2.ppf(cl, 1)
    if k == 1:
        out["wilks_threshold"] = float(t1)
        out["allowed_intervals_wilks"] = intervals(axes[0], q <= t1)
        out["disconnected"] = len(out["allowed_intervals_wilks"]) > 1
        out["reaches_grid_edge"] = bool((q <= t1)[0] or (q <= t1)[-1])
        if toys:
            rng = np.random.default_rng(seed)
            crit = np.empty(len(axes[0]))
            for j, c in enumerate(axes[0]):
                nu = expected(model, np.array([c]))
                ns = rng.poisson(np.clip(nu, 0, None), size=(toys, len(nu)))
                nl_t = np.stack([nll(model, mesh, n=x) for x in ns])
                q_t = 2.0 * (nl_t[:, j] - np.min(np.where(np.isfinite(nl_t), nl_t, np.inf), axis=1))
                crit[j] = np.quantile(q_t, cl)
            out["toy_belt"] = {"toys_per_point": toys, "seed": seed, "critical_values": crit.tolist(),
                               "allowed_intervals_toys": intervals(axes[0], q <= crit)}
    else:
        t2 = stats.chi2.ppf(cl, 2)
        joint = q <= t2
        labels, ncomp = ndimage.label(joint)
        prof = [np.min(q, axis=1 - i) for i in range(2)]
        edge = bool(joint[0, :].any() or joint[-1, :].any() or joint[:, 0].any() or joint[:, -1].any())
        out.update({"joint_threshold_2dof": float(t2), "joint_region_components": int(ncomp), "reaches_grid_edge": edge,
                    "joint_region_fraction_of_grid": float(joint.mean()),
                    "profiled_threshold_1dof": float(t1),
                    "profiled_intervals": [intervals(axes[i], prof[i] <= t1) for i in range(2)],
                    "joint_projection_intervals": [intervals(axes[i], np.any(joint, axis=1 - i)) for i in range(2)],
                    "note": "the joint region uses the 2-dof threshold; profiled 1D intervals use 1 dof: different questions"})
    out["q_on_grid"] = q.tolist()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--input", required=True)
    s.add_argument("--cl", type=float, default=0.95)
    s.add_argument("--toys", type=int, default=0)
    s.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    try:
        out = scan(json.loads(Path(a.input).read_text()), a.cl, a.toys, a.seed)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    out["status"] = "ok"
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
