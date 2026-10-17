"""D11: stability_monitor.py, stability of a calibration or performance quantity over time.

Oracles:
- AC-B: in the synthetic data of toy_spectrometer.py (fictional configuration, an era that adds a layer and a longer
  lever arm from period 6), the per-period width of the proton curvature residual times beta R (the Highland term
  b, 0.0231 -> 0.0160) has one change point, at period 6, proposed as a calibration era boundary;
- a constant series has no change point at the calibrated false-alarm rate; the declared rate and the toys are echoed;
- out-of-tolerance periods are listed against a declared reference and tolerance;
- proposals are never written into a spec (the output says so);
- missing --false-alarm, a non-positive uncertainty, a missing column: exit 2.
Inputs are SYNTHETIC.
"""
import csv
import io
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "hep-detector" / "scripts"
TOOL = SCRIPTS / "stability_monitor.py"
TOY = SCRIPTS / "toy_spectrometer.py"
CONFIG = ROOT / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json"


def run_json(*args, timeout=600):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def write_series(path, rows, header=("period", "time_s", "value", "error")):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


class EraBoundaryInToyData(unittest.TestCase):
    def test_added_layer_era_is_found(self):
        try:
            import numpy  # noqa: F401  (toy_spectrometer.py generate needs NumPy)
        except ImportError:
            self.skipTest("NumPy not installed")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            gen = subprocess.run([sys.executable, "-B", str(TOY), "generate", str(CONFIG), "--seed", "7",
                                  "--events-out", str(t / "ev.csv"), "--periods-out", str(t / "per.csv")],
                                 capture_output=True, text=True, timeout=600)
            self.assertEqual(gen.returncode, 0, gen.stdout + gen.stderr)
            lines = [ln for ln in (t / "ev.csv").read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
            per = {}
            for r in csv.DictReader(io.StringIO("\n".join(lines))):
                if r["species"] != "p":
                    continue
                rt, bt = float(r["rigidity_true_gv"]), float(r["beta_true"])
                if rt >= 10.0:  # below 10 GV the Highland term dominates (a R < 0.006 << b)
                    continue
                q = (float(r["inv_rigidity_meas_per_gv"]) - 1.0 / rt) * bt * rt
                per.setdefault(int(r["period"]), []).append(q)
            rows = []
            for p in sorted(per):
                v = per[p]
                rms = math.sqrt(sum(x * x for x in v) / len(v))
                rows.append([p, 1000.0 * p, rms, rms / math.sqrt(2 * (len(v) - 1))])
            write_series(t / "series.csv", rows)
            code, out = run_json(t / "series.csv", "--time-column", "time_s", "--value-column", "value",
                                 "--error-column", "error", "--period-column", "period", "--false-alarm", "0.01",
                                 "--toys", "2000", "--seed", "4")
        self.assertEqual(code, 0, out)
        cps = out["change_points"]
        self.assertEqual([c["index"] for c in cps], [6], out)
        prop = out["proposed_era_boundaries"]
        self.assertEqual(len(prop), 1)
        self.assertEqual(prop[0]["kind"], "calibration")
        self.assertEqual(prop[0]["first_period"], 6)
        self.assertLess(prop[0]["step"], 0)
        self.assertIn("never written into a spec", out["proposal_note"])
        self.assertEqual(out["status_label"], "unvalidated")


class Series(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_constant_series_and_tolerance(self):
        rng = random.Random(1)
        rows = [[i, float(i), 1.0 + rng.gauss(0, 0.01), 0.01] for i in range(30)]
        rows[17][2] = 1.06  # one outlier: out of tolerance, but a single point is not an era
        write_series(self.d / "s.csv", rows)
        code, out = run_json(self.d / "s.csv", "--time-column", "time_s", "--value-column", "value",
                             "--error-column", "error", "--false-alarm", "0.05", "--toys", "2000", "--seed", "2",
                             "--reference", "1.0", "--tolerance", "0.03", "--min-segment", "3")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["change_points"], [])
        self.assertEqual([p["index"] for p in out["out_of_tolerance"]], [17])
        cal = out["calibration"]["segmentation"]
        self.assertEqual((cal["false_alarm_rate"], cal["toys"], cal["seed"]), (0.05, 2000, 2))
        self.assertIn("constant", out["trends"])
        self.assertIn("linear", out["trends"])
        self.assertIn("cusum", out)

    def test_bad_input(self):
        write_series(self.d / "s.csv", [[0, 0.0, 1.0, 0.1], [1, 1.0, 1.0, 0.0], [2, 2.0, 1.0, 0.1]])
        base = [self.d / "s.csv", "--time-column", "time_s", "--value-column", "value", "--toys", "500", "--seed", "1"]
        for extra in (["--error-column", "error"],  # no --false-alarm
                      ["--error-column", "error", "--false-alarm", "0.05"],  # sigma 0
                      ["--error-column", "nope", "--false-alarm", "0.05"]):
            with self.subTest(extra=extra):
                code, out = run_json(*base, *extra)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
