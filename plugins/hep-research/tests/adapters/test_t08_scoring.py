"""D4 stage E6c: T08 scoring on the statistics core (tests/adapters/t08_scoring.py, t04_bin_scorer.py; d4-e6c-brief.md, items 1 and 4).

Every test runs on hand-made inputs: noise-free shower images written as calo-cells/1, reconstructed in process by the recipe's own chain and
clustering (as test_calo_cluster.ProductFormat), and truth arrays written here; no fixture is drawn and no Monte Carlo runs. Sections cited are
of t04-values-v4.md (Freeze A). Expectations, fixed before the first run (d4-e6c-report.md, "Predictions"): each record equals the core's own
call on the same per-event values; v4 5.3's 101 and v4 10's 80; the bilinear target equals the node at a node and the plain mean of the four
corners at the centre of a rectangle; a seed fires at T_s exactly and not below.

Run from the plugin root: python -m unittest tests.adapters.test_t08_scoring -v
"""
from __future__ import annotations

import copy
import dataclasses
import io
import math
import sys
import unittest
from pathlib import Path

import numpy
from scipy import special

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "calo-cluster" / "assets"
for _p in (ROOT, ASSETS, ASSETS / "fixture_tools"):
    sys.path.insert(0, str(_p))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_bin_scorer as scorer_module  # noqa: E402
from tests.adapters import t08_scoring as t08  # noqa: E402
from calo_recipe import cell_chain, cell_input, clustering, configuration, product  # noqa: E402
import t08_readings  # noqa: E402

N = 40
CFG = configuration.load()
EDGES = numpy.arange(N + 1, dtype=float)
REFERENCE = {"iso": 2.907, "dead": 2.855, "sat": 3.485, "edge": {0.5: 1.503, 1.0: 1.633, 1.5: 1.701, 2.0: 1.967},
             "far": {(e, d): 2.0 for e in (250.0, 1000.0, 16000.0) for d in (3.0, 8.0)},
             "near": {(e, d): 3.5 for e in (250.0, 1000.0, 16000.0) for d in (1.5, 3.0)}}


def profile(x, y):
    gx = numpy.diff(special.ndtr(EDGES - x))
    gy = numpy.diff(special.ndtr(EDGES - y))
    return numpy.outer(gx, gy)


def payloads():
    ped = cell_input.payload_bytes("pedestal", "subtract", 0.0, N * N, "adc", "nominal", "hand-made test constant")
    gain = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                    derived_against=[__import__("hashlib").sha256(ped).hexdigest()])
    return ped, gain


def build(showers_per_event, *, dead=None, clip=None):
    """A product of noise-free events (the recipe's chain and clustering, in process) and its truth arrays. showers_per_event: per event a
    list of (E MeV, x, y). dead: a cell (ix, iy) made dead in every event; clip: a clip value in MeV."""
    n = len(showers_per_event)
    raw = numpy.zeros((n, N, N))
    deposit = numpy.zeros((n, 2, N, N))
    for i, showers in enumerate(showers_per_event):
        for s, (e, x, y) in enumerate(showers):
            deposit[i, s] = e * profile(x, y)
        raw[i] = deposit[i].sum(axis=0)
    live = numpy.ones(raw.shape, bool)
    sat = numpy.zeros(raw.shape, bool)
    if dead is not None:
        raw[:, dead[0], dead[1]] = numpy.nan
        live[:, dead[0], dead[1]] = False
        deposit[:, :, dead[0], dead[1]] = 0.0
    if clip is not None:
        sat = raw >= clip
        raw = numpy.where(sat, clip, raw)
    content = cell_input.cells_bytes(raw, live, sat)
    cells = cell_input.read_cells(content)
    ped, gain = (cell_input.read_payload(b) for b in payloads())
    chain = cell_chain.chain_record(ped, gain)
    header = product.header_document("hand-made-e6c", N, N, cells.sha256, cells.events, CFG.sha256, chain)
    stream = io.StringIO()
    writer = product.Writer(stream, header)
    for i in range(cells.events):
        c = cell_chain.apply(cells.raw[i], cells.live[i], cells.saturated[i], ped, gain)
        writer.event(product.event_document(i, c, clustering.cluster_event(c.energy, c.live, c.saturated, CFG), N))
    writer.finish()
    text = stream.getvalue()
    truth = {"energy_mev": numpy.array([s[0][0] for s in showers_per_event]), "n_showers": numpy.array([len(s) for s in showers_per_event]),
             "showers": numpy.full((n, 2, 2), numpy.nan), "d": numpy.full(n, numpy.nan), "t": numpy.full(n, numpy.nan),
             "f_dead": numpy.full(n, numpy.nan), "deposit": deposit, "clip_reference_mev": numpy.full(n, numpy.nan)}
    for i, showers in enumerate(showers_per_event):
        for s, (_, x, y) in enumerate(showers):
            truth["showers"][i, s] = (x, y)
        if len(showers) == 2:
            truth["d"][i] = math.dist(showers[0][1:], showers[1][1:])
    return product.read_text(text), truth, content, text, sat


