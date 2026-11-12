"""D4 stage E6c: T09 scoring on the statistics core (tests/adapters/t09_scoring.py; d4-e6c-brief.md, items 2 and 4).

Every test runs on hand-made event documents and truth arrays written here (the fields the scoring reads, in the products' own key names); no
fixture is drawn, no fit runs. Sections cited are of t04-values-v4.md (Freeze A). Expectations, fixed before the first run
(d4-e6c-report.md, "Predictions"): v4 5.3's 333 and v4 10's 270; each record equals the core's own call on the same values; clause (b) counts
in B2-B4 and not in B1; U-K4's undecided event is a miss; the "fires" rules are strict at 0.10.

Run from the plugin root: python -m unittest tests.adapters.test_t09_scoring -v
"""
from __future__ import annotations

import dataclasses
import math
import sys
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "photon-likelihood" / "assets"
for _p in (ROOT, ASSETS, ASSETS / "fixture_tools"):
    sys.path.insert(0, str(_p))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_bin_scorer as bs  # noqa: E402
from tests.adapters import t09_scoring as t09  # noqa: E402
from light_recipe.likelihood import frame  # noqa: E402

SIGMA = numpy.array([0.015625, 0.01, 0.01, 0.02, 0.02, 0.05, 0.3])     # x, y, z, u1, u2, e_vis, t0: hand-made uncertainties
DIRECTION = numpy.array([0.0, 0.6, 0.8])


def fit_doc(offsets=(0, 0, 0, 0, 0, 0, 0), *, status="converged", ln_l=-100.0, vertex=(1.0, 0.5, -0.2), direction=DIRECTION):
    """A converged fit at truth + offsets x sigma (x, y, z, e_vis, t0; the direction offsets along the truth frame)."""
    if status != "converged":
        return {"status": status, "failure": "budget", "vertex": None, "direction": None, "e_vis": None, "t0": None, "frame": None,
                "covariance": None, "uncertainty_status": "not-formed", "ln_likelihood": None}
    d = numpy.asarray(direction, float)
    e1, e2 = frame(d)
    fitted = d + offsets[3] * SIGMA[3] * e1 + offsets[4] * SIGMA[4] * e2
    fitted = fitted / numpy.linalg.norm(fitted)
    f1, f2 = frame(fitted)
    v = numpy.asarray(vertex, float) + numpy.array(offsets[:3]) * SIGMA[:3]
    return {"status": "converged", "failure": None, "vertex": list(v), "direction": list(fitted), "e_vis": 1.0 + offsets[5] * SIGMA[5],
            "t0": 20.0 + offsets[6] * SIGMA[6], "frame": {"e1": list(f1), "e2": list(f2)}, "covariance": numpy.diag(SIGMA ** 2).tolist(),
            "uncertainty_status": "ok", "ln_likelihood": ln_l}


def event(i, fit, *, choice="H1", states="H" * 5 + "U" * 5, failures=0, h2_failures=0):
    return {"event": i, "fit": fit, "states": states, "probability_check": {"failures": failures},
            "topology": {"choice": choice, "probability_check": None if choice is None else {"failures": h2_failures}}}


def truth(n, *, vertex=(1.0, 0.5, -0.2), dead=()):
    return {"vertex": numpy.tile(vertex, (n, 1)), "direction": numpy.tile(DIRECTION, (n, 1)), "e_vis": numpy.ones(n), "t0": numpy.full(n, 20.0),
            "n_exp": numpy.full(n, 300.0), "dead_channels": numpy.array(dead, dtype=numpy.int64)}


def header(fixture, stratum, block, n):
    return {"fixture": fixture, "stratum": stratum, "block": block, "events": n, "readout_sha256": "a" * 64}


def ts_doc(ln_l=-100.0, status="converged"):
    doc = fit_doc(ln_l=ln_l) if status == "converged" else fit_doc(status="failed")
    if status != "converged":
        doc["ln_likelihood"] = ln_l
    return doc


class TestCount(unittest.TestCase):
    def test_333_and_270(self):
        self.assertEqual(t09.count_tests(), {"total": 333, "required": 270, "main": 288, "controls": 45})

    def test_b1_pulls_ungated_63(self):
        ungated = [(k.name, g[0]) for k in t09.ALL_BINS for g in t09.gates_of_bin(k) if not g[2]]
        self.assertEqual(len(ungated), 63)
        self.assertTrue(all(name.startswith("main-B1-") and gate.endswith(" pulls") for name, gate in ungated))

    def test_main_bin_has_24(self):
        for k in t09.ALL_BINS:
            n = {"main": 24, "dead": 21, "saturation": 21, "two-source": 1}[k.fixture]
            self.assertEqual(len(t09.gates_of_bin(k)), n)


