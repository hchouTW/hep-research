"""D4 stage E6a: the statistics core of the evaluation harness (freeze-b-proposal.md section 4, row E6; d4-e6a-brief.md).

The core is tests/adapters/t04_evaluation_core.py, scoring side. Sections cited are of t04-values-v4.md (Freeze A). Every test here runs on
hand-made inputs: fixed arrays, fixed counts and fixed bootstrap indices, no draw of any fixture and no Monte Carlo. One class reads files from
outside this module and skips without them; the job of record counts a skip as a failure:
- FrozenCodingAgreement: the frozen codings `calc-pull-table.py` (section 18, row A, 5c3c7dd3...) and `calc-rate-rule.py` (a70704dc...), named
  by HEP_T04_CALC_PULL_TABLE and HEP_T04_CALC_RATE_RULE. Their functions are called, never edited or copied.

Expectations, fixed before the first run (d4-e6a-report.md, "Predictions"): the closed-form values of v4 (sections 3.4, 5.2, 5.3) are met to
the printed digits; the core's statistics, pull rule and rate bound equal the frozen codings exactly (==) on the hand-made inputs.

Run from the plugin root: python -m unittest tests.adapters.test_t04_evaluation_core -v
"""
from __future__ import annotations

import ast
import dataclasses
import importlib.util
import math
import os
import sys
import unittest
from pathlib import Path

import numpy
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
import t07_fake_rate as fake_rate  # noqa: E402

PULL_TABLE = os.environ.get("HEP_T04_CALC_PULL_TABLE", "")
RATE_RULE = os.environ.get("HEP_T04_CALC_RATE_RULE", "")
PULL_TABLE_SHA256 = "5c3c7dd3de32df59dc255a7bac0486836b6b67053328480f0009fa0e706faa40"  # section 18, row A: 5c3c7dd3de32df59; job 7474461's receipt
RATE_RULE_SHA256 = "a70704dcd6aa6df67c42e5ac4779bb2172aa68150bb1c98efff72335205995c9"  # section 18, row A: a70704dcd6aa6df6
K_WID = 0.9617  # calc-closed-form.py, the exact Gaussian se constant of sigma_68 (section 5.1, design se 0.962/sqrt(n))

T07_NOISE = core.BinIdentity("T07", 7002, 11, 3)
T07_NOISE_2 = core.BinIdentity("T07", 7002, 12, 3)   # attempt 2: the level comes from the block
ATTEMPT_1 = core.level_of_block(11)
ATTEMPT_2 = core.level_of_block(12)


def spread_counts(events: int, objects: int, failures: int):
    """m and y with `failures` failures, one per event in the first events: the v4 5.2 example's form."""
    m = numpy.full(events, objects)
    y = numpy.zeros(events, dtype=numpy.int64)
    y[:failures] = 1
    return m, y


def hand_pulls(events: int, objects: int, scale: float = 1.0, shift: float = 0.0):
    """Fixed pulls, no random numbers: a smooth deterministic sequence with Gaussian-like quantiles (the normal quantile of a stratified grid)."""
    count = events * objects
    grid = (numpy.arange(count) * 0.6180339887498949) % 1.0
    values = stats.norm.ppf(numpy.clip(grid, 1e-6, 1 - 1e-6))
    return (shift + scale * values).reshape(events, objects)


def hand_indices(events: int, replicates: int):
    """Fixed bootstrap indices without a generator: a quadratic walk, with repeats (no row is a permutation of the events)."""
    b = numpy.arange(replicates)[:, None]
    i = numpy.arange(events)[None, :]
    rows = (i * i * (2 * b + 3) + 5 * b + 1) % events
    return rows.astype(numpy.int64)


class AttemptLevel(unittest.TestCase):
    """Section 3.4: attempt 1 at 95 %, attempt 2 at 99 % (`z` 2.326) on every test; the attempt comes from the block (11 or 12, section 3.2) only."""

    def test_block_11_is_attempt_1_at_95_percent(self):
        self.assertEqual((ATTEMPT_1.block, ATTEMPT_1.attempt, ATTEMPT_1.confidence, ATTEMPT_1.alpha), (11, 1, 0.95, 0.05))
        self.assertEqual(ATTEMPT_1.z, float(stats.norm.isf(0.05)))
        self.assertEqual(round(ATTEMPT_1.z, 3), 1.645)

    def test_block_12_is_attempt_2_at_99_percent(self):
        self.assertEqual((ATTEMPT_2.block, ATTEMPT_2.attempt, ATTEMPT_2.confidence, ATTEMPT_2.alpha), (12, 2, 0.99, 0.01))
        self.assertEqual(round(ATTEMPT_2.z, 3), 2.326)

    def test_no_other_block_gives_a_level(self):
        for block in (0, 1, 2, 3, 4, 5, 6, 10, 13, -11):
            with self.subTest(block=block):
                with self.assertRaises(core.CoreError):
                    core.level_of_block(block)

    def test_a_level_made_by_hand_is_refused(self):
        with self.assertRaises(core.CoreError):
            core.Level(block=11, attempt=1, confidence=0.99, alpha=0.01, z=2.326)
        with self.assertRaises(core.CoreError):
            core.Level(block=12, attempt=1, confidence=0.95, alpha=0.05, z=float(stats.norm.isf(0.05)))

    def test_attempt_2_slack_closed_form(self):
        """Section 3.4: 0.0369 at se 0.0095, 0.0283 at the cap; section 5.3 at attempt 1: 0.0434 and 0.0356."""
        self.assertEqual(round(core.slack(0.0095, ATTEMPT_2), 4), 0.0369)
        self.assertEqual(round(core.slack(core.PRECISION_CAP, ATTEMPT_2), 4), 0.0283)
        self.assertEqual(round(core.slack(0.0095, ATTEMPT_1), 4), 0.0434)
        self.assertEqual(round(core.slack(core.PRECISION_CAP, ATTEMPT_1), 4), 0.0356)
        self.assertEqual(round(core.Z_FAMILY, 3), 4.316)


