"""CLI tests for skills/physics-ml/scripts/write_ml_artifact.py: a run summary with a calibration becomes a valid
ml-artifact; a failed split check, a probability output without a calibration and malformed input are refused.
All inputs SYNTHETIC."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "physics-ml" / "scripts" / "write_ml_artifact.py"
SPLIT_SCRIPT = ROOT / "skills" / "physics-ml" / "scripts" / "check_split_integrity.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(ROOT))
import write_ml_artifact as wma  # noqa: E402

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

SUMMARY = {
    "task": "classification", "features": ["x", "y"], "units": {"x": "GeV", "y": "1"}, "labels": ["sig", "bkg"],
    "grouping_key": "run_id", "split_manifest": "splits.json",
    "split_check": {"tool": "check_split_integrity.py", "result": "pass", "report": None},
    "training_domain": {"x": [0.0, 10.0], "y": [-1.0, 1.0]},
    "preprocessing": [{"step": "standardize", "features": ["x", "y"], "mean": [5.0, 0.0], "std": [2.0, 0.5]}],
    "weights": {"source": "synthetic generator weights", "negative_weight_treatment": "none-present",
                "class_balancing": None, "used_in": ["loss", "metrics"]},
    "model_hash": "sha256:" + "ab" * 32, "checkpoint": "model.pt",
    "environment": {"torch_version": "synthetic", "device": "cpu", "precision": "fp32", "seeds": {"torch": 1, "split": 2}},
    "metrics": {"val": {"bce": 0.4}, "test": {"bce": 0.41}}, "scores": {"test": "scores_test.npz"},
}
CALIBRATION = {"calibration": {"method": "temperature", "params": {"T": 1.3}, "fit_sample": "val",
                               "validation": {"metric": "ece", "sample": "test", "before": 0.06, "after": 0.01,
                                              "bins": 15, "binning": "equal-width"}}}
DOMAIN_SHIFT = {"control_sample": "synthetic control region", "method": "score-shape comparison",
                "result": {"ks_p": 0.3}, "status": "checked", "outcome": "no-shift"}
DOWNSTREAM = [{"metric": "working-point-efficiency", "quantity_affected": "signal efficiency in the synthetic signal region",
               "value": 0.51, "uncertainty": 0.02, "criterion": ">= 0.5", "passed": True, "ref": "synthetic"}]


class WriteMlArtifactTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def write(self, name, obj):
        path = self.tmp / name
        path.write_text(json.dumps(obj), encoding="utf-8")
        return str(path)

    def run_main(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = wma.main([*args, "--out", str(self.tmp / "ml.json"), "--created", "2026-10-13"])
        return code, json.loads(buf.getvalue())

    def full_args(self, summary=None):
        return ["--run-summary", self.write("run.json", summary or SUMMARY), "--calibration", self.write("cal.json", CALIBRATION),
                "--domain-shift", self.write("ds.json", DOMAIN_SHIFT), "--downstream", self.write("dv.json", DOWNSTREAM),
                "--output-semantics", "probability", "--status", "synthetic", "--status", "unvalidated"]

    def test_summary_with_calibration_validates(self):
        # the overlap result comes from a report, never from the summary's own claim (PML-WP0.4)
        splits = {"train": ["a", "b"], "test": ["c"], "groups": {"a": "r1", "b": "r1", "c": "r2"}}
        proc = subprocess.run([sys.executable, str(SPLIT_SCRIPT), self.write("splits.json", splits), "--json"],
                              capture_output=True, text=True, timeout=60)
        code, out = self.run_main(*self.full_args(), "--split-report", self.write("rep.json", json.loads(proc.stdout)))
        self.assertEqual((code, out["status"]), (0, "written"), out)
        doc = json.loads((self.tmp / "ml.json").read_text())
        self.assertEqual(doc["contract_version"], CONTRACTS_VERSION)
        self.assertEqual(doc["artifact_type"], "ml-artifact")
        self.assertEqual(doc["status"], ["synthetic", "unvalidated"])
        self.assertEqual(doc["extension"]["calibration"]["validation"]["sample"], "test")
        self.assertEqual(doc["extension"]["splits"]["overlap_check"]["result"], "pass")
        self.assertEqual([o["ref"] for o in doc["outputs"]], ["model.pt", "scores_test.npz"])
        self.assertEqual(doc["inputs"], [])  # tool outputs are source files, not artifact inputs (PML-WP0.5)
        self.assertTrue(all(len(i["sha256"]) == 64 for i in doc["extension"]["source_files"]))
        self.assertTrue(doc["extension"]["splits"]["test_groups_disjoint"])
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertEqual([f.code for f in rep.findings], [])

    def test_validate_cli_accepts_the_output(self):
        code, _ = self.run_main(*self.full_args())
        self.assertEqual(code, 0)
        proc = subprocess.run([sys.executable, str(ROOT / "contracts" / "validate.py"), str(self.tmp / "ml.json")],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_failing_split_check_is_an_error(self):
        summary = dict(SUMMARY, split_check={"tool": "check_split_integrity.py", "result": "fail", "report": "r.json"})
        code, out = self.run_main(*self.full_args(summary))
        self.assertEqual((code, out["status"]), (1, "invalid"))
        self.assertIn("ml.split_overlap", {f["code"] for f in out["findings"] if f["severity"] == "error"})
        self.assertFalse((self.tmp / "ml.json").exists())

    def test_split_report_with_group_leakage_is_an_error(self):
        splits = {"train": ["a", "b"], "test": ["c", "d"], "groups": {"a": "r1", "b": "r2", "c": "r2", "d": "r3"}}
        proc = subprocess.run([sys.executable, str(SPLIT_SCRIPT), self.write("splits.json", splits), "--json"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 1)
        report = self.write("split_report.json", json.loads(proc.stdout))
        code, out = self.run_main(*self.full_args(), "--split-report", report)
        self.assertEqual(code, 1)
        self.assertIn("ml.split_overlap", {f["code"] for f in out["findings"]})

    def test_clean_split_report_sets_disjoint_groups(self):
        splits = {"train": ["a", "b"], "test": ["c"], "groups": {"a": "r1", "b": "r1", "c": "r2"}}
        proc = subprocess.run([sys.executable, str(SPLIT_SCRIPT), self.write("splits.json", splits), "--json"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        code, out = self.run_main(*self.full_args(), "--split-report", self.write("rep.json", json.loads(proc.stdout)))
        self.assertEqual(code, 0, out)
        sp = json.loads((self.tmp / "ml.json").read_text())["extension"]["splits"]
        self.assertEqual((sp["overlap_check"]["result"], sp["test_groups_disjoint"]), ("pass", True))

    def test_incomplete_split_report_is_unresolved(self):
        rep = {"status": "incomplete", "splits": {"train": 2, "test": 1}, "group_leakage": {}, "groups_checked": False}
        code, out = self.run_main(*self.full_args(), "--split-report", self.write("rep.json", rep))
        self.assertEqual(code, 0, out)
        self.assertIn("ml.split_overlap_not_run", {f["code"] for f in out["findings"] if f["severity"] == "unresolved"})

    def test_probability_without_calibration_is_an_error(self):
        code, out = self.run_main("--run-summary", self.write("run.json", SUMMARY), "--output-semantics", "probability",
                                  "--status", "synthetic")
        self.assertEqual(code, 1)
        self.assertIn("ml.calibration_missing", {f["code"] for f in out["findings"] if f["severity"] == "error"})

    def test_score_without_calibration_is_written_with_findings(self):
        code, out = self.run_main("--run-summary", self.write("run.json", SUMMARY), "--output-semantics", "score",
                                  "--status", "synthetic")
        self.assertEqual(code, 0, out)
        self.assertIn("ml.no_downstream_validation", {f["code"] for f in out["findings"]})

    def test_malformed_input_exits_2(self):
        bad = dict(SUMMARY)
        del bad["model_hash"]
        code, out = self.run_main("--run-summary", self.write("run.json", bad))
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = self.run_main("--run-summary", self.write("run.json", SUMMARY), "--calibration",
                                  self.write("cal.json", {"method": "temperature"}))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
