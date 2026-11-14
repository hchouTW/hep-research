"""adapters/photon-likelihood, D3 stage 1 of T09 (t07-t09-task-sheets.md, T09): the readout, the charge-only all-channel
likelihood with its fit, and the product format, on hand-made events only. No fixture event and no Monte Carlo: every event
here is written by hand or is a noise-free closed-form light pattern, so each expectation is fixed in the test before the
recipe runs.

Expectations come from a second coding of t04-values-v4.md section 4.3 and of the photon-likelihood reference in plain Python
(math, loops), not from the recipe's modules. A test that calls the recipe compares it with that second coding.
Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood -v
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

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "photon-likelihood"
ASSETS = ADAPTER / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from light_recipe import LABEL, PARAMETERS, RECIPE, charge_response, configuration, fit, light_model, likelihood, product, readout  # noqa: E402
import t09_fixture_files  # noqa: E402
import t09_readings  # noqa: E402
from contracts import tool_contract  # noqa: E402

# t04-values-v4.md section 4.3, written here from the text
R_S, SENSORS, AREA, SPEED, ATTENUATION = 5.0, 1000, 0.094, 0.22, 30.0
F_EMIT, K_EMIT, DARK, WINDOW, SIGMA_T = 0.6, 5.0, 0.002, 200.0, 1.5
PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA, THRESHOLD, CLIP = 1.0, 0.3, 0.25, 5.0
CFG = configuration.load()
MODEL = likelihood.Model(CFG)


# --- a second coding of section 4.3 and of the reference, from their text ---------------------------------------------

def lattice():
    out = []
    for i in range(SENSORS):
        polar = math.acos(1.0 - 2.0 * (i + 0.5) / SENSORS)
        azimuth = math.pi * (1.0 + math.sqrt(5.0)) * (i + 0.5)
        out.append((math.sin(polar) * math.cos(azimuth), math.sin(polar) * math.sin(azimuth), math.cos(polar)))
    return out


NORMALS = lattice()
POSITIONS = [tuple(R_S * c for c in n) for n in NORMALS]


def unit(v):
    norm = math.sqrt(sum(c * c for c in v))
    return tuple(c / norm for c in v)


def emission(c):
    return (1 - F_EMIT) / (4 * math.pi) + F_EMIT * K_EMIT * math.exp(K_EMIT * c) / (4 * math.pi * math.sinh(K_EMIT))


def text_shape(positions, normals, vertex, direction, area=AREA):
    out = []
    for p, n in zip(positions, normals):
        r = [p[k] - vertex[k] for k in range(3)]
        dist = math.sqrt(sum(c * c for c in r))
        u = [c / dist for c in r]
        cos_inc = sum(u[k] * n[k] for k in range(3))
        c = sum(u[k] * direction[k] for k in range(3))
        out.append(area * cos_inc / dist ** 2 * math.exp(-dist / ATTENUATION) * emission(c))
    return out


def text_mean(positions, normals, vertex, direction, e_vis):
    """m_i = mu_i + dark, mu_i = 1000 E_vis s_i (section 4.3: E_vis = N_exp / (1000 S))."""
    return [SENSORS * e_vis * s + DARK for s in text_shape(positions, normals, vertex, direction)]


def log_pois(n, m):
    return n * math.log(m) - m - math.lgamma(n + 1)


def lse(values):
    top = max(values)
    return top + math.log(sum(math.exp(v - top) for v in values))


def n_range(m, extra=0.0):
    return range(0, int(max(m, extra) + 40 * math.sqrt(max(m, extra, 1.0)) + 100))


def log_upper(z):
    """ln P(Z >= z) for a standard normal: from erfc below z = 5; above it, -z^2/2 - ln sqrt(2 pi) + ln R(z) with the Mills ratio
    R(z) = 1/(z + 1/(z + 2/(z + 3/(z + ...)))) from its continued fraction (fix round 1: erfc underflows above z of about 27,
    which dropped the dominant terms of the no-hit sum at m = 1e5)."""
    if z < 5.0:
        return math.log(0.5 * math.erfc(z / math.sqrt(2.0)))
    tail = z
    for k in range(200, 0, -1):
        tail = z + k / tail
    return -0.5 * z * z - 0.5 * math.log(2 * math.pi) - math.log(tail)


def upper(z):
    """P(Z >= z) as a log, for the sums below (never underflows)."""
    return log_upper(z)


def text_ln_no_hit(m, threshold=THRESHOLD):
    terms = [-m]
    for n in n_range(m):
        if n == 0:
            continue
        terms.append(log_pois(n, m) + upper((n - threshold) / (PHOTON_CHARGE_SIGMA * math.sqrt(n))))   # P(q < T | n)
    return lse(terms)


def text_ln_at_or_above(level, m):
    terms = []
    for n in n_range(m, level):
        if n == 0:
            continue
        terms.append(log_pois(n, m) + upper((level - n) / (PHOTON_CHARGE_SIGMA * math.sqrt(n))))
    return lse(terms)


def text_ln_density(q, m):
    terms = []
    for n in n_range(m, q):
        if n == 0:
            continue
        s = PHOTON_CHARGE_SIGMA * math.sqrt(n)
        terms.append(log_pois(n, m) - 0.5 * ((q - n) / s) ** 2 - math.log(s * math.sqrt(2 * math.pi)))
    return lse(terms)


def density(q, m):
    return math.exp(text_ln_density(q, m))


def six_sensor_geometry():
    normals = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    return normals, [tuple(R_S * c for c in n) for n in normals]


def frame_text(d):
    a = (0.0, 0.0, 1.0) if abs(d[2]) <= 0.9 else (1.0, 0.0, 0.0)
    e1 = unit((a[1] * d[2] - a[2] * d[1], a[2] * d[0] - a[0] * d[2], a[0] * d[1] - a[1] * d[0]))
    e2 = (d[1] * e1[2] - d[2] * e1[1], d[2] * e1[0] - d[0] * e1[2], d[0] * e1[1] - d[1] * e1[0])
    return e1, e2


def noise_free_event(vertex, direction, n_exp, dead=()):
    """Charges set to their expectation m_i (no noise): hit where m_i >= T, unhit (charge 0) below; dead channels NaN."""
    shape = text_shape(POSITIONS, NORMALS, vertex, direction)
    e_vis = n_exp / (SENSORS * sum(shape))
    m = [SENSORS * e_vis * s + DARK for s in shape]
    state = numpy.array([readout.LIVE_HIT if x >= THRESHOLD else readout.LIVE_UNHIT for x in m], dtype=numpy.int8)
    charge = numpy.array([x if x >= THRESHOLD else 0.0 for x in m])
    for ch in dead:
        state[ch] = readout.DEAD
        charge[ch] = numpy.nan
    return state, charge, e_vis


def event_from(state, charge, saturated=None, saturation_charge=None):
    saturated = numpy.zeros(len(state), bool) if saturated is None else numpy.asarray(saturated, bool)
    return likelihood.EventData(numpy.asarray(state, numpy.int8), numpy.asarray(charge, float), saturated, saturation_charge,
                                THRESHOLD)


def readout_file(states, charges, saturated=None, saturation_charge=None, threshold=THRESHOLD):
    states = numpy.asarray(states, numpy.int8)
    charges = numpy.asarray(charges, float)
    times = numpy.where(states == readout.LIVE_HIT, 20.0, numpy.nan)
    saturated = numpy.zeros(states.shape, bool) if saturated is None else numpy.asarray(saturated, bool)
    return readout.readout_bytes(states, charges, times, saturated, threshold, saturation_charge)


# --- configuration, geometry, light model -------------------------------------------------------------------------------

class Configuration(unittest.TestCase):
    def test_values_are_section_4_3s_constants(self):
        expected = {"sphere_radius_m": R_S, "sensors": SENSORS, "sensor_area_m2": AREA, "photon_speed_m_per_ns": SPEED,
                    "attenuation_length_m": ATTENUATION, "emission_f": F_EMIT, "emission_k": K_EMIT,
                    "dark_mean_per_window": DARK, "window_ns": WINDOW, "time_spread_ns": SIGMA_T, "photon_charge_mean": PHOTON_CHARGE_MEAN,
                    "photon_charge_sigma": PHOTON_CHARGE_SIGMA, "charge_threshold": THRESHOLD}
        self.assertEqual({k: CFG.values[k] for k in expected}, expected)
        self.assertEqual(set(CFG.values), set(expected) | {"format"})

    def test_an_extra_or_missing_key_is_refused(self):
        doc = json.loads(configuration.DEFAULT.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            for name, bad in (("extra", {**doc, "charge_scale": 1.02}), ("missing", {k: v for k, v in doc.items() if k != "photon_charge_sigma"}),
                              ("format", {**doc, "format": "other/1"})):
                with self.subTest(case=name):
                    path = Path(folder) / f"{name}.json"
                    path.write_text(json.dumps(bad), encoding="utf-8")
                    with self.assertRaises(configuration.ConfigurationError):
                        configuration.load(path)


class Geometry(unittest.TestCase):
    def test_fibonacci_lattice_as_the_text(self):
        geo = configuration.fibonacci_geometry(CFG)
        self.assertEqual(geo.positions.shape, (SENSORS, 3))
        self.assertLess(numpy.abs(geo.positions - numpy.array(POSITIONS)).max(), 1e-12)
        self.assertLess(numpy.abs(geo.normals - numpy.array(NORMALS)).max(), 1e-12)
        self.assertEqual(geo.area, AREA)


class LightModel(unittest.TestCase):
    VERTEX = (1.1, -2.0, 0.7)
    DIRECTION = unit((0.2, 0.9, -0.4))

    def test_expected_signal_as_the_text(self):
        got = light_model.expected(MODEL, numpy.array(self.VERTEX), numpy.array(self.DIRECTION), 0.8)
        want = numpy.array(text_mean(POSITIONS, NORMALS, self.VERTEX, self.DIRECTION, 0.8))
        self.assertLess(numpy.abs(got / want - 1).max(), 1e-12)

    def test_e_vis_sets_n_exp(self):
        """Section 4.3: sum_i mu_i = N_exp with E_vis = N_exp / (1000 S)."""
        s = text_shape(POSITIONS, NORMALS, self.VERTEX, self.DIRECTION)
        e_vis = 300.0 / (SENSORS * sum(s))
        mu = light_model.expected(MODEL, numpy.array(self.VERTEX), numpy.array(self.DIRECTION), e_vis) - DARK
        self.assertAlmostEqual(mu.sum(), 300.0, delta=1e-9)

    def test_log_derivatives_against_finite_differences(self):
        x = numpy.array(self.VERTEX)
        d = numpy.array(self.DIRECTION)
        s, dx, dd = light_model.shape_log_gradient(MODEL, x, d)
        for k in range(3):
            step = numpy.zeros(3)
            step[k] = 1e-6
            fd = (numpy.log(light_model.shape(MODEL, x + step, d)) - numpy.log(light_model.shape(MODEL, x - step, d))) / 2e-6
            self.assertLess(numpy.abs(dx[:, k] - fd).max() / numpy.abs(fd).max(), 1e-6)
            fd = (numpy.log(light_model.shape(MODEL, x, d + step)) - numpy.log(light_model.shape(MODEL, x, d - step))) / 2e-6
            self.assertLess(numpy.abs(dd[:, k] - fd).max() / numpy.abs(fd).max(), 1e-6)


# --- the threshold model and the charge terms ---------------------------------------------------------------------------

M_GRID = (1e-6, 1e-3, 0.002, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 120.0, 300.0, 1000.0, 2000.0, 5000.0, 1e5)
EPSILON = 2.0 ** -52


def text_tolerance(m):
    """Fix round 1, F5: 64 eps (1 + m |ln m|), the rounding of the log terms n ln m - m - lnGamma(n + 1) with margin."""
    return 64 * EPSILON * (1 + m * abs(math.log(m)))


class SumToOne(unittest.TestCase):
    """The sheet's stop: per channel, P(hit) + P(no hit) = 1 under one threshold model, few-photon regime included."""
    RESPONSE = charge_response.ChargeResponse(THRESHOLD, PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA)

    def test_sum_to_one_over_expected_charges(self):
        m = numpy.array(M_GRID)
        p_hit, p_no = self.RESPONSE.probability_sums(m)
        tolerance = likelihood.sum_tolerance(m)
        for k, value in enumerate(M_GRID):
            with self.subTest(m=value):
                self.assertAlmostEqual(tolerance[k], text_tolerance(value), delta=1e-6 * tolerance[k])
                self.assertLessEqual(abs(p_hit[k] + p_no[k] - 1.0), tolerance[k])
        dense = numpy.exp(numpy.linspace(math.log(500.0), math.log(1e5), 400))
        p_hit, p_no = self.RESPONSE.probability_sums(dense)
        self.assertTrue(numpy.all(numpy.abs(p_hit + p_no - 1.0) <= likelihood.sum_tolerance(dense)))
        self.assertLess(likelihood.sum_tolerance(numpy.array([1101.0]))[0], 2e-10)    # the fixture's largest truth m (review F5)

    def test_no_hit_and_hit_against_a_brute_force_sum(self):
        m = numpy.array(M_GRID)
        ln_no = self.RESPONSE.log_no_hit(m)[0]
        ln_hit = self.RESPONSE.log_at_or_above(THRESHOLD, m)[0]
        for k, value in enumerate(M_GRID):
            with self.subTest(m=value):
                # fix round 1, F5: both sides carry the rounding of the log terms, eps m |ln m| each
                delta = max(1e-10, 2 * text_tolerance(value))
                self.assertAlmostEqual(ln_no[k], text_ln_no_hit(value), delta=delta * max(1.0, abs(ln_no[k])))
                self.assertAlmostEqual(ln_hit[k], text_ln_at_or_above(THRESHOLD, value), delta=delta)

    def test_hit_density_integrates_to_p_hit(self):
        for value in (0.01, 0.1, 0.5, 1.0, 3.0, 10.0):
            with self.subTest(m=value):
                top = value + 12 * math.sqrt(value) + 12
                points = [n for n in range(1, int(top))]
                total, _ = integrate.quad(lambda q: density(q, value), THRESHOLD, top, points=points, limit=400, epsabs=1e-13)
                self.assertAlmostEqual(total, math.exp(text_ln_at_or_above(THRESHOLD, value)), delta=1e-8)
                got = numpy.exp(self.RESPONSE.log_hit_density(numpy.array([1.3]), numpy.array([value]))[0][0])
                self.assertAlmostEqual(got, density(1.3, value), delta=1e-12 * max(1.0, got))

    def test_density_against_the_brute_force_sum(self):
        for q, value in ((0.26, 0.002), (0.4, 0.1), (1.0, 1.0), (2.3, 4.0), (0.3, 500.0), (300.0, 0.01), (95.0, 100.0), (180.0, 140.0)):
            with self.subTest(q=q, m=value):
                got = self.RESPONSE.log_hit_density(numpy.array([q]), numpy.array([value]))[0][0]
                self.assertAlmostEqual(got, text_ln_density(q, value), delta=1e-10 * max(1.0, abs(got)))

    def test_saturation_splits_hit_without_losing_probability(self):
        for value in (1.0, 4.0, 8.0):
            with self.subTest(m=value):
                below, _ = integrate.quad(lambda q: density(q, value), THRESHOLD, CLIP, points=[1, 2, 3, 4], limit=400, epsabs=1e-13)
                at_or_above = math.exp(self.RESPONSE.log_at_or_above(CLIP, numpy.array([value]))[0][0])
                no_hit = math.exp(self.RESPONSE.log_no_hit(numpy.array([value]))[0][0])
                self.assertAlmostEqual(below + at_or_above + no_hit, 1.0, delta=1e-8)
                self.assertAlmostEqual(math.log(at_or_above), text_ln_at_or_above(CLIP, value), delta=1e-10)

    def test_mismatched_threshold_is_caught_by_the_check(self):
        """Control: a no-hit term on another threshold than the hit term's breaks the sum, so the check is not true by
        construction of a single code path."""
        mixed = charge_response.ChargeResponse(THRESHOLD, PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA)
        mixed.log_no_hit = charge_response.ChargeResponse(0.30, PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA).log_no_hit
        p_hit, p_no = mixed.probability_sums(numpy.array([0.1, 1.0, 3.0]))
        self.assertTrue(numpy.all(numpy.abs(p_hit + p_no - 1.0) > 1e3 * likelihood.sum_tolerance(numpy.array([0.1, 1.0, 3.0]))))

    def test_derivatives_in_m(self):
        for name, fn in (("no hit", lambda m: self.RESPONSE.log_no_hit(m)),
                         ("density q 1.7", lambda m: self.RESPONSE.log_hit_density(numpy.full(m.shape, 1.7), m)),
                         ("at or above 5", lambda m: self.RESPONSE.log_at_or_above(CLIP, m))):
            for value in (0.05, 0.8, 3.0, 40.0):
                with self.subTest(term=name, m=value):
                    h = 1e-4 * value
                    l0, l1, l2 = (a[0] for a in fn(numpy.array([value])))
                    lp, lm = fn(numpy.array([value + h]))[0][0], fn(numpy.array([value - h]))[0][0]
                    self.assertAlmostEqual(l1, (lp - lm) / (2 * h), delta=1e-6 * max(1.0, abs(l1)))
                    self.assertAlmostEqual(l2, (lp - 2 * l0 + lm) / h ** 2, delta=1e-4 * max(1.0, abs(l2)))


