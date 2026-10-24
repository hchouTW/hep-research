"""Analytic trajectories of a charged particle through piecewise-uniform magnetic fields (Geant4 program B1.7).

The reference of the deterministic field check: inside an axis-aligned box with a uniform field B the trajectory is
a helix about B, outside every field box it is a straight line. With path length s, unit direction u, momentum p
(GeV/c), charge q (units of e) and kappa = 0.299792458e-3 q |B| / p (1/mm, B in tesla), du/ds = kappa (u x b), whose
solution is u(s) = u_par b + u_perp cos(kappa s) + (u_perp x b) sin(kappa s) and
x(s) = x0 + u_par b s + u_perp sin(kappa s)/kappa + (u_perp x b) 2 sin^2(kappa s / 2)/kappa (the half-angle form
avoids the cancellation of 1 - cos at large radii). A positive charge moving along +x in B along +z bends toward -y.
Time is s / (beta c) with beta = p / E (beta = 1 for a massless charged geantino). Field boxes are given in mm in
world coordinates and may touch but not overlap; the trajectory is followed segment by segment, a helix inside a
box until it leaves the box, then a straight line until it enters the next box. first_entry gives the first point
at which the trajectory enters a box (a plane element): the earliest crossing of one of its faces with the other two
coordinates inside the face; on a helix segment the crossing is bracketed on a grid of steps no longer than
min(1 mm, 0.01 / kappa) and refined by bisection to 1e-12 mm. Standard library only; used by the geant4 adapter's
field check (geant4_verify.py field) and by hep-detector's field_propagation benchmark."""
from __future__ import annotations

import math
from dataclasses import dataclass

from core import trace

C_GEV_PER_T_MM = 0.299792458e-3  # p [GeV/c] = 0.299792458 B [T] r [m]: kappa per mm per tesla per (GeV/c)
C_MM_PER_NS = 299.792458


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _scale(a, k):
    return [a[0] * k, a[1] * k, a[2] * k]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(a):
    n = math.sqrt(_dot(a, a))
    if n == 0:
        raise ValueError("the zero vector has no direction")
    return [a[0] / n, a[1] / n, a[2] / n]


@dataclass
class FieldBox:
    lo: list  # mm, world coordinates
    hi: list
    b_tesla: list

    def contains(self, x, tol=1e-9) -> bool:
        return all(self.lo[i] - tol <= x[i] <= self.hi[i] + tol for i in range(3))


@dataclass
class Segment:
    """A piece of trajectory from path length s0 to s1: a helix (kappa != 0) or a straight line."""
    s0: float
    s1: float
    x0: list
    u0: list
    kappa: float = 0.0
    b: list | None = None

    def point(self, s: float) -> tuple[list, list]:
        t = s - self.s0
        if self.kappa == 0.0 or self.b is None:
            return _add(self.x0, _scale(self.u0, t)), list(self.u0)
        b, k = self.b, self.kappa
        upar = _dot(self.u0, b)
        uperp = _add(self.u0, _scale(b, -upar))
        w = _cross(uperp, b)
        c, sn = math.cos(k * t), math.sin(k * t)
        half = math.sin(k * t / 2)
        x = _add(_add(_add(self.x0, _scale(b, upar * t)), _scale(uperp, sn / k)), _scale(w, 2 * half * half / k))
        u = _add(_add(_scale(b, upar), _scale(uperp, c)), _scale(w, sn))
        return x, u


def _exit_straight(x, u, box: FieldBox) -> float:
    """Path length until a ray starting inside `box` leaves it."""
    out = math.inf
    for i in range(3):
        if u[i] > 0:
            out = min(out, (box.hi[i] - x[i]) / u[i])
        elif u[i] < 0:
            out = min(out, (box.lo[i] - x[i]) / u[i])
    return max(out, 0.0)


def _enter_straight(x, u, lo, hi) -> float | None:
    """Path length until a ray enters the box [lo, hi] (0 if it starts inside), None if never."""
    tmin, tmax = -math.inf, math.inf
    for i in range(3):
        if u[i] == 0:
            if not lo[i] <= x[i] <= hi[i]:
                return None
            continue
        a, b = (lo[i] - x[i]) / u[i], (hi[i] - x[i]) / u[i]
        tmin, tmax = max(tmin, min(a, b)), min(tmax, max(a, b))
    if tmax < max(tmin, 0.0):
        return None
    return max(tmin, 0.0)


def _bisect(f, a: float, b: float, fa: float) -> float:
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = f(m)
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b = m
        if b - a < 1e-12:
            break
    return 0.5 * (a + b)


def _grid(seg: Segment) -> float:
    return min(1.0, 0.01 / abs(seg.kappa)) if seg.kappa else math.inf


