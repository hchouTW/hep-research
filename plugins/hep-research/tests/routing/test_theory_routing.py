"""Static routing checks (Section 12 theory-routing fix): derivation -> hep-theory, inference -> hep-statistics,
explanation -> research-communication. Reads skill text only; nothing is executed."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SKILLS = PLUGIN / "skills"


def text(rel):
    return (SKILLS / rel).read_text(encoding="utf-8")


def description(skill):
    m = re.search(r'^description:\s*"(.*)"\s*$', text(f"{skill}/SKILL.md"), re.M)
    return m.group(1)


class OwnershipTests(unittest.TestCase):
    def test_derivation_reasoning_lives_in_hep_theory(self):
        self.assertTrue((SKILLS / "hep-theory/references/mathematical-reasoning-and-proof.md").is_file())
        self.assertFalse(any((SKILLS / s / "references/mathematical-reasoning-and-proof.md").exists()
                             for s in ("research-communication", "hep-statistics", "hep-analysis")))

    def test_inference_reasoning_lives_in_hep_statistics(self):
        self.assertTrue((SKILLS / "hep-statistics/references/statistical-inference-for-physics.md").is_file())

    def test_descriptions_route_by_kind_of_work(self):
        theory, stats, comm = description("hep-theory"), description("hep-statistics"), description("research-communication")
        self.assertIn("derivations", theory)
        self.assertRegex(theory, r"fitting or limit-setting itself \(hep-statistics\)")
        self.assertRegex(theory, r"manuscript writing \(research-communication\)")
        self.assertRegex(stats, r"deriving predictions \(hep-theory\)")
        self.assertRegex(comm, r"derivations \(hep-theory\)")
        self.assertRegex(comm, r"fits and limits \(hep-statistics\)")


class ReferenceRoutingTests(unittest.TestCase):
    def test_statistical_inference_routes_each_step(self):
        head = text("hep-statistics/references/statistical-inference-for-physics.md")[:1500]
        self.assertNotRegex(head, r"use `hep-analysis` \(pyhf")
        self.assertNotIn("`deep-learning`", head)
        self.assertRegex(head, r"also `hep-statistics` work")
        self.assertRegex(head, r"`hep-theory`\s*\(`\.\./\.\./hep-theory/references/mathematical-reasoning-and-proof\.md`\)")
        self.assertRegex(head, r"writing up the result is\s*`research-communication`")

    def test_no_reference_routes_fits_or_limits_away_from_hep_statistics(self):
        bad = re.compile(r"use `(hep-analysis|deep-learning|hep-theory|research-communication)`[^.]{0,80}"
                         r"(pyhf|Combine|RooStats|limit-setting|run the fit)", re.S)
        hits = [str(p.relative_to(PLUGIN)) for p in SKILLS.glob("*/references/*.md") if bad.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_ml_references_route_statistical_validity_to_hep_statistics(self):
        for rel in ("evaluation-strategy.md", "scientific-machine-learning.md", "deep-learning-guide.md"):
            t = text(f"physics-ml/references/{rel}")
            self.assertNotIn("`academic-papers`", t, rel)
            self.assertIn("`hep-statistics`", t, rel)

    def test_equation_auditing_hands_derivation_validity_to_hep_theory(self):
        t = text("research-communication/references/equation-and-notation-auditing.md")[:1500]
        self.assertIn("../../hep-theory/references/mathematical-reasoning-and-proof.md", t)


if __name__ == "__main__":
    unittest.main()
