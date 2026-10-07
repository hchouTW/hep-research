"""B11: the T21 job as a batch campaign on fake Slurm and HTCondor schedulers (SYNTHETIC, injected faults)."""
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
class BatchPartitionExampleTests(unittest.TestCase):
    def test_every_criterion_passes_and_output_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, str(PLUGIN / "examples" / "batch-partition" / "run.py"), "--out", td],
                               capture_output=True, text=True, timeout=1200)
            fresh = (Path(td) / "results.json").read_bytes()
        r = json.loads(fresh)
        self.assertEqual(p.returncode, 0, r["pass"])
        for backend in ("slurm", "htcondor"):
            self.assertTrue(all(v is True for v in r["pass"][backend].values()), r["pass"][backend])
        self.assertIn("SYNTHETIC", r["label"])
        self.assertIn("FAKE", r["label"])
        self.assertEqual(fresh, (PLUGIN / "examples" / "batch-partition" / "output" / "results.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