# --- the likelihood on a tiny hand-made sphere --------------------------------------------------------------------------

class TinySphere(unittest.TestCase):
    """Six sensors on the axes of a 5 m sphere: +x saturated (C = 5), -x unhit, +y hit 2.3, -y dead, +z hit 0.4, -z unhit."""
    VERTEX = (1.0, 0.5, -0.3)
    DIRECTION = unit((1.0, 1.0, 0.2))
    E_VIS = 2.0

    @classmethod
    def setUpClass(cls):
        normals, positions = six_sensor_geometry()
        cls.normals, cls.positions = normals, positions
        cls.model = likelihood.Model(CFG, geometry=configuration.Geometry(numpy.array(positions, float), numpy.array(normals, float), AREA))
        cls.state = [readout.LIVE_HIT, readout.LIVE_UNHIT, readout.LIVE_HIT, readout.DEAD, readout.LIVE_HIT, readout.LIVE_UNHIT]
        cls.charge = [CLIP, 0.0, 2.3, numpy.nan, 0.4, 0.0]
        cls.saturated = [True, False, False, False, False, False]
        cls.m = text_mean(positions, normals, cls.VERTEX, cls.DIRECTION, cls.E_VIS)

    def event(self, state=None):
        return event_from(self.state if state is None else state, self.charge, self.saturated, CLIP)

    def ln_l(self, event):
        return likelihood.log_likelihood(self.model, event, numpy.array(self.VERTEX), numpy.array(self.DIRECTION), self.E_VIS)

    def test_expected_charges_span_the_few_photon_regime(self):
        self.assertLess(min(self.m), 3.0)
        self.assertGreater(max(self.m), 0.3)

    def test_value_against_a_hand_computation(self):
        m = self.m
        hand = text_ln_at_or_above(CLIP, m[0]) + text_ln_no_hit(m[1]) + text_ln_density(2.3, m[2]) \
            + text_ln_density(0.4, m[4]) + text_ln_no_hit(m[5])
        self.assertAlmostEqual(self.ln_l(self.event()), hand, delta=1e-10)

    def test_dead_channel_is_excluded_not_unhit(self):
        dead_read_as_unhit = list(self.state)
        dead_read_as_unhit[3] = readout.LIVE_UNHIT
        charge = list(self.charge)
        charge[3] = 0.0
        unhit_event = event_from(dead_read_as_unhit, charge, self.saturated, CLIP)
        difference = self.ln_l(unhit_event) - self.ln_l(self.event())
        self.assertAlmostEqual(difference, text_ln_no_hit(self.m[3]), delta=1e-10)
        self.assertLess(difference, -1e-3)

    def test_saturated_channel_is_censored(self):
        censored = text_ln_at_or_above(CLIP, self.m[0])
        as_measured = text_ln_density(CLIP, self.m[0])
        self.assertGreater(abs(censored - as_measured), 0.1)
        unflagged = event_from(self.state, [4.9] + self.charge[1:], [False] * 6, CLIP)
        delta = self.ln_l(self.event()) - self.ln_l(unflagged)
        self.assertAlmostEqual(delta, censored - text_ln_density(4.9, self.m[0]), delta=1e-10)

    def test_probability_check_on_every_live_channel(self):
        check = likelihood.probability_check(self.model, self.event(), numpy.array(self.VERTEX), numpy.array(self.DIRECTION), self.E_VIS)
        self.assertEqual((check["channels"], check["failures"]), (5, 0))
        self.assertLessEqual(check["max_abs_deviation"], 1e-12)

    def test_gradient_and_hessian_against_finite_differences(self):
        event = self.event()
        objective = likelihood.Objective(self.model, event, numpy.array(self.DIRECTION))
        p0 = numpy.array([*self.VERTEX, 0.03, -0.02, self.E_VIS])
        value, gradient, hessian = objective.derivatives(p0)
        steps = numpy.array([1e-4, 1e-4, 1e-4, 1e-5, 1e-5, 1e-5 * self.E_VIS])
        for k in range(6):
            e = numpy.zeros(6)
            e[k] = steps[k]
            fd = (objective.value(p0 + e) - objective.value(p0 - e)) / (2 * steps[k])
            self.assertAlmostEqual(gradient[k], fd, delta=1e-5 * max(1.0, abs(fd)))
            fd_row = (objective.derivatives(p0 + e)[1] - objective.derivatives(p0 - e)[1]) / (2 * steps[k])
            self.assertLess(numpy.abs(hessian[k] - fd_row).max(), 1e-5 * max(1.0, numpy.abs(fd_row).max()))
        self.assertLess(numpy.abs(hessian - hessian.T).max(), 1e-12 * numpy.abs(hessian).max())

    def test_outside_the_sphere_or_non_positive_yield_is_out_of_domain(self):
        event = self.event()
        objective = likelihood.Objective(self.model, event, numpy.array(self.DIRECTION))
        self.assertEqual(objective.value(numpy.array([5.0, 0.0, 0.0, 0.0, 0.0, 1.0])), -math.inf)
        self.assertEqual(objective.value(numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])), -math.inf)


