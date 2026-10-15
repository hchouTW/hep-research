"""CLI input-error regressions for skills/hep-measurement/scripts/mask_blinded_bins.py (synthetic histograms)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "mask_blinded_bins.py"
GOOD = {"edges": [100.0, 110.0, 120.0, 130.0, 140.0], "values": [5.0, 6.0, 7.0, 8.0]}


class MaskBlindedBinsCliTests(unittest.TestCase):
    def run_hist(self, hist, low, high, reference=None):
        with tempfile.TemporaryDirectory() as tmp:
            h = Path(tmp) / "h.json"
            h.write_text(json.dumps(hist), encoding="utf-8")
            extra = []
            if reference is not None:
                r = Path(tmp) / "r.json"
                r.write_text(json.dumps(reference), encoding="utf-8")
                extra = ["--reference", str(r)]
            return subprocess.run([sys.executable, str(SCRIPT), "--hist", str(h), "--low", str(low), "--high", str(high), *extra],
                                  capture_output=True, text=True, timeout=600)

    def assertCleanError(self, proc, text):
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn(text, proc.stderr)

    def test_inverted_or_empty_range_rejected(self):
        self.assertCleanError(self.run_hist(GOOD, 130, 120), "--low < --high")
        self.assertCleanError(self.run_hist(GOOD, 120, 120), "--low < --high")

    def test_missing_keys_reported_cleanly(self):
        self.assertCleanError(self.run_hist({"edges": GOOD["edges"]}, 120, 130), "'values'")
        self.assertCleanError(self.run_hist({"values": GOOD["values"]}, 120, 130), "'edges'")
        self.assertCleanError(self.run_hist(GOOD, 120, 130, reference={"edges": GOOD["edges"]}), "'values'")

    def test_valid_input_still_masks(self):
        proc = self.run_hist(GOOD, 120, 130)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["values"], [5.0, 6.0, None, 8.0])


class FailClosedTests(MaskBlindedBinsCliTests):
    """ANA-P2-7: the script-side guards alone (independent of core.blinding, whose steward is hep-computing)."""

    def test_reference_length_mismatch_exits_2(self):
        proc = self.run_hist(GOOD, 120, 130, reference={"values": [1.0, 2.0]})
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("refusing to align", proc.stderr)

    def test_non_numeric_values_exit_2(self):
        for bad in ([5.0, "x", 7.0, 8.0], [5.0, True, 7.0, 8.0]):
            with self.subTest(bad=bad):
                proc = self.run_hist(dict(GOOD, values=bad), 120, 130)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")

    def test_errors_and_variances_are_masked_with_the_values(self):
        hist = dict(GOOD, errors=[0.5, 0.6, 0.7, 0.8], variances=[0.25, 0.36, 0.49, 0.64])
        out = json.loads(self.run_hist(hist, 120, 130).stdout)
        self.assertEqual(out["values"][2], None)
        self.assertEqual(out["errors"], [0.5, 0.6, None, 0.8])
        self.assertEqual(out["variances"][2], None)
        proc = self.run_hist(dict(GOOD, errors=[0.5, 0.6]), 120, 130)
        self.assertEqual(proc.returncode, 2)

    def test_flow_bins_masked_when_the_range_reaches_them(self):
        hist = dict(GOOD, underflow=3.0, overflow=4.0)
        inner = json.loads(self.run_hist(hist, 120, 130).stdout)
        self.assertEqual((inner["underflow"], inner["overflow"]), (3.0, 4.0))
        upper = json.loads(self.run_hist(hist, 130, 1e9).stdout)
        self.assertEqual((upper["underflow"], upper["overflow"]), (3.0, None))
        lower = json.loads(self.run_hist(hist, -1e9, 105).stdout)
        self.assertIsNone(lower["underflow"])

    def test_ratio_is_masked_and_aligned(self):
        out = json.loads(self.run_hist(GOOD, 120, 130, reference={"values": [1.0, 2.0, 0.0, 4.0]}).stdout)
        self.assertEqual(out["ratio_to_reference"], [5.0, 3.0, None, 2.0])


if __name__ == "__main__":
    unittest.main()
