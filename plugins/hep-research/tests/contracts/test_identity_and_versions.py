"""AGENTIC-R5 T0.3 and T0.4 (contracts 2.1.0, Q-04): release identity in artifacts, the version and capability policy
of the validator, and validation of every dependency source."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION, KNOWN_CAPABILITIES  # noqa: E402
from contracts import identity  # noqa: E402
from contracts.dependencies import validate_dependencies  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.partition import campaign, states  # noqa: E402

THEORY = json.loads((ROOT / "contracts/fixtures/artifacts/valid/theory_spec.json").read_text())


def at(version: str, doc: dict = THEORY) -> dict:
    d = copy.deepcopy(doc)
    d["contract_version"] = version
    d["versions"]["contracts"] = version
    return d


def codes(rep, severity=None):
    return {f.code for f in rep.findings if severity is None or f.severity == severity}


class ReleaseIdentityT03(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "plugin"
        (self.root / ".claude-plugin").mkdir(parents=True)
        (self.root / ".claude-plugin" / "plugin.json").write_text('{"version": "9.9.9"}')
        (self.root / "core.py").write_text("x = 1\n")
        identity._plugin_release.cache_clear()

    def tearDown(self):
        identity._plugin_release.cache_clear()
        self.tmp.cleanup()

    def record(self):
        (self.root / "release-manifests").mkdir()
        man = identity.generate(self.root)
        (self.root / "release-manifests" / "9.9.9.json").write_text(json.dumps(man))
        return man

    def test_verified_release_records_its_full_digest(self):
        man = self.record()  # the recorded manifest is not part of the bundle it describes
        self.assertEqual(identity.plugin_release(self.root), {"release": "9.9.9", "digest": man["digest"]})
        self.assertEqual(len(man["digest"]), 64)

    def test_changed_or_unrecorded_tree_is_unreleased(self):
        self.assertEqual(identity.plugin_release(self.root), identity.UNKNOWN)
        self.record()
        (self.root / "core.py").write_text("x = 2\n")
        identity._plugin_release.cache_clear()
        self.assertEqual(identity.plugin_release(self.root), identity.UNKNOWN)

    def test_schema_accepts_identity_and_legacy_absence(self):
        doc = at(CONTRACTS_VERSION)
        self.assertTrue(validate_artifact(doc).ok)  # legacy: no plugin_release, identity unknown
        doc["versions"]["plugin_release"] = {"release": "0.5.0", "digest": "a" * 64}
        self.assertTrue(validate_artifact(doc).ok)
        for bad in ({"release": "0.5.0", "digest": "a" * 12}, {"release": "latest", "digest": "unknown"}, {"digest": "unknown"}):
            doc["versions"]["plugin_release"] = bad
            self.assertFalse(validate_artifact(doc).ok, bad)

    def test_truncated_digests_are_full(self):
        self.assertEqual(len(campaign.resources_hash({"resources": {"cpus": 1}})), 64)
        full = campaign.resources_hash({"resources": {"cpus": 1}})
        self.assertTrue(states.same_resources(full[:16], full))  # a campaign recorded by an older version
        self.assertFalse(states.same_resources(full[:15], full))
        self.assertFalse(states.same_resources(full, campaign.resources_hash({"resources": {"cpus": 2}})))


class VersionPolicyT04(unittest.TestCase):
    def test_newer_minor_warns_and_fails_for_protected_use(self):
        doc = at("2.9.0")
        self.assertIn("contract.newer_minor", codes(validate_artifact(doc), "warning"))
        self.assertTrue(validate_artifact(doc).ok)
        self.assertIn("contract.newer_minor", codes(validate_artifact(doc, protected=True), "error"))

    def test_version_stamps_agree(self):
        vocab = json.loads((ROOT / "contracts/vocab/core.json").read_text())
        self.assertEqual(vocab["contracts_version"], CONTRACTS_VERSION)

    def test_newer_major_is_an_error(self):
        self.assertIn("contract.unsupported_major", codes(validate_artifact(at("9.0.0")), "error"))

    def test_versions_contracts_must_match(self):
        doc = at(CONTRACTS_VERSION)
        doc["versions"]["contracts"] = "2.0.0"
        self.assertIn("contract.version_mismatch", codes(validate_artifact(doc), "error"))
        old = at("1.0.0")
        old["versions"]["contracts"] = "2.0.0"
        self.assertIn("contract.version_mismatch", codes(validate_artifact(old), "warning"))

    def test_required_capabilities(self):
        doc = at(CONTRACTS_VERSION)
        doc["required_capabilities"] = sorted(KNOWN_CAPABILITIES)
        self.assertTrue(validate_artifact(doc).ok)
        doc["required_capabilities"] = ["core:revocation-v9"]
        self.assertIn("contract.unknown_capability", codes(validate_artifact(doc), "error"))

    def test_unknown_top_level_key_is_a_warning(self):
        doc = at(CONTRACTS_VERSION)
        doc["approved_by_maintainer"] = True
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok)
        self.assertIn("envelope.unknown_key", codes(rep, "warning"))

    def test_input_version_pattern(self):
        doc = at(CONTRACTS_VERSION)
        doc["inputs"] = [{"ref": "x.json", "version": "latest"}]
        self.assertFalse(validate_artifact(doc).ok)

    def test_data_exposure_is_structured(self):
        doc = at(CONTRACTS_VERSION)
        doc["data_exposure"] = {"state": "unknown", "basis": "legacy-text"}
        self.assertTrue(validate_artifact(doc).ok)
        doc["data_exposure"] = {"state": "probably-not", "basis": "none"}
        self.assertFalse(validate_artifact(doc).ok)


class DependencySourcesT04(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def chain(self, source: dict, **kw) -> dict:
        src = self.root / "src.json"
        src.write_text(json.dumps(source))
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        consumer = at(CONTRACTS_VERSION)
        consumer["inputs"] = [{"ref": "src.json", "sha256": sha, "status": source.get("status", [])}]
        consumer["status"] = sorted(set(consumer["status"]) | set(source.get("status", [])))
        dst = self.root / "consumer.json"
        dst.write_text(json.dumps(consumer))
        return validate_dependencies(dst, self.root, **kw)

    def test_valid_source(self):
        rep = self.chain(at(CONTRACTS_VERSION))
        self.assertEqual(rep["status"], "ok", rep["findings"])

    def test_invalid_or_unsupported_sources_are_errors(self):
        broken = at(CONTRACTS_VERSION)
        del broken["objective"]
        unknown_type = at(CONTRACTS_VERSION)
        unknown_type["artifact_type"] = "oracle-verdict"
        for name, src in (("schema-invalid", broken), ("unknown type", unknown_type), ("newer major", at("9.0.0"))):
            with self.subTest(name):
                rep = self.chain(src)
                self.assertIn("dependency.source_invalid", {f["code"] for f in rep["findings"]})
                self.assertEqual(rep["status"], "error")

    def test_newer_minor_source(self):
        rep = self.chain(at("2.9.0"))
        self.assertIn("dependency.source_newer_minor", {f["code"] for f in rep["findings"]})
        self.assertEqual(rep["status"], "ok")
        self.assertEqual(self.chain(at("2.9.0"), protected=True)["status"], "error")


if __name__ == "__main__":
    unittest.main()
