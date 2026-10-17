"""D6: "Adding a tracking layer to a running detector" in calibration-and-alignment.md.

Checks: the section exists and covers the outer lever arm and weak modes, stereo planes, alignment with existing
tracks, time dependence, the rigidity scale with and without the new layer (a split-consistency test) and the
hand-off of per-era residuals to propagate_scale_distortion.py; the experiment statements sit only inside an example
block, cite the beam-test paper arXiv:2603.25085 with its read level and the public profile claim ams02:C101, and
state that the era boundary must come from the experiment's own sources.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "skills" / "hep-detector" / "references" / "calibration-and-alignment.md"
EXAMPLE = re.compile(r"<!--\s*example.*?<!--\s*/example\s*-->", re.S)


def section(text):
    m = re.search(r"^## Adding a tracking layer to a running detector\n(.*?)(?=^## )", text, re.S | re.M)
    return m.group(1) if m else ""


class AddingALayer(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")
        self.sec = section(self.text)

    def test_section_covers_the_card(self):
        self.assertTrue(self.sec, "section missing")
        for phrase in ("lever arm", "weak mode", "stereo", "existing tracks", "time dependence", "rigidity scale",
                       "split", "propagate_scale_distortion.py", "era"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.sec.lower() if phrase.islower() else self.sec)

    def test_experiment_statements_only_in_an_example_block(self):
        blocks = EXAMPLE.findall(self.sec)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        for needle in ("arXiv:2603.25085", "abstract", "ams02:C101"):
            self.assertIn(needle, block)
        self.assertIn("era boundary", block)
        outside = EXAMPLE.sub("", self.text)
        self.assertNotRegex(outside, r"\bAMS\b|ams02:")


if __name__ == "__main__":
    unittest.main()
