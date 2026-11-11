"""adapters/photon-likelihood, D3 stage 2 of T09 (t07-t09-task-sheets.md, T09): the time term (the first-arrival density with
the noise rate included), the joint charge-time likelihood with the t0 parameter, v4 9.3's two deterministic checks at the fixed
points (driver and independent evaluation), and the stage 1 re-review nits N4 and N5. Hand-made events only: no fixture event and
no Monte Carlo of the frozen generator; noisy events are drawn with this module's own coding of t04-values-v4.md section 4.3
and its own random numbers.

Expectations come from a second coding of section 4.3 and of the photon-likelihood reference in plain Python (math, loops), in
the order-statistic form sum_n Pois(n; m) w_n(q) n f(t) (1 - F(t))^(n-1), never from the recipe's modules. Stage 1's module
tests/adapters/test_photon_likelihood.py is unchanged; its helpers are reused here by import.
Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood_time -v
"""
from __future__ import annotations

import ast
import copy
import io
import json
import math
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

import numpy
from scipy import integrate

from tests.adapters import test_photon_likelihood as stage1

ROOT = stage1.ROOT
ASSETS = stage1.ASSETS
from light_recipe import arrival_response, configuration, fit, joint, likelihood, product, readout  # noqa: E402
import t09_fixed_points  # noqa: E402
import t09_independent_likelihood as independent  # noqa: E402
import t09_readings  # noqa: E402

R_S, SENSORS, SPEED, DARK, WINDOW, SIGMA_T = stage1.R_S, stage1.SENSORS, stage1.SPEED, stage1.DARK, stage1.WINDOW, stage1.SIGMA_T
THRESHOLD, CLIP = stage1.THRESHOLD, stage1.CLIP
CFG, MODEL = stage1.CFG, stage1.MODEL
POSITIONS, NORMALS, unit = stage1.POSITIONS, stage1.NORMALS, stage1.unit
log_pois, lse, log_upper = stage1.log_pois, stage1.lse, stage1.log_upper
RATE = DARK / WINDOW
NEG_INF = -math.inf


# --- a second coding of the joint term, order-statistic form, from the text ---------------------------------------------

def logadd(a, b):
    if a == NEG_INF:
        return b
    if b == NEG_INF:
        return a
    top = max(a, b)
    return top + math.log(math.exp(a - top) + math.exp(b - top))


def text_arrival(t, mu_s, tau):
    """(ln f(t), ln (1 - F(t)), m): the normalised arrival mixture of one channel and its survival, signal mu_s Gaussian
    SIGMA_T about tau, dark DARK uniform on [0, WINDOW)."""
    m = mu_s + DARK
    z = (t - tau) / SIGMA_T
    signal = math.log(mu_s) - 0.5 * z * z - math.log(SIGMA_T * math.sqrt(2 * math.pi)) if mu_s > 0 else NEG_INF
    ln_rate = logadd(signal, math.log(RATE) if 0.0 <= t < WINDOW else NEG_INF)
    after_signal = math.log(mu_s) + log_upper(z) if mu_s > 0 else NEG_INF
    dark_after = DARK * (1.0 - min(max(t, 0.0), WINDOW) / WINDOW)
    ln_after = logadd(after_signal, math.log(dark_after) if dark_after > 0 else NEG_INF)
    return ln_rate - math.log(m), ln_after - math.log(m), m


def charge_weight(n, q=None, level=None):
    s = stage1.PHOTON_CHARGE_SIGMA * math.sqrt(n)
    if level is not None:
        return log_upper((level - n) / s)
    return -0.5 * ((q - n) / s) ** 2 - math.log(s * math.sqrt(2 * math.pi))


def text_ln_joint(t, mu_s, tau, q=None, level=None):
    """ln p(q, t, hit) (q given) or ln P(charge >= level, t) (level given), by the order statistic summed over n."""
    ln_f, ln_s, m = text_arrival(t, mu_s, tau)
    top = max(m, q if q is not None else level)
    terms = []
    for n in range(1, int(top + 40 * math.sqrt(max(top, 1.0)) + 100)):
        terms.append(log_pois(n, m) + charge_weight(n, q, level) + math.log(n) + ln_f + (n - 1) * ln_s)
    return lse(terms)


def text_median_first_arrival(mu_s, tau):
    """Median of the first arrival given at least one photon: Lambda_<(t) = -ln(1 - (1 - e^-m)/2), by bisection."""
    m = mu_s + DARK
    target = -math.log(1.0 - 0.5 * (1.0 - math.exp(-m)))
    lo, hi = tau - 60.0, tau + 400.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        before = mu_s * 0.5 * math.erfc(-(mid - tau) / (SIGMA_T * math.sqrt(2))) + RATE * min(max(mid, 0.0), WINDOW)
        lo, hi = (mid, hi) if before < target else (lo, mid)
    return 0.5 * (lo + hi)


def delays(vertex, positions=POSITIONS):
    return [math.dist(p, vertex) / SPEED for p in positions]


def noise_free_timed_event(vertex, direction, n_exp, t0, dead=()):
    """Stage 1's noise-free charges (m_i, hit at m_i >= T) with each hit's time at its median first arrival."""
    state, charge, e_vis = stage1.noise_free_event(vertex, direction, n_exp, dead=dead)
    m = stage1.text_mean(POSITIONS, NORMALS, vertex, direction, e_vis)
    d = delays(vertex)
    times = numpy.full(SENSORS, numpy.nan)
    for i in range(SENSORS):
        if state[i] == readout.LIVE_HIT:
            times[i] = text_median_first_arrival(m[i] - DARK, t0 + d[i])
    return state, charge, times, e_vis


def timed(state, charge, times, saturated=None, saturation_charge=None):
    ev = stage1.event_from(state, charge, saturated, saturation_charge)
    return joint.TimedEvent(ev, numpy.asarray(times, float))


def noisy_timed_event(rng, vertex, direction, n_exp, t0, dead=(), clip=None):
    """A noisy event of this module's coding of section 4.3 with its own random numbers: Poisson signal and dark counts,
    per-photon times (signal t0 + d/v + 1.5 N(0, 1), dark uniform on the window), first arrival, summed Gaussian(1, 0.3)
    charges, hit at 0.25, clip at C, dead channels without value."""
    shape = numpy.array(stage1.text_shape(POSITIONS, NORMALS, vertex, direction))
    mu = n_exp * shape / shape.sum()
    d = delays(vertex)
    state = numpy.zeros(SENSORS, numpy.int8)
    charge = numpy.zeros(SENSORS)
    times = numpy.full(SENSORS, numpy.nan)
    saturated = numpy.zeros(SENSORS, bool)
    for i in range(SENSORS):
        ns, nd = rng.poisson(mu[i]), rng.poisson(DARK)
        arrivals = list(t0 + d[i] + SIGMA_T * rng.standard_normal(ns)) + list(rng.uniform(0.0, WINDOW, nd))
        q = float(rng.normal(1.0, 0.3, ns + nd).sum()) if ns + nd else 0.0
        if q >= THRESHOLD:
            state[i], charge[i], times[i] = readout.LIVE_HIT, q, min(arrivals)
            if clip is not None and q >= clip:
                saturated[i], charge[i] = True, clip
    for ch in dead:
        state[ch], charge[ch], times[ch], saturated[ch] = readout.DEAD, numpy.nan, numpy.nan, False
    return timed(state, charge, times, saturated, clip)