class PullRule(unittest.TestCase):
    """Section 5.2, pull tests, steps 1 to 4 in their order, each at and across its boundary."""

    def word(self, estimate, se, level=ATTEMPT_1, target=0.0):
        return core.pull_step(estimate, target, se, level)

    def test_step_1_fails_whatever_the_cap_says(self):
        self.assertEqual(self.word(0.12, 0.012), ("fail", 1))  # se above the cap, and still fail
        self.assertEqual(self.word(-0.12, 0.012), ("fail", 1))

    def test_step_1_boundary(self):
        se = 0.005
        edge = 0.10 + ATTEMPT_1.z * se
        self.assertEqual(self.word(edge + 1e-9, se), ("fail", 1))
        self.assertEqual(self.word(edge - 1e-9, se), ("fail", 4))  # past step 1, not inside at step 3

    def test_worked_case_width_1_123_at_n_10000(self):
        """Section 5.2: se reaches the cap at width 1.123 at n = 10,000, where step 1 reads 0.105."""
        se = 1.123 * K_WID / math.sqrt(10000)
        self.assertAlmostEqual(se, core.PRECISION_CAP, delta=1e-6)
        self.assertEqual(round(abs(1.123 - 1.0) - ATTEMPT_1.z * se, 3), 0.105)
        self.assertEqual(core.pull_step(1.123, 1.0, se, ATTEMPT_1), ("fail", 1))
        self.assertEqual(core.pull_step(1.123, 1.0, core.PRECISION_CAP + 1e-6, ATTEMPT_1), ("fail", 1))

    def test_exact_boundaries_of_steps_1_and_3(self):
        """At se = 0 the bounds are exact: e = 0.10 is not above the tolerance (step 1) and is within it (step 3, "<=")."""
        self.assertEqual(self.word(0.10, 0.0), ("pass", 3))
        self.assertEqual(self.word(-0.10, 0.0), ("pass", 3))
        self.assertEqual(core.pull_step(1.10, 1.0, 0.0, ATTEMPT_1), ("fail", 1))  # 1.10 - 1.0 is 0.10000000000000009 in binary64

    def test_step_2_boundary(self):
        self.assertEqual(self.word(0.0, core.PRECISION_CAP + 1e-9), ("inconclusive", 2))
        self.assertEqual(self.word(0.0, core.PRECISION_CAP), ("pass", 3))

    def test_step_3_boundary(self):
        se = 0.008
        edge = 0.10 - ATTEMPT_1.z * se
        self.assertEqual(self.word(edge - 1e-9, se), ("pass", 3))
        self.assertEqual(self.word(edge + 1e-9, se), ("fail", 4))
        self.assertEqual(self.word(-(edge - 1e-9), se), ("pass", 3))

    def test_attempt_2_widens_every_bound(self):
        self.assertEqual(self.word(0.08, 0.01, ATTEMPT_1), ("pass", 3))   # 0.08 + 0.01645 = 0.0964
        self.assertEqual(self.word(0.08, 0.01, ATTEMPT_2), ("fail", 4))   # 0.08 + 0.02326 = 0.1033
        self.assertEqual(self.word(0.125, 0.01, ATTEMPT_1), ("fail", 1))  # 0.125 - 0.01645 = 0.1086
        self.assertEqual(self.word(0.125, 0.01, ATTEMPT_2), ("fail", 1))  # step 1 at 95 % at both attempts (the user, K09): 0.1086 > 0.10
        self.assertEqual(self.word(0.115, 0.01, ATTEMPT_1), ("fail", 4))  # 0.115 - 0.01645 = 0.0986: past step 1
        self.assertEqual(self.word(0.12, 0.01, ATTEMPT_2), ("fail", 1))   # 0.12 - 0.01645 = 0.1036: step 1 (no longer 2.326, E6c fix round 1)
        self.assertEqual(self.word(0.115, 0.01, ATTEMPT_2), ("fail", 4))  # 0.115 - 0.01645 = 0.0986: past step 1

    def test_the_rule_needs_finite_numbers(self):
        for estimate, se in ((math.nan, 0.01), (0.0, math.nan), (0.0, -0.001), (math.inf, 0.01)):
            with self.subTest(estimate=estimate, se=se):
                with self.assertRaises(core.CoreError):
                    self.word(estimate, se)


class Statistics(unittest.TestCase):
    """Section 5.1: trimmed mean at 10 % per side, sigma_68 half the central 68.27 % interval; mean and RMS reported beside them (section 6)."""

    def test_trimmed_centre(self):
        self.assertEqual(core.trimmed_centre(numpy.arange(1.0, 11.0)), 5.5)       # 1 cut from each side of 10
        self.assertEqual(core.trimmed_centre(numpy.array([0.0] * 9 + [100.0])), 0.0)
        self.assertEqual(core.trimmed_centre(numpy.arange(19.0)), 9.0)           # int(1.9) = 1 cut from each side
        self.assertEqual(core.trimmed_centre(numpy.array([5.0, -3.0, 1.0, 9.0, 0.0, 2.0, 7.0, 4.0, 6.0, 8.0])), 4.125)

    def test_sigma_68(self):
        x = numpy.arange(101.0)
        expected = (numpy.quantile(x, 0.841345) - numpy.quantile(x, 0.158655)) / 2
        self.assertEqual(core.sigma_68(x), expected)
        self.assertEqual(core.SIGMA68_PROBABILITIES, (0.158655, 0.841345))
        self.assertAlmostEqual(core.sigma_68(stats.norm.ppf((numpy.arange(200001) + 0.5) / 200001)), 1.0, places=4)

    def test_readings(self):
        readings = core.pull_readings(numpy.array([[1.0, -1.0], [3.0, -3.0]]))
        self.assertEqual(readings, {"objects": 4, "events": 2, "mean": 0.0, "rms": math.sqrt(5.0)})


