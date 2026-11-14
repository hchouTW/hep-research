"""adapters/timing-pid, T10 timing lane stage 1: the calibration-interface checks CAI-T10-1 and CAI-T10-2 of plan v9.2 R37, on
hand-made hits only (t10-timing-stage-plan.md, rows CAI-T10-1a to f and CAI-T10-2; tolerances in its section 3, fixed before the
code was written).

Two layers. First, the recipe itself under a changed offset payload, against expectations computed here from the stage plan's
section 2 (the R37 formulas and the two-ended derivation marked there "derived here, not from a source"). Second, the scoring-side
check fixture_tools/t10_cai.py: it must PASS on the recipe and FAIL under each planted defect, so the check can see what it claims to.

Run from the plugin root: python -m unittest tests.adapters.test_timing_cai -v
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "timing-pid" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from timing_recipe import event_time, time_chain, timing_payload  # noqa: E402
import t10_cai  # noqa: E402

DELTA_NS = 0.1                    # the recorded finite step, halved to 0.05 ns (stage plan section 3)
TIME_TOL_NS = 1e-12
POSITION_TOL_CM = 1e-10
BETA_REL_TOL = 1e-12
C_CM_PER_NS = 29.9792458
BETA_HYP = 1.0
SOURCE = "T10 timing lane stage 1 hand-made constants; no measurement (R31)"
WEIGHTS = {10: 0.1, 11: 0.2, 12: 0.3, 13: 0.4}
T0_EXTERNAL = 3.25
OFFSETS, WALKS, SPEEDS = [1.0, 2.0, 3.0, 4.0], [0.5, 0.6, 0.7, 0.8], [15.0, 15.0, 16.0, 16.0]


def contents(offsets=OFFSETS, counters=4, ends=1, walks=WALKS, speeds=SPEEDS):
    return {step: timing_payload.payload_bytes(step, list(values), counters, ends, "nominal", SOURCE)
            for step, values in (("offset", offsets), ("walk", walks), ("propagation", speeds))}


def read_all(raw):
    return {k: timing_payload.read(v) for k, v in raw.items()}


def hits():
    rows = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 2, 1, 45.0, 64.0, 50.0, 320.0), (12, 3, 2, 50.0, 25.0, 10.0, 350.0),
            (13, 4, 3, 42.0, 400.0, 80.0, 310.0)]
    return [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a, "position_cm": d, "path_length_cm": l}
            for h, t, c, r, a, d, l in rows]


def changed(raw, channel, delta):
    return {**raw, "offset": timing_payload.derive(raw["offset"], {channel: OFFSETS[channel] + delta}, "CAI-T10-1 synthetic change")}


def corrected(records):
    return {r["hit_id"]: r["corrected_time_ns"] for r in records}


def offset_corrected(records):
    return {r["hit_id"]: r["steps"][0]["after_ns"] for r in records}


class SingleEndedRecipe(unittest.TestCase):  # CAI-T10-1, the recipe against the R37 formulas
    channel, hit_k = 2, 12

    def run_pair(self, delta):
        raw = contents()
        return time_chain.correct(hits(), read_all(raw)), time_chain.correct(hits(), read_all(changed(raw, self.channel, delta)))

    def test_offset_moves_own_hits_by_minus_delta_others_by_zero(self):  # 1a
        for delta in (DELTA_NS, DELTA_NS / 2):
            before, after = self.run_pair(delta)
            b, a = offset_corrected(before), offset_corrected(after)
            for h in b:
                with self.subTest(delta=delta, hit=h):
                    if h == self.hit_k:
                        self.assertLessEqual(abs((a[h] - b[h]) - (-delta)), TIME_TOL_NS)
                    else:
                        self.assertEqual(a[h] - b[h], 0.0)
            full_b, full_a = corrected(before), corrected(after)
            self.assertLessEqual(abs((full_a[self.hit_k] - full_b[self.hit_k]) - (-delta)), TIME_TOL_NS)   # dt_k = -delta
            # applied once and first: the offset step's applied value is the payload's, and it is step 1
            k_after = next(r for r in after if r["hit_id"] == self.hit_k)
            self.assertEqual(k_after["steps"][0]["step"], "offset")
            self.assertEqual(sum(s["step"] == "offset" for s in k_after["steps"]), 1)
            self.assertLessEqual(abs(k_after["steps"][0]["applied_ns"] - (OFFSETS[self.channel] + delta)), TIME_TOL_NS)

    def tofs(self, records, start_of):
        return {r["hit_id"]: event_time.tof(r, start_of(r), records)["tof_ns"] for r in records}

    def test_external_event_time(self):  # 1b
        before, after = self.run_pair(DELTA_NS)
        start = event_time.external(T0_EXTERNAL, "fixture start counter")
        dt_k = corrected(after)[self.hit_k] - corrected(before)[self.hit_k]
        for rb, ra in zip(before, after):
            tb, ta = event_time.tof(rb, start), event_time.tof(ra, start)
            with self.subTest(hit=rb["hit_id"]):
                if rb["hit_id"] == self.hit_k:
                    self.assertLessEqual(abs((ta["tof_ns"] - tb["tof_ns"]) - dt_k), TIME_TOL_NS)
                    want = rb["path_length_cm"] / (C_CM_PER_NS * (tb["tof_ns"] + dt_k))
                    self.assertLessEqual(abs(ta["beta"] - want) / want, BETA_REL_TOL)
                    self.assertNotEqual(ta["beta"], tb["beta"])
                else:
                    self.assertEqual(ta["tof_ns"], tb["tof_ns"])
                    self.assertEqual(ta["beta"], tb["beta"])

    def test_common_linear_event_time(self):  # 1c
        before, after = self.run_pair(DELTA_NS)
        eb, ea = event_time.common_linear(before, WEIGHTS, BETA_HYP), event_time.common_linear(after, WEIGHTS, BETA_HYP)
        dt_k = corrected(after)[self.hit_k] - corrected(before)[self.hit_k]
        w_k = WEIGHTS[self.hit_k]
        self.assertLessEqual(abs((ea["value_ns"] - eb["value_ns"]) - w_k * dt_k), TIME_TOL_NS)
        tb, ta = self.tofs(before, lambda r: eb), self.tofs(after, lambda r: ea)
        for h in tb:
            want = (1 - w_k) * dt_k if h == self.hit_k else -w_k * dt_k
            with self.subTest(hit=h):
                self.assertLessEqual(abs((ta[h] - tb[h]) - want), TIME_TOL_NS)

    def test_leave_one_out_event_time(self):  # 1d
        before, after = self.run_pair(DELTA_NS)
        dt_k = corrected(after)[self.hit_k] - corrected(before)[self.hit_k]

        def loo(records):
            return lambda r: event_time.leave_one_out(records, WEIGHTS, BETA_HYP, track_id=r["track_id"])

        tb, ta = self.tofs(before, loo(before)), self.tofs(after, loo(after))
        for h in tb:
            if h == self.hit_k:
                want = dt_k
            else:
                want = -WEIGHTS[self.hit_k] / (1.0 - WEIGHTS[h]) * dt_k      # w_k^(-j) = w_k / sum_{l != j} w_l
            with self.subTest(hit=h):
                self.assertLessEqual(abs((ta[h] - tb[h]) - want), TIME_TOL_NS)

    def test_beta_forward_difference_halves(self):  # 1f, beta
        start = event_time.external(T0_EXTERNAL, "fixture start counter")
        errors = []
        for delta in (DELTA_NS, DELTA_NS / 2):
            before, after = self.run_pair(delta)
            rb = next(r for r in before if r["hit_id"] == self.hit_k)
            ra = next(r for r in after if r["hit_id"] == self.hit_k)
            tb, ta = event_time.tof(rb, start), event_time.tof(ra, start)
            derivative = tb["beta"] / tb["tof_ns"]                       # d beta / d delta, TOF = TOF_0 - delta
            errors.append(abs((ta["beta"] - tb["beta"]) / delta - derivative))
        self.assertGreater(errors[0], 0.0)
        self.assertGreaterEqual(errors[1] / errors[0], 0.45)
        self.assertLessEqual(errors[1] / errors[0], 0.55)


class SeveralHits(unittest.TestCase):  # fix round 1: M7 (two hits on the changed channel) and I1 (two hits on one track)
    """Expectations in the general form of the stage plan section 2, computed here; R37's formulas are its one-hit case."""

    def records(self, rows, weights, delta, channel=2):
        hit_list = [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a, "position_cm": d, "path_length_cm": l}
                    for h, t, c, r, a, d, l in rows]
        raw = contents()
        return time_chain.correct(hit_list, read_all(raw)), time_chain.correct(hit_list, read_all(changed(raw, channel, delta)))

    ROWS_CHANNEL = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 2, 1, 45.0, 64.0, 50.0, 320.0), (12, 3, 2, 50.0, 25.0, 10.0, 350.0),
                    (13, 4, 3, 42.0, 400.0, 80.0, 310.0), (14, 5, 2, 47.0, 49.0, 60.0, 330.0)]     # hits 12 and 14 on channel 2
    W_CHANNEL = {10: 0.1, 11: 0.1, 12: 0.3, 13: 0.3, 14: 0.2}
    ROWS_TRACK = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 1, 2, 45.0, 64.0, 50.0, 320.0), (12, 3, 1, 50.0, 25.0, 10.0, 350.0),
                  (13, 4, 3, 42.0, 400.0, 80.0, 310.0)]                                          # track 1: hits 10 and 11; 11 on channel 2
    W_TRACK = {10: 0.1, 11: 0.2, 12: 0.3, 13: 0.4}

    def expectations(self, before, after, weights, start_of_track=None):
        track = {r["hit_id"]: r["track_id"] for r in before}
        dt = {h: corrected(after)[h] - corrected(before)[h] for h in track}
        common = math.fsum(weights[h] * dt[h] for h in track)
        loo = {}
        for j in set(track.values()):
            norm = math.fsum(w for h, w in weights.items() if track[h] != j)
            loo[j] = math.fsum(weights[h] / norm * dt[h] for h in track if track[h] != j)
        return track, dt, common, loo

    def check_all(self, rows, weights, channel_hits):
        before, after = self.records(rows, weights, DELTA_NS)
        track, dt, common, loo = self.expectations(before, after, weights)
        for h in track:
            self.assertLessEqual(abs(dt[h] - (-DELTA_NS if h in channel_hits else 0.0)), TIME_TOL_NS)
        eb, ea = event_time.common_linear(before, weights, BETA_HYP), event_time.common_linear(after, weights, BETA_HYP)
        self.assertLessEqual(abs((ea["value_ns"] - eb["value_ns"]) - common), TIME_TOL_NS)
        b, a = {r["hit_id"]: r for r in before}, {r["hit_id"]: r for r in after}
        start = event_time.external(T0_EXTERNAL, "fixture start counter")
        for h in track:
            with self.subTest(hit=h):
                self.assertLessEqual(abs((event_time.tof(a[h], ea, after)["tof_ns"] - event_time.tof(b[h], eb, before)["tof_ns"]) - (dt[h] - common)),
                                     TIME_TOL_NS)
                lb = event_time.leave_one_out(before, weights, BETA_HYP, track_id=track[h])
                la = event_time.leave_one_out(after, weights, BETA_HYP, track_id=track[h])
                self.assertLessEqual(abs((event_time.tof(a[h], la, after)["tof_ns"] - event_time.tof(b[h], lb, before)["tof_ns"])
                                         - (dt[h] - loo[track[h]])), TIME_TOL_NS)
                self.assertLessEqual(abs((event_time.tof(a[h], start)["tof_ns"] - event_time.tof(b[h], start)["tof_ns"]) - dt[h]),
                                     TIME_TOL_NS)

    def test_two_hits_on_the_changed_channel(self):  # M7
        self.check_all(self.ROWS_CHANNEL, self.W_CHANNEL, {12, 14})

    def test_two_hits_on_one_track(self):  # I1: track 1's leave-one-out excludes both its hits
        self.check_all(self.ROWS_TRACK, self.W_TRACK, {11})
        before, _ = self.records(self.ROWS_TRACK, self.W_TRACK, DELTA_NS)
        self.assertEqual(event_time.leave_one_out(before, self.W_TRACK, BETA_HYP, track_id=1)["excluded_hits"], [10, 11])

    def test_check_tool_passes_both(self):
        for rows, weights in ((self.ROWS_CHANNEL, self.W_CHANNEL), (self.ROWS_TRACK, self.W_TRACK)):
            hit_list = [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a, "position_cm": d, "path_length_cm": l}
                        for h, t, c, r, a, d, l in rows]
            result = t10_cai.check_single_ended(hit_list, contents(), channel=2, delta=DELTA_NS, weights=weights,
                                                beta_hypothesis=BETA_HYP, external_t0=T0_EXTERNAL)
            with self.subTest(rows=rows[1][1]):
                self.assertEqual(result["verdict"], "PASS", json.dumps(result["items"], indent=1))