def text_joint_ln_l(positions, normals, tev, vertex, direction, e_vis, t0):
    """ln L of the joint likelihood by the second coding: hit terms joint, saturated censored joint, unhit no-hit, dead out."""
    m = stage1.text_mean(positions, normals, vertex, direction, e_vis)
    d = delays(vertex, positions)
    ev = tev.event
    total = 0.0
    for i in range(len(positions)):
        state = int(ev.state[i])
        if state == readout.LIVE_UNHIT:
            total += stage1.text_ln_no_hit(m[i])
        elif state == readout.LIVE_HIT:
            if ev.saturated[i]:
                total += text_ln_joint(float(tev.time[i]), m[i] - DARK, t0 + d[i], level=ev.saturation_charge)
            else:
                total += text_ln_joint(float(tev.time[i]), m[i] - DARK, t0 + d[i], q=float(ev.charge[i]))
    return total


ARRIVAL = MODEL.arrival


# --- the time term: normalisation, limits, hand computation, derivatives, windows -----------------------------------------

class TimeDensity(unittest.TestCase):
    CASES = (("few photons", 0.05, 1.1, 30.0), ("several", 5.0, 4.7, 40.0), ("many", 300.0, 310.0, 60.0),
             ("near the window start", 2.0, 2.2, 3.0), ("near the window end", 2.0, 1.8, 197.0))

    def conditional_integral(self, q, mu_s, tau, level=None):
        """int p(q, t) dt over the real line, piecewise around the signal peak and the window edges."""
        def p(t):
            if level is None:
                return math.exp(ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]),
                                                          numpy.array([tau]))[0][0])
            return math.exp(ARRIVAL.log_joint_at_or_above(level, numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0])
        cuts = sorted({-400.0, tau - 60.0, tau - 10.0, tau - 3.0, tau, tau + 3.0, tau + 10.0, tau + 60.0, 0.0, WINDOW, 600.0})
        total = 0.0
        for a, b in zip(cuts[:-1], cuts[1:]):
            total += integrate.quad(p, a, b, limit=400, epsabs=0.0, epsrel=1e-12)[0]
        return total

    def test_integrates_to_the_charge_density_at_each_charge(self):
        for name, mu_s, q, tau in self.CASES:
            with self.subTest(case=name):
                m = mu_s + DARK
                ratio = self.conditional_integral(q, mu_s, tau) / math.exp(stage1.text_ln_density(q, m))
                self.assertAlmostEqual(ratio, 1.0, delta=1e-8)

    def test_censored_and_threshold_terms_integrate_to_their_probabilities(self):
        for name, mu_s, _, tau in self.CASES:
            with self.subTest(case=name):
                m = mu_s + DARK
                for level, want in ((CLIP, stage1.text_ln_at_or_above(CLIP, m)), (THRESHOLD, stage1.text_ln_at_or_above(THRESHOLD, m))):
                    got = self.conditional_integral(None, mu_s, tau, level=level)
                    self.assertAlmostEqual(got / math.exp(want), 1.0, delta=1e-8)

    def test_no_signal_limit_is_the_dark_order_statistic(self):
        mu_s, tau, q = 1e-15, 100.0, 1.0
        density_q = math.exp(stage1.text_ln_density(q, mu_s + DARK))
        for t in (1.0, 50.0, 150.0, 199.0):
            with self.subTest(t=t):
                got = math.exp(ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]),
                                                         numpy.array([tau]))[0][0]) / density_q
                hand = math.exp(text_ln_joint(t, mu_s, tau, q=q)) / density_q
                self.assertAlmostEqual(got / hand, 1.0, delta=1e-9)
                self.assertLess(abs(WINDOW * got - 1.0), 3e-3)
        for t in (-5.0, 250.0):
            got = ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0]
            self.assertLess(got - math.log(density_q), math.log(1e-100 / WINDOW))

    def test_many_photon_limit_is_the_references_first_arrival(self):
        """P(q >= T, t) = m f e^{-m F} = lambda e^{-Lambda_<} at mu_s 1000 (the reference's f_1 times 1 - e^-m), and it peaks
        well before tau (the earliest of about 1,000 arrivals)."""
        mu_s, tau = 1000.0, 50.0
        grid = numpy.linspace(tau - 9.0, tau + 3.0, 121)
        got = ARRIVAL.log_joint_at_or_above(THRESHOLD, grid, numpy.full(grid.size, mu_s), numpy.full(grid.size, tau))[0]
        for t, value in zip(grid, got):
            z = (t - tau) / SIGMA_T
            rate = mu_s * math.exp(-0.5 * z * z) / (SIGMA_T * math.sqrt(2 * math.pi)) + RATE
            before = mu_s * 0.5 * math.erfc(-z / math.sqrt(2)) + RATE * t
            self.assertAlmostEqual(value, math.log(rate) - before, delta=1e-12 * max(1.0, abs(value)))
        fine = numpy.linspace(tau - 15.0, tau + 5.0, 4001)
        dens = numpy.exp(ARRIVAL.log_joint_at_or_above(THRESHOLD, fine, numpy.full(fine.size, mu_s), numpy.full(fine.size, tau))[0])
        mean = float((fine * dens).sum() / dens.sum())
        self.assertTrue(tau - 4 * SIGMA_T < mean < tau - 2.5 * SIGMA_T, mean)

    def test_joint_term_against_the_order_statistic_by_hand(self):
        for mu_s, q, tau, t in ((0.05, 1.1, 30.0, 31.0), (5.0, 4.7, 40.0, 38.5), (300.0, 310.0, 60.0, 56.0), (2.0, 2.2, 3.0, 150.0),
                                (40.0, 3.0, 20.0, 80.0), (0.3, 7.0, 25.0, -2.0), (800.0, 1100.0, 70.0, 66.0)):
            with self.subTest(mu_s=mu_s, q=q, t=t):
                got = ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0]
                self.assertAlmostEqual(got, text_ln_joint(t, mu_s, tau, q=q), delta=1e-10 * max(1.0, abs(got)))
                got = ARRIVAL.log_joint_at_or_above(CLIP, numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0]
                self.assertAlmostEqual(got, text_ln_joint(t, mu_s, tau, level=CLIP), delta=1e-10 * max(1.0, abs(got)))

    def test_charge_and_time_are_not_independent(self):
        """A bright channel: the joint term is not ln f(q) + ln f_1(t), the product an independence assumption would give."""
        mu_s, q, tau, t = 50.0, 20.0, 40.0, 38.0
        m = mu_s + DARK
        got = ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0]
        ln_f, ln_s, _ = text_arrival(t, mu_s, tau)
        f_1 = math.log(m) + ln_f - m * (1.0 - math.exp(ln_s)) - math.log(1.0 - math.exp(-m))
        self.assertGreater(abs(got - (stage1.text_ln_density(q, m) + f_1)), 1e-3)

    def test_sum_windows_against_a_brute_force_sum(self):
        """Lambda_> from about 1e-300 (late times after the window) to 1e3, q from 0.25 to 1,100."""
        for mu_s, q, tau, t in ((1000.0, 1100.0, 20.0, 10.0), (1000.0, 0.25, 20.0, 17.0), (1e-3, 0.25, 20.0, 5.0),
                                (200.0, 150.0, 30.0, 30.0 + 37.0 * SIGMA_T + 200.0), (5.0, 60.0, 30.0, 30.0 + 30.0 * SIGMA_T)):
            with self.subTest(mu_s=mu_s, q=q, t=t):
                got = ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))[0][0]
                self.assertTrue(math.isfinite(got))
                self.assertAlmostEqual(got, text_ln_joint(t, mu_s, tau, q=q), delta=1e-10 * max(1.0, abs(got)))

    def test_derivatives_in_mu_and_tau(self):
        for kind in ("density", "censored"):
            for mu_s, q, tau, t in ((0.05, 1.1, 30.0, 31.0), (5.0, 4.7, 40.0, 38.5), (300.0, 310.0, 60.0, 56.0), (2.0, 2.2, 30.0, 150.0),
                                    (40.0, 6.0, 20.0, 24.0)):
                with self.subTest(kind=kind, mu_s=mu_s, t=t):
                    def term(mu, ta):
                        args = (numpy.array([t]), numpy.array([mu]), numpy.array([ta]))
                        out = ARRIVAL.log_joint_density(numpy.array([q]), *args) if kind == "density" else \
                            ARRIVAL.log_joint_at_or_above(CLIP, *args)
                        return [float(v[0]) for v in out]
                    l0, l_m, l_t, l_mm, l_mt, l_tt = term(mu_s, tau)
                    hm, ht = 1e-5 * mu_s, 1e-5
                    up_m, dn_m, up_t, dn_t = term(mu_s + hm, tau), term(mu_s - hm, tau), term(mu_s, tau + ht), term(mu_s, tau - ht)
                    for got, fd in ((l_m, (up_m[0] - dn_m[0]) / (2 * hm)), (l_t, (up_t[0] - dn_t[0]) / (2 * ht)),
                                    (l_mm, (up_m[1] - dn_m[1]) / (2 * hm)), (l_mt, (up_t[1] - dn_t[1]) / (2 * ht)),
                                    (l_mt, (up_m[2] - dn_m[2]) / (2 * hm)), (l_tt, (up_t[2] - dn_t[2]) / (2 * ht))):
                        self.assertAlmostEqual(got, fd, delta=1e-6 * max(1.0, abs(fd)))


    def test_derivatives_stay_finite_long_after_the_expected_arrival(self):
        """Found on hand-made events at the t0 edge: a bright charge at a time 50 to 100 sigma after tau makes Lambda_> about
        e^-2000 and A_1/A_0 about e^900; the products with Q(z) must stay finite and equal finite differences."""
        for mu_s, q, dz in ((18.0, 18.2, 65.0), (12.5, 14.0, 32.0), (300.0, 290.0, 40.0), (5.0, 9.0, 100.0)):
            with self.subTest(mu_s=mu_s, dz=dz):
                tau, t = 400.0, 400.0 + dz * SIGMA_T
                def term(mu, ta):
                    return [float(v[0]) for v in ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu]),
                                                                           numpy.array([ta]))]
                values = term(mu_s, tau)
                self.assertTrue(all(math.isfinite(v) for v in values), values)
                self.assertAlmostEqual(values[0], text_ln_joint(t, mu_s, tau, q=q), delta=1e-10 * abs(values[0]))
                # Steps 1e-3 ns and 1e-4 mu_s: a 1e-6 ns step leaves about 1e-4 of rounding in the difference of l_tau (about 640
                # here), larger than the truncation error of 1e-3. In this regime l_tautau carries about 4e-7 relative rounding of
                # its own: G'' (mu_s phi_s)^2 is a difference of two terms near 4e5 (probe 10 against a 60-digit evaluation).
                hm, ht = 1e-4 * mu_s, 1e-3
                fd_t = (term(mu_s, tau + ht)[0] - term(mu_s, tau - ht)[0]) / (2 * ht)
                fd_m = (term(mu_s + hm, tau)[0] - term(mu_s - hm, tau)[0]) / (2 * hm)
                fd_tt = (term(mu_s, tau + ht)[2] - term(mu_s, tau - ht)[2]) / (2 * ht)
                self.assertAlmostEqual(values[2], fd_t, delta=1e-6 * max(1.0, abs(fd_t)))
                self.assertAlmostEqual(values[1], fd_m, delta=1e-6 * max(1.0, abs(fd_m)))
                self.assertAlmostEqual(values[5], fd_tt, delta=1e-6 * max(1.0, abs(fd_tt)))

