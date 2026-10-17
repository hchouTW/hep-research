"""astroparticle-essentials.md (Th11): an entry page of at most 8 KB; every link and named tool exists; the DSA index,
the Hillas criterion, the averaged flavour-ratio rule and the threshold formula are stated with their sources."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-theory" / "references" / "astroparticle-essentials.md"


class AstroparticleEssentials(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_size(self):
        self.assertLessEqual(len(self.text.encode()), 8192)

    def test_links_and_tools_exist(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)
        for token in re.findall(r"`<plugin root>/([^` ]+)", self.text):
            self.assertTrue((PLUGIN / token).exists(), token)
        for script in set(re.findall(r"`([a-z_]+\.py)", self.text)):
            self.assertTrue((REF.parents[1] / "scripts" / script).is_file(), script)

    def test_relations_stated(self):
        for needle in ("alpha = 3r / (r - 1)", "E_max ~ Z e c B R", "P(alpha -> beta) = sum_i |U_alpha i|^2 |U_beta i|^2",
                       "E = (K^2 + m^2)/(2K)", "E_gamma + m_pi^2/(4 E_gamma)", "gamma tau", "Sources read"):
            self.assertIn(needle, self.text)


if __name__ == "__main__":
    unittest.main()
