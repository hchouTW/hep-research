"""C2: environment_manifest.py pairs compares the data and simulation software versions declared for each era.
A mismatch fails (exit 1), an undeclared version is incomplete (exit 3), a malformed file is rejected (exit 2).
All inputs are SYNTHETIC."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "environment_manifest.py"


def run(doc):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "pairs.json"
        p.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "pairs", "--pairs", str(p)], capture_output=True,
                            text=True, timeout=600)
    return cp.returncode, json.loads(cp.stdout)


GOOD = {"eras": [{"id": "e1", "data": {"reconstruction": "v5.1", "calibration": "c12"},
                  "mc": {"reconstruction": "v5.1", "calibration": "c12"}},
                 {"id": "e2", "data": {"reconstruction": "v6.0"}, "mc": {"reconstruction": "v6.0"}}]}


class VersionPairs(unittest.TestCase):
    def test_matching_pairs_pass(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertEqual([e["verdict"] for e in out["eras"]], ["match", "match"])

    def test_a_version_mismatch_is_caught(self):
        doc = json.loads(json.dumps(GOOD))
        doc["eras"][1]["mc"]["reconstruction"] = "v5.1"
        code, out = run(doc)
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        e2 = out["eras"][1]
        self.assertEqual(e2["verdict"], "mismatch")
        self.assertEqual(e2["mismatches"], [{"component": "reconstruction", "data": "v6.0", "mc": "v5.1"}])

    def test_undeclared_versions_are_incomplete(self):
        doc = json.loads(json.dumps(GOOD))
        del doc["eras"][0]["mc"]["calibration"]
        doc["eras"][1]["mc"] = {}
        code, out = run(doc)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "incomplete")
        self.assertEqual(out["eras"][0]["undeclared"], [{"component": "calibration", "missing_in": "mc"}])

    def test_malformed_input_is_rejected(self):
        for doc in ("{", {"eras": []}, {"eras": [{"data": {}}]}):
            with self.subTest(doc=doc):
                code, out = run(doc)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