class Bootstrap(unittest.TestCase):
    """Section 5.1: the event bootstrap, B = 1,000, seeded from the bin's identity; two runs give the same replicates; no global state, no clock."""

    def test_the_seeding_is_the_bins_identity(self):
        indices = core.bootstrap_indices(T07_NOISE, 50)
        sequence = numpy.random.SeedSequence([core.BOOTSTRAP_DOMAIN, 7002, 11, 3])
        expected = numpy.random.Generator(numpy.random.PCG64(sequence)).integers(0, 50, size=(core.BOOTSTRAP_REPLICATES, 50))
        self.assertEqual(indices.shape, (1000, 50))
        self.assertTrue(numpy.array_equal(indices, expected))
        self.assertEqual(core.BOOTSTRAP_REPLICATES, 1000)

    def test_two_runs_give_the_same_replicates_and_global_state_does_not_enter(self):
        numpy.random.seed(1)
        first = core.bootstrap_indices(T07_NOISE, 40)
        numpy.random.seed(2)
        numpy.random.random(17)
        second = core.bootstrap_indices(T07_NOISE, 40)
        self.assertTrue(numpy.array_equal(first, second))

    def test_each_part_of_the_identity_changes_the_replicates(self):
        base = core.bootstrap_indices(T07_NOISE, 40)
        for other in (core.BinIdentity("T07", 7001, 11, 3), core.BinIdentity("T07", 7002, 12, 3), core.BinIdentity("T07", 7002, 11, 4)):
            with self.subTest(other=other):
                self.assertFalse(numpy.array_equal(base, core.bootstrap_indices(other, 40)))

    def test_the_identity_is_checked(self):
        for workflow, fixture, block, stratum in (("T10", 7002, 11, 3), ("T07", 8001, 11, 3), ("T07", 7002, 11, -1), ("T07", 7002, 11, 12)):
            with self.subTest(fixture=fixture, workflow=workflow):
                with self.assertRaises(core.CoreError):
                    core.BinIdentity(workflow, fixture, block, stratum)

    def test_the_identity_names_no_event_and_is_not_a_generator_seed(self):
        """The generator's state is SeedSequence([fixture_id, block, stratum, event_index]) (section 3.2); the bootstrap's leads with its own tag."""
        self.assertEqual(core.seed_entropy(T07_NOISE), (core.BOOTSTRAP_DOMAIN, 7002, 11, 3))

    def test_ragged_gather_equals_the_rectangular_one(self):
        x = hand_pulls(30, 4)
        idx = hand_indices(30, 5)
        events = core.EventValues.of(x)
        for b in range(5):
            self.assertTrue(numpy.array_equal(events.gather(idx[b]), x[idx[b]].ravel()))

    def test_ragged_events_with_empty_ones(self):
        events = core.EventValues.of([numpy.array([1.0, 2.0]), numpy.array([]), numpy.array([3.0])])
        self.assertEqual((events.events, events.objects), (3, 3))
        self.assertEqual(events.gather(numpy.array([2, 1, 0, 0])).tolist(), [3.0, 1.0, 2.0, 1.0, 2.0])

    def test_the_standard_error_is_the_spread_of_the_replicates(self):
        x = hand_pulls(60, 3)
        idx = hand_indices(60, 25)
        centre, width = core.replay_pull_tests("pull x", x, attempt=1, indices=idx)
        rep_c = [core.trimmed_centre(x[i].ravel()) for i in idx]
        rep_w = [core.sigma_68(x[i].ravel()) for i in idx]
        self.assertEqual(centre.standard_error, float(numpy.std(rep_c, ddof=1)))
        self.assertEqual(width.standard_error, float(numpy.std(rep_w, ddof=1)))
        self.assertEqual(centre.estimate, core.trimmed_centre(x.ravel()))
        self.assertEqual(width.estimate, core.sigma_68(x.ravel()) - 1.0)

    def test_indices_must_be_the_bins(self):
        x = hand_pulls(20, 2)
        for bad in (numpy.zeros((10, 19), dtype=numpy.int64), numpy.full((10, 20), 20), numpy.full((10, 20), -1), numpy.zeros((1, 20), dtype=numpy.int64)):
            with self.subTest(shape=bad.shape):
                with self.assertRaises(core.CoreError):
                    core.replay_pull_tests("pull x", x, attempt=1, indices=bad)


class PullRecords(unittest.TestCase):
    """The pull test's typed record (test, bin, statistic, se, bound, result word), the default replicates, mean and RMS beside it."""

    def test_records(self):
        x = hand_pulls(400, 2)
        centre, width = core.pull_tests("pull x", T07_NOISE, x)
        self.assertEqual((centre.gate, centre.statistic, width.statistic), ("pull x", "trimmed-centre", "sigma68-width"))
        self.assertEqual(centre.bin, "T07 fixture 7002 block 11 stratum 3")
        self.assertEqual((centre.attempt, centre.confidence, centre.replicates), (1, 0.95, 1000))
        self.assertEqual(centre.lower, centre.estimate - ATTEMPT_1.z * centre.standard_error)
        self.assertEqual(centre.upper, centre.estimate + ATTEMPT_1.z * centre.standard_error)
        self.assertEqual(centre.limit, 0.10)
        self.assertIn(centre.result, core.RESULT_WORDS)
        self.assertEqual(centre.readings["objects"], 800)
        self.assertEqual(centre.readings, width.readings)
        self.assertGreater(centre.standard_error, core.PRECISION_CAP)  # 800 pulls of 400 events: above the cap
        self.assertEqual((centre.result, centre.step), ("inconclusive", 2))
        again = core.pull_tests("pull x", T07_NOISE, x)
        self.assertEqual((centre, width), again)

    def test_no_pull_is_required_output_missing(self):
        centre, width = core.pull_tests("pull x", T07_NOISE, [numpy.array([]), numpy.array([])])
        for record in (centre, width):
            self.assertEqual(record.result, "inconclusive")
            self.assertIn("required output missing", record.reason)

    def test_a_non_finite_pull_is_refused(self):
        with self.assertRaises(core.CoreError):
            core.pull_tests("pull x", T07_NOISE, numpy.array([[0.0, math.nan]]))


