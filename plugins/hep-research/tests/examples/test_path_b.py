"""Path B (journey J3) regression tests: SYNTHETIC corrected angular distribution with the illustrative
experiment:synthetic-collider profile. Reproducibility, Asimov and toy closure, independent expected values,
contract validity, synthetic labels, and that no other profile (AMS, theory) is loaded."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "collider-angular" / "run_path_b.py"

try:
    import numpy as np
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def load():
    spec = importlib.util.spec_from_file_location("run_path_b", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_path_b"] = mod
    spec.loader.exec_module(mod)
    return mod


def run(mod, *argv):
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.main(list(argv))


@unittest.skipUnless(HAVE_DEPS, "numpy and matplotlib are required (D5 environment)")
class PathBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "a"
        cls.code = run(cls.m, "--out", str(cls.out))
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.r["pass"])

    def test_reproducible(self):
        other = Path(self.tmp.name) / "b"
        run(self.m, "--out", str(other))
        h = [hashlib.sha256((d / "results.json").read_bytes()).hexdigest() for d in (self.out, other)]
        self.assertEqual(h[0], h[1])

    def test_expected_values_are_independent_of_the_chain(self):
        # analytic: f = 1 + c^2, norm 8/3; bin [0, 0.18): sigma * (0.18 + 0.18^3/3) / (8/3) / 0.18
        e = self.m.expected_dsigma(870.0, 1.0, 0.0)
        j = list(self.m.TE).index(0.0)
        self.assertAlmostEqual(e[j], 870.0 * (0.18 + 0.18 ** 3 / 3) / (8 / 3) / 0.18, places=9)
        # integrating the expected values over [-1, 1] returns the generator cross section
        self.assertAlmostEqual(float(np.sum(e * self.m.WIDTH)), 870.0, places=9)

    def test_asimov_closure_exact(self):
        self.assertLess(max(self.r["asimov_closure"].values()), 1e-9)

    def test_measurement_consistent_with_expected(self):
        f = self.r["fiducial_cross_section_pb"]
        self.assertLess(abs(f["value"] - f["expected"]), 4 * (f["stat"] ** 2 + f["lumi"] ** 2) ** 0.5)
        self.assertGreater(self.r["chi2_vs_expected"]["p_value"], 1e-3)

    def test_luminosity_normalization_and_artifacts(self):
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        norm = spec["extension"]["observable"]["normalization"]
        self.assertEqual((norm["kind"], norm["value"], norm["unit"]), ("integrated-luminosity", 20.0, "pb^-1"))
        self.assertTrue(all(c["ok"] for c in self.r["contract_validation"].values()))
        for f in (self.out / "artifacts").glob("*.json"):
            doc = json.loads(f.read_text())
            self.assertIn("synthetic", doc["status"])
            self.assertEqual([b["profile"] for b in doc["bindings"]["experiments"]], ["experiment:synthetic-collider"])
            self.assertEqual(doc["bindings"]["theory"], [])

    def test_only_the_illustrative_profile_is_loaded(self):
        self.assertEqual(self.r["profiles_loaded"], ["experiment:synthetic-collider"])
        text = SCRIPT.read_text()
        for forbidden in ("ams-02", "ams02", "profiles/theory", "qed"):
            self.assertNotIn(forbidden, text.lower())

    def test_labels(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        self.assertIn("ILLUSTRATIVE", (self.out / "report.md").read_text().splitlines()[0])


if __name__ == "__main__":
    unittest.main()
