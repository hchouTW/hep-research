"""Com4: venues and typesetting. The venue reference covers PLB/NPB, NIM A, JINST, PoS, SciPost, PTEP and Chinese
Physics C, each with a source and a date or marked to-verify; Chinese typesetting (xeCJK, ctex) and a thesis skeleton
that builds with XeLaTeX when it is installed; check_diagram_sources.py reads .dot, .mmd, .puml and .tex files by
extension (a user's .dot file passes); the reading-notes record template passes check_communication.py; and
build_lit_matrix.py --require-provenance records read levels and identifiers. All inputs are SYNTHETIC."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SKILL = PLUGIN / "skills" / "hep-writing"
VENUES = SKILL / "references" / "latex-venue-setup.md"
DIAG = SKILL / "scripts" / "check_diagram_sources.py"
COMM = SKILL / "scripts" / "check_communication.py"
LIT = PLUGIN / "skills" / "hep-literature"
MATRIX = LIT / "scripts" / "build_lit_matrix.py"
NEW_VENUES = ("PLB", "NPB", "NIM A", "JINST", "PoS", "SciPost", "PTEP", "Chinese Physics C")


def run(script, *args, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


class Venues(unittest.TestCase):
    def setUp(self):
        self.text = VENUES.read_text(encoding="utf-8")
        self.quick = self.text.split("## Quick reference", 1)[1].split("\n## ", 1)[0]
        self.sources = self.text.split("## Venue rules: sources and last-verified dates", 1)[1]

    def test_each_new_venue_has_a_row_and_a_dated_or_to_verify_source(self):
        for v in NEW_VENUES:
            with self.subTest(venue=v):
                self.assertTrue(any(line.startswith(f"| {v}") or f"| {v} " in line[:40]
                                    for line in self.quick.splitlines()), v)
                rows = [line for line in self.sources.splitlines() if line.startswith("|") and v in line.split("|")[1]]
                self.assertTrue(rows, v)
                self.assertTrue(all(re.search(r"\| 20\d\d-\d\d(-\d\d)? \|$", r.strip()) or "to-verify" in r for r in rows), rows)

    def test_chinese_typesetting(self):
        for term in ("xeCJK", "ctex", "XeLaTeX", "thesis-skeleton-zh.tex"):
            with self.subTest(term=term):
                self.assertIn(term, self.text)


class ThesisSkeleton(unittest.TestCase):
    def test_skeleton_builds_with_xelatex(self):
        tex = SKILL / "assets" / "paper" / "thesis-skeleton-zh.tex"
        text = tex.read_text(encoding="utf-8")
        self.assertIn("ctexbook", text)
        self.assertIn("[VALUE NEEDED]", text)
        if shutil.which("xelatex") is None:
            self.skipTest("xelatex is not installed")
        probe = subprocess.run(["kpsewhich", "ctexbook.cls"], capture_output=True, text=True, timeout=120)
        if not probe.stdout.strip():
            self.skipTest("the ctex bundle is not installed")
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(tex, d)
            p = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name], cwd=d,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 0, p.stdout[-2000:])
            self.assertTrue((Path(d) / "thesis-skeleton-zh.pdf").is_file())


class DiagramFiles(unittest.TestCase):
    def check(self, name, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / name
            f.write_text(text, encoding="utf-8")
            code, out, err = run(DIAG, f, "--format", "json", "--no-tikz", *extra)
        return code, json.loads(out), err

    def test_a_users_dot_file_passes(self):
        code, rep, err = self.check("flow.dot", "digraph G { reco -> fit; fit -> result; }\n")
        self.assertEqual(code, 0, (rep, err))
        self.assertEqual([b["lang"] for b in rep["blocks"]], ["dot"])
        self.assertIn(rep["blocks"][0]["outcome"], ("rendered", "skipped"))
        if shutil.which("dot"):
            self.assertEqual(rep["blocks"][0]["outcome"], "rendered")

    def test_a_broken_dot_file_is_a_source_error_when_dot_exists(self):
        if shutil.which("dot") is None:
            self.skipTest("Graphviz dot is not installed")
        code, rep, _ = self.check("bad.gv", "digraph G { a -> ; }\n")
        self.assertEqual(code, 1)
        self.assertEqual(rep["blocks"][0]["outcome"], "source-error")

    def test_mermaid_plantuml_and_tex_files_by_extension(self):
        code, rep, _ = self.check("flow.mmd", "flowchart LR\n  A --> B\n", "--no-mermaid")
        self.assertEqual((code, rep["blocks"][0]["lang"], rep["blocks"][0]["outcome"]), (0, "mermaid", "lint-only"))
        code, rep, _ = self.check("seq.puml", "@startuml\nA -> B: hello\n@enduml\n")
        self.assertEqual(rep["blocks"][0]["lang"], "plantuml")
        code, rep, _ = self.check("fig.tex", "\\begin{tikzpicture}\\draw (0,0) -- (1,1);\\end{tikzpicture}\n")
        self.assertEqual((code, rep["blocks"][0]["lang"], rep["blocks"][0]["outcome"]), (0, "latex", "skipped"))

    def test_an_unknown_extension_holds_no_block(self):
        code, rep, _ = self.check("notes.txt", "digraph G { a -> b; }\n")
        self.assertEqual(code, 2)


class ReadingNotes(unittest.TestCase):
    def test_markdown_template_asks_for_identifiers_and_read_level(self):
        text = (LIT / "assets" / "reading-notes-template.md").read_text(encoding="utf-8")
        self.assertIn("**Identifiers", text)
        self.assertIn("**Read level", text)
        for level in ("not-opened", "metadata-only", "abstract+metadata", "page", "full-text"):
            self.assertIn(level, text)

    def test_record_template_passes_check_communication(self):
        rec = LIT / "assets" / "reading-notes-record-template.json"
        with tempfile.TemporaryDirectory() as d:
            code, out, err = run(COMM, rec, "--project-root", d, "--checks", "schema", "--format", "json")
        self.assertEqual(code, 0, (out[-1500:], err[-800:]))


class LiteratureMatrix(unittest.TestCase):
    def write(self, d, rows):
        f = Path(d) / "notes.csv"
        f.write_text("key,year,identifier,read_level,result\n" + "".join(",".join(r) + "\n" for r in rows),
                     encoding="utf-8")
        return f

    def test_valid_provenance_passes_and_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.write(d, [("Smith2024", "2024", "arXiv:2401.01234", "full-text", "x"),
                               ("Lee2023", "2023", "doi:10.1103/PhysRevD.108.012345", "abstract+metadata", "y")])
            code, out, err = run(MATRIX, f, "--require-provenance")
        self.assertEqual(code, 0, err)
        self.assertIn("full-text", out)
        self.assertIn("arXiv:2401.01234", out)

    def test_missing_or_unknown_read_level_and_bad_identifier_fail(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.write(d, [("A", "2024", "arXiv:2401.01234", "skimmed", "x"),
                               ("B", "2023", "", "full-text", "y"),
                               ("C", "2022", "see the talk", "page", "z")])
            code, out, err = run(MATRIX, f, "--require-provenance")
        self.assertEqual(code, 1)
        for key in ("A", "B", "C"):
            self.assertIn(f"row {key}", err)

    def test_columns_required(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "n.csv"
            f.write_text("key,year\nA,2024\n", encoding="utf-8")
            code, _, err = run(MATRIX, f, "--require-provenance")
        self.assertEqual(code, 2)
        self.assertIn("identifier", err)


if __name__ == "__main__":
    unittest.main()