def two_ended_hits():
    return [{"hit_id": 20, "track_id": 1, "counter": 0, "path_length_cm": 300.0, "counter_length_cm": 120.0,
             "ends": [{"end": 0, "raw_time_ns": 47.0, "amplitude": 81.0}, {"end": 1, "raw_time_ns": 49.0, "amplitude": 49.0}]},
            {"hit_id": 21, "track_id": 2, "counter": 1, "path_length_cm": 330.0, "counter_length_cm": 120.0,
             "ends": [{"end": 0, "raw_time_ns": 52.0, "amplitude": 36.0}, {"end": 1, "raw_time_ns": 50.0, "amplitude": 144.0}]}]


TWO_OFFSETS, TWO_WALKS, TWO_SPEEDS = [1.0, 1.5, 2.0, 2.5], [0.5, 0.5, 0.6, 0.6], [15.0, 15.0, 16.0, 16.0]


class TwoEndedRecipe(unittest.TestCase):  # CAI-T10-2, stage plan section 2 (derived here, not from a source)
    def run_pair(self, channel, delta):
        raw = contents(TWO_OFFSETS, 2, 2, TWO_WALKS, TWO_SPEEDS)
        changed_contents = {**raw, "offset": timing_payload.derive(raw["offset"], {channel: TWO_OFFSETS[channel] + delta}, "CAI-T10-2 change")}
        return time_chain.correct(two_ended_hits(), read_all(raw)), time_chain.correct(two_ended_hits(), read_all(changed_contents))

    def test_one_end_offset_moves_mean_and_position(self):
        start = event_time.external(T0_EXTERNAL, "fixture start counter")
        for channel, sign in ((0, -1.0), (1, +1.0)):          # counter 0: end 0 is channel 0, end 1 is channel 1
            v = TWO_SPEEDS[0]
            for delta in (DELTA_NS, DELTA_NS / 2):
                before, after = self.run_pair(channel, delta)
                with self.subTest(channel=channel, delta=delta):
                    b, a = before[0], after[0]
                    self.assertLessEqual(abs((a["propagation"]["mean_time_ns"] - b["propagation"]["mean_time_ns"]) + delta / 2), TIME_TOL_NS)
                    self.assertLessEqual(abs((a["corrected_time_ns"] - b["corrected_time_ns"]) + delta / 2), TIME_TOL_NS)
                    self.assertLessEqual(abs((a["position"]["value_cm"] - b["position"]["value_cm"]) - sign * v * delta / 2), POSITION_TOL_CM)
                    self.assertEqual(after[1]["corrected_time_ns"], before[1]["corrected_time_ns"])   # the other counter: 0
                    self.assertEqual(after[1]["position"]["value_cm"], before[1]["position"]["value_cm"])
                    tb, ta = event_time.tof(b, start), event_time.tof(a, start)
                    self.assertLessEqual(abs((ta["tof_ns"] - tb["tof_ns"]) + delta / 2), TIME_TOL_NS)
                    self.assertEqual(event_time.tof(after[1], start)["tof_ns"], event_time.tof(before[1], start)["tof_ns"])


