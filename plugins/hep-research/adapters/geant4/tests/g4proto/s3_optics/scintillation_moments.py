"""Exact moments of the GB15 target behaviour and of the bin-level formula of Section 10.3, shared by derive_registration.py and judge.py.

Per step: Poisson(mu) for mu <= 10, otherwise max(0, round(X)) with X normal, mean mu and width r sqrt(mu). The moments are summed numerically over the
integers. Two shortcuts, each far below the margins: with width >= 1 the ripple of the rounding is at most (1/pi) exp(-2 pi^2) = 9e-10, so without truncation
the moments are mu and width^2 + 1/12; with truncation, for a fixed r, they come from a table on a 0.01 grid of mu (self_check() bounds both against direct sums).
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr

POISSON_LIMIT = 10.0
REACH_WIDTHS = 9.0  # 9 widths: the normal tail beyond is below 1e-18
TABLE_SPACING = 0.01


def rounded_normal_moments(mean: np.ndarray, width: np.ndarray) -> tuple:
    """Mean and variance of max(0, round(X)), X ~ N(mean, width), by direct summation over k >= 1, in groups of similar reach."""
    mean, width = np.broadcast_arrays(np.asarray(mean, dtype=float), np.asarray(width, dtype=float))
    first_moment, second_moment = np.zeros(mean.shape), np.zeros(mean.shape)
    low = np.maximum(1, np.floor(mean - REACH_WIDTHS * width)).astype(np.int64)
    high = np.ceil(mean + REACH_WIDTHS * width).astype(np.int64) + 1
    span = np.maximum(high - low, 0)
    groups = np.ceil(np.log2(span + 2)).astype(int)
    for group in np.unique(groups):
        chosen = np.flatnonzero(groups == group)
        for start in range(0, chosen.size, 1 << 20):
            part = chosen[start:start + (1 << 20)]
            spread = 1.0 / width[part]
            center = mean[part]
            sum_first, sum_second = np.zeros(part.size), np.zeros(part.size)
            number = low[part].astype(float)
            below = ndtr((number - 0.5 - center) * spread)
            for _ in range(int(span[part].max()) + 1):
                above = ndtr((number + 0.5 - center) * spread)
                chance = above - below
                sum_first += number * chance
                sum_second += number * number * chance
                below = above
                number += 1.0
            first_moment[part], second_moment[part] = sum_first, sum_second
    return first_moment, second_moment - first_moment * first_moment


class StepMoments:
    """The moments m(mu), v(mu) of one step at resolution scale r."""

    def __init__(self, resolution: float):
        self.resolution = resolution
        self.table_top = REACH_WIDTHS ** 2 * resolution ** 2  # above it the mean sits more than 9 widths above 0
        self.grid = None
        if resolution >= 1.0:
            self.grid = np.arange(POISSON_LIMIT, self.table_top + 2 * TABLE_SPACING, TABLE_SPACING)
            self.grid_mean, self.grid_variance = rounded_normal_moments(self.grid, resolution * np.sqrt(self.grid))

    def __call__(self, mu: np.ndarray, poisson_limit: float = POISSON_LIMIT) -> tuple:
        mu = np.asarray(mu, dtype=float)
        mean, variance = mu.copy(), mu.copy()
        gaussian = mu > poisson_limit
        width = self.resolution * np.sqrt(mu[gaussian])
        got_mean, got_variance = mu[gaussian].copy(), width * width + 1.0 / 12.0
        if self.grid is not None:
            near = mu[gaussian] < self.table_top
            got_mean[near] = np.interp(mu[gaussian][near], self.grid, self.grid_mean)
            got_variance[near] = np.interp(mu[gaussian][near], self.grid, self.grid_variance)
        else:
            narrow = width < 1.0
            got_mean[narrow], got_variance[narrow] = rounded_normal_moments(mu[gaussian][narrow], width[narrow])
        mean[gaussian], variance[gaussian] = got_mean, got_variance
        return mean, variance


def formula_variance(resolution: float, large_light: np.ndarray, small_light: np.ndarray, large_steps: np.ndarray) -> np.ndarray:
    """v_b of Section 10.3: r^2 LY E^L + LY E^S + n^L / 12."""
    return resolution ** 2 * large_light + small_light + large_steps / 12.0


def formula_moments(mean: np.ndarray, variance: np.ndarray, subtract_rounding: bool = True) -> tuple:
    """Moments of the digitization draw of Section 10.3: Poisson(mu_b) for mu_b <= 10, otherwise a normal of width sqrt(v_b - 1/12), rounded, 0 below 0."""
    drawn_mean, drawn_variance = mean.copy(), mean.copy()
    gaussian = mean > POISSON_LIMIT
    width = np.sqrt(variance[gaussian] - (1.0 / 12.0 if subtract_rounding else 0.0))
    got_mean, got_variance = mean[gaussian].copy(), width * width + 1.0 / 12.0
    direct = (width < 1.0) | (mean[gaussian] < REACH_WIDTHS * width)
    got_mean[direct], got_variance[direct] = rounded_normal_moments(mean[gaussian][direct], width[direct])
    drawn_mean[gaussian], drawn_variance[gaussian] = got_mean, got_variance
    return drawn_mean, drawn_variance


def self_check() -> dict:
    """The table and the shortcuts against direct sums, and the two numbers Section 23 quotes for r = 2 near mu = 10."""
    worst = 0.0
    for resolution in (0.15, 1.0, 2.0, 3.0):
        mu = np.array([10.0001, 10.37, 11.0, 12.5, 15.123, 25.5, 44.3, 44.5, 80.9, 81.1, 200.3, 329.7, 500.25, 1000.5])
        got_mean, got_variance = StepMoments(resolution)(mu)
        want_mean, want_variance = rounded_normal_moments(mu, resolution * np.sqrt(mu))
        worst = max(worst, float(np.max(np.abs(got_mean - want_mean) / mu)), float(np.max(np.abs(got_variance - want_variance) / want_variance)))
    near_mean, near_variance = rounded_normal_moments(np.array([10.0]), np.array([2.0 * np.sqrt(10.0)]))
    return {"worst_relative_shortcut_error": worst, "r2_mu10_mean_excess": float(near_mean[0] / 10.0 - 1.0), "r2_mu10_variance_excess_vs_r2mu": float(near_variance[0] / 40.0 - 1.0),
            "r2_mu10_variance_excess_vs_r2mu_plus_twelfth": float(near_variance[0] / (40.0 + 1.0 / 12.0) - 1.0)}
