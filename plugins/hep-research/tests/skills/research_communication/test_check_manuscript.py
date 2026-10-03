"""Unit tests for skills/research-communication/scripts/check_manuscript.py.

Run with:
    python -m unittest discover -s tests -t .

from the plugin root (plugins/hep-research).
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills" / "research-communication"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import check_manuscript as cm  # noqa: E402


class TestCheckManuscript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _write(self, rel_path: str, content: str) -> Path:
        p = self.tmpdir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_clean_manuscript_has_no_issues(self):
        self._write(
            "paper.tex",
            r"""
            \section{Introduction}
            As shown in Fig.~\ref{fig:mass}, the result agrees with theory~\cite{Aad:2012tfa}.
            \label{sec:intro}
            """,
        )
        self._write(
            "figs.tex",
            r"""
            \begin{figure}
            \label{fig:mass}
            \end{figure}
            """,
        )
        self._write("refs.bib", "@article{Aad:2012tfa,\n  title={Observation of a new particle},\n}\n")

        results = cm.scan(self.tmpdir)
        self.assertEqual(results["missing_bib"], {})
        self.assertEqual(results["duplicate_labels"], {})
        self.assertEqual(results["undefined_refs"], {})
        self.assertEqual(results["todos"], [])
        self.assertEqual(results["unused_bib"], [])

    def test_missing_bib_entry_detected(self):
        self._write("paper.tex", r"\cite{DoesNotExist}")
        self._write("refs.bib", "@article{SomeOtherKey,\n  title={x},\n}\n")

        results = cm.scan(self.tmpdir)
        self.assertIn("DoesNotExist", results["missing_bib"])

    def test_unused_bib_entry_detected(self):
        self._write("paper.tex", r"\cite{UsedKey}")
        self._write(
            "refs.bib",
            "@article{UsedKey,\n  title={x},\n}\n@article{UnusedKey,\n  title={y},\n}\n",
        )

        results = cm.scan(self.tmpdir)
        self.assertIn("UnusedKey", results["unused_bib"])
        self.assertNotIn("UsedKey", results["unused_bib"])

    def test_duplicate_label_detected(self):
        self._write(
            "paper.tex",
            "\\label{fig:same}\nsome text\n\\label{fig:same}\n",
        )

        results = cm.scan(self.tmpdir)
        self.assertIn("fig:same", results["duplicate_labels"])
        self.assertEqual(len(results["duplicate_labels"]["fig:same"]), 2)

    def test_undefined_ref_detected(self):
        self._write("paper.tex", r"See Fig.~\ref{fig:missing} for details.")

        results = cm.scan(self.tmpdir)
        self.assertIn("fig:missing", results["undefined_refs"])

    def test_todo_marker_detected(self):
        self._write("paper.tex", "The efficiency is TODO: fill in from the fit.\n")

        results = cm.scan(self.tmpdir)
        self.assertEqual(len(results["todos"]), 1)

    def test_value_needed_marker_detected(self):
        self._write("paper.tex", "The mass is [VALUE NEEDED: fit result] GeV.\n")

        results = cm.scan(self.tmpdir)
        self.assertEqual(len(results["todos"]), 1)

    def test_placeholder_text_detected(self):
        self._write("paper.tex", "Results: ??? need to fill in once fit converges.\n")

        results = cm.scan(self.tmpdir)
        self.assertEqual(len(results["placeholders"]), 1)

    # Regression cases found on real arXiv sources and a synthetic edge-case
    # manuscript (2026-09-26; see legacy academic-papers/VALIDATION.md at agentic-ai-skills@3e995a4).

    def test_commented_out_cite_and_label_are_ignored(self):
        self._write("paper.tex", "\\label{sec:a}\n% \\label{sec:a}\n% \\cite{Gone}\nText 50\\% \\cite{K}.\n")
        self._write("refs.bib", "@article{K,\n  title={x},\n}\n")
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["missing_bib"], {})
        self.assertEqual(results["duplicate_labels"], {})
        self.assertEqual(results["unused_bib"], [])  # \cite{K} after an escaped \% still counts

    def test_cite_variants_count_as_cited(self):
        self._write(
            "paper.tex",
            "\\citep[see][p.~3]{TwoOpt} \\cite{LineA,\n  LineB} \\citeauthor{Auth} \\citeyear{Year}\n"
            "\\parencite{Bl1} \\textcite{Bl2} \\autocite[5]{Bl3} \\nocite{NoCite}\n",
        )
        keys = ["TwoOpt", "LineA", "LineB", "Auth", "Year", "Bl1", "Bl2", "Bl3", "NoCite"]
        self._write("refs.bib", "".join(f"@article{{{k},\n  title={{x}},\n}}\n" for k in keys))
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["unused_bib"], [])
        self.assertEqual(results["missing_bib"], {})

    def test_nocite_star_marks_all_entries_cited(self):
        self._write("paper.tex", "\\nocite{*}\n")
        self._write("refs.bib", "@article{A,\n  title={x},\n}\n@book{B,\n  title={y},\n}\n")
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["unused_bib"], [])
        self.assertEqual(results["missing_bib"], {})

    def test_duplicate_bib_key_detected_case_insensitively(self):
        self._write("paper.tex", "\\cite{Dup}\n")
        self._write(
            "refs.bib",
            "@article{Dup,\n  title={x},\n}\n@article{dup,\n  title={y},\n}\n"
            "@string{jhep = \"JHEP\"}\n@comment{not an entry}\n@misc(Paren,\n  title={z})\n",
        )
        results = cm.scan(self.tmpdir)
        self.assertEqual(list(results["duplicate_bib"]), ["Dup"])
        self.assertEqual(len(results["duplicate_bib"]["Dup"]), 2)
        self.assertEqual(results["unused_bib"], ["Paren"])

    def test_cref_list_split_and_pageref_checked(self):
        self._write(
            "paper.tex",
            "\\label{a}\\label{b}\n\\cref{a,b} \\Cref{b} \\pageref{missing} \\nameref{a}\n",
        )
        results = cm.scan(self.tmpdir)
        self.assertEqual(set(results["undefined_refs"]), {"missing"})

    def test_macro_parameters_are_not_labels(self):
        # 1207.7214 (ATLAS): \newcommand{\figref}[1]{Fig.~\ref{#1}}
        self._write("paper.tex", "\\newcommand{\\figref}[1]{Fig.~\\ref{#1}\\label{#1}}\n\\label{#1}\n")
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["undefined_refs"], {})
        self.assertEqual(results["duplicate_labels"], {})

    def test_todo_macro_definitions_and_lowercase_xxx_are_not_markers(self):
        self._write(
            "paper.tex",
            "\\newcommand\\todo[1]{\\textcolor{red}{#1}}\n"
            "\\newcommand{\\note}[1]{\\textbf{TODO:} #1}\n"
            "% option [fontset=xxx] is a keyvalue\n"
            "% Package for lorem ipsum\n",
        )
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["todos"], [])
        self.assertEqual(results["placeholders"], [])

    def test_todo_in_comment_and_todo_call_are_markers(self):
        self._write("paper.tex", "%TODO(noam): update results\nText \\todo{check number}.\n")
        results = cm.scan(self.tmpdir)
        self.assertEqual([ln for _, ln, _ in results["todos"]], [1, 2])

    # Advisory --style checks (2026-09-27), tuned on 16 real arXiv sources.

    def test_style_ref_without_tie_only_after_label_words(self):
        self._write(
            "paper.tex",
            "See Fig. \\ref{a} and Table \\ref{b}.\n"      # 2 findings
            "Fig.~\\ref{a}, Props.~\\ref{c} and \\ref{d}, in \\eqref{e}, (\\ref{f}).\n"  # none
            "% Fig. \\ref{commented}\n",                    # comment: none
        )
        kinds = [(ln, k) for _, ln, k, _ in cm.style_scan(self.tmpdir)]
        self.assertEqual(kinds, [(1, "ref without ~"), (1, "ref without ~")])

    def test_style_number_unit_spacing_skips_layout_lengths(self):
        self._write(
            "paper.tex",
            "at 125 GeV and 125GeV with 4.7 fb$^{-1}$\n"   # 3 findings
            "125~GeV, 125\\,GeV, \\SI{125}{GeV}, v2 and 2019 data\n"  # none
            "\\vspace{-2mm} \\node[right=2.5cm] {x};\n",     # layout: none
        )
        texts = [text for _, _, kind, text in cm.style_scan(self.tmpdir)]
        self.assertEqual(texts, ["125 GeV", "125GeV", "4.7 fb"])

    def test_style_findings_do_not_change_exit_code(self):
        self._write("paper.tex", "See Fig. \\ref{a} at 125 GeV.\\label{a}\n")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = cm.main([str(self.tmpdir), "--style"])
        self.assertEqual(code, 0)
        self.assertIn("[STYLE] 2 advisory", out.getvalue())

    def test_report_exit_code_zero_when_clean(self):
        self._write("paper.tex", r"\cite{K}\label{a}")
        self._write("refs.bib", "@article{K,\n  title={x},\n}\n")
        results = cm.scan(self.tmpdir)
        code = cm.report(results, strict=False)
        self.assertEqual(code, 0)

    def test_report_exit_code_nonzero_when_issues(self):
        self._write("paper.tex", r"\cite{Missing}")
        self._write("refs.bib", "@article{Other,\n  title={x},\n}\n")
        results = cm.scan(self.tmpdir)
        code = cm.report(results, strict=False)
        self.assertEqual(code, 1)



class TestCitationsWithoutBibliographyAuditT08(unittest.TestCase):
    """Audit T08: citations with no resolvable bibliography must not pass."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _write(self, rel_path: str, content: str) -> Path:
        p = self.tmpdir / rel_path
        p.write_text(content, encoding="utf-8")
        return p

    def _main(self, *extra):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = cm.main([str(self.tmpdir), *extra])
        return code, buf.getvalue()

    def test_citation_without_any_bibliography_fails(self):
        self._write("main.tex", "A claim \\cite{Nonexistent}.\n")
        results = cm.scan(self.tmpdir)
        self.assertIn("Nonexistent", results["missing_bib"])
        self.assertTrue(results["no_bibliography"])
        code, out = self._main()
        self.assertEqual(code, 1)
        self.assertNotIn("No issues found", out)
        self.assertIn("no bibliography", out.lower())

    def test_valid_bibliography_passes(self):
        self._write("main.tex", "A claim \\cite{Known}.\n")
        self._write("refs.bib", "@article{Known,\n  title={x},\n}\n")
        self.assertEqual(self._main()[0], 0)

    def test_document_without_citations_passes(self):
        self._write("main.tex", "No citations here.\n")
        code, out = self._main()
        self.assertEqual(code, 0)
        self.assertIn("No issues found", out)

    def test_inline_thebibliography_resolves(self):
        self._write("main.tex", "A \\cite{Inline,Other}.\n\\begin{thebibliography}{9}\n\\bibitem{Inline} A. Author.\n"
                                "\\bibitem[Oth(2020)]{Other} B. Author.\n\\end{thebibliography}\n")
        results = cm.scan(self.tmpdir)
        self.assertEqual(results["missing_bib"], {})
        self.assertEqual(self._main()[0], 0)
        self._write("main.tex", "A \\cite{Missing}.\n\\begin{thebibliography}{9}\n\\bibitem{Inline} A.\n\\end{thebibliography}\n")
        self.assertIn("Missing", cm.scan(self.tmpdir)["missing_bib"])

    def test_declared_external_bibliography_is_unresolved_not_missing(self):
        self._write("main.tex", "A claim \\cite{CollabDB:2026}.\n")
        results = cm.scan(self.tmpdir, external_bib="collaboration database export at build time")
        self.assertEqual(results["missing_bib"], {})
        self.assertIn("CollabDB:2026", results["unresolved_citations"])
        code, out = self._main("--external-bib", "collaboration database export at build time")
        self.assertEqual(code, 3)
        self.assertIn("UNRESOLVED", out)


if __name__ == "__main__":
    unittest.main()