class Wiring(unittest.TestCase):
    def make_main(self, n=20, block=11, stratum=4):
        offsets = [(0.3 * ((i % 5) - 2), 0.1 * (i % 3), -0.2, 0.1, -0.1, 0.05 * (i % 4), 0.2) for i in range(n)]
        events = [event(i, fit_doc(o)) for i, o in enumerate(offsets)]
        events[3] = event(3, fit_doc(status="failed"), choice=None)
        events[5] = event(5, fit_doc(offsets[5]), choice="H2")
        ts = [ts_doc() for _ in range(n)]
        return events, ts, truth(n), header("main", stratum, block, n)

    def test_main_records_are_the_cores_on_the_same_values(self):
        events, ts, tr, head = self.make_main()
        identity = core.BinIdentity("T09", 9001, 11, 4)
        score = t09.score_bin(identity, events, head, tr, truth_start_docs=ts, readout_sha256="a" * 64)
        s = bs.BinScorer(identity)
        pulls = t09.event_parameter_pulls(events, tr)
        want = []
        for name in t09.PARAMETERS:
            want += s.pulls(f"{name} pulls", pulls[name])
        failures = [int(e["fit"]["status"] != "converged") for e in events]
        want.append(s.rate("fit failure", [1] * 20, failures, 0.01))
        wm = t09.wrong_minimum_counts(events, ts, tr, True)
        want.append(s.rate("wrong minimum", wm["m"], wm["y"], 0.005))
        want.append(s.rate("mis-ID H1 truth", [1] * 20, [int(e["topology"]["choice"] == "H2") for e in events], 0.01))
        self.assertEqual(score.records, want)
        self.assertEqual(len(score.records), 24)
        self.assertEqual(score.records[-3].readings["failures"], 1)
        self.assertEqual(score.records[-1].readings["failures"], 1)
        self.assertAlmostEqual(pulls["x"][0][0], -0.6, places=9)
        self.assertEqual(pulls["x"][3], [])

    def test_b1_pulls_ungated_rates_required(self):
        events, ts, tr, head = self.make_main(stratum=1)
        score = t09.score_bin(core.BinIdentity("T09", 9001, 11, 1), events, head, tr, truth_start_docs=ts)
        self.assertEqual([r.required for r in score.records], [False] * 21 + [True] * 3)
        self.assertTrue(all(r.result == "inconclusive" for r in score.records[:21]))

    def test_identity_and_truth_must_agree(self):
        events, ts, tr, head = self.make_main()
        for h in (header("main", 5, 11, 20), header("main", 4, 12, 20), header("dead", 4, 11, 20), header("main", 4, 11, 21)):
            with self.subTest(h=h), self.assertRaises(bs.ScoringError):
                t09.score_bin(core.BinIdentity("T09", 9001, 11, 4), events, h, tr, truth_start_docs=ts)
        with self.assertRaises(bs.ScoringError):
            t09.score_bin(core.BinIdentity("T09", 9001, 11, 4), events, head, tr, truth_start_docs=ts, readout_sha256="b" * 64)


class WrongMinimum(unittest.TestCase):
    def test_clause_b_counts_in_b2_to_b4_only(self):
        tr = truth(2)
        events = [event(0, fit_doc((6.0, 0, 0, 0, 0, 0, 0))), event(1, fit_doc())]
        ts = [ts_doc(), ts_doc()]
        b2 = t09.wrong_minimum_counts(events, ts, tr, True)
        b1 = t09.wrong_minimum_counts(events, ts, tr, False)
        self.assertEqual((b2["y"], b2["clause_b"]), ([1, 0], 1))
        self.assertEqual((b1["y"], b1["clause_b_reported"]), ([0, 0], 1))

    def test_clause_b_at_five_sigmas_exactly_is_not_wrong(self):
        tr = truth(1)
        self.assertEqual(t09.wrong_minimum_counts([event(0, fit_doc((5.0, 0, 0, 0, 0, 0, 0)))], [ts_doc()], tr, True)["y"], [0])
        self.assertEqual(t09.wrong_minimum_counts([event(0, fit_doc((5.0001, 0, 0, 0, 0, 0, 0)))], [ts_doc()], tr, True)["y"], [1])

    def test_clause_a_everywhere_at_half_a_unit(self):
        tr = truth(2)
        events = [event(0, fit_doc(ln_l=-100.5)), event(1, fit_doc(ln_l=numpy.nextafter(-100.5, 0)))]
        found = t09.wrong_minimum_counts(events, [ts_doc(-100.0), ts_doc(-100.0)], tr, False)
        self.assertEqual(found["y"], [1, 0])

    def test_comparator_unavailable_counts_as_wrong(self):
        """The user's answer (2026-11-12): an event whose truth-start fit failed counts as a wrong minimum; the count is printed."""
        tr = truth(3)
        events = [event(i, fit_doc(ln_l=-101.0)) for i in range(3)]
        ts = [ts_doc(-100.0, status="failed"), ts_doc(-100.9, status="failed"), ts_doc(None, status="failed")]
        found = t09.wrong_minimum_counts(events, ts, tr, True)
        self.assertEqual((found["m"], found["y"], found["unavailable"], found["unavailable_shows_a"]), ([1, 1, 1], [1, 1, 1], 3, 1))
        self.assertEqual(t09.WRONG_MINIMUM_WITHOUT_TRUTH_START, "counted")

    def test_the_other_reading_is_refused(self):
        with self.assertRaises(bs.ScoringError):
            t09.wrong_minimum_counts([event(0, fit_doc())], [ts_doc()], truth(1), True, without_truth_start="left-out")

    def test_failed_reported_fit_is_not_in_the_denominator(self):
        found = t09.wrong_minimum_counts([event(0, fit_doc(status="failed"))], [ts_doc()], truth(1), True)
        self.assertEqual((found["m"], found["y"]), ([0], [0]))


