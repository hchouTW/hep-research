"""physics-ml audit (PML-WP0.4: ML-C06, ML-K11, ML-C07): write_ml_artifact.py does not trust self-reported results.

Before the fix (0.9.0): a split report whose status said "passed" while it listed leakage was copied as a pass; the
test split was found by the substring "test", so a split named "TEST" or "holdout" escaped the disjointness check; a
run summary's split_check "pass" with no report behind it became overlap_check "pass"; and an artifact written
without --status from a synthetic run lost the "synthetic" label (default "unvalidated"). All inputs SYNTHETIC.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "physics-ml" / "scripts" / "write_ml_artifact.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(ROOT))
import write_ml_artifact as wma  # noqa: E402

SUMMARY = {"task": "classification", "features": ["x"], "labels": ["bkg", "sig"], "grouping_key": "run",
           "training_domain": {"x": [0.0, 1.0]}, "preprocessing": [], "model_hash": "sha256:" + "ab" * 32,
           "environment": {"device": "cpu", "precision": "fp32", "seeds": {"torch": 1}},
           "weights": {"source": "w", "negative_weight_treatment": "none-present", "used_in": ["loss"]}}
CLEAN = {"status": "passed", "splits": {"train": 2, "val": 1, "test": 1}, "duplicates_within_split": {},
         "overlaps_between_splits": {}, "group_leakage": {}, "temporal_violations": {}, "groups_checked": True,
         "group_coverage": {"covered": 4, "total": 4, "fraction": 1.0, "missing_ids": []}}


class WriterTrustTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def write(self, name, obj):
        path = self.tmp / name
        path.write_text(json.dumps(obj))
        return str(path)

    def run_main(self, *args, summary=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = wma.main(["--run-summary", self.write("run.json", summary or SUMMARY), *args,
                             "--out", str(self.tmp / "ml.json"), "--created", "2026-10-14"])
        return code, json.loads(buf.getvalue())

    def doc(self):
        return json.loads((self.tmp / "ml.json").read_text())

    def test_passed_report_that_lists_leakage_is_refused(self):
        for key, value in (("group_leakage", {"r2": ["test", "train"]}), ("overlaps_between_splits", {"test|train": ["a"]}),
                           ("temporal_violations", {"train|test": {}}), ("duplicates_within_split", {"train": ["a"]})):
            with self.subTest(key):
                report = dict(CLEAN, **{key: value})
                code, out = self.run_main("--split-report", self.write("rep.json", report), "--status", "synthetic")
                self.assertEqual(code, 2, out)
                self.assertIn("contradicts", out["error"])

    def test_passed_report_with_incomplete_coverage_is_refused(self):
        report = dict(CLEAN, groups_checked=False,
                      group_coverage={"covered": 3, "total": 4, "fraction": 0.75, "missing_ids": ["d"]})
        code, out = self.run_main("--split-report", self.write("rep.json", report), "--status", "synthetic")
        self.assertEqual(code, 2, out)

    def test_test_split_named_in_capitals_or_by_role(self):
        report = dict(CLEAN, status="failed", splits={"train": 2, "TEST": 1}, group_leakage={"r2": ["TEST", "train"]})
        code, out = self.run_main("--split-report", self.write("rep.json", report), "--status", "synthetic")
        self.assertEqual(code, 1, out)  # leakage is an error finding, the artifact is not written
        self.assertIn("ml.split_overlap", {f["code"] for f in out["findings"]})
        manifest = self.write("m.json", {"train": ["a"], "holdout": ["b"], "roles": {"test": "holdout"},
                                         "groups": {"a": "r1", "b": "r2"}})
        report = dict(CLEAN, splits={"train": 1, "holdout": 1})
        code, out = self.run_main("--split-report", self.write("rep.json", report), "--status", "synthetic",
                                  summary=dict(SUMMARY, split_manifest=manifest))
        self.assertEqual(code, 0, out)
        self.assertTrue(self.doc()["extension"]["splits"]["test_groups_disjoint"])

    def test_self_declared_pass_without_report_is_not_run(self):
        summary = dict(SUMMARY, split_check={"tool": "check_split_integrity.py", "result": "pass"})
        code, out = self.run_main("--status", "synthetic", summary=summary)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["extension"]["splits"]["overlap_check"]["result"], "not-run")
        summary = dict(SUMMARY, split_check={"tool": "check_split_integrity.py", "result": "pass",
                                             "report": self.write("rep.json", dict(CLEAN, status="failed",
                                                                                     group_leakage={"r": ["test", "train"]}))})
        code, out = self.run_main("--status", "synthetic", summary=summary)
        self.assertEqual(code, 1, out)  # the report behind the claimed pass shows leakage

    def test_status_is_required_unless_the_summary_carries_one(self):
        code, out = self.run_main()
        self.assertEqual(code, 2, out)
        self.assertIn("--status", out["error"])
        code, out = self.run_main(summary=dict(SUMMARY, status="synthetic"))
        self.assertEqual(code, 0, out)
        self.assertIn("synthetic", self.doc()["status"])
        code, out = self.run_main("--status", "unvalidated", summary=dict(SUMMARY, status="synthetic"))
        self.assertEqual(code, 0, out)
        self.assertEqual(set(self.doc()["status"]), {"synthetic", "unvalidated"})  # a sticky label is never dropped


if __name__ == "__main__":
    unittest.main()
