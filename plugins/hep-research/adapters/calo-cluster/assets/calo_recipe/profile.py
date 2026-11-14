"""The shower profile of section 7.1: a two-dimensional Gaussian of width W integrated over each cell, g_c(x, y).

The grid covers [0, nx) x [0, ny) in cell units; cell ix spans [ix, ix + 1) along x (t04-values-v4.md section 7.1: cell centre
x_c = ix + 0.5). The profile factorises, g_c(x, y) = G(ix; x) G(iy; y), with G(i; c) = Phi((i + 1 - c)/W) - Phi((i - c)/W).

The difference of two normal integrals is formed on the side of the centre where it does not cancel: above the centre as
Q(a) - Q(b) with Q the upper tail, below it as Phi(b) - Phi(a). So a cell far from the centre gets its small value, not
rounding noise. dG/dc = -(phi((i + 1 - c)/W) - phi((i - c)/W)) / W.
"""
from __future__ import annotations

import numpy
from scipy import special

INV_SQRT_2PI = 0.3989422804014327


def axis_profile(centre: float, cells: int, width: float) -> numpy.ndarray:
    """G(i; centre) for i = 0 .. cells - 1."""
    lower = (numpy.arange(cells, dtype=float) - centre) / width
    upper = lower + 1.0 / width
    above = lower >= 0.0
    out = numpy.empty(cells)
    out[above] = special.ndtr(-lower[above]) - special.ndtr(-upper[above])
    out[~above] = special.ndtr(upper[~above]) - special.ndtr(lower[~above])
    return numpy.maximum(out, 0.0)


def axis_profile_derivative(centre: float, cells: int, width: float) -> numpy.ndarray:
    """dG(i; c)/dc at c = centre, for i = 0 .. cells - 1."""
    lower = (numpy.arange(cells, dtype=float) - centre) / width
    upper = lower + 1.0 / width
    density = lambda u: INV_SQRT_2PI * numpy.exp(-0.5 * u * u)  # noqa: E731
    return -(density(upper) - density(lower)) / width


def cell_profile(x: float, y: float, nx: int, ny: int, width: float) -> numpy.ndarray:
    """g_c(x, y) on the whole grid, array axis 0 is ix."""
    return numpy.outer(axis_profile(x, nx, width), axis_profile(y, ny, width))
