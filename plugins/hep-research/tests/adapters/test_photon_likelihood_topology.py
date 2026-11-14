"""adapters/photon-likelihood, D3 stage 4 of T09 (t07-t09-task-sheets.md, T09: steps "... then topology"; acceptance "mirrored
vertices and reversed tracks; two simultaneous events", "A hypothesis with more parameters is not preferred for a higher raw
likelihood alone", "No data-side truth (A09)"): the two-source hypothesis H2 on the joint likelihood with both sources' light
summed per channel, its data-side starts and budget, the topology choice of t04-values-v4.md section 7 ("H2 is chosen if and
only if 2(lnL_2 - lnL_1) >= 30"), the product light-likelihood-product/4, the two-source control's files, the scoring-side
readings (mis-ID, mirrored, reversed, D_bar), and the stage 3 re-review nits N-A and N-B. Hand-made events only: no fixture
event and no Monte Carlo of the frozen generator.

Expectations come from a second coding in this module (the two-source arrival terms by the order statistic, the shapes, the
start rules, the definitions of section 7) or from the stated rule, never from the recipe's output. Stage 1's to 3's modules are
unchanged; their helpers are reused by import.
Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood_topology -v
"""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy

from tests.adapters import test_photon_likelihood as stage1
from tests.adapters import test_photon_likelihood_time as stage2
from tests.adapters import test_photon_likelihood_multistart as stage3

ROOT, ASSETS = stage1.ROOT, stage1.ASSETS
from light_recipe import configuration, fit, joint, likelihood, multistart, product, readout, topology  # noqa: E402
import t09_fixture_files  # noqa: E402
import t09_job_lines  # noqa: E402
import t09_topology_readings  # noqa: E402
import t09_truth_start  # noqa: E402

CFG, MODEL = stage1.CFG, stage1.MODEL
POSITIONS, NORMALS, unit = stage1.POSITIONS, stage1.NORMALS, stage1.unit
SENSORS, SPEED, DARK, SIGMA_T, WINDOW = stage1.SENSORS, stage1.SPEED, stage1.DARK, stage2.SIGMA_T, stage2.WINDOW
RATE, NEG_INF = stage2.RATE, stage2.NEG_INF
THRESHOLD, R_S = stage1.THRESHOLD, stage1.R_S
BUDGET_FILE = ASSETS / "t09-topology-2.budget.json"
START_NAMES = ("h1 + residual", "h1 + residual, reversed", "h1 + residual, mirrored", "h1 + residual, turned",
               "h1 + largest residual", "h1 + mirrored h1", "charge split", "charge split, reversed")
H1_ANCHORED = START_NAMES[:6]
log_pois, lse, log_upper, logadd = stage1.log_pois, stage1.lse, stage1.log_upper, stage2.logadd


# --- a second coding: two sources in one channel, the order statistic, from the text ---------------------------------------

def text_arrival2(t, sources):
    """(ln f(t), ln (1 - F(t)), m) of one channel with sources [(mu_j, tau_j)]: each Gaussian SIGMA_T about tau_j, dark DARK
    uniform on [0, WINDOW)."""
    m = sum(mu for mu, _ in sources) + DARK
    ln_rate = math.log(RATE) if 0.0 <= t < WINDOW else NEG_INF
    dark_after = DARK * (1.0 - min(max(t, 0.0), WINDOW) / WINDOW)
    ln_after = math.log(dark_after) if dark_after > 0 else NEG_INF
    for mu, tau in sources:
        z = (t - tau) / SIGMA_T
        ln_rate = logadd(ln_rate, math.log(mu) - 0.5 * z * z - math.log(SIGMA_T * math.sqrt(2 * math.pi)))
        ln_after = logadd(ln_after, math.log(mu) + log_upper(z))
    return ln_rate - math.log(m), ln_after - math.log(m), m


def text_ln_joint2(t, sources, q=None, level=None):
    """ln p(q, t, hit) or ln P(q >= level, t) by the sum over the photon count n of Pois(n; m) w_n n f (1 - F)^(n - 1)."""
    ln_f, ln_s, m = text_arrival2(t, sources)
    top = max(m, q if q is not None else level)
    terms = [log_pois(n, m) + stage2.charge_weight(n, q, level) + math.log(n) + ln_f + (n - 1) * ln_s
             for n in range(1, int(top + 40 * math.sqrt(max(top, 1.0)) + 100))]
    return lse(terms)


def text_median_first_arrival2(sources):
    """The median first arrival given at least one photon, two sources: Lambda_<(t) = -ln(1 - (1 - e^-m)/2), by bisection."""
    m = sum(mu for mu, _ in sources) + DARK
    target = -math.log(1.0 - 0.5 * (1.0 - math.exp(-m)))
    lo, hi = min(tau for _, tau in sources) - 60.0, max(tau for _, tau in sources) + 400.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        before = RATE * min(max(mid, 0.0), WINDOW) + sum(mu * 0.5 * math.erfc(-(mid - tau) / (SIGMA_T * math.sqrt(2))) for mu, tau in sources)
        lo, hi = (mid, hi) if before < target else (lo, mid)
    return 0.5 * (lo + hi)


def text_shape_mu(vertex, direction, n_exp):
    shape = stage1.text_shape(POSITIONS, NORMALS, tuple(vertex), tuple(direction))
    total = sum(shape)
    return [n_exp * s / total for s in shape], n_exp / (SENSORS * total)


def times_of(t0):
    """One emission time per source: a number (both sources) or a pair."""
    return (float(t0), float(t0)) if isinstance(t0, (int, float)) else tuple(float(x) for x in t0)


def noise_free_two_source_event(sources, t0):
    """Charges at their means m_i = mu_1i + mu_2i + dark (hit at m_i >= T), times at the two-source median first arrival.
    sources: [(vertex, direction, n_exp)]; t0 one time or one per source. Returns the timed event and the truth e_vis per source."""
    t0s = times_of(t0)
    mus, e_vis, delays = [], [], []
    for vertex, direction, n_exp in sources:
        mu, e = text_shape_mu(vertex, direction, n_exp)
        mus.append(mu)
        e_vis.append(e)
        delays.append(stage2.delays(vertex))
    state = numpy.zeros(SENSORS, numpy.int8)
    charge = numpy.zeros(SENSORS)
    times = numpy.full(SENSORS, numpy.nan)
    for i in range(SENSORS):
        m = sum(mu[i] for mu in mus) + DARK
        if m >= THRESHOLD:
            state[i], charge[i] = readout.LIVE_HIT, m
            times[i] = text_median_first_arrival2([(mu[i], t + d[i]) for mu, d, t in zip(mus, delays, t0s)])
    return stage2.timed(state, charge, times), e_vis


def noisy_two_source_event(rng, sources, t0):
    """A noisy two-source event of this module's coding of section 4.3: per source Poisson photons with Gaussian times, dark
    counts once, summed Gaussian(1, 0.3) charges, first arrival, hit at 0.25 (the generator's _readout, by the text)."""
    t0s = times_of(t0)
    mus, delays = [], []
    for vertex, direction, n_exp in sources:
        mus.append(text_shape_mu(vertex, direction, n_exp)[0])
        delays.append(stage2.delays(vertex))
    state = numpy.zeros(SENSORS, numpy.int8)
    charge = numpy.zeros(SENSORS)
    times = numpy.full(SENSORS, numpy.nan)
    for i in range(SENSORS):
        arrivals = []
        for mu, d, t in zip(mus, delays, t0s):
            arrivals += list(t + d[i] + SIGMA_T * rng.standard_normal(rng.poisson(mu[i])))
        arrivals += list(rng.uniform(0.0, WINDOW, rng.poisson(DARK)))
        q = float(rng.normal(1.0, 0.3, len(arrivals)).sum()) if arrivals else 0.0
        if q >= THRESHOLD:
            state[i], charge[i], times[i] = readout.LIVE_HIT, q, min(arrivals)
    return stage2.timed(state, charge, times)


def point_of(sources, e_vis, t0):
    return topology.Point(numpy.array([s[0] for s in sources], float), numpy.array([s[1] for s in sources], float),
                          numpy.array(e_vis, float), numpy.array(times_of(t0), float))


def h1_result(vertex, direction, e_vis, t0, ln_l, status="converged"):
    return fit.FitResult(status, None if status == "converged" else "not-converged", numpy.asarray(vertex, float),
                         numpy.asarray(direction, float), float(e_vis), None, "not-formed", ln_l, None, None, 0, 0, None, None, float(t0))


SEPARATED = [((-1.6, 0.4, 0.3), unit((0.2, 1.0, -0.3)), 10000.0), ((1.6, -0.3, -0.5), unit((-0.4, -0.2, 1.0)), 10000.0)]
SEPARATED_T0 = (15.0, 21.0)          # each source its own time (rebuild, case R-h2-parameters)


# --- the budget and the penalty ---------------------------------------------------------------------------------------------

