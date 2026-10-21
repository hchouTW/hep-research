"""State table of the independent review (contracts/review.py; spec sections 6.2-6.7; acceptance criteria 3 and 4):
one table test per decide row (1-14), the effect of every arbitration conclusion, and the exhaustive test over slot,
arbitration-item and finding states."""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import review as R  # noqa: E402

T = "2026-01-01T00:00:00Z"
DL = "2026-01-01T01:00:00Z"


def snap(**kw):
    base = {"log_ok": True, "terminal": None, "escalation": None, "repair": [], "slots": {}, "items": {}, "needed": [],
            "findings": {}, "double_verdicts": [], "doc_differs": False, "round": 1, "round_limit": 3,
            "accept_round_limit": False}
    base.update(kw)
    return base


def slot(state, kind="review", resolved=False, deadline=DL):
    return {"state": state, "kind": kind, "resolved": resolved, "attempt": 1, "deadline": deadline}


ACCEPTED = {"S1": slot("accepted"), "S2": slot("accepted")}


class DecideRowTests(unittest.TestCase):
    """One case per row of the decision table (spec 6.5)."""

    def row(self, s):
        return R.decide(s)

    def test_row_1_broken_log(self):
        a = self.row(snap(log_ok=False, slots={"S1": slot("submitted")}))
        self.assertEqual((a["row"], a["action"]), (1, "stop"))
        self.assertIn("error", a["reason"])

    def test_row_2_terminal(self):
        self.assertEqual(self.row(snap(terminal="closed"))["action"], "stop")
        self.assertEqual(self.row(snap(terminal="superseded"))["row"], 2)

    def test_row_2_escalated_report_then_wait(self):
        a = self.row(snap(escalation={"pending": ["finding:1/S1/F1"], "reported": False}, slots={"S1": slot("submitted")}))
        self.assertEqual((a["row"], a["action"]), (2, "report"))
        a = self.row(snap(escalation={"pending": ["finding:1/S1/F1"], "reported": True}))
        self.assertEqual((a["row"], a["action"]), (2, "stop"))
        self.assertIn("finding:1/S1/F1", a["reason"])

    def test_row_3_repair(self):
        a = self.row(snap(repair=["isolation_precondition"], slots={"S1": slot("submitted")}))
        self.assertEqual((a["row"], a["action"], a["codes"]), (3, "repair", ["isolation_precondition"]))

    def test_row_4_receive(self):
        a = self.row(snap(slots={"S2": slot("submitted"), "S1": slot("returned-empty")}))
        self.assertEqual((a["row"], a["action"], a["slots"]), (4, "receive", ["S2"]))

    def test_row_5_returned_empty(self):
        a = self.row(snap(slots={"S1": slot("returned-empty"), "S2": slot("overdue")}))
        self.assertEqual((a["row"], a["action"], a["reason"]), (5, "withdraw", "host-failure"))

    def test_row_6_overdue(self):
        a = self.row(snap(slots={"S1": slot("overdue"), "S2": slot("none")}))
        self.assertEqual((a["row"], a["action"], a["reason"]), (6, "withdraw", "timeout"))

    def test_row_7_dispatch_all_at_once(self):
        a = self.row(snap(slots={"S10": slot("none"), "S2": slot("rejected"), "S3": slot("withdrawn"), "S4": slot("dispatched")}))
        self.assertEqual((a["row"], a["action"], a["slots"]), (7, "dispatch", ["S2", "S3", "S10"]))

    def test_row_8_await_earliest_deadline(self):
        a = self.row(snap(slots={"S1": slot("dispatched", deadline="2026-01-01T03:00:00Z"),
                                 "S2": slot("dispatched", deadline="2026-01-01T02:00:00Z"), "S3": slot("accepted")}))
        self.assertEqual((a["row"], a["action"], a["deadline"]), (8, "await", "2026-01-01T02:00:00Z"))

    def test_row_9_exhausted_review_slot(self):
        a = self.row(snap(slots={"S1": slot("exhausted"), "S2": slot("accepted")}))
        self.assertEqual((a["row"], a["action"], a["items"]), (9, "escalate", ["slot:1/S1"]))
        a = self.row(snap(slots={"S1": slot("exhausted", resolved=True), "S2": slot("accepted")}))
        self.assertEqual(a["row"], 14)

    def test_row_9_does_not_cover_arbiters(self):
        a = self.row(snap(slots=dict(ACCEPTED, S9=slot("exhausted", kind="arbiter")), items={"A1.1": "unresolved"}))
        self.assertEqual((a["row"], a["action"]), (11, "escalate"))

    def test_row_10_arbitrate(self):
        need = [{"type": "decline", "first": None, "second": None, "finding": "1/S1/F1"}]
        a = self.row(snap(slots=ACCEPTED, needed=need, findings={"1/S1/F1": "declined-pending"}))
        self.assertEqual((a["row"], a["action"], a["items"]), (10, "arbitrate", need))

    def test_row_11_unresolved(self):
        self.assertEqual(self.row(snap(slots=ACCEPTED, items={"A1.1": "unresolved"}))["row"], 11)
        a = self.row(snap(slots=ACCEPTED, findings={"1/S1/F1": "unresolved", "1/S1/F2": "open"}))
        self.assertEqual((a["row"], a["items"]), (11, ["finding:1/S1/F1"]))
        self.assertEqual(self.row(snap(slots=ACCEPTED, double_verdicts=["1/S1/C1"]))["items"], ["verdict:1/S1/C1"])

    def test_row_12_dispose(self):
        a = self.row(snap(slots=ACCEPTED, findings={"1/S1/F1": "open", "1/S2/F1": "reopened", "1/S2/F2": "closed"}))
        self.assertEqual((a["row"], a["action"], a["findings"]), (12, "dispose", ["1/S1/F1", "1/S2/F1"]))

    def test_row_13_rereview_or_escalate_at_limit(self):
        a = self.row(snap(slots=ACCEPTED, doc_differs=True, findings={"1/S1/F1": "changed"}))
        self.assertEqual((a["row"], a["action"]), (13, "rereview"))
        a = self.row(snap(slots=ACCEPTED, doc_differs=True, round=3))
        self.assertEqual((a["row"], a["action"], a["items"]), (13, "escalate", ["round-limit"]))
        self.assertEqual(self.row(snap(slots=ACCEPTED, doc_differs=True, round=3, accept_round_limit=True))["row"], 14)

    def test_row_14_close(self):
        a = self.row(snap(slots=ACCEPTED, findings={"1/S1/F1": "closed", "1/S1/F2": "change-confirmed"}))
        self.assertEqual((a["row"], a["action"]), (14, "close"))


