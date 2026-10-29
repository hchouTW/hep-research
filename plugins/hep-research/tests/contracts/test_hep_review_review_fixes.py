"""Regression tests for the independent T01 review (docs/dev/hep-review/reviews/t01-review.md, findings F1-F15).
Each test reproduces the reviewer's failing input and asserts the specified behaviour."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from hep_review_fixtures import Case, obligation, hexd  # noqa: E402

V = H.LATEST_VALIDATOR
GOOD_ATT = {"report_mode": "current", "validator_is_latest_approved": True, "head_continuity": "verified",
            "r3_state_matches": True}


def run(case: Case, att=None):
    p = H.project(H.validate(case.bundle(), V), V)
    return p, H.decide_summary(p, dict(GOOD_ATT, **(att or {})))


def outcome(p, oid):
    return next(o for o in p["obligations"] if o["id"] == oid)


def set_obj(case: Case, oid: str, **changes):
    for e in case.entries:
        o = e["objects"][0]
        if o["id"] == oid:
            o.update(changes)


class F1Determinism(unittest.TestCase):
    def test_layer1_identical_under_different_hash_seeds(self):
        here = str(Path(__file__).resolve().parent)
        prog = (
            f"import sys; sys.path.insert(0, {str(ROOT)!r}); sys.path.insert(0, {here!r})\n"
            "from contracts import hep_review as H\n"
            "from hep_review_fixtures import Case, obligation\n"
            "c = Case()\n"
            "c.plan([obligation('O1', independence_requirements=['second-reviewer','domain-expert',"
            "'different-institute','cross-check'])])\n"
            "c.review('O1', 'supported')\n"
            "print(H.metadata_digest(H.project(H.validate(c.bundle(), H.LATEST_VALIDATOR), H.LATEST_VALIDATOR)))\n"
        )
        digests = set()
        for seed in ("1", "2", "3", "4"):
            r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(r.returncode, 0, r.stderr)
            digests.add(r.stdout.strip())
        self.assertEqual(len(digests), 1, digests)


class F2RenameDowngrades(unittest.TestCase):
    def strong(self, oid="O1"):
        return obligation(oid, tolerances=[{"quantity": "x", "value": "0.001", "kind": "relative"}],
                          adoption={"second_method_required": True, "verification_required": True,
                                    "qualifications": ["stats"]})

    def test_rename_is_checked_field_by_field(self):
        c = Case()
        parent = c.plan([self.strong()])
        weak = obligation("O1b", decision_required=False, methods=(), evidence=())
        child = c.plan([weak], obligation_map=[{"old_id": "O1", "new_ids": ["O1b"], "retired_reason": None}])
        codes = {e["code"] for e in H.check_plan(child, parent, c.intent)}
        for code in ("downgrade.method_removed", "downgrade.evidence_removed", "downgrade.decision_required_dropped",
                     "downgrade.tolerance_loosened", "downgrade.adoption_loosened", "downgrade.criterion_changed"):
            self.assertIn(code, codes)

    def test_pure_rename_with_equal_fields_is_accepted(self):
        c = Case()
        o = self.strong()
        parent = c.plan([o])
        renamed = dict(copy.deepcopy(o), id="O1b")
        child = c.plan([renamed], obligation_map=[{"old_id": "O1", "new_ids": ["O1b"], "retired_reason": None}])
        self.assertEqual(H.check_plan(child, parent, c.intent), [])

    def test_split_keeps_union_of_methods_and_needs_each_target_strong(self):
        c = Case()
        parent = c.plan([obligation("O1", methods=("recompute", "derivation"))])
        a = obligation("O1a", methods=("recompute",))
        b = obligation("O1b", methods=())
        child = c.plan([a, b], obligation_map=[{"old_id": "O1", "new_ids": ["O1a", "O1b"], "retired_reason": None}])
        self.assertIn("downgrade.method_removed", {e["code"] for e in H.check_plan(child, parent, c.intent)})


class F3PositiveAnswers(unittest.TestCase):
    def test_unqualified_reviewer_cannot_make_supported(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        set_obj(c, r["assignment_id"], qualified={"satisfied": False, "basis": "declared"})
        p, s = run(c)
        self.assertNotEqual(outcome(p, "O1")["outcome"], "supported")
        self.assertFalse(s["output_summary"])

    def test_adoption_policy_applies_to_positive_answers(self):
        pol = {"second_method_required": False, "verification_required": True, "qualifications": []}
        c = Case()
        c.plan([obligation("O1", adoption=pol)])
        r = c.review("O1", "supported")
        p, s = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "undetermined")
        self.assertFalse(s["output_summary"])
        c.judge([{"id": "J1", "kind": "answer_assessment", "answer_id": r["answers"][0]["id"], "verdict": "supported",
                  "basis": "observed", "depends_on": []}])
        p, s = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "supported")

    def test_second_method_required(self):
        pol = {"second_method_required": True, "verification_required": False, "qualifications": []}
        c = Case()
        c.plan([obligation("O1", adoption=pol)])
        c.review("O1", "supported")
        p, _ = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "undetermined")
        c.review("O1", "supported", method="independent-derivation")
        p, _ = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "supported")

    def test_author_response_record_cannot_support(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported", actor="author-a", role="author", record_type="response")
        p, s = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "not-examined")
        self.assertFalse(s["output_summary"])


class F4Discharge(unittest.TestCase):
    def test_only_listed_applicability_reasons_with_accepted_basis(self):
        for d in ({"reason_category": "data-unavailable", "basis": "declared", "reason": "x"},
                  {"reason_category": "condition-absent", "basis": "self-reported", "reason": "x"}):
            with self.subTest(d):
                c = Case()
                c.plan([obligation("O1")])
                r = c.review("O1", "not-applicable", discharge=d)
                v = H.validate(c.bundle(), V)
                self.assertIn(r["answers"][0]["id"], v["quarantined_items"])
                p, s = run(c)
                self.assertFalse(s["output_summary"])


class F5AuthorJudgments(unittest.TestCase):
    def test_author_cannot_refute_a_finding(self):
        pol = {"second_method_required": False, "verification_required": True, "qualifications": []}
        c = Case()
        c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False, adoption=pol)])
        c.review("O1", "supported")
        r = c.review("O2", "violated", finding=True)
        fid = r["findings"][0]["id"]
        c.judge([{"id": "J1", "kind": "finding_assessment", "finding_id": fid, "verdict": "supported",
                  "basis": "observed", "depends_on": []}])
        c.judge([{"id": "JA", "kind": "finding_assessment", "finding_id": fid, "verdict": "refuted",
                  "basis": "self-reported", "depends_on": []}], actor="author-a", role="verifier")
        p, s = run(c)
        self.assertEqual(next(f for f in p["findings"] if f["id"] == fid)["state"], "supported")
        self.assertTrue(p["flags"]["has_supported_defects"])
        self.assertFalse(s["output_summary"])


class F6ClaimBinding(unittest.TestCase):
    def test_claim_binding_is_not_a_bundle_key(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        b = c.bundle()
        b["claim_binding"] = {}
        with self.assertRaises(H.BundleError):
            H.validate(b, V)

    def test_self_anchored_binding_does_not_reach_r3(self):
        claim = {"id": "claim-z", "state": "evaluated-scope", "fingerprint": "z"}
        head = {"protocol": H.PROTOCOL, "context_id": "e", "segment_id": "e", "seq": 7, "prev_commit_digest": None,
                "operation_id": "e7", "payload_digest": hexd("p"), "validator_version": V, "writer_session_id": "s"}
        chain = [{"commit": head, "digest": H.metadata_digest(head), "object_digests": [H.metadata_digest(claim)]}]
        c = Case(target_tier="R3")
        c.plan([obligation("O1")], required_restrictions=["no-network"])  # no trusted checkpoint, no fingerprint
        r = c.review("O1", "supported")
        set_obj(c, r["assignment_id"], restrictions=[{"id": "no-network", "status": "enforced", "basis": "observed"}])
        c.add(H_claim_binding(claim, chain, {"seq": 7, "digest": chain[0]["digest"]}, "z"))
        p, s = run(c)
        self.assertNotEqual(p["achieved_tier"], "R3")


def H_claim_binding(claim, chain, checkpoint, fingerprint):
    return {"protocol": H.PROTOCOL, "schema_version": H.SCHEMA_VERSION, "record_kind": "claim-binding",
            "id": "binding-1", "context_id": "ctx-1", "claim": claim, "chain_segment": chain,
            "case_fingerprint": fingerprint, "stated_checkpoint": checkpoint}


class F7ValidatorScope(unittest.TestCase):
    def test_bool_is_not_a_plan_revision(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        set_obj(c, r["id"], plan_revision=True)
        v = H.validate(c.bundle(), V)
        self.assertIn(r["id"], v["quarantined_records"])

    def test_non_compliant_head_plan_is_a_version_inconsistency(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O2")])
        c.review("O1", "supported")
        c.review("O2", "supported")
        c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
        p, s = run(c)
        self.assertTrue(p["version_inconsistencies"])
        self.assertFalse(s["output_summary"])


class F8LongIntegers(unittest.TestCase):
    def test_long_integer_token_is_an_ingest_error(self):
        with self.assertRaises(H.IngestError) as cm:
            H.ingest_json(b"[" + b"1" * 5000 + b"]")
        self.assertEqual(cm.exception.code, "json.int_range")


class F9Wording(unittest.TestCase):
    def test_correct_or_passed_and_split_qualifier_refused(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        p, _ = run(c)
        kw = {"bundle": c.bundle(), "validator_version": V}
        for pres in ({"title": "Analysis passed: physics is correct"},
                     {"summary_sentence": "{tier_qualifier}. The analysis is fine; " + H.NO_DEFECT + "."},
                     {"summary_sentence": "{tier_qualifier}: " + H.NO_DEFECT + ". It is correct."}):
            with self.subTest(pres):
                with self.assertRaises(H.RenderError):
                    H.render_report(H.encode(p), GOOD_ATT, presentation=pres, **kw)


class F10Locators(unittest.TestCase):
    def test_locator_digest_must_match_manifest(self):
        c = Case()
        c.plan([obligation("O1")])
        bad = {"id": "FX", "obligation_id": "O1", "claim": "c", "element": "e",
               "locator": {"material_id": "M2", "digest": "0" * 64}, "depends_on": []}
        r = c.review("O1", "violated", findings_extra=[bad])
        v = H.validate(c.bundle(), V)
        self.assertEqual(v["quarantined_records"][r["id"]]["code"], "binding.locator_digest")

    def test_located_material_is_in_the_closure(self):
        c = Case()
        o = obligation("O1")  # targets M1 only
        c.plan([o])
        loc = {"id": "FY", "obligation_id": "O1", "claim": "c", "element": "e",
               "locator": {"material_id": "M2", "digest": c.materials["M2"]["raw_ref"]["digest"]}, "depends_on": []}
        c.review("O1", "violated", findings_extra=[loc], evidence=False, answer_extra={"depends_on": []})
        c.new_manifest(M2="M2-v2")
        c.plan([o])
        p, _ = run(c)
        f = next(x for x in p["findings"] if x["id"] == "FY")
        self.assertFalse(f["current"])


class F11Disclosure(unittest.TestCase):
    def test_advisory_sentence_in_disclosure_even_without_summary(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "violated", finding=True)
        p, s = run(c)
        self.assertFalse(s["output_summary"])
        self.assertIn("neither observed nor enforced", " ".join(s["disclosure"]))

    def test_target_reasons_only_for_the_shortfall(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O2")])
        c.review("O1", "supported")
        c.review("O2", "supported", fidelity="transcribed")
        p, s = run(c)
        text = " ".join(s["disclosure"])
        self.assertIn("transcribed", text)
        self.assertNotIn("R3 is not claimed", text)


class F12OptionalConflict(unittest.TestCase):
    def test_conflict_on_optional_is_open(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
        c.review("O1", "supported")
        c.review("O2", "supported")
        c.review("O2", "violated")
        p, s = run(c)
        self.assertTrue(p["flags"]["has_open_questions"])
        self.assertNotIn("O2", p["uncovered_optional"]["undetermined"])
        self.assertFalse(s["output_summary"])


class F13Fixtures(unittest.TestCase):
    def test_d25_admissible_form_unmapped_optional_with_violated_finding(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O9", required=False, decision_required=False)])
        c.review("O1", "supported")
        c.review("O9", "violated", finding=True)
        parent = c.plans[-1]
        child = c.plan([obligation("O1")], obligation_map=[])
        self.assertEqual(H.check_plan(child, parent, c.intent), [])
        p, s = run(c)
        self.assertIn("O9", [g["obligation_id"] for g in p["planning_gaps"] if g["kind"] == "unmapped_old_obligation"])
        self.assertEqual(len(p["unverified_historical_defects"]), 1)
        self.assertTrue(p["flags"]["has_open_questions"])
        self.assertFalse(p["flags"]["plan_requirements_met"])

    def test_historical_check_with_an_older_rule_set(self):
        def stricter(committed, lookup):
            if committed.get("record_kind") == "plan" and "required_restrictions" not in committed:
                return [{"code": "plan.required_restrictions_missing", "path": "$", "message": "m"}]
            return []
        rules = dict(H.VALIDATOR_RULES)
        rules["0.2.0-test"] = H.VALIDATOR_RULES[V] + (stricter,)
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        b = c.bundle()
        old = H.encode(H.project(H.validate(b, V, rules=rules), V, rules=rules))
        self.assertEqual(H.check_historical(old, b, V, rules=rules), "match")
        self.assertEqual(H.check_historical(old, b, "0.2.0-test", rules=rules), "mismatch")


class F14ProjectRecomputes(unittest.TestCase):
    def test_edited_disposition_is_refused(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        c.blob_checks[r["evidence"][0]["content_ref"]["digest"]] = "changed"
        v = H.validate(c.bundle(), V)
        v["quarantined_items"] = {}
        v["record_integrity"] = "valid"
        with self.assertRaises(ValueError):
            H.project(v, V)


class F15CreationOrder(unittest.TestCase):
    def test_assignment_before_its_plan_is_quarantine_or_refusal(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        # commit the assignment before the plan it names
        e = c.entries
        i_plan = next(i for i, x in enumerate(e) if x["objects"][0]["record_kind"] == "plan")
        i_asg = next(i for i, x in enumerate(e) if x["objects"][0]["id"] == r["assignment_id"])
        e.insert(i_plan, e.pop(i_asg))
        v = H.validate(c.bundle(), V)
        self.assertIn(r["id"], v["quarantined_records"])

    def test_metadata_ref_to_a_later_object_is_flagged(self):
        c = Case()
        p = c.plan([obligation("O1")])
        c.review("O1", "supported")
        later = c.entries[-1]["objects"][0]
        set_obj(c, p["id"], limits={"see": H.object_ref(later)})
        v = H.validate(c.bundle(), V)
        self.assertIn("order.forward_reference", {d["code"] for d in v["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