class TopologyBudget(unittest.TestCase):
    def test_shipped_budget(self):
        b = topology.load()
        self.assertEqual(tuple(b.starts), START_NAMES)
        self.assertEqual(b.tie_tolerance, 1e-6)
        self.assertEqual(b.format, "light-likelihood-topology/1")
        self.assertEqual(b.sha256, hashlib.sha256(BUDGET_FILE.read_bytes()).hexdigest())
        self.assertEqual(Path(topology.DEFAULT).resolve(), BUDGET_FILE.resolve())

    def test_refusals(self):
        good = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        cases = {"unknown key": {**good, "penalty": 30}, "missing key": {k: v for k, v in good.items() if k != "tie_tolerance"},
                 "unknown start": {**good, "starts": good["starts"] + ["random"]},
                 "repeated start": {**good, "starts": good["starts"] + ["charge split"]}, "no starts": {**good, "starts": []},
                 "tie zero": {**good, "tie_tolerance": 0.0}, "tie text": {**good, "tie_tolerance": "1e-6"},
                 "tie boolean": {**good, "tie_tolerance": True}, "other format": {**good, "format": "light-likelihood-topology/2"},
                 "starts not a list": {**good, "starts": "charge split"}}
        with tempfile.TemporaryDirectory() as folder:
            for name, doc in cases.items():
                with self.subTest(defect=name):
                    path = Path(folder) / "b.json"
                    path.write_text(json.dumps(doc))
                    with self.assertRaises(topology.BudgetError):
                        topology.load(path)
            (Path(folder) / "nan.json").write_text('{"format": "light-likelihood-topology/1", "starts": ["charge split"], "tie_tolerance": NaN}')
            with self.assertRaises(topology.BudgetError):
                topology.load(Path(folder) / "nan.json")
            with self.assertRaises(topology.BudgetError):
                topology.load(Path(folder) / "missing.json")

    def test_penalty_is_v4s_frozen_constant(self):
        self.assertEqual(topology.PENALTY, 30.0)
        source = (ASSETS / "light_recipe" / "topology.py").read_text(encoding="utf-8")
        line = [x for x in source.splitlines() if x.startswith("PENALTY = ")]
        self.assertEqual(len(line), 1, line)
        self.assertIn("t04-values-v4.md section 7", line[0])
        self.assertNotIn("penalty", json.loads(BUDGET_FILE.read_text()))


# --- the choice rule ------------------------------------------------------------------------------------------------------

class ChoiceRule(unittest.TestCase):
    def test_at_the_threshold(self):
        ln_l1 = -1000.0
        for stat, want in ((29.99, "H1"), (30.0, "H2"), (30.01, "H2"), (0.0, "H1"), (1e6, "H2")):
            with self.subTest(statistic=stat):
                ln_l2, source, s = topology.statistic(ln_l1, ln_l1 + stat / 2)
                self.assertEqual((ln_l2, source, s), (ln_l1 + stat / 2, "h2", 2 * (ln_l1 + stat / 2 - ln_l1)))
                self.assertEqual(topology.choose(s), want)
        self.assertEqual(topology.choose(29.999999999), "H1")
        self.assertEqual(topology.choose(30.0), "H2")

    def test_h1_boundary(self):
        self.assertEqual(topology.statistic(-500.0, -500.5), (-500.0, "h1 boundary", 0.0))
        self.assertEqual(topology.statistic(-500.0, None), (-500.0, "h1 boundary", 0.0))
        self.assertEqual(topology.choose(0.0), "H1")

    def test_a_higher_raw_likelihood_alone_does_not_choose_h2(self):
        """H2 has 6 more coordinates; a higher raw ln L (here 14.9 above H1's) is not enough (the sheet; v4 section 7)."""
        ln_l2, source, s = topology.statistic(-800.0, -785.1)
        self.assertGreater(ln_l2, -800.0)
        self.assertEqual(topology.choose(s), "H1")

    def test_reported_h2_point(self):
        r = topology.report_choice
        self.assertEqual(r([-10.0, -5.0], 1e-6), (1, topology.REPORT_BEST))
        self.assertEqual(r([None, -5.0], 1e-6), (1, topology.REPORT_BEST))
        self.assertEqual(r([-5.0, -5.0 - 1e-6], 1e-6), (0, topology.REPORT_TIE))
        self.assertEqual(r([-5.0 - 1e-6, -5.0], 1e-6), (0, topology.REPORT_TIE))
        self.assertEqual(r([-5.0 - 2e-6, -5.0], 1e-6), (1, topology.REPORT_BEST))
        self.assertEqual(r([None, None], 1e-6), (None, topology.REPORT_NONE))
        self.assertEqual(r([], 1e-6), (None, topology.REPORT_NONE))


# --- the per-channel terms ------------------------------------------------------------------------------------------------

class ChannelTerms(unittest.TestCase):
    def two(self, rows, mu1, tau1, mu2, tau2):
        state = numpy.array([r[0] for r in rows], numpy.int8)
        charge = numpy.array([r[1] for r in rows], float)
        times = numpy.array([r[2] for r in rows], float)
        sat = numpy.array([r[3] for r in rows], bool)
        normals, positions = stage1.six_sensor_geometry()
        model = likelihood.Model(CFG, configuration.Geometry(numpy.array(positions, float), numpy.array(normals, float), stage1.AREA))
        ev = likelihood.EventData(state, charge, sat, 5.0, THRESHOLD)
        tev = joint.TimedEvent(ev, times)
        mu = numpy.array([mu1, mu2], float)
        tau = numpy.array([tau1, tau2], float)
        return model, tev, topology.channel_terms(model, tev, mu, tau)

    ROWS = [(readout.LIVE_HIT, 2.3, 41.0, False), (readout.LIVE_HIT, 5.0, 37.5, True), (readout.LIVE_UNHIT, 0.0, numpy.nan, False),
            (readout.LIVE_HIT, 0.9, 150.0, False), (readout.DEAD, numpy.nan, numpy.nan, False), (readout.LIVE_HIT, 4.2, 39.0, False)]

    def test_a_vanishing_second_source_is_stage_twos_terms(self):
        mu1, tau1 = [1.7, 6.0, 0.4, 0.05, 1.0, 9.0], [40.0, 38.0, 41.0, 39.0, 40.0, 38.5]
        model, tev, (l, g, h) = self.two(self.ROWS, mu1, tau1, [1e-300] * 6, [80.0] * 6)
        want = joint.channel_terms(model, tev, numpy.array(mu1), numpy.array(tau1))
        live = [0, 1, 2, 3, 5]
        for k, (got, expect) in enumerate(((l, want[0]), (g[:, 0], want[1]), (g[:, 1], want[2]), (h[:, 0, 0], want[3]),
                                           (h[:, 0, 1], want[4]), (h[:, 1, 1], want[5]))):
            with self.subTest(term=k):
                numpy.testing.assert_allclose(got[live], expect[live], rtol=1e-12, atol=1e-300)
        self.assertEqual(float(l[4]), 0.0)
        self.assertTrue(numpy.all(g[4] == 0.0) and numpy.all(h[4] == 0.0))

    def test_against_the_order_statistic(self):
        mu1, tau1, mu2, tau2 = [1.7, 6.0, 0.4, 0.05, 1.0, 9.0], [40.0, 38.0, 41.0, 39.0, 40.0, 38.5], \
            [0.8, 2.5, 0.3, 0.02, 1.0, 4.0], [43.0, 36.5, 39.0, 47.0, 40.0, 41.0]
        model, tev, (l, _, _) = self.two(self.ROWS, mu1, tau1, mu2, tau2)
        for i, (state, q, t, sat) in enumerate(self.ROWS):
            with self.subTest(channel=i):
                sources = [(mu1[i], tau1[i]), (mu2[i], tau2[i])]
                if state == readout.LIVE_UNHIT:
                    want = stage1.text_ln_no_hit(mu1[i] + mu2[i] + DARK)
                elif state == readout.DEAD:
                    want = 0.0
                elif sat:
                    want = text_ln_joint2(t, sources, level=5.0)
                else:
                    want = text_ln_joint2(t, sources, q=q)
                self.assertAlmostEqual(float(l[i]), want, delta=1e-10 * max(1.0, abs(want)))

    def test_derivatives_in_the_channel_variables(self):
        mu1, tau1, mu2, tau2 = [1.7, 6.0, 0.4, 0.05, 1.0, 9.0], [40.0, 38.0, 41.0, 39.0, 40.0, 38.5], \
            [0.8, 2.5, 0.3, 0.02, 1.0, 4.0], [43.0, 36.5, 39.0, 47.0, 40.0, 41.0]
        base = numpy.array([mu1, tau1, mu2, tau2], float)
        model, tev, (l, g, h) = self.two(self.ROWS, *base)
        steps = (1e-6, 1e-5, 1e-6, 1e-5)
        for k in range(4):
            up, down = base.copy(), base.copy()
            up[k] *= 1 + steps[k]
            down[k] *= 1 - steps[k]
            hk = base[k] * steps[k]
            _, _, (lu, gu, _) = self.two(self.ROWS, *up)
            _, _, (ld, gd, _) = self.two(self.ROWS, *down)
            for i in (0, 1, 2, 3, 5):
                with self.subTest(variable=k, channel=i):
                    num = (lu[i] - ld[i]) / (2 * hk[i])
                    self.assertAlmostEqual(float(g[i, k]), float(num), delta=1e-5 * max(1.0, abs(num)))
                    num2 = (gu[i] - gd[i]) / (2 * hk[i])
                    scale = max(1.0, float(numpy.abs(h[i]).max()))
                    numpy.testing.assert_allclose(h[i, :, k], num2, atol=1e-5 * scale)


