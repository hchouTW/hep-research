"""Generic tests of core/evidence (ledger validator and index renderer) on a two-record
synthetic ledger. Experiment ledgers are tested in their own profile folders."""
import copy
import unittest
from datetime import date

from core.evidence import ledger as vel
from core.evidence import render_index as rsi

TODAY = date(2026, 10, 2)
SOURCE = {"id": "fx:S01", "title": "Synthetic source (fixture, not a real paper)", "authors": "fixture", "year": 2020,
          "year_text": "2020", "dois": [], "url": None, "locator_text": "synthetic", "inspire_record_id": None,
          "arxiv_ids": [], "tier": 1, "tier_range": None, "tier_text": "1", "verification_level": "abstract+metadata",
          "verification_note": None, "verification_date": "2026-09-20", "publication_date": "2020",
          "data_taking_period": None, "supersedes": [], "superseded_by": [], "supersession_note": None, "notes": None,
          "verification_limitations": None, "formal_status": "published"}
CLAIM = {"id": "fx:C01", "claim": "Synthetic claim used only by tests", "claim_types": ["published_result"],
         "claim_type_note": None, "support_kind": "primary", "source_ids": ["fx:S01"], "location": "abstract",
         "scope": {"text": "synthetic scope"}, "limitations": None, "verification_strength": "abstract+metadata",
         "numeric_quotation_allowed": True, "last_reviewed": "2026-09-20", "evidence_status": "public-fact"}


def run(sources, claims, namespace="fx"):
    return vel.check_ledger(sources, claims, TODAY, 365, namespace)


def codes(report):
    return {e["code"] for e in report["errors"]}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.s, self.c = [copy.deepcopy(SOURCE)], [copy.deepcopy(CLAIM)]

    def test_valid(self):
        r = run(self.s, self.c)
        self.assertEqual(r["status"], "pass", r["errors"])

    def test_malformed_records_are_findings_with_field_paths(self):
        bad_source = dict(self.s[0], id="fx:S02", year="2020", data_taking_period="2019-2020")
        undated = {k: v for k, v in self.s[0].items() if k != "id"}
        undated["verification_date"] = "2020-01-01"  # old enough to be stale: used to raise on the missing id
        claim = dict(self.c[0], source_ids=[["fx:S01"]], claim_types="published_result", verification_strength=["full-text"])
        r = run(self.s + [bad_source, "not a record", undated], self.c + [claim, 7])
        found = {(e["code"], e["where"]) for e in r["errors"]}
        self.assertIn(("source.bad_field_type", "fx:S02.year"), found)
        self.assertIn(("source.bad_field_type", "fx:S02.data_taking_period"), found)
        self.assertIn(("source.malformed", "sources[2]"), found)
        self.assertIn(("source.missing_field", "sources[3]"), found)
        self.assertIn(("claim.bad_field_type", "fx:C01.source_ids"), found)
        self.assertIn(("claim.bad_field_type", "fx:C01.claim_types"), found)
        self.assertIn(("claim.bad_field_type", "fx:C01.verification_strength"), found)
        self.assertIn(("claim.malformed", "claims[2]"), found)

    def test_namespace_enforced_only_when_given(self):
        self.s[0]["id"], self.c[0]["source_ids"] = "S01", ["S01"]
        self.c[0]["id"] = "C01"
        self.assertIn("source.bad_id", codes(run(self.s, self.c)))
        self.assertEqual(run(self.s, self.c, namespace=None)["status"], "pass")

    def test_wrong_namespace(self):
        self.c[0]["id"] = "other:C01"
        self.assertIn("claim.bad_id", codes(run(self.s, self.c)))

    def test_legacy_access_date_is_still_read(self):
        del self.s[0]["verification_date"]
        self.s[0]["access_date"] = "2027-01-01"
        self.assertIn("source.future_access_date", codes(run(self.s, self.c)))

    def test_unknown_date_marker_needs_unread_level(self):
        self.s[0]["verification_date"] = "unknown"
        self.assertIn("source.level_without_access_date", codes(run(self.s, self.c)))
        self.s[0]["verification_level"] = "not-verified"
        self.c[0].update(verification_strength="not-verified", numeric_quotation_allowed=False)
        self.assertNotIn("source.level_without_access_date", codes(run(self.s, self.c)))

    def test_claim_stronger_than_source(self):
        self.c[0]["verification_strength"] = "full-text"
        self.assertIn("claim.stronger_than_sources", codes(run(self.s, self.c)))


class DateDistinctionTests(unittest.TestCase):
    """Section 12: current date, publication/data-taking dates and verification date stay distinct."""

    def setUp(self):
        self.s, self.c = [copy.deepcopy(SOURCE)], [copy.deepcopy(CLAIM)]

    def test_full_publication_date_after_verification(self):
        self.s[0].update(publication_date="2026-09-30", year=2026, year_text="2026")  # same year, later day
        self.assertIn("source.published_after_access", codes(run(self.s, self.c)))

    def test_publication_month_compared_at_shared_precision(self):
        self.s[0].update(publication_date="2026-09", year=2026, year_text="2026")  # cannot tell: same month
        self.assertNotIn("source.published_after_access", codes(run(self.s, self.c)))
        self.s[0]["publication_date"] = "2026-10"
        self.assertIn("source.published_after_access", codes(run(self.s, self.c)))

    def test_data_period_reversed(self):
        self.s[0]["data_taking_period"] = {"start": "2019-01-01", "end": "2018-12-31"}
        self.assertIn("source.data_period_reversed", codes(run(self.s, self.c)))

    def test_data_taken_after_publication(self):
        self.s[0]["data_taking_period"] = {"start": "2018-01-01", "end": "2021-06-30"}
        self.assertIn("source.data_after_publication", codes(run(self.s, self.c)))

    def test_verification_date_after_current_date(self):
        self.assertIn("source.future_access_date", codes(vel.check_ledger(self.s, self.c, date(2026, 9, 1), 365, "fx")))

    def test_consistent_dates_pass(self):
        self.s[0]["data_taking_period"] = {"start": "2018-01-01", "end": "2019-06-30"}
        self.assertEqual(run(self.s, self.c)["status"], "pass")


class RenderTests(unittest.TestCase):
    def test_round_trip(self):
        text = "# Index\n\n<!-- BEGIN GENERATED: source-table -->\n<!-- END GENERATED: source-table -->\n\n" \
               "<!-- BEGIN GENERATED: claim-ledger -->\n<!-- END GENERATED: claim-ledger -->\n\nprose\n"
        out = rsi.write_index(text, [SOURCE], [CLAIM])
        self.assertTrue(rsi.check_index(out, [SOURCE], [CLAIM])[0])
        self.assertIn("| fx:S01 |", out)
        self.assertTrue(out.endswith("prose\n"))
        self.assertFalse(rsi.check_index(text, [SOURCE], [CLAIM])[0])


if __name__ == "__main__":
    unittest.main()
