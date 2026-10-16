"""F-14: the core vocabulary has the levels top-of-instrument and top-of-atmosphere (a minor, additive change), and the
synthetic cosmic-ray worked spec uses top-of-instrument instead of detector. Before the fix only the profile term
crflux:top-of-instrument existed and the synthetic spec, which needs no profile, said 'detector'."""
import json
import unittest
from pathlib import Path

from contracts.validate import validate_artifact

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "skills" / "hep-measurement" / "assets" / "worked-spec.cosmic-ray.synthetic.json"


class Levels(unittest.TestCase):
    def test_core_levels(self):
        levels = json.loads((ROOT / "contracts/vocab/core.json").read_text())["vocabularies"]["levels"]
        for term in ("top-of-instrument", "top-of-atmosphere"):
            self.assertIn(term, levels)
        for old in ("parton", "particle-fiducial", "detector", "unfolded"):
            self.assertIn(old, levels)

    def test_synthetic_spec_validates_with_top_of_instrument(self):
        doc = json.loads(SPEC.read_text())
        self.assertEqual(doc["extension"]["observable"]["level"], "top-of-instrument")
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse([f for f in rep.as_dict()["findings"] if "level" in f.get("path", "")])

    def test_an_unknown_level_is_still_refused(self):
        doc = json.loads(SPEC.read_text())
        doc["extension"]["observable"]["level"] = "top-of-the-world"
        self.assertFalse(validate_artifact(doc).ok)


if __name__ == "__main__":
    unittest.main()
