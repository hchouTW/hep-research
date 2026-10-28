"""Decision-table generator for hep-review spec v9 section 19.1 (task file T01 step 6).

For every row three things are compared:
1. TABLE: the hand-written row of the specification (defects, disputed, open, met, summary);
2. RULES: a small rule model of section 7.4/7.5 (extended from the task file's Appendix A) evaluated on a row
   descriptor, so the table is recomputed from the rules and not only copied;
3. KERNEL: the real projection: a fixture bundle -> validate -> project -> decide_summary.
Any disagreement fails. When the rules and the table disagree the rules prevail (spec 19.1) and the table is to be
corrected; no such disagreement exists for v9."""
from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from hep_review_fixtures import Case, obligation  # noqa: E402

GOOD_ATT = {"report_mode": "current", "validator_is_latest_approved": True, "head_continuity": "verified",
            "r3_state_matches": None}

# ------------------------------------------------------------------------------------------------------------------
# The rule model (task file Appendix A, extended with integrity, tier and continuity)
# ------------------------------------------------------------------------------------------------------------------


@dataclass
class ObligationRow:
    required: bool = True
    decision: bool = False
    outcome: str = "supported"
    cur_supported: int = 0
    stale_supported: int = 0
    candidate: int = 0
    disputed: int = 0
    tier: int = 2


@dataclass
class Row:
    obs: list = field(default_factory=lambda: [ObligationRow()])
    planning_gap: bool = False
    version_inconsistency: bool = False
    dep_gap: bool = False
    unjudged_conflict: bool = False
    stale_negative_followup: bool = False
    integrity: str = "valid"
    continuity: str = "verified"


def rule_flags(c: Row) -> dict:
    defects = any(o.cur_supported for o in c.obs)
    disputed = any(o.disputed for o in c.obs)
    open_ = (any(o.candidate or o.disputed or o.stale_supported for o in c.obs)
             or c.stale_negative_followup or c.planning_gap or c.version_inconsistency
             or c.unjudged_conflict or c.dep_gap
             or any(o.required and o.outcome in ("not-examined", "undetermined") for o in c.obs))
    met = (not c.planning_gap
           and all(o.outcome != "not-examined" for o in c.obs if o.required)
           and all(not (o.decision and o.outcome in ("undetermined", "not-examined")) for o in c.obs if o.required))
    tier = min(o.tier for o in c.obs if o.required)
    eligible = (tier >= 1 and c.integrity == "valid" and met and not defects and not disputed and not open_)
    return dict(defects=defects, disputed=disputed, open=open_, met=met,
                summary=eligible and c.continuity == "verified")


# ------------------------------------------------------------------------------------------------------------------
# Rows: (TABLE values, rule descriptor, fixture builder, attestation override)
# ------------------------------------------------------------------------------------------------------------------

def b_d1():
    c = Case()
    c.plan([obligation("O1"), obligation("O2")])
    c.review("O1", "violated", finding=True)
    return c


def _conflict(decision):
    c = Case()
    c.plan([obligation("O1", decision_required=decision)])
    r = c.review("O1", "violated", finding=True)
    fid = r["findings"][0]["id"]
    c.review("O1", "supported", judgments=[{"id": "J-x", "kind": "finding_assessment", "finding_id": fid,
                                           "verdict": "refuted", "basis": "declared", "depends_on": []}])
    return c


def b_d4():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "violated", finding=True)
    return c


def b_d5():
    c = Case()
    c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
    c.review("O1", "supported")
    c.review("O2", "violated", finding=True)
    return c


def b_d6():
    c = Case()
    c.plan([obligation("O1"), obligation("O2")])
    c.review("O1", "supported")
    c.review("O2", "not-applicable", discharge={"reason_category": "condition-absent", "basis": "observed",
                                               "reason": "no correlated inputs exist"})
    return c


def b_d7():
    c = Case(requirements=("REQ-1", "REQ-2"))
    c.plan([obligation("O1")])
    c.review("O1", "supported")
    return c


def b_d8():
    c = Case()
    c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
    c.review("O1", "supported")
    return c


