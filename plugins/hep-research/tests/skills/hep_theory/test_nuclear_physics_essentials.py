"""nuclear-physics-essentials.md (Th12): an entry page of at most 8 KB; every link and named tool exists; the electron
bookkeeping of beta+ (2 m_e), the NUBASE year and the S-factor convention are stated; structure calculations stay
outside v1."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-theory" / "references" / "nuclear-physics-essentials.md"


class NuclearPhysicsEssentials(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_size(self):
        self.assertLessEqual(len(self.text.encode()), 8192)

    def test_links_and_tools_exist(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)
        for token in re.findall(r"`<plugin root>/([^` ]+)", self.text):
            self.assertTrue((PLUGIN / token).exists(), token)

    def test_conventions_stated(self):
        for needle in ("- 2 m_e", "365.2422 d", "sigma(E) = S(E) e^{-2 pi eta} / E", "outside v1", "decay_chain.py",
                       "secular", "transient"):
            self.assertIn(needle, self.text)


if __name__ == "__main__":
    unittest.main()
