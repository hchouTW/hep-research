#!/usr/bin/env python3
"""
check_manuscript.py -- read-only pre-submission checker for a LaTeX manuscript.

Scans a directory of .tex and .bib files and reports, without modifying
anything:
  - citation keys (\\cite, \\citep/\\citet/\\citeauthor/..., biblatex \\parencite/
    \\textcite/\\autocite/..., \\nocite) that do not resolve to any bibliography
    entry: a .bib file, an inline thebibliography (\\bibitem), or a built .bbl.
    Citations with no bibliography at all are missing, not skipped. A
    bibliography produced by an external build step is declared with
    --external-bib; keys found nowhere locally are then reported as unresolved
    (exit code 3), never as verified
  - .bib entries that are never cited (\\nocite{*} marks all as cited)
  - .bib keys defined more than once (BibTeX "Repeated entry"; case-insensitive)
  - \\label{...} keys defined more than once
  - \\ref / \\eqref / \\autoref / \\pageref / \\nameref / \\cref-family targets
    with no matching \\label{} (\\cref{a,b} lists are split)
  - leftover TODO / FIXME / XXX / placeholder markers

With --style, two advisory typography checks are also reported (they can flag
correct text, so they never change the exit code):
  - \\ref / \\eqref after a label word (Fig., Table, Eq., Section, ...) and a
    plain space ("Fig. \\ref{a}"), where a tie
    ("Fig.~\\ref{a}") keeps the label and number on one line
  - a number followed by a unit with no space or a plain space ("125GeV",
    "125 GeV"), where "125~GeV", "125\\,GeV" or siunitx keeps them together

LaTeX comments (unescaped % to end of line) are ignored, except that TODO
markers are still reported inside comments; % inside \\url, \\href and \\path
arguments is literal. \\iffalse ... \\fi blocks, the comment environment,
verbatim bodies and \\verb are not scanned. A command's argument may wrap
onto the next line; optional arguments may nest brackets and braces, and the
biblatex multicite commands (\\cites, \\textcites, ...) are read group by
group. .bib files are read by brace depth: an entry inside a field or an
@comment is not an entry, and a crossref parent counts as cited.

Two modes, neither a compile nor a check of scientific content:
  - directory mode (positional DIR): a repository-wide source scan that merges
    every .tex, .bib and .bbl under DIR. A label in any file satisfies a
    reference in any other, so a backup or an unused file can mask a missing
    reference; use it for a quick sweep of one paper's folder.
  - main mode (--main MAIN.tex): a selected-document scan. Only the files MAIN
    reaches through literal \\input (braced or plain-TeX \\input name), \\include,
    \\subfile and \\import are scanned;
    their names are resolved against --build-root (default: MAIN's folder), as
    TeX does, never against the including file's folder, and nothing outside
    --project-root (default: the build root) is opened. Only the bibliography
    the document declares (\\bibliography{...}, \\addbibresource{...}, an inline
    thebibliography) counts; a built .bbl counts only when associated with
    --bbl, because a file name or a timestamp does not prove it was built from
    this document. What the scanner cannot follow (a macro-generated file name,
    an include inside a conditional, \\includeonly, a missing include or .bib,
    a file outside the root, an include cycle) is reported as incomplete
    coverage, never guessed.

Standard library only. Intended to be run near the end of a drafting session,
not after every edit.

Usage:
    python3 check_manuscript.py <path-to-manuscript-dir> [--strict] [--format text|json]
    python3 check_manuscript.py --main MAIN.tex [--build-root DIR] [--project-root DIR] [--bbl FILE.bbl]
                                [--strict] [--format text|json]

Exit codes: 0 no issue found by the requested checks (no certificate of
correctness); 1 at least one confirmed issue; 2 invalid invocation or no
manuscript input (an empty directory is not a clean manuscript); 3 nothing
confirmed wrong but a required check is incomplete: citations deferred to a
declared external bibliography (--external-bib), citations that only a built
or missing bibliography could resolve, or includes the scanner could not
follow in main mode. --strict also treats "unused .bib entry" as an issue for
exit-code purposes (by default it is reported but does not affect the exit
code, since a shared/collaboration .bib file legitimately contains more
entries than any single paper cites). --format json prints one report object
(report_version 1.0.0) with findings, coverage and the checks run and not run.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.protected.guard import protected_main  # noqa: E402

# Any natbib/biblatex/plain citation command (\cite, \citep, \Citet, \citeauthor,
# \parencite, \textcite, \autocite, \footcite, \nocite, ...). Arguments are read by
# scan_citations: optional [..] arguments may nest brackets and braces, and the
# biblatex multicite commands (\cites, \textcites, ...) take repeated groups.
CITE_CMD_RE = re.compile(r"\\([A-Za-z]*[Cc]ite[A-Za-z]*)\*?")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(ref|eqref|autoref|pageref|nameref|vref|Vref|cref|Cref|cpageref|Cpageref|labelcref)\*?\{([^}]+)\}")
MULTI_REF_CMDS = {"cref", "Cref", "cpageref", "Cpageref", "labelcref", "vref", "Vref"}
BIB_AT_RE = re.compile(r"@(\w+)\s*([{(])")
CROSSREF_RE = re.compile(r"\bcrossref\s*=\s*[{\"]?\s*([^,}\"\s]+)", re.I)
BIBITEM_RE = re.compile(r"\\bibitem\s*(?:\[[^\]]*\]\s*)?\{([^}]+)\}")
BBL_ENTRY_RE = re.compile(r"\\entry\{([^}]+)\}")  # biblatex .bbl
NON_ENTRY_TYPES = {"string", "comment", "preamble"}
COMMENT_RE = re.compile(r"(?<!\\)%.*")
# Upper-case TODO/FIXME/XXX only: lower-case "xxx" is a common template placeholder
# ("fontset=xxx"). "(?<!\\)" skips a macro name such as "\newcommand\TODO"; a
# \todo{...} call (todonotes) is still a marker.
TODO_RE = re.compile(r"(?<!\\)\b(?:TODO|FIXME|XXX)\b|(?i:\\todo(?:\[[^\]]*\])?\{|\[VALUE NEEDED[^\]]*\]|\[CITATION NEEDED[^\]]*\])")
PLACEHOLDER_RE = re.compile(r"lorem ipsum|\?\?\?|\[FIGURE HERE\]|\[TABLE HERE\]", re.IGNORECASE)
# Advisory --style checks.
# Only after a label word ("Fig. \ref", "Table \ref"), not "and \ref" or "in \eqref",
# which gave most false positives on real arXiv sources.
LABEL_WORDS = (r"(?:Fig(?:ure)?s?|Tab(?:le)?s?|Eqs?|Equations?|Sec(?:tion)?s?|App(?:endix|endices)?"
               r"|Chap(?:ter)?s?|Refs?|Lines?|Algorithms?|Propositions?|Theorems?|Lemmas?"
               r"|Corollar(?:y|ies)|Definitions?)")
REF_NO_TIE_RE = re.compile(r"\b" + LABEL_WORDS + r"\.?[ \t\n]+\\(?:ref|eqref)\{", re.IGNORECASE)
UNITS = r"(?:[kMGTPE]?eV|[kMGT]?V|[kMG]?Hz|[mcnk]m|[mnµ]s|fb|pb|nb)"
# Not after "=", "{" or "-" (TikZ/option lengths such as right=2.5cm, \vspace{-2mm}).
UNIT_NO_TIE_RE = re.compile(r"(?<![\w.\\{=\-])\d+(?:\.\d+)? ?" + UNITS + r"\b")
# Lines that set layout lengths, not physics quantities.
LAYOUT_LINE_RE = re.compile(r"\\(?:[vh]space|[vh]skip|vertex|node|draw|includegraphics|setlength|addvspace)"
                            r"|(?:sep|width|height|distance)\s*=")
DEFINITION_RE = re.compile(r"\\(?:(?:re|provide)?newcommand|DeclareRobustCommand|def)\b")
# Main mode: literal include mechanisms the scanner follows, and the ones it only reports.
INPUT_RE = re.compile(r"\\(input|include|subfile|InputIfFileExists)\s*\{([^}]*)\}")
# Plain-TeX form without braces: \input sec1 (the name ends at a space, brace, backslash or comment sign).
INPUT_BARE_RE = re.compile(r"\\(input|include)(?![A-Za-z@])\s+([^\s\\{}%]+)")
IMPORT_RE = re.compile(r"\\(?:sub)?import\s*\{([^}]*)\}\s*\{([^}]*)\}")
INCLUDEONLY_RE = re.compile(r"\\includeonly\s*\{([^}]*)\}")
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{([^}]*)\}")
ADDBIBRESOURCE_RE = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\])?\{([^}]*)\}")
THEBIBLIOGRAPHY_RE = re.compile(r"\\begin\{thebibliography\}")
COND_RE = re.compile(r"\\(newif\s*\\if[A-Za-z@]*|if[A-Za-z@]*|else\b|fi\b)")
VERBATIM_RE = re.compile(r"\\begin\{(verbatim\*?|Verbatim|lstlisting|minted|alltt|comment)\}.*?\\end\{\1\}", re.S)
IFFALSE_RE = re.compile(r"\\iffalse(?![A-Za-z@])")
URL_ARG_RE = re.compile(r"\\(?:url|href|path)\s*\{")
VERB_RE = re.compile(r"\\verb\*?([^A-Za-z\s*])")
TEX_SUFFIXES = (".tex", ".ltx", ".latex")


def strip_verbatim(text: str) -> str:
    """Blank what TeX typesets or skips but does not execute, keeping line count: verbatim and listing bodies, the
    comment environment and \\iffalse ... \\fi blocks (their \\cite, \\label and \\input do not count)."""
    text = VERBATIM_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    out, pos = [], 0
    for m in IFFALSE_RE.finditer(text):
        if m.start() < pos:
            continue
        depth, end = 0, None
        for c in COND_RE.finditer(text, m.start()):
            tok = c.group(1)
            if tok.startswith("newif"):
                continue
            if tok.startswith("if"):
                depth += 1
            elif tok.startswith("fi"):
                depth -= 1
                if depth == 0:
                    end = c.end()
                    break
        end = len(text) if end is None else end
        out.append(text[pos:m.start()])
        out.append("\n" * text.count("\n", m.start(), end))
        pos = end
    out.append(text[pos:])
    return "".join(out)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _tex_candidates(name: str, build_root: Path) -> list[Path]:
    """The files TeX would try for \\input{name}: name.tex first (unless the name already ends in .tex), then name itself."""
    cand = build_root / name
    if name.endswith(".tex"):
        return [cand]
    return [cand.with_name(cand.name + ".tex"), cand]


def _tex_candidate(name: str, build_root: Path) -> Path:
    """The first existing candidate, else the .tex candidate (for the message)."""
    cands = _tex_candidates(name, build_root)
    return next((c for c in cands if c.is_file()), cands[0])


def discover_manuscript_files(main: Path, project_root: Path, build_root: Path) -> dict:
    """The files a main document reaches through literal includes, resolved against the build root and bounded by
    the project root. Returns {"main", "files": [Path, ...] in inclusion order, "unresolved": [{"file", "line",
    "kind", "raw", "reason"}], "bib_files": [Path], "bib_declared": bool, "inline_bibliography": bool,
    "coverage": "complete" | "incomplete"}. Kinds: macro-generated, conditional, includeonly, missing, outside-root,
    cycle, missing-bib, outside-root-bib. A conditional include is scanned and flagged: the branch taken is unknown.
    Nothing outside the project root is opened."""
    main, project_root, build_root = Path(main).resolve(), Path(project_root).resolve(), Path(build_root).resolve()
    files: list[Path] = []
    unresolved: list[dict] = []
    bib_files: list[Path] = []
    state = {"bib_declared": False, "inline": False}

    def add(file: Path, line: int, kind: str, raw: str, reason: str) -> None:
        unresolved.append({"file": str(file), "line": line, "kind": kind, "raw": raw, "reason": reason})

    def resolve(file: Path, line: int, raw: str, directory: str = "") -> Path | None:
        name = (directory + raw).strip()
        if "\\" in name or "#" in name:
            add(file, line, "macro-generated", raw, "file name is produced by a macro; the scanner does not expand TeX")
            return None
        cand = _tex_candidate(name, build_root)
        res = cand.resolve()
        if not _inside(res, project_root):
            add(file, line, "outside-root", raw, f"resolves outside the project root {project_root}; not opened")
            return None
        if not res.is_file():
            _missing(file, line, raw, res)
            return None
        return res

    def _missing(file: Path, line: int, raw: str, res: Path) -> bool:
        add(file, line, "missing", raw, f"{res} does not exist (resolved against the build root {build_root})")
        return True

    def visit(file: Path, stack: tuple) -> None:
        files.append(file)
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            add(file, 0, "unreadable", str(file), str(exc))
            return
        code = strip_verbatim(strip_comments(text))
        for m in INCLUDEONLY_RE.finditer(code):
            add(file, line_of(code, m.start()), "includeonly", m.group(1), "\\includeonly restricts \\include; not applied")
        cond = _conditional_depths(code)
        for m in BIBLIOGRAPHY_RE.finditer(code):
            state["bib_declared"] = True
            for raw in split_keys(m.group(1)):
                cand = build_root / raw
                cand = cand if cand.suffix == ".bib" else cand.with_name(cand.name + ".bib")
                res = cand.resolve()
                if not _inside(res, project_root):
                    add(file, line_of(code, m.start()), "outside-root-bib", raw, "bibliography resolves outside the project root; not opened")
                elif not res.is_file():
                    add(file, line_of(code, m.start()), "missing-bib", raw, f"{res} does not exist")
                elif res not in bib_files:
                    bib_files.append(res)
        for m in ADDBIBRESOURCE_RE.finditer(code):
            state["bib_declared"] = True
            res = (build_root / m.group(1).strip()).resolve()
            if not _inside(res, project_root):
                add(file, line_of(code, m.start()), "outside-root-bib", m.group(1), "bibliography resolves outside the project root; not opened")
            elif not res.is_file():
                add(file, line_of(code, m.start()), "missing-bib", m.group(1), f"{res} does not exist")
            elif res not in bib_files:
                bib_files.append(res)
        if THEBIBLIOGRAPHY_RE.search(code):
            state["inline"] = True
        includes = [(m.start(), m.group(1), m.group(2), "") for m in INPUT_RE.finditer(code)]
        includes += [(m.start(), m.group(1), m.group(2), "") for m in INPUT_BARE_RE.finditer(code)]
        includes += [(m.start(), "import", m.group(2), m.group(1)) for m in IMPORT_RE.finditer(code)]
        for pos, cmd, raw, directory in sorted(includes):
            line = line_of(code, pos)
            if cond(pos) > 0:
                add(file, line, "conditional", raw, "include inside \\if...\\fi: the branch taken is unknown; scanned anyway")
            if cmd == "InputIfFileExists":
                cand = _tex_candidate((directory + raw).strip(), build_root).resolve()
                if not cand.is_file() or not _inside(cand, project_root):
                    continue  # optional by construction
            res = resolve(file, line, raw, directory)
            if res is None:
                continue
            if res in stack:
                add(file, line, "cycle", raw, f"{res.name} is already being included: {[p.name for p in stack]}")
                continue
            if res in files:
                continue  # included twice (a diamond): scanned once
            visit(res, stack + (res,))

    if not main.is_file():
        add(main, 0, "missing", str(main), "main document does not exist")
    elif not _inside(main, project_root):
        add(main, 0, "outside-root", str(main), "main document lies outside the project root; not opened")
    else:
        visit(main, (main,))
    return {"main": main, "files": files, "unresolved": unresolved, "bib_files": bib_files,
            "bib_declared": state["bib_declared"], "inline_bibliography": state["inline"],
            "coverage": "incomplete" if unresolved else "complete"}


def _conditional_depths(code: str):
    """A function giving the \\if...\\fi nesting depth at a character offset (\\newif declarations do not count)."""
    events = []
    depth = 0
    for m in COND_RE.finditer(code):
        tok = m.group(1)
        if tok.startswith("newif"):
            continue
        if tok.startswith("if"):
            depth += 1
        elif tok.startswith("fi"):
            depth = max(depth - 1, 0)
        events.append((m.start(), depth))

    def at(pos: int) -> int:
        d = 0
        for start, dep in events:
            if start > pos:
                break
            d = dep
        return d
    return at


def split_keys(raw: str):
    # Keys containing '#' are macro parameters inside a \newcommand body (\ref{#1}).
    return [k.strip() for k in raw.split(",") if k.strip() and "#" not in k]


def _strip_comment_line(line: str) -> str:
    """One line without its comment: % is literal inside \\url, \\href and \\path arguments, and a \\verb body is
    blanked (typeset, never scanned)."""
    out, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\":
            m = URL_ARG_RE.match(line, i)
            if m:
                depth, j = 1, m.end()
                while j < n and depth:
                    depth += {"{": 1, "}": -1}.get(line[j], 0)
                    j += 1
                out.append(line[i:j])
                i = j
                continue
            m = VERB_RE.match(line, i)
            if m:
                close = line.find(m.group(1), m.end())
                j = n if close < 0 else close + 1
                out.append(" " * (j - i))
                i = j
                continue
            out.append(line[i:i + 2])
            i += 2
            continue
        if ch == "%":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def strip_comments(text: str) -> str:
    """Drop LaTeX comments (unescaped % to end of line), keeping the line count."""
    return "\n".join(_strip_comment_line(line) for line in text.split("\n"))


def _balanced(text: str, i: int, open_ch: str, close_ch: str) -> int | None:
    """End offset (exclusive) of the group opening at text[i], counting nested braces and the group's own delimiter."""
    j, n = i, len(text)
    stack: list[str] = []
    while j < n:
        ch = text[j]
        if ch == "\\":
            j += 2
            continue
        if ch in "{[(" and (ch == "{" or ch == open_ch):
            stack.append(ch)
        elif ch in "}])" and stack and {"}": "{", "]": "[", ")": "("}[ch] == stack[-1]:
            stack.pop()
            if not stack:
                return j + 1
        j += 1
    return None


