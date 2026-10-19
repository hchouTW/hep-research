"""communication_lib.reporting (plan T5): conditional reporting policies per result type check supplied method
metadata; they never choose a method or invent a default. All synthetic."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-writing" / "scripts"
sys.path.insert(0, str(SCRIPTS))
POLICY = SCRIPTS.parent / "assets" / "reporting-policies.json"

try:
    from communication_lib.reporting import check_reporting, load_policy
except ImportError:
    check_reporting = load_policy = None


def ctx(result_type, method=None, **fields):
    return {"result_type": result_type, "method": method or {}, "fields": {k: (v if isinstance(v, dict) else {"state": "provided", "value": v})
                                                                           for k, v in fields.items()}}


def codes(findings, severity=None):
    return {f["code"] for f in findings if severity is None or f["severity"] == severity}


class PolicyFile(unittest.TestCase):
    def test_policy_file_loads_and_covers_the_result_types(self):
        self.assertIsNotNone(load_policy, "communication_lib.reporting does not exist")
        pol = load_policy(POLICY)
        self.assertEqual(pol["policy_version"], "1.2.0")  # Com2: five add-only flux-measurement fields
        self.assertEqual(set(pol["result_types"]), {"measurement", "search", "limit", "theory-prediction", "ml-result", "flux-measurement"})
        schema = json.loads((POLICY.parents[3] / "contracts" / "schemas" / "ext_communication_traceability.json").read_text(encoding="utf-8"))
        enum = schema["$defs"]["reporting_context"]["properties"]["result_type"]["enum"]
        self.assertEqual(set(enum), set(pol["result_types"]), "every policy result type is a contract result type")
        for rt, spec in pol["result_types"].items():
            for name, field in spec["fields"].items():
                self.assertIn("description", field, (rt, name))


class Measurement(unittest.TestCase):
    def setUp(self):
        self.pol = load_policy(POLICY)

    def test_complete_measurement_passes(self):
        r = check_reporting(ctx("measurement", {"uncertainty_split": "stat+syst"}, value="1.02", unit="1",
                                uncertainty_definition="68% interval", statistical_uncertainty="0.05", systematic_uncertainty="0.03",
                                scope="fixture", corrections_applied="none"), self.pol)
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["fields"]["unit"]["state"], "provided")

    def test_missing_unit_and_scope_are_unresolved_not_defaulted(self):
        r = check_reporting(ctx("measurement", {}, value="1.02", uncertainty_definition="68%", statistical_uncertainty="0.05",
                                systematic_uncertainty={"state": "not-applicable", "reason": "stat only"}, corrections_applied="none"), self.pol)
        missing = {f["location"] for f in r["findings"] if f["code"] == "reporting.field_missing"}
        self.assertEqual(missing, {"fields.unit", "fields.scope"})
        self.assertTrue(all(f["severity"] == "unresolved" for f in r["findings"]))
        self.assertNotIn("value", json.dumps([f.get("default") for f in r["findings"]]))

    def test_not_applicable_needs_a_reason(self):
        r = check_reporting(ctx("measurement", {}, value="1.02", unit="1", uncertainty_definition="68%", statistical_uncertainty="0.05",
                                systematic_uncertainty={"state": "not-applicable"}, scope="x", corrections_applied="none"), self.pol)
        self.assertIn("reporting.not_applicable_without_reason", codes(r["findings"], "error"))

    def test_unknown_result_type_is_an_error(self):
        r = check_reporting(ctx("anomaly"), self.pol)
        self.assertIn("reporting.unknown_result_type", codes(r["findings"], "error"))


class Limits(unittest.TestCase):
    def setUp(self):
        self.pol = load_policy(POLICY)

    def test_expected_limit_does_not_imply_asimov(self):
        base = dict(cl="0.95", construction="CLs", observed_limit="2.1", unit="pb", scope="fixture")
        r = check_reporting(ctx("limit", {"expected_reported": True}, **base, expected_limit="1.8"), self.pol)
        self.assertIn("fields.expected_bands", {f["location"] for f in r["findings"] if f["code"] == "reporting.field_missing"})
        self.assertIn("fields.expected_construction", {f["location"] for f in r["findings"] if f["code"] == "reporting.field_missing"})
        r = check_reporting(ctx("limit", {"expected_reported": True}, **base, expected_limit="1.8", expected_bands="[1.3, 2.5]",
                                expected_construction="toys"), self.pol)
        self.assertEqual(r["findings"], [])

    def test_applicability_unknown_is_unresolved_not_missing(self):
        r = check_reporting(ctx("limit", {}, cl="0.95", construction="CLs", observed_limit="2.1", unit="pb", scope="fixture"), self.pol)
        self.assertEqual(r["fields"]["expected_bands"]["state"], "unresolved")
        self.assertIn("reporting.applicability_unknown", codes(r["findings"], "unresolved"))
        self.assertNotIn("reporting.field_missing", codes(r["findings"]))

    def test_bayesian_interval_does_not_need_a_frequentist_construction(self):
        r = check_reporting(ctx("limit", {"paradigm": "bayesian", "expected_reported": False}, credible_level="0.95", prior="flat in mu",
                                observed_limit="2.1", unit="pb", scope="fixture"), self.pol)
        self.assertEqual(r["findings"], [], r["findings"])
        r = check_reporting(ctx("limit", {"paradigm": "bayesian", "expected_reported": False}, cl="0.95", construction="CLs",
                                observed_limit="2.1", unit="pb", scope="fixture"), self.pol)
        self.assertIn("reporting.interval_kind_mismatch", codes(r["findings"], "error"))


class Searches(unittest.TestCase):
    def setUp(self):
        self.pol = load_policy(POLICY)

    def test_scan_needs_global_significance_and_trials_method(self):
        r = check_reporting(ctx("search", {"scan": True}, local_significance="3.4", expected_significance="2.9",
                                observed_vs_expected="stated", scope="fixture"), self.pol)
        self.assertEqual({f["location"] for f in r["findings"] if f["code"] == "reporting.field_missing"},
                         {"fields.global_significance", "fields.trials_method"})
        r = check_reporting(ctx("search", {"scan": False}, local_significance="3.4", expected_significance="2.9",
                                observed_vs_expected="stated", scope="fixture"), self.pol)
        self.assertEqual(r["findings"], [])

    def test_observed_expected_and_stat_syst_distinctions(self):
        r = check_reporting(ctx("search", {"scan": False}, local_significance="3.4", scope="fixture"), self.pol)
        self.assertIn("fields.observed_vs_expected", {f["location"] for f in r["findings"]})
        r = check_reporting(ctx("measurement", {"uncertainty_split": "stat+syst"}, value="1", unit="1", uncertainty_definition="68%",
                                statistical_uncertainty="0.05", scope="x", corrections_applied="none"), self.pol)
        self.assertIn("fields.systematic_uncertainty", {f["location"] for f in r["findings"]})


class TheoryAndMl(unittest.TestCase):
    def setUp(self):
        self.pol = load_policy(POLICY)

    def test_theory_prediction_fields(self):
        r = check_reporting(ctx("theory-prediction", {"hadronic": False}, order="NLO", scale_choice="mu = m", scale_uncertainty="envelope",
                                validity_domain="x", unit="pb"), self.pol)
        self.assertEqual(r["findings"], [])
        r = check_reporting(ctx("theory-prediction", {"hadronic": True}, order="NLO", scale_choice="mu = m", scale_uncertainty="envelope",
                                validity_domain="x", unit="pb"), self.pol)
        self.assertIn("fields.pdf_set", {f["location"] for f in r["findings"]})

    def test_ml_result_fields(self):
        r = check_reporting(ctx("ml-result", {}, metric_definition="AUC", evaluation_split="grouped by run", seed_variance="5 seeds",
                                baseline="BDT", training_domain="x"), self.pol)
        self.assertEqual(r["findings"], [])
        r = check_reporting(ctx("ml-result", {}, metric_definition="AUC"), self.pol)
        self.assertGreaterEqual(len(r["findings"]), 4)


if __name__ == "__main__":
    unittest.main()