def header_of(fixture, stratum, block, events, separation):
    return {"fixture": fixture, "stratum": stratum, "block": block, "events": events, "separation": separation}


def iso_events(n, energy, *, offset=0.0):
    return [[(energy, 20.3 + 0.01 * (i % 7) + offset, 19.6 + 0.013 * (i % 5))] for i in range(n)]


def far_events(n, energy, d=4.0):
    return [[(energy, 15.0 + 0.01 * i % 1, 20.0), (energy, 15.0 + d, 20.0 + 0.01 * (i % 3))] for i in range(n)]


class TestCount(unittest.TestCase):
    def test_101_tests_and_80_required(self):
        self.assertEqual(t08.count_tests(), {"total": 101, "required": 80, "iso": 40, "far": 43, "near": 12, "controls": 6})

    def test_e1_pulls_ungated_and_21(self):
        ungated = [(k.name, g) for k in t08.ALL_BINS for g in t08.gates_of_bin(k) if not g[2]]
        self.assertEqual(len(ungated), 21)
        self.assertTrue(all(name.startswith("main-E1-") for name, _ in ungated))
        self.assertTrue(all(g[0] != "efficiency" for _, g in ungated))

    def test_merge_only_in_far_e2_to_e4_and_no_saturation_test(self):
        merges = [k.name for k in t08.ALL_BINS for g in t08.gates_of_bin(k) if g[0] == "merge"]
        self.assertEqual(merges, ["main-E2-far", "main-E3-far", "main-E4-far"])
        self.assertEqual(t08.gates_of_bin(t08.bin_kind(8004, 0)), [])

    def test_a_changed_count_is_refused(self):
        original = t08.gates_of_bin

        def one_more(kind):
            return original(kind) + ([("extra", "rate", True, "")] if kind.name == "edge-E3" else [])
        t08.gates_of_bin = one_more
        try:
            with self.assertRaises(scorer_module.ScoringError):
                t08.count_tests()
        finally:
            t08.gates_of_bin = original


