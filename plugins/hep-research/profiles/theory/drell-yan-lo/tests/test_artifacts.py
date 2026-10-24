"""theory:drell-yan-lo envelope artifacts: the theory-spec and the prediction validate with contracts/validate.py,
the references read carry their date, the model alternative is not Gaussian, and the stored artifacts are current."""
import json
import subprocess
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
VALIDATE = PLUGIN / "contracts" / "validate.py"
SPEC = ROOT / "derivations" / "theory-spec.json"
PRED = ROOT / "predictions" / "angular-coefficients.prediction.json"
PROFILE_ID = "theory:drell-yan-lo"


def validate(doc_or_path, project: Path | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        path = doc_or_path
        if isinstance(doc_or_path, dict):
            path = Path(tmp) / "artifact.json"
            path.write_text(json.dumps(doc_or_path), encoding="utf-8")
        cmd = [sys.executable, str(VALIDATE), str(path)] + (["--profiles-from", str(project)] if project else [])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout)


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.tmp.name) / "hep-research.project.json"
        cls.project.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.10,<1.0",
                                           "experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                          "version": "0.1.0"}]}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_theory_spec_validates_clean(self):
        code, rep = validate(SPEC)
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["findings"], [])

    def test_theory_spec_content(self):
        ext = json.loads(SPEC.read_text(encoding="utf-8"))["extension"]
        self.assertEqual(ext["derivation_status"], "perturbative-argument")
        self.assertIn("O(alpha_s^1)", ext["order"])
        self.assertEqual(len(ext["references_read"]), 2)
        self.assertTrue(all(r["date_read"] == "2026-10-23" for r in ext["references_read"]))
        self.assertTrue(any("Eq. 9" in c for c in ext["checks_not_run"]))
        for key in ("exchanged_bosons", "rapidity_frame", "azimuth_convention", "em_coupling"):
            self.assertIn(key, ext["conventions"])

    def test_prediction_validates_with_the_profile_vocabulary(self):
        code, rep = validate(PRED, self.project)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])

    def test_prediction_vocabulary_needs_the_profile(self):
        code, rep = validate(PRED)
        self.assertEqual(code, 1)
        self.assertIn("vocab.unknown_term", [f["code"] for f in rep["findings"]])

    def test_prediction_content(self):
        pred = json.loads(PRED.read_text(encoding="utf-8"))
        ext = pred["extension"]
        self.assertNotIn("observed", pred["status"])
        self.assertTrue(all(ext["point_values"]["checks"].values()))
        self.assertEqual(set(ext["point_values"]["channels"]), {"qqbar", "qg"})
        self.assertEqual(ext["uncertainties"], [])  # the A-average mixture is exact: no mixing-rule alternative
        self.assertNotIn("lambda and nu averaged", json.dumps(pred))

    def test_gaussian_model_alternative_rejected(self):
        doc = json.loads(PRED.read_text(encoding="utf-8"))
        doc["extension"]["uncertainties"] = [{"name": "test input", "kind": "model-alternative",
                                              "correlation": "fully-correlated", "gaussian": True}]
        code, rep = validate(doc, self.project)
        self.assertEqual(code, 1)
        self.assertIn("uncertainty.auto_gaussian", [f["code"] for f in rep["findings"]])

    @unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
    def test_stored_artifacts_are_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
