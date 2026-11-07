"""T15a: finite candidate index and replayable selection, on artificial fixtures only (plan Section 5.14, DS1-DS3; A47, A52,
A60; K16: every value here is artificial and tests rules, not recipes)."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import candidate_selection  # noqa: E402
from contracts.candidate_selection import check_selection_replay, select_candidate  # noqa: E402
from contracts.input_inspector import inspect_inputs  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402
from tests.contracts.reconstruction_fixtures import (ARTIFICIAL_COST_UNIT, REQUIRED_CHECK, SCHEMA_CONDITION, artificial_evidence, artificial_inspection, artificial_recipe, calibration_payload,  # noqa: E402
                                                     candidate_index, code_list, constraint_product, consumer, constraint_witness, quality_first_witness, hybrid_policy_witness, evidence_check, index_row, measurement, product, selection_policy, selection_record, used_payload)

INSPECTION = artificial_inspection()
SIGNATURE_ID = INSPECTION["signatures"][0]["signature_id"]
NO_QUALIFIED = "no qualified candidate"


def selected(witness, inspection=None, signature_id=None):
    return select_candidate(signature_id or SIGNATURE_ID, inspection or INSPECTION, **witness)


def rows_of(record) -> dict:
    return {row["recipe"]: row for row in record["formal"]["judgments"]}


class NecessaryQualityPrecedesSpeed(unittest.TestCase):
    """Section 5.14, DS1; Section 5.9 item 1."""

    def test_the_reference_is_selected_and_the_faster_two_are_not(self):
        record = selected(quality_first_witness())
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("selected", "recipe.c-reference"))
        judged = rows_of(record)
        self.assertEqual(judged["recipe.c-fast"]["standing"], "excluded")
        self.assertEqual(judged["recipe.c-fast"]["blocks"], ["quality-failed"])
        self.assertEqual(judged["recipe.c-unknown"]["standing"], "qualification-candidate")
        self.assertEqual(record["formal"]["qualification_candidates"], ["recipe.c-unknown"])

    def test_a_cost_cap_of_2_gives_no_qualified_candidate(self):
        record = selected(quality_first_witness(cap=2))
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertIn(record["decision"]["state"], ("abstained", "needs-evidence"))
        self.assertTrue(record["decision"]["reason"].startswith(NO_QUALIFIED))
        self.assertEqual(rows_of(record)["recipe.c-reference"]["blocks"], ["over-budget"])

    def test_every_form_of_a_failed_required_check_excludes(self):
        """Section 5.9 item 1: nothing compensates, however cheap."""
        for state, check_state in (("failed", "fail"), ("failed", "pass"), ("inconclusive", "fail"), ("unvalidated", "fail")):
            witness = quality_first_witness()
            witness["evidence"][0] = artificial_evidence(witness["recipes"][0], state, check_state)
            record = selected(witness)
            self.assertEqual(rows_of(record)["recipe.c-fast"]["blocks"], ["quality-failed"], (state, check_state))
            self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-reference", (state, check_state))

    def test_every_form_of_insufficient_evidence_keeps_a_candidate_out_of_the_routine_set(self):
        """DS1, c_unknown; SEL06. One defect each on otherwise valid evidence for the cheapest candidate."""
        def candidate(**fields):
            return artificial_recipe("c-unknown", **fields)
        routine = candidate()
        other = artificial_recipe("c-other")
        cases = {"inconclusive": artificial_evidence(routine, "inconclusive", "inconclusive"), "unvalidated": artificial_evidence(routine, "unvalidated", "inconclusive"),
                 "backend smoke only": artificial_evidence(routine, stage="backend-smoke"),
                 "another recipe": dict(artificial_evidence(other), evidence_id="evidence.c-unknown"),
                 "another version": dict(artificial_evidence(routine), recipe_sha256="e" * 64),
                 "outside the tested domain": dict(artificial_evidence(routine), scope={"statement": "artificial fixture only", "tested_domain": {"rate": {"min": 6, "max": 10}}}),
                 "axis not tested": dict(artificial_evidence(routine), scope={"statement": "artificial fixture only", "tested_domain": {}}),
                 "check not constructible": dict(artificial_evidence(routine), checks=[evidence_check(REQUIRED_CHECK, "pass", False)]),
                 "required check skipped": dict(artificial_evidence(routine), checks=[evidence_check("artificial.other"), evidence_check(REQUIRED_CHECK, "skipped")]),
                 "required check absent": dict(artificial_evidence(routine), checks=[evidence_check("artificial.other")]),
                 "evidence not supplied": None}
        for name, evidence in cases.items():
            witness = quality_first_witness()
            witness["recipes"][2] = routine
            witness["index"]["candidates"][2] = index_row(routine, 0.5)
            witness["evidence"] += [] if evidence is None else [evidence]
            record = selected(witness)
            self.assertEqual(code_list(read_sidecar(record)), [], name)
            self.assertEqual(rows_of(record)["recipe.c-unknown"]["blocks"], ["insufficient-evidence"], name)
            self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-reference", name)

    def test_failed_evidence_of_another_recipe_or_version_says_nothing_about_this_one(self):
        """Section 17.3: a changed recipe inherits nothing, failures included: it is unknown, not failed."""
        routine, other = artificial_recipe("c-unknown"), artificial_recipe("c-other")
        for name, evidence in (("another recipe", dict(artificial_evidence(other, "failed", "fail"), evidence_id="evidence.c-unknown")), ("another version", dict(artificial_evidence(routine, "failed", "fail"), recipe_sha256="e" * 64))):
            witness = quality_first_witness()
            witness["recipes"][2] = routine
            witness["index"]["candidates"][2] = index_row(routine, 0.5)
            witness["evidence"].append(evidence)
            record = selected(witness)
            self.assertEqual(rows_of(record)["recipe.c-unknown"]["blocks"], ["insufficient-evidence"], name)
            self.assertIsNone(record["candidates"][2]["quality_evidence"], name)

    def test_a_development_recipe_with_passed_evidence_stays_a_qualification_candidate(self):
        """Section 5.10: a pilot stays unqualified until it is routine."""
        witness = quality_first_witness()
        development = artificial_recipe("c-unknown", status="development")
        witness["recipes"][2] = development
        witness["index"]["candidates"][2] = index_row(development, 0.5)
        witness["evidence"].append(artificial_evidence(development))
        self.assertEqual(selected(witness)["decision"]["chosen_recipe"], "recipe.c-reference")

    def test_honest_variations_still_select_the_reference(self):
        """Other evidence stages, other caps at and above its cost, more checks passed, and a cheaper rival that is out."""
        for cap in (4, 5, 4.5, 100):
            self.assertEqual(selected(quality_first_witness(cap=cap))["decision"]["chosen_recipe"], "recipe.c-reference", cap)
        witness = quality_first_witness()
        witness["evidence"][1] = dict(witness["evidence"][1], checks=[evidence_check(REQUIRED_CHECK), evidence_check("artificial.other", "skipped"), evidence_check("artificial.another", "not-applicable")])
        self.assertEqual(selected(witness)["decision"]["chosen_recipe"], "recipe.c-reference")
        witness = quality_first_witness()
        witness["evidence"][1] = artificial_evidence(witness["recipes"][1], stage="simulation-pilot")
        self.assertEqual(selected(witness)["decision"]["chosen_recipe"], "recipe.c-reference")

    def test_a_recipe_with_no_required_check_is_not_qualified(self):
        """C3 review, M2. Section 5.14: "pass all necessary conditions and quality checks"; an empty list is not vacuously true, here as in Section 5.8."""
        witness = quality_first_witness()
        fast = artificial_recipe("c-fast", checks=[])
        witness["recipes"][0] = fast
        witness["index"]["candidates"][0] = index_row(fast, 1)
        witness["evidence"][0] = artificial_evidence(fast, checks=[evidence_check("artificial.other"), evidence_check(REQUIRED_CHECK, "skipped")])
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.c-fast"]["blocks"], ["insufficient-evidence"])
        self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-reference")

    def narrow_candidate(self, state, *rows):
        """A recipe whose own list is narrower than the contract: the tail is required by the contract alone."""
        document = artificial_recipe("c-narrow", checks=["artificial.other"])
        return selected(one_candidate(document, [artificial_evidence(document, state, checks=[evidence_check("artificial.other")] + list(rows))]))

    def test_a_check_only_the_contract_requires_excludes_when_it_fails(self):
        """C3 re-review, R2. Section 5.14, DS1: "Required tail check fails", "Exclude; speed cannot compensate for quality"."""
        for state in ("inconclusive", "unvalidated"):
            record = self.narrow_candidate(state, evidence_check(REQUIRED_CHECK, "fail"))
            judged = rows_of(record)["recipe.c-narrow"]
            self.assertEqual((judged["blocks"], judged["standing"], judged["open"]), (["quality-failed"], "excluded", []), state)
            self.assertEqual(record["decision"]["state"], "abstained", state)
            self.assertEqual(record["formal"]["qualification_candidates"], [], state)

    def test_a_check_only_the_recipe_requires_excludes_when_it_fails(self):
        """The other half of the same rule: DS1 asks of a required check, whichever list requires it."""
        document = artificial_recipe("c-own", checks=[REQUIRED_CHECK, "artificial.own"])
        checks = [evidence_check(REQUIRED_CHECK), evidence_check("artificial.own", "fail")]
        record = selected(one_candidate(document, [artificial_evidence(document, "inconclusive", checks=checks)]))
        self.assertEqual(rows_of(record)["recipe.c-own"]["blocks"], ["quality-failed"])

    def test_an_unfinished_required_check_is_missing_evidence_not_a_failure(self):
        """DS1: "Required quality evidence still insufficient", "Not in the routine set; may be listed separately as a qualification candidate".
        Section 8.4 check 6 names failed, inconclusive and unvalidated as three states, and only a fail is a failed check."""
        for state, row_state in (("inconclusive", "inconclusive"), ("unvalidated", "inconclusive"), ("inconclusive", "skipped"), ("unvalidated", "not-applicable")):
            judged = rows_of(self.narrow_candidate(state, evidence_check(REQUIRED_CHECK, row_state)))["recipe.c-narrow"]
            self.assertEqual((judged["blocks"], judged["standing"]), (["insufficient-evidence"], "qualification-candidate"), (state, row_state))
            self.assertIn(REQUIRED_CHECK, judged["open"], (state, row_state))

    def test_a_failed_check_nothing_requires_is_no_exclusion(self):
        document = artificial_recipe("c-side")
        checks = [evidence_check(REQUIRED_CHECK), evidence_check("artificial.side", "fail")]
        record = selected(one_candidate(document, [artificial_evidence(document, "inconclusive", checks=checks)]))
        self.assertEqual(rows_of(record)["recipe.c-side"]["blocks"], ["insufficient-evidence"], "the evidence as a whole stays inconclusive")

    def test_evidence_that_failed_as_a_whole_excludes_with_no_failed_row(self):
        document = artificial_recipe("c-whole")
        self.assertEqual(rows_of(selected(one_candidate(document, [artificial_evidence(document, "failed", "inconclusive")])))["recipe.c-whole"]["blocks"], ["quality-failed"])

    def test_a_recipe_with_no_required_check_says_so_in_the_record(self):
        """C3 re-review, r2: the coordinator's ruling keeps this insufficient, and a restriction names what is missing (Section 5.6 item 5)."""
        document = artificial_recipe("c-empty", checks=[])
        record = selected(one_candidate(document, [artificial_evidence(document)]))
        self.assertEqual(rows_of(record)["recipe.c-empty"]["open"], ["no required check stated by the recipe"])

    def test_a_null_contract_does_not_let_an_empty_list_through(self):
        document = artificial_recipe("c-empty", checks=[])
        witness = one_candidate(document, [artificial_evidence(document, checks=[evidence_check("artificial.other")])], cap=None, quality_contract=None, baseline="recipe.c-empty")
        self.assertIsNone(selected(witness)["decision"]["chosen_recipe"])

    def test_the_contract_is_compared_with_what_the_evidence_covers(self):
        """Section 8.4 check 6 and the T06 reading: "required checks match and are constructible". One pass of another id covers nothing."""
        for name, checks in (("another id", [evidence_check("artificial.other")]), ("skipped", [evidence_check("artificial.other"), evidence_check(REQUIRED_CHECK, "skipped")]),
                             ("not applicable", [evidence_check("artificial.other"), evidence_check(REQUIRED_CHECK, "not-applicable")]),
                             ("not constructible", [evidence_check("artificial.other"), evidence_check(REQUIRED_CHECK, "pass", False)])):
            document = artificial_recipe("c-narrow", checks=["artificial.other"])
            record = selected(one_candidate(document, [artificial_evidence(document, checks=checks)]))
            self.assertEqual(rows_of(record)["recipe.c-narrow"]["blocks"], ["insufficient-evidence"], name)
            self.assertIn(REQUIRED_CHECK, rows_of(record)["recipe.c-narrow"]["open"], name)
            self.assertIn(REQUIRED_CHECK, record["formal"]["restricted_delivery"]["open"], name)

    def test_every_check_of_the_contract_is_needed(self):
        document = artificial_recipe("c-partial")
        contract = {"contract_id": "artificial-quality-contract", "required_checks": [REQUIRED_CHECK, "artificial.second"]}
        record = selected(one_candidate(document, [artificial_evidence(document)], quality_contract=contract))
        self.assertEqual(rows_of(record)["recipe.c-partial"]["blocks"], ["insufficient-evidence"])

    def test_evidence_that_covers_the_contract_passes_with_more_checks_beside_it(self):
        document = artificial_recipe("c-wide", checks=[REQUIRED_CHECK, "artificial.second"])
        checks = [evidence_check(REQUIRED_CHECK), evidence_check("artificial.second"), evidence_check("artificial.third", "skipped")]
        record = selected(one_candidate(document, [artificial_evidence(document, checks=checks)]))
        self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-wide")
        self.assertEqual(record["policy"]["quality_contract"], "artificial-quality-contract")

    def test_a_contract_with_no_check_is_refused(self):
        witness = quality_first_witness()
        witness["policy"]["quality_contract"]["required_checks"] = []
        self.assertIsNone(selected(witness)["decision"]["chosen_recipe"])
        self.assertNotIn("formal", selected(witness))

    def test_an_expert_is_supported_only_as_far_as_the_contract_goes(self):
        witness = hybrid_policy_witness()
        witness["policy"]["quality_contract"]["required_checks"] = ["artificial.second"]
        self.assertEqual(selected(witness)["formal"]["claims"]["expert_support"], [])

    def test_the_order_of_the_index_decides_nothing(self):
        witness = quality_first_witness()
        witness["index"]["candidates"].reverse()
        self.assertEqual(selected(witness)["decision"]["chosen_recipe"], "recipe.c-reference")

    def test_the_cheaper_of_two_qualified_candidates_is_selected(self):
        cheap, dear = artificial_recipe("c-cheap"), artificial_recipe("c-dear")
        for rows in ([index_row(cheap, 2), index_row(dear, 3)], [index_row(dear, 3), index_row(cheap, 2)]):
            record = selected({"index": candidate_index([cheap, dear], rows), "policy": selection_policy(), "recipes": [cheap, dear], "evidence": [artificial_evidence(cheap), artificial_evidence(dear)]})
            self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("selected", "recipe.c-cheap"))
            self.assertIn("no global-best claim", record["decision"]["reason"])
            self.assertIs(record["formal"]["claims"]["global_best"], False)

    def test_the_cap_counts_the_shared_overhead(self):
        """Section 5.14: the zero is this fixture's; a stated overhead is charged."""
        witness = quality_first_witness()
        witness["policy"]["shared_overhead"]["value"] = 1.5
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.c-reference"]["blocks"], ["over-budget"])
        self.assertTrue(record["decision"]["reason"].startswith(NO_QUALIFIED))

    def test_the_cap_is_met_at_the_stated_tolerance_and_no_wider(self):
        for cost, overhead, cap, within in ((0.1, 0.2, 0.3, True), (5.000000000001, 0, 5, True), (5.0001, 0, 5, False), (4, 1, 5, True), (0, 0, 0, True), (1e-300, 0, 0, False)):
            document = artificial_recipe("c-edge")
            witness = one_candidate(document, [artificial_evidence(document)])
            witness["index"]["candidates"][0]["cost"]["value"] = cost
            witness["policy"]["shared_overhead"]["value"] = overhead
            witness["policy"]["objective"]["cap"]["value"] = cap
            self.assertEqual(selected(witness)["decision"]["chosen_recipe"] is not None, within, (cost, overhead, cap))

    def test_a_policy_cannot_widen_the_tolerance(self):
        witness = quality_first_witness()
        witness["policy"]["objective"]["tolerance"] = 1.0
        self.assertIsNone(selected(witness)["decision"]["chosen_recipe"])

    def test_an_unknown_or_foreign_cost_is_not_compared(self):
        """Fail closed: a cost that cannot be read against the cap is neither cheapest nor within it."""
        for cost in (None, {"value": 0.1, "unit": "seconds"}):
            witness = quality_first_witness()
            witness["index"]["candidates"][1]["cost"] = cost
            record = selected(witness)
            self.assertEqual(rows_of(record)["recipe.c-reference"]["blocks"], ["cost-unknown"], cost)
            self.assertIsNone(record["decision"]["chosen_recipe"], cost)
            self.assertEqual(record["decision"]["state"], "needs-evidence", cost)


