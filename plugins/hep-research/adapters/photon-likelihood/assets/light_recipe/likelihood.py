"""The charge-only all-channel likelihood (the reference, "The per-channel likelihood"; t07-t09-task-sheets.md, T09):

    ln L = sum_{live hit, unsaturated} ln f(q_i | m_i) + sum_{live hit, saturated} ln P(q >= C | m_i) + sum_{live unhit} ln P(no hit | m_i)

Every live channel enters; dead and disabled channels are excluded, never unhit; the hit and no-hit terms use the one threshold
model of charge_response, so P(hit) + P(no hit) = 1 per channel, which probability_check verifies at a point (the sheet's stop);
saturated channels are censored. m_i comes from the stated light model (light_model). The channel product assumes independent
channels: the fixture has no correlated noise or afterpulsing (the reference, channel independence).

The fit coordinates are p = (x, y, z, a, b, E_vis): vertex in m; a, b the tangent components of a chart around a reference
direction d_ref, direction = norm(d_ref + a e1 + b e2) with (e1, e2) = frame(d_ref), section 7's rule; E_vis. Objective gives
ln L, its gradient and its Hessian in these coordinates: per-channel derivatives in m are exact (charge_response); the first
derivatives of m are analytic (light_model); its second derivatives in (x, a, b) are central differences of those analytic first
derivatives, with the steps HESSIAN_STEPS (case O-uncertainty).

The domain (fix round 1, F1 and F3; case O-domain): |x| < R_s (1 - DOMAIN_MARGIN), E_vis > 0, and the implied photon yield
sum_i mu_i = 1000 E_vis S at most YIELD_DOMAIN (fifty times section 4.3's largest N_exp, 2,000). The yield bound caps every m_i
and so the cost of every term; the margin (5 mm) keeps the light model's 1/d^2 finite and is far wider than the Hessian's
finite-difference steps. Outside the domain the objective is total: ln L = -inf with a zero gradient and the Hessian -I, so a
trust-region proposal there is evaluated cheaply and rejected (rho = -inf), never raised. The fixture's vertices lie at
r <= 0.9 R_s and its yields at N_exp <= 2,000, inside the domain by a wide margin.

The per-channel sum check's tolerance (fix round 1, F5) follows the arithmetic: each log term n ln m - m - lnGamma(n + 1) has an
absolute rounding error of order eps m |ln m|, which becomes the absolute error of P(hit) and P(no hit); the tolerance is
64 eps (1 + m |ln m|) per channel, eps = 2^-52 (1.4e-14 at m <= 1; 1.1e-10 at m = 1,101, the largest m at the fixture's truth;
1.6e-8 at m = 1e5, the most one channel can hold inside the yield domain).

A hit charge above CHARGE_DOMAIN (the yield domain's 1e5) is refused as outside the model's domain (D3 stage 2, re-review N5):
the charge sets the width of the sums over the photon count, so an absurd but finite charge (1e9) would otherwise exhaust memory.
The fixture's charges stay below a few thousand.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy

from . import light_model, readout
from .arrival_response import ArrivalResponse
from .charge_response import ChargeResponse
from .configuration import Configuration, Geometry, fibonacci_geometry

EPSILON = 2.0 ** -52
TOLERANCE_FACTOR = 64
TOLERANCE_RULE = "64 eps (1 + m |ln m|) per channel, eps = 2^-52"
HESSIAN_STEPS = {"vertex_m": 1e-5, "direction": 1e-6}
DOMAIN_MARGIN = 1e-3          # a vertex must satisfy |x| < R_s (1 - DOMAIN_MARGIN), 5 mm inside the sensors
YIELD_DOMAIN = 1e5           # sum_i mu_i at most fifty times section 4.3's largest N_exp
CHARGE_DOMAIN = 1e5          # a hit charge at most the yield domain (D3 stage 2, N5)


def sum_tolerance(m):
    """The per-channel tolerance of |P(hit) + P(no hit) - 1| at mean count m (module docstring)."""
    m = numpy.asarray(m, float)
    return TOLERANCE_FACTOR * EPSILON * (1.0 + m * numpy.abs(numpy.log(m)))


class EventError(ValueError):
    """An event is refused for the likelihood: the reason names the defect."""


class Model:
    """The configuration, the sensor geometry (the Fibonacci lattice unless given), and the charge response with the
    configuration's threshold."""

    def __init__(self, cfg: Configuration, geometry: Geometry | None = None):
        self.cfg = cfg
        self.geometry = geometry if geometry is not None else fibonacci_geometry(cfg)
        self.response = ChargeResponse(cfg.charge_threshold, cfg.photon_charge_mean, cfg.photon_charge_sigma)
        self.dark = cfg.dark_mean_per_window
        self.scale = cfg.sensors          # the 1000 of E_vis = N_exp / (1000 S), section 4.3
        self.arrival = ArrivalResponse(self.response, cfg.time_spread_ns, cfg.dark_mean_per_window, cfg.window_ns)