class BinScorerPaths(unittest.TestCase):
    def test_block_refusal(self):
        for block in (2, 5, 6, 13):
            with self.subTest(block=block), self.assertRaises(scorer_module.ScoringError):
                scorer_module.BinScorer(core.BinIdentity("T08", 8001, block, 3))

    def test_development_efficiency_is_the_cores_flip(self):
        m = numpy.ones(4000, dtype=numpy.int64)
        failures = numpy.zeros(4000, dtype=numpy.int64)
        failures[:5] = 1
        evaluated = core.efficiency_test("efficiency", core.BinIdentity("T08", 8001, 11, 3), m, failures, 0.99)
        rate = core.rate_test("efficiency", core.BinIdentity("T08", 8001, 11, 3), m, failures, 1 - 0.99, min_events=3000)
        self.assertEqual(scorer_module.as_efficiency(rate, 0.99), evaluated)

    def test_development_records_are_labelled_and_never_evaluation(self):
        s = scorer_module.BinScorer(core.BinIdentity("T08", 8001, 1, 3))
        records = s.pulls("energy pulls", [[0.1], [-0.2], [0.3], [0.0]])
        self.assertTrue(all(r.bin.startswith(scorer_module.DEVELOPMENT_LABEL) for r in records))
        self.assertTrue(all(r.readings.get("label") == scorer_module.DEVELOPMENT_LABEL for r in records))
        self.assertIn("no verdict", scorer_module.record_line(records[0]))

    def test_pulls_equal_the_cores_calls_on_block_11(self):
        identity = core.BinIdentity("T08", 8001, 11, 3)
        rng = numpy.random.Generator(numpy.random.PCG64(7))   # hand-made numbers, not a fixture draw
        per_event = [list(rng.normal(0, 1, k)) for k in rng.integers(0, 3, 200)]
        per_event[3] = [4.0]
        records = scorer_module.BinScorer(identity).pulls("energy pulls", per_event)
        centre, width = core.pull_tests("energy pulls", identity, per_event)
        counts = numpy.array([len(e) for e in per_event])
        beyond = numpy.array([sum(abs(v) > 3 for v in e) for e in per_event])
        tail = core.rate_test("energy pulls", identity, counts, beyond, 0.01, statistic="tail")
        self.assertEqual(records, [centre, width, tail])

    def test_ungated_pulls_are_inconclusive_required_no(self):
        records = scorer_module.BinScorer(core.BinIdentity("T08", 8001, 11, 0)).pulls("energy pulls", [[0.1]] * 50, required=False, reason="E1")
        self.assertEqual([(r.result, r.required, r.reason) for r in records], [("inconclusive", False, "E1")] * 3)

    def test_records_round_trip_as_json(self):
        record = scorer_module.BinScorer(core.BinIdentity("T08", 8001, 12, 3)).rate("merge", [1] * 10, [0] * 10, 0.01)
        self.assertEqual(scorer_module.record_of(scorer_module.record_document(record)), record)
        self.assertEqual(record.confidence, 0.99)


class Targets(unittest.TestCase):
    def test_bilinear_at_nodes_and_between(self):
        table = {(250.0, 3.0): 1.0, (250.0, 8.0): 2.0, (1000.0, 3.0): 3.0, (1000.0, 8.0): 5.0}
        for (e, d), value in table.items():
            self.assertAlmostEqual(t08_readings.bilinear(table, e, d), value, places=12)
        self.assertAlmostEqual(t08_readings.bilinear(table, 500.0, 5.5), (1 + 2 + 3 + 5) / 4, places=12)   # ln 500 is the middle of ln 250, ln 1000
        self.assertAlmostEqual(t08_readings.bilinear(table, 250.0, 5.5), 1.5, places=12)
        with self.assertRaises(t08_readings.ReadingError):
            t08_readings.bilinear(table, 249.0, 5.0)
        with self.assertRaises(t08_readings.ReadingError):
            t08_readings.bilinear(table, 500.0, 8.5)

    def test_far_pull_uses_the_interpolated_target(self):
        events = far_events(3, 1000.0, d=5.5)
        prod, truth, _, _, _ = build(events)
        ref = copy.deepcopy(REFERENCE)
        ref["far"] = {(e, d): (1.0 if d == 3.0 else 3.0) for e in (250.0, 1000.0, 16000.0) for d in (3.0, 8.0)}
        match = t08_readings.match_event(prod.events[0], truth["deposit"][0], 2)
        pulls = t08_readings.event_pulls(prod.events[0], "main", "far", 0, truth, ref, match)
        k = match["primary"][0]
        cluster = prod.events[0]["objects"][k]
        self.assertAlmostEqual(pulls["energy"][0], (cluster["energy"] - (1000.0 - 2.0)) / cluster["sigma_energy"], places=12)


class EfficiencyReference(unittest.TestCase):
    def test_lower_limits(self):
        self.assertAlmostEqual(t08.efficiency_lower_limit(0.9924), 0.9824, places=12)
        self.assertAlmostEqual(t08.efficiency_lower_limit(1.000), 0.99, places=12)

    def test_a_node_interpolation_would_understate_r_in_e1(self):
        """The log's `closed` column at the iso nodes 80, 100, 125 MeV (job 7479146: 0.84020, 0.99954, 1.00000): linear in ln E over E1 it gives
        0.984, against v4's integral 0.9924; the bin constant is v4's."""
        nodes = numpy.log([80.0, 100.0, 125.0, 250.0])
        p = [0.84020, 0.99954, 1.0, 1.0]
        x = numpy.linspace(math.log(80), math.log(250), 200001)[:-1]
        chord = float(numpy.interp(x, nodes, p).mean())
        self.assertLess(chord, t08.REFERENCE_EFFICIENCY[0] - 0.007)
        self.assertEqual(t08.REFERENCE_EFFICIENCY, {0: 0.9924, 1: 1.0, 2: 1.0, 3: 1.0})