class EventDataRefusals(unittest.TestCase):
    def test_refusals(self):
        good = dict(state=[1, 0, 2], charge=[1.2, 0.0, numpy.nan], saturated=[False, False, False])
        cases = {"dead with a charge": dict(good, charge=[1.2, 0.0, 0.5]),
                 "unhit with a charge": dict(good, charge=[1.2, 0.1, numpy.nan]),
                 "hit below threshold": dict(good, charge=[0.2, 0.0, numpy.nan]),
                 "flag without a saturation value": dict(good, saturated=[True, False, False]),
                 "unknown state": dict(good, state=[1, 0, 7])}
        for name, case in cases.items():
            with self.subTest(case=name), self.assertRaises(likelihood.EventError):
                event_from(case["state"], case["charge"], case["saturated"])
        with self.assertRaises(likelihood.EventError):
            event_from([1, 0, 2], [4.0, 0.0, numpy.nan], [True, False, False], CLIP)      # flagged, not C
        with self.assertRaises(likelihood.EventError):
            event_from([1, 0, 2], [5.0, 0.0, numpy.nan], [False, False, False], CLIP)     # unflagged at C

    def test_states_are_three_explicit_kinds_plus_disabled(self):
        ev = event_from([1, 0, 2, 3], [1.0, 0.0, numpy.nan, numpy.nan])
        self.assertEqual((ev.live.tolist(), ev.hit.tolist(), ev.unhit.tolist(), ev.dead.tolist(), ev.disabled.tolist()),
                         ([True, True, False, False], [True, False, False, False], [False, True, False, False],
                          [False, False, True, False], [False, False, False, True]))


# --- frame, seed and fit ------------------------------------------------------------------------------------------------

class Frame(unittest.TestCase):
    def test_section_7_rule(self):
        for d in (unit((0.3, -0.5, 0.8)), unit((0.1, 0.1, 0.99)), unit((0.0, 0.0, -1.0)), unit((1.0, 0.0, 0.0))):
            with self.subTest(d=d):
                e1, e2 = fit.frame(numpy.array(d))
                t1, t2 = frame_text(d)
                self.assertLess(numpy.abs(e1 - numpy.array(t1)).max(), 1e-14)
                self.assertLess(numpy.abs(e2 - numpy.array(t2)).max(), 1e-14)
                self.assertAlmostEqual(float(numpy.dot(numpy.cross(e1, e2), d)), 1.0, delta=1e-14)


