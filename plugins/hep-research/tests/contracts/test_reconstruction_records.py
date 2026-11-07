"""The record sidecars of the reconstruction contracts (contract-map.md): reconstruction_recipe, binding_evidence,
selection_record and input signature, with scenarios A02, A16, A18, the contract parts of A03, A22 and A25, and the
recorded use of payloads (R32). Selection and recognition behaviour belongs to T14 and T15; here only their records are
readable and honest. Synthetic documents only."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import check_rebinding, check_recipe_evidence, read_sidecar, recipe_identity, runnable  # noqa: E402
from contracts.schema import validate  # noqa: E402
from tests.contracts.reconstruction_fixtures import (association_product, association_witness, binding_evidence,  # noqa: E402
                                                     bound_payload, calibration_payload, code_list, constraint_product,
                                                     constraint_witness, evidence_check, input_signature, measurement, port, product,
                                                     proposal_recipe, recipe, selection_record, signature_fact, used_payload)


class Recipes(unittest.TestCase):
    def test_recipe_is_read(self):
        self.assertEqual(code_list(read_sidecar(recipe())), [])

    def test_an_old_recipe_is_not_a_reconstruction_recipe(self):
        """R09: the same word, a different thing."""
        old = json.loads((ROOT / "contracts/semantics/recipes/flux_from_counts.json").read_text(encoding="utf-8"))
        self.assertEqual(code_list(read_sidecar(old)), ["reconstruction.reader.unknown_format"])
        self.assertFalse(validate(recipe(), "recipe.json").ok)

    def test_reproducibility_form_is_declared(self):
        """Minor 15: the corrected text of analysis-workflows.md attaches here."""
        document = recipe()
        del document["reproducibility"]
        self.assertTrue(code_list(read_sidecar(document)))
        self.assertIn("reconstruction.recipe.comparators_missing", code_list(read_sidecar(recipe(reproducibility={"form": "statistical", "comparators": []}))))
        self.assertEqual(code_list(read_sidecar(recipe(reproducibility={"form": "byte", "comparators": []}))), [])

    def test_port_with_an_unknown_required_extension_stops_the_reader(self):
        document = recipe(inputs=[port("input", required_extensions=["reconstruction:future-semantics-v9"])], recipe_id=None)
        self.assertEqual(code_list(read_sidecar(document)), ["reconstruction.reader.unknown_required_extension"])

    def test_output_port_must_be_an_output(self):
        self.assertIn("reconstruction.recipe.port_direction", code_list(read_sidecar(recipe(outputs=[port("input")]))))

    def test_same_source_summaries_are_not_assumed_independent(self):
        first, second = port("input", port_id="port.first", source_ref="source-1"), port("input", port_id="port.second", source_ref="source-1")
        document = recipe(inputs=[first, second], independent_inputs=[["port.first", "port.second"]])
        self.assertIn("reconstruction.recipe.same_source_independent", code_list(read_sidecar(document)))
        second["source_ref"] = "source-2"
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_lossy_converter_is_recorded(self):
        converter = {"converter_id": "converter.pack", "version": "1.0.0", "input": port()["quantity"], "output": port()["quantity"],
                     "uncertainty_handling": "propagated", "association_handling": "kept", "cost": "one pass", "information_loss": True}
        self.assertIn("reconstruction.converter.loss_unrecorded", code_list(read_sidecar(recipe(converters=[converter]))))


class ProfileSwitch(unittest.TestCase):
    """A02: rebind device conditions and check the support domain, without duplicating the method card."""

    def rebound(self):
        document = recipe()
        document["profile_binding"]["profile_id"] = "synthetic-profile-b"
        document["profile_binding"]["conditions"] = [bound_payload(calibration_payload("3"))]
        return document

    def test_same_card_with_other_conditions_rebinds(self):
        self.assertEqual(code_list(check_rebinding(recipe(), self.rebound())), [])

    def test_rebinding_changes_the_profile(self):
        """Minor 12."""
        other = self.rebound()
        other["profile_binding"]["profile_id"] = recipe()["profile_binding"]["profile_id"]
        self.assertIn("reconstruction.recipe.profile_not_rebound", code_list(check_rebinding(recipe(), other)))

    def test_rebinding_checks_the_new_support_domain(self):
        """Minor 12."""
        other = self.rebound()
        other["profile_binding"]["request"]["rate"] = 99
        self.assertIn("reconstruction.recipe.outside_support_domain", code_list(check_rebinding(recipe(), other)))

    def test_every_support_axis_is_requested(self):
        """Minor 12."""
        document = recipe()
        document["profile_binding"]["request"] = {}
        self.assertIn("reconstruction.recipe.request_incomplete", code_list(read_sidecar(document)))

    def test_nothing_to_rebind_is_not_a_refusal(self):
        """Re-review 2 minor 13."""
        first, second = recipe(), self.rebound()
        first["profile_binding"]["conditions"], second["profile_binding"]["conditions"] = [], []
        self.assertEqual(code_list(check_rebinding(first, second)), [])

    def test_changed_card_is_not_a_rebinding(self):
        other = self.rebound()
        other["method"]["card_sha256"] = "e" * 64
        self.assertIn("reconstruction.recipe.method_card_changed", code_list(check_rebinding(recipe(), other)))

    def test_unchanged_conditions_are_not_a_rebinding(self):
        self.assertIn("reconstruction.recipe.conditions_not_rebound", code_list(check_rebinding(recipe(), recipe())))

    def test_method_text_cannot_be_copied_into_a_binding(self):
        document = recipe()
        document["method"]["blueprint_text"] = "a copy of the method card"
        self.assertTrue(code_list(read_sidecar(document)))

    def test_request_outside_the_support_domain_is_refused(self):
        document = recipe()
        document["profile_binding"]["request"]["rate"] = 11
        self.assertIn("reconstruction.recipe.outside_support_domain", code_list(read_sidecar(document)))
        document["profile_binding"]["request"] = {"energy": 1}
        self.assertIn("reconstruction.recipe.outside_support_domain", code_list(read_sidecar(document)))

    def test_a_binding_has_no_consumed_round(self):
        """Re-review minor 9: R32 and R36 say products; a recipe is bound before anything consumed a payload."""
        self.assertNotIn("round", recipe()["profile_binding"]["conditions"][0])
        self.assertEqual(code_list(read_sidecar(recipe())), [])

    def test_binding_records_identities_not_tags(self):
        document = recipe()
        del document["profile_binding"]["conditions"][0]["payload_id"]
        self.assertTrue(code_list(read_sidecar(document)))


class ConceptualQuestions(unittest.TestCase):
    """A16, contract part: a proposal starts no backend. The routing side is the G01 text and T14."""

    def test_proposal_is_read_and_is_not_runnable(self):
        self.assertEqual(code_list(read_sidecar(proposal_recipe())), [])
        self.assertFalse(runnable(proposal_recipe()))
        self.assertTrue(runnable(recipe()))

    def test_proposal_with_a_command_is_refused(self):
        document = proposal_recipe()
        document["command"] = ["synthetic-entry"]
        self.assertIn("reconstruction.recipe.proposal_not_executable", code_list(read_sidecar(document)))

    def test_a_proposal_may_leave_its_form_and_domain_null(self):
        """Re-review minor 8, Section 8.7: "null must not be filled with a guessed backend"."""
        document = proposal_recipe()
        document["reproducibility"] = None
        document["profile_binding"].update({"support_domain": {}, "request": {}})
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_only_a_proposal_may_leave_them_null(self):
        """Re-review minor 8; G03: other recipes declare their form."""
        document = recipe(reproducibility=None)
        self.assertEqual(code_list(read_sidecar(document)), ["reconstruction.recipe.reproducibility_undeclared"])
        document = recipe(status="routine", evidence_ref="evidence.linear-pulse")
        document["profile_binding"].update({"support_domain": {}, "request": {}})
        self.assertEqual(code_list(read_sidecar(document)), ["reconstruction.recipe.request_incomplete"], "Section 8.4 check 6: routine use has a domain")

    def test_a_pilot_or_a_proposal_may_have_no_domain_yet(self):
        """Re-review 2 minor 13: Section 8.4 judges pilots separately, and Section 8.7 keeps unknowns."""
        for document in (recipe(), proposal_recipe()):
            document["profile_binding"].update({"support_domain": {}, "request": {"rate": 1}})
            self.assertEqual(code_list(read_sidecar(document)), [])

    def test_null_backend_is_not_filled_by_a_guess(self):
        document = recipe()
        document["implementation"]["backend"] = None
        self.assertIn("reconstruction.recipe.proposal_not_executable", code_list(read_sidecar(document)))


class LegacySerializedBackend(unittest.TestCase):
    """A18: integrate safely, without configuring an unsupported reentrant mode."""

    def test_one_slot_is_safe(self):
        self.assertEqual(code_list(read_sidecar(recipe())), [])

    def test_more_slots_on_a_serialized_backend_are_refused(self):
        document = recipe(execution={"concurrency": "serialized", "slots": 4})
        self.assertIn("reconstruction.recipe.reentrant_on_serialized", code_list(read_sidecar(document)))

    def test_reentrant_backend_may_use_more_slots(self):
        self.assertEqual(code_list(read_sidecar(recipe(execution={"concurrency": "reentrant", "slots": 4}))), [])


class Evidence(unittest.TestCase):
    def test_evidence_is_read(self):
        self.assertEqual(code_list(read_sidecar(binding_evidence())), [])

    def test_it_is_never_a_deployment_guarantee(self):
        document = binding_evidence()
        document["deployment_guarantee"] = True
        self.assertTrue(code_list(read_sidecar(document)))

    def test_passed_needs_every_check_passed(self):
        for state in ("fail", "inconclusive", "skipped", "not-applicable"):
            document = binding_evidence(checks=[evidence_check(state=state)])
            self.assertIn("reconstruction.evidence.pass_without_checks", code_list(read_sidecar(document)), state)
        self.assertIn("reconstruction.evidence.pass_without_checks", code_list(read_sidecar(binding_evidence(checks=[]))))

    def test_a_skip_beside_a_pass_is_judged_against_the_recipe(self):
        """Re-review 2 minor 14: Section 9.8 bars a pass made of skips; a skip the recipe does not require blocks nothing."""
        for state in ("skipped", "not-applicable"):
            self.assertEqual(code_list(read_sidecar(binding_evidence(checks=[evidence_check(), evidence_check("extra", state)]))), [], state)
        document = recipe(status="routine", evidence_ref="evidence.linear-pulse", checks=["witness.linear-pulse", "extra"])
        evidence = binding_evidence(checks=[evidence_check(), evidence_check("extra", "skipped")])
        evidence["recipe_sha256"] = recipe_identity(document)
        self.assertEqual(code_list(check_recipe_evidence(document, evidence)), ["reconstruction.recipe.required_check_not_evidenced"])

    def test_failed_evidence_stays_failed(self):
        document = binding_evidence("failed", [evidence_check(state="fail")])
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_routine_use_needs_passed_evidence(self):
        document = recipe(status="routine")
        self.assertIn("reconstruction.recipe.routine_without_evidence", code_list(read_sidecar(document)))
        document["evidence_ref"] = "evidence.linear-pulse"
        self.assertEqual(code_list(read_sidecar(document)), [])
        self.assertEqual(code_list(check_recipe_evidence(document, binding_evidence())), [])
        failed = binding_evidence("inconclusive", [evidence_check(state="inconclusive")])
        self.assertIn("reconstruction.recipe.evidence_not_passed", code_list(check_recipe_evidence(document, failed)))
        other = dict(binding_evidence(), recipe_id="recipe.other")
        self.assertIn("reconstruction.recipe.evidence_not_passed", code_list(check_recipe_evidence(document, other)))

    def test_changed_recipe_does_not_inherit_evidence(self):
        """M7, Section 17.3."""
        document = recipe(status="routine", evidence_ref="evidence.linear-pulse")
        self.assertEqual(code_list(check_recipe_evidence(document, binding_evidence())), [])
        document["preconditions"] = ["another precondition"]
        self.assertIn("reconstruction.recipe.evidence_of_another_recipe", code_list(check_recipe_evidence(document, binding_evidence())))

    def test_identity_ignores_only_what_evidence_itself_changes(self):
        self.assertEqual(recipe_identity(recipe()), recipe_identity(recipe(status="routine", evidence_ref="evidence.linear-pulse")))
        self.assertNotEqual(recipe_identity(recipe()), recipe_identity(recipe(checks=[])))

    def routine(self, **fields):
        return recipe(status="routine", evidence_ref="evidence.linear-pulse", **fields)

    def test_a_request_inside_the_tested_domain_keeps_its_evidence(self):
        """RM2, Section 8.4 check 6: "the tested domain must cover the request"."""
        document = self.routine()
        document["profile_binding"]["request"]["rate"] = 6
        self.assertEqual(code_list(check_recipe_evidence(document, binding_evidence())), [])

    def test_a_changed_support_domain_loses_its_evidence(self):
        """RM2: the request leaves the identity, the support domain stays in it."""
        document = self.routine()
        document["profile_binding"]["support_domain"]["rate"]["max"] = 20
        self.assertEqual(code_list(check_recipe_evidence(document, binding_evidence())), ["reconstruction.recipe.evidence_of_another_recipe"])

    def test_a_request_outside_the_tested_domain_is_refused(self):
        """RM1, Section 8.4 check 6: inside the support domain, outside what was tested."""
        document = self.routine()
        self.assertEqual(code_list(check_recipe_evidence(document, binding_evidence(tested=(0, 4)))), ["reconstruction.recipe.request_outside_tested_domain"])

    def test_an_axis_never_tested_is_refused(self):
        """RM1."""
        evidence = binding_evidence()
        evidence["scope"]["tested_domain"] = {"temperature": {"min": 0, "max": 1}}
        self.assertEqual(code_list(check_recipe_evidence(self.routine(), evidence)), ["reconstruction.recipe.request_outside_tested_domain"])

    def test_scope_is_read(self):
        """RM1: the refusal quotes the evidence's own statement of what it tested."""
        report = check_recipe_evidence(self.routine(), binding_evidence(tested=(0, 4)))
        self.assertIn("synthetic fixture only", report.errors[0].message)

    def test_evidence_for_other_checks_supports_nothing(self):
        """RM1: the re-review's probe."""
        document = self.routine(checks=["check.a", "check.b"])
        evidence = binding_evidence(checks=[evidence_check("unrelated")])
        evidence["recipe_sha256"] = recipe_identity(document)
        self.assertEqual(code_list(check_recipe_evidence(document, evidence)), ["reconstruction.recipe.required_check_not_evidenced"] * 2)
        evidence["checks"] = [evidence_check("check.a"), evidence_check("check.b"), evidence_check("unrelated")]
        self.assertEqual(code_list(check_recipe_evidence(document, evidence)), [])

    def test_a_check_that_cannot_be_constructed_is_refused(self):
        """RM1, Section 8.4 check 6: "required checks and denominators must be constructible"."""
        evidence = binding_evidence(checks=[evidence_check(constructible=False)])
        self.assertEqual(code_list(check_recipe_evidence(self.routine(), evidence)), ["reconstruction.recipe.required_check_not_constructible"])

    def test_passed_simulation_pilot_is_allowed_inside_its_domain(self):
        """The plan names no minimum stage above witness and smoke; the ruling keeps it, under check 6 only."""
        self.assertEqual(code_list(check_recipe_evidence(self.routine(), binding_evidence(stage="simulation-pilot"))), [])

    def test_a_witness_or_smoke_run_does_not_support_routine_use(self):
        """M7, Section 12.1: no automatic promotion between levels."""
        document = recipe(status="routine", evidence_ref="evidence.linear-pulse")
        for stage in ("artificial-witness", "backend-smoke"):
            self.assertIn("reconstruction.recipe.evidence_stage_insufficient", code_list(check_recipe_evidence(document, binding_evidence(stage=stage))), stage)


