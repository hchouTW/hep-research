"""The joint charge-time all-channel likelihood (D3 stage 2; the reference, "The per-channel likelihood" with its time term;
t07-t09-task-sheets.md, T09):

    ln L = sum_{live hit, unsaturated} ln p(q_i, t_i) + sum_{live hit, saturated} ln P(q >= C, t_i) + sum_{live unhit} ln P(no hit | m_i)

p and P(q >= C, t) are arrival_response's joint terms (charge and first-arrival time together, exact for the fixture: case
O-factorization of the D3 stage 2 report); unhit live channels keep stage 1's no-hit term and carry no time; dead and disabled
channels stay out. Per channel mu_i = 1000 E_vis s_i (light_model), m_i = mu_i + dark, tau_i = t0 + d_i / v (d_i the distance to
sensor i, v the photon speed of section 4.3). The per-channel sum check is stage 1's (likelihood.probability_check): the time
density integrates to one at every charge, identically.

The fit coordinates are stage 1's with t0 appended: p = (x, y, z, a, b, E_vis, t0). Objective gives ln L, its gradient and its
Hessian: the derivatives of each term in (mu, tau) are exact (arrival_response, charge_response); dmu/dp and its second
derivatives as stage 1 (likelihood.Objective); dtau/dx = -u_i / v and d2tau/dx dx = (I - u_i u_i^T) / (d_i v), exact.

The domain is stage 1's with -W < t0 < 2W (W the window, 200 ns; case O-t0-domain); outside it the objective is total as in
stage 1 (ln L = -inf, zero gradient, Hessian -I). A hit time beyond +-TIME_DOMAIN is refused as outside the model's domain.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy

from . import light_model, readout
from .likelihood import EventData, EventError, Model, Objective as ChargeObjective, _check_model, in_domain

T0_DOMAIN_WINDOWS = (-1.0, 2.0)        # t0 in (-W, 2W)
TIME_DOMAIN = 1e6                     # ns: a hit time beyond +-1e6 ns is outside the model's domain


@dataclass(frozen=True)
class TimedEvent:
    """One event with its first-arrival times: the readout's charge view (EventData) and the time per channel, finite for every
    hit and NaN elsewhere, checked by the readout format's own rules."""
    event: EventData
    time: numpy.ndarray

    def __post_init__(self):
        ev = self.event
        if self.time.shape != ev.state.shape:
            raise EventError("time must be one value per channel")
        try:
            readout.check_arrays(ev.state, ev.charge, self.time, ev.saturated, ev.threshold, ev.saturation_charge)
        except readout.ReadoutError as exc:
            raise EventError(str(exc)) from None
        if numpy.any(numpy.abs(self.time[ev.hit]) > TIME_DOMAIN):
            raise EventError(f"a hit time beyond +-{TIME_DOMAIN:g} ns is outside the model's domain")

    @classmethod
    def from_readout(cls, rd, index: int) -> "TimedEvent":
        return cls(EventData.from_readout(rd, index), rd.time[index])


def t0_in_domain(model: Model, t0) -> bool:
    lo, hi = (w * model.cfg.window_ns for w in T0_DOMAIN_WINDOWS)
    return bool(math.isfinite(t0) and lo < t0 < hi)


def arrival_delays(model: Model, vertex):
    """d_i / v per channel (ns) and the unit vectors u_i from the vertex to the sensors, with d_i."""
    r = model.geometry.positions - numpy.asarray(vertex, float)
    dist = numpy.sqrt((r * r).sum(axis=1))
    return dist / model.cfg.photon_speed_m_per_ns, r / dist[:, None], dist


def channel_terms(model: Model, tev: TimedEvent, mu, tau):
    """(l, l_mu, l_tau, l_mumu, l_mutau, l_tautau) per channel at signal means mu and arrival centres tau; zero for dead and
    disabled channels, which do not enter; the time derivatives zero for unhit channels."""
    ev = tev.event
    out = [numpy.zeros(ev.channels) for _ in range(6)]
    if ev.unhit.any():
        l0, l1, l2 = model.response.log_no_hit(mu[ev.unhit] + model.dark)
        out[0][ev.unhit], out[1][ev.unhit], out[3][ev.unhit] = l0, l1, l2
    for mask, term in ((ev.hit & ~ev.saturated, lambda sel: model.arrival.log_joint_density(ev.charge[sel], tev.time[sel], mu[sel], tau[sel])),
                       (ev.hit & ev.saturated, lambda sel: model.arrival.log_joint_at_or_above(ev.saturation_charge, tev.time[sel],
                                                                                              mu[sel], tau[sel]))):
        if mask.any():
            values = term(mask)
            for k in range(6):
                out[k][mask] = values[k]
    return out


