"""Contract side of the optional expert slot (contracts 3.6.0; docs/dev/independent-review-spec.md sections 5.1, 5.3,
6.10 and 7.6): the spec's tables against the code, the context-free rules of an expert record, receipt without
coverage or canary rules, fold and snapshot (kind expert), the expert slot's attempt limit, the log transitions, the
carry-forward of a changed expert finding to the design lens, and an exhaustive check that an expert slot is
dispatched and received like any other but never escalated. Synthetic data only."""
from __future__ import annotations

import copy
import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-authoring" / "scripts"))

from contracts import review as R  # noqa: E402
from review_lib.packet import example_record, expert_example_record  # noqa: E402
from tests.contracts.test_review_contract import spec_section  # noqa: E402
from tests.contracts.test_review_state import DL, SLOT_STATES, T, base_events, ev, first_row, slot, snap  # noqa: E402


def expert_events(max_attempts=None):
    """base_events with an expert slot S3 in round 1 (model m-x), not yet dispatched."""
    evs = base_events(sev="medium", second_verdict="partially-supported")
    rs = evs[0]["data"]
    rs["config"]["expert"] = {"model": "m-x"}
    if max_attempts:
        rs["config"]["max_attempts_per_slot"] = max_attempts
    rs["slots"].append({"slot_id": "S3", "model": "m-x"})
    rs["expert"] = {"slot_id": "S3", "model": "m-x"}
    return evs


def accept_expert(evs, verdict="unsupported", units=("U0007",)):
    return evs + [ev("dispatched", round=1, slot_id="S3", attempt=1, deadline=DL),
                  ev("accepted", round=1, slot_id="S3", attempt=1,
                     verdicts=[{"claim_id": "C1", "units": list(units), "verdict": verdict, "finding_ids": ["F1"],
                                "eligible": True}],
                     findings=[{"id": "F1", "severity": "medium", "units": list(units)}])]


def ctx(**kw):
    c = {"kind": "expert", "lens": "facts", "slot_id": "S9",
         "dispatched": {"packet_sha256": "0123456789abcdef" * 4, "nonce": "n0nce-from-dispatch-line",
                        "instructions_sha256": "0123456789abcdef" * 4},
         "author": "author-agent", "parties": [], "limits": {"max_units_per_claim": 3},
         "unit_text": {"U0011": "Earlier text.", "U0012": "Here rapidity is unchanged by a boost along the beam axis.",
                       "U0031": "Later the shift is used."},
         "skim_units": [], "deep_units": [], "canaries": [], "carry_refs": [], "items": {}, "files": {},
         "instructions_changed": False}
    c.update(kw)
    return c


class SpecTests(unittest.TestCase):
    def test_receipt_codes_are_in_the_spec(self):
        text = spec_section("7.6 Receipt rules (expert slot)")
        for code in R.EXPERT_CODES:
            self.assertIn(f"`{code}`", text, code)
        for code in ("canary_missed", "deep_missing", "skim_missing", "carry_forward_missing", "unresolved_dominant",
                     "refutation_weak"):
            if code not in R.EXPERT_CODES:
                self.assertIn(f"`{code}`", text, code)  # named as not applying

    def test_config_and_flow_sections(self):
        self.assertIn("`expert`", spec_section("5.1 Configuration `review_config` (1.0.0)"))
        flow = spec_section("6.10 Expert slot (contracts 3.6.0, optional)")
        for part in ("Canaries: none", "round 1", "whole document", "min(2, `max_attempts_per_slot`)", "row 9"):
            self.assertIn(part, flow)

    def test_codes(self):
        self.assertEqual(R.EXPERT_MAX_ATTEMPTS, 2)
        self.assertEqual(set(R.EXPERT_CODES) - set(R.REVIEWER_CODES), {"finding_without_verdict"})
        self.assertEqual(R.ROLE_REQUIRED["expert"], ("claims", "verdicts", "findings"))


