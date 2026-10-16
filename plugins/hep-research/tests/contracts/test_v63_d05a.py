"""v6.3 D05a: identity, recipe instances, typed references, root intent and declaration records (V05, V36, V42; the
D05a parts of V15 and V37). Synthetic data only."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

FIX = ROOT / "contracts" / "fixtures" / "artifacts" / "valid"
TABLE = json.loads((ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json").read_text())
RECIPE = json.loads((ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json").read_text())
AXES = {"species": ["proton", "helium"], "period": ["p1", "p2"]}
CAP = "measurement:correction-keys-v1"
R4 = ("target_scope", "calibration_digest", "variation_id", "stage", "application_id")


def keyed_spec(capability=True):
    spec = json.loads((FIX / "measurement_ratio.json").read_text())
    spec["extension"]["corrections"][0].update(target_scope="species:proton/period:p1", calibration_digest="none",
                                               variation_id="nominal", stage="estimator", application_id="exposure")
    if capability:
        spec["required_capabilities"] = [CAP]
    return spec


def instance(**kw):
    inst = {"instance_id": "p-p1", "recipe": "recipe", "scope": "species:proton/period:p1", "variation": "nominal",
            "role": "nominal", "nominal": None, "calibrations": {}}
    inst.update(kw)
    return inst


class V36SpecKeys(unittest.TestCase):
    """V36: with the capability the R4 keys and application_id are known; without it the legacy warnings stay."""

    @unittest.expectedFailure  # V36 (D05a)
    def test_capability_makes_the_keys_known(self):
        rep = validate_artifact(keyed_spec(), Vocabulary(), strict=True)
        self.assertFalse([f for f in rep.findings if f.code in ("measurement.unknown_key", "contract.unknown_capability")],
                         [f.as_dict() for f in rep.findings])

    def test_without_capability_the_legacy_threshold_holds(self):
        rep = validate_artifact(keyed_spec(capability=False), Vocabulary(), strict=True)
        flagged = {f.path.rsplit(".", 1)[-1] for f in rep.findings if f.code == "measurement.unknown_key"}
        self.assertEqual(flagged, set(R4))

    @unittest.expectedFailure  # V36 (D05a): malformed keys are errors under the capability
    def test_malformed_keys_are_errors(self):
        spec = keyed_spec()
        spec["extension"]["corrections"][0]["calibration_digest"] = "not-a-digest"
        rep = validate_artifact(spec, Vocabulary(), strict=True)
        self.assertIn("measurement.bad_correction_key", {f.code for f in rep.errors})


class V42ScopeParser(unittest.TestCase):
    """V42: illegal grammar is rejected and missing information is not a wildcard."""

    @unittest.expectedFailure  # V42 (D05a)
    def test_grammar(self):
        from contracts.analysis_checks.scope import parse_scope
        self.assertEqual(parse_scope("period:p1/species:proton", AXES)["axes"], {"period": "p1", "species": "proton"})
        cases = {"species:proton/species:helium": "scope.repeated_axis", "species:muon": "scope.unknown_value",
                 "detector:inner": "scope.unknown_axis", "species=proton": "scope.bad_syntax", "": "scope.bad_syntax"}
        for text, code in cases.items():
            with self.subTest(text=text):
                res = parse_scope(text, AXES)
                self.assertFalse(res["ok"])
                self.assertIn(code, res["errors"])

    @unittest.expectedFailure  # V42 (D05a)
    def test_comparison(self):
        from contracts.analysis_checks.scope import compare_scopes
        self.assertEqual(compare_scopes("species:proton/period:p1", "period:p1/species:proton", AXES), "equal")
        self.assertEqual(compare_scopes("species:proton/period:p1", "species:proton/period:p2", AXES), "different")
        self.assertEqual(compare_scopes("species:proton", "species:proton/period:p1", AXES), "unknown")
        self.assertEqual(compare_scopes("region-a", "region-b", AXES), "invalid")


class V05InstanceViews(unittest.TestCase):
    """V05: one recipe template builds instances; each view has sources; unspecified keys are filled, a literal that
    disagrees is never overridden; operators and step order are never replaced."""

    def build(self, recipe, inst, digests=None):
        from contracts.analysis_checks.instances import build_view
        return build_view(recipe, "recipe", TABLE, inst, "/recipe_instances/0", digests or {})

    @unittest.expectedFailure  # V05 (D05a)
    def test_template_filled_with_sources(self):
        views = [self.build(RECIPE, instance(instance_id=f"{s}-{p}", scope=f"species:{s}/period:{p}"))
                 for s in ("proton", "helium") for p in ("p1", "p2")]
        self.assertEqual(len({v["recipe"] for v in views}), 1)
        v = views[0]
        self.assertEqual([s["step_id"] for s in v["steps"]], [s["step_id"] for s in RECIPE["steps"]])
        key = v["steps"][1]["effects"]["exposure"]
        self.assertEqual(key["target_scope"], {"value": "species:proton/period:p1", "source": "context:/recipe_instances/0/scope"})
        self.assertEqual(key["variation_id"]["source"], "context:/recipe_instances/0/variation")
        self.assertEqual(key["calibration_digest"], {"value": None, "source": None})
        self.assertEqual(v["adapter"], "recipe-1.0.0-view")
        self.assertEqual(v["findings"], [])
        self.assertNotEqual(views[0]["view_digest"], views[1]["view_digest"])

    @unittest.expectedFailure  # V05 (D05a)
    def test_literal_is_never_overridden(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["recipe_version"] = "1.1.0"
        recipe["steps"][1]["effect_keys"] = {"exposure": {"target_scope": "species:helium/period:p1",
                                                          "calibration_digest": "none", "variation_id": "nominal",
                                                          "stage": "normalization"}}
        v = self.build(recipe, instance())
        self.assertIn("instance.override_rejected", {f["code"] for f in v["findings"]})
        key = v["steps"][1]["effects"]["exposure"]
        self.assertEqual(key["target_scope"]["value"], "species:helium/period:p1")
        self.assertEqual(key["target_scope"]["source"], "recipe:/steps/1/effect_keys/exposure/target_scope")

    @unittest.expectedFailure  # V05 (D05a)
    def test_calibration_binding_fills_the_digest(self):
        v = self.build(RECIPE, instance(calibrations={"exposure": "cal-p1"}), {"cal-p1": "c" * 64})
        key = v["steps"][1]["effects"]["exposure"]
        self.assertEqual(key["calibration_digest"], {"value": "c" * 64, "source": "context:/recipe_instances/0/calibrations/exposure"})


class ContextRecords(unittest.TestCase):
    """Typed bindings and declarations: an unknown binding type is unsupported, a declaration needs its author and
    basis, and a declaration that a rule does not apply is never counted (V25 definition)."""

    def ctx(self):
        return {"context_version": "1.0.0", "suite": {"id": "counting-chain", "version": "1.0.0"}, "spec": "spec",
                "scope_axes": AXES,
                "roots": [{"root_id": "flux-p-p1", "quantity": "differential_flux", "unit": "1/(m2 sr s GV)",
                           "binning": {"item": "spec", "pointer": "/extension/observable/variables/0/edges"},
                           "scope": "species:proton/period:p1", "output": {"instance": "p-p1"}}],
                "recipe_instances": [instance()], "bindings": [], "declarations": [],
                "obligations": {"generator": {"id": "g", "version": "1.0.0"}, "digest": "0" * 64, "items": []}}

    @unittest.expectedFailure  # D05a
    def test_clean_context(self):
        from contracts.analysis_checks.context import check_context
        self.assertEqual(check_context(self.ctx(), {"spec": "measurement-spec", "recipe": "recipe"}), [])

    @unittest.expectedFailure  # D05a
    def test_defects(self):
        from contracts.analysis_checks.context import check_context
        ctx = self.ctx()
        ctx["bindings"].append({"binding_id": "b1", "type": "same_as", "from": {"instance": "p-p1"}, "to": {"instance": "p-p1"}})
        ctx["declarations"].append({"declaration_id": "d1", "type": "instance_mapping", "content": {}})
        ctx["declarations"].append({"declaration_id": "d2", "type": "not_applicable", "asserted_by": {"kind": "agent", "id": "a"},
                                    "basis": {"rationale": "the rule does not apply"}, "content": {"rule": "r-resp.response_use"}})
        ctx["recipe_instances"].append(instance())
        ctx["roots"][0]["output"] = {"instance": "missing"}
        codes = {f["code"] for f in check_context(ctx, {"spec": "measurement-spec", "recipe": "recipe"})}
        self.assertTrue({"context.unsupported_binding", "context.declaration_unattributed",
                         "declaration.rule_waiver_not_counted", "context.duplicate_id", "context.unknown_reference"} <= codes,
                        codes)


if __name__ == "__main__":
    unittest.main()
