"""v6.3 D04: the effect catalog (classification, conditional composition) and versioned operator coverage contracts,
definition parts of V35, V43 and V58. Missing definitions stay unverified or unsupported and are never filled in from
class names (O09); the legacy table, its digest and IMPLIED_CORRECTIONS are unchanged. Synthetic definitions only."""
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


def ec():
    from contracts import effect_catalog
    return effect_catalog


def catalog():
    return ec().load_catalog()


def coverage():
    return ec().load_coverage("differential-flux")


class ShippedDefinitions(unittest.TestCase):
    def test_catalog_and_coverage_check_clean(self):
        cat, cov = catalog(), coverage()
        self.assertEqual(ec().check_catalog(cat), [])
        self.assertEqual(ec().check_coverage(cov, cat, TABLE), [])
        self.assertEqual(cov["table_sha256"], canonical_sha256(TABLE))

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
        cat = catalog()
        self.assertEqual(ec().classify(cat, "trigger_efficiency"), {"class": "efficiency", "basis": "catalog"})
        # a name matching the old pattern but not in the catalog is classified only by the legacy adapter
        self.assertEqual(ec().classify(cat, "timing_efficiency"), {"class": "efficiency", "basis": "legacy-pattern"})
        self.assertEqual(ec().classify(cat, "unheard_of"), {"class": None, "basis": None})


class V35Definition(unittest.TestCase):
    """V35 (definition part): trigger and selection efficiency against an effective exposure are realized only with
    listed operator coverage; the efficiency classification alone is not enough."""

    def test_class_alone_is_not_coverage(self):
        cat, cov = catalog(), coverage()
        for member in ("trigger_efficiency", "selection_efficiency"):
            self.assertEqual(ec().coverage_state(cov, "divide_effective_exposure", member, cat)["state"], "unverified")

    def test_listed_members_are_covered(self):
        cat, cov = catalog(), copy.deepcopy(coverage())
        op = next(o for o in cov["operators"] if o["operator_id"] == "divide_effective_exposure")
        op["class_coverage"]["efficiency"] = {"members": ["trigger_efficiency", "selection_efficiency"],
                                              "basis": "synthetic test contract"}
        self.assertEqual(ec().check_coverage(cov, cat, TABLE), [])
        for member in ("trigger_efficiency", "selection_efficiency"):
            self.assertEqual(ec().coverage_state(cov, "divide_effective_exposure", member, cat)["state"], "covered")


class V43Definition(unittest.TestCase):
    """V43 (definition part): a new efficiency member not in an operator's coverage cannot be realized
    automatically."""

    def test_new_member_is_not_covered(self):
        cat = copy.deepcopy(catalog())
        cat["effects"].append({"effect_id": "tracking_efficiency", "class": "efficiency",
                               "definition": "synthetic new member"})
        next(c for c in cat["classes"] if c["class_id"] == "efficiency")["members"].append("tracking_efficiency")
        self.assertEqual(ec().check_catalog(cat), [])
        cov = copy.deepcopy(coverage())
        op = next(o for o in cov["operators"] if o["operator_id"] == "correct_efficiency")
        self.assertNotIn("tracking_efficiency", op["class_coverage"]["efficiency"]["members"])
        self.assertEqual(ec().coverage_state(cov, "correct_efficiency", "tracking_efficiency", cat)["state"],
                         "not_covered")

    def test_unknown_effect_or_operator_is_unsupported(self):
        cat, cov = catalog(), coverage()
        self.assertEqual(ec().coverage_state(cov, "correct_efficiency", "unheard_of", cat)["state"], "unsupported")
        self.assertEqual(ec().coverage_state(cov, "no_such_operator", "trigger_efficiency", cat)["state"], "unsupported")

    def test_bare_efficiency_keeps_legacy_coverage(self):
        cat, cov = catalog(), coverage()
        res = ec().coverage_state(cov, "divide_effective_exposure", "efficiency", cat)
        self.assertEqual((res["state"], res["basis"]), ("covered", "legacy-table"))


class V58Definition(unittest.TestCase):
    """V58 (definition part): resolving a class's member set records its dependencies; an updated class set changes
    the closure, an unrelated definition does not."""

    def test_member_closure(self):
        cat = catalog()
        base = ec().resolve_members(cat, "efficiency")
        self.assertEqual(base["strategy"], "listed")
        self.assertIn("trigger_efficiency", base["members"])
        self.assertIn("efficiency", base["dependencies"])
        unrelated = copy.deepcopy(cat)
        unrelated["effects"].append({"effect_id": "dead_time", "class": None, "definition": "synthetic, unrelated"})
        self.assertEqual(ec().resolve_members(unrelated, "efficiency")["closure_digest"], base["closure_digest"])
        grown = copy.deepcopy(cat)
        grown["effects"].append({"effect_id": "tracking_efficiency", "class": "efficiency", "definition": "synthetic"})
        next(c for c in grown["classes"] if c["class_id"] == "efficiency")["members"].append("tracking_efficiency")
        res = ec().resolve_members(grown, "efficiency")
        self.assertNotEqual(res["closure_digest"], base["closure_digest"])
        self.assertIn("tracking_efficiency", res["members"])


class CatalogChecks(unittest.TestCase):
    def test_defects_are_reported(self):
        cat = copy.deepcopy(catalog())
        cat["effects"].append(copy.deepcopy(cat["effects"][0]))
        next(c for c in cat["classes"] if c["class_id"] == "efficiency")["members"].append("absent_efficiency")
        cat["compositions"].append({"composition_id": "bad", "parent": "exposure", "children":
                                    [{"effect": "nothing", "power": 1}], "normalization_kind": "exposure",
                                    "conditions": ["synthetic"], "convention": "synthetic"})
        codes = {f["code"] for f in ec().check_catalog(cat)}
        self.assertTrue({"catalog.duplicate_effect", "catalog.unknown_member", "catalog.unknown_effect"} <= codes, codes)

    def test_coverage_bound_to_the_table(self):
        cat, cov = catalog(), copy.deepcopy(coverage())
        cov["table_sha256"] = "0" * 64
        cov["operators"].append({"operator_id": "no_such_operator", "stage": "estimator", "covers": [],
                                 "class_coverage": {}})
        codes = {f["code"] for f in ec().check_coverage(cov, cat, TABLE)}
        self.assertTrue({"coverage.table_changed", "coverage.unknown_operator"} <= codes, codes)


if __name__ == "__main__":
    unittest.main()