class RateRule(unittest.TestCase):
    """Section 5.2, rate tests with an upper limit L: DEFF_hat, U_A, U_B, U, steps 1 to 4, N_min = 30/L; E2's rule reused."""

    def test_the_v4_example(self):
        """200 events of 10: 1.49 %, 1.58 %, 1.67 %, 1.76 % at k = 0, 1, 2, 3."""
        found = [core.rate_test("rate", T07_NOISE, *spread_counts(200, 10, k), 0.01).upper for k in range(4)]
        self.assertEqual([round(100 * u, 2) for u in found], [1.49, 1.58, 1.67, 1.76])

    def test_zero_failures_give_the_v3_bound(self):
        for events in (299, 3000, 6000, 12000):
            with self.subTest(events=events):
                record = core.rate_test("rate", T07_NOISE, *spread_counts(events, 6, 0), 0.01)
                self.assertAlmostEqual(record.upper, 1 - 0.05 ** (1 / events), delta=1e-12)
                self.assertEqual(record.lower, 0.0)

    def test_n_min_table(self):
        self.assertEqual(core.minimum_events(0.01), 3000)
        self.assertEqual(core.minimum_events(0.005), 6000)
        self.assertEqual(core.rate_test("rate", T07_NOISE, *spread_counts(2999, 6, 0), 0.01).result, "inconclusive")
        record = core.rate_test("rate", T07_NOISE, *spread_counts(3000, 6, 0), 0.01)
        self.assertEqual((record.result, record.step), ("pass", 3))
        self.assertEqual(round(100 * record.upper, 2), 0.10)   # the zero-failure bound there: 0.10 %
        record = core.rate_test("rate", T07_NOISE, *spread_counts(6000, 6, 0), 0.005)
        self.assertEqual(round(100 * record.upper, 2), 0.05)
        self.assertEqual(core.rate_test("rate", T07_NOISE, *spread_counts(5999, 6, 0), 0.005).step, 2)

    def test_step_1_fails_whatever_the_count(self):
        m, y = numpy.full(100, 10), numpy.full(100, 5)
        record = core.rate_test("rate", T07_NOISE, m, y, 0.01)
        self.assertEqual((record.result, record.step), ("fail", 1))

    def test_step_4(self):
        m, y = spread_counts(3000, 6, 60)   # p = 1/300, U well above 0.2 %
        record = core.rate_test("rate", T07_NOISE, m, y, 0.002)
        self.assertEqual(core.minimum_events(0.002), 15000)
        self.assertEqual((record.result, record.step), ("fail", 1))   # the lower bound is above 0.2 %: step 1 before step 2
        self.assertGreater(record.lower, 0.002)
        record = core.rate_test("rate", T07_NOISE, m, y, 0.004)
        self.assertEqual((record.result, record.step), ("inconclusive", 2))
        m, y = spread_counts(12000, 6, 200)  # p = 0.00278, lower bound under 0.004, U above it
        record = core.rate_test("rate", T07_NOISE, m, y, 0.003)
        self.assertEqual((record.result, record.step), ("fail", 4))
        self.assertLess(record.lower, 0.003)
        self.assertGreater(record.upper, 0.003)

    def test_exact_boundaries_of_steps_1_and_3(self):
        """U equal to L passes (step 3, "U <= L"; as E2's U_dev equal to C); a lower bound equal to L does not fail at step 1."""
        m, y = spread_counts(3000, 6, 3)
        found = core.rate_test("rate", T07_NOISE, m, y, 0.01)
        at_upper = core.rate_test("rate", T07_NOISE, m, y, found.upper, min_events=3000)
        self.assertEqual((at_upper.result, at_upper.step), ("pass", 3))
        at_lower = core.rate_test("rate", T07_NOISE, m, y, found.lower, min_events=3000)
        self.assertEqual((at_lower.result, at_lower.step), ("fail", 4))

    def test_attempt_1_is_e2s_rule_by_import(self):
        for m, y in (spread_counts(200, 10, 3), (numpy.array([3, 1, 4, 1, 5, 9, 2, 6]), numpy.array([1, 0, 2, 0, 0, 3, 0, 1]))):
            found = fake_rate.rate_rule(m, y)
            record = core.rate_test("rate", T07_NOISE, m, y, 0.01)
            self.assertEqual((record.upper, record.lower), (found["u_dev"], found["l_dev"]))
            self.assertEqual(record.readings["deff_hat"], found["deff_hat"])
            self.assertEqual(record.estimate, found["r_dev"])

    def test_the_level_argument_at_95_percent_is_e2s_bounds(self):
        for k, n, events, deff in ((0, 1200, 200, 1.0), (3, 2000, 200, 1.0), (7, 900, 300, 1.7), (31, 5000, 1000, 0.8), (400, 3000, 3000, 2.5)):
            with self.subTest(k=k, n=n):
                own = core.bounds_at(k, n, events, deff, 0.95)
                theirs = fake_rate.bounds_of(k, n, events, deff)
                self.assertEqual((own["u_a"], own["u_b"], own["u"], own["lower"]), (theirs["u_a"], theirs["u_b"], theirs["u_dev"], theirs["l_dev"]))

    def test_attempt_2_raises_the_pass_bound_only(self):
        m, y = spread_counts(3000, 6, 3)
        one = core.rate_test("rate", T07_NOISE, m, y, 0.01)
        two = core.rate_test("rate", T07_NOISE_2, m, y, 0.01)
        self.assertGreater(two.upper, one.upper)
        self.assertEqual(two.lower, one.lower)                           # step 1's fail bound stays at 95 % (the user, K09)
        self.assertEqual((two.attempt, two.confidence), (2, 0.99))
        self.assertAlmostEqual(core.rate_test("rate", T07_NOISE_2, *spread_counts(3000, 6, 0), 0.01).upper, 1 - 0.01 ** (1 / 3000), delta=1e-12)

    def test_no_objects_is_inconclusive_and_k_equal_to_n_fails(self):
        record = core.rate_test("rate", T07_NOISE, numpy.zeros(10, dtype=numpy.int64), numpy.zeros(10, dtype=numpy.int64), 0.01)
        self.assertEqual(record.result, "inconclusive")
        self.assertIn("required output missing", record.reason)
        record = core.rate_test("rate", T07_NOISE, numpy.full(10, 2), numpy.full(10, 2), 0.01)
        self.assertEqual((record.result, record.step), ("fail", 1))   # fix round 1, M2: k = n fails at step 1, whatever the count
        self.assertIn("k = n", record.reason)

    def test_counts_are_checked(self):
        for m, y in ((numpy.array([1, 2]), numpy.array([2, 0])), (numpy.array([1, -1]), numpy.array([0, 0])), (numpy.array([[1]]), numpy.array([[0]]))):
            with self.assertRaises(core.CoreError):
                core.rate_test("rate", T07_NOISE, m, y, 0.01)
        with self.assertRaises(core.CoreError):
            core.rate_test("rate", T07_NOISE, *spread_counts(10, 1, 0), 0.0)


class Efficiency(unittest.TestCase):
    """Section 5.2, efficiency tests: the failure rate on the same rule, lower bound 1 - U, L = 1 - (R - delta), N_min 3,000; delta(R) frozen."""

    def test_delta_at_the_table_rows(self):
        rows = ((1 - 1e-4, 0.0100), (0.98, 0.0100), (0.975, 0.0100), (0.97, 0.0102), (0.95, 0.0130), (0.90, 0.0179))
        for reference, delta in rows:
            with self.subTest(reference=reference):
                self.assertEqual(round(core.efficiency_margin(reference), 4), delta)
        self.assertEqual(core.efficiency_margin(0.992), 0.01)

    def test_the_limit_and_the_bound(self):
        m, y = spread_counts(3000, 6, 3)
        record = core.efficiency_test("efficiency clean", T07_NOISE, m, y, 0.99)
        rate = core.rate_test("rate", T07_NOISE, m, y, 0.01, min_events=3000)
        self.assertEqual(record.lower, 1 - rate.upper)
        self.assertEqual(record.estimate, 1 - 3 / 18000)
        self.assertEqual(record.limit, 0.99)
        self.assertEqual((record.result, record.statistic), ("pass", "efficiency"))
        self.assertAlmostEqual(core.efficiency_lower_limit(0.992), 0.982, places=12)

    def test_n_min_is_3000_events(self):
        self.assertEqual(core.efficiency_test("e", T07_NOISE, *spread_counts(2999, 6, 0), 0.99).result, "inconclusive")
        self.assertEqual(core.efficiency_test("e", T07_NOISE, *spread_counts(3000, 6, 0), 0.99).result, "pass")

    def test_a_low_efficiency_fails(self):
        m, y = numpy.full(3000, 6), numpy.zeros(3000, dtype=numpy.int64)
        y[:600] = 1  # efficiency 1 - 600/18000 = 0.9667
        self.assertEqual(core.efficiency_test("e", T07_NOISE, m, y, 0.99).result, "fail")


