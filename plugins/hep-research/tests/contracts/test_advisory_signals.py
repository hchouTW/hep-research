"""U13 (AGENTIC-R5 T0.8): agent-run checks report no authorization signal (HC-05). formal_use_allowed is always
false, including for '{}' and for artifacts without inputs, and no agent-fillable asset field names an authorization."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.dependencies import validate_dependencies  # noqa: E402


class NoFormalUseSignal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, doc) -> dict:
        p = self.root / "a.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        return validate_dependencies(p, self.root)

    def test_empty_object(self):
        rep = self.report({})
        self.assertIs(rep["formal_use_allowed"], False)
        self.assertTrue(rep["dependency_consistency_ok"])  # consistent, but consistency is not authorization

    def test_artifact_without_inputs_or_with_failed_status(self):
        for doc in ({"artifact_type": "hepdata_record", "inputs": []},
                    {"contract_version": "9.0.0", "status": ["failed"]}):
            with self.subTest(doc=doc):
                self.assertIs(self.report(doc)["formal_use_allowed"], False)

    def test_cli_never_prints_true(self):
        p = self.root / "empty.json"
        p.write_text("{}", encoding="utf-8")
        out = subprocess.run([sys.executable, "-I", str(ROOT / "contracts" / "dependencies.py"), str(p),
                              "--root", str(self.root)], capture_output=True, text=True, timeout=60)
        self.assertIs(json.loads(out.stdout)["formal_use_allowed"], False)


class NoAuthorizationField(unittest.TestCase):
    def test_analysis_contract_has_no_authorization_field(self):
        text = (ROOT / "skills" / "hep-analysis" / "assets" / "analysis-contract.yaml").read_text(encoding="utf-8")
        self.assertNotIn("unblinding_authorization", text)
        self.assertIn("unblinding_record_ref", text)


if __name__ == "__main__":
    unittest.main()
