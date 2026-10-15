"""check_manuscript.py main-document mode (hep-communication plan T2): the checker scans the files the selected
main document actually includes, resolved against the declared build root and bounded by the project root, and reports
what it could not follow as incomplete coverage instead of guessing. Directory mode keeps its behavior except that an
empty directory is a no-input failure. All manuscripts are synthetic fixtures."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-communication"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import check_manuscript as cm  # noqa: E402

SCRIPT = SKILL_ROOT / "scripts" / "check_manuscript.py"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.ms = self.tmpdir / "ms"
        self.ms.mkdir()

    def w(self, rel: str, content: str, base: Path | None = None) -> Path:
        p = (base or self.ms) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def run_main(self, *args):
        buf, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", buf), mock.patch("sys.stderr", err):
            code = cm.main([str(a) for a in args])
        return code, buf.getvalue(), err.getvalue()

    def discover(self, main, project_root=None, build_root=None):
        return cm.discover_manuscript_files(Path(main), Path(project_root or self.ms), Path(build_root or self.ms))

    def names(self, disc):
        return [str(Path(f).relative_to(self.ms.resolve())) for f in disc["files"]]


class DirectoryModeTests(Base):
    def test_empty_directory_is_not_success(self):
        code, out, err = self.run_main(self.ms)
        self.assertEqual(code, 2)
        self.assertNotIn("No issues found", out)
        self.assertIn("no manuscript", (out + err).lower())

    def test_directory_mode_is_labeled_repository_wide(self):
        self.w("a.tex", "\\label{x}\n")
        code, out, _ = self.run_main(self.ms)
        self.assertEqual(code, 0)
        self.assertIn("repository-wide", out.lower())


class DiscoveryTests(Base):
    def test_unincluded_label_does_not_resolve_main_reference(self):
        main = self.w("main.tex", "\\documentclass{article}\\begin{document}See \\ref{fig:only-in-backup}.\\end{document}\n")
        self.w("old_backup.tex", "\\label{fig:only-in-backup}\n")
        self.assertEqual(self.run_main(self.ms)[0], 0, "directory mode merges every file (unchanged, labeled as such)")
        code, out, _ = self.run_main("--main", main)
        self.assertEqual(code, 1)
        self.assertIn("fig:only-in-backup", out)
        self.assertIn("[UNDEFINED REF]", out)

    def test_nested_input_include_and_optional_suffix(self):
        main = self.w("main.tex", "\\input{sections/intro}\n\\include{sections/results.tex}\n\\label{a}\\ref{b}\\ref{c}\n")
        self.w("sections/intro.tex", "\\label{b}\\input{sections/deep}\n")
        self.w("sections/deep.tex", "\\label{c}\n")
        self.w("sections/results.tex", "text\n")
        disc = self.discover(main)
        self.assertEqual(self.names(disc), ["main.tex", "sections/intro.tex", "sections/deep.tex", "sections/results.tex"])
        self.assertEqual(disc["unresolved"], [])
        self.assertEqual(disc["coverage"], "complete")
        self.assertEqual(self.run_main("--main", main)[0], 0)

    def test_missing_include_is_unresolved_and_incomplete(self):
        main = self.w("main.tex", "\\input{sections/missing}\n\\ref{x}\n")
        disc = self.discover(main)
        self.assertEqual(disc["coverage"], "incomplete")
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["missing"])
        self.assertEqual(disc["unresolved"][0]["line"], 1)
        code, out, _ = self.run_main("--main", main)
        self.assertEqual(code, 1, "the undefined ref is a confirmed error; the missing include is also reported")
        self.assertIn("missing", out)
        self.w("main.tex", "\\input{sections/missing}\n")
        code, out, _ = self.run_main("--main", main)
        self.assertEqual(code, 3, "nothing wrong was confirmed, but coverage is incomplete")
        self.assertIn("incomplete", out.lower())

    def test_include_cycle_detected(self):
        main = self.w("main.tex", "\\input{a}\n")
        self.w("a.tex", "\\input{b}\n")
        self.w("b.tex", "\\input{a}\n")
        disc = self.discover(main)
        self.assertEqual(self.names(disc), ["main.tex", "a.tex", "b.tex"])
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["cycle"])
        self.assertEqual(disc["coverage"], "incomplete")

    def test_build_root_path_semantics(self):
        # TeX resolves \input against the build working directory, not the including file's folder
        main = self.w("main.tex", "\\input{sections/a}\n")
        self.w("sections/a.tex", "\\input{b}\n\\input{sections/c}\n")
        self.w("sections/b.tex", "\\label{sibling}\n")
        self.w("sections/c.tex", "\\label{c}\n")
        disc = self.discover(main)
        self.assertEqual(self.names(disc), ["main.tex", "sections/a.tex", "sections/c.tex"])
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["missing"])
        self.assertIn("b", disc["unresolved"][0]["raw"])
        disc = self.discover(main, build_root=self.ms / "sections")  # a different build root changes what resolves
        self.assertEqual(self.names(disc), ["main.tex"])
        self.assertEqual(disc["unresolved"][0]["raw"], "sections/a")

    def test_outside_project_root_is_not_traversed(self):
        shared = self.w("macros.tex", "\\label{shared}\n", base=self.tmpdir / "shared")
        main = self.w("main.tex", "\\input{../shared/macros}\n\\ref{shared}\n")
        opened, watching = [], []
        sys.addaudithook(lambda ev, args: opened.append(str(args[0])) if watching and ev == "open" and isinstance(args[0], (str, Path)) else None)
        watching.append(1)
        try:
            disc = self.discover(main)
        finally:
            watching.clear()
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["outside-root"])
        self.assertNotIn(str(shared), opened)
        self.assertNotIn(str(shared.resolve()), opened)
        disc = self.discover(main, project_root=self.tmpdir)  # a wider boundary lets it resolve
        self.assertEqual(disc["unresolved"], [])
        self.assertEqual(len(disc["files"]), 2)

    def test_macro_generated_and_conditional_includes_are_incomplete(self):
        main = self.w("main.tex", "\\newcommand{\\sec}{intro}\n\\input{sections/\\sec}\n\\ifdraft\\input{draft}\\else\\input{final}\\fi\n")
        self.w("draft.tex", "d\n")
        self.w("final.tex", "f\n")
        disc = self.discover(main)
        kinds = sorted(u["kind"] for u in disc["unresolved"])
        self.assertEqual(kinds, ["conditional", "conditional", "macro-generated"])
        self.assertEqual(disc["coverage"], "incomplete")
        self.assertEqual(self.names(disc), ["main.tex", "draft.tex", "final.tex"], "conditional branches are scanned and flagged")
        code, out, _ = self.run_main("--main", main)
        self.assertEqual(code, 3)
        self.assertIn("macro-generated", out)

    def test_unsupported_mechanisms_are_reported_not_guessed(self):
        main = self.w("main.tex", "\\includeonly{a}\n\\input{a}\n\\import{sub/}{b}\n")
        self.w("a.tex", "a\n")
        self.w("sub/b.tex", "b\n")
        disc = self.discover(main)
        self.assertEqual(self.names(disc), ["main.tex", "a.tex", "sub/b.tex"])
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["includeonly"])
        self.assertEqual(disc["coverage"], "incomplete")

    def test_comments_and_verbatim_are_ignored(self):
        main = self.w("main.tex", "% \\input{ghost}\n\\begin{verbatim}\n\\input{ghost2}\\label{v}\n\\end{verbatim}\n"
                                  "\\begin{lstlisting}\n\\cite{nope}\n\\end{lstlisting}\n\\label{v}\n")
        disc = self.discover(main)
        self.assertEqual(disc["unresolved"], [])
        results = cm.scan_main(main, self.ms, self.ms)
        self.assertEqual(results["duplicate_labels"], {})
        self.assertEqual(results["missing_bib"], {})


class BibliographyTests(Base):
    def test_literal_bibliography_declaration_resolves_only_named_bib(self):
        main = self.w("main.tex", "\\cite{A}\\cite{B}\n\\bibliography{refs,more}\n")
        self.w("refs.bib", "@article{A,\n title={a},\n}\n")
        self.w("more.bib", "@article{B,\n title={b},\n}\n")
        self.w("unrelated.bib", "@article{C,\n title={c},\n}\n")
        disc = self.discover(main)
        self.assertEqual(sorted(p.name for p in disc["bib_files"]), ["more.bib", "refs.bib"])
        results = cm.scan_main(main, self.ms, self.ms)
        self.assertEqual(results["missing_bib"], {})
        self.assertEqual(results["unused_bib"], [])
        self.w("main.tex", "\\cite{A}\\cite{C}\n\\bibliography{refs}\n")
        results = cm.scan_main(main, self.ms, self.ms)
        self.assertIn("C", results["missing_bib"], "a .bib the document does not declare cannot satisfy its citations")

    def test_biblatex_resource_declaration(self):
        main = self.w("main.tex", "\\addbibresource{refs.bib}\n\\cite{A}\n")
        self.w("refs.bib", "@article{A,\n title={a},\n}\n")
        self.assertEqual(cm.scan_main(main, self.ms, self.ms)["missing_bib"], {})

    def test_declared_bib_missing_is_unresolved(self):
        main = self.w("main.tex", "\\cite{A}\n\\bibliography{gone}\n")
        disc = self.discover(main)
        self.assertEqual([u["kind"] for u in disc["unresolved"]], ["missing-bib"])
        self.assertEqual(self.run_main("--main", main)[0], 3)

    def test_stale_bbl_cannot_certify_another_main(self):
        self.w("main.tex", "\\cite{OnlyInMain}\n\\bibliography{refs}\n")
        self.w("refs.bib", "@article{OnlyInMain,\n title={m},\n}\n")
        self.w("main.bbl", "\\begin{thebibliography}{1}\n\\bibitem{OnlyInMain} m.\n\\bibitem{Ghost} g.\n\\end{thebibliography}\n")
        supp = self.w("supplement.tex", "\\cite{Ghost}\n")
        self.assertEqual(self.run_main(self.ms)[0], 0, "directory mode still merges the .bbl (repository-wide scan)")
        code, out, _ = self.run_main("--main", supp)
        self.assertEqual(code, 3, out)
        self.assertIn("Ghost", out)
        self.assertIn("built", out.lower())
        code, out, _ = self.run_main("--main", supp, "--bbl", self.ms / "main.bbl")
        self.assertEqual(code, 0, out)

    def test_citations_without_any_bibliography_are_missing(self):
        main = self.w("main.tex", "\\cite{A}\n")
        results = cm.scan_main(main, self.ms, self.ms)
        self.assertIn("A", results["missing_bib"])
        self.assertTrue(results["no_bibliography"])
        self.assertEqual(self.run_main("--main", main)[0], 1)


class SeparateDocumentsTests(Base):
    def test_independent_main_and_supplement_share_labels(self):
        main = self.w("main.tex", "\\label{sec:intro}\\ref{sec:intro}\n")
        supp = self.w("supplement.tex", "\\label{sec:intro}\\ref{sec:intro}\n")
        self.assertEqual(self.run_main(self.ms)[0], 1, "directory mode sees a duplicate: the two documents are merged")
        self.assertEqual(self.run_main("--main", main)[0], 0)
        self.assertEqual(self.run_main("--main", supp)[0], 0)
        self.w("main.tex", "\\label{sec:intro}\\label{sec:intro}\n")
        code, out, _ = self.run_main("--main", main)
        self.assertEqual(code, 1)
        self.assertIn("[DUPLICATE LABEL]", out)


class CliTests(Base):
    def test_json_report_shape(self):
        main = self.w("main.tex", "\\input{missing}\n\\ref{x}\\label{y}\n")
        code, out, _ = self.run_main("--main", main, "--format", "json")
        self.assertEqual(code, 1)
        rep = json.loads(out)
        self.assertEqual(rep["report_version"], "1.0.0")
        self.assertEqual(rep["tool"], "check_manuscript")
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(rep["exit_code"], 1)
        self.assertEqual(rep["scope"]["mode"], "main")
        self.assertEqual(rep["coverage"], "incomplete")
        self.assertIn("include-discovery", rep["checks_run"])
        self.assertTrue(any(c["check"] == "compile" for c in rep["checks_not_run"]))
        codes = {f["code"] for f in rep["findings"]}
        self.assertIn("manuscript.undefined_ref", codes)
        self.assertIn("manuscript.include_unresolved", codes)
        sev = {f["code"]: f["severity"] for f in rep["findings"]}
        self.assertEqual(sev["manuscript.include_unresolved"], "unresolved")
        self.assertTrue(all({"code", "severity", "location", "message", "suggested_action"} <= set(f) for f in rep["findings"]))

    def test_json_in_directory_mode(self):
        self.w("a.tex", "\\ref{x}\n")
        code, out, _ = self.run_main(self.ms, "--format", "json")
        self.assertEqual(code, 1)
        rep = json.loads(out)
        self.assertEqual(rep["scope"]["mode"], "directory")
        self.assertIn("repository-wide", rep["scope"]["note"])

    def test_invalid_invocation(self):
        self.assertEqual(self.run_main()[0], 2)
        self.assertEqual(self.run_main("--main", self.ms / "nope.tex")[0], 2)
        self.assertEqual(self.run_main(self.ms / "nope")[0], 2)

    def test_main_mode_is_read_only(self):
        main = self.w("main.tex", "\\input{a}\n\\cite{K}\\bibliography{refs}\n")
        self.w("a.tex", "x\n")
        self.w("refs.bib", "@article{K,\n title={k},\n}\n")
        before = {p: p.read_bytes() for p in self.ms.rglob("*") if p.is_file()}
        self.run_main("--main", main, "--format", "json")
        after = {p: p.read_bytes() for p in self.ms.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_help_mentions_modes(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0)
        self.assertIn("--main", run.stdout)
        self.assertIn("--build-root", run.stdout)


if __name__ == "__main__":
    unittest.main()


class ReviewMinors(Base):
    def test_input_without_tex_suffix_falls_back_to_the_bare_file(self):
        main = self.w("main.tex", "\\input{notation}\n\\input{chap.v2}\n\\ref{n}\\ref{c}\n")
        self.w("notation", "\\label{n}\n")
        self.w("chap.v2.tex", "\\label{c}\n")
        disc = self.discover(main)
        self.assertEqual(self.names(disc), ["main.tex", "notation", "chap.v2.tex"])
        self.assertEqual(disc["unresolved"], [])
        self.assertEqual(self.run_main("--main", main)[0], 0)

    def test_style_in_main_mode_scans_only_the_included_files(self):
        main = self.w("main.tex", "\\input{a}\nSee Fig. \\ref{x}.\\label{x}\n")
        self.w("a.tex", "at 125 GeV\n")
        self.w("unused.tex", "at 999GeV and Fig. \\ref{x} and Table \\ref{x}\n")
        code, out, _ = self.run_main("--main", main, "--style")
        self.assertEqual(code, 0)
        self.assertIn("[STYLE] 2 advisory", out)
