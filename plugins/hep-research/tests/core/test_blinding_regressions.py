"""Blinding regressions from the hep-computing remediation (CMP-04, CMP-05) of core/blinding/blinding.py and
skills/hep-computing/scripts/audit_blinded_outputs.py.

CMP-04: seal() sealed exact zero (twice: a blinded 0 and its fraction 0/total) and cumulative sums that equal public
        sideband sums when a blinded bin is empty, so a log 'job finished: 0 errors' or a CSV of the public sideband
        yields failed the scan (exit 1). Rule (Q3, option a): drop exact zero and every number the unblinded bins give
        alone; keep the rest.
CMP-05: an object .npy or a non-zip .npz aborted the scan (exit 2) and a corrupt zip .npz raised BadZipFile
        (traceback, exit 1, the code reserved for a found leak). Now each is unscanned: status incomplete, exit 3.
Each test fails on c1d375c. All inputs SYNTHETIC.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.blinding import blinding as bl  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "audit_blinded_outputs.py"
EDGES = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
EMPTY_BLINDED = [812.0, 640.5, 0.0, 377.25, 210.0]   # blinded bin [120, 130) is empty
BLINDED = [812.0, 640.5, 1234.567, 377.25, 210.0]
SR = {"variable": "m", "low": 120.0, "high": 130.0}


def run(*argv):
    p = subprocess.run([sys.executable, str(SCRIPT), *map(str, argv)], capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


class SealedValueRuleTests(unittest.TestCase):
    """CMP-04."""

    def test_zero_and_public_sums_are_not_sealed(self):
        s = bl.seal(EDGES, EMPTY_BLINDED, SR)
        self.assertNotIn(0.0, s)
        for public in (812.0 + 640.5, 377.25 + 210.0, sum(EMPTY_BLINDED), 812.0, 210.0):
            self.assertFalse(any(abs(x - public) <= 1e-9 * public for x in s), public)

    def test_values_that_include_a_blinded_count_stay_sealed(self):
        s = bl.seal(EDGES, BLINDED, SR)
        for v in (1234.567, 812.0 + 640.5 + 1234.567, 1234.567 + 377.25 + 210.0, sum(BLINDED)):
            self.assertTrue(any(abs(x - v) <= 1e-9 * v for x in s), v)

    def scan_dir(self, hist, files):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "hist.json").write_text(json.dumps({"edges": EDGES, "values": hist}))
            out = d / "outputs"
            out.mkdir()
            for name, text in files.items():
                (out / name).write_text(text)
            code, _, err = run("seal", "--hist", d / "hist.json", "--low", 120, "--high", 130, "--out", d / "sealed.json")
            self.assertEqual(code, 0, err)
            return run("scan", "--sealed", d / "sealed.json", out)

    def test_zero_errors_log_and_public_sideband_csv_pass(self):
        files = {"job.log": "job finished: 0 errors\nwarnings: 0\n",
                 "sideband.csv": "region,yield\nlow,1452.5\nhigh,587.25\nall,2039.75\n"}
        code, out, err = self.scan_dir(EMPTY_BLINDED, files)
        self.assertNotIn("Traceback", err)
        self.assertEqual(json.loads(out)["status"], "pass", out)
        self.assertEqual(code, 0)

    def test_exact_nonzero_blinded_value_still_fails(self):
        code, out, _ = self.scan_dir(BLINDED, {"job.log": "job finished: 0 errors\nsignal bin 1234.567\n"})
        self.assertEqual((code, json.loads(out)["status"]), (1, "fail"))

    def test_all_blinded_content_public_or_zero_gives_an_empty_seal_that_scans(self):
        """Every blinded number is zero or public: nothing is sealable; the scan still reads every output."""
        code, out, err = self.scan_dir([5.0, 0.0, 0.0, 0.0, 7.0], {"a.log": "0 events in 5 bins, 12 total\n"})
        self.assertNotIn("Traceback", err)
        self.assertEqual(json.loads(out)["status"], "pass", out)
        self.assertEqual(code, 0)


class UnreadableArrayTests(unittest.TestCase):
    """CMP-05."""

    def setUp(self):
        import numpy as np
        self.np = np
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / "hist.json").write_text(json.dumps({"edges": EDGES, "values": BLINDED}))
        self.assertEqual(run("seal", "--hist", self.d / "hist.json", "--low", 120, "--high", 130,
                             "--out", self.d / "sealed.json")[0], 0)

    def bad_files(self):
        import pickle
        np = self.np
        yield "object.npy", lambda p: np.save(p, np.array([{"a": 1}, None], dtype=object), allow_pickle=True)
        yield "pickled.npz", lambda p: p.write_bytes(pickle.dumps({"x": [1, 2]}))
        yield "text.npz", lambda p: p.write_text("not an archive at all\n")
        yield "corrupt.npz", lambda p: p.write_bytes(b"PK\x03\x04" + b"\x00" * 40 + b"garbage")

    def test_each_bad_cache_is_unscanned_not_an_error(self):
        for name, make in self.bad_files():
            with self.subTest(name=name):
                out = self.d / f"out-{name}"
                out.mkdir()
                (out / "clean.csv").write_text("bin,yield\nlow,812\n")
                self.np.save(out / "clean.npy", self.np.array([1.0, 2.0]))
                make(out / name)
                self.assertEqual(bl.scan_paths([out], [1234.567])["status"], "incomplete")
                code, stdout, err = run("scan", "--sealed", self.d / "sealed.json", out)
                self.assertNotIn("Traceback", err)
                view = json.loads(stdout)
                self.assertEqual((code, view["status"]), (3, "incomplete"), stdout)
                self.assertEqual([Path(u).name for u in view["unscanned"]], [name])


if __name__ == "__main__":
    unittest.main()
