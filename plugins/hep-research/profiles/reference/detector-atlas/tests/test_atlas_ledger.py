"""Tests of the shipped detector-atlas ledger: core/evidence/ledger.py passes, the evidence index is in sync, every
claim carries a complete atlas block with an allowed kind, and coverage matches index.md (six experiments, about ten
claims each, no AMS-02 claim). Run from the profile folder: python3 -m unittest discover -s tests -t tests -v"""
import json
import re
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))
from core.evidence import ledger as vel  # noqa: E402
from core.evidence import render_index as rsi  # noqa: E402

NS = "detector-atlas"
SOURCES, CLAIMS, INDEX = (ROOT / "evidence" / n for n in ("sources.json", "claims.json", "index.md"))
FIELDS = ("experiment", "subsystem", "quantity", "value", "unit", "kind", "valid_for", "conditions")
KINDS = {"design", "achieved", "operating"}


def load():
    return vel.load_ledger(SOURCES, CLAIMS)


class AtlasLedger(unittest.TestCase):
    def test_ledger_passes_at_its_latest_verification_date(self):
        sources, claims = load()
        today = max(date.fromisoformat(s["verification_date"]) for s in sources)
        rep = vel.check_ledger(sources, claims, today, 365, NS)
        self.assertEqual(rep["status"], "pass", rep["errors"] + rep["warnings"])

    def test_index_in_sync(self):
        sources, claims = load()
        self.assertEqual(rsi.check_index(INDEX.read_text(encoding="utf-8"), sources, claims)[0], True)

    def test_atlas_blocks(self):
        _, claims = load()
        for c in claims:
            with self.subTest(claim=c["id"]):
                a = c["atlas"]
                self.assertEqual(set(a), set(FIELDS))
                self.assertIn(a["kind"], KINDS)
                for k in ("experiment", "subsystem", "quantity", "value", "unit", "valid_for"):
                    self.assertTrue(isinstance(a[k], str) and a[k].strip(), k)
                self.assertEqual(c["verification_strength"], "full-text")

    def test_coverage_matches_the_index(self):
        _, claims = load()
        counts = Counter(c["atlas"]["experiment"] for c in claims)
        text = (ROOT / "index.md").read_text(encoding="utf-8")
        for exp, n in counts.items():
            self.assertGreaterEqual(n, 9, exp)
            name = "Super-Kamiokande" if exp == "Super-K" else exp
            self.assertRegex(text, rf"\| {re.escape(name)} \| {n} \|")
        self.assertEqual(len(counts), 6)
        self.assertNotIn("AMS-02", counts)

    def test_values_appear_in_the_claim_sentence(self):
        """A guard against transcription slips: each numeric token of the value occurs in the claim sentence."""
        _, claims = load()
        for c in claims:
            for token in re.findall(r"\d+(?:\.\d+)?", c["atlas"]["value"]):
                with self.subTest(claim=c["id"], token=token):
                    self.assertIn(token, c["claim"].replace(" ", "").replace(",", "") + c["claim"])


if __name__ == "__main__":
    unittest.main()