class Seed(unittest.TestCase):
    def test_seed_is_finite_and_inside(self):
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0)
        s = fit.seed(MODEL, event_from(state, charge))
        self.assertLess(numpy.linalg.norm(s.vertex), R_S)
        self.assertAlmostEqual(float(numpy.linalg.norm(s.direction)), 1.0, delta=1e-12)
        self.assertGreater(s.e_vis, 0.0)

    def test_seed_is_the_stated_moment_estimate_over_live_channels(self):
        """Case O-seed: charge centroid, vertex 0.5 c, charge-weighted direction, E_vis from the live channels only."""
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0, dead=tuple(range(0, 1000, 5)))
        s = fit.seed(MODEL, event_from(state, charge))
        hits = [i for i in range(SENSORS) if state[i] == readout.LIVE_HIT]
        total = sum(charge[i] for i in hits)
        x0 = [0.5 * sum(charge[i] * POSITIONS[i][k] for i in hits) / total for k in range(3)]
        pull = [0.0, 0.0, 0.0]
        for i in hits:
            r = [POSITIONS[i][k] - x0[k] for k in range(3)]
            norm = math.sqrt(sum(c * c for c in r))
            pull = [pull[k] + charge[i] * r[k] / norm for k in range(3)]
        d0 = unit(pull)
        shape = text_shape(POSITIONS, NORMALS, x0, d0)
        e0 = total / (SENSORS * sum(shape[i] for i in range(SENSORS) if state[i] != readout.DEAD))
        self.assertLess(numpy.abs(s.vertex - numpy.array(x0)).max(), 1e-12)
        self.assertLess(numpy.abs(s.direction - numpy.array(d0)).max(), 1e-12)
        self.assertAlmostEqual(s.e_vis, e0, delta=1e-12 * e0)

    def test_budget_and_decrement_rules(self):
        """Section 7's fit failure: the iteration budget, and the Newton-decrement test (case O-optimizer, amendment 1)."""
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0)
        ev = event_from(state, charge)
        with unittest.mock.patch.object(fit, "MAX_ITERATIONS", 1):
            self.assertEqual(fit.fit_event(MODEL, ev).failure, "iteration-budget")
        with unittest.mock.patch.object(fit, "DECREMENT_TOL", -1.0):
            res = fit.fit_event(MODEL, ev)
            self.assertEqual((res.status, res.failure), ("failed", "not-converged"))
            self.assertIsNotNone(res.newton_decrement)
        res = fit.fit_event(MODEL, ev)
        self.assertEqual(res.status, "converged")
        self.assertLessEqual(res.newton_decrement, fit.DECREMENT_TOL)

    def test_no_hit_channel_gives_no_seed_and_a_recorded_failure(self):
        ev = event_from(numpy.zeros(SENSORS, numpy.int8), numpy.zeros(SENSORS))
        self.assertIsNone(fit.seed(MODEL, ev))
        res = fit.fit_event(MODEL, ev)
        self.assertEqual((res.status, res.failure), ("failed", "no-hit-channel"))


class NoiseFreeFit(unittest.TestCase):
    TRUTH = (1.2, -0.8, 0.6)
    DIRECTION = unit((0.3, -0.5, 0.8))

    def test_fit_recovers_a_hand_made_vertex(self):
        state, charge, e_vis = noise_free_event(self.TRUTH, self.DIRECTION, 20000.0)
        ev = event_from(state, charge)
        rot = math.radians(40.0)
        e1, _ = frame_text(self.DIRECTION)
        start_dir = unit(tuple(math.cos(rot) * self.DIRECTION[k] + math.sin(rot) * e1[k] for k in range(3)))
        start = fit.Seed(numpy.array(self.TRUTH) + numpy.array([0.6, 0.6, -0.5]), numpy.array(start_dir), 0.5 * e_vis)
        res = fit.fit_event(MODEL, ev, start=start)
        self.assertEqual(res.status, "converged", res.failure)
        self.assertLess(numpy.linalg.norm(res.vertex - numpy.array(self.TRUTH)), 0.05)
        self.assertLess(math.acos(min(1.0, float(numpy.dot(res.direction, self.DIRECTION)))), 0.03)
        self.assertLess(abs(res.e_vis / e_vis - 1.0), 0.03)
        self.assertEqual(res.uncertainty_status, "ok")
        numpy.linalg.cholesky(res.covariance)
        self.assertLess(res.gradient_norm, 1e-4)
        check = likelihood.probability_check(MODEL, ev, res.vertex, res.direction, res.e_vis)
        self.assertEqual((check["channels"], check["failures"]), (SENSORS, 0))

    def test_dead_channels_are_left_out_of_the_fit(self):
        """Dead channels hold NaN: a fit that read them would not be finite."""
        dead = tuple(range(200))
        state, charge, _ = noise_free_event(self.TRUTH, self.DIRECTION, 2000.0, dead=dead)
        res = fit.fit_event(MODEL, event_from(state, charge))
        self.assertEqual(res.status, "converged", res.failure)
        self.assertTrue(math.isfinite(res.ln_likelihood))


# --- the readout format -------------------------------------------------------------------------------------------------

class Readout(unittest.TestCase):
    def sample(self):
        states = numpy.array([[1, 0, 2, 1], [0, 0, 2, 1]], numpy.int8)
        charges = numpy.array([[5.0, 0.0, numpy.nan, 0.7], [0.0, 0.0, numpy.nan, 1.9]])
        times = numpy.where(states == 1, 21.5, numpy.nan)
        saturated = numpy.array([[True, False, False, False], [False, False, False, False]])
        return states, charges, times, saturated

    def test_round_trip(self):
        states, charges, times, saturated = self.sample()
        content = readout.readout_bytes(states, charges, times, saturated, THRESHOLD, CLIP)
        got = readout.read_bytes(content)
        self.assertEqual(got.events, 2)
        numpy.testing.assert_array_equal(got.state, states)
        numpy.testing.assert_array_equal(got.charge, charges)
        numpy.testing.assert_array_equal(got.time, times)
        numpy.testing.assert_array_equal(got.saturated, saturated)
        self.assertEqual((got.header["threshold"], got.header["saturation_charge"]), (THRESHOLD, CLIP))
        self.assertEqual(readout.readout_bytes(got.state, got.charge, got.time, got.saturated, THRESHOLD, CLIP), content)

    def test_header_holds_no_truth_seed_or_generator_field(self):
        states, charges, times, saturated = self.sample()
        header = readout.read_bytes(readout.readout_bytes(states, charges, times, saturated, THRESHOLD, CLIP)).header
        self.assertEqual(set(header), readout.HEADER_KEYS)
        for word in ("seed", "stratum", "block", "fixture", "generator", "truth", "event_index"):
            self.assertNotIn(word, header)

    def test_refusals(self):
        states, charges, times, saturated = self.sample()
        good = readout.readout_bytes(states, charges, times, saturated, THRESHOLD, CLIP)
        cases = {}

        def with_header(change):
            head_len = int.from_bytes(good[8:12], "little")
            head = json.loads(good[12:12 + head_len])
            change(head)
            text = json.dumps(head, sort_keys=True).encode()
            return good[:8] + len(text).to_bytes(4, "little") + text + good[12 + head_len:]
        cases["extra header key, a seed"] = with_header(lambda h: h.update(seed=9001))
        cases["role truth"] = with_header(lambda h: h.update(role="truth"))
        cases["truncated"] = good[:-3]
        cases["magic"] = b"XXXXXXXX" + good[8:]

        def variant(**kw):
            s, c, t, z = (kw.get(k, v.copy()) for k, v in (("s", states), ("c", charges), ("t", times), ("z", saturated)))
            return readout.readout_bytes(s, c, t, z, THRESHOLD, kw.get("clip", CLIP), check=False)
        c = charges.copy(); c[0, 2] = 0.3
        cases["dead with a charge"] = variant(c=c)
        t = times.copy(); t[0, 2] = 5.0
        cases["dead with a time"] = variant(t=t)
        c = charges.copy(); c[0, 1] = 0.1
        cases["unhit with a charge"] = variant(c=c)
        t = times.copy(); t[0, 1] = 5.0
        cases["unhit with a time"] = variant(t=t)
        c = charges.copy(); c[0, 3] = 0.2
        cases["hit below threshold"] = variant(c=c)
        cases["flag without a saturation value"] = variant(clip=None)
        c = charges.copy(); c[0, 0] = 4.0
        cases["flagged charge not C"] = variant(c=c)
        c = charges.copy(); c[1, 3] = 6.0
        cases["unflagged at or above C"] = variant(c=c)
        s = states.copy(); s[1, 0] = 7
        cases["unknown state"] = variant(s=s)
        for name, bad in cases.items():
            with self.subTest(defect=name), self.assertRaises(readout.ReadoutError):
                readout.read_bytes(bad)