# --- arbitration conclusions through fold (spec 6.7) -----------------------------------------------------------------

def ev(event, seq=0, **data):
    return {"seq": seq, "event": event, "time": T, "data": data}


def base_events(sev="high", second_verdict="unsupported"):
    out = [ev("round_started", review_id="R", round=1, document="d.md", source_sha256="0" * 64, units_sha256="0" * 64,
              config={"models": ["m"]}, config_sha256="0" * 64, author={"identity": "a", "model": "m"},
              slots=[{"slot_id": "S1", "model": "m"}, {"slot_id": "S2", "model": "m"}], carry_forward={},
              removed_findings=[])]
    for sid, verdict, fs in (("S1", "supported", []), ("S2", second_verdict, ["F1"])):
        out.append(ev("dispatched", round=1, slot_id=sid, attempt=1, deadline=DL))
        out.append(ev("accepted", round=1, slot_id=sid, attempt=1,
                      verdicts=[{"claim_id": "C1", "units": ["U0001"], "verdict": verdict, "finding_ids": fs, "eligible": True}],
                      findings=[{"id": f, "severity": sev, "units": ["U0001"]} for f in fs]))
    out.append(ev("observed", time=T, document_sha256="0" * 64, sidecars={}, repair=[], warnings=[]))
    return out


def arb(item_type, conclusion, **extra):
    d = {"round": 1, "item_id": "A1.1", "type": item_type, "slot_id": "S9", "model": "m", "lenses": ["design"]}
    d.update(extra)
    return [ev("arbitration_needed", **d), ev("dispatched", round=1, slot_id="S9", attempt=1, deadline=DL),
            ev("accepted", round=1, slot_id="S9", attempt=1),
            ev("arbitration_resolved", round=1, item_id="A1.1", conclusion=conclusion, record_sha256="0" * 64)]


