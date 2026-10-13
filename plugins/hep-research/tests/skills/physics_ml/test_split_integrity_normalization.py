"""check_split_integrity.py review fixes: an ID with a null group is a reported problem, never a silent pass, and
IDs and groups are compared after normalization (whitespace stripped, case folded by default) so cosmetic
differences cannot hide leakage."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "physics-ml" / "scripts" / "check_split_integrity.py"
sys.path.insert(0, str(SCRIPT.parent))
from check_split_integrity import check  # noqa: E402


class NullGroupTests(unittest.TestCase):
    def test_null_group_is_not_a_pass(self):
        # Before the fix, "b" counted as covered but was skipped by the leakage check: status "passed".
        for null in (None, "", "   ", "NaN", "null"):
            with self.subTest(null=null):
                rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "run1", "b": null}})
                self.assertEqual(rep["status"], "incomplete")
                self.assertFalse(rep["passed"])
                self.assertEqual(rep["null_group_ids"], ["b"])
                self.assertEqual(rep["group_coverage"]["missing_ids"], ["b"])
                self.assertFalse(rep["groups_checked"])

    def test_null_group_fails_under_strict(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "run1", "b": None}}, strict=True)
        self.assertEqual((rep["status"], rep["failure_kind"]), ("failed", ["missing-metadata"]))

    def test_cli_reports_null_groups_with_exit_3(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "s.json"
            f.write_text(json.dumps({"train": ["a"], "test": ["b"], "groups": {"a": "run1", "b": None}}))
            res = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f)], capture_output=True, text=True,
                                 timeout=600)
        self.assertEqual(res.returncode, 3)
        self.assertIn("null or empty group", res.stdout)


class NormalizationTests(unittest.TestCase):
    def test_group_case_and_whitespace_variants_leak(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "Run7", "b": " run7 "}})
        self.assertEqual(rep["status"], "failed")
        self.assertEqual(rep["group_leakage"], {"run7": ["test", "train"]})

    def test_id_variants_overlap(self):
        rep = check({"train": ["Ev1 "], "test": ["ev1"], "groups": {"ev1": "r1"}})
        self.assertEqual(rep["overlaps_between_splits"], {"test|train": ["ev1"]})
        self.assertEqual(rep["status"], "failed")

    def test_case_sensitive_opt_out(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "Run7", "b": "run7 "}}, case_sensitive=True)
        self.assertEqual(rep["group_leakage"], {})
        self.assertEqual(rep["status"], "passed")
        self.assertEqual(rep["normalization"], {"strip_whitespace": True, "case_sensitive": True})

    def test_group_keys_normalized_to_the_split_ids(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {" A": "r1", "B ": "r2"}})
        self.assertEqual(rep["status"], "passed")

    def test_conflicting_keys_after_normalization_are_reported(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "r1", "A": "r2", "b": "r3"}})
        self.assertEqual(rep["normalization_conflicts"]["groups"], ["a"])
        self.assertEqual(rep["status"], "incomplete")
        self.assertEqual(rep["group_coverage"]["missing_ids"], ["a"])


if __name__ == "__main__":
    unittest.main()