# --- the product format -------------------------------------------------------------------------------------------------

class ProductFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state_a, charge_a, _ = noise_free_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0)
        state_b, charge_b, _ = noise_free_event((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0, dead=(5, 6, 7))
        cls.content = readout_file(numpy.array([state_a, state_b]), numpy.array([charge_a, charge_b]))
        rd = readout.read_bytes(cls.content)
        buf = io.StringIO()
        writer = product.Writer(buf, product.header_document("hand-made", rd, CFG))
        for i in range(rd.events):
            ev = likelihood.EventData.from_readout(rd, i)
            s = fit.seed(MODEL, ev)
            res = fit.fit_event(MODEL, ev)
            writer.event(product.event_document(i, ev, s, res, product.check_at(MODEL, ev, s, res)))
        writer.finish()
        cls.text = buf.getvalue()

    def test_round_trip_is_byte_equal(self):
        read = product.read_text(self.text, MODEL, CFG)
        buf = io.StringIO()
        writer = product.Writer(buf, read.header)
        for doc in read.events:
            writer.event(doc)
        writer.finish()
        self.assertEqual(buf.getvalue(), self.text)
        self.assertEqual(read.header["label"], LABEL)
        self.assertEqual(read.header["recipe"], RECIPE)
        self.assertEqual([p["name"] for p in read.header["parameters"]], list(PARAMETERS))
        self.assertEqual(read.events[1]["states"][5:8], "DDD")
        self.assertEqual(read.events[0]["fit"]["t0"], "not-estimated")

    def test_refuses_malformed_or_incomplete(self):
        lines = self.text.splitlines()
        header, events, end = json.loads(lines[0]), [json.loads(x) for x in lines[1:-1]], json.loads(lines[-1])

        def build(h=None, evs=None, e=None, extra=""):
            parts = [h or header] + (events if evs is None else evs) + [e or end]
            return "".join(json.dumps(p, sort_keys=True, allow_nan=False) + "\n" for p in parts) + extra

        def changed(index, change):
            evs = copy.deepcopy(events)
            change(evs[index])
            return build(evs=evs)
        cases = {"missing end": "".join(x + "\n" for x in lines[:-1]),
                 "wrong end count": build(e={**end, "events": 5}),
                 "text after the end": build(extra="{}\n"),
                 "unknown header key": build(h={**header, "seed": 1}),
                 "missing header key": build(h={k: v for k, v in header.items() if k != "retention"}),
                 "label not shared-model closure": build(h={**header, "label": "validated"}),
                 "events out of order": build(evs=[events[1], events[0]]),
                 "unknown event key": changed(0, lambda d: d.update(note="x")),
                 "t0 given a value": changed(0, lambda d: d["fit"].update(t0=20.0)),
                 "states of wrong length": changed(0, lambda d: d.update(states=d["states"][:-1])),
                 "states with an unknown letter": changed(0, lambda d: d.update(states="Z" + d["states"][1:])),
                 "a hit without a row": changed(0, lambda d: d.update(hits=d["hits"][1:])),
                 "counts not the states'": changed(1, lambda d: d["counts"].update(dead=2)),
                 "asymmetric covariance": changed(0, lambda d: d["fit"]["covariance"][0].__setitem__(1, d["fit"]["covariance"][0][1] + 1.0)),
                 "non-positive covariance": changed(0, lambda d: d["fit"]["covariance"][2].__setitem__(2, -1.0)),
                 "non-unit direction": changed(0, lambda d: d["fit"].update(direction=[2 * c for c in d["fit"]["direction"]])),
                 "frame not section 7's": changed(0, lambda d: d["fit"]["frame"].update(e1=d["fit"]["frame"]["e2"], e2=d["fit"]["frame"]["e1"])),
                 "ln L that does not recompute": changed(0, lambda d: d["fit"].update(ln_likelihood=d["fit"]["ln_likelihood"] + 1e-3)),
                 "probability check that does not recompute": changed(0, lambda d: d["probability_check"].update(failures=1))}
        hit_row_for_unhit = copy.deepcopy(events)
        first_unhit = hit_row_for_unhit[0]["states"].index("U")
        hit_row_for_unhit[0]["hits"].append([first_unhit, 1.0, 0])
        hit_row_for_unhit[0]["hits"].sort()
        cases["a hit row for a non-hit channel"] = build(evs=hit_row_for_unhit)
        for name, bad in cases.items():
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad, MODEL, CFG)


# --- the recipe imports no generator ------------------------------------------------------------------------------------

class RecipeImportsNoGenerator(unittest.TestCase):
    """Section 3.1 and Freeze A amendment 1: a recipe never links or imports a generator, seed code or truth readers."""
    FORBIDDEN_MODULES = ("gen_t08_grid", "gen_t09_sphere", "check_generators", "t09_fixture_files", "t09_readings", "fixture_tools",
                         "importlib", "numpy.random", "runpy", "subprocess", "pickle", "multiprocessing", "imp", "zipimport")
    FORBIDDEN_CALLS = ("spec_from_file_location", "__import__", "exec", "eval", "compile", "SeedSequence", "default_rng", "read_truth",
                       "run_path", "run_module", "import_module", "system", "popen", "Popen", "execv", "execl", "spawnv")
    FORBIDDEN_NUMPY = ("random", "load", "loadtxt", "fromfile", "genfromtxt")   # numpy.load reads an npz: the truth file's format
    PLANTED = {"import runpy": "import runpy\nrunpy.run_path('gen_t09_sphere.py')\n",
               "subprocess": "import subprocess\nsubprocess.run(['python', 'gen_t09_sphere.py'])\n",
               "os.system": "import os\nos.system('python gen_t09_sphere.py')\n",
               "numpy.load": "import numpy\nnumpy.load('stratum.truth.npz')\n",
               "numpy.load by name": "from numpy import load\nload('stratum.truth.npz')\n",
               "importlib": "import importlib\nimportlib.import_module('gen_t09_sphere')\n",
               "__import__": "__import__('gen_t09_sphere')\n",
               "exec": "exec(open('gen_t09_sphere.py').read())\n",
               "relative import of fixture_tools": "from . import fixture_tools\n",
               "from-import of a generator": "from gen_t09_sphere import event\n",
               "pickle": "import pickle\n",
               "multiprocessing": "import multiprocessing\n",
               "numpy.random": "import numpy.random\n",
               "default_rng": "import numpy as np\nnp.random.default_rng(1)\n"}

    def findings_in(self, text):
        tree = ast.parse(text)
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found += [a.name for a in node.names if a.name.startswith(self.FORBIDDEN_MODULES)]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names]
                if module.startswith(self.FORBIDDEN_MODULES) or any(n.startswith(self.FORBIDDEN_MODULES) for n in names) \
                        or (module == "numpy" and any(n in self.FORBIDDEN_NUMPY for n in names)):
                    found.append(module or ",".join(names))
            elif isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_CALLS:
                    found.append(node.attr)
                elif node.attr in self.FORBIDDEN_NUMPY and isinstance(node.value, ast.Name) and node.value.id in ("numpy", "np"):
                    found.append(f"numpy.{node.attr}")
            elif isinstance(node, ast.Name) and node.id in self.FORBIDDEN_CALLS:
                found.append(node.id)
        return found

    def recipe_files(self):
        files = sorted((ASSETS / "light_recipe").rglob("*.py")) + [ASSETS / "photon_likelihood.py"]
        self.assertGreaterEqual(len(files), 8)
        return files

    def test_each_planted_form_is_caught(self):
        for name, text in self.PLANTED.items():
            with self.subTest(planted=name):
                self.assertTrue(self.findings_in(text), name)

    def test_recipe_imports_no_generator_seed_or_truth_code(self):
        for path in self.recipe_files():
            with self.subTest(file=path.name):
                self.assertEqual(self.findings_in(path.read_text(encoding="utf-8")), [])

    def test_the_scan_finds_them_where_they_are(self):
        """Control: the scoring-side harness loads the generator by importlib, and the scan sees it there."""
        self.assertIn("spec_from_file_location", self.findings_in((ASSETS / "fixture_tools" / "t09_fixture_files.py").read_text(encoding="utf-8")))
        self.assertIn("t09_fixture_files", self.findings_in((ASSETS / "fixture_tools" / "t09_readings.py").read_text(encoding="utf-8")))

    def test_harness_refuses_a_generator_that_is_not_the_frozen_one(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "gen_t09_sphere.py"
            fake.write_text("GENERATOR = 't09-sphere/1'\n", encoding="utf-8")
            with self.assertRaisesRegex(t09_fixture_files.FixtureError, "not the frozen"):
                t09_fixture_files.load_generator(fake)


# --- the command line ---------------------------------------------------------------------------------------------------

def run_cli(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "photon_likelihood.py"), *args], capture_output=True, text=True,
                          timeout=600)