class ObjectiveInFitCoordinates(unittest.TestCase):
    def test_gradient_and_hessian_against_differences(self):
        rng = numpy.random.default_rng([20261111, 400])
        sources = [((-1.2, 0.5, 0.4), unit((0.3, 1.0, -0.2)), 300.0), ((1.4, -0.6, -0.3), unit((-0.5, -0.1, 1.0)), 250.0)]
        tev = noisy_two_source_event(rng, sources, 20.0)
        d_refs = [numpy.array(s[1]) for s in sources]
        objective = topology.Objective(MODEL, tev, d_refs)
        e_vis = [text_shape_mu(s[0], s[1], s[2])[1] for s in sources]
        p = numpy.r_[sources[0][0], 0.02, -0.01, e_vis[0], 20.3, sources[1][0], -0.015, 0.01, e_vis[1], 19.6]
        value, grad, hess = objective.derivatives(p)
        self.assertAlmostEqual(value, objective.value(p), delta=1e-9 * abs(value))
        self.assertEqual(topology.SIZE, 14)
        self.assertEqual((grad.shape, hess.shape), ((14,), (14, 14)))
        steps = numpy.array([1e-5] * 3 + [1e-6] * 2 + [1e-6 * e_vis[0]] + [1e-5] + [1e-5] * 3 + [1e-6] * 2 + [1e-6 * e_vis[1]] + [1e-5])
        for k in range(14):
            e = numpy.zeros(14)
            e[k] = steps[k]
            with self.subTest(coordinate=k):
                num = (objective.value(p + e) - objective.value(p - e)) / (2 * steps[k])
                self.assertAlmostEqual(float(grad[k]), float(num), delta=1e-4 * max(1.0, float(numpy.abs(grad).max())))
                num2 = (objective.derivatives(p + e)[1] - objective.derivatives(p - e)[1]) / (2 * steps[k])
                numpy.testing.assert_allclose(hess[:, k], num2, atol=1e-4 * float(numpy.abs(hess).max()))
        point = objective.point_of(p)
        self.assertAlmostEqual(topology.log_likelihood(MODEL, tev, point), value, delta=1e-9 * abs(value))
        self.assertEqual(tuple(point.t0), (20.3, 19.6))

    def test_each_source_has_its_own_time(self):
        """14 parameters (case R-h2-parameters): ln L reads t0_2 apart from t0_1, through tau_2 = t0_2 + d_2 / v only."""
        rng = numpy.random.default_rng([20261111, 402])
        sources = [((-1.2, 0.5, 0.4), unit((0.3, 1.0, -0.2)), 300.0), ((1.4, -0.6, -0.3), unit((-0.5, -0.1, 1.0)), 250.0)]
        tev = noisy_two_source_event(rng, sources, (18.0, 24.0))
        e_vis = [text_shape_mu(s[0], s[1], s[2])[1] for s in sources]
        base = point_of(sources, e_vis, (18.0, 24.0))
        moved = point_of(sources, e_vis, (18.0, 25.0))
        a, b = topology.log_likelihood(MODEL, tev, base), topology.log_likelihood(MODEL, tev, moved)
        self.assertNotEqual(a, b)
        mu = topology.signal_means(MODEL, moved)
        tau = numpy.array([18.0 + numpy.array(stage2.delays(sources[0][0])), 25.0 + numpy.array(stage2.delays(sources[1][0]))])
        self.assertAlmostEqual(b, float(topology.channel_terms(MODEL, tev, mu, tau)[0].sum()), delta=1e-9 * abs(b))
        same = point_of(sources, e_vis, (18.0, 18.0))
        self.assertNotEqual(topology.log_likelihood(MODEL, tev, same), a)

    def test_outside_the_domain(self):
        tev, e_vis = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        objective = topology.Objective(MODEL, tev, [numpy.array(s[1]) for s in SEPARATED])
        good = numpy.r_[SEPARATED[0][0], 0, 0, e_vis[0], SEPARATED_T0[0], SEPARATED[1][0], 0, 0, e_vis[1], SEPARATED_T0[1]]
        self.assertTrue(math.isfinite(objective.value(good)))
        for name, k, value in (("vertex 2 outside", 7, 4.999), ("E_2 zero", 12, 0.0), ("E_1 negative", 5, -1e-3), ("t0_1 early", 6, -250.0),
                               ("t0_2 late", 13, 450.0)):
            with self.subTest(case=name):
                p = good.copy()
                p[k] = value
                self.assertEqual(objective.value(p), -math.inf)
                v, g, h = objective.derivatives(p)
                self.assertEqual(v, -math.inf)
                self.assertTrue(numpy.array_equal(g, numpy.zeros(14)) and numpy.array_equal(h, -numpy.eye(14)))


class ProbabilityCheckOnTwoSources(unittest.TestCase):
    def test_the_check_reads_both_sources_means(self):
        tev, e_vis = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        point = point_of(SEPARATED, e_vis, SEPARATED_T0)
        m1 = numpy.array(stage1.text_mean(POSITIONS, NORMALS, SEPARATED[0][0], SEPARATED[0][1], e_vis[0]))
        m2 = numpy.array(stage1.text_mean(POSITIONS, NORMALS, SEPARATED[1][0], SEPARATED[1][1], e_vis[1]))
        numpy.testing.assert_allclose(topology.expected_counts(MODEL, point), m1 + m2 - DARK, rtol=1e-12)
        check = topology.probability_check(MODEL, tev.event, point)
        self.assertEqual((check["channels"], check["failures"]), (SENSORS, 0))
        one = likelihood.probability_check(MODEL, tev.event, point.vertices[0], point.directions[0], point.e_vis[0])
        self.assertEqual(set(check), set(one))
        # the check's numbers are those of the summed means, not of one source's
        m = topology.expected_counts(MODEL, point)
        p_hit, p_no = MODEL.response.probability_sums(m)
        deviation = numpy.abs(p_hit + p_no - 1.0)
        self.assertEqual(check["max_abs_deviation"], float(deviation.max()))
        self.assertEqual(check["largest_ratio"], float((deviation / likelihood.sum_tolerance(m)).max()))


# --- the starts -------------------------------------------------------------------------------------------------------------

def moment_point(ev, weights):
    """Stage 1's moment rule on weights, by the text: (vertex 0.5 x the weighted centroid, the weighted direction) or None."""
    total = sum(weights)
    if total <= 0:
        return None
    c = [sum(w * POSITIONS[i][k] for i, w in enumerate(weights)) / total for k in range(3)]
    x = [0.5 * ck for ck in c]
    pull = [0.0, 0.0, 0.0]
    for i, w in enumerate(weights):
        if w:
            d = math.dist(POSITIONS[i], x)
            for k in range(3):
                pull[k] += w * (POSITIONS[i][k] - x[k]) / d
    norm = math.sqrt(sum(p * p for p in pull))
    if norm == 0:
        return None
    return x, [p / norm for p in pull]


def e_at(ev, weights, x, d):
    """E(w; x, d) = sum w / (1000 sum_live s_i(x, d))."""
    shape = stage1.text_shape(POSITIONS, NORMALS, tuple(x), tuple(d))
    return sum(weights) / (SENSORS * sum(shape[i] for i in range(SENSORS) if ev.live[i]))


