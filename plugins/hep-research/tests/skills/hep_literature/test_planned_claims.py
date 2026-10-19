"""Com1: planned claims (kind "planned" with a recheck_by date) in evidence ledgers and communication records.

Oracles: manage_literature.py flags a planned claim whose recheck_by date has passed (exit 3) and not one whose date
is still ahead (dates are fixed through --today, so the test does not depend on the clock); a planned claim without
recheck_by or with a malformed date is reported; audit_claims refuses a planned claim as support for a measured
result, and a measured claim that is itself marked planned. All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tests.skills.hep_writing import comm_fixtures as fx
from tests.skills.hep_writing.test_claim_audit import Base as AuditBase
from tests.skills.hep_literature.test_literature_lifecycle import claim, source

import manage_literature as cli  # noqa: E402  (scripts folder put on sys.path by the imported test modules)
from literature_lib.literature import import_literature  # noqa: E402


def planned(cid, sids, recheck_by="2027-06-30"):
    c = claim(cid, sids)
    c.update(claim="the fixture upgrade is planned for installation (as of 2026-10-12)", kind="planned")
    if recheck_by is not None:
        c["recheck_by"] = recheck_by
    return c


class LedgerSide(unittest.TestCase):
    def run_import(self, claims, today):
        data = {"sources": [source("lit:S01", "Fixture schedule note", doi="10.0000/plan")], "claims": claims}
        return import_literature([{"path": "input.json", "sha256": "0" * 64, "data": data}], None, today=today)

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    def test_expired_planned_claim_is_flagged_and_unexpired_is_not(self):
        record, rep = self.run_import([planned("lit:C01", ["lit:S01"], "2026-10-01")], today="2026-10-12")
        self.assertIn("literature.planned_claim_expired", self.codes(rep, "unresolved"))
        self.assertEqual(rep["exit_code"], 3)
        self.assertIn({"source_id": "lit:S01", "reason": "planned claim lit:C01 passed its recheck_by date 2026-10-01",
                       "level": "recheck-plan", "claims": ["lit:C01"]}, record["flags"])
        record, rep = self.run_import([planned("lit:C01", ["lit:S01"], "2026-10-12")], today="2026-10-12")
        self.assertNotIn("literature.planned_claim_expired", self.codes(rep))  # due today, not yet past
        self.assertEqual(rep["exit_code"], 0, rep["findings"])
        self.assertEqual(record["flags"], [])

    def test_planned_claim_without_recheck_date_is_open(self):
        _, rep = self.run_import([planned("lit:C01", ["lit:S01"], None)], today="2026-10-12")
        self.assertIn("literature.planned_claim_no_recheck", self.codes(rep, "unresolved"))
        self.assertEqual(rep["exit_code"], 3)

    def test_malformed_recheck_date_is_a_confirmed_problem(self):
        _, rep = self.run_import([planned("lit:C01", ["lit:S01"], "next spring")], today="2026-10-12")
        self.assertIn("literature.planned_claim_bad_date", self.codes(rep, "error"))
        self.assertEqual(rep["exit_code"], 1)

    def test_ordinary_claims_are_unaffected(self):
        _, rep = self.run_import([claim("lit:C01", ["lit:S01"])], today="2030-01-01")
        self.assertFalse({c for c in self.codes(rep) if c.startswith("literature.planned")})

    def test_cli_exit_code_follows_today(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        inp = tmp / "input.json"
        inp.write_text(json.dumps({"sources": [source("lit:S01", "Fixture schedule note", doi="10.0000/plan")],
                                   "claims": [planned("lit:C01", ["lit:S01"], "2027-06-30")]}), encoding="utf-8")
        for today, code in (("2027-06-30", 0), ("2027-07-01", 3)):
            with self.subTest(today=today), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["import", str(inp), "--project-root", str(tmp), "--out", str(tmp / "rec.json"),
                                           "--today", today]), code)


class AuditSide(AuditBase):
    def with_ledger(self, claims):
        ext = self.doc["extension"]
        src = {"id": "lit:S01", "title": "Synthetic schedule note", "authors": "Fixture et al.", "year": 2026, "tier": 2,
               "verification_level": "full-text", "verification_date": "2026-10-12", "supersedes": [], "superseded_by": [],
               "identifiers": {"doi": "10.0000/synthetic-plan"}, "verification_limitations": "fixture"}
        sp = fx.write(self.p["root"] / "evidence" / "sources.json", [src])
        cp = fx.write(self.p["root"] / "evidence" / "claims.json", claims)
        ext["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/sources.json", "claims_ref": "evidence/claims.json",
                                    "sources_sha256": fx.sha(sp), "claims_sha256": fx.sha(cp)}]
        ext["sources_read"] = [{"id": "lit:S01", "level": "full-text", "verification_date": "2026-10-12", "locators": []}]
        self.c1()["evidence"].append({"id": "ev:C1-s", "target_kind": "source", "target": "lit:S01", "locator": "Section 2",
                                      "role": "supports", "usage": "used-in-claim", "version": "2026-10-12"})
        self.c1()["assessment"]["evidence_ids"].append("ev:C1-s")

    def test_planned_claim_is_refused_as_support_for_a_measured_result(self):
        self.assertEqual(self.c1()["claim_type"], "measurement")
        self.with_ledger([planned("lit:C01", ["lit:S01"])])
        rep = self.audit()
        self.assertIn("claim.planned_support", self.codes(rep, "error"), rep["findings"])
        self.assertEqual(rep["exit_code"], 1)

    def test_source_with_a_measured_claim_too_is_not_refused(self):
        self.with_ledger([planned("lit:C01", ["lit:S01"]), claim("lit:C02", ["lit:S01"])])
        self.assertNotIn("claim.planned_support", self.codes(self.audit()))

    def test_planned_support_for_a_background_claim_is_allowed(self):
        self.with_ledger([planned("lit:C01", ["lit:S01"])])
        self.c1()["claim_type"] = "background"
        self.assertNotIn("claim.planned_support", self.codes(self.audit()))

    def test_measured_claim_marked_planned_is_refused(self):
        self.c1()["kind"] = "planned"
        rep = self.audit()
        self.assertIn("claim.planned_as_measured", self.codes(rep, "error"))
        self.assertEqual(rep["exit_code"], 1)


if __name__ == "__main__":
    unittest.main()
