"""theory:cr-secondary-ratio envelope artifacts: the theory-spec and the prediction validate with contracts/validate.py,
the stored artifacts are current, and a theory-spec copy without degenerate_directions fails with
theory.degeneracy_missing (contracts 2.6.0 rule for model.family 'cosmic-ray-propagation')."""
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
PRED = ROOT / "predictions" / "bc-benchmark.prediction.json"
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
                                           "experiments": [], "theory": [{"profile": "theory:cr-secondary-ratio",
                                                                          "version": "0.1.0"}]}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_theory_spec_validates(self):
        code, rep = validate(SPEC)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(spec["extension"]["model"]["family"], "cosmic-ray-propagation")
        self.assertEqual(spec["extension"]["degenerate_directions"], ["D0/L"])

    def test_theory_spec_without_degenerate_directions_fails(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        for variant in ("absent", "empty", "blank"):
            doc = copy.deepcopy(spec)
            if variant == "absent":
                del doc["extension"]["degenerate_directions"]
            else:
                doc["extension"]["degenerate_directions"] = [] if variant == "empty" else ["  "]
            with self.subTest(variant=variant):
                code, rep = validate(doc)
                self.assertEqual(code, 1)
                self.assertIn("theory.degeneracy_missing", [f["code"] for f in rep["findings"]])

    def test_prediction_validates_with_the_profile_vocabulary(self):
        code, rep = validate(PRED, self.project)
        self.assertEqual(code, 0, rep)
        self.assertEqual([f for f in rep["findings"] if f["severity"] == "error"], [])

    def test_prediction_level_needs_the_profile(self):
        code, rep = validate(PRED)
        self.assertEqual(code, 1)
        self.assertIn("vocab.unknown_term", [f["code"] for f in rep["findings"]])

    def test_prediction_links_its_theory_spec_and_keeps_labels(self):
        pred = json.loads(PRED.read_text(encoding="utf-8"))
        ext = pred["extension"]
        self.assertEqual(ext["theory_spec_ref"], "derivations/theory-spec.json")
        self.assertIn("synthetic", pred["status"])
        self.assertNotIn("observed", pred["status"])
        alt = [u for u in ext["uncertainties"] if u["kind"] == "model-alternative"]
        self.assertEqual(len(alt), 1)
        self.assertFalse(alt[0]["gaussian"])
        self.assertEqual(len(alt[0]["values"]), len(ext["values"]["values"]))

    @unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
    def test_stored_artifacts_are_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    @unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
    def test_prediction_at_another_point_also_validates(self):
        import make_artifacts
        arts = make_artifacts.build({"D0_cm2_s": 2e28, "L_kpc": 6.0})
        code, rep = validate(arts[make_artifacts.PRED_PATH], self.project)
        self.assertEqual(code, 0, rep)


if __name__ == "__main__":
    unittest.main()