def t_median(tev, x, weights):
    """T(x; S): the median over channels with weight above 0 of t_i - |P_i - x| / v."""
    values = sorted(float(tev.time[i]) - math.dist(POSITIONS[i], tuple(x)) / SPEED for i in range(SENSORS) if weights[i] > 0)
    n = len(values)
    return values[n // 2] if n % 2 else 0.5 * (values[n // 2 - 1] + values[n // 2])


def hand_starts(tev, h1):
    """The 8 starts of case R-h2-starts, by the text: [(name, ((x1, d1, E1, t1), (x2, d2, E2, t2)) or None)]."""
    ev = tev.event
    m = stage1.text_mean(POSITIONS, NORMALS, tuple(h1.vertex), tuple(h1.direction), h1.e_vis)
    r = [max(float(ev.charge[i]) - m[i], 0.0) if ev.hit[i] else 0.0 for i in range(SENSORS)]
    one = (list(h1.vertex), list(h1.direction), h1.e_vis, h1.t0)
    neg = lambda v: [-c for c in v]  # noqa: E731
    out = []
    base = moment_point(ev, r)

    def second(x, d, t=None):
        return (x, d, e_at(ev, r, x, d), t_median(tev, x, r) if t is None else t)
    if base is None:
        out += [(name, None) for name in START_NAMES[:6]]
    else:
        x2, d2 = base
        out.append((START_NAMES[0], (one, second(x2, d2))))
        out.append((START_NAMES[1], (one, second(x2, neg(d2)))))
        out.append((START_NAMES[2], (one, second(neg(x2), neg(d2)))))
        out.append((START_NAMES[3], (one, second(x2, list(stage1.frame_text(tuple(d2))[0])))))
        k = max(range(SENSORS), key=lambda i: (r[i], -i))
        xk = [0.5 * c for c in POSITIONS[k]]
        dk = [c / R_S for c in POSITIONS[k]]
        out.append((START_NAMES[4], (one, second(xk, dk, float(tev.time[k]) - math.dist(POSITIONS[k], xk) / SPEED))))
        out.append((START_NAMES[5], (one, second(neg(list(h1.vertex)), neg(list(h1.direction))))))
    q = [float(ev.charge[i]) if ev.hit[i] else 0.0 for i in range(SENSORS)]
    total = sum(q)
    c = numpy.array([sum(q[i] * POSITIONS[i][k] for i in range(SENSORS)) / total for k in range(3)])
    scatter = sum(q[i] * numpy.outer(numpy.array(POSITIONS[i]) - c, numpy.array(POSITIONS[i]) - c) for i in range(SENSORS) if q[i])
    axis = numpy.linalg.eigh(scatter)[1][:, -1]
    axis = axis if axis[int(numpy.argmax(numpy.abs(axis)))] > 0 else -axis
    side = [float((numpy.array(POSITIONS[i]) - c) @ axis) for i in range(SENSORS)]
    halves = [[q[i] if side[i] >= 0 else 0.0 for i in range(SENSORS)], [q[i] if side[i] < 0 else 0.0 for i in range(SENSORS)]]
    points = [moment_point(ev, h) for h in halves]
    if any(pt is None for pt in points):
        out += [(START_NAMES[6], None), (START_NAMES[7], None)]
    else:
        for name, sign in ((START_NAMES[6], 1), (START_NAMES[7], -1)):
            out.append((name, tuple((x, [sign * v for v in d], e_at(ev, h, x, [sign * v for v in d]), t_median(tev, x, h))
                                    for (x, d), h in zip(points, halves))))
    return out


class StartRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = numpy.random.default_rng([20261111, 401])
        cls.tev = noisy_two_source_event(rng, [((-1.0, 0.8, 0.2), unit((0.1, 1.0, 0.0)), 350.0),
                                               ((1.5, -0.4, -0.8), unit((0.0, -0.3, 1.0)), 300.0)], (21.0, 26.0))
        cls.h1 = h1_result((-0.7, 0.6, 0.1), unit((0.1, 1.0, 0.1)), 0.9, 21.3, -1500.0)

    def close(self, got, want):
        numpy.testing.assert_allclose(numpy.asarray(got, float), numpy.asarray(want, float), rtol=1e-12, atol=1e-12)

    def test_the_eight_starts_by_hand(self):
        starts = topology.start_points(MODEL, self.tev, topology.load(), self.h1)
        self.assertEqual([name for name, _ in starts], list(START_NAMES))
        for (name, got), (_, want) in zip(starts, hand_starts(self.tev, self.h1)):
            with self.subTest(start=name):
                self.assertIsNotNone(want)
                for j in range(2):
                    x, d, e, t0 = want[j]
                    self.close(got.vertices[j], x)
                    self.close(got.directions[j], d)
                    self.close([got.e_vis[j], got.t0[j]], [e, t0])
                if name in H1_ANCHORED:
                    self.assertEqual((tuple(got.vertices[0]), tuple(got.directions[0]), got.e_vis[0], got.t0[0]),
                                     (tuple(self.h1.vertex), tuple(self.h1.direction), self.h1.e_vis, self.h1.t0))

    def test_the_starts_read_the_data_and_h1_only(self):
        import inspect
        self.assertEqual(list(inspect.signature(topology.start_points).parameters), ["model", "tev", "budget", "h1"])

    def test_a_start_that_cannot_be_formed(self):
        """No positive residual: H1 predicts more than every hit charge."""
        h1 = h1_result((0.0, 0.0, 0.0), unit((0.0, 0.0, 1.0)), 1e3, 21.0, -5000.0)
        starts = dict(topology.start_points(MODEL, self.tev, topology.load(), h1))
        self.assertIsNone(starts["h1 + residual"])
        topo = topology.fit_topology(MODEL, self.tev, topology.load(), h1)
        record = topo.records[0]
        self.assertEqual((record.result.status, record.result.failure, record.result.point), ("failed", topology.NO_START, None))
        for name in H1_ANCHORED:
            self.assertIsNone(starts[name], name)


# --- H2 on noise-free events and the choice ---------------------------------------------------------------------------------

class TwoSeparatedSources(unittest.TestCase):
    def test_h2_recovers_two_separated_noise_free_sources(self):
        tev, e_vis = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        ms = multistart.fit_multistart(MODEL, tev, multistart.load())
        self.assertEqual(ms.result.status, "converged", ms.result.failure)
        topo = topology.fit_topology(MODEL, tev, topology.load(), ms.result)
        res = topo.result
        print(f"\nTWO-SOURCE noise-free: H1 ln L {ms.result.ln_likelihood:.3f}, H2 starts "
              f"{[(r.name, r.result.status, r.result.failure, r.result.ln_likelihood) for r in topo.records]}, statistic "
              f"{topo.statistic:.1f}", file=sys.stderr)
        self.assertEqual(res.status, "converged", res.failure)
        for j, (vertex, direction, _) in enumerate(SEPARATED):
            k = int(numpy.argmin([numpy.linalg.norm(res.point.vertices[i] - numpy.array(vertex)) for i in range(2)]))
            with self.subTest(source=j):
                self.assertLess(numpy.linalg.norm(res.point.vertices[k] - numpy.array(vertex)), 0.05)
                self.assertLess(math.acos(min(1.0, float(res.point.directions[k] @ numpy.array(direction)))), 0.03)
                self.assertLess(abs(res.point.e_vis[k] / e_vis[j] - 1.0), 0.03)
        for j, (vertex, _, _) in enumerate(SEPARATED):
            k = int(numpy.argmin([numpy.linalg.norm(res.point.vertices[i] - numpy.array(vertex)) for i in range(2)]))
            # 0.1 ns was the prediction; 0.146 ns came out (rebuild-green-1.log). The measured reason (review F1, the reviewer's
            # probe 1): the t0 offsets were -0.146 and -0.020 ns at 10,000 photons per source, -0.139 and -0.085 at 20,000, -0.136
            # and -0.112 at 40,000, and at each count the reported point and the truth-started fit are one maximum. The offset comes
            # from the event's construction (times at the median first arrival of two overlapping Gaussians, not an exact maximum),
            # does not shrink with photons, and is no search failure. So 0.2 ns on truth; the tight check is against the
            # truth-started fit, below.
            self.assertLess(abs(res.point.t0[k] - SEPARATED_T0[j]), 0.2, "each source its own time")
        truth_fit = topology.fit_two_source(MODEL, tev, point_of(SEPARATED, e_vis, SEPARATED_T0))
        self.assertEqual(truth_fit.status, "converged", truth_fit.failure)
        self.assertAlmostEqual(res.ln_likelihood, truth_fit.ln_likelihood, delta=1e-6)
        for k in range(2):
            i = int(numpy.argmin([numpy.linalg.norm(truth_fit.point.vertices[m] - res.point.vertices[k]) for m in range(2)]))
            with self.subTest(source=k, against="truth-started fit"):
                self.assertLess(numpy.linalg.norm(res.point.vertices[k] - truth_fit.point.vertices[i]), 1e-5)
                self.assertLess(abs(res.point.t0[k] - truth_fit.point.t0[i]), 1e-4)
        self.assertEqual(res.covariance.shape, (14, 14))
        numpy.linalg.cholesky(res.covariance)
        self.assertGreater(topo.statistic, topology.PENALTY)
        self.assertEqual(topo.choice, "H2")
        self.assertEqual(topology.probability_check(MODEL, tev.event, res.point)["failures"], 0)

    def test_one_source_keeps_h1(self):
        state, charge, times, _ = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 300.0, 15.0)
        tev = stage2.timed(state, charge, times)
        ms = multistart.fit_multistart(MODEL, tev, multistart.load())
        topo = topology.fit_topology(MODEL, tev, topology.load(), ms.result)
        self.assertLess(topo.statistic, topology.PENALTY)
        self.assertEqual(topo.choice, "H1")
        self.assertGreaterEqual(topo.ln_likelihood_2, topo.ln_likelihood_1)

    def test_h1_failed_gives_no_choice(self):
        tev, _ = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        failed = h1_result((0.0, 0.0, 0.0), unit((0.0, 0.0, 1.0)), 1.0, 20.0, -1.0, status="failed")
        topo = topology.fit_topology(MODEL, tev, topology.load(), failed)
        self.assertEqual((topo.choice, topo.statistic, topo.records, topo.rule), (None, None, [], topology.CHOICE_H1_FAILED))


# --- product /4 -------------------------------------------------------------------------------------------------------------

def topology_texts(content):
    """(the /3 text, the /4 text) of a hand-made readout, made the recipe's way."""
    text3 = stage3.multistart_product_text(content)
    rd = readout.read_bytes(content)
    h3 = product.read_text(text3, MODEL, CFG, multistart.load())
    buf = io.StringIO()
    tb = topology.load()
    sha3 = hashlib.sha256(text3.encode()).hexdigest()
    writer = product.Writer(buf, product.topology_header_document(h3.header, sha3, "hand-made-4", tb))
    for i, doc in enumerate(h3.events):
        tev = joint.TimedEvent.from_readout(rd, i)
        topo = topology.fit_topology(MODEL, tev, tb, product.fit_result_of(doc["fit"]))
        writer.event(product.topology_event_document(doc, topo, topology.check_at(MODEL, tev.event, topo)))
    writer.finish()
    return text3, buf.getvalue()


class TopologyProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tev, _ = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        a = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        cls.content = stage2.timed_readout([a[:3], (tev.event.state, tev.event.charge, tev.time)])
        cls.text3, cls.text = topology_texts(cls.content)

    def read(self, text, model=MODEL, tb=None):
        return product.read_text(text, model, CFG, multistart.load(), tb or topology.load())

    def test_round_trip_and_the_h1_lines(self):
        read = self.read(self.text)
        self.assertEqual(read.header["format"], "light-likelihood-product/4")
        self.assertEqual(read.header["topology"]["penalty"], 30.0)
        self.assertEqual(read.header["topology"]["sha256"], topology.load().sha256)
        self.assertEqual(read.header["h1_product"]["sha256"], hashlib.sha256(self.text3.encode()).hexdigest())
        again = "".join(product.dumps(d) + "\n" for d in [read.header] + read.events) + product.dumps({"end": read.header["format"],
                                                                                                         "events": len(read.events)}) + "\n"
        self.assertEqual(again, self.text)
        lines3 = self.text3.splitlines()
        for i, doc in enumerate(read.events):
            stripped = {k: v for k, v in doc.items() if k != "topology"}
            self.assertEqual(product.dumps(stripped), lines3[i + 1])
        self.assertEqual([d["topology"]["choice"] for d in read.events], ["H1", "H2"])
        for d in read.events:
            self.assertEqual([s["name"] for s in d["topology"]["h2"]["starts"]], list(START_NAMES), "8 starts recorded")

    def test_refuses_defects(self):
        h, events, end = stage3.lines_of(self.text)

        def plant(fn):
            hh, ee = copy.deepcopy(h), copy.deepcopy(events)
            fn(hh, ee)
            return stage3.build(hh, ee, end)

        def bump_start_ln_l(hh, ee):
            s = [x for x in ee[1]["topology"]["h2"]["starts"] if x["ln_likelihood"] is not None][0]
            s["ln_likelihood"] += 1e-3

        def h2_wrong_choice(hh, ee):
            ee[0]["topology"]["choice"] = "H2"

        def statistic_off(hh, ee):
            ee[1]["topology"]["statistic"] += 1.0

        def ln_l2_off(hh, ee):
            ee[1]["topology"]["ln_likelihood_2"] += 1.0

        def choice_h2_at_29(hh, ee):
            t = ee[0]["topology"]
            t["ln_likelihood_2"] = t["ln_likelihood_1"] + 14.5
            t["statistic"] = 29.0
            t["choice"] = "H2"

        def penalty(hh, ee):
            hh["topology"]["penalty"] = 20.0

        def ln_l1_moved(hh, ee):           # review F2: lnL_1 not H1's, everything after it recomputed to match
            top = ee[1]["topology"]
            top["ln_likelihood_1"] += 1.0
            ln_l2, source, stat = topology.statistic(top["ln_likelihood_1"], top["h2"]["fit"]["ln_likelihood"])
            top.update(ln_likelihood_2=ln_l2, ln_likelihood_2_from=source, statistic=stat, choice=topology.choose(stat))

        def event_penalty(hh, ee):
            ee[1]["topology"]["penalty"] = 20.0

        def budget_hash(hh, ee):
            hh["topology"]["sha256"] = "0" * 64

        def unknown_key(hh, ee):
            ee[0]["topology"]["truth"] = 1

        def start_removed(hh, ee):
            ee[1]["topology"]["h2"]["starts"].pop()

        def starts_swapped(hh, ee):
            s = ee[1]["topology"]["h2"]["starts"]
            s[0], s[1] = s[1], s[0]

        def start_moved(hh, ee):
            s = [x for x in ee[1]["topology"]["h2"]["starts"] if x["start"] is not None][0]
            s["start"]["sources"][1]["t0"] += 0.5

        def split_vertex_moved(hh, ee):     # no structural rule reads it: only the recomputation from H1 and the data
            s = [x for x in ee[1]["topology"]["h2"]["starts"] if x["name"] == "charge split"][0]
            s["start"]["sources"][1]["vertex"][0] += 1e-3

        def reported_index(hh, ee):
            rep = ee[1]["topology"]["h2"]["reported"]
            rep["index"] = 1 - rep["index"]

        def fit_not_reported(hh, ee):
            ee[1]["topology"]["h2"]["fit"]["iterations"] += 1

        def h1_line_changed(hh, ee):
            ee[0]["fit"]["iterations"] += 1

        def check_moved(hh, ee):
            ee[1]["topology"]["probability_check"]["channels"] -= 1

        for name, fn in (("start ln L", bump_start_ln_l), ("choice", h2_wrong_choice), ("statistic", statistic_off),
                         ("ln L 2", ln_l2_off), ("H2 at 29", choice_h2_at_29), ("penalty", penalty), ("event penalty", event_penalty), ("lnL_1 not H1's", ln_l1_moved), ("budget hash", budget_hash),
                         ("unknown key", unknown_key), ("start removed", start_removed), ("starts swapped", starts_swapped),
                         ("start moved", start_moved), ("split start vertex moved", split_vertex_moved), ("reported index", reported_index), ("fit not the reported", fit_not_reported),
                         ("an H1 line changed", h1_line_changed), ("check moved", check_moved)):
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                self.read(plant(fn))

    def test_structure_only_refusals_and_formats(self):
        h, events, end = stage3.lines_of(self.text)
        bad = copy.deepcopy(events)
        bad[0]["topology"]["choice"] = "H2"
        with self.assertRaises(product.ProductError):
            product.read_text(stage3.build(h, bad, end), None, CFG, multistart.load(), topology.load())
        anchored = copy.deepcopy(events)
        anchored[1]["topology"]["h2"]["starts"][3]["start"]["sources"][0]["t0"] += 0.25     # source 1 of an H1-anchored start, not H1's
        with self.assertRaises(product.ProductError):
            product.read_text(stage3.build(h, anchored, end), None, CFG, multistart.load(), topology.load())
        h3, e3, end3 = stage3.lines_of(self.text3)
        e3[0]["topology"] = events[0]["topology"]
        with self.assertRaises(product.ProductError):
            product.read_text(stage3.build(h3, e3, end3), None, CFG, multistart.load())
        other = json.loads(BUDGET_FILE.read_text())
        other["tie_tolerance"] = 2e-6
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "o.json"
            path.write_text(json.dumps(other))
            with self.assertRaises(product.ProductError):
                product.read_text(self.text, None, CFG, multistart.load(), topology.load(path))

    def test_every_field_replaced_gives_product_error_or_acceptance(self):
        """Any replaced leaf of the topology record is refused as a ProductError or accepted, never an internal error."""
        h, events, end = stage3.lines_of(self.text)
        for path in stage2.leaves(events[1]["topology"], ("topology",)):
            for value in (None, "x", -1, 1e300, [], {}):
                with self.subTest(path=path, value=value):
                    ee = copy.deepcopy(events)
                    ee[1] = stage2.replaced(ee[1], path, value)
                    try:
                        product.read_text(stage3.build(h, ee, end), None, CFG, multistart.load(), topology.load())
                    except product.ProductError:
                        pass


# --- the CLI --------------------------------------------------------------------------------------------------------------

