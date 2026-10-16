"""v6.3 M2a review findings: missing or malformed inputs give unverified outcomes or an input-invalid report, never a
pass or a traceback; declaration-reached outcomes of every state are flagged; the CLI keeps its exit-code contract."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import v63_cases as cases  # noqa: E402

SCOPE = "species:proton/period:synthetic-period-1"
COMP = "exposure_acceptance_livetime"


def ac():
    from contracts import analysis_check
    return analysis_check


def cli(*argv) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return ac().main([str(a) for a in argv])


def get(rep, oid):
    return next(o for o in rep["obligations"] if o["obligation_id"] == oid)


@unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")
class Findings(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)
        self.n = 0

    def case(self, builder=cases.positive_case, variant=None):
        self.n += 1
        root = self.base / f"c{self.n}"
        return builder(root, variant), root

    def report(self, builder=cases.positive_case, variant=None):
        b, root = self.case(builder, variant)
        view, diags = ac().load_subject(b, root)
        return ac().evaluate(view, diags)

    def test_missing_recipe_file(self):
        b, root = self.case()
        (root / "recipe.json").unlink()
        self.assertEqual(cli("check", b, "--root", root), 1)

    def test_freeze_refuses_malformed_recipe(self):
        def bad(c):
            c.files["recipe.json"] = {"steps": ["x"]}
        with self.assertRaises(ac().BundleRefused):
            self.case(variant=bad)

    def test_malformed_recipe_in_bundle(self):
        b, root = self.case()
        (root / "recipe.json").write_text(json.dumps({"steps": ["x"]}))
        view, diags = ac().load_subject(b, root)
        self.assertEqual(ac().evaluate(view, diags)["input_validity"], "invalid")

    def test_root_needs_the_estimand(self):
        from contracts.analysis_checks.rules import evaluate
        b, root = self.case()
        view, _ = ac().load_subject(b, root)
        view["items"]["flux-reduced"]["doc"].pop("estimand_kind")
        out = {o["obligation_id"]: o for o in evaluate(view, view["context"]["obligations"]["items"])}
        self.assertEqual(out["r-inv.root:flux-proton-p1"]["state"], "unverified")

    def factors(self, values):
        def variant(c):
            c.add("calibration", "factors", "factors.json", {"factor_table_version": "1.0.0", "factors": values})
            c.context["recipe_instances"][0]["calibrations"] = {"exposure": "factors"}
        return get(self.report(variant=variant), f"r-comp.factor_values:proton-p1#{COMP}")

    def test_factor_values_need_finite_bins(self):
        empty = {k: {"values": []} for k in ("exposure", "acceptance", "livetime")}
        self.assertEqual(self.factors(empty)["state"], "unverified")
        nan = {"exposure": {"values": [float("nan")]}, "acceptance": {"values": [1.0]}, "livetime": {"values": [1.0]}}
        self.assertNotEqual(self.factors(nan)["state"], "satisfied")

    def test_declaration_reached_not_applicable(self):
        def two(c):
            spec = c.doc("spec")
            for corr in spec["extension"]["corrections"]:
                corr.pop("target_scope")
            c.context["scope_axes"]["period"].append("synthetic-period-2")
            c.context["recipe_instances"].append(dict(c.context["recipe_instances"][0], instance_id="proton-p2",
                                                      scope="species:proton/period:synthetic-period-2"))
            c.context["declarations"] = cases.mapping({"selection_efficiency": ["proton-p2"], "acceptance": ["proton-p2"]})
        rep = self.report(variant=two)
        o = get(rep, "r-real.description:acceptance@proton-p1")
        self.assertEqual((o["state"], o["declaration_based"]), ("not_applicable", True))
        self.assertLess(rep["formal_use_view"]["counts"]["not_applicable"], rep["counts"]["not_applicable"])

    def test_response_rule_with_unknown_coverage(self):
        from test_v63_d06 import custom_table

        def variant(c):
            custom_table(c, "differential-flux-z", None, None, drop_cov=("divide_bin_width",))
        o = get(self.report(variant=variant), "r-resp.response_use:proton-p1")
        self.assertEqual(o["state"], "unsupported")

    def test_duplicate_effect_ids(self):
        def dup(c):
            spec = c.doc("spec")
            spec["extension"]["corrections"].append(dict(spec["extension"]["corrections"][1], category="fiducial"))
        with self.assertRaises(ac().BundleRefused):
            self.case(variant=dup)
        from contracts.analysis_check import shape_diagnostics
        spec = {"extension": {"corrections": [{"effect_id": "x"}, {"effect_id": "x", "category": "fiducial"}]}}
        diags = shape_diagnostics({"spec": {"role": "measurement-spec", "ref": "s.json", "doc": spec}})
        self.assertEqual([d["code"] for d in diags], ["spec.duplicate_effect_id"])

    def test_partial_target_scope(self):
        def partial(c):
            c.doc("spec")["extension"]["corrections"][0]["target_scope"] = "species:proton"
            c.context["declarations"] = cases.mapping({"selection_efficiency": ["proton-p1"]})
        o = get(self.report(variant=partial), "r-real.description:selection_efficiency@proton-p1")
        self.assertEqual(o["state"], "unverified")

    def test_freeze_guards(self):
        with self.assertRaises(ac().BundleRefused):
            ac().freeze(self.base, "a", ["x"], {})
        c = cases.positive_case(self.base / "g", None, freeze=False)
        c.write()
        (self.base / "items.json").write_text(json.dumps(c.items))
        (self.base / "ctx.json").write_text(json.dumps(c.context))
        args = ["freeze", "--root", c.root, "--analysis", "a", "--items", self.base / "items.json", "--context", self.base / "ctx.json"]
        self.assertEqual(cli(*args, "--out", c.root / "check-context.json"), 2)
        self.assertEqual(cli(*args[:4], "", *args[5:], "--out", self.base / "b.json"), 1)
        self.assertFalse((c.root / "check-context.json").exists())
        self.assertEqual(cli(*args, "--out", self.base / "b.json"), 0)

    def test_cli_usage_errors(self):
        b, root = self.case()
        bad = self.base / "list.json"
        bad.write_text("[]")
        self.assertEqual(cli("check", b, "--root", root, "--previous", bad), 2)
        self.assertEqual(cli("summary", bad), 2)
        self.assertEqual(cli("check", b, "--root", root, "--out", self.base / "no" / "dir" / "r.json"), 2)

    def test_inventory_mismatch_under_drift(self):
        b, root = self.case()
        view, diags = ac().load_subject(b, root)
        view["coverage"]["differential-flux"]["doc"] = copy.deepcopy(view["coverage"]["differential-flux"]["doc"])
        for op in view["coverage"]["differential-flux"]["doc"]["operators"]:
            if op["operator_id"] == "divide_exposure":
                op["covers"] = []
        rep = ac().evaluate(view, diags)
        self.assertEqual(rep["input_validity"], "valid")
        self.assertEqual(ac().exit_code(rep), 3)


if __name__ == "__main__":
    unittest.main()
