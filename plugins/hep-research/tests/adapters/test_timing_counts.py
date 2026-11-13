"""adapters/timing-pid, T10 stage 2: the native non-hit input example of plan section 3.3 (W6, BP12, A19; t10-timing-stage-plan.md
section 6.1, row W6-T10). Counts with thresholds and exposure, in their native form, through a recipe: a valid zero, an absent
interval, per-channel valid exposure; the product must pass the T06 contract reader. Hand-made input; every expectation computed here.

Run from the plugin root: python -m unittest tests.adapters.test_timing_counts -v
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "timing-pid" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS))

from contracts.reconstruction import observed_intervals  # noqa: E402
from timing_recipe import counts  # noqa: E402


def native():
    return [{"channel": "counter-0", "threshold": {"value": 3.0, "unit": "adc"}, "response_ref": "native:response-counter-0",
             "intervals": [{"interval_id": "c0-i0", "start_s": 0.0, "end_s": 40.0, "dead_s": 2.0, "read": True},
                           {"interval_id": "c0-i1", "start_s": 40.0, "end_s": 70.0, "dead_s": 0.0, "read": False},
                           {"interval_id": "c0-i2", "start_s": 70.0, "end_s": 100.0, "dead_s": 1.0, "read": True}],
             "pulses": [{"time_s": 5.0, "amplitude": 2.0}, {"time_s": 30.0, "amplitude": 2.5}, {"time_s": 80.0, "amplitude": 3.0},
                        {"time_s": 90.0, "amplitude": 9.5}]},
            {"channel": "counter-1", "threshold": {"value": 9.0, "unit": "adc"}, "response_ref": "native:response-counter-1",
             "intervals": [{"interval_id": "c1-i0", "start_s": 0.0, "end_s": 50.0, "dead_s": 0.0, "read": True},
                           {"interval_id": "c1-i1", "start_s": 50.0, "end_s": 100.0, "dead_s": 5.0, "read": True}],
             "pulses": [{"time_s": 10.0, "amplitude": 4.0}, {"time_s": 60.0, "amplitude": 9.0}]}]


class NativeCounts(unittest.TestCase):
    def setUp(self):
        self.product, self.readings = counts.build(native(), "product.t10-counts")

    def test_the_product_passes_the_contract_reader(self):
        self.assertEqual(counts.check(self.product), [])
        self.assertIn("reconstruction:counts-v1", self.product["required_extensions"])

    def test_zero_absent_and_counts(self):
        by_id = {i["interval_id"]: i for i in self.product["counts"]["intervals"]}
        self.assertEqual(by_id["c0-i0"], {"interval_id": "c0-i0", "channel": "counter-0", "presence": "present", "count": 0})  # a valid zero
        self.assertEqual(by_id["c0-i1"], {"interval_id": "c0-i1", "channel": "counter-0", "presence": "absent"})  # not read: no count
        self.assertEqual(by_id["c0-i2"]["count"], 2)                    # 3.0 and 9.5 pass the threshold 3.0 (at or above)
        self.assertEqual(by_id["c1-i0"]["count"], 0)
        self.assertEqual(by_id["c1-i1"]["count"], 1)
        observed = {i["interval_id"]: i["count"] for i in observed_intervals(self.product)}
        self.assertEqual(observed, {"c0-i0": 0, "c0-i2": 2, "c1-i0": 0, "c1-i1": 1})

    def test_each_channel_uses_its_own_valid_exposure(self):
        block = self.product["counts"]
        exposure = {c["channel"]: c["valid_exposure"] for c in block["channels"]}
        self.assertEqual(exposure, {"counter-0": {"value": 38.0 + 29.0, "unit": "s"}, "counter-1": {"value": 50.0 + 45.0, "unit": "s"}})
        self.assertEqual(block["run_time"], {"value": 100.0, "unit": "s"})
        for rate in block["rates"]:
            self.assertEqual(rate["denominator"], {"source": "valid-exposure", **exposure[rate["channel"]]})
        self.assertEqual(self.readings["counter-0"], {"count": 2, "valid_exposure_s": 67.0, "rate_per_s": 2 / 67.0})
        self.assertEqual(self.readings["counter-1"], {"count": 1, "valid_exposure_s": 95.0, "rate_per_s": 1 / 95.0})

    def test_no_per_event_energy_is_delivered(self):  # A19
        block = self.product["counts"]
        self.assertEqual((block["capability"], block["observables"], block["per_event_energy"]), ("counting", ["count"], False))
        self.assertIsNone(block["count_model"]["inferred_from"])
        self.assertEqual(sorted(s["threshold"]["value"] for s in block["selections"]), [3.0, 9.0])

    def test_the_contract_catches_what_the_recipe_never_does(self):
        absent = copy.deepcopy(self.product)
        next(i for i in absent["counts"]["intervals"] if i["presence"] == "absent")["count"] = 0
        self.assertIn("reconstruction.counts.absent_filled", counts.check(absent))
        run_time = copy.deepcopy(self.product)
        for rate in run_time["counts"]["rates"]:
            rate["denominator"] = {"source": "run-time", "value": 100.0, "unit": "s"}
        self.assertIn("reconstruction.counts.run_time_denominator", counts.check(run_time))

    def test_input_refusals(self):
        cases = {"overlapping intervals": lambda n: n[0]["intervals"][1].__setitem__("start_s", 30.0),
                 "dead time above the interval": lambda n: n[0]["intervals"][0].__setitem__("dead_s", 50.0),
                 "pulse outside every interval": lambda n: n[1]["pulses"].append({"time_s": 120.0, "amplitude": 10.0}),
                 "pulse in an unread interval": lambda n: n[0]["pulses"].append({"time_s": 50.0, "amplitude": 8.0}),
                 "no threshold": lambda n: n[0].__setitem__("threshold", None),
                 "channel twice": lambda n: n[1].__setitem__("channel", "counter-0")}
        for name, change in cases.items():
            native_channels = native()
            change(native_channels)
            with self.subTest(case=name), self.assertRaises(counts.InputError):
                counts.build(native_channels, "product.t10-counts")


class Tool(unittest.TestCase):
    def test_cli_counts_and_its_controls(self):
        script = ASSETS / "fixture_tools" / "t10_stage2.py"
        with tempfile.TemporaryDirectory() as scratch:
            base = [sys.executable, "-B", str(script), "counts", "--seed", "3", "--events", "20"]
            p = subprocess.run(base + ["--out", str(Path(scratch) / "ok")], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("RESULT t10-counts PASS", p.stdout)
            doc = json.loads((Path(scratch) / "ok" / "t10-counts.json").read_text())
            self.assertEqual((doc["format"], doc["status_label"]), ("t10-counts-record/1", "synthetic"))
            self.assertTrue(any(i["count"] == 0 for e in doc["events"] for i in e["product"]["counts"]["intervals"] if "count" in i))
            self.assertTrue(any(i["presence"] == "absent" for e in doc["events"] for i in e["product"]["counts"]["intervals"]))
            for plant in ("absent-as-zero", "run-time-denominator"):
                with self.subTest(plant=plant):
                    q = subprocess.run(base + ["--out", str(Path(scratch) / plant), "--plant", plant], capture_output=True, text=True,
                                       timeout=120)
                    self.assertEqual(q.returncode, 1, q.stdout + q.stderr)
                    self.assertIn(f"PLANT {plant} item contract FAIL in 20 of 20 events", q.stdout)
                    self.assertIn(f"RESULT t10-counts FAIL failed items contract plant {plant}", q.stdout)      # fix round 1, I4
                    code = {"absent-as-zero": "reconstruction.counts.absent_filled",
                            "run-time-denominator": "reconstruction.counts.run_time_denominator"}[plant]
                    self.assertIn(f"PLANT-CODES {code}\n", q.stdout)                                           # fix round 1, M7


if __name__ == "__main__":
    unittest.main()
