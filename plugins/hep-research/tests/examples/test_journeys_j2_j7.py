"""Journeys J2 (detector study) and J7 (recast): SYNTHETIC executed examples. Reproduction against the committed
output, every pre-declared criterion, synthetic labels, and the profiles each one loads."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
try:
    import numpy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _Example:
    script = None
    args = []
    profiles = []

    @classmethod
    def setUpClass(cls):
        cls.mod = load(cls.script.stem, cls.script)
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(cls.args + ["--out", cls.tmp.name])
        cls.r = json.loads((Path(cls.tmp.name) / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()))

    def test_reproduces_committed_output(self):
        committed = (self.script.parent / "output" / "results.json").read_bytes()
        self.assertEqual((Path(self.tmp.name) / "results.json").read_bytes(), committed)

    def test_synthetic_everywhere(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        for f in (Path(self.tmp.name) / "artifacts").glob("*.json"):
            self.assertIn("synthetic", json.loads(f.read_text())["status"], f.name)
        self.assertIn("SYNTHETIC", (Path(self.tmp.name) / "report.md").read_text())

    def test_profiles_loaded(self):
        self.assertEqual(self.r["profiles_loaded"], self.profiles)


@unittest.skipUnless(HAVE_DEPS, "numpy and matplotlib not installed")
class J2DetectorStudyTests(_Example, unittest.TestCase):
    script = PLUGIN / "examples" / "detector-resolution" / "run_j2.py"
    profiles = ["experiment:synthetic-collider"]

    def test_records_are_detector_level_resolution_and_efficiency(self):
        art = Path(self.tmp.name) / "artifacts"
        q = {json.loads((art / f"{n}.json").read_text())["extension"]["observable"]["quantity"] for n in ("resolution", "efficiency")}
        self.assertEqual(q, {"resolution", "efficiency"})
        self.assertEqual(json.loads((art / "resolution.json").read_text())["extension"]["observable"]["level"], "detector")


@unittest.skipUnless(HAVE_DEPS, "numpy not installed")
class J7RecastTests(_Example, unittest.TestCase):
    script = PLUGIN / "examples" / "recasting" / "run_j7.py"
    profiles = []

    def test_outside_validity_is_refused(self):
        with self.assertRaises(self.mod.ValidityError):
            self.mod.efficiency(1000.0)
        with self.assertRaises(self.mod.ValidityError):
            self.mod.efficiency(150.0)

    def test_double_efficiency_named(self):
        mm = self.r["double_efficiency_variant"]["mismatches"]
        self.assertTrue(any("already applied before folding" in m["reason"] for m in mm))

    def test_response_is_parametrized_with_validity(self):
        resp = json.loads((Path(self.tmp.name) / "artifacts" / "efficiency_map.json").read_text())["extension"]
        self.assertEqual(resp["form"], "parametrized")
        self.assertEqual(resp["parametrization"]["validity_range"], {"m_X": [200.0, 800.0]})

    def test_closed_form_reference(self):
        # independent of the toys: CLs with no background uncertainty for n = 9, b = 6.2
        self.assertAlmostEqual(self.mod.closed_form_cls(9, 6.2, 0.95), 9.7178, places=3)


if __name__ == "__main__":
    unittest.main()
