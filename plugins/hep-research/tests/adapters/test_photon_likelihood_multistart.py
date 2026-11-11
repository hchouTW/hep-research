"""adapters/photon-likelihood, D3 stage 3 of T09 (t07-t09-task-sheets.md, T09: "seeded multistart fits", "Wrong-minimum rate
reported beside resolution"): the data-side multistart seeds and their choice rule, product light-likelihood-product/3 with its
per-start records, the scoring-side truth-start fit (t04-values-v4.md section 7, "Truth-start fit": scoring side only, never on
the data side), the wrong-minimum clauses (a) and (b) and the fit-failure readings, and the stage 2 re-review nit N2. Hand-made
events only: no fixture event and no Monte Carlo of the frozen generator; noisy events are drawn with stage 2's module's coding of
section 4.3 and its own random numbers.

Expectations come from a second coding (the frame, the moment and median rules, the clauses) in this module, or from the stated
rule, never from the recipe's output. Stage 1's and stage 2's modules are unchanged; their helpers are reused by import.
Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood_multistart -v
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
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

from tests.adapters import test_photon_likelihood as stage1
from tests.adapters import test_photon_likelihood_time as stage2

ROOT, ASSETS = stage1.ROOT, stage1.ASSETS
from light_recipe import fit, joint, likelihood, multistart, product, readout  # noqa: E402
import t09_readings  # noqa: E402
import t09_truth_start  # noqa: E402

CFG, MODEL = stage1.CFG, stage1.MODEL
POSITIONS, NORMALS, unit = stage1.POSITIONS, stage1.NORMALS, stage1.unit
SENSORS, SPEED, DARK = stage1.SENSORS, stage1.SPEED, stage1.DARK
BUDGET_FILE = ASSETS / "t09-multistart-1.budget.json"
START_NAMES = ("prefit", "reversed", "turned +e1", "turned -e1", "turned +e2", "turned -e2", "mirrored", "charge seed")


# --- the second coding of the start rules (case O-starts, O-start-values) -------------------------------------------------

def hand_e_vis(tev, vertex, direction):
    """Stage 1's moment rule at (vertex, direction): sum q over hits / (1000 sum_live s_i)."""
    ev = tev.event
    shape = stage1.text_shape(POSITIONS, NORMALS, tuple(vertex), tuple(direction))
    total = sum(float(ev.charge[i]) for i in range(SENSORS) if ev.hit[i])
    return total / (SENSORS * sum(shape[i] for i in range(SENSORS) if ev.live[i]))