class TopologyCommandLine(unittest.TestCase):
    def test_topology_check_and_refusals(self):
        tev, _ = noise_free_two_source_event(SEPARATED, SEPARATED_T0)
        a = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "r.readout").write_bytes(stage2.timed_readout([a[:3], (tev.event.state, tev.event.charge, tev.time)]))
            (folder / "o.readout").write_bytes(stage2.timed_readout([a[:3]]))
            r = str(folder / "r.readout")
            p = stage1.run_cli("fit", "--readout", r, "--product", str(folder / "m.jsonl"), "--product-id", "hm", "--likelihood",
                               "charge-time", "--starts", "multistart")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = stage1.run_cli("fit", "--readout", r, "--product", str(folder / "j.jsonl"), "--product-id", "hm", "--likelihood", "charge-time")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            base = ["topology", "--readout", r, "--h1-product", str(folder / "m.jsonl"), "--product-id", "hm4"]
            p = stage1.run_cli(*base, "--product", str(folder / "t.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual((out["status"], out["events"], out["choices"], out["topology_budget_sha256"], out["penalty"]),
                             ("ok", 2, {"H1": 1, "H2": 1}, topology.load().sha256, 30.0))
            p = stage1.run_cli("check-product", "--product", str(folder / "t.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["format"], "light-likelihood-product/4")
            refusals = {"another readout": ["--readout", str(folder / "o.readout")], "a /2 as H1": ["--h1-product", str(folder / "j.jsonl")],
                        "an existing product": ["--product", str(folder / "t.jsonl")]}
            for name, change in refusals.items():
                with self.subTest(refused=name):
                    args = list(base)
                    if change[0] in args:
                        args[args.index(change[0]) + 1] = change[1]
                        args += ["--product", str(folder / f"{name}.jsonl")]
                    else:
                        args += change
                    p = stage1.run_cli(*args)
                    self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"), p.stdout + p.stderr)
                    self.assertFalse((folder / f"{name}.jsonl").exists())
            (folder / "bad.json").write_text("{}")
            p = stage1.run_cli(*base, "--product", str(folder / "b.jsonl"), "--topology-budget", str(folder / "bad.json"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            other = json.loads(BUDGET_FILE.read_text())
            other["tie_tolerance"] = 2e-6
            (folder / "other.json").write_text(json.dumps(other))
            p = stage1.run_cli("check-product", "--product", str(folder / "t.jsonl"), "--topology-budget", str(folder / "other.json"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            p = stage1.run_cli("check-product", "--product", str(folder / "m.jsonl"), "--topology-budget", str(folder / "bad.json"))
            self.assertEqual(p.returncode, 0, "the topology budget is read for a /4 product only")

    def test_tool_contract_and_adapter(self):
        stage1.CommandLine("test_tool_contract_passes").test_tool_contract_passes()
        doc = json.loads((ROOT / "contracts" / "tool_contracts" / "photon_likelihood.json").read_text(encoding="utf-8"))
        ops = {o["operation_id"]: o for o in doc["operations"]}
        self.assertIn("topology", ops)
        flags = [o["flag"] for o in ops["topology"]["invocation"]["options"]]
        for flag in ("--readout", "--h1-product", "--product", "--product-id", "--topology-budget"):
            self.assertIn(flag, flags)
        self.assertIn("--topology-budget", [o["flag"] for o in ops["check-product"]["invocation"]["options"]])
        self.assertEqual(doc["contract_version"], "1.0.0")
        adapter = json.loads((ASSETS.parent / "adapter.json").read_text(encoding="utf-8"))
        for asset in ("assets/light_recipe/topology.py", "assets/fixture_tools/t09_topology_readings.py", "assets/fixture_tools/t09_job_lines.py",
                      "assets/t09-topology-2.budget.json"):
            self.assertIn(asset, adapter["assets"])
        self.assertIn("../../tests/adapters/test_photon_likelihood_topology.py", adapter["tests"])


# --- no truth on the data side ----------------------------------------------------------------------------------------------

class TwoSourceStandIn(stage1.HandMadeGenerator):
    """The frozen generator's interface for the two-source control, with noise-free two-source events (this module's coding)."""
    PAIRS = [SEPARATED, [((0.3, 1.9, 0.0), unit((1.0, 0.0, 0.2)), 3000.0), ((0.1, -1.8, 0.4), unit((-0.2, 1.0, 0.0)), 2500.0)]]

    def event(self, fixture, block, stratum, event_index):
        if fixture != "two-source":
            return stage3.TimedGenerator().event(fixture, block, stratum, event_index)
        sources = self.PAIRS[event_index]
        tev, e_vis = noise_free_two_source_event(sources, 19.0)
        state = numpy.where(tev.event.state == readout.LIVE_HIT, self.HIT, self.UNHIT)
        return {"generator": self.GENERATOR, "fixture": fixture, "block": block, "stratum": stratum, "event_index": event_index,
                "data": {"state": state, "charge": tev.event.charge, "time": tev.time, "saturated": numpy.zeros(SENSORS, bool)},
                "truth": {"n_exp": numpy.array([s[2] for s in sources]), "vertex": numpy.array([s[0] for s in sources]),
                          "direction": numpy.array([s[1] for s in sources]), "t0": 19.0, "e_vis": numpy.array(e_vis),
                          "separation": float(numpy.linalg.norm(numpy.subtract(sources[0][0], sources[1][0])))}}


class TruthUnreachable(unittest.TestCase):
    def test_the_recipe_imports_no_scoring_tool(self):
        scan = stage1.RecipeImportsNoGenerator()
        files = sorted((ASSETS / "light_recipe").rglob("*.py")) + [ASSETS / "photon_likelihood.py"]
        self.assertIn(ASSETS / "light_recipe" / "topology.py", files)
        for path in files:
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(scan.findings_in(text), [])
                tree = ast.parse(text)
                names = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
                names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
                self.assertFalse([m for m in names if m.startswith(("t09_", "fixture_tools", "gen_"))], names)
                for word in ("t09_truth_start", "truth.npz", "t09_topology_readings", "truth-two-source"):
                    self.assertNotIn(word, text)

    def test_topology_opens_only_its_inputs_beside_truth_files(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder).resolve()
            gen = TwoSourceStandIn()
            files = t09_fixture_files.stratum_files(gen, "two-source", 1, 0, 1, folder, "s")
            t09_fixture_files.stratum_files(gen, "main", 1, 0, 1, folder, "m")
            p = stage1.run_cli("fit", "--readout", files["readout"]["path"], "--product", str(folder / "p3.jsonl"), "--product-id", "x",
                               "--likelihood", "charge-time", "--starts", "multistart")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            report = folder / "audit.json"
            p = stage3.audit_run(["topology", "--readout", files["readout"]["path"], "--h1-product", str(folder / "p3.jsonl"),
                                  "--product", str(folder / "p4.jsonl"), "--product-id", "x4"], report)
            out = json.loads(report.read_text())
            self.assertEqual(out["code"], 0, p.stdout + p.stderr)
            inside = sorted({Path(f).name for f in out["opened"] if Path(f).parent == folder} - {"audit.json"})
            self.assertEqual(inside, ["p3.jsonl", "p4.jsonl.partial", "s.readout"], inside)
            self.assertEqual(out["modules"], [])

    def test_readers_refuse_both_truth_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            two = t09_fixture_files.stratum_files(TwoSourceStandIn(), "two-source", 1, 0, 2, folder, "s")
            one = t09_fixture_files.stratum_files(TwoSourceStandIn(), "main", 1, 0, 1, folder, "m")
            for path in (two["truth"]["path"], one["truth"]["path"]):
                with self.subTest(file=Path(path).name):
                    with self.assertRaises(readout.ReadoutError):
                        readout.read_file(path)
                    p = stage1.run_cli("check-product", "--product", path)
                    self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            with self.assertRaises(t09_fixture_files.FixtureError):
                t09_fixture_files.read_truth(two["truth"]["path"])
            with self.assertRaises(t09_fixture_files.FixtureError):
                t09_fixture_files.read_truth_two_source(one["truth"]["path"])


# --- the two-source control's files -----------------------------------------------------------------------------------------

class TwoSourceHarness(unittest.TestCase):
    PINNED = {  # this module's pin of the harness's main, dead and saturation outputs before this stage (pin-harness-before.log)
        ("stage1", "main"): ("bd9401e24dd2071665d173455915367451c6eb06f95e1ab7de5555ffa2e8acb5", "256b5e2b4c4d0f8dddf2f69126effab94b38a9edf7d38d754072acf59d5db6e2"),
        ("stage1", "dead"): ("2427aec2b092aac98cde6067a446f37f4d693e75e8fb3c0e0cf98f4f90d17050", "8423eba857cac94c4de666e2ffc0a837c18c55cd04e50f323d77dd63d7304943"),
        ("stage1", "saturation"): ("85c82a84fe42f31a078459990966fe64340c1c81f19cbeaad83c9f035ddca3a8", "3d80c88dcf2c4a0e531355f07b6ebfa8b3314373d555a10887cce3bd02c2cb4e"),
        ("timed", "main"): ("e16e466055ca98bcacab568e794f35b29fc92e745b9e80db413ef9b1e4b05553", "0413cac9c3a176f844d238694eafeb55f123b16fd9b61d7b14b7079bb8b85f20"),
        ("timed", "dead"): ("9108ff60cf01611037cba752f8615339ed0375b37e2a4843fb07188f0b6b4413", "177382c40fe41ff7ec0c51e51a6b1c842191de67740d75d6a42a58392e37aead"),
        ("timed", "saturation"): ("a9fcf64b4bd04a151fd3df644ce4d46322b3c4cf8989cee17a218ce06848f114", "14eef0581dd3f8980ba4ee91521f14cacf0c147c4596fc50f56a27797413ef19")}

    @unittest.skipUnless(platform.system() == "Linux" and platform.libc_ver()[0] == "glibc",
                         "the pins are the bytes of values from Python's math module (the C library's exp, cos, sqrt), pinned on Linux "
                         "with glibc; macOS's libm rounds some of them otherwise (macOS CI run of PR #411)")
    def test_main_dead_and_saturation_outputs_are_unchanged(self):
        for (name, fixture), want in self.PINNED.items():
            gen = stage1.HandMadeGenerator() if name == "stage1" else stage3.TimedGenerator()
            with self.subTest(generator=name, fixture=fixture), tempfile.TemporaryDirectory() as folder:
                f = t09_fixture_files.stratum_files(gen, fixture, 1, 0, 3, folder, "s")
                self.assertEqual((f["readout"]["sha256"], f["truth"]["sha256"]), want)

    def test_two_source_files(self):
        gen = TwoSourceStandIn()
        with tempfile.TemporaryDirectory() as folder:
            f = t09_fixture_files.stratum_files(gen, "two-source", 1, 0, 2, folder, "s")
            rd = readout.read_file(f["readout"]["path"])
            self.assertEqual((rd.events, rd.header["saturation_charge"]), (2, None))
            head, truth = t09_fixture_files.read_truth_two_source(f["truth"]["path"])
            self.assertEqual((head["format"], head["role"], head["fixture"], head["events"], head["readout_sha256"]),
                             ("t09-truth-two-source/1", "truth", "two-source", 2, rd.sha256))
            self.assertEqual((truth["vertex"].shape, truth["direction"].shape, truth["e_vis"].shape, truth["n_exp"].shape,
                              truth["t0"].shape, truth["separation"].shape), ((2, 2, 3), (2, 2, 3), (2, 2), (2, 2), (2,), (2,)))
            numpy.testing.assert_array_equal(truth["vertex"][0], numpy.array([s[0] for s in SEPARATED]))
            ev = gen.event("two-source", 1, 0, 1)
            numpy.testing.assert_array_equal(rd.charge[1], ev["data"]["charge"])
            self.assertEqual(float(truth["separation"][1]), ev["truth"]["separation"])
        p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_fixture_files.py"), "--generator", "x",
                            "--fixture", "two-source", "--block", "1", "--stratum", "0", "--count", "1", "--out-dir", "y", "--stem", "z"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        out = json.loads(p.stdout)   # two-source is a known fixture now: the bad generator path, not the fixture, is refused
        self.assertEqual(out["status"], "rejected")
        self.assertIn("generator", out["reason"])


# --- the definitions of section 7 on hand-made outcomes ---------------------------------------------------------------------

class MirroredAndReversed(unittest.TestCase):
    def test_reversed_boundary(self):
        d = numpy.array([0.0, 0.0, 1.0])
        for c, want in ((-0.5, False), (-0.5000001, True), (-1.0, True), (0.0, False), (1.0, False)):
            with self.subTest(cosine=c):
                fitted = numpy.array([math.sqrt(1 - c * c), 0.0, c])
                self.assertEqual(t09_topology_readings.reversed_fit(fitted, d), want)

    def test_mirrored_boundary_and_population(self):
        x = numpy.array([2.0, 0.0, 0.0])
        self.assertFalse(t09_topology_readings.mirrored_fit(numpy.array([0.0, 1.0, 0.0]), x), "equidistant is not closer")
        self.assertTrue(t09_topology_readings.mirrored_fit(numpy.array([-0.001, 1.0, 0.0]), x))
        self.assertFalse(t09_topology_readings.mirrored_fit(numpy.array([1.9, 0.0, 0.0]), x))
        self.assertFalse(t09_topology_readings.in_mirror_population(numpy.array([0.3999 * R_S, 0.0, 0.0]), R_S))
        self.assertTrue(t09_topology_readings.in_mirror_population(numpy.array([0.4 * R_S, 0.0, 0.0]), R_S))

    def test_counts(self):
        z = [0.0, 0.0, 1.0]
        fits = [{"status": "converged", "vertex": [-2.1, 0.0, 0.0], "direction": [0.0, 0.0, -1.0]},   # mirrored and reversed
                {"status": "converged", "vertex": [2.0, 0.0, 0.0], "direction": z},
                {"status": "failed", "vertex": [-2.0, 0.0, 0.0], "direction": [0.0, 0.0, -1.0]},       # failures apart
                {"status": "converged", "vertex": [-1.0, 0.0, 0.0], "direction": z},                  # inside 0.4 R_s: no mirror reading
                # review F3: the population is read on the true radius, never the fitted one
                {"status": "converged", "vertex": [1.0, 0.0, 0.0], "direction": z},    # true 0.5 R_s, fitted 0.2: in, not mirrored
                {"status": "converged", "vertex": [-2.5, 0.0, 0.0], "direction": z}]   # true 0.2 R_s, fitted 0.5: out, though closer to -x_true
        vertices = numpy.array([[2.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.5, 0.0, 0.0], [1.0, 0.0, 0.0]])
        out = t09_topology_readings.mirror_reversed(fits, vertices, numpy.tile(z, (6, 1)), R_S)
        self.assertEqual(out, {"events": 6, "converged": 5, "failed": 1, "reversed": 1, "mirror_population": 3, "mirrored": 1,
                               "reversed_events": [0], "mirrored_events": [0]})

    def test_misid_counts(self):
        topo = [{"choice": "H1"}, {"choice": "H2"}, {"choice": None}, {"choice": "H2"}]
        self.assertEqual(t09_topology_readings.misid([t for t in topo], truth="H1"),
                         {"events": 4, "decided": 3, "none": 1, "H1": 1, "H2": 2, "misid": 2})
        self.assertEqual(t09_topology_readings.misid([t for t in topo], truth="H2"),
                         {"events": 4, "decided": 3, "none": 1, "H1": 1, "H2": 2, "misid": 1})

    def test_pool_reads_b2_to_b4_only(self):
        self.assertEqual([s for s in range(12) if t09_topology_readings.pooled_stratum(s)], list(range(3, 12)))


class DBar(unittest.TestCase):
    def test_the_eight_starts(self):
        """Review N1: v4 section 7's 8 starts, by case O-dbar's text."""
        x = numpy.array([[-1.0, 0.0, 0.0], [1.0, 0.5, 0.0]])
        d = numpy.array([unit((1.0, 0.0, 0.0)), unit((0.0, 1.0, 0.0))])
        mid = 0.5 * (x[0] + x[1])
        want = [(x[0], d[0]), (x[0], d[1]), (x[1], d[1]), (x[1], d[0]), (mid, d[0]), (mid, d[1]), (x[0], -d[0]), (x[1], -d[1])]
        got = t09_topology_readings.d_bar_starts(x, d)
        self.assertEqual(len(got), 8)
        for (a, b), (c, e) in zip(got, want):
            numpy.testing.assert_array_equal(a, c)
            numpy.testing.assert_array_equal(b, e)

    def test_a_later_start_bounds_it(self):
        """Review N1: with source 2 dominant, H1 at source 2's truth point (start 2, E by the count) bounds the best H1 fit, so
        D_bar is at most lnL(m2) minus the count ln L there (a second coding of the count form)."""
        sources = [((-2.5, 0.5, 0.0), unit((-1.0, 0.2, 0.0)), 40.0), ((2.5, -0.3, 0.4), unit((1.0, 0.0, 0.3)), 2000.0)]
        mus, e = [], []
        for v, dd, n in sources:
            mu, ev = text_shape_mu(v, dd, n)
            mus.append(numpy.array(mu))
            e.append(ev)
        m2 = mus[0] + mus[1] + DARK
        shape2 = numpy.array(stage1.text_shape(POSITIONS, NORMALS, sources[1][0], sources[1][1]))
        e_start = float((m2 - DARK).sum() / (SENSORS * shape2.sum()))
        m1 = SENSORS * e_start * shape2 + DARK
        bound = float((m2 * numpy.log(m2) - m2).sum() - (m2 * numpy.log(m1) - m1).sum())
        value = t09_topology_readings.d_bar(MODEL, numpy.array([s[0] for s in sources]), numpy.array([s[1] for s in sources]),
                                            numpy.array(e), numpy.ones(SENSORS, bool))
        self.assertLessEqual(value, bound + 1e-6)
        self.assertGreaterEqual(value, -1e-9)

    def test_coincident_sources_give_zero(self):
        s = ((0.5, -0.3, 0.2), unit((0.2, 0.4, 1.0)))
        e = text_shape_mu(s[0], s[1], 300.0)[1]
        value = t09_topology_readings.d_bar(MODEL, numpy.array([s[0], s[0]]), numpy.array([s[1], s[1]]), numpy.array([e, e]),
                                            numpy.ones(SENSORS, bool))
        self.assertLess(abs(value), 1e-2)

    def test_separated_sources_give_a_positive_value(self):
        sources = [((-1.0, 0.0, 0.0), unit((1.0, 0.0, 0.0)), 300.0), ((1.0, 0.0, 0.0), unit((1.0, 0.0, 0.0)), 300.0)]
        e = [text_shape_mu(v, d, n)[1] for v, d, n in sources]
        value = t09_topology_readings.d_bar(MODEL, numpy.array([s[0] for s in sources]), numpy.array([s[1] for s in sources]),
                                            numpy.array(e), numpy.ones(SENSORS, bool))
        self.assertGreater(value, 0.0)


# --- the readings end to end ------------------------------------------------------------------------------------------------

def run_tool(name, *args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / name), *args], capture_output=True, text=True,
                          timeout=1200)


def result_line(stdout):
    lines = stdout.splitlines()
    return json.loads(lines[-1][len("RESULT "):]) if lines and lines[-1].startswith("RESULT ") else None


class ReadingsEndToEnd(unittest.TestCase):
    def make(self, folder, fixture, count):
        files = t09_fixture_files.stratum_files(TwoSourceStandIn(), fixture, 1, 4 if fixture == "main" else 0, count, folder, fixture)
        r = files["readout"]["path"]
        for args in (("fit", "--readout", r, "--product", str(folder / f"{fixture}.p3"), "--product-id", "hm", "--likelihood",
                      "charge-time", "--starts", "multistart"),
                     ("topology", "--readout", r, "--h1-product", str(folder / f"{fixture}.p3"), "--product", str(folder / f"{fixture}.p4"),
                      "--product-id", "hm4"),
                     ("check-product", "--product", str(folder / f"{fixture}.p4"))):
            p = stage1.run_cli(*args)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return files["truth"]["path"]

    def test_stratum_two_source_and_pool(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            t_main = self.make(folder, "main", 2)
            t_two = self.make(folder, "two-source", 2)
            p = run_tool("t09_topology_readings.py", "stratum", "--product", str(folder / "main.p4"), "--multistart", str(folder / "main.p3"),
                         "--truth", t_main, "--label", "hm-topology")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = p.stdout
            for text in ("READING hm-topology mis-ID (H1 truth)", "READING hm-topology statistic", "READING hm-topology H2 starts",
                         "READING hm-topology reversed", "READING hm-topology mirrored"):
                self.assertIn(text, out)
            gates = [x for x in out.splitlines() if x.startswith("GATE ")]
            self.assertEqual(len(gates), 2, out)
            self.assertTrue(all(x.endswith("PASS") for x in gates), out)
            self.assertEqual(result_line(out), {"operation": "stratum", "status": "ok", "exit_code": 0, "reason": ""})
            p = run_tool("t09_topology_readings.py", "two-source", "--product", str(folder / "two-source.p4"), "--multistart",
                         str(folder / "two-source.p3"), "--truth", t_two, "--label", "hm2-topology", "--d-bar-events", "1")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            for text in ("READING hm2-topology mis-ID (H2 truth)", "READING hm2-topology statistic", "READING hm2-topology D_bar"):
                self.assertIn(text, p.stdout)
            self.assertIn("H1 0", p.stdout.split("mis-ID (H2 truth)")[1].splitlines()[0])
            self.assertIn("READING hm2-topology undecided (H1 failed, no H2 fit, no choice): 0 of 2; mis-ID (H2 truth) with the undecided "
                          "counted as misses: 0 of 2", p.stdout)
            self.assertEqual(len([x for x in p.stdout.splitlines() if x.startswith("GATE ") and x.endswith("PASS")]), 2, p.stdout)
            p = run_tool("t09_topology_readings.py", "pool", "--label", "hm-pool", "--pair", str(folder / "main.p4"), t_main)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("READING hm-pool pooled B2-B4 strata [4]", p.stdout)
            # refused: a one-source truth file for the two-source reading, and the reverse; a /4 of another readout
            p = run_tool("t09_topology_readings.py", "two-source", "--product", str(folder / "two-source.p4"), "--multistart",
                         str(folder / "two-source.p3"), "--truth", t_main, "--label", "x")
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (2, "rejected"), p.stdout)
            p = run_tool("t09_topology_readings.py", "stratum", "--product", str(folder / "main.p4"), "--multistart",
                         str(folder / "two-source.p3"), "--truth", t_main, "--label", "x")
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (2, "rejected"), p.stdout)
            # planted: a /4 whose H1 line differs from the /3's in a field no reader recomputes (the iterations of the reported fit
            # and of its chosen start, together): the /4 still reads, and the carry gate fails
            h, events, end = stage3.lines_of((folder / "main.p4").read_text())
            events[0]["fit"]["iterations"] += 1
            events[0]["starts"][events[0]["choice"]["chosen"]]["iterations"] += 1
            (folder / "bad.p4").write_text(stage3.build(h, events, end))
            product.read_text((folder / "bad.p4").read_text(), None, CFG, multistart.load(), topology.load())
            p = run_tool("t09_topology_readings.py", "stratum", "--product", str(folder / "bad.p4"), "--multistart", str(folder / "main.p3"),
                         "--truth", t_main, "--label", "bad")
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (1, "failed"), p.stdout + p.stderr)


# --- re-review nits N-A and N-B ---------------------------------------------------------------------------------------------

class ComparatorResultLine(unittest.TestCase):
    """The comparator's RESULT line tells a failed gate (exit 1, status failed) from a crash (no RESULT line)."""

    def test_comparator_result_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            files = t09_fixture_files.stratum_files(stage3.TimedGenerator(), "main", 1, 4, 2, folder, "s")
            r, t = files["readout"]["path"], files["truth"]["path"]
            for name, extra in (("one.jsonl", []), ("many.jsonl", ["--starts", "multistart"])):
                p = stage1.run_cli("fit", "--readout", r, "--product", str(folder / name), "--product-id", "hm", "--likelihood",
                                   "charge-time", *extra)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = run_tool("t09_truth_start.py", "fit", "--readout", r, "--truth", t, "--out", str(folder / "ts.jsonl"))
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (0, "ok"), p.stdout)
            args = ["compare", "--one-seed", str(folder / "one.jsonl"), "--multistart", str(folder / "many.jsonl"), "--truth", t,
                    "--truth-start", str(folder / "ts.jsonl"), "--label", "hm"]
            p = run_tool("t09_truth_start.py", *args)
            self.assertEqual((p.returncode, result_line(p.stdout)), (0, {"operation": "compare", "status": "ok", "exit_code": 0, "reason": ""}))
            self.assertEqual(t09_job_lines.classify(p.returncode, p.stdout), "passed")
            h, events, end = stage3.lines_of((folder / "one.jsonl").read_text())
            events[0]["fit"]["iterations"] += 1
            (folder / "bad.jsonl").write_text(stage3.build(h, events, end))
            p = run_tool("t09_truth_start.py", *[str(folder / "bad.jsonl") if a.endswith("one.jsonl") else a for a in args])
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (1, "failed"))
            self.assertEqual(t09_job_lines.classify(p.returncode, p.stdout), "gate-failed")
            p = run_tool("t09_truth_start.py", *[str(folder / "none.jsonl") if a.endswith("ts.jsonl") else a for a in args])
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (2, "rejected"))
            self.assertEqual(t09_job_lines.classify(p.returncode, p.stdout), "rejected")
            # a planted internal error inside compare: a truth file whose vertex array is missing
            import numpy as np
            with np.load(t) as npz:
                arrays = {k: npz[k] for k in npz.files if k != "vertex"}
            with open(folder / "cut.npz", "wb") as stream:
                np.savez(stream, **arrays)
            ts_lines = (folder / "ts.jsonl").read_text().splitlines()
            head = json.loads(ts_lines[0])
            head["truth_sha256"] = hashlib.sha256((folder / "cut.npz").read_bytes()).hexdigest()
            (folder / "ts-cut.jsonl").write_text("\n".join([json.dumps(head, sort_keys=True)] + ts_lines[1:]) + "\n")
            p = run_tool("t09_truth_start.py", *[str(folder / "cut.npz") if a == t else str(folder / "ts-cut.jsonl") if a.endswith("ts.jsonl")
                                                 else a for a in args])
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (2, "error"), p.stdout + p.stderr)
            self.assertEqual(t09_job_lines.classify(p.returncode, p.stdout), "error")
            # a crash before main: the tool copied where its imports fail; a bare traceback, exit 1, no RESULT line
            shutil.copy(ASSETS / "fixture_tools" / "t09_truth_start.py", folder / "t09_truth_start.py")
            p = subprocess.run([sys.executable, "-I", "-B", str(folder / "t09_truth_start.py"), *args], capture_output=True, text=True,
                               timeout=120)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIsNone(result_line(p.stdout))
            self.assertEqual(t09_job_lines.classify(p.returncode, p.stdout), "crash")

    def test_an_error_status_is_never_read_as_rejected(self):
        """Review N5: the comparator's run functions return a run status; an error status gives exit 2, status error."""
        import contextlib
        import unittest.mock
        for operation, target, args in (("compare", "run_compare", ["compare", "--one-seed", "a", "--multistart", "b", "--truth", "c",
                                                                     "--truth-start", "d", "--label", "x"]),
                                        ("fit", "run_fit", ["fit", "--readout", "a", "--truth", "b", "--out", "c"])):
            for status, code in (("error", 2), ("rejected", 2), ("failed", 1), ("ok", 0)):
                with self.subTest(operation=operation, status=status), unittest.mock.patch.object(t09_truth_start, target, return_value=status):
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        got = t09_truth_start.main(args)
                    self.assertEqual((got, result_line(buf.getvalue())["status"], result_line(buf.getvalue())["exit_code"]),
                                     (code, status, code))

    def test_classifier_pairs(self):
        c = t09_job_lines.classify
        ok = 'RESULT {"exit_code": 0, "operation": "x", "reason": "", "status": "ok"}'
        failed = 'RESULT {"exit_code": 1, "operation": "x", "reason": "", "status": "failed"}'
        self.assertEqual(c(0, "a\n" + ok + "\n"), "passed")
        self.assertEqual(c(1, failed), "gate-failed")
        self.assertEqual(c(1, "Traceback (most recent call last):\n"), "crash")
        self.assertEqual(c(1, ok), "crash", "a code that does not match its status")
        self.assertEqual(c(0, failed), "crash")
        self.assertEqual(c(1, failed + "\nmore"), "crash", "the RESULT line must be the last")
        self.assertEqual(c(2, 'RESULT {"exit_code": 2, "operation": "x", "reason": "r", "status": "rejected"}'), "rejected")
        self.assertEqual(c(2, 'RESULT {"exit_code": 2, "operation": "x", "reason": "r", "status": "error"}'), "error")
        self.assertEqual(c(1, 'RESULT {"exit_code": 0, "operation": "x", "reason": "", "status": "failed"}'), "crash",
                         "the RESULT line's own exit code must be the run's")
        self.assertEqual(c(-9, ""), "crash")
        self.assertEqual(c(1, "RESULT {not json"), "crash")


