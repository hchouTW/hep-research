"""Evidence ledger of scientific corrections (docs/evidence/sci-fixes.json): every entry uses the two-axis vocabulary,
names existing evidence tests, and states its gaps whenever it is below the requirement for its severity. The ledger
records evidence; it never authorizes anything, and a fix below its requirement is reported, not refused."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LEDGER = ROOT / "docs" / "evidence" / "sci-fixes.json"
C = ("C0", "C1", "C2", "C3", "C4")
D = ("D0", "D1", "D2", "D3")
REQUIRED = {"S1": ("C3", "D2"), "S2": ("C2", "D2"), "S4": ("C1", "D2")}
ORACLES = {"exhaustive", "symbolic", "analytic", "published", "independent-implementation", "invariant", "closure",
           "pinned-value", "behavioral"}
INDEPENDENT = {"exhaustive", "symbolic", "analytic", "published", "independent-implementation"}
BASES = {"locator", "third-party", "exhaustive", "person"}  # docs/maintenance.md, oracle independence


def below(entry) -> bool:
    need_c, need_d = REQUIRED[entry["severity"]]
    return C.index(entry["correctness"]) < C.index(need_c) or D.index(entry["discrimination"]) < D.index(need_d)


class SciFixLedger(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_vocabulary_tests_and_unique_ids(self):
        ids = [f["id"] for f in self.doc["fixes"]] + [f["id"] for f in self.doc["documentation_fixes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                self.assertIn(f["severity"], REQUIRED)
                self.assertIn(f["correctness"], C)
                self.assertIn(f["discrimination"], D)
                self.assertTrue(f["evidence_tests"])
                for t in f["evidence_tests"]:
                    self.assertTrue((ROOT / t).is_file(), t)
                self.assertTrue(set(f["oracle_kinds"]) <= ORACLES, f["oracle_kinds"])
                self.assertIsInstance(f["negative_control_emulates_pre_fix"], bool)

    def test_grades_are_consistent_with_the_oracles(self):
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                kinds = set(f["oracle_kinds"]) & INDEPENDENT
                if f["correctness"] in ("C2", "C3"):
                    self.assertTrue(kinds, "C2 or above needs an independent oracle kind")
                if f["correctness"] == "C3":
                    self.assertGreaterEqual(len(kinds), 2)
                    self.assertIn("invariant", f["oracle_kinds"])
                    self.assertTrue(f["negative_control_emulates_pre_fix"])
                if f["correctness"] == "C4":
                    self.assertTrue({"exhaustive", "symbolic"} & set(f["oracle_kinds"]))

    def test_every_counted_kind_has_a_qualifying_basis(self):
        """The maintainer's rule (docs/maintenance.md, oracle independence): an independent kind counts only with a
        record naming its test and a basis, locator, third-party, exhaustive or person; C2 needs one such kind, C3
        two distinct ones, C4 an exhaustive or symbolic one."""
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                records = f.get("independence", [])
                for rec in records:
                    self.assertIn(rec["kind"], INDEPENDENT, rec)
                    self.assertIn(rec["basis"], BASES, rec)
                    self.assertTrue(rec["detail"], rec)
                    self.assertTrue((ROOT / rec["test"].split("::")[0]).is_file(), rec["test"])
                qualified = {rec["kind"] for rec in records}
                self.assertEqual(set(f["oracle_kinds"]) & INDEPENDENT, qualified,
                                 "an independent kind is listed exactly when a record qualifies it")
                need = {"C1": 0, "C2": 1, "C3": 2, "C4": 1}[f["correctness"]] if f["correctness"] != "C0" else 0
                self.assertGreaterEqual(len(qualified), need, (f["correctness"], qualified))
                if f["correctness"] == "C4":
                    self.assertTrue({"exhaustive", "symbolic"} & qualified, qualified)

    def test_entries_below_their_requirement_state_their_gaps(self):
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                if below(f):
                    self.assertTrue(f["gaps"], "an entry below its requirement must list what is missing")


if __name__ == "__main__":
    unittest.main()