def two_qualified(first_cost=2, second_cost=3, **policy_fields):
    cheap, dear = artificial_recipe("c-cheap"), artificial_recipe("c-dear")
    return {"index": candidate_index([cheap, dear], [index_row(cheap, first_cost), index_row(dear, second_cost)]), "policy": selection_policy(**policy_fields), "recipes": [cheap, dear],
            "evidence": [artificial_evidence(cheap), artificial_evidence(dear)]}


class DeclaredBaseline(unittest.TestCase):
    """Section 5.9 item 4, K16: with no single supported answer, the predeclared baseline, called a qualified default choice; DS1, last sentence."""

    def test_no_objective_returns_to_the_baseline(self):
        record = selected(two_qualified(cap=None, baseline="recipe.c-dear"))
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("qualified-default", "recipe.c-dear"))
        self.assertIn("qualified default choice", record["decision"]["reason"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_no_objective_and_no_baseline_delivers_options_and_no_choice(self):
        record = selected(two_qualified(cap=None))
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("abstained", None))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["objective-not-fixed"])
        self.assertEqual(record["formal"]["restricted_delivery"]["options"], ["recipe.c-cheap", "recipe.c-dear"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_no_quality_contract_means_no_fixed_objective(self):
        record = selected(two_qualified(quality_contract=None))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["objective-not-fixed"])
        record = selected(two_qualified(quality_contract=None, baseline="recipe.c-dear"))
        self.assertEqual(record["decision"]["state"], "qualified-default")

    def test_a_tie_at_the_tolerance_makes_no_winner(self):
        for second in (2, 2.0000000000001):
            record = selected(two_qualified(2, second))
            self.assertIsNone(record["decision"]["chosen_recipe"], second)
            self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["tied-within-tolerance"], second)
            record = selected(two_qualified(2, second, baseline="recipe.c-dear"))
            self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("qualified-default", "recipe.c-dear"), second)

    def test_a_clear_difference_is_no_tie(self):
        self.assertEqual(selected(two_qualified(2, 2.001, baseline="recipe.c-dear"))["decision"]["state"], "selected")

    def test_an_eligible_baseline_outside_the_tie_is_used(self):
        """Section 5.9 item 4 as written: "If evidence is insufficient or differences uncertain, use a predeclared conservative baseline/tie-break"."""
        cheap, dear, third = artificial_recipe("c-cheap"), artificial_recipe("c-dear"), artificial_recipe("c-third")
        witness = {"index": candidate_index([cheap, dear, third], [index_row(cheap, 2), index_row(dear, 2), index_row(third, 3)]), "policy": selection_policy(baseline="recipe.c-third"),
                   "recipes": [cheap, dear, third], "evidence": [artificial_evidence(cheap), artificial_evidence(dear), artificial_evidence(third)]}
        record = selected(witness)
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("qualified-default", "recipe.c-third"))
        self.assertEqual(code_list(read_sidecar(record)), [])
        witness["policy"]["baseline"] = None
        self.assertEqual(selected(witness)["formal"]["restricted_delivery"]["options"], ["recipe.c-cheap", "recipe.c-dear"], "the options stay the tied candidates")

    def test_an_ineligible_baseline_does_not_break_a_tie(self):
        """Glossary: a qualified baseline has its evidence. A declared one that failed is in the index, and is still no fallback."""
        cheap, dear, failed = artificial_recipe("c-cheap"), artificial_recipe("c-dear"), artificial_recipe("c-failed")
        witness = {"index": candidate_index([cheap, dear, failed], [index_row(cheap, 2), index_row(dear, 2), index_row(failed, 3)]), "policy": selection_policy(baseline="recipe.c-failed"),
                   "recipes": [cheap, dear, failed], "evidence": [artificial_evidence(cheap), artificial_evidence(dear), artificial_evidence(failed, "failed", "fail")]}
        record = selected(witness)
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(record["formal"]["restricted_delivery"]["options"], ["recipe.c-cheap", "recipe.c-dear"])
        self.assertIsNone(selected(two_qualified(2, 2, baseline="recipe.c-unlisted"))["decision"]["chosen_recipe"])

    def test_evidence_of_different_stages_is_not_ranked(self):
        """Section 5.9 item 2: evidence must align in measured stage."""
        witness = two_qualified()
        witness["evidence"][1] = artificial_evidence(witness["recipes"][1], stage="simulation-pilot")
        record = selected(witness)
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["evidence-not-comparable"])
        witness["policy"] = selection_policy(baseline="recipe.c-dear")
        self.assertEqual(selected(witness)["decision"]["state"], "qualified-default")

    def test_a_baseline_that_is_not_qualified_is_not_chosen(self):
        """Section 5.9 item 5: thresholds are not lowered to reach a declared name."""
        for baseline, cap in (("recipe.c-fast", 5), ("recipe.c-unknown", 5), ("recipe.c-reference", 2), ("recipe.not-indexed", 2)):
            witness = quality_first_witness(cap)
            witness["policy"]["baseline"] = baseline
            record = selected(witness)
            self.assertNotEqual(record["decision"]["chosen_recipe"], baseline, baseline)
            self.assertNotEqual(record["decision"]["state"], "qualified-default", baseline)


