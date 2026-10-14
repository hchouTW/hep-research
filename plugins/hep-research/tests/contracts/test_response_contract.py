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
    """The legacy fixture at the current contract version, with an inline matrix and the declarations that contracts
    2.8.0 requires of a matrix (intended_use, underflow_overflow; rule R1)."""
    doc = copy.deepcopy(LEGACY)
    doc["contract_version"] = CONTRACTS_VERSION
    doc["versions"]["contracts"] = CONTRACTS_VERSION
    doc["extension"]["matrix"] = copy.deepcopy(MATRIX)
    doc["extension"].update(intended_use="forward_folding", underflow_overflow="not_represented")
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


# Contracts 2.8.0 response hardening (detector-response audit DR-WP2-03): one mutation per error rule R1-R6.
MUTATIONS_V28 = {
    "R1_intended_use_missing": (lambda e: e.pop("intended_use", None), "response.declaration_missing"),
    "R2_misspelled_key": (lambda e: e.update(intended_usage=e.pop("intended_use", "forward_folding")), "response.misspelled_key"),
    "R3_efficiency_included_but_outside": (lambda e: e.update(inefficiency="outside_matrix", normalization="joint_counts"),
                                           "response.placement_inconsistent"),
    "R4_unnormalized_matrix": (lambda e: e.update(normalization="unnormalized"), "response.normalization_unusable"),
    "R5_exposure_and_livetime": (lambda e: e.update(acceptance="outside_matrix", includes=["efficiency"],
                                                    applied_separately=["exposure", "livetime"]), "response.correction_overlap"),
    "R6_explicit_bins_without_vectors": (lambda e: e.update(underflow_overflow="explicit_bins"), "response.flow_vectors_missing"),
}
CRAFTED = ART / "invalid" / "response_2_8"
CRAFTED_WARN = ART / "warning" / "response_2_8"
# The 30 crafted broken responses of the audit appendix (case 22 dropped: at 2.8.0 it repeats case 03), each with the
# error code(s) contracts 2.8.0 reports natively and under --strict; 20 and 24 pass with these warnings.
CRAFTED_CODES = {
    "01_cos_cols_not_normalized": {"response.numeric.normalization.truth_sum"},
    "02_cog_colsum_gt1": {"response.numeric.normalization.exceeds_one"},
    "03_negative_entries": {"response.numeric.entries.negative"},
    "04_shape_vs_edges": {"response.numeric.dimensions.mismatch"},
    "05_unfolding_singular": {"response.numeric.identifiability.rank_deficient"},
    "06_eff_class_double": {"response.double_counted"},
    "07_eff_outside_not_applied": {"response.numeric.bookkeeping.inefficiency_not_applied"},
    "08_transposed": {"response.numeric.orientation.likely_transposed"},
    "09_unnormalized_unfolding": {"response.normalization_unusable"},
    "10_nonmonotonic_edges": {"response.numeric.edges.truth_axis"},
    "11_var_mismatch_noconv": {"response.numeric.axes.variable_mismatch"},
    "12_bad_flow_string": {"schema.enum"},
    "13_cog_ineff_outside": {"response.normalization_inconsistent"},
    "14_nan_entry": {"number.non_finite"},
    "15_acceptance_double": {"response.double_counted"},
    "16_reco_edges_count": {"response.numeric.dimensions.mismatch"},
    "17_ragged": {"response.numeric.shape.ragged"},
    "18_joint_counts_gen_lt_counts": {"response.numeric.normalization.exceeds_generated"},
    "19_no_use_singular": {"response.declaration_missing", "response.numeric.identifiability.rank_deficient"},
    "21_fakes_double": {"response.double_counted"},
    "23_square_transposed_cog": {"response.numeric.orientation.likely_transposed"},
    "25_explicit_bins_no_vectors": {"response.flow_vectors_missing"},
    "26_no_use_no_flow": {"response.declaration_missing"},
    "27_includes_eff_but_outside": {"response.placement_inconsistent"},
    "28_acceptance_and_exposure": {"response.correction_overlap"},
    "29_matrix_axis_missing": {"response.axes_missing", "response.placement_missing"},
    "30_misspelled_keys": {"response.misspelled_key", "response.declaration_missing"},
}
CRAFTED_WARNINGS = {"20_cog_eff_not_visible": {"response.numeric.double_counting.efficiency_not_visible"},
                    "24_unfolding_near_singular": {"response.numeric.identifiability.ill_conditioned"}}
# Default outcome of the same artifacts under the 2.6.0/2.7.0 rules: only these failed (the audit's probe, 5 of 30).
LEGACY_FAILING = {"06_eff_class_double", "14_nan_entry", "15_acceptance_double", "21_fakes_double", "29_matrix_axis_missing"}