@dataclass(frozen=True)
class EventData:
    """One event as the charge-only likelihood sees it: per channel the state, charge and saturated flag, side by side, with
    the readout's threshold and saturation value. Built through the readout format's own rules."""
    state: numpy.ndarray
    charge: numpy.ndarray
    saturated: numpy.ndarray
    saturation_charge: float | None
    threshold: float

    def __post_init__(self):
        if not (self.state.ndim == 1 and self.state.shape == self.charge.shape == self.saturated.shape):
            raise EventError("state, charge and saturated must be one array per channel each")
        try:
            readout.check_arrays(self.state, self.charge, None, self.saturated, self.threshold, self.saturation_charge)
        except readout.ReadoutError as exc:
            raise EventError(str(exc)) from None
        if numpy.any(self.charge[self.state == readout.LIVE_HIT] > CHARGE_DOMAIN):
            raise EventError(f"a hit charge above {CHARGE_DOMAIN:g} is outside the model's domain")

    @classmethod
    def from_readout(cls, rd, index: int) -> "EventData":
        return cls(rd.state[index], rd.charge[index], rd.saturated[index], rd.header["saturation_charge"], rd.header["threshold"])

    @property
    def channels(self) -> int:
        return self.state.size

    @property
    def hit(self):
        return self.state == readout.LIVE_HIT

    @property
    def unhit(self):
        return self.state == readout.LIVE_UNHIT

    @property
    def live(self):
        return self.hit | self.unhit

    @property
    def dead(self):
        return self.state == readout.DEAD

    @property
    def disabled(self):
        return self.state == readout.DISABLED


def frame(d):
    """Section 7's tangent frame at the unit vector d: e1 = a x d normalised, a the z axis, or the x axis where |d_z| > 0.9;
    e2 = d x e1."""
    d = numpy.asarray(d, float)
    a = numpy.array([0.0, 0.0, 1.0]) if abs(d[2]) <= 0.9 else numpy.array([1.0, 0.0, 0.0])
    e1 = numpy.cross(a, d)
    e1 /= numpy.linalg.norm(e1)
    return e1, numpy.cross(d, e1)


def _check_model(model: Model, event: EventData) -> None:
    if event.threshold != model.response.threshold:
        raise EventError(f"the readout's threshold {event.threshold} is not the configuration's {model.response.threshold}: "
                         "hit flag and likelihood must share one threshold model")
    if event.channels != model.geometry.channels:
        raise EventError(f"{event.channels} channels in the event, {model.geometry.channels} in the geometry")


def in_domain(model: Model, vertex, e_vis, m=None) -> bool:
    """The fit's domain (module docstring). m, the mean counts at the point, if already computed."""
    vertex = numpy.asarray(vertex, float)
    if not (numpy.all(numpy.isfinite(vertex)) and numpy.linalg.norm(vertex) < model.cfg.sphere_radius_m * (1.0 - DOMAIN_MARGIN)
            and math.isfinite(e_vis) and e_vis > 0):
        return False
    if m is None:
        return True
    return bool(numpy.all(numpy.isfinite(m)) and (m - model.dark).sum() <= YIELD_DOMAIN)


def channel_terms(model: Model, event: EventData, m):
    """(l, dl/dm, d2l/dm2) per channel at mean counts m; zero for dead and disabled channels, which do not enter."""
    out = [numpy.zeros(event.channels) for _ in range(3)]
    hit_open = event.hit & ~event.saturated
    hit_clipped = event.hit & event.saturated
    groups = ((event.unhit, lambda mm: model.response.log_no_hit(mm)),
              (hit_open, lambda mm: model.response.log_hit_density(event.charge[hit_open], mm)),
              (hit_clipped, lambda mm: model.response.log_at_or_above(event.saturation_charge, mm)))
    for mask, term in groups:
        if mask.any():
            values = term(m[mask])
            for k in range(3):
                out[k][mask] = values[k]
    return out


def log_likelihood(model: Model, event: EventData, vertex, direction, e_vis) -> float:
    _check_model(model, event)
    vertex = numpy.asarray(vertex, float)
    if not in_domain(model, vertex, e_vis):
        return -math.inf
    direction = numpy.asarray(direction, float) / numpy.linalg.norm(direction)
    m = light_model.expected(model, vertex, direction, e_vis)
    if not in_domain(model, vertex, e_vis, m):
        return -math.inf
    return float(channel_terms(model, event, m)[0].sum())