def hand_t0(tev, vertex):
    """Stage 2's median rule at the vertex: median over hits of t_i - |P_i - x| / v."""
    values = sorted(float(tev.time[i]) - math.dist(POSITIONS[i], tuple(vertex)) / SPEED for i in range(SENSORS) if tev.event.hit[i])
    n = len(values)
    return values[n // 2] if n % 2 else 0.5 * (values[n // 2 - 1] + values[n // 2])


def hand_starts(tev, anchor):
    """(name, vertex, direction) of the 8 starts from the anchor, by the text of case O-starts; the charge seed by stage 1's rule."""
    x, d = tuple(float(c) for c in anchor.vertex), tuple(float(c) for c in anchor.direction)
    e1, e2 = stage1.frame_text(d)
    neg = lambda v: tuple(-c for c in v)  # noqa: E731
    seed = fit.seed(MODEL, tev.event)
    return [("prefit", x, d), ("reversed", x, neg(d)), ("turned +e1", x, e1), ("turned -e1", x, neg(e1)), ("turned +e2", x, e2),
            ("turned -e2", x, neg(e2)), ("mirrored", neg(x), neg(d)),
            ("charge seed", tuple(float(c) for c in seed.vertex), tuple(float(c) for c in seed.direction))]


def multistart_product_text(content, budget=None, model=MODEL):
    budget = budget or multistart.load()
    rd = readout.read_bytes(content)
    buf = io.StringIO()
    writer = product.Writer(buf, product.header_document("hand-made", rd, CFG, likelihood="charge-time", budget=budget))
    for i in range(rd.events):
        tev = joint.TimedEvent.from_readout(rd, i)
        ms = multistart.fit_multistart(model, tev, budget)
        writer.event(product.multistart_event_document(i, tev, ms, product.check_at(model, tev.event, ms.anchor, ms.result)))
    writer.finish()
    return buf.getvalue()


def lines_of(text):
    lines = text.splitlines()
    return json.loads(lines[0]), [json.loads(x) for x in lines[1:-1]], json.loads(lines[-1])


def build(header, events, end):
    return "".join(json.dumps(p, sort_keys=True, allow_nan=False) + "\n" for p in [header] + events + [end])


def fake_result(status, ln_l, failure=None):
    return fit.FitResult(status, failure, numpy.zeros(3), numpy.array([0.0, 0.0, 1.0]), 1.0, None, "not-formed", ln_l, None, None, 0, 0,
                         None, None, 20.0)


# --- the budget file (case O-budget) ---------------------------------------------------------------------------------------

class Budget(unittest.TestCase):
    def test_shipped_budget(self):
        b = multistart.load()
        self.assertEqual(tuple(b.starts), START_NAMES)
        self.assertEqual(b.tie_tolerance, 1e-6)
        self.assertEqual(b.sha256, hashlib.sha256(BUDGET_FILE.read_bytes()).hexdigest())
        self.assertEqual(b.format, "light-likelihood-multistart/1")
        self.assertEqual(Path(multistart.DEFAULT).resolve(), BUDGET_FILE.resolve())

    def test_refusals(self):
        good = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        cases = {"unknown key": {**good, "iterations": 3}, "missing key": {k: v for k, v in good.items() if k != "tie_tolerance"},
                 "unknown start": {**good, "starts": good["starts"] + ["random"]},
                 "repeated start": {**good, "starts": good["starts"] + ["reversed"]},
                 "start 0 not prefit": {**good, "starts": good["starts"][1:] + ["prefit"]}, "no starts": {**good, "starts": []},
                 "tie zero": {**good, "tie_tolerance": 0.0}, "tie not a number": {**good, "tie_tolerance": "1e-6"},
                 "tie boolean": {**good, "tie_tolerance": True}, "other format": {**good, "format": "light-likelihood-multistart/2"},
                 "starts not a list": {**good, "starts": "prefit"}}
        with tempfile.TemporaryDirectory() as folder:
            for name, doc in cases.items():
                with self.subTest(defect=name):
                    path = Path(folder) / "b.json"
                    path.write_text(json.dumps(doc))
                    with self.assertRaises(multistart.BudgetError):
                        multistart.load(path)
            (Path(folder) / "nan.json").write_text('{"format": "light-likelihood-multistart/1", "starts": ["prefit"], "tie_tolerance": NaN}')
            with self.assertRaises(multistart.BudgetError):
                multistart.load(Path(folder) / "nan.json")
            with self.assertRaises(multistart.BudgetError):
                multistart.load(Path(folder) / "missing.json")


# --- the starts and the choice rule -----------------------------------------------------------------------------------------

class StartSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state, charge, times, e_vis = stage2.noise_free_timed_event((1.5, 0.5, -1.0), unit((0.0, 1.0, 1.0)), 300.0, 17.0,
                                                                     dead=(3, 4))
        cls.tev = stage2.timed(state, charge, times)

    def test_the_eight_starts_by_hand(self):
        budget = multistart.load()
        anchor, prefit, origin = fit.joint_seed(MODEL, self.tev)
        points = multistart.start_points(MODEL, self.tev, budget, anchor)
        self.assertEqual([name for name, _ in points], list(START_NAMES))
        self.assertIs(points[0][1], anchor)
        for (name, start), (hname, hx, hd) in zip(points[1:], hand_starts(self.tev, anchor)[1:]):
            with self.subTest(start=name):
                self.assertEqual(name, hname)
                self.assertLess(numpy.abs(start.vertex - numpy.array(hx)).max(), 1e-12)
                self.assertLess(numpy.abs(start.direction - numpy.array(hd)).max(), 1e-12)
                e = hand_e_vis(self.tev, hx, hd)
                self.assertAlmostEqual(start.e_vis, e, delta=1e-12 * e)
                self.assertAlmostEqual(start.t0, hand_t0(self.tev, hx), delta=1e-9)

    def test_a_shorter_budget_gives_its_starts_in_its_order(self):
        budget = dataclasses.replace(multistart.load(), starts=("prefit", "mirrored"))
        anchor, _, _ = fit.joint_seed(MODEL, self.tev)
        self.assertEqual([n for n, _ in multistart.start_points(MODEL, self.tev, budget, anchor)], ["prefit", "mirrored"])


class ChoiceRule(unittest.TestCase):
    TOL = 1e-6

    def test_highest_converged_wins(self):
        outcomes = [("converged", -100.0), ("converged", -90.0), ("failed", -10.0), ("converged", -95.0)]
        self.assertEqual(multistart.choose(outcomes, self.TOL), (1, multistart.RULE_BEST))

    def test_a_failed_start_never_wins(self):
        self.assertEqual(multistart.choose([("failed", -1.0), ("converged", -50.0)], self.TOL), (1, multistart.RULE_BEST))
        self.assertEqual(multistart.choose([("failed", None), ("converged", -50.0)], self.TOL), (1, multistart.RULE_BEST))

    def test_ties_go_to_the_lowest_index(self):
        self.assertEqual(multistart.choose([("converged", -90.0 - 0.9e-6), ("failed", None), ("converged", -90.0)], self.TOL),
                         (0, multistart.RULE_TIE))
        self.assertEqual(multistart.choose([("converged", -90.0), ("converged", -90.0)], self.TOL), (0, multistart.RULE_TIE))
        self.assertEqual(multistart.choose([("converged", -90.0 - 2e-6), ("converged", -90.0)], self.TOL), (1, multistart.RULE_BEST))
        # a later start inside the tolerance of the best, an earlier one outside it: the lowest tied index is the best's group
        self.assertEqual(multistart.choose([("converged", -91.0), ("converged", -90.0), ("converged", -90.0 - 0.5e-6)], self.TOL),
                         (1, multistart.RULE_TIE))

    def test_all_failed_and_no_start(self):
        self.assertEqual(multistart.choose([("failed", -1.0), ("failed", None)], self.TOL), (None, multistart.RULE_ALL_FAILED))
        self.assertEqual(multistart.choose([], self.TOL), (None, multistart.RULE_NO_START))


class AllStartsFail(unittest.TestCase):
    """Case O-all-fail: every start failed gives the kind all-starts-failed, with start 0's last point if it has one."""

    @classmethod
    def setUpClass(cls):
        state, charge, times, _ = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        cls.tev = stage2.timed(state, charge, times)
        cls.content = stage2.timed_readout([(state, charge, times)])

    def failing(self, with_point):
        def fake(model, tev, start=None):
            if with_point:
                ln_l = joint.log_likelihood(model, tev, start.vertex, start.direction, start.e_vis, start.t0)
                return fit._failed("no-finite-covariance", start, 5, 1, start.vertex, start.direction, start.e_vis, ln_l, 1.0,
                                   "not-positive-definite", t0=start.t0)
            return fit._failed("non-finite", start, 0, 1)
        return fake

    def test_with_a_point(self):
        with unittest.mock.patch.object(multistart.fit, "fit_joint_event", side_effect=self.failing(True)):
            ms = multistart.fit_multistart(MODEL, self.tev, multistart.load())
            text = multistart_product_text(self.content)
        self.assertEqual((ms.result.status, ms.result.failure, ms.chosen, ms.choice), ("failed", multistart.ALL_FAILED, None,
                                                                                      multistart.RULE_ALL_FAILED))
        self.assertEqual(len(ms.starts), 8)
        self.assertTrue(all(r.result.failure == "no-finite-covariance" for r in ms.starts))
        self.assertLess(numpy.abs(ms.result.vertex - ms.starts[0].result.vertex).max(), 1e-15)
        read = product.read_text(text, MODEL, CFG, budget=multistart.load())
        doc = read.events[0]
        self.assertEqual((doc["fit"]["failure"], doc["probability_check"]["point"], doc["choice"]["chosen"]),
                         (multistart.ALL_FAILED, "fit-last", None))

    def test_without_a_point(self):
        with unittest.mock.patch.object(multistart.fit, "fit_joint_event", side_effect=self.failing(False)):
            ms = multistart.fit_multistart(MODEL, self.tev, multistart.load())
            text = multistart_product_text(self.content)
        self.assertEqual((ms.result.failure, ms.result.vertex), (multistart.ALL_FAILED, None))
        doc = product.read_text(text, MODEL, CFG, budget=multistart.load()).events[0]
        self.assertEqual(doc["probability_check"]["point"], "dark-only")
        self.assertTrue(all(s["failure"] == "non-finite" and s["end"] is None for s in doc["starts"]))

    def test_no_hit_channel_has_no_start(self):
        tev = stage2.timed(numpy.zeros(SENSORS, numpy.int8), numpy.zeros(SENSORS), numpy.full(SENSORS, numpy.nan))
        ms = multistart.fit_multistart(MODEL, tev, multistart.load())
        self.assertEqual((ms.result.failure, ms.starts, ms.chosen, ms.choice), ("no-hit-channel", [], None, multistart.RULE_NO_START))


class WrongMaximumRecovered(unittest.TestCase):
    """A hand-made noisy event (stage 2's coding of section 4.3, this stream) on which start 0, the one-seed fit, converges to a
    maximum whose ln L lies at least 0.5 below another start's: multistart reports the higher one. For the one-seed fit the
    event is a clause (a) wrong minimum against the truth-start fit; for the multistart fit it is not."""
    STREAM = (20261111, 300)
    N_EXP = 40.0
    INDEX = 12              # pinned after the first scan of the stream (run-3-wrong-maximum-scan.log); None scans up to LIMIT
    LIMIT = 300

    def draw(self, rng):
        vertex, direction = stage1.draw_source(rng, 0.0, 0.9)
        t0 = float(rng.uniform(10.0, 30.0))
        return vertex, direction, t0, stage2.noisy_timed_event(rng, vertex, direction, self.N_EXP, t0)

    def verdict(self, vertex, direction, t0, tev, budget):
        ms = multistart.fit_multistart(MODEL, tev, budget)
        first = ms.starts[0].result if ms.starts else None
        if first is None or first.status != "converged" or ms.result.status != "converged":
            return None
        ts = t09_truth_start.truth_start_fit(MODEL, tev, vertex, direction, stage1_e_vis(vertex, direction, self.N_EXP), t0)
        if ts.status != "converged":
            return None
        if t09_truth_start.clause_a(first.ln_likelihood, ts.ln_likelihood) and not t09_truth_start.clause_a(ms.result.ln_likelihood,
                                                                                                           ts.ln_likelihood):
            return ms, ts
        return None

    def test_multistart_recovers_the_higher_maximum(self):
        budget = multistart.load()
        rng = numpy.random.default_rng(list(self.STREAM))
        found = None
        for index in range(self.LIMIT if self.INDEX is None else self.INDEX + 1):
            vertex, direction, t0, tev = self.draw(rng)
            if self.INDEX is not None and index != self.INDEX:
                continue
            out = self.verdict(vertex, direction, t0, tev, budget)
            if out is not None:
                found = (index, *out)
                break
        self.assertIsNotNone(found, "no event of the stream shows a wrong maximum of start 0 that another start recovers")
        index, ms, ts = found
        first = ms.starts[0].result
        print(f"\nWRONG-MAXIMUM stream {self.STREAM} index {index}: start 0 ln L {first.ln_likelihood:.4f}, chosen "
              f"{ms.starts[ms.chosen].name!r} ln L {ms.result.ln_likelihood:.4f}, truth-start ln L {ts.ln_likelihood:.4f}",
              file=sys.stderr)
        self.assertNotEqual(ms.chosen, 0)
        self.assertGreaterEqual(ms.result.ln_likelihood - first.ln_likelihood, 0.5)
        self.assertEqual(ms.result.ln_likelihood, max(r.result.ln_likelihood for r in ms.starts if r.result.status == "converged"))


def stage1_e_vis(vertex, direction, n_exp):
    """Truth E_vis = N_exp / (1000 S), section 4.3, by the test's coding."""
    return n_exp / (SENSORS * sum(stage1.text_shape(POSITIONS, NORMALS, tuple(vertex), tuple(direction))))


# --- product /3: the per-start record and its reader ---------------------------------------------------------------------

class MultistartProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        b = stage2.noise_free_timed_event((-1.5, 0.2, 2.0), unit((-0.2, 0.1, -1.0)), 250.0, 22.0, dead=(5, 6, 7))
        cls.content = stage2.timed_readout([a[:3], b[:3]])
        cls.text = multistart_product_text(cls.content)
        cls.budget = multistart.load()

    def test_round_trip_and_header(self):
        read = product.read_text(self.text, MODEL, CFG, budget=self.budget)
        buf = io.StringIO()
        writer = product.Writer(buf, read.header)
        for doc in read.events:
            writer.event(doc)
        writer.finish()
        self.assertEqual(buf.getvalue(), self.text)
        header = read.header
        self.assertEqual(header["format"], "light-likelihood-product/3")
        self.assertEqual(header["budget"], {"format": self.budget.format, "sha256": self.budget.sha256, "starts": list(START_NAMES),
                                            "tie_tolerance": 1e-6})
        self.assertIn("highest ln L", header["fit_settings"]["choice_rule"])
        doc = read.events[0]
        self.assertEqual([s["name"] for s in doc["starts"]], list(START_NAMES))
        self.assertEqual(set(doc["starts"][0]), {"name", "start", "status", "failure", "ln_likelihood", "end", "iterations", "rounds"})
        self.assertEqual(doc["starts"][0]["start"], {k: doc["seed"][k] for k in ("vertex", "direction", "e_vis", "t0")})
        chosen = doc["choice"]["chosen"]
        self.assertEqual(doc["fit"]["ln_likelihood"], doc["starts"][chosen]["ln_likelihood"])
        self.assertEqual(len(doc["fit"]["covariance"]), 7)

    def test_start_zero_is_the_one_seed_fit(self):
        """Case O-start0: start 0 of /3 is stage 2's one-seed fit, field for field, and its seed and prefit are /2's."""
        one = product.read_text(stage2.joint_product_text(self.content), MODEL, CFG).events
        many = product.read_text(self.text, MODEL, CFG, budget=self.budget).events
        for a, b in zip(one, many):
            self.assertEqual(a["seed"], b["seed"])
            self.assertEqual(a["prefit"], b["prefit"])
            s0, f = b["starts"][0], a["fit"]
            self.assertEqual((s0["status"], s0["failure"], s0["ln_likelihood"], s0["iterations"], s0["rounds"]),
                             (f["status"], f["failure"], f["ln_likelihood"], f["iterations"], f["rounds"]))
            self.assertEqual(s0["end"], {"vertex": f["vertex"], "direction": f["direction"], "e_vis": f["e_vis"], "t0": f["t0"]})

    def test_refuses_defects(self):
        header, events, end = lines_of(self.text)
        conv = [i for i, s in enumerate(events[0]["starts"]) if s["status"] == "converged"]
        self.assertGreaterEqual(len(conv), 2, "the noise-free event should converge from at least two starts")
        other = next(i for i in conv if i != events[0]["choice"]["chosen"])

        def changed(change, h=None):
            evs = copy.deepcopy(events)
            change(evs[0])
            return build(h or header, evs, end)

        def move_start(d):
            d["starts"][3]["start"]["vertex"][0] += 1e-3
        cases = {"a start removed": changed(lambda d: d["starts"].pop()),
                 "two starts swapped": changed(lambda d: d["starts"].__setitem__(slice(1, 3), d["starts"][2:0:-1])),
                 "a start point moved": changed(move_start),
                 "a start's ln L that does not recompute": changed(lambda d: d["starts"][conv[-1]].update(
                     ln_likelihood=d["starts"][conv[-1]]["ln_likelihood"] + 1e-3)),
                 "a chosen index that is not the rule's": changed(lambda d: d["choice"].update(chosen=other)),
                 "a rule that is not the rule's": changed(lambda d: d["choice"].update(rule="highest ln L" if d["choice"]["rule"] != "highest ln L" else "tie within tolerance, lowest index")),
                 "a reported fit that is not the chosen start's": changed(lambda d: d["fit"].update(iterations=d["fit"]["iterations"] + 1)),
                 "a truth_start field planted": changed(lambda d: d.update(truth_start={"ln_likelihood": 0.0})),
                 "a start with an unknown kind": changed(lambda d: d["starts"][1].update(status="failed", failure="wrong-minimum")),
                 "budget hash not the file's": build({**header, "budget": {**header["budget"], "sha256": "0" * 64}}, events, end),
                 "budget starts not the file's": build({**header, "budget": {**header["budget"], "starts": list(START_NAMES[:7])}}, events, end),
                 "header without its budget": build({k: v for k, v in header.items() if k != "budget"}, events, end)}
        for name, bad in cases.items():
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad, MODEL, CFG, budget=self.budget)

    def test_a_start_ln_l_is_recomputed_even_where_the_choice_still_holds(self):
        """Mutation run 1: lower a converged start that is not chosen by 1e-3 and restate the choice the rule then gives, so only
        the recomputation of that start's ln L can refuse it."""
        header, events, end = lines_of(self.text)
        evs = copy.deepcopy(events)
        doc = evs[0]
        k = next(i for i, s in enumerate(doc["starts"]) if s["status"] == "converged" and i != doc["choice"]["chosen"])
        doc["starts"][k]["ln_likelihood"] -= 1e-3
        chosen, rule = multistart.choose([(s["status"], s["ln_likelihood"]) for s in doc["starts"]], self.budget.tie_tolerance)
        self.assertEqual(chosen, doc["choice"]["chosen"])
        doc["choice"] = {"chosen": chosen, "rule": rule}
        bad = build(header, evs, end)
        product.read_text(bad, None, CFG, budget=self.budget)          # its structure holds
        with self.assertRaisesRegex(product.ProductError, "does not recompute"):
            product.read_text(bad, MODEL, CFG, budget=self.budget)

    def test_start_record_rules_structure_only(self):
        """Review N1 (mutants R6, R10): a start record never carries all-starts-failed; a converged start needs its end point and
        ln L. Each defect keeps the choice the rule gives, so only the start-record rule can refuse it."""
        header, events, end = lines_of(self.text)
        doc0 = events[0]
        k = next(i for i, s in enumerate(doc0["starts"]) if s["status"] == "converged" and i != doc0["choice"]["chosen"])

        def planted(change):
            evs = copy.deepcopy(events)
            change(evs[0]["starts"][k])
            return build(header, evs, end)

        def all_failed(s):
            s.update(status="failed", failure=multistart.ALL_FAILED)

        def no_end(s):
            s.update(end=None, ln_likelihood=None)
        for name, change in (("a start with all-starts-failed", all_failed), ("a converged start without end or ln L", no_end)):
            with self.subTest(defect=name):
                evs = copy.deepcopy(events)
                change(evs[0]["starts"][k])
                chosen, rule = multistart.choose([(s["status"], s["ln_likelihood"]) for s in evs[0]["starts"]], self.budget.tie_tolerance)
                self.assertEqual(chosen, doc0["choice"]["chosen"])
                evs[0]["choice"] = {"chosen": chosen, "rule": rule}
                with self.assertRaises(product.ProductError):
                    product.read_text(build(header, evs, end), None, CFG, budget=self.budget)

    def test_start_zero_must_be_the_seed_structure_only(self):
        """Mutation run 1: without the model (structure only, as the comparator reads), start 0 must still be the seed."""
        header, events, end = lines_of(self.text)
        evs = copy.deepcopy(events)
        evs[0]["starts"][0]["start"]["t0"] += 0.5
        with self.assertRaisesRegex(product.ProductError, "start 0 is not the seed"):
            product.read_text(build(header, evs, end), None, CFG, budget=self.budget)

    def test_the_new_failure_kind_is_refused_in_product_2(self):
        text = stage2.joint_product_text(self.content)
        header, events, end = lines_of(text)
        evs = copy.deepcopy(events)
        evs[0]["fit"].update(status="failed", failure=multistart.ALL_FAILED, covariance=None, uncertainty_status="not-formed")
        with self.assertRaises(product.ProductError):
            product.read_text(build(header, evs, end), MODEL, CFG)

    def test_every_field_replaced_gives_product_error_or_acceptance(self):
        """Stage 2's N5 rule holds for /3: a malformed field is refused, never an internal error."""
        docs = [json.loads(line) for line in self.text.splitlines()]
        for line_no, doc in enumerate(docs[:2]):
            for path in stage2.leaves(doc):
                if len(path) > 4:
                    continue
                for value in (None, "x", [], {}, -1):
                    bad = stage2.replaced(doc, path, value)
                    if bad == doc:
                        continue
                    lines = [json.dumps(d, sort_keys=True) for d in docs]
                    lines[line_no] = json.dumps(bad, sort_keys=True)
                    try:
                        product.read_text("\n".join(lines) + "\n", MODEL, CFG, budget=self.budget)
                    except product.ProductError:
                        pass
                    except Exception as exc:  # noqa: BLE001 - the defect under test
                        self.fail(f"line {line_no} path {path} value {value!r}: {type(exc).__name__}: {exc}")


