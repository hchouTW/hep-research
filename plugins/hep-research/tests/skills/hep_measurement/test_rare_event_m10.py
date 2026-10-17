"""rare-event-and-neutrino-measurements.md (M10): the topics of the card are covered, every link resolves, no number
with a unit is quoted outside example blocks (experiment values come from profiles, papers or the user), and the
reference is routed from the hep-measurement guide."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-measurement" / "references" / "rare-event-and-neutrino-measurements.md"
SKILL = PLUGIN / "skills" / "hep-measurement" / "SKILL.md"


class RareEventReference(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_topics(self):
        for needle in ("kg y", "live time", "region of interest", "Salting", "Background budget", "quenching",
                       "keVee", "near detector", "flux", "cross section", "limit"):
            self.assertIn(needle, self.text)

    def test_links_resolve(self):
        for target in re.findall(r"\]\(([^)#]+)", self.text):
            self.assertTrue((REF.parent / target).is_file(), target)

    def test_no_numbers_with_units_outside_examples(self):
        body = re.sub(r"<!-- example.*?<!-- /example -->", "", self.text, flags=re.S)
        body = body.split("## Sources")[0]
        hits = re.findall(r"\b\d[\d.,]*\s*(?:kg|t y|keV|MeV|GeV|events|d\b|y\b|%)", body)
        self.assertEqual(hits, [])

    def test_routed_from_the_guide(self):
        guide = SKILL.parent / "references" / "hep-measurement-guide.md"
        self.assertIn("(rare-event-and-neutrino-measurements.md)", guide.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
