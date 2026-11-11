"""The arrival-time model of one channel and the joint charge-time terms of a hit channel (D3 stage 2; the reference, "Several
photons on one channel"; t07-t09-task-sheets.md, T09: "Single-time readout uses the first-arrival density, with the noise rate
included"; "charge and time from one sensor are modelled jointly or conditionally, not assumed independent"). Case
O-factorization of the D3 stage 2 report.

Arrivals at one channel form a Poisson process of intensity

    lambda(t) = mu_s phi((t - tau) / sigma) / sigma + rho [0 <= t < W],   rho = dark / W,

the signal (mean mu_s photons, Gaussian time spread sigma about tau = t0 + d / v, instant emission; not truncated) plus the dark
counts (mean `dark` per window, uniform on [0, W)), t04-values-v4.md section 4.3. Lambda_<(t) and Lambda_>(t) are its integrals
before and after t, with Lambda_< + Lambda_> = m = mu_s + dark. Every photon carries a charge Normal(mu_c, sigma_c^2), independent
of its time; the readout records the summed charge q, a hit when q >= T, and the time of the first photon. So the joint density
of a hit channel's (q, t) is exactly

    p(q, t) = lambda(t) e^{-Lambda_<(t)} sum_{k>=0} Pois(k; Lambda_>(t)) N(q; (k + 1) mu_c, (k + 1) sigma_c^2)

(no photon before t, one at t, k after), and that of a saturated channel (q >= C, censored) the same with N replaced by
P(Q_{k+1} >= C). This equals sum_{n>=1} Pois(n; m) N(q; n mu_c, n sigma_c^2) n f(t) (1 - F(t))^{n-1}, f = lambda / m: the charge
density times the first-arrival density given the charge, never their product as if independent. Summed over the charge (no
threshold) it is the reference's f_1(t) = m f e^{-m F} (times 1 - e^{-m}). Its time integral is the charge density at every q:
int lambda e^{-m} Lambda_>^k / k! dt = Pois(k + 1; m).

Each term is returned as (l, dl/dmu_s, dl/dtau, d2l/dmu_s2, d2l/dmu_s dtau, d2l/dtau2) per channel. With
A_j = sum_k Lambda_>^k / k! w_{k+1+j} (w the charge weight), G = -Lambda_> + ln A_0, G' = A_1/A_0 - 1, G'' = A_2/A_0 - (A_1/A_0)^2,
z = (t - tau)/sigma, phi_s = phi(z)/sigma, pi_s = mu_s phi_s / lambda (the signal's share of the intensity at t), r = phi_s / lambda:

    l        = ln lambda - Lambda_< + G
    l_mu     = r - Phi(z) + G' Q(z)            (each product of A_j / A_0 with Q or mu_s phi_s formed in log space)
    l_tau    = pi_s z / sigma + (A_1/A_0) mu_s phi_s
    l_mumu   = -r^2 + G'' Q(z)^2
    l_mutau  = r z (1 - pi_s) / sigma + (A_1/A_0) phi_s + G'' Q(z) mu_s phi_s
    l_tautau = pi_s (z^2 - 1)/sigma^2 - pi_s^2 z^2/sigma^2 + (A_1/A_0) mu_s phi_s z / sigma + G'' (mu_s phi_s)^2

The sums over k run over stage 1's charge window (charge_response._span about the charge centre and Lambda_>), from k = 0 for the
censored term (case O-window-k), in log space; ln Lambda_> is formed from log_ndtr, so a time long after the expected arrival
(Lambda_> below 1e-300) stays finite.
"""
from __future__ import annotations

import math

import numpy
from scipy import special

from .charge_response import HALF_LOG_TWO_PI, ChargeResponse


