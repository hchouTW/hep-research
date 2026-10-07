"""Tests for scripts/audit_analysis_spec.py. Mutation style: start from the valid
specification fixture, introduce one controlled defect, and assert that the
intended diagnostic is emitted with the right severity class. Covers duplicated
corrections, unsupported ratio cancellation, invalid low-count approximations,
Gaussian-core tail estimates, scale systematics on final values, undefined units
and species, and undocumented AMS numbers. Run from the skill directory with
`python3 -m unittest discover -s tests -v`."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root: core/, contracts/
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))
import audit_analysis_spec as aas  # noqa: E402

CLAIMS = json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))


def spec():
    return json.loads((FIX / "spec_valid.json").read_text(encoding="utf-8"))


def audit(doc, claims=CLAIMS):
    return aas.audit_spec(doc, claims)


def codes(report, severity=None):
    return {f["code"] for f in report["findings"] if severity is None or f["severity"] == severity}


def ratio_spec():
    doc = spec()
    doc["measurement"]["target"] = "ratio"
    doc["ratio"] = {
        "numerator": "helium flux", "denominator": "proton flux",
        "cancellations": [
            {"effect": "geometric acceptance", "treatment": "correlated",
             "correlation_model": "same fiducial region; correlation from shared MC", "verification": "MC comparison per bin"},
            {"effect": "charge estimator efficiency", "treatment": "independent",
             "correlation_model": None, "verification": "measured per species"}]}
    return doc


class ValidSpecTests(unittest.TestCase):
    def test_valid_fixture_has_no_errors_or_warnings(self):
        report = audit(spec())
        self.assertEqual(report["counts"]["error"], 0, report["findings"])
        self.assertEqual(report["counts"]["warning"], 0, report["findings"])
        self.assertEqual(report["verdict"], "acceptable with open inputs")

    def test_proposals_and_unresolved_are_kept_separate_from_errors(self):
        report = audit(spec())
        self.assertEqual(report["counts"]["proposal"], 1)
        self.assertEqual(report["counts"]["unresolved"], 2)
        self.assertIn("claim.proposal", codes(report, "proposal"))
        self.assertIn("input.unresolved", codes(report, "unresolved"))

    def test_valid_ratio_spec_passes(self):
        self.assertEqual(audit(ratio_spec())["counts"]["error"], 0)

    def test_audit_does_not_modify_input(self):
        doc = spec()
        before = copy.deepcopy(doc)
        audit(doc)
        self.assertEqual(doc, before)


class MeasurementDefinitionTests(unittest.TestCase):
    def mutate(self, edit):
        doc = spec()
        edit(doc)
        return audit(doc)

    def test_missing_estimand(self):
        def edit(d): del d["measurement"]["estimand"]
        report = self.mutate(edit)
        self.assertIn("estimand.missing", codes(report, "error"))
        self.assertEqual(report["verdict"], "blocked")

    def test_ambiguous_measurement_level(self):
        def edit(d): d["measurement"]["level"] = "somewhere in between"
        self.assertIn("level.ambiguous", codes(self.mutate(edit), "error"))

    def test_undefined_variable_and_unit(self):
        def var(d): d["measurement"]["variable"] = "energy"
        def unit(d): del d["measurement"]["unit"]
        self.assertIn("variable.undefined", codes(self.mutate(var), "error"))
        self.assertIn("unit.undefined", codes(self.mutate(unit), "error"))

    def test_rigidity_labelled_as_momentum_unit(self):
        def edit(d): d["measurement"]["unit"] = "GeV/c"
        self.assertIn("unit.mismatch", codes(self.mutate(edit), "error"))

    def test_missing_charge_number_and_sign(self):
        def z(d): del d["measurement"]["species"][0]["abs_Z"]
        def sign(d): del d["measurement"]["species"][0]["charge_sign"]
        self.assertIn("species.abs_Z", codes(self.mutate(z), "error"))
        self.assertIn("species.charge_sign", codes(self.mutate(sign), "error"))

    def test_energy_variable_requires_mass_and_A(self):
        def edit(d):
            d["measurement"].update({"variable": "kinetic_energy_per_nucleon", "unit": "GeV/n"})
            del d["measurement"]["species"][0]["mass_GeV"]
            del d["measurement"]["species"][0]["A"]
        report = self.mutate(edit)
        self.assertTrue({"species.mass", "species.A"} <= codes(report, "error"))

    def test_no_species(self):
        def edit(d): d["measurement"]["species"] = []
        self.assertIn("species.missing", codes(self.mutate(edit), "error"))

    def test_bad_range_and_bins(self):
        def edit(d):
            d["measurement"]["range"] = [100.0, 1.0]
            d["measurement"]["bin_edges"] = [1.0, 5.0, 2.0]
        report = self.mutate(edit)
        self.assertTrue({"range.invalid", "binning.invalid"} <= codes(report, "error"))

    def test_undeclared_period_and_sample_are_unresolved_not_errors(self):
        def edit(d):
            d["data_scope"]["period"] = {}
            del d["measurement"]["sample"]
        report = self.mutate(edit)
        self.assertTrue({"data_scope.period", "sample.undeclared"} <= codes(report, "unresolved"))
        self.assertEqual(report["counts"]["error"], 0)

    def test_charge_sign_from_a_subsystem_that_cannot_measure_it(self):
        def edit(d): d["observables"][1]["subsystem"] = "TRD"
        self.assertIn("observable.charge_sign_source", codes(self.mutate(edit), "error"))

    def test_wrong_spec_version(self):
        def edit(d): d["spec_version"] = "0"
        self.assertIn("spec.version", codes(self.mutate(edit), "error"))


class SelectionAndBackgroundTests(unittest.TestCase):
    def mutate(self, edit):
        doc = spec()
        edit(doc)
        return audit(doc)

    def test_selection_without_denominator(self):
        def edit(d): del d["selections"][0]["conditional_denominator"]
        self.assertIn("selection.no_denominator", codes(self.mutate(edit), "error"))

    def test_selection_without_validation(self):
        def edit(d): d["selections"][1]["validation"] = []
        self.assertIn("selection.no_validation", codes(self.mutate(edit), "error"))

    def test_validation_without_metric_threshold_or_action(self):
        def edit(d): d["selections"][0]["validation"] = [{"metric": "agreement looks reasonable"}]
        report = self.mutate(edit)
        finding = next(f for f in report["findings"] if f["code"] == "validation.incomplete")
        self.assertIn("threshold", finding["message"])
        self.assertIn("action", finding["message"])

    def test_top_level_validation_incomplete(self):
        def edit(d): d["validation"][0] = {"name": "closure", "kind": "closure", "metric": "chi2"}
        self.assertIn("validation.incomplete", codes(self.mutate(edit), "error"))

    def test_background_without_control_or_constraint(self):
        def edit(d): del d["backgrounds"][0]["control_region"]
        self.assertIn("background.no_constraint", codes(self.mutate(edit), "error"))

    def test_background_with_constraint_but_no_control_is_accepted(self):
        def edit(d):
            del d["backgrounds"][0]["control_region"]
            d["backgrounds"][0]["constraint"] = "auxiliary measurement of the contamination fraction"
        self.assertNotIn("background.no_constraint", codes(self.mutate(edit)))

    def test_background_without_estimator(self):
        def edit(d): del d["backgrounds"][1]["estimator"]
        self.assertIn("background.no_estimator", codes(self.mutate(edit), "error"))

    def test_control_region_gaps_are_warnings(self):
        def edit(d):
            del d["backgrounds"][0]["transfer_model"]
            del d["backgrounds"][0]["contamination_correction"]
            del d["backgrounds"][0]["closure_test"]
        report = self.mutate(edit)
        self.assertTrue({"background.no_transfer_model", "background.no_contamination", "background.no_closure"} <= codes(report, "warning"))
        self.assertEqual(report["verdict"], "needs work")

    def test_unregistered_numeric_threshold_is_flagged(self):
        def edit(d): d["selections"][0]["definition"] = "chi2 < 10 in both projections"
        self.assertIn("selection.unregistered_number", codes(self.mutate(edit), "warning"))


class CorrectionChainTests(unittest.TestCase):
    def mutate(self, edit):
        doc = spec()
        edit(doc)
        return audit(doc)

    def test_same_effect_corrected_as_veto_and_efficiency(self):
        def edit(d):
            d["corrections"].append({"effect_id": "tof_timing_drift", "category": "veto", "applied_in": "estimator"})
        report = self.mutate(edit)
        self.assertIn("correction.double_applied", codes(report, "error"))
        self.assertIn("tof_timing_drift", next(f for f in report["findings"] if f["code"] == "correction.double_applied")["message"])

    def test_efficiency_in_response_and_estimator(self):
        def edit(d): d["response"]["includes"] = ["efficiency"]
        self.assertIn("correction.response_and_estimator", codes(self.mutate(edit), "error"))

    def test_acceptance_row_in_response_and_estimator_list(self):
        def edit(d):
            d["corrections"].append({"effect_id": "fiducial", "category": "acceptance", "applied_in": "response_matrix"})
        self.assertIn("correction.response_and_estimator", codes(self.mutate(edit), "error"))

    def test_exposure_applied_with_its_factors(self):
        def edit(d): d["estimator"]["applies"] = ["efficiency", "exposure", "livetime"]
        self.assertIn("exposure.decomposed_and_composite", codes(self.mutate(edit), "error"))

    def test_diagonal_estimator_without_migration_study(self):
        def edit(d): d["estimator"]["form"] = "diagonal"
        self.assertIn("estimator.diagonal_unvalidated", codes(self.mutate(edit), "warning"))

    def test_missing_effect_id_and_bad_category(self):
        def edit(d):
            d["corrections"][0].pop("effect_id")
            d["corrections"][1]["category"] = "magic"
        report = self.mutate(edit)
        self.assertTrue({"correction.no_effect_id", "correction.bad_category"} <= codes(report, "error"))

    def test_response_required_by_method(self):
        def edit(d): del d["response"]
        self.assertIn("response.missing", codes(self.mutate(edit), "error"))

    def test_response_card_incomplete(self):
        def edit(d): del d["response"]["normalization"]
        self.assertIn("response.card_incomplete", codes(self.mutate(edit), "error"))

    def test_truth_and_reco_variables_mixed_without_conversion(self):
        def edit(d): d["response"]["reco_variable"] = "total_energy"
        self.assertIn("response.variable_mixing", codes(self.mutate(edit), "error"))
        def declared(d):
            d["response"]["reco_variable"] = "total_energy"
            d["response"]["variable_conversion"] = "E from ECAL versus R from Tracker; stated |Z|=1 relation"
        self.assertNotIn("response.variable_mixing", codes(self.mutate(declared)))

    def test_response_truth_variable_differs_from_binning_variable(self):
        def edit(d):
            d["response"]["truth_variable"] = "kinetic_energy"
            d["response"]["reco_variable"] = "kinetic_energy"
        self.assertIn("variable.mixed", codes(self.mutate(edit), "error"))


class RatioTests(unittest.TestCase):
    def test_ratio_without_ratio_section(self):
        doc = spec()
        doc["measurement"]["target"] = "ratio"
        self.assertIn("ratio.missing", codes(audit(doc), "error"))

    def test_ratio_with_no_cancellation_analysis(self):
        doc = ratio_spec()
        doc["ratio"]["cancellations"] = []
        self.assertIn("ratio.no_cancellation_analysis", codes(audit(doc), "error"))

    def test_assumed_cancellation_without_correlation_model(self):
        doc = ratio_spec()
        doc["ratio"]["cancellations"][0] = {"effect": "geometric acceptance", "treatment": "cancels"}
        self.assertIn("ratio.cancellation_unsupported", codes(audit(doc), "error"))

    def test_cancellation_with_model_but_no_verification_is_still_unsupported(self):
        doc = ratio_spec()
        doc["ratio"]["cancellations"][0] = {"effect": "geometric acceptance", "treatment": "cancels",
                                            "correlation_model": "fully correlated"}
        self.assertIn("ratio.cancellation_unsupported", codes(audit(doc), "error"))

    def test_partial_correlation_needs_a_model(self):
        doc = ratio_spec()
        doc["ratio"]["cancellations"][0] = {"effect": "trigger", "treatment": "partial"}
        self.assertIn("ratio.no_correlation_model", codes(audit(doc), "error"))

    def test_fraction_target_also_requires_ratio_section(self):
        doc = spec()
        doc["measurement"]["target"] = "fraction"
        self.assertIn("ratio.missing", codes(audit(doc), "error"))


class LowCountAndTailTests(unittest.TestCase):
    def mutate(self, edit):
        doc = spec()
        edit(doc)
        return audit(doc)

    def test_gaussian_approximation_at_low_counts(self):
        def edit(d):
            d["inference"].update({"approximation": "gaussian", "approximation_validated": False, "min_expected_counts": 3})
        report = self.mutate(edit)
        self.assertIn("inference.gaussian_low_count", codes(report, "error"))

    def test_wilks_on_a_boundary_parameter(self):
        def edit(d):
            d["inference"].update({"approximation": "wilks", "approximation_validated": False,
                                   "min_expected_counts": 5000, "parameter_on_boundary": True})
        self.assertIn("inference.gaussian_low_count", codes(self.mutate(edit), "error"))

    def test_s_over_sqrt_b_for_a_limit(self):
        def edit(d):
            d["measurement"]["target"] = "limit"
            d["inference"].update({"approximation": "s_over_sqrt_b", "approximation_validated": False, "min_expected_counts": None})
        self.assertIn("inference.gaussian_low_count", codes(self.mutate(edit), "error"))

    def test_validated_approximation_is_accepted(self):
        def edit(d):
            d["inference"].update({"approximation": "asymptotic", "approximation_validated": True, "min_expected_counts": 3})
        self.assertNotIn("inference.gaussian_low_count", codes(self.mutate(edit)))

    def test_exact_poisson_at_low_counts_is_accepted(self):
        def edit(d): d["inference"].update({"approximation": "exact_poisson", "min_expected_counts": 0})
        self.assertNotIn("inference.gaussian_low_count", codes(self.mutate(edit)))

    def test_gaussian_with_unknown_counts_is_unresolved(self):
        def edit(d):
            d["inference"].update({"approximation": "gaussian", "approximation_validated": False, "min_expected_counts": None})
        self.assertIn("inference.expected_counts_unknown", codes(self.mutate(edit), "unresolved"))

    def test_threshold_is_configurable(self):
        doc = spec()
        doc["inference"].update({"approximation": "gaussian", "approximation_validated": False, "min_expected_counts": 50})
        self.assertNotIn("inference.gaussian_low_count", codes(aas.audit_spec(doc, CLAIMS, low_count_threshold=20)))
        self.assertIn("inference.gaussian_low_count", codes(aas.audit_spec(doc, CLAIMS, low_count_threshold=100)))

    def test_inference_missing(self):
        def edit(d): d["inference"] = {}
        self.assertIn("inference.missing", codes(self.mutate(edit), "error"))

    def test_charge_confusion_from_gaussian_core(self):
        def edit(d): d["tail_estimates"][0]["method"] = "gaussian_core"
        self.assertIn("tail.gaussian_core", codes(self.mutate(edit), "error"))

    def test_background_estimated_from_gaussian_core(self):
        def edit(d): d["backgrounds"][1]["estimate_basis"] = "gaussian_core"
        self.assertIn("tail.gaussian_core", codes(self.mutate(edit), "error"))

    def test_tail_estimate_without_validation(self):
        def edit(d): del d["tail_estimates"][0]["tail_validation"]
        self.assertIn("tail.unvalidated", codes(self.mutate(edit), "error"))

    def test_negative_species_without_charge_confusion_estimate(self):
        def edit(d):
            d["measurement"]["species"][0]["charge_sign"] = -1
            d["tail_estimates"] = []
        self.assertIn("tail.charge_confusion_missing", codes(self.mutate(edit), "warning"))


class SystematicTests(unittest.TestCase):
    def mutate(self, edit):
        doc = spec()
        edit(doc)
        return audit(doc)

    def test_scale_uncertainty_on_final_values_only(self):
        def edit(d): d["systematics"][0]["applied_via"] = "final_value"
        self.assertIn("systematic.scale_on_final_value", codes(self.mutate(edit), "error"))

    def test_migration_effect_on_final_values(self):
        def edit(d):
            d["systematics"][1].update({"effect": "migration", "applied_via": "final_value"})
        self.assertIn("systematic.scale_on_final_value", codes(self.mutate(edit), "error"))

    def test_normalization_on_final_value_is_not_this_error(self):
        def edit(d): d["systematics"][1]["applied_via"] = "final_value"
        self.assertNotIn("systematic.scale_on_final_value", codes(self.mutate(edit)))

    def test_registry_gaps_are_warnings(self):
        def edit(d):
            for k in ("correlations_across_bins", "validation", "double_counting_checks"):
                del d["systematics"][0][k]
        report = self.mutate(edit)
        self.assertTrue({"systematic.no_correlations", "systematic.no_validation", "systematic.no_double_counting_check"} <= codes(report, "warning"))

    def test_no_systematic_registry(self):
        def edit(d): d["systematics"] = []
        self.assertIn("systematics.none", codes(self.mutate(edit), "warning"))

    def test_missing_closure_and_stress_tests(self):
        def edit(d): d["validation"] = []
        report = self.mutate(edit)
        self.assertTrue({"validation.no_closure", "validation.no_stress_test"} <= codes(report, "warning"))


class EvidenceTests(unittest.TestCase):
    def mutate(self, edit, claims=CLAIMS):
        doc = spec()
        edit(doc)
        return audit(doc, claims)

    def test_documented_parameter_without_claim(self):
        def edit(d): d["parameters"][0]["claim_ids"] = []
        self.assertIn("parameter.undocumented", codes(self.mutate(edit), "error"))

    def test_documented_parameter_with_unknown_claim(self):
        def edit(d): d["parameters"][0]["claim_ids"] = ["C999"]
        self.assertIn("parameter.unknown_claim", codes(self.mutate(edit), "error"))

    def test_namespaced_and_bare_claim_ids_resolve_alike(self):
        # the ledger is namespaced (ams02:C31); a spec may cite the bare short form (C31)
        for cid in ("C31", "ams02:C31"):
            def edit(d, cid=cid): d["parameters"][0]["claim_ids"] = [cid]
            self.assertNotIn("parameter.unknown_claim", codes(self.mutate(edit), "error"), cid)

    def test_other_namespace_is_not_resolved(self):
        def edit(d): d["parameters"][0]["claim_ids"] = ["other:C31"]
        self.assertIn("parameter.unknown_claim", codes(self.mutate(edit), "error"))

    def test_claim_that_forbids_numeric_quotation(self):
        def edit(d): d["parameters"][0]["claim_ids"] = ["C13"]
        self.assertIn("parameter.numeric_not_allowed", codes(self.mutate(edit), "error"))

    def test_paper_specific_choice_applied_to_another_species(self):
        def edit(d):
            d["parameters"][0]["applies_to"] = {"species": ["helium"]}
        report = self.mutate(edit)
        self.assertIn("parameter.scope_check", codes(report, "warning"))
        self.assertIn("not a universal AMS rule", next(f for f in report["findings"] if f["code"] == "parameter.scope_check")["message"])

    def test_parameter_without_provenance(self):
        def edit(d): del d["parameters"][1]["provenance"]
        self.assertIn("parameter.no_provenance", codes(self.mutate(edit), "error"))

    def test_proposal_and_unknown_parameters_are_classified(self):
        def edit(d):
            d["parameters"].append({"name": "template smoothing", "value": "kernel", "provenance": "proposal"})
            d["parameters"].append({"name": "trigger efficiency", "provenance": "unknown"})
        report = self.mutate(edit)
        self.assertIn("parameter.proposal", codes(report, "proposal"))
        self.assertIn("parameter.unknown", codes(report, "unresolved"))
        self.assertEqual(report["counts"]["error"], 0)

    def test_documented_statement_without_claim_id(self):
        def edit(d): d["ams_claims"][0]["claim_ids"] = []
        self.assertIn("claim.undocumented", codes(self.mutate(edit), "error"))

    def test_statement_without_valid_label(self):
        def edit(d): d["ams_claims"][1]["label"] = "Standard AMS practice"
        self.assertIn("claim.label", codes(self.mutate(edit), "error"))

    def test_unknown_claim_id_in_statement(self):
        def edit(d): d["ams_claims"][0]["claim_ids"] = ["C999"]
        self.assertIn("claim.unknown", codes(self.mutate(edit), "error"))

    def test_without_ledger_claim_ids_are_not_resolved(self):
        def edit(d): d["parameters"][0]["claim_ids"] = ["C999"]
        report = self.mutate(edit, claims=None)
        self.assertNotIn("parameter.unknown_claim", codes(report))


class SeverityAndOutputTests(unittest.TestCase):
    def test_findings_are_ordered_by_severity(self):
        doc = spec()
        del doc["measurement"]["estimand"]
        doc["systematics"] = []
        order = [f["severity"] for f in audit(doc)["findings"]]
        self.assertEqual(order, sorted(order, key=aas.SEVERITIES.index))

    def test_every_finding_has_the_full_shape(self):
        doc = spec()
        del doc["measurement"]["estimand"]
        for f in audit(doc)["findings"]:
            self.assertEqual(set(f), {"severity", "code", "path", "message", "remedy"})
            self.assertIn(f["severity"], aas.SEVERITIES)

    def test_markdown_is_verdict_first(self):
        doc = spec()
        doc["selections"][0].pop("conditional_denominator")
        text = aas.render_markdown(audit(doc), "test")
        lines = [l for l in text.splitlines() if l.startswith("#")]
        self.assertEqual(lines[1], "## Verdict")
        self.assertIn("**blocked**", text)
        self.assertLess(text.index("## Verdict"), text.index("## Defects (errors)"))
        self.assertIn("selection.no_denominator", text)

    def test_completely_empty_spec_is_blocked_not_a_crash(self):
        report = audit({})
        self.assertEqual(report["verdict"], "blocked")

    def test_hostile_types_do_not_crash(self):
        report = audit({"spec_version": "1", "measurement": {"species": "proton", "range": "wide"}, "selections": "none",
                        "corrections": [1, None], "systematics": [None], "parameters": ["x"], "ams_claims": [3]})
        self.assertEqual(report["verdict"], "blocked")


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = aas.main(list(argv))
        return code, buf.getvalue()

    def test_valid_spec_exit_0(self):
        code, out = self.run_cli(str(FIX / "spec_valid.json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["verdict"], "acceptable with open inputs")

    def test_defective_spec_exit_1_and_markdown(self):
        doc = spec()
        doc["corrections"].append({"effect_id": "livetime", "category": "veto", "applied_in": "estimator"})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(Path(fh.name).unlink)
        code, out = self.run_cli(fh.name)
        self.assertEqual(code, 1)
        self.assertIn("correction.double_applied", out)
        code, out = self.run_cli(fh.name, "--markdown")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("# Analysis review"))

    def test_strict_fails_on_warnings(self):
        doc = spec()
        doc["backgrounds"][0].pop("closure_test")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(Path(fh.name).unlink)
        self.assertEqual(self.run_cli(fh.name)[0], 0)
        self.assertEqual(self.run_cli(fh.name, "--strict")[0], 1)

    def test_unreadable_and_non_object_exit_2(self):
        self.assertEqual(self.run_cli(str(FIX / "missing.json"))[0], 2)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("[1, 2]")
        self.addCleanup(Path(fh.name).unlink)
        self.assertEqual(self.run_cli(fh.name)[0], 2)

    def test_no_claims_flag(self):
        doc = spec()
        doc["parameters"][0]["claim_ids"] = ["C999"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(Path(fh.name).unlink)
        self.assertEqual(self.run_cli(fh.name)[0], 1)
        self.assertEqual(self.run_cli(fh.name, "--no-claims")[0], 0)


if __name__ == "__main__":
    unittest.main()
