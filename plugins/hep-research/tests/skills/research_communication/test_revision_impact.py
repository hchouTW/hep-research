"""track_revision_impact.py and communication_lib.revisions (plan T6): compare a baseline and a revised communication
record, propagate material changes through recorded occurrences, reopen stale assessments and revision items, and
bound the coverage honestly. The baseline is immutable. Golden scenario of Section 3; all synthetic."""
from __future__ import annotations

import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.research_communication import comm_fixtures as fx

SCRIPTS = fx.PLUGIN / "skills" / "research-communication" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from communication_lib.revisions import diff_communication
    from contracts.communication_project import resolve_context
    import track_revision_impact as cli
except ImportError:
    diff_communication = resolve_context = cli = None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")
        self.before = fx.clone(self.p["doc"])
        self.baseline = fx.write(self.p["root"] / "artifacts" / "comm_v1.json", self.before)
        self.baseline_bytes = self.baseline.read_bytes()
        self.after = fx.clone(self.p["doc"])

    def diff(self, after=None, *, refresh=False):
        self.assertIsNotNone(diff_communication, "communication_lib.revisions does not exist")
        after = after if after is not None else self.after
        if refresh:
            fx.refresh_assessments(after)
        fx.write(self.p["record"], after)
        ctx = resolve_context(self.p["record"], self.p["root"])
        rep = diff_communication(json.loads(self.baseline.read_text()), json.loads(self.p["record"].read_text()), ctx)
        self.assertEqual(self.baseline.read_bytes(), self.baseline_bytes, "the baseline is never modified")
        return rep

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    def c1(self, doc=None):
        return (doc or self.after)["extension"]["claims"][0]

    def new_result(self, value="1.09", unc="0.05"):
        """A new authoritative result under a new source version; the record points at it, text and occurrences unchanged."""
        obs2 = fx.write(self.p["root"] / "artifacts" / "obs_v2.json", fx.observed_result(value, unc))
        self.after["inputs"][0].update(ref="artifacts/obs_v2.json", sha256=fx.sha(obs2))
        self.c1()["evidence"][0]["target"] = "artifacts/obs_v2.json"
        return obs2


class GoldenScenario(Base):
    def test_no_change_has_no_impact(self):
        rep = self.diff()
        self.assertEqual(rep["tool"], "track_revision_impact")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        self.assertEqual(rep["impacts"], [])
        self.assertEqual(rep["coverage"]["claims"]["changed"], 0)

    def test_changed_result_lists_exactly_the_stale_occurrences_and_keeps_the_illustration(self):
        self.new_result()
        rep = self.diff()
        self.assertEqual((rep["status"], rep["exit_code"]), ("incomplete", 3), rep["findings"])
        impacts = {i["claim_id"]: i for i in rep["impacts"]}
        self.assertEqual(set(impacts), {"claim:C1"})
        c1 = impacts["claim:C1"]
        self.assertEqual(c1["kind"], "analysis-rerun")
        self.assertEqual(c1["evidence_changed"], [{"edge": "ev:C1-a", "from": "artifacts/obs.json", "to": "artifacts/obs_v2.json",
                                                   "identity_before": "sha256:" + fx.sha(self.p["obs"]),
                                                   "identity_after": "sha256:" + fx.sha(self.p["root"] / "artifacts" / "obs_v2.json")}])
        self.assertEqual([o["id"] for o in c1["occurrences"]], ["occ:abstract", "occ:body", "occ:caption"])
        self.assertTrue(all(o["state"] == "stale" for o in c1["occurrences"]))
        self.assertEqual(c1["assessment"], "reopened")
        self.assertIn("inspect the new evidence", " ".join(c1["required_actions"]).lower())
        self.assertNotIn("claim:C2", impacts, "the unaffected illustration keeps its provenance")
        self.assertEqual({r["id"]: r["provenance"] for r in rep["unaffected"]}["claim:C2"], ["synthetic", "unvalidated"])
        self.assertIn("revision.assessment_stale", self.codes(rep, "unresolved"))
        self.assertNotIn("revision.assessment_false", " ".join(self.codes(rep)), "a stale assessment is not called false")

    def test_unresolved_new_source_is_incomplete_not_pass(self):
        self.new_result()
        (self.p["root"] / "artifacts" / "obs_v2.json").unlink()
        rep = self.diff()
        self.assertNotEqual(rep["status"], "pass")
        self.assertIn("revision.evidence_unavailable", self.codes(rep))
        self.assertEqual(rep["impacts"][0]["content_comparison"], "incomplete")