class PairedBound(unittest.TestCase):
    """U-K2: estimate - 1.645 x the event-bootstrap se (B = 1,000); the percentile printed as a reading; at attempt 2, z 2.326 (v4 3.4; a
    reading awaiting the user, PAIRED_ALPHA_OF_ATTEMPT)."""

    def setUp(self):
        self.events = 3000
        self.m = numpy.full(self.events, 6)
        self.a = numpy.full(self.events, 6)
        self.b = numpy.full(self.events, 6)
        self.a[::50] = 5      # 60 losses in the recipe
        self.b[::300] = 5     # 10 in the comparator

    def replicates(self, identity):
        idx = core.bootstrap_indices(identity, self.events)
        return [(self.a[i].sum() - self.b[i].sum()) / self.m[i].sum() for i in idx]

    def test_estimate_standard_error_and_bound(self):
        record = core.paired_test("efficiency noise (a)", T07_NOISE, self.m, self.a, self.b, -0.01)
        n = self.m.sum()
        self.assertEqual(record.estimate, (self.a.sum() - self.b.sum()) / n)
        reps = self.replicates(T07_NOISE)
        self.assertEqual(record.standard_error, float(numpy.std(reps, ddof=1)))
        self.assertEqual(record.replicates, 1000)
        self.assertEqual(record.lower, record.estimate - ATTEMPT_1.z * record.standard_error)
        self.assertEqual(record.readings["percentile_lower"], float(numpy.quantile(reps, 0.05)))
        self.assertEqual((record.result, record.statistic, record.limit), ("pass", "paired-difference", -0.01))

    def test_attempt_2_and_the_limit(self):
        one = core.paired_test("p", T07_NOISE, self.m, self.a, self.b, -0.01)
        two = core.paired_test("p", T07_NOISE_2, self.m, self.a, self.b, -0.01)
        self.assertEqual(round(ATTEMPT_2.paired_z, 3), 2.326)
        self.assertEqual(two.lower, two.estimate - ATTEMPT_2.paired_z * two.standard_error)
        self.assertEqual(two.readings["percentile_lower"], float(numpy.quantile(self.replicates(T07_NOISE_2), 0.01)))
        self.assertEqual(two.attempt, 2)
        tight = core.paired_test("p", T07_NOISE, self.m, self.a, self.b, one.lower + 1e-12)
        self.assertEqual(tight.result, "fail")
        edge = core.paired_test("p", T07_NOISE, self.m, self.a, self.b, one.lower)
        self.assertEqual(edge.result, "pass")

    def test_short_or_empty_bins_are_inconclusive(self):
        short = core.paired_test("p", T07_NOISE, self.m[:2999], self.a[:2999], self.b[:2999], -0.01)
        self.assertEqual((short.result, short.step), ("inconclusive", 2))
        empty = core.paired_test("p", T07_NOISE, numpy.zeros(3000, dtype=numpy.int64), numpy.zeros(3000, dtype=numpy.int64), numpy.zeros(3000, dtype=numpy.int64), -0.01)
        self.assertIn("required output missing", empty.reason)

    def test_counts_are_checked(self):
        with self.assertRaises(core.CoreError):
            core.paired_test("p", T07_NOISE, self.m, self.m + 1, self.b, -0.01)


class LevelFromTheBinsBlock(unittest.TestCase):
    """Fix round 1, I1: the level comes from identity.block only (11 is 95 %, 12 is 99 %, anything else refused); the replay has its own path."""

    def test_every_evaluation_test_refuses_a_bin_outside_blocks_11_and_12(self):
        m, y = spread_counts(3000, 6, 1)
        for block in (1, 2, 5, 6, 13):
            identity = core.BinIdentity("T07", 7002, block, 3)
            with self.subTest(block=block):
                for call in (lambda: core.pull_tests("p", identity, hand_pulls(20, 2)), lambda: core.rate_test("r", identity, m, y, 0.01),
                             lambda: core.efficiency_test("e", identity, m, y, 0.99), lambda: core.paired_test("q", identity, m, m - y, m, -0.01),
                             lambda: core.missing_output("p", identity, "rate", "x")):
                    with self.assertRaises(core.CoreError):
                        call()

    def test_a_block_12_bin_is_scored_at_99_percent(self):
        m, y = spread_counts(3000, 6, 3)
        self.assertEqual(core.rate_test("r", T07_NOISE_2, m, y, 0.01).confidence, 0.99)
        self.assertEqual(core.rate_test("r", T07_NOISE, m, y, 0.01).confidence, 0.95)
        centre, _ = core.pull_tests("p", T07_NOISE_2, hand_pulls(30, 2))
        self.assertEqual((centre.attempt, centre.confidence), (2, 0.99))
        self.assertEqual(centre.lower, centre.estimate - ATTEMPT_2.z * centre.standard_error)

    def test_evaluation_tests_take_no_level_and_no_indices(self):
        import inspect
        for function in (core.pull_tests, core.rate_test, core.efficiency_test, core.paired_test):
            with self.subTest(function=function.__name__):
                self.assertFalse({"level", "indices"} & set(inspect.signature(function).parameters))

    def test_the_replay_is_labelled_and_never_required(self):
        centre, width = core.replay_pull_tests("p", hand_pulls(30, 2), attempt=1, indices=hand_indices(30, 20))
        record = core.replay_rate_test("r", *spread_counts(3000, 6, 1), 0.01, attempt=2)
        for found in (centre, width, record):
            self.assertEqual((found.bin, found.required), (core.REPLAY_LABEL, False))
        self.assertEqual(record.confidence, 0.99)
        with self.assertRaises(core.CoreError):
            core.replay_rate_test("r", *spread_counts(3000, 6, 1), 0.01, attempt=3)

    def test_a_workflow_refuses_records_of_another_attempt(self):
        records = full_set("T07")
        records[0] = dataclasses.replace(records[0], attempt=2, confidence=0.99)
        with self.assertRaises(core.CoreError):
            core.workflow_outcome("T07", records, [], attempt=1, required_checks=())