def scan_citations(code: str):
    """(offset, [keys]) for each citation command: optional [..] arguments may nest; a multicite command (name ending
    in 'cites') takes repeated ([..])([..]){keys} groups and optional (..) global notes."""
    for m in CITE_CMD_RE.finditer(code):
        multi = m.group(1).lower().endswith("cites")
        i, n, keys, groups = m.end(), len(code), [], 0
        while i < n:
            while i < n and code[i] in " \t\n":
                i += 1
            if i >= n:
                break
            ch = code[i]
            if ch == "[" or (ch == "(" and multi):
                end = _balanced(code, i, ch, {"[": "]", "(": ")"}[ch])
                if end is None:
                    break
                i = end
                continue
            if ch == "{":
                end = _balanced(code, i, "{", "}")
                if end is None:
                    break
                keys += split_keys(code[i + 1:end - 1])
                groups += 1
                i = end
                if multi:
                    continue
            break
        if groups:
            yield m.start(), keys


def iter_bib_entries(text: str):
    """(type, key, offset, body) for each BibTeX entry at brace depth 0; @comment, @preamble and @string bodies and
    anything inside a field are skipped, so an '@misc{' in a note is not an entry."""
    i, n = 0, len(text)
    while i < n:
        m = BIB_AT_RE.search(text, i)
        if not m:
            return
        end = _balanced(text, m.end() - 1, m.group(2), {"{": "}", "(": ")"}[m.group(2)])
        end = n if end is None else end
        body = text[m.end():end - 1]
        kind = m.group(1).lower()
        if kind not in NON_ENTRY_TYPES:
            key = body.split(",", 1)[0].strip()
            if key and "," in body:
                yield kind, key, m.start(), body
        i = end


