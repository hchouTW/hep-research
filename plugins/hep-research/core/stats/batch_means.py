"""Block (batch-means) estimators of a simulation run: the run's N events are split by event number into K blocks of B
events, an estimate theta_b is made in each block, and theta = mean(theta_b) with SE = sd(theta_b)/sqrt(K) on K - 1
degrees of freedom. Also: covariances of several block estimates, exact intervals for low counts (Clopper-Pearson for
proportions, Garwood for counts, the conditional binomial for a ratio of rates), linear-interpolation quantiles of a
fixed-binning histogram, and the most probable value (three-point parabola through the fullest bin of each block's
histogram). Standard library only; the inputs are the accumulators of a simulation-summary/1 (core.simulation.summary).

Assumption: events are independent (no state carried between events); the batch means are then unbiased for means
and proportions, and carry an O(1/B) bias for ratios, quantiles and modes of skewed distributions."""
from __future__ import annotations

import math
import statistics

from core import trace
from core.stats.distributions import t_ppf
from core.stats.poisson_diagnostics import central_interval
from core.stats.tail_estimation import clopper_pearson

COVERAGE_1SIGMA = 0.6827  # the coverage contracts/design.py reads a scalar uncertainty with
LOW_COUNT_TOTAL = 100  # below this merged total (or with any empty block) a count estimator uses exact intervals
MIN_BLOCKS = 2


class BatchMeansError(ValueError):
    """Unusable block estimates."""


def batch_mean(thetas) -> dict:
    """theta, its SE sd(theta_b)/sqrt(K) and K - 1 degrees of freedom from the per-block estimates."""
    trace.tag("geant4-batch-means")
    th = [float(x) for x in thetas]
    if len(th) < MIN_BLOCKS or not all(math.isfinite(x) for x in th):
        raise BatchMeansError(f"batch means need at least {MIN_BLOCKS} finite block estimates, got {len(th)}")
    k = len(th)
    return {"value": math.fsum(th) / k, "se": statistics.stdev(th) / math.sqrt(k), "dof": k - 1, "blocks": k}


def covariance(vectors) -> list[list[float]]:
    """Covariance matrix of the means of several block estimates: vectors[b] is the estimate vector of block b;
    cov(theta_i, theta_j) = sum_b (x_bi - m_i)(x_bj - m_j) / (K (K - 1))."""
    rows = [[float(x) for x in v] for v in vectors]
    k = len(rows)
    if k < MIN_BLOCKS or len({len(r) for r in rows}) != 1:
        raise BatchMeansError("covariance needs at least two blocks of equal-length estimate vectors")
    p = len(rows[0])
    m = [math.fsum(r[i] for r in rows) / k for i in range(p)]
    return [[math.fsum((r[i] - m[i]) * (r[j] - m[j]) for r in rows) / (k * (k - 1)) for j in range(p)]
            for i in range(p)]


def t_halfwidth(se: float, dof: float, coverage: float = COVERAGE_1SIGMA) -> float:
    """Half-width of the central t interval of the given coverage: t_{(1+c)/2}(dof) SE. At coverage 0.6827 this is
    the statistical_uncertainty a study record writes (about 1.03 SE at K = 16)."""
    return t_ppf(0.5 + coverage / 2.0, dof) * se


def low_count(block_counts, total: int | None = None, threshold: int = LOW_COUNT_TOTAL) -> bool:
    """Whether a count estimator must use exact intervals: any block is 0, or the merged total is below threshold."""
    counts = list(block_counts)
    total = sum(counts) if total is None else total
    return any(c == 0 for c in counts) or total < threshold


def exact_proportion(k: int, n: int, cl: float) -> tuple[float, float]:
    """Clopper-Pearson central interval of a proportion k/n from the merged accumulators."""
    return clopper_pearson(int(k), int(n), cl)


def exact_count(n: int, cl: float) -> tuple[float, float]:
    """Garwood central interval of a Poisson mean from the merged count (core.stats.poisson_diagnostics)."""
    g = central_interval(int(n), cl)
    return g["lower"], g["upper"]


def rate_ratio_interval(n1: int, n2: int, cl: float, exposure1: float = 1.0, exposure2: float = 1.0) -> tuple[float, float]:
    """Central interval of the ratio of two Poisson rates r = (mu1/t1)/(mu2/t2), conditional on n1 + n2: n1 is
    binomial with p = r t1 / (r t1 + t2), so the Clopper-Pearson interval on p maps to r = p t2 / ((1 - p) t1). Exact
    for Poisson counts; only approximate for proportions (their denominators are fixed). Relative difference = r - 1."""
    n1, n2 = int(n1), int(n2)
    if n1 + n2 == 0:
        return 0.0, math.inf
    lo, hi = clopper_pearson(n1, n1 + n2, cl)
    f = exposure2 / exposure1
    return (lo / (1.0 - lo) * f if lo < 1.0 else math.inf), (hi / (1.0 - hi) * f if hi < 1.0 else math.inf)