class AttemptTwoReadings(unittest.TestCase):
    """The user's answers on the attempt-2 levels (K09, 2026-11-12): step 1, a fail bound, stays at 95 % at both attempts; the paired bound, a
    pass bound, is at 2.326 at attempt 2; and k = n reads fail at step 1 (E6a fix round 1, M2)."""

    def test_step_1_stays_at_95_percent_at_attempt_2(self):
        """e - 1.645 se > 0.10 with se above the cap fails at step 1 at both attempts (E6c fix round 1, the user's answer)."""
        self.assertEqual((core.STEP1_ALPHA_OF_ATTEMPT, core.PAIRED_ALPHA_OF_ATTEMPT), ({1: 0.05, 2: 0.05}, {1: 0.05, 2: 0.01}))
        self.assertEqual(core.pull_step(0.125, 0.0, 0.012, ATTEMPT_1), ("fail", 1))
        self.assertEqual(core.pull_step(0.125, 0.0, 0.012, ATTEMPT_2), ("fail", 1))
        self.assertEqual(ATTEMPT_2.z, float(stats.norm.isf(0.01)))     # the pass bound (step 3) at 99 %
        self.assertEqual(core.pull_step(0.08, 0.0, 0.0095, ATTEMPT_1), ("pass", 3))
        self.assertEqual(core.pull_step(0.08, 0.0, 0.0095, ATTEMPT_2), ("fail", 4))   # 0.08 + 2.326 x 0.0095 > 0.10

    def test_rate_step_1_stays_at_95_percent_at_attempt_2(self):
        m, y = spread_counts(3000, 6, 30)
        one = core.rate_test("r", T07_NOISE, m, y, 0.01)
        two = core.rate_test("r", T07_NOISE_2, m, y, 0.01)
        self.assertEqual(two.lower, one.lower)
        self.assertEqual(two.lower, core.bounds_at(30, 18000, 3000, two.readings["deff_hat"], 0.95)["lower"])
        self.assertGreater(two.upper, one.upper)                         # the pass bound U at 99 %

    def test_k_equal_to_n_fails_at_step_1(self):
        m = numpy.full(3000, 2)
        record = core.rate_test("r", T07_NOISE, m, m.copy(), 0.01)
        self.assertEqual((record.result, record.step, record.upper), ("fail", 1, 1.0))
        self.assertEqual(record.lower, 0.05 ** (1 / 3000))
        self.assertIn("k = n", record.reason)
        record = core.efficiency_test("e", T07_NOISE, m, m.copy(), 0.99)
        self.assertEqual(record.result, "fail")


def passing(name: str, required: bool = True, attempt: int = 1) -> core.TestResult:
    return core.TestResult(gate=name, bin="T07 fixture 7001 block 11 stratum 0", statistic="rate", estimate=0.0, standard_error=None, lower=0.0, upper=0.001,
                           limit=0.01, result="pass", step=3, attempt=attempt, confidence=0.95 if attempt == 1 else 0.99, replicates=None, required=required,
                           reason="", readings={})


def with_result(record: core.TestResult, result: str, step: int = 4, reason: str = "") -> core.TestResult:
    return core.replace_result(record, result, step, reason)


def full_set(workflow: str = "T07", attempt: int = 1, *replacements) -> list:
    """Section 10's required count of passing records (two gates), with the given records in place of the first ones."""
    count = core.REQUIRED_TESTS[workflow]
    records = [passing("a", attempt=attempt)] * (count - 1) + [passing("b", attempt=attempt)]
    for i, record in enumerate(replacements):
        records[i] = record
    return records