class ExactEqualityPatterns(unittest.TestCase):
    """PASS EQUAL lines are counted by exact full-line patterns; a line no pattern matches fails the count."""
    SPEC = {"golden": {"pattern": r"PASS EQUAL all 61 GOLDEN lines equal job 7571207's", "expected": 1},
            "readout": {"pattern": r"PASS EQUAL [A-Za-z0-9.-]+ readout sha256 [0-9a-f]{64} equals job 7571207's", "expected": 2}}

    def test_exact_counts(self):
        lines = ["PASS EQUAL all 61 GOLDEN lines equal job 7571207's", "PASS EQUAL main-B1 readout sha256 " + "a" * 64 + " equals job 7571207's",
                 "PASS EQUAL dead-B3 readout sha256 " + "b" * 64 + " equals job 7571207's", "READING x"]
        counts, unmatched, ok = t09_job_lines.count_exact(lines, self.SPEC)
        self.assertEqual((counts, unmatched, ok), ({"golden": 1, "readout": 2}, [], True))
        planted = lines + ["PASS EQUAL something else"]
        counts, unmatched, ok = t09_job_lines.count_exact(planted, self.SPEC)
        self.assertEqual((unmatched, ok), (["PASS EQUAL something else"], False))
        self.assertEqual(sum(1 for x in planted if x.startswith("PASS EQUAL ")), 4, "the old prefix count would have read 4")
        counts, unmatched, ok = t09_job_lines.count_exact(lines[:2], self.SPEC)
        self.assertFalse(ok, "a kind short of its expected count fails")
        trailing = ["PASS EQUAL all 61 GOLDEN lines equal job 7571207's and more"]
        self.assertEqual(t09_job_lines.count_exact(trailing, self.SPEC)[1], trailing, "anchored at the end too")

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "spec.json").write_text(json.dumps(self.SPEC))
            (folder / "a.log").write_text("PASS EQUAL all 61 GOLDEN lines equal job 7571207's\nPASS EQUAL x readout sha256 " + "c" * 64
                                          + " equals job 7571207's\n")
            (folder / "b.log").write_text("PASS EQUAL y readout sha256 " + "d" * 64 + " equals job 7571207's\nPASS EQUAL planted\n")
            p = run_tool("t09_job_lines.py", "count-exact", "--spec", str(folder / "spec.json"), str(folder / "a.log"), str(folder / "b.log"))
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (1, "failed"), p.stdout)
            self.assertIn("UNMATCHED PASS EQUAL planted", p.stdout)
            (folder / "b.log").write_text("PASS EQUAL y readout sha256 " + "d" * 64 + " equals job 7571207's\n")
            p = run_tool("t09_job_lines.py", "count-exact", "--spec", str(folder / "spec.json"), str(folder / "a.log"), str(folder / "b.log"))
            self.assertEqual((p.returncode, result_line(p.stdout)["status"]), (0, "ok"), p.stdout)
            out = folder / "o.txt"
            out.write_text("x\n" + 'RESULT {"exit_code": 1, "operation": "x", "reason": "", "status": "failed"}' + "\n")
            p = run_tool("t09_job_lines.py", "classify", "1", str(out))
            self.assertEqual((p.returncode, p.stdout.strip()), (0, "gate-failed"))


