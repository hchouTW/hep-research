"""Event weights of Part B section 3.6 and 6.1 (calib_reweight.py; G4 is phase 2, G4-L phase 5).

The weight formula, with S_theta the nodes whose parameters change and S_q the nodes with a broadened proposal:

    w_i = prod_{s in S_theta} K_s(x_si | x_pa(s),i; theta') prod_{s in S_q \\ S_theta} K_s(x_si | ...; theta_0)
          / ( [sum_j c_j prod_{s in S_q} q_js(x_si | ...)] prod_{s in S_theta \\ S_q} K_s(x_si | ...; theta_0) )

c_j = n_j / N (balance heuristic); the denominator of every event is recomputed with all q_j, old events included, so
merging additional events (section 6.1 item 5) is adding a component and recomputing c_j. Check: S_q empty and
theta' = theta_0 gives w = 1. Step-level reweighting is the same formula with K_s a product over the stored steps."""
from __future__ import annotations

import math

import numpy as np
from scipy import special


def log_weights(log_target: np.ndarray, log_components: list[np.ndarray] | None, fractions: list[float] | None,
                log_nominal_outside_q: np.ndarray | None = None) -> np.ndarray:
    """log w for each event.

    log_target: sum over s in S_theta u S_q of log K_s(x; theta') (theta_0 for the nodes of S_q \\ S_theta).
    log_components: for each mixture component j, sum over s in S_q of log q_js(x) (None or [] when S_q is empty).
    fractions: c_j = n_j / N, normalized here.
    log_nominal_outside_q: sum over s in S_theta \\ S_q of log K_s(x; theta_0).
    A NaN term (an output not recorded: zero suppression, filtering) gives NaN: missing support, never a weight."""
    lw = np.asarray(log_target, dtype=float).copy()
    if log_components:
        c = np.asarray(fractions, dtype=float)
        c = c / c.sum()
        stack = np.stack([math.log(cj) + np.asarray(lc, dtype=float) for cj, lc in zip(c, log_components)])
        lw = lw - special.logsumexp(stack, axis=0)
    if log_nominal_outside_q is not None:
        lw = lw - np.asarray(log_nominal_outside_q, dtype=float)
    return lw


def step_log_density(step_logpdfs: np.ndarray) -> np.ndarray:
    """Step-level reweighting: the kernel density of an event is the product over its stored steps (rows: steps)."""
    return np.asarray(step_logpdfs, dtype=float).sum(axis=0)


def kish(w: np.ndarray) -> float:
    """Kish effective sample size (sum w)^2 / sum w^2 (section 6.7)."""
    w = np.asarray(w, dtype=float)
    s2 = float((w ** 2).sum())
    return float(w.sum() ** 2 / s2) if s2 > 0 else 0.0


def merged_fractions(sizes: list[int]) -> list[float]:
    """c_j = n_j / N after merging additional events (section 6.1 item 5): every event's denominator is recomputed
    with these fractions and all components."""
    total = float(sum(sizes))
    return [n / total for n in sizes]


def poisson_ess_fraction(mu_per_channel, r: float) -> float:
    """Predicted N_eff / N for reweighting Poisson counts with means mu_ch to r mu_ch (section 3.6):
    exp(-sum_ch mu_ch (r - 1)^2)."""
    return math.exp(-float(np.sum(mu_per_channel)) * (r - 1.0) ** 2)


def summary(weights: dict) -> dict:
    """Per run: the number of events, the Kish ESS, the largest weight fraction, and max |w - 1| (the section 3.6 check
    is 0 when S_q is empty and theta' is the generation point)."""
    out = {}
    for rid, x in weights.items():
        x = np.asarray(x, dtype=float)
        tot = float(x.sum())
        out[rid] = {"n": int(len(x)), "kish": kish(x), "max_weight_fraction": float(x.max() / tot) if tot > 0 else None,
                    "max_abs_w_minus_1": float(np.abs(x - 1).max()) if len(x) else 0.0}
    return out