class R11Mapping(unittest.TestCase):
    """Section 10, from test results to R11 state, every row; the fixed obligations and U-K7's built in per workflow (fix round 1, I2)."""

    def outcome(self, tests=None, checks=None, workflow="T07", **kwargs):
        tests = full_set(workflow, kwargs.get("attempt", 1)) if tests is None else tests
        checks = [core.CheckResult("A05 wrong hits", "negative", "pass")] if checks is None else checks
        kwargs.setdefault("attempt", 1)
        kwargs.setdefault("required_checks", ())
        return core.workflow_outcome(workflow, tests, checks, **kwargs)

    def test_a_required_check_absent_is_refused(self):
        """E6c fix round 1, I2: every record pass and a required check absent is no outcome (v4 10: the checks must pass)."""
        with self.assertRaises(core.CoreError):
            self.outcome(required_checks=("A05 wrong hits", "CAI-T07-1"))
        with self.assertRaises(core.CoreError):
            core.workflow_outcome("T07", full_set("T07"), [], attempt=1)
        self.assertEqual(self.outcome(required_checks=("A05 wrong hits",)).r11_state, "done (narrowed claim)")

    def test_row_all_pass_is_a_narrowed_claim_for_every_workflow(self):
        for workflow in ("T07", "T08", "T09"):
            with self.subTest(workflow=workflow):
                found = self.outcome(workflow=workflow)
                self.assertEqual((found.workflow_result, found.r11_state, found.attempt), ("pass", "done (narrowed claim)", 1))
                self.assertEqual(found.gate_results, {"a": "pass", "b": "pass"})
                self.assertEqual([o.name for o in found.open_obligations], [row[0] for row in core.FIXED_OBLIGATIONS[workflow]])

    def test_plain_done_is_unreachable_for_t07_to_t09(self):
        for workflow in ("T07", "T08", "T09"):
            self.assertTrue(core.fixed_obligations(workflow))
        with self.assertRaises(core.CoreError):
            core.fixed_obligations("T10")

    def test_u_k7_obligations_are_built_in_and_never_a_pass(self):
        self.assertIn("A01", [o.name for o in self.outcome().open_obligations])
        names = [o.name for o in self.outcome(workflow="T08").open_obligations]
        self.assertTrue({"A38.3", "A15 (b)", "T08 angle and particle type"} <= set(names))
        self.assertIn("T09 medium", [o.name for o in self.outcome(workflow="T09").open_obligations])
        self.assertNotIn("A38.3", self.outcome(workflow="T08").gate_results)

    def test_a_found_obligation_is_listed_beside_the_fixed_ones(self):
        found = self.outcome(found_obligations=[core.Obligation("CAI-T07-9", None, "found at run time")])
        self.assertEqual(found.open_obligations[-1].name, "CAI-T07-9")

    def test_row_any_required_fail(self):
        found = self.outcome(full_set("T07", 1, with_result(passing("b"), "fail")))
        self.assertEqual((found.gate_results["b"], found.workflow_result, found.r11_state), ("fail", "fail", "failed"))
        self.assertTrue(found.failure_record)

    def test_row_any_required_inconclusive(self):
        found = self.outcome(full_set("T07", 1, with_result(passing("b"), "inconclusive", 2)))
        self.assertEqual((found.gate_results["b"], found.workflow_result, found.r11_state), ("inconclusive", "fail", "failed"))
        self.assertIn("a required check was inconclusive", " ".join(found.reasons))

    def test_row_deterministic_or_negative_check_fails(self):
        found = self.outcome(checks=[core.CheckResult("A05 wrong hits", "negative", "fail")])
        self.assertEqual((found.workflow_result, found.r11_state, found.stop), ("fail", "failed", False))
        found = self.outcome(checks=[core.CheckResult("double count", "deterministic", "fail", stop=True)])
        self.assertEqual((found.r11_state, found.stop), ("failed", True))

    def test_row_ungated_bin_has_no_effect_and_stays_open(self):
        ungated = core.mark_ungated(passing("E1 pull"), "outside the valid range (section 3.3): T08 E1")
        self.assertEqual((ungated.result, ungated.required), ("inconclusive", False))
        self.assertNotIn("computed_result", ungated.readings)   # O4: the computed word is dropped, the numbers stay as a reading
        self.assertNotIn("pass", " ".join(str(v) for v in ungated.readings.values()))
        self.assertEqual((ungated.estimate, ungated.upper), (0.0, 0.001))
        found = self.outcome(full_set("T07") + [ungated])
        self.assertEqual((found.workflow_result, found.r11_state), ("pass", "done (narrowed claim)"))
        self.assertNotIn("E1 pull", found.gate_results)
        self.assertIn("E1 pull", [o.name for o in found.open_obligations])

    def test_an_ungated_pass_or_a_required_not_applicable_is_refused(self):
        with self.assertRaises(core.CoreError):
            self.outcome(full_set("T07") + [passing("a", required=False)])
        with self.assertRaises(core.CoreError):
            self.outcome(full_set("T07", 1, with_result(passing("a"), "not-applicable", 0)))
        not_applicable = with_result(passing("merge iso", required=False), "not-applicable", 0, "cannot exist: merge rate in an iso bin")
        self.assertEqual(self.outcome(full_set("T07") + [not_applicable]).r11_state, "done (narrowed claim)")

    def test_row_required_set_not_intact_is_counted(self):
        for tests in (full_set("T07")[:-1], full_set("T07") + [passing("c")]):
            found = self.outcome(tests)
            self.assertEqual((found.gate_results, found.workflow_result, found.r11_state), ({}, "fail", "failed"))
            self.assertIn("required set not intact", found.reasons[0])
        self.assertEqual(core.REQUIRED_TESTS, {"T07": 1260, "T08": 80, "T09": 270})

    def test_row_cai_check(self):
        found = self.outcome(checks=[core.CheckResult("CAI-T07-1", "cai", "fail")])
        self.assertEqual(found.r11_state, "failed")
        found = self.outcome(checks=[core.CheckResult("CAI-T07-2", "cai", "gap", recorded_unsupported_gap=True)])
        self.assertEqual(found.r11_state, "done (narrowed claim)")
        self.assertIn("CAI-T07-2", [o.name for o in found.open_obligations])

    def test_row_forbidden_constant(self):
        found = self.outcome(forbidden_constants=["seed_window_sigma"])
        self.assertEqual((found.gate_results["seed_window_sigma"], found.r11_state), ("void (read as fail)", "failed"))

    def test_row_freeze_b_blocks_used_up(self):
        found = self.outcome(freeze_b_blocks_used_up=True)
        self.assertEqual((found.gate_results, found.workflow_result, found.r11_state), ({}, "not judged", "blocked-by-decision"))

    def test_row_critical_false_success(self):
        found = self.outcome(critical_false_success=["vertex finding"])
        self.assertEqual((found.gate_results["vertex finding"], found.r11_state), ("blocked", "failed"))

    def test_row_required_output_missing(self):
        missing = core.missing_output("pull q/p", core.BinIdentity("T07", 7002, 11, 5), "rate", "no product for events 6000-11999")
        self.assertEqual((missing.result, missing.required, missing.attempt), ("inconclusive", True, 1))
        self.assertEqual(self.outcome(full_set("T07", 1, missing)).r11_state, "failed")

    def test_row_resources(self):
        shrunk = core.missing_output("rate", core.BinIdentity("T07", 7001, 11, 0), "rate", "K10: resources shrank the sample")
        self.assertEqual(self.outcome(full_set("T07", 1, shrunk)).r11_state, "failed")
        found = self.outcome(evaluation_could_not_run=True)
        self.assertEqual((found.workflow_result, found.r11_state), ("not judged", "blocked-by-resource"))

    def test_row_method_changed_and_recorded(self):
        failed = self.outcome(full_set("T07", 1, with_result(passing("a"), "fail")))
        again = core.after_method_change(failed, recorded=True)
        self.assertEqual((again.r11_state, again.attempt), ("in-progress", 1))
        self.assertEqual(core.after_method_change(failed, recorded=False).r11_state, "failed")
        second = self.outcome(full_set("T07", 2, with_result(passing("a", attempt=2), "fail")), attempt=2)
        self.assertEqual(core.after_method_change(second, recorded=True).r11_state, "failed")  # after attempt 2, failed stands

    def test_row_matching_sensitivity_has_no_effect(self):
        found = self.outcome(matching_sensitivity_disagrees=True)
        self.assertEqual((found.workflow_result, found.r11_state), ("pass", "done (narrowed claim)"))
        self.assertIn("matching sensitivity disagrees (recorded, no effect)", found.recorded)

    def test_worst_gate_wins_and_no_mean_over_bins(self):
        found = self.outcome(full_set("T07", 1, with_result(passing("tail"), "pass"), with_result(passing("tail"), "fail"),
                                      with_result(passing("tail"), "inconclusive", 2)))
        self.assertEqual((found.gate_results["tail"], found.r11_state), ("fail", "failed"))

    def test_attempt_is_reported_with_any_pass_and_only_1_or_2(self):
        self.assertEqual(self.outcome(full_set("T07", 2), attempt=2).attempt, 2)
        with self.assertRaises(core.CoreError):
            self.outcome(attempt=3)

    def test_result_words_are_v4s(self):
        self.assertEqual(core.RESULT_WORDS, ("pass", "fail", "inconclusive", "not-applicable"))
        with self.assertRaises(core.CoreError):
            with_result(passing("a"), "passed")


RECIPE_FILES = {
    "acts-tracking": ["assets/acts_tracking.py"] + [f"assets/native/{p.name}" for p in sorted((ROOT / "adapters/acts-tracking/assets/native").glob("*")) if p.is_file()],
    "calo-cluster": ["assets/calo_cluster.py"] + [f"assets/calo_recipe/{p.name}" for p in sorted((ROOT / "adapters/calo-cluster/assets/calo_recipe").glob("*.py"))],
    "photon-likelihood": ["assets/photon_likelihood.py"] + [f"assets/light_recipe/{p.name}" for p in sorted((ROOT / "adapters/photon-likelihood/assets/light_recipe").glob("*.py"))],
}
HARNESS_MODULES = ("t04_evaluation_core", "t04_evaluation_layout")


