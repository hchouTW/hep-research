"""literature-record (contracts 2.13.0, restructuring plan G1): manage_literature.py writes the record inside the
common envelope, so a record written into the project's artifacts_dir passes contracts/validate.py on the directory
(before 2.13.0 the bare record was reported as artifacts_dir.not_artifact); --into still reads a bare record written
before 2.13.0; a hand-edited record that breaks the ledger rules fails validation. All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-literature" / "scripts"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(SCRIPTS))

import manage_literature as cli  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from tests.skills.hep_literature.test_literature_lifecycle import claim, search, source  # noqa: E402


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main([str(a) for a in args])
    return code, out.getvalue(), err.getvalue()


class LiteratureRecordArtifact(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "project"
        (self.root / "hep-research-artifacts").mkdir(parents=True)
        self.inp = self.root / "lit_input.json"
        self.inp.write_text(json.dumps({"sources": [source("lit:S01", "Fixture", doi="10.0000/f", arxiv="2610.00001v2", key="Fix:2026a")],
                                        "claims": [claim("lit:C01", ["lit:S01"])], "search_log": [search()]}), encoding="utf-8")

    def write(self, name="literature.json", *extra):
        out = self.root / "hep-research-artifacts" / name
        code, stdout, err = run_cli("import", self.inp, "--project-root", self.root, "--out", out, "--today", "2026-10-19", *extra)
        self.assertEqual(code, 0, stdout + err)
        return out

    def test_envelope_fields(self):
        doc = json.loads(self.write().read_text(encoding="utf-8"))
        self.assertEqual((doc["artifact_type"], doc["provenance"]["producer_skill"], doc["status"]),
                         ("literature-record", "hep-literature", ["user-supplied"]))
        self.assertEqual(doc["artifact_id"], "literature-record-literature")
        self.assertEqual(doc["extension"]["verification"]["online"], "not-performed")
        self.assertEqual(json.loads(self.write("b.json", "--artifact-id", "lit-1").read_text())["artifact_id"], "lit-1")

    def test_validate_accepts_the_written_artifacts_dir(self):
        self.write()
        p = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(self.root / "hep-research-artifacts")],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("artifacts_dir.not_artifact", p.stdout)

    def test_into_reads_a_bare_record_written_before_2_13(self):
        doc = json.loads(self.write().read_text(encoding="utf-8"))
        legacy = self.root / "legacy.json"
        legacy.write_text(json.dumps(doc["extension"]), encoding="utf-8")
        out = self.write("merged.json", "--into", legacy)
        self.assertEqual(list(json.loads(out.read_text())["extension"]["sources"]), ["lit:S01"])

    def test_broken_record_fails_validation(self):
        doc = json.loads(self.write().read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(doc).ok)
        doc["extension"]["claims"]["lit:C01"]["source_ids"] = ["lit:S99"]
        codes = {f.code for f in validate_artifact(doc).errors}
        self.assertIn("literature.ledger_invalid", codes)


if __name__ == "__main__":
    unittest.main()