DECLINE = dict(first=None, second=None, finding="1/S2/F1")
CONFLICT = dict(first="1/S1/C1", second="1/S2/C1", finding=None)


class ArbitrationConclusionTests(unittest.TestCase):
    def test_conflict_is_needed_with_first_and_second_in_order(self):
        st = R.fold(base_events())
        self.assertEqual(R.needed_items(st), [{"type": "conflict", "first": "1/S1/C1", "second": "1/S2/C1", "finding": None}])
        self.assertEqual(R.decide(R.snapshot(st))["action"], "arbitrate")

    def test_no_conflict_for_ineligible_canary_verdicts(self):
        evs = base_events()
        evs[2]["data"]["verdicts"][0]["eligible"] = False
        self.assertEqual(R.needed_items(R.fold(evs)), [])

    def test_declined_high_finding_needs_arbitration(self):
        evs = base_events(second_verdict="partially-supported") + [
            ev("disposed", finding="1/S2/F1", disposition="declined", reason="r", verification=None, edited_units=[],
               finding_units=["U0001"], round=1, by="a")]
        st = R.fold(evs)
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "declined-pending")
        self.assertEqual([i["type"] for i in R.needed_items(st)], ["decline"])

    def _decline(self, conclusion):
        evs = base_events(second_verdict="partially-supported") + [
            ev("disposed", finding="1/S2/F1", disposition="declined", reason="r", verification=None, edited_units=[],
               finding_units=["U0001"], round=1, by="a")] + arb("decline", conclusion, **DECLINE)
        return R.fold(evs)

    def test_uphold_finding_reopens(self):
        st = self._decline("uphold-finding")
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "reopened")
        self.assertEqual(R.decide(R.snapshot(st))["action"], "dispose")

    def test_accept_decline_closes(self):
        st = self._decline("accept-decline")
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "closed")
        self.assertEqual(R.decide(R.snapshot(st))["action"], "close")

    def test_unresolved_escalates(self):
        st = self._decline("unresolved")
        self.assertEqual(R.snapshot(st)["items"], {"A1.1": "unresolved"})
        a = R.decide(R.snapshot(st))
        self.assertEqual((a["row"], a["items"]), (11, ["item:A1.1"]))

    def test_uphold_first_supersedes_second_and_closes_its_findings(self):
        st = R.fold(base_events() + arb("conflict", "uphold-first", **CONFLICT))
        self.assertTrue(st["verdicts"]["1/S2/C1"]["superseded"])
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "closed")
        self.assertEqual(st["findings"]["1/S2/F1"]["closed_by"], "superseded-by-arbitration")

    def test_uphold_second_supersedes_first_and_keeps_the_winners_findings(self):
        st = R.fold(base_events() + arb("conflict", "uphold-second", **CONFLICT))
        self.assertTrue(st["verdicts"]["1/S1/C1"]["superseded"])
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "open")  # disposed as usual
        self.assertEqual(R.decide(R.snapshot(st))["action"], "dispose")

    def test_overturned_and_winning_verdict_goes_to_a_human(self):
        st = R.fold(base_events() + arb("conflict", "uphold-first", **CONFLICT))
        st["verdicts"]["1/S1/C1"]["lost"] = 1  # it also lost another conflict item
        self.assertEqual(R.decide(R.snapshot(st))["items"], ["verdict:1/S1/C1"])

    def test_exhausted_arbiter_makes_its_item_unresolved(self):
        evs = base_events() + [ev("arbitration_needed", round=1, item_id="A1.1", type="conflict", slot_id="S9", model="m",
                                  lenses=["design"], **CONFLICT)]
        for k in (1, 2):
            evs += [ev("dispatched", round=1, slot_id="S9", attempt=k, deadline=DL),
                    ev("rejected", round=1, slot_id="S9", attempt=k, codes=["x"])]
        s = R.snapshot(R.fold(evs))
        self.assertEqual((s["slots"]["S9"]["state"], s["items"]["A1.1"]), ("exhausted", "unresolved"))
        self.assertEqual(R.decide(s)["row"], 11)

    def test_human_resolution_applies(self):
        evs = base_events() + arb("conflict", "unresolved", **CONFLICT) + [
            ev("escalated", seq=50, items=["item:A1.1"], reason="r"), ev("reported", report_sha256="0" * 64)]
        st = R.fold(evs)
        self.assertEqual(R.decide(R.snapshot(st))["action"], "stop")
        st = R.fold(evs + [ev("human_resolved", item="item:A1.1", by="h", decision="uphold-first", reason="r")])
        self.assertTrue(st["verdicts"]["1/S2/C1"]["superseded"])
        self.assertEqual(R.decide(R.snapshot(st))["action"], "close")


