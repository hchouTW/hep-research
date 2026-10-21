"""tools/check_ownership.py: passes on the plugin and fails on each seeded contradiction."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_ownership", PLUGIN / "tools" / "check_ownership.py")
co = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(co)


class OwnershipCheckTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        for rel in ("README.md", "docs/routing-contract.md", "docs/capability-matrix.md",
                    *(str(p.relative_to(PLUGIN)) for p in PLUGIN.glob("skills/*/SKILL.md"))):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(PLUGIN / rel, self.root / rel)

    def tearDown(self):
        self.td.cleanup()

    def mutate(self, rel, old, new):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text, f"mutation anchor missing in {rel}")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_plugin_passes(self):
        self.assertEqual(co.check(PLUGIN), [])
        self.assertEqual(co.check(self.root), [])
        self.assertGreaterEqual(len(co.ownership_table(PLUGIN)), 5)

    def test_owns_line_claim_by_another_skill_fails(self):
        # the r1 contradiction: hep-statistics owned the forward-folding algorithms
        self.mutate("skills/hep-statistics/SKILL.md", "unfolding algorithms and regularization,",
                    "unfolding and forward-folding algorithms,")
        problems = co.check(self.root)
        self.assertTrue(any("hep-statistics claims ['forward folding'] in its owns" in p for p in problems), problems)

    def test_description_claim_fails(self):
        self.mutate("skills/hep-statistics/SKILL.md", "unfolding with regularization and coverage",
                    "unfolding and forward folding with regularization and coverage")
        self.assertTrue(any("in its use_when" in p for p in co.check(self.root)))

    def test_not_for_clause_is_not_a_claim(self):
        self.mutate("skills/hep-measurement/SKILL.md", "Not for: detector performance", "Not for: forward folding, detector performance")
        self.assertEqual(co.check(self.root), [])

    def test_readme_row_claim_fails(self):
        self.mutate("README.md", "response matrices and forward folding, simulation", "unfolding, simulation")
        problems = co.check(self.root)
        self.assertTrue(any("hep-detector claims ['unfolding'] in its readme" in p for p in problems), problems)

    def test_capability_matrix_owner_mismatch_fails(self):
        self.mutate("docs/capability-matrix.md", "| Unfolding | hep-statistics |", "| Unfolding | hep-detector |")
        self.assertTrue(any("capability-matrix row 'Unfolding'" in p for p in co.check(self.root)))

    def test_owner_that_does_not_claim_fails(self):
        self.mutate("skills/hep-detector/SKILL.md", "forward folding of predictions, ", "")
        self.assertTrue(any("does not claim it" in p for p in co.check(self.root)))

    def test_missing_table_fails(self):
        self.mutate("docs/routing-contract.md", "<!-- ownership-table", "<!-- table")
        self.assertTrue(co.check(self.root))

    def test_terms_match_on_word_boundaries_with_hyphens_as_spaces(self):
        self.assertTrue(co.claims("Owns: double-counting checks", "double counting checks"))
        self.assertTrue(co.claims("forward-folding algorithms", "forward folding"))
        self.assertFalse(co.claims("unfolding", "folding"))

    def test_plural_of_a_term_is_a_claim(self):
        # T07: a non-letter was required right after the term, so 'BDTs' did not claim 'BDT'
        self.assertTrue(co.claims("trains BDTs.", "BDT"))
        self.assertTrue(co.claims("Owns: fit diagnostics and template fits", "template fit"))
        self.assertTrue(co.claims("several boxes", "box"))
        self.assertFalse(co.claims("BDTstyle", "BDT"))
        self.mutate("skills/hep-statistics/SKILL.md", "unfolding algorithms and regularization,",
                    "unfolding algorithms and regularization, BDTs,")
        problems = co.check(self.root)
        self.assertTrue(any("owned by hep-ml but hep-statistics claims ['BDT'] in its owns" in p for p in problems),
                        problems)


if __name__ == "__main__":
    unittest.main()
