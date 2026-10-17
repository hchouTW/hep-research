"""ML1: a detector configuration change (an era) in machine-learning studies is documented where the robustness and
the astroparticle references are read: the training options (per-era training, era conditioning, common features
only, missing-feature indicators), per-era calibration and working points, efficiencies measured in data, and the
link to the executable BDT path. Standard library only."""
import re
import unittest
from pathlib import Path

REFS = Path(__file__).resolve().parents[3] / "skills" / "hep-ml" / "references"
FILES = ("robustness-and-distribution-shift.md", "space-and-astroparticle-ml.md")
TERMS = ("per-era training", "era conditioning", "common features", "missing-feature indicator",
         "per-era calibration", "working point", "measured in data")


def section(text):
    m = re.search(r"^## [^\n]*[Cc]onfiguration change[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


class EraChangesInMl(unittest.TestCase):
    def test_both_references_have_the_section(self):
        for name in FILES:
            with self.subTest(file=name):
                body = section((REFS / name).read_text(encoding="utf-8"))
                self.assertTrue(body, "no '## ... configuration change ...' section")
                low = body.lower()
                for term in TERMS:
                    self.assertIn(term, low, term)
                self.assertIn("multivariate-analysis-bdt-nn.md", body, "link to the executable BDT path")


if __name__ == "__main__":
    unittest.main()