# --- exhaustive test (spec 6.5, acceptance criterion 4) --------------------------------------------------------------

SLOT_STATES = ("none", "dispatched", "returned-empty", "overdue", "submitted", "accepted", "rejected", "withdrawn",
               "exhausted", "exhausted-resolved")
ARBITER_LIVE = ("none", "dispatched", "returned-empty", "overdue", "submitted", "rejected", "withdrawn")
ITEM_STATES = ("absent", "needed", "resolved", "unresolved") + tuple(f"dispatched/{s}" for s in ARBITER_LIVE)
FINDING_STATES = ("none", "open", "changed", "change-confirmed", "unresolved", "declined-pending", "reopened", "closed",
                  "removed-pending")
NOT_REPORTABLE = ("open", "reopened", "declined-pending")


DECLINE_STATES = ("needed", "unresolved") + tuple(f"dispatched/{s}" for s in ARBITER_LIVE)


def world(a, b, item, finding, differs, at_limit, decline=None):
    """Two review slots, one conflict item (with its arbiter slot), one finding; a declined-pending finding also has
    its decline item in the given state (needed, dispatched with its arbiter slot, or unresolved)."""
    slots = {}
    for sid, s in (("S1", a), ("S2", b)):
        slots[sid] = slot("exhausted", resolved=True) if s == "exhausted-resolved" else slot(s)
    items, needed = {}, []
    if item == "needed":
        needed.append({"type": "conflict", "first": "1/S1/C1", "second": "1/S2/C1", "finding": None})
    elif item.startswith("dispatched/"):
        items["A1.1"] = "dispatched"
        slots["S9"] = slot(item.split("/")[1], kind="arbiter")
    elif item != "absent":
        items["A1.1"] = item
        slots["S9"] = slot("accepted", kind="arbiter")
    findings = {} if finding == "none" else {"1/S1/F1": finding}
    if decline == "needed":
        needed.append({"type": "decline", "first": None, "second": None, "finding": "1/S1/F1"})
    elif decline and decline.startswith("dispatched/"):
        items["A1.2"] = "dispatched"
        slots["S10"] = slot(decline.split("/")[1], kind="arbiter")
    elif decline:
        items["A1.2"] = decline
        slots["S10"] = slot("accepted", kind="arbiter")
    return snap(slots=slots, items=items, needed=needed, findings=findings, doc_differs=differs, round=3 if at_limit else 1)


def first_row(s):
    """The decision table written as independent predicates, in priority order."""
    sl = s["slots"]
    review = [v for v in sl.values() if v["kind"] == "review"]
    states = {v["state"] for v in sl.values()}
    preds = [
        (1, not s["log_ok"]), (2, bool(s["terminal"] or s["escalation"])), (3, bool(s["repair"])),
        (4, "submitted" in states), (5, "returned-empty" in states), (6, "overdue" in states),
        (7, bool(states & {"none", "rejected", "withdrawn"})), (8, "dispatched" in states),
        (9, any(v["state"] == "exhausted" and not v["resolved"] for v in review)),
        (10, all(v["state"] == "accepted" or v["resolved"] for v in review) and bool(s["needed"])),
        (11, "unresolved" in s["items"].values() or "unresolved" in s["findings"].values() or bool(s["double_verdicts"])),
        (12, any(x in ("open", "reopened", "removed-pending") for x in s["findings"].values())),
        (13, s["doc_differs"] and not s["accept_round_limit"]), (14, True)]
    matches = [r for r, ok in preds if ok]
    return matches[0]


