"""contracts/validate.py on a directory: every JSON file under an artifacts_dir must be a valid artifact, so raw tool
outputs left there are found (registry rule CTX-ARTIFACTS-VALID, evals/behavior/invariants.json)."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.validate import main as validate_main  # noqa: E402

FIXTURES = ROOT / "contracts" / "fixtures" / "artifacts"


def run(*args) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = validate_main([str(a) for a in args])
    return rc, json.loads(buf.getvalue())


def codes(out: dict) -> list[str]:
    return [f["code"] for f in out["findings"]]


class ValidateDirectory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "sub").mkdir()
        shutil.copy(FIXTURES / "valid" / "computational_run.json", self.d / "run.json")
        shutil.copy(FIXTURES / "valid" / "dataset_record.json", self.d / "sub" / "record.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_artifacts_pass(self):
        rc, out = run(self.d)
        self.assertEqual(rc, 0, out)
        self.assertEqual([e["path"] for e in out["files"]], ["run.json", "sub/record.json"])

    def test_raw_tool_output_is_an_error(self):
        (self.d / "unfold_it4.json").write_text(json.dumps({"status": "ok", "unfolded": [1, 2]}))
        rc, out = run(self.d)
        self.assertEqual(rc, 1)
        self.assertIn("artifacts_dir.not_artifact", codes(out))

    def test_invalid_artifact_fails(self):
        shutil.copy(FIXTURES / "invalid" / "communication_bad_types.json", self.d / "comm.json")
        rc, out = run(self.d)
        self.assertEqual(rc, 1)
        self.assertFalse(next(e for e in out["files"] if e["path"] == "comm.json")["ok"])

    def test_upper_case_json_suffix_is_validated(self):
        """Triage T09: bad.JSON was only a non_json warning, so an invalid artifact passed the directory check."""
        shutil.copy(FIXTURES / "invalid" / "communication_bad_types.json", self.d / "comm.JSON")
        (self.d / "notes.Json").write_text(json.dumps({"status": "ok"}))
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertFalse(next(e for e in out["files"] if e["path"] == "comm.JSON")["ok"])
        self.assertEqual(codes(out), ["artifacts_dir.not_artifact"])
        shutil.copy(FIXTURES / "valid" / "computational_run.json", self.d / "comm.JSON")
        (self.d / "notes.Json").unlink()
        rc, out = run(self.d)
        self.assertEqual(rc, 0, out)
        self.assertEqual([e["path"] for e in out["files"]], ["comm.JSON", "run.json", "sub/record.json"])

    def test_unreadable_json_is_an_error(self):
        (self.d / "broken.json").write_text("{")
        rc, out = run(self.d)
        self.assertEqual(rc, 1)
        self.assertIn("artifacts_dir.unreadable", codes(out))

    def test_sidecar_and_hidden_files(self):
        (self.d / "model.onnx").write_bytes(b"\0")
        (self.d / ".DS_Store").write_bytes(b"\0")
        rc, out = run(self.d)
        self.assertEqual(rc, 0, out)
        self.assertEqual(codes(out), ["artifacts_dir.non_json"])

    def test_empty_directory_warns(self):
        with tempfile.TemporaryDirectory() as empty:
            rc, out = run(empty)
        self.assertEqual(rc, 0)
        self.assertEqual(codes(out), ["artifacts_dir.empty"])

    def _refer(self, ref: str):
        run = json.loads((self.d / "run.json").read_text())
        run["outputs"] = [{"ref": ref}]
        (self.d / "run.json").write_text(json.dumps(run))

    def test_referenced_sidecar_passes(self):
        (self.d / "bdt_run").mkdir()
        (self.d / "bdt_run" / "split_report.json").write_text(json.dumps({"status": "ok", "overlap": 0}))
        for ref in ("bdt_run/split_report.json", f"{self.d.name}/bdt_run/split_report.json",
                    str(self.d / "bdt_run" / "split_report.json")):
            with self.subTest(ref=ref):
                self._refer(ref)
                rc, out = run(self.d)
                self.assertEqual(rc, 0, out)
                self.assertEqual(out["sidecars"], ["bdt_run/split_report.json"])

    def test_unreferenced_sidecar_still_fails(self):
        (self.d / "split_report.json").write_text(json.dumps({"status": "ok"}))
        self._refer("other_report.json")
        rc, out = run(self.d)
        self.assertEqual(rc, 1)
        self.assertIn("artifacts_dir.not_artifact", codes(out))

    def test_referenced_non_json_file_has_no_warning(self):
        (self.d / "model.onnx").write_bytes(b"\0")
        self._refer("model.onnx")
        rc, out = run(self.d)
        self.assertEqual((rc, codes(out), out["sidecars"]), (0, [], ["model.onnx"]))

    def test_gate_refuses_a_directory(self):
        rc, out = run(self.d, "--gate", "publication")
        self.assertEqual(rc, 2)
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
