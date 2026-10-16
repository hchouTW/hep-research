"""v6.3 D12a: the rule and obligation registry. The shipped registry validates; a new or changed rule without reason
codes for all five states is rejected while a legacy rule may stay 'pending' (and then evaluates as unverified);
prerequisites and V-case references are checked; a V case claimed as running names an existing test; impact closure
maps paths to existing checks and falls back to the full closure for unmatched paths, not-available checks and full
groups. The checker runs in the static part of the gate."""
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
from contracts import rule_registry as rr  # noqa: E402

SHIPPED = json.loads(rr.REGISTRY.read_text(encoding="utf-8"))
FULL_CONTRACT = {"satisfied": ["x.ok"], "violated": ["x.bad"], "not_applicable": ["x.no_subject"],
                 "unverified": ["x.missing_input"], "unsupported": ["x.unknown_operator"]}


def new_rule(**kw):
    rule = {"rule_id": "l3.example", "version": "1.0.0", "layer": "L3", "suites": ["counting-chain/v1"], "kind": "new",
            "prerequisites": ["a bound response"], "applicability": "every unfolding step", "outcome_contract":
            copy.deepcopy(FULL_CONTRACT), "legacy_codes": [], "native_from": None, "v_cases": ["V34"], "waivable": False,
            "accepted_applicability_facts": [], "owner": "hep-measurement", "review_status": "unreviewed",
            "lifecycle": "proposed"}
    rule.update(kw)
    return rule


def with_rule(rule):
    doc = copy.deepcopy(SHIPPED)
    doc["rules"].append(rule)
    return doc


def codes(rep):
    return {f.code for f in rep.findings if f.severity == "error"}


