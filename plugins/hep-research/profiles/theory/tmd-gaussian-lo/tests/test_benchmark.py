"""theory:tmd-gaussian-lo against the published closed forms of Anselmino et al. (Eqs. 38-39, 64-67): the benchmark
carries citation, location and date read; the profile's quadrature reproduces both closed forms; a wrong width
combination in the closed form is caught."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

BENCH = json.loads((ROOT / "benchmarks" / "anselmino-closed-forms.json").read_text(encoding="utf-8"))


class SourceTests(unittest.TestCase):
    def test_benchmark_is_sourced(self):
        src = BENCH["source"]
        self.assertIn("hep-ph/0501196v2", src["citation"])
        self.assertIn("Eqs. (38)-(39)", src["location"])
        self.assertIn("(63)-(67)", src["location"])
        self.assertEqual(src["date_read"], "2026-10-23")
        self.assertTrue(BENCH["illustrative"])
        self.assertIn("formulas, not these numbers", BENCH["illustrative_reason"])
        self.assertIn("not physics", BENCH["independence"])
        self.assertIn("SYNTHETIC", BENCH["settings"]["note"])


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
class BenchmarkTests(unittest.TestCase):
    def test_quadrature_reproduces_published_closed_forms(self):
        out = predict.benchmark_comparison(BENCH)
        self.assertTrue(out["all_pass"], [r for r in out["rows"] if not r["pass"]])
        self.assertEqual(len(out["rows"]), 2 * len(BENCH["points"]))

    def test_wrong_width_combination_is_caught(self):
        s = BENCH["settings"]
        z, p = 0.4, 0.5
        num = predict.cahn_ratio_numeric(z, p, s["y"], s["Q_gev"], 0.0, s["kperp2_gev2"], s["pperp2_gev2"])
        # <P_T^2> = <p^2> + z <k^2> (z instead of z^2) mimics a transcription error of Eq. 39
        y, q, k2 = s["y"], s["Q_gev"], s["kperp2_gev2"]
        w_wrong = s["pperp2_gev2"] + z * k2
        unpol = 1 + (1 - y) ** 2
        wrong = (unpol - 4 * (2 - y) * (1 - y) ** 0.5 * k2 * z * p / (w_wrong * q)) / unpol
        self.assertGreater(abs(num / wrong - 1), BENCH["relative_tolerance"])
        good = predict.cahn_ratio_closed(z, p, s["y"], s["Q_gev"], 0.0, s["kperp2_gev2"], s["pperp2_gev2"])
        self.assertLess(abs(num / good - 1), BENCH["relative_tolerance"])

    def test_sivers_sign_follows_N(self):
        s = BENCH["settings"]
        a = predict.sivers_asymmetry_closed(0.4, 0.5, 0.3, s["kperp2_gev2"], s["pperp2_gev2"], s["Mprime2_gev2"])
        b = predict.sivers_asymmetry_closed(0.4, 0.5, -0.3, s["kperp2_gev2"], s["pperp2_gev2"], s["Mprime2_gev2"])
        self.assertGreater(a, 0)
        self.assertEqual(a, -b)


if __name__ == "__main__":
    unittest.main()
