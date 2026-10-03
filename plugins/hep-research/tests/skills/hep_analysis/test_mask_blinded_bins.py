"""CLI input-error regressions for skills/hep-analysis/scripts/mask_blinded_bins.py (synthetic histograms)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-analysis" / "scripts" / "mask_blinded_bins.py"
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
                                  capture_output=True, text=True)

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


if __name__ == "__main__":
    unittest.main()
