"""GB15 statistics shared by derive_registration.py and judge.py: read the step records, form the residuals d1 and d2 of Section 23, and run or size the TOSTs.

A test is one (set, regime, moment, bin). A hypothesis is the pair of moments the sample is compared with: the target behaviour, or a wrong one (a negative control).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

import scintillation_moments as moments

MOMENTS = ("mean", "variance")
KEY_SLICES = 1 << 12
SUM_NAMES = ("records", "d1", "d1_squared", "d2", "d2_squared", "m", "v", "expected_d1", "expected_d2")


def hexed(text: str) -> float:
    return float.fromhex(text)


def record_type(components: int) -> np.dtype:
    fields = [("deposit", "<f8"), ("visible", "<f8"), ("photons", "<i4"), ("event", "<i4"), ("slice", "<i4")]
    if components > 1:
        fields += [("fast", "<i4"), ("medium", "<i4"), ("slow", "<i4")]
    return np.dtype(fields)


def read_steps(prefix: Path) -> tuple:
    header = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    steps = np.fromfile(prefix.with_suffix(".steps"), dtype=record_type(header["components"]))
    if steps.dtype.itemsize != header["record_bytes"]:
        raise ValueError(f"{prefix}: record size differs from the header")
    return header, steps


def bin_labels(design_edges: list) -> list:
    return [f"({low:g},{high:g}]" for low, high in zip(design_edges[:-1], design_edges[1:])]


def regime(edges: list, index: int) -> str:
    return "poisson" if edges[index + 1] <= moments.POISSON_LIMIT else "gaussian"


class Sums:
    """Running sums per hypothesis and bin, so a set may arrive in several chunks."""

    def __init__(self, edges: list, hypotheses: list):
        self.edges = np.asarray(edges, dtype=float)
        self.table = {name: np.zeros((len(SUM_NAMES), len(edges) - 1)) for name in hypotheses}

    def add(self, hypothesis: str, axis: np.ndarray, count: np.ndarray, mean: np.ndarray, variance: np.ndarray, true_mean=None, true_variance=None) -> None:
        index = np.searchsorted(self.edges, axis, side="left") - 1  # a value on an edge goes to the bin below: bins are (low, high]
        keep = (index >= 0) & (index < self.edges.size - 1)
        index = index[keep]
        d1 = count[keep] - mean[keep]
        d2 = d1 * d1 - variance[keep]
        bins = self.edges.size - 1
        row = self.table[hypothesis]
        expected_d1 = np.zeros(d1.size) if true_mean is None else (true_mean - mean)[keep]
        expected_d2 = np.zeros(d1.size) if true_variance is None else (true_variance + (true_mean - mean) ** 2 - variance)[keep]
        for position, values in enumerate((np.ones(d1.size), d1, d1 * d1, d2, d2 * d2, mean[keep], variance[keep], expected_d1, expected_d2)):
            row[position] += np.bincount(index, weights=values, minlength=bins)


def step_hypotheses(step_set: dict, light_yield: float, table: dict) -> dict:
    """The moments each hypothesis gives one step, as functions of the step records; the first is the target behaviour."""
    resolution = step_set["resolution"]

    def light(records, saturated=step_set["saturation"]):
        return light_yield * (records["visible"] if saturated else records["deposit"])

    def target(records):
        return table[resolution](light(records))

    def from_other_light(records):
        return table[resolution](light(records, not step_set["saturation"]))

    def untruncated(records):
        mu = light(records)
        return mu, np.where(mu > moments.POISSON_LIMIT, resolution ** 2 * mu, mu)

    def resolution_r1(records):
        return table[1.0](light(records))

    def gaussian_below_limit(records):
        mu = light(records)
        mean, variance = target(records)
        return mean, np.where(mu > moments.POISSON_LIMIT, variance, resolution ** 2 * mu + 1.0 / 12.0)

    known = {"total_deposit": from_other_light, "visible_energy": from_other_light, "untruncated": untruncated, "resolution_r1": resolution_r1, "gaussian_below_limit": gaussian_below_limit}
    return {"target": target, **{name: known[name] for name in step_set["controls"]}}


def add_step_chunk(sums: Sums, step_set: dict, steps: np.ndarray, light_yield: float, table: dict) -> None:
    axis = light_yield * (steps["visible"] if step_set["saturation"] else steps["deposit"])
    count = steps["photons"].astype(float)
    for name, function in step_hypotheses(step_set, light_yield, table).items():
        mean, variance = function(steps)
        sums.add(name, axis, count, mean, variance)


def segmentation_bins(steps: np.ndarray, light_yield: float, resolution_table) -> dict:
    """The sums of Section 10.3 for each (event, slice): E^L, E^S, n^L, and the exact moments of Geant4's per-step sampling."""
    key = steps["event"].astype(np.int64) * KEY_SLICES + steps["slice"]
    order = np.argsort(key, kind="stable")
    key = key[order]
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    mu = light_yield * steps["visible"][order]
    large = mu > moments.POISSON_LIMIT
    step_mean, step_variance = resolution_table(mu)
    return {"large_light": np.add.reduceat(np.where(large, mu, 0.0), starts), "small_light": np.add.reduceat(np.where(large, 0.0, mu), starts),
            "large_steps": np.add.reduceat(large.astype(float), starts), "photons": np.add.reduceat(steps["photons"][order].astype(float), starts),
            "true_mean": np.add.reduceat(step_mean, starts), "true_variance": np.add.reduceat(step_variance, starts)}