def log_likelihood(model: Model, tev: TimedEvent, vertex, direction, e_vis, t0) -> float:
    _check_model(model, tev.event)
    vertex = numpy.asarray(vertex, float)
    if not (in_domain(model, vertex, e_vis) and t0_in_domain(model, t0)):
        return -math.inf
    direction = numpy.asarray(direction, float) / numpy.linalg.norm(direction)
    mu = model.scale * e_vis * light_model.shape(model, vertex, direction)
    if not in_domain(model, vertex, e_vis, mu + model.dark):
        return -math.inf
    delay, _, _ = arrival_delays(model, vertex)
    return float(channel_terms(model, tev, mu, t0 + delay)[0].sum())


class Objective:
    """ln L of the joint likelihood in p = (x, y, z, a, b, E_vis, t0) around d_ref, with its gradient and Hessian."""

    def __init__(self, model: Model, tev: TimedEvent, d_ref):
        self.charge = ChargeObjective(model, tev.event, d_ref)
        self.model = model
        self.tev = tev
        self.d_ref, self.e1, self.e2 = self.charge.d_ref, self.charge.e1, self.charge.e2
        self._value_cache = (None, None)
        self._full_cache = (None, None)

    def direction(self, a: float, b: float):
        return self.charge.direction(a, b)

    def _inside(self, p) -> bool:
        return in_domain(self.model, p[:3], p[5]) and t0_in_domain(self.model, p[6])

    def value(self, p) -> float:
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._value_cache[0] == key:
            return self._value_cache[1]
        out = -math.inf
        if self._inside(p):
            mu, _ = self.charge._mu_gradient(p[:6])
            if in_domain(self.model, p[:3], p[5], mu + self.model.dark):
                delay, _, _ = arrival_delays(self.model, p[:3])
                out = float(channel_terms(self.model, self.tev, mu, p[6] + delay)[0].sum())
        self._value_cache = (key, out)
        return out

    def derivatives(self, p):
        """(ln L, gradient (7,), Hessian (7, 7)) at p; outside the domain (-inf, zeros, -I)."""
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._full_cache[0] == key:
            return self._full_cache[1]
        outside = (-math.inf, numpy.zeros(7), -numpy.eye(7))
        if not self._inside(p):
            return outside
        mu, grad6 = self.charge._mu_gradient(p[:6])
        if not in_domain(self.model, p[:3], p[5], mu + self.model.dark):
            return outside
        delay, u, dist = arrival_delays(self.model, p[:3])
        speed = self.model.cfg.photon_speed_m_per_ns
        l0, l_m, l_t, l_mm, l_mt, l_tt = channel_terms(self.model, self.tev, mu, p[6] + delay)
        channels = mu.size
        grad_m = numpy.zeros((channels, 7))
        grad_m[:, :6] = grad6
        grad_t = numpy.zeros((channels, 7))
        grad_t[:, :3] = -u / speed
        grad_t[:, 6] = 1.0
        second_m = numpy.zeros((channels, 7, 7))
        second_m[:, :6, :6] = self.charge.second_derivatives(p[:6], grad6)
        second_t = numpy.zeros((channels, 7, 7))
        second_t[:, :3, :3] = (numpy.eye(3)[None, :, :] - u[:, :, None] * u[:, None, :]) / (dist * speed)[:, None, None]
        gradient = grad_m.T @ l_m + grad_t.T @ l_t
        cross = (grad_m * l_mt[:, None]).T @ grad_t
        hessian = (grad_m * l_mm[:, None]).T @ grad_m + cross + cross.T + (grad_t * l_tt[:, None]).T @ grad_t \
            + numpy.einsum("i,ijk->jk", l_m, second_m) + numpy.einsum("i,ijk->jk", l_t, second_t)
        hessian = 0.5 * (hessian + hessian.T)
        out = (float(l0.sum()), gradient, hessian)
        self._full_cache = (key, out)
        self._value_cache = (key, out[0])
        return out
