"""theory:tmd-gaussian-lo envelope artifacts: the theory-spec and the three predictions validate with
contracts/validate.py, carry their labels, cite the references read with dates, and are current."""
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
PREDS = sorted((ROOT / "predictions").glob("*.prediction.json"))
PROFILE_ID = "theory:tmd-gaussian-lo"


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
        self.assertEqual(ext["derivation_status"], "heuristic-argument")
        self.assertEqual(len(ext["references_read"]), 3)
        self.assertTrue(all(r["date_read"] == "2026-10-23" for r in ext["references_read"]))
        self.assertTrue(any("Drell-Yan Sivers asymmetry" in c for c in ext["checks_not_run"]))
        self.assertIn("synthetic", spec["status"])
        for key in ("polarization_convention", "azimuth_convention", "exchanged_bosons", "target_normalization"):
            self.assertIn(key, ext["conventions"])

    def test_three_predictions_validate_with_the_profile_vocabulary(self):
        self.assertEqual(len(PREDS), 3)
        for p in PREDS:
            with self.subTest(p=p.name):
                code, rep = validate(p, self.project)
                self.assertEqual(code, 0, rep)
                self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])

    def test_sidis_prediction_needs_the_profile(self):
        code, rep = validate(ROOT / "predictions" / "sidis-fuut.prediction.json")
        self.assertEqual(code, 1)
        self.assertIn("vocab.unknown_term", [f["code"] for f in rep["findings"]])

    def test_prediction_labels(self):
        for p in PREDS:
            doc = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(doc["status"], ["synthetic", "unvalidated"])
            self.assertEqual(doc["extension"]["derivation_status"], "heuristic-argument")
            self.assertTrue(all(doc["extension"]["point_values"]["checks"].values()))
        siv = json.loads((ROOT / "predictions" / "sivers-asymmetry.prediction.json").read_text(encoding="utf-8"))
        for r in siv["extension"]["point_values"]["sivers_function"]:
            self.assertEqual(r["Delta_N_f_DY"], -r["Delta_N_f_SIDIS"])

    def test_observed_status_rejected(self):
        doc = json.loads((ROOT / "predictions" / "dy-qt-shape.prediction.json").read_text(encoding="utf-8"))
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
