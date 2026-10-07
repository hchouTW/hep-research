"""theory:qed-benchmark derivation tests: SymPy result vs reference forms and stated status."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import derive  # noqa: E402


class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = derive.derive()

    def test_all_symbolic_checks_pass(self):
        self.assertTrue(all(self.rec["checks"].values()), self.rec["checks"])
        self.assertEqual(len(self.rec["checks"]), 8)

    def test_status_is_analytic_derivation_not_proof(self):
        self.assertEqual(self.rec["derivation_status"], "analytic-derivation")
        self.assertIn("Not a formal proof", self.rec["status_note"])

    def test_stored_record_is_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["results"], self.rec["results"])
        self.assertEqual(stored["checks"], self.rec["checks"])

    def test_derivation_record_lists_checks_not_run(self):
        text = (ROOT / "derivations" / "derivation-record.md").read_text(encoding="utf-8")
        self.assertIn("## Checks not run", text)
        self.assertIn("not a formal proof", text.lower())

    def test_reference_claims_exist(self):
        claims = {c["id"] for c in json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))}
        self.assertEqual(claims, {"qedbench:C01", "qedbench:C02"})


if __name__ == "__main__":
    unittest.main()
