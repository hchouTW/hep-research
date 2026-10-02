"""End-to-end smoke test: bundled skeleton + .bib -> check_manuscript.py, and
reading notes -> build_lit_matrix.py, run in sequence as a user would.

Run with:
    python -m unittest discover -s tests -t .

from the plugin root (plugins/hep-research).

The optional compile step runs only if `tectonic` is on PATH.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills" / "research-communication"
TEMPLATES = SKILL_ROOT / "assets" / "templates"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_lit_matrix as blm  # noqa: E402
import check_manuscript as cm  # noqa: E402

NOTES = (
    "key,year,method,result\n"
    'Cowan:2010js,2011,"asymptotic formulae, Asimov dataset",q0 ~ half chi2\n'
    "Gross:2010qma,2010,look-elsewhere trials,upcrossings\n"
    "Feldman:1997qc,1998,unified intervals,FC ordering\n"
)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        shutil.copy(TEMPLATES / "paper_skeleton.tex", self.dir / "paper.tex")
        shutil.copy(TEMPLATES / "references.bib", self.dir / "references.bib")

    def _check(self):
        with redirect_stdout(io.StringIO()) as out:
            code = cm.main([str(self.dir)])
        return code, out.getvalue()

    def test_bundled_templates_pass_the_checker(self):
        code, out = self._check()
        self.assertEqual(code, 0, out)

    def test_drafting_mistakes_are_caught(self):
        paper = self.dir / "paper.tex"
        text = paper.read_text(encoding="utf-8")
        text = text.replace(
            r"\end{document}",
            "As in~\\cite{Missing:2024abc}, see Sec.~\\ref{sec:nowhere}.\n"
            "\\label{sec:intro}\n"
            "TODO: final number.\n"
            "\\end{document}",
        )
        paper.write_text(text, encoding="utf-8")
        bib = self.dir / "references.bib"
        bib.write_text(bib.read_text(encoding="utf-8")
                       + '\n@article{example:key,\n    title = "{Duplicate}",\n}\n', encoding="utf-8")
        code, out = self._check()
        self.assertEqual(code, 1)
        for tag in ("[MISSING BIB ENTRY]", "Missing:2024abc", "[UNDEFINED REF]", "sec:nowhere",
                    "[DUPLICATE LABEL]", "sec:intro", "[DUPLICATE BIB KEY]", "example:key",
                    "[TODO / PLACEHOLDER MARKER]"):
            self.assertIn(tag, out)

    def test_lit_matrix_feeds_the_paper(self):
        notes = self.dir / "notes.csv"
        notes.write_text(NOTES, encoding="utf-8")
        table = self.dir / "lit_matrix.md"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(blm.main([str(notes), "--sort-by", "year", "-o", str(table)]), 0)
        lines = table.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[2].startswith("| Feldman:1997qc | 1998"))
        self.assertIn("asymptotic formulae, Asimov dataset", lines[4])
        # Citing the tabulated papers without adding them to the .bib is exactly
        # what the checker should then flag.
        paper = self.dir / "paper.tex"
        keys = ",".join(line.split("|")[1].strip() for line in lines[2:])
        paper.write_text(paper.read_text(encoding="utf-8").replace(
            r"\end{document}", f"Prior work~\\cite{{{keys}}}.\n\\end{{document}}"), encoding="utf-8")
        code, out = self._check()
        self.assertEqual(code, 1)
        for key in ("Cowan:2010js", "Gross:2010qma", "Feldman:1997qc"):
            self.assertIn(key, out)

    @unittest.skipUnless(shutil.which("tectonic"), "tectonic not installed")
    def test_bundled_skeleton_compiles(self):
        run = subprocess.run(["tectonic", "--keep-logs", "paper.tex"], cwd=self.dir,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        log = (self.dir / "paper.log").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("undefined", log.lower().replace("infwarerr", ""))


if __name__ == "__main__":
    unittest.main()