class CommandLine(unittest.TestCase):
    def test_fit_then_check_product(self):
        state_a, charge_a, _ = noise_free_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0)
        state_b, charge_b, _ = noise_free_event((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "r.readout").write_bytes(readout_file(numpy.array([state_a, state_b]), numpy.array([charge_a, charge_b])))
            args = ["fit", "--readout", str(folder / "r.readout"), "--product", str(folder / "out.jsonl"), "--product-id", "hand-made-cli"]
            p = run_cli(*args)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual((out["status"], out["events"], out["converged"], out["probability_failures"], out["label"]),
                             ("ok", 2, 2, 0, LABEL))
            p = run_cli("check-product", "--product", str(folder / "out.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["probability_failures"], 0)
            # refusals: a readout with another threshold, a missing file; no product written
            (folder / "t.readout").write_bytes(readout_file(numpy.array([state_a]), numpy.array([charge_a]), threshold=0.2))
            for name, swap in (("other threshold", ("r.readout", "t.readout")), ("missing", ("r.readout", "none.readout"))):
                with self.subTest(refused=name):
                    bad = [a.replace(swap[0], swap[1]) if a.endswith(swap[0]) else a for a in args]
                    bad[bad.index("--product") + 1] = str(folder / f"{name}.jsonl")
                    p = run_cli(*bad)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertEqual(json.loads(p.stdout)["status"], "rejected")
                    self.assertFalse((folder / f"{name}.jsonl").exists())
            p = run_cli(*args)
            self.assertEqual(p.returncode, 2, "an existing product is never overwritten")
            (folder / "cut.jsonl").write_text("\n".join((folder / "out.jsonl").read_text().split("\n")[:-2]) + "\n")
            p = run_cli("check-product", "--product", str(folder / "cut.jsonl"))
            self.assertEqual(p.returncode, 2)

    def test_tool_contract_passes(self):
        doc = json.loads((ROOT / "contracts" / "tool_contracts" / "photon_likelihood.json").read_text(encoding="utf-8"))
        res = tool_contract.check(doc)
        self.assertEqual(res["status"], "pass", res["findings"])


# --- the scoring side on a hand-made stand-in generator ------------------------------------------------------------------

class HandMadeGenerator:
    """Stands in for the frozen generator's interface (constants and event()) with noise-free events, so the harness, the CLI
    and the readings run end to end without the fixture."""
    GENERATOR = "t09-sphere/1"
    N_SENSORS = SENSORS
    THRESHOLD = THRESHOLD
    CLIP = CLIP
    UNHIT, HIT, DEAD = 0, 1, 2
    DEAD_CHANNELS = numpy.arange(200)
    TRUTHS = [((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0), ((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0),
              ((0.3, -2.2, 0.9), unit((0.0, 1.0, 0.2)), 600.0)]

    def event(self, fixture, block, stratum, event_index):
        vertex, direction, n_exp = self.TRUTHS[event_index]
        dead = tuple(self.DEAD_CHANNELS) if fixture == "dead" else ()
        state, charge, e_vis = noise_free_event(vertex, direction, n_exp, dead=dead)
        saturated = numpy.zeros(SENSORS, bool)
        if fixture == "saturation":
            saturated = numpy.nan_to_num(charge) >= CLIP
            charge = numpy.where(saturated, CLIP, charge)
        time_ = numpy.where(state == self.HIT, 20.0, numpy.nan)
        return {"generator": self.GENERATOR, "fixture": fixture, "block": block, "stratum": stratum, "event_index": event_index,
                "data": {"state": state, "charge": charge, "time": time_, "saturated": saturated},
                "truth": {"n_exp": numpy.array([n_exp]), "vertex": numpy.array([vertex]), "direction": numpy.array([direction]),
                          "t0": 20.0, "e_vis": numpy.array([e_vis])}}


class ScoringSide(unittest.TestCase):
    def test_centre_and_width(self):
        values = numpy.arange(-9.5, 10.5, 1.0)       # 20 values, 2 trimmed at each end
        self.assertAlmostEqual(t09_readings.centre(values), 0.0, delta=1e-15)
        self.assertAlmostEqual(t09_readings.centre(numpy.r_[values[:-1], 1000.0]), t09_readings.centre(values), delta=1e-15)
        lo, hi = numpy.quantile(values, (0.158655, 0.841345))
        self.assertAlmostEqual(t09_readings.width(values), (hi - lo) / 2, delta=1e-15)

    def test_pulls_by_hand(self):
        truth_dir = numpy.array(unit((0.3, -0.5, 0.8)))
        t1, t2 = (numpy.array(v) for v in frame_text(tuple(truth_dir)))
        fit_dir = truth_dir + 0.02 * t1 - 0.01 * t2
        fit_dir /= numpy.linalg.norm(fit_dir)
        f1, f2 = fit.frame(fit_dir)
        cov = numpy.diag([0.01, 0.04, 0.0025, 1e-4, 4e-4, 0.0009])
        doc = {"status": "converged", "vertex": [1.1, -0.2, 0.05], "direction": fit_dir.tolist(), "e_vis": 1.03,
               "frame": {"e1": f1.tolist(), "e2": f2.tolist()}, "covariance": cov.tolist(), "uncertainty_status": "ok"}
        pulls = t09_readings.event_pulls(doc, numpy.array([1.0, 0.0, 0.0]), truth_dir, 1.0)
        self.assertAlmostEqual(pulls["x"], 1.0, delta=1e-12)
        self.assertAlmostEqual(pulls["y"], -1.0, delta=1e-12)
        self.assertAlmostEqual(pulls["z"], 1.0, delta=1e-12)
        self.assertAlmostEqual(pulls["e_vis"], 1.0, delta=1e-12)
        jac = numpy.array([[t1 @ f1, t1 @ f2], [t2 @ f1, t2 @ f2]])
        c2 = jac @ cov[3:5, 3:5] @ jac.T
        self.assertAlmostEqual(pulls["u1"], float((fit_dir - truth_dir) @ t1) / math.sqrt(c2[0, 0]), delta=1e-12)
        self.assertAlmostEqual(pulls["u2"], float((fit_dir - truth_dir) @ t2) / math.sqrt(c2[1, 1]), delta=1e-12)

    def test_dead_gate_fails_on_dead_read_as_unhit(self):
        dead = [0, 1, 2]
        good = {"event": 0, "states": "DDD" + "U" * 7}
        bad = {"event": 0, "states": "DUD" + "U" * 7}
        self.assertEqual(t09_readings.dead_state_defects([good], dead), [])
        self.assertTrue(t09_readings.dead_state_defects([bad], dead))
        self.assertTrue(t09_readings.dead_state_defects([{"event": 0, "states": "DDDD" + "U" * 6}], dead))

    def test_harness_cli_and_readings_end_to_end(self):
        for fixture in ("main", "dead", "saturation"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                files = t09_fixture_files.stratum_files(HandMadeGenerator(), fixture, 1, 0, 3, folder, "s")
                rd = readout.read_file(files["readout"]["path"])
                self.assertEqual(set(rd.header), readout.HEADER_KEYS)
                self.assertEqual(rd.header["saturation_charge"], CLIP if fixture == "saturation" else None)
                head, arrays = t09_fixture_files.read_truth(files["truth"]["path"])
                self.assertEqual(head["readout_sha256"], rd.sha256)
                self.assertEqual(len(arrays["dead_channels"]), 200 if fixture == "dead" else 0)
                p = run_cli("fit", "--readout", files["readout"]["path"], "--product", str(folder / "p.jsonl"), "--product-id", "hm")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_readings.py"), "--product",
                                    str(folder / "p.jsonl"), "--truth", files["truth"]["path"], "--label", f"hm-{fixture}"],
                                   capture_output=True, text=True, timeout=600)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                gates = [line for line in p.stdout.splitlines() if line.startswith("GATE ")]
                self.assertEqual(len(gates), 2, p.stdout)
                self.assertTrue(all(line.endswith("PASS") for line in gates), p.stdout)
                self.assertIn("READING hm-" + fixture + " fits", p.stdout)
                self.assertIn("pull x", p.stdout)

    def test_readings_refuse_a_truth_file_of_another_readout(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            a = t09_fixture_files.stratum_files(HandMadeGenerator(), "main", 1, 0, 2, folder, "a")
            b = t09_fixture_files.stratum_files(HandMadeGenerator(), "dead", 1, 0, 2, folder, "b")
            p = run_cli("fit", "--readout", a["readout"]["path"], "--product", str(folder / "p.jsonl"), "--product-id", "hm")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_readings.py"), "--product",
                                str(folder / "p.jsonl"), "--truth", b["truth"]["path"], "--label", "x"], capture_output=True, text=True,
                               timeout=600)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("REFUSED", p.stdout)


# --- fix round 1: the no-hit window, the domain, noisy and near-wall events, the convergence rule, exit codes -------------

def noisy_event(rng, vertex, direction, n_exp, dead=(), clip=None):
    """A noisy hand-made event from this module's second coding of section 4.3, with this module's own random numbers (never
    the frozen generator): Poisson signal and dark counts, Normal(n, 0.3^2 n) summed charge, hit at 0.25, clip at C."""
    shape = numpy.array(text_shape(POSITIONS, NORMALS, vertex, direction))
    mu = n_exp * shape / shape.sum()
    n = rng.poisson(mu) + rng.poisson(DARK, SENSORS)
    charge = numpy.where(n > 0, rng.normal(n * PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA * numpy.sqrt(numpy.maximum(n, 1))), 0.0)
    hit = charge >= THRESHOLD
    state = numpy.where(hit, readout.LIVE_HIT, readout.LIVE_UNHIT).astype(numpy.int8)
    charge = numpy.where(hit, charge, 0.0)
    saturated = numpy.zeros(SENSORS, bool)
    if clip is not None:
        saturated = charge >= clip
        charge = numpy.where(saturated, clip, charge)
    for ch in dead:
        state[ch], charge[ch], saturated[ch] = readout.DEAD, numpy.nan, False
    return event_from(state, charge, saturated, clip)


def draw_source(rng, r_lo, r_hi):
    def iso():
        c, a = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
        s = math.sqrt(1 - c * c)
        return (s * math.cos(a), s * math.sin(a), c)
    r = R_S * (rng.uniform(r_lo ** 3, r_hi ** 3)) ** (1 / 3)
    return tuple(r * c for c in iso()), iso()


DEAD_200 = tuple(sorted(range(SENSORS), key=lambda i: (-NORMALS[i][2], i))[:200])     # the 200 sensors nearest +z, from the text
NOISY_CASES = (("B3 r/R_s [0, 0.4)", 300.0, (0.0, 0.4), {}), ("B3 r/R_s [0.4, 0.7)", 300.0, (0.4, 0.7), {}),
               ("B1 r/R_s [0.7, 0.9)", 40.0, (0.7, 0.9), {}), ("B3 r/R_s [0.7, 0.9)", 300.0, (0.7, 0.9), {}),
               ("B4 r/R_s [0.7, 0.9)", 1500.0, (0.7, 0.9), {}), ("dead, B3 r/R_s [0.4, 0.7)", 300.0, (0.4, 0.7), {"dead": DEAD_200}),
               ("saturation, B3 r/R_s [0.7, 0.9)", 300.0, (0.7, 0.9), {"clip": CLIP}))
NOISY_EVENTS = 8


class NoisyAndNearWall(unittest.TestCase):
    """Review F1 and F7: every event ends converged or as a counted failure kind, never as an exception, and the per-channel
    check holds at its reported point."""

    def outcome(self, ev):
        res = fit.fit_event(MODEL, ev)
        self.assertIn(res.status, ("converged", "failed"))
        if res.status == "failed":
            self.assertIn(res.failure, fit.FAILURES)
        s = fit.seed(MODEL, ev)
        check = product.check_at(MODEL, ev, s, res)
        self.assertEqual(check["failures"], 0, check)
        return res

    def test_the_reviewers_wall_event(self):
        doc = json.loads((ROOT / "tests" / "adapters" / "data" / "t09_wall_event.json").read_text(encoding="utf-8"))
        ev = event_from(numpy.array(doc["state"], numpy.int8), numpy.array(doc["charge"]))
        started = time.perf_counter()
        res = self.outcome(ev)
        print(f"\nWALL review event: {res.status} {res.failure}, {res.iterations} iterations, "
              f"{time.perf_counter() - started:.2f} s, |vertex - truth| "
              f"{numpy.linalg.norm(res.vertex - numpy.array(doc['vertex'])) if res.vertex is not None else float('nan'):.3f} m",
              file=sys.stderr)

    def test_noisy_events_per_case(self):
        lines = []
        for k, (name, n_exp, (r_lo, r_hi), options) in enumerate(NOISY_CASES):
            rng = numpy.random.default_rng([20261110, k])
            counts, seconds = {}, []
            for _ in range(NOISY_EVENTS):
                vertex, direction = draw_source(rng, r_lo, r_hi)
                ev = noisy_event(rng, vertex, direction, n_exp, **options)
                with self.subTest(case=name):
                    started = time.perf_counter()
                    res = self.outcome(ev)
                    seconds.append(time.perf_counter() - started)
                    counts[res.failure or "converged"] = counts.get(res.failure or "converged", 0) + 1
            lines.append(f"{name}: {dict(sorted(counts.items()))}, {1e3 * numpy.mean(seconds):.0f} ms mean, {1e3 * max(seconds):.0f} ms largest")
        print("\nNOISY " + "; ".join(lines), file=sys.stderr)


class DomainAndWindows(unittest.TestCase):
    """Review F1 and F3: outside the domain the objective is total (value -inf, zero gradient, Hessian -I) and cheap; the
    no-hit series is bounded around its peak with a stated tail bound."""

    def test_objective_is_total_outside_the_domain(self):
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0)
        objective = likelihood.Objective(MODEL, event_from(state, charge), numpy.array(unit((0.0, 1.0, 1.0))))
        for name, p in (("outside the sphere", [5.1, 0.0, 0.0, 0.0, 0.0, 1.0]), ("on the margin", [4.99999, 0.0, 0.0, 0.0, 0.0, 1.0]),
                        ("zero yield", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), ("huge yield", [0.0, 0.0, 0.0, 0.0, 0.0, 1e9])):
            with self.subTest(point=name):
                value, gradient, hessian = objective.derivatives(numpy.array(p))
                self.assertEqual(value, -math.inf)
                numpy.testing.assert_array_equal(gradient, numpy.zeros(6))
                numpy.testing.assert_array_equal(hessian, -numpy.eye(6))

    def test_near_wall_point_stays_cheap(self):
        """A vertex 1 mm inside the domain's edge, on a sensor's axis: one evaluation stays well under a second."""
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0)
        ev = event_from(state, charge)
        edge = CFG.sphere_radius_m * (1 - likelihood.DOMAIN_MARGIN) - 1e-3
        for e_vis in (1.0, 50.0):
            p = numpy.r_[edge * numpy.array(NORMALS[0]), 0.0, 0.0, e_vis]
            objective = likelihood.Objective(MODEL, ev, numpy.array(NORMALS[0]))
            started = time.perf_counter()
            objective.derivatives(p)
            self.assertLess(time.perf_counter() - started, 1.0)

    def test_no_hit_window_is_bounded_with_its_tail_bound(self):
        """Tail bound of the docstring: dropped mass <= 8.04 e^(-m + lambda) P(Pois(lambda) outside the window), lambda =
        m exp(-1/(2 sigma^2)); it must be below 1e-17 of the kept sum for m from 1e-8 to the domain's cap."""
        from scipy import special
        response = charge_response.ChargeResponse(THRESHOLD, PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA)
        for value in (1e-8, 1e-3, 0.002, 1.0, 10.0, 300.0, 1e4, likelihood.YIELD_DOMAIN):
            with self.subTest(m=value):
                lo, hi = response.no_hit_window(numpy.array([value]))
                lam = value * math.exp(-1.0 / (2 * PHOTON_CHARGE_SIGMA ** 2))
                self.assertLessEqual(hi[0] - lo[0], 2 * (12 * math.sqrt(max(lam, 1.0)) + 60) + 2)
                outside = float(special.pdtrc(hi[0], lam) + (special.pdtr(lo[0] - 1, lam) if lo[0] > 0 else 0.0))
                ln_s = response.log_no_hit(numpy.array([value]))[0][0]
                bound = math.log(8.04) - value + lam + (math.log(outside) if outside > 0 else -math.inf)
                self.assertLess(bound - ln_s, math.log(1e-17))

    def test_no_hit_brute_force_at_large_m(self):
        response = charge_response.ChargeResponse(THRESHOLD, PHOTON_CHARGE_MEAN, PHOTON_CHARGE_SIGMA)
        for value in (5000.0, 1e5):
            with self.subTest(m=value):
                got = response.log_no_hit(numpy.array([value]))[0][0]
                self.assertAlmostEqual(got, text_ln_no_hit(value), delta=1e-10 * abs(got))


class ConvergenceRule(unittest.TestCase):
    """Review F4: amendment 1's rule is guarded: a SciPy status outside {0, 2} is not converged, and a round that stops 0.05
    sigma from the maximum with status 2 is not converged (its decrement exceeds the tolerance)."""

    @classmethod
    def setUpClass(cls):
        state, charge, _ = noise_free_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0)
        cls.ev = event_from(state, charge)
        cls.best = fit.fit_event(MODEL, cls.ev)

    def mocked(self, status, offset):
        from scipy.optimize import OptimizeResult
        best = self.best
        x = numpy.r_[best.vertex + numpy.array([offset, 0.0, 0.0]), 0.0, 0.0, best.e_vis]
        start = fit.Seed(best.vertex, best.direction, best.e_vis)
        result = OptimizeResult(x=x, status=status, success=status == 0, nit=3, fun=0.0, message="mocked")
        with unittest.mock.patch.object(fit.optimize, "minimize", return_value=result):
            return fit.fit_event(MODEL, self.ev, start=start)

    def test_status_three_is_not_converged(self):
        self.assertEqual(self.best.status, "converged")
        res = self.mocked(3, 0.0)
        self.assertEqual((res.status, res.failure), ("failed", "not-converged"))

    def test_status_two_short_of_the_maximum_is_not_converged(self):
        sigma_x = math.sqrt(self.best.covariance[0, 0])
        res = self.mocked(2, 0.05 * sigma_x)
        self.assertEqual((res.status, res.failure), ("failed", "not-converged"))
        self.assertGreater(res.newton_decrement, 1e3 * fit.DECREMENT_TOL)
        res = self.mocked(2, 0.0)
        self.assertEqual(res.status, "converged")


