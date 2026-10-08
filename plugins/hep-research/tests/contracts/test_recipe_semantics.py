"""T4.6: operator semantics for bounded recipes. The shipped recipe passes against the shipped table; repeated
corrections (within the recipe or across upstream artifacts, P05), wrong order, kind or unit mismatches, incomplete
results, unknown operators, changed tables and uncontracted tools fail with specific codes. Synthetic values only."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import recipe_semantics as rs  # noqa: E402

SEM = ROOT / "contracts" / "semantics"
TABLE = json.loads((SEM / "tables" / "differential_flux.json").read_text(encoding="utf-8"))
RECIPE = json.loads((SEM / "recipes" / "flux_from_counts.json").read_text(encoding="utf-8"))
TABLES = {TABLE["table_id"]: TABLE}


def codes(res):
    return sorted({f["code"] for f in res["findings"] if f["severity"] == "error"})


def recipe(*ops, applied=(), estimand="differential_flux"):
    r = copy.deepcopy(RECIPE)
    r["steps"] = [{"step_id": f"s{i}", "operator": op} for i, op in enumerate(ops)]
    r["input"]["applied_effects"] = list(applied)
    r["estimand_kind"] = estimand
    if "unfold" in ops or "unfold_with_efficiency" in ops:
        r["not_applied"] = []
    return r


SEPARATE = ("subtract_background", "unfold", "correct_efficiency", "divide_exposure", "divide_bin_width")


class ShippedTests(unittest.TestCase):
    def test_every_shipped_table_passes(self):
        for p in sorted((SEM / "tables").glob("*.json")):
            with self.subTest(table=p.name):
                rep = rs.check_table(json.loads(p.read_text(encoding="utf-8")))
                self.assertTrue(rep.ok, rep.as_dict())

    def test_every_shipped_recipe_passes(self):
        paths = sorted((SEM / "recipes").glob("*.json"))
        self.assertTrue(paths)
        for p in paths:
            with self.subTest(recipe=p.name):
                res = rs.check_recipe(json.loads(p.read_text(encoding="utf-8")), TABLES)
                self.assertEqual(res["status"], "pass", res["findings"])

    def test_valid_variants(self):
        for ops in (SEPARATE, ("subtract_background", "unfold_with_efficiency", "divide_exposure", "divide_bin_width"),
                    ("subtract_background", "correct_efficiency", "divide_exposure", "divide_bin_width")):
            with self.subTest(ops=ops):
                self.assertEqual(rs.check_recipe(recipe(*ops), TABLES)["status"], "pass")

    def test_cli(self):
        cmd = [sys.executable, "-B", str(ROOT / "contracts" / "recipe_semantics.py"), str(SEM / "recipes" / "flux_from_counts.json")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            up = Path(tmp) / "up.json"
            up.write_text(json.dumps({"extension": {"observable": {"included_corrections": ["efficiency"]}}}))
            p = subprocess.run(cmd + ["--upstream", str(up)], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 1)
            self.assertIn("semantics.repeated_correction", p.stdout)
            up.write_text("[")
            p = subprocess.run(cmd + ["--upstream", str(up)], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 2)


class RepeatedCorrectionTests(unittest.TestCase):
    """P05: a correction applied in two steps, or upstream and again here."""

    def test_within_recipe(self):
        for ops in (("subtract_background", "unfold_with_efficiency", "correct_efficiency", "divide_exposure", "divide_bin_width"),
                    ("subtract_background", "correct_efficiency", "divide_effective_exposure", "divide_bin_width"),
                    ("subtract_background", "unfold_with_efficiency", "divide_effective_exposure", "divide_bin_width")):
            with self.subTest(ops=ops):
                self.assertIn("semantics.repeated_correction", codes(rs.check_recipe(recipe(*ops), TABLES)))

    def test_declared_input_needs_upstream_record(self):
        r = recipe("correct_efficiency", "divide_exposure", "divide_bin_width", applied=["background"])
        res = rs.check_recipe(r, TABLES)
        self.assertEqual(res["status"], "pass")
        self.assertIn("semantics.input_effects_unverified", [f["code"] for f in res["findings"]])
        art = {"extension": {"observable": {"included_corrections": []}}}
        self.assertEqual(codes(rs.check_recipe(r, TABLES, upstream=[art])), ["semantics.input_effects_uncorroborated"])

    def test_upstream_without_record(self):
        for art in ({}, [], {"extension": {}}, {"extension": {"observable": {}}}):
            with self.subTest(art=art):
                self.assertIn("semantics.upstream_unrecorded", codes(rs.check_recipe(RECIPE, TABLES, upstream=[art])))

    def test_declared_input(self):
        res = rs.check_recipe(recipe(*SEPARATE, applied=["background"]), TABLES)
        self.assertIn("semantics.repeated_correction", codes(res))

    def test_upstream_artifact(self):
        for art in ({"extension": {"observable": {"included_corrections": ["efficiency"]}}},
                    {"extension": {"corrections": ["efficiency"]}},
                    {"extension": {"corrections": [{"effect_id": "efficiency", "category": "x", "applied_in": "y"}]}}):
            with self.subTest(art=art):
                res = rs.check_recipe(RECIPE, TABLES, upstream=[art])
                self.assertIn("semantics.repeated_correction", codes(res))

    def test_malformed_upstream_entry_fails_closed(self):
        for entry in ({"category": "x"}, 7, None):
            with self.subTest(entry=entry):
                art = {"extension": {"corrections": [entry]}}
                self.assertIn("semantics.upstream_unmapped", codes(rs.check_recipe(RECIPE, TABLES, upstream=[art])))

    def test_upstream_name_outside_table_fails_closed(self):
        art = {"extension": {"observable": {"included_corrections": ["trigger efficiency"]}}}
        self.assertIn("semantics.upstream_unmapped", codes(rs.check_recipe(RECIPE, TABLES, upstream=[art])))

    def test_upstream_effect_also_declared_is_one_application(self):
        art = {"extension": {"observable": {"included_corrections": ["background"]}}}
        r = recipe("correct_efficiency", "divide_exposure", "divide_bin_width", applied=["background"])
        self.assertEqual(rs.check_recipe(r, TABLES, upstream=[art])["status"], "pass")


class OrderAndKindTests(unittest.TestCase):
    def test_background_after_efficiency(self):
        r = recipe("correct_efficiency", "subtract_background", "divide_exposure", "divide_bin_width")
        self.assertIn("semantics.order", codes(rs.check_recipe(r, TABLES)))

    def test_unfold_after_efficiency(self):
        r = recipe("subtract_background", "correct_efficiency", "unfold", "divide_exposure", "divide_bin_width")
        self.assertIn("semantics.order", codes(rs.check_recipe(r, TABLES)))

    def test_kind_chain(self):
        r = recipe("subtract_background", "divide_bin_width", "divide_exposure")
        self.assertIn("semantics.kind_mismatch", codes(rs.check_recipe(r, TABLES)))

    def test_ends_in_wrong_kind(self):
        r = recipe("subtract_background", "correct_efficiency", "divide_exposure")
        self.assertIn("semantics.kind_mismatch", codes(rs.check_recipe(r, TABLES)))

    def test_incomplete(self):
        r = recipe("subtract_background", "divide_exposure", "divide_bin_width")
        self.assertIn("semantics.incomplete", codes(rs.check_recipe(r, TABLES)))

    def test_unknown_operator_and_estimand(self):
        self.assertIn("semantics.unknown_operator", codes(rs.check_recipe(recipe("subtract_background", "smooth"), TABLES)))
        r = recipe(*SEPARATE[:-1], estimand="integrated_flux")
        self.assertIn("semantics.unknown_estimand", codes(rs.check_recipe(r, TABLES)))

    def test_duplicate_step_id(self):
        r = recipe(*SEPARATE)
        r["steps"][1]["step_id"] = r["steps"][0]["step_id"]
        self.assertIn("semantics.duplicate_id", codes(rs.check_recipe(r, TABLES)))


class OmissionTests(unittest.TestCase):
    def test_undeclared_omission(self):
        r = copy.deepcopy(RECIPE)
        r["not_applied"] = []
        self.assertEqual(codes(rs.check_recipe(r, TABLES)), ["semantics.omission_undeclared"])

    def test_invalid_not_applied(self):
        for name, extra in {"applied": {"effect_id": "background", "reason": "x"},
                            "unknown": {"effect_id": "luminosity", "reason": "x"},
                            "twice": {"effect_id": "migration", "reason": "again"}}.items():
            with self.subTest(name):
                r = copy.deepcopy(RECIPE)
                r["not_applied"].append(extra)
                self.assertIn("semantics.not_applied_invalid", codes(rs.check_recipe(r, TABLES)))

    def test_failing_tool_contract_is_not_used(self):
        contract = json.loads((ROOT / "contracts" / "tool_contracts" / "cosmic_ray_flux.json").read_text(encoding="utf-8"))
        contract["operations"][0]["required_capabilities"] = ["core:never-implemented"]
        res = rs.check_recipe(RECIPE, TABLES, contracts=[contract])
        self.assertIn("semantics.tool_uncontracted", codes(res))


class BindingTests(unittest.TestCase):
    def test_changed_table(self):
        t = copy.deepcopy(TABLE)
        t["operators"][0]["forbids_after"] = []
        self.assertEqual(codes(rs.check_recipe(RECIPE, {t["table_id"]: t})), ["semantics.table_changed"])

    def test_missing_or_invalid_table(self):
        self.assertEqual(codes(rs.check_recipe(RECIPE, {})), ["semantics.table_missing"])
        t = copy.deepcopy(TABLE)
        t["operators"][0]["applies"] = ["nonexistent"]
        self.assertEqual(codes(rs.check_recipe(RECIPE, {t["table_id"]: t})), ["semantics.table_invalid"])

    def test_tool_must_list_operator(self):
        r = copy.deepcopy(RECIPE)
        r["steps"][1]["operator"] = "divide_exposure"
        r["steps"].insert(1, {"step_id": "eff", "operator": "correct_efficiency", "tool": "cosmic-ray-flux:flux"})
        self.assertEqual(codes(rs.check_recipe(r, TABLES)), ["semantics.tool_uncontracted"])
        r["steps"][1]["tool"] = "no-such-tool:run"
        self.assertEqual(codes(rs.check_recipe(r, TABLES)), ["semantics.tool_uncontracted"])

    def test_schema_refusals(self):
        for name, fn in {"no steps": lambda r: r.update(steps=[]), "approval field": lambda r: r.update(approved=True),
                         "short digest": lambda r: r["semantics"].update(sha256="abc")}.items():
            with self.subTest(name):
                r = copy.deepcopy(RECIPE)
                fn(r)
                self.assertEqual(rs.check_recipe(r, TABLES)["status"], "fail")


class TableTests(unittest.TestCase):
    def test_table_defects(self):
        cases = {
            "semantics.duplicate_id": lambda t: t["effects"].append(dict(t["effects"][0])),
            "semantics.undeclared_kind": lambda t: t["operators"][0].update(output_kind="rate"),
            "semantics.undeclared_effect": lambda t: t["estimands"][0]["required_effects"].append("luminosity"),
            "semantics.self_contradiction": lambda t: t["operators"][0]["requires"].append("background"),
        }
        for code, fn in cases.items():
            with self.subTest(code):
                t = copy.deepcopy(TABLE)
                fn(t)
                self.assertIn(code, codes({"findings": [f.as_dict() for f in rs.check_table(t).findings]}))


if __name__ == "__main__":
    unittest.main()