class ExhaustiveTests(unittest.TestCase):
    def test_every_combination(self):
        n = 0
        combos = itertools.product(SLOT_STATES, SLOT_STATES, ITEM_STATES, FINDING_STATES, (False, True), (False, True))
        for a, b, item, finding, differs, at_limit, decline in (
                c + (d,) for c in combos for d in (DECLINE_STATES if c[3] == "declined-pending" else (None,))):
            s = world(a, b, item, finding, differs, at_limit, decline)
            act = R.decide(s)
            n += 1
            key = (a, b, item, finding, differs, at_limit, decline)
            self.assertEqual(act["row"], first_row(s), key)  # exactly one row: the first whose condition holds
            pending_item = item == "needed" or item.startswith("dispatched/") or (decline or "").startswith(("needed", "dispatched"))
            if pending_item or finding in NOT_REPORTABLE:
                self.assertNotIn(act["action"], ("report", "close"), key)
            if finding == "changed" and differs:
                self.assertNotEqual(act["action"], "close", key)
                if act["row"] >= 13:
                    self.assertEqual(act["action"], "escalate" if at_limit else "rereview", key)
        self.assertEqual(n, len(SLOT_STATES) ** 2 * len(ITEM_STATES) * (len(FINDING_STATES) - 1 + len(DECLINE_STATES)) * 4)

    def test_escalation_pauses_everything(self):
        for finding in FINDING_STATES:
            s = world("submitted", "accepted", "needed", finding, True, False)
            s["escalation"] = {"pending": ["x"], "reported": False}
            self.assertEqual(R.decide(s)["action"], "report")
            s["escalation"]["reported"] = True
            self.assertEqual(R.decide(s)["action"], "stop")

    def test_changed_findings_are_carried_forward(self):
        """Every finding changed in the previous round is in the next round's carry_forward, or, when all its units
        were removed, in the dispose list of A4.3."""
        roles = {"S1": {"role": "lens", "lens": "facts"}, "S2": {"role": "shadow", "lens": "facts"},
                 "S3": {"role": "lens", "lens": "design"}}
        mapping_keep = {"unchanged": [["U0001", "U0001"]], "changed": [["U0002", "U0002"]], "added": [], "removed": []}
        mapping_drop = {"unchanged": [["U0001", "U0001"]], "changed": [], "added": [], "removed": ["U0002"]}
        for states in itertools.product(FINDING_STATES[1:], repeat=3):
            for mapping in (mapping_keep, mapping_drop):
                st = {"round": 1, "verdicts": {}, "findings": {}}
                for sid, state in zip(("S1", "S2", "S3"), states):
                    st["findings"][f"1/{sid}/F1"] = {"slot": sid, "round": 1, "units": ["U0002"], "state": state}
                plan, removed = R.carry_forward_plan(st, mapping, roles, {"facts": "S5", "design": "S6"})
                carried = {c["target"] for items in plan.values() for c in items if c["kind"] == "finding"}
                for g, f in st["findings"].items():
                    if f["state"] == "changed":
                        self.assertIn(g, carried | set(removed), (states, mapping is mapping_keep))
                        if mapping is mapping_keep:
                            self.assertIn(g, carried)
                    else:
                        self.assertNotIn(g, carried | set(removed))
                for g in carried:  # a shadow's finding goes to its main lens's new slot
                    lens = roles[g.split("/")[1]]["lens"]
                    self.assertIn(g, {c["target"] for c in plan[{"facts": "S5", "design": "S6"}[lens]]})

    def test_rereview_round_with_changed_finding_does_not_close(self):
        st = R.fold(base_events(second_verdict="partially-supported") + [
            ev("disposed", finding="1/S2/F1", disposition="changed", reason="r", verification={"verified": "x"},
               edited_units=["U0001"], finding_units=["U0001"], round=1, by="a"),
            ev("observed", time=T, document_sha256="1" * 64, sidecars={}, repair=[], warnings=[])])
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "changed")
        self.assertEqual(R.decide(R.snapshot(st))["action"], "rereview")


if __name__ == "__main__":
    unittest.main()