class TwoSource(unittest.TestCase):
    def test_undecided_is_a_miss(self):
        events = [event(0, fit_doc(), choice="H2"), event(1, fit_doc(), choice="H1"), event(2, fit_doc(status="failed"), choice=None)]
        self.assertEqual(t09.two_source_misses(events), [0, 1, 1])
        tr = truth(3)
        score = t09.score_bin(core.BinIdentity("T09", 9004, 11, 0), events, header("two-source", 0, 11, 3), tr)
        self.assertEqual(len(score.records), 1)
        self.assertEqual((score.records[0].gate, score.records[0].readings["failures"]), ("mis-ID H2 truth", 2))


class Pool(unittest.TestCase):
    def test_pooled_over_strata_3_to_11(self):
        columns = {}
        for s in range(3, 12):
            tr = truth(2, vertex=(3.0, 0.0, 0.0))     # |x| / R_s = 0.6: in the mirror population
            events = [event(0, fit_doc()), event(1, fit_doc(vertex=(-3.0, 0.0, 0.0), direction=-DIRECTION))]
            columns[s] = t09.pool_columns(events, tr)
        records = t09.score_pool(11, columns)
        self.assertEqual([r.gate for r in records], ["reversed", "mirrored"])
        self.assertEqual([(r.readings["objects"], r.readings["failures"]) for r in records], [(18, 9), (18, 9)])
        self.assertEqual([r.limit for r in records], [0.005, 0.005])
        self.assertEqual(records[0].bin, t09.pool_identity(11).label)
        self.assertIn("pool 0", records[0].bin)
        with self.assertRaises(bs.ScoringError):
            t09.score_pool(11, {s: columns[s] for s in range(3, 11)})

    def test_mirror_population_from_radius_0_4(self):
        columns = {s: t09.pool_columns([event(0, fit_doc(vertex=(-1.0, 0, 0)))], truth(1, vertex=(1.0, 0.0, 0.0))) for s in range(3, 12)}   # 0.2 R_s
        mirrored = t09.score_pool(11, columns)[1]
        self.assertEqual(mirrored.readings.get("objects", 0), 0)


class Fires(unittest.TestCase):
    def centre(self, estimate, se):
        return core.TestResult("x", "b", "trimmed-centre", estimate, se, None, None, 0.1, "pass", 3, 1, 0.95, 1000, True, "", {})

    def test_strict_at_0_10(self):
        z = 1.6448536269514722
        self.assertFalse(t09.fires(self.centre(0.10 + z * 0.01, 0.01), 1)[1])
        self.assertTrue(t09.fires(self.centre(0.10 + z * 0.01 + 1e-12, 0.01), 1)[1])
        self.assertTrue(t09.fires(self.centre(-(0.10 + z * 0.01 + 1e-12), 0.01), 1)[1])

    def test_attempt_2_uses_1_645_too(self):
        """The user's answer (K09, 2026-11-12): the "fires" rules use 1.645 at both attempts."""
        for attempt in (1, 2):
            value, hit = t09.fires(self.centre(0.12, 0.01), attempt)
            self.assertAlmostEqual(value, 0.12 - 1.6448536269514722 * 0.01, places=12)
            self.assertTrue(hit)
        self.assertEqual(t09.FIRES_ALPHA_OF_ATTEMPT, {1: 0.05, 2: 0.05})

    def test_e1a_fires_on_any_of_four_and_e1b_on_t0(self):
        n = 40
        tr = truth(n)
        shifted = [event(i, fit_doc((0, 0, 0.5 + 0.01 * (i % 3), 0, 0, 0, 0))) for i in range(n)]
        check, lines = t09.negative_check(core.BinIdentity("T09", 9002, 11, 0), "dead read as unhit (E1a)", shifted, tr, t09.E1A_PARAMETERS)
        self.assertEqual((check.kind, check.result), ("negative", "pass"))
        self.assertEqual(len(lines), 4)
        unshifted = [event(i, fit_doc((0.3, 0, 0, 0, 0, 0, 0.05 * (i % 3)))) for i in range(n)]
        check, _ = t09.negative_check(core.BinIdentity("T09", 9001, 11, 10), "single-photon density (E1b)", unshifted, tr, t09.E1B_PARAMETERS)
        self.assertEqual(check.result, "fail")      # t0 centre 0.05: does not fire; a check that does not fire is fail


