"""Seeded fixture generators, so cases can ship realistic synthetic inputs without large literal files.

A case fixture {"generate": "<name>", ...params} is written by the runner from the generator below. Every output is
labeled SYNTHETIC in its header and is identical for identical parameters (seeded), so a regraded run sees the same
inputs as the live run did.
"""
from __future__ import annotations

import math
import random


def _powerlaw(rng: random.Random, lo: float, hi: float, gamma: float) -> float:
    a = 1.0 - gamma
    u = rng.random()
    return (lo ** a + u * (hi ** a - lo ** a)) ** (1.0 / a)


def matched_events(n: int = 3000, seed: int = 1, lo: float = 1.0, hi: float = 64.0, gamma: float = 2.7,
                   resolution: float = 0.08, efficiency: float = 0.9, variable: str = "rigidity_GV") -> str:
    rng = random.Random(seed)
    rows = [f"# SYNTHETIC matched truth/reco sample (seed {seed}); invented, not data from any experiment",
            f"truth_{variable},reco_{variable},selected,weight"]
    for _ in range(n):
        t = _powerlaw(rng, lo, hi, gamma)
        sel = rng.random() < efficiency
        r = t * (1.0 + rng.gauss(0.0, resolution)) if sel else ""
        rows.append(f"{t:.5f},{r if r == '' else f'{r:.5f}'},{int(sel)},1.0")
    return "\n".join(rows) + "\n"


def binned_counts(edges=(1, 2, 4, 8, 16, 32, 64), seed: int = 2, norm: float = 20000.0, gamma: float = 2.7,
                  variable: str = "rigidity", unit: str = "GV") -> str:
    rng = random.Random(seed)
    a = 1.0 - gamma
    total = edges[-1] ** a - edges[0] ** a
    rows = [f"# SYNTHETIC measured spectrum (seed {seed}); invented", f"{variable}_lo_{unit},{variable}_hi_{unit},counts"]
    for lo, hi in zip(edges[:-1], edges[1:]):
        mu = norm * (hi ** a - lo ** a) / total
        # Poisson via normal approximation for large mu, exact inversion for small
        if mu > 50:
            k = max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
        else:
            k, p, L = 0, 1.0, math.exp(-mu)
            while True:
                p *= rng.random()
                if p <= L:
                    break
                k += 1
        rows.append(f"{lo},{hi},{k}")
    return "\n".join(rows) + "\n"


GENERATORS = {"matched_events": matched_events, "binned_counts": binned_counts}


def generate(spec: dict) -> str:
    params = {k: v for k, v in spec.items() if k != "generate"}
    if "edges" in params:
        params["edges"] = tuple(params["edges"])
    return GENERATORS[spec["generate"]](**params)
