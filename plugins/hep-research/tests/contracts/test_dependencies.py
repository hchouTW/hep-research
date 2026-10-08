"""Audit T05: project-level dependency validation (contracts/dependencies.py).

The single-file schema validator never opens a referenced file; this layer resolves every input ref inside a controlled
project root and checks existence, artifact ID and type, contract version, sha256 and the statuses the source really
carries. All artifacts are SYNTHETIC."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402

try:
    from contracts.dependencies import validate_dependencies
except ImportError:  # the regression tests below must fail, not error at import, on the code before the fix
    validate_dependencies = None

PRED = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/prediction.json").read_text())
THEORY = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/theory_spec.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyAuditT05(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        (self.root / "artifacts").mkdir(parents=True)
        self.src = self.root / "artifacts" / "theory_spec.json"
        self.src.write_text(json.dumps(THEORY, indent=1))

    def tearDown(self):
        self.tmp.cleanup()

    def consumer(self, **inp):
        d = copy.deepcopy(PRED)
        entry = {"ref": "artifacts/theory_spec.json", "artifact_type": "theory-spec", "artifact_id": THEORY["artifact_id"],
                 "version": THEORY["contract_version"], "sha256": sha(self.src), "status": list(THEORY["status"])}
        entry.update(inp)
        d["inputs"] = [{k: v for k, v in entry.items() if v is not None}]
        d["status"] = sorted(set(d["status"]) | set(THEORY["status"]))
        path = self.root / "artifacts" / "prediction.json"
        path.write_text(json.dumps(d, indent=1))
        return path

    def check(self, path):
        self.assertIsNotNone(validate_dependencies, "contracts.dependencies does not exist")
        return validate_dependencies(path, self.root)

    def codes(self, rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    def test_repro_dangling_ref_with_bad_hash_is_an_error(self):
        path = self.consumer(ref="does/not/exist.json", sha256="not-a-hash")
        self.assertTrue(validate_artifact(json.loads(path.read_text())).ok, "schema validation stays single-file")
        rep = self.check(path)
        self.assertEqual(rep["status"], "error")
        self.assertIn("dependency.missing", self.codes(rep, "error"))
        self.assertIn("dependency.bad_hash_format", self.codes(rep, "error"))
        self.assertFalse(rep["dependency_consistency_ok"])

    def test_valid_chain(self):
        rep = self.check(self.consumer())
        self.assertEqual(rep["status"], "ok", rep["findings"])
        self.assertTrue(rep["dependency_consistency_ok"])

    def test_missing_file(self):
        self.assertIn("dependency.missing", self.codes(self.check(self.consumer(ref="artifacts/gone.json"))))

    def test_hash_mismatch(self):
        rep = self.check(self.consumer(sha256="0" * 64))
        self.assertIn("dependency.hash_mismatch", self.codes(rep, "error"))

    def test_substituted_source_detected_by_hash(self):
        path = self.consumer()
        other = copy.deepcopy(THEORY)
        other["objective"] = "a different theory spec under the same name"
        self.src.write_text(json.dumps(other))
        self.assertIn("dependency.hash_mismatch", self.codes(self.check(path)))

    def test_type_id_and_version_mismatch(self):
        self.assertIn("dependency.type_mismatch", self.codes(self.check(self.consumer(artifact_type="prediction"))))
        self.assertIn("dependency.id_mismatch", self.codes(self.check(self.consumer(artifact_id="someone-else"))))
        self.assertIn("dependency.version_mismatch", self.codes(self.check(self.consumer(version="2.0.0"))))

    def test_undeclared_failed_upstream(self):
        failed = copy.deepcopy(THEORY)
        failed["status"] = sorted(set(failed["status"]) | {"failed"})
        self.src.write_text(json.dumps(failed))
        rep = self.check(self.consumer(sha256=sha(self.src)))  # the manifest still declares the old statuses
        self.assertIn("dependency.status_undeclared", self.codes(rep, "error"))
        self.assertIn("dependency.status_not_propagated", self.codes(rep, "error"))
        self.assertFalse(rep["dependency_consistency_ok"])

    def test_external_ref_is_unresolved(self):
        rep = self.check(self.consumer(ref="hepdata:ins0000000/t1", external=True, sha256=None))
        self.assertEqual(rep["status"], "unresolved")
        self.assertIn("dependency.external_unresolved", self.codes(rep, "unresolved"))
        self.assertFalse(rep["dependency_consistency_ok"])

    def test_out_of_root_paths_never_read(self):
        outside = Path(self.tmp.name) / "secret.json"
        outside.write_text(json.dumps(THEORY))
        digest, opened, watching = sha(outside), [], []
        sys.addaudithook(lambda ev, args: opened.append(str(args[0])) if watching and ev == "open" and isinstance(args[0], (str, Path)) else None)
        (self.root / "artifacts" / "link.json").symlink_to(outside)
        for ref in ("../secret.json", str(outside), "artifacts/../../secret.json", "artifacts/link.json"):
            path = self.consumer(ref=ref, sha256=digest)
            watching.append(1)
            rep = self.check(path)
            watching.clear()
            self.assertIn("dependency.outside_root", self.codes(rep, "error"), ref)
        self.assertNotIn(str(outside), opened)
        self.assertTrue(opened, "the audit hook saw the consumer being read")

    def test_artifact_outside_root_rejected(self):
        outside = Path(self.tmp.name) / "consumer.json"
        outside.write_text(json.dumps(PRED))
        self.assertIn("dependency.outside_root", self.codes(validate_dependencies(outside, self.root)))

    def test_cli_exit_codes(self):
        self.assertIsNotNone(validate_dependencies)
        run = lambda p: subprocess.run([sys.executable, str(PLUGIN / "contracts" / "dependencies.py"), str(p), "--root", str(self.root)],
                                       capture_output=True, text=True, timeout=600)
        self.assertEqual(run(self.consumer()).returncode, 0)
        self.assertEqual(run(self.consumer(sha256="0" * 64)).returncode, 1)
        self.assertEqual(run(self.consumer(ref="hepdata:x", external=True, sha256=None)).returncode, 3)


if __name__ == "__main__":
    unittest.main()
