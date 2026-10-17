"""light-nuclei-coalescence.md (Th6): every link and named tool exists; both B_A conventions, the spin-isospin factors
and the hand-off to the antiproton profile (by role, no profile ID) are stated; sources are listed."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-theory" / "references" / "light-nuclei-coalescence.md"


class LightNucleiCoalescence(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_links_and_tools_exist(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)
        for token in re.findall(r"`<plugin root>/([^` ]+)", self.text):
            self.assertTrue((PLUGIN / token).exists(), token)

    def test_conventions_stated(self):
        for needle in ("B_A = A (4 pi p0^3 / (3 m_N))^(A-1)", "m_A / m_p^A", "S = 3/8", "S = 1/12",
                       "secondary-antiproton theory-domain profile", "Sources read"):
            self.assertIn(needle, self.text)
        self.assertNotIn("theory:", self.text)


if __name__ == "__main__":
    unittest.main()
