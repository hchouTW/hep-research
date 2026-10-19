"""Runs the static routing check (tools/check_routing_static.py) as part of the test suite."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class StaticRoutingTests(unittest.TestCase):
    def test_descriptions_cover_every_case(self):
        p = subprocess.run([sys.executable, str(ROOT / "tools" / "check_routing_static.py")], capture_output=True, text=True, timeout=600)
        rep = json.loads(p.stdout)
        self.assertEqual(p.returncode, 0, rep)
        self.assertGreaterEqual(rep["cases"], 7 * 3 + 12)

    def test_cases_file_is_generated_from_the_table(self):
        # compare without rewriting the tracked file, so a hand edit to cases.json fails every run
        generated = subprocess.run([sys.executable, str(ROOT / "tests" / "routing" / "make_cases.py"), "--stdout"],
                                   check=True, capture_output=True, timeout=600).stdout
        self.assertEqual((ROOT / "tests" / "routing" / "cases.json").read_bytes(), generated)


    def test_unpinned_phrase_report(self):
        # a report, not a failure: phrases no trigger term or description-topics entry overlaps
        sys.path.insert(0, str(ROOT / "tools"))
        import check_routing_static as crs
        d = {"s": {"use": "use when x: alpha beta, gamma delta (epsilon), pinned phrase here. ", "not_for": "", "body": ""}}
        cases = [{"expected_primary": "s", "trigger_terms": ["Pinned phrase"]},
                 {"expected_primary": "other", "trigger_terms": ["alpha beta"]},
                 {"expected_primary": "x", "turns": [{"expected": "s", "trigger_terms": ["epsilon"]}]}]
        rep = crs.unpinned_phrases(d, cases, {"s": ["gamma"]})
        self.assertEqual(rep["s"]["phrases"], ["use when x", "alpha beta"])
        self.assertEqual(rep["s"]["chars"], len("use when x") + len("alpha beta"))
        p = subprocess.run([sys.executable, str(ROOT / "tools" / "check_routing_static.py")], capture_output=True, text=True, timeout=600)
        full = json.loads(p.stdout)["unpinned_phrases"]
        self.assertEqual(set(full), set(crs.SKILLS))


class LanguageIndependenceSTH46(unittest.TestCase):
    """STH-T4.6: natural non-English prompts need no English trigger terms; they may not quote the description; the
    owned topics listed in docs/routing-contract.md must stay named in the description."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "tools"))
        import check_routing_static as crs
        cls.crs = crs
        cls.cases = json.loads((ROOT / "tests" / "routing" / "cases.json").read_text(encoding="utf-8"))["cases"]

    def test_natural_zh_hant_statistics_cases(self):
        nat = [c for c in self.cases if c.get("natural") and c["lang"] == "zh-Hant" and c["expected_primary"] == "hep-statistics"]
        self.assertGreaterEqual(len(nat), 5)
        desc = self.crs.descriptions()["hep-statistics"]["use"]
        for c in nat:
            self.assertIsNone(self.crs.reused_ngram(c["prompt"], desc), c["id"])
            self.assertEqual(c["trigger_terms"], [])

    def test_reuse_is_detected(self):
        desc = self.crs.descriptions()["hep-statistics"]["use"]
        self.assertEqual(self.crs.reused_ngram("請做 combinations across datasets or experiments。", desc),
                         "combinations across datasets or")
        self.assertIsNone(self.crs.reused_ngram("combinations across datasets", desc))   # three words are allowed

    def test_removing_a_topic_from_the_description_fails(self):
        from unittest import mock
        real = self.crs.descriptions()

        def without_unfolding():
            d = {k: dict(v) for k, v in real.items()}
            d["hep-statistics"]["use"] = d["hep-statistics"]["use"].replace("unfolding", "")
            return d
        import contextlib
        import io
        with mock.patch.object(self.crs, "descriptions", without_unfolding), contextlib.redirect_stdout(io.StringIO()) as buf:
            code = self.crs.main()
        rep = json.loads(buf.getvalue())
        self.assertEqual(code, 1)
        self.assertIn("hep-statistics: topic 'unfolding' is not named in its description", rep["topic_errors"])

    def test_topics_table_is_read(self):
        topics = self.crs.description_topics()
        self.assertIn("folded prediction", topics["hep-statistics"])

    def test_gap_cases_and_j05_fit_half(self):
        ids = {c["id"]: c for c in self.cases}
        for cid in ("st-t46-ratio-1", "st-t46-break-1", "st-t46-bump-1", "st-t46-comb-1"):
            self.assertEqual(ids[cid]["expected_primary"], "hep-statistics")
        self.assertEqual(ids["j05-turn-fit"]["turns"][0]["expected"], "hep-statistics")


if __name__ == "__main__":
    unittest.main()
