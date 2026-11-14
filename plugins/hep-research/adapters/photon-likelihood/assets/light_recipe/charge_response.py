"""The charge model and the one threshold model, shared by the hit and no-hit terms (t07-t09-task-sheets.md, T09, likelihood;
the reference's charge term and unhit channels). Cases O-charge, O-dark, O-threshold and O-saturation of the D3 stage 1 report.

A channel's photon count is n ~ Poisson(m), m the mean count of the window (signal plus dark, light_model.expected). Each photon
gives a charge Normal(photon_charge_mean, photon_charge_sigma) (t04-values-v4.md section 4.3), so the summed charge given n is
Normal(n photon_charge_mean, photon_charge_sigma^2 n), and n = 0 is a point mass at charge 0. One sharp threshold T on the summed charge decides a
hit (q >= T). With Pois(n; m) the Poisson probability:

    P(no hit | m)        = e^-m + sum_{n>=1} Pois(n; m) Phi((T - n photon_charge_mean) / (photon_charge_sigma sqrt n))
    f(q | m), q >= T     = sum_{n>=1} Pois(n; m) phi((q - n photon_charge_mean) / (photon_charge_sigma sqrt n)) / (photon_charge_sigma sqrt n)   (per unit charge)
    P(q >= L | m)        = sum_{n>=1} Pois(n; m) Phi((n photon_charge_mean - L) / (photon_charge_sigma sqrt n))                      (L > 0)

P(hit | m) is P(q >= T | m), so P(hit) + P(no hit) = sum_n Pois(n; m) = 1 per channel. A saturated channel (charge at or above
the readout's saturation value C) is censored: it contributes P(q >= C | m), never a density.

Each term is a sum over n of Pois(n; m) w_n with weights that do not depend on m, evaluated in log space over a window of n
outside which the dropped terms are below e^-40 of the largest kept term (each term is log-concave in n, so the tail beyond the
window is bounded geometrically); the others span [min(q, m) - D, max(q, m) + D] with D = 12 sqrt(max(q, m, 1)) + 30, clipped
at n = 1; their cost is bounded by the likelihood's yield domain (likelihood.YIELD_DOMAIN).

The no-hit window (fix round 1, F3) is centred on the summand's peak, lambda = m exp(-mu_c^2 / (2 sigma_c^2)) (mu_c, sigma_c the
single-photon charge mean and width), and spans [lambda - D0, lambda + D0], D0 = 12 sqrt(max(lambda, 1)) + 60, clipped at 0; its
width does not grow with m beyond sqrt(lambda). Tail bound: for n >= 1, n mu_c >= T, so Phi((T - n mu_c)/(sigma_c sqrt n)) <=
1/2 exp(-x^2/2) with x^2/2 >= n mu_c^2 / (2 sigma_c^2) - T mu_c / sigma_c^2, hence each dropped term is at most
max(1, 1/2 exp(T mu_c / sigma_c^2)) e^(-m + lambda) Pois(n; lambda) (the n = 0 term is e^-m = e^(-m + lambda) Pois(0; lambda)), and
the dropped mass is at most 8.04 e^(-m + lambda) P(Pois(lambda) outside the window) at section 4.3's constants. The test module
evaluates this bound against the kept sum for m from 1e-8 to the yield domain's edge: below 1e-17 of it everywhere, far below the
sum tolerance. Each term
returns (l, dl/dm, d2l/dm2): with rho_n the normalised summands, dl/dm = <n>/m - 1 and d2l/dm2 = (Var(n) - <n>)/m^2.
"""
from __future__ import annotations

import math

import numpy
from scipy import special

SPAN_SIGMAS = 12.0
SPAN_EXTRA = 30.0
NO_HIT_SIGMAS = 12.0
NO_HIT_EXTRA = 60.0
HALF_LOG_TWO_PI = 0.5 * math.log(2.0 * math.pi)


