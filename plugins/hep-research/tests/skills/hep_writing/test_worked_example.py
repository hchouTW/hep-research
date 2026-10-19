"""The synthetic worked example of evidence-linked writing (plan T11): result artifact -> claim map -> paragraph and
caption -> changed result -> impact report -> response draft, with an unresolved-evidence branch. `run.py` regenerates
the reports into a temporary folder; they must equal the committed output byte for byte (relative paths only)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
EXAMPLE = PLUGIN / "skills" / "hep-writing" / "examples" / "evidence-linked"
STEPS = ("01-check-communication", "02-audit-claims", "03-revision-impact", "04-responses", "05-unresolved-source")


class WorkedExample(unittest.TestCase):
    def test_reports_regenerate_byte_identical(self):
        self.assertTrue((EXAMPLE / "run.py").is_file(), "the worked example does not exist")
        with tempfile.TemporaryDirectory() as td:
            run = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--out-dir", td], capture_output=True, text=True, timeout=600)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            for step in STEPS:
                fresh = (Path(td) / f"{step}.json").read_bytes()
                committed = (EXAMPLE / "output" / f"{step}.json").read_bytes()
                self.assertEqual(fresh, committed, step)
            summary = json.loads((Path(td) / "summary.json").read_text())
        self.assertEqual(summary["steps"]["01-check-communication"]["status"], "pass")
        self.assertEqual(summary["steps"]["02-audit-claims"]["status"], "pass")
        self.assertEqual(summary["steps"]["03-revision-impact"]["status"], "incomplete")
        self.assertEqual(summary["steps"]["04-responses"]["status"], "fail", "the rerun has not happened; the reply must not claim it")
        self.assertEqual(summary["steps"]["05-unresolved-source"]["status"], "incomplete")

    def test_outputs_are_path_stable_and_labeled_synthetic(self):
        private = [str(Path.home()), tempfile.gettempdir(), str(PLUGIN)]
        for step in STEPS:
            text = (EXAMPLE / "output" / f"{step}.json").read_text(encoding="utf-8")
            for frag in private:
                self.assertNotIn(frag, text, (step, frag))
            self.assertFalse(re.search(r"(?<![\w.>])/(?:Users|home|tmp|private|var|opt|mnt)/", text), (step, "an absolute path leaked"))
        readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
        self.assertIn("synthetic", readme.lower())
        for word in ("claim map", "caption", "changed result", "impact", "response", "unresolved"):
            self.assertIn(word, readme.lower(), word)

    def test_project_record_validates(self):
        from contracts.validate import validate_artifact
        rec = json.loads((EXAMPLE / "project" / "artifacts" / "comm.json").read_text())
        rep = validate_artifact(rec)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertIn("SYNTHETIC", rec["objective"])


if __name__ == "__main__":
    unittest.main()