class AlternativeConstraintWitness(unittest.TestCase):
    """Section 5.14, DS2: schema && (external_constraint || qualified_internal_constraint); A47."""

    REQUIRES = {"all_of": [SCHEMA_CONDITION, {"any_of": [{"fact": "constraint.external.external-time-origin", "equals": "available"},
                                                        {"all_of": [{"fact": "constraint.internal.internal-time-constraint", "equals": "qualified"},
                                                                    {"fact": "constraint.internal.internal-time-constraint.sufficient", "equals": True}]}]}]}

    def judged(self, inspection):
        document = artificial_recipe("c-timed")
        witness = {"index": candidate_index([document], [index_row(document, 1, self.REQUIRES)]), "policy": selection_policy(), "recipes": [document], "evidence": [artificial_evidence(document)]}
        return selected(witness, inspection, inspection["signatures"][0]["signature_id"])

    def test_the_internal_branch_passes_and_is_named_with_external_missing(self):
        record = self.judged(artificial_inspection(constraint_product()))
        self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-timed")
        self.assertEqual(rows_of(record)["recipe.c-timed"]["branch"], ["product_schema", "constraint.internal.internal-time-constraint", "constraint.internal.internal-time-constraint.sufficient"])

    def test_internal_unknown_and_external_missing_does_not_pass(self):
        """The product states no internal alternative, so nothing establishes it."""
        declared = constraint_product(constraint_witness("restricted", internal="not-available", sufficient=False))
        declared["constraint_resolution"]["internal"] = []
        declared["constraint_resolution"]["joint"] = [{"name": "unrelated", "state": "not-available", "sufficient": False}]
        record = self.judged(artificial_inspection(declared))
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-unknown"])
        self.assertEqual(record["decision"]["state"], "needs-evidence")

    def test_external_available_passes_whatever_the_internal_branch_states(self):
        """A47: "valid alternatives can pass"; unused branches may be missing (Section 5.8)."""
        for internal, sufficient in (("not-available", False), ("unqualified", False), ("qualified", True)):
            record = self.judged(artificial_inspection(constraint_product(constraint_witness(external="available", internal=internal, sufficient=sufficient))))
            self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-timed", internal)
            self.assertEqual(rows_of(record)["recipe.c-timed"]["branch"], ["product_schema", "constraint.external.external-time-origin"], internal)

    def test_half_an_internal_branch_does_not_pass(self):
        """Section 5.8: having an internal field is not enough."""
        for state, sufficient in (("qualified", False), ("unqualified", True), ("not-available", False)):
            document = constraint_product(constraint_witness("restricted", internal=state, sufficient=sufficient))
            record = self.judged(artificial_inspection(document))
            self.assertIsNone(record["decision"]["chosen_recipe"], state)
            self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-unsatisfied"], state)
            self.assertEqual(record["decision"]["state"], "abstained", state)

    def test_a_conflict_on_a_branch_blocks_even_with_another_branch_passing(self):
        """The user's ruling (decisions.md, "T14 rulings"): a conflict on any branch of an OR blocks."""
        conflict = [{"key": "constraint.external.external-time-origin", "value": "available", "reference": "manifest:artificial", "kind": "declaration"}]
        record = self.judged(artificial_inspection(constraint_product(), declared=conflict))
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-conflicting"])
        self.assertIn("constraint.external.external-time-origin", rows_of(record)["recipe.c-timed"]["open"])

    def test_a_conflict_on_the_schema_or_the_branch_used_blocks(self):
        """DS2: resolve a scope conflict first, whatever the confidence."""
        for key, value in (("product_schema", "other-schema"), ("constraint.internal.internal-time-constraint", "unqualified")):
            conflict = [{"key": key, "value": value, "reference": "manifest:artificial", "kind": "declaration"}]
            record = self.judged(artificial_inspection(constraint_product(), declared=conflict))
            self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-conflicting"], key)
            self.assertIsNone(record["decision"]["chosen_recipe"], key)

    def test_a_condition_on_an_extracted_value_stays_unknown(self):
        """K15, A49: an LLM's value is a declaration to check."""
        extracted = [{"key": "constraint.external.not-in-the-product", "value": "available", "reference": "extraction:artificial", "kind": "llm-extraction"}]
        document = artificial_recipe("c-timed")
        requires = {"fact": "constraint.external.not-in-the-product", "equals": "available"}
        witness = {"index": candidate_index([document], [index_row(document, 1, requires)]), "policy": selection_policy(), "recipes": [document], "evidence": [artificial_evidence(document)]}
        inspection = artificial_inspection(declared=extracted)
        record = selected(witness, inspection, inspection["signatures"][0]["signature_id"])
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-unknown"])

    def test_a_malformed_condition_is_unknown_for_that_candidate_alone(self):
        """Section 5.8: unknown is never true; an empty list is not vacuously true."""
        good, broken = artificial_recipe("c-good"), artificial_recipe("c-broken")
        for condition in ({"all_of": []}, {"any_of": []}, {}, None, 3, "schema", {"fact": "product_schema"}, {"fact": "product_schema", "equals": None}):
            rows = [index_row(good, 3), dict(index_row(broken, 1), requires=condition)]
            witness = {"index": candidate_index([good, broken], rows), "policy": selection_policy(), "recipes": [good, broken], "evidence": [artificial_evidence(good), artificial_evidence(broken)]}
            record = selected(witness)
            self.assertEqual(rows_of(record)["recipe.c-broken"]["blocks"], ["necessary-unknown"], repr(condition))
            self.assertEqual(record["decision"]["chosen_recipe"], "recipe.c-good", repr(condition))

    def test_a_score_on_a_row_opens_nothing(self):
        """A49 through the index: the schema refuses it, so nothing is selected."""
        document = artificial_recipe("c-timed")
        row = dict(index_row(document, 1, {"fact": "not-established", "equals": True}), score=0.9999)
        record = selected({"index": candidate_index([document], [row]), "policy": selection_policy(), "recipes": [document], "evidence": [artificial_evidence(document)]})
        self.assertIsNone(record["decision"]["chosen_recipe"])

    def test_a_conflict_under_an_unsatisfied_item_of_a_branch_blocks(self):
        """C3 review, M1, on this witness's own REQUIRES. The ruling: a conflict on any branch of an OR blocks, even with another branch passing."""
        dispute = [{"key": "constraint.internal.internal-time-constraint.sufficient", "value": True, "reference": "manifest:artificial", "kind": "declaration"}]
        document = constraint_product(constraint_witness(external="available", internal="unqualified", sufficient=False))
        record = self.judged(artificial_inspection(document, declared=dispute))
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-conflicting"])
        self.assertEqual(record["decision"]["state"], "needs-evidence", "a conflict alone is lifted by more information (SEL08)")
        self.assertIn("constraint.internal.internal-time-constraint.sufficient", record["formal"]["restricted_delivery"]["open"], "Section 5.6 item 5: the facts still missing")

    def test_a_failed_schema_condition_blocks_with_a_passing_branch(self):
        """A47: schema and a constraint, not either."""
        document = artificial_recipe("c-timed")
        requires = {"all_of": [{"fact": "product_schema", "equals": "another-schema"}, self.REQUIRES["all_of"][1]]}
        witness = {"index": candidate_index([document], [index_row(document, 1, requires)]), "policy": selection_policy(), "recipes": [document], "evidence": [artificial_evidence(document)]}
        inspection = artificial_inspection(constraint_product())
        record = selected(witness, inspection, inspection["signatures"][0]["signature_id"])
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-unsatisfied"])

    def test_a_product_that_states_no_constraint_at_all_is_unknown(self):
        record = self.judged(artificial_inspection())
        self.assertEqual(rows_of(record)["recipe.c-timed"]["blocks"], ["necessary-unknown"])
        self.assertIn("constraint.external.external-time-origin", rows_of(record)["recipe.c-timed"]["open"])

    def test_the_branch_used_enters_the_record_and_a_failed_row_names_none(self):
        """Section 5.8: "the constraint branch used must enter the manifest"."""
        passing = self.judged(artificial_inspection(constraint_product()))
        self.assertIn("constraint.internal.internal-time-constraint", rows_of(passing)["recipe.c-timed"]["branch"])
        failing = self.judged(artificial_inspection())
        self.assertEqual(rows_of(failing)["recipe.c-timed"]["branch"], [])


