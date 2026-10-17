"""dark-matter-phenomenology.md (Th5): every link and named tool exists; the self-conjugacy factor, the J-factor
definition and its uniform-sphere limit, the Helm parameters and the relic estimate are stated with their sources;
the out-of-v1 boundary (interpreting an excess, Boltzmann solvers) is explicit; no experiment is named."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-theory" / "references" / "dark-matter-phenomenology.md"


class DarkMatterPhenomenology(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_links_and_tools_exist(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)
        for token in re.findall(r"`<plugin root>/([^` ]+)", self.text):
            self.assertTrue((PLUGIN / token).exists(), token)

    def test_conventions_stated(self):
        for needle in ("c = 1/2 for a self-conjugate", "c = 1/4", "4 pi r^3 rho^2 / (3 d^2)", "c = 1.23 A^(1/3) - 0.60 fm",
                       "sigma_N = sigma_n A^2 (mu_N / mu_n)^2", "x_fo between 10 and 50", "Outside v1",
                       "to-verify", "Sources read"):
            self.assertIn(needle, self.text)


if __name__ == "__main__":
    unittest.main()