class Selection(unittest.TestCase):
    def test_undecided_record_is_read(self):
        self.assertEqual(code_list(read_sidecar(selection_record())), [])

    def test_undecided_record_names_no_recipe(self):
        self.assertIn("reconstruction.selection.choice_without_decision", code_list(read_sidecar(selection_record(chosen_recipe="recipe.linear-pulse"))))

    def test_selected_recipe_is_a_candidate_with_evidence(self):
        document = selection_record(state="selected", chosen_recipe="recipe.other")
        self.assertIn("reconstruction.selection.unknown_choice", code_list(read_sidecar(document)))
        document = selection_record(state="selected", chosen_recipe="recipe.linear-pulse")
        self.assertIn("reconstruction.selection.choice_without_evidence", code_list(read_sidecar(document)))
        document["candidates"][0]["quality_evidence"] = "evidence.linear-pulse"
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_qualified_default_needs_no_quality_claim(self):
        self.assertEqual(code_list(read_sidecar(selection_record(state="qualified-default", chosen_recipe="recipe.linear-pulse"))), [])

    def test_a_decided_record_keeps_its_exclusion_reasons(self):
        document = selection_record()
        del document["candidates"][0]["exclusion_or_probe_reason"]
        self.assertTrue(code_list(read_sidecar(document)))

    def test_granularity_is_never_per_event(self):
        document = selection_record()
        document["policy"]["granularity"] = "event"
        self.assertTrue(code_list(read_sidecar(document)), "K16: a per-event policy is a separate recipe")