# --- the joint likelihood on the six-sensor sphere -----------------------------------------------------------------------

class JointTinySphere(unittest.TestCase):
    """Stage 1's six sensors: +x saturated (C = 5) with a time, -x unhit, +y hit 2.3, -y dead, +z hit 0.4, -z unhit."""
    VERTEX, DIRECTION, E_VIS, T0 = (1.0, 0.5, -0.3), unit((1.0, 1.0, 0.2)), 2.0, 20.0

    @classmethod
    def setUpClass(cls):
        tiny = stage1.TinySphere
        tiny.setUpClass()
        cls.tiny = tiny
        cls.model = tiny.model
        cls.times = [31.0, numpy.nan, 37.5, numpy.nan, 120.0, numpy.nan]

    def tev(self):
        return timed(self.tiny.state, self.tiny.charge, self.times, self.tiny.saturated, CLIP)

    def test_value_against_a_hand_computation(self):
        got = joint.log_likelihood(self.model, self.tev(), numpy.array(self.VERTEX), numpy.array(self.DIRECTION), self.E_VIS, self.T0)
        hand = text_joint_ln_l(self.tiny.positions, self.tiny.normals, self.tev(), self.VERTEX, self.DIRECTION, self.E_VIS, self.T0)
        self.assertAlmostEqual(got, hand, delta=1e-10)

    def test_dead_stays_out_and_unhit_keeps_its_no_hit_term(self):
        ev = self.tev()
        base = joint.log_likelihood(self.model, ev, numpy.array(self.VERTEX), numpy.array(self.DIRECTION), self.E_VIS, self.T0)
        charge_only = likelihood.log_likelihood(self.model, ev.event, numpy.array(self.VERTEX), numpy.array(self.DIRECTION), self.E_VIS)
        m = stage1.text_mean(self.tiny.positions, self.tiny.normals, self.VERTEX, self.DIRECTION, self.E_VIS)
        unhit = stage1.text_ln_no_hit(m[1]) + stage1.text_ln_no_hit(m[5])
        charge_hits = charge_only - unhit
        joint_hits = base - unhit
        self.assertNotAlmostEqual(charge_hits, joint_hits, delta=1e-3)       # the hit terms carry time
        # moving an unhit channel's (absent) time cannot matter; a dead channel's neither
        self.assertEqual(joint.channel_terms(self.model, ev, numpy.array(m) - DARK, numpy.zeros(6) + 20.0)[0][3], 0.0)

    def test_gradient_and_hessian_against_finite_differences(self):
        objective = joint.Objective(self.model, self.tev(), numpy.array(self.DIRECTION))
        p0 = numpy.array([*self.VERTEX, 0.03, -0.02, self.E_VIS, self.T0])
        value, gradient, hessian = objective.derivatives(p0)
        self.assertAlmostEqual(value, objective.value(p0), delta=1e-12 * abs(value))
        steps = numpy.array([1e-4, 1e-4, 1e-4, 1e-5, 1e-5, 1e-5 * self.E_VIS, 1e-4])
        for k in range(7):
            e = numpy.zeros(7)
            e[k] = steps[k]
            fd = (objective.value(p0 + e) - objective.value(p0 - e)) / (2 * steps[k])
            self.assertAlmostEqual(gradient[k], fd, delta=1e-5 * max(1.0, abs(fd)))
            fd_row = (objective.derivatives(p0 + e)[1] - objective.derivatives(p0 - e)[1]) / (2 * steps[k])
            self.assertLess(numpy.abs(hessian[k] - fd_row).max(), 1e-5 * max(1.0, numpy.abs(fd_row).max()))
        self.assertLess(numpy.abs(hessian - hessian.T).max(), 1e-12 * numpy.abs(hessian).max())

    def test_domain_in_t0_is_total(self):
        objective = joint.Objective(self.model, self.tev(), numpy.array(self.DIRECTION))
        for t0 in (-WINDOW, 2 * WINDOW, 1e9, math.nan):
            with self.subTest(t0=t0):
                value, gradient, hessian = objective.derivatives(numpy.array([*self.VERTEX, 0.0, 0.0, self.E_VIS, t0]))
                self.assertEqual(value, -math.inf)
                numpy.testing.assert_array_equal(gradient, numpy.zeros(7))
                numpy.testing.assert_array_equal(hessian, -numpy.eye(7))
        self.assertTrue(math.isfinite(objective.value(numpy.array([*self.VERTEX, 0.0, 0.0, self.E_VIS, 2 * WINDOW - 1e-6]))))

    def test_timed_event_refuses_a_hit_without_a_time(self):
        with self.assertRaises(likelihood.EventError):
            timed(self.tiny.state, self.tiny.charge, [numpy.nan] * 6, self.tiny.saturated, CLIP)
        with self.assertRaises(likelihood.EventError):
            timed(self.tiny.state, self.tiny.charge, [31.0, 5.0, 37.5, numpy.nan, 120.0, numpy.nan], self.tiny.saturated, CLIP)