class HybridPolicyWitness(unittest.TestCase):
    """Section 5.14, DS3; Sections 5.11, 11.5; K16: the router, the experts and the rest are one policy, tested as a whole."""

    def test_the_claim_is_limited_to_the_two_experts(self):
        record = selected(hybrid_policy_witness())
        claims = record["formal"]["claims"]
        self.assertEqual(claims["expert_support"], ["recipe.e1", "recipe.e2"])
        self.assertIs(claims["policy_confirmed"], False)
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(rows_of(record)["recipe.hybrid-policy"]["blocks"], ["insufficient-evidence"])
        self.assertIsNone(record["candidates"][0]["quality_evidence"], "an expert's evidence is not the policy's")

    def test_an_expert_record_offered_as_the_policy_evidence_is_not_inherited(self):
        witness = hybrid_policy_witness()
        whole = next(document for document in witness["recipes"] if document["recipe_id"] == "recipe.hybrid-policy")
        whole.update(status="routine", evidence_ref="evidence.e1")
        witness["index"]["candidates"][0] = index_row(whole, 1, composition=witness["index"]["candidates"][0]["composition"])
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.hybrid-policy"]["blocks"], ["insufficient-evidence"])
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertIsNone(record["candidates"][0]["quality_evidence"], "the row shows no evidence that is not its own")

    def test_a_missing_expert_leaves_the_whole_unsupported_even_with_evidence(self):
        """Section 5.11: the router, all experts and the rest are the policy."""
        witness = hybrid_policy_witness(experts=["recipe.e1", "recipe.not-supplied"])
        whole = next(document for document in witness["recipes"] if document["recipe_id"] == "recipe.hybrid-policy")
        whole.update(status="routine", evidence_ref="evidence.hybrid-policy")
        witness["index"]["candidates"][0] = index_row(whole, 1, composition=witness["index"]["candidates"][0]["composition"])
        witness["evidence"].append(artificial_evidence(whole))
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.hybrid-policy"]["blocks"], ["insufficient-evidence"])
        self.assertEqual(rows_of(record)["recipe.hybrid-policy"]["open"][-1], "recipe.not-supplied")

    def test_an_expert_with_failed_or_absent_evidence_is_not_supported(self):
        witness = hybrid_policy_witness()
        witness["evidence"][0] = artificial_evidence(witness["recipes"][0], "failed", "fail")
        self.assertEqual(selected(witness)["formal"]["claims"]["expert_support"], ["recipe.e2"])
        witness = hybrid_policy_witness()
        del witness["evidence"][1]
        self.assertEqual(selected(witness)["formal"]["claims"]["expert_support"], ["recipe.e1"])

    def test_evidence_for_the_whole_can_make_it_eligible_and_still_confirms_nothing(self):
        """K16: tested as a whole, it is a recipe like any other. K18: no post-selection claim without independent confirmation."""
        witness = hybrid_policy_witness()
        whole = next(document for document in witness["recipes"] if document["recipe_id"] == "recipe.hybrid-policy")
        whole.update(status="routine", evidence_ref="evidence.hybrid-policy")
        witness["index"]["candidates"][0] = index_row(whole, 1, composition=witness["index"]["candidates"][0]["composition"])
        witness["evidence"].append(artificial_evidence(whole))
        record = selected(witness)
        self.assertEqual(record["decision"]["chosen_recipe"], "recipe.hybrid-policy")
        self.assertIs(record["formal"]["claims"]["policy_confirmed"], False)
        self.assertIsNone(record["formal"]["post_selection_evidence"])

    def test_no_actual_router_means_no_support_for_the_whole_even_with_evidence(self):
        """DS3: "Full-chain confirmation requires the actual router"."""
        for router in (None, "recipe.not-supplied"):
            witness = hybrid_policy_witness(router=router)
            whole = next(document for document in witness["recipes"] if document["recipe_id"] == "recipe.hybrid-policy")
            whole.update(status="routine", evidence_ref="evidence.hybrid-policy")
            witness["index"]["candidates"][0] = index_row(whole, 1, composition=witness["index"]["candidates"][0]["composition"])
            witness["evidence"].append(artificial_evidence(whole))
            record = selected(witness)
            self.assertEqual(rows_of(record)["recipe.hybrid-policy"]["blocks"], ["insufficient-evidence"], router)
            self.assertIsNone(record["decision"]["chosen_recipe"], router)

    def test_an_expert_listed_on_its_own_can_still_be_chosen_for_itself(self):
        witness = hybrid_policy_witness()
        first = witness["recipes"][0]
        witness["index"] = candidate_index([first, witness["recipes"][3]], [index_row(first, 2)] + witness["index"]["candidates"])
        record = selected(witness)
        self.assertEqual(record["decision"]["chosen_recipe"], "recipe.e1")
        self.assertIs(record["formal"]["claims"]["policy_confirmed"], False)


