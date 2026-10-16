"""F-12: the venue-agnostic paper skeleton prints arXiv eprints and DOIs in its bibliography, and its example result is
an unfilled placeholder that check_manuscript.py reports (before the fix the style was `plain`, which drops eprints,
and the example number 125.3 GeV passed as a filled value)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "skills" / "hep-communication" / "assets" / "paper"
CHECK = ROOT / "skills" / "hep-communication" / "scripts" / "check_manuscript.py"


class PaperSkeleton(unittest.TestCase):
    def test_bibliography_style_prints_eprints(self):
        tex = (PAPER / "paper-skeleton.tex").read_text(encoding="utf-8")
        style = re.search(r"^\\bibliographystyle\{([^}]*)\}", tex, re.M).group(1)
        self.assertNotEqual(style, "plain")
        self.assertIn(style, ("unsrturl", "apsrev4-2", "JHEP", "utphys"))

    def test_example_result_is_a_placeholder_the_checker_reports(self):
        tex = (PAPER / "paper-skeleton.tex").read_text(encoding="utf-8")
        results = tex[tex.index("\\section{Results}"):tex.index("\\section{Summary}")]
        self.assertIn("[VALUE NEEDED", results)
        self.assertNotRegex(results, r"\d+\.\d+\s*\\pm")
        with tempfile.TemporaryDirectory() as td:
            shutil.copy(PAPER / "paper-skeleton.tex", Path(td) / "main.tex")
            shutil.copy(PAPER / "references.bib", Path(td) / "references.bib")
            res = subprocess.run([sys.executable, "-I", str(CHECK), td, "--format", "json"], capture_output=True,
                                 text=True, timeout=300)
        rep = json.loads(res.stdout)
        found = [f for f in rep.get("findings", []) if "VALUE NEEDED" in json.dumps(f)]
        self.assertTrue(found, rep.get("findings", [])[:5])

    @unittest.skipUnless(shutil.which("pdflatex") and shutil.which("bibtex"), "pdflatex and bibtex not installed")
    def test_compiled_bibliography_shows_an_eprint(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            tex = (PAPER / "paper-skeleton.tex").read_text(encoding="utf-8")
            keys = re.findall(r"^@\w+\{([^,]+),", (PAPER / "references.bib").read_text(encoding="utf-8"), re.M)
            self.assertTrue(keys)
            (d / "main.tex").write_text(tex.replace("\\end{document}", "\\nocite{*}\n\\end{document}"))
            shutil.copy(PAPER / "references.bib", d / "references.bib")
            run = dict(capture_output=True, text=True, timeout=300, cwd=d)
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "main.tex"], **run)
            bib = subprocess.run(["bibtex", "main"], **run)
            if not (d / "main.bbl").exists():
                self.skipTest(f"bibtex produced no .bbl: {bib.stdout[-300:]}")
            bbl = (d / "main.bbl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("arXiv:", bbl)


if __name__ == "__main__":
    unittest.main()
