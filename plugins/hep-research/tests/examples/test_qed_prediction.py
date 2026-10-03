"""Path C (journey J4) regression tests: standalone theory with theory:qed-benchmark and zero experiment resources."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "qed-prediction" / "run.py"

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import sympy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy, sympy and matplotlib are required (D5 environment)")
class PathCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        # a fresh interpreter, so the record of opened files covers the whole run
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True)
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stdout + self.proc.stderr)
        self.assertTrue(all(self.r["pass"].values()))

    def test_zero_experiment_resources(self):
        self.assertTrue(self.r["profile_files_read"])
        self.assertTrue(all(p.startswith("profiles/theory/qed-benchmark/") for p in self.r["profile_files_read"]), self.r["profile_files_read"])
        for name in ("theory_spec", "prediction"):
            doc = json.loads((self.out / "artifacts" / f"{name}.json").read_text())
            self.assertEqual(doc["bindings"]["experiments"], [])
        spec = json.loads((self.out / "artifacts" / "theory_spec.json").read_text())["extension"]
        for field in ("blinding", "detector", "luminosity", "data"):
            self.assertNotIn(field, spec)
            self.assertIn(field, " ".join(spec["inapplicable"]))

    def test_status_and_reference(self):
        spec = json.loads((self.out / "artifacts" / "theory_spec.json").read_text())["extension"]
        self.assertEqual(spec["derivation_status"], "analytic-derivation")
        self.assertIn("51.2", spec["references_read"][0]["location"])
        self.assertTrue(any("formal proof" in c for c in spec["checks_not_run"]))
        self.assertTrue(all(c["result"] == "pass" for c in spec["checks_run"]))

    def test_prediction_units_and_uncertainties(self):
        pred = json.loads((self.out / "artifacts" / "prediction.json").read_text())["extension"]
        self.assertEqual(pred["values"]["unit"], "pb")
        kinds = {u["kind"] for u in pred["values"]["uncertainties"]} | {u["kind"] for u in pred["uncertainties"]}
        self.assertEqual(kinds, {"parametric", "numerical", "truncation"})
        self.assertFalse(any(u.get("gaussian") for u in pred["uncertainties"]))
        self.assertAlmostEqual(self.r["prediction"]["sigma_total_pb"], 868.0, places=9)


if __name__ == "__main__":
    unittest.main()