def backendless_recipe(name, **fields):
    """No backend selected: null is never filled with a guess (Section 8.7)."""
    document = artificial_recipe(name, command=None, **fields)
    document["implementation"] = {"backend": None, "version": None, "native_entrypoint": None}
    return document


def one_candidate(document, evidence, **policy_fields):
    return {"index": candidate_index([document], [index_row(document, 1)]), "policy": selection_policy(**policy_fields), "recipes": [document], "evidence": evidence}


class QualificationCandidates(unittest.TestCase):
    """Section 5.10: "A qualification pilot may test a clearly specified new binding while it is unqualified"; DS1: "listed separately"."""

    def standing(self, document, cost=1, evidence=(), **policy_fields):
        witness = one_candidate(document, list(evidence), **policy_fields)
        witness["index"]["candidates"][0]["cost"] = None if cost is None else {"value": cost, "unit": ARTIFICIAL_COST_UNIT}
        record = selected(witness)
        self.assertEqual(code_list(read_sidecar(record)), [])
        return rows_of(record)[document["recipe_id"]]["standing"], record["formal"]["qualification_candidates"]

    def test_a_pilot_lacks_what_a_pilot_finds_out(self):
        pilot = dict(status="development", evidence_ref=None)
        self.assertEqual(self.standing(artificial_recipe("c-pilot", runtime_evidence=None, **pilot)), ("qualification-candidate", ["recipe.c-pilot"]))
        self.assertEqual(self.standing(artificial_recipe("c-pilot", **pilot), cost=None), ("qualification-candidate", ["recipe.c-pilot"]))

    def test_what_cannot_be_piloted_stays_out(self):
        pilot = dict(status="development", evidence_ref=None)
        self.assertEqual(self.standing(backendless_recipe("c-none", **pilot)), ("excluded", []), "no backend: nothing to run")
        self.assertEqual(self.standing(artificial_recipe("c-dear", **pilot), cost=9), ("excluded", []), "over the cap")
        document = artificial_recipe("c-failed")
        self.assertEqual(self.standing(document, evidence=[artificial_evidence(document, "failed", "fail")]), ("excluded", []), "failed")
        document = artificial_recipe("c-unpriced")
        self.assertEqual(self.standing(document, cost=None, evidence=[artificial_evidence(document)]), ("excluded", []), "no lack of evidence")


class A52RestrictedDelivery(unittest.TestCase):
    """A52: no available backend and insufficient evidence are told apart, with a restricted delivery and no fabricated command or success."""

    def test_no_backend_alone(self):
        document = backendless_recipe("c-backendless")
        record = selected(one_candidate(document, [artificial_evidence(document)]))
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("needs-evidence", None))
        self.assertTrue(record["decision"]["reason"].startswith(NO_QUALIFIED))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["no-available-backend"])

    def test_insufficient_evidence_alone(self):
        document = artificial_recipe("c-unevidenced")
        record = selected(one_candidate(document, [artificial_evidence(document, "inconclusive", "inconclusive")]))
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("needs-evidence", None))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["insufficient-evidence"])

    def test_both_reasons_stay_visible(self):
        document = backendless_recipe("c-neither")
        record = selected(one_candidate(document, []))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["no-available-backend", "insufficient-evidence"])
        self.assertEqual(record["decision"]["state"], "needs-evidence", "Section 8.7's worked record")

    def test_the_worked_record_of_section_8_7_is_needs_evidence(self):
        """Section 8.7: unknown semantics, no backend, "command": null, "runtime_evidence": null, state needs-evidence. The same content as a proposal."""
        document = backendless_recipe("c-proposal", status="proposal", evidence_ref=None, reproducibility=None, runtime_evidence=None)
        witness = one_candidate(document, [])
        witness["index"]["candidates"][0]["requires"] = {"fact": "sampling.time_system", "equals": "digitizer-clock"}
        record = selected(witness)
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("needs-evidence", None))
        self.assertEqual(rows_of(record)["recipe.c-proposal"]["blocks"], ["necessary-unknown", "no-available-backend", "insufficient-evidence"])
        self.assertIsNone(rows_of(record)["recipe.c-proposal"]["runtime_evidence"])

    def test_what_no_information_can_lift_stays_abstained(self):
        """SEL08 "stop": a failed check or a limit does not move with more information."""
        document = backendless_recipe("c-failed")
        record = selected(one_candidate(document, [artificial_evidence(document, "failed", "fail")]))
        self.assertEqual(record["decision"]["state"], "abstained")
        document = artificial_recipe("c-dear")
        witness = one_candidate(document, [artificial_evidence(document)], cap=0.5)
        self.assertEqual(selected(witness)["decision"]["state"], "abstained")

    def test_what_stays_open_is_in_the_restriction(self):
        """Section 5.6 item 5: "the necessary facts still missing"."""
        document = artificial_recipe("c-open")
        witness = one_candidate(document, [artificial_evidence(document)])
        witness["index"]["candidates"][0]["requires"] = {"fact": "sampling.time_system", "equals": "digitizer-clock"}
        self.assertEqual(selected(witness)["formal"]["restricted_delivery"]["open"], ["sampling.time_system"])

    def test_a_cost_alone_unknown_needs_evidence(self):
        """SEL08: a cost can be measured, so this is not a stop."""
        document = artificial_recipe("c-unpriced")
        witness = one_candidate(document, [artificial_evidence(document)])
        witness["index"]["candidates"][0]["cost"] = None
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.c-unpriced"]["blocks"], ["cost-unknown"])
        self.assertEqual(record["decision"]["state"], "needs-evidence")

    def test_a_named_backend_with_no_runtime_evidence_is_not_available(self):
        """Section 5.5: an available library does not establish recipe usability; K02: a backend is confirmed once it has run."""
        document = artificial_recipe("c-unrun", runtime_evidence=None)
        record = selected(one_candidate(document, [artificial_evidence(document)]))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["no-available-backend"])

    def test_a_proposal_is_never_chosen(self):
        document = backendless_recipe("c-proposal", status="proposal", evidence_ref=None, reproducibility=None)
        record = selected(one_candidate(document, []))
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertIn("no-available-backend", record["formal"]["restricted_delivery"]["reasons"])

    def test_no_command_and_no_backend_name_reach_a_record(self):
        document = artificial_recipe("c-backed", command=["artificial-entry-with-a-token"])
        for evidence in ([], [artificial_evidence(document)]):
            text = json.dumps(selected(one_candidate(document, evidence)))
            self.assertNotIn("artificial-entry-with-a-token", text)
            self.assertNotIn('"command"', text)
            self.assertNotIn("synthetic-backend", text)

    def test_the_record_of_a_restricted_delivery_is_a_valid_sidecar(self):
        document = backendless_recipe("c-neither")
        self.assertEqual(code_list(read_sidecar(selected(one_candidate(document, [])))), [])

    def test_a_chosen_recipe_carries_no_restriction(self):
        self.assertIsNone(selected(quality_first_witness())["formal"]["restricted_delivery"])

    def test_every_block_reaches_the_reasons(self):
        record = selected(quality_first_witness(cap=0.1))
        self.assertEqual(record["formal"]["restricted_delivery"]["reasons"], ["quality-failed", "insufficient-evidence", "over-budget"])


def replayed(record, witness, inspection=None):
    return check_selection_replay(record, inspection or INSPECTION, **witness)


def changed_codes(report) -> list:
    return sorted(finding.message.split(":")[0] for finding in report.errors if finding.code == "reconstruction.selection.dependency_changed")