# --- the truth-start fit: scoring side only, unreachable from the data side -------------------------------------------------

def audit_run(argv, report):
    """Run photon_likelihood.py with argv under an audit hook; write the opened files and the loaded t09_ modules to report."""
    code = (
        "import json, os, runpy, sys\n"
        "opened = []\n"
        "def hook(event, args):\n"
        "    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):\n"
        "        opened.append(os.path.realpath(os.fsdecode(args[0])))\n"
        "sys.addaudithook(hook)\n"
        f"script, report = {str(ASSETS / 'photon_likelihood.py')!r}, {str(report)!r}\n"
        f"sys.argv = [script] + {list(argv)!r}\n"
        "try:\n"
        "    runpy.run_path(script, run_name='__main__')\n"
        "    code = 0\n"
        "except SystemExit as exc:\n"
        "    code = exc.code\n"
        "mods = sorted(m for m in sys.modules if m.startswith(('t09_', 'gen_', 'check_generators', 'fixture_tools')))\n"
        "json.dump({'code': code, 'opened': opened, 'modules': mods}, open(report, 'w'))\n")
    return subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True, timeout=900)


class TruthUnreachable(unittest.TestCase):
    """V4 section 7 and A09, section 3.1, Freeze A amendment 1: the truth-start fit lives on the scoring side; the recipe never
    reaches a truth file or the truth-start fit."""

    def test_the_recipe_imports_no_scoring_tool(self):
        scan = stage1.RecipeImportsNoGenerator()
        files = sorted((ASSETS / "light_recipe").rglob("*.py")) + [ASSETS / "photon_likelihood.py"]
        self.assertIn(ASSETS / "light_recipe" / "multistart.py", files)
        for path in files:
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(scan.findings_in(text), [])
                tree = ast.parse(text)
                names = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
                names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
                self.assertFalse([m for m in names if m.startswith(("t09_", "fixture_tools", "gen_"))], names)
                self.assertNotIn("t09_truth_start", text)
                self.assertNotIn("truth.npz", text)
        self.assertTrue((ASSETS / "fixture_tools" / "t09_truth_start.py").is_file())

    def test_fit_opens_only_its_inputs_beside_truth_files(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder).resolve()
            gen = TimedGenerator()
            files = stage1.t09_fixture_files.stratum_files(gen, "main", 1, 0, 2, folder, "s")
            ts_path = folder / "s.truth-start.jsonl"
            p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_truth_start.py"), "fit", "--readout",
                                files["readout"]["path"], "--truth", files["truth"]["path"], "--out", str(ts_path)],
                               capture_output=True, text=True, timeout=900)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            report = folder / "audit.json"
            p = audit_run(["fit", "--readout", files["readout"]["path"], "--product", str(folder / "p.jsonl"), "--product-id", "x",
                           "--likelihood", "charge-time", "--starts", "multistart"], report)
            out = json.loads(report.read_text())
            self.assertEqual(out["code"], 0, p.stdout + p.stderr)
            inside = sorted({Path(f).name for f in out["opened"] if Path(f).parent == folder} - {"audit.json"})   # the hook's own report
            self.assertEqual(inside, ["p.jsonl.partial", "s.readout"], inside)
            self.assertEqual(out["modules"], [])
            budget_opened = [f for f in out["opened"] if f.endswith(".budget.json")]
            self.assertEqual(budget_opened, [str(BUDGET_FILE.resolve())])

    def test_no_truth_option_and_the_readers_refuse_truth_files(self):
        p = stage1.run_cli("fit", "--readout", "r", "--product", "p", "--product-id", "x", "--truth", "t")
        self.assertEqual(p.returncode, 2)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            files = stage1.t09_fixture_files.stratum_files(TimedGenerator(), "main", 1, 0, 1, folder, "s")
            ts_path = folder / "s.truth-start.jsonl"
            self.assertEqual(t09_truth_start.main(["fit", "--readout", files["readout"]["path"], "--truth", files["truth"]["path"],
                                                   "--out", str(ts_path)]), 0)
            for path in (ts_path, Path(files["truth"]["path"])):
                with self.subTest(file=path.name), self.assertRaises(readout.ReadoutError):
                    readout.read_file(path)
            p = stage1.run_cli("check-product", "--product", str(ts_path))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"], "rejected")
            p = stage1.run_cli("fit", "--readout", str(ts_path), "--product", str(folder / "x.jsonl"), "--product-id", "x",
                               "--likelihood", "charge-time", "--starts", "multistart")
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))


