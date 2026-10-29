"""hep-review capability claims: binding, fingerprint and lifecycle (spec v9 section 15.6, T08).

A claim binds what was measured (scope, suite, trial plan, results, limitations) to a fingerprint of what the
capability depended on when it was measured. It moves up only with new gate evidence of the right kind, falls to
needs-reassessment when its fingerprint changes or a new failure type appears, and comes back only with new evidence
and a new fingerprint. The registry check replays every claim's history through the same state machine."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))

from hep_review_support import coordinator as K  # noqa: E402
from hep_review_support import evaluation as E  # noqa: E402

SCOPE = {"domain": "statistics", "method": "assumption-check+recompute", "format": "text+json", "host":
         "claude-code-cli-macos", "tier": "R2", "material": "single page, up to 3 planted defects"}
BINDING = {"policy": "frozen-protocol g2x", "rubric": "grader-instructions g2x", "gold": "commitments a1201a0a",
           "suite": "g2x", "case_distribution": {"C01": 8, "C02": 4, "C03": 2, "C04": 2},
           "trial_plan": "3 per instance, 48"}


def gate(report: str, kind: str = "pilot", **changes) -> dict:
    return {"engineering_gate": True, "graders_calibrated": True, "report": report, "kind": kind} | changes


def parts(**changes):
    p = E.fingerprint_parts(model_alias="opus", model_pinned=False, date="2026-10-29")
    p.update(changes)
    return p


def claim(state="experimental"):
    c = E.make_claim("hep-review/statistics-narrow", SCOPE, BINDING, results={"defect_detection": "37/39"},
                     limitations=["same model family wrote the brief"], parts=parts(), measured_at="9c499a24")
    if state == "experimental":
        return c
    c = E.transition(c, "pilot-checked-scope", evidence=gate("g2x-report.md"), at="2026-10-29")
    if state == "evaluated-scope":
        c = E.transition(c, "evaluated-scope", evidence=gate("g3-report.md", "held-out-evaluation"), at="2026-10-29")
    return c


class Fingerprint(unittest.TestCase):
    def test_parts_name_what_the_capability_depends_on(self):
        p = parts()
        for key in ("host_capabilities_digest", "packet_template_digest", "validator_version", "reader_digest",
                    "hash_profile", "model"):
            self.assertIn(key, p)
        self.assertEqual(p["model"], {"alias": "opus", "pinned": "unknown", "date": "2026-10-29"})

    def test_every_part_change_changes_the_fingerprint(self):
        base = E.fingerprint(parts())
        self.assertEqual(base, E.fingerprint(parts()))
        for key, value in (("host_capabilities_digest", "1" * 64), ("packet_template_digest", "0" * 64),
                           ("validator_version", "9.9.9"), ("reader_digest", "2" * 64),
                           ("hash_profile", ["other/1"]), ("model", {"alias": "x", "pinned": True, "date": "d"})):
            self.assertNotEqual(base, E.fingerprint(parts(**{key: value})), key)

    def test_host_notes_do_not_move_the_fingerprint_but_capabilities_do(self):
        host = K.load_host_profile()
        noted = copy.deepcopy(host)
        noted["note"] = "reworded"
        for cap in noted["capabilities"].values():
            cap["evidence"] = "reworded evidence"
        self.assertEqual(E.host_capabilities_digest(host), E.host_capabilities_digest(noted))
        changed = copy.deepcopy(host)
        changed["capabilities"]["parallel_dispatch"]["value"] = False
        self.assertNotEqual(E.host_capabilities_digest(host), E.host_capabilities_digest(changed))


class Lifecycle(unittest.TestCase):
    def test_a_new_claim_is_experimental_with_its_binding(self):
        c = claim()
        self.assertEqual(c["state"], "experimental")
        for key in ("scope", "binding", "results", "limitations", "fingerprint", "fingerprint_parts",
                    "initial_fingerprint_parts", "measured_at", "history"):
            self.assertIn(key, c)
        self.assertEqual(c["fingerprint"], E.fingerprint(c["fingerprint_parts"]))

    def test_upgrade_needs_complete_gate_evidence(self):
        for bad in (None, gate("r", engineering_gate=False), gate("r", graders_calibrated=False), gate(""),
                    dict(gate("r"), kind="opinion")):
            with self.assertRaises(E.ClaimError, msg=str(bad)):
                E.transition(claim(), "pilot-checked-scope", evidence=bad, at="2026-10-29")
        c = E.transition(claim(), "pilot-checked-scope", evidence=gate("r"), at="2026-10-29")
        self.assertEqual((c["state"], c["history"][-1]["to"]), ("pilot-checked-scope", "pilot-checked-scope"))

    def test_evaluated_scope_needs_a_held_out_evaluation(self):
        with self.assertRaises(E.ClaimError):
            E.transition(claim("pilot-checked-scope"), "evaluated-scope", evidence=gate("g3"), at="2026-10-29")
        with self.assertRaises(E.ClaimError):  # a pilot cannot skip to evaluated-scope
            E.transition(claim(), "evaluated-scope", evidence=gate("g3"), at="2026-10-29")
        direct = E.transition(claim(), "evaluated-scope", evidence=gate("g3", "held-out-evaluation"), at="2026-10-29")
        self.assertEqual(direct["state"], "evaluated-scope")

    def test_the_same_evidence_cannot_be_used_twice(self):
        c = claim("pilot-checked-scope")
        with self.assertRaises(E.ClaimError):
            E.transition(c, "evaluated-scope", evidence=gate("g2x-report.md", "held-out-evaluation"), at="2026-10-29")

    def test_reassessment_paths(self):
        with self.assertRaises(E.ClaimError):  # nothing to reassess before anything was claimed
            E.transition(claim(), "needs-reassessment", reason="new-failure-type", at="2026-10-30")
        with self.assertRaises(E.ClaimError):
            E.transition(claim("pilot-checked-scope"), "needs-reassessment", at="2026-10-30")
        down = E.transition(claim("pilot-checked-scope"), "needs-reassessment", reason="new-failure-type",
                            at="2026-10-30")
        with self.assertRaises(E.ClaimError):  # cannot climb above where it was
            E.transition(down, "evaluated-scope", evidence=gate("new", "held-out-evaluation"), at="2026-10-31")
        with self.assertRaises(E.ClaimError):  # needs new evidence
            E.transition(down, "pilot-checked-scope", evidence=gate("g2x-report.md"), at="2026-10-31")
        back = E.transition(down, "pilot-checked-scope", evidence=gate("rerun-report.md"), at="2026-10-31")
        self.assertEqual(back["state"], "pilot-checked-scope")

    def test_a_changed_fingerprint_forces_reassessment_and_refingerprinting(self):
        c = claim("pilot-checked-scope")
        self.assertEqual(E.reassess_if_changed(c, parts(), at="2026-10-30")["state"], "pilot-checked-scope")
        moved = E.reassess_if_changed(c, parts(packet_template_digest="0" * 64), at="2026-10-30")
        self.assertEqual((moved["state"], moved["history"][-1]["reason"]), ("needs-reassessment",
                                                                            "fingerprint-changed"))
        with self.assertRaises(E.ClaimError):  # coming back needs the new fingerprint
            E.transition(moved, "pilot-checked-scope", evidence=gate("rerun"), at="2026-10-31")
        new_parts = parts(packet_template_digest="0" * 64)
        back = E.transition(moved, "pilot-checked-scope", evidence=gate("rerun"), parts=new_parts, at="2026-10-31")
        self.assertEqual(back["fingerprint"], E.fingerprint(new_parts))

    def test_no_way_back_from_retired_and_no_mutation(self):
        c = claim("pilot-checked-scope")
        before = copy.deepcopy(c)
        retired = E.transition(c, "retired", reason="superseded", at="2026-10-30")
        self.assertEqual(c, before)
        with self.assertRaises(E.ClaimError):
            E.transition(retired, "pilot-checked-scope", evidence=gate("x"), at="2026-10-31")


class Registry(unittest.TestCase):
    def check(self, *claims, current=False):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "claims.json"
            path.write_text(json.dumps({"claims": list(claims)}))
            return E.check_registry(path, current=current)

    def test_a_valid_registry_has_no_problems(self):
        self.assertEqual(self.check(claim("pilot-checked-scope"), claim("evaluated-scope")), [])

    def test_forgeries_are_flagged(self):
        skipped = claim()
        skipped["state"] = "evaluated-scope"
        skipped["history"] = [{"from": "experimental", "to": "evaluated-scope", "at": "x", "evidence": gate("r")}]
        false_gate = claim("pilot-checked-scope")
        false_gate["history"][0]["evidence"]["engineering_gate"] = False
        refingerprinted = claim("pilot-checked-scope")
        refingerprinted["fingerprint_parts"] = parts(validator_version="9.9.9")
        refingerprinted["fingerprint"] = E.fingerprint(refingerprinted["fingerprint_parts"])
        no_model = claim("pilot-checked-scope")
        del no_model["fingerprint_parts"]["model"]
        for cid, c in (("skipped", skipped), ("false-gate", false_gate), ("refingerprinted", refingerprinted),
                       ("no-model", no_model)):
            c["id"] = cid
        problems = self.check(skipped, false_gate, refingerprinted, no_model, current=True)
        for cid in ("skipped", "false-gate", "refingerprinted", "no-model"):
            self.assertTrue([x for x in problems if x.startswith(cid + ":")], (cid, problems))

    def test_a_stale_live_claim_is_flagged_when_current(self):
        stale = E.make_claim("old", SCOPE, BINDING, results={}, limitations=[], measured_at="x",
                             parts=parts(packet_template_digest="0" * 64))
        stale = E.transition(stale, "pilot-checked-scope", evidence=gate("r"), at="x")
        self.assertTrue(self.check(stale, current=True))
        self.assertFalse(self.check(E.reassess_if_changed(stale, parts(), at="y"), current=True))

    def test_shipped_registry_is_valid_and_current(self):
        problems = E.check_registry(ROOT / "skills" / "hep-review" / "assets" / "claims.json", current=True)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