class Signature(unittest.TestCase):
    def test_signature_is_read_and_multi_label(self):
        self.assertEqual(code_list(read_sidecar(input_signature(family_candidates=["family-a", "family-b"]))), [])

    def test_file_names_shapes_and_confidence_are_not_evidence(self):
        for kind in ("file-name", "array-shape", "model-confidence"):
            self.assertIn("reconstruction.signature.not_evidence", code_list(read_sidecar(input_signature([signature_fact(kind=kind)]))), kind)

    def test_extracted_value_stays_a_declaration(self):
        self.assertIn("reconstruction.signature.unconfirmed_fact", code_list(read_sidecar(input_signature([signature_fact(kind="llm-extraction")]))))
        self.assertEqual(code_list(read_sidecar(input_signature([signature_fact(kind="llm-extraction", method="declared")]))), [])

    def test_conflicts_stay_visible(self):
        facts = [signature_fact(), signature_fact(value="image")]
        self.assertIn("reconstruction.signature.hidden_conflict", code_list(read_sidecar(input_signature(facts))))
        self.assertEqual(code_list(read_sidecar(input_signature(facts, conflicts=["representation"]))), [])


class MissingConstraint(unittest.TestCase):
    """A03, A25, contract parts: alternatives come first, and restriction only when information stays insufficient."""

    def test_qualified_internal_constraint_gives_full_delivery(self):
        self.assertEqual(code_list(read_sidecar(constraint_product())), [])

    def test_insufficient_information_gives_restricted_delivery(self):
        resolution = constraint_witness("restricted", sufficient=False)
        self.assertEqual(code_list(read_sidecar(constraint_product(resolution))), [])

    def test_restriction_while_a_qualified_constraint_suffices_is_refused(self):
        resolution = constraint_witness("restricted")
        self.assertIn("reconstruction.constraint.needless_restriction", code_list(read_sidecar(constraint_product(resolution))))

    def test_restriction_before_checking_alternatives_is_refused(self):
        resolution = constraint_witness("restricted")
        resolution["internal"] = []
        self.assertIn("reconstruction.constraint.alternatives_not_checked", code_list(read_sidecar(constraint_product(resolution))))

    def test_full_delivery_without_information_is_refused(self):
        for resolution in (constraint_witness(sufficient=False), constraint_witness(internal="unqualified")):
            self.assertIn("reconstruction.constraint.full_without_information", code_list(read_sidecar(constraint_product(resolution))))

    def test_external_constraint_alone_is_enough(self):
        resolution = constraint_witness(external="available", sufficient=False)
        self.assertEqual(code_list(read_sidecar(constraint_product(resolution))), [])

    def test_joint_constraint_counts(self):
        resolution = constraint_witness(sufficient=False)
        resolution["joint"] = [{"name": "joint-fit", "state": "qualified", "sufficient": True}]
        self.assertEqual(code_list(read_sidecar(constraint_product(resolution))), [])

    def test_full_delivery_carries_no_restriction(self):
        """Minor 9."""
        resolution = constraint_witness()
        resolution["restriction"] = {"omits": ["absolute position"], "reason": "stated"}
        self.assertIn("reconstruction.constraint.restriction_on_full", code_list(read_sidecar(constraint_product(resolution))))

    def test_restriction_states_what_it_omits(self):
        resolution = constraint_witness("restricted", sufficient=False)
        resolution["restriction"] = None
        self.assertIn("reconstruction.constraint.restriction_unstated", code_list(read_sidecar(constraint_product(resolution))))


