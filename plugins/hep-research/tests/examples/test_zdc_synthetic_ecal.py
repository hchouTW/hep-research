"""The synthetic ZDC example: its specifications pass, and they fix the committed geometry."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples/zdc-synthetic-ecal"


class SyntheticEcal(unittest.TestCase):
    def test_reproduces_the_committed_output(self):
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--out", folder], capture_output=True, text=True, check=False, timeout=120)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads((Path(folder) / "summary.json").read_text(encoding="utf-8")), json.loads((EXAMPLE / "output/summary.json").read_text(encoding="utf-8")))

    def test_it_is_labelled_synthetic(self):
        self.assertEqual(json.loads((EXAMPLE / "output/summary.json").read_text(encoding="utf-8"))["label"], "synthetic")


if __name__ == "__main__":
    unittest.main()