def harness_imports(source: str) -> list:
    """The harness modules a Python source imports, in any form."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in ("import_module", "__import__") and node.args \
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            names = [node.args[0].value]
        else:
            continue
        found += [name for name in names if any(part in HARNESS_MODULES for part in name.split("."))]
    return found


class NoRecipeImportsTheCore(unittest.TestCase):
    """The core is scoring side: shared by T07, T08 and T09 and never imported by a recipe (v4 3.1; Freeze A amendment 1)."""

    def test_no_recipe_file_names_the_harness(self):
        count = 0
        for adapter, files in RECIPE_FILES.items():
            for name in files:
                path = ROOT / "adapters" / adapter / name
                text = path.read_text(encoding="utf-8")
                count += 1
                with self.subTest(path=f"{adapter}/{name}"):
                    if path.suffix == ".py":
                        self.assertEqual(harness_imports(text), [])
                    for module in HARNESS_MODULES:
                        self.assertNotIn(module, text)
        self.assertGreaterEqual(count, 40)

    def test_an_import_would_be_caught_in_each_form(self):
        for source in ("import t04_evaluation_core\n", "from tests.adapters import t04_evaluation_core\n", "from tests.adapters.t04_evaluation_layout import split\n",
                       "import tests.adapters.t04_evaluation_core as c\n", "importlib.import_module('t04_evaluation_core')\n"):
            with self.subTest(source=source):
                self.assertTrue(harness_imports(source))
        self.assertEqual(harness_imports("import t09_readings\n"), [])

    def test_the_core_imports_no_recipe_module(self):
        source = (ROOT / "tests" / "adapters" / "t04_evaluation_core.py").read_text(encoding="utf-8")
        modules = {alias.name.split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Import) for alias in node.names}
        modules |= {(node.module or "").split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
        self.assertFalse(modules & {"light_recipe", "calo_recipe", "acts_tracking", "photon_likelihood", "calo_cluster"})


def load_frozen(path: str, expected: str, name: str):
    import hashlib
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise AssertionError(f"{path} is not the frozen {name}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PULL_TABLE and RATE_RULE, "HEP_T04_CALC_PULL_TABLE and HEP_T04_CALC_RATE_RULE name the frozen codings (the job sets them)")
class FrozenCodingAgreement(unittest.TestCase):
    """The core against the frozen codings, on hand-made inputs: exact equality (==)."""

    @classmethod
    def setUpClass(cls):
        cls.pull = load_frozen(PULL_TABLE, PULL_TABLE_SHA256, "calc_pull_table_frozen")
        cls.rate = load_frozen(RATE_RULE, RATE_RULE_SHA256, "calc_rate_rule_frozen")

    def test_statistics_equal(self):
        for events, objects, scale, shift in ((1000, 1, 1.0, 0.0), (300, 6, 1.1, 0.03), (77, 3, 0.9, -0.2)):
            x = hand_pulls(events, objects, scale, shift).ravel()
            with self.subTest(events=events, objects=objects):
                self.assertEqual(core.trimmed_centre(x), self.pull.trimmed(x))
                self.assertEqual(core.sigma_68(x), self.pull.s68(x))

    def test_pull_rule_equal_at_attempt_1(self):
        for estimate in numpy.linspace(-0.13, 0.13, 53):
            for se in (0.002, 0.008, 0.0107, 0.0108, 0.0109, 0.015, 0.03):
                word, _ = core.pull_step(float(estimate), 0.0, se, ATTEMPT_1)
                self.assertEqual(word, self.pull.verdict(float(estimate), se), (estimate, se))
        self.assertEqual(self.pull.Z, ATTEMPT_1.z)
        self.assertEqual((self.pull.TOL, self.pull.CAP), (core.TOLERANCE, core.PRECISION_CAP))

    def test_replicates_equal_with_the_frozen_codings_indices(self):
        x = hand_pulls(200, 6, 1.05)
        idx = hand_indices(200, 30)
        centre, width = core.replay_pull_tests("pull", x, attempt=1, indices=idx)
        bc = numpy.array([self.pull.trimmed(x[i].ravel()) for i in idx])
        bw = numpy.array([self.pull.s68(x[i].ravel()) for i in idx])
        self.assertEqual((centre.standard_error, width.standard_error), (bc.std(ddof=1), bw.std(ddof=1)))

    def test_tail_bound_equal(self):
        for events, objects, cut in ((3000, 1, 2.9), (500, 6, 2.5), (200, 36, 3.0)):
            flags = numpy.abs(hand_pulls(events, objects, 1.1)) > cut
            m = numpy.full(events, objects)
            record = core.replay_rate_test("tail", m, flags.sum(axis=1), 0.01, attempt=1)
            self.assertEqual(record.upper, self.pull.tail_upper(flags))

    def test_rate_bound_equal_at_both_levels(self):
        sets = [spread_counts(200, 10, k) for k in range(4)] + [spread_counts(3000, 2, 31), spread_counts(12000, 6, 0)]
        m = 1 + (numpy.arange(997) * 7) % 13
        y = numpy.minimum(m, (numpy.arange(997) * 5) % 4 == 0)
        sets.append((m, y.astype(numpy.int64)))
        m2 = 1 + (numpy.arange(3001) * 3) % 36
        sets.append((m2, (numpy.arange(3001) % 97 == 0).astype(numpy.int64) * numpy.minimum(m2, 2)))
        for m, y in sets:
            with self.subTest(events=m.size, k=int(y.sum())):
                self.assertEqual(core.replay_rate_test("r", m, y, 0.01, attempt=1).upper, self.rate.bound(m, y))
                self.assertEqual(core.replay_rate_test("r", m, y, 0.01, attempt=2).upper, self.rate.bound(m, y, cl=0.99))


class EmptyReplicatesAndPools(unittest.TestCase):
    """E6c fix round 1: a bootstrap replicate with no object gives inconclusive with its reason (E6b review I4); the pooled identity."""

    def test_an_empty_replicate_is_inconclusive_not_a_crash(self):
        per_event = [numpy.array([0.3])] + [numpy.array([])] * 3      # one pull in four events: some of the 1,000 rows hold no object
        centre, width = core.pull_tests("pull x", T07_NOISE, per_event)
        for record in (centre, width):
            self.assertEqual((record.result, record.step), ("inconclusive", 2))
            self.assertIn("bootstrap replicates hold no pull", record.reason)
        full = [numpy.array([0.3 + 0.01 * i]) for i in range(50)]
        self.assertEqual(core.pull_tests("pull x", T07_NOISE, full)[0].step in (1, 2, 3, 4), True)

    def test_a_pool_has_its_own_entropy_and_level(self):
        pool = core.PooledIdentity("T09", 9001, 11, 0, tuple(range(3, 12)), "main B2-B4")
        self.assertEqual(core.seed_entropy(pool), (520, 9001, 11, 100))
        bins = {core.seed_entropy(core.BinIdentity("T09", 9001, 11, s)) for s in range(12)}
        self.assertNotIn(core.seed_entropy(pool), bins)
        self.assertEqual(pool.level, core.level_of_block(11))
        self.assertIn("pool 0", pool.label)
        record = core.rate_test("reversed", pool, numpy.ones(10, dtype=int), numpy.zeros(10, dtype=int), 0.005)
        self.assertEqual(record.bin, pool.label)
        for bad in ((9001, 11, 0, (3,), "x"), (9001, 11, 0, (3, 3), "x"), (9001, 11, 12, (3, 4), "x"), (7001, 11, 0, (3, 4), "x"), (9001, 11, 0, (3, 12), "x")):
            with self.subTest(bad=bad), self.assertRaises(core.CoreError):
                core.PooledIdentity("T09", *bad)
        with self.assertRaises(core.CoreError):
            core.PooledIdentity("T09", 9001, 1, 0, (3, 4), "x").level


if __name__ == "__main__":
    unittest.main()