def cli(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = rr.main([str(a) for a in argv])
    return code, json.loads(buf.getvalue())


class ShippedRegistry(unittest.TestCase):
    def test_validates(self):
        rep = rr.check(SHIPPED)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])

    def test_catalogue_and_first_entries(self):
        self.assertEqual([c["v_id"] for c in SHIPPED["v_cases"]], [f"V{i:02d}" for i in range(1, 72)])
        statuses = {p["status"] for c in SHIPPED["v_cases"] for p in c["parts"]}
        self.assertLessEqual(statuses, {"not-run", "expected-failure", "required-before-enforcement", "passing"})
        r4 = {r["rule_id"]: r for r in SHIPPED["rules"]}
        self.assertEqual(set(r4), {"l2.r4.repeat", "l2.r4.upstream", "l2.r4.keys"})
        self.assertEqual({r["outcome_contract"] for r in r4.values()}, {"pending"})
        self.assertIn("semantics.repeated_correction", r4["l2.r4.repeat"]["legacy_codes"])

    def test_split_cases_keep_their_slices(self):
        v11 = next(c for c in SHIPPED["v_cases"] if c["v_id"] == "V11")
        self.assertEqual([(p["slice"], p["suite"], p["work_packages"]) for p in v11["parts"]],
                         [("M2a", "chain", ["D05b", "D05c"]), ("M2b", "model", ["D07"])])

    def test_cli_check_passes(self):
        code, out = cli("check")
        self.assertEqual((code, out["status"]), (0, "pass"))
        self.assertEqual(out["counts"]["v_cases"], 71)

    def test_wired_into_the_static_gate(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import run_all_checks
        self.assertIn(("rule_registry", ["contracts/rule_registry.py", "check"]), run_all_checks.STATIC_SCRIPTS)


class OutcomeContract(unittest.TestCase):
    def test_complete_new_rule_is_accepted(self):
        self.assertTrue(rr.check(with_rule(new_rule())).ok)

    def test_new_or_changed_rule_without_a_state_is_rejected(self):
        for kind in ("new", "changed"):
            for state in rr.STATES:
                with self.subTest(kind=kind, state=state):
                    oc = copy.deepcopy(FULL_CONTRACT)
                    oc[state] = []
                    self.assertIn("registry.outcome_contract_incomplete",
                                  codes(rr.check(with_rule(new_rule(kind=kind, outcome_contract=oc)))))

    def test_new_rule_cannot_be_pending(self):
        self.assertIn("registry.outcome_contract_incomplete",
                      codes(rr.check(with_rule(new_rule(outcome_contract="pending")))))

    def test_a_code_in_two_states_is_rejected(self):
        oc = copy.deepcopy(FULL_CONTRACT)
        oc["unverified"].append("x.ok")
        self.assertIn("registry.outcome_code_ambiguous", codes(rr.check(with_rule(new_rule(outcome_contract=oc)))))

    def test_legacy_pending_is_accepted_and_unverified(self):
        legacy = next(r for r in SHIPPED["rules"] if r["rule_id"] == "l2.r4.repeat")
        for code in ("semantics.repeated_correction", "anything", None):
            self.assertEqual(rr.state_for(legacy, code), "unverified")

    def test_state_for_maps_codes_and_never_assumes_satisfied(self):
        rule = new_rule()
        for state, cs in FULL_CONTRACT.items():
            self.assertEqual(rr.state_for(rule, cs[0]), state)
        self.assertEqual(rr.state_for(rule, None), "unverified")
        self.assertEqual(rr.state_for(rule, "x.something_else"), "unverified")

    def test_legacy_rule_cannot_be_enforcing(self):
        self.assertIn("registry.legacy_lifecycle",
                      codes(rr.check(with_rule(new_rule(kind="legacy", outcome_contract="pending", suites=[],
                                                        lifecycle="enforcing")))))

    def test_new_rule_names_a_suite(self):
        self.assertIn("registry.suite_missing", codes(rr.check(with_rule(new_rule(suites=[])))))


class Prerequisites(unittest.TestCase):
    def test_prerequisites_are_required(self):
        self.assertIn("registry.prerequisites_missing", codes(rr.check(with_rule(new_rule(prerequisites=[])))))

    def test_unknown_v_case_is_rejected(self):
        self.assertIn("registry.unknown_v_case", codes(rr.check(with_rule(new_rule(v_cases=["V99"])))))

    def test_running_v_case_needs_an_existing_test(self):
        doc = copy.deepcopy(SHIPPED)
        part = doc["v_cases"][33]["parts"][0]
        part["status"] = "passing"
        self.assertIn("registry.v_case_without_test", codes(rr.check(doc)))
        part["tests"] = ["tests.contracts.test_v63_rule_registry.Prerequisites.test_absent"]
        self.assertIn("registry.test_missing", codes(rr.check(doc)))
        part["tests"] = ["tests.contracts.test_v63_rule_registry.Prerequisites.test_prerequisites_are_required"]
        self.assertTrue(rr.check(doc).ok)

    def test_duplicates_and_gaps(self):
        doc = copy.deepcopy(SHIPPED)
        doc["v_cases"].append(copy.deepcopy(doc["v_cases"][0]))
        doc["rules"].append(copy.deepcopy(doc["rules"][0]))
        del doc["v_cases"][5]
        found = codes(rr.check(doc))
        self.assertTrue({"registry.duplicate_v_case", "registry.duplicate_rule", "registry.v_case_gap"} <= found)

    def test_schema_errors_stop_the_check(self):
        doc = copy.deepcopy(SHIPPED)
        doc["rules"][0]["layer"] = "L4"
        self.assertIn("schema.enum", codes(rr.check(doc)))


class ImpactClosure(unittest.TestCase):
    def test_a_bounded_change(self):
        out = rr.impact(["core/evidence/query.py"], SHIPPED)
        self.assertFalse(out["full"])
        self.assertIn("tests.core.test_v63_evidence_query", out["modules"])
        self.assertEqual(out["parts"], [])

    def test_every_listed_module_exists(self):
        mods = {c for g in SHIPPED["impact"] for c in g["checks"] if c.startswith("tests.")}
        for m in mods:
            self.assertTrue((ROOT / Path(*m.split("."))).with_suffix(".py").is_file(), m)

    def test_not_available_forces_the_full_closure(self):
        out = rr.impact(["contracts/recipe_semantics.py"], SHIPPED)
        self.assertTrue(out["full"])
        self.assertEqual(out["parts"], ["all"])
        self.assertIn("tests.contracts.test_recipe_semantics", out["modules"])
        self.assertTrue(any(r.startswith("not available: catalog-operators") for r in out["reasons"]))

    def test_unmatched_path_falls_back(self):
        out = rr.impact(["tools/some_new_tool.py"], SHIPPED)
        self.assertTrue(out["full"])
        self.assertEqual(out["unmatched"], ["tools/some_new_tool.py"])

    def test_full_group(self):
        out = rr.impact(["contracts/schemas/recipe.json"], SHIPPED)
        self.assertTrue(out["full"])
        self.assertIn("shared-schemas-readers", out["groups"])

    def test_a_changed_test_module_runs_itself(self):
        out = rr.impact(["tests/contracts/test_permits.py"], SHIPPED)
        self.assertEqual((out["full"], out["modules"]), (False, ["tests.contracts.test_permits"]))

    def test_no_paths_cannot_be_bounded(self):
        self.assertTrue(rr.impact([], SHIPPED)["full"])

    def test_cli(self):
        code, out = cli("impact", "core/evidence/query.py", "./core/evidence/ledger.py")
        self.assertEqual((code, out["status"], out["full"]), (0, "ok", False))
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "r.json"
            bad.write_text(json.dumps(with_rule(new_rule(prerequisites=[]))))
            code, out = cli("check", "--registry", bad)
            self.assertEqual((code, out["status"]), (1, "fail"))
            code, out = cli("impact", "core/evidence/query.py", "--registry", bad)
            self.assertEqual((code, out["full"]), (2, True))
            bad.write_text("{")
            code, out = cli("check", "--registry", bad)
            self.assertEqual((code, out["status"]), (2, "unreadable"))


if __name__ == "__main__":
    unittest.main()