class ArrivalResponse:
    def __init__(self, charge: ChargeResponse, time_spread: float, dark_mean: float, window: float):
        if not (time_spread > 0 and dark_mean > 0 and window > 0):
            raise ValueError("time_spread, dark_mean and window must be positive")
        self.charge = charge
        self.time_spread = float(time_spread)
        self.dark_mean = float(dark_mean)
        self.window = float(window)
        self.rate = self.dark_mean / self.window

    # --- the two hit terms ---------------------------------------------------------------------------------------------

    def log_joint_density(self, q, t, mu_s, tau):
        """ln p(q, t) of a hit channel, per unit charge and per ns, and its derivatives in (mu_s, tau)."""
        q = numpy.asarray(q, float)
        mc, sc = self.charge.photon_charge_mean, self.charge.photon_charge_sigma

        def weight(n, owner):
            s = sc * numpy.sqrt(n)
            z = (q[owner] - n * mc) / s
            return -0.5 * z * z - numpy.log(s) - HALF_LOG_TWO_PI
        return self._terms(q / mc, t, mu_s, tau, weight, from_zero=False)

    def log_joint_at_or_above(self, level, t, mu_s, tau):
        """ln P(q >= level, t) (the censored term of a saturated channel; at level T, the hit's time density), and its
        derivatives in (mu_s, tau)."""
        t = numpy.asarray(t, float)
        level = numpy.broadcast_to(numpy.asarray(level, float), t.shape)
        if numpy.any(level <= 0):
            raise ValueError("level must be positive")
        mc, sc = self.charge.photon_charge_mean, self.charge.photon_charge_sigma

        def weight(n, owner):
            return special.log_ndtr((n * mc - level[owner]) / (sc * numpy.sqrt(n)))
        return self._terms(level / mc, t, mu_s, tau, weight, from_zero=True)

    # --- the intensity and the sums --------------------------------------------------------------------------------------

    def _terms(self, centre, t, mu_s, tau, weight, from_zero):
        t = numpy.asarray(t, float)
        mu_s = numpy.asarray(mu_s, float)
        tau = numpy.asarray(tau, float)
        if t.size == 0:
            return tuple(numpy.zeros(0) for _ in range(6))
        if numpy.any(~numpy.isfinite(mu_s)) or numpy.any(mu_s <= 0) or numpy.any(~numpy.isfinite(t)) \
                or numpy.any(~numpy.isfinite(tau)):
            raise ValueError("mu_s must be positive and finite, t and tau finite")
        sigma = self.time_spread
        z = (t - tau) / sigma
        ln_phi = -0.5 * z * z - math.log(sigma) - HALF_LOG_TWO_PI          # ln phi_s = ln (phi(z) / sigma)
        ln_mu = numpy.log(mu_s)
        ln_signal = ln_mu + ln_phi
        in_window = (t >= 0.0) & (t < self.window)
        ln_rate = numpy.where(in_window, math.log(self.rate), -numpy.inf)
        ln_lambda = numpy.logaddexp(ln_signal, ln_rate)
        clipped = numpy.clip(t, 0.0, self.window)
        cdf, sf = special.ndtr(z), special.ndtr(-z)
        before = mu_s * cdf + self.rate * clipped
        dark_after = self.rate * (self.window - clipped)
        with numpy.errstate(divide="ignore"):
            ln_after = numpy.logaddexp(ln_mu + special.log_ndtr(-z), numpy.log(dark_after))
        ln_a = self._k_sums(centre, ln_after, weight, from_zero)
        after = numpy.exp(ln_after)
        # A_1/A_0 and A_2/A_0 can overflow where Lambda_> is tiny (a time long after the expected arrival, with a charge that
        # asks for more photons); they only ever multiply Q(z) or mu_s phi_s, which are then as small, so every product is formed
        # in log space: e^{a1 + ln Q} etc. stay finite (stage 2, found on hand-made events at the t0 edge).
        a1, a2 = ln_a[1] - ln_a[0], ln_a[2] - ln_a[0]
        ln_sf = special.log_ndtr(-z)
        r1_sf, r1_signal, r1_phi = numpy.exp(a1 + ln_sf), numpy.exp(a1 + ln_signal), numpy.exp(a1 + ln_phi)
        g2_sf2 = numpy.exp(a2 + 2.0 * ln_sf) - r1_sf * r1_sf                 # G'' Q^2
        g2_sf_signal = numpy.exp(a2 + ln_sf + ln_signal) - r1_sf * r1_signal  # G'' Q mu_s phi_s
        g2_signal2 = numpy.exp(a2 + 2.0 * ln_signal) - r1_signal * r1_signal  # G'' (mu_s phi_s)^2
        pi_s = numpy.exp(ln_signal - ln_lambda)
        r = numpy.exp(ln_phi - ln_lambda)
        l0 = ln_lambda - before - after + ln_a[0]
        l_mu = r - cdf + (r1_sf - sf)
        l_tau = pi_s * z / sigma + r1_signal
        l_mumu = -r * r + g2_sf2
        l_mutau = r * z * (1.0 - pi_s) / sigma + r1_phi + g2_sf_signal
        l_tautau = pi_s * (z * z - 1.0) / sigma ** 2 - (pi_s * z / sigma) ** 2 + r1_signal * z / sigma + g2_signal2
        return l0, l_mu, l_tau, l_mumu, l_mutau, l_tautau

    @staticmethod
    def _k_sums(centre, ln_lam, weight, from_zero):
        """ln A_j = ln sum_{k>=0} Lambda^k / k! w_{k+1+j}, j = 0, 1, 2, per channel, over stage 1's charge window in n = k + 1
        (widened by the two shifts), from k = 0 for the censored term."""
        lam = numpy.exp(ln_lam)
        lo, hi = ChargeResponse._span(numpy.asarray(centre, float), lam)
        lo = numpy.zeros_like(lo) if from_zero else numpy.maximum(0, lo - 3)
        hi = hi.astype(numpy.int64)
        counts = hi - lo + 1
        starts = numpy.concatenate(([0], numpy.cumsum(counts)[:-1]))
        owner = numpy.repeat(numpy.arange(lam.size), counts)
        k = (lo[owner] + numpy.arange(owner.size) - starts[owner]).astype(float)
        base = numpy.where(k == 0.0, 0.0, k * ln_lam[owner]) - special.gammaln(k + 1.0)
        out = []
        for j in range(3):
            terms = base + weight(k + 1.0 + j, owner)
            top = numpy.maximum.reduceat(terms, starts)
            out.append(top + numpy.log(numpy.add.reduceat(numpy.exp(terms - top[owner]), starts)))
        return out
