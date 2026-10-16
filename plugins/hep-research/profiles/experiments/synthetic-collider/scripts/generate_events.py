#!/usr/bin/env python3
"""SYNTHETIC e+e- -> mu+mu- angular event generator for the illustrative synthetic-collider profile.

Draws N ~ Poisson(L x sigma) events with cos theta from f(c) = 1 + a c^2 + b c on [-1, 1] (accept-reject),
applies the synthetic detector (scripts/detector.py: efficiency, Gaussian cos theta smearing) and writes
per-event truth cos theta, a selected flag and the reconstructed cos theta. sigma, a and b are synthetic
inputs (benchmarks/path-b.json), not predictions; this module imports no theory code.

Optional synthetic background (the "background" block of the benchmark): generate_background() draws a second,
independent sample of muon pairs (an invented tau-pair-like process) through the same detector, each event with a
visible-energy fraction x_vis = E_vis / sqrt(s) from a Beta(alpha, beta) shape; signal_xvis() gives signal events
x_vis = 1 + N(0, sigma_x) from its own seeded stream, so generate() and its outputs are unchanged.
xvis_fraction() is the analytic fraction of either sample in an x_vis interval (the "simulation" an analysis uses
for a sideband transfer factor).

Usage: python3 generate_events.py [--config ../benchmarks/path-b.json] [--seed N] [--sigma-pb X]
                                  [--shape-a A] [--shape-b B] [--background] [--out events.npz] [--summary]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(HERE))
import detector  # noqa: E402

DEFAULT_CONFIG = HERE.parent / "benchmarks" / "path-b.json"


def shape(c, a: float, b: float):
    return 1.0 + a * np.asarray(c) ** 2 + b * np.asarray(c)


def sample_cos(rng: np.random.Generator, n: int, a: float, b: float) -> np.ndarray:
    """Accept-reject on [-1, 1]; f must be non-negative there."""
    grid = shape(np.linspace(-1.0, 1.0, 2001), a, b)
    if np.any(grid < 0):
        raise ValueError("shape 1 + a c^2 + b c is negative somewhere in [-1, 1]")
    fmax = 1.0001 * float(grid.max())  # f is a quadratic, so the grid maximum is within 1e-6 of the true maximum
    out = np.empty(0)
    while out.size < n:
        c = rng.uniform(-1.0, 1.0, size=max(2 * (n - out.size), 1000))
        keep = rng.uniform(0.0, fmax, size=c.size) < shape(c, a, b)
        out = np.concatenate([out, c[keep]])
    return out[:n]


def generate(cfg: dict, seed: int, sigma_pb: float | None = None, a: float | None = None, b: float | None = None) -> dict:
    g = cfg["generator"]
    sigma = g["sigma_pb"] if sigma_pb is None else sigma_pb
    a = g["shape_a"] if a is None else a
    b = g["shape_b"] if b is None else b
    rng = np.random.default_rng(seed)
    n = rng.poisson(cfg["integrated_luminosity_pb"] * sigma)
    truth = sample_cos(rng, n, a, b)
    selected = rng.uniform(size=n) < detector.efficiency(truth, cfg)
    reco = detector.smear(rng, truth, cfg)
    return {"truth_cos": truth, "selected": selected, "reco_cos": reco,
            "meta": {"label": "SYNTHETIC", "seed": seed, "sigma_pb": sigma, "shape_a": a, "shape_b": b,
                     "integrated_luminosity_pb": cfg["integrated_luminosity_pb"], "n_generated": int(n)}}


def _beta_cdf(x, alpha: int, beta: int) -> float:
    """CDF of Beta(alpha, beta) on [0, 1] for positive integer shapes (finite binomial sum)."""
    from math import comb
    x = min(max(float(x), 0.0), 1.0)
    n = alpha + beta - 1
    return float(sum(comb(n, k) * x ** k * (1.0 - x) ** (n - k) for k in range(alpha, n + 1)))


def xvis_fraction(cfg: dict, lo: float, hi: float, sample: str) -> float:
    """Fraction of the 'signal' or 'background' sample with lo <= x_vis < hi (analytic, from the benchmark model)."""
    bx = cfg["background"]["x_vis"]
    if sample == "background":
        return _beta_cdf(hi, bx["alpha"], bx["beta"]) - _beta_cdf(lo, bx["alpha"], bx["beta"])
    if sample == "signal":
        from math import erf, inf, sqrt
        s = bx["signal_sigma"]
        cdf = lambda x: 0.0 if x == -inf else 1.0 if x == inf else 0.5 * (1.0 + erf((x - 1.0) / (s * sqrt(2.0))))  # noqa: E731
        return cdf(hi) - cdf(lo)
    raise ValueError("sample must be 'signal' or 'background'")


def signal_xvis(cfg: dict, n: int, seed: int) -> np.ndarray:
    """x_vis for n signal events from its own stream (seed), so the signal sample of generate() is unchanged."""
    rng = np.random.default_rng(seed)
    return 1.0 + rng.normal(0.0, cfg["background"]["x_vis"]["signal_sigma"], size=n)


def generate_background(cfg: dict, seed: int) -> dict:
    """SYNTHETIC background sample: N ~ Poisson(L x sigma_b), cos theta from 1 + a_b c^2 + b_b c, the same detector
    efficiency and smearing as the signal, and x_vis ~ Beta(alpha, beta) independent of cos theta."""
    bkg = cfg["background"]
    rng = np.random.default_rng(seed)
    n = rng.poisson(cfg["integrated_luminosity_pb"] * bkg["sigma_pb"])
    truth = sample_cos(rng, n, bkg["shape_a"], bkg["shape_b"])
    selected = rng.uniform(size=n) < detector.efficiency(truth, cfg)
    reco = detector.smear(rng, truth, cfg)
    x_vis = rng.beta(bkg["x_vis"]["alpha"], bkg["x_vis"]["beta"], size=n)
    return {"truth_cos": truth, "selected": selected, "reco_cos": reco, "x_vis": x_vis,
            "meta": {"label": "SYNTHETIC background", "seed": seed, "sigma_pb": bkg["sigma_pb"], "shape_a": bkg["shape_a"],
                     "shape_b": bkg["shape_b"], "integrated_luminosity_pb": cfg["integrated_luminosity_pb"],
                     "n_generated": int(n)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--sigma-pb", type=float)
    ap.add_argument("--shape-a", type=float)
    ap.add_argument("--shape-b", type=float)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--summary", action="store_true", help="print a JSON summary")
    ap.add_argument("--background", action="store_true", help="generate the synthetic background sample instead")
    args = ap.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    seed = cfg["seed"] if args.seed is None else args.seed
    if args.background:
        ev = generate_background(cfg, seed)
    else:
        ev = generate(cfg, seed, args.sigma_pb, args.shape_a, args.shape_b)
    if args.out:
        extra = {"x_vis": ev["x_vis"]} if "x_vis" in ev else {}
        np.savez_compressed(args.out, truth_cos=ev["truth_cos"], selected=ev["selected"], reco_cos=ev["reco_cos"],
                            meta=json.dumps(ev["meta"]), **extra)
    if args.summary or not args.out:
        print(json.dumps({**ev["meta"], "n_selected": int(ev["selected"].sum())}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