# --- noisy events and their cost --------------------------------------------------------------------------------------------

NOISY_TOPOLOGY_CASES = (("B1 one source", 60.0, None), ("B2 one source", 160.0, None), ("B3 one source", 300.0, None),
                        ("B4 one source", 1000.0, None), ("two sources B3 + B3", 300.0, 250.0))
NOISY_TOPOLOGY_EVENTS = 3


class NoisyTopologyFits(unittest.TestCase):
    def test_noisy_events(self):
        budget, tb = multistart.load(), topology.load()
        lines = []
        for k, (name, n1, n2) in enumerate(NOISY_TOPOLOGY_CASES):
            rng = numpy.random.default_rng([20261111, 500 + k])
            seconds, choices, statistics, h2_outcomes = [], {}, [], {}
            for _ in range(NOISY_TOPOLOGY_EVENTS):
                v1, d1 = stage1.draw_source(rng, 0.0, 0.7)
                t0 = float(rng.uniform(10.0, 30.0))
                if n2 is None:
                    tev = stage2.noisy_timed_event(rng, v1, d1, n1, t0)
                else:
                    axis = numpy.array(stage1.draw_source(rng, 0.0, 0.1)[1])
                    sep = float(rng.uniform(0.4, 1.2)) * R_S
                    mid = numpy.array(v1) * 0.3 / 0.7 * 0.5
                    sources = [(tuple(mid - axis * sep / 2), d1, n1), (tuple(mid + axis * sep / 2), stage1.draw_source(rng, 0, 0.1)[1], n2)]
                    tev = noisy_two_source_event(rng, sources, t0)
                with self.subTest(case=name):
                    ms = multistart.fit_multistart(MODEL, tev, budget)
                    started = time.perf_counter()
                    topo = topology.fit_topology(MODEL, tev, tb, ms.result)
                    seconds.append(time.perf_counter() - started)
                    choices[topo.choice] = choices.get(topo.choice, 0) + 1
                    if topo.statistic is not None:
                        statistics.append(round(topo.statistic, 1))
                    for r in topo.records:
                        key = r.result.failure or "converged"
                        h2_outcomes[key] = h2_outcomes.get(key, 0) + 1
                    if topo.result is not None and topo.result.point is not None:
                        self.assertEqual(topology.probability_check(MODEL, tev.event, topo.result.point)["failures"], 0)
            lines.append(f"{name}: choices {choices}, statistics {statistics}, H2 starts {dict(sorted(h2_outcomes.items()))}, "
                         f"{1e3 * numpy.mean(seconds):.0f} ms mean, {1e3 * max(seconds):.0f} ms largest (H2 only)")
        print("\nNOISY-TOPOLOGY " + "; ".join(lines), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
