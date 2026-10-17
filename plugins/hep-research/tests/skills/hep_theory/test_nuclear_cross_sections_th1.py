"""Th1: the hep-theory reference on nuclear cross-section conventions covers inelastic, charge-changing and isotopic
production cross sections, ISM versus detector-material targets, the straight-ahead approximation, cumulative cross
sections with short-lived intermediates, the validity of parametrization families, uncertainty as model alternatives
plus a normalization nuisance, and the joint declaration of correlations; it cites only sources it opened, with their
read level, and is reachable from the hep-theory routing table and the detector and measurement references."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "skills" / "hep-theory" / "references" / "nuclear-cross-sections.md"
SKILL = ROOT / "skills" / "hep-theory" / "SKILL.md"


class NuclearCrossSections(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_required_topics(self):
        low = self.text.lower()
        for phrase in ("inelastic", "charge-changing", "isotopic production", "interstellar", "detector material",
                       "straight-ahead", "cumulative", "short-lived", "parametrization", "validity",
                       "model alternatives", "normalization nuisance", "correlation"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, low.replace("**", ""))

    def test_interaction_length_and_mixture_rule(self):
        self.assertIn("lambda = A / (N_A sigma)", self.text)
        self.assertIn("1/lambda = sum_i w_i N_A sigma_i / A_i", self.text)

    def test_sources_read_with_read_level(self):
        sec = self.text[self.text.index("## Sources read"):]
        for src in ("arXiv:1803.04686", "arXiv:1711.09616"):
            self.assertIn(src, sec)
        self.assertRegex(sec, r"full text")
        self.assertIn("2026-10-17", sec)

    def test_routed_and_linked(self):
        self.assertIn("references/nuclear-cross-sections.md", SKILL.read_text(encoding="utf-8"))
        corr = (ROOT / "skills" / "hep-measurement" / "references" / "correction-chain.md").read_text(encoding="utf-8")
        self.assertIn("nuclear-cross-sections.md", corr)

    def test_no_numbers_from_memory(self):
        # the reference states conventions; numeric cross sections come from the user's tables
        self.assertIsNone(re.search(r"\b\d+(\.\d+)?\s*mb\b", self.text.split("## Sources read")[0]))


if __name__ == "__main__":
    unittest.main()
