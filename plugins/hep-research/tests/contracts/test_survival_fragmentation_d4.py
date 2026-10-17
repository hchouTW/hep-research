"""D4 (gate G4): the effect catalog gains survival and fragmentation_feeddown (no class, owner core); the
differential-flux coverage contract lists survival for divide_effective_exposure and fragmentation_feeddown for
subtract_background; the catalog and coverage checks pass and the efficiency closure is unchanged."""
import json
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
        self.cov = ec.load_coverage("differential-flux")

    def test_effects(self):
        effects = {e["effect_id"]: e for e in self.cat["effects"]}
        for e in NEW:
            self.assertIn(e, effects)
            self.assertIsNone(effects[e]["class"])
        self.assertEqual(self.cat["owner"], "core")

    def test_checks_pass(self):
        self.assertEqual(ec.check_catalog(self.cat), [])
        self.assertEqual(ec.check_coverage(self.cov, self.cat, ec._table("differential-flux")), [])
        self.assertEqual(ec.main(["check"]), 0)

    def test_coverage(self):
        state = lambda op, e: ec.coverage_state(self.cov, op, e, self.cat)["state"]  # noqa: E731
        self.assertEqual(state("divide_effective_exposure", "survival"), "covered")
        self.assertEqual(state("subtract_background", "fragmentation_feeddown"), "covered")
        self.assertEqual(state("divide_exposure", "survival"), "not_covered")
        self.assertEqual(state("divide_bin_width", "fragmentation_feeddown"), "not_covered")

    def test_efficiency_closure_unchanged(self):
        base = json.loads(json.dumps(self.cat))
        base["effects"] = [e for e in base["effects"] if e["effect_id"] not in NEW]
        self.assertEqual(ec.resolve_members(self.cat, "efficiency")["closure_digest"],
                         ec.resolve_members(base, "efficiency")["closure_digest"])


if __name__ == "__main__":
    unittest.main()