class RecordRuleTests(unittest.TestCase):
    def setUp(self):
        self.rec = expert_example_record("S9")

    def codes(self, rec, role="expert"):
        return sorted({c for c, _ in R.record_rules(rec, role)})

    def test_example_passes_and_roles_do_not_mix(self):
        self.assertEqual(self.codes(self.rec), [])
        self.assertEqual(self.codes(self.rec, "reviewer"), ["schema_invalid"])
        self.assertEqual(self.codes(example_record("lens", "S1"), "expert"), ["schema_invalid"])
        self.assertEqual(self.codes(dict(self.rec, role="filter")), ["schema_invalid"])

    def test_role_required_and_forbidden_fields(self):
        for key in ("claims", "verdicts", "findings"):
            rec = copy.deepcopy(self.rec)
            rec.pop(key)
            self.assertIn("schema_invalid", self.codes(rec), key)
        for key, val in (("skim", [{"unit": "U0012", "mark": "ok"}]), ("carry_forward", [{"ref": "CF1", "status": "reopened"}]),
                         ("resolves", [{"item_id": "A1.1", "conclusion": "unresolved", "rationale": "r", "evidence_ids": []}])):
            self.assertEqual(self.codes(dict(self.rec, **{key: val})), ["schema_invalid"], key)
        self.assertEqual(self.codes(dict(self.rec, skim=[], carry_forward=[])), [])  # empty lists are harmless

    def test_finding_without_verdict(self):
        rec = copy.deepcopy(self.rec)
        rec["verdicts"][0].update(verdict="unresolved", finding_ids=[])
        self.assertEqual(self.codes(rec), ["finding_without_verdict"])
        rec = copy.deepcopy(self.rec)
        rec["verdicts"][0]["verdict"] = "supported"
        rec["verdicts"][0]["refutation_attempts"] = [{"method": "m", "target": "U0031", "outcome": "o"}]
        self.assertEqual(self.codes(rec), ["finding_without_verdict"])
        rec = copy.deepcopy(self.rec)
        rec["findings"].append(dict(rec["findings"][0], id="F2"))
        self.assertEqual(self.codes(rec), ["finding_without_verdict"])

    def test_nothing_found(self):
        self.assertEqual(self.codes(dict(self.rec, claims=[], verdicts=[], findings=[])), [])


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.rec = expert_example_record("S9")
        self.rec["findings"][0]["value"] = "rapidity is unchanged by a boost along the beam axis"
        self.rec["paths_read"] = []  # no file facts in this pure test

    def codes(self, rec, **kw):
        return sorted({c for c, _ in R.receipt_codes(rec, ctx(**kw))})

    def test_good_record_and_no_coverage_rules(self):
        # output files are not in work/ in this pure test: only output_mismatch, nothing on coverage or canaries
        self.assertEqual(self.codes(self.rec), ["output_mismatch"])
        self.assertEqual(self.codes(self.rec, deep_units=["U0011", "U0031"], skim_units=["U0011"],
                                    canaries=[{"unit": "U0031", "new_key": "9", "old_key": "8"}], carry_refs=["CF1"]),
                         ["output_mismatch"])

    def test_basis_missing_any_evidence(self):
        rec = copy.deepcopy(self.rec)
        rec["evidence"] = [rec["evidence"][1]]
        rec["verdicts"][0]["evidence_ids"] = ["E2"]
        self.assertEqual(self.codes(rec), [])  # internal evidence is enough: the expert slot is loose
        rec["verdicts"][0]["evidence_ids"] = []
        self.assertEqual(self.codes(rec), ["basis_missing"])
        rec["verdicts"][0].update(verdict="unresolved", finding_ids=[])
        rec["findings"] = []
        self.assertEqual(self.codes(rec), [])  # an unresolved verdict needs no evidence

    def test_identity_shape_and_role(self):
        rec = copy.deepcopy(self.rec)
        rec["evidence"] = [rec["evidence"][1]]
        rec["verdicts"][0]["evidence_ids"] = ["E2"]
        self.assertEqual(self.codes(rec, author="expert-agent-1"), ["same_identity"])
        bad = copy.deepcopy(rec)
        bad["findings"][0]["value"] = "not in the unit"
        self.assertEqual(self.codes(bad), ["finding_shape"])
        bad = copy.deepcopy(rec)
        bad["claims"][0]["units"] = ["U0099"]
        self.assertEqual(self.codes(bad), ["claim_shape"])
        self.assertEqual(self.codes(dict(rec, role="reviewer")), ["schema_invalid"])
        self.assertEqual(self.codes(rec, slot_id="S1"), ["dispatch_mismatch"])


