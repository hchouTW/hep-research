"""Cross-artifact check Phase 2, release R3: r-real.undescribed 1.0.0 (G1, DR-8) on generator 1.1.0 and catalog 1.1.0,
and the factor obligation under any composition key (G14). Each applied effect needs a spec description: background
by a non-empty backgrounds block, exposure by the observable's normalization kind, another effect by a correction of
exactly that category; bin_width needs none. Synthetic cases only (tests/contracts/analysis_check_cases.py)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def report(variant=None, builder=None) -> dict:
    from contracts import analysis_check as ac
    root = Path(tempfile.mkdtemp()) / "c"
    bundle = (builder or cases.positive_case)(root, cases.both(variant, cases.context_1_1))
    view, diags = ac.load_subject(bundle, root)
    return ac.evaluate(view, diags)


def state(rep: dict, oid: str) -> tuple[str, str]:
    o = next(x for x in rep["obligations"] if x["obligation_id"] == oid)
    return o["state"], o["reason"]


def spec(c) -> dict:
    return c.doc("spec")["extension"]


@NEEDS_AMS
class Undescribed(unittest.TestCase):
    def test_outcomes(self):
        rep = report()
        self.assertEqual((rep["status"], rep["consistency"]), ("complete", "consistent"))
        self.assertEqual(state(rep, "r-real.undescribed:background@proton-p1"), ("satisfied", "check.effect_described"))
        self.assertEqual(state(rep, "r-real.undescribed:exposure@proton-p1"), ("satisfied", "check.effect_described"))
        self.assertEqual(state(rep, "r-real.undescribed:bin_width@proton-p1"), ("not_applicable", "check.description_not_required"))

        def drop(effect):
            def v(c):
                spec(c)["corrections"] = [x for x in spec(c)["corrections"] if x["category"] != effect]
            return v
        self.assertEqual(state(report(drop("livetime")), "r-real.undescribed:livetime@proton-p1"),
                         ("violated", "check.undescribed_correction"))

        def no_backgrounds(c):
            spec(c)["backgrounds"] = []
            spec(c)["no_backgrounds_reason"] = "synthetic: none"
        self.assertEqual(state(report(no_backgrounds), "r-real.undescribed:background@proton-p1"),
                         ("violated", "check.description_contradicted"))

        def other_normalization(c):
            spec(c)["observable"]["normalization"]["kind"] = "live-time"
        self.assertEqual(state(report(other_normalization), "r-real.undescribed:exposure@proton-p1"),
                         ("violated", "check.undescribed_correction"))

        def class_name_only(c):  # a class name describes no member (DR-8)
            for x in spec(c)["corrections"]:
                if x["category"] == "selection_efficiency":
                    x["category"] = "efficiency"
        self.assertEqual(state(report(class_name_only), "r-real.undescribed:selection_efficiency@proton-p1"),
                         ("violated", "check.undescribed_correction"))

        def unscoped(c):
            for x in spec(c)["corrections"]:
                if x["category"] == "livetime":
                    x.pop("target_scope")
        self.assertEqual(state(report(unscoped), "r-real.undescribed:livetime@proton-p1"),
                         ("unverified", "check.applicability_unbound"))

    def test_undefined_class_members_are_not_judged(self):
        # an operator whose class coverage leaves its members undefined applies no member here (DR-8)
        from contracts.analysis_checks.obligations import applied_effects
        view = {"items": {"r": {"doc": {"semantics": {"table_id": "t"}, "steps": [{"operator": "op"}]}}},
                "coverage": {"t": {"doc": {"operators": [{"operator_id": "op", "covers": ["migration"],
                                                          "class_coverage": {"efficiency": {"members": None}}}]}}}}
        self.assertEqual(applied_effects(view, {"recipe": "r"}), {"migration"})
        view["coverage"]["t"]["doc"]["operators"][0]["class_coverage"]["efficiency"]["members"] = ["selection_efficiency"]
        self.assertEqual(applied_effects(view, {"recipe": "r"}), {"migration", "selection_efficiency"})

    def test_a_1_0_0_suite_has_no_undescribed_obligation(self):
        from contracts import analysis_check as ac
        root = Path(tempfile.mkdtemp()) / "old"
        view, diags = ac.load_subject(cases.positive_case(root), root)
        self.assertFalse([o for o in ac.evaluate(view, diags)["obligations"] if o["rule_id"] == "r-real.undescribed"])


@NEEDS_AMS
class FactorKeys(unittest.TestCase):
    def test_parent_or_child_key(self):
        def table(key):
            def v(c):
                c.add("calibration", "exp-factors", "exposure-factors.json", {
                    "factor_table_version": "1.0.0", "factors": {"exposure": {"values": [1.0, 2.0]},
                                                                 "acceptance": {"values": [0.5, 1.0]},
                                                                 "livetime": {"values": [2.0, 2.0]}}})
                c.context["recipe_instances"][0]["calibrations"] = {key: "exp-factors"}
            return v
        for key in ("exposure", "acceptance", "livetime"):
            with self.subTest(key=key):
                obs = [o for o in report(table(key))["obligations"] if o["rule_id"] == "r-comp.factor_values"]
                self.assertEqual([o["state"] for o in obs], ["satisfied"], obs)

    def test_two_tables_under_two_keys_are_both_checked(self):
        def two(c):
            for item, key in (("t-a", "exposure"), ("t-b", "acceptance")):
                c.add("calibration", item, f"{item}.json", {
                    "factor_table_version": "1.0.0", "factors": {"exposure": {"values": [1.0]}, "acceptance": {"values": [0.5]},
                                                                 "livetime": {"values": [2.0]}}})
            c.context["recipe_instances"][0]["calibrations"] = {"exposure": "t-a", "acceptance": "t-b"}
        obs = [o["obligation_id"] for o in report(two)["obligations"] if o["rule_id"] == "r-comp.factor_values"]
        self.assertEqual(len(obs), 2)
        self.assertTrue(all(o.endswith(("@t-a", "@t-b")) for o in obs), obs)



class CatalogVersion(unittest.TestCase):
    def test_catalog_1_1_0_and_coverage_compatibility(self):
        import json
        from contracts.effect_catalog import _catalog_compatible
        cat = json.loads((ROOT / "contracts" / "vocab" / "effects.json").read_text())
        self.assertEqual(cat["catalog_version"], "1.1.0")
        self.assertEqual({e["effect_id"] for e in cat["effects"] if not e["description_required"]}, {"bin_width"})
        self.assertTrue(_catalog_compatible("1.0.0", "1.1.0"))  # a contract written for 1.0.0 still reads
        self.assertTrue(_catalog_compatible("1.1.0", "1.1.0"))
        self.assertFalse(_catalog_compatible("1.1.0", "1.0.0"))  # never a contract newer than the catalog
        self.assertFalse(_catalog_compatible("2.0.0", "1.1.0"))
        self.assertFalse(_catalog_compatible("x", "1.1.0"))



class ShrinkDeprecation(unittest.TestCase):
    """The value gate's Shrink decision (2026-10-23): model-card and run-lineage are deprecated; the check CLI says so
    on stderr and changes neither stdout nor the report; counting-chain and ratio-subset say nothing."""

    def check_cli(self, bundle: Path, root: Path):
        import subprocess
        return subprocess.run([sys.executable, str(ROOT / "contracts" / "analysis_check.py"), "check", str(bundle),
                               "--root", str(root)], capture_output=True, text=True, timeout=300)

    def test_notice_for_deprecated_suites_only(self):
        import json
        for builder, deprecated in ((cases.model_case, True), (cases.ratio_case, False)):
            with self.subTest(case=builder.__name__):
                root = Path(tempfile.mkdtemp()) / "c"
                res = self.check_cli(builder(root, cases.context_1_1), root)
                self.assertEqual("deprecated:" in res.stderr, deprecated, res.stderr[-500:])
                self.assertIn("obligations", json.loads(res.stdout))

    def test_deprecated_rules_are_registered_as_deprecated(self):
        import json
        reg = json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text())
        live = [r for r in reg["rules"] if r["lifecycle"] != "retired" and r["kind"] != "legacy"]
        for r in live:
            gone = any(x.startswith(("model-card", "run-lineage")) for x in r["suites"])
            with self.subTest(rule=f"{r['rule_id']}@{r['version']}"):
                self.assertEqual(r["lifecycle"] == "deprecated", gone)


if __name__ == "__main__":
    unittest.main()
