"""Response artifact semantics and the artifact -> validator adapter (detector-response review 2026-10-12, WP1).

The review found that contracts/validate.py passed a response with no matrix, with 'conditional_on_selected' and
inefficiency or acceptance inside the matrix, 'joint_counts' with inefficiency inside, one variable in two units, and
a separately applied 'trigger_efficiency' on a matrix that already holds the inefficiency (free-string comparison).
Contracts 2.4.0 report these natively; older artifacts keep their outcome and get them with --strict. The adapter
turns a response artifact into core/stats/validate_response.py input, so the two vocabularies meet in one place.
All fixtures SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import response_adapter as ra  # noqa: E402
from contracts import validate as v  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
LEGACY = json.loads((ART / "valid" / "response.json").read_text())
MATRIX = [[0.7, 0.1], [0.1, 0.6]]  # rows reco, cols truth; columns sum to 0.8 and 0.7 (efficiency inside)


def current(**ext):
    doc = copy.deepcopy(LEGACY)
    doc["contract_version"] = CONTRACTS_VERSION
    doc["versions"]["contracts"] = CONTRACTS_VERSION
    doc["extension"]["matrix"] = copy.deepcopy(MATRIX)
    doc["extension"].update(ext)
    return doc


def codes(rep, level="error"):
    return {f.code for f in (rep.errors if level == "error" else [x for x in rep.findings if x.severity == level])}


MUTATIONS = {
    "trigger_efficiency_twice": (lambda e: e.update(applied_separately=["trigger_efficiency"]), "response.double_counted"),
    "acceptance_twice_not_in_includes": (lambda e: e.update(includes=["efficiency"], applied_separately=["acceptance"]),
                                         "response.double_counted"),
    "matrix_missing": (lambda e: e.pop("matrix"), "response.matrix_missing"),
    "selected_with_inefficiency_inside": (lambda e: e.update(normalization="conditional_on_selected"),
                                          "response.normalization_inconsistent"),
    "selected_with_acceptance_inside": (lambda e: e.update(normalization="conditional_on_selected", inefficiency="outside_matrix",
                                                           includes=["acceptance"], applied_separately=["efficiency"]),
                                        "response.normalization_inconsistent"),
    "joint_counts_with_inefficiency_inside": (lambda e: e.update(normalization="joint_counts"), "response.normalization_inconsistent"),
    "unit_mismatch": (lambda e: e["reco_axis"].update(unit="deg"), "response.unit_mismatch"),
    "unknown_correction_term": (lambda e: e.update(applied_separately=["trigger eff"]), "response.unknown_correction"),
}


def mutated(name, legacy=False):
    doc = copy.deepcopy(LEGACY) if legacy else current()
    if legacy:
        doc["extension"]["matrix"] = copy.deepcopy(MATRIX)
    MUTATIONS[name][0](doc["extension"])
    return doc


class ResponseSemanticsTests(unittest.TestCase):
    def test_current_artifact_with_matrix_is_valid(self):
        rep = v.validate_artifact(current())
        self.assertTrue(rep.ok, rep.as_dict())

    def test_each_mutation_is_reported_natively(self):
        for name, (_, code) in MUTATIONS.items():
            with self.subTest(name):
                self.assertIn(code, codes(v.validate_artifact(mutated(name))))

    def test_legacy_artifact_keeps_its_outcome_and_strict_reports(self):
        self.assertTrue(v.validate_artifact(copy.deepcopy(LEGACY)).ok)
        for name, (_, code) in MUTATIONS.items():
            with self.subTest(name):
                self.assertNotIn(code, codes(v.validate_artifact(mutated(name, legacy=True))))
                self.assertIn(code, codes(v.validate_artifact(mutated(name, legacy=True), strict=True)))

    def test_literal_efficiency_double_count_is_still_reported_for_every_version(self):
        doc = copy.deepcopy(LEGACY)
        doc["extension"]["applied_separately"] = ["efficiency"]
        self.assertIn("response.double_counted", codes(v.validate_artifact(doc)))

    def test_matrix_ref_satisfies_the_matrix_requirement(self):
        doc = current(matrix_ref="response_matrix.json")
        doc["extension"].pop("matrix")
        self.assertTrue(v.validate_artifact(doc).ok)

    def test_namespaced_correction_is_accepted(self):
        doc = current(applied_separately=["exp-x:cutoff_fraction", "luminosity"])
        self.assertTrue(v.validate_artifact(doc).ok, v.validate_artifact(doc).as_dict())

    def test_parametrized_response_needs_no_matrix(self):
        doc = json.loads((ART / "valid" / "response_parametrized.json").read_text())
        self.assertTrue(v.validate_artifact(doc, strict=True).ok, v.validate_artifact(doc, strict=True).as_dict())


class AdapterTests(unittest.TestCase):
    def test_fixture_with_matrix_converts_and_validates(self):
        out = ra.to_validator_input(current()["extension"])
        self.assertTrue(out["ok"], out)
        doc = out["input"]
        meta = doc["metadata"]
        self.assertEqual(meta["truth_axis"]["variable"], "cos_theta")
        self.assertEqual(meta["normalization"], "includes_efficiency")
        self.assertIs(meta["efficiency_applied_separately"], False)
        self.assertIs(meta["acceptance_applied_separately"], False)
        self.assertNotEqual(validate_response(doc)["status"], "fail", validate_response(doc))

    def test_vocabulary_mapping(self):
        ext = current(normalization="joint_counts", inefficiency="outside_matrix", includes=["migration"],
                      applied_separately=["trigger_efficiency", "acceptance"], acceptance="outside_matrix",
                      intended_use="forward_folding", underflow_overflow="explicit_bins")["extension"]
        meta = ra.to_validator_input(ext)["input"]["metadata"]
        self.assertEqual(meta["normalization"], "counts")
        self.assertIs(meta["efficiency_applied_separately"], True)
        self.assertIs(meta["acceptance_applied_separately"], True)
        self.assertEqual((meta["intended_use"], meta["underflow_overflow"]), ("forward_folding", "explicit_bins"))

    def test_unmappable_values_are_explicit_errors(self):
        for change, field in ((dict(normalization="unnormalized"), "normalization"),
                              (dict(acceptance="not-applicable"), "acceptance"),
                              (dict(form="parametrized"), "form"),
                              (dict(underflow_overflow="somewhere"), "underflow_overflow")):
            with self.subTest(field):
                out = ra.to_validator_input(current(**change)["extension"])
                self.assertFalse(out["ok"])
                self.assertIsNone(out["input"])
                self.assertTrue(any(e["field"] == field for e in out["errors"]), out)

    def test_missing_matrix_is_an_error_and_matrix_argument_wins(self):
        ext = current()["extension"]
        ext.pop("matrix")
        self.assertFalse(ra.to_validator_input(ext)["ok"])
        self.assertEqual(ra.to_validator_input(ext, matrix=MATRIX)["input"]["matrix"], MATRIX)

    def test_undeclared_flow_is_an_assumption_not_silent(self):
        out = ra.to_validator_input(current()["extension"])
        self.assertEqual(out["input"]["metadata"]["underflow_overflow"], "not_represented")
        self.assertTrue(any("underflow_overflow" in a for a in out["assumptions"]))

    def test_end_to_end_artifact_validate_convert_validate_fold(self):
        artifact = current(intended_use="forward_folding")
        self.assertTrue(v.validate_artifact(artifact).ok)
        out = ra.to_validator_input(artifact["extension"], closure={"truth": [1000, 500], "reco": [750, 400]})
        self.assertTrue(out["ok"], out)
        report = validate_response(out["input"])
        self.assertEqual(report["status"], "pass", report)
        folded = ra.fold(out["input"], [1000, 500], background=[5, 5])
        self.assertEqual(report["metrics"]["closure"]["predicted_reco"], [750.0, 400.0])
        for got, want in zip(folded, [755.0, 405.0]):
            self.assertAlmostEqual(got, want, places=12)

    def test_fold_counts_matches_probabilities(self):
        ext = current(normalization="joint_counts", inefficiency="outside_matrix", applied_separately=["efficiency"])["extension"]
        counts = ra.to_validator_input(ext, matrix=[[70, 10], [10, 60]], generated_per_truth_bin=[80, 70])["input"]
        probs = dict(counts, matrix=[[70 / 80, 10 / 70], [10 / 80, 60 / 70]])
        probs["metadata"] = dict(counts["metadata"], normalization="conditional_on_selected")
        del probs["generated_per_truth_bin"]
        for a, b in zip(ra.fold(counts, [3.5, 9.25]), ra.fold(probs, [3.5, 9.25])):
            self.assertLess(abs(a - b), 1e-12)


if __name__ == "__main__":
    unittest.main()
