"""R5 proposals: contract-major gate, revocation events, run-record hash verification (synthetic inputs only)."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from contracts import CONTRACTS_VERSION
from contracts.dependencies import validate_dependencies
from contracts.validate import validate_artifact
from contracts.verify_run import verify_run


def run_doc(**over) -> dict:
    doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": "fixture-synthetic-r5", "artifact_type": "computational-run",
           "objective": "SYNTHETIC test record", "bindings": {"experiments": [], "theory": []},
           "versions": {"plugin": "0.3.0", "contracts": CONTRACTS_VERSION, "profiles": {}},
           "provenance": {"producer_skill": "hep-computing", "created": "2026-10-07", "evidence_ids": []},
           "inputs": [], "outputs": [], "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
           "extension": {"input_manifest": [], "tools": [{"name": "python", "version": "3"}], "commands": ["x"],
                         "environment": {}, "seeds": {}, "tolerances": {}, "exit_status": 0, "output_hashes": {}}}
    doc.update(over)
    return doc


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class ContractMajorTests(unittest.TestCase):
    def test_future_major_is_refused(self):
        rep = validate_artifact(run_doc(contract_version="9.0.0"))
        self.assertFalse(rep.ok)
        self.assertIn("contract.unsupported_major", {f.code for f in rep.findings})

    def test_current_and_older_versions_keep_their_outcome(self):
        for v in (CONTRACTS_VERSION, "1.0.0", "1.1.0"):
            self.assertTrue(validate_artifact(run_doc(contract_version=v)).ok, v)


class RevocationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.up = self.root / "up.json"
        self.up.write_text(json.dumps(run_doc(artifact_id="up")), encoding="utf-8")
        down = run_doc(artifact_id="down", inputs=[{"ref": "up.json", "sha256": sha(self.up), "status": ["synthetic", "unvalidated"]}])
        self.down = self.root / "down.json"
        self.down.write_text(json.dumps(down), encoding="utf-8")
        self.rev = self.root / "revocations.jsonl"

    def test_no_revocation_file_keeps_old_behaviour(self):
        rep = validate_dependencies(self.down, self.root)
        self.assertTrue(rep["formal_use_allowed"])
        self.assertEqual(rep["dependency_consistency_ok"], rep["formal_use_allowed"])
        self.assertFalse(rep["revocations_checked"])

    def test_revoked_upstream_blocks_without_changing_its_bytes(self):
        before = sha(self.up)
        self.rev.write_text(json.dumps({"subject_sha256": before, "reason": "operator bug found", "issued": "2026-10-07",
                                        "issuer": "maintainer"}) + "\n", encoding="utf-8")
        rep = validate_dependencies(self.down, self.root, revocations=self.rev)
        codes = {f["code"] for f in rep["findings"]}
        self.assertIn("dependency.revoked", codes)
        self.assertNotIn("dependency.hash_mismatch", codes)  # history intact: the cited bytes still verify
        self.assertFalse(rep["formal_use_allowed"])
        self.assertEqual(rep["dependency_consistency_ok"], rep["formal_use_allowed"])
        self.assertTrue(rep["revocations_checked"])
        self.assertEqual(sha(self.up), before)

    def test_revoked_artifact_itself(self):
        self.rev.write_text(json.dumps({"subject_sha256": sha(self.down), "reason": "superseded"}) + "\n", encoding="utf-8")
        rep = validate_dependencies(self.down, self.root, revocations=self.rev)
        self.assertIn("dependency.revoked", {f["code"] for f in rep["findings"]})

    def test_malformed_revocation_file_fails_closed(self):
        self.rev.write_text("not json\n" + json.dumps({"subject_sha256": "abc", "reason": ""}) + "\n", encoding="utf-8")
        rep = validate_dependencies(self.down, self.root, revocations=self.rev)
        self.assertEqual(rep["status"], "error")
        self.assertIn("dependency.revocations_unreadable", {f["code"] for f in rep["findings"]})

    def test_missing_revocation_file_fails_closed(self):
        rep = validate_dependencies(self.down, self.root, revocations=self.root / "absent.jsonl")
        self.assertFalse(rep["formal_use_allowed"])


class VerifyRunTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "in.json").write_text("{}", encoding="utf-8")
        (self.base / "out.json").write_text("[1]", encoding="utf-8")

    def doc(self, inp, outs):
        d = run_doc()
        d["extension"]["input_manifest"] = inp
        d["extension"]["output_hashes"] = outs
        return d

    def test_placeholder_is_unresolved(self):
        rep = verify_run(self.doc([{"path": "in.json", "sha256": "placeholder"}], {}), self.base)
        self.assertEqual(rep["status"], "unresolved")

    def test_matching_hashes_ok(self):
        d = self.doc([{"path": "in.json", "sha256": sha(self.base / "in.json")}], {"out.json": sha(self.base / "out.json")})
        self.assertEqual(verify_run(d, self.base)["status"], "ok")

    def test_changed_output_is_error(self):
        d = self.doc([{"path": "in.json", "sha256": sha(self.base / "in.json")}], {"out.json": sha(self.base / "out.json")})
        (self.base / "out.json").write_text("[2]", encoding="utf-8")
        rep = verify_run(d, self.base)
        self.assertEqual(rep["status"], "error")
        self.assertIn("mismatch", {e["result"] for e in rep["entries"]})

    def test_path_escape_is_not_read(self):
        d = self.doc([{"path": "../../etc/hostname", "sha256": "0" * 64}], {})
        rep = verify_run(d, self.base)
        self.assertEqual(rep["entries"][0]["result"], "outside-base")
        self.assertEqual(rep["status"], "error")


if __name__ == "__main__":
    unittest.main()
