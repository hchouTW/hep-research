"""Change points in a series with known per-point uncertainties: the step statistic, binary segmentation, CUSUM,
thresholds calibrated by toys to a declared false-alarm rate, and weighted constant, linear and piecewise fits (D11).

Model: y_i = mu(t_i) + e_i, e_i ~ N(0, sigma_i^2) independent, sigma_i supplied. The step statistic at a split k
(points 0..k-1 against k..n-1) is z_k = |m2 - m1| / sqrt(1/W1 + 1/W2) with inverse-variance weighted means and
W = sum 1/sigma^2; under no change each z_k is |N(0, 1)|. Binary segmentation splits a segment at its largest z_k when
that exceeds the threshold and recurses; under the global null the first test decides, so the false-alarm rate of
the whole series is P(max_k z_k > threshold), which calibrate_threshold sets by toys drawn with the same sigma_i.
CUSUM: standardized residuals e_i = (y_i - mu0) / sigma_i, S+ = max(0, S+ + e - k), S- = max(0, S- - e - k), alarm
when either exceeds h; mu0 is given or is the weighted mean of the first reference_points points, and the toys
repeat that estimate. If the quoted sigma_i are too small the false-alarm rate is higher than declared: check the
chi2 of the constant fit first.

Used by skills/hep-detector/scripts/stability_monitor.py (and by period searches in hep-statistics). Standard library
only; [General method].
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

from core.stats.statistical_toys import chi2_sf

LABEL = "[General method]"


class ChangePointError(ValueError):
    """Invalid series, uncertainties or options."""


def _check(y: Sequence[float], sigma: Sequence[float], min_points: int = 2) -> tuple[list[float], list[float]]:
    if len(y) != len(sigma):
        raise ChangePointError(f"values and uncertainties differ in length ({len(y)} vs {len(sigma)})")
    if len(y) < min_points:
        raise ChangePointError(f"need at least {min_points} points, got {len(y)}")
    yy, ss = [], []
    for v, s in zip(y, sigma):
        if isinstance(v, bool) or isinstance(s, bool):
            raise ChangePointError("values and uncertainties must be numbers")
        v, s = float(v), float(s)
        if not (math.isfinite(v) and math.isfinite(s)):
            raise ChangePointError("values and uncertainties must be finite")
        if s <= 0:
            raise ChangePointError("uncertainties must be > 0")
        yy.append(v)
        ss.append(s)
    return yy, ss


def split_statistics(y: Sequence[float], sigma: Sequence[float], min_size: int = 1) -> list[float]:
    """z_k for k = 0..n (0 where the split is not allowed: k < min_size or n - k < min_size)."""
    yy, ss = _check(y, sigma)
    n = len(yy)
    w = [1.0 / s / s for s in ss]
    cw, cwy = [0.0], [0.0]
    for wi, yi in zip(w, yy):
        cw.append(cw[-1] + wi)
        cwy.append(cwy[-1] + wi * yi)
    z = [0.0] * (n + 1)
    for k in range(max(min_size, 1), n - max(min_size, 1) + 1):
        w1, w2 = cw[k], cw[n] - cw[k]
        m1, m2 = cwy[k] / w1, (cwy[n] - cwy[k]) / w2
        z[k] = abs(m2 - m1) / math.sqrt(1.0 / w1 + 1.0 / w2)
    return z


def best_split(y: Sequence[float], sigma: Sequence[float], min_size: int = 1) -> dict:
    """The split with the largest step statistic: index k (first point after the step), z and the step m2 - m1."""
    yy, ss = _check(y, sigma)
    if len(yy) < 2 * max(min_size, 1):
        raise ChangePointError("the series is too short for the minimum segment size")
    z = split_statistics(yy, ss, min_size)
    k = max(range(len(z)), key=lambda i: z[i])
    w = [1.0 / s / s for s in ss]
    m1 = sum(a * b for a, b in zip(w[:k], yy[:k])) / sum(w[:k])
    m2 = sum(a * b for a, b in zip(w[k:], yy[k:])) / sum(w[k:])
    return {"index": k, "z": z[k], "step": m2 - m1}


def binary_segmentation(y: Sequence[float], sigma: Sequence[float], threshold: float, min_size: int = 1,
                        max_changes: int | None = None) -> list[dict]:
    """Change points (sorted by index) found by recursive splitting at z > threshold."""
    yy, ss = _check(y, sigma)
    if not math.isfinite(threshold) or threshold <= 0:
        raise ChangePointError("threshold must be a positive number")
    found: list[dict] = []
    stack = [(0, len(yy))]
    while stack:
        a, b = stack.pop()
        if b - a < 2 * max(min_size, 1):
            continue
        best = best_split(yy[a:b], ss[a:b], min_size)
        if best["z"] > threshold:
            k = a + best["index"]
            found.append({"index": k, "z": best["z"], "step": best["step"], "segment": [a, b]})
            if max_changes is not None and len(found) >= max_changes:
                break
            stack.extend([(a, k), (k, b)])
    return sorted(found, key=lambda c: c["index"])


def _mu0(y, sigma, reference_points, mu0):
    if mu0 is not None:
        return float(mu0)
    if reference_points is None or not 1 <= reference_points <= len(y):
        raise ChangePointError("CUSUM needs mu0 or 1 <= reference_points <= n")
    w = [1.0 / s / s for s in sigma[:reference_points]]
    return sum(a * b for a, b in zip(w, y[:reference_points])) / sum(w)


def cusum(y: Sequence[float], sigma: Sequence[float], k: float, mu0: float | None = None,
          reference_points: int | None = None) -> dict:
    """Two-sided CUSUM paths S+ and S- of the standardized residuals."""
    yy, ss = _check(y, sigma)
    if not math.isfinite(k) or k < 0:
        raise ChangePointError("the CUSUM allowance k must be >= 0")
    m = _mu0(yy, ss, reference_points, mu0)
    sp, sm, up, dn = 0.0, 0.0, [], []
    for v, s in zip(yy, ss):
        e = (v - m) / s
        sp, sm = max(0.0, sp + e - k), max(0.0, sm - e - k)
        up.append(sp)
        dn.append(sm)
    return {"mu0": m, "s_plus": up, "s_minus": dn}


def cusum_first_alarm(y: Sequence[float], sigma: Sequence[float], k: float, h: float, mu0: float | None = None,
                      reference_points: int | None = None) -> int | None:
    """Index of the first point where S+ or S- exceeds h (after the reference points), or None."""
    c = cusum(y, sigma, k, mu0, reference_points)
    start = reference_points if (mu0 is None and reference_points) else 0
    for i in range(start, len(c["s_plus"])):
        if c["s_plus"][i] > h or c["s_minus"][i] > h:
            return i
    return None


def _cusum_max(y, sigma, k, mu0, reference_points):
    c = cusum(y, sigma, k, mu0, reference_points)
    start = reference_points if (mu0 is None and reference_points) else 0
    return max(max(c["s_plus"][start:], default=0.0), max(c["s_minus"][start:], default=0.0))


def calibrate_threshold(sigma: Sequence[float], alpha: float, toys: int, seed: int, method: str = "segmentation",
                        min_size: int = 1, cusum_k: float = 0.5, reference_points: int | None = None) -> dict:
    """Threshold with P(detection somewhere in the series | no change) = alpha, from toys y_i ~ N(0, sigma_i)."""
    _, ss = _check([0.0] * len(sigma), sigma)
    if not 0.0 < alpha < 1.0:
        raise ChangePointError("the false-alarm rate must be in (0, 1)")
    if toys < max(100, int(math.ceil(10.0 / alpha))):
        raise ChangePointError(f"use at least max(100, 10 / alpha) = {max(100, int(math.ceil(10 / alpha)))} toys")
    rng = random.Random(seed)
    stat: Callable[[list[float]], float]
    if method == "segmentation":
        def stat(v: list[float]) -> float:
            return max(split_statistics(v, ss, min_size))
    elif method == "cusum":
        def stat(v: list[float]) -> float:
            return _cusum_max(v, ss, cusum_k, None if reference_points else 0.0, reference_points)
    else:
        raise ChangePointError("method must be segmentation or cusum")
    maxima = sorted(stat([rng.gauss(0.0, s) for s in ss]) for _ in range(toys))
    q = int(math.ceil((1.0 - alpha) * toys)) - 1
    thr = maxima[min(max(q, 0), toys - 1)]
    achieved = sum(1 for m in maxima if m > thr) / toys
    return {"method": method, "threshold": thr, "false_alarm_rate": alpha, "toys": toys, "seed": seed,
            "achieved_on_toys": achieved, "toy_uncertainty": math.sqrt(alpha * (1 - alpha) / toys),
            "cusum_k": cusum_k if method == "cusum" else None,
            "reference_points": reference_points if method == "cusum" else None, "min_size": min_size,
            "label": LABEL}


def weighted_fit(t: Sequence[float], y: Sequence[float], sigma: Sequence[float], model: str = "constant") -> dict:
    """Weighted least squares: 'constant' (mean) or 'linear' (intercept + slope t); chi2, ndf and p-value."""
    yy, ss = _check(y, sigma, 1 if model == "constant" else 2)
    tt = [float(v) for v in t]
    if len(tt) != len(yy) or not all(math.isfinite(v) for v in tt):
        raise ChangePointError("times must be finite and as many as the values")
    w = [1.0 / s / s for s in ss]
    if model == "constant":
        m = sum(a * b for a, b in zip(w, yy)) / sum(w)
        params = {"mean": m, "mean_error": 1.0 / math.sqrt(sum(w))}
        pred = [m] * len(yy)
        ndf = len(yy) - 1
    elif model == "linear":
        sw, st, sy = sum(w), sum(a * b for a, b in zip(w, tt)), sum(a * b for a, b in zip(w, yy))
        stt = sum(a * b * b for a, b in zip(w, tt))
        sty = sum(a * b * c for a, b, c in zip(w, tt, yy))
        det = sw * stt - st * st
        if det <= 0:
            raise ChangePointError("a linear fit needs at least two distinct times")
        slope = (sw * sty - st * sy) / det
        icpt = (stt * sy - st * sty) / det
        params = {"intercept": icpt, "slope": slope, "intercept_error": math.sqrt(stt / det),
                  "slope_error": math.sqrt(sw / det)}
        pred = [icpt + slope * v for v in tt]
        ndf = len(yy) - 2
    else:
        raise ChangePointError("model must be constant or linear")
    chi2 = sum(((a - b) / s) ** 2 for a, b, s in zip(yy, pred, ss))
    return {"model": model, "params": params, "chi2": chi2, "ndf": ndf,
            "p_value": chi2_sf(chi2, ndf) if ndf >= 1 else None, "label": LABEL}


def piecewise_constant(y: Sequence[float], sigma: Sequence[float], boundaries: Sequence[int]) -> dict:
    """Weighted means between the boundaries (indices of the first point of each new segment), chi2 and p-value."""
    yy, ss = _check(y, sigma, 1)
    cuts = [0] + sorted(int(b) for b in boundaries) + [len(yy)]
    if any(b <= a for a, b in zip(cuts, cuts[1:])):
        raise ChangePointError("boundaries must be distinct indices inside the series")
    segs, chi2 = [], 0.0
    for a, b in zip(cuts, cuts[1:]):
        w = [1.0 / s / s for s in ss[a:b]]
        m = sum(p * q for p, q in zip(w, yy[a:b])) / sum(w)
        chi2 += sum(((v - m) / s) ** 2 for v, s in zip(yy[a:b], ss[a:b]))
        segs.append({"start": a, "end": b, "mean": m, "mean_error": 1.0 / math.sqrt(sum(w))})
    ndf = len(yy) - len(segs)
    return {"segments": segs, "chi2": chi2, "ndf": ndf, "p_value": chi2_sf(chi2, ndf) if ndf >= 1 else None,
            "label": LABEL}