def b_d10():
    c = Case(mode="R0")
    c.plan([obligation("O1")])
    c.review("O1", "supported")
    return c


def b_d11():
    c = Case()
    c.plan([obligation("O1")])
    r = c.review("O1", "supported")
    c.blob_checks[r["evidence"][0]["content_ref"]["digest"]] = "changed"
    return c


def _carry(variant):
    c = Case()
    o = obligation("O1", targets=("M1", "M2"))
    c.plan([o], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
    c.review("O1", "supported", cited=("M1",), tools=[] if variant == "tools-empty" else ("python3",))
    if variant == "uncited-target":
        c.new_manifest(M2="M2-v2")
        c.plan([o], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
    elif variant == "adoption-tightened":
        o2 = dict(o, adoption_policy={"second_method_required": False, "verification_required": True,
                                      "qualifications": []})
        c.plan([o2], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
    elif variant == "no-env-observation":
        c.plan([o], env=[])
    elif variant == "other-executor":
        c.plan([o], env=[{"executor": "exec-2", "tools": ["python3"], "environment_refs": []}])
    elif variant == "identical":
        c.plan([o], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
    elif variant == "tools-empty":
        c.plan([o], env=[])
    elif variant == "regroup":
        c.plan([o], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}],
               assignment_specs=[{"id": "spec-9", "obligation_ids": ["O1"], "role": "reviewer", "deadline": "P7D"}])
    return c


def b_d14():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported", omit_tools=True)
    return c


def b_d16():
    c = Case()
    o = obligation("O1")
    c.plan([o])
    c.review("O1", "violated", finding=True)
    c.new_manifest(M1="M1-v2")
    c.plan([o])
    return c


def b_d17():
    c = Case()
    c.plan([obligation("O1")])
    r1 = c.review("O1", "supported")
    c.review("O1", "supported", suspected_conflicts=[{"id": "S1", "between": [r1["answers"][0]["id"]],
                                                      "note": "the reasoning texts look opposed"}])
    return c


def b_d18():
    c = Case()
    c.plan([obligation("O1"), obligation("O2", required=False, decision_required=False)])
    c.review("O1", "supported")
    c.review("O2", "undetermined")
    return c


def b_d19():
    c = Case()
    c.plan([obligation("O1")], independence=[])
    c.review("O1", "supported")
    return c


def b_d20():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported", actor="author-a")
    return c


def b_plain():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported")
    return c


def b_d24():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported")
    return c


def b_d25():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "violated", finding=True)
    c.plan([obligation("O1a"), obligation("O1b")], obligation_map=[])
    return c


def b_d26():
    c = Case()
    c.plan([obligation("O1")])
    cond = {"non-author": {"satisfied": True, "basis": "declared"},
            "fresh-context": {"satisfied": True, "basis": "self-reported"},
            "no-other-evaluations-seen": {"satisfied": True, "basis": "advisory"}}
    c.review("O1", "supported", conditions=cond)
    return c


def b_d28():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported", fidelity="mismatch")
    return c


def b_d29():
    c = Case()
    c.plan([obligation("O1")])
    c.review("O1", "supported")
    c.plan([obligation("O1a"), obligation("O1b")],
           obligation_map=[{"old_id": "O1", "new_ids": ["O1a", "O1b"], "retired_reason": None}])
    c.review("O1a", "supported")
    c.review("O1b", "supported")
    return c


def b_d30():
    c = Case()
    o = obligation("O1")
    c.plan([o])
    c.review("O1", "supported")
    c.plan([o], required_restrictions=[], env=[{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}])
    return c


def rule_plan_declares_restrictions(committed: dict) -> list:
    """A stricter rule a later validator could add (test only): every plan states its required_restrictions."""
    if committed.get("record_kind") == "plan" and "required_restrictions" not in committed:
        return [{"code": "plan.required_restrictions_missing", "path": "$", "message": "missing"}]
    return []


STRICT_RULES = dict(H.VALIDATOR_RULES)
STRICT_RULES["0.2.0-test"] = H.VALIDATOR_RULES[H.LATEST_VALIDATOR] + (rule_plan_declares_restrictions,)

ROWS = {
    #       defects disputed open  met   summary   rule descriptor                                       builder
    "D1": ((True, False, True, False, False), Row([ObligationRow(outcome="violated", cur_supported=1), ObligationRow(outcome="not-examined")]), b_d1),
    "D2": ((False, True, True, True, False), Row([ObligationRow(outcome="undetermined", disputed=1)]), lambda: _conflict(False)),
    "D3": ((False, True, True, False, False), Row([ObligationRow(outcome="undetermined", disputed=1, decision=True)]), lambda: _conflict(True)),
    "D4": ((True, False, False, True, False), Row([ObligationRow(outcome="violated", cur_supported=1)]), b_d4),
    "D5": ((True, False, False, True, False), Row([ObligationRow(), ObligationRow(required=False, outcome="violated", cur_supported=1)]), b_d5),
    "D6": ((False, False, False, True, True), Row([ObligationRow(), ObligationRow(outcome="not-applicable")]), b_d6),
    "D7": ((False, False, True, False, False), Row([ObligationRow()], planning_gap=True), b_d7),
    "D8": ((False, False, False, True, True), Row([ObligationRow(), ObligationRow(required=False, outcome="not-examined")]), b_d8),
    "D10": ((False, False, False, True, False), Row([ObligationRow(tier=0)], integrity="not-checked"), b_d10),
    "D11": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")], dep_gap=True, integrity="partial-invalid"), b_d11),
    "D12a": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")]), lambda: _carry("uncited-target")),
    "D12b": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")]), lambda: _carry("adoption-tightened")),
    "D12c": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")]), lambda: _carry("no-env-observation")),
    "D12d": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")]), lambda: _carry("other-executor")),
    "D13": ((False, False, False, True, True), Row([ObligationRow()]), lambda: _carry("identical")),
    "D14": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")]), b_d14),
    "D15": ((False, False, False, True, True), Row([ObligationRow()]), lambda: _carry("tools-empty")),
    "D16": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined", stale_supported=1)], stale_negative_followup=True), b_d16),
    "D17": ((False, False, True, True, False), Row([ObligationRow()], unjudged_conflict=True), b_d17),
    "D18": ((False, False, False, True, True), Row([ObligationRow(), ObligationRow(required=False, outcome="undetermined")]), b_d18),
    "D19": ((False, False, False, True, True), Row([ObligationRow(tier=1)]), b_d19),
    "D20": ((False, False, False, True, True), Row([ObligationRow(tier=1)]), b_d20),
    "D21": ((False, False, False, True, False), Row([ObligationRow()], continuity="unverified"), b_plain),
    "D24": ((False, False, True, True, False), Row([ObligationRow()], version_inconsistency=True), b_d24),
    "D25": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined"), ObligationRow(outcome="not-examined")], planning_gap=True, stale_negative_followup=True), b_d25),
    "D26": ((False, False, False, True, True), Row([ObligationRow(tier=1)]), b_d26),
    "D27": ((False, False, False, True, True), Row([ObligationRow()]), lambda: _carry("regroup")),
    "D28": ((False, False, True, False, False), Row([ObligationRow(outcome="not-examined")], integrity="partial-invalid"), b_d28),
    "D29": ((False, False, True, False, False), Row([ObligationRow(), ObligationRow()], planning_gap=True), b_d29),
    "D30": ((False, False, False, True, True), Row([ObligationRow()]), b_d30),
}
ATTESTATION = {"D21": {"head_continuity": "unverified"}}
VERSION = {"D24": "0.2.0-test", "D30": "0.2.0-test"}


def kernel(row: str):
    b = ROWS[row][2]().bundle()
    version = VERSION.get(row, H.LATEST_VALIDATOR)
    rules = STRICT_RULES if row in VERSION else None
    v = H.validate(b, version, rules=rules)
    p = H.project(v, version, rules=rules)
    att = dict(GOOD_ATT, **ATTESTATION.get(row, {}))
    s = H.decide_summary(p, att)
    f = p["flags"]
    return p, s, (f["has_supported_defects"], f["has_disputed_findings"], f["has_open_questions"],
                  f["plan_requirements_met"], s["output_summary"])


class DecisionTable(unittest.TestCase):
    def test_rules_reproduce_the_table(self):
        for row, (table, desc, _) in ROWS.items():
            with self.subTest(row):
                r = rule_flags(desc)
                self.assertEqual((r["defects"], r["disputed"], r["open"], r["met"], r["summary"]), table)

    def test_kernel_reproduces_the_table(self):
        for row, (table, _, _) in ROWS.items():
            with self.subTest(row):
                self.assertEqual(kernel(row)[2], table)

    def test_d9_plan_without_explicit_decision_required_is_rejected(self):
        errs = H.check_plan(obligation_plan([obligation("O1", decision_required=None)]), parent=None,
                            intent=Case().intent)
        self.assertIn("plan.decision_required_missing", {e["code"] for e in errs})

    def test_d22_broken_continuity_never_outputs_and_integrity_is_not_valid(self):
        p, _, _ = kernel("D4")
        s = H.decide_summary(H.project(H.validate(b_plain().bundle(), H.LATEST_VALIDATOR), H.LATEST_VALIDATOR),
                             dict(GOOD_ATT, head_continuity="broken"))
        self.assertFalse(s["output_summary"])
        self.assertEqual(s["record_integrity"], "invalid-continuity-broken")

    def test_d23_historical_check_outputs_only_match_or_mismatch(self):
        b = b_plain().bundle()
        old = H.encode(H.project(H.validate(b, H.LATEST_VALIDATOR), H.LATEST_VALIDATOR))
        self.assertEqual(H.check_historical(old, b, H.LATEST_VALIDATOR), "match")
        self.assertEqual(H.check_historical(old.replace(b'"supported"', b'"violated"', 1), b, H.LATEST_VALIDATOR),
                         "mismatch")

    def test_row_details(self):
        p, s, _ = kernel("D6")
        self.assertEqual(p["coverage"]["discharged"], 1)
        self.assertEqual(p["coverage"]["total_required"], 2)
        self.assertEqual(p["coverage"]["methods_not_run_by_discharge"], ["O2:recompute"])
        p, s, _ = kernel("D8")
        self.assertEqual(p["uncovered_optional"], {"not_examined": ["O2"], "undetermined": []})
        p, s, _ = kernel("D18")
        self.assertEqual(p["uncovered_optional"], {"not_examined": [], "undetermined": ["O2"]})
        p, s, _ = kernel("D10")
        self.assertEqual(p["record_integrity"], "not-checked")
        self.assertEqual(p["achieved_tier"], "R0")
        for row in ("D13", "D27"):
            p, s, _ = kernel(row)
            self.assertEqual([c["obligation_id"] for c in p["carried_over"]], ["O1"], row)
        p, s, _ = kernel("D16")
        self.assertEqual(len(p["unverified_historical_defects"]), 1)
        p, s, _ = kernel("D25")
        self.assertIn("O1", [g["obligation_id"] for g in p["planning_gaps"] if g["kind"] == "unmapped_old_obligation"])
        self.assertEqual(len(p["unverified_historical_defects"]), 1)
        p, s, _ = kernel("D29")
        self.assertIn("split_without_scope_judgment", {g["kind"] for g in p["planning_gaps"]})
        for row in ("D19", "D20", "D26"):
            p, s, _ = kernel(row)
            self.assertEqual(p["achieved_tier"], "R1", row)
            self.assertIn("R1 (non-independent", s["summary_text"], row)
        p, s, _ = kernel("D19")
        self.assertTrue(p["independence_floor_not_met"])
        p, s, _ = kernel("D26")
        self.assertIn("target R2", " ".join(s["disclosure"]))
        p, s, _ = kernel("D28")
        self.assertEqual(p["record_integrity"], "partial-invalid")
        p, s, _ = kernel("D21")
        self.assertTrue(p["summary_eligible"])
        p, s, _ = kernel("D24")
        self.assertEqual(len(p["version_inconsistencies"]), 1)
        p, s, _ = kernel("D30")
        self.assertEqual(p["version_inconsistencies"], [])


def obligation_plan(obligations):
    c = Case()
    return c.plan(obligations)


if __name__ == "__main__":
    unittest.main()
