#!/usr/bin/env python3
"""Check the diagram sources embedded in this skill's markdown files.

Purpose: keep the DOT/Mermaid snippets in references/, assets/diagrams/, and examples/ from rotting.

What it does: extracts fenced ```dot, ```mermaid, ```plantuml, and ```svg blocks from markdown files.
- dot: compiled with Graphviz `dot -Tsvg` when `dot` is on PATH (skipped with a notice otherwise).
- mermaid: rendered with Mermaid CLI (`mmdc`) when it is on PATH; otherwise only a cheap
  structural lint (known diagram keyword on the first line, balanced brackets/parentheses/
  braces/quotes outside of quoted labels) - NOT a real Mermaid parse. `mmdc` needs its headless
  Chrome; a "Could not find chrome-headless-shell" error is a setup problem, not a source error
  (see references/mermaid-patterns.md).
- plantuml: rendered with `plantuml -pipe` when `plantuml` (and a Java runtime) is on PATH, else
  skipped with a notice. A fragment without `@startuml` is wrapped first, because PlantUML
  silently renders nothing (exit 0) for input that lacks the markers.
- svg: parsed as XML (well-formedness only; render it to check the layout).
LaTeX/TikZ blocks are never compiled here.

Usage: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_diagram_sources.py [path ...]` (default: the whole bundle).
Exit status 1 if any checked block fails. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import xml.dom.minidom
import xml.parsers.expat
from pathlib import Path

FENCE_RE = re.compile(r"```(dot|mermaid|plantuml|svg)\n(.*?)```", re.S)
MERMAID_STARTS = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "erDiagram", "classDiagram", "gantt", "journey", "mindmap", "timeline",
)
OPEN, CLOSE = "([{", ")]}"


def extract_blocks(text: str) -> list[tuple[str, str]]:
    """Return (language, source) pairs for every dot/mermaid/plantuml/svg fence in text."""
    return [(m.group(1), m.group(2)) for m in FENCE_RE.finditer(text)]


def lint_mermaid(source: str) -> list[str]:
    """Return lint problems for a Mermaid source (empty list if it looks sane)."""
    lines = [ln for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines:
        return ["empty Mermaid block"]
    if not lines[0].strip().startswith(MERMAID_STARTS):
        return [f"unknown diagram type on first line: {lines[0].strip()!r}"]
    if lines[0].strip().startswith("erDiagram"):
        return []  # crow's-foot tokens (|o--o{) are deliberately unbalanced
    problems = []
    for n, line in enumerate(lines, 1):
        stripped = re.sub(r'"[^"]*"', '""', line)
        stripped = re.sub(r"--?\)", "", stripped)  # sequence async arrows -) and --)
        if stripped.count('"') % 2:
            problems.append(f"line {n}: unbalanced quote")
        stack = []
        for ch in stripped:
            if ch in OPEN:
                stack.append(ch)
            elif ch in CLOSE:
                if not stack or OPEN.index(stack.pop()) != CLOSE.index(ch):
                    problems.append(f"line {n}: mismatched {ch!r}")
                    break
        else:
            if stack and not any(w in line for w in ("subgraph",)):
                problems.append(f"line {n}: unclosed bracket")
    return problems


def check_dot(source: str) -> str | None:
    """Return an error string if `dot` rejects the source, else None."""
    result = subprocess.run(
        ["dot", "-Tsvg", "-o", "/dev/null"], input=source, text=True, capture_output=True
    )
    return result.stderr.strip() or "dot failed" if result.returncode else None


def check_mermaid(source: str, mmdc: str = "mmdc") -> str | None:
    """Return an error string if Mermaid CLI cannot render the source, else None."""
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.mmd", Path(tmp) / "out.svg"
        src.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [mmdc, "-q", "-i", str(src), "-o", str(out)], text=True, capture_output=True
        )
        if result.returncode or not out.exists():
            return (result.stderr.strip() or result.stdout.strip() or "mmdc failed")[:500]
    return None


def check_plantuml(source: str, plantuml: str = "plantuml") -> str | None:
    """Return an error string if PlantUML cannot render the source, else None."""
    if "@startuml" not in source:
        source = f"@startuml\n{source}@enduml\n"
    result = subprocess.run(
        [plantuml, "-tsvg", "-pipe"], input=source, text=True, capture_output=True
    )
    if result.returncode:
        return (result.stderr.strip() or "plantuml failed").replace("\n", " ")[:500]
    return None


def check_svg(source: str) -> str | None:
    """Return an error string if the SVG source is not well-formed XML, else None."""
    try:
        xml.dom.minidom.parseString(source)
    except xml.parsers.expat.ExpatError as exc:
        return f"SVG is not well-formed XML: {exc}"
    return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path, help="markdown files to check (default: every .md in the skill)")
    root = Path(__file__).resolve().parents[1]
    paths = ap.parse_args(argv).paths or sorted(root.rglob("*.md"))
    have_dot = shutil.which("dot") is not None
    if not have_dot:
        print("note: Graphviz `dot` not found; skipping DOT compilation")
    mmdc = shutil.which("mmdc")
    if not mmdc:
        print("note: Mermaid CLI `mmdc` not found; Mermaid blocks get the structural lint only")
    plantuml = shutil.which("plantuml")
    if not plantuml:
        print("note: `plantuml` not found; skipping PlantUML rendering")
    failures = checked = 0
    for path in paths:
        for lang, source in extract_blocks(path.read_text(encoding="utf-8")):
            checked += 1
            if lang == "dot":
                error = check_dot(source) if have_dot else None
                problems = [error] if error else []
            elif lang == "plantuml":
                error = check_plantuml(source, plantuml) if plantuml else None
                problems = [error] if error else []
            elif lang == "svg":
                error = check_svg(source)
                problems = [error] if error else []
            else:
                problems = lint_mermaid(source)
                if mmdc and not problems:
                    error = check_mermaid(source, mmdc)
                    problems = [error] if error else []
            for problem in problems:
                failures += 1
                print(f"{path}: {lang}: {problem}")
    print(f"Checked {checked} block(s); {failures} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