# --- seed and fit ----------------------------------------------------------------------------------------------------------

class JointSeedAndFit(unittest.TestCase):
    TRUTH, DIRECTION, T0 = (1.2, -0.8, 0.6), unit((0.3, -0.5, 0.8)), 20.0

    def test_t0_seed_is_the_median_rule(self):
        state, charge, times, _ = noise_free_timed_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0, 17.0)
        tev = timed(state, charge, times)
        start, prefit, origin = fit.joint_seed(MODEL, tev)
        base = prefit.vertex if prefit.vertex is not None else fit.seed(MODEL, tev.event).vertex
        hits = [i for i in range(SENSORS) if state[i] == readout.LIVE_HIT]
        want = float(numpy.median([times[i] - math.dist(POSITIONS[i], tuple(base)) / SPEED for i in hits]))
        self.assertAlmostEqual(start.t0, want, delta=1e-12)
        self.assertEqual(origin, "charge-only fit" if prefit.status == "converged" else origin)
        numpy.testing.assert_array_equal(start.vertex, base)

    def test_no_hit_channel_gives_no_seed(self):
        tev = timed(numpy.zeros(SENSORS, numpy.int8), numpy.zeros(SENSORS), numpy.full(SENSORS, numpy.nan))
        start, prefit, origin = fit.joint_seed(MODEL, tev)
        self.assertIsNone(start)
        res = fit.fit_joint_event(MODEL, tev)
        self.assertEqual((res.status, res.failure, res.t0), ("failed", "no-hit-channel", None))

    def test_t0_recovered_on_a_noise_free_event(self):
        state, charge, times, e_vis = noise_free_timed_event(self.TRUTH, self.DIRECTION, 20000.0, self.T0)
        res = fit.fit_joint_event(MODEL, timed(state, charge, times))
        self.assertEqual(res.status, "converged", res.failure)
        self.assertLess(abs(res.t0 - self.T0), 0.1)
        self.assertLess(numpy.linalg.norm(res.vertex - numpy.array(self.TRUTH)), 0.05)
        self.assertLess(math.acos(min(1.0, float(numpy.dot(res.direction, self.DIRECTION)))), 0.03)
        self.assertLess(abs(res.e_vis / e_vis - 1.0), 0.03)
        self.assertEqual(res.covariance.shape, (7, 7))
        numpy.linalg.cholesky(res.covariance)
        self.assertLessEqual(res.newton_decrement, fit.DECREMENT_TOL)


class EdgeOfTheDomain(unittest.TestCase):
    """Re-review N4: a fit whose maximum lies beyond the domain's edge, started beside it, is pushed against the edge and never
    reads as converged. Found on login (probes 5 to 8 of the D3 stage 2 report): from stage 1's own seed the vertex events below
    converge to an interior maximum (r about 3 m, zero gradient), so the start is set beside the edge; there the vertex fit ends
    no-finite-covariance (the edge point is not a maximum: the Hessian is not negative definite), the yield and t0 fits
    not-converged (their Newton decrement stays far above the tolerance)."""
    EDGE = CFG.sphere_radius_m * (1 - likelihood.DOMAIN_MARGIN)

    def test_charge_only_fit_against_the_vertex_edge(self):
        outward = numpy.array(unit((0.3, -0.5, 0.8)))
        state, charge, e_vis = stage1.noise_free_event(tuple(4.999 * outward), unit((-0.3, 0.5, -0.8)), 300.0)
        start = fit.Seed(4.97 * outward, numpy.array(unit((-0.3, 0.5, -0.8))), e_vis)
        res = fit.fit_event(MODEL, stage1.event_from(state, charge), start=start)
        self.assertEqual((res.status, res.failure, res.uncertainty_status), ("failed", "no-finite-covariance", "not-positive-definite"))
        self.assertLess(numpy.linalg.norm(res.vertex), self.EDGE)
        self.assertGreater(numpy.linalg.norm(res.vertex), self.EDGE - 1e-6)

    def test_charge_only_fit_against_the_yield_edge(self):
        state, charge, e_vis = stage1.noise_free_event((1.2, -0.8, 0.6), unit((0.3, -0.5, 0.8)), 2e5)
        start = fit.Seed(numpy.array((1.2, -0.8, 0.6)), numpy.array(unit((0.3, -0.5, 0.8))), e_vis / 4)
        res = fit.fit_event(MODEL, stage1.event_from(state, charge), start=start)
        self.assertEqual((res.status, res.failure), ("failed", "not-converged"))
        self.assertGreater(res.newton_decrement, 1e3 * fit.DECREMENT_TOL)

    def test_joint_fit_against_the_t0_edge(self):
        truth, direction = (1.2, -0.8, 0.6), unit((0.3, -0.5, 0.8))
        state, charge, times, e_vis = noise_free_timed_event(truth, direction, 2000.0, 405.0)
        start = fit.JointSeed(numpy.array(truth), numpy.array(direction), e_vis, 398.0)
        res = fit.fit_joint_event(MODEL, timed(state, charge, times), start=start)
        self.assertEqual((res.status, res.failure), ("failed", "not-converged"))
        self.assertLess(res.t0, 2 * WINDOW)
        self.assertGreater(res.t0, 2 * WINDOW - 1e-6)
        self.assertGreater(res.newton_decrement, 1e3 * fit.DECREMENT_TOL)


