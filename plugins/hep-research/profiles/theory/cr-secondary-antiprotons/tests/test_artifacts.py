"""theory:cr-secondary-antiprotons envelope artifacts: the theory-spec and the prediction validate with
contracts/validate.py, the stored artifacts are current, and the theory-spec needs no degenerate_directions because
its model.family is a source term; the same spec relabelled as 'cosmic-ray-propagation' fails with
theory.degeneracy_missing (the rule's trigger is the declared family)."""
import copy
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
PRED = ROOT / "predictions" / "source-term-benchmark.prediction.json"
sys.path.insert(0, str(ROOT / "scripts"))


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
                                           "experiments": [], "theory": [{"profile": "theory:cr-secondary-antiprotons",
                                                                          "version": "0.1.0"}]}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_theory_spec_validates_without_degenerate_directions(self):
        code, rep = validate(SPEC)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(spec["extension"]["model"]["family"], "cosmic-ray-secondary-source-term")
        self.assertNotIn("degenerate_directions", spec["extension"])

    def test_relabelled_as_propagation_family_fails(self):
        doc = copy.deepcopy(json.loads(SPEC.read_text(encoding="utf-8")))
        doc["extension"]["model"]["family"] = "cosmic-ray-propagation"
        code, rep = validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("theory.degeneracy_missing", [f["code"] for f in rep["findings"]])

    def test_b2_recorded_as_not_run(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertTrue(any("B2" in c for c in spec["extension"]["checks_not_run"]))
        self.assertEqual(spec["extension"]["references_read"], [])

    def test_prediction_validates_with_the_profile_vocabulary(self):
        code, rep = validate(PRED, self.project)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])

    def test_prediction_level_needs_the_profile(self):
        code, rep = validate(PRED)
        self.assertEqual(code, 1)
        self.assertIn("vocab.unknown_term", [f["code"] for f in rep["findings"]])

    def test_prediction_model_alternatives_and_labels(self):
        pred = json.loads(PRED.read_text(encoding="utf-8"))
        ext = pred["extension"]
        self.assertEqual(ext["theory_spec_ref"], "derivations/theory-spec.json")
        self.assertIn("synthetic", pred["status"])
        alts = [u for u in ext["uncertainties"] if u["kind"] == "model-alternative"]
        self.assertEqual(len(alts), 2)
        for a in alts:
            self.assertFalse(a["gaussian"])
            self.assertEqual(len(a["values"]), len(ext["values"]["values"]))
        self.assertTrue(all(v > 0 for v in ext["values"]["values"]))

    @unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
    def test_stored_artifacts_are_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
