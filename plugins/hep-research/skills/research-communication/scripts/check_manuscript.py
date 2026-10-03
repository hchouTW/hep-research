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
markers are still reported inside comments. A command's argument may wrap
onto the next line.

Standard library only. Intended to be run near the end of a drafting session,
not after every edit.

Usage:
    python3 check_manuscript.py <path-to-manuscript-dir> [--strict]

Exit code is 0 if no issues are found, 1 otherwise (useful in CI / pre-commit
hooks), and 3 when the only findings are citations left unresolved by a
declared external bibliography. --strict also treats "unused .bib entry" as an issue for exit-code
purposes (by default it is reported but does not affect the exit code, since
a shared/collaboration .bib file legitimately contains more entries than any
single paper cites).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# Any natbib/biblatex/plain citation command (\cite, \citep, \Citet, \citeauthor,
# \parencite, \textcite, \autocite, \footcite, \nocite, ...) with up to two
# optional arguments ([pre][post]) and a key list that may span lines.
CITE_RE = re.compile(r"\\(?:[A-Za-z]*cite[A-Za-z]*)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(ref|eqref|autoref|pageref|nameref|vref|Vref|cref|Cref|cpageref|Cpageref|labelcref)\*?\{([^}]+)\}")
MULTI_REF_CMDS = {"cref", "Cref", "cpageref", "Cpageref", "labelcref", "vref", "Vref"}
BIBENTRY_RE = re.compile(r"@(\w+)\s*[{(]\s*([^,\s]+)\s*,")
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


def split_keys(raw: str):
    # Keys containing '#' are macro parameters inside a \newcommand body (\ref{#1}).
    return [k.strip() for k in raw.split(",") if k.strip() and "#" not in k]


def strip_comments(text: str) -> str:
    """Drop LaTeX comments (unescaped % to end of line), keeping the line count."""
    return "\n".join(COMMENT_RE.sub("", line) for line in text.split("\n"))


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def find_tex_and_bib(root: Path):
    tex_files = sorted(root.rglob("*.tex"))
    bib_files = sorted(root.rglob("*.bib"))
    return tex_files, bib_files


def scan(root: Path, external_bib: str | None = None):
    tex_files, bib_files = find_tex_and_bib(root)
    bbl_files = sorted(root.rglob("*.bbl"))
    inline_entries = set()

    cite_keys = defaultdict(list)   # key -> [(file, line)]
    label_defs = defaultdict(list)  # label -> [(file, line)]
    ref_targets = defaultdict(list)  # label -> [(file, line)]
    todos = []      # (file, line, text)
    placeholders = []  # (file, line, text)

    for tex in tex_files:
        text = tex.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(text)
        inline_entries.update(m.group(1).strip() for m in BIBITEM_RE.finditer(code))
        for m in CITE_RE.finditer(code):
            for key in split_keys(m.group(1)):
                cite_keys[key].append((tex, line_of(code, m.start())))
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
    bib_defs = defaultdict(list)  # lower-cased key -> [(file, line, key)]
    for bib in bib_files:
        text = bib.read_text(encoding="utf-8", errors="replace")
        for m in BIBENTRY_RE.finditer(text):
            if m.group(1).lower() in NON_ENTRY_TYPES:
                continue
            key = m.group(2)
            bib_entries.add(key)
            bib_defs[key.lower()].append((bib, line_of(text, m.start()), key))
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
    cited_lower = {k.lower() for k in cite_keys}
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
    }


def fmt_locs(locs):
    return "; ".join(f"{f.name}:{ln}" for f, ln in locs[:5]) + (" ..." if len(locs) > 5 else "")


def style_scan(root: Path):
    """Advisory typography findings: (file, line, kind, text) tuples."""
    findings = []
    for tex in sorted(root.rglob("*.tex")):
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


def report(results, strict: bool) -> int:
    n_tex = len(results["tex_files"])
    n_bib = len(results["bib_files"])
    print(f"Scanned {n_tex} .tex file(s) and {n_bib} .bib file(s).\n")

    issues = 0

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
        if strict:
            issues += len(results["unused_bib"])
        print()

    unresolved = results.get("unresolved_citations") or {}
    if unresolved:
        print(f"[UNRESOLVED] {len(unresolved)} cite key(s) not found locally; they can only resolve in the declared "
              f"external bibliography ({results['external_bib']}), so they are not verified here:")
        for key, locs in sorted(unresolved.items())[:40]:
            print(f"  - {key}  ({fmt_locs(locs)})")
        print()

    if issues == 0 and not unresolved:
        print("No issues found.")
    elif issues == 0:
        print("No issues found locally; citations unresolved (see above).")
    else:
        print(f"Total issues: {issues}")

    return 1 if issues > 0 else (3 if unresolved else 0)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Directory containing the manuscript's .tex/.bib files")
    parser.add_argument("--strict", action="store_true", help="Treat unused .bib entries as issues for exit code purposes")
    parser.add_argument("--external-bib", metavar="DESCRIPTION",
                        help="the bibliography is built outside this directory (name the source); keys not found "
                             "locally are reported as unresolved (exit 3) instead of missing")
    parser.add_argument("--style", action="store_true",
                        help="Also report advisory typography checks (ref ties, number-unit spacing); exit code unaffected")
    args = parser.parse_args(argv)

    if not args.path.is_dir():
        print(f"error: {args.path} is not a directory", file=sys.stderr)
        return 2

    results = scan(args.path, external_bib=args.external_bib)
    if args.style:
        report_style(style_scan(args.path))
    return report(results, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