def trajectory(x0, direction, p_gev: float, charge: float, boxes: list[FieldBox], max_length_mm: float = 1e5,
               mass_gev: float = 0.0) -> dict:
    """The trajectory from x0 (mm) along direction with momentum p_gev and charge (e): its segments and its beta."""
    trace.tag("geant4-analytic-helix")
    if p_gev <= 0:
        raise ValueError("the momentum must be positive")
    x, u, s = list(map(float, x0)), _unit(list(map(float, direction))), 0.0
    segs: list[Segment] = []
    for _ in range(1000):
        if s >= max_length_mm:
            break
        probe = _add(x, _scale(u, 1e-7))
        inside = next((b for b in boxes if b.contains(probe, 0.0)), None)
        if inside is not None and any(inside.b_tesla) and charge:
            bmag = math.sqrt(_dot(inside.b_tesla, inside.b_tesla))
            seg = Segment(s, math.inf, list(x), list(u), C_GEV_PER_T_MM * charge * bmag / p_gev,
                          _unit(inside.b_tesla))
            h = _grid(seg)

            def outside(t, seg=seg, box=inside):
                pt = seg.point(t)[0]
                return max(max(box.lo[i] - pt[i], pt[i] - box.hi[i]) for i in range(3))
            t, prev = s, outside(s + 1e-7)
            end = None
            while t < max_length_mm:
                t2 = t + h
                f2 = outside(t2)
                if f2 > 0 >= prev:
                    end = _bisect(outside, t, t2, prev)
                    break
                t, prev = t2, f2
            end = max_length_mm if end is None else end
            seg.s1 = end
            segs.append(seg)
            x, u = seg.point(end)
            s = end
            continue
        # straight: until the next field box is entered (or for ever)
        nxt = math.inf
        for b in boxes:
            if not any(b.b_tesla) or b.contains(probe, 0.0):
                continue
            d = _enter_straight(x, u, b.lo, b.hi)
            if d is not None and d > 1e-9:
                nxt = min(nxt, d)
        end = min(s + nxt, max_length_mm)
        segs.append(Segment(s, end, list(x), list(u)))
        x, s = _add(x, _scale(u, end - s)), end
    beta = p_gev / math.sqrt(p_gev * p_gev + mass_gev * mass_gev)
    return {"segments": segs, "beta": beta}


def _helix_entry(seg: Segment, lo, hi) -> float | None:
    """The earliest path length in a helix segment at which it crosses a face of [lo, hi] with the other two
    coordinates inside the face (s0 itself if it starts inside). Each face is a sign change of one coordinate minus
    the face value, bracketed on the grid (a thin box cannot be stepped over this way) and bisected."""
    x0 = seg.point(seg.s0)[0]
    if all(lo[i] <= x0[i] <= hi[i] for i in range(3)):
        return seg.s0
    best = None
    h = _grid(seg)
    for axis in range(3):
        for value in (lo[axis], hi[axis]):
            def f(t, axis=axis, value=value):
                return seg.point(t)[0][axis] - value
            t, prev = seg.s0, f(seg.s0)
            while t < seg.s1 and (best is None or t < best):
                t2 = min(t + h, seg.s1)
                f2 = f(t2)
                if (f2 > 0) != (prev > 0) or f2 == 0:
                    r = _bisect(f, t, t2, prev) if f2 != 0 else t2
                    pt = seg.point(r)[0]
                    if all(lo[i] - 1e-9 <= pt[i] <= hi[i] + 1e-9 for i in range(3) if i != axis):
                        best = r if best is None else min(best, r)
                        break
                t, prev = t2, f2
    return best


def first_entry(traj: dict, lo, hi) -> dict | None:
    """The first point at which the trajectory enters the box [lo, hi] (mm): position, direction, path length and
    time (ns from s = 0); None if it never does."""
    for seg in traj["segments"]:
        if seg.kappa == 0.0:
            d = _enter_straight(seg.x0, seg.u0, lo, hi)
            if d is None or seg.s0 + d > seg.s1:
                continue
            s = seg.s0 + d
        else:
            s = _helix_entry(seg, lo, hi)
            if s is None:
                continue
        x, u = seg.point(s)
        return {"position_mm": x, "direction": u, "path_mm": s, "time_ns": s / (traj["beta"] * C_MM_PER_NS)}
    return None


def at_coordinate(traj: dict, axis: int, value: float) -> dict | None:
    """The first point at which coordinate `axis` of the trajectory equals `value` (the analytic trajectory evaluated
    at a plane's x)."""
    for seg in traj["segments"]:
        def f(t, seg=seg):
            return seg.point(t)[0][axis] - value
        if seg.kappa == 0.0:
            if seg.u0[axis] == 0:
                continue
            t = seg.s0 + (value - seg.x0[axis]) / seg.u0[axis]
            if not seg.s0 - 1e-12 <= t <= seg.s1 + 1e-12:
                continue
            s = t
        else:
            h, t, prev, s = _grid(seg), seg.s0, f(seg.s0), None
            if prev == 0:
                s = t
            while s is None and t < seg.s1:
                t2 = min(t + h, seg.s1)
                f2 = f(t2)
                if (f2 > 0) != (prev > 0) or f2 == 0:
                    s = _bisect(f, t, t2, prev)
                    break
                t, prev = t2, f2
            if s is None:
                continue
        x, u = seg.point(s)
        return {"position_mm": x, "direction": u, "path_mm": s, "time_ns": s / (traj["beta"] * C_MM_PER_NS)}
    return None