class ChartExit(unittest.TestCase):
    """Case O-chart-exit (found on noisy hand-made events, probes 11 to 13): a joint round ends once |(a, b)| > 1 and the next
    re-centres; SciPy's status 99 for that stop never reads as converged; the charge-only fit keeps stage 1's rule."""

    @classmethod
    def setUpClass(cls):
        state, charge, times, e_vis = noise_free_timed_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0, 17.0)
        cls.tev = timed(state, charge, times)
        cls.start = fit.JointSeed(numpy.array((1.5, 0.5, -1.0)), numpy.array(unit((0.0, 1.0, 1.0))), e_vis, 17.0)

    def mocked(self, status, joint_fit=True):
        from scipy.optimize import OptimizeResult
        x = numpy.r_[self.start.vertex, 0.0, 0.0, self.start.e_vis, self.start.t0]
        if not joint_fit:
            x = x[:6]
        result = OptimizeResult(x=x, status=status, success=False, nit=3, fun=0.0, message="mocked")
        with unittest.mock.patch.object(fit.optimize, "minimize", return_value=result):
            if joint_fit:
                return fit.fit_joint_event(MODEL, self.tev, start=self.start)
            return fit.fit_event(MODEL, self.tev.event, start=fit.Seed(self.start.vertex, self.start.direction, self.start.e_vis))

    def test_status_99_alone_never_converges(self):
        res = self.mocked(fit.CALLBACK_STOP)
        self.assertEqual((res.status, res.failure, res.rounds), ("failed", "iteration-budget", fit.MAX_ROUNDS))

    def test_a_genuine_failure_status_of_a_joint_round_is_not_converged(self):
        """Review F2: the chart exit hides no SciPy failure. A joint round ending in status 3 (or 1, 4) fails not-converged after
        that one round; it is never re-centred."""
        for status in (3, 4):
            with self.subTest(status=status):
                res = self.mocked(status)
                self.assertEqual((res.status, res.failure, res.rounds), ("failed", "not-converged", 1))

    def test_charge_only_keeps_stage_1s_status_rule(self):
        res = self.mocked(fit.CALLBACK_STOP, joint_fit=False)
        self.assertEqual((res.status, res.failure), ("failed", "not-converged"))

    def test_a_mirrored_charge_only_start_is_recovered(self):
        """Stage 1's noisy case B4 r/R_s [0.7, 0.9), this module's stream, event 1: the charge-only prefit ends about 5.5 m from
        the truth (mirrored); the joint fit, through chart exits, converges within 0.1 m and 0.5 ns of the truth."""
        name, n_exp, (r_lo, r_hi), options = stage1.NOISY_CASES[4]
        rng = numpy.random.default_rng([20261111, 104])
        for _ in range(2):
            vertex, direction = stage1.draw_source(rng, r_lo, r_hi)
            t0 = float(rng.uniform(10.0, 30.0))
            tev = noisy_timed_event(rng, vertex, direction, n_exp, t0, **options)
        start, prefit, origin = fit.joint_seed(MODEL, tev)
        self.assertGreater(numpy.linalg.norm(prefit.vertex - numpy.array(vertex)), 4.0)
        calls = []
        real = fit.optimize.minimize

        def spy(*args, **kwargs):
            out = real(*args, **kwargs)
            calls.append(int(out.status))
            return out
        with unittest.mock.patch.object(fit.optimize, "minimize", side_effect=spy):
            res = fit.fit_joint_event(MODEL, tev, start)
        self.assertEqual(res.status, "converged", res.failure)
        self.assertIn(fit.CALLBACK_STOP, calls)
        self.assertLess(numpy.linalg.norm(res.vertex - numpy.array(vertex)), 0.1)
        self.assertLess(abs(res.t0 - t0), 0.5)


# --- the independent evaluation and the fixed-point driver -------------------------------------------------------------------

