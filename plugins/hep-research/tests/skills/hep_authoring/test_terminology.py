"""check_terminology.py and communication_lib.terminology (plan T9): glossary-driven, context-scoped terminology and
notation findings over the record's documents; lexical variation is not a contradiction. All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.hep_authoring import comm_fixtures as fx

SCRIPTS = fx.PLUGIN / "skills" / "hep-authoring" / "scripts"
sys.path.insert(0, str(SCRIPTS))
GLOSSARY_TEMPLATE = SCRIPTS.parent / "assets" / "paper" / "glossary-template.json"

try:
    from communication_lib.terminology import check_terminology, load_glossary
    from contracts.communication_project import resolve_context
    import check_terminology as cli
except ImportError:
    check_terminology = load_glossary = resolve_context = cli = None

GLOSSARY = {
    "glossary_version": "1.0.0",
    "entries": [
        {"id": "term:acceptance", "concept": "geometric acceptance", "preferred": {"en": "acceptance", "zh-Hant": "接受度"},
         "aliases": {"en": ["geometric acceptance"], "zh-Hant": ["幾何接受度"]}, "definition": "the fraction of generated events inside the detector's geometry",
         "abbreviations": [], "scope": "detector",
         "disallowed": [{"term": "efficiency", "when_near": ["geometric", "geometry"], "reason": "efficiency is the fraction of accepted events that are reconstructed; not interchangeable with acceptance"},
                        {"term": "效率", "when_near": ["幾何"], "reason": "效率 (efficiency) 與 接受度 (acceptance) 不可互換"}]},
        {"id": "term:resolution", "concept": "resolution", "preferred": {"en": "resolution"}, "aliases": {"en": []}, "definition": "the width of the response",
         "abbreviations": [], "scope": "detector",
         "disallowed": [{"term": "precision", "when_near": ["detector", "energy", "momentum"], "reason": "resolution is a detector property; precision describes a measurement's uncertainty"}]},
        {"id": "term:confidence-interval", "concept": "frequentist interval", "preferred": {"en": "confidence interval"}, "aliases": {"en": ["CL interval"]},
         "definition": "a frequentist interval with stated coverage", "abbreviations": ["CL"], "scope": "statistics",
         "disallowed": [{"term": "credible", "when_near": ["CLs", "frequentist", "confidence level", "coverage"], "reason": "a credible interval is Bayesian; a frequentist construction gives a confidence interval"}]},
        {"id": "term:charge-sign-ratio", "concept": "charge-sign ratio", "preferred": {"en": "charge-sign ratio"}, "aliases": {"en": []}, "definition": "ratio of the positive to the negative flux",
         "abbreviations": ["CSR"], "scope": "analysis", "disallowed": []}
    ],
    "notation": [
        {"symbol": "R", "definition": "the flux ratio", "scope": "section:Results"},
        {"symbol": "R", "definition": "the rigidity", "scope": "section:Detector"}
    ]
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")
        self.doc = fx.clone(self.p["doc"])

    def run_check(self, text, fmt="markdown", glossary=None, extra_docs=()):
        self.assertIsNotNone(check_terminology, "communication_lib.terminology does not exist")
        self.p["paper"].write_text(text, encoding="utf-8")
        self.doc["extension"]["documents"][0]["format"] = fmt
        for did, rel, body in extra_docs:
            fx.write(self.p["root"] / rel, body)
            self.doc["extension"]["documents"].append({"id": did, "path": rel, "format": "markdown"})
        fx.write(self.p["record"], self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        return check_terminology(json.loads(self.p["record"].read_text()), ctx, glossary or GLOSSARY)

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    @staticmethod
    def by_code(rep, code):
        return [f for f in rep["findings"] if f["code"] == code]


class ConceptSubstitutions(Base):
    def test_translation_confuses_acceptance_and_efficiency(self):
        rep = self.run_check("# 偵測器\n\n我們量測了偵測器的幾何效率，並與模擬比較。\n\n## Results\n\n觸發效率為 0.9。\n")
        f = self.by_code(rep, "terminology.concept_substitution")
        self.assertEqual(len(f), 1, rep["findings"])
        self.assertEqual(f[0]["rule"], "term:acceptance")
        self.assertIn("doc:paper", f[0]["location"])
        self.assertIn("line 3", f[0]["location"])
        self.assertIn("幾何效率", f[0]["message"])
        self.assertIn("接受度", f[0]["suggested_action"])
        self.assertEqual(f[0]["severity"], "warning", "contextual: a reader decides")
        self.assertEqual(rep["status"], "pass")

    def test_english_variant_and_unrelated_use(self):
        rep = self.run_check("# Detector\n\nThe geometric efficiency of the tracker is 92%. The trigger efficiency is 0.9.\n")
        f = self.by_code(rep, "terminology.concept_substitution")
        self.assertEqual(len(f), 1)
        self.assertIn("geometric efficiency", f[0]["message"])

    def test_precision_vs_resolution_and_confidence_vs_credible(self):
        rep = self.run_check("# Detector\n\nThe energy precision of the calorimeter is 2%.\n\n## Statistics\n\n"
                             "We quote a 95% credible interval from the CLs construction. The value is measured with a precision of 1%.\n")
        rules = sorted(f["rule"] for f in self.by_code(rep, "terminology.concept_substitution"))
        self.assertEqual(rules, ["term:confidence-interval", "term:resolution"])

    def test_quoted_terminology_is_not_flagged(self):
        rep = self.run_check('# Detector\n\nRef. [3] reports the so-called "geometric efficiency" of their setup; we use the acceptance instead.\n')
        self.assertEqual(self.by_code(rep, "terminology.concept_substitution"), [])

    def test_bilingual_variants_with_equivalent_meaning_are_fine(self):
        rep = self.run_check("# 偵測器\n\n接受度與幾何接受度在本文中同義；the acceptance is 0.3 (synthetic fixture).\n")
        self.assertEqual(rep["findings"], [])
        self.assertTrue(any(n["code"] == "terminology.alias_used" for n in rep["notes"]))


class NotationAndAbbreviations(Base):
    def test_scoped_symbol_reuse_is_distinguished_from_drift(self):
        rep = self.run_check("# Detector\n\nHere R denotes the rigidity of the particle.\n\n## Results\n\nHere R denotes the flux ratio.\n")
        self.assertEqual(self.by_code(rep, "terminology.conflicting_definitions"), [])
        rep = self.run_check("# Results\n\nHere R denotes the flux ratio.\n\nLater, R denotes the rigidity.\n")
        f = self.by_code(rep, "terminology.conflicting_definitions")
        self.assertEqual(len(f), 1)
        self.assertIn("line 3", f[0]["location"])
        self.assertIn("line 5", f[0]["location"])
        self.assertEqual(f[0]["severity"], "error")

    def test_definition_outside_declared_scope_is_for_review(self):
        rep = self.run_check("# Appendix\n\nHere R denotes the radius.\n")
        f = self.by_code(rep, "terminology.definition_undeclared")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["severity"], "warning")
        self.assertIn("section:Appendix", f[0]["message"])

    def test_abbreviation_redefined_and_used_before_definition(self):
        rep = self.run_check("# Intro\n\nThe CSR rises with energy.\n\n## Method\n\nWe define the charge-sign ratio (CSR) as the ratio of fluxes.\n\n"
                             "## Discussion\n\nThe cosmic-ray spectrum (CSR) is steep.\n")
        self.assertEqual(len(self.by_code(rep, "terminology.abbreviation_redefined")), 1)
        f = self.by_code(rep, "terminology.abbreviation_redefined")[0]
        self.assertIn("charge-sign ratio", f["message"])
        self.assertIn("cosmic-ray spectrum", f["message"])
        self.assertEqual(len(self.by_code(rep, "terminology.abbreviation_undefined")), 1)
        self.assertIn("line 3", self.by_code(rep, "terminology.abbreviation_undefined")[0]["location"])

    def test_latex_document_and_second_document(self):
        tex = "\\documentclass{article}\\begin{document}\n\\section{Detector}\nThe geometric efficiency is 92\\%. % comment with geometric efficiency\n\\end{document}\n"
        rep = self.run_check(tex, fmt="latex", extra_docs=[("doc:talk", "talk/slides.md", "# Slides\n\nenergy precision of 2%\n")])
        subs = self.by_code(rep, "terminology.concept_substitution")
        self.assertEqual(sorted(f["location"].split(" ")[0] for f in subs), ["doc:paper", "doc:talk"])
        self.assertEqual(rep["coverage"]["documents"], {"declared": 2, "scanned": 2})


class Glossary(Base):
    def test_template_glossary_loads(self):
        g = load_glossary(GLOSSARY_TEMPLATE)
        self.assertEqual(g["glossary_version"], "1.0.0")
        self.assertTrue(all({"id", "concept", "preferred", "definition", "disallowed"} <= set(e) for e in g["entries"]))
        self.assertTrue(any("zh-Hant" in e["preferred"] for e in g["entries"]))

    def test_invalid_glossary_is_rejected(self):
        with self.assertRaises(ValueError):
            load_glossary(fx.write(self.tmp / "bad.json", {"entries": "no"}))

    def test_no_documents_is_unresolved(self):
        self.doc["extension"]["documents"] = []
        self.doc["extension"]["occurrences"] = []
        fx.write(self.p["record"], self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        rep = check_terminology(json.loads(self.p["record"].read_text()), ctx, GLOSSARY)
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("terminology.no_documents", self.codes(rep, "unresolved"))
        self.assertIn("semantic", rep["note"].lower())


class Cli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_json_markdown_and_exit_codes(self):
        self.p["paper"].write_text("# Results\n\nHere R denotes the flux ratio.\n\nLater, R denotes the rigidity.\n")
        fx.write(self.p["record"], self.doc)
        g = fx.write(self.tmp / "glossary.json", GLOSSARY)
        code, out, err = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--glossary", g)
        self.assertEqual(code, 1, out + err)
        self.assertEqual(json.loads(out)["tool"], "check_terminology")
        code, out, _ = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--glossary", g, "--format", "markdown")
        self.assertTrue(out.startswith("# check_terminology"))
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--glossary", self.tmp / "nope.json")[0], 2)
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--glossary", g, "--out", g)[0], 2)
        before = {p: p.read_bytes() for p in self.p["root"].rglob("*") if p.is_file()}
        self.run_cli(self.p["record"], "--project-root", self.p["root"], "--glossary", g)
        self.assertEqual({p: p.read_bytes() for p in self.p["root"].rglob("*") if p.is_file()}, before)


if __name__ == "__main__":
    unittest.main()


class ReviewFixes(Base):
    """Final review of the branch: I6, false confirmed errors on correct text."""

    def test_abbreviation_expansion_takes_only_the_expansion_words(self):
        rep = self.run_check("# Method\n\nWe train a boosted decision tree (BDT) on the sample. Later the boosted decision tree (BDT) output is cut.\n",
                             glossary={"glossary_version": "1.0.0", "entries": [{"id": "term:bdt", "concept": "boosted decision tree", "preferred": {"en": "boosted decision tree"},
                                                                                "aliases": {}, "definition": "x", "abbreviations": ["BDT"], "disallowed": []}]})
        self.assertEqual(self.by_code(rep, "terminology.abbreviation_redefined"), [])
        rep = self.run_check("# Method\n\nWe train a boosted decision tree (BDT). The binned data table (BDT) is separate.\n",
                             glossary={"glossary_version": "1.0.0", "entries": [{"id": "term:bdt", "concept": "boosted decision tree", "preferred": {"en": "boosted decision tree"},
                                                                                "aliases": {}, "definition": "x", "abbreviations": ["BDT"], "disallowed": []}]})
        f = self.by_code(rep, "terminology.abbreviation_redefined")
        self.assertEqual(len(f), 1)
        self.assertIn("'boosted decision tree'", f[0]["message"])
        self.assertIn("'binned data table'", f[0]["message"])

    def test_assignments_are_not_definitions(self):
        rep = self.run_check("# Results\n\nWe find R = 1.02 +/- 0.05. The illustration gives R = 0.98.\n")
        self.assertEqual(self.by_code(rep, "terminology.conflicting_definitions"), [])
