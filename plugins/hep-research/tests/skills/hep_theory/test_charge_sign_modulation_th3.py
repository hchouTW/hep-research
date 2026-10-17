"""Th3: the force-field part of the propagation reference states the limits of drift (charge-sign) effects, segments
time-resolved data by polarity era, fits one phi per period, names the heliospheric-modulation profile by its role
(never its ID), and cites the cycle-25 polar-field reversal only from the public paper arXiv:2606.15259 with its own
hedging (the reversals "likely occurred" in 2024)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "skills" / "hep-theory" / "references" / "cosmic-ray-propagation.md"


def force_field_section() -> str:
    text = REF.read_text()
    start = text.index("## Force-field solar modulation")
    end = text.index("\n## ", start + 3)
    return text[start:end]


class ChargeSignModulation(unittest.TestCase):
    def setUp(self):
        self.sec = force_field_section()

    def test_polarity_era_segmentation_and_one_phi_per_period(self):
        self.assertIn("### Charge-sign-dependent modulation", self.sec)
        for phrase in ("polarity era", "one phi per period", "drift", "reversal"):
            self.assertIn(phrase, self.sec.lower() if phrase != "one phi per period" else self.sec)

    def test_cycle_25_reversal_cited_from_the_paper_with_hedging(self):
        self.assertIn("arXiv:2606.15259", self.sec)
        cite = self.sec[self.sec.index("arXiv:2606.15259") - 600: self.sec.index("arXiv:2606.15259") + 600]
        self.assertRegex(cite, r"likely")
        self.assertIn("2026-10-17", REF.read_text()[REF.read_text().index("## Sources read"):])

    def test_profile_named_by_role_not_id(self):
        self.assertIn("heliospheric-modulation profile", self.sec)
        self.assertIsNone(re.search(r"theory:heliospheric", REF.read_text()))


if __name__ == "__main__":
    unittest.main()
