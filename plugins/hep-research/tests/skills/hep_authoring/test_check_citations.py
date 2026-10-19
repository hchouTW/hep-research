"""check_citations.py (restructuring plan G3, hep-authoring invariant "never cites from memory"): each citation of a draft
is matched to a hep-citations record or a profile evidence ledger by identifier, then by stored citation key; a
citation found nowhere is not-verified (exit 3), one found everywhere passes (exit 0). All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-authoring" / "scripts"))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-citations" / "scripts"))

import check_citations as cc  # noqa: E402
import manage_literature  # noqa: E402
from tests.skills.hep_citations.test_literature_lifecycle import source  # noqa: E402

BIB = """@article{Fix:2026a,
  author = "Fixture, A.",
  title = {{A synthetic fixture paper}},
  doi = "10.0000/fixture.1",
  eprint = "2610.00001",
  archivePrefix = "arXiv",
  year = "2026"
}
@article{Ghost:2026zz,
  title = {{A paper nobody recorded}},
  doi = "10.0000/ghost",
  year = "2026"
}
"""
TEX = r"""\documentclass{article}
\begin{document}
The fixture value is quoted from \cite{Fix:2026a}.
% \cite{Commented:2026} is a comment, not a citation
A second claim rests on \citep[see][Sec.~2]{Ghost:2026zz}.
\bibliography{refs}
\end{document}
"""


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cc.main([str(a) for a in args])
    return code, out.getvalue(), err.getvalue()


class CheckCitations(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "refs.bib").write_text(BIB, encoding="utf-8")
        (self.tmp / "paper.tex").write_text(TEX, encoding="utf-8")
        inp = self.tmp / "lit.json"
        inp.write_text(json.dumps({"sources": [source("lit:S01", "A synthetic fixture paper", doi="10.0000/fixture.1",
                                                      arxiv="2610.00001v1", level="page")]}), encoding="utf-8")
        self.record = self.tmp / "record.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(manage_literature.main(["import", str(inp), "--project-root", str(self.tmp), "--out", str(self.record),
                                                     "--today", "2026-10-19"]), 0)

    def report(self, *args):
        code, out, err = run(*args)
        return code, json.loads(out)

    def test_found_and_missing(self):
        code, rep = self.report(self.tmp / "paper.tex", self.tmp / "refs.bib", "--record", self.record)
        self.assertEqual((code, rep["status"]), (3, "incomplete"))
        rows = {r["citation"]: r for r in rep["citations"]}
        self.assertEqual(set(rows), {"Fix:2026a", "Ghost:2026zz"}, "a commented-out \\cite is not a citation")
        self.assertEqual((rows["Fix:2026a"]["status"], rows["Fix:2026a"]["matched_by"], rows["Fix:2026a"]["read_level"]),
                         ("found", "identifier", "page"))
        self.assertEqual(rows["Ghost:2026zz"]["status"], "not-verified")
        missing = [f for f in rep["findings"] if f["code"] == "citation.not_verified"]
        self.assertEqual([(f["severity"], f["location"]) for f in missing], [("unresolved", "paper.tex:5")])

    def test_all_found_passes(self):
        tex = self.tmp / "only.tex"
        tex.write_text(r"Quoted from \cite{Fix:2026a}.", encoding="utf-8")
        code, rep = self.report(tex, self.tmp / "refs.bib", "--record", self.record)
        self.assertEqual((code, rep["status"], rep["counts_citations"]["not_verified"]), (0, "pass", 0))

    def test_no_record_means_nothing_is_verified(self):
        code, rep = self.report(self.tmp / "paper.tex", self.tmp / "refs.bib")
        self.assertEqual(code, 3)
        self.assertEqual({r["status"] for r in rep["citations"]}, {"not-verified"})

    def test_ledger_by_identifier_and_markdown_bare_ids(self):
        ledger = self.tmp / "sources.json"
        ledger.write_text(json.dumps([{"id": "x:S01", "title": "Ledger paper", "verification_level": "metadata-only",
                                       "verification_date": "2026-09-20", "dois": [], "arxiv_ids": ["2611.00002v3"],
                                       "inspire_record_id": None}]), encoding="utf-8")
        md = self.tmp / "draft.md"
        md.write_text("As shown in arXiv:2611.00002v2 and [@Fix:2026a], see also doi:10.0000/unknown.\n", encoding="utf-8")
        code, rep = self.report(md, self.tmp / "refs.bib", "--ledger", ledger, "--record", self.record)
        rows = {r["citation"]: r for r in rep["citations"]}
        self.assertEqual(rows["2611.00002v2"]["source_id"], "x:S01")
        self.assertEqual(rows["Fix:2026a"]["source_id"], "lit:S01")
        self.assertEqual(rows["10.0000/unknown"]["status"], "not-verified")
        codes = {f["code"] for f in rep["findings"]}
        self.assertTrue({"citation.read_level_low", "citation.version_differs", "citation.not_verified"} <= codes, codes)
        self.assertEqual(code, 3)

    def test_key_match_when_the_bib_lacks_identifiers(self):
        rec = json.loads(self.record.read_text(encoding="utf-8"))
        rec["extension"]["sources"]["lit:S01"]["citation_key"] = "Fix:2026a"
        self.record.write_text(json.dumps(rec), encoding="utf-8")
        tex = self.tmp / "k.tex"
        tex.write_text(r"\cite{Fix:2026a}", encoding="utf-8")
        code, rep = self.report(tex, "--record", self.record)
        self.assertEqual((code, rep["citations"][0]["matched_by"]), (0, "citation key"))

    def test_bad_input_is_exit_2(self):
        self.assertEqual(run()[0], 2)
        self.assertEqual(run(self.tmp / "missing.tex")[0], 2)
        bad = self.tmp / "x.txt"
        bad.write_text("text", encoding="utf-8")
        self.assertEqual(run(bad)[0], 2)
        notrec = self.tmp / "notrec.json"
        notrec.write_text("{}", encoding="utf-8")
        self.assertEqual(run(self.tmp / "paper.tex", "--record", notrec)[0], 2)
        self.assertEqual(run(self.tmp / "paper.tex", "--out", self.tmp / "paper.tex")[0], 2)

    def test_markdown_view(self):
        code, out, _ = run(self.tmp / "paper.tex", self.tmp / "refs.bib", "--record", self.record, "--format", "markdown")
        self.assertEqual(code, 3)
        self.assertIn("citation.not_verified", out)


if __name__ == "__main__":
    unittest.main()
