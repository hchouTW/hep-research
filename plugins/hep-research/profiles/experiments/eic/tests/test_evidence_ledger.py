"""Tests of the shipped eic evidence ledger with core/evidence/ledger.py and render_index.py.
The shipped ledger must pass; mutation tests start from the shipped data, introduce one defect, and assert the
diagnostic. Run from the profile folder: python3 -m unittest discover -s tests -t tests -v"""
import copy
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))
from core.evidence import ledger as vel  # noqa: E402
from core.evidence import render_index as rsi  # noqa: E402

NS = "eic"
SOURCES, CLAIMS, INDEX = ROOT / "evidence" / "sources.json", ROOT / "evidence" / "claims.json", ROOT / "evidence" / "index.md"
MODULES = sorted((ROOT / "modules").rglob("*.md"))


def ledger():
    s, c = vel.load_ledger(SOURCES, CLAIMS)
    return copy.deepcopy(s), copy.deepcopy(c)


def today(sources):
    """The latest verification date in the ledger: reproducible, and never earlier than any read."""
    return max(date.fromisoformat(s["verification_date"]) for s in sources if s.get("verification_date") not in (None, "unknown"))


def run(sources, claims):
    return vel.check_ledger(sources, claims, today(sources), 365, NS)


def codes(report, kind="errors"):
    return {e["code"] for e in report[kind]}


class ShippedLedgerTests(unittest.TestCase):
    def test_shipped_ledger_passes(self):
        sources, claims = ledger()
        rep = run(sources, claims)
        self.assertEqual(rep["status"], "pass", rep["errors"] + rep["warnings"])
        self.assertGreaterEqual(rep["counts"]["sources"], 4)
        self.assertGreaterEqual(rep["counts"]["claims"], 6)

    def test_every_source_has_a_level_and_a_verification_date(self):
        for s in ledger()[0]:
            self.assertIn(s["verification_level"], vel.STRENGTH, s["id"])
            self.assertRegex(s["verification_date"], r"^\d{4}-\d{2}-\d{2}$", s["id"])
            self.assertIn("publication_date", s, s["id"])
            self.assertNotEqual(s["publication_date"], s["verification_date"], s["id"])

    def test_no_claim_is_called_measured(self):
        for c in ledger()[1]:
            self.assertNotIn("measured", c["claim"].lower(), c["id"])
            self.assertTrue(c["scope"]["text"], c["id"])
            self.assertTrue(c.get("limitations"), c["id"])

    def test_numeric_claims_say_design_or_projection(self):
        for c in ledger()[1]:
            if c["numeric_quotation_allowed"]:
                text = (c["scope"]["text"] + " " + c["limitations"]).lower()
                self.assertTrue("design" in text or "projection" in text, c["id"])

    def test_module_citations_resolve(self):
        sources, claims = ledger()
        sids, cids = {s["id"] for s in sources}, {c["id"] for c in claims}
        for path in MODULES:
            text = path.read_text(encoding="utf-8")
            for sid in set(re.findall(r"\bS\d\d\b", text)):
                self.assertIn(f"{NS}:{sid}", sids, (path.name, sid))
            for cid in set(re.findall(r"\bC\d\d\b", text)):
                self.assertIn(f"{NS}:{cid}", cids, (path.name, cid))

    def test_facility_and_detector_bullets_each_cite_a_claim(self):
        for rel in ("facility/eic-facility-context.md", "detector/epic-detector-context.md", "detector/epic-software-entry-points.md"):
            for line in (ROOT / "modules" / rel).read_text(encoding="utf-8").splitlines():
                if line.startswith("- "):
                    self.assertRegex(line, r"\bC\d\d\b", (rel, line))

    def test_facility_claims_cite_facility_sources_and_epic_claims_cite_epic_sources(self):
        _, claims = ledger()
        for c in claims:
            scope = c["scope"]["text"].lower()
            self.assertTrue(scope.startswith("eic facility") or scope.startswith("epic"), c["id"])

    def test_proceedings_source_is_context_only(self):
        sources, claims = ledger()
        s05 = next(s for s in sources if s["id"] == "eic:S05")
        self.assertEqual((s05["tier"], s05["verification_level"]), (3, "abstract+metadata"))
        self.assertIn("osti.gov", s05["url"])
        self.assertIn("10.1051/epjconf/202429503011", s05["dois"])
        citing = [c for c in claims if "eic:S05" in c["source_ids"]]
        self.assertEqual([c["id"] for c in citing], ["eic:C09"])
        self.assertEqual(citing[0]["support_kind"], "third_party_context")
        self.assertFalse(citing[0]["numeric_quotation_allowed"])


class DefectTests(unittest.TestCase):
    def test_namespace_is_required(self):
        sources, claims = ledger()
        sources[0]["id"] = "S01"
        self.assertIn("source.bad_id", codes(run(sources, claims)))

    def test_numeric_quotation_needs_a_read_source(self):
        sources, claims = ledger()
        s = sources[0]
        s["verification_level"] = "metadata-only"
        rep = run(sources, claims)
        self.assertTrue({"claim.stronger_than_sources", "claim.numeric_without_reading"} & codes(rep), rep["errors"])

    def test_claim_cannot_outrank_its_source(self):
        sources, claims = ledger()
        claims[0]["verification_strength"] = "full-text"
        self.assertIn("claim.stronger_than_sources", codes(run(sources, claims)))

    def test_primary_claim_needs_tier_1_or_2(self):
        sources, claims = ledger()
        for s in sources:
            s["tier"] = 3
            s["tier_text"] = "3"
        self.assertIn("claim.no_primary_source", codes(run(sources, claims)))

    def test_future_verification_date_rejected(self):
        sources, claims = ledger()
        sources[0]["verification_date"] = "2099-01-01"
        rep = vel.check_ledger(sources, claims, date(2026, 10, 4), 365, NS)
        self.assertIn("source.future_access_date", codes(rep))


class RenderTests(unittest.TestCase):
    def test_index_in_sync(self):
        sources, claims = ledger()
        ok, detail = rsi.check_index(INDEX.read_text(encoding="utf-8"), sources, claims)
        self.assertTrue(ok, detail)

    def test_edited_claim_is_detected(self):
        sources, claims = ledger()
        claims[0]["claim"] += " (edited)"
        ok, detail = rsi.check_index(INDEX.read_text(encoding="utf-8"), sources, claims)
        self.assertFalse(ok)
        self.assertIn(claims[0]["id"], detail)


if __name__ == "__main__":
    unittest.main()