_LINE_CACHE: list = [None, []]  # (text, newline offsets) of the last text asked about


def line_of(text: str, offset: int) -> int:
    """1-based line of an offset; newline offsets are computed once per text, so a scan is not quadratic."""
    if _LINE_CACHE[0] is not text:
        _LINE_CACHE[0], _LINE_CACHE[1] = text, [i for i, ch in enumerate(text) if ch == "\n"]
    return bisect.bisect_left(_LINE_CACHE[1], offset) + 1


def find_tex_and_bib(root: Path):
    tex_files = sorted(root.rglob("*.tex"))
    bib_files = sorted(root.rglob("*.bib"))
    return tex_files, bib_files


def scan(root: Path, external_bib: str | None = None):
    """Directory mode: every .tex, .bib and .bbl under root, merged (a repository-wide source scan)."""
    tex_files, bib_files = find_tex_and_bib(root)
    bbl_files = sorted(root.rglob("*.bbl"))
    results = scan_files(tex_files, bib_files, bbl_files, external_bib)
    results["mode"] = "directory"
    return results


def scan_main(main: Path, project_root: Path, build_root: Path, external_bib: str | None = None, bbl: Path | None = None):
    """Main mode: the files the selected document includes (discover_manuscript_files), the bibliography it declares,
    and a built .bbl only when explicitly associated. Unassociated .bbl files in the build root, a declared but missing
    .bib, or an external bibliography leave citations unresolved rather than missing or verified."""
    disc = discover_manuscript_files(main, project_root, build_root)
    bbl_files = [Path(bbl).resolve()] if bbl else []
    results = scan_files(disc["files"], disc["bib_files"], bbl_files, external_bib)
    results["mode"] = "main"
    results["discovery"] = disc
    results["unassociated_bbl"] = sorted(p for p in Path(build_root).resolve().glob("*.bbl") if p not in bbl_files)
    missing_bib_declared = any(u["kind"] in ("missing-bib", "outside-root-bib") for u in disc["unresolved"])
    if results["missing_bib"] and (results["unassociated_bbl"] or missing_bib_declared):
        reason = ("a built bibliography is present but not associated with this document (pass --bbl to use it)"
                  if results["unassociated_bbl"] else "a declared bibliography file is missing or outside the root")
        results["unresolved_citations"] = {**results["unresolved_citations"], **results["missing_bib"]}
        results["missing_bib"] = {}
        results["no_bibliography"] = False
        results["unresolved_reason"] = reason
    return results