class SeedFiring(unittest.TestCase):
    def event(self, values):
        return {"cells": [[c, v, 0.0, v, 1.0, v, 0, 0] for c, v in values]}

    def test_fires_at_the_threshold_and_not_below(self):
        deposit = numpy.zeros((2, N, N))
        deposit[0].flat[100] = 10.0
        self.assertEqual(t08.seed_fired(self.event([(100, 10.0)]), deposit, 1), [True])
        self.assertEqual(t08.seed_fired(self.event([(100, numpy.nextafter(10.0, 0.0))]), deposit, 1), [False])

    def test_each_shower_alone_by_its_largest_deposit(self):
        deposit = numpy.zeros((2, N, N))
        deposit[0].flat[100], deposit[1].flat[100] = 6.0, 5.0
        deposit[0].flat[900], deposit[1].flat[900] = 0.5, 11.0
        self.assertEqual(t08.seed_fired(self.event([(100, 11.0)]), deposit, 2), [True, False])
        self.assertEqual(t08.seed_fired(self.event([(100, 11.0), (900, 11.5)]), deposit, 2), [True, True])
        self.assertEqual(t08.seed_fired(self.event([(900, 9.0)]), deposit, 2), [False, False])


class Wiring(unittest.TestCase):
    def test_iso_e2_records_are_the_cores_on_the_same_values(self):
        events = iso_events(30, 600.0)
        prod, truth, _, _, _ = build(events)
        identity = core.BinIdentity("T08", 8001, 11, 3)
        score = t08.score_sample(identity, prod.events, header_of("main", 3, 11, 30, "iso"), truth, REFERENCE, products_header=prod.header)
        self.assertEqual([(r.gate, r.statistic) for r in score.records], [(g, s) for g, s, _, _ in t08.gates_of_bin(t08.bin_kind(8001, 3))])
        per = {"energy": [], "x": [], "y": []}
        for i, ev in enumerate(prod.events):
            m = t08_readings.match_event(ev, truth["deposit"][i], 1)
            found = t08_readings.event_pulls(ev, "main", "iso", i, truth, REFERENCE, m)
            for key in per:
                per[key].append(found.get(key, []))
        s = scorer_module.BinScorer(identity)
        want = s.pulls("energy pulls", per["energy"]) + s.pulls("position x pulls", per["x"]) + s.pulls("position y pulls", per["y"])
        want.append(s.efficiency("efficiency", [1] * 30, [0] * 30, 0.99))
        self.assertEqual(score.records, want)
        self.assertTrue(all(r.required for r in score.records))
        self.assertEqual(score.records[-1].result, "inconclusive")       # 30 events < N_min 3,000: step 2
        self.assertEqual(score.records[-1].step, 2)

    def test_e1_iso_pulls_ungated_efficiency_required(self):
        prod, truth, _, _, _ = build(iso_events(10, 120.0))
        score = t08.score_sample(core.BinIdentity("T08", 8001, 11, 0), prod.events, header_of("main", 0, 11, 10, "iso"), truth, REFERENCE)
        self.assertEqual([r.required for r in score.records], [False] * 9 + [True])
        self.assertTrue(all(r.result == "inconclusive" and r.reason == t08.E1_REASON for r in score.records[:9]))
        self.assertAlmostEqual(score.records[-1].limit, 0.9824, places=12)

    def test_far_e2_has_merge_and_seed_efficiency(self):
        prod, truth, _, _, _ = build(far_events(12, 800.0, d=5.0))
        score = t08.score_sample(core.BinIdentity("T08", 8001, 11, 4), prod.events, header_of("main", 4, 11, 12, "far"), truth, REFERENCE)
        eff = [r for r in score.records if r.gate == "efficiency"][0]
        merge = [r for r in score.records if r.gate == "merge"][0]
        self.assertEqual((eff.readings["objects"], eff.readings["failures"]), (24, 0))
        self.assertEqual((merge.readings["objects"], merge.readings["failures"]), (12, 0))

    def test_merge_is_counted_per_event(self):
        prod, truth, _, _, _ = build(far_events(4, 800.0, d=1.2))     # 1.2 W apart: one object holds both
        truth["d"][:] = 3.0                                              # the target's d inside the far nodes; merge reads the product only
        score = t08.score_sample(core.BinIdentity("T08", 8001, 11, 4), prod.events, header_of("main", 4, 11, 4, "far"), truth, REFERENCE)
        merge = [r for r in score.records if r.gate == "merge"][0]
        self.assertEqual(merge.readings["failures"], 4)

    def test_another_bin_is_refused(self):
        prod, truth, _, _, _ = build(iso_events(3, 600.0))
        for header in (header_of("main", 6, 11, 3, "iso"), header_of("main", 3, 12, 3, "iso"), header_of("edge", 3, 11, 3, "iso"),
                       header_of("main", 3, 11, 4, "iso")):
            with self.subTest(header=header), self.assertRaises(scorer_module.ScoringError):
                t08.score_sample(core.BinIdentity("T08", 8001, 11, 3), prod.events, header, truth, REFERENCE)

    def test_a_product_of_another_configuration_is_refused(self):
        prod, truth, _, _, _ = build(iso_events(3, 600.0))
        other = copy.deepcopy(prod.header)
        other["configuration"]["sha256"] = "0" * 64
        with self.assertRaises(scorer_module.ScoringError):
            t08.score_sample(core.BinIdentity("T08", 8001, 11, 3), prod.events, header_of("main", 3, 11, 3, "iso"), truth, REFERENCE,
                             products_header=other)

    def test_edge_pools_the_four_t(self):
        events = [[(2000.0, 0.5 + t - 0.5 + 6, 20.0)] for t in (0.5, 1.0, 1.5, 2.0)] * 3
        prod, truth, _, _, _ = build(events)
        truth["t"] = numpy.array([0.5, 1.0, 1.5, 2.0] * 3)
        score = t08.score_sample(core.BinIdentity("T08", 8002, 11, 0), prod.events, header_of("edge", 0, 11, 12, "iso"), truth, REFERENCE)
        self.assertEqual([(r.gate, r.statistic) for r in score.records], [("edge energy pulls", s) for s in ("trimmed-centre", "sigma68-width", "tail")])
        self.assertEqual(score.records[0].readings["objects"], 12)


