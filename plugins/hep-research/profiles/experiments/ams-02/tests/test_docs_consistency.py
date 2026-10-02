"""Regression tests tying the profile's documentation to the code it describes (task Section 12)."""
import re
from datetime import date
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from contracts.legacy import yaml_subset as ys  # noqa: E402
from core.evidence import ledger as vel  # noqa: E402

ARTIFACTS = (ROOT / "modules" / "methods" / "analysis-artifacts.md").read_text(encoding="utf-8")

# one sample per feature the module says is rejected, with the line the error must name
REJECTED = {
    "Anchors": ("a: &x 1\n", 1), "aliases": ("a: *x\n", 1), "tags": ("a: !!str 1\n", 1),
    "multiple documents": ("a: 1\n---\nb: 2\n", 2), "multi-line flow": ("a: [1,\n  2]\n", 1),
    "quoted scalars": ('a: "one\n  two"\n', 1), "tab indentation": ("a:\n\tb: 1\n", 2), "duplicate keys": ("a: 1\na: 2\n", 2),
}
ACCEPTED = {"mappings": "a:\n  b: 1\n", "lists": "a:\n- 1\n- 2\n", "comments": "a: 1  # note\n",
            "one-line": "a: [1, 2]\nb: {c: 3}\n", "block scalars": "a: |\n  x\n  y\nb: >-\n  p\n  q\n"}


class YamlDocumentationTests(unittest.TestCase):
    """Section 12: the artifact docs denied YAML parsing although a strict subset is implemented."""

    def test_docs_no_longer_deny_yaml(self):
        self.assertNotIn("no YAML parser", ARTIFACTS)
        self.assertIn("strict subset", ARTIFACTS)

    def test_every_rejected_feature_named_in_the_docs_is_rejected_with_its_line(self):
        line = next(l for l in ARTIFACTS.splitlines() if l.startswith("A YAML specification is read with a strict subset"))
        for feature, (text, lineno) in REJECTED.items():
            self.assertIn(feature, line, feature)
            with self.assertRaises(ys.YamlSubsetError, msg=feature) as cm:
                ys.loads(text)
            self.assertTrue(str(cm.exception).startswith(f"line {lineno}:"), (feature, str(cm.exception)))

    def test_every_supported_feature_named_in_the_docs_parses(self):
        for feature, text in ACCEPTED.items():
            self.assertIsInstance(ys.loads(text), dict, feature)

    def test_strings_stay_strings(self):
        self.assertEqual(ys.loads("d: 2026-10-02\ny: yes\n"), {"d": "2026-10-02", "y": "yes"})


class NewerLiteratureTests(unittest.TestCase):
    """Section 12 / T17: newer or inaccessible literature is unverified, not nonexistent; the level read is kept."""

    POLICY = (ROOT / "modules" / "sources" / "source-policy.md").read_text(encoding="utf-8")

    def test_policy_classifies_newer_citations_as_unverified(self):
        self.assertNotIn("likely nonexistent", self.POLICY)
        line = next(l for l in self.POLICY.splitlines() if "after the verification date" in l)
        self.assertIn("unverified", line)
        self.assertIn("not as nonexistent", line)
        self.assertIn("level actually read", line)

    def test_a_newer_source_enters_the_ledger_at_the_level_read(self):
        sources, claims = vel.load_ledger(ROOT / "evidence" / "sources.json", ROOT / "evidence" / "claims.json")
        new = dict(sources[0], id="ams02:S61", legacy_id=None, title="A paper published after the last verification (test record)",
                   year=2026, year_text="2026", publication_date="2026-09-30", verification_level="metadata-only",
                   verification_note=None, verification_date="2026-10-02", data_taking_period=None,
                   supersedes=[], superseded_by=[], dois=[], locator_text="test")
        claim = dict(claims[0], id="ams02:C184", legacy_id=None, source_ids=["ams02:S61"], claim="test claim",
                     verification_strength="metadata-only", numeric_quotation_allowed=False)
        ok = vel.check_ledger(sources + [new], claims + [claim], date(2026, 10, 2), 365, "ams02")
        self.assertEqual(ok["status"], "pass", ok["errors"])
        over = dict(claim, verification_strength="full-text")
        bad = vel.check_ledger(sources + [new], claims + [over], date(2026, 10, 2), 365, "ams02")
        self.assertIn("claim.stronger_than_sources", {e["code"] for e in bad["errors"]})


class DateWordingTests(unittest.TestCase):
    """Section 12: fixed-date wording conflated the host date with the source verification date."""

    POLICY = (ROOT / "modules" / "sources" / "source-policy.md").read_text(encoding="utf-8")
    RULES = (ROOT / "modules" / "working-rules.md").read_text(encoding="utf-8")

    def test_three_dates_named_distinctly(self):
        for phrase in ("**current date**", "**publication date and data-taking period**", "**verification date**"):
            self.assertIn(phrase, self.POLICY)
        self.assertIn("Never present a verification date as today's date", self.POLICY)

    def test_no_single_fixed_verification_date_for_the_whole_ledger(self):
        for text in (self.POLICY, self.RULES):
            self.assertNotIn("post-2025", text)
            self.assertNotIn("as of the last verification, 2026-09-20", text)
            self.assertNotIn("skill's last verification", text)

    def test_ledger_rows_really_have_different_verification_dates(self):
        import json
        dates = {s["verification_date"] for s in json.loads((ROOT / "evidence" / "sources.json").read_text(encoding="utf-8"))}
        self.assertGreater(len(dates - {"unknown"}), 1)


if __name__ == "__main__":
    unittest.main()