def scan_files(tex_files, bib_files, bbl_files=(), external_bib: str | None = None):
    tex_files, bib_files, bbl_files = list(tex_files), list(bib_files), list(bbl_files)
    inline_entries = set()

    cite_keys = defaultdict(list)   # key -> [(file, line)]
    label_defs = defaultdict(list)  # label -> [(file, line)]
    ref_targets = defaultdict(list)  # label -> [(file, line)]
    todos = []      # (file, line, text)
    placeholders = []  # (file, line, text)

    for tex in tex_files:
        text = tex.read_text(encoding="utf-8", errors="replace")
        code = strip_verbatim(strip_comments(text))
        inline_entries.update(m.group(1).strip() for m in BIBITEM_RE.finditer(code))
        for pos, keys in scan_citations(code):
            for key in keys:
                cite_keys[key].append((tex, line_of(code, pos)))
        for m in LABEL_RE.finditer(code):
            if "#" not in m.group(1):
                label_defs[m.group(1)].append((tex, line_of(code, m.start())))
        for m in REF_RE.finditer(code):
            cmd, raw = m.group(1), m.group(2)
            keys = split_keys(raw) if cmd in MULTI_REF_CMDS else [raw.strip()]
            keys = [k for k in keys if "#" not in k]
            for key in keys:
                ref_targets[key].append((tex, line_of(code, m.start())))
        # TODO markers count inside comments too ("% TODO" is still unfinished work),
        # but not on a line that defines a macro such as \newcommand{\todo}[1]{...}.
        # Placeholder text only counts outside comments, where it would be typeset.
        for lineno, (line, code_line) in enumerate(zip(text.split("\n"), code.split("\n")), start=1):
            if TODO_RE.search(line) and not DEFINITION_RE.search(code_line):
                todos.append((tex, lineno, line.strip()))
            if PLACEHOLDER_RE.search(code_line):
                placeholders.append((tex, lineno, line.strip()))

    bib_entries = set()
    crossref_targets = set()  # parents named by crossref fields count as used
    bib_defs = defaultdict(list)  # lower-cased key -> [(file, line, key)]
    for bib in bib_files:
        text = bib.read_text(encoding="utf-8", errors="replace")
        for _kind, key, pos, body in iter_bib_entries(text):
            bib_entries.add(key)
            bib_defs[key.lower()].append((bib, line_of(text, pos), key))
            crossref_targets.update(c.lower() for c in CROSSREF_RE.findall(body))
    duplicate_bib = {locs[0][2]: [(f, ln) for f, ln, _ in locs]
                     for locs in bib_defs.values() if len(locs) > 1}

    for bbl in bbl_files:
        text = bbl.read_text(encoding="utf-8", errors="replace")
        inline_entries.update(m.group(1).strip() for m in BIBITEM_RE.finditer(text))
        inline_entries.update(m.group(1).strip() for m in BBL_ENTRY_RE.finditer(text))
    cite_all = "*" in cite_keys  # \nocite{*}
    cite_keys.pop("*", None)
    known = bib_entries | inline_entries
    unresolved = {k: v for k, v in cite_keys.items() if k not in known}
    no_bibliography = bool(cite_keys) and not (bib_files or inline_entries)
    # With no bibliography at all every citation is missing; only a declared external bibliography defers them.
    missing_bib, unresolved_citations = ({}, unresolved) if external_bib else (unresolved, {})
    cited_lower = {k.lower() for k in cite_keys} | crossref_targets
    unused_bib = [] if cite_all or not bib_files else sorted(
        locs[0][2] for lower, locs in bib_defs.items() if lower not in cited_lower)
    duplicate_labels = {k: v for k, v in label_defs.items() if len(v) > 1}
    undefined_refs = {k: v for k, v in ref_targets.items() if k not in label_defs}

    return {
        "tex_files": tex_files,
        "bib_files": bib_files,
        "missing_bib": missing_bib,
        "no_bibliography": no_bibliography and not external_bib,
        "unresolved_citations": unresolved_citations,
        "external_bib": external_bib,
        "inline_entries": sorted(inline_entries),
        "unused_bib": unused_bib,
        "duplicate_bib": duplicate_bib,
        "duplicate_labels": duplicate_labels,
        "undefined_refs": undefined_refs,
        "todos": todos,
        "placeholders": placeholders,
        "unresolved_reason": f"declared external bibliography ({external_bib})" if external_bib else None,
    }


