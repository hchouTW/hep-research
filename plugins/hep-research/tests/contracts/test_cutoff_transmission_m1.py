"""M1 (gate G4): the effect catalog gains the effect cutoff_transmission and the three-child composition
exposure_acceptance_livetime_transmission; the two-child composition is unchanged; the catalog check passes. (The
coverage-contract parts went with the cross-artifact check.)"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import effect_catalog as ec  # noqa: E402


class CutoffTransmissionCatalog(unittest.TestCase):
    def setUp(self):
        self.cat = ec.load_catalog()

    def test_effect_and_composition(self):
        effects = {e["effect_id"]: e for e in self.cat["effects"]}
        self.assertIn("cutoff_transmission", effects)
        self.assertIsNone(effects["cutoff_transmission"]["class"])
        comps = {c["composition_id"]: c for c in self.cat["compositions"]}
        new = comps["exposure_acceptance_livetime_transmission"]
        self.assertEqual(new["parent"], "exposure")
        self.assertEqual([(c["effect"], c["power"]) for c in new["children"]],
                         [("acceptance", 1), ("livetime", 1), ("cutoff_transmission", 1)])
        old = comps["exposure_acceptance_livetime"]
        self.assertEqual([c["effect"] for c in old["children"]], ["acceptance", "livetime"])
        self.assertEqual(self.cat["owner"], "core")

    def test_catalog_check_passes(self):
        self.assertEqual(ec.check_catalog(self.cat), [])
        self.assertEqual(ec.main(["check"]), 0)


if __name__ == "__main__":
    unittest.main()