class A60Replay(unittest.TestCase):
    """A60: a replay holds policy, candidate, evidence and input versions and feature costs; an old decision is not proof of current validity."""

    def test_the_same_inputs_give_the_same_record(self):
        for witness in (quality_first_witness(), quality_first_witness(cap=2), hybrid_policy_witness()):
            first, second = selected(witness), selected(copy.deepcopy(witness))
            self.assertEqual(first, second)
            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_a_round_through_json_changes_nothing(self):
        witness = quality_first_witness()
        through = json.loads(json.dumps(witness))
        self.assertEqual(selected(witness), selected(through, json.loads(json.dumps(INSPECTION))))

    def test_the_order_of_recipes_and_evidence_does_not_matter(self):
        witness = quality_first_witness()
        turned = dict(witness, recipes=list(reversed(witness["recipes"])), evidence=list(reversed(witness["evidence"])))
        self.assertEqual(selected(witness), selected(turned))

    def test_a_record_replays_on_its_own_inputs(self):
        for witness in (quality_first_witness(), quality_first_witness(cap=2), hybrid_policy_witness()):
            self.assertEqual(code_list(replayed(selected(witness), witness)), [])

    def test_a_replay_survives_a_record_written_to_a_file(self):
        witness = quality_first_witness()
        self.assertEqual(code_list(replayed(json.loads(json.dumps(selected(witness))), witness)), [])

    def test_the_record_is_a_valid_sidecar_with_every_hash_of_section_8_7(self):
        record = selected(quality_first_witness())
        self.assertEqual(code_list(read_sidecar(record)), [])
        hashes = record["formal"]["hashes"]
        self.assertEqual(sorted(hashes), ["candidate_set_sha256", "conditions_sha256", "evidence_sha256", "input_sha256", "policy_sha256", "reader_sha256", "rule_sha256"])
        for value in hashes.values():
            self.assertRegex(value, "^[0-9a-f]{64}$")
        self.assertEqual(len(set(hashes.values())), len(hashes), "seven inputs, seven different digests")

    def test_each_hash_is_a_dependency_of_the_record(self):
        record = selected(quality_first_witness())
        self.assertEqual(sorted(record["dependencies"]), sorted(f"{name}:{value}" for name, value in record["formal"]["hashes"].items()))

    def test_the_record_keeps_versions_costs_roles_and_scopes(self):
        record = selected(quality_first_witness())
        self.assertEqual(record["formal"]["candidate_set"], {"index_id": "index.artificial-witness", "version": "1"})
        self.assertEqual(record["policy"]["version"], "1")
        self.assertEqual(record["sample_roles"], ["selection"])
        self.assertEqual(record["formal"]["values_role"], "artificial-witness")
        self.assertEqual(len(record["trials"]), len(INSPECTION["probes"]))
        self.assertIn("bytes_read=", record["trials"][0]["cost"])
        self.assertEqual({fact["scope"] for fact in record["formal"]["signature"]["facts"]} >= {INSPECTION["signatures"][0]["facts"][0]["scope"]}, True)
        self.assertEqual(rows_of(record)["recipe.c-reference"]["evidence_stage"], "artificial-witness")

    def test_a_changed_policy_is_named(self):
        witness = quality_first_witness()
        record = selected(witness)
        self.assertEqual(changed_codes(replayed(record, dict(witness, policy=selection_policy(version="2")))), ["policy_sha256"])

    def test_a_changed_index_is_named(self):
        witness = quality_first_witness()
        record = selected(witness)
        later = copy.deepcopy(witness)
        later["index"]["version"] = "2"
        self.assertEqual(changed_codes(replayed(record, later)), ["candidate_set_sha256"])

    def test_changed_evidence_invalidates_even_when_the_choice_stays(self):
        """A60: the same winner is no proof the old decision is current."""
        witness = quality_first_witness()
        record = selected(witness)
        later = copy.deepcopy(witness)
        later["evidence"][1]["scope"]["statement"] = "a later artificial pilot"
        self.assertEqual(selected(later)["decision"]["chosen_recipe"], record["decision"]["chosen_recipe"])
        self.assertEqual(changed_codes(replayed(record, later)), ["evidence_sha256"])

    def test_a_changed_input_is_named(self):
        witness = quality_first_witness()
        record = selected(witness)
        later = artificial_inspection(product("product.hits-a", objects=[measurement(0)], revision=2))
        report = replayed(record, witness, later)
        self.assertIn("input_sha256", changed_codes(report))

    def test_a_changed_feature_cost_is_a_changed_input(self):
        witness = quality_first_witness()
        record = selected(witness)
        later = copy.deepcopy(INSPECTION)
        later["probes"][0]["cost"]["seconds"] += 1
        later["spent"]["seconds"] += 1
        self.assertIn("input_sha256", changed_codes(replayed(record, witness, later)))

    def test_changed_runtime_evidence_is_named_though_the_recipe_identity_stays(self):
        witness = quality_first_witness()
        record = selected(witness)
        later = copy.deepcopy(witness)
        later["recipes"][1]["runtime_evidence"] = "another artificial runtime note"
        self.assertIn("candidate_set_sha256", changed_codes(replayed(record, later)))

    def test_changed_conditions_are_named(self):
        witness = quality_first_witness()
        record = selected(witness)
        later = copy.deepcopy(witness)
        later["recipes"][0]["profile_binding"]["conditions"] = []
        self.assertIn("conditions_sha256", changed_codes(replayed(record, later)))

    def test_changed_rules_or_readers_are_named(self):
        witness = quality_first_witness()
        for name in ("rule_sha256", "reader_sha256"):
            record = selected(witness)
            record["formal"]["hashes"][name] = "0" * 64
            self.assertEqual(changed_codes(replayed(record, witness)), [name])

    def test_a_failed_probe_is_a_trial_too(self):
        """K17, A60: failures included."""
        stopped = artificial_inspection(budget={"probes": 1, "bytes": 1, "seconds": 60, "memory_bytes": 10**10, "tools": 1})
        self.assertNotEqual(stopped["probes"][0]["outcome"], "read")
        record = selected(quality_first_witness(), stopped, stopped["signatures"][0]["signature_id"])
        self.assertEqual([(trial["trial_id"], trial["outcome"]) for trial in record["trials"]], [(probe["run"], probe["outcome"]) for probe in stopped["probes"]])

    def test_the_digests_name_the_modules_that_decide(self):
        """Section 8.7. judge_candidates and canonical_sha256 are rules of this selection, wherever they live (C3 review, m5, m12)."""
        self.assertLessEqual({"candidate_selection.py", "input_inspector.py", "reconstruction.py", "recipe_semantics.py", "conditions.py"}, set(candidate_selection.RULE_SOURCES))

    def test_a_change_in_each_rule_source_changes_the_rule_digest(self):
        real = Path.read_bytes
        for name in candidate_selection.RULE_SOURCES:
            def changed(path, source=name):
                return real(path) + b"#" if path.name == Path(source).name else real(path)
            before = candidate_selection._source_sha256(candidate_selection.RULE_SOURCES)
            with mock.patch.object(Path, "read_bytes", changed):
                self.assertNotEqual(candidate_selection._source_sha256(candidate_selection.RULE_SOURCES), before, name)

    def test_groups_and_the_declared_fallback_enter_the_record(self):
        """Section 5.13: "fallback", "data roles/groups"."""
        witness = quality_first_witness()
        witness["policy"]["baseline"] = "recipe.c-reference"
        record = selected(witness)
        self.assertEqual(record["formal"]["sample_groups"], ["artificial-group"])
        self.assertEqual(record["formal"]["baseline"], "recipe.c-reference")

    def test_a_rule_digest_follows_the_source(self):
        witness = quality_first_witness()
        first = selected(witness)["formal"]["hashes"]
        with mock.patch.object(candidate_selection, "RULE_SOURCES", candidate_selection.RULE_SOURCES[1:]):
            second = selected(witness)["formal"]["hashes"]
        self.assertNotEqual(first["rule_sha256"], second["rule_sha256"])
        self.assertEqual(first["input_sha256"], second["input_sha256"])

    def test_a_reader_digest_follows_the_source(self):
        witness = quality_first_witness()
        first = selected(witness)["formal"]["hashes"]
        with mock.patch.object(candidate_selection, "READER_SOURCES", candidate_selection.READER_SOURCES[1:]):
            second = selected(witness)["formal"]["hashes"]
        self.assertNotEqual(first["reader_sha256"], second["reader_sha256"])
        self.assertEqual(first["rule_sha256"], second["rule_sha256"])

    def test_every_source_a_digest_names_exists(self):
        self.assertTrue(all((candidate_selection.CONTRACTS_FOLDER / name).is_file() for name in candidate_selection.RULE_SOURCES + candidate_selection.READER_SOURCES))
        self.assertIn("schemas/selection_record.json", candidate_selection.READER_SOURCES)

    def test_conditions_a_product_used_enter_their_digest(self):
        """Section 8.7. Two payloads differ only in identity, as a later payload under one tag would."""
        witness = quality_first_witness()
        digests = []
        for content in ("1", "2"):
            inspection = artificial_inspection(consumer(used_payload(calibration_payload(content))))
            digests.append(selected(witness, inspection, inspection["signatures"][0]["signature_id"])["formal"]["hashes"]["conditions_sha256"])
        self.assertNotEqual(digests[0], digests[1])

    def test_an_edited_decision_does_not_replay(self):
        witness = quality_first_witness()
        for field, value in (("reason", "a better reason"), ("decision_record_ref", "decision.other")):
            record = selected(witness)
            record["decision"][field] = value
            self.assertIn("reconstruction.selection.record_altered", code_list(replayed(record, witness)), field)

    def test_a_record_with_no_formal_block_cannot_be_replayed(self):
        self.assertEqual(code_list(replayed(selection_record(), quality_first_witness())), ["reconstruction.selection.not_replayable"])

    def test_a_refused_selection_cannot_be_replayed(self):
        witness = quality_first_witness()
        record = selected(dict(witness, policy={"schema": "selection-policy/9"}))
        self.assertEqual(code_list(replayed(record, witness)), ["reconstruction.selection.not_replayable"])

    def test_unreadable_rule_sources_end_with_no_choice(self):
        with mock.patch.object(candidate_selection, "RULE_SOURCES", ("no-such-source.py",)):
            record = selected(quality_first_witness())
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertNotIn("formal", record)
        self.assertEqual(code_list(read_sidecar(record)), [])


