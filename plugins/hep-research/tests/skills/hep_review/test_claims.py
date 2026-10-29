"""hep-review capability claims: binding, fingerprint and lifecycle (spec v9 section 15.6, T08).

A claim binds what was measured (scope, suite, trial plan, results, limitations) to a fingerprint of what the
capability depends on; it moves up only with gate evidence and falls to needs-reassessment when the fingerprint
changes or a new failure type appears."""
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

from hep_review_support import evaluation as E  # noqa: E402

SCOPE = {"domain": "statistics", "method": "assumption-check+recompute", "format": "text+json", "host":
         "claude-code-cli-macos", "tier": "R2", "material": "single page, up to 3 planted defects"}
BINDING = {"policy": "frozen-protocol g2x", "rubric": "grader-instructions g2x", "gold": "commitments a1201a0a",
           "suite": "g2x", "case_distribution": {"C01": 8, "C02": 4, "C03": 2, "C04": 2},
           "trial_plan": "3 per instance, 48"}
GATE_PASS = {"engineering_gate": True, "graders_calibrated": True, "report": "docs/dev/hep-review/g2x-report.md"}


def parts(**changes):
    p = E.fingerprint_parts(model_alias="opus", model_pinned=False, date="2026-10-29")
    p.update(changes)
    return p


def claim(state="experimental"):
    c = E.make_claim("hep-review/statistics-narrow", SCOPE, BINDING, results={"defect_detection": "37/39"},
                     limitations=["same model family wrote the brief"], parts=parts())
    return c if state == "experimental" else E.transition(c, state, evidence=GATE_PASS, at="2026-10-29")


class Fingerprint(unittest.TestCase):
    def test_parts_name_what_the_capability_depends_on(self):
        p = parts()
        for key in ("host_profile_digest", "packet_template_digest", "validator_version", "reader_profile",
                    "hash_profile", "model"):
            self.assertIn(key, p)
        self.assertEqual(p["model"], {"alias": "opus", "pinned": "unknown", "date": "2026-10-29"})

    def test_any_part_change_changes_the_fingerprint(self):
        base = E.fingerprint(parts())
        self.assertEqual(base, E.fingerprint(parts()))
        for key, value in (("packet_template_digest", "0" * 64), ("validator_version", "9.9.9"),
                           ("host_profile_digest", "1" * 64)):
            self.assertNotEqual(base, E.fingerprint(parts(**{key: value})), key)


class Lifecycle(unittest.TestCase):
    def test_a_new_claim_is_experimental_with_its_binding(self):
        c = claim()
        self.assertEqual(c["state"], "experimental")
        for key in ("scope", "binding", "results", "limitations", "fingerprint", "fingerprint_parts", "history"):
            self.assertIn(key, c)
        self.assertEqual(c["fingerprint"], E.fingerprint(c["fingerprint_parts"]))

    def test_upgrade_needs_gate_evidence(self):
        with self.assertRaises(E.ClaimError):
            E.transition(claim(), "pilot-checked-scope", evidence=None, at="2026-10-29")
        with self.assertRaises(E.ClaimError):
            E.transition(claim(), "pilot-checked-scope", evidence=dict(GATE_PASS, engineering_gate=False),
                         at="2026-10-29")
        c = E.transition(claim(), "pilot-checked-scope", evidence=GATE_PASS, at="2026-10-29")
        self.assertEqual(c["state"], "pilot-checked-scope")
        self.assertEqual(c["history"][-1]["to"], "pilot-checked-scope")

    def test_no_skipping_and_no_way_back_from_retired(self):
        with self.assertRaises(E.ClaimError):
            E.transition(claim(), "evaluated-scope", evidence=GATE_PASS, at="2026-10-29")
        retired = E.transition(claim("pilot-checked-scope"), "retired", reason="superseded", at="2026-10-30")
        with self.assertRaises(E.ClaimError):
            E.transition(retired, "pilot-checked-scope", evidence=GATE_PASS, at="2026-10-31")

    def test_reassessment_needs_a_stated_reason(self):
        with self.assertRaises(E.ClaimError):
            E.transition(claim("pilot-checked-scope"), "needs-reassessment", at="2026-10-30")
        c = E.transition(claim("pilot-checked-scope"), "needs-reassessment", reason="new-failure-type",
                         at="2026-10-30")
        self.assertEqual(c["state"], "needs-reassessment")

    def test_a_changed_fingerprint_forces_reassessment(self):
        c = claim("pilot-checked-scope")
        same = E.reassess_if_changed(c, parts(), at="2026-10-30")
        self.assertEqual(same["state"], "pilot-checked-scope")
        moved = E.reassess_if_changed(c, parts(packet_template_digest="0" * 64), at="2026-10-30")
        self.assertEqual(moved["state"], "needs-reassessment")
        self.assertEqual(moved["history"][-1]["reason"], "fingerprint-changed")

    def test_transition_never_mutates_its_input(self):
        c = claim()
        before = copy.deepcopy(c)
        E.transition(c, "pilot-checked-scope", evidence=GATE_PASS, at="2026-10-29")
        self.assertEqual(c, before)


class Registry(unittest.TestCase):
    def test_registry_check_flags_bad_claims(self):
        good = claim("pilot-checked-scope")
        forged = dict(claim("pilot-checked-scope"), fingerprint="0" * 64)
        upgraded = dict(claim(), state="evaluated-scope")  # state without history
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "claims.json"
            path.write_text(json.dumps({"claims": [good]}))
            self.assertEqual(E.check_registry(path), [])
            path.write_text(json.dumps({"claims": [good, forged, upgraded]}))
            problems = E.check_registry(path)
            self.assertEqual(len(problems), 2, problems)

    def test_shipped_registry_is_valid_and_current(self):
        problems = E.check_registry(ROOT / "skills" / "hep-review" / "assets" / "claims.json", current=True)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
