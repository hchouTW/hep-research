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


if __name__ == "__main__":
    unittest.main()
