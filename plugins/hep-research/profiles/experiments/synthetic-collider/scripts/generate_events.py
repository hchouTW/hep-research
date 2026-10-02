#!/usr/bin/env python3
"""SYNTHETIC e+e- -> mu+mu- angular event generator for the illustrative synthetic-collider profile.

Draws N ~ Poisson(L x sigma) events with cos theta from f(c) = 1 + a c^2 + b c on [-1, 1] (accept-reject),
applies the synthetic detector (scripts/detector.py: efficiency, Gaussian cos theta smearing) and writes
per-event truth cos theta, a selected flag and the reconstructed cos theta. sigma, a and b are synthetic
inputs (benchmarks/path-b.json), not predictions; this module imports no theory code.

Usage: python3 generate_events.py [--config ../benchmarks/path-b.json] [--seed N] [--sigma-pb X]
                                  [--shape-a A] [--shape-b B] [--out events.npz] [--summary]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--sigma-pb", type=float)
    ap.add_argument("--shape-a", type=float)
    ap.add_argument("--shape-b", type=float)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--summary", action="store_true", help="print a JSON summary")
    args = ap.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    ev = generate(cfg, cfg["seed"] if args.seed is None else args.seed, args.sigma_pb, args.shape_a, args.shape_b)
    if args.out:
        np.savez_compressed(args.out, truth_cos=ev["truth_cos"], selected=ev["selected"], reco_cos=ev["reco_cos"],
                            meta=json.dumps(ev["meta"]))
    if args.summary or not args.out:
        print(json.dumps({**ev["meta"], "n_selected": int(ev["selected"].sum())}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
