"""D4 (gate G4): the effect catalog gains survival and fragmentation_feeddown (no class, owner core); the catalog
check passes. (The coverage-contract parts went with the cross-artifact check.)"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import effect_catalog as ec  # noqa: E402

NEW = ("survival", "fragmentation_feeddown")


class SurvivalFragmentationCatalog(unittest.TestCase):
    def setUp(self):
        self.cat = ec.load_catalog()

    def test_effects(self):
        effects = {e["effect_id"]: e for e in self.cat["effects"]}
        for e in NEW:
            self.assertIn(e, effects)
            self.assertIsNone(effects[e]["class"])
        self.assertEqual(self.cat["owner"], "core")

    def test_checks_pass(self):
        self.assertEqual(ec.check_catalog(self.cat), [])
        self.assertEqual(ec.main(["check"]), 0)


if __name__ == "__main__":
    unittest.main()