def fmt_locs(locs):
    return "; ".join(f"{f.name}:{ln}" for f, ln in locs[:5]) + (" ..." if len(locs) > 5 else "")


def style_scan(root_or_files):
    """Advisory typography findings: (file, line, kind, text) tuples, over a directory or an explicit list of files."""
    findings = []
    files = sorted(Path(root_or_files).rglob("*.tex")) if isinstance(root_or_files, (str, Path)) else list(root_or_files)
    for tex in files:
        code = strip_comments(tex.read_text(encoding="utf-8", errors="replace"))
        lines = code.split("\n")
        for regex, kind in ((REF_NO_TIE_RE, "ref without ~"), (UNIT_NO_TIE_RE, "number-unit spacing")):
            for m in regex.finditer(code):
                ln = line_of(code, m.start())
                if kind == "number-unit spacing" and LAYOUT_LINE_RE.search(lines[ln - 1]):
                    continue
                findings.append((tex, ln, kind, " ".join(m.group(0).split())))
    return findings


def report_style(findings) -> None:
    if not findings:
        print("[STYLE] no typography findings.\n")
        return
    print(f"[STYLE] {len(findings)} advisory typography finding(s); these may be false positives "
          f"and do not affect the exit code:")
    for f, ln, kind, text in findings[:40]:
        print(f"  - {f.name}:{ln}: {kind}: {text}")
    if len(findings) > 40:
        print(f"  ... and {len(findings) - 40} more")
    print()