class Deterministic(unittest.TestCase):
    def test_conservation_and_fractions(self):
        prod, _, _, _, _ = build(iso_events(1, 600.0))
        ev = prod.events[0]
        self.assertEqual(t08.conservation_defects(ev), [])
        broken = copy.deepcopy(ev)
        broken["unclustered_sum"] += 1e-3
        self.assertTrue(t08.conservation_defects(broken))
        broken = copy.deepcopy(ev)
        broken["objects"][0]["members"][0][1] = 0.5
        self.assertTrue(any("fractions" in d for d in t08.conservation_defects(broken)))

    def test_dead_cell_never_in_a_cluster(self):
        prod, _, _, _, _ = build(iso_events(1, 2000.0), dead=(20, 19))
        ev = prod.events[0]
        self.assertEqual(t08.dead_cell_defects(ev), [])
        broken = copy.deepcopy(ev)
        broken["dead_channels"].append(broken["cells"][0][0])
        self.assertTrue(t08.dead_cell_defects(broken))

    def test_saturation_flag_zero_exceptions(self):
        prod, _, _, _, sat = build(iso_events(1, 8000.0), clip=400.0)
        ev = prod.events[0]
        self.assertTrue(any(row[6] for row in ev["cells"]))
        self.assertEqual(t08.saturation_defects(ev, sat[0]), [])
        broken = copy.deepcopy(ev)
        broken["objects"][0]["saturated"] = False
        self.assertTrue(t08.saturation_defects(broken, sat[0]))
        other = numpy.zeros_like(sat[0])
        self.assertTrue(t08.saturation_defects(ev, other))      # the product's flags against another readout's

    def test_checks_carry_the_stop(self):
        prod, truth, _, _, _ = build(iso_events(2, 600.0))
        score = t08.score_sample(core.BinIdentity("T08", 8001, 11, 3), prod.events, header_of("main", 3, 11, 2, "iso"), truth, REFERENCE)
        score.defects["double-count"].append("event 0: planted")
        checks = {c.name: c for c in t08.sample_checks(score)}
        self.assertEqual((checks["double-count main-E2-iso"].result, checks["double-count main-E2-iso"].stop), ("fail", True))
        self.assertEqual(checks["conservation main-E2-iso"].result, "pass")


