"""Shared numerical helpers for core/stats (private; standard library only): linear algebra, one-dimensional root
finding and minimization. Each is owned here once; the modules keep thin aliases for their old private names.

Every helper reports when it did not do its job: `cholesky` refuses a matrix that is not positive (semi-)definite, and
records any shift it made; `jacobi_eigh` fills `info` with whether the rotations converged; `solve` refuses an exactly
singular matrix and records its smallest pivot relative to the largest entry; `bisect` refuses a root the interval
does not bracket instead of returning an end of the interval.

`cholesky` works on the matrix scaled to a unit diagonal, so its tolerance is relative and its result does not depend
on the units of the input: a matrix scaled by 1e-12 or 1e12 gives the same verdict and a factor scaled by 1e-6 or 1e6.
It never repairs a matrix silently: a pivot below -rel_tol raises, a pivot within rel_tol of zero raises unless the
caller accepts a semi-definite matrix, and then the shift applied to that pivot is returned so the caller can report it.
"""
from __future__ import annotations

import math
import os


class LinAlgError(ValueError):
    """A matrix is not positive (semi-)definite within the stated relative tolerance."""


def cholesky(c, name: str, *, rel_tol: float = 1e-10, semidefinite: bool = False,
             error: type[Exception] = LinAlgError) -> tuple[list[list[float]], dict | None]:
    """Lower-triangular L with L L^T = c, and a record of any regularization (None when none was needed).

    c is a square symmetric matrix (the caller checks symmetry). A zero diagonal entry is allowed only with
    semidefinite=True and only when its whole row is zero; that row of L is zero. With semidefinite=True, a pivot in
    [-rel_tol, rel_tol] of the unit-diagonal matrix is raised to rel_tol and counted in the record.
    """
    n = len(c)
    diag = [c[i][i] for i in range(n)]
    if any(not math.isfinite(v) for row in c for v in row):
        raise error(f"{name} has a non-finite entry")
    if any(d < 0 for d in diag):
        raise error(f"{name} has a negative diagonal entry")
    top = max(diag, default=0.0)
    if top <= 0:
        raise error(f"{name} is zero")
    zero = [d <= 0.0 for d in diag]
    if any(zero) and not semidefinite:
        raise error(f"{name} has a zero diagonal entry: it is not positive definite")
    for i in range(n):
        if zero[i] and any(c[i][j] != 0.0 for j in range(n)):
            raise error(f"{name} row {i} has a zero variance but a nonzero covariance: it is not positive semi-definite")
    s = [0.0 if zero[i] else math.sqrt(diag[i]) for i in range(n)]
    l = [[0.0] * n for _ in range(n)]
    shifted, worst = 0, 0.0
    for i in range(n):
        if zero[i]:
            continue
        for j in range(i + 1):
            if zero[j]:
                continue
            v = c[i][j] / (s[i] * s[j]) - sum(l[i][m] * l[j][m] for m in range(j))
            if i != j:
                l[i][j] = v / l[j][j]
                continue
            if v < -rel_tol:
                raise error(f"{name} is not positive semi-definite: pivot {v:.3g} at row {i} of the unit-diagonal "
                            f"matrix (tolerance {rel_tol:g})")
            if v <= rel_tol:
                if not semidefinite:
                    raise error(f"{name} is singular within the relative tolerance {rel_tol:g} (pivot {v:.3g} at row "
                                f"{i}); a fit or inverse needs a positive-definite matrix")
                shifted += 1
                worst = max(worst, rel_tol - v)
                v = rel_tol
            l[i][i] = math.sqrt(v)
    for i in range(n):
        l[i] = [l[i][j] * s[i] for j in range(n)]
    record = None
    if shifted:
        record = {"matrix": name, "pivots_shifted": shifted, "max_shift_relative_to_unit_diagonal": worst,
                  "rel_tol": rel_tol, "note": "semi-definite within the tolerance; the shifted pivots were raised to it"}
    return l, record


def jacobi_eigh(matrix, max_sweeps: int = 100, *, criterion: str = "frobenius", sort: bool = True,
                info: dict | None = None) -> tuple[list[float], list[list[float]]]:
    """Eigen-decomposition of a real symmetric matrix by cyclic Jacobi rotations: (eigenvalues, eigenvector columns).

    criterion: when the off-diagonal part counts as zero. "frobenius" (validate_covariance): sum of squared
    off-diagonal entries <= (eps^2 * 1e-4) times the sum of all squared entries. "diagonal" (unfolding): < 1e-24 times
    the sum of squared diagonal entries. sort=True returns the eigenvalues ascending with their vectors.
    info, when given, receives {"converged", "sweeps", "off_diagonal"}: max_sweeps can run out.
    """
    n = len(matrix)
    a = [list(row) for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    eps = 2.220446049250313e-16
    scale = sum(x * x for row in a for x in row) or 1.0
    converged, sweeps, off = False, 0, 0.0
    for sweeps in range(1, max_sweeps + 1):  # noqa: B007 - read after the loop, for info
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(i + 1, n))
        if criterion == "frobenius":
            done = off <= (eps ** 2) * scale * 1e-4
        else:
            done = off < 1e-24 * max(sum(a[i][i] ** 2 for i in range(n)), 1e-300)
        if done:
            converged = True
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if (apq == 0.0) if criterion == "frobenius" else (abs(apq) < 1e-300):
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                sign = math.copysign(1.0, theta) if criterion == "frobenius" else (1.0 if theta >= 0 else -1.0)
                t = sign / (abs(theta) + math.sqrt(theta * theta + 1.0))  # the two callers' sign conventions at -0.0
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    else:
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(i + 1, n))
    if info is not None:
        info.update(converged=converged or n <= 1, sweeps=sweeps, off_diagonal=off)
    if not sort:
        return [a[i][i] for i in range(n)], v
    order = sorted(range(n), key=lambda i: a[i][i])
    return [a[i][i] for i in order], [[v[k][i] for i in order] for k in range(n)]


