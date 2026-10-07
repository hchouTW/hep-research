"""T21: local chunk resubmission and merge (SYNTHETIC job with injected failures)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]

try:
    import numpy  # noqa: F401
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


@unittest.skipUnless(HAVE_NP, "numpy required (D5 environment)")
class PartitionExampleTests(unittest.TestCase):
    def test_every_criterion_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, str(PLUGIN / "examples" / "local-partition" / "run.py"), "--out", td],
                               capture_output=True, text=True, timeout=1200)
            r = json.loads((Path(td) / "results.json").read_text())
        self.assertEqual(p.returncode, 0, r["pass"])
        self.assertTrue(all(v is True for v in r["pass"].values()), r["pass"])
