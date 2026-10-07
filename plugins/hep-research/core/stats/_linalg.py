"""Shared linear-algebra helpers for core/stats (private; standard library only).

`cholesky` is the one Cholesky factorization of a covariance or correlation matrix in core/stats. It works on the
matrix scaled to a unit diagonal, so its tolerance is relative and its result does not depend on the units of the
input: a matrix scaled by 1e-12 or 1e12 gives the same verdict and a factor scaled by 1e-6 or 1e6. It never repairs a
matrix silently: a pivot below -rel_tol raises, a pivot within rel_tol of zero raises unless the caller accepts a
semi-definite matrix, and then the shift applied to that pivot is returned so the caller can report it.
"""
from __future__ import annotations

import math


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