class FailClosed(unittest.TestCase):
    """Malformed input gives a safe record, and a document a reader refuses is not acted on (K13)."""

    def assert_refused(self, record, name):
        self.assertIsNone(record["decision"]["chosen_recipe"], name)
        self.assertEqual(record["decision"]["state"], "abstained", name)
        self.assertNotIn("formal", record, name)
        self.assertEqual(code_list(read_sidecar(record)), [], name)
        self.assertTrue(record["decision"]["reason"].startswith(NO_QUALIFIED), name)

    def test_arguments_that_are_no_documents_give_a_safe_record(self):
        witness = quality_first_witness()
        for bad in (None, 3, "text", [], {}, [None], [3], {"schema": 3}, [{}]):
            for name in ("index", "policy"):
                self.assert_refused(select_candidate(SIGNATURE_ID, INSPECTION, **dict(witness, **{name: bad})), f"{name}={bad!r}")
            self.assert_refused(select_candidate(SIGNATURE_ID, bad, **witness), f"inspection={bad!r}")

    def test_lists_that_hold_no_documents_give_a_safe_record(self):
        witness = quality_first_witness()
        for bad in (None, 3, "text", {"a": witness["evidence"][0]}, [None], [3]):
            self.assert_refused(selected(dict(witness, evidence=bad)), f"evidence={bad!r}")
        for bad in (None, 3, "text", {"a": witness["recipes"][0]}, [None], [3]):
            self.assert_refused(selected(dict(witness, recipes=bad)), f"recipes={bad!r}")

    def test_a_signature_that_is_not_in_the_inspection_gives_a_safe_record(self):
        for bad in ("signature.other", "", None, 3, [], {}):
            self.assert_refused(select_candidate(bad, INSPECTION, **quality_first_witness()), repr(bad))

    def test_two_signatures_under_one_identity_are_not_told_apart(self):
        doubled = copy.deepcopy(INSPECTION)
        doubled["signatures"].append(copy.deepcopy(doubled["signatures"][0]))
        record = selected(quality_first_witness(), doubled)
        self.assertIsNone(record["decision"]["chosen_recipe"])

    def test_a_policy_outside_the_contract_is_refused(self):
        """K16: only artificial values; SEL01: a target is irreplaceable; Section 5.10: no confirmation data; Section 5.11: no per-event unit."""
        for field, value in (("role", "user-frozen"), ("target", ""), ("target", None), ("sample_roles", ["confirmation"]), ("sample_roles", ["selection", "confirmation"]), ("sample_roles", []),
                             ("granularity", "event"), ("objective", {"kind": "maximum-score", "cap": {"value": 5, "unit": ARTIFICIAL_COST_UNIT}}), ("objective", "fast")):
            witness = quality_first_witness()
            witness["policy"][field] = value
            self.assert_refused(selected(witness), f"{field}={value!r}")

    def test_a_cost_that_is_no_finite_number_is_refused(self):
        for value in (float("nan"), float("inf"), -1, True, "4", 10**400):
            witness = quality_first_witness()
            witness["index"]["candidates"][1]["cost"]["value"] = value
            self.assert_refused(selected(witness), repr(value)[:20])
        for value in (float("nan"), float("inf"), -1, True):
            witness = quality_first_witness()
            witness["policy"]["objective"]["cap"]["value"] = value
            self.assert_refused(selected(witness), repr(value))

    def test_a_sum_that_overflows_is_an_unknown_cost(self):
        witness = quality_first_witness()
        witness["index"]["candidates"][1]["cost"]["value"] = 1.5e308
        witness["policy"]["shared_overhead"]["value"] = 1.5e308
        witness["policy"]["objective"]["cap"]["value"] = 1.7e308
        self.assertEqual(rows_of(selected(witness))["recipe.c-reference"]["blocks"], ["cost-unknown"])

    def test_a_condition_nested_too_deep_is_no_exception(self):
        nested = SCHEMA_CONDITION
        for _ in range(5000):
            nested = {"all_of": [nested]}
        witness = quality_first_witness()
        witness["index"]["candidates"][1]["requires"] = nested
        self.assertIsNone(selected(witness)["decision"]["chosen_recipe"])

    def test_an_overhead_in_another_unit_is_refused(self):
        witness = quality_first_witness()
        witness["policy"]["shared_overhead"]["unit"] = "seconds"
        self.assert_refused(selected(witness), "overhead unit")

    def test_an_index_outside_the_contract_is_refused(self):
        def duplicate(index):
            index["candidates"].append(copy.deepcopy(index["candidates"][0]))

        def foreign_method(index):
            index["candidates"][0]["method_ref"] = "method-card.not-indexed"

        def real_role(index):
            index["role"] = "routine"

        def no_candidates(index):
            index["candidates"] = []

        def no_method_index(index):
            index["methods"] = []

        def not_a_blueprint(index):
            index["methods"][0]["blueprints"] = ["BP16"]

        for change in (duplicate, foreign_method, real_role, no_candidates, no_method_index, not_a_blueprint):
            witness = quality_first_witness()
            change(witness["index"])
            self.assert_refused(selected(witness), change.__name__)

    def test_the_reader_names_what_is_wrong_with_an_index(self):
        """Read directly: selecting on such an index is refused anyway, for a reason a test cannot tell apart."""
        index = quality_first_witness()["index"]
        index["candidates"][0]["method_ref"] = "method-card.not-indexed"
        self.assertEqual(code_list(read_sidecar(index)), ["reconstruction.index.method_not_indexed"])
        index = quality_first_witness()["index"]
        index["candidates"].append(copy.deepcopy(index["candidates"][0]))
        self.assertEqual(code_list(read_sidecar(index)), ["reconstruction.index.duplicate_entry"])

    def test_a_method_and_a_recipe_may_share_a_name(self):
        """C3 review, m6: each appears once, in its own list."""
        document = artificial_recipe("c-shared", method={"card_ref": "recipe.c-shared", "card_sha256": "d" * 64})
        witness = one_candidate(document, [artificial_evidence(document)])
        self.assertEqual(code_list(read_sidecar(witness["index"])), [])
        self.assertEqual(selected(witness)["decision"]["chosen_recipe"], "recipe.c-shared")

    def test_a_row_whose_recipe_is_missing_or_changed_is_never_chosen(self):
        """SEL04: only what the finite index binds. Section 17.3: a changed recipe inherits nothing."""
        witness = quality_first_witness()
        del witness["recipes"][1]
        record = selected(witness)
        self.assertEqual(rows_of(record)["recipe.c-reference"]["blocks"], ["recipe-unavailable"])
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(code_list(read_sidecar(record)), [])
        witness = quality_first_witness()
        witness["recipes"][1]["preconditions"] = ["a precondition added later"]
        self.assertIn("recipe-unavailable", rows_of(selected(witness))["recipe.c-reference"]["blocks"])
        witness = quality_first_witness()
        witness["index"]["methods"][1]["card_sha256"] = "e" * 64
        self.assertEqual(rows_of(selected(witness))["recipe.c-reference"]["blocks"], ["recipe-unavailable"])

    def test_two_recipes_or_two_evidence_records_under_one_identity_are_not_used(self):
        """Section 5.5: no value is chosen arbitrarily."""
        witness = quality_first_witness()
        witness["recipes"].append(copy.deepcopy(witness["recipes"][1]))
        self.assertEqual(rows_of(selected(witness))["recipe.c-reference"]["blocks"], ["recipe-unavailable"])
        witness = quality_first_witness()
        witness["evidence"].append(artificial_evidence(witness["recipes"][1], "failed", "fail"))
        self.assertEqual(rows_of(selected(witness))["recipe.c-reference"]["blocks"], ["insufficient-evidence"])

    def test_a_product_beside_its_payload_selects_as_the_product_alone(self):
        """C3 re-review, R1, through the real inspector and DS1."""
        with tempfile.TemporaryDirectory() as folder:
            paths = Path(folder) / "a.json", Path(folder) / "b.json"
            paths[0].write_text(json.dumps(product("product.hits-a", objects=[measurement(0)])), encoding="utf-8")
            paths[1].write_text(json.dumps(calibration_payload()), encoding="utf-8")
            inspection = inspect_inputs([{"product": "product.hits-a", "path": str(path)} for path in paths], {"probes": 2, "bytes": 1_000_000, "seconds": 60, "memory_bytes": 10**10, "tools": 2})
        record = selected(quality_first_witness(), inspection, inspection["signatures"][0]["signature_id"])
        self.assertEqual((record["decision"]["state"], record["decision"]["chosen_recipe"]), ("selected", "recipe.c-reference"))

    def test_two_rows_for_one_check_refuse_the_selection_in_either_order(self):
        """C3 re-review, r1."""
        for states in (("skipped", "pass"), ("pass", "skipped")):
            witness = quality_first_witness()
            witness["evidence"][1]["checks"] = [evidence_check(REQUIRED_CHECK, state) for state in states]
            self.assert_refused(selected(witness), states)

    def test_a_refused_recipe_or_evidence_refuses_the_selection(self):
        witness = quality_first_witness()
        witness["recipes"][1]["evidence_ref"] = None
        self.assert_refused(selected(witness), "routine with no evidence")
        witness = quality_first_witness()
        witness["evidence"][1]["checks"] = [evidence_check(REQUIRED_CHECK, "skipped")]
        self.assert_refused(selected(witness), "passed on a skip alone")

    def test_a_budget_stop_keeps_its_unknowns_and_shows_in_the_record(self):
        """A59, SEL03: a stopped inspection names its stop, and what it did not read stays unknown."""
        stopped = artificial_inspection(budget={"probes": 1, "bytes": 1, "seconds": 60, "memory_bytes": 10**10, "tools": 1})
        self.assertEqual(stopped["state"], "stopped")
        record = selected(quality_first_witness(), stopped, stopped["signatures"][0]["signature_id"])
        self.assertIsNone(record["decision"]["chosen_recipe"])
        self.assertEqual(record["formal"]["inspection"]["stop_reason"], "budget-bytes")
        self.assertEqual({row["blocks"][0] for row in record["formal"]["judgments"]}, {"necessary-unknown"})

    def test_a_replay_of_malformed_input_is_a_report(self):
        witness = quality_first_witness()
        record = selected(witness)
        for bad in (None, 3, "text", {}, [None]):
            self.assertTrue(code_list(check_selection_replay(bad, INSPECTION, **witness)), repr(bad))
            self.assertTrue(code_list(check_selection_replay(record, bad, **witness)), repr(bad))