class CheckTool(unittest.TestCase):  # the scoring-side check: PASS on the recipe, FAIL under each planted defect
    def single(self, plant=None):
        return t10_cai.check_single_ended(hits(), contents(), channel=2, delta=DELTA_NS, weights=WEIGHTS, beta_hypothesis=BETA_HYP,
                                          external_t0=T0_EXTERNAL, plant=plant)

    def two(self, plant=None):
        return t10_cai.check_two_ended(two_ended_hits(), contents(TWO_OFFSETS, 2, 2, TWO_WALKS, TWO_SPEEDS), channel=1, delta=DELTA_NS,
                                       external_t0=T0_EXTERNAL, plant=plant)

    def test_pass_on_the_recipe(self):
        result = self.single()
        self.assertEqual(result["verdict"], "PASS", json.dumps(result, indent=1))
        self.assertEqual(sorted(result["items"]), ["CAI-T10-1a", "CAI-T10-1b", "CAI-T10-1c", "CAI-T10-1d", "CAI-T10-1f"])
        self.assertEqual(result["steps_ns"], [DELTA_NS, DELTA_NS / 2])
        self.assertIn("CAI-T10-1e", result["recorded"])                        # the median: recorded, no assertion
        self.assertEqual(set(result["recorded"]["CAI-T10-1e"]), {str(DELTA_NS), str(DELTA_NS / 2)})
        self.assertEqual(self.two()["verdict"], "PASS")

    def test_each_plant_fails_its_item(self):
        expected = {"offset-twice": "CAI-T10-1a", "offset-sign": "CAI-T10-1a", "external-uses-hits": "CAI-T10-1b",
                    "stale-event-time": "CAI-T10-1c", "loo-keeps-own-hit": "CAI-T10-1d",
                    "recipe-offset-twice": "CAI-T10-1a", "recipe-loo-common": "CAI-T10-1d"}   # recipe-side plants (fix round 1, M4)
        self.assertEqual(dict(t10_cai.SINGLE_PLANTS), expected)
        self.assertEqual(t10_cai.PLANT_FAILED_ITEMS, {          # stage 2 fix round 1, I4: fixed before the change to t10_cai.py
            "offset-twice": {"CAI-T10-1a", "CAI-T10-1f"}, "offset-sign": {"CAI-T10-1a", "CAI-T10-1f"},
            "external-uses-hits": {"CAI-T10-1b", "CAI-T10-1f"}, "stale-event-time": {"CAI-T10-1c"}, "loo-keeps-own-hit": {"CAI-T10-1d"},
            "recipe-offset-twice": {"CAI-T10-1a", "CAI-T10-1b", "CAI-T10-1c", "CAI-T10-1d", "CAI-T10-1f"}, "recipe-loo-common": {"CAI-T10-1d"},
            "position-no-half": {"CAI-T10-2"}, "mean-one-end": {"CAI-T10-2"}, "recipe-position-no-half": {"CAI-T10-2"}})
        for plant, item in expected.items():
            with self.subTest(plant=plant):
                result = self.single(plant)
                self.assertEqual(result["verdict"], "FAIL")
                self.assertEqual(result["items"][item]["verdict"], "FAIL")
                failed = sorted(k for k, v in result["items"].items() if v["verdict"] == "FAIL")
                self.assertEqual(failed, sorted(t10_cai.PLANT_FAILED_ITEMS[plant]))     # stage 2 fix round 1, I4: the exact set
        two_expected = {"position-no-half": "CAI-T10-2", "mean-one-end": "CAI-T10-2", "recipe-position-no-half": "CAI-T10-2"}
        self.assertEqual(dict(t10_cai.TWO_PLANTS), two_expected)
        for plant, item in two_expected.items():
            with self.subTest(plant=plant):
                result = self.two(plant)
                self.assertEqual(result["verdict"], "FAIL")
                self.assertEqual(result["items"][item]["verdict"], "FAIL")      # N2: the item, not only the verdict
                failed = sorted(k for k, v in result["items"].items() if v["verdict"] == "FAIL")
                self.assertEqual(failed, sorted(t10_cai.PLANT_FAILED_ITEMS[plant]))

    def test_recipe_plants_leave_the_recipe_unchanged_afterwards(self):  # a plant is undone after its run
        self.single("recipe-offset-twice")
        self.two("recipe-position-no-half")
        self.single("recipe-loo-common")
        self.assertEqual(self.single()["verdict"], "PASS")
        self.assertEqual(self.two()["verdict"], "PASS")

    def test_cli_run_and_exit_codes(self):
        script = ASSETS / "fixture_tools" / "t10_cai.py"
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / "run"
            p = subprocess.run([sys.executable, "-B", str(script), "run", "--seed", "7", "--events", "5", "--out", str(out)],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("RESULT t10-cai PASS", p.stdout)
            doc = json.loads((out / "t10-cai.json").read_text())
            self.assertEqual(doc["format"], "t10-cai-record/1")
            self.assertEqual(doc["status_label"], "synthetic")
            self.assertEqual(len(doc["events"]), 5)
            again = subprocess.run([sys.executable, "-B", str(script), "run", "--seed", "7", "--events", "5", "--out", str(out)],
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(again.returncode, 2, "an output that exists is never overwritten")
            planted = subprocess.run([sys.executable, "-B", str(script), "run", "--seed", "7", "--events", "5", "--out", str(Path(scratch) / "p"),
                                      "--plant", "offset-sign"], capture_output=True, text=True, timeout=120)
            self.assertEqual(planted.returncode, 1, planted.stdout + planted.stderr)
            self.assertIn("RESULT t10-cai FAIL", planted.stdout)
            self.assertIn("PLANT offset-sign item CAI-T10-1a failed in 5 of 5 events", planted.stdout)   # M4
            self.assertIn("RESULT t10-cai FAIL events 5 failed 5 plant offset-sign items CAI-T10-1a,CAI-T10-1f\n", planted.stdout)
            bad = subprocess.run([sys.executable, "-B", str(script), "run", "--seed", "7", "--events", "0", "--out", str(Path(scratch) / "b")],
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(bad.returncode, 2)
            self.assertIn('"status": "rejected"', bad.stdout)
            self.assertNotIn("refused", bad.stdout.lower())                                          # M2
            blocker = Path(scratch) / "a-file"
            blocker.write_text("x")
            unwritable = subprocess.run([sys.executable, "-B", str(script), "run", "--seed", "7", "--events", "1", "--out", str(blocker / "o")],
                                        capture_output=True, text=True, timeout=120)
            self.assertEqual(unwritable.returncode, 3, unwritable.stdout)                            # N3
            self.assertIn('"status": "incomplete"', unwritable.stdout)

    def test_internal_errors_exit_three(self):  # M1: an error on the tool's own generated fixture, or any crash, is incomplete
        original = t10_cai.run
        try:
            for error in (event_time.InputError("tof not positive"), RuntimeError("boom"), TypeError("bad")):
                def failing(*args, error=error, **kwargs):
                    raise error
                t10_cai.run = failing
                with tempfile.TemporaryDirectory() as scratch, self.subTest(error=type(error).__name__), \
                        contextlib.redirect_stdout(io.StringIO()) as printed:
                    self.assertEqual(t10_cai.main(["run", "--seed", "1", "--events", "1", "--out", str(Path(scratch) / "o")]), 3)
                self.assertIn('"status": "incomplete"', printed.getvalue())
        finally:
            t10_cai.run = original


if __name__ == "__main__":
    unittest.main()
