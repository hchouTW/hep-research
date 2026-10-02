"""Tests for the academic-diagrams diagram-source checker (ported from the legacy academic-diagrams skill).

Purpose: guard the helper script and the shipped diagram sources against regressions.
What it does: unit-tests the parsing/lint helpers on synthetic input and runs the source
checker against the shipped research-communication skill folder. Usage:
`python -m unittest discover -s tests -t .` from the plugin root (plugins/hep-research).
Standard library only; DOT compilation is skipped when Graphviz is absent, PlantUML when `plantuml` is.
Bundle-validator tests were retired with legacy scripts/validate_skill_bundle.py.
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "research-communication"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sources = load("check_diagram_sources")


class MermaidLint(unittest.TestCase):
    def test_good_flowchart(self):
        self.assertEqual(sources.lint_mermaid("flowchart LR\n A[Raw] --> B{ok?}\n"), [])

    def test_sequence_async_arrow_is_not_a_bracket(self):
        self.assertEqual(sources.lint_mermaid("sequenceDiagram\n A--)B: hi\n"), [])

    def test_unbalanced_bracket(self):
        self.assertTrue(sources.lint_mermaid("flowchart LR\n A[Raw --> B\n"))

    def test_unknown_type(self):
        self.assertTrue(sources.lint_mermaid("foo\n A --> B\n"))

    def test_er_crows_foot_allowed(self):
        self.assertEqual(sources.lint_mermaid("erDiagram\n A ||--o{ B : has\n"), [])

    def test_extract_blocks(self):
        text = "x\n```dot\ndigraph{}\n```\n```mermaid\nflowchart LR\n```\n```text\nA\n```"
        self.assertEqual([lang for lang, _ in sources.extract_blocks(text)], ["dot", "mermaid"])


@unittest.skipUnless(shutil.which("dot"), "Graphviz not installed")
class DotCompile(unittest.TestCase):
    def test_valid_dot(self):
        self.assertIsNone(sources.check_dot("digraph G { A -> B; }"))

    def test_invalid_dot(self):
        self.assertTrue(sources.check_dot("digraph G { A -> ; ;; -> }"))


class SvgCheck(unittest.TestCase):
    def test_well_formed(self):
        self.assertIsNone(sources.check_svg('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'))

    def test_malformed(self):
        self.assertIn("not well-formed", sources.check_svg("<svg><rect></svg>"))

    def test_svg_fence_extracted(self):
        self.assertEqual([l for l, _ in sources.extract_blocks("```svg\n<svg/>\n```")], ["svg"])


class MermaidRender(unittest.TestCase):
    def fake_mmdc(self, directory, exit_code, stderr=""):
        """Write a stand-in `mmdc` that writes the -o file (or fails) so no browser is needed."""
        script = Path(directory) / "fake_mmdc"
        script.write_text(
            "#!/bin/sh\n"
            'while [ $# -gt 0 ]; do [ "$1" = "-o" ] && out="$2"; shift; done\n'
            f'[ {exit_code} -eq 0 ] && echo "<svg/>" > "$out"\n'
            f'echo "{stderr}" >&2\nexit {exit_code}\n'
        )
        script.chmod(0o755)
        return str(script)

    def test_render_success(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(sources.check_mermaid("flowchart LR\n A-->B", self.fake_mmdc(d, 0)))

    def test_render_failure_reports_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            error = sources.check_mermaid("flowchart LR\n A-->", self.fake_mmdc(d, 1, "Parse error"))
            self.assertIn("Parse error", error)

    @unittest.skipUnless(shutil.which("mmdc"), "Mermaid CLI not installed")
    def test_real_mmdc_rejects_bad_syntax(self):
        self.assertTrue(sources.check_mermaid("flowchart LR\n A -.->|x| B --- ??? C"))


class PlantUmlRender(unittest.TestCase):
    def fake_plantuml(self, directory, exit_code, stderr=""):
        """Write a stand-in `plantuml` that copies stdin to a file and exits with exit_code."""
        script = Path(directory) / "fake_plantuml"
        script.write_text(f'#!/bin/sh\ncat > "{directory}/stdin"\necho "{stderr}" >&2\nexit {exit_code}\n')
        script.chmod(0o755)
        return str(script)

    def test_fragment_is_wrapped(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(sources.check_plantuml("A -> B\n", self.fake_plantuml(d, 0)))
            self.assertTrue((Path(d) / "stdin").read_text().startswith("@startuml\n"))

    def test_failure_reports_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            error = sources.check_plantuml("@startuml\nx\n@enduml\n", self.fake_plantuml(d, 200, "Syntax Error?"))
            self.assertIn("Syntax Error?", error)

    def test_plantuml_fence_extracted(self):
        self.assertEqual([l for l, _ in sources.extract_blocks("```plantuml\nA -> B\n```")], ["plantuml"])

    @unittest.skipUnless(shutil.which("plantuml"), "PlantUML not installed")
    def test_real_plantuml_rejects_one_line_class_body(self):
        self.assertTrue(sources.check_plantuml("class Sample { +id : int  +energy : float }\n"))


class RealBundle(unittest.TestCase):
    def run_script(self, name):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)], capture_output=True, text=True
        )

    def test_shipped_diagram_sources_pass(self):
        result = self.run_script("check_diagram_sources.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_example_has_caption_and_source(self):
        for path in sorted((ROOT / "examples").rglob("[0-9]*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIn("**Caption:**", text, path.name)
            self.assertIn("```", text, path.name)
            self.assertIn("**Type:**", text.replace("**Diagram type:**", "**Type:**"), path.name)


if __name__ == "__main__":
    unittest.main()
