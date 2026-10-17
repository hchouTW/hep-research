"""particle-physics-essentials.md (Th10): an entry page of at most 8 KB, mostly routing; every link and named tool
exists; it routes the running coupling to running_coupling.py and keeps global fits outside v1."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-theory" / "references" / "particle-physics-essentials.md"


class ParticlePhysicsEssentials(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_size(self):
        self.assertLessEqual(len(self.text.encode()), 8192)

    def test_links_and_tools_exist(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)
        for token in re.findall(r"`<plugin root>/([^` ]+)", self.text):
            self.assertTrue((PLUGIN / token).exists(), token)

    def test_routes_and_scope(self):
        for needle in ("running_coupling.py", "kinematics.py lifetime", "physical_data.py", "outside v1",
                       "Eq. 12.3", "Eq. 9.4", "10LZZZAAAI"):
            self.assertIn(needle, self.text)


if __name__ == "__main__":
    unittest.main()