SCOPE_NOTE = {"directory": "repository-wide source scan: every .tex/.bib/.bbl under the directory is merged; "
                           "not a compile or a check of scientific content",
              "main": "selected-document scan: only the files the main document includes and the bibliography it "
                      "declares; not a compile or a check of scientific content"}


def _coverage_incomplete(results) -> bool:
    disc = results.get("discovery")
    return bool(disc and disc["unresolved"])


def report(results, strict: bool) -> int:
    n_tex = len(results["tex_files"])
    n_bib = len(results["bib_files"])
    mode = results.get("mode", "directory")
    print(f"Scanned {n_tex} .tex file(s) and {n_bib} .bib file(s).")
    print(f"({SCOPE_NOTE[mode]})\n")

    issues = 0
    disc = results.get("discovery")
    if disc and disc["unresolved"]:
        print(f"[COVERAGE INCOMPLETE] {len(disc['unresolved'])} include(s) or bibliography declaration(s) the scanner "
              "could not follow; files behind them were not checked:")
        for u in disc["unresolved"]:
            print(f"  - {Path(u['file']).name}:{u['line']}: {u['kind']}: {u['raw']}  ({u['reason']})")
        print()
    if results.get("unassociated_bbl") and results.get("unresolved_citations"):
        print(f"[BUILT BIBLIOGRAPHY NOT ASSOCIATED] {', '.join(p.name for p in results['unassociated_bbl'])} in the build root "
              "was not used: a built .bbl certifies citations only when it is associated with --bbl (its provenance is "
              "the caller's assertion)\n")

    if results.get("no_bibliography"):
        print("[NO BIBLIOGRAPHY] citations found, but no .bib file, thebibliography or .bbl; every citation is "
              "missing (declare an externally built bibliography with --external-bib):")
    if results["missing_bib"]:
        issues += len(results["missing_bib"])
        print(f"[MISSING BIB ENTRY] {len(results['missing_bib'])} cite key(s) not found in any bibliography:")
        for key, locs in sorted(results["missing_bib"].items()):
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    if results["duplicate_bib"]:
        issues += len(results["duplicate_bib"])
        print(f"[DUPLICATE BIB KEY] {len(results['duplicate_bib'])} .bib key(s) defined more than once "
              "(BibTeX keeps the first and warns \"Repeated entry\"):")
        for key, locs in sorted(results["duplicate_bib"].items()):
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    if results["duplicate_labels"]:
        issues += len(results["duplicate_labels"])
        print(f"[DUPLICATE LABEL] {len(results['duplicate_labels'])} label(s) defined more than once:")
        for key, locs in sorted(results["duplicate_labels"].items()):
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    if results["undefined_refs"]:
        issues += len(results["undefined_refs"])
        print(f"[UNDEFINED REF] {len(results['undefined_refs'])} \\ref/\\eqref target(s) with no matching \\label:")
        for key, locs in sorted(results["undefined_refs"].items()):
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    if results["todos"]:
        issues += len(results["todos"])
        print(f"[TODO / PLACEHOLDER MARKER] {len(results['todos'])} found:")
        for f, ln, line in results["todos"][:20]:
            print(f"  - {f.name}:{ln}: {line}")
        if len(results["todos"]) > 20:
            print(f"  ... and {len(results['todos']) - 20} more")
        print()

    if results["placeholders"]:
        issues += len(results["placeholders"])
        print(f"[PLACEHOLDER TEXT] {len(results['placeholders'])} found:")
        for f, ln, line in results["placeholders"][:20]:
            print(f"  - {f.name}:{ln}: {line}")
        print()

    if results["unused_bib"]:
        print(f"[INFO] {len(results['unused_bib'])} .bib entr{'y is' if len(results['unused_bib']) == 1 else 'ies are'} never cited "
              f"(harmless in a shared library, worth checking in a single-paper .bib):")
        for key in results["unused_bib"][:20]:
            print(f"  - {key}")
        if len(results["unused_bib"]) > 20:
            print(f"  ... and {len(results['unused_bib']) - 20} more")
        if strict and _coverage_incomplete(results):
            print("  (--strict: not counted as issues while coverage is incomplete; an uncited entry may be cited in a file not scanned)")
        elif strict:
            issues += len(results["unused_bib"])
        print()

    unresolved = results.get("unresolved_citations") or {}
    if unresolved:
        print(f"[UNRESOLVED] {len(unresolved)} cite key(s) not found locally; they are not verified here "
              f"({results.get('unresolved_reason') or 'no local bibliography resolves them'}):")
        for key, locs in sorted(unresolved.items())[:40]:
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    incomplete = bool(disc and disc["unresolved"])
    if issues == 0 and not unresolved and not incomplete:
        print("No issues found.")
    elif issues == 0:
        print("No issues found locally; " + ("citations unresolved" if unresolved else "coverage incomplete") + " (see above).")
    else:
        print(f"Total issues: {issues}")

    return 1 if issues > 0 else (3 if (unresolved or incomplete) else 0)