class IndependentEvaluation(unittest.TestCase):
    ALLOWED = {"math", "json", "sys", "argparse", "__future__"}

    def test_imports_only_the_standard_library_and_no_recipe(self):
        tree = ast.parse((ASSETS / "fixture_tools" / "t09_independent_likelihood.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0] or ".")
        self.assertLessEqual(imported, self.ALLOWED, imported)
        text = (ASSETS / "fixture_tools" / "t09_independent_likelihood.py").read_text(encoding="utf-8")
        for name in ("configuration.json", "open(", "read_text", "read_bytes"):
            self.assertNotIn(name, text)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {"light_recipe", "numpy", "np", "scipy", "special"}, names & {"light_recipe", "numpy", "np", "scipy"})

    def test_the_recipe_imports_no_fixture_tool(self):
        scan = stage1.RecipeImportsNoGenerator()
        for path in sorted((ASSETS / "light_recipe").rglob("*.py")) + [ASSETS / "photon_likelihood.py"]:
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(scan.findings_in(text), [])
                self.assertNotIn("t09_independent_likelihood", text)
                self.assertNotIn("t09_fixed_points", text)

    def test_agrees_with_the_recipe_on_hand_made_points(self):
        rng = numpy.random.default_rng([20261111, 1])
        cases = (((1.0, -0.5, 0.8), unit((0.2, 0.9, -0.3)), 300.0, 18.0, {}),
                 ((-1.5, 2.0, 1.0), unit((1.0, 0.0, 0.2)), 300.0, 25.0, {"dead": stage1.DEAD_200}),
                 ((2.5, 2.0, 1.5), unit((-0.5, 0.5, 0.5)), 300.0, 12.0, {"clip": CLIP}))
        worst = 0.0
        for vertex, direction, n_exp, t0, options in cases:
            tev = noisy_timed_event(rng, vertex, direction, n_exp, t0, **options)
            e_vis = n_exp / (SENSORS * sum(stage1.text_shape(POSITIONS, NORMALS, vertex, direction)))
            off = (tuple(v + 0.5 / math.sqrt(3) for v in vertex), unit(tuple(direction[k] + 0.2 * (0.0, 1.0, 0.0)[k] for k in range(3))),
                   1.2 * e_vis, t0 + 3.0)
            for point in ((vertex, direction, e_vis, t0), off):
                with self.subTest(point=point[0]):
                    args = (numpy.array(point[0]), numpy.array(point[1]), point[2])
                    recipe_joint = joint.log_likelihood(MODEL, tev, *args, point[3])
                    recipe_charge = likelihood.log_likelihood(MODEL, tev.event, *args)
                    ind = independent.evaluate(tev.event.state.tolist(), tev.event.charge.tolist(), tev.time.tolist(),
                                               tev.event.saturated.tolist(), tev.event.saturation_charge, point[0], point[1],
                                               point[2], point[3])
                    self.assertLessEqual(abs(recipe_joint - ind["joint"]), 1e-9)
                    self.assertLessEqual(abs(recipe_charge - ind["charge_only"]), 1e-9)
                    worst = max(worst, abs(recipe_joint - ind["joint"]), abs(recipe_charge - ind["charge_only"]))
        print(f"\nINDEPENDENT hand-made points: largest |ln L difference| {worst:.3e}", file=sys.stderr)

    def test_agrees_outside_the_window(self):
        """Hit times before 0 and after 200 ns (signal alone there; mutation run 1 found this case untested): the recipe and
        the independent evaluation agree within 1e-9, and moving such a time changes ln L."""
        rng = numpy.random.default_rng([20261111, 2])
        tev = noisy_timed_event(rng, (1.0, -0.5, 0.8), unit((0.2, 0.9, -0.3)), 300.0, 18.0)
        hits = numpy.flatnonzero(tev.event.hit)
        times = tev.time.copy()
        times[hits[:4]] = (-3.0, -0.5, 200.0, 260.0)
        moved = joint.TimedEvent(tev.event, times)
        point = ((1.1, -0.4, 0.7), unit((0.25, 0.85, -0.3)), 0.9 * 300.0 / (SENSORS * sum(stage1.text_shape(POSITIONS, NORMALS, (1.0, -0.5, 0.8), unit((0.2, 0.9, -0.3))))), 19.0)
        for event in (tev, moved):
            recipe = joint.log_likelihood(MODEL, event, numpy.array(point[0]), numpy.array(point[1]), point[2], point[3])
            ind = independent.evaluate(event.event.state.tolist(), event.event.charge.tolist(), event.time.tolist(),
                                       event.event.saturated.tolist(), None, *point)
            self.assertLessEqual(abs(recipe - ind["joint"]), 1e-9)
        self.assertGreater(abs(joint.log_likelihood(MODEL, moved, numpy.array(point[0]), numpy.array(point[1]), point[2], point[3])
                               - joint.log_likelihood(MODEL, tev, numpy.array(point[0]), numpy.array(point[1]), point[2], point[3])), 1.0)

    def test_a_planted_constant_is_seen(self):
        tev = timed(*noise_free_timed_event((1.0, -0.5, 0.8), unit((0.2, 0.9, -0.3)), 300.0, 18.0)[:3])
        args = ((1.0, -0.5, 0.8), unit((0.2, 0.9, -0.3)), 0.002, 18.0)
        recipe_joint = joint.log_likelihood(MODEL, tev, numpy.array(args[0]), numpy.array(args[1]), args[2], args[3])
        with unittest.mock.patch.object(independent, "SIGMA_T", 1.6):
            ind = independent.evaluate(tev.event.state.tolist(), tev.event.charge.tolist(), tev.time.tolist(),
                                       tev.event.saturated.tolist(), None, *args)
        self.assertGreater(abs(recipe_joint - ind["joint"]), 1e-3)


class HandMadeFixedPointGenerator:
    """Stands in for the frozen generator's interface for the fixed-point driver: likelihood_points() and event() with noisy
    timed events of this module's own coding."""
    GENERATOR = "t09-sphere/1"
    N_SENSORS = SENSORS
    THRESHOLD = THRESHOLD
    CLIP = CLIP
    UNHIT, HIT, DEAD = 0, 1, 2
    DEAD_CHANNELS = numpy.array(sorted(stage1.DEAD_200))
    POINTS = [{"n_exp": 150.0, "vertex": numpy.array([0.5, -1.0, 0.3]), "direction": numpy.array(unit((0.0, 0.6, 0.8))), "t0": 14.0},
              {"n_exp": 260.0, "vertex": numpy.array([-2.0, 1.0, 2.2]), "direction": numpy.array(unit((1.0, 0.2, 0.0))), "t0": 27.0}]

    def likelihood_points(self):
        out = []
        for p in self.POINTS:
            s = sum(stage1.text_shape(POSITIONS, NORMALS, tuple(p["vertex"]), tuple(p["direction"])))
            out.append({**p, "e_vis": p["n_exp"] / (SENSORS * s)})
        return out

    def event(self, fixture, block, stratum, event_index):
        rng = numpy.random.default_rng([7, block, stratum, event_index, len(fixture)])
        vertex, direction = stage1.draw_source(rng, 0.0, 0.7)
        options = {"dead": stage1.DEAD_200} if fixture == "dead" else {"clip": CLIP} if fixture == "saturation" else {}
        tev = noisy_timed_event(rng, vertex, direction, 250.0, 20.0, **options)
        ev = tev.event
        state = numpy.select([ev.state == readout.LIVE_UNHIT, ev.state == readout.LIVE_HIT, ev.state == readout.DEAD],
                             [self.UNHIT, self.HIT, self.DEAD])
        return {"data": {"state": state, "charge": ev.charge, "time": tev.time, "saturated": ev.saturated}}


class FixedPointDriver(unittest.TestCase):
    def test_gates_pass_on_a_hand_made_generator(self):
        out = io.StringIO()
        code = t09_fixed_points.run(HandMadeFixedPointGenerator(), out)
        text = out.getvalue()
        gates = [line for line in text.splitlines() if line.startswith("GATE ")]
        self.assertEqual(len(gates), 3, text)
        self.assertTrue(all(line.endswith("PASS") for line in gates), text)
        self.assertEqual(code, 0)
        self.assertEqual(text.count("POINT "), 2 * 3, text)

    def test_the_likelihood_gate_fails_on_a_planted_defect(self):
        out = io.StringIO()
        with unittest.mock.patch.object(independent, "SIGMA_T", 1.6):
            code = t09_fixed_points.run(HandMadeFixedPointGenerator(), out)
        gates = [line for line in out.getvalue().splitlines() if line.startswith("GATE ")]
        self.assertTrue(any("joint" in line and line.endswith("FAIL") for line in gates), out.getvalue())
        self.assertEqual(code, 1)

    def test_an_unexpected_exception_is_status_error_exit_2(self):
        """Review F5: the driver's exit codes are core/status.py's: an unexpected exception prints an ERROR line and exits 2
        (error), never 1 (a gate failing)."""
        out = io.StringIO()
        with unittest.mock.patch.object(t09_fixed_points.t09_fixture_files, "load_generator", return_value=HandMadeFixedPointGenerator()), \
                unittest.mock.patch.object(joint, "log_likelihood", side_effect=RuntimeError("planted")), \
                unittest.mock.patch("sys.stdout", out):
            code = t09_fixed_points.main(["--generator", "unused"])
        self.assertEqual(code, 2)
        self.assertIn("ERROR fixed points: unexpected RuntimeError: planted", out.getvalue())
        self.assertNotIn("GATE", out.getvalue())

    def test_driver_refuses_a_generator_that_is_not_the_frozen_one(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "gen_t09_sphere.py"
            fake.write_text("GENERATOR = 't09-sphere/1'\n", encoding="utf-8")
            p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_fixed_points.py"), "--generator",
                                str(fake)], capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("not the frozen", p.stdout)


# --- the product /2, the CLI, the readings ---------------------------------------------------------------------------------

def timed_readout(rows):
    states = numpy.array([r[0] for r in rows], numpy.int8)
    charges = numpy.array([r[1] for r in rows], float)
    times = numpy.array([r[2] for r in rows], float)
    return readout.readout_bytes(states, charges, times, numpy.zeros(states.shape, bool), THRESHOLD, None)


def joint_product_text(content, model=MODEL):
    rd = readout.read_bytes(content)
    buf = io.StringIO()
    writer = product.Writer(buf, product.header_document("hand-made", rd, CFG, likelihood="charge-time"))
    for i in range(rd.events):
        tev = joint.TimedEvent.from_readout(rd, i)
        start, prefit, origin = fit.joint_seed(model, tev)
        res = fit.fit_joint_event(model, tev, start)
        writer.event(product.joint_event_document(i, tev, start, origin, prefit, res, product.check_at(model, tev.event, start, res)))
    writer.finish()
    return buf.getvalue()


class JointProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        b = noise_free_timed_event((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0, 22.0, dead=(5, 6, 7))
        cls.content = timed_readout([a[:3], b[:3]])
        cls.text = joint_product_text(cls.content)

    def test_round_trip_is_byte_equal(self):
        read = product.read_text(self.text, MODEL, CFG)
        buf = io.StringIO()
        writer = product.Writer(buf, read.header)
        for doc in read.events:
            writer.event(doc)
        writer.finish()
        self.assertEqual(buf.getvalue(), self.text)
        self.assertEqual(read.header["format"], "light-likelihood-product/2")
        self.assertEqual([p["name"] for p in read.header["parameters"]][-1], "t0")
        self.assertIsInstance(read.events[0]["fit"]["t0"], float)
        self.assertEqual(len(read.events[0]["fit"]["covariance"]), 7)
        self.assertEqual(len(read.events[0]["hits"][0]), 4)

    def test_header_records_the_joint_fit_rules(self):
        """Review F4 and F6: /2's fit settings record the chart-exit radius, the status-99 rule and the t0 domain in windows,
        each from the recipe's own constant."""
        settings = json.loads(self.text.splitlines()[0])["fit_settings"]
        self.assertEqual(settings["joint_chart_radius"], fit.JOINT_CHART_RADIUS)
        self.assertEqual(settings["callback_stop_status"], fit.CALLBACK_STOP)
        self.assertIn("never convergence", settings["callback_stop_rule"])
        self.assertEqual(settings["t0_domain_windows"], list(joint.T0_DOMAIN_WINDOWS))
        self.assertNotIn("t0_domain_ns", settings)

    def test_refuses_malformed_or_incomplete(self):
        lines = self.text.splitlines()
        header, events, end = json.loads(lines[0]), [json.loads(x) for x in lines[1:-1]], json.loads(lines[-1])

        def build(h=None, evs=None):
            parts = [h or header] + (events if evs is None else evs) + [end]
            return "".join(json.dumps(p, sort_keys=True, allow_nan=False) + "\n" for p in parts)

        def changed(change):
            evs = copy.deepcopy(events)
            change(evs[0])
            return build(evs=evs)
        cases = {"t0 not a number": changed(lambda d: d["fit"].update(t0="not-estimated")),
                 "6 x 6 covariance": changed(lambda d: d["fit"].update(covariance=[r[:6] for r in d["fit"]["covariance"][:6]])),
                 "a hit row without a time": changed(lambda d: d["hits"][0].pop()),
                 "a time not a number": changed(lambda d: d["hits"][0].__setitem__(3, "inf")),
                 "the stage 1 likelihood text": build(h={**header, "likelihood": "charge-only, all live channels (stage 1)"}),
                 "joint ln L that does not recompute": changed(lambda d: d["fit"].update(ln_likelihood=d["fit"]["ln_likelihood"] + 1e-3)),
                 "a moved time": changed(lambda d: d["hits"][0].__setitem__(3, d["hits"][0][3] + 0.5)),
                 "prefit missing": changed(lambda d: d.pop("prefit"))}
        for name, bad in cases.items():
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad, MODEL, CFG)


def leaves(doc, path=()):
    """Every path into a JSON document, containers included."""
    yield path
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from leaves(v, path + (k,))
    elif isinstance(doc, list):
        for i, v in enumerate(doc[:3]):
            yield from leaves(v, path + (i,))


def replaced(doc, path, value):
    doc = copy.deepcopy(doc)
    if not path:
        return value
    target = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return doc


class MalformedFields(unittest.TestCase):
    """Re-review N5: any malformed field is refused as ProductError (status rejected, exit 2), never an internal error."""
    VALUES = (None, True, "x", [], {}, 1e308, -1)

    @classmethod
    def setUpClass(cls):
        state, charge, _ = stage1.noise_free_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0)
        rd = readout.read_bytes(stage1.readout_file(numpy.array([state]), numpy.array([charge])))
        ev = likelihood.EventData.from_readout(rd, 0)
        res = fit.fit_event(MODEL, ev)
        buf = io.StringIO()
        writer = product.Writer(buf, product.header_document("x", rd, CFG))
        writer.event(product.event_document(0, ev, fit.seed(MODEL, ev), res, product.check_at(MODEL, ev, fit.seed(MODEL, ev), res)))
        writer.finish()
        a = noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        cls.texts = {"charge-only": buf.getvalue(), "charge-time": joint_product_text(timed_readout([a[:3]]))}

    def test_every_field_replaced_gives_product_error_or_acceptance(self):
        accepted = {}
        for kind, text in self.texts.items():
            docs = [json.loads(line) for line in text.splitlines()]
            for line_no, doc in enumerate(docs):
                for path in leaves(doc):
                    for value in self.VALUES:
                        bad_doc = replaced(doc, path, value)
                        if bad_doc == doc:
                            continue
                        lines = [json.dumps(d, sort_keys=True) for d in docs]
                        lines[line_no] = json.dumps(bad_doc, sort_keys=True)
                        try:
                            product.read_text("\n".join(lines) + "\n", MODEL, CFG)
                            accepted.setdefault(kind, []).append((line_no, path, value))
                        except product.ProductError:
                            pass
                        except Exception as exc:  # noqa: BLE001 - the defect under test
                            self.fail(f"{kind} line {line_no} path {path} value {value!r}: {type(exc).__name__}: {exc}")
        print(f"\nMALFORMED accepted replacements (well-typed values the reader does not recompute): "
              f"{ {k: len(v) for k, v in accepted.items()} }", file=sys.stderr)

    def test_an_absurd_hit_charge_or_time_is_refused_not_an_error(self):
        """Found on login (probe red-3): a stored hit charge of 1e9 made the unchanged reader allocate 7.45 GiB (MemoryError,
        status error). Charges above 1e5 and, for /2, times beyond +-1e6 ns are outside the model's domain: refused at once."""
        for kind, index, value in (("charge-only", 1, 1e9), ("charge-time", 1, 1e9), ("charge-time", 3, 5e6)):
            with self.subTest(kind=kind, field=index):
                lines = self.texts[kind].splitlines()
                doc = json.loads(lines[1])
                doc["hits"][0][index] = value
                started = time.perf_counter()
                with self.assertRaises(product.ProductError):
                    product.read_text("\n".join([lines[0], json.dumps(doc, sort_keys=True), lines[2]]) + "\n", MODEL, CFG)
                self.assertLess(time.perf_counter() - started, 5.0)
        state, charge, times, _ = noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        first = int(numpy.flatnonzero(state == readout.LIVE_HIT)[0])
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for name, likelihood_name, edit in (("charge", "charge-only", lambda c, t: c.__setitem__(first, 2e5)),
                                               ("time", "charge-time", lambda c, t: t.__setitem__(first, 2e6))):
                c, t = charge.copy(), times.copy()
                edit(c, t)
                (folder / f"{name}.readout").write_bytes(timed_readout([(state, c, t)]))
                p = stage1.run_cli("fit", "--readout", str(folder / f"{name}.readout"), "--product", str(folder / f"{name}.jsonl"),
                                   "--product-id", "x", "--likelihood", likelihood_name)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertEqual(json.loads(p.stdout)["status"], "rejected", p.stdout)
                self.assertFalse((folder / f"{name}.jsonl").exists())

    def test_a_structural_exception_inside_a_check_is_refused_and_a_recipe_defect_is_not(self):
        """The N5 rule itself (mutation run 1: no field replacement reaches it, the checks guard every type, so it is defence in
        depth): a KeyError or TypeError raised inside a structural check becomes ProductError; an exception of the recomputation
        that is not a ValueError stays what it is, a defect of the recipe (status error)."""
        text = self.texts["charge-time"]
        for target, exc in (("_check_header", KeyError("planted")), ("_event_arrays", TypeError("planted")),
                            ("_check_fit", IndexError("planted")), ("_check_seed", AttributeError("planted"))):
            with self.subTest(target=target), unittest.mock.patch.object(product, target, side_effect=exc):
                with self.assertRaisesRegex(product.ProductError, "malformed field"):
                    product.read_text(text, MODEL, CFG)
        with unittest.mock.patch.object(joint, "log_likelihood", side_effect=RuntimeError("planted")):
            with self.assertRaises(RuntimeError):
                product.read_text(text, MODEL, CFG)

    def test_a_deeply_nested_line_is_refused_not_an_error(self):
        """Review F3: a line nested 200,000 deep makes json.loads raise RecursionError; both readers refuse it (ProductError,
        status rejected, exit 2), never status error."""
        deep = "[" * 200000 + "]" * 200000
        for kind, text in self.texts.items():
            lines = text.splitlines()
            for where in (0, 1):
                with self.subTest(kind=kind, line=where):
                    bad = list(lines)
                    bad[where] = deep
                    with self.assertRaises(product.ProductError):
                        product.read_text("\n".join(bad) + "\n", MODEL, CFG)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "deep.jsonl"
                path.write_text("\n".join([lines[0], deep] + lines[2:]) + "\n")
                p = stage1.run_cli("check-product", "--product", str(path))
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertEqual(json.loads(p.stdout)["status"], "rejected", p.stdout)

    def test_seed_origin_must_agree_with_the_prefit(self):
        """Review F8: "charge-only fit" needs a converged prefit, "charge-only fit, last point" a failed prefit with a point,
        "charge seed" a failed prefit without one; a converged prefit always has a point."""
        lines = self.texts["charge-time"].splitlines()
        doc = json.loads(lines[1])
        self.assertEqual((doc["seed"]["from"], doc["prefit"]["status"]), ("charge-only fit", "converged"))
        for origin in ("charge-only fit, last point", "charge seed"):
            with self.subTest(origin=origin):
                bad = copy.deepcopy(doc)
                bad["seed"]["from"] = origin
                with self.assertRaises(product.ProductError):
                    product.read_text("\n".join([lines[0], json.dumps(bad, sort_keys=True), lines[2]]) + "\n", MODEL, CFG)
        for change in ({"status": "failed", "failure": "not-converged"}, {"point": False}, {"point": 1}):
            with self.subTest(prefit=change):
                bad = copy.deepcopy(doc)
                bad["prefit"].update(change)
                with self.assertRaises(product.ProductError):
                    product.read_text("\n".join([lines[0], json.dumps(bad, sort_keys=True), lines[2]]) + "\n", MODEL, CFG)
        good = copy.deepcopy(doc)
        good["prefit"].update(status="failed", failure="not-converged")
        good["seed"]["from"] = "charge-only fit, last point"
        product.read_text("\n".join([lines[0], json.dumps(good, sort_keys=True), lines[2]]) + "\n", MODEL, CFG)

    def test_check_product_reports_rejected_for_a_malformed_header(self):
        lines = self.texts["charge-only"].splitlines()
        header = json.loads(lines[0])
        header["input"] = ["not", "a", "dict"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            path.write_text("\n".join([json.dumps(header, sort_keys=True)] + lines[1:]) + "\n")
            p = stage1.run_cli("check-product", "--product", str(path))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"], "rejected", p.stdout)


class JointCommandLine(unittest.TestCase):
    def test_fit_charge_time_then_check_product_and_the_default(self):
        a = noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        b = noise_free_timed_event((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0, 22.0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "r.readout").write_bytes(timed_readout([a[:3], b[:3]]))
            base = ["fit", "--readout", str(folder / "r.readout"), "--product-id", "hm"]
            p = stage1.run_cli(*base, "--product", str(folder / "joint.jsonl"), "--likelihood", "charge-time")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual((out["status"], out["events"], out["likelihood"]), ("ok", 2, "charge-time"))
            p = stage1.run_cli("check-product", "--product", str(folder / "joint.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = stage1.run_cli(*base, "--product", str(folder / "default.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = stage1.run_cli(*base, "--product", str(folder / "charge.jsonl"), "--likelihood", "charge-only")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual((folder / "default.jsonl").read_bytes(), (folder / "charge.jsonl").read_bytes())
            self.assertEqual(json.loads((folder / "default.jsonl").read_text().splitlines()[0])["format"], "light-likelihood-product/1")
            p = stage1.run_cli(*base, "--product", str(folder / "x.jsonl"), "--likelihood", "time-only")
            self.assertNotEqual(p.returncode, 0)

    def test_tool_contract_passes(self):
        stage1.CommandLine("test_tool_contract_passes").test_tool_contract_passes()
        doc = json.loads((ROOT / "contracts" / "tool_contracts" / "photon_likelihood.json").read_text(encoding="utf-8"))
        flags = [o["flag"] for o in doc["operations"][0]["invocation"]["options"]]
        self.assertIn("--likelihood", flags)


class JointReadings(unittest.TestCase):
    def test_t0_pull_by_hand(self):
        truth_dir = numpy.array(unit((0.3, -0.5, 0.8)))
        f1, f2 = fit.frame(truth_dir)
        cov = numpy.diag([0.01, 0.04, 0.0025, 1e-4, 4e-4, 0.0009, 0.0625])
        doc = {"status": "converged", "vertex": [1.1, -0.2, 0.05], "direction": truth_dir.tolist(), "e_vis": 1.03, "t0": 20.5,
               "frame": {"e1": f1.tolist(), "e2": f2.tolist()}, "covariance": cov.tolist(), "uncertainty_status": "ok"}
        pulls = t09_readings.event_pulls(doc, numpy.array([1.0, 0.0, 0.0]), truth_dir, 1.0, truth_t0=20.0)
        self.assertAlmostEqual(pulls["t0"], 2.0, delta=1e-12)
        self.assertAlmostEqual(pulls["x"], 1.0, delta=1e-12)

    def test_harness_cli_and_readings_end_to_end_with_time(self):
        class Timed(stage1.HandMadeGenerator):
            def event(self, fixture, block, stratum, event_index):
                vertex, direction, n_exp = self.TRUTHS[event_index]
                ev = super().event(fixture, block, stratum, event_index)
                _, _, times, _ = noise_free_timed_event(vertex, direction, n_exp, 20.0,
                                                        dead=tuple(self.DEAD_CHANNELS) if fixture == "dead" else ())
                ev["data"]["time"] = times
                return ev
        for fixture in ("main", "dead", "saturation"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                files = stage1.t09_fixture_files.stratum_files(Timed(), fixture, 1, 0, 3, folder, "s")
                p = stage1.run_cli("fit", "--readout", files["readout"]["path"], "--product", str(folder / "p.jsonl"), "--product-id",
                                   "hm", "--likelihood", "charge-time")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_readings.py"), "--product",
                                    str(folder / "p.jsonl"), "--truth", files["truth"]["path"], "--label", f"hm-{fixture}"],
                                   capture_output=True, text=True, timeout=600)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                gates = [line for line in p.stdout.splitlines() if line.startswith("GATE ")]
                self.assertEqual(len(gates), 2, p.stdout)
                self.assertTrue(all(line.endswith("PASS") for line in gates), p.stdout)
                self.assertIn("pull t0", p.stdout)


# --- noisy joint fits and cost ---------------------------------------------------------------------------------------------

class NoisyJointFits(unittest.TestCase):
    """Stage 1's seven noisy cases, now with times: every event ends converged or as a counted failure kind, the per-channel
    check holding at its reported point."""

    def test_noisy_events_per_case(self):
        lines = []
        for k, (name, n_exp, (r_lo, r_hi), options) in enumerate(stage1.NOISY_CASES):
            rng = numpy.random.default_rng([20261111, 100 + k])
            counts, seconds, t0_errors = {}, [], []
            for _ in range(stage1.NOISY_EVENTS):
                vertex, direction = stage1.draw_source(rng, r_lo, r_hi)
                t0 = float(rng.uniform(10.0, 30.0))
                tev = noisy_timed_event(rng, vertex, direction, n_exp, t0, **options)
                with self.subTest(case=name):
                    started = time.perf_counter()
                    start, prefit, origin = fit.joint_seed(MODEL, tev)
                    res = fit.fit_joint_event(MODEL, tev, start)
                    seconds.append(time.perf_counter() - started)
                    self.assertIn(res.status, ("converged", "failed"))
                    if res.status == "failed":
                        self.assertIn(res.failure, fit.FAILURES)
                    check = product.check_at(MODEL, tev.event, start, res)
                    self.assertEqual(check["failures"], 0, check)
                    counts[res.failure or "converged"] = counts.get(res.failure or "converged", 0) + 1
                    if res.t0 is not None:
                        t0_errors.append(abs(res.t0 - t0))
            lines.append(f"{name}: {dict(sorted(counts.items()))}, {1e3 * numpy.mean(seconds):.0f} ms mean, "
                         f"{1e3 * max(seconds):.0f} ms largest, median |t0 - truth| {numpy.median(t0_errors):.2f} ns")
        print("\nNOISY-JOINT " + "; ".join(lines), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
