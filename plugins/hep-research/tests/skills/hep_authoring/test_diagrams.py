"""Tests for the hep-authoring diagram-source checker.

Purpose: guard the helper script and the shipped diagram sources against regressions.
What it does: unit-tests the parsing/lint helpers on synthetic input and runs the source
checker against the shipped hep-authoring skill folder. Usage:
`python -m unittest discover -s tests -t .` from the plugin root (plugins/hep-research).
Standard library only; DOT compilation is skipped when Graphviz is absent, PlantUML when `plantuml` is.
"""
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-authoring"


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
        script.write_text(f'#!/bin/sh\ncat > "{directory}/stdin"\necho "{stderr}" >&2\n[ {exit_code} -eq 0 ] && echo "<svg/>"\nexit {exit_code}\n')
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
    def run_script(self, name, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name), *args], capture_output=True, text=True, timeout=600
        )

    def test_shipped_diagram_sources_pass(self):
        """TikZ blocks are compiled only in the slow tier (HEP_SLOW_TESTS=1): CI runners may lack TeX (RC-A11, Q4)."""
        import os
        slow = os.environ.get("HEP_SLOW_TESTS") == "1"
        result = self.run_script("check_diagram_sources.py", *([] if slow else ["--no-tikz"]))
        if result.returncode == 3:  # a renderer that cannot run here is not a defect in the sources: unverified, not failed
            self.skipTest("a diagram renderer is unavailable on this host: " + next(
                (line for line in result.stdout.splitlines() if "environment" in line), result.stdout[-300:]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_hanging_renderer_is_an_environment_error_launched_once(self):
        """Mermaid's mmdc launches Chromium, which can hang where Chromium cannot start (T14). The preflight hangs once;
        no block launches it again, and the outcome is an environment error (exit 3), not a source error."""
        import os
        import time
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "mmdc"
            fake.write_text(f"#!/bin/sh\necho launched >> {shlex.quote(tmp + '/launches')}\nsleep 30\n")
            fake.chmod(0o755)
            md = Path(tmp) / "two.md"
            md.write_text("```mermaid\nflowchart LR\n  A --> B\n```\n\n```mermaid\nflowchart LR\n  C --> D\n```\n")
            env = dict(os.environ, PATH=f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}", HEP_RENDER_TIMEOUT="1")
            start = time.monotonic()
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_diagram_sources.py"), str(md), "--format", "json"],
                                    capture_output=True, text=True, env=env, timeout=60)
            elapsed = time.monotonic() - start
            launches = (Path(tmp) / "launches").read_text().count("launched")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        rep = json.loads(result.stdout)
        self.assertEqual([b["outcome"] for b in rep["blocks"]], ["environment-error", "environment-error"])
        self.assertIn("did not finish within 1 s", rep["renderers"]["mmdc"]["reason"])
        self.assertEqual(launches, 1)
        self.assertLess(elapsed, 20)

    def test_help_prints_usage_and_exits_zero(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_diagram_sources.py"), "--help"],
                                capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_explicit_file_argument_still_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "bad.md"
            md.write_text("```mermaid\nflowchart LR\n  A[open --> B\n```\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_diagram_sources.py"), str(md)],
                                    capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Checked 1 block(s)", result.stdout)


MD = ("```dot\ndigraph G { A -> B; }\n```\n\n```mermaid\nflowchart LR\n  A --> B\n```\n\n"
      "```mermaid\nflowchart LR\n  A[open --> B\n```\n\n```svg\n<svg xmlns=\"http://www.w3.org/2000/svg\"><rect/></svg>\n```\n\n"
      "```tikz\n\\begin{tikzpicture}\\node{a};\\end{tikzpicture}\n```\n")


_TOOL_DIR = None
SHELL_TOOLS = ("sh", "grep", "sleep", "cat")  # what the fake renderers below call; never a renderer


def tool_dir() -> str:
    """A folder holding links to the shell utilities only, so PATH lookups cannot find a real renderer."""
    global _TOOL_DIR
    if _TOOL_DIR is None:
        _TOOL_DIR = tempfile.mkdtemp()
        for name in SHELL_TOOLS:
            found = shutil.which(name)
            if found:
                os.symlink(found, Path(_TOOL_DIR) / name)
    return _TOOL_DIR


class CoverageOutcomes(unittest.TestCase):
    """T3: every block gets one of rendered, lint-only, skipped, source-error, environment-error; counts reconcile; an
    unavailable renderer never counts as rendered; a broken renderer is launched once; rendering is not inspection."""

    def run_checker(self, md_text, *args, bin_dir=None, timeout_s=None):
        tmp = tempfile.mkdtemp()
        md = Path(tmp) / "d.md"
        md.write_text(md_text, encoding="utf-8")
        # no real renderer unless a fake (or a real one's folder) is placed in bin_dir; the shell utilities the fakes use
        # come from a private folder of links, never from /usr/bin or /bin, where a real `dot` may live (Linux images)
        env = dict(os.environ, PATH=f"{bin_dir or tmp}{os.pathsep}{tool_dir()}")
        if timeout_s:
            env["HEP_RENDER_TIMEOUT"] = str(timeout_s)
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_diagram_sources.py"), str(md), "--format", "json", *args],
                                capture_output=True, text=True, env=env, timeout=120)
        rep = json.loads(result.stdout) if result.stdout.strip().startswith("{") else None
        return result.returncode, rep, result

    def fake(self, directory, name, body):
        p = Path(directory) / name
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(0o755)
        return p

    def test_outcomes_without_renderers(self):
        rc, rep, res = self.run_checker(MD)
        self.assertIsNotNone(rep, res.stdout + res.stderr)
        outcomes = [(b["lang"], b["outcome"]) for b in rep["blocks"]]
        self.assertEqual(outcomes, [("dot", "skipped"), ("mermaid", "lint-only"), ("mermaid", "source-error"),
                                    ("svg", "lint-only"), ("tikz", "skipped")])
        self.assertEqual(rep["blocks"][3]["renderer"], "xml")
        self.assertIn("lualatex", rep["blocks"][4]["reason"], "no TeX engine on PATH: the TikZ block is skipped")
        self.assertEqual(rep["counts"]["total"], 5)
        self.assertEqual(sum(v for k, v in rep["counts"].items() if k != "total"), 5)
        self.assertEqual(rep["counts"]["rendered"], 0)
        self.assertEqual(rc, 1, "the lint source error is a confirmed error")
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(rep["visual_inspection"], "not-performed")
        self.assertFalse(rep["renderers"]["dot"]["available"])

    def test_unavailable_rendering_is_not_rendered_and_strict_is_incomplete(self):
        clean = MD.replace("```mermaid\nflowchart LR\n  A[open --> B\n```\n\n", "")
        rc, rep, _ = self.run_checker(clean)
        self.assertEqual(rc, 0, "default mode: nothing confirmed wrong (compatibility)")
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["counts"]["rendered"], 0)
        rc, rep, _ = self.run_checker(clean, "--require-render")
        self.assertEqual(rc, 3)
        self.assertEqual(rep["status"], "incomplete")
        self.assertTrue(any(c["check"] == "render" and c["required"] for c in rep["checks_not_run"]))
        rc, rep, _ = self.run_checker(MD, "--require-render")
        self.assertEqual(rc, 1, "a source error wins over incompleteness")

    def test_startup_failure_preflights_once_and_marks_blocks(self):
        tmp = tempfile.mkdtemp()
        self.fake(tmp, "mmdc", f"echo launched >> {shlex.quote(tmp + '/launches')}\necho 'Error: Could not find Chromium (rev. 1181205)' >&2\nexit 1\n")
        md = "```mermaid\nflowchart LR\n  A --> B\n```\n\n```mermaid\nflowchart LR\n  C --> D\n```\n"
        rc, rep, res = self.run_checker(md, bin_dir=tmp)
        self.assertIsNotNone(rep, res.stdout + res.stderr)
        self.assertEqual([b["outcome"] for b in rep["blocks"]], ["environment-error", "environment-error"])
        self.assertIn("Chromium", rep["renderers"]["mmdc"]["reason"])
        self.assertEqual((Path(tmp) / "launches").read_text().count("launched"), 1)
        self.assertEqual(rc, 3)
        self.assertEqual(rep["counts"]["environment-error"], 2)

    def test_parse_error_and_timeout_are_distinct(self):
        tmp = tempfile.mkdtemp()
        self.fake(tmp, "mmdc", 'while [ $# -gt 0 ]; do [ "$1" = "-i" ] && src="$2"; [ "$1" = "-o" ] && out="$2"; shift; done\n'
                               'if grep -q open "$src"; then echo "Parse error on line 2" >&2; exit 1; fi\n'
                               'if grep -q SLOW "$src"; then sleep 30; fi\necho "<svg/>" > "$out"\n')
        md = ("```mermaid\nflowchart LR\n  A --> B\n```\n\n```mermaid\nflowchart LR\n  A[open] --> B\n```\n\n"
              "```mermaid\nflowchart LR\n  SLOW --> B\n```\n\n```mermaid\nflowchart LR\n  C --> D\n```\n")
        rc, rep, res = self.run_checker(md, bin_dir=tmp, timeout_s=1)
        self.assertIsNotNone(rep, res.stdout + res.stderr)
        self.assertEqual([b["outcome"] for b in rep["blocks"]], ["rendered", "source-error", "environment-error", "environment-error"])
        self.assertIn("Parse error", rep["blocks"][1]["reason"])
        self.assertIn("did not finish", rep["blocks"][2]["reason"])
        self.assertIn("not launched again", rep["blocks"][3]["reason"])
        self.assertEqual(rep["blocks"][0]["output_format"], "svg")
        self.assertEqual(rc, 1)

    def test_render_needs_nonempty_output_and_reports_tool_version(self):
        tmp = tempfile.mkdtemp()
        # renders the preflight diagram (lower-case) but exits 0 without output for the block (upper-case)
        self.fake(tmp, "dot", 'if [ "$1" = "-V" ]; then echo "dot - graphviz version 9.9.9 (fake)" >&2; exit 0; fi\n'
                              'read -r line\ncase "$line" in *"a -> b"*) echo "<svg/>";; esac\nexit 0\n')
        rc, rep, res = self.run_checker("```dot\ndigraph G { A -> B; }\n```\n", bin_dir=tmp)
        self.assertIsNotNone(rep, res.stdout + res.stderr)
        self.assertEqual(rep["blocks"][0]["outcome"], "environment-error")
        self.assertIn("no output", rep["blocks"][0]["reason"])
        self.assertIn("9.9.9", rep["renderers"]["dot"]["version"])
        self.assertEqual(rc, 3)

    def test_real_dot_source_error_is_not_environment(self):
        if not shutil.which("dot"):
            self.skipTest("Graphviz not installed")
        rc, rep, _ = self.run_checker("```dot\ndigraph G { A -> ; ;; -> }\n```\n```dot\ndigraph G { A -> B; }\n```\n",
                                      bin_dir=Path(shutil.which("dot")).parent)
        self.assertEqual([b["outcome"] for b in rep["blocks"]], ["source-error", "rendered"])
        self.assertEqual(rc, 1)

    def test_prose_examples_follow_the_contrast_format(self):
        """examples/prose/: weak-versus-better writing examples pass the canonical-example validator and are indexed."""
        prose = ROOT / "examples" / "prose"
        files = sorted(prose.glob("[0-9]*.md"))
        self.assertGreaterEqual(len(files), 3)
        index = (prose / "README.md").read_text(encoding="utf-8")
        validator = ROOT.parents[1] / "tools" / "validate_skill_example.py"
        for path in files:
            with self.subTest(path.name):
                res = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True, check=False, timeout=60)
                self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
                self.assertIn(path.name, index)
                self.assertIn("Illustrative example", path.read_text(encoding="utf-8"))

    def test_every_example_has_caption_and_source(self):
        for path in sorted((ROOT / "examples").rglob("[0-9]*.md")):
            if "prose" in path.relative_to(ROOT / "examples").parts:
                continue  # writing examples, not diagrams: checked by test_prose_examples_follow_the_contrast_format
            text = path.read_text(encoding="utf-8")
            self.assertIn("**Caption:**", text, path.name)
            self.assertIn("```", text, path.name)
            self.assertIn("**Type:**", text.replace("**Diagram type:**", "**Type:**"), path.name)


if __name__ == "__main__":
    unittest.main()


class LatexFences(unittest.TestCase):
    """Review minor: a ```latex code example is not a diagram; only tikz fences and latex fences holding a tikzpicture count."""

    def test_plain_latex_fence_is_not_a_block(self):
        text = "```latex\n\\section{Intro}\n```\n```latex\n\\begin{tikzpicture}\\node{a};\\end{tikzpicture}\n```\n```tikz\n\\node{b};\n```\n"
        self.assertEqual([lang for lang, _ in sources.extract_blocks(text)], ["latex", "tikz"])
