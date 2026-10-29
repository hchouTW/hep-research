"""The effect catalog contracts/vocab/effects.json (classification, conditional composition), checked by
contracts/effect_catalog.py; the legacy operator-semantics table, its digest and IMPLIED_CORRECTIONS are unchanged.
(Kept from the cross-artifact check's D04 tests when the check was retired; the operator coverage contracts went with
it.) Synthetic definitions only."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.recipe_semantics import canonical_sha256  # noqa: E402

TABLE_PATH = ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json"
TABLE = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
LEGACY_TABLE_SHA = "126407076c775268589c65501c05cda08ef623923b70a458325e33fbbd911a49"


def catalog_module():
    from contracts import effect_catalog
    return effect_catalog


def catalog():
    return catalog_module().load_catalog()


class ShippedDefinitions(unittest.TestCase):
    def test_legacy_table_and_adapters_unchanged(self):
        from contracts.validate import IMPLIED_CORRECTIONS
        self.assertEqual(canonical_sha256(TABLE), LEGACY_TABLE_SHA)
        self.assertEqual(IMPLIED_CORRECTIONS, {"exposure": {"acceptance", "livetime"}})

    def test_composition_is_conditional(self):
        comp = [c for c in catalog()["compositions"] if c["parent"] == "exposure"]
        self.assertTrue(comp)
        for c in comp:
            self.assertTrue(c["conditions"], "never claim every exposure equals acceptance x live time")

    def test_classification_and_legacy_adapter_are_separate(self):
        cat, classify = catalog(), catalog_module().classify
        self.assertEqual(classify(cat, "trigger_efficiency"), {"class": "efficiency", "basis": "catalog"})
        # a name matching the old pattern but not in the catalog is classified only by the legacy adapter
        self.assertEqual(classify(cat, "timing_efficiency"), {"class": "efficiency", "basis": "legacy-pattern"})
        self.assertEqual(classify(cat, "unheard_of"), {"class": None, "basis": None})


class CatalogChecks(unittest.TestCase):
    def test_defects_are_reported(self):
        cat = copy.deepcopy(catalog())
        cat["effects"].append(copy.deepcopy(cat["effects"][0]))
        next(c for c in cat["classes"] if c["class_id"] == "efficiency")["members"].append("absent_efficiency")
        cat["compositions"].append({"composition_id": "bad", "parent": "exposure", "children":
                                    [{"effect": "nothing", "power": 1}], "normalization_kind": "exposure",
                                    "conditions": ["synthetic"], "convention": "synthetic"})
        codes = {f["code"] for f in catalog_module().check_catalog(cat)}
        self.assertTrue({"catalog.duplicate_effect", "catalog.unknown_member", "catalog.unknown_effect"} <= codes, codes)


if __name__ == "__main__":
    unittest.main()