class Associations(unittest.TestCase):
    """A22, contract part: each sensor kind keeps its respective response, and states a time base and window."""

    def test_witness_is_read(self):
        self.assertEqual(code_list(read_sidecar(association_product())), [])

    def test_one_response_for_two_kinds_is_refused(self):
        """A22: each kind associates through its respective response."""
        association = association_witness()
        association["members"][1]["response_ref"] = association["members"][0]["response_ref"]
        self.assertIn("reconstruction.association.shared_response", code_list(read_sidecar(association_product(association))))

    def test_one_timing_reference_for_two_kinds_is_allowed(self):
        """M9: neither A22 nor the contract map says the time bases must differ."""
        association = association_witness()
        association["members"][1]["time_base"] = association["members"][0]["time_base"]
        self.assertEqual(code_list(read_sidecar(association_product(association))), [])

    def test_time_base_and_window_are_stated(self):
        for field in ("time_base", "time_window"):
            association = association_witness()
            del association["members"][0][field]
            self.assertTrue(code_list(read_sidecar(association_product(association))), field)


class RecordedConditions(unittest.TestCase):
    """R32: every product records the identity and round of each payload it consumed."""

    def test_product_records_identity_and_round(self):
        payload = calibration_payload(loop={"family": "synthetic-loop", "round": 2})
        document = product(objects=[measurement(0)], conditions_used=[used_payload(payload)])
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_a_product_must_state_what_it_consumed(self):
        """B3: an empty list is a statement; a missing field is not."""
        document = product(objects=[measurement(0)])
        self.assertEqual(code_list(read_sidecar(document)), [])
        del document["conditions_used"]
        self.assertTrue(code_list(read_sidecar(document)))

    def test_the_round_field_is_required(self):
        """B3."""
        payload = calibration_payload(loop={"family": "synthetic-loop", "round": 2})
        record = used_payload(payload)
        del record["round"]
        self.assertTrue(code_list(read_sidecar(product(objects=[measurement(0)], conditions_used=[record]))))

    def test_a_tag_alone_is_refused(self):
        document = product(objects=[measurement(0)], conditions_used=[{"slot": "gain", "tag": "synthetic_gain_tag", "origin": "measured", "round": None}])
        self.assertTrue(code_list(read_sidecar(document)))


if __name__ == "__main__":
    unittest.main()
