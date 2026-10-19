"""check_adaptation.py and communication_lib.adaptation (plan T8): a derived draft (paragraph, abstract, talk, poster,
public summary) keeps its claim ids in a companion manifest, its numbers and status labels consistent with the record,
and its indispensable limitations and scope; reviewer responses are worded from the recorded action state. All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.hep_writing import comm_fixtures as fx

SCRIPTS = fx.PLUGIN / "skills" / "hep-writing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from communication_lib.adaptation import check_adaptation, draft_responses
    from contracts.communication_project import resolve_context
    import check_adaptation as cli
except ImportError:
    check_adaptation = draft_responses = resolve_context = cli = None

SUMMARY = ("In a synthetic fixture sample, the ratio R was found to be 1.02 +/- 0.05, consistent with unity. "
           "The uncertainty quoted is statistical only. A synthetic illustration at 0.98 is shown for orientation.")


def manifest(record_path: Path, statements=None, **brief):
    b = {"audience": "public", "format": "summary", "length_budget": "80 words", "central_claim": "claim:C1",
         "record_ref": "artifacts/comm.json", "record_sha256": fx.sha(record_path),
         "indispensable_limitations": [{"text": "statistical uncertainty only", "as_written": "statistical only"}, "synthetic fixture"]}
    b.update(brief)
    return {"manifest_version": "1.0.0", "brief": b,
            "statements": statements if statements is not None else [
                {"id": "st:1", "text": "the ratio R was found to be 1.02 +/- 0.05, consistent with unity", "claim_ids": ["claim:C1"], "kind": "quantitative"},
                {"id": "st:2", "text": "A synthetic illustration at 0.98 is shown for orientation", "claim_ids": ["claim:C2"], "kind": "context"}],
            "omissions": [{"what": "the fit procedure", "reason": "not needed for a public summary; the number and its scope are kept"}],
            "unresolved_inputs": [],
            "semantic_review": {"by": "fixture author", "date": "2026-10-12", "verdict": "consistent"}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")
        self.doc = fx.clone(self.p["doc"])

    def check(self, draft=SUMMARY, man=None, doc=None):
        self.assertIsNotNone(check_adaptation, "communication_lib.adaptation does not exist")
        fx.write(self.p["record"], doc or self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        man = man if man is not None else manifest(self.p["record"])
        return check_adaptation(json.loads(self.p["record"].read_text()), ctx, man, draft)

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}


class Manifest(Base):
    def test_consistent_summary_passes(self):
        rep = self.check()
        self.assertEqual(rep["tool"], "check_adaptation")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        self.assertEqual(rep["coverage"]["statements"], {"declared": 2, "located": 2, "with_claim": 2})
        self.assertEqual(rep["coverage"]["limitations"], {"indispensable": 2, "present": 2})

    def test_statement_missing_from_draft_or_without_claim(self):
        man = manifest(self.p["record"])
        man["statements"][0]["text"] = "the ratio R was found to be 1.03"
        rep = self.check(man=man)
        self.assertIn("adaptation.statement_not_in_draft", self.codes(rep, "error"))
        man = manifest(self.p["record"])
        man["statements"][0]["claim_ids"] = []
        rep = self.check(man=man)
        self.assertIn("adaptation.statement_without_claim", self.codes(rep, "error"))
        man["statements"][0]["claim_ids"] = ["claim:C9"]
        self.assertIn("adaptation.unknown_claim", self.codes(self.check(man=man), "error"))

    def test_number_must_match_the_record(self):
        draft = SUMMARY.replace("1.02 +/- 0.05", "1.03 +/- 0.05")
        man = manifest(self.p["record"])
        man["statements"][0]["text"] = "the ratio R was found to be 1.03 +/- 0.05, consistent with unity"
        rep = self.check(draft=draft, man=man)
        self.assertIn("adaptation.number_mismatch", self.codes(rep, "error"))
        self.assertEqual(rep["status"], "fail")

    def test_unmapped_number_in_the_draft_is_flagged(self):
        draft = SUMMARY + " The sample held 12 345 events."
        rep = self.check(draft=draft)
        self.assertIn("adaptation.unmapped_number", self.codes(rep, "warning"))

    def test_status_label_cannot_be_compressed_away(self):
        draft = SUMMARY.replace("A synthetic illustration at 0.98", "An illustration at 0.98")
        man = manifest(self.p["record"])
        man["statements"][1]["text"] = "An illustration at 0.98 is shown for orientation"
        man["brief"]["indispensable_limitations"] = [{"text": "statistical uncertainty only", "as_written": "statistical only"}]
        rep = self.check(draft=draft, man=man)
        self.assertIn("adaptation.status_dropped", self.codes(rep, "error"))
        self.assertIn("claim:C2", json.dumps([f for f in rep["findings"] if f["code"] == "adaptation.status_dropped"]))

    def test_decisive_caveat_dropped_by_compression(self):
        draft = SUMMARY.replace(" The uncertainty quoted is statistical only.", "")
        rep = self.check(draft=draft)
        self.assertIn("adaptation.caveat_dropped", self.codes(rep, "error"))
        f = next(x for x in rep["findings"] if x["code"] == "adaptation.caveat_dropped")
        self.assertIn("statistical uncertainty only", f["message"])
        man = manifest(self.p["record"])
        man["brief"]["indispensable_limitations"] = [{"text": "statistical uncertainty only", "as_written": "consistent with unity"}]
        self.assertNotIn("adaptation.caveat_dropped", self.codes(self.check(draft=draft, man=man)), "a declared paraphrase counts")

    def test_public_summary_that_becomes_universal_needs_its_scope(self):
        draft = "The ratio R is 1.02 +/- 0.05 for all energies and samples. The uncertainty is statistical only (synthetic fixture)."
        man = manifest(self.p["record"], statements=[{"id": "st:1", "text": "The ratio R is 1.02 +/- 0.05 for all energies and samples",
                                                        "claim_ids": ["claim:C1"], "kind": "conclusion"}])
        rep = self.check(draft=draft, man=man)
        self.assertIn("adaptation.scope_dropped", self.codes(rep, "error"))
        f = next(x for x in rep["findings"] if x["code"] == "adaptation.scope_dropped")
        self.assertIn("synthetic fixture sample", f["message"])
        self.assertIn("revise", f["suggested_action"].lower())

    def test_stale_record_and_missing_semantic_review_are_unresolved(self):
        man = manifest(self.p["record"], record_sha256="0" * 64)
        rep = self.check(man=man)
        self.assertIn("adaptation.record_stale", self.codes(rep, "unresolved"))
        man = manifest(self.p["record"])
        del man["semantic_review"]
        rep = self.check(man=man)
        self.assertIn("adaptation.semantic_review_pending", self.codes(rep, "unresolved"))
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("keyword", rep["note"].lower())

    def test_omissions_and_unresolved_inputs_are_listed(self):
        man = manifest(self.p["record"])
        man["unresolved_inputs"] = ["the systematic uncertainty, requested from hep-measurement"]
        rep = self.check(man=man)
        self.assertEqual(rep["omissions"][0]["what"], "the fit procedure")
        self.assertEqual(rep["unresolved_inputs"], ["the systematic uncertainty, requested from hep-measurement"])
        self.assertEqual(rep["status"], "incomplete")


class ReviewerResponses(Base):
    def items(self, *items):
        self.doc["extension"]["reviewer_items"] = list(items)
        self.doc["extension"].setdefault("revision_items", [])

    def rev(self, rid, state, evidence=None, claims=("claim:C1",), occ=("occ:body",)):
        it = {"id": rid, "cause": "referee comment", "kind": "content-edit", "impacted_claims": list(claims), "impacted_occurrences": list(occ),
              "required_actions": ["restate the uncertainty"], "state": state}
        if evidence:
            it["completion_evidence"] = [{"check": "check_communication --checks manuscript", "version": "sha256:" + fx.sha(self.p["paper"]), "date": "2026-10-12"}]
        self.doc["extension"]["revision_items"].append(it)
        return it

    def responses(self):
        self.assertIsNotNone(draft_responses, "communication_lib.adaptation does not exist")
        fx.write(self.p["record"], self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        return draft_responses(json.loads(self.p["record"].read_text()), ctx)

    def test_requested_rerun_not_done_stays_pending(self):
        self.items({"id": "rev:R1", "comment": "Please rerun the fit with the updated calibration.", "requested_action": "rerun the fit with the updated calibration",
                    "claims": ["claim:C1"], "revision_items": ["rev:1"], "disposition": "changed", "response_draft": "We have rerun the fit and updated the number."})
        self.rev("rev:1", "pending-evidence")
        rep = self.responses()
        row = rep["action_table"][0]
        self.assertEqual(row["comment_id"], "rev:R1")
        self.assertEqual(row["state"], "pending")
        self.assertIn("response.changed_without_completion", self.codes(rep, "error"))
        self.assertIn("response.asserts_uncompleted_work", self.codes(rep, "error"))
        self.assertNotIn("we have rerun", rep["drafts"][0]["text"].lower())
        self.assertIn("pending", rep["drafts"][0]["text"].lower())
        self.assertEqual(rep["status"], "fail")

    def test_completed_change_may_use_past_tense_with_locator(self):
        self.items({"id": "rev:R2", "comment": "State the uncertainty type.", "requested_action": "state that the uncertainty is statistical",
                    "claims": ["claim:C1"], "revision_items": ["rev:2"], "disposition": "changed"})
        self.rev("rev:2", "verified", evidence=True)
        rep = self.responses()
        self.assertEqual(rep["status"], "pass", rep["findings"])
        text = rep["drafts"][0]["text"]
        self.assertIn("We have", text)
        self.assertIn("section:Results", text)
        self.assertEqual(rep["action_table"][0]["verification"][0]["check"], "check_communication --checks manuscript")

    def test_several_comments_one_change_and_one_comment_several_changes(self):
        self.items({"id": "rev:R3", "comment": "a", "requested_action": "clarify the uncertainty", "claims": ["claim:C1"], "revision_items": ["rev:3"], "disposition": "changed"},
                   {"id": "rev:R4", "comment": "b", "requested_action": "clarify the uncertainty in the caption too", "claims": ["claim:C1"], "revision_items": ["rev:3"], "disposition": "changed"},
                   {"id": "rev:R5", "comment": "c", "requested_action": "update abstract and caption", "claims": ["claim:C1"], "revision_items": ["rev:4", "rev:5"], "disposition": "changed"})
        self.rev("rev:3", "verified", evidence=True)
        self.rev("rev:4", "verified", evidence=True, occ=("occ:abstract",))
        self.rev("rev:5", "edited", occ=("occ:caption",))
        rep = self.responses()
        states = {r["comment_id"]: r["state"] for r in rep["action_table"]}
        self.assertEqual(states, {"rev:R3": "completed", "rev:R4": "completed", "rev:R5": "pending"})
        self.assertEqual(rep["action_table"][2]["revision_items"], [{"id": "rev:4", "state": "verified"}, {"id": "rev:5", "state": "edited"}])
        self.assertIn("rev:5", rep["drafts"][2]["text"])
        self.assertIn("response.changed_without_completion", self.codes(rep, "error"))

    def test_reasoned_decline_is_valid_and_needs_a_reason(self):
        self.items({"id": "rev:R6", "comment": "Use a different binning.", "requested_action": "rebin", "claims": ["claim:C1"], "revision_items": [],
                    "disposition": "declined", "response_draft": "The binning follows the detector resolution; a finer binning would not be populated (synthetic fixture)."})
        rep = self.responses()
        self.assertEqual(rep["status"], "pass", rep["findings"])
        self.assertIn("not changed", rep["drafts"][0]["text"].lower())
        self.items({"id": "rev:R7", "comment": "x", "requested_action": "y", "claims": [], "revision_items": [], "disposition": "declined"})
        rep = self.responses()
        self.assertIn("response.decline_without_reason", self.codes(rep, "error"))

    def test_no_items_is_a_no_op_with_a_note(self):
        rep = self.responses()
        self.assertEqual(rep["action_table"], [])
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("response.no_items", self.codes(rep, "unresolved"))


class Cli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_manifest_mode_and_responses_mode(self):
        fx.write(self.p["record"], self.doc)
        man = fx.write(self.tmp / "manifest.json", manifest(self.p["record"]))
        draft = fx.write(self.tmp / "summary.md", SUMMARY)
        code, out, err = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--manifest", man, "--draft", draft)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out)["tool"], "check_adaptation")
        code, out, _ = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--responses", "--format", "markdown")
        self.assertEqual(code, 3)
        self.assertTrue(out.startswith("# draft_reviewer_responses"))
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"])[0], 2, "one mode is required")
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--manifest", man)[0], 2, "--draft goes with --manifest")
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--manifest", man, "--draft", draft, "--out", draft)[0], 2)


if __name__ == "__main__":
    unittest.main()


class ReviewFixes(Base):
    """Final review of the branch: I7 (negated completion wording; a completed state on stale evidence) and the
    English-only status words that made a Traditional Chinese summary a false error."""

    def items(self, *items):
        self.doc["extension"]["reviewer_items"] = list(items)
        self.doc["extension"].setdefault("revision_items", [])

    def responses(self):
        fx.write(self.p["record"], self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        return draft_responses(json.loads(self.p["record"].read_text()), ctx)

    def test_negated_completion_wording_is_not_an_assertion(self):
        self.items({"id": "rev:R8", "comment": "rerun", "requested_action": "rerun the fit", "claims": ["claim:C1"], "revision_items": ["rev:8"],
                    "disposition": "pending", "response_draft": "We have not yet rerun the fit; it is pending."})
        self.doc["extension"]["revision_items"].append({"id": "rev:8", "cause": "referee", "kind": "analysis-rerun", "impacted_claims": ["claim:C1"],
                                                        "required_actions": ["rerun"], "state": "pending-evidence"})
        rep = self.responses()
        self.assertNotIn("response.asserts_uncompleted_work", self.codes(rep))

    def test_verified_item_on_a_stale_version_is_not_completed(self):
        self.items({"id": "rev:R9", "comment": "x", "requested_action": "state the uncertainty type", "claims": ["claim:C1"], "revision_items": ["rev:9"],
                    "disposition": "changed"})
        self.doc["extension"]["revision_items"].append({"id": "rev:9", "cause": "referee", "kind": "content-edit", "impacted_claims": ["claim:C1"],
                                                        "impacted_occurrences": ["occ:body"], "required_actions": ["x"], "state": "verified",
                                                        "completion_evidence": [{"check": "check_communication --checks manuscript", "version": "sha256:" + "0" * 64, "date": "2026-10-12"}]})
        rep = self.responses()
        self.assertEqual(rep["action_table"][0]["state"], "pending")
        self.assertIn("response.evidence_not_current", self.codes(rep, "unresolved"))
        self.assertNotIn("We have", rep["drafts"][0]["text"])

    def test_chinese_status_words_count(self):
        draft = "在合成樣本中，比值 R 為 1.02 +/- 0.05，僅含統計不確定度。0.98 為合成示意值，僅供參考。"
        man = manifest(self.p["record"], statements=[{"id": "st:1", "text": "比值 R 為 1.02 +/- 0.05", "claim_ids": ["claim:C1"], "kind": "quantitative"},
                                                     {"id": "st:2", "text": "0.98 為合成示意值", "claim_ids": ["claim:C2"], "kind": "context"}],
                       indispensable_limitations=["統計不確定度", "合成"])
        rep = self.check(draft=draft, man=man)
        self.assertNotIn("adaptation.status_dropped", self.codes(rep))
        self.assertEqual(rep["status"], "pass", rep["findings"])


class ReviewMinors(Base):
    def test_unmapped_number_findings_are_ordered_independently_of_the_hash_seed(self):
        import os
        import subprocess
        fx.write(self.p["record"], self.doc)
        man = fx.write(self.tmp / "manifest.json", manifest(self.p["record"]))
        draft = fx.write(self.tmp / "summary.md", SUMMARY + " Counts: 77, 12, 9, 310, 4.")
        outs = []
        for seed in ("1", "2"):
            run = subprocess.run([sys.executable, str(SCRIPTS / "check_adaptation.py"), str(self.p["record"]), "--project-root", str(self.p["root"]),
                                  "--manifest", str(man), "--draft", str(draft)], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed), timeout=120)
            outs.append(run.stdout)
        self.assertEqual(outs[0], outs[1])
        self.assertIn("adaptation.unmapped_number", outs[0])
