"""theory:cr-secondary-ratio open question B1: the search record for an external B/C benchmark is consistent with the
evidence ledger, stays 'open', and carries no reference value (tables-only rule; nothing read off a figure)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = json.loads((ROOT / "benchmarks" / "external-benchmark-search.json").read_text(encoding="utf-8"))
SOURCES = {s["id"]: s for s in json.loads((ROOT / "evidence" / "sources.json").read_text(encoding="utf-8"))}
CLAIMS = {c["id"]: c for c in json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))}


class ExternalBenchmarkSearchTests(unittest.TestCase):
    def test_status_open_and_dated(self):
        self.assertEqual(REC["status"], "open")
        self.assertEqual(REC["access_date"], "2026-10-15")

    def test_every_examined_paper_is_in_the_ledger_with_its_version(self):
        for e in REC["examined"]:
            src = SOURCES[e["ledger"]]
            self.assertEqual(src["verification_date"], "2026-10-15", e["ledger"])
            self.assertNotEqual(src["verification_level"], "not-opened", e["ledger"])
            arxiv_id, _, version = e["arxiv"].rpartition("v")
            self.assertIn(arxiv_id, src["identifiers"]["arxiv_ids"])
            self.assertTrue(version.isdigit(), e["arxiv"])
            self.assertTrue(e["why_not_usable"])

    def test_absence_claim_cites_every_examined_paper(self):
        c = CLAIMS["crsr:C06"]
        self.assertEqual(c["support_kind"], "absence_search")
        self.assertFalse(c["numeric_quotation_allowed"])
        self.assertEqual(set(c["source_ids"]), {e["ledger"] for e in REC["examined"]})

    def test_no_reference_values(self):
        def numbers(obj):
            if isinstance(obj, dict):
                return [n for v in obj.values() for n in numbers(v)]
            if isinstance(obj, list):
                return [n for v in obj for n in numbers(v)]
            return [obj] if isinstance(obj, (int, float)) and not isinstance(obj, bool) else []
        self.assertEqual(numbers(REC), [])


if __name__ == "__main__":
    unittest.main()
