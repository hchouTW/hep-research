"""physics-ml handoffs (PML-WP2.1, ML-K15): one test per SKILL.md handoff row that had none. hep-statistics has its
own (tests/contracts/test_ml_provenance_gate.py). Each test passes an ml-artifact (or a check it records) across the
boundary and shows that the receiving side sees what it needs, or that a broken handoff is refused. All SYNTHETIC."""
import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "physics-ml" / "scripts"))
import check_surrogate_domain  # noqa: E402
from contracts import dependencies  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

VALID = PLUGIN / "contracts" / "fixtures" / "artifacts" / "valid"
ML = json.loads((VALID / "ml_artifact_v25.json").read_text())


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


class TheoryHandoff(unittest.TestCase):
    """hep-theory: the physics and validity domain of a surrogate. A theory parameter point outside the surrogate's
    declared domain is flagged before the surrogate's prediction is used; a surrogate without an extrapolation
    policy is refused."""

    def test_parameter_point_outside_the_domain_is_flagged(self):
        rep = check_surrogate_domain.check({"features": ["mass", "coupling"],
                                            "training_domain": {"mass": [100.0, 500.0], "coupling": [0.1, 1.0]},
                                            "queries": [[300.0, 0.5], [800.0, 0.5]]})
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside"])

    def test_surrogate_needs_an_extrapolation_policy(self):
        doc = copy.deepcopy(ML)
        doc["extension"].update(task="surrogate", output_semantics="regression-value")
        doc["extension"].pop("calibration")
        self.assertIn("ml.task_validation_missing", codes(validate_artifact(doc)))
        doc["extension"]["extrapolation_policy"] = {"action": "flag", "consumer": "hep-theory prediction"}
        self.assertTrue(validate_artifact(doc).ok, validate_artifact(doc).as_dict())


class AnalysisHandoff(unittest.TestCase):
    """hep-analysis: the working point of a selection built on the score must come from validation."""

    def test_working_point_from_validation_only(self):
        doc = copy.deepcopy(ML)
        doc["extension"]["metrics"] = {"test": {"working_point": {"threshold_from": "val", "threshold": 0.8}}}
        self.assertTrue(validate_artifact(doc).ok)
        doc["extension"]["metrics"]["test"]["working_point"]["threshold_from"] = "test"
        self.assertIn("ml.threshold_from_test", codes(validate_artifact(doc)))


class DetectorResponseHandoff(unittest.TestCase):
    """detector-response: a fast-simulation (generative) model hands over its physics validation, with the power of
    its two-sample test, for detector-level validation against full simulation."""

    def test_generative_model_needs_physics_validation_with_power(self):
        doc = copy.deepcopy(ML)
        doc["extension"].update(task="generation", output_semantics="generated-sample")
        doc["extension"].pop("calibration")
        self.assertIn("ml.task_validation_missing", codes(validate_artifact(doc)))
        doc["extension"]["generative_validation"] = {
            "observables": {"shower_depth": {"metric": "Wasserstein-1", "value": 0.02}},
            "two_sample_test": {"method": "classifier AUC", "result": 0.51},
            "conditioning_range": {"x": [0.0, 1.0]}}
        self.assertIn("ml.two_sample_power_missing", codes(validate_artifact(doc)))
        doc["extension"]["generative_validation"]["two_sample_test"].update(
            power=0.9, injected_distortion="shower depth scaled by 1.05")
        self.assertTrue(validate_artifact(doc).ok, validate_artifact(doc).as_dict())


def write(path, doc):
    path.write_text(json.dumps(doc))
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ComputingAndCommunicationHandoff(unittest.TestCase):
    """hep-computing (a computational-run that used the model) and research-communication (a write-up that cites
    it): the downstream artifact resolves the ml-artifact by hash and must carry its 'synthetic' label."""

    def chain(self, consumer_name, carry_label):
        d = Path(self._td.name)
        ml_sha = write(d / "ml.json", ML)
        consumer = json.loads((VALID / consumer_name).read_text())
        consumer["inputs"] = [{"ref": "ml.json", "artifact_type": "ml-artifact", "sha256": ml_sha,
                               "status": ML["status"]}]
        labels = set(consumer["status"])
        consumer["status"] = sorted(labels | {"synthetic"} if carry_label else labels - {"synthetic"})
        write(d / "consumer.json", consumer)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = dependencies.main([str(d / "consumer.json"), "--root", str(d)])
        return code, {f["code"] for f in json.loads(out.getvalue())["findings"]}

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)

    def test_computational_run_and_communication(self):
        for name in ("computational_run.json", "communication.json"):
            with self.subTest(name):
                code, found = self.chain(name, carry_label=True)
                self.assertNotIn("dependency.status_not_propagated", found)
                self.assertNotIn("dependency.source_invalid", found)
                code, found = self.chain(name, carry_label=False)
                self.assertEqual(code, 1)
                self.assertIn("dependency.status_not_propagated", found)


if __name__ == "__main__":
    unittest.main()