class ChangeKinds(Base):
    def test_renamed_file_with_stable_id_is_identity_only(self):
        moved = fx.write(self.p["root"] / "artifacts" / "renamed_obs.json", json.loads(self.p["obs"].read_text()))
        self.after["inputs"][0].update(ref="artifacts/renamed_obs.json", sha256=fx.sha(moved))
        self.c1()["evidence"][0]["target"] = "artifacts/renamed_obs.json"
        rep = self.diff()
        self.assertEqual(rep["impacts"][0]["kind"], "reference-move")
        self.assertEqual(rep["impacts"][0]["value_change"], "none")
        self.assertEqual(rep["status"], "pass", rep["findings"])

    def test_source_replaced_under_the_same_filename(self):
        self.p["obs"].write_text(json.dumps(fx.observed_result("1.09", "0.05")))
        self.after["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        rep = self.diff()
        i = rep["impacts"][0]
        self.assertEqual(i["kind"], "analysis-rerun")
        self.assertEqual(i["evidence_changed"][0]["from"], i["evidence_changed"][0]["to"])
        # the old file is gone: the old value is not recovered from today's file; the baseline's recorded display value is reported as such
        self.assertEqual(i["value_change"], {"locator": "extension.results.ratio", "before": None, "before_recorded_display": "1.02", "after": "1.09"})
        self.assertEqual(i["content_comparison"], "incomplete")
        self.assertIn("revision.history_unavailable", self.codes(rep, "unresolved"))
        self.assertIn("revision.identity_changed", self.codes(rep))

    def test_rounding_only_presentation_change_is_a_content_edit(self):
        for o in self.after["extension"]["occurrences"]:
            if o["claim_id"] == "claim:C1":
                o["passage"] = o["passage"].replace("1.02 +/- 0.05", "1.020 +/- 0.050")
                o["value"] = {"value": "1.020", "unit": "1", "rounding": "decimals:3"}
        rep = self.diff()
        i = rep["impacts"][0]
        self.assertEqual(i["kind"], "content-edit")
        self.assertEqual(i["value_change"], "none")
        self.assertEqual(i["assessment"], "kept")
        self.assertEqual(rep["status"], "pass", rep["findings"])

    def test_stronger_wording_with_unchanged_sources_reopens_the_assessment(self):
        self.c1()["text"] = "The ratio R establishes a deviation of 1.02 +/- 0.05 (synthetic fixture)."
        rep = self.diff()
        i = rep["impacts"][0]
        self.assertEqual(i["kind"], "reassessment")
        self.assertEqual(i["assessment"], "reopened")
        self.assertEqual(i["evidence_changed"], [])
        self.assertIn("revision.assessment_stale", self.codes(rep, "unresolved"))
        self.assertEqual([o["id"] for o in i["occurrences"]], ["occ:abstract", "occ:body", "occ:caption"])

    def test_metadata_only_source_change_does_not_reopen(self):
        obs = json.loads(self.p["obs"].read_text())
        obs["provenance"]["created"] = "2026-10-13"
        self.p["obs"].write_text(json.dumps(obs))
        self.after["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        rep = self.diff()
        i = rep["impacts"][0]
        self.assertEqual(i["kind"], "source-change")
        self.assertEqual(i["value_change"], "none")
        self.assertEqual(i["assessment"], "reconcile-identity")
        self.assertIn("revision.identity_changed", self.codes(rep, "unresolved"))
        self.assertNotIn("revision.assessment_stale", self.codes(rep))

    def test_a_change_to_one_claim_does_not_mark_the_others(self):
        self.after["extension"]["claims"][1]["text"] = "A synthetic illustration gives R = 0.97 (synthetic fixture)."
        rep = self.diff()
        self.assertEqual([i["claim_id"] for i in rep["impacts"]], ["claim:C2"])
        self.assertEqual({r["id"] for r in rep["unaffected"]}, {"claim:C1"})

    def test_removed_and_added_claims(self):
        del self.after["extension"]["claims"][1]
        self.after["extension"]["occurrences"] = [o for o in self.after["extension"]["occurrences"] if o["claim_id"] != "claim:C2"]
        rep = self.diff()
        self.assertEqual(rep["impacts"][0]["kind"], "removed")
        self.assertEqual(rep["coverage"]["claims"], {"before": 2, "after": 1, "changed": 1, "unaffected": 1})


class HistoryAndCoverage(Base):
    def test_historical_content_unavailable_reports_identity_impact_only(self):
        self.new_result()
        self.p["obs"].unlink()  # the historical file was overwritten or removed; no snapshot
        rep = self.diff()
        i = rep["impacts"][0]
        self.assertEqual(i["content_comparison"], "incomplete")
        self.assertEqual(i["evidence_changed"][0]["identity_before"], "sha256:" + self.before["inputs"][0]["sha256"])
        self.assertIsNone(i["value_change"]["before"], "the old content is not recovered from today's file")
        self.assertEqual(i["value_change"]["before_recorded_display"], "1.02", "only the baseline's own recorded display value is reported")
        self.assertIn("revision.history_unavailable", self.codes(rep, "unresolved"))

    def test_unmapped_occurrences_bound_the_coverage(self):
        self.new_result()
        self.after["extension"]["occurrences"] = [o for o in self.after["extension"]["occurrences"] if o["id"] != "occ:caption"]
        rep = self.diff()
        self.assertIn("revision.coverage_unmapped", self.codes(rep, "unresolved"))
        self.assertEqual(rep["coverage"]["whole_manuscript"], "not-claimed")
        self.assertIn("targeted read", " ".join(f["suggested_action"] for f in rep["findings"] if f["code"] == "revision.coverage_unmapped"))

    def test_verified_revision_item_becomes_stale_after_a_later_edit(self):
        self.after["extension"]["revision_items"] = [{"id": "rev:1", "cause": "referee comment 2", "kind": "content-edit",
                                                      "impacted_claims": ["claim:C1"], "impacted_occurrences": ["occ:body"],
                                                      "required_actions": ["restate the uncertainty"], "state": "verified",
                                                      "completion_evidence": [{"check": "check_communication --checks manuscript",
                                                                               "version": "sha256:" + fx.sha(self.p["paper"]), "date": "2026-10-12"}]}]
        rep = self.diff()
        self.assertEqual(rep["revision_items"][0]["state"], "verified")
        self.c1()["text"] = "The ratio R is 1.02 +/- 0.05 (stat only; synthetic fixture)."
        rep = self.diff()
        self.assertEqual(rep["revision_items"][0]["state"], "stale")
        self.assertIn("revision.item_reopened", self.codes(rep, "unresolved"))

    def test_verified_needs_completion_evidence(self):
        self.after["extension"]["revision_items"] = [{"id": "rev:2", "cause": "author decision", "kind": "content-edit",
                                                      "impacted_claims": ["claim:C1"], "required_actions": ["x"], "state": "verified"}]
        rep = self.diff()
        self.assertIn("revision.verified_without_evidence", self.codes(rep, "error"))
        self.assertEqual(rep["status"], "fail")

    def test_edit_list_is_not_evidence(self):
        self.after["extension"]["revision_items"] = [{"id": "rev:3", "cause": "new result", "kind": "analysis-rerun",
                                                      "impacted_claims": ["claim:C1"], "required_actions": ["update abstract"], "state": "edited"}]
        self.new_result()
        rep = self.diff()
        self.assertEqual(rep["revision_items"][0]["state"], "edited")
        self.assertIn("revision.item_not_verified", self.codes(rep, "unresolved"))


class Cli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_cli_outputs_and_exit_codes(self):
        self.new_result()
        fx.write(self.p["record"], self.after)
        code, out, err = self.run_cli(self.baseline, self.p["record"], "--project-root", self.p["root"])
        self.assertEqual(code, 3, out + err)
        rep = json.loads(out)
        self.assertEqual(rep["status"], "incomplete")
        self.assertEqual(rep["scope"]["before"], str(self.baseline))
        report = self.tmp / "impact.md"
        code, out, err = self.run_cli(self.baseline, self.p["record"], "--project-root", self.p["root"], "--format", "markdown", "--out", report)
        self.assertEqual(code, 3)
        self.assertTrue(report.read_text().startswith("# track_revision_impact"))
        self.assertEqual(self.baseline.read_bytes(), self.baseline_bytes)

    def test_invalid_invocation_and_aliases(self):
        self.assertEqual(self.run_cli(self.baseline)[0], 2)
        self.assertEqual(self.run_cli(self.tmp / "nope.json", self.p["record"], "--project-root", self.p["root"])[0], 2)
        self.assertEqual(self.run_cli(self.baseline, self.p["record"], "--project-root", self.p["root"], "--out", self.baseline)[0], 2)
        self.assertEqual(self.run_cli(self.baseline, self.p["record"], "--project-root", self.p["root"], "--out", self.p["record"])[0], 2)


if __name__ == "__main__":
    unittest.main()