class TimedGenerator(stage1.HandMadeGenerator):
    """Stage 1's stand-in generator with stage 2's median first-arrival times at t0 20 ns."""

    def event(self, fixture, block, stratum, event_index):
        vertex, direction, n_exp = self.TRUTHS[event_index]
        ev = super().event(fixture, block, stratum, event_index)
        _, _, times, _ = stage2.noise_free_timed_event(vertex, direction, n_exp, 20.0,
                                                       dead=tuple(self.DEAD_CHANNELS) if fixture == "dead" else ())
        ev["data"]["time"] = times
        return ev


class TruthStartFit(unittest.TestCase):
    def test_is_the_recipe_started_at_truth(self):
        vertex, direction = (0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3))
        state, charge, times, e_vis = stage2.noise_free_timed_event(vertex, direction, 400.0, 15.0)
        tev = stage2.timed(state, charge, times)
        got = t09_truth_start.truth_start_fit(MODEL, tev, vertex, direction, e_vis, 15.0)
        want = fit.fit_joint_event(MODEL, tev, fit.JointSeed(numpy.array(vertex), numpy.array(direction), e_vis, 15.0))
        for field in dataclasses.fields(fit.FitResult):
            a, b = getattr(got, field.name), getattr(want, field.name)
            with self.subTest(field=field.name):
                if isinstance(a, numpy.ndarray):
                    self.assertTrue(numpy.array_equal(a, b))
                else:
                    self.assertEqual(a, b)
        self.assertEqual(got.status, "converged")

    def test_file_round_trip_and_refusals(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            files = stage1.t09_fixture_files.stratum_files(TimedGenerator(), "main", 1, 0, 3, folder, "s")
            other = stage1.t09_fixture_files.stratum_files(TimedGenerator(), "dead", 1, 0, 3, folder, "o")
            out = folder / "s.truth-start.jsonl"
            self.assertEqual(t09_truth_start.main(["fit", "--readout", files["readout"]["path"], "--truth", files["truth"]["path"],
                                                   "--out", str(out)]), 0)
            header, docs = t09_truth_start.read_truth_start(out)
            self.assertEqual((header["format"], header["role"], header["events"], len(docs)), ("t09-truth-start/1", "scoring-comparator", 3, 3))
            self.assertEqual(header["readout_sha256"], files["readout"]["sha256"])
            self.assertTrue(all(d["status"] == "converged" and len(d["covariance"]) == 7 for d in docs))
            self.assertEqual(t09_truth_start.main(["fit", "--readout", files["readout"]["path"], "--truth", other["truth"]["path"],
                                                   "--out", str(folder / "x.jsonl")]), 2)
            self.assertFalse((folder / "x.jsonl").exists())
            self.assertEqual(t09_truth_start.main(["fit", "--readout", files["readout"]["path"], "--truth", files["truth"]["path"],
                                                   "--out", str(out)]), 2, "an existing file is never overwritten")
            text = out.read_text().splitlines()
            (folder / "cut.jsonl").write_text("\n".join(text[:-1]) + "\n")
            with self.assertRaises(t09_truth_start.TruthStartError):
                t09_truth_start.read_truth_start(folder / "cut.jsonl")


# --- the clauses (cases O-clause-a, O-clause-b, O-b-where) -------------------------------------------------------------------

class ClauseA(unittest.TestCase):
    def test_boundary(self):
        self.assertEqual(t09_truth_start.CLAUSE_A_LN_L, 0.5)
        self.assertTrue(t09_truth_start.clause_a(-100.5, -100.0))
        self.assertFalse(t09_truth_start.clause_a(-100.4999999, -100.0))
        self.assertFalse(t09_truth_start.clause_a(-99.0, -100.0))
        self.assertTrue(t09_truth_start.clause_a(-1000.0, -10.0))


class ClauseB(unittest.TestCase):
    """Residuals at section 7's truth frame (the test's own coding), sigmas from the truth-start covariance projected there."""
    TRUTH_D = unit((0.3, -0.5, 0.8))

    def setUp(self):
        self.t1, self.t2 = (numpy.array(v) for v in stage1.frame_text(self.TRUTH_D))
        self.truth = {"vertex": numpy.array([1.0, 0.0, -1.0]), "direction": numpy.array(self.TRUTH_D), "e_vis": 1.0, "t0": 20.0}
        self.sig = numpy.array([0.1, 0.2, 0.05, 0.01, 0.02, 0.03, 0.25])
        ts_dir = numpy.array(self.TRUTH_D)              # the truth-start fit at the truth direction: its frame is the truth frame
        self.ts = {"covariance": numpy.diag(self.sig ** 2).tolist(), "direction": ts_dir.tolist(),
                   "frame": {"e1": self.t1.tolist(), "e2": self.t2.tolist()}}

    def point(self, **shift):
        vertex = self.truth["vertex"].copy()
        for k, name in enumerate("xyz"):
            vertex[k] += shift.get(name, 0.0) * self.sig[k]
        d = numpy.array(self.TRUTH_D) + shift.get("u1", 0.0) * self.sig[3] * self.t1 + shift.get("u2", 0.0) * self.sig[4] * self.t2
        d /= numpy.linalg.norm(d)
        return {"vertex": vertex.tolist(), "direction": d.tolist(), "e_vis": 1.0 + shift.get("e_vis", 0.0) * self.sig[5],
                "t0": 20.0 + shift.get("t0", 0.0) * self.sig[6]}

    def test_each_parameter_at_the_boundary(self):
        self.assertEqual(t09_truth_start.CLAUSE_B_SIGMAS, 5.0)
        for name in ("x", "y", "z", "e_vis", "t0"):
            with self.subTest(parameter=name):
                r = t09_truth_start.clause_b_ratios(self.point(**{name: 5.01}), self.truth, self.ts)
                self.assertAlmostEqual(r[name], 5.01, delta=1e-9)
                self.assertTrue(t09_truth_start.clause_b(r))
                self.assertFalse(t09_truth_start.clause_b(t09_truth_start.clause_b_ratios(self.point(**{name: 4.99}), self.truth, self.ts)))
        for name in ("u1", "u2"):
            with self.subTest(parameter=name):
                # (d_fit - d) . e_k after normalisation: a tangent step s gives s / sqrt(1 + s^2), so ask for the residual itself
                big = t09_truth_start.clause_b_ratios(self.point(**{name: 5.2}), self.truth, self.ts)
                small = t09_truth_start.clause_b_ratios(self.point(**{name: 4.9}), self.truth, self.ts)
                s = 5.2 * self.sig[3 if name == "u1" else 4]
                self.assertAlmostEqual(big[name], s / math.sqrt(1 + s * s) / self.sig[3 if name == "u1" else 4], delta=1e-9)
                self.assertTrue(t09_truth_start.clause_b(big))
                self.assertFalse(t09_truth_start.clause_b(small))

    def test_direction_sigma_is_projected_to_the_truth_frame(self):
        """The truth-start fit's frame is at its own direction, here 0.1 rad from the truth; its tangent covariance is
        projected with J_kj = e_k(truth) . e_j(truth-start)."""
        tilted = numpy.array(self.TRUTH_D) + 0.1 * self.t1
        tilted /= numpy.linalg.norm(tilted)
        f1, f2 = (numpy.array(v) for v in stage1.frame_text(tuple(tilted)))
        ts = {**self.ts, "direction": tilted.tolist(), "frame": {"e1": f1.tolist(), "e2": f2.tolist()}}
        jac = numpy.array([[self.t1 @ f1, self.t1 @ f2], [self.t2 @ f1, self.t2 @ f2]])
        tangent = jac @ numpy.diag(self.sig[3:5] ** 2) @ jac.T
        p = self.point(u2=3.0)
        r = t09_truth_start.clause_b_ratios(p, self.truth, ts)
        resid = (numpy.array(p["direction"]) - numpy.array(self.TRUTH_D)) @ self.t2
        self.assertAlmostEqual(r["u2"], abs(resid) / math.sqrt(tangent[1, 1]), delta=1e-9)

    def test_where_clause_b_counts(self):
        cases = {("main", 0): (1, False), ("main", 2): (1, False), ("main", 3): (2, True), ("main", 11): (4, True), ("dead", 0): (3, True),
                 ("saturation", 0): (3, True)}
        for (fixture, stratum), (bin_, counted) in cases.items():
            with self.subTest(fixture=fixture, stratum=stratum):
                header = {"fixture": fixture, "stratum": stratum}
                self.assertEqual(t09_truth_start.bin_of(header), bin_)
                self.assertEqual(t09_truth_start.clause_b_counts(header), counted)


# --- the readings end to end, and the comparator's two gates ------------------------------------------------------------

class ReadingsEndToEnd(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_truth_start.py"), *args],
                              capture_output=True, text=True, timeout=900)

    def test_one_seed_against_multistart(self):
        for fixture in ("main", "dead"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                files = stage1.t09_fixture_files.stratum_files(TimedGenerator(), fixture, 1, 0, 3, folder, "s")
                r, t = files["readout"]["path"], files["truth"]["path"]
                for name, extra in (("one.jsonl", []), ("many.jsonl", ["--starts", "multistart"])):
                    p = stage1.run_cli("fit", "--readout", r, "--product", str(folder / name), "--product-id", "hm", "--likelihood",
                                       "charge-time", *extra)
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = stage1.run_cli("check-product", "--product", str(folder / "many.jsonl"))
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = self.run_tool("fit", "--readout", r, "--truth", t, "--out", str(folder / "ts.jsonl"))
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = self.run_tool("compare", "--one-seed", str(folder / "one.jsonl"), "--multistart", str(folder / "many.jsonl"),
                                  "--truth", t, "--truth-start", str(folder / "ts.jsonl"), "--label", f"hm-{fixture}")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                out = p.stdout
                for fit_name in ("one-seed", "multistart"):
                    self.assertIn(f"READING hm-{fixture} {fit_name} fits events 3", out)
                    self.assertIn(f"READING hm-{fixture} {fit_name} wrong minimum", out)
                    self.assertIn(f"READING hm-{fixture} {fit_name} pull widths", out)
                self.assertIn("clause (b) reported only" if fixture == "main" else "clause (b) counted", out)
                gates = [line for line in out.splitlines() if line.startswith("GATE ")]
                self.assertEqual(len(gates), 2, out)
                self.assertTrue(all(line.endswith("PASS") for line in gates), out)
                p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_readings.py"), "--product",
                                    str(folder / "many.jsonl"), "--truth", t, "--label", "hm"], capture_output=True, text=True, timeout=600)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertIn("pull t0", p.stdout)
                self.assertIn("format light-likelihood-product/3", p.stdout)
                # planted: the one-seed product's event 0 records one more iteration; it still reads, and the start-0 gate fails
                header, events, end = lines_of((folder / "one.jsonl").read_text())
                events[0]["fit"]["iterations"] += 1
                (folder / "bad.jsonl").write_text(build(header, events, end))
                p = self.run_tool("compare", "--one-seed", str(folder / "bad.jsonl"), "--multistart", str(folder / "many.jsonl"),
                                  "--truth", t, "--truth-start", str(folder / "ts.jsonl"), "--label", "bad")
                self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
                self.assertTrue(any(line.startswith("GATE bad start 0") and line.endswith("FAIL") for line in p.stdout.splitlines()),
                                p.stdout)
                p = self.run_tool("compare", "--one-seed", str(folder / "one.jsonl"), "--multistart", str(folder / "many.jsonl"),
                                  "--truth", t, "--truth-start", str(folder / "none.jsonl"), "--label", "x")
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn("unavailable", out)
                if fixture == "main":
                    self.planted_comparator_defects(folder, t)

    def planted_comparator_defects(self, folder, t):
        """Review F4 (mutants R1, R3, R12) and N5: each planted defect gives its exit code and its line."""
        def compare(one, many, ts, label):
            return self.run_tool("compare", "--one-seed", str(one), "--multistart", str(many), "--truth", t, "--truth-start", str(ts),
                                 "--label", label)

        def gate(p, label, which):
            return [line for line in p.stdout.splitlines() if line.startswith(f"GATE {label} {which}")]
        # (1) the one-seed fit's end vertex moved: the start-0 gate fails
        header, events, end = lines_of((folder / "one.jsonl").read_text())
        events[0]["fit"]["vertex"][0] += 0.01
        (folder / "moved.jsonl").write_text(build(header, events, end))
        p = compare(folder / "moved.jsonl", folder / "many.jsonl", folder / "ts.jsonl", "moved")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertTrue(gate(p, "moved", "start 0") and gate(p, "moved", "start 0")[0].endswith("FAIL"), p.stdout)
        # (2) the multistart ln L lowered by 1 throughout event 0 (start records and fit, the choice unchanged): the second gate fails
        header, events, end = lines_of((folder / "many.jsonl").read_text())
        for s in events[0]["starts"]:
            if s["ln_likelihood"] is not None:
                s["ln_likelihood"] -= 1.0
        events[0]["fit"]["ln_likelihood"] -= 1.0
        (folder / "lower.jsonl").write_text(build(header, events, end))
        product.read_text((folder / "lower.jsonl").read_text(), None, CFG, budget=multistart.load())
        p = compare(folder / "one.jsonl", folder / "lower.jsonl", folder / "ts.jsonl", "lower")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertTrue(gate(p, "lower", "multistart ln L") and gate(p, "lower", "multistart ln L")[0].endswith("FAIL"), p.stdout)
        # (3) a truth-start file of another readout, of another truth file, or of another configuration: refused
        lines = (folder / "ts.jsonl").read_text().splitlines()
        for key, label in (("readout_sha256", "other-readout"), ("truth_sha256", "other-truth"), ("configuration_sha256", "other-cfg")):
            with self.subTest(planted=key):
                head = json.loads(lines[0])
                head[key] = "0" * 64
                (folder / f"{label}.jsonl").write_text("\n".join([json.dumps(head, sort_keys=True)] + lines[1:]) + "\n")
                p = compare(folder / "one.jsonl", folder / "many.jsonl", folder / f"{label}.jsonl", label)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn(f"REFUSED {label}", p.stdout)

    def test_counts_on_hand_made_outcomes(self):
        """The comparator's tally on hand-made documents: a fit failure, an unavailable comparator, (a), (b) in B2 and in B1."""
        truth = {"vertex": numpy.zeros((4, 3)), "direction": numpy.tile([0.0, 0.0, 1.0], (4, 1)), "e_vis": numpy.ones(4),
                 "t0": numpy.full(4, 20.0)}
        cov = numpy.diag(numpy.full(7, 0.01)).tolist()
        frame = {"e1": [0.0, 1.0, 0.0], "e2": [-1.0, 0.0, 0.0]}
        ts = [{"status": "converged", "ln_likelihood": -10.0, "covariance": cov, "direction": [0.0, 0.0, 1.0], "frame": frame}] * 4
        ts[1] = {"status": "failed", "ln_likelihood": -9.0, "covariance": None, "direction": None, "frame": None}

        def fitdoc(status, ln_l, x=0.0, failure=None):
            return {"status": status, "failure": failure, "ln_likelihood": ln_l, "vertex": [x, 0.0, 0.0], "direction": [0.0, 0.0, 1.0],
                    "e_vis": 1.0, "t0": 20.0, "covariance": cov, "frame": frame}
        fits = [fitdoc("failed", None, failure="no-finite-covariance"), fitdoc("converged", -10.0), fitdoc("converged", -10.6),
                fitdoc("converged", -10.0, x=0.6)]
        for counted, want_b in ((True, 1), (False, 1)):
            with self.subTest(counted=counted):
                tally = t09_truth_start.tally(fits, ts, truth, counted)
                self.assertEqual((tally["events"], tally["converged"], tally["failures"]), (4, 3, {"no-finite-covariance": 1}))
                self.assertEqual((tally["evaluated"], tally["unavailable"], tally["clause_a"], tally["clause_b"]), (2, 1, 1, want_b))
                self.assertEqual(tally["wrong_minimum"], 2 if counted else 1)
                # review F2: the failed truth-start fit's last point (-9.0) is already 1.0 above the reported fit (-10.0)
                self.assertEqual(tally["unavailable_shows_a"], 1)
        ts[1] = {**ts[1], "ln_likelihood": -9.6}
        self.assertEqual(t09_truth_start.tally(fits, ts, truth, True)["unavailable_shows_a"], 0)
        ts[1] = {**ts[1], "ln_likelihood": None}
        self.assertEqual(t09_truth_start.tally(fits, ts, truth, True)["unavailable_shows_a"], 0)


