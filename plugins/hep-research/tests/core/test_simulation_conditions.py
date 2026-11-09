"""Condition snapshots (g4sim S9, Section 17): IOV lookup by time, defaults, the response layer's use of them, and the Section 15.1
negative test of S9 for snapshots: condition snapshots with overlapping IOVs."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import conditions, digitize  # noqa: E402

SNAPSHOT = {"schema": conditions.SCHEMA, "readout": "bar", "version": "1", "time_unit": "ns", "defaults": {"gain_factor": 1.0},
            "iovs": [{"start_ns": 0, "end_ns": 1000, "rows": [{"cell": {"volume": 5, "channel": 1}, "dead": True}]},
                     {"start_ns": 1000, "end_ns": 5000, "rows": [{"cell": {"volume": 5, "channel": 0}, "gain_factor": 2.0, "threshold": 0.5}]}]}
JOB = {"schema": digitize.SCHEMA, "run_seed": 11, "replica": 0, "readout": "bar", "channels": ["left", "right"],
       "stage": {"name": "scintillation", "light_yield_per_MeV": 200.0, "resolution_scale": 0.6}, "efficiencies": {"0": [0.1, 0.2]}, "timing": None,
       "sensor": {"name": "sensor", "gain": 1.0, "excess_noise": 0.1, "dark_rate_per_ns": 1e-3, "gate_ns": 50.0},
       "electronics": {"name": "electronics", "noise_sigma": 0.5, "threshold": 1.0, "lsb": 0.5, "bits": 10}}
ROWS = [(0, 5, 0, 0.2, 0.01, 4), (1, 5, 0, 0.5, 0.02, 9)]


class Snapshots(unittest.TestCase):
    def test_lookup_by_time_and_defaults(self):
        conditions.check_snapshot(SNAPSHOT, fields=("volume", "channel"))
        self.assertTrue(conditions.at(SNAPSHOT, 10, {"volume": 5, "channel": 1})["dead"])
        self.assertEqual(conditions.at(SNAPSHOT, 1000, {"volume": 5, "channel": 0})["gain_factor"], 2.0)
        self.assertEqual(conditions.at(SNAPSHOT, 1000, {"volume": 5, "channel": 1}), {"gain_factor": 1.0, "dead": False})
        with self.assertRaises(conditions.ConditionError) as caught:
            conditions.at(SNAPSHOT, 5000, {"volume": 5, "channel": 0})
        self.assertEqual(caught.exception.code, "no-iov")

    def test_overlapping_iovs_are_refused(self):  # Section 15.1, S9
        overlapping = copy.deepcopy(SNAPSHOT)
        overlapping["iovs"][1]["start_ns"] = 999
        with self.assertRaises(conditions.ConditionError) as caught:
            conditions.check_snapshot(overlapping)
        self.assertEqual(caught.exception.code, "iov-overlap")

    def test_malformed_snapshots(self):
        for change, code in ((lambda s: s.update(schema="x"), "schema"), (lambda s: s["iovs"][0].update(end_ns=0), "iov-empty"),
                             (lambda s: s["iovs"][0]["rows"].append(dict(s["iovs"][0]["rows"][0])), "cell-twice"),
                             (lambda s: s["iovs"][0]["rows"][0]["cell"].update(layer=1), "cell-fields")):
            snapshot = copy.deepcopy(SNAPSHOT)
            change(snapshot)
            with self.assertRaises(conditions.ConditionError) as caught:
                conditions.check_snapshot(snapshot, fields=("volume", "channel"))
            self.assertEqual(caught.exception.code, code)


class Response(unittest.TestCase):
    def test_conditions_enter_the_response_only_where_they_apply(self):
        plain, _ = digitize.digitize(JOB, ROWS)
        conditioned, _ = digitize.digitize({**JOB, "conditions": SNAPSHOT, "event_time_ns": {"0": 10, "1": 2000}}, ROWS)
        self.assertEqual([row[:4] for row in plain], [row[:4] for row in conditioned])  # photoelectrons do not move
        self.assertIsNone(conditioned[1][5])  # event 0, channel 1: dead
        self.assertEqual(plain[0], conditioned[0])  # event 0, channel 0: no row, defaults
        self.assertNotEqual(plain[2][4], conditioned[2][4])  # event 1, channel 0: gain doubled
        self.assertEqual(plain[3], conditioned[3])

    def test_refusals(self):
        with self.assertRaises(digitize.DigiError) as caught:
            digitize.digitize({**JOB, "conditions": SNAPSHOT, "event_time_ns": {"0": 10}}, ROWS)
        self.assertEqual(caught.exception.code, "event-time")
        with self.assertRaises(digitize.DigiError) as caught:
            digitize.digitize({**JOB, "conditions": {**SNAPSHOT, "readout": "other"}, "event_time_ns": {}}, ROWS)
        self.assertEqual(caught.exception.code, "conditions")
        with self.assertRaises(digitize.DigiError) as caught:
            digitize.job_with_keys({**JOB, "conditions": SNAPSHOT})
        self.assertEqual(caught.exception.code, "conditions-python-only")


if __name__ == "__main__":
    unittest.main()
