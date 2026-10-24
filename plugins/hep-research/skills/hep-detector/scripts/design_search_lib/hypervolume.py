"""Exact hypervolume of a point set for minimisation (WFG: L. While, L. Bradstreet, L. Barone, "A fast way of
calculating exact hypervolumes", IEEE Trans. Evol. Comput. 16 (2012) 86-95), with exact sweeps for two and three
objectives as the base cases. Points not strictly better than the reference point on every objective contribute
nothing."""
from __future__ import annotations

import math


def dominates(a, b) -> bool:
    """a is no worse than b on every objective and better on one (minimisation)."""
    better = False
    for x, y in zip(a, b):
        if x > y:
            return False
        if x < y:
            better = True
    return better


def nondominated(points: list) -> list:
    """The non-dominated points (duplicates kept once), in input order."""
    out: list = []
    for p in points:
        if any(dominates(q, p) or list(q) == list(p) for q in out):
            continue
        out = [q for q in out if not dominates(p, q)] + [list(p)]
    return out


def _hv2(points: list, ref) -> float:
    pts = sorted(points)
    total, best_y = 0.0, ref[1]
    for x, y in pts:
        if y < best_y:
            total += (ref[0] - x) * (best_y - y)
            best_y = y
    return total


def _hv3(points: list, ref) -> float:
    """Three objectives: sweep along the third, keeping the two-objective staircase of the points below and its area
    updated incrementally (each insertion adds the area between the new point and the old staircase)."""
    import bisect
    pts = sorted(points, key=lambda p: (p[2], p[0], p[1]))
    xs: list = []  # staircase: x ascending, y descending
    ys: list = []
    area, total = 0.0, 0.0
    rx, ry = ref[0], ref[1]
    for k, (x, y, z) in enumerate(pts):
        i = bisect.bisect_left(xs, x)
        if i > 0 and ys[i - 1] <= y or i < len(xs) and xs[i] == x and ys[i] <= y:
            pass  # dominated in (x, y) by a point already below
        else:
            j = i
            while j < len(xs) and ys[j] >= y:
                j += 1
            h = ys[i - 1] if i > 0 else ry  # height of the old staircase just right of x
            edges = [x] + xs[i:j] + [xs[j] if j < len(xs) else rx]
            heights = [h] + ys[i:j]
            area += sum((b - a) * (hh - y) for a, b, hh in zip(edges, edges[1:], heights))
            xs[i:j] = [x]
            ys[i:j] = [y]
        z_next = pts[k + 1][2] if k + 1 < len(pts) else ref[2]
        total += area * (z_next - z)
    return total


def _wfg(points: list, ref, sweep3: bool = True) -> float:
    """WFG on non-dominated points: the sum of each point's exclusive volume, its inclusive box minus the volume of
    the limit set of the points after it."""
    if not points:
        return 0.0
    m = len(ref)
    if m == 1:
        return ref[0] - min(p[0] for p in points)
    if m == 2:
        return _hv2(points, ref)
    if m == 3 and sweep3:
        return _hv3(points, ref)
    pts = sorted(points, key=lambda p: p[-1], reverse=True)
    total = 0.0
    for k, p in enumerate(pts):
        incl = math.prod(r - x for r, x in zip(ref, p))
        limit = [[max(a, b) for a, b in zip(p, q)] for q in pts[k + 1:]]
        total += incl - _wfg(nondominated(limit), ref, sweep3)
    return total


def _wfg_generic(points: list, ref) -> float:
    """WFG without the three-objective sweep (a cross-check in the tests)."""
    return _wfg(points, ref, sweep3=False)


def hypervolume(points: list, ref) -> float:
    """Exact hypervolume dominated by points and bounded by ref (minimisation)."""
    inside = [list(p) for p in points if all(math.isfinite(x) and x < r for x, r in zip(p, ref))]
    if len(ref) in (2, 3):  # the sweeps need no prior non-dominated filter
        return _wfg(inside, list(ref))
    return _wfg(nondominated(inside), list(ref))