class NegativeCases(unittest.TestCase):
    def test_digital_and_incident_are_refused(self):
        _, _, content, text, _ = build(iso_events(2, 600.0))
        self.assertTrue(t08.negative_digital_as_analog(content)[0])
        self.assertTrue(t08.negative_deposited_as_incident(text)[0])
        self.assertEqual([c.result for c in t08.negative_checks(content, text)], ["pass", "pass"])


class MissingOutput(unittest.TestCase):
    def test_a_missing_bin_keeps_every_test_and_fails_the_workflow(self):
        records = []
        for kind in t08.ALL_BINS:
            records += t08.missing_records(core.BinIdentity("T08", kind.fixture_id, 11, kind.stratum), "the range task crashed")
        self.assertEqual(len(records), 101)
        self.assertEqual(sum(r.required for r in records), 80)
        outcome = core.workflow_outcome("T08", records, [], attempt=1, found_obligations=t08.FOUND_OBLIGATIONS, required_checks=())
        self.assertEqual((outcome.workflow_result, outcome.r11_state), ("fail", "failed"))
        self.assertIn("a required check was inconclusive (R11)", outcome.reasons)
        self.assertTrue(all("required output missing" in r.reason or not r.required for r in records))


class LimitsAndRequiredChecks(unittest.TestCase):
    """Fix round 1 (review M8, I2): the limits of v4 9.1 and 6 on the records, the near target, the required checks."""

    def test_merge_and_tail_limits(self):
        prod, truth, _, _, _ = build(far_events(4, 800.0, d=5.0))
        score = t08.score_sample(core.BinIdentity("T08", 8001, 11, 4), prod.events, header_of("main", 4, 11, 4, "far"), truth, REFERENCE)
        limits = {(r.gate, r.statistic): r.limit for r in score.records}
        self.assertEqual(limits[("merge", "rate")], 0.01)
        self.assertEqual(limits[("energy pulls", "tail")], 0.01)
        self.assertEqual(limits[("energy pulls", "trimmed-centre")], 0.10)

    def test_near_target_is_2e_minus_b_near(self):
        prod, truth, _, _, _ = build(far_events(1, 1000.0, d=2.0))
        truth["d"][:] = 2.0
        ev = prod.events[0]
        match = t08_readings.match_event(ev, truth["deposit"][0], 2)
        pulls = t08_readings.event_pulls(ev, "main", "near", 0, truth, REFERENCE, match)
        self.assertAlmostEqual(pulls["energy"][0], (ev["event_sum"]["energy"] - (2 * 1000.0 - 3.5)) / ev["event_sum"]["sigma"], places=12)

    def test_required_checks(self):
        names = t08.required_checks()
        self.assertEqual(len(names), 15 * 3 + 2 + 2 + 3)
        self.assertIn("dead cell in a cluster dead-E3", names)
        self.assertIn("saturation flag saturation-E4", names)
        self.assertEqual(names[-3:], ("CAI-T08-1", "CAI-T08-2", "reference selection (A38.1)"))
        records = [r for k in t08.ALL_BINS for r in t08.missing_records(core.BinIdentity("T08", k.fixture_id, 11, k.stratum), "x")]
        with self.assertRaises(core.CoreError):
            core.workflow_outcome("T08", records, [core.CheckResult(n, "deterministic", "pass") for n in names[1:]], attempt=1, required_checks=names)


class NoRecipeImportsTheScoring(unittest.TestCase):
    def test_no_recipe_file_names_the_scoring_modules(self):
        names = ("t08_scoring", "t09_scoring", "t04_bin_scorer", "t04_evaluation_tasks")
        files = [ASSETS / "calo_cluster.py", *sorted((ASSETS / "calo_recipe").glob("*.py")),
                 ROOT / "adapters/photon-likelihood/assets/photon_likelihood.py", *sorted((ROOT / "adapters/photon-likelihood/assets/light_recipe").glob("*.py"))]
        self.assertGreaterEqual(len(files), 20)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for name in names:
                self.assertNotIn(name, text, f"{path} names {name}")


if __name__ == "__main__":
    unittest.main()
