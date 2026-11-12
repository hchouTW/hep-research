"""adapters/timing-pid, T10 timing lane stage 1: the R35 time-chain records (plan v9.2 R35; t10-timing-stage-plan.md rows R35-1 to
R35-5) and the timing-payload/1 payload, on hand-made hits only. Every expected value is computed here from the conventions of the
stage plan, section 2, never by the recipe's modules.

Run from the plugin root: python -m unittest tests.adapters.test_timing_chain -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "timing-pid" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS))

from timing_recipe import event_time, time_chain, timing_payload  # noqa: E402

TIME_TOLERANCE_NS = 1e-12          # stage plan section 3
SOURCE = "T10 timing lane stage 1 hand-made constants; no measurement (R31)"
MAP_SINGLE = "timing-channel-map/1\ncounters 4\nends 1\nchannel = counter * E + end, counter in [0, N), end in [0, E)\n"


def single_payloads(offsets=(1.0, 2.0, 3.0, 4.0), walks=(0.5, 0.6, 0.7, 0.8), speeds=(15.0, 15.0, 16.0, 16.0)):
    out = {}
    against = []
    for step, values in (("offset", offsets), ("walk", walks), ("propagation", speeds)):
        content = timing_payload.payload_bytes(step, list(values), counters=4, ends=1, origin="nominal", source=SOURCE,
                                               derived_against=list(against))
        out[step] = content
        against.append(hashlib.sha256(content).hexdigest())
    return out


def single_hits():
    # hit_id, track_id, counter, raw time [ns], amplitude [a.u.], distance to the read-out end [cm], path length [cm]
    rows = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 2, 1, 45.0, 64.0, 50.0, 320.0), (12, 3, 2, 50.0, 25.0, 10.0, 350.0),
            (13, 4, 3, 42.0, 400.0, 80.0, 310.0)]
    return [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a, "position_cm": d, "path_length_cm": l}
            for h, t, c, r, a, d, l in rows]


def expected_single(hit, offsets, walks, speeds):
    t1 = hit["raw_time_ns"] - offsets[hit["counter"]]
    t2 = t1 - walks[hit["counter"]] / math.sqrt(hit["amplitude"])
    t3 = t2 - hit["position_cm"] / speeds[hit["counter"]]
    return t1, t2, t3


class PayloadFormat(unittest.TestCase):
    def test_channel_map_identity_is_the_text_hash(self):
        self.assertEqual(timing_payload.channel_map_text(4, 1), MAP_SINGLE)
        self.assertEqual(timing_payload.channel_map_identity(4, 1), hashlib.sha256(MAP_SINGLE.encode()).hexdigest())

    def test_round_trip_and_identity_by_content(self):
        content = single_payloads()["offset"]
        payload = timing_payload.read(content)
        self.assertEqual(payload.step, "offset")
        self.assertEqual(payload.unit, "ns")
        self.assertEqual(payload.identity, hashlib.sha256(content).hexdigest())
        self.assertEqual(list(payload.values), [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(json.loads(content)["format"], "timing-payload/1")

    def test_units_per_step(self):
        loaded = {k: timing_payload.read(v) for k, v in single_payloads().items()}
        self.assertEqual({k: p.unit for k, p in loaded.items()}, {"offset": "ns", "walk": "ns", "propagation": "cm/ns"})

    def _mutated(self, change):
        doc = json.loads(single_payloads()["offset"])
        change(doc)
        return (json.dumps(doc, sort_keys=True, indent=1) + "\n").encode()

    def test_refusals(self):
        cases = {
            "unknown channel": lambda d: d["values"].append([4, 1.0]),
            "repeated channel": lambda d: d["values"].__setitem__(1, [0, 1.0]),
            "missing channel": lambda d: d["values"].pop(),
            "another map": lambda d: d.__setitem__("channel_map", "0" * 64),
            "unknown step": lambda d: d.__setitem__("step", "gain"),
            "wrong unit": lambda d: d.__setitem__("unit", "cm/ns"),
            "extra key": lambda d: d.__setitem__("note", "x"),
            "non-finite": lambda d: d["values"].__setitem__(0, [0, "nan"]),
        }
        for name, change in cases.items():
            with self.subTest(case=name), self.assertRaises(timing_payload.InputError):
                timing_payload.read(self._mutated(change))

    def test_speed_and_walk_must_be_positive_offset_may_be_any_sign(self):
        timing_payload.payload_bytes("offset", [-1.0, 0.0, 2.0, 3.0], 4, 1, "nominal", SOURCE)
        for step in ("walk", "propagation"):
            with self.subTest(step=step), self.assertRaises(timing_payload.InputError):
                timing_payload.payload_bytes(step, [1.0, 0.0, 1.0, 1.0], 4, 1, "nominal", SOURCE)

    def test_derived_payload_has_own_identity_and_source(self):
        parent = single_payloads()["offset"]
        child = timing_payload.derive(parent, {2: 3.1}, "CAI-T10-1 synthetic change")
        p, c = timing_payload.read(parent), timing_payload.read(child)
        self.assertNotEqual(p.identity, c.identity)
        self.assertEqual(c.derived_from, p.identity)
        self.assertEqual(c.changed_channels, (2,))
        self.assertEqual(c.origin, "measured")
        self.assertEqual(list(c.values), [1.0, 2.0, 3.1, 4.0])
        doc = json.loads(child)
        doc["origin"] = "nominal"
        with self.assertRaises(timing_payload.InputError):
            timing_payload.read((json.dumps(doc, sort_keys=True, indent=1) + "\n").encode())


class SingleEndedChain(unittest.TestCase):
    def setUp(self):
        self.contents = single_payloads()
        self.payloads = {k: timing_payload.read(v) for k, v in self.contents.items()}
        self.records = time_chain.correct(single_hits(), self.payloads)

    def test_values_before_and_after_each_step_in_chain_order(self):  # R35-1
        offsets, walks, speeds = (1.0, 2.0, 3.0, 4.0), (0.5, 0.6, 0.7, 0.8), (15.0, 15.0, 16.0, 16.0)
        for hit, record in zip(single_hits(), self.records):
            with self.subTest(hit=hit["hit_id"]):
                t1, t2, t3 = expected_single(hit, offsets, walks, speeds)
                steps = record["steps"]
                self.assertEqual([s["step"] for s in steps], ["offset", "walk", "propagation"])
                self.assertEqual([s["order"] for s in steps], [1, 2, 3])
                self.assertEqual(steps[0]["before_ns"], hit["raw_time_ns"])
                for got, want in zip([s["after_ns"] for s in steps], (t1, t2, t3)):
                    self.assertLessEqual(abs(got - want), TIME_TOLERANCE_NS)
                for prev, nxt in zip(steps, steps[1:]):
                    self.assertEqual(nxt["before_ns"], prev["after_ns"])
                self.assertEqual(record["corrected_time_ns"], steps[-1]["after_ns"])
                for s in steps:
                    self.assertEqual(s["payload_id"], self.payloads[s["step"]].identity)
                self.assertEqual(record["format"], "timing-hit-record/1")
                self.assertEqual(record["readout"], "single-ended")

    def test_amplitude_position_and_path_kept(self):  # R35-2, R35-3, R35-4
        for hit, record in zip(single_hits(), self.records):
            self.assertEqual(record["amplitude"], hit["amplitude"])
            self.assertEqual(record["path_length_cm"], hit["path_length_cm"])
            self.assertEqual(record["position"], {"value_cm": hit["position_cm"], "source": "track",
                                                  "measured_from": "read-out end"})
            self.assertEqual((record["hit_id"], record["track_id"], record["channel"]), (hit["hit_id"], hit["track_id"], hit["counter"]))

    def test_reader_accepts_own_records(self):
        for record in self.records:
            time_chain.check_record(record)

    def test_reader_refuses_broken_records(self):  # R35-1 negative cases
        def swap(r):
            r["steps"][0], r["steps"][1] = r["steps"][1], r["steps"][0]

        def repeat(r):
            r["steps"].insert(1, copy.deepcopy(r["steps"][0]))

        def drop(r):
            r["steps"].pop(1)

        def gap(r):
            r["steps"][1]["before_ns"] += 1e-6

        def no_payload(r):
            r["steps"][2]["payload_id"] = None

        for name, change in {"swapped": swap, "repeated": repeat, "missing": drop, "discontinuous": gap, "no payload": no_payload}.items():
            record = copy.deepcopy(self.records[0])
            change(record)
            with self.subTest(case=name), self.assertRaises(time_chain.InputError):
                time_chain.check_record(record)

    def test_reader_recomputes_applied_values_and_position(self):  # R35-1, fix round 1 M3
        def walk_plus_five(r):  # a walk raised by 5 ns, carried consistently through the later steps
            r["steps"][1]["applied_ns"] += 5.0
            r["steps"][1]["after_ns"] -= 5.0
            r["steps"][2]["before_ns"] -= 5.0
            r["steps"][2]["after_ns"] -= 5.0
            r["corrected_time_ns"] -= 5.0

        def invented_position(r):
            r["position"] = {"value_cm": -3.0, "source": "invented", "measured_from": "read-out end"}

        def offset_not_parameter(r):
            r["steps"][0]["applied_ns"] += 1.0
            r["steps"][0]["after_ns"] -= 1.0
            r["steps"][1]["before_ns"] -= 1.0
            r["steps"][1]["after_ns"] -= 1.0
            r["steps"][2]["before_ns"] -= 1.0
            r["steps"][2]["after_ns"] -= 1.0
            r["corrected_time_ns"] -= 1.0

        for name, change in {"walk +5 ns": walk_plus_five, "invented position": invented_position,
                             "offset not its parameter": offset_not_parameter}.items():
            record = copy.deepcopy(self.records[0])
            change(record)
            with self.subTest(case=name), self.assertRaises(time_chain.InputError):
                time_chain.check_record(record)

    def test_reader_checks_against_the_payloads(self):  # fix round 1 M3
        time_chain.check_record(self.records[0], self.payloads)
        other = {k: timing_payload.read(v) for k, v in single_payloads(walks=(0.9, 0.6, 0.7, 0.8)).items()}
        with self.assertRaises(time_chain.InputError):
            time_chain.check_record(self.records[0], other)          # another walk payload: identity and parameter differ
        record = copy.deepcopy(self.records[0])
        record["steps"][1]["parameter"] = 0.9                         # parameter edited, payload identity kept
        record["steps"][1]["applied_ns"] = 0.9 / math.sqrt(record["amplitude"])
        record["steps"][1]["after_ns"] = record["steps"][1]["before_ns"] - record["steps"][1]["applied_ns"]
        record["steps"][2]["before_ns"] = record["steps"][1]["after_ns"]
        record["steps"][2]["after_ns"] = record["steps"][2]["before_ns"] - record["steps"][2]["applied_ns"]
        record["corrected_time_ns"] = record["steps"][2]["after_ns"]
        time_chain.check_record(record)                               # self-consistent without the payloads
        with self.assertRaises(time_chain.InputError):
            time_chain.check_record(record, self.payloads)

    def test_malformed_records_are_input_errors_not_crashes(self):  # fix round 1 M1
        def string_applied(r):
            r["steps"][1]["applied_ns"] = "0.5"

        def no_steps(r):
            r["steps"] = None

        def step_not_object(r):
            r["steps"][0] = 3

        for name, change in {"string applied": string_applied, "no steps": no_steps, "step not an object": step_not_object}.items():
            record = copy.deepcopy(self.records[0])
            change(record)
            with self.subTest(case=name), self.assertRaises(time_chain.InputError):
                time_chain.check_record(record)

    def test_hit_refusals(self):  # R35-2, R35-3, R35-4 negative cases
        cases = {"no amplitude": ("amplitude", None), "zero amplitude": ("amplitude", 0.0), "no track position": ("position_cm", None),
                 "no path length": ("path_length_cm", None), "unknown counter": ("counter", 7)}
        for name, (key, value) in cases.items():
            hits = single_hits()
            hits[0][key] = value
            with self.subTest(case=name), self.assertRaises(time_chain.InputError):
                time_chain.correct(hits, self.payloads)

    def test_payloads_must_share_the_map_and_be_in_their_steps(self):
        other = timing_payload.read(timing_payload.payload_bytes("walk", [0.5] * 5, 5, 1, "nominal", SOURCE))
        with self.assertRaises(time_chain.InputError):
            time_chain.correct(single_hits(), {**self.payloads, "walk": other})
        with self.assertRaises(time_chain.InputError):
            time_chain.correct(single_hits(), {**self.payloads, "walk": self.payloads["offset"]})


def two_ended_payloads(offsets=(1.0, 1.5, 2.0, 2.5), walks=(0.5, 0.5, 0.6, 0.6), speeds=(15.0, 15.0, 16.0, 16.0)):
    return {step: timing_payload.read(timing_payload.payload_bytes(step, list(values), 2, 2, "nominal", SOURCE))
            for step, values in (("offset", offsets), ("walk", walks), ("propagation", speeds))}


def two_ended_hits():
    return [{"hit_id": 20, "track_id": 1, "counter": 0, "path_length_cm": 300.0, "counter_length_cm": 120.0,
             "ends": [{"end": 0, "raw_time_ns": 47.0, "amplitude": 81.0}, {"end": 1, "raw_time_ns": 49.0, "amplitude": 49.0}]},
            {"hit_id": 21, "track_id": 2, "counter": 1, "path_length_cm": 330.0, "counter_length_cm": 120.0,
             "ends": [{"end": 0, "raw_time_ns": 52.0, "amplitude": 36.0}, {"end": 1, "raw_time_ns": 50.0, "amplitude": 144.0}]}]


class TwoEndedChain(unittest.TestCase):
    def test_both_ends_kept_and_position_and_time_as_derived(self):  # R35-3, stage plan section 2
        offsets, walks, speeds = (1.0, 1.5, 2.0, 2.5), (0.5, 0.5, 0.6, 0.6), (15.0, 15.0, 16.0, 16.0)
        records = time_chain.correct(two_ended_hits(), two_ended_payloads())
        for hit, record in zip(two_ended_hits(), records):
            with self.subTest(hit=hit["hit_id"]):
                self.assertEqual(record["readout"], "two-ended")
                ends = []
                for end in hit["ends"]:
                    channel = hit["counter"] * 2 + end["end"]
                    t1 = end["raw_time_ns"] - offsets[channel]
                    ends.append(t1 - walks[channel] / math.sqrt(end["amplitude"]))
                v = speeds[hit["counter"] * 2]
                mean = 0.5 * (ends[0] + ends[1])
                x = 0.5 * v * (ends[0] - ends[1])
                t0 = mean - hit["counter_length_cm"] / (2 * v)
                got_ends = record["ends"]
                self.assertEqual([e["end"] for e in got_ends], [0, 1])
                for e, want, raw in zip(got_ends, ends, hit["ends"]):
                    self.assertEqual(e["raw_time_ns"], raw["raw_time_ns"])
                    self.assertEqual(e["amplitude"], raw["amplitude"])
                    self.assertEqual([s["step"] for s in e["steps"]], ["offset", "walk"])
                    self.assertLessEqual(abs(e["steps"][-1]["after_ns"] - want), TIME_TOLERANCE_NS)
                prop = record["propagation"]
                self.assertEqual((prop["order"], prop["step"]), (3, "propagation"))
                self.assertLessEqual(abs(prop["mean_time_ns"] - mean), TIME_TOLERANCE_NS)
                self.assertLessEqual(abs(record["position"]["value_cm"] - x), 1e-10)
                self.assertEqual(record["position"]["source"], "two-ended")
                self.assertLessEqual(abs(record["corrected_time_ns"] - t0), TIME_TOLERANCE_NS)
                time_chain.check_record(record)

    def test_malformed_two_ended_records_are_input_errors(self):  # fix round 1 M1, M3
        records = time_chain.correct(two_ended_hits(), two_ended_payloads())
        time_chain.check_record(records[0], two_ended_payloads())

        def end_without_key(r):
            del r["ends"][0]["end"]

        def parameter_none(r):
            r["propagation"]["parameter"] = None

        def end_walk_plus_one(r):
            r["ends"][0]["steps"][1]["applied_ns"] += 1.0
            r["ends"][0]["steps"][1]["after_ns"] -= 1.0

        for name, change in {"end without key": end_without_key, "parameter None": parameter_none,
                             "end walk +1 ns": end_walk_plus_one}.items():
            record = copy.deepcopy(records[0])
            change(record)
            with self.subTest(case=name), self.assertRaises(time_chain.InputError):
                time_chain.check_record(record)

    def test_missing_end_is_refused_never_zero_filled(self):
        hits = two_ended_hits()
        hits[0]["ends"].pop()
        with self.assertRaises(time_chain.InputError):
            time_chain.correct(hits, two_ended_payloads())

    def test_ends_with_different_speeds_are_refused(self):
        payloads = two_ended_payloads(speeds=(15.0, 14.0, 16.0, 16.0))
        with self.assertRaises(time_chain.InputError):
            time_chain.correct(two_ended_hits(), payloads)


C_CM_PER_NS = 29.9792458
BETA_HYP = 1.0


class EventTimeRecords(unittest.TestCase):  # R35-5
    def setUp(self):
        self.records = time_chain.correct(single_hits(), {k: timing_payload.read(v) for k, v in single_payloads().items()})
        self.weights = {10: 0.1, 11: 0.2, 12: 0.3, 13: 0.4}

    def per_hit(self):
        return {r["hit_id"]: r["corrected_time_ns"] - r["path_length_cm"] / (C_CM_PER_NS * BETA_HYP) for r in self.records}

    def test_external(self):
        rec = event_time.external(3.25, "fixture start counter")
        self.assertEqual((rec["format"], rec["source"], rec["estimator"], rec["hits"], rec["value_ns"]),
                         ("timing-event-time/1", "external", "external", [], 3.25))
        event_time.check(rec)

    def test_common_linear_records_hits_and_weights(self):
        rec = event_time.common_linear(self.records, self.weights, BETA_HYP)
        self.assertEqual((rec["source"], rec["estimator"]), ("internal", "linear-fixed-weights"))
        self.assertEqual(rec["hits"], [{"hit_id": h, "weight": w} for h, w in sorted(self.weights.items())])
        self.assertEqual(rec["beta_hypothesis"], BETA_HYP)
        self.assertIsNone(rec["excluded_track"])
        self.assertEqual(rec["excluded_hits"], [])
        want = sum(self.weights[h] * t for h, t in self.per_hit().items())
        self.assertLessEqual(abs(rec["value_ns"] - want), TIME_TOLERANCE_NS)
        event_time.check(rec)

    def test_leave_one_out_excludes_own_hit(self):
        rec = event_time.leave_one_out(self.records, self.weights, BETA_HYP, track_id=3)
        self.assertEqual((rec["excluded_track"], rec["excluded_hits"]), (3, [12]))
        self.assertNotIn(12, [h["hit_id"] for h in rec["hits"]])
        norm = 1.0 - 0.3
        for h in rec["hits"]:
            self.assertLessEqual(abs(h["weight"] - self.weights[h["hit_id"]] / norm), 1e-15)
        want = sum(self.weights[h] / norm * t for h, t in self.per_hit().items() if h != 12)
        self.assertLessEqual(abs(rec["value_ns"] - want), TIME_TOLERANCE_NS)
        event_time.check(rec)

    def test_median_records_its_hits(self):
        rec = event_time.median(self.records, BETA_HYP)
        self.assertEqual(rec["estimator"], "median")
        self.assertEqual([h["hit_id"] for h in rec["hits"]], [10, 11, 12, 13])
        self.assertTrue(all(h["weight"] is None for h in rec["hits"]))
        values = sorted(self.per_hit().values())
        self.assertLessEqual(abs(rec["value_ns"] - 0.5 * (values[1] + values[2])), TIME_TOLERANCE_NS)

    def test_refusals(self):
        with self.assertRaises(event_time.InputError):
            event_time.common_linear(self.records, {10: 0.5, 11: 0.2, 12: 0.3, 13: 0.4}, BETA_HYP)   # sum 1.4
        with self.assertRaises(event_time.InputError):
            event_time.common_linear(self.records, {10: -0.1, 11: 0.4, 12: 0.3, 13: 0.4}, BETA_HYP)  # negative
        with self.assertRaises(event_time.InputError):
            event_time.common_linear(self.records, {10: 0.5, 11: 0.5}, BETA_HYP)                    # hits without weight
        with self.assertRaises(event_time.InputError):
            event_time.common_linear([], {}, BETA_HYP)
        rec = event_time.leave_one_out(self.records, self.weights, BETA_HYP, track_id=3)
        rec["hits"].append({"hit_id": 12, "weight": 0.0})
        with self.assertRaises(event_time.InputError):
            event_time.check(rec)                                                                     # own hit used

    def test_tof_record(self):
        start = event_time.external(3.25, "fixture start counter")
        tof = event_time.tof(self.records[1], start)
        self.assertEqual(tof["format"], "timing-tof/1")
        self.assertEqual((tof["hit_id"], tof["track_id"]), (11, 2))
        self.assertEqual(tof["tof_ns"], self.records[1]["corrected_time_ns"] - 3.25)
        self.assertEqual(tof["beta"], 320.0 / (C_CM_PER_NS * tof["tof_ns"]))
        self.assertEqual(tof["event_time"], {"source": "external", "estimator": "external", "excluded_track": None, "excluded_hits": [],
                                             "value_ns": 3.25, "hit_ids": [], "identity": canonical_identity(start)})
        self.assertEqual(tof["path_length_cm"], 320.0)
        with self.assertRaises(event_time.InputError):
            event_time.tof(self.records[2], event_time.leave_one_out(self.records, self.weights, BETA_HYP, track_id=2))

    def test_tof_names_its_event_time(self):  # fix round 1 M8: a stale event time is distinguishable
        common = event_time.common_linear(self.records, self.weights, BETA_HYP)
        tof = event_time.tof(self.records[0], common)
        self.assertEqual(tof["event_time"]["value_ns"], common["value_ns"])
        self.assertEqual(tof["event_time"]["hit_ids"], [10, 11, 12, 13])
        self.assertEqual(tof["event_time"]["identity"], canonical_identity(common))
        other = event_time.common_linear(self.records, {10: 0.4, 11: 0.3, 12: 0.2, 13: 0.1}, BETA_HYP)
        self.assertNotEqual(event_time.tof(self.records[0], other)["event_time"]["identity"], tof["event_time"]["identity"])


def two_hit_track_records():
    """Track 1 has two timing hits (counters 0 and 1): a track crossing two planes (fix round 1, I1)."""
    hits = single_hits()
    hits[1]["track_id"] = 1
    return time_chain.correct(hits, {k: timing_payload.read(v) for k, v in single_payloads().items()})


class LeaveOneOutByTrack(unittest.TestCase):  # fix round 1 I1
    weights = {10: 0.1, 11: 0.2, 12: 0.3, 13: 0.4}

    def test_every_hit_of_the_track_is_excluded(self):
        records = two_hit_track_records()
        rec = event_time.leave_one_out(records, self.weights, BETA_HYP, track_id=1)
        self.assertEqual((rec["excluded_track"], rec["excluded_hits"]), (1, [10, 11]))
        self.assertEqual([h["hit_id"] for h in rec["hits"]], [12, 13])
        for h in rec["hits"]:
            self.assertLessEqual(abs(h["weight"] - self.weights[h["hit_id"]] / 0.7), 1e-15)
        event_time.check(rec)
        for record in records[:2]:                                    # both hits of track 1 may use it
            event_time.tof(record, rec)
        with self.assertRaises(event_time.InputError):
            event_time.tof(records[2], rec)                           # track 3 may not

    def test_a_record_listing_a_hit_of_its_own_track_is_refused(self):
        rec = event_time.leave_one_out(two_hit_track_records(), self.weights, BETA_HYP, track_id=1)
        rec["hits"].append({"hit_id": 11, "weight": 0.0})
        with self.assertRaises(event_time.InputError):
            event_time.check(rec)

    def test_unknown_track_is_refused(self):
        with self.assertRaises(event_time.InputError):
            event_time.leave_one_out(two_hit_track_records(), self.weights, BETA_HYP, track_id=9)


def canonical_identity(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