class LimitsAndNames(unittest.TestCase):
    """Fix round 1 (review M8, I2): the limits, the E1a parameters and E1b's stratum, the required checks."""

    def test_limits(self):
        events, ts, tr, head = Wiring().make_main()
        score = t09.score_bin(core.BinIdentity("T09", 9001, 11, 4), events, head, tr, truth_start_docs=ts)
        limits = {r.gate: r.limit for r in score.records if r.statistic == "rate"}
        self.assertEqual(limits, {"fit failure": 0.01, "wrong minimum": 0.005, "mis-ID H1 truth": 0.01})
        two = t09.score_bin(core.BinIdentity("T09", 9004, 11, 0), [event(0, fit_doc(), choice="H2")], header("two-source", 0, 11, 1), truth(1))
        self.assertEqual(two.records[0].limit, 0.01)

    def test_e1a_and_e1b(self):
        self.assertEqual((t09.E1A_PARAMETERS, t09.E1B_PARAMETERS, t09.E1B_STRATUM), (("x", "y", "z", "t0"), ("t0",), 10))
        self.assertEqual(t09.bin_kind(9001, 10).name, "main-B4-r0.4-0.7")

    def test_required_checks(self):
        names = t09.required_checks()
        self.assertEqual(len(names), 15 + 14 + 13 + 3)
        self.assertEqual(names[-3:], (t09.E1A_NAME, t09.E1B_NAME, t09.FIXED_POINTS_NAME))
        self.assertNotIn("dead channels excluded two-source", names)


class Deterministic(unittest.TestCase):
    def test_probability_and_dead_and_fixed_points(self):
        events = [event(0, fit_doc(), failures=0), event(1, fit_doc(), failures=2, h2_failures=1)]
        self.assertEqual(len(t09.probability_defects(events)), 1)
        self.assertEqual(len(t09.probability_defects(events, with_h2=True)), 2)
        self.assertEqual(t09.fixed_point_check(["GATE a PASS", "GATE b PASS", "GATE c PASS", "POINT x"]).result, "pass")
        self.assertEqual(t09.fixed_point_check(["GATE a PASS", "GATE b PASS"]).result, "fail")
        self.assertEqual(t09.fixed_point_check(["GATE a PASS", "GATE b PASS", "GATE c FAIL"]).result, "fail")

    def test_dead_read_as_unhit_is_a_defect(self):
        tr = truth(1, dead=(2,))
        events = [event(0, fit_doc(), states="HHDUU")]
        score = t09.score_bin(core.BinIdentity("T09", 9002, 11, 0), events, header("dead", 0, 11, 1), tr)
        self.assertEqual(score.defects["dead channels excluded"], [])
        events = [event(0, fit_doc(), states="HHUUU")]
        score = t09.score_bin(core.BinIdentity("T09", 9002, 11, 0), events, header("dead", 0, 11, 1), tr)
        self.assertTrue(score.defects["dead channels excluded"])
        self.assertEqual([c.result for c in t09.bin_checks(score)], ["pass", "fail"])


class MissingOutput(unittest.TestCase):
    def test_every_test_of_an_incomplete_workflow(self):
        records = []
        for k in t09.ALL_BINS:
            records += t09.missing_records(core.BinIdentity("T09", k.fixture_id, 12, k.stratum), "a range task crashed")
        records += t09.missing_pool(12, "a range task crashed")
        self.assertEqual((len(records), sum(r.required for r in records)), (333, 270))
        outcome = core.workflow_outcome("T09", records, [], attempt=2, required_checks=())
        self.assertEqual(outcome.r11_state, "failed")
        self.assertTrue(all(r.confidence == 0.99 for r in records))


if __name__ == "__main__":
    unittest.main()
