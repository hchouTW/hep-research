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


class UnfoldedTarget(unittest.TestCase):
    """Triage T36: the vocabulary says the target level of 'unfolded' must be declared separately, but an unfolded
    observable with no target validated with no finding. Contracts 3.3.0 has no field for it, so the target is named in
    phase_space.definition; without one the observable gets the warning observable.unfolded_target_undeclared."""
    CODE = "observable.unfolded_target_undeclared"

    def run_with(self, level, definition):
        doc = json.loads(SPEC.read_text())
        doc["extension"]["observable"]["level"] = level
        doc["extension"]["observable"]["phase_space"]["definition"] = definition
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        return [(f.severity, f.path) for f in rep.findings if f.code == self.CODE]

    def test_unfolded_without_target_warns(self):
        for definition in ("SYNTHETIC: rigidity 2-100 GV", "unfolded to detector level", "unfolded, see note"):
            with self.subTest(definition=definition):
                self.assertEqual(self.run_with("unfolded", definition),
                                 [("warning", "$.extension.observable.level")])

    def test_unfolded_with_a_named_target_passes(self):
        for definition in ("unfolded to particle-fiducial: |eta| < 2.5", "Top-of-Instrument flux, rigidity 2-100 GV",
                           "target: parton level", "unfolded to particle_fiducial level"):
            with self.subTest(definition=definition):
                self.assertEqual(self.run_with("unfolded", definition), [])

    def test_other_levels_are_untouched(self):
        self.assertEqual(self.run_with("top-of-instrument", "SYNTHETIC: rigidity 2-100 GV"), [])


if __name__ == "__main__":
    unittest.main()
