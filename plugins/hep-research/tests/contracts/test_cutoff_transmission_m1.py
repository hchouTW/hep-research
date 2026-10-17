"""M1 (gate G4): the effect catalog gains the effect cutoff_transmission and the three-child composition
exposure_acceptance_livetime_transmission; the two-child composition is unchanged; the differential-flux coverage
contract lists the new effect for the exposure operators; the catalog and coverage checks still pass."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import effect_catalog as ec  # noqa: E402


class CutoffTransmissionCatalog(unittest.TestCase):
    def setUp(self):
        self.cat = ec.load_catalog()
        self.cov = ec.load_coverage("differential-flux")

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

    def test_catalog_and_coverage_checks_pass(self):
        self.assertEqual(ec.check_catalog(self.cat), [])
        table = ec._table("differential-flux")
        self.assertEqual(ec.check_coverage(self.cov, self.cat, table), [])
        self.assertEqual(ec.main(["check"]), 0)

    def test_exposure_operators_cover_the_transmission(self):
        for op in ("divide_exposure", "divide_effective_exposure"):
            with self.subTest(op=op):
                self.assertEqual(ec.coverage_state(self.cov, op, "cutoff_transmission", self.cat)["state"], "covered")
        self.assertEqual(ec.coverage_state(self.cov, "divide_bin_width", "cutoff_transmission", self.cat)["state"],
                         "not_covered")

    def test_efficiency_closure_is_unchanged_by_the_new_entries(self):
        base = json.loads(json.dumps(self.cat))
        base["effects"] = [e for e in base["effects"] if e["effect_id"] != "cutoff_transmission"]
        base["compositions"] = [c for c in base["compositions"]
                                if c["composition_id"] != "exposure_acceptance_livetime_transmission"]
        self.assertEqual(ec.resolve_members(self.cat, "efficiency")["closure_digest"],
                         ec.resolve_members(base, "efficiency")["closure_digest"])

    def test_a_factor_table_chooses_its_composition(self):
        from contracts.analysis_checks.obligations import factor_compositions
        comps = [c for c in self.cat["compositions"] if c["parent"] == "exposure"]
        self.assertEqual(len(comps), 2)

        def chosen(*names):
            return [c["composition_id"] for c in factor_compositions(comps, {"factors": {n: {} for n in names}})]
        self.assertEqual(chosen("exposure", "acceptance", "livetime"), ["exposure_acceptance_livetime"])
        self.assertEqual(chosen("exposure", "acceptance", "livetime", "cutoff_transmission"),
                         ["exposure_acceptance_livetime_transmission"])
        self.assertEqual(chosen("exposure", "acceptance"), ["exposure_acceptance_livetime"])  # as before: one check
        self.assertEqual(factor_compositions(comps[:1], {"factors": {}}), comps[:1])


if __name__ == "__main__":
    unittest.main()