# --- the command line, the contract, stage 2's re-review nit N2 ------------------------------------------------------------

class MultistartCommandLine(unittest.TestCase):
    def test_fit_check_and_refusals(self):
        a = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "r.readout").write_bytes(stage2.timed_readout([a[:3]]))
            base = ["fit", "--readout", str(folder / "r.readout"), "--product-id", "hm"]
            p = stage1.run_cli(*base, "--product", str(folder / "m.jsonl"), "--likelihood", "charge-time", "--starts", "multistart")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual((out["status"], out["starts"], out["budget_sha256"]), ("ok", "multistart", multistart.load().sha256))
            p = stage1.run_cli("check-product", "--product", str(folder / "m.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["format"], "light-likelihood-product/3")
            # the default and --starts one give stage 2's product, byte for byte
            p = stage1.run_cli(*base, "--product", str(folder / "d.jsonl"), "--likelihood", "charge-time")
            q = stage1.run_cli(*base, "--product", str(folder / "o.jsonl"), "--likelihood", "charge-time", "--starts", "one")
            self.assertEqual((p.returncode, q.returncode), (0, 0))
            self.assertEqual((folder / "d.jsonl").read_bytes(), (folder / "o.jsonl").read_bytes())
            self.assertEqual(json.loads(p.stdout)["budget_sha256"], None)
            p = stage1.run_cli(*base, "--product", str(folder / "c.jsonl"), "--starts", "multistart")
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            self.assertFalse((folder / "c.jsonl").exists())
            (folder / "bad.json").write_text("{}")
            p = stage1.run_cli(*base, "--product", str(folder / "b.jsonl"), "--likelihood", "charge-time", "--starts", "multistart",
                               "--budget", str(folder / "bad.json"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            other = json.loads(BUDGET_FILE.read_text())
            other["tie_tolerance"] = 2e-6
            (folder / "other.json").write_text(json.dumps(other))
            p = stage1.run_cli("check-product", "--product", str(folder / "m.jsonl"), "--budget", str(folder / "other.json"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))
            # review N3: the budget is read for a /3 product only; a /1 or /2 product reads whatever --budget names
            for name in ("d.jsonl", "o.jsonl"):
                p = stage1.run_cli("check-product", "--product", str(folder / name), "--budget", str(folder / "bad.json"))
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = stage1.run_cli("check-product", "--product", str(folder / "m.jsonl"), "--budget", str(folder / "bad.json"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))

    def test_tool_contract_passes(self):
        stage1.CommandLine("test_tool_contract_passes").test_tool_contract_passes()
        doc = json.loads((ROOT / "contracts" / "tool_contracts" / "photon_likelihood.json").read_text(encoding="utf-8"))
        fit_flags = [o["flag"] for o in doc["operations"][0]["invocation"]["options"]]
        check_flags = [o["flag"] for o in doc["operations"][1]["invocation"]["options"]]
        self.assertIn("--starts", fit_flags)
        self.assertIn("--budget", fit_flags)
        self.assertIn("--budget", check_flags)
        self.assertEqual(doc["contract_version"], "1.0.0")

    def test_adapter_lists_the_new_files(self):
        doc = json.loads((ASSETS.parent / "adapter.json").read_text(encoding="utf-8"))
        for asset in ("assets/light_recipe/multistart.py", "assets/fixture_tools/t09_truth_start.py", "assets/t09-multistart-1.budget.json"):
            self.assertIn(asset, doc["assets"])
        self.assertIn("../../tests/adapters/test_photon_likelihood_multistart.py", doc["tests"])


class StageTwoNitN2(unittest.TestCase):
    """Re-review N2: (i) check-product on a /1 and a /2 product whose header line is nested 200,000 deep exits 2, rejected;
    (ii) a /2 event whose prefit failed without a point and whose seed comes from the charge seed is accepted."""

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
        a = stage2.noise_free_timed_event((0.8, 1.0, -0.4), unit((1.0, -0.2, 0.3)), 400.0, 15.0)
        cls.texts = {"charge-only": buf.getvalue(), "charge-time": stage2.joint_product_text(stage2.timed_readout([a[:3]]))}

    def test_a_deep_header_line_through_check_product(self):
        deep = "[" * 200000 + "]" * 200000
        for kind, text in self.texts.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "deep.jsonl"
                path.write_text("\n".join([deep] + text.splitlines()[1:]) + "\n")
                p = stage1.run_cli("check-product", "--product", str(path))
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertEqual(json.loads(p.stdout)["status"], "rejected", p.stdout)

    def test_charge_seed_origin_with_a_failed_prefit_without_a_point(self):
        lines = self.texts["charge-time"].splitlines()
        doc = json.loads(lines[1])
        doc["prefit"].update(status="failed", failure="non-finite", point=False, ln_likelihood=None)
        doc["seed"]["from"] = "charge seed"
        read = product.read_text("\n".join([lines[0], json.dumps(doc, sort_keys=True), lines[2]]) + "\n", MODEL, CFG)
        self.assertEqual(read.events[0]["seed"]["from"], "charge seed")


# --- noisy multistart fits and their cost ---------------------------------------------------------------------------------

class NoisyMultistartFits(unittest.TestCase):
    """Stage 1's seven noisy cases with times (stage 2's stream): every event ends converged or as a counted failure kind; the
    multistart ln L is at least start 0's wherever start 0 converged; the per-channel check holds at the reported point."""

    def test_noisy_events_per_case(self):
        budget = multistart.load()
        lines = []
        for k, (name, n_exp, (r_lo, r_hi), options) in enumerate(stage1.NOISY_CASES):
            rng = numpy.random.default_rng([20261111, 100 + k])
            counts, seconds, better = {}, [], 0
            for _ in range(stage1.NOISY_EVENTS):
                vertex, direction = stage1.draw_source(rng, r_lo, r_hi)
                t0 = float(rng.uniform(10.0, 30.0))
                tev = stage2.noisy_timed_event(rng, vertex, direction, n_exp, t0, **options)
                with self.subTest(case=name):
                    started = time.perf_counter()
                    ms = multistart.fit_multistart(MODEL, tev, budget)
                    seconds.append(time.perf_counter() - started)
                    res = ms.result
                    self.assertIn(res.status, ("converged", "failed"))
                    if res.status == "failed":
                        self.assertIn(res.failure, multistart.FAILURES)
                    first = ms.starts[0].result
                    if first.status == "converged":
                        self.assertEqual(res.status, "converged")
                        self.assertGreaterEqual(res.ln_likelihood, first.ln_likelihood - budget.tie_tolerance)
                        better += res.ln_likelihood > first.ln_likelihood + 0.5
                    check = product.check_at(MODEL, tev.event, ms.anchor, res)
                    self.assertEqual(check["failures"], 0, check)
                    counts[res.failure or "converged"] = counts.get(res.failure or "converged", 0) + 1
            lines.append(f"{name}: {dict(sorted(counts.items()))}, better than start 0 by 0.5: {better}, {1e3 * numpy.mean(seconds):.0f} ms "
                         f"mean, {1e3 * max(seconds):.0f} ms largest")
        print("\nNOISY-MULTISTART " + "; ".join(lines), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