def probability_check(model: Model, event: EventData, vertex=None, direction=None, e_vis=None) -> dict:
    """P(hit) + P(no hit) per live channel at a point (vertex None: the dark-only mean, the point of an event with no seed)."""
    _check_model(model, event)
    live = event.live
    if vertex is None:
        m = numpy.full(event.channels, model.dark)
    else:
        m = light_model.expected(model, numpy.asarray(vertex, float), numpy.asarray(direction, float), e_vis)
    if vertex is not None and not in_domain(model, vertex, e_vis, m):
        raise EventError("the probability check was asked outside the fit's domain")
    p_hit, p_no = model.response.probability_sums(m[live])
    deviation = numpy.abs(p_hit + p_no - 1.0)
    ratio = deviation / sum_tolerance(m[live])
    bad = ~(ratio <= 1.0)
    channels = numpy.flatnonzero(live)
    return {"channels": int(live.sum()), "failures": int(bad.sum()),
            "max_abs_deviation": float(deviation.max()) if deviation.size else 0.0,
            "largest_ratio": float(ratio.max()) if ratio.size else 0.0,
            "failed_channels": [int(c) for c in channels[bad][:10]]}


class Objective:
    """ln L in the chart coordinates p = (x, y, z, a, b, E_vis) around d_ref, with its gradient and Hessian."""

    def __init__(self, model: Model, event: EventData, d_ref):
        _check_model(model, event)
        self.model = model
        self.event = event
        self.d_ref = numpy.asarray(d_ref, float) / numpy.linalg.norm(d_ref)
        self.e1, self.e2 = frame(self.d_ref)
        self._value_cache = (None, None)
        self._full_cache = (None, None)

    def direction(self, a: float, b: float):
        v = self.d_ref + a * self.e1 + b * self.e2
        return v / numpy.linalg.norm(v)

    def _m_gradient(self, p):
        """m (C,) and dm/dp (C, 6) at p."""
        mu, gradient = self._mu_gradient(p)
        return mu + self.model.dark, gradient

    def _mu_gradient(self, p):
        """mu (C,), the expected signal photons without the dark mean, and dmu/dp = dm/dp (C, 6) at p."""
        model = self.model
        vertex = p[:3]
        v = self.d_ref + p[3] * self.e1 + p[4] * self.e2
        norm = numpy.linalg.norm(v)
        d = v / norm
        jac_dir = numpy.column_stack([(e - d * (d @ e)) / norm for e in (self.e1, self.e2)])   # d direction / d(a, b)
        s, d_x, d_dir = light_model.shape_log_gradient(model, vertex, d)
        mu = model.scale * p[5] * s
        gradient = numpy.column_stack((mu[:, None] * d_x, mu[:, None] * (d_dir @ jac_dir), model.scale * s))
        return mu, gradient

    def value(self, p) -> float:
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._value_cache[0] == key:
            return self._value_cache[1]
        out = -math.inf
        if in_domain(self.model, p[:3], p[5]):
            m, _ = self._m_gradient(p)
            if in_domain(self.model, p[:3], p[5], m):
                out = float(channel_terms(self.model, self.event, m)[0].sum())
        self._value_cache = (key, out)
        return out

    def derivatives(self, p):
        """(ln L, gradient (6,), Hessian (6, 6)) at p. Outside the domain: (-inf, zeros, -I), total and cheap, so a trust-region
        proposal there is rejected rather than raised (fix round 1, F1)."""
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._full_cache[0] == key:
            return self._full_cache[1]
        outside = (-math.inf, numpy.zeros(6), -numpy.eye(6))
        if not in_domain(self.model, p[:3], p[5]):
            return outside
        m, grad_m = self._m_gradient(p)
        if not in_domain(self.model, p[:3], p[5], m):
            return outside
        l0, l1, l2 = channel_terms(self.model, self.event, m)
        second = self.second_derivatives(p, grad_m)
        gradient = grad_m.T @ l1
        hessian = (grad_m * l2[:, None]).T @ grad_m + numpy.einsum("i,ijk->jk", l1, second)
        hessian = 0.5 * (hessian + hessian.T)
        out = (float(l0.sum()), gradient, hessian)
        self._full_cache = (key, out)
        self._value_cache = (key, out[0])
        return out

    def second_derivatives(self, p, grad_m):
        """d2 m / dp dp (C, 6, 6) at p: central differences of the analytic first derivatives in (x, a, b) with HESSIAN_STEPS,
        the E_vis rows exact (case O-uncertainty)."""
        second = numpy.zeros((grad_m.shape[0], 6, 6))
        steps = (HESSIAN_STEPS["vertex_m"],) * 3 + (HESSIAN_STEPS["direction"],) * 2
        for k, h in enumerate(steps):
            e = numpy.zeros(6)
            e[k] = h
            second[:, k, :5] = (self._m_gradient(p + e)[1][:, :5] - self._m_gradient(p - e)[1][:, :5]) / (2 * h)
            second[:, k, 5] = grad_m[:, k] / p[5]          # d2 m / d q_k d E = 1000 ds/dq_k, exact
        second[:, :5, :5] = 0.5 * (second[:, :5, :5] + second[:, :5, :5].transpose(0, 2, 1))
        second[:, 5, :5] = second[:, :5, 5]
        return second
