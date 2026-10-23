"""theory:drell-yan-lo against the published closed form of Peng et al. Eq. (10): the benchmark file carries its
citation, location and date read; the profile's lambda and nu agree at every qT/Q value; a corrupted benchmark entry
is caught."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

BENCH = json.loads((ROOT / "benchmarks" / "peng-eq10.json").read_text(encoding="utf-8"))


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_is_sourced(self):
        src = BENCH["source"]
        self.assertIn("1511.08932v3", src["citation"])
        self.assertIn("Eq. (10)", src["location"])
        self.assertEqual(src["date_read"], "2026-10-23")
        self.assertFalse(BENCH["illustrative"])
        self.assertIn("same route", BENCH["independence"])

    def test_printed_and_rational_forms_agree(self):
        """The rational coefficients are a transcription of the printed lines (Q = 1)."""
        for ch, q, expr in (("qqbar", "lambda", lambda r: (2 - r * r) / (2 + 3 * r * r)),
                            ("qqbar", "nu", lambda r: 2 * r * r / (2 + 3 * r * r)),
                            ("qg", "lambda", lambda r: (2 - 5 * r * r) / (2 + 15 * r * r)),
                            ("qg", "nu", lambda r: 10 * r * r / (2 + 15 * r * r))):
            for r in BENCH["qT_over_Q"]:
                self.assertAlmostEqual(predict.peng_eq10(BENCH, ch, q, r), expr(r), places=15)

    def test_profile_reproduces_published_closed_form(self):
        out = predict.benchmark_comparison(BENCH)
        self.assertTrue(out["all_pass"], [r for r in out["rows"] if not r["pass"]])
        self.assertEqual(len(out["rows"]), 2 * 2 * len(BENCH["qT_over_Q"]))

    def test_corrupted_benchmark_is_caught(self):
        bad = copy.deepcopy(BENCH)
        bad["rational_form"]["qg"]["nu"] = [0, 10, 2, 5]
        self.assertFalse(predict.benchmark_comparison(bad)["all_pass"])

    def test_published_limits(self):
        for ch in predict.CHANNELS:
            self.assertEqual(predict.channel_coefficients(ch, 0.0)["lambda"], 1.0)
            self.assertAlmostEqual(predict.channel_coefficients(ch, 1e4)["lambda"], -1 / 3, places=6)


if __name__ == "__main__":
    unittest.main()