FINDING_CODES = (("missing_bib", "manuscript.missing_bib_entry", "error", "add the entry to a declared bibliography or fix the key"),
                 ("duplicate_bib", "manuscript.duplicate_bib_key", "error", "keep one entry per key"),
                 ("duplicate_labels", "manuscript.duplicate_label", "error", "rename one label"),
                 ("undefined_refs", "manuscript.undefined_ref", "error", "add the \\label or fix the \\ref target"))


def json_report(results, strict: bool, exit_code: int, style_findings=None) -> dict:
    """The same findings as the text report, as one object (report_version 1.0.0)."""
    mode = results.get("mode", "directory")
    findings = []
    for key, code, severity, action in FINDING_CODES:
        for name, locs in sorted(results[key].items()):
            findings.append({"code": code, "severity": severity, "location": fmt_locs(locs), "message": f"{name}",
                             "suggested_action": action})
    for f, ln, line in results["todos"]:
        findings.append({"code": "manuscript.todo_marker", "severity": "error", "location": f"{f.name}:{ln}", "message": line,
                         "suggested_action": "resolve the marker before submission"})
    for f, ln, line in results["placeholders"]:
        findings.append({"code": "manuscript.placeholder", "severity": "error", "location": f"{f.name}:{ln}", "message": line,
                         "suggested_action": "replace the placeholder text"})
    if results.get("no_bibliography"):
        findings.append({"code": "manuscript.no_bibliography", "severity": "error", "location": "-",
                         "message": "citations found but no bibliography", "suggested_action": "declare a bibliography or --external-bib"})
    for key in results["unused_bib"]:
        severity = ("unresolved" if _coverage_incomplete(results) else "error") if strict else "warning"
        findings.append({"code": "manuscript.unused_bib_entry", "severity": severity, "location": "-",
                         "message": key, "suggested_action": "harmless in a shared .bib; check in a single-paper .bib"})
    for key, locs in sorted((results.get("unresolved_citations") or {}).items()):
        findings.append({"code": "manuscript.unresolved_citation", "severity": "unresolved", "location": fmt_locs(locs), "message": key,
                         "suggested_action": results.get("unresolved_reason") or "provide the bibliography"})
    disc = results.get("discovery")
    for u in (disc["unresolved"] if disc else []):
        findings.append({"code": "manuscript.include_unresolved", "severity": "unresolved", "location": f"{Path(u['file']).name}:{u['line']}",
                         "message": f"{u['kind']}: {u['raw']} ({u['reason']})",
                         "suggested_action": "make the include literal, pass --build-root/--project-root, or check the file by hand"})
    for f, ln, kind, text in style_findings or []:
        findings.append({"code": "manuscript.style", "severity": "warning", "location": f"{f.name}:{ln}", "message": f"{kind}: {text}",
                         "suggested_action": "advisory typography; may be a false positive"})
    status = {0: "pass", 1: "fail", 3: "incomplete", 2: "input-error"}[exit_code]
    scope = {"mode": mode, "note": SCOPE_NOTE[mode], "files": [str(p) for p in results["tex_files"]],
             "bib_files": [str(p) for p in results["bib_files"]], "strict": strict}
    if disc:
        scope["main"] = str(disc["main"])
    checks_run = ["citations", "bibliography-keys", "labels", "references", "markers"] + (["include-discovery"] if disc else []) \
        + (["style"] if style_findings is not None else [])
    checks_not_run = [{"check": "compile", "reason": "not a compile; run the TeX engine", "required": False},
                      {"check": "scientific-content", "reason": "wording, numbers and claims are not checked here", "required": False}]
    if not disc:
        checks_not_run.append({"check": "include-discovery", "reason": "directory mode merges every file; use --main", "required": False})
    return {"report_version": "1.0.0", "tool": "check_manuscript", "scope": scope, "status": status, "exit_code": exit_code,
            "coverage": (disc["coverage"] if disc else "repository-wide"), "checks_run": checks_run, "checks_not_run": checks_not_run,
            "findings": findings, "counts": {"tex_files": len(results["tex_files"]), "bib_files": len(results["bib_files"]),
                                             "findings": len(findings)}}