class RecordRules(unittest.TestCase):
    """Sections 5.9, 5.13: one edit on an otherwise valid record, refused by the reader; a consistent edit, refused by the replay."""

    def edited_codes(self, change, witness=None):
        record = selected(witness or quality_first_witness())
        change(record)
        return code_list(read_sidecar(record))

    def test_a_record_cannot_claim_a_failed_candidate(self):
        def choose_fast(record):
            record["decision"]["chosen_recipe"] = "recipe.c-fast"
        self.assertIn("reconstruction.selection.choice_not_eligible", self.edited_codes(choose_fast))

    def test_a_record_cannot_claim_a_qualification_candidate(self):
        def choose_unknown(record):
            record["decision"]["state"] = "qualified-default"
            record["decision"]["chosen_recipe"] = "recipe.c-unknown"
            record["formal"]["baseline"] = "recipe.c-unknown"
        self.assertIn("reconstruction.selection.choice_not_eligible", self.edited_codes(choose_unknown))

    def test_a_choice_and_a_restriction_exclude_each_other(self):
        def add_restriction(record):
            record["formal"]["restricted_delivery"] = {"reasons": ["over-budget"], "open": [], "options": []}

        def drop_restriction(record):
            record["formal"]["restricted_delivery"] = None
        self.assertIn("reconstruction.selection.restriction_disagrees", self.edited_codes(add_restriction))
        self.assertIn("reconstruction.selection.restriction_disagrees", self.edited_codes(drop_restriction, quality_first_witness(cap=2)))

    def test_a_default_is_the_baseline(self):
        def relabel(record):
            record["decision"]["state"] = "qualified-default"
        self.assertIn("reconstruction.selection.default_not_baseline", self.edited_codes(relabel))

    def test_selected_needs_an_objective(self):
        def drop_objective(record):
            record["policy"]["objective"] = None
        self.assertIn("reconstruction.selection.selected_without_objective", self.edited_codes(drop_objective))

    def test_standing_follows_the_blocks(self):
        def promote(record):
            record["formal"]["judgments"][0]["standing"] = "routine-eligible"

        def list_a_failure(record):
            record["formal"]["judgments"][0]["standing"] = "qualification-candidate"

        def bury_a_clean_row(record):
            record["formal"]["judgments"][1]["standing"] = "excluded"
        for change in (promote, list_a_failure, bury_a_clean_row):
            self.assertIn("reconstruction.selection.standing_disagrees", self.edited_codes(change), change.__name__)

    def test_every_candidate_keeps_its_judgment(self):
        def drop(record):
            del record["formal"]["judgments"][0]
        self.assertIn("reconstruction.selection.judgments_disagree", self.edited_codes(drop))

    def test_no_claim_of_confirmation_or_of_a_global_best(self):
        """DS3, K18, SEL08."""
        def confirmed(record):
            record["formal"]["claims"]["policy_confirmed"] = True

        def best(record):
            record["formal"]["claims"]["global_best"] = True

        def post_selection(record):
            record["formal"]["post_selection_evidence"] = "evidence.after"

        def ranker(record):
            record["formal"]["learned_ranker"] = "model.a"

        def real_values(record):
            record["formal"]["values_role"] = "routine"

        def command(record):
            record["command"] = ["artificial-entry"]
        for change in (confirmed, best, post_selection, ranker, real_values, command):
            self.assertTrue(self.edited_codes(change), change.__name__)

    def test_a_consistent_forgery_passes_the_reader_and_fails_the_replay(self):
        """The reader sees one document; only the replay sees the inputs (A60)."""
        witness = quality_first_witness()
        record = selected(witness)

        def promote(row):
            row.update(standing="routine-eligible", blocks=[])
        promote(rows_of(record)["recipe.c-fast"])
        record["decision"]["chosen_recipe"] = "recipe.c-fast"
        self.assertEqual(code_list(read_sidecar(record)), [])
        codes = code_list(replayed(record, witness))
        self.assertIn("reconstruction.selection.record_altered", codes)
        self.assertIn("reconstruction.selection.decision_changed", codes)

    def test_an_old_record_keeps_its_meaning(self):
        """K13: the shape of Section 8.7 without a formal block is read as before."""
        self.assertEqual(code_list(read_sidecar(selection_record())), [])


class ColdProcess(unittest.TestCase):
    """contracts.reconstruction must not need this module: T14's budget watch starts after the readers are imported, and that list did not grow."""

    def cold(self, code):
        return subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); {code}"], capture_output=True, text=True, timeout=25, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_this_module_imports_first_in_a_fresh_process(self):
        finished = self.cold("import contracts.candidate_selection")
        self.assertEqual(finished.returncode, 0, finished.stderr[-800:])

    def test_the_readers_do_not_load_this_module(self):
        finished = self.cold("import contracts.reconstruction, contracts.input_inspector; print('contracts.candidate_selection' in sys.modules)")
        self.assertEqual(finished.stdout.strip(), "False", finished.stderr[-800:])

    def test_a_record_does_not_depend_on_the_hash_seed(self):
        """A set's order differs between processes, so a record built on one would not replay."""
        arguments = json.dumps([SIGNATURE_ID, INSPECTION, quality_first_witness(cap=0.1)])
        code = ("import json; from contracts.candidate_selection import select_candidate; signature_id, inspection, witness = json.loads(sys.stdin.read()); "
                "print(json.dumps(select_candidate(signature_id, inspection, **witness), sort_keys=True))")
        printed = {subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); {code}"], input=arguments, capture_output=True, text=True, timeout=25,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED=seed)).stdout for seed in ("1", "2", "3")}
        self.assertEqual(printed, {json.dumps(selected(quality_first_witness(cap=0.1)), sort_keys=True) + "\n"})

    def test_a_new_format_is_read_in_a_fresh_process(self):
        finished = self.cold("from contracts.sidecar_reader import read_document; print(read_document({'schema': 'selection-policy/1', 'required_extensions': []}).ok)")
        self.assertEqual(finished.stdout.strip(), "False", finished.stderr[-800:])
