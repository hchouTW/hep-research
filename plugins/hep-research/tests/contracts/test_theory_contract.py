"""theory-spec and prediction semantics (hep-theory audit 2026-10-13, THY-WP2 and WP4.3).

The audit found that contracts/validate.py checked only experiment fields, auto-Gaussian uncertainties and the payload
of a theory-spec or prediction: none of the hep-theory invariants (conventions block, order of a perturbative
argument, limit of an asymptotic one, checks behind a strong status, a validity domain, a linked theory spec, an
envelope prescription, a truncation method) was checked. Contracts 2.6.0 add optional fields for them; the rules are
native from 2.6.0, and an older artifact keeps its outcome unless --strict. All fixtures SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
THEORY_1_0 = json.loads((ART / "valid" / "theory_spec.json").read_text())
PREDICTION_1_0 = json.loads((ART / "valid" / "prediction.json").read_text())


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


class SchemaFieldTests(unittest.TestCase):
    """THY-WP2.1: optional fields only; their types are checked, their absence is not."""

    def test_new_theory_spec_fields_are_accepted(self):
        doc = copy.deepcopy(THEORY_1_0)
        doc["extension"].update(limit="m_e / sqrt(s) -> 0", neglected=["Z exchange"], computational_run_ref="run.json",
                                degenerate_directions=["D0/L"])
        doc["extension"]["model"]["family"] = "synthetic-family"
        doc["extension"]["checks_run"] = [{"name": "units", "result": "pass", "tolerance": 1e-12},
                                          {"name": "limit", "result": "pass", "tolerance": "exact"}]
        doc["extension"]["references_read"] = [{"citation": "synthetic", "location": "eq. 1", "date_read": "2026-10-13"}]
        rep = v.validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse(codes(rep))

    def test_new_field_types_are_checked(self):
        for field, value in (("limit", 3), ("neglected", "Z exchange"), ("computational_run_ref", {}),
                             ("degenerate_directions", "D0/L")):
            with self.subTest(field=field):
                doc = copy.deepcopy(THEORY_1_0)
                doc["extension"][field] = value
                self.assertIn("schema.type", codes(v.validate_artifact(doc)))
        doc = copy.deepcopy(THEORY_1_0)
        doc["extension"]["checks_run"] = [{"name": "units", "result": "pass", "tolerance": [1]}]
        self.assertFalse(v.validate_artifact(doc).ok)

    def test_new_prediction_and_uncertainty_fields(self):
        doc = copy.deepcopy(PREDICTION_1_0)
        doc["extension"]["derivation_status"] = "perturbative-argument"
        doc["extension"]["uncertainties"][0].update(prescription="7-point", values=[0.9, 1.1])
        doc["extension"]["uncertainties"].append({"name": "mho", "kind": "truncation", "correlation": "unknown",
                                                  "method": "last-term"})
        rep = v.validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        doc["extension"]["derivation_status"] = "proved"
        self.assertIn("vocab.unknown_term", codes(v.validate_artifact(doc)))


CORE_KEYS = ["unit_system", "hbar_c_one", "metric_signature", "coupling_normalization", "renormalization_scheme",
             "scales", "energy_variable", "frame", "angle_definition", "spin_treatment", "mass_approximation"]


def stamp(doc, version):
    doc = copy.deepcopy(doc)
    doc["contract_version"] = version
    doc["versions"]["contracts"] = version
    return doc


def theory_base(version="2.6.0"):
    """The 1.0.0 fixture completed so that every 2.6.0 rule is satisfied."""
    doc = stamp(THEORY_1_0, version)
    ext = doc["extension"]
    ext["conventions"] = {k: ext["conventions"].get(k, "not-applicable") for k in CORE_KEYS}
    ext.update(derivation_status="perturbative-argument", order="tree-level",
               checks_run=[{"name": "units", "result": "pass", "tolerance": "exact"}])
    return doc


def prediction_base(version="2.6.0"):
    doc = stamp(PREDICTION_1_0, version)
    ext = doc["extension"]
    ext["theory_spec_ref"] = "artifacts/theory_spec.json"
    ext["uncertainties"] = [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown", "prescription": "3-point",
                             "values": [0.9, 1.1]},
                            {"name": "mho", "kind": "truncation", "correlation": "unknown", "method": "last-term"}]
    return doc


def _ext(f):
    def g(doc):
        f(doc["extension"])
    return g


# name -> (base, mutation of the document, level, code)
MUTATIONS = {
    "pred_observed": ("prediction", lambda d: d.update(status=["observed"]), "error", "prediction.status_upgraded"),
    "pred_validated_unsupported": ("prediction", lambda d: d.update(status=["validated-in-scope"]), "error",
                                   "prediction.status_upgraded"),
    "pred_validated_wrong_input": ("prediction", lambda d: d.update(
        status=["validated-in-scope"], inputs=[{"ref": "other.json", "artifact_type": "theory-spec",
                                                "status": ["validated-in-scope"]}]), "error", "prediction.status_upgraded"),
    "pred_unlinked": ("prediction", _ext(lambda e: e.pop("theory_spec_ref")), "unresolved", "prediction.spec_unlinked"),
    "pred_envelope_no_prescription": ("prediction", _ext(lambda e: e["uncertainties"][0].pop("prescription")), "error",
                                      "prediction.envelope_prescription"),
    "pred_envelope_unknown_prescription": ("prediction", _ext(lambda e: e["uncertainties"][0].update(prescription="max")),
                                           "error", "prediction.envelope_prescription"),
    "pred_envelope_inverted": ("prediction", _ext(lambda e: e["uncertainties"][0].update(values=[1.1, 0.9])), "error",
                               "prediction.envelope_prescription"),
    "pred_envelope_not_a_pair": ("prediction", _ext(lambda e: e["uncertainties"][0].update(values=[0.9, 1.0, 1.1, 1.2])),
                                 "error", "prediction.envelope_prescription"),
    "pred_envelope_bounds_short": ("prediction", _ext(lambda e: (e["uncertainties"][0].pop("values"), e["uncertainties"][0].update(
        bounds={"lower": [0.9, 0.9], "upper": [1.1, 1.1]}))), "error", "prediction.envelope_prescription"),
    "pred_truncation_no_method": ("prediction", _ext(lambda e: e["uncertainties"][1].pop("method")), "warning",
                                  "prediction.truncation_method"),
    "ts_conventions_incomplete": ("theory", _ext(lambda e: e["conventions"].pop("frame")), "warning",
                                  "theory.conventions_incomplete"),
    "ts_conventions_blank": ("theory", _ext(lambda e: e["conventions"].update(frame=" ")), "warning",
                             "theory.conventions_incomplete"),
    "ts_order_missing": ("theory", _ext(lambda e: e.update(order=" ")), "error", "theory.order_missing"),
    "ts_limit_missing": ("theory", _ext(lambda e: e.update(derivation_status="asymptotic-argument")), "error",
                         "theory.limit_missing"),
    "ts_formal_proof_unchecked": ("theory", _ext(lambda e: e.update(derivation_status="formal-proof", checks_run=[])),
                                  "error", "theory.unchecked_strong_status"),
    "ts_analytic_unchecked": ("theory", _ext(lambda e: e.update(derivation_status="analytic-derivation", checks_run=[])),
                              "error", "theory.unchecked_strong_status"),
    "ts_check_result_vocab": ("theory", _ext(lambda e: e["checks_run"].append({"name": "limits", "result": "looks fine"})),
                              "error", "theory.check_result_vocab"),
    "ts_validity_empty": ("theory", _ext(lambda e: e.update(validity_domain={})), "error", "theory.validity_empty"),
    "ts_degeneracy_missing": ("theory", _ext(lambda e: e["model"].update(family="cosmic-ray-propagation")), "error",
                              "theory.degeneracy_missing"),
    "ts_degeneracy_blank": ("theory", _ext(lambda e: (e["model"].update(family="cosmic-ray-propagation"),
                                                      e.update(degenerate_directions=[" "]))), "error",
                            "theory.degeneracy_missing"),
}


def mutated(name, version="2.6.0"):
    base, f, _, _ = MUTATIONS[name]
    doc = theory_base(version) if base == "theory" else prediction_base(version)
    f(doc)
    return doc


class NativeRuleTests(unittest.TestCase):
    """THY-WP2.2 and WP4.3: the rules fire natively on a 2.6.0 artifact, each at its level."""

    def test_complete_bases_have_no_findings_from_the_new_rules(self):
        for doc in (theory_base(), prediction_base()):
            rep = v.validate_artifact(doc)
            self.assertTrue(rep.ok, rep.as_dict())
            self.assertFalse({f.code for f in rep.findings if f.code.startswith(("theory.", "prediction."))}, rep.as_dict())

    def test_each_mutation_is_reported_natively_at_its_level(self):
        for name, (_, _, level, code) in MUTATIONS.items():
            with self.subTest(name):
                rep = v.validate_artifact(mutated(name))
                self.assertIn(code, codes(rep, level), rep.as_dict())
                self.assertEqual(rep.ok, level != "error")

    def test_positive_forms(self):
        ok = []
        d = prediction_base(); d.update(status=["validated-in-scope"], inputs=[
            {"ref": "artifacts/theory_spec.json", "artifact_type": "theory-spec", "status": ["validated-in-scope"]}])
        ok.append(("validated with linked spec", d))
        d = prediction_base(); d["extension"].pop("theory_spec_ref"); d["extension"]["derivation_status"] = "numerical-evidence"
        ok.append(("derivation_status instead of a ref", d))
        d = prediction_base(); d["extension"]["uncertainties"][0].pop("values")
        ok.append(("envelope without values", d))
        d = prediction_base(); d["extension"]["uncertainties"][0].pop("values")
        d["extension"]["uncertainties"][0]["bounds"] = {"lower": [0.9] * 4, "upper": [1.1] * 4}
        ok.append(("binned envelope bounds", d))
        d = prediction_base(); d["extension"]["uncertainties"][0]["prescription"] = "synthetic-collider:custom"
        ok.append(("namespaced prescription", d))
        d = theory_base(); d["extension"]["conventions"].pop("frame"); d["extension"]["inapplicable"] = ["frame"]
        ok.append(("key listed in inapplicable", d))
        d = theory_base(); d["extension"].update(derivation_status="asymptotic-argument", limit="m_e -> 0")
        ok.append(("asymptotic with limit", d))
        d = theory_base(); d["extension"]["model"]["family"] = "cosmic-ray-propagation"
        d["extension"]["degenerate_directions"] = ["D0/L"]
        ok.append(("propagation model with degeneracies", d))
        d = theory_base(); d["extension"]["model"]["id"] = "cosmic-ray-propagation-diffusion"
        ok.append(("trigger is model.family, not model.id (Q10)", d))
        for name, doc in ok:
            with self.subTest(name):
                rep = v.validate_artifact(doc)
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertFalse({f.code for f in rep.findings if f.code.startswith(("theory.", "prediction."))},
                                 rep.as_dict())

    def test_conventions_rule_stays_a_warning_under_strict(self):
        """Q2: --strict applies newer rules to older artifacts at the same level; it never raises a level."""
        for version in ("2.6.0", "2.5.0"):
            rep = v.validate_artifact(mutated("ts_conventions_incomplete", version), strict=True)
            self.assertIn("theory.conventions_incomplete", codes(rep, "warning"))
            self.assertTrue(rep.ok)


class FixtureTests(unittest.TestCase):
    """THY-WP2.3: generated fixtures (tests/contracts/make_fixtures.py) cover every rule with a negative and a positive."""
    CASES = json.loads((ART / "cases.json").read_text())
    RULES = {"prediction.status_upgraded", "theory.conventions_incomplete", "theory.order_missing", "theory.limit_missing",
             "theory.unchecked_strong_status", "theory.check_result_vocab", "theory.validity_empty",
             "prediction.spec_unlinked", "prediction.envelope_prescription", "prediction.truncation_method",
             "theory.degeneracy_missing", "theory.degeneracy_evidence_missing", "theory.degeneracy_range_missing",
             "theory.degeneracy_evidence_unknown", "theory.transport_break_incomplete",
             "theory.transport_break_kind_unknown"}

    def test_warning_fixtures_are_valid_and_warn(self):
        self.assertTrue(self.CASES["warning"])
        for name, expected in self.CASES["warning"].items():
            with self.subTest(name):
                rep = v.validate_artifact(json.loads((ART / "warning" / name).read_text()))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertTrue(set(expected) <= codes(rep, "warning"), rep.as_dict())

    def test_every_rule_has_a_negative_fixture(self):
        covered = set()
        for group in ("invalid", "unresolved", "warning"):
            for codes_ in self.CASES[group].values():
                covered |= set(codes_)
        self.assertEqual(self.RULES - covered, set())

    def test_positive_v26_fixtures_have_no_theory_findings(self):
        names = [n for n in self.CASES["valid"] if n.startswith(("theory_spec_v26", "prediction_v26"))]
        self.assertGreaterEqual(len(names), 8)
        for name in names:
            with self.subTest(name):
                rep = v.validate_artifact(json.loads((ART / "valid" / name).read_text()))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertFalse({f.code for f in rep.findings if f.code.startswith(("theory.", "prediction."))},
                                 rep.as_dict())

    def test_legacy_valid_fixtures_are_complete(self):
        """valid/theory_spec.json lists every core convention key; valid/prediction.json names its envelope prescription;
        both stay 1.0.0."""
        self.assertEqual(THEORY_1_0["contract_version"], "1.0.0")
        self.assertEqual(sorted(THEORY_1_0["extension"]["conventions"]), sorted(CORE_KEYS))
        self.assertEqual(PREDICTION_1_0["extension"]["uncertainties"][0]["prescription"], "3-point")
        for doc in (THEORY_1_0, PREDICTION_1_0):
            strict = v.validate_artifact(copy.deepcopy(doc), strict=True)
            self.assertTrue(strict.ok, strict.as_dict())


def audit_copies():
    """The six reproductions of the audit (fixture copies at contract 2.5.0), rebuilt here, with the codes expected at
    2.6.0 (or under --strict)."""
    out = {}
    d = stamp(PREDICTION_1_0, "2.5.0"); d["status"] = ["observed"]
    out["pred_observed"] = (d, {"prediction.status_upgraded"})
    d = stamp(PREDICTION_1_0, "2.5.0"); d["extension"]["uncertainties"][0].pop("prescription", None)
    d["extension"]["uncertainties"][0]["values"] = [1.2, 0.8, 1.0]
    out["pred_envelope"] = (d, {"prediction.envelope_prescription"})
    d = stamp(PREDICTION_1_0, "2.5.0")
    out["pred_unlinked"] = (d, {"prediction.spec_unlinked"})
    d = stamp(THEORY_1_0, "2.5.0"); d["extension"]["derivation_status"] = "asymptotic-argument"
    out["ts_asymptotic_nolimit"] = (d, {"theory.limit_missing"})
    d = stamp(THEORY_1_0, "2.5.0")
    d["extension"].update(conventions={}, order="", derivation_status="perturbative-argument", validity_domain={},
                          checks_run=[{"name": "units", "result": "looks fine"}])
    out["ts_empty"] = (d, {"theory.conventions_incomplete", "theory.order_missing", "theory.validity_empty",
                           "theory.check_result_vocab"})
    d = stamp(THEORY_1_0, "2.5.0"); d["extension"].update(derivation_status="formal-proof", checks_run=[], checks_not_run=[])
    out["ts_formalproof"] = (d, {"theory.unchecked_strong_status"})
    return out


def all_codes(rep):
    return {f.code for f in rep.findings}


class BackCompatibilityTests(unittest.TestCase):
    """THY-WP2.4: an artifact written under contracts 2.5.0 keeps its outcome; --strict applies the 2.6.0 rules."""

    def test_2_5_artifact_keeps_its_outcome_and_strict_reports(self):
        for name, (_, _, level, code) in MUTATIONS.items():
            with self.subTest(name):
                doc = mutated(name, version="2.5.0")
                rep = v.validate_artifact(doc)
                self.assertNotIn(code, all_codes(rep))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertIn(code, codes(v.validate_artifact(doc, strict=True), level))

    def test_audit_reproductions(self):
        for name, (doc, expected) in audit_copies().items():
            with self.subTest(name):
                rep = v.validate_artifact(doc)
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertFalse(expected & all_codes(rep))
                self.assertTrue(expected <= all_codes(v.validate_artifact(doc, strict=True)))
                self.assertTrue(expected <= all_codes(v.validate_artifact(stamp(doc, "2.6.0"))))

    def test_legacy_1_0_fixtures_keep_their_outcome(self):
        for doc in (THEORY_1_0, PREDICTION_1_0):
            rep = v.validate_artifact(copy.deepcopy(doc))
            self.assertTrue(rep.ok)
            self.assertFalse({f.code for f in rep.findings if f.code.startswith(("theory.", "prediction."))})

    def test_cli_strict_flag(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("ts_validity_empty", "pred_observed", "pred_envelope_inverted"):
                with self.subTest(name):
                    path = Path(tmp) / f"{name}.json"
                    path.write_text(json.dumps(mutated(name, version="2.5.0")))
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        self.assertEqual(v.main([str(path)]), 0)
                        self.assertEqual(v.main([str(path), "--strict"]), 1)
                    self.assertIn(MUTATIONS[name][3], buf.getvalue())


class CommittedExampleTests(unittest.TestCase):
    """THY-WP2.5: the committed theory examples are written under the current contracts and satisfy the theory rules."""
    PATHS = ("examples/qed-prediction/output/artifacts/theory_spec.json",
             "examples/qed-prediction/output/artifacts/prediction.json",
             "examples/theory-comparison/output/artifacts/folded_expectation.json",
             "examples/recasting/output/artifacts/prediction_m300.json")

    def test_theory_examples_validate_at_the_current_contracts(self):
        from contracts import CONTRACTS_VERSION
        for rel in self.PATHS:
            with self.subTest(rel):
                if not (ROOT / rel).is_file():  # tools/check_ams_optional.py runs tests/contracts on a copy without examples
                    self.skipTest(f"{rel} is not in this copy of the plugin")
                doc = json.loads((ROOT / rel).read_text())
                self.assertEqual(doc["contract_version"], CONTRACTS_VERSION)
                rep = v.validate_artifact(doc)
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertFalse({f.code for f in rep.findings if f.code.startswith(("theory.", "prediction."))},
                                 rep.as_dict())


if __name__ == "__main__":
    unittest.main()
