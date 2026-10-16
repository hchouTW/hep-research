"""v6.3 D06: chain rules (R-REAL, R-STAGE, R-REP, R-COMP, R-RESP) on CASE-CHAIN, the reduced positive case and their
named variants (CHAIN-ID, CHAIN-SCOPE, CHAIN-RESPONSE, CHAIN-FLOW, L2 regression). V01-V04, V09, V10, V16, V21-V23,
V34, V35, V37, V39-V41, V43, V48, V49, V69 and the rule-dependent parts of V11, V12, V18, V64. Synthetic and public
inputs only, built in temporary folders by tests/contracts/v63_cases.py."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import v63_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")
SCOPE = "species:proton/period:synthetic-period-1"
COMP = "exposure_acceptance_livetime"


def ac():
    from contracts import analysis_check
    return analysis_check


def get(rep: dict, oid: str) -> dict:
    return next(o for o in rep["obligations"] if o["obligation_id"] == oid)


def by_rule(rep: dict, rule: str) -> list[dict]:
    return [o for o in rep["obligations"] if o["rule_id"] == rule]


def legacy_codes(rep: dict) -> set:
    return {f["code"] for f in rep["legacy_findings"]}


def recipe_of(c, rid="flux-reduced") -> dict:
    return c.doc(rid)


def keyed(scope, cal="none", variation="nominal", stage="estimator") -> dict:
    return {"efficiency": {"target_scope": scope, "calibration_digest": cal, "variation_id": variation, "stage": stage}}


def add_instance(c, iid, recipe_id, steps, role="nominal", nominal=None, variation="nominal", scope=SCOPE, feeds=None,
                 estimand="counts"):
    r = copy.deepcopy(recipe_of(c))
    r.update(recipe_id=recipe_id, steps=steps, estimand_kind=estimand)
    c.add("recipe", recipe_id, f"{recipe_id}.json", r)
    c.context["recipe_instances"].append({"instance_id": iid, "recipe": recipe_id, "scope": scope, "variation": variation,
                                          "role": role, "nominal": nominal, "calibrations": {}})
    if feeds:
        c.context["bindings"].append({"binding_id": f"{iid}-feeds", "type": "input_of", "from": {"instance": iid},
                                      "to": {"instance": feeds}})


PRE_STEPS = [{"step_id": "background", "operator": "subtract_background"},
             {"step_id": "efficiency", "operator": "correct_efficiency"}]


def custom_table(c, table_id, extra_op, extra_cov, recipe_id="flux-reduced", drop_cov=()):
    """A bundle-supplied table and coverage contract for a synthetic operator (no plugin coverage exists for it)."""
    from contracts.effect_catalog import load_coverage
    from contracts.recipe_semantics import canonical_sha256
    table = copy.deepcopy(c.doc("differential-flux"))
    table["table_id"] = table_id
    if extra_op:
        table["operators"].append(extra_op)
    c.remove("differential-flux")
    c.add("semantics-table", table_id, f"{table_id}.json", table)
    recipe_of(c, recipe_id)["semantics"] = {"table_id": table_id, "sha256": canonical_sha256(table)}
    cov = copy.deepcopy(load_coverage("differential-flux"))
    cov.update(table_id=table_id, table_sha256=canonical_sha256(table))
    cov["operators"] = [o for o in cov["operators"] if o["operator_id"] not in drop_cov]
    if extra_cov:
        cov["operators"].append(extra_cov)
    c.add("coverage-contract", f"{table_id}-coverage", f"{table_id}.coverage.json", cov)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def run_case(self, builder, variant=None) -> dict:
        self.n += 1
        root = Path(self.td.name) / f"c{self.n}"
        bundle = builder(root, variant)
        view, diags = ac().load_subject(bundle, root)
        return ac().evaluate(view, diags)

    def pos(self, variant=None) -> dict:
        return self.run_case(cases.positive_case, variant)

    def chain(self, variant=None) -> dict:
        return self.run_case(cases.chain_case, variant)


@NEEDS_AMS
class Realization(Tmp):
    def test_v01_one_more_consistent_description(self):
        base = self.pos()

        def more(c):
            c.doc("spec")["extension"]["corrections"].append(
                {"effect_id": "exposure", "category": "exposure", "applied_in": "normalization", "target_scope": SCOPE,
                 "variation_id": "nominal"})
        rep = self.pos(more)
        self.assertEqual(get(rep, "r-real.description:exposure@proton-p1")["state"], "satisfied")
        self.assertEqual([(o["obligation_id"], o["state"], o["evidence"]) for o in by_rule(base, "r-rep.repetition")],
                         [(o["obligation_id"], o["state"], o["evidence"]) for o in by_rule(rep, "r-rep.repetition")])
        self.assertEqual((rep["status"], rep["consistency"]), (base["status"], base["consistency"]))

    def test_v02_calibration_differs(self):
        for keep_id in (True, False):
            def cal(c, keep_id=keep_id):
                c.add("calibration", "cal-sel", "cal-sel.json", {"synthetic": "selection efficiency calibration"})
                c.context["recipe_instances"][0]["calibrations"] = {"efficiency": "cal-sel"}
                corr = c.doc("spec")["extension"]["corrections"][0]
                corr["calibration_digest"] = "f" * 64
                if not keep_id:
                    corr.pop("application_id")
            with self.subTest(application_id=keep_id):
                rep = self.pos(cal)
                o = get(rep, "r-real.description:selection_efficiency@proton-p1")
                self.assertEqual((o["state"], o["reason"]), ("violated", "check.description_conflict"))
                self.assertFalse([c for c in legacy_codes(rep) if "description" in c])

    def test_v09_parent_described_by_a_child(self):
        rep = self.pos()
        self.assertEqual(get(rep, "r-real.description:acceptance@proton-p1")["state"], "satisfied")
        self.assertEqual(get(rep, f"r-comp.composition:flux-proton-p1#{COMP}")["reason"], "check.composition_once")
        self.assertEqual(get(rep, "r-rep.repetition:flux-proton-p1#exposure")["state"], "satisfied")

    def test_v23_ambiguous_mapping(self):
        def two(c):
            recipe_of(c)["steps"].insert(3, {"step_id": "exposure2", "operator": "divide_effective_exposure"})
        o = get(self.pos(two), "r-real.description:acceptance@proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.ambiguous_application"))

    def test_v37_scopeless_correction_against_four_instances(self):
        def unmapped(c):
            c.context["declarations"] = []
        rep = self.chain(unmapped)
        reals = [o for o in by_rule(rep, "r-real.description") if o["reason"] != "check.realized_by_response"]
        self.assertEqual(len(reals), 12)
        self.assertEqual({o["reason"] for o in reals}, {"check.applicability_unbound"})
        mapped = self.chain()
        self.assertNotIn("check.applicability_unbound", {o["reason"] for o in by_rule(mapped, "r-real.description")})

    def test_v39_application_id_mismatch(self):
        def wrong_effect(c):
            c.doc("spec")["extension"]["corrections"][0]["application_id"] = "exposure"
        o = get(self.pos(wrong_effect), "r-real.description:selection_efficiency@proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.description_conflict"))

        def wrong_stage(c):
            corr = c.doc("spec")["extension"]["corrections"][1]
            corr.update(applied_in="estimator", application_id="exposure")
        rep = self.pos(wrong_stage)
        self.assertEqual(get(rep, "r-stage.position:acceptance@proton-p1")["reason"], "check.stage_conflict")
        self.assertEqual(get(rep, "r-real.description:acceptance@proton-p1")["state"], "satisfied")


@NEEDS_AMS
class Coverage(Tmp):
    def test_v35_effective_exposure(self):
        rep = self.chain()
        for m in ("trigger_efficiency", "selection_efficiency"):
            self.assertEqual(get(rep, f"r-real.description:{m}@proton-p1")["reason"], "check.coverage_undefined")
        from contracts.analysis_checks.rules import evaluate
        root = Path(self.td.name) / "listed"
        view, _ = ac().load_subject(cases.chain_case(root), root)
        op = next(o for o in view["coverage"]["differential-flux"]["doc"]["operators"]
                  if o["operator_id"] == "divide_effective_exposure")
        op["class_coverage"]["efficiency"] = {"members": ["trigger_efficiency", "selection_efficiency"], "basis": "synthetic"}
        out = {o["obligation_id"]: o for o in evaluate(view, view["context"]["obligations"]["items"])}
        for m in ("trigger_efficiency", "selection_efficiency"):
            self.assertEqual(out[f"r-real.description:{m}@proton-p1"]["state"], "satisfied")

    def test_v43_new_member(self):
        from contracts.analysis_checks.rules import evaluate

        def tracking(c):
            c.doc("spec")["extension"]["corrections"][0].update(effect_id="tracking_efficiency",
                                                                 category="tracking_efficiency")
            c.doc("spec")["extension"]["corrections"][0].pop("application_id")
        root = Path(self.td.name) / "new-member"
        view, _ = ac().load_subject(cases.positive_case(root, tracking), root)
        obligations = view["context"]["obligations"]["items"]
        before = {o["obligation_id"]: o for o in evaluate(view, obligations)}
        self.assertEqual(before["r-real.description:tracking_efficiency@proton-p1"]["state"], "unsupported")
        view["catalog"]["effects"].append({"effect_id": "tracking_efficiency", "class": "efficiency", "definition": "new"})
        next(c for c in view["catalog"]["classes"] if c["class_id"] == "efficiency")["members"].append("tracking_efficiency")
        after = {o["obligation_id"]: o for o in evaluate(view, obligations)}
        o = after["r-real.description:tracking_efficiency@proton-p1"]
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.unrealized_correction"))

    def test_v18_unsupported_operator(self):
        rep = self.pos(lambda c: custom_table(c, "differential-flux-y", None, None, drop_cov=("divide_bin_width",)))
        o = get(rep, "r-rep.repetition:flux-proton-p1#bin_width")
        self.assertEqual((o["state"], o["reason"]), ("unsupported", "check.unsupported_operator"))
        self.assertNotIn("semantics.unknown_operator", legacy_codes(rep))
        self.assertNotEqual(rep["status"], "complete")


@NEEDS_AMS
class Repetition(Tmp):
    def test_v03_same_slot_twice_on_one_path(self):
        rep = self.pos(lambda c: add_instance(c, "proton-p1-pre", "flux-pre", PRE_STEPS, feeds="proton-p1"))
        o = get(rep, "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.repeated_application"))
        self.assertEqual(rep["consistency"], "inconsistent")

    def test_v49_variation_rejoins(self):
        rep = self.pos(lambda c: add_instance(c, "proton-p1-alt", "flux-alt", PRE_STEPS, role="systematic",
                                              nominal="proton-p1", variation="alt", feeds="proton-p1"))
        self.assertEqual(get(rep, "r-rep.repetition:flux-proton-p1#efficiency")["reason"], "check.repeated_application")

    def test_v04_alternative_branches(self):
        def alternatives(c, role="alternative"):
            for k in ("a", "b"):
                add_instance(c, f"alt-{k}", f"flux-alt-{k}", copy.deepcopy(recipe_of(c)["steps"]), role=role,
                             nominal="proton-p1" if role != "nominal" else None, variation=f"alt-{k}",
                             estimand="differential_flux")
        rep = self.pos(alternatives)
        self.assertEqual({o["state"] for o in by_rule(rep, "r-rep.repetition") if "flux-proton-p1" in o["obligation_id"]},
                         {"satisfied"})
        unbound = self.pos(lambda c: alternatives(c, role="nominal"))
        self.assertEqual(get(unbound, "r-rep.repetition:flux-proton-p1#efficiency")["reason"], "check.branch_unbound")

    def regression(self, keys_a, keys_b):
        def variant(c):
            r = recipe_of(c)
            r["recipe_version"] = "1.1.0"
            r["steps"] = [{"step_id": "background", "operator": "subtract_background"},
                          dict({"step_id": "eff-a", "operator": "correct_efficiency"}, **({"effect_keys": keys_a} if keys_a else {})),
                          dict({"step_id": "eff-b", "operator": "correct_efficiency"}, **({"effect_keys": keys_b} if keys_b else {})),
                          {"step_id": "exposure", "operator": "divide_exposure"},
                          {"step_id": "bin-width", "operator": "divide_bin_width"}]
            c.doc("spec")["extension"]["corrections"][0].pop("application_id")
        return self.pos(variant)

    def test_v21_same_scope_two_calibrations(self):
        rep = self.regression(keyed(SCOPE, "a" * 64), keyed(SCOPE, "b" * 64))
        self.assertIn("semantics.repeated_correction", legacy_codes(rep))
        o = get(rep, "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.repeated_application"))

    def test_v22_incomplete_keys(self):
        rep = self.regression(keyed("species:proton"), None)
        self.assertIn("semantics.repeat_undetermined", legacy_codes(rep))
        o = get(rep, "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.keys_incomplete"))

    def test_v16_opaque_scope_strings(self):
        rep = self.regression(keyed("region-a"), keyed("region-b"))
        self.assertIn("semantics.repeat_distinct_instance", legacy_codes(rep))
        o = get(rep, "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.scope_relation_unknown"))

    def scoped_pair(self, declaration=None):
        def variant(c):
            c.context["recipe_instances"][0]["scope"] = "sel-b"
            c.context["roots"][0]["scope"] = "sel-b"
            add_instance(c, "pre", "flux-pre", PRE_STEPS, scope="sel-a", feeds="proton-p1")
            if declaration:
                c.context["declarations"].append(declaration)
        return self.pos(variant)

    def test_v40_no_basis_for_exclusion(self):
        o = get(self.scoped_pair(), "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.scope_relation_unknown"))

    def test_v41_declared_exclusion(self):
        def decl(sel_a, sel_b):
            return {"declaration_id": "excl", "type": "partition_exclusive", "asserted_by": dict(cases.AGENT),
                    "basis": {"rationale": "two charge windows of one dataset"},
                    "content": {"source": "spec", "subsets": [{"scope": "sel-a", "selection": sel_a},
                                                              {"scope": "sel-b", "selection": sel_b}]}}
        o = get(self.scoped_pair(decl("q-low", "q-high")), "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"], o["declaration_based"]), ("satisfied", "check.exclusive_scopes", True))
        o = get(self.scoped_pair(decl("q-window", "q-window")), "r-rep.repetition:flux-proton-p1#efficiency")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.exclusion_contradiction"))


@NEEDS_AMS
class Composition(Tmp):
    def test_v10_parent_and_decomposition(self):
        op = {"operator_id": "divide_acceptance", "input_kind": "counts", "output_kind": "counts", "applies": ["exposure"],
              "requires": ["background"], "forbids_after": [], "meaning": "synthetic: divide by the acceptance alone"}
        cov = {"operator_id": "divide_acceptance", "stage": "normalization", "covers": ["acceptance"], "class_coverage": {},
               "factors": [{"effect": "acceptance", "power": -1}]}

        def variant(c):
            custom_table(c, "differential-flux-x", op, cov)
            recipe_of(c)["steps"].insert(2, {"step_id": "acceptance", "operator": "divide_acceptance"})
            c.doc("spec")["extension"]["corrections"][1]["application_id"] = "exposure"
        o = get(self.pos(variant), f"r-comp.composition:flux-proton-p1#{COMP}")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.decomposition_double_counted"))

    def factors(self, broken=()):
        n = 400

        def variant(c):
            acc = [0.5 + 0.001 * k for k in range(n)]
            live = [1000.0 + k for k in range(n)]
            exp = [a * t for a, t in zip(acc, live)]
            for k in broken:
                exp[k] *= 1.01
            c.add("calibration", "factors", "factors.json", {"factor_table_version": "1.0.0", "tolerance": {"relative": 1e-9},
                  "factors": {"exposure": {"values": exp}, "acceptance": {"values": acc}, "livetime": {"values": live}}})
            c.context["recipe_instances"][0]["calibrations"] = {"exposure": "factors"}
        return self.pos(variant)

    def test_v69_factor_check_across_bins(self):
        o = get(self.factors(), f"r-comp.factor_values:proton-p1#{COMP}")
        self.assertEqual((o["state"], o["bins"]), ("satisfied", {"evaluated": 400, "failed": 0, "first_failures": []}))
        rep = self.factors(broken=(3, 50, 51, 300, 301, 302, 399))
        o = get(rep, f"r-comp.factor_values:proton-p1#{COMP}")
        self.assertEqual((o["state"], o["bins"]["failed"], o["bins"]["first_failures"]), ("violated", 7, [3, 50, 51, 300, 301]))
        self.assertEqual(len([x for x in rep["obligations"] if x["rule_id"] == "r-comp.factor_values"]), 1)
        self.assertLess(len(json.dumps(o)), 1500)
        self.assertNotIn("1000.0", json.dumps(rep["obligations"]))


@NEEDS_AMS
class ResponseUse(Tmp):
    def test_v34_unfolding_against_not_applied(self):
        def unfolding(c):
            corr = next(x for x in c.doc("spec")["extension"]["corrections"] if x["category"] == "migration")
            corr["applied_in"] = "unfolding"
        rep = self.chain(unfolding)
        o = get(rep, "r-resp.response_use:proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.response_use_conflict"))
        self.assertEqual(rep["consistency"], "inconsistent")

    def test_v48_not_applied_only(self):
        o = get(self.chain(), "r-resp.response_use:proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.response_use_unbound"))

        def folded(c):
            c.context["bindings"].append({"binding_id": "fold", "type": "response_used_by",
                                          "from": {"item": "response-proton-p1"}, "to": {"prediction": "dataset-p1"}})
        o = get(self.chain(folded), "r-resp.response_use:proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("unsupported", "check.folding_unsupported"))

    def unfold_recipe(self, c, bind):
        r = c.doc("flux-from-counts")
        r["steps"] = [{"step_id": "background", "operator": "subtract_background"},
                      {"step_id": "unfold", "operator": "unfold"},
                      {"step_id": "exposure", "operator": "divide_effective_exposure"},
                      {"step_id": "bin-width", "operator": "divide_bin_width"}]
        r["not_applied"] = []
        if bind:
            for s in cases.SPECIES:
                for p in cases.PERIODS:
                    iid = f"{s}-{cases.SHORT[p]}"
                    c.context["bindings"].append({"binding_id": f"resp-{iid}", "type": "response_used_by",
                                                  "from": {"item": f"response-{iid}"}, "to": {"instance": iid, "step": "unfold"}})

    def test_v11_missing_response_binding(self):
        rep = self.chain(lambda c: self.unfold_recipe(c, bind=False))
        o = get(rep, "r-resp.response_use:proton-p1")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.response_use_unbound"))
        self.assertEqual(rep["coverage"]["value"], "partial")
        bound = self.chain(lambda c: self.unfold_recipe(c, bind=True))
        self.assertEqual(get(bound, "r-resp.response_use:proton-p1")["state"], "satisfied")

    def test_v12_response_not_needed(self):
        def no_migration(c):
            spec = c.doc("spec")
            spec["extension"]["corrections"] = [x for x in spec["extension"]["corrections"] if x["category"] != "migration"]
            c.context["declarations"] = [d for d in c.context["declarations"] if d["content"]["correction"] != "rigidity_migration"]
            for it in [i for i in c.items if i["role"] == "response"]:
                c.remove(it["id"])
        rep = self.chain(no_migration)
        self.assertEqual({(o["state"], o["reason"]) for o in by_rule(rep, "r-resp.response_use")},
                         {("not_applicable", "check.response_not_needed")})
        self.assertEqual({o["state"] for o in by_rule(self.chain(), "r-resp.response_use")}, {"unverified"})


@NEEDS_AMS
class DeclarationFlags(Tmp):
    def test_v64_declaration_based(self):
        rep = self.chain()
        o = get(rep, "r-real.description:acceptance@proton-p1")
        self.assertEqual((o["state"], o["declaration_based"], o["declarations"]), ("satisfied", True, ["map-acceptance"]))
        flagged = sum(x["declaration_based"] for x in rep["obligations"])
        self.assertGreater(flagged, 0)
        self.assertEqual(rep["formal_use_view"]["counts"]["satisfied"], rep["counts"]["satisfied"] - flagged)
        self.assertIn({"declaration_id": "map-acceptance", "type": "instance_mapping", "asserted_by": cases.AGENT},
                      rep["declarations"])
        self.assertFalse(any(x["declaration_based"] for x in self.pos()["obligations"]))


class ReasonCodes(unittest.TestCase):
    """Every reason code a chain rule can return is registered for that rule and state (D12a outcome contract)."""

    def test_codes_are_registered(self):
        import ast
        import inspect
        from contracts.analysis_checks import rules
        registry = {r["rule_id"]: r for r in json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text())["rules"]}
        helpers = {"_pair": "r-rep.repetition"}
        for rule_id, fn in list(rules.RULES.items()) + [(v, getattr(rules, k)) for k, v in helpers.items()]:
            contract = registry[rule_id]["outcome_contract"]
            for node in ast.walk(ast.parse(inspect.getsource(fn))):
                consts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
                if isinstance(node, (ast.Call, ast.Return, ast.Tuple)) and len(consts) >= 2:
                    for state, code in zip(consts, consts[1:]):
                        if state in contract and code.startswith("check."):
                            with self.subTest(rule=rule_id, code=code):
                                self.assertIn(code, contract[state])


if __name__ == "__main__":
    unittest.main()
