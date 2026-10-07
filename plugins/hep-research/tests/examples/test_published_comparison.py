"""T24 (journey J6): published-data comparison via a SYNTHETIC dataset record; no detector module is read."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "published-comparison" / "run.py"
PRED = json.loads((PLUGIN / "profiles" / "theory" / "qed-benchmark" / "predictions" / "sqrt_s_10gev.json").read_text())

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy and scipy are required (D5 environment)")
class T24Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "t24"
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True)
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes(self):
        self.assertEqual(self.proc.returncode, 0, self.r["pass"])

    def test_no_detector_module_or_profile_file_read(self):
        self.assertEqual(self.r["detector_files_read"], [])
        self.assertFalse(any(f.startswith("profiles/experiments/") for f in self.r["files_read"]))
        self.assertIn("examples/published-comparison/synthetic-published-record.json", self.r["files_read"])

    def test_gate_transformations_declared(self):
        self.assertEqual(self.r["gate_transformations"], ["level-identification", "fiducial-restriction"])

    def test_T08_conversion_independently_checked(self):
        # the restricted prediction integrates to the theory profile's own fiducial cross section
        self.assertAlmostEqual(self.r["fiducial_prediction_pb"], PRED["sigma_fiducial_pb"], places=9)
        self.assertEqual(self.r["edges"][0], -0.9)
        self.assertEqual(self.r["edges"][-1], 0.9)

    def test_limitation_on_multiplicative_covariance_reported(self):
        self.assertIn("Peelle", (self.out / "report.md").read_text())


    def test_files_read_does_not_depend_on_the_bytecode_cache(self):
        """An import opens the .py source on a cold cache and the cached .pyc on a warm one; the record of files read
        must be the same either way (FULLTEST-E3 L04)."""
        cold, warm = cold_and_warm(SCRIPT, "files_read")
        self.assertEqual(cold, warm)

    @unittest.skipUnless((SCRIPT.parent / "output" / "results.json").is_file(), "no committed output in this copy")
    def test_files_read_match_the_committed_output(self):
        committed = json.loads((SCRIPT.parent / "output" / "results.json").read_text())["files_read"]
        self.assertEqual(self.r["files_read"], committed)


def cold_and_warm(script, key):
    """Run `script` twice against a fresh bytecode cache: cold (sources compiled), then warm (cached .pyc read). The
    cache sits inside the plugin's profiles/ folder, where a cold in-tree cache writes its temporary .pyc.<id> files
    (E4); outside the plugin those writes were invisible to the record."""
    got = []
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory(dir=PLUGIN / "profiles", prefix=".pyc-test-") as cache:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
        for run in ("cold", "warm"):
            p = subprocess.run([sys.executable, str(script), "--out", str(Path(td) / run)], capture_output=True, text=True, env=env)
            if p.returncode:
                raise AssertionError(p.stdout[-1000:] + p.stderr[-2000:])
            got.append(json.loads((Path(td) / run / "results.json").read_text())[key])
    return got


if __name__ == "__main__":
    unittest.main()