class ChargeResponse:
    def __init__(self, threshold: float, photon_charge_mean: float, photon_charge_sigma: float):
        if not (threshold > 0 and photon_charge_mean > 0 and photon_charge_sigma > 0):
            raise ValueError("threshold, photon_charge_mean and photon_charge_sigma must be positive")
        self.threshold = float(threshold)
        self.photon_charge_mean = float(photon_charge_mean)
        self.photon_charge_sigma = float(photon_charge_sigma)

    # --- the three terms -----------------------------------------------------------------------------------------------

    def log_no_hit(self, m):
        """ln P(no hit | m) and its first two derivatives in m, per channel."""
        m = numpy.asarray(m, float)
        lo, hi = self.no_hit_window(m)
        threshold = self.threshold

        def weight(n, _owner):
            out = numpy.zeros(n.shape)
            pos = n > 0
            out[pos] = special.log_ndtr((threshold - n[pos] * self.photon_charge_mean) / (self.photon_charge_sigma * numpy.sqrt(n[pos])))
            return out
        return self._sum(m, lo, hi, weight)

    def no_hit_window(self, m):
        """[lo, hi] of the no-hit sum per channel, centred on the summand's peak (module docstring, tail bound)."""
        lam = numpy.asarray(m, float) * math.exp(-self.photon_charge_mean ** 2 / (2.0 * self.photon_charge_sigma ** 2))
        reach = NO_HIT_SIGMAS * numpy.sqrt(numpy.maximum(lam, 1.0)) + NO_HIT_EXTRA
        return numpy.maximum(0, numpy.floor(lam - reach)).astype(numpy.int64), numpy.ceil(lam + reach).astype(numpy.int64)

    def log_at_or_above(self, level, m):
        """ln P(q >= level | m) for a level > 0 (the threshold: P(hit); the saturation value: the censored term)."""
        m = numpy.asarray(m, float)
        level = numpy.broadcast_to(numpy.asarray(level, float), m.shape)
        if numpy.any(level <= 0):
            raise ValueError("level must be positive")
        _, hi = self._span(level / self.photon_charge_mean, m)
        lo = numpy.ones(m.shape, numpy.int64)

        def weight(n, owner):
            return special.log_ndtr((n * self.photon_charge_mean - level[owner]) / (self.photon_charge_sigma * numpy.sqrt(n)))
        return self._sum(m, lo, hi, weight)

    def log_hit_density(self, q, m):
        """ln f(q | m), the density of the summed charge q per unit charge (for a hit, q >= threshold)."""
        m = numpy.asarray(m, float)
        q = numpy.asarray(q, float)
        lo, hi = self._span(q / self.photon_charge_mean, m)

        def weight(n, owner):
            s = self.photon_charge_sigma * numpy.sqrt(n)
            z = (q[owner] - n * self.photon_charge_mean) / s
            return -0.5 * z * z - numpy.log(s) - HALF_LOG_TWO_PI
        return self._sum(m, lo, hi, weight)

    def probability_sums(self, m):
        """(P(hit | m), P(no hit | m)) per channel, from two code paths: the upper tails at the threshold (the path the censored
        term uses) and the likelihood's own no-hit term. Their sum is the sheet's per-channel check."""
        return numpy.exp(self.log_at_or_above(self.threshold, m)[0]), numpy.exp(self.log_no_hit(m)[0])

    # --- the sum over n ------------------------------------------------------------------------------------------------

    @staticmethod
    def _span(centre, m):
        low = numpy.minimum(centre, m)
        high = numpy.maximum(centre, m)
        reach = SPAN_SIGMAS * numpy.sqrt(numpy.maximum(high, 1.0)) + SPAN_EXTRA
        lo = numpy.maximum(1, numpy.floor(low - reach)).astype(numpy.int64)
        hi = numpy.ceil(high + reach).astype(numpy.int64)
        return lo, hi

    @staticmethod
    def _sum(m, lo, hi, weight):
        """sum_{n=lo}^{hi} Pois(n; m) w_n per channel, in logs: (l, dl/dm, d2l/dm2)."""
        if m.size == 0:
            empty = numpy.zeros(0)
            return empty, empty.copy(), empty.copy()
        if numpy.any(~numpy.isfinite(m)) or numpy.any(m <= 0):
            raise ValueError("the mean count m must be positive and finite")
        counts = hi - lo + 1
        starts = numpy.concatenate(([0], numpy.cumsum(counts)[:-1]))
        owner = numpy.repeat(numpy.arange(m.size), counts)
        n = (lo[owner] + numpy.arange(owner.size) - starts[owner]).astype(float)
        mo = m[owner]
        terms = n * numpy.log(mo) - mo - special.gammaln(n + 1.0) + weight(n, owner)
        top = numpy.maximum.reduceat(terms, starts)
        e = numpy.exp(terms - top[owner])
        s0 = numpy.add.reduceat(e, starts)
        mean = numpy.add.reduceat(e * n, starts) / s0
        var = numpy.add.reduceat(e * (n - mean[owner]) ** 2, starts) / s0
        return top + numpy.log(s0), mean / m - 1.0, (var - mean) / m ** 2