class StateTests(unittest.TestCase):
    def test_fold_and_snapshot(self):
        st = R.fold(expert_events())
        self.assertEqual(st["expert_slots"], {(1, "S3"): "m-x"})
        s = R.snapshot(st)
        self.assertEqual(s["slots"]["S3"], {"state": "none", "attempt": 0, "deadline": None, "kind": "expert",
                                            "resolved": False})
        self.assertEqual(R.decide(s), {"row": 7, "action": "dispatch", "slots": ["S3"]})
        self.assertEqual(R.sidecar_name(st, 1, "S3"), R.SIDECAR)

    def test_accepted_expert_findings_are_ordinary_findings(self):
        st = R.fold(accept_expert(expert_events()))
        self.assertEqual(st["findings"]["1/S3/F1"]["state"], "open")
        self.assertIn("1/S3/C1", st["verdicts"])
        self.assertIn("1/S3/F1", R.filter_pool(st))
        self.assertEqual(R.decide(R.snapshot(st)), {"row": 12, "action": "dispose", "findings": ["1/S2/F1", "1/S3/F1"]})

    def test_expert_verdict_forms_a_conflict(self):
        st = R.fold(accept_expert(expert_events(), units=("U0001",)))
        need = R.needed_items(st)
        self.assertIn({"type": "conflict", "first": "1/S1/C1", "second": "1/S3/C1", "finding": None}, need)

    def test_exhausted_after_two_attempts_and_not_escalated(self):
        evs = expert_events(max_attempts=3)
        for k in (1, 2):
            evs += [ev("dispatched", round=1, slot_id="S3", attempt=k, deadline=DL),
                    ev("rejected", round=1, slot_id="S3", attempt=k, codes=["x"])]
        s = R.snapshot(R.fold(evs))
        self.assertEqual((s["slots"]["S3"]["state"], s["slots"]["S3"]["kind"]), ("exhausted", "expert"))
        self.assertEqual(R.decide(s)["action"], "dispose")
        self.assertNotIn("slot:1/S3", R.escalation_items(s))
        self.assertEqual(R.slot_state(R.fold(expert_events(max_attempts=1)), 1, "S3")["state"], "none")

    def test_transitions(self):
        recs = []
        for e in expert_events(max_attempts=3):
            recs.append(R.make_event(recs[-1] if recs else None, e["event"], T, e["data"]))
        self.assertEqual(R.transition_problems(recs), [])
        third = recs[:]
        for k in (1, 2, 3):
            third.append(R.make_event(third[-1], "dispatched", T, {"round": 1, "slot_id": "S3", "attempt": k}))
            third.append(R.make_event(third[-1], "rejected", T, {"round": 1, "slot_id": "S3", "attempt": k}))
        self.assertIn("attempt 3 out of order for (1, 'S3')", " ".join(R.transition_problems(third)))
        lens3 = recs[:]  # base_events already holds S2's attempt 1, accepted; a review slot may not get a fourth
        for k in (1, 2, 3):
            lens3.append(R.make_event(lens3[-1], "dispatched", T, {"round": 1, "slot_id": "S2", "attempt": k + 1}))
            lens3.append(R.make_event(lens3[-1], "rejected", T, {"round": 1, "slot_id": "S2", "attempt": k + 1}))
        self.assertTrue(any("attempt 4 out of order" in x for x in R.transition_problems(lens3)))

    def test_carry_forward_of_a_changed_expert_finding(self):
        evs = accept_expert(expert_events())
        evs.append(ev("disposed", finding="1/S3/F1", disposition="changed", reason="r", verification={"verified": "x"},
                      edited_units=["U0007"], finding_units=["U0007"], round=1, by="a"))
        st = R.fold(evs)
        self.assertEqual(st["findings"]["1/S3/F1"]["state"], "changed")
        mapping = {"unchanged": [], "changed": [["U0007", "U0008"], ["U0001", "U0001"]], "added": [], "removed": []}
        roles = {"1": {"S1": {"role": "lens", "lens": "facts"}, "S2": {"role": "lens", "lens": "design"},
                       "S3": {"role": "expert", "lens": None}}}
        plan, removed = R.carry_forward_plan(st, mapping, roles, {"facts": "S5", "design": "S6"})
        self.assertIn({"ref": plan["S6"][-1]["ref"], "kind": "finding", "target": "1/S3/F1", "units": ["U0008"]}, plan["S6"])
        self.assertEqual(removed, [])
        plan, removed = R.carry_forward_plan(st, mapping, roles, {"facts": "S5"})  # no design lens slot
        self.assertEqual(removed, ["1/S3/F1"])
        self.assertFalse([c for c in plan["S5"] if c["target"] == "1/S3/F1"])

    def test_expert_verdicts_are_not_carried_forward(self):
        st = R.fold(accept_expert(expert_events()))
        mapping = {"unchanged": [["U0001", "U0001"], ["U0007", "U0007"]], "changed": [], "added": [], "removed": []}
        roles = {"1": {"S1": {"role": "lens", "lens": "facts"}, "S2": {"role": "lens", "lens": "design"},
                       "S3": {"role": "expert", "lens": None}}}
        plan, _ = R.carry_forward_plan(st, mapping, roles, {"facts": "S5", "design": "S6"})
        self.assertFalse([c for cs in plan.values() for c in cs if c["target"].startswith("1/S3/")])

    def test_exhaustive_expert_slot(self):
        """Two review slots and the expert slot in every state: decide is the first row whose condition holds, with
        the expert slot counted in rows 4-8 only; an exhausted expert slot is never escalated."""
        for a, b, x, finding in itertools.product(SLOT_STATES, SLOT_STATES, SLOT_STATES[:-1], ("none", "open")):
            slots = {}
            for sid, s in (("S1", a), ("S2", b)):
                slots[sid] = slot("exhausted", resolved=True) if s == "exhausted-resolved" else slot(s)
            slots["S3"] = slot(x, kind="expert")
            s = snap(slots=slots, findings={"1/S1/F1": "open"} if finding == "open" else {})
            act = R.decide(s)
            self.assertEqual(act["row"], first_row(s), (a, b, x, finding))
            if x == "exhausted":
                self.assertNotIn("slot:1/S3", act.get("items") or [])
            if act["action"] in ("dispose", "close", "arbitrate"):
                self.assertIn(x, ("accepted", "exhausted"))


if __name__ == "__main__":
    unittest.main()