def stamped(doc, version):
    doc = copy.deepcopy(doc)
    doc["contract_version"] = version
    doc["versions"]["contracts"] = version
    return doc


class ResponseHardeningTests(unittest.TestCase):
    """Contracts 2.8.0 response hardening (detector-response audit 2026-10-13, DR-WP2): rules R1-R10."""

    def test_each_v28_mutation_is_reported_natively(self):
        for name, (fn, code) in MUTATIONS_V28.items():
            with self.subTest(name):
                doc = current()
                fn(doc["extension"])
                self.assertIn(code, codes(v.validate_artifact(doc)))

    def test_v26_and_v27_artifacts_keep_their_outcome_and_strict_reports(self):
        for version in ("2.6.0", "2.7.0"):
            for name, (fn, code) in MUTATIONS_V28.items():
                with self.subTest(version=version, mutation=name):
                    doc = stamped(current(), version)
                    fn(doc["extension"])
                    self.assertNotIn(code, codes(v.validate_artifact(doc)))
                    self.assertIn(code, codes(v.validate_artifact(doc, strict=True)))

    def test_crafted_responses_fail_natively_and_under_strict(self):
        files = {p.stem: p for p in CRAFTED.glob("*.json")}
        self.assertEqual(set(files), set(CRAFTED_CODES))
        for name, expected in CRAFTED_CODES.items():
            doc = json.loads(files[name].read_text())
            for strict in (False, True):
                with self.subTest(case=name, strict=strict):
                    rep = v.validate_artifact(doc, strict=strict)
                    self.assertFalse(rep.ok)
                    self.assertTrue(expected <= codes(rep), (expected, codes(rep)))

    def test_cases_20_and_24_pass_with_warnings(self):
        for name, expected in CRAFTED_WARNINGS.items():
            with self.subTest(case=name):
                rep = v.validate_artifact(json.loads((CRAFTED_WARN / f"{name}.json").read_text()))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertTrue(expected <= codes(rep, "warning"), codes(rep, "warning"))

    def test_crafted_responses_keep_their_legacy_outcome(self):
        for path in [*CRAFTED.glob("*.json"), *CRAFTED_WARN.glob("*.json")]:
            for version in ("2.6.0", "2.7.0"):
                with self.subTest(case=path.stem, version=version):
                    ok = v.validate_artifact(stamped(json.loads(path.read_text()), version)).ok
                    self.assertEqual(ok, path.stem not in LEGACY_FAILING)

    def test_valid_v28_fixture_has_no_findings(self):
        rep = v.validate_artifact(json.loads((ART / "valid" / "response_v28.json").read_text()), strict=True)
        self.assertEqual(rep.findings, [], rep.as_dict())

    def test_correction_space_rules(self):
        doc = current(normalization="conditional_on_selected", inefficiency="outside_matrix", acceptance="outside_matrix",
                      includes=["migration"], applied_separately=["efficiency", "acceptance"],
                      correction_space={"acceptance": {"space": "reco"}, "luminosity": {"space": "global"}})
        rep = v.validate_artifact(doc)
        self.assertIn("response.correction_space_inconsistent", codes(rep))
        self.assertIn("response.correction_space_unknown_term", codes(rep))
        self.assertIn("response.correction_space_missing", codes(rep, "warning"))

    def test_unfolding_without_mc_stat_is_unresolved_and_payload_is_checked(self):
        doc = current(intended_use="unfolding")
        self.assertIn("response.mc_stat_missing", codes(v.validate_artifact(doc), "unresolved"))
        doc = current(mc_stat={"kind": "generated_counts"})
        self.assertIn("response.mc_stat_payload_missing", codes(v.validate_artifact(doc)))
        doc = current(mc_stat={"kind": "generated_counts", "events_per_truth_bin": [1, 2, 3]})
        self.assertIn("response.mc_stat_payload_missing", codes(v.validate_artifact(doc)))

    def test_variations_and_periods_match_the_nominal_shape(self):
        var = {"nuisance": "scale", "direction": "up", "matrix": [[0.7, 0.1, 0.0], [0.1, 0.6, 0.0]]}
        rep = v.validate_artifact(current(systematic_variations=[var, dict(var, matrix=MATRIX)]))
        self.assertIn("response.variation_shape", codes(rep))
        self.assertIn("response.variation_duplicate", codes(rep))
        rep = v.validate_artifact(current(periods=[{"id": "p1", "exposure_weight": 0, "matrix": [[1.0]]}]))
        self.assertIn("response.variation_shape", codes(rep))

    def test_matrix_ref_alone_is_numerically_unchecked(self):
        doc = current(matrix_ref="matrices/response.json")
        doc["extension"].pop("matrix")
        rep = v.validate_artifact(doc)
        self.assertTrue(rep.ok)
        self.assertIn("response.numeric_unchecked", codes(rep, "unresolved"))

    def test_fakes_inside_is_a_warning(self):
        rep = v.validate_artifact(current(includes=["efficiency", "acceptance", "fakes"]))
        self.assertIn("response.fakes_inside", codes(rep, "warning"))
        self.assertNotIn("response.fakes_inside", codes(rep))


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
        ext = current()["extension"]
        ext.pop("underflow_overflow")
        out = ra.to_validator_input(ext)
        self.assertEqual(out["input"]["metadata"]["underflow_overflow"], "not_represented")
        self.assertTrue(any("underflow_overflow" in a for a in out["assumptions"]))

    def test_undeclared_flow_is_an_error_from_2_8(self):
        ext = current()["extension"]
        ext.pop("underflow_overflow")
        self.assertTrue(ra.to_validator_input(ext, contract_version="2.7.0")["ok"])
        out = ra.to_validator_input(ext, contract_version="2.8.0")
        self.assertFalse(out["ok"])
        self.assertTrue(any(e["field"] == "underflow_overflow" for e in out["errors"]), out)

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



