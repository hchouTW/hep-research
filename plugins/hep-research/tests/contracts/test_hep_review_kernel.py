"""hep-review kernel cases owned by T01 outside the decision table (spec v9 section 19): plan admission and the
downgrade list, obligation_map, creation order and self-reference, disposition and quarantine, finding lifecycle,
facets, tiers (R2 floor, R3 binding), rendering, legacy refs and byte reproducibility."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from contracts.schema import validate as schema_validate  # noqa: E402
from hep_review_fixtures import Case, obligation, hexd, header  # noqa: E402

V = H.LATEST_VALIDATOR
GOOD_ATT = {"report_mode": "current", "validator_is_latest_approved": True, "head_continuity": "verified",
            "r3_state_matches": None}


def run(case: Case, att=None):
    v = H.validate(case.bundle(), V)
    p = H.project(v, V)
    return v, p, H.decide_summary(p, dict(GOOD_ATT, **(att or {})))


def codes(errs):
    return {e["code"] for e in errs}


def outcome(p, oid):
    return next(o for o in p["obligations"] if o["id"] == oid)


class PlanAdmission(unittest.TestCase):
    def setUp(self):
        self.intent = Case().intent

    def plan(self, obligations, **kw):
        return Case().plan(obligations, **kw)

    def test_n68_plan_without_required_obligations_is_rejected(self):
        self.assertIn("plan.no_required_obligation", codes(H.check_plan(self.plan([]), None, self.intent)))
        opt = obligation("O1", required=False, decision_required=False)
        self.assertIn("plan.no_required_obligation", codes(H.check_plan(self.plan([opt]), None, self.intent)))

    def test_n23_decision_required_explicit_and_fixed_false_for_optional(self):
        self.assertIn("plan.decision_required_missing",
                      codes(H.check_plan(self.plan([obligation("O1", decision_required=None)]), None, self.intent)))
        bad = obligation("O1", required=False, decision_required=True)
        errs = H.check_plan(self.plan([obligation("O0"), bad]), None, self.intent)
        self.assertIn("plan.optional_decision_required", codes(errs))
        notbool = obligation("O1", decision_required=1)
        self.assertIn("plan.decision_required_missing", codes(H.check_plan(self.plan([notbool]), None, self.intent)))

    def test_n46_plan_cannot_carry_another_target_tier(self):
        p = self.plan([obligation("O1")], target_tier="R1")
        self.assertIn("plan.target_tier", codes(H.check_plan(p, None, self.intent)))

    def downgrade(self, earlier, revised, **kw):
        c = Case()
        parent = c.plan([earlier])
        child = c.plan([revised], **kw)
        return codes(H.check_plan(child, parent, c.intent))

    def test_a10_a22a_downgrades_rejected_at_commit(self):
        o = obligation("O1", tolerances=[{"quantity": "x", "value": "0.001", "kind": "relative"}],
                       adoption={"second_method_required": True, "verification_required": True,
                                 "qualifications": ["stats"]}, independence_requirements=["second-reviewer"])
        cases = {
            "downgrade.required_removed": None,
            "downgrade.required_to_optional": dict(o, required=False, decision_required=False),
            "downgrade.method_removed": dict(o, required_methods=[]),
            "downgrade.evidence_removed": dict(o, evidence_requirements=[]),
            "downgrade.independence_removed": dict(o, independence_requirements=[]),
            "downgrade.decision_required_dropped": dict(o, decision_required=False),
            "downgrade.tolerance_loosened": dict(o, tolerances=[{"quantity": "x", "value": "0.01", "kind": "relative"}]),
            "downgrade.adoption_loosened": dict(o, adoption_policy={"second_method_required": False,
                                                                    "verification_required": True,
                                                                    "qualifications": ["stats"]}),
            "downgrade.criterion_changed": dict(o, criterion="A looser criterion."),
            "downgrade.assumptions_changed": dict(o, assumptions=["Gaussian errors"]),
        }
        for code, revised in cases.items():
            with self.subTest(code):
                if revised is None:
                    c = Case()
                    parent = c.plan([o, obligation("O2")])
                    child = c.plan([obligation("O2")])
                    got = codes(H.check_plan(child, parent, c.intent))
                else:
                    got = self.downgrade(o, revised)
                self.assertIn(code, got)

    def test_plan_level_independence_floor_removal_is_a_downgrade(self):
        c = Case()
        parent = c.plan([obligation("O1")])
        child = c.plan([obligation("O1")], independence=[])
        self.assertIn("downgrade.independence_removed", codes(H.check_plan(child, parent, c.intent)))

    def test_strengthening_is_accepted(self):
        o = obligation("O1", tolerances=[{"quantity": "x", "value": "0.01", "kind": "relative"}])
        stronger = dict(o, tolerances=[{"quantity": "x", "value": "0.001", "kind": "relative"}],
                        required_methods=["recompute", "independent-derivation"])
        self.assertEqual(self.downgrade(o, stronger), set())

    def test_n58_criterion_change_needs_equivalent_or_stronger_judgment(self):
        o = obligation("O1")
        revised = dict(o, criterion="A reworded criterion.")
        self.assertIn("downgrade.criterion_changed", self.downgrade(o, revised))
        j = {"id": "J1", "kind": "equivalent_or_stronger", "obligation_ids": ["O1"], "actor": "verifier-1",
             "basis": "declared", "reason": "same test, clearer words"}
        self.assertEqual(self.downgrade(o, revised, judgments=[j]), set())

    def test_n56_obligation_map_cannot_retire_or_demote_required(self):
        c = Case()
        parent = c.plan([obligation("O1")])
        child = c.plan([obligation("O1a", required=False, decision_required=False)],
                       obligation_map=[{"old_id": "O1", "new_ids": ["O1a"], "retired_reason": None}])
        self.assertIn("downgrade.mapped_to_optional", codes(H.check_plan(child, parent, c.intent)))
        c = Case()
        parent = c.plan([obligation("O1"), obligation("O2")])
        child = c.plan([obligation("O2")], obligation_map=[{"old_id": "O1", "new_ids": [], "retired_reason": "done"}])
        self.assertIn("downgrade.required_retired", codes(H.check_plan(child, parent, c.intent)))

    def test_change_request_is_not_handled_in_this_version(self):
        o = obligation("O1")
        got = self.downgrade(o, dict(o, required_methods=[]), change_request={"id": "CR1", "authorized_by": "user"})
        self.assertIn("downgrade.method_removed", got)
        self.assertIn("plan.change_request_unsupported", got)


class CreationOrderAndRefs(unittest.TestCase):
    def test_a25_n05_object_embedding_its_own_digest_is_rejected(self):
        c = Case()
        p = c.plan([obligation("O1")])
        bad = dict(p, self_ref={"logical_id": p["id"], "digest": H.metadata_digest(p)})
        self.assertIn("object.self_reference", codes(H.check_object(bad)))
        bad2 = dict(p, digest="ab" * 32)
        self.assertIn("object.embedded_digest", codes(H.check_object(bad2)))
        bad3 = dict(p, excluded_fields=["judgments"])
        self.assertIn("object.producer_excluded_fields", codes(H.check_object(bad3)))

    def test_a25_plan_cannot_reference_assignments_or_packets(self):
        c = Case()
        p = c.plan([obligation("O1")], assignments=["asg-1"])
        self.assertIn("order.plan_references_assignment", codes(H.check_object(p)))
        packet = header("packet", "pk-1") | {"assignment_id": "asg-1", "obligation_ids": ["O1"]}
        self.assertIn("order.packet_references_assignment", codes(H.check_object(packet)))
        report = header("report", "rep-1")
        self.assertIn("order.report_is_not_a_commit_input", codes(H.check_object(report)))

    def test_a25_back_filled_reference_to_a_later_object_is_quarantined(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        # commit the record before its assignment: the record then references a later object
        e = c.entries
        i_asg = next(i for i, x in enumerate(e) if x["objects"][0]["id"] == r["assignment_id"])
        i_rec = next(i for i, x in enumerate(e) if x["objects"][0]["id"] == r["id"])
        e[i_asg], e[i_rec] = e[i_rec], e[i_asg]
        v = H.validate(c.bundle(), V)
        self.assertIn(r["id"], v["quarantined_records"])

    def test_p04_same_digest_other_profile_is_not_the_same_ref(self):
        a = {"logical_id": "x", "algorithm": "sha256", "hash_scope": "raw", "profile_id": H.RAW_PROFILE, "digest": "ab" * 32}
        b = dict(a, profile_id=H.METADATA_PROFILE, hash_scope="metadata")
        self.assertFalse(H.same_ref(a, b))
        self.assertTrue(H.same_ref(a, dict(a)))

    def test_p03_p28_legacy_native_hash_kept_field_by_field(self):
        native = {"approval_ref": "R-1", "manifest_sha256": "cd" * 32, "files": 3}
        lr = H.legacy_ref("release-approval/1", native, logical_id="approval-1")
        self.assertEqual(lr["profile_id"], "legacy:release-approval/1")
        self.assertEqual(lr["native"]["manifest_sha256"], "cd" * 32)
        self.assertEqual(lr["excluded_fields"], ["approval_ref"])
        raw = {"logical_id": "approval-1", "algorithm": "sha256", "hash_scope": "raw", "profile_id": H.RAW_PROFILE,
               "digest": "cd" * 32}
        self.assertFalse(H.same_ref(lr, raw))
        with self.assertRaises(ValueError):
            H.legacy_ref("unknown-adapter/1", native, logical_id="x")


class Disposition(unittest.TestCase):
    def test_a05_a27_corrupt_evidence_quarantines_dependents_only(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O2")])
        ra = c.review("O1", "violated", finding=True)
        rb = c.review("O2", "supported")
        c.blob_checks[rb["evidence"][0]["content_ref"]["digest"]] = "changed"
        v, p, s = run(c)
        self.assertIn(rb["evidence"][0]["id"], v["quarantined_items"])
        self.assertIn(rb["answers"][0]["id"], v["quarantined_items"])
        self.assertNotIn(ra["findings"][0]["id"], v["quarantined_items"])
        self.assertEqual(outcome(p, "O1")["outcome"], "violated")
        self.assertEqual(outcome(p, "O2")["outcome"], "not-examined")
        self.assertIn("dependency_gap", {r["kind"] for r in p["open_reasons"]})

    def test_a27_unknown_dependency_quarantines_whole_record(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported", answer_extra={"depends_on": ["E-does-not-exist"]})
        v, p, s = run(c)
        self.assertIn(r["id"], v["quarantined_records"])
        self.assertEqual(outcome(p, "O1")["outcome"], "not-examined")

    def test_invalid_role_binding_quarantines_record_and_keeps_raw_ref(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported")
        for e in c.entries:  # committed as such: the record names an actor that is not its assignment's
            if e["objects"][0]["id"] == r["id"]:
                e["objects"][0]["actor"] = "someone-else"
        v = H.validate(c.bundle(), V)
        self.assertEqual(v["quarantined_records"][r["id"]]["code"], "binding.actor")
        p = H.project(v, V)
        self.assertIn(r["id"], [q["record_id"] for q in p["quarantined"]])
        self.assertTrue(all(q["raw_submission_ref"] for q in p["quarantined"]))

    def test_a06_no_trustworthy_scope_is_input_error_only(self):
        c = Case()
        c.intent["material_scope"] = []
        c.entries[0]["objects"][0]["material_scope"] = []
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        v, p, s = run(c)
        self.assertEqual(p["input_error"]["code"], "input.no_scope")
        self.assertNotIn("obligations", p)
        self.assertFalse(s["output_summary"])

    def test_a07_not_applicable_because_hard_is_refused(self):
        for reason in ("missing-data", "difficulty", "budget"):
            with self.subTest(reason):
                c = Case()
                c.plan([obligation("O1")])
                r = c.review("O1", "not-applicable", discharge={"reason_category": reason, "basis": "declared",
                                                               "reason": "too hard"})
                v, p, s = run(c)
                self.assertEqual(v["quarantined_items"][r["answers"][0]["id"]]["code"], "discharge.invalid_reason")
                self.assertEqual(outcome(p, "O1")["outcome"], "not-examined")

    def test_a07_author_cannot_discharge(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "not-applicable", actor="author-a",
                     discharge={"reason_category": "condition-absent", "basis": "declared", "reason": "n/a"})
        v, p, s = run(c)
        self.assertEqual(v["quarantined_items"][r["answers"][0]["id"]]["code"], "discharge.by_author")

    def test_a26_only_committed_objects_are_projected(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "violated", finding=True)
        b = c.bundle()
        b["uncommitted_judgments"] = [{"kind": "finding_assessment", "verdict": "refuted"}]
        with self.assertRaises(H.BundleError):
            H.validate(b, V)
        with self.assertRaises(TypeError):
            H.project(H.validate(c.bundle(), V), V, judgments=[])  # type: ignore[call-arg]

    def test_n69_mismatch_quarantines_submission(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "supported", fidelity="mismatch")
        v, p, s = run(c)
        self.assertEqual(v["quarantined_records"][r["id"]]["code"], "fidelity.mismatch")
        self.assertEqual(p["record_integrity"], "partial-invalid")


class Findings(unittest.TestCase):
    def test_a14_a17_direct_adoption_under_policy(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "violated", finding=True)
        v, p, s = run(c)
        f = next(x for x in p["findings"] if x["id"] == r["findings"][0]["id"])
        self.assertEqual(f["state"], "supported")
        self.assertTrue(f["current"])

    def test_verification_required_keeps_candidate_until_verified(self):
        pol = {"second_method_required": False, "verification_required": True, "qualifications": []}
        c = Case()
        c.plan([obligation("O1", adoption=pol)])
        r = c.review("O1", "violated", finding=True)
        v, p, s = run(c)
        fid = r["findings"][0]["id"]
        self.assertEqual(next(x for x in p["findings"] if x["id"] == fid)["state"], "candidate")
        self.assertEqual(outcome(p, "O1")["outcome"], "undetermined")
        self.assertTrue(p["flags"]["has_open_questions"])
        c.judge([{"id": "J1", "kind": "finding_assessment", "finding_id": fid, "verdict": "supported",
                  "basis": "observed", "depends_on": []}])
        v, p, s = run(c)
        self.assertEqual(next(x for x in p["findings"] if x["id"] == fid)["state"], "supported")
        self.assertEqual(outcome(p, "O1")["outcome"], "violated")

    def test_a15_fix_submitted_but_not_reverified(self):
        c = Case()
        c.plan([obligation("O1")])
        r = c.review("O1", "violated", finding=True)
        fid = r["findings"][0]["id"]
        c.review("O1", None, actor="author-a", role="author", record_type="response", evidence=False,
                 responses=[{"id": "R1", "finding_id": fid, "response": "changed", "fix_check": "pending"}])
        v, p, s = run(c)
        f = next(x for x in p["findings"] if x["id"] == fid)
        self.assertEqual(f["state"], "supported")
        self.assertEqual(f["response"], "changed")
        self.assertEqual(f["fix_check"], "pending")
        self.assertTrue(p["flags"]["has_supported_defects"])

    def test_two_conflicting_adjudications_remain_disputed(self):
        c = _conflicting()
        fid, jid = c._fid, c._jid
        for verdict, actor in (("supported", "arb-1"), ("refuted", "arb-2")):
            c.judge([{"id": f"ADJ-{actor}", "kind": "adjudication", "finding_id": fid, "handles": [jid, fid],
                      "verdict": verdict, "basis": "declared", "depends_on": []}], actor=actor, role="arbiter")
        v, p, s = run(c)
        self.assertEqual(next(x for x in p["findings"] if x["id"] == fid)["state"], "disputed")

    def test_one_adjudication_resolves(self):
        c = _conflicting()
        c.judge([{"id": "ADJ-1", "kind": "adjudication", "finding_id": c._fid, "handles": [c._jid, c._fid],
                  "verdict": "refuted", "basis": "declared", "depends_on": []}], actor="arb-1", role="arbiter")
        v, p, s = run(c)
        self.assertEqual(next(x for x in p["findings"] if x["id"] == c._fid)["state"], "refuted")
        self.assertFalse(p["flags"]["has_disputed_findings"])

    def test_n12_free_text_is_not_a_conflict_but_suspicion_stays_open(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        c.review("O1", "supported", answer_extra={"reasoning": "this is completely wrong"})
        v, p, s = run(c)
        self.assertFalse(p["flags"]["has_disputed_findings"])
        self.assertTrue(s["output_summary"])


def _conflicting():
    c = Case()
    c.plan([obligation("O1", decision_required=False)])
    r = c.review("O1", "violated", finding=True)
    fid = r["findings"][0]["id"]
    c.review("O1", "supported", judgments=[{"id": "J-x", "kind": "finding_assessment", "finding_id": fid,
                                           "verdict": "refuted", "basis": "declared", "depends_on": []}])
    c._fid, c._jid = fid, "J-x"
    return c


class Closures(unittest.TestCase):
    def test_n20_tools_missing_is_not_empty(self):
        a = {"executor": "exec-1", "environment_refs": []}
        self.assertIsNone(H.environment_component(a, observations=None))
        self.assertEqual(H.environment_component(dict(a, tools=[]), observations=[]), {"tools": []})

    def test_p18_environment_change_alone_changes_the_closure(self):
        c = Case()
        o = obligation("O1")
        c.plan([o], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
        c.review("O1", "supported")
        c.plan([o], env=[{"executor": "exec-1", "tools": ["python3", "numpy-2.4"], "environment_refs": []}])
        v, p, s = run(c)
        self.assertEqual(outcome(p, "O1")["outcome"], "not-examined")
        self.assertIn("stale", outcome(p, "O1")["reasons"][0])

    def test_n33_uncited_target_changed(self):
        from test_hep_review_decision_table import kernel
        p, s, _ = kernel("D12a")
        self.assertEqual(outcome(p, "O1")["outcome"], "not-examined")


class Tiers(unittest.TestCase):
    def test_n29_self_reported_fresh_context_is_not_the_floor(self):
        c = Case()
        c.plan([obligation("O1")])
        cond = {"non-author": {"satisfied": True, "basis": "declared"}, "fresh-context": {"satisfied": True, "basis": "self-reported"},
                "no-other-evaluations-seen": {"satisfied": True, "basis": "advisory"}}
        c.review("O1", "supported", conditions=cond)
        v, p, s = run(c)
        self.assertEqual(outcome(p, "O1")["obligation_tier"], "R1")
        self.assertIn("fresh-context", " ".join(outcome(p, "O1")["tier_reasons"]))

    def test_n28_floor_condition_marked_optional(self):
        c = Case()
        ind = [{"condition": "non-author", "required": True}, {"condition": "fresh-context", "required": False},
               {"condition": "no-other-evaluations-seen", "required": True}]
        c.plan([obligation("O1")], independence=ind)
        c.review("O1", "supported")
        v, p, s = run(c)
        self.assertEqual(p["achieved_tier"], "R1")
        self.assertTrue(p["independence_floor_not_met"])
        self.assertIn("independent-review floor not met", " ".join(s["disclosure"]))

    def test_advisory_wording_present_at_r2(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        v, p, s = run(c)
        self.assertEqual(p["achieved_tier"], "R2")
        self.assertIn("instructed not to read other evaluations; this was neither observed nor enforced",
                      s["summary_text"])

    def test_transcribed_submission_is_at_most_r1(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported", fidelity="transcribed")
        v, p, s = run(c)
        self.assertEqual(p["achieved_tier"], "R1")

    def test_optional_obligation_tier_does_not_lower_report(self):
        c = Case()
        c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
        c.review("O1", "supported")
        c.review("O2", "supported", fidelity="transcribed")
        v, p, s = run(c)
        self.assertEqual(p["achieved_tier"], "R2")
        self.assertEqual(outcome(p, "O2")["obligation_tier"], "R1")

    def test_n37_n63_r3_needs_claim_binding_with_chain_segment(self):
        def r3_case(binding):
            c = Case(target_tier="R3")
            c.plan([obligation("O1")], required_restrictions=["no-network"])
            c.review("O1", "supported", conditions=None)
            for e in c.entries:
                o = e["objects"][0]
                if o["record_kind"] == "assignment":
                    o["restrictions"] = [{"id": "no-network", "status": "enforced", "basis": "observed"}]
            c.extra_claim = binding
            return run(c)
        v, p, s = r3_case(None)
        self.assertEqual(p["achieved_tier"], "R2")
        good = make_binding()
        v, p, s = r3_case(good)
        self.assertEqual(p["achieved_tier"], "R3")
        no_chain = dict(good, chain_segment=[])
        self.assertEqual(r3_case(no_chain)[1]["achieved_tier"], "R2")
        wrong_fp = dict(good, case_fingerprint="other")
        self.assertEqual(r3_case(wrong_fp)[1]["achieved_tier"], "R2")
        broken = copy.deepcopy(good)
        broken["chain_segment"][1]["commit"]["prev_commit_digest"] = "00" * 32
        self.assertEqual(r3_case(broken)[1]["achieved_tier"], "R2")
        v, p, s = r3_case(good)
        s2 = H.decide_summary(p, dict(GOOD_ATT, r3_state_matches=False))
        self.assertFalse(s2["output_summary"])
        self.assertIn("rebind", " ".join(s2["disclosure"]))


def make_binding():
    claim = {"id": "claim-1", "state": "pilot-checked-scope", "fingerprint": "fp-1"}
    claim_digest = H.metadata_digest(claim)
    chain = []
    prev = None
    for seq, objs in ((1, [{"digest": hexd("protocol")}]), (2, [{"digest": claim_digest}])):
        c = {"protocol": H.PROTOCOL, "context_id": "eval-1", "segment_id": "eval-seg", "seq": seq,
             "prev_commit_digest": prev, "operation_id": f"e{seq}", "payload_digest": hexd(f"p{seq}"),
             "validator_version": V, "writer_session_id": "s"}
        d = H.metadata_digest(c)
        chain.append({"commit": c, "digest": d, "object_digests": [o["digest"] for o in objs]})
        prev = d
    return {"claim": claim, "chain_segment": chain, "trusted_checkpoint": {"seq": 1, "digest": chain[0]["digest"]},
            "case_fingerprint": "fp-1"}


class Facets(unittest.TestCase):
    def test_p11_exit_zero_or_hash_is_not_reproduction(self):
        c = Case()
        c.plan([obligation("O1", methods=("functional-check",))])
        c.review("O1", "supported", method="functional-check")
        v, p, s = run(c)
        f = outcome(p, "O1")["facets"]
        self.assertTrue(f["artifact_functional"]["performed"])
        self.assertFalse(f["result_reproduced"]["performed"])
        self.assertFalse(f["independent_method_checked"]["performed"])

    def test_reproduction_needs_preset_reference_and_tolerance(self):
        c = Case()
        tol = [{"quantity": "sigma", "value": "0.001", "kind": "relative"}]
        c.plan([obligation("O1", methods=("reproduction",), tolerances=tol)])
        r = c.review("O1", "supported", method="reproduction")
        b = c.bundle()
        v, p, s = run(c)
        self.assertFalse(outcome(p, "O1")["facets"]["result_reproduced"]["performed"])
        c2 = Case()
        c2.plan([obligation("O1", methods=("reproduction",), tolerances=tol)])
        c2.review("O1", "supported", method="reproduction")
        for e in c2.entries:
            o = e["objects"][0]
            if o["record_kind"] == "record":
                o["attempts"][0]["reproduction"] = {"reference_quantities": ["sigma"], "tolerance_quantities": ["sigma"]}
        v, p, s = run(c2)
        self.assertTrue(outcome(p, "O1")["facets"]["result_reproduced"]["performed"])
        del r, b

    def test_stale_obligation_has_no_current_positive_facet(self):
        c = Case()
        o = obligation("O1", methods=("functional-check",))
        c.plan([o])
        c.review("O1", "supported", method="functional-check")
        c.new_manifest(M1="M1-v9")
        c.plan([o])
        v, p, s = run(c)
        self.assertFalse(outcome(p, "O1")["facets"]["artifact_functional"]["performed"])


class Rendering(unittest.TestCase):
    def setUp(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        _, self.p, _ = run(c)
        self.att = GOOD_ATT
        self.kw = {"bundle": c.bundle(), "validator_version": V}

    def test_render_has_summary_with_qualifier_in_same_sentence(self):
        text = H.render_report(H.encode(self.p), self.att, **self.kw)
        line = next(x for x in text.split("\n") if "no still-valid defect was observed" in x)
        self.assertIn("R2 (independent review under the recorded conditions)", line)

    def test_n36_template_without_qualifier_refused(self):
        with self.assertRaises(H.RenderError):
            H.render_report(H.encode(self.p), self.att, presentation={"summary_sentence": "No defects found."},
                            **self.kw)

    def test_p24_n14_presentation_cannot_hand_fill_or_signal_pass(self):
        for key in ("facets", "flags", "outcomes", "closed", "formal_use_allowed", "achieved_tier"):
            with self.subTest(key):
                with self.assertRaises(H.RenderError):
                    H.render_report(H.encode(self.p), self.att, presentation={key: True}, **self.kw)
        tampered = json.loads(H.encode(self.p))
        tampered["obligations"][0]["facets"]["result_reproduced"]["performed"] = True
        with self.assertRaises(H.RenderError):
            H.render_report(json.dumps(tampered).encode(), self.att, **self.kw)
        with self.assertRaises(H.RenderError):
            H.render_report(H.encode(tampered), self.att, **self.kw)

    def test_n14_discharge_display_is_not_an_enum(self):
        self.assertNotIn("not-run-with-approved-discharge", H.OUTCOMES)
        self.assertNotIn("not-run-with-approved-discharge", H.METHOD_OBSERVATIONS)

    def test_r0_never_renders_no_defect_summary(self):
        c = Case(mode="R0")
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        _, p, s = run(c)
        text = H.render_report(H.encode(p), GOOD_ATT, bundle=c.bundle(), validator_version=V)
        self.assertNotIn("no still-valid defect", text)
        self.assertIn("unrecorded, non-independent preliminary opinion", text)


class Reproducibility(unittest.TestCase):
    def test_n60_layer1_bytes_identical_after_export_round_trip(self):
        from test_hep_review_decision_table import ROWS
        for row in ("D1", "D6", "D13", "D16", "D25"):
            with self.subTest(row):
                b = ROWS[row][2]().bundle()
                one = H.encode(H.project(H.validate(b, V), V))
                again = H.ingest_json(H.encode(b), max_depth=128)
                two = H.encode(H.project(H.validate(again, V), V))
                self.assertEqual(one, two)

    def test_n38_historical_check_with_old_validator(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        b = c.bundle()
        old = H.encode(H.project(H.validate(b, V), V))
        self.assertEqual(H.check_historical(old, b, V), "match")
        with self.assertRaises(ValueError):
            H.check_historical(old, b, "9.9.9")

    def test_layer1_carries_as_of_and_validator(self):
        c = Case()
        c.plan([obligation("O1")])
        c.review("O1", "supported")
        b = c.bundle()
        p = H.project(H.validate(b, V), V)
        self.assertEqual(p["as_of_seq"], b["as_of_seq"])
        self.assertEqual(p["as_of_commit_digest"], b["as_of_commit_digest"])
        self.assertEqual(p["validator_version"], V)


class Schemas(unittest.TestCase):
    def test_n11_fixture_objects_and_layer1_match_the_schemas(self):
        from test_hep_review_decision_table import ROWS
        for row in ("D1", "D2", "D6", "D16", "D25", "D29"):
            b = ROWS[row][2]().bundle()
            for x in b["commits"]:
                for o in x["objects"]:
                    with self.subTest(row=row, obj=o["id"]):
                        rep = schema_validate(o, f"hep_review_{o['record_kind']}.json")
                        self.assertTrue(rep.ok, rep.as_dict())
            p = H.project(H.validate(b, V), V)
            rep = schema_validate(p, "hep_review_report.json")
            self.assertTrue(rep.ok, rep.as_dict())

    def test_schema_rejects_bool_as_integer_and_unknown_fields(self):
        c = Case()
        p = c.plan([obligation("O1")])
        self.assertFalse(schema_validate(dict(p, revision=True), "hep_review_plan.json").ok)
        self.assertFalse(schema_validate(dict(p, surprise=1), "hep_review_plan.json").ok)


if __name__ == "__main__":
    unittest.main()