def add_formula_chunk(sums: Sums, formula_set: dict, steps: np.ndarray, light_yield: float, resolution_table) -> None:
    resolution = formula_set["resolution"]
    cells = segmentation_bins(steps, light_yield, resolution_table)
    mean = cells["large_light"] + cells["small_light"]
    variance = moments.formula_variance(resolution, cells["large_light"], cells["small_light"], cells["large_steps"])
    drawn = {"target": moments.formula_moments(mean, variance)}
    if "without_rounding_term" in formula_set["controls"]:
        drawn["without_rounding_term"] = moments.formula_moments(mean, variance - cells["large_steps"] / 12.0)
    if "width_without_subtraction" in formula_set["controls"]:
        drawn["width_without_subtraction"] = moments.formula_moments(mean, variance, subtract_rounding=False)
    for name, (drawn_mean, drawn_variance) in drawn.items():
        sums.add(name, mean, cells["photons"], drawn_mean, drawn_variance, cells["true_mean"], cells["true_variance"])


def summarize(row: np.ndarray, index: int, moment: str, design: dict) -> dict:
    """Mean and error of the residual of one test, and the absolute margin from the bin averages of m and v."""
    n = row[0, index]
    sum_position = 1 if moment == "mean" else 3
    average = row[sum_position, index] / n
    spread = max(row[sum_position + 1, index] / n - average * average, 0.0)
    scale = row[5 if moment == "mean" else 6, index] / n
    margin = (design["mean_margin"] if moment == "mean" else design["variance_margin"]) * scale
    expected = row[7 if moment == "mean" else 8, index] / n
    return {"records": n, "residual": average, "residual_variance": spread, "error": (spread / n) ** 0.5, "margin": margin, "expected_difference": expected}


def tost(summary: dict, alpha: float) -> dict:
    reach = norm.isf(alpha) * summary["error"]
    return {**summary, "lower": summary["residual"] - reach, "upper": summary["residual"] + reach,
            "equivalent": bool(summary["residual"] - reach > -summary["margin"] and summary["residual"] + reach < summary["margin"])}


def tost_power(records: float, spread: float, margin: float, difference: float, alpha: float) -> float:
    error = (spread / records) ** 0.5
    reach = norm.isf(alpha)
    return float(norm.cdf((margin - difference) / error - reach) - norm.cdf((-margin - difference) / error + reach))


def required_records(spread: float, margin: float, difference: float, alpha: float, power: float) -> float:
    """The smallest number of records with TOST power >= power at this true difference (normal approximation, valid at these sizes)."""
    low, high = 1.0, 1e15
    if tost_power(high, spread, margin, difference, alpha) < power:
        return float("inf")
    while high / low > 1.0001:
        middle = (low * high) ** 0.5
        if tost_power(middle, spread, margin, difference, alpha) >= power:
            high = middle
        else:
            low = middle
    return high


def tests_of(sums: Sums, hypothesis: str, design: dict, edges: list) -> list:
    rows = []
    for index, label in enumerate(bin_labels(edges)):
        for moment in MOMENTS:
            if sums.table[hypothesis][0, index] == 0:
                rows.append({"bin": label, "regime": regime(edges, index), "moment": moment, "records": 0.0, "equivalent": False})
                continue
            rows.append({"bin": label, "regime": regime(edges, index), "moment": moment, **tost(summarize(sums.table[hypothesis], index, moment, design), design["alpha"])})
    return rows
