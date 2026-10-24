"""bartels_rotation.py (Th13): Bartels rotation numbers from the 1832-02-08 epoch (WDC Kp/Ap format description), the
cross-check rotation 2426 = 2011-05-15 (Caltech ACE table, read 2026-10-20), rotation edges, lagged rotation averages
of a daily series with coverage, and refusals. Inputs are SYNTHETIC."""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "bartels_rotation.py"


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=120)
    return p.returncode, json.loads(p.stdout)


def series(td: Path, days: dict) -> Path:
    path = td / "s.csv"
    path.write_text("date,tilt\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in days.items()))
    return path


class Rotations(unittest.TestCase):
    def test_epoch_and_published_cross_check(self):
        code, out = run("rotation", "--date", "1832-02-08", "1832-03-05", "1832-03-06", "2011-05-15")
        self.assertEqual(code, 0, out)
        got = [(r["rotation"], r["day_in_rotation"]) for r in out["rows"]]
        self.assertEqual(got, [(1, 1), (1, 27), (2, 1), (2426, 1)])
        self.assertEqual(out["rows"][3]["end_exclusive"], "2011-06-11")
        self.assertIn("1832-02-08", out["conventions"]["definition"])

    def test_dates_range_is_contiguous(self):
        code, out = run("dates", "--range", "2426", "2504")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out["rows"]), 79)
        for a, b in zip(out["rows"], out["rows"][1:]):
            self.assertEqual(a["end_exclusive"], b["start"])
            self.assertEqual((dt.date.fromisoformat(a["end_exclusive"]) - dt.date.fromisoformat(a["start"])).days, 27)

    def test_refusals(self):
        self.assertEqual(run("rotation", "--date", "1800-01-01")[0], 2)
        self.assertEqual(run("dates", "--rotation", "0")[0], 2)
        self.assertEqual(run("dates")[0], 2)
        self.assertEqual(run("dates", "--range", "5", "4")[0], 2)


class LaggedAverages(unittest.TestCase):
    def test_full_window_mean_and_lag_shift(self):
        start = dt.date(2011, 5, 15)
        days = {start + dt.timedelta(days=i - 30): float(i) for i in range(0, 90)}  # value = index, linear in time
        with tempfile.TemporaryDirectory() as td:
            path = series(Path(td), days)
            common = ("average", "--series", str(path), "--date-column", "date", "--value-column", "tilt",
                      "--rotation", "2426", "--min-coverage", "1")
            code0, lag0 = run(*common, "--lag-days", "0")
            code10, lag10 = run(*common, "--lag-days", "10")
        self.assertEqual((code0, code10), (0, 0), (lag0, lag10))
        r0, r10 = lag0["rows"][0], lag10["rows"][0]
        self.assertEqual((r0["n_days"], r0["coverage"]), (27, 1.0))
        self.assertAlmostEqual(r0["mean"], 30 + 13)  # indices 30..56
        self.assertAlmostEqual(r10["mean"], 20 + 13)  # the window moves 10 days earlier
        self.assertEqual(r10["window_start"], "2011-05-05")

    def test_low_coverage_is_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            path = series(Path(td), {dt.date(2011, 5, 20): 10.0, dt.date(2011, 5, 21): ""})
            code, out = run("average", "--series", str(path), "--date-column", "date", "--value-column", "tilt",
                            "--rotation", "2426", "--lag-days", "0", "--min-coverage", "0.5")
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "incomplete")
        self.assertEqual(out["below_min_coverage"], [2426])
        self.assertEqual(out["rows"][0]["n_days"], 1)

    def test_byte_order_mark_and_negative_lag(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bom.csv"
            p.write_text("\ufeffdate,tilt\n2011-06-12,7\n", encoding="utf-8")
            code, out = run("average", "--series", str(p), "--date-column", "date", "--value-column", "tilt",
                            "--rotation", "2426", "--lag-days", "-2", "--min-coverage", "0.01")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["rows"][0]["window_end_exclusive"], "2011-06-13")
        self.assertEqual(out["rows"][0]["mean"], 7.0)

    def test_bad_series_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dup.csv"
            p.write_text("date,tilt\n2011-05-20,1\n2011-05-20,2\n")
            args = ("average", "--series", str(p), "--date-column", "date", "--value-column", "tilt",
                    "--rotation", "2426", "--lag-days", "0", "--min-coverage", "0.5")
            self.assertEqual(run(*args)[0], 2)
            p.write_text("date,tilt\n2011-05-20,nan\n")
            self.assertEqual(run(*args)[0], 2)
            p.write_text("date,tilt\n2011-05-20T12:00:00Z,1\n")
            self.assertEqual(run(*args)[0], 2)  # timestamps are not days
            p.write_text("day,tilt\n2011-05-20,1\n")
            self.assertEqual(run(*args)[0], 2)
            p.write_text("date,tilt\n2011-05-20,1\n")
            self.assertEqual(run(*args[:-2], "--min-coverage", "0")[0], 2)
            self.assertEqual(run(*args[:-4], "--lag-days", "1.5", "--min-coverage", "0.5")[0], 2)


if __name__ == "__main__":
    unittest.main()
