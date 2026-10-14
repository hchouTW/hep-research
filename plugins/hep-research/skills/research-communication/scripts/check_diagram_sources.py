#!/usr/bin/env python3
"""Check the diagram sources embedded in this skill's markdown files.

Purpose: keep the DOT/Mermaid/PlantUML/SVG snippets in references/, assets/diagrams/, and examples/ from rotting, and
say exactly what was verified for each block.

What it does: extracts fenced ```dot, ```mermaid, ```plantuml, ```svg, ```tikz and ```latex (only when the block holds a
tikzpicture; a LaTeX code example is not a diagram) blocks from markdown files
and gives every block one outcome:
  rendered          the renderer produced a nonempty SVG from the source;
  lint-only         structural check only (a Mermaid source when `mmdc` is absent: keyword and bracket lint, NOT a real
                    parse; an SVG source: XML well-formedness only, never its appearance);
  skipped           no check was possible (DOT without `dot`, PlantUML without `plantuml`, TikZ/LaTeX without a TeX
                    engine or with --no-tikz);
  source-error      the renderer or the lint rejected the source (a parse or syntax error);
  environment-error the renderer could not do its job: not started, timed out, crashed at startup, or exited without
                    output. One preflight per renderer with a minimal diagram decides availability; a renderer that fails
                    its preflight, or times out on a block, is not launched again and its remaining blocks are
                    environment errors.
TikZ/LaTeX blocks are compiled with LuaLaTeX (else pdfLaTeX) in a standalone harness that loads tikz and
tikz-feynman (compat 1.1.0), as references/tikz-patterns.md does; a block with its own \\documentclass is compiled as it
is. LaTeX fences above a block in the same file that only set up (packages, \\tikzset styles) go into its preamble.
A missing package or class is an environment error, a TeX error in the block a source error. A fragment that cannot
compile alone carries a line '% diagram-check: skip <reason>' and is reported as skipped with that reason.
Rendering is not visual inspection: a rendered block may still have overlapping labels or a wrong layout, and nothing
here checks the physics a diagram shows.

Usage: `python3 <plugin root>/skills/research-communication/scripts/check_diagram_sources.py [path ...] [--format text|json]
        [--require-render] [--no-tikz]` (default paths: the whole bundle).
Exit codes: 2 a named file holds no diagram block (nothing was checked) or cannot be read; 1 at least one source error; 3 no source error but at least one environment error, or --require-render and
at least one block was not rendered (lint-only or skipped); 0 otherwise. Without --require-render, lint-only and
skipped blocks keep the previous behavior (exit 0) and are reported as such; they are never counted as rendered.
A renderer that does not finish within HEP_RENDER_TIMEOUT seconds (default 60) is an environment error; Mermaid's
`mmdc` starts Chromium, which can hang where Chromium cannot start. --format json prints one report object
(report_version 1.0.0) with per-block outcomes, renderer availability and versions, and reconciled counts.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.dom.minidom
import xml.parsers.expat
from pathlib import Path

FENCE_RE = re.compile(r"```(dot|mermaid|plantuml|svg|tikz|latex)\n(.*?)```", re.S)
MERMAID_STARTS = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "erDiagram", "classDiagram", "gantt", "journey", "mindmap", "timeline",
)
OPEN, CLOSE = "([{", ")]}"
OUTCOMES = ("rendered", "lint-only", "skipped", "source-error", "environment-error")
# Renderer stderr that names the source, and stderr that names the host; an unknown nonzero exit blames the source
# (a renderer that is running and rejects input is reporting on the input), never the environment by default.
SOURCE_PATTERNS = re.compile(r"parse error|syntax error|lexical error|expecting|unexpected|syntax is|unknown diagram", re.I)
ENV_PATTERNS = re.compile(r"chrom|could not find|failed to launch|enoent|spawn|cannot open display|no such file|"
                          r"command not found|java\.lang|unable to access jarfile|out of memory|killed|segmentation", re.I)
PREFLIGHT = {"dot": "digraph G { a -> b; }", "mmdc": "flowchart LR\n  A --> B\n", "plantuml": "@startuml\na -> b\n@enduml\n",
             "tex": "\\begin{tikzpicture}\\draw (0,0) -- (1,1);\\end{tikzpicture}\n"}
TEX_HARNESS = ("\\documentclass[tikz,border=2pt]{standalone}\n\\usepackage{tikz}\n"
               "\\usetikzlibrary{arrows.meta,positioning,shapes,calc,fit,backgrounds,decorations.pathmorphing}\n"
               "\\usepackage[compat=1.1.0]{tikz-feynman}\n")
PREAMBLE_LINE = re.compile(r"^\s*\\(?:usepackage|usetikzlibrary|usepgfplotslibrary|pgfplotsset|definecolor|tikzfeynmanset)\b")
TEX_ENV_ERROR = re.compile(r"File `[^']+\.(?:sty|cls|cfg|def)' not found|I can't find file|Font .* not found", re.I)


SKIP_DIRECTIVE = re.compile(r"^\s*%\s*diagram-check:\s*skip\b\s*(.*)$", re.M)


def extract_blocks(text: str) -> list[tuple[str, str]]:
    """Return (language, source) pairs for every dot/mermaid/plantuml/svg/tikz/latex fence in text."""
    return [(lang, src) for lang, src, _ in extract_blocks_with_setup(text)]


def extract_blocks_with_setup(text: str) -> list[tuple[str, str, str]]:
    """(language, source, setup) for every diagram fence; setup is the text of the LaTeX fences above it in the same file
    that set things up without drawing (package lines, \\tikzset styles), which a later snippet relies on."""
    out, setup = [], []
    for m in FENCE_RE.finditer(text):
        lang, src = m.group(1), m.group(2)
        if lang == "latex" and "tikzpicture" not in src:
            if "\\documentclass" not in src:
                setup.append(src)
            continue
        out.append((lang, src, "\n".join(setup) if lang in ("latex", "tikz") else ""))
    return out


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


RENDER_TIMEOUT = float(os.environ.get("HEP_RENDER_TIMEOUT", "60"))  # seconds per diagram and renderer


class RenderTimeout(Exception):
    """A renderer did not finish within RENDER_TIMEOUT; the diagram counts as an environment error, never as checked."""


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=RENDER_TIMEOUT, **kwargs)
    except subprocess.TimeoutExpired as exc:
        hint = " (mmdc starts Chromium: check that it can run here)" if "mmdc" in Path(cmd[0]).name else ""
        raise RenderTimeout(f"{Path(cmd[0]).name} did not finish within {RENDER_TIMEOUT:g} s{hint}") from exc


def _classify(returncode: int, stderr: str, tool: str) -> dict:
    text = (stderr or "").strip()
    if SOURCE_PATTERNS.search(text):
        return {"outcome": "source-error", "reason": text[:500] or f"{tool} failed"}
    if ENV_PATTERNS.search(text) or returncode < 0:
        return {"outcome": "environment-error", "reason": (text or f"{tool} exited {returncode}")[:500]}
    return {"outcome": "source-error", "reason": (text or f"{tool} failed (exit {returncode})")[:500]}


def render_dot(source: str, dot: str = "dot") -> dict:
    """{"outcome", "reason", "output_format"} for one DOT source through Graphviz."""
    try:
        result = _run([dot, "-Tsvg"], input=source)
    except RenderTimeout as exc:
        return {"outcome": "environment-error", "reason": str(exc), "timeout": True}
    except OSError as exc:
        return {"outcome": "environment-error", "reason": f"cannot start {dot}: {exc}"}
    if result.returncode:
        return _classify(result.returncode, result.stderr, "dot")
    if not result.stdout.strip():
        return {"outcome": "environment-error", "reason": "dot exited 0 but produced no output"}
    return {"outcome": "rendered", "reason": None, "output_format": "svg"}


def render_mermaid(source: str, mmdc: str = "mmdc") -> dict:
    """{"outcome", "reason", "output_format"} for one Mermaid source through the Mermaid CLI."""
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.mmd", Path(tmp) / "out.svg"
        src.write_text(source, encoding="utf-8")
        try:
            result = _run([mmdc, "-q", "-i", str(src), "-o", str(out)])
        except RenderTimeout as exc:
            return {"outcome": "environment-error", "reason": str(exc), "timeout": True}
        except OSError as exc:
            return {"outcome": "environment-error", "reason": f"cannot start {mmdc}: {exc}"}
        if result.returncode:
            return _classify(result.returncode, result.stderr or result.stdout, "mmdc")
        if not out.exists() or not out.read_bytes().strip():
            return {"outcome": "environment-error", "reason": "mmdc exited 0 but produced no output"}
    return {"outcome": "rendered", "reason": None, "output_format": "svg"}


def render_plantuml(source: str, plantuml: str = "plantuml") -> dict:
    """{"outcome", "reason", "output_format"} for one PlantUML source. A fragment without @startuml is wrapped first,
    because PlantUML silently renders nothing (exit 0) for input that lacks the markers."""
    if "@startuml" not in source:
        source = f"@startuml\n{source}@enduml\n"
    try:
        result = _run([plantuml, "-tsvg", "-pipe"], input=source)
    except RenderTimeout as exc:
        return {"outcome": "environment-error", "reason": str(exc), "timeout": True}
    except OSError as exc:
        return {"outcome": "environment-error", "reason": f"cannot start {plantuml}: {exc}"}
    if result.returncode:
        return _classify(result.returncode, (result.stderr or "plantuml failed").replace("\n", " "), "plantuml")
    if not result.stdout.strip():
        return {"outcome": "environment-error", "reason": "plantuml exited 0 but produced no output"}
    return {"outcome": "rendered", "reason": None, "output_format": "svg"}


def tex_document(source: str, setup: str = "") -> str:
    """A compilable document for one block: as is when it has a \\documentclass, else the standalone harness with the
    file's setup fences and the block's package lines in the preamble."""
    if "\\documentclass" in source:
        return source
    pre = [ln for ln in setup.splitlines()] + [ln for ln in source.splitlines() if PREAMBLE_LINE.match(ln)]
    body = [ln for ln in source.splitlines() if not PREAMBLE_LINE.match(ln)]
    if "tikzpicture" not in source:  # a ```tikz fence may hold only the picture's body
        body = ["\\begin{tikzpicture}"] + body + ["\\end{tikzpicture}"]
    return TEX_HARNESS + "\n".join(pre) + "\n\\begin{document}\n" + "\n".join(body) + "\n\\end{document}\n"


def render_tex(source: str, engine: str = "lualatex", setup: str = "") -> dict:
    """{"outcome", "reason", "output_format"} for one TikZ/LaTeX block compiled to PDF (no shell escape)."""
    with tempfile.TemporaryDirectory() as tmp:
        tex = Path(tmp) / "block.tex"
        tex.write_text(tex_document(source, setup), encoding="utf-8")
        try:
            result = _run([engine, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "block.tex"], cwd=tmp)
        except RenderTimeout as exc:
            return {"outcome": "environment-error", "reason": str(exc), "timeout": True}
        except OSError as exc:
            return {"outcome": "environment-error", "reason": f"cannot start {engine}: {exc}"}
        log = (Path(tmp) / "block.log").read_text(encoding="utf-8", errors="replace") if (Path(tmp) / "block.log").exists() else result.stdout
        if result.returncode == 0 and (Path(tmp) / "block.pdf").is_file():
            return {"outcome": "rendered", "reason": None, "output_format": "pdf"}
        first = next((ln.strip() for ln in log.splitlines() if ln.startswith("!")), None) or (result.stdout or "")[-300:]
        if TEX_ENV_ERROR.search(log):
            return {"outcome": "environment-error", "reason": TEX_ENV_ERROR.search(log).group(0)[:300]}
        return {"outcome": "source-error", "reason": f"{Path(engine).name}: {first}"[:500]}


def check_dot(source: str) -> str | None:
    """Return an error string if `dot` rejects the source, else None (rendered)."""
    r = render_dot(source)
    return None if r["outcome"] == "rendered" else r["reason"]


def check_mermaid(source: str, mmdc: str = "mmdc") -> str | None:
    """Return an error string if Mermaid CLI cannot render the source, else None (rendered)."""
    r = render_mermaid(source, mmdc)
    return None if r["outcome"] == "rendered" else r["reason"]


def check_plantuml(source: str, plantuml: str = "plantuml") -> str | None:
    """Return an error string if PlantUML cannot render the source, else None (rendered)."""
    r = render_plantuml(source, plantuml)
    return None if r["outcome"] == "rendered" else r["reason"]


def check_svg(source: str) -> str | None:
    """Return an error string if the SVG source is not well-formed XML, else None (well-formed, not rendered)."""
    try:
        xml.dom.minidom.parseString(source)
    except xml.parsers.expat.ExpatError as exc:
        return f"SVG is not well-formed XML: {exc}"
    return None


def _version(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, text=True, capture_output=True, timeout=min(RENDER_TIMEOUT, 30))
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = next((ln.strip() for ln in (r.stdout + "\n" + r.stderr).splitlines() if ln.strip()), None)
    return line[:120] if line else None


def preflight_renderers(tikz: bool = True) -> dict:
    """One minimal render per renderer on PATH: {"dot"|"mmdc"|"plantuml"|"tex": {"available", "path", "version",
    "reason"}}. A renderer that fails its preflight is unavailable for the run and is not launched again. "tex" is
    LuaLaTeX, else pdfLaTeX; with tikz=False it is not looked for."""
    out = {}
    engine = shutil.which("lualatex") or shutil.which("pdflatex")
    if not tikz:
        out["tex"] = {"available": False, "path": None, "version": None, "reason": "TikZ compile switched off (--no-tikz)"}
    elif not engine:
        out["tex"] = {"available": False, "path": None, "version": None, "reason": "neither `lualatex` nor `pdflatex` on PATH"}
    else:
        r = render_tex(PREFLIGHT["tex"], engine)
        ok = r["outcome"] == "rendered"
        out["tex"] = {"available": ok, "path": engine, "version": _version([engine, "--version"]) if ok else None,
                      "reason": None if ok else f"preflight compile failed ({r['reason']}); not launched again"}
    for name, render, vcmd in (("dot", render_dot, ["-V"]), ("mmdc", render_mermaid, ["--version"]), ("plantuml", render_plantuml, ["-version"])):
        path = shutil.which(name)
        if not path:
            out[name] = {"available": False, "path": None, "version": None, "reason": f"`{name}` not on PATH"}
            continue
        r = render(PREFLIGHT[name], path)
        ok = r["outcome"] == "rendered"
        out[name] = {"available": ok, "path": path, "version": _version([path] + vcmd) if ok else None,
                     "reason": None if ok else f"preflight render failed ({r['reason']}); not launched again"}
    return out


def check_block(lang: str, source: str, renderers: dict, setup: str = "") -> dict:
    """Outcome of one block given the renderer states (which this function may update on a timeout). A block with a
    '% diagram-check: skip <reason>' line (a fragment that cannot compile alone, such as a Beamer overlay) is skipped
    with that reason."""
    directive = SKIP_DIRECTIVE.search(source)
    if directive:
        return {"outcome": "skipped", "renderer": None, "reason": "marked in the source: " + (directive.group(1).strip() or "no reason given")}
    def unavailable(name: str) -> dict:
        state = renderers[name]
        if state["path"] is None:
            return {"outcome": "skipped", "renderer": None, "reason": state["reason"]}
        return {"outcome": "environment-error", "renderer": name, "reason": state["reason"]}

    def through(name: str, render) -> dict:
        state = renderers[name]
        if not state["available"]:
            return unavailable(name)
        r = render(source, state["path"])
        if r.get("timeout"):
            state["available"] = False
            state["reason"] = f"{r['reason']}; not launched again for the remaining blocks"
        return {"outcome": r["outcome"], "renderer": name, "reason": r["reason"], "output_format": r.get("output_format")}

    if lang == "dot":
        return through("dot", render_dot)
    if lang == "plantuml":
        return through("plantuml", render_plantuml)
    if lang == "svg":
        err = check_svg(source)
        return {"outcome": "source-error" if err else "lint-only", "renderer": "xml",
                "reason": err or "XML well-formedness only; the SVG was not rendered or looked at"}
    if lang in ("tikz", "latex"):
        return through("tex", lambda src, path: render_tex(src, path, setup))
    problems = lint_mermaid(source)
    if problems:
        return {"outcome": "source-error", "renderer": "lint", "reason": "; ".join(problems)}
    if not renderers["mmdc"]["available"]:
        r = unavailable("mmdc")
        if r["outcome"] == "skipped":
            r.update(outcome="lint-only", renderer="lint", reason="structural lint only (keyword and brackets), not a Mermaid parse: " + renderers["mmdc"]["reason"])
        return r
    return through("mmdc", render_mermaid)


def run(paths: list[Path], require_render: bool = False, tikz: bool = True) -> dict:
    renderers = preflight_renderers(tikz)
    blocks = []
    for path in paths:
        for i, (lang, source, setup) in enumerate(extract_blocks_with_setup(path.read_text(encoding="utf-8"))):
            r = check_block(lang, source, renderers, setup)
            blocks.append({"file": str(path), "block": i, "lang": lang, "renderer": r.get("renderer"), "outcome": r["outcome"],
                           "reason": r.get("reason"), "output_format": r.get("output_format")})
    counts = {o: sum(1 for b in blocks if b["outcome"] == o) for o in OUTCOMES}
    counts["total"] = len(blocks)
    not_rendered = counts["lint-only"] + counts["skipped"]
    if not blocks:
        status, code = "input-error", 2
    elif counts["source-error"]:
        status, code = "fail", 1
    elif counts["environment-error"] or (require_render and not_rendered):
        status, code = "incomplete", 3
    else:
        status, code = "pass", 0
    checks_not_run = [{"check": "visual-inspection", "reason": "rendering says nothing about layout or labels; look at the output", "required": False},
                      {"check": "physics-content", "reason": "what a diagram shows is reviewed by hep-theory or the owning skill", "required": False}]
    if not blocks:
        checks_not_run.append({"check": "render", "reason": "no diagram block in the named files: nothing was checked", "required": True})
    if not_rendered:
        checks_not_run.append({"check": "render", "reason": f"{not_rendered} block(s) were linted or skipped, not rendered",
                               "required": bool(require_render)})
    return {"report_version": "1.0.0", "tool": "check_diagram_sources", "status": status, "exit_code": code,
            "scope": {"files": [str(p) for p in paths], "require_render": require_render, "timeout_s": RENDER_TIMEOUT},
            "renderers": renderers, "blocks": blocks, "counts": counts, "visual_inspection": "not-performed",
            "checks_run": ["extract", "preflight"] + sorted({b["renderer"] for b in blocks if b["renderer"]}),
            "checks_not_run": checks_not_run,
            "note": "a rendered block is a renderer's acceptance of the source, not a visual or scientific check"}


def print_text(rep: dict) -> None:
    for name, st in rep["renderers"].items():
        if not st["available"]:
            print(f"note: {name}: {st['reason']}")
        elif st["version"]:
            print(f"note: {name}: {st['version']}")
    for b in rep["blocks"]:
        if b["outcome"] in ("source-error", "environment-error"):
            print(f"{b['file']}: {b['lang']} (block {b['block']}): {b['outcome']}: {b['reason']}")
    c = rep["counts"]
    print(f"Checked {c['total']} block(s): {c['rendered']} rendered, {c['lint-only']} lint-only, {c['skipped']} skipped, "
          f"{c['source-error']} source error(s), {c['environment-error']} environment error(s). Visual inspection: not performed.")
    print(f"Status: {rep['status']} (exit {rep['exit_code']}).")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path, help="markdown files to check (default: every .md in the skill)")
    ap.add_argument("--format", choices=("text", "json"), default="text", help="text (default) or one JSON report object")
    ap.add_argument("--require-render", action="store_true",
                    help="strict: a block that was only linted or skipped makes the run incomplete (exit 3)")
    ap.add_argument("--no-tikz", action="store_true", help="do not compile TikZ/LaTeX blocks (they are reported as skipped)")
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    paths = args.paths or sorted(root.rglob("*.md"))
    rep = run(paths, args.require_render, tikz=not args.no_tikz)
    if args.format == "json":
        print(json.dumps(rep, indent=1))
    else:
        print_text(rep)
    return rep["exit_code"]


if __name__ == "__main__":
    import sys as _sys
    try:
        raise SystemExit(main(sys.argv[1:]))
    except OSError as _exc:  # a missing or unreadable input: one line, no traceback
        print(f"check_diagram_sources.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2) from None
