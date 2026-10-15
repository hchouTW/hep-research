"""hep-communication plan T4: the main skill and its references agree on task ownership and evidence semantics.
Textual regressions over the shipped Markdown: they pin the routing sentences a reader acts on, not prose style."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "hep-communication"
REF = SKILL / "references"


def text(name: str) -> str:
    return (REF / name).read_text(encoding="utf-8")


def flat(name: str) -> str:
    """One line per bullet: wrapped Markdown lines joined, so a sentence can be matched across a line break."""
    return re.sub(r"\n(?![-\d#])", " ", text(name))


class CodeReviewHandoffs(unittest.TestCase):
    def test_routes_by_question_not_by_library(self):
        t = flat("code-review-report.md")
        self.assertNotRegex(t, r"ROOT/PyROOT/RDataFrame or uproot/awkward columnar analysis code — invoke\s+`hep-measurement` for cutflow logic, statistical treatment",
                            "statistical treatment is not hep-measurement's")
        for skill, topic in (("hep-computing", r"implementation|I/O|performance"), ("hep-statistics", r"statistical"),
                             ("hep-measurement", r"measurement design|selection|corrections"), ("hep-ml", r"ML"),
                             ("hep-theory", r"theor"), ("hep-detector", r"detector response|calibration")):
            with self.subTest(skill=skill):
                self.assertRegex(t, rf"(?i)`{skill}`[^\n]*({topic})|({topic})[^\n]*`{skill}`")
        self.assertRegex(t, r"(?i)by (the )?(actual )?question", "routing is by the question asked")

    def test_papers_guide_routes_execution_to_computing(self):
        t = flat("academic-papers-guide.md")
        self.assertNotIn("hand execution to `hep-measurement`/`hep-ml`", t)
        self.assertRegex(t, r"Reproducibility auditing[^\n]*`hep-computing`")
        self.assertRegex(t, r"Code review report[^\n]*`hep-computing`")


class EvidenceTerminology(unittest.TestCase):
    def test_significance_language_is_scoped(self):
        t = flat("scientific-style.md")
        self.assertRegex(t, r"(?i)significance language[\s\S]{0,900}(applies|apply) (only )?to", "the table states its scope")
        self.assertRegex(t, r"(?i)(evidence)[^\n]*(citation|source|support)[^\n]*(not|never)[^\n]*(threshold|σ|sigma)",
                         "the everyday sense of 'evidence' carries no sigma threshold")
        g = text("academic-papers-guide.md")
        self.assertRegex(g, r"(?i)\*\*Calibrate claims to the evidence\.\*\*[\s\S]{0,700}(source's own community|field convention)")


class LiteratureReuse(unittest.TestCase):
    def test_reusing_verified_records_keeps_their_dates(self):
        t = text("citation-verification.md")
        self.assertRegex(t, r"(?i)## Reusing (a )?(previously )?verified")
        for phrase in ("verification date", "read level", "locator", "never", "new read"):
            self.assertIn(phrase, t.lower().replace("verification_date", "verification date"))
        self.assertRegex(t, r"(?i)time-sensitive|latest|current")


class ReviewerResponses(unittest.TestCase):
    def test_response_wording_follows_completion_state(self):
        t = flat("submission-and-peer-review.md")
        self.assertRegex(t, r"(?i)we have (changed|revised|added)[^\n]*(only|requires|completed)")
        self.assertRegex(t, r"(?i)(pending|planned|not (yet )?happened)[^\n]*(rerun|re-run|stays|remain|explicit)")
        self.assertIn("revision-impact-tracking.md", t)


class SkillHandoffTable(unittest.TestCase):
    def test_skill_handoff_table_agrees_with_references(self):
        s = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        rows = dict(re.findall(r"^\| ([^|]+?) \| ([a-z-]+) \|", s, re.M))
        self.assertEqual(rows.get("Code or scripts behind a figure or table"), "hep-computing")
        self.assertEqual(rows.get("Statistical wording of a claim"), "hep-statistics")
        self.assertEqual(rows.get("Measurement design or selection behind a claim"), "hep-measurement")


if __name__ == "__main__":
    unittest.main()
