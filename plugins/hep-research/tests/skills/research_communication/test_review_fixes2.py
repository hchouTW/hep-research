"""Second audit of research-communication (RC-AUDIT-2, 2026-10-14): each checker defect reproduced as a regression.
All projects are the synthetic golden scenario of comm_fixtures; every number is a placeholder."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.research_communication import comm_fixtures as fx
from tests.skills.research_communication import test_adaptation as ta
from tests.skills.research_communication import test_terminology as tt

SCRIPTS = fx.PLUGIN / "skills" / "research-communication" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from communication_lib import numbers as N  # noqa: E402
from communication_lib.adaptation import _numbers  # noqa: E402
from communication_lib.audit import audit_communication  # noqa: E402
from communication_lib.claims import audit_claims  # noqa: E402
from contracts.communication_project import resolve_context  # noqa: E402

POLICY = SCRIPTS.parent / "assets" / "reporting-policies.json"


def codes(rep, severity=None):
    return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}


class Project(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")
        self.doc = fx.clone(self.p["doc"])

    def set_source(self, value):
        self.p["obs"].write_text(json.dumps(fx.observed_result(value)))
        self.doc["inputs"][0]["sha256"] = fx.sha(self.p["obs"])

    def set_c1_values(self, value, rounding="decimals:2"):
        for o in self.doc["extension"]["occurrences"]:
            if o["claim_id"] == "claim:C1":
                o["value"] = {"value": value, "unit": "1"}
                if rounding is not None:
                    o["value"]["rounding"] = rounding

    def save(self):
        fx.refresh_assessments(self.doc)
        fx.write(self.p["record"], self.doc)
        return resolve_context(self.p["record"], self.p["root"]), json.loads(self.p["record"].read_text())

    def manuscript(self):
        ctx, rec = self.save()
        return audit_communication(rec, ctx, checks="manuscript")

    def claims(self):
        ctx, rec = self.save()
        return audit_claims(rec, ctx, json.loads(POLICY.read_text(encoding="utf-8")))


class ReviewFixes2Numbers(unittest.TestCase):
    """RC-A2/A3: one number tokenizer for passages, records and drafts."""

    def test_tokens_at_sentence_end_next_to_cjk_signed_exponent_and_grouped(self):
        self.assertEqual(N.tokens("The ratio is 1.09."), ["1.09"])
        self.assertEqual(N.tokens("R為1.09（合成資料）"), ["1.09"])
        self.assertEqual(N.tokens("R = -0.50"), ["-0.50"])
        self.assertEqual(N.tokens("1.2e-3"), ["1.2e-3"])
        self.assertEqual(N.tokens("12,000 events"), ["12000"])
        self.assertEqual(N.tokens("R = 1.02 +/- 0.05"), ["1.02", "0.05"])
        self.assertEqual(N.tokens(r"$1.02 \pm 0.05$"), ["1.02", "0.05"])
        self.assertEqual(N.tokens("12\\,000 and 3{,}000 and −0.5"), ["12000", "3000", "-0.5"])
        self.assertEqual(N.tokens("claim C1 on x86, 2nd pass"), [])

    def test_adaptation_numbers_use_the_shared_tokenizer(self):
        self.assertEqual(_numbers("The ratio is 1.09."), {"1.09"})
        self.assertEqual(_numbers("R為1.09（合成資料）"), {"1.09"})
        self.assertEqual(_numbers("1.2e-3"), {"1.2e-3"})

    def test_contains_value_is_numeric_not_substring(self):
        self.assertFalse(N.contains_value("R = 1.02 +/- 0.05", "1.0"))
        self.assertTrue(N.contains_value("R = 1.020", "1.02"))


class ReviewFixes2ValueVsPassage(Project):
    """RC-A2: a displayed value absent from its located passage is an error in check_communication and audit_claims."""

    def test_record_value_disagreeing_with_manuscript_fails(self):
        for value in ("1.09", "1.0"):
            with self.subTest(value=value):
                self.setUp()
                self.set_source(value)
                self.set_c1_values(value)
                rep = self.manuscript()
                self.assertIn("occurrence.value_not_in_passage", codes(rep, "error"), rep["findings"])
                self.assertEqual(rep["exit_code"], 1)
                rep = self.claims()
                self.assertIn("occurrence.value_not_in_passage", codes(rep, "error"), rep["findings"])
                self.assertEqual(rep["exit_code"], 1)

    def test_unchanged_record_still_passes(self):
        self.assertEqual(self.manuscript()["exit_code"], 0)
        self.assertEqual(self.claims()["exit_code"], 0)


class ReviewFixes2Adaptation(ta.Base):
    """RC-A3: a 9.99 draft against a 1.02 record fails in English and Traditional Chinese."""

    def test_wrong_number_at_sentence_end_or_next_to_cjk_fails(self):
        for draft, st in [("In this sample the ratio is 9.99. The uncertainty quoted is statistical only. Synthetic fixture.",
                           "In this sample the ratio is 9.99."),
                          ("在此樣本中比值為9.99。統計不確定度（statistical only），synthetic fixture。", "在此樣本中比值為9.99")]:
            with self.subTest(draft=draft[:20]):
                man = ta.manifest(self.p["record"], statements=[{"id": "st:1", "text": st, "claim_ids": ["claim:C1"], "kind": "quantitative"}])
                rep = self.check(draft=draft, man=man)
                self.assertIn("adaptation.number_mismatch", self.codes(rep, "error"), rep["findings"])
                self.assertEqual(rep["exit_code"], 1)


class Manuscript(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_main(self, body, bib=None, *extra):
        import check_manuscript as cm
        bibline = "\\bibliography{refs}\n" if bib is not None else ""
        if bib is not None:
            self.write("refs.bib", bib)
        main = self.write("main.tex", "\\documentclass{article}\\begin{document}\n" + body + "\n" + bibline + "\\end{document}\n")
        out = io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            code = cm.main(["--main", str(main), "--format", "json", *[str(e) for e in extra]])
        rep = json.loads(out.getvalue())
        return code, rep

    @staticmethod
    def found(rep, code):
        return {f["message"] for f in rep["findings"] if f["code"] == code}


class ReviewFixes2Includes(Manuscript):
    """RC-A1: a brace-less \\input is followed; an unresolvable one leaves coverage incomplete."""

    def test_braceless_input_is_followed(self):
        self.write("sec1.tex", "See \\ref{nolabel} and \\cite{ghost}.\n")
        code, rep = self.run_main("\\input sec1", "@article{real, title={x}}\n")
        self.assertEqual(code, 1, rep)
        self.assertIn("ghost", self.found(rep, "manuscript.missing_bib_entry"))
        self.assertIn("nolabel", self.found(rep, "manuscript.undefined_ref"))

    def test_occurrence_region_with_braceless_input_is_not_followed(self):
        from communication_lib.documents import check_occurrence
        res = check_occurrence("\\section{Results}\n\\input sec1\n", "latex", {"locator": "section:Results", "passage": "R = 1.02"})
        self.assertEqual(res["outcome"], "include", res)

    def test_unresolvable_braceless_input_is_incomplete(self):
        code, rep = self.run_main("\\input nofile")
        self.assertEqual((code, rep["coverage"]), (3, "incomplete"), rep)


BIB = "@article{a, title={x}}\n@article{b, title={x}}\n@article{c, title={x}}\n@article{d, title={x}}\n"


class ReviewFixes2Citations(Manuscript):
    """RC-A4: citation commands, arguments, comments and .bib structure parsed as TeX and BibTeX read them."""

    def missing(self, body, bib=BIB, *extra):
        code, rep = self.run_main(body, bib, *extra)
        return code, self.found(rep, "manuscript.missing_bib_entry"), rep

    def test_capitalised_cite_commands(self):
        _, miss, _ = self.missing("\\Citet{x1} \\Cite{x2} \\Citeauthor{x3}", "")
        self.assertEqual(miss, {"x1", "x2", "x3"})

    def test_multicite_groups(self):
        _, miss, _ = self.missing("\\textcites{a}{xb} \\cites[p.~1]{c}[p.~2]{xd}")
        self.assertEqual(miss, {"xb", "xd"})

    def test_nested_optional_argument(self):
        _, miss, _ = self.missing("\\autocite[see][{p.~[3]}]{xa}")
        self.assertEqual(miss, {"xa"})

    def test_percent_inside_url_is_not_a_comment(self):
        _, miss, _ = self.missing("\\url{http://x/a%20b} \\cite{xa}")
        self.assertEqual(miss, {"xa"})

    def test_bib_entries_inside_fields_or_comments_are_not_entries(self):
        bib = "@article{real, note={see @misc{fake1, title={y}}}}\n@comment{@article{fake2, title={y}}}\n"
        _, miss, _ = self.missing("\\cite{fake1,fake2,real}", bib)
        self.assertEqual(miss, {"fake1", "fake2"})

    def test_iffalse_comment_environment_and_verb_are_not_scanned(self):
        body = ("\\iffalse \\cite{x1} \\label{l} \\fi\n\\begin{comment}\n\\cite{x2}\n\\end{comment}\n"
                "\\verb|\\cite{x3}| \\label{l}")
        code, miss, rep = self.missing(body)
        self.assertEqual(miss, set())
        self.assertEqual(self.found(rep, "manuscript.duplicate_label"), set())

    def test_crossref_parent_is_used(self):
        bib = "@inproceedings{child, crossref={parent}, title={x}}\n@proceedings{parent, title={y}}\n"
        code, rep = self.run_main("\\cite{child}", bib, "--strict")
        self.assertEqual(self.found(rep, "manuscript.unused_bib_entry"), set())
        self.assertEqual(code, 0, rep)


class ReviewFixes2Rounding(Project):
    """RC-A5, A6, A15: displays are checked against the source with or without a rule; round half up by default."""

    def test_no_rule_accepts_only_a_rounding_of_the_source(self):
        self.set_source("1.09")
        self.set_c1_values("1.02", rounding=None)
        rep = self.claims()
        self.assertIn("occurrence.value_mismatch", codes(rep, "error"))
        self.assertEqual(rep["exit_code"], 1)

    def test_no_rule_rounding_is_a_warning_only(self):
        from communication_lib.claims import _rounds_somehow
        from decimal import Decimal
        self.assertTrue(_rounds_somehow(Decimal("1.09"), Decimal("1.1")))
        self.assertFalse(_rounds_somehow(Decimal("1.09"), Decimal("1.02")))
        self.set_source("1.0237")
        self.set_c1_values("1.02", rounding=None)
        rep = self.claims()
        self.assertIn("occurrence.value_unrounded_comparison", codes(rep, "warning"))
        self.assertNotIn("occurrence.value_mismatch", codes(rep))

    def test_malformed_rule_is_an_error(self):
        for rule in ("decimals:x", "decimals:2:banker", "rounded:2", "decimals:999999"):
            with self.subTest(rule=rule):
                self.setUp()
                self.set_c1_values("1.02", rounding=rule)
                rep = self.claims()
                self.assertIn("occurrence.rounding_malformed", codes(rep, "error"), rep["findings"])
                self.assertEqual(rep["exit_code"], 1)

    def test_default_rounding_is_half_up_and_half_even_is_opt_in(self):
        from communication_lib.claims import _round
        self.assertEqual(_round("1.025", "decimals:2"), "1.03")
        self.assertEqual(_round("1.025", "decimals:2:half-even"), "1.02")
        self.assertEqual(_round("1.025", "significant:3:half-up"), "1.03")
        self.set_source("1.025")
        self.set_c1_values("1.02", rounding="decimals:2")
        self.assertIn("occurrence.value_mismatch", codes(self.claims(), "error"))
        self.setUp()
        self.set_source("1.025")
        self.set_c1_values("1.02", rounding="decimals:2:half-even")
        rep = self.claims()
        self.assertNotIn("occurrence.value_mismatch", codes(rep))
        self.assertEqual(rep["exit_code"], 0, rep["findings"])

    def test_non_finite_values_are_record_findings(self):
        for src, shown in (("Infinity", "1.02"), ("NaN", "NaN")):
            with self.subTest(src=src):
                self.setUp()
                self.set_source(src)
                self.set_c1_values(shown)
                rep = self.claims()
                self.assertIn("occurrence.value_not_finite", codes(rep, "error"), rep["findings"])
                self.assertEqual(rep["exit_code"], 1)


class ReviewFixes2Locators(unittest.TestCase):
    """RC-A8: section titles with nested braces, notation-normalized passages, headings inside fenced code."""

    def test_latex_section_title_with_nested_braces(self):
        from communication_lib.documents import check_occurrence
        tex = "\\section{Results at $\\sqrt{s}=13$~TeV}\nThe ratio is R = 1.02.\n\\section{Next}\nx\n"
        res = check_occurrence(tex, "latex", {"locator": "section:Results at $\\sqrt{s}=13$~TeV", "passage": "The ratio is R = 1.02."})
        self.assertEqual(res["outcome"], "located", res)

    def test_plus_minus_notations_match(self):
        from communication_lib.documents import check_occurrence
        tex = "\\section{Results}\nWe find $R = 1.02 \\pm 0.05$.\n"
        res = check_occurrence(tex, "latex", {"locator": "section:Results", "passage": "We find R = 1.02 \u00b1 0.05."})
        self.assertEqual(res["outcome"], "located", res)

    def test_heading_inside_fenced_code_is_not_a_section(self):
        from communication_lib.documents import check_occurrence
        md = "# Results\n\nR = 1.02.\n\n```bash\n# Results\necho\n```\n"
        res = check_occurrence(md, "markdown", {"locator": "section:Results", "passage": "R = 1.02."})
        self.assertEqual(res["outcome"], "located", res)


class ReviewFixes2ManuscriptBounds(Manuscript):
    """RC-A7 --bbl inside the project root; RC-A9 linear scan time; RC-A18 --strict with incomplete coverage."""

    def test_bbl_outside_project_root_is_an_input_error(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        bbl = outside / "main.bbl"
        bbl.write_text("\\bibitem{a} x\n", encoding="utf-8")
        code, rep = self.run_main("\\cite{a}", None, "--bbl", bbl)
        self.assertEqual(code, 2, rep)
        inside = self.write("main.bbl", "\\bibitem{a} x\n")
        code, rep = self.run_main("\\cite{a}", None, "--bbl", inside)
        self.assertEqual(code, 0, rep)

    def test_scan_time_is_linear_in_lines(self):
        import time
        import check_manuscript as cm

        def timed(n):
            body = "".join(f"\\cite{{k{i}}} \\label{{l{i}}} \\ref{{l{i}}}\n" for i in range(n))
            f = self.write(f"m{n}.tex", body)
            t0 = time.perf_counter()
            cm.scan_files([f], [])
            return time.perf_counter() - t0
        small, large = timed(5000), timed(20000)
        self.assertLess(large, 5.0)
        self.assertLess(large / max(small, 1e-3), 8.0, f"5k lines {small:.2f} s, 20k lines {large:.2f} s: not linear")

    def test_strict_unused_entries_are_incomplete_when_coverage_is(self):
        code, rep = self.run_main("\\cite{a} \\input missing", "@article{a, title={x}}\n@article{b, title={x}}\n", "--strict")
        self.assertEqual(code, 3, rep)
        self.assertEqual({f["severity"] for f in rep["findings"] if f["code"] == "manuscript.unused_bib_entry"}, {"unresolved"})
        code, rep = self.run_main("\\cite{a}", "@article{a, title={x}}\n@article{b, title={x}}\n", "--strict")
        self.assertEqual(code, 1, rep)


class ReviewFixes2Chinese(Project):
    """RC-A10: status wording in Traditional Chinese gives the same finding as its English twin."""

    def wording(self, text):
        c1 = self.doc["extension"]["claims"][0]
        c1["text"], c1["status"] = text, ["synthetic"]
        return codes(self.claims(), "warning")

    def test_status_promotion_in_both_languages(self):
        self.assertIn("wording.status_promotion", self.wording("We measured the ratio R = 1.02 in data."))
        self.setUp()
        self.assertIn("wording.status_promotion", self.wording("我們在資料中測量到比值 R 為 1.02。"))

    def test_negated_chinese_sentence_is_not_a_promotion(self):
        self.assertNotIn("wording.status_promotion", self.wording("我們並未在資料中測量到比值 R。"))


class ReviewFixes2ChineseTerminology(tt.Base):
    """RC-A10: notation and abbreviation definitions in Traditional Chinese."""

    def test_conflicting_symbol_definitions_in_one_section(self):
        en = self.run_check("# Results\n\nR denotes the flux ratio.\n\nR denotes the rigidity.\n")
        zh = self.run_check("# Results\n\nR 表示通量比。\n\nR 表示剛度。\n")
        self.assertIn("terminology.conflicting_definitions", self.codes(en, "error"))
        self.assertIn("terminology.conflicting_definitions", self.codes(zh, "error"))

    def test_chinese_abbreviation_definition_counts(self):
        rep = self.run_check("# Results\n\n我們使用信賴水準（CL）表示區間。\n\n此處 CL 為 95%。\n")
        self.assertNotIn("terminology.abbreviation_undefined", self.codes(rep))
        rep = self.run_check("# Results\n\n此處 CL 為 95%。\n")
        self.assertIn("terminology.abbreviation_undefined", self.codes(rep))


class ReviewFixes2LabelWords(unittest.TestCase):
    """RC-A13: status words are matched as words; NEGATED_RE no longer fires on every 未."""

    def test_status_word_boundaries(self):
        from communication_lib.adaptation import NEGATED_RE, _has_label
        self.assertTrue(_has_label("a synthetic sample", "synthetic"))
        self.assertTrue(_has_label("R為1.09（合成資料）", "合成"))
        self.assertFalse(_has_label("a non-synthetic sample", "synthetic"))
        self.assertFalse(_has_label("the sample is not synthetic", "synthetic"))
        self.assertFalse(_has_label("非合成樣本", "合成"))
        self.assertTrue(_has_label("未經驗證的結果", "未經驗證"))
        self.assertIsNone(NEGATED_RE.search("結果未驗證"))
        self.assertIsNotNone(NEGATED_RE.search("we have not yet rerun it"))


class ReviewFixes2SmallClis(unittest.TestCase):
    """RC-A14 --today must be a date; RC-A16 build_lit_matrix never overwrites its input."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def call(self, module, *args):
        mod = __import__(module)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = mod.main([str(a) for a in args])
        return code, out.getvalue() + err.getvalue()

    def test_today_must_be_a_date(self):
        inp = self.tmp / "in.json"
        inp.write_text("{}", encoding="utf-8")
        code, out = self.call("manage_literature", "import", inp, "--project-root", self.tmp, "--out", self.tmp / "o.json", "--today", "notadate")
        self.assertEqual(code, 2, out)
        self.assertIn("notadate", out)

    def test_matrix_output_cannot_alias_input(self):
        csv_path = self.tmp / "n.csv"
        csv_path.write_text("key,year\na,2020\n", encoding="utf-8")
        code, out = self.call("build_lit_matrix", csv_path, "-o", csv_path)
        self.assertEqual(code, 2, out)
        self.assertEqual(csv_path.read_text(encoding="utf-8"), "key,year\na,2020\n")


