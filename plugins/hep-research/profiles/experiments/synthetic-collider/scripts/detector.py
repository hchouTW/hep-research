"""SYNTHETIC detector model for the illustrative synthetic-collider profile (see modules/detector-model.md).

efficiency(c) = e0 - e1 c^4 (acceptance and selection folded together); reconstructed cos theta = c + N(0, sigma_c),
values outside the reco range are lost. response() integrates shape x efficiency x smearing over each truth bin.
All parameters are invented and come from the benchmark configuration.
"""
from __future__ import annotations

import math

import numpy as np


def efficiency(c, cfg: dict):
    e = cfg["efficiency"]
    return e["e0"] - e["e1"] * np.asarray(c) ** 4


def smear(rng: np.random.Generator, c, cfg: dict):
    return np.asarray(c) + rng.normal(0.0, cfg["resolution"]["sigma_cos"], size=np.shape(c))


def _ncdf(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x) / math.sqrt(2.0)))


def response(cfg: dict, a: float, b: float, n: int = 2001) -> dict:
    """R[k][j] = P(reco in bin k and selected | truth in bin j); rows reco, cols truth.

    Truth inside a bin is weighted by the generator shape 1 + a c^2 + b c. Returns the matrix, the per-bin
    efficiency (column sum including losses), and the selected-but-outside-range fractions (underflow/overflow)."""
    te, re_ = np.asarray(cfg["truth_edges"]), np.asarray(cfg["reco_edges"])
    s = cfg["resolution"]["sigma_cos"]
    m = np.zeros((len(re_) - 1, len(te) - 1))
    under, over, eff = np.zeros(len(te) - 1), np.zeros(len(te) - 1), np.zeros(len(te) - 1)
    for j in range(len(te) - 1):
        c = np.linspace(te[j], te[j + 1], n)
        w = 1.0 + a * c ** 2 + b * c
        wt = np.full(n, 1.0)
        wt[0] = wt[-1] = 0.5  # trapezoid weights
        w = w * wt / np.sum(w * wt)
        e = efficiency(c, cfg)
        cdf = _ncdf((re_[:, None] - c[None, :]) / s)  # P(reco < edge | c)
        m[:, j] = (np.diff(cdf, axis=0) * (w * e)[None, :]).sum(axis=1)
        under[j] = np.sum(cdf[0] * w * e)
        over[j] = np.sum((1.0 - cdf[-1]) * w * e)
        eff[j] = np.sum(w * e)
    return {"matrix": m, "underflow": under, "overflow": over, "efficiency": eff}
