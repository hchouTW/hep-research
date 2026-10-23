"""theory:dis-parton-model envelope artifacts: the theory-spec and the prediction validate with contracts/validate.py,
both are labelled synthetic, the references read carry their date, and the stored artifacts are current."""
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
PRED = ROOT / "predictions" / "fl-toy-grid.prediction.json"
PROFILE_ID = "theory:dis-parton-model"


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
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        ext = spec["extension"]
        self.assertEqual(ext["derivation_status"], "perturbative-argument")
        self.assertIn("alpha_s^1", ext["order"])
        self.assertIn("synthetic", spec["status"])
        self.assertEqual(len(ext["references_read"]), 2)
        self.assertTrue(all(r["date_read"] == "2026-10-23" for r in ext["references_read"]))
        self.assertTrue(any("published F_L" in c for c in ext["checks_not_run"]))
        for key in ("target_normalization", "exchanged_bosons", "heavy_quark_scheme", "factorization_scheme",
                    "target_mass_treatment"):
            self.assertIn(key, ext["conventions"])

    def test_missing_order_is_an_error(self):
        doc = json.loads(SPEC.read_text(encoding="utf-8"))
        doc["extension"]["order"] = ""
        code, rep = validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("theory.order_missing", [f["code"] for f in rep["findings"]])

    def test_prediction_validates_with_the_profile_vocabulary(self):
        code, rep = validate(PRED, self.project)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])

    def test_prediction_vocabulary_needs_the_profile(self):
        code, rep = validate(PRED)
        self.assertEqual(code, 1)
        self.assertIn("vocab.unknown_term", [f["code"] for f in rep["findings"]])

    def test_prediction_labels_and_values(self):
        pred = json.loads(PRED.read_text(encoding="utf-8"))
        self.assertEqual(pred["status"], ["synthetic", "unvalidated"])
        ext = pred["extension"]
        self.assertEqual(ext["theory_spec_ref"], "derivations/theory-spec.json")
        rows = ext["point_values"]["rows"]
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(0.0 <= r["FL"] <= r["F2"] for r in rows))
        self.assertTrue(all(ext["point_values"]["checks"].values()))
        self.assertFalse(any(u.get("gaussian") for u in ext["uncertainties"]))

    def test_observed_status_rejected(self):
        doc = json.loads(PRED.read_text(encoding="utf-8"))
        doc["status"] = ["observed"]
        doc["inputs"][0]["status"] = []
        code, rep = validate(doc, self.project)
        self.assertEqual(code, 1)
        self.assertIn("prediction.status_upgraded", [f["code"] for f in rep["findings"]])

    @unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
    def test_stored_artifacts_are_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
