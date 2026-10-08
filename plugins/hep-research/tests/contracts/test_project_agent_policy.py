"""AGENTIC-R5 T1.3 (K05): agent_policy in the project config (schema 1.1.0), the schema_version check, the closed
blinding block, and blinding loads that fail closed. All results are advisory."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.project import load_blinding, load_project  # noqa: E402
from core.blinding.blinding import load_project_blinding  # noqa: E402

BASE = {"schema_version": "1.1.0", "plugin_version": ">=0.1",
        "blinding": {"blinded": ["m_sr"], "allowed_outputs": [], "regions": [{"variable": "m", "low": 120, "high": 130}]},
        "agent_policy": {"policy_version": "1.0.0", "model_context_allowed": ["public", "synthetic"],
                         "protected_paths": ["private/", "data/unblinded/"], "unblinding": "outside-agent-session"}}


class AgentPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, cfg):
        (self.d / "hep-research.project.json").write_text(json.dumps(cfg))
        return load_project(self.d)

    def codes(self, cfg):
        return {f.code for f in self.load(cfg).report.errors}

    def edited(self, fn):
        cfg = copy.deepcopy(BASE)
        fn(cfg)
        return cfg

    def test_valid_policy(self):
        self.assertTrue(self.load(BASE).report.ok, self.load(BASE).report.as_dict())

    def test_schema_version_is_checked(self):
        self.assertIn("project.policy_needs_schema", self.codes(self.edited(lambda c: c.update(schema_version="1.0.0"))))
        for v in ("1.2.0", "2.0.0"):
            self.assertIn("project.unsupported_schema", self.codes(self.edited(lambda c: c.update(schema_version=v))))

    def test_old_reader_contract_is_unchanged_without_policy(self):
        cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.1", "blinding": {"blinded": [], "extra": 1}}
        self.assertTrue(self.load(cfg).report.ok)  # 1.0.0 blinding blocks stay open

    def test_blinding_block_closed_and_required(self):
        self.assertIn("project.blinding_unknown_key", self.codes(self.edited(lambda c: c["blinding"].update(masks=[]))))
        self.assertIn("project.blinding_missing", self.codes(self.edited(lambda c: c.pop("blinding"))))
        self.assertIn("project.bad_region", self.codes(self.edited(lambda c: c["blinding"]["regions"][0].update(low=140))))

    def test_policy_paths(self):
        for bad in ("../outside", "/abs/path", "~/x"):
            with self.subTest(path=bad):
                self.assertIn("project.policy_bad_path",
                              self.codes(self.edited(lambda c: c["agent_policy"].update(protected_paths=[bad]))))

    def test_release_manifest_digests(self):
        (self.d / "manifests").mkdir()
        (self.d / "manifests" / "blinded-v1.json").write_text("{}")
        good = hashlib.sha256(b"{}").hexdigest()
        ok = self.edited(lambda c: c["agent_policy"].update(release_manifests=[{"ref": "manifests/blinded-v1.json", "sha256": good}]))
        self.assertTrue(self.load(ok).report.ok)
        self.assertIn("project.policy_manifest_mismatch", self.codes(self.edited(
            lambda c: c["agent_policy"].update(release_manifests=[{"ref": "manifests/blinded-v1.json", "sha256": "0" * 64}]))))
        self.assertIn("project.policy_manifest_missing", self.codes(self.edited(
            lambda c: c["agent_policy"].update(release_manifests=[{"ref": "manifests/gone.json", "sha256": good}]))))

    def test_unknown_policy_field_and_unblinding_value(self):
        self.assertTrue(self.codes(self.edited(lambda c: c["agent_policy"].update(approved=True))))
        self.assertTrue(self.codes(self.edited(lambda c: c["agent_policy"].update(unblinding="agent-may-unblind"))))

    def test_blinding_loads_fail_closed(self):
        (self.d / "hep-research.project.json").write_text(json.dumps(BASE))
        self.assertEqual(load_blinding(self.d)["blinded"], ["m_sr"])
        no_block = self.edited(lambda c: c.pop("blinding"))
        (self.d / "hep-research.project.json").write_text(json.dumps(no_block))
        with self.assertRaises(ValueError):
            load_blinding(self.d)
        with self.assertRaises(ValueError):
            load_project_blinding(self.d / "hep-research.project.json")

    def test_cli_says_advisory(self):
        (self.d / "hep-research.project.json").write_text(json.dumps(BASE))
        p = subprocess.run([sys.executable, str(ROOT / "contracts" / "project.py"), str(self.d)], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("advisory", json.loads(p.stdout)["note"])


if __name__ == "__main__":
    unittest.main()