def hist_quantile(counts, lo: float, width: float, q: float, underflow: int = 0, overflow: int = 0) -> dict:
    """The q-quantile of a fixed-binning histogram by linear interpolation within the bin that contains it (counts of
    the bins [lo + i width, lo + (i + 1) width)); a quantile that lands in the underflow or overflow is incomplete."""
    total = underflow + sum(counts) + overflow
    if total <= 0 or not 0.0 < q < 1.0:
        return {"value": None, "status": "incomplete", "reason": "empty-histogram" if total <= 0 else "bad-q"}
    target = q * total
    if target <= underflow:
        return {"value": None, "status": "incomplete", "reason": "quantile-in-underflow"}
    cum = float(underflow)
    for i, c in enumerate(counts):
        if c > 0 and cum + c >= target:
            return {"value": lo + (i + (target - cum) / c) * width, "status": "ok", "bin": i}
        cum += c
    return {"value": None, "status": "incomplete", "reason": "quantile-in-overflow"}


def empirical_quantile(values, q: float) -> dict:
    """The q-quantile of raw values by Hyndman and Fan's type 7 (linear interpolation between order statistics:
    h = (n - 1) q, x_(floor h) + (h - floor h)(x_(floor h + 1) - x_(floor h)), 0-based), the default of R and numpy."""
    xs = sorted(float(x) for x in values)
    if not xs or not 0.0 <= q <= 1.0:
        return {"value": None, "status": "incomplete", "reason": "no-values" if not xs else "bad-q"}
    h = (len(xs) - 1) * q
    j = math.floor(h)
    hi = xs[min(j + 1, len(xs) - 1)]
    return {"value": xs[j] + (h - j) * (hi - xs[j]), "status": "ok", "method": "hyndman-fan-7"}


def block_mode(counts, lo: float, width: float) -> dict:
    """Mode of one block's histogram: the vertex of the parabola through the fullest bin (lowest index on ties) and
    its two neighbours, x0 + width (y- - y+) / (2 (y- - 2 y0 + y+)) with x0 the bin centre. When the fullest bin is
    the first or last bin, or the denominator is 0, the mode is the bin centre and the block is flagged."""
    trace.tag("geant4-mpv-block")
    if not counts or max(counts) <= 0:
        return {"value": None, "fallback": True, "reason": "empty-histogram"}
    k = max(range(len(counts)), key=lambda i: (counts[i], -i))
    centre = lo + (k + 0.5) * width
    if k == 0 or k == len(counts) - 1:
        return {"value": centre, "fallback": True, "reason": "edge-bin"}
    ym, y0, yp = counts[k - 1], counts[k], counts[k + 1]
    den = ym - 2 * y0 + yp
    if den == 0:
        return {"value": centre, "fallback": True, "reason": "flat-top"}
    return {"value": centre + width * (ym - yp) / (2.0 * den), "fallback": False}


def mpv(block_histograms, lo: float, width: float, tol_relative: float | None = None, merged=None) -> dict:
    """Most probable value: mean of the block modes with its batch-means SE. Incomplete when more than K/4 blocks
    fell back to a bin centre. With tol_relative and the merged histogram, the per-execution check: m = the mode of the
    merged histogram, |theta - m| / |m| <= tol/5 + 2 SE/|m|, else incomplete."""
    modes = [block_mode(h, lo, width) for h in block_histograms]
    if any(m["value"] is None for m in modes):
        return {"status": "incomplete", "reason": "empty-block-histogram", "value": None}
    fallbacks = sum(m["fallback"] for m in modes)
    out = {**batch_mean(m["value"] for m in modes), "fallback_blocks": fallbacks, "status": "ok",
           "estimator": "mean of the three-point parabola modes of the block histograms"}
    if fallbacks > len(modes) / 4:
        out.update(status="incomplete", reason="too-many-fallback-blocks")
        return out
    if tol_relative is not None and merged is not None:
        m = block_mode(merged, lo, width)["value"]
        bound = tol_relative / 5 + 2 * out["se"] / abs(m)
        out["merged_mode"] = m
        out["merged_check"] = {"relative_difference": abs(out["value"] - m) / abs(m), "bound": bound}
        if abs(out["value"] - m) / abs(m) > bound:
            out.update(status="incomplete", reason="block-mode-differs-from-merged")
    return out