class ReviewFixes2TerminologyEdges(tt.Base):
    """RC-A17: a disallowed CJK term inside a declared term is not flagged; a use before the definition on the same
    line is."""

    def test_disallowed_part_of_a_declared_term(self):
        import copy
        g = copy.deepcopy(tt.GLOSSARY)
        g["entries"].append({"id": "term:reco-eff", "concept": "reconstruction efficiency", "preferred": {"zh-Hant": "重建效率"},
                             "aliases": {}, "definition": "fraction of accepted events reconstructed", "abbreviations": [], "disallowed": []})
        rep = self.run_check("# 偵測器\n\n幾何區域內的重建效率為 0.9。\n", glossary=g)
        self.assertNotIn("terminology.concept_substitution", self.codes(rep))
        rep = self.run_check("# 偵測器\n\n我們量測了偵測器的幾何效率。\n", glossary=g)
        self.assertIn("terminology.concept_substitution", self.codes(rep))

    def test_use_before_definition_on_the_same_line(self):
        rep = self.run_check("# Results\n\nThe CL is 95%, a confidence interval (CL) construction.\n")
        self.assertIn("terminology.abbreviation_undefined", self.codes(rep))
        rep = self.run_check("# Results\n\nA confidence interval (CL) at 95% CL.\n")
        self.assertNotIn("terminology.abbreviation_undefined", self.codes(rep))


if __name__ == "__main__":
    unittest.main()