@protected_main("check_manuscript")
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, nargs="?", help="Directory containing the manuscript's .tex/.bib files (directory mode)")
    parser.add_argument("--main", type=Path, metavar="MAIN.tex", help="selected main document (main mode): scan only what it includes")
    parser.add_argument("--build-root", type=Path, metavar="DIR", help="directory TeX runs in; include names resolve against it (default: MAIN's folder)")
    parser.add_argument("--project-root", type=Path, metavar="DIR", help="boundary: no file outside it is opened (default: the build root)")
    parser.add_argument("--bbl", type=Path, metavar="FILE.bbl", help="a built bibliography to associate with the main document (main mode)")
    parser.add_argument("--strict", action="store_true", help="Treat unused .bib entries as issues for exit code purposes")
    parser.add_argument("--external-bib", metavar="DESCRIPTION",
                        help="the bibliography is built outside this directory (name the source); keys not found "
                             "locally are reported as unresolved (exit 3) instead of missing")
    parser.add_argument("--style", action="store_true",
                        help="Also report advisory typography checks (ref ties, number-unit spacing); exit code unaffected")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="text (default) or one JSON report object")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def fail(msg: str) -> int:
        if args.format == "json":
            print(json.dumps({"report_version": "1.0.0", "tool": "check_manuscript", "status": "input-error", "exit_code": 2,
                              "findings": [{"code": "manuscript.input_error", "severity": "error", "location": "-", "message": msg,
                                            "suggested_action": "fix the invocation"}]}, indent=1))
        print(f"error: {msg}", file=sys.stderr)
        return 2
    if args.main is None and args.path is None:
        return fail("give a manuscript directory or --main MAIN.tex")
    if args.main is not None:
        if not args.main.is_file():
            return fail(f"{args.main} is not a file")
        build_root = args.build_root or args.main.resolve().parent
        project_root = args.project_root or build_root
        if args.bbl is not None and not args.bbl.is_file():
            return fail(f"--bbl {args.bbl} is not a file")
        if args.bbl is not None and not _inside(args.bbl.resolve(), Path(project_root).resolve()):
            return fail(f"--bbl {args.bbl} lies outside the project root {project_root}; not opened")
        results = scan_main(args.main, project_root, build_root, external_bib=args.external_bib, bbl=args.bbl)
        style_root = results["tex_files"]  # main mode: only the files the document includes
    else:
        if not args.path.is_dir():
            return fail(f"{args.path} is not a directory")
        results = scan(args.path, external_bib=args.external_bib)
        if not results["tex_files"]:
            return fail(f"no manuscript files (.tex) under {args.path}: nothing was checked")
        style_root = args.path
    style_findings = style_scan(style_root) if args.style else None
    if args.format == "json":
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            code = report(results, strict=args.strict)
        print(json.dumps(json_report(results, args.strict, code, style_findings), indent=1))
        return code
    if args.style:
        report_style(style_findings)
    return report(results, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