def solve(a, b, *, error: type[Exception] = LinAlgError, what: str = "matrix", info: dict | None = None):
    """Solve a X = b (square a, matrix b) by Gauss-Jordan elimination with partial pivoting.

    An exactly singular pivot (below 1e-300) raises `error`; info, when given, receives the smallest pivot relative to
    the largest |a| entry, a measure of how close to singular the system was."""
    n = len(a)
    m = [list(a[i]) + list(b[i]) for i in range(n)]
    top = max((abs(x) for row in a for x in row), default=0.0) or 1.0
    smallest = math.inf
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[piv][c]) < 1e-300:
            raise error(f"singular {what}; use a larger strength or fewer singular values")
        smallest = min(smallest, abs(m[piv][c]) / top)
        m[c], m[piv] = m[piv], m[c]
        pv = m[c][c]
        m[c] = [v / pv for v in m[c]]
        for r in range(n):
            if r != c and m[r][c] != 0.0:
                f = m[r][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    if info is not None:
        info["min_pivot_ratio"] = smallest if n else None
    return [row[n:] for row in m]


def chol_solve(l, b):
    """x with L L^T x = b for a lower-triangular L (forward then back substitution)."""
    n = len(l)
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(l[i][j] * y[j] for j in range(i))) / l[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(l[j][i] * x[j] for j in range(i + 1, n))) / l[i][i]
    return x


def matmul(a, b):
    bt = list(zip(*b))
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def transpose(a):
    return [list(r) for r in zip(*a)]


def bisect(f, lo: float, hi: float, iters: int, *, increasing: bool, error: type[Exception] = LinAlgError,
           what: str = "the root") -> float:
    """Root of a monotone f on [lo, hi] by bisection, refusing an interval that does not bracket it.

    increasing=True: f(lo) < 0 <= f(hi), and a midpoint with f < 0 moves lo. increasing=False: f(lo) > 0 >= f(hi), and a
    midpoint with f > 0 moves lo."""
    below = (lambda y: y < 0) if increasing else (lambda y: y > 0)
    if not below(f(lo)) or below(f(hi)):
        raise error(f"{what} is not bracketed in [{lo:g}, {hi:g}]: no value is reported")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if below(f(mid)):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def golden_min(f, lo, hi, iters=60):
    """Minimum of a unimodal f on [lo, hi] by golden-section search (the interval shrinks by 0.618 per step)."""
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
    f1, f2 = f(x1), f(x2)
    for _ in range(iters):
        if f1 > f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + g * (hi - lo)
            f2 = f(x2)
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - g * (hi - lo)
            f1 = f(x1)
    return 0.5 * (lo + hi)


def scan_then_golden(f, lo, hi, points=25):
    """A grid scan for the lowest point, then golden-section search between its neighbours."""
    grid = [lo + (hi - lo) * k / (points - 1) for k in range(points)]
    k = min(range(points), key=lambda i: f(grid[i]))
    return golden_min(f, grid[max(k - 1, 0)], grid[min(k + 1, points - 1)])


def eigh(matrix, *, info: dict | None = None) -> tuple[list[float], list[list[float]]]:
    """Eigenvalues ascending and eigenvector columns of a real symmetric matrix, by numpy.linalg.eigh when NumPy is
    installed (fast at any size) and otherwise by Jacobi rotations (standard library only, cubic cost).
    HEP_STATS_PURE_PYTHON=1 forces the Jacobi path. info receives the method and whether it converged."""
    if os.environ.get("HEP_STATS_PURE_PYTHON") != "1":
        try:
            import numpy as np
        except ImportError:
            np = None  # type: ignore[assignment]  # optional dependency: None marks it absent
        if np is not None and matrix:
            try:
                np_values, np_vectors = np.linalg.eigh(np.asarray(matrix, dtype=float))
            except np.linalg.LinAlgError:
                pass  # did not converge: fall back to the rotations, which say so in info
            else:
                if info is not None:
                    info.update(method="numpy.linalg.eigh", converged=True)
                return [float(x) for x in np_values], [[float(x) for x in row] for row in np_vectors]
    values, vectors = jacobi_eigh(matrix, criterion="frobenius", info=info)
    if info is not None:
        info["method"] = "jacobi"
    return values, vectors
