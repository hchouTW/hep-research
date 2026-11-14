"""The stated analytic light model of t04-values-v4.md section 4.3, the forward model of the likelihood (an analytic model of a
clear, uniform medium, in the reference's terms; its optical parameters are the section 4.3 constants, fixed, not fitted).

For a point source at `x` emitting along the unit vector `d`, the unscaled expected signal of sensor i is

    s_i = A cos(incidence_i) / d_i^2 exp(-d_i / 30 m) g(c_i),   g(c) = (1 - f)/(4 pi) + f k exp(k c) / (4 pi sinh k),

with `d_i` the distance to the sensor, `u_i` the unit vector to it, `cos(incidence_i) = u_i . n_i` and `c_i = u_i . d`. The
expected number of photons is `mu_i = 1000 E_vis s_i` (section 4.3: E_vis = N_exp / (1000 S), S = sum_i s_i), and the mean count
the charge model reads is `m_i = mu_i + dark`, dark the mean dark count per window. For a vertex inside the sphere every
`cos(incidence_i)` is positive, so no clip is applied (case O-domain of the D3 stage 1 report).

`model` is any object with `geometry` (configuration.Geometry) and `cfg` (configuration.Configuration).
"""
from __future__ import annotations

import math

import numpy


def _emission(cfg, c):
    norm = cfg.emission_f * cfg.emission_k / (4.0 * math.pi * math.sinh(cfg.emission_k))
    g = (1.0 - cfg.emission_f) / (4.0 * math.pi) + norm * numpy.exp(cfg.emission_k * c)
    return g, cfg.emission_k * norm * numpy.exp(cfg.emission_k * c)


def _geometry_terms(model, vertex):
    r = model.geometry.positions - vertex
    dist = numpy.sqrt((r * r).sum(axis=1))
    u = r / dist[:, None]
    return dist, u, (u * model.geometry.normals).sum(axis=1)


def shape(model, vertex, direction) -> numpy.ndarray:
    """s_i per channel, unscaled."""
    cfg = model.cfg
    dist, u, cos_incidence = _geometry_terms(model, numpy.asarray(vertex, float))
    g, _ = _emission(cfg, u @ numpy.asarray(direction, float))
    return model.geometry.area * cos_incidence / dist ** 2 * numpy.exp(-dist / cfg.attenuation_length_m) * g


def expected(model, vertex, direction, e_vis) -> numpy.ndarray:
    """m_i = 1000 E_vis s_i + dark, the mean photon count per channel in the readout window (signal plus dark)."""
    return model.cfg.sensors * e_vis * shape(model, vertex, direction) + model.cfg.dark_mean_per_window


def shape_log_gradient(model, vertex, direction):
    """(s, d ln s / d x, d ln s / d direction), the last two (C, 3). The direction derivative treats `direction` as a free
    3-vector (c = u . direction); the chart's chain rule is the caller's. Analytic:

    d ln s / d x = (d cos_inc / d x) / cos_inc + (2 / d_i + 1 / lambda) u_i + (g'/g)(d c / d x),
    d cos_inc / d x = -(n_i - cos_inc u_i) / d_i,  d c / d x = -(direction - c u_i) / d_i,  d ln s / d direction = (g'/g) u_i.
    """
    cfg = model.cfg
    vertex = numpy.asarray(vertex, float)
    direction = numpy.asarray(direction, float)
    dist, u, cos_incidence = _geometry_terms(model, vertex)
    c = u @ direction
    g, g_prime = _emission(cfg, c)
    s = model.geometry.area * cos_incidence / dist ** 2 * numpy.exp(-dist / cfg.attenuation_length_m) * g
    ratio = g_prime / g
    d_cos = -(model.geometry.normals - cos_incidence[:, None] * u) / dist[:, None]
    d_c = -(direction[None, :] - c[:, None] * u) / dist[:, None]
    d_x = d_cos / cos_incidence[:, None] + (2.0 / dist + 1.0 / cfg.attenuation_length_m)[:, None] * u + ratio[:, None] * d_c
    return s, d_x, ratio[:, None] * u