def run_main(module, argv):
    out = io.StringIO()
    with unittest.mock.patch("sys.stdout", out):
        code = module.main(argv)
    return code, json.loads(out.getvalue())


class ExitCodes(unittest.TestCase):
    """Review F2, fix round 2: the codes are core/status.py's. Exit 1 is the probability-sum stop only, with its record in the
    JSON; an unexpected exception prints status error and exits exit_code("error") = 2, with no product and no partial file;
    the product reader raises ProductError only."""

    @classmethod
    def setUpClass(cls):
        import importlib.util as loader
        spec = loader.spec_from_file_location("photon_likelihood_cli", ASSETS / "photon_likelihood.py")
        cls.cli = loader.module_from_spec(spec)
        spec.loader.exec_module(cls.cli)

    def readout_path(self, folder):
        state, charge, _ = noise_free_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0)
        path = Path(folder) / "r.readout"
        path.write_bytes(readout_file(numpy.array([state]), numpy.array([charge])))
        return path

    def test_codes_are_core_status(self):
        from core.status import exit_code
        self.assertEqual((exit_code("failed"), exit_code("rejected"), exit_code("error"), exit_code("missing-dependency")), (1, 2, 2, 3))

    def test_an_exception_in_the_fit_is_error_exit_2_and_leaves_no_product(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "p.jsonl"
            with unittest.mock.patch.object(fit, "fit_event", side_effect=RuntimeError("planted")):
                code, out = run_main(self.cli, ["fit", "--readout", str(self.readout_path(folder)), "--product", str(target),
                                                "--product-id", "x"])
            self.assertEqual((code, out["status"], out["exit_code"]), (2, "error", 2))
            self.assertIn("planted", out["reason"])
            self.assertNotIn("probability_failures", out)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(folder).glob("*.partial")), [])

    def test_an_exception_in_check_product_is_error_exit_2(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "p.jsonl"
            code, _ = run_main(self.cli, ["fit", "--readout", str(self.readout_path(folder)), "--product", str(target), "--product-id", "x"])
            self.assertEqual(code, 0)
            with unittest.mock.patch.object(product, "read_product", side_effect=RuntimeError("planted")):
                code, out = run_main(self.cli, ["check-product", "--product", str(target)])
            self.assertEqual((code, out["status"]), (2, "error"))

    def test_an_exception_outside_the_fit_loop_is_error_exit_2(self):
        """An exception the operations do not classify (here, building the model) is still status error, exit 2, never 1."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "p.jsonl"
            with unittest.mock.patch.object(likelihood, "Model", side_effect=RuntimeError("planted")):
                code, out = run_main(self.cli, ["fit", "--readout", str(self.readout_path(folder)), "--product", str(target),
                                                "--product-id", "x"])
            self.assertEqual((code, out["status"]), (2, "error"))
            self.assertFalse(target.exists())

    def test_rejected_input_is_rejected_exit_2(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out = run_main(self.cli, ["fit", "--readout", str(Path(folder) / "none.readout"), "--product",
                                            str(Path(folder) / "p.jsonl"), "--product-id", "x"])
            self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_the_stop_is_exit_1_with_its_record_and_the_product(self):
        """A planted per-channel failure (the check reports one failing channel): exit 1, status failed, probability_failures
        above 0, the product written and recording it; check-product then also exits 1 with the record."""
        real = product.probability_check

        def one_failure(*args, **kwargs):
            out = real(*args, **kwargs)
            return {**out, "failures": 1, "failed_channels": [0]}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "p.jsonl"
            with unittest.mock.patch.object(product, "probability_check", side_effect=one_failure):
                code, out = run_main(self.cli, ["fit", "--readout", str(self.readout_path(folder)), "--product", str(target),
                                                "--product-id", "x"])
            self.assertEqual((code, out["status"], out["probability_failures"]), (1, "failed", 1))
            self.assertTrue(target.exists())
            self.assertEqual(json.loads(target.read_text().splitlines()[1])["probability_check"]["failures"], 1)
            with unittest.mock.patch.object(product, "probability_check", side_effect=one_failure):
                code, out = run_main(self.cli, ["check-product", "--product", str(target)])
            self.assertEqual((code, out["status"], out["probability_failures"]), (1, "failed", 1))

    def test_reader_raises_product_error_only(self):
        state, charge, _ = noise_free_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0)
        rd = readout.read_bytes(readout_file(numpy.array([state]), numpy.array([charge])))
        ev = likelihood.EventData.from_readout(rd, 0)
        res = fit.fit_event(MODEL, ev)
        buf = io.StringIO()
        writer = product.Writer(buf, product.header_document("x", rd, CFG))
        doc = product.event_document(0, ev, fit.seed(MODEL, ev), res, product.check_at(MODEL, ev, fit.seed(MODEL, ev), res))
        doc = copy.deepcopy(doc)
        doc["fit"]["vertex"] = [6.0, 0.0, 0.0]          # outside the sphere: the recomputation would have no mean count
        writer.event(doc)
        writer.finish()
        with self.assertRaisesRegex(product.ProductError, "outside the fit's domain"):
            product.read_text(buf.getvalue(), MODEL, CFG)


class Cost(unittest.TestCase):
    def test_cost_on_hand_made_events(self):
        rows = []
        for vertex, direction, n_exp in ((((0.5, 1.0, -0.8), unit((1, 1, 0)), 40.0)), (((2.5, -1.0, 2.5), unit((0, -1, 1)), 300.0)),
                                         (((-3.0, 2.0, -2.0), unit((1, 0, 0.3)), 1500.0))):
            state, charge, _ = noise_free_event(vertex, direction, n_exp)
            ev = event_from(state, charge)
            started = time.perf_counter()
            res = fit.fit_event(MODEL, ev)
            rows.append((n_exp, time.perf_counter() - started, res.status, res.iterations))
        print("\nCOST " + "; ".join(f"N_exp {n:.0f}: {s * 1e3:.0f} ms, {st}, {it} iterations" for n, s, st, it in rows), file=sys.stderr)
        self.assertTrue(all(st == "converged" for _, _, st, _ in rows), rows)


if __name__ == "__main__":
    unittest.main()