class AdapterMatrixRefTests(unittest.TestCase):
    """detector-response audit DR-WP2-04: matrix_ref objects, fragments, folder boundary and unreadable refs."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "artifacts"
        self.dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def ext(self, ref, **extra):
        fields = dict(normalization="conditional_on_selected", inefficiency="outside_matrix", acceptance="outside_matrix",
                      includes=["migration"], applied_separately=["efficiency", "acceptance"],
                      underflow_overflow="explicit_bins")
        e = current(**{**fields, **extra})["extension"]
        e.pop("matrix")
        e["matrix_ref"] = ref
        return e

    def write(self, name, payload):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload))
        return path

    def test_flow_vectors_come_from_the_matrix_ref_object(self):
        self.write("m.json", {"matrix": [[0.8, 0.1], [0.1, 0.7]], "underflow": [0.1, 0.0], "overflow": [0.0, 0.2]})
        out = ra.to_validator_input(self.ext("m.json"), base_dir=self.dir)
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["input"]["underflow"], out["input"]["overflow"]), ([0.1, 0.0], [0.0, 0.2]))
        self.assertEqual(validate_response(out["input"])["status"], "pass", validate_response(out["input"]))

    def test_fragment_selects_a_member(self):
        self.write("r.json", {"response": {"matrix": [[0.8, 0.1], [0.1, 0.7]], "underflow": [0.1, 0.0],
                                           "overflow": [0.0, 0.2]}})
        out = ra.to_validator_input(self.ext("r.json#response"), base_dir=self.dir)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["input"]["overflow"], [0.0, 0.2])

    def test_object_without_matrix_is_named(self):
        self.write("r.json", {"response": [[1.0]]})
        out = ra.to_validator_input(self.ext("r.json"), base_dir=self.dir)
        self.assertFalse(out["ok"])
        self.assertTrue(any("holds no 'matrix'" in e["message"] for e in out["errors"]), out)

    def test_ref_outside_the_artifact_folder_is_refused(self):
        (self.dir.parent / "outside.json").write_text(json.dumps({"matrix": [[1.0, 0.0], [0.0, 1.0]]}))
        out = ra.to_validator_input(self.ext("../outside.json"), base_dir=self.dir)
        self.assertFalse(out["ok"])
        self.assertTrue(any("outside the artifact folder" in e["message"] for e in out["errors"]), out)

    def test_malformed_ref_exits_2_with_json(self):
        import subprocess
        self.write("bad.json", "{not json")
        art = self.write("response.json", {"extension": self.ext("bad.json")})
        proc = subprocess.run([sys.executable, str(ROOT / "contracts" / "response_adapter.py"), str(art), "--validate"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["ok"])

    def test_exposure_counts_as_acceptance_applied_separately(self):
        e = self.ext("m.json", applied_separately=["efficiency", "exposure"])
        self.write("m.json", {"matrix": [[0.8, 0.1], [0.1, 0.7]], "underflow": [0.1, 0.0], "overflow": [0.0, 0.2]})
        out = ra.to_validator_input(e, base_dir=self.dir)
        self.assertIs(out["input"]["metadata"]["acceptance_applied_separately"], True)
        self.assertNotIn("bookkeeping.acceptance_not_applied",
                         {x["code"] for x in validate_response(out["input"])["errors"]})


if __name__ == "__main__":
    unittest.main()
