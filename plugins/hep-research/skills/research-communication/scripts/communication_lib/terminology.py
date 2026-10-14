"""Project terminology and notation consistency (plan T9).

Deterministic detection is limited to what a glossary declares: concept substitutions (a disallowed term used next
to a context word, in any declared language), aliases (noted, never flagged), abbreviations (redefined with another
expansion, or used before any definition), and notation definitions by section scope (the same symbol defined twice
in one section with different wording is a conflict; a definition in a section the glossary does not declare is for
review; a declared scoped reuse is legitimate). Quoted language and "so-called" mentions are skipped. Ambiguous usage
and the meaning of prose or equations are the reader's semantic review; nothing is replaced or translated.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from communication_lib import report as R
from communication_lib.documents import markdown_headings, normalize, strip_tex_comments, tex_sections
from contracts.communication import format_of

QUOTE_RE = re.compile(r"[\"“「『][^\"”」』]*[\"”」』]|so-called\s+\S+")
ABBR_DEF_HEAD = r"([A-Za-z\u4e00-\u9fff][A-Za-z\-\u4e00-\u9fff ]{1,80}?)\s*[\(\uff08]("
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ABBR_DEF_TAIL = r")[\)\uff09]"
NOTE = ("deterministic detection limited to glossary rules, explicit definitions and declared scopes; ambiguous usage and the "
        "meaning of prose or equations are the reader's semantic review; nothing is replaced or translated")


def load_glossary(path) -> dict:
    g = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(g, dict) or "glossary_version" not in g or not isinstance(g.get("entries"), list):
        raise ValueError(f"{path}: a glossary needs glossary_version and an entries array")
    for e in g["entries"]:
        if not isinstance(e, dict) or not {"id", "concept", "preferred", "definition"} <= set(e) or not isinstance(e["preferred"], dict):
            raise ValueError(f"{path}: every entry needs id, concept, preferred (per language), definition")
        e.setdefault("disallowed", [])
        e.setdefault("aliases", {})
        e.setdefault("abbreviations", [])
    for n in g.get("notation", []) or []:
        if not isinstance(n, dict) or not {"symbol", "definition", "scope"} <= set(n):
            raise ValueError(f"{path}: every notation entry needs symbol, definition, scope")
    return g


def _sections(text: str, fmt: str) -> list[tuple[int, str]]:
    """(line number, section title) for every heading, in order."""
    heads = [(pos, title) for pos, _, title in (tex_sections(text) if fmt == "latex" else markdown_headings(text))]
    return [(text.count("\n", 0, pos) + 1, normalize(title)) for pos, title in heads]


def _section_at(sections: list, line: int) -> str | None:
    cur = None
    for ln, title in sections:
        if ln <= line:
            cur = title
        else:
            break
    return cur


def _unquoted(line: str) -> str:
    return QUOTE_RE.sub(" ", line)


def _contains(hay: str, needle: str) -> int:
    """Index of needle in hay, word-bounded for ASCII words, plain substring otherwise; -1 if absent."""
    if re.search(r"[A-Za-z]", needle):
        m = re.search(r"(?<![A-Za-z])" + re.escape(needle) + r"(?![A-Za-z])", hay, re.I)
        return m.start() if m else -1
    return hay.find(needle)


def check_terminology(record: dict, context: dict, glossary: dict) -> dict:
    findings: list[dict] = []
    notes: list[dict] = []
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    docs_meta = {d.get("id"): d for d in ext.get("documents", []) or [] if isinstance(d, dict)}
    root = Path(context["project_root"])
    texts: dict[str, tuple[str, str]] = {}
    for did, d in context.get("documents", {}).items():
        if d.get("resolved"):
            try:
                raw = (root / d["resolved_path"]).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fmt = str(docs_meta.get(did, {}).get("format", "text"))
            texts[did] = (strip_tex_comments(raw) if fmt == "latex" else raw, fmt)
    scope = {"glossary_version": glossary.get("glossary_version"), "entries": [e.get("id") for e in glossary.get("entries", [])],
             "documents": list(docs_meta)}
    if format_of(record) != "traceability":
        findings.append(R.finding("terminology.legacy_record", "unresolved", "$.required_capabilities", "legacy record declares no documents",
                                  "write a traceability record with its documents", source="terminology"))
    if not texts:
        findings.append(R.finding("terminology.no_documents", "unresolved", "$.extension.documents", "no readable document to scan",
                                  "declare the documents (project-relative paths) in the record", source="terminology"))
    for did, (text, fmt) in texts.items():
        lines = text.split("\n")
        sections = _sections(text, fmt)
        _concepts(did, lines, glossary, findings, notes)
        _abbreviations(did, lines, glossary, findings)
        _notation(did, lines, sections, glossary, findings)
    return R.assemble("check_terminology", scope, findings, checks_run=["concept-substitutions", "aliases", "abbreviations", "notation-scopes"],
                      checks_not_run=[{"check": "semantic-review", "reason": "ambiguous usage and meaning are the reader's judgment", "required": False}],
                      notes=notes, coverage={"documents": {"declared": len(docs_meta), "scanned": len(texts)}}, note=NOTE)


def _concepts(did, lines, glossary, findings, notes):
    for e in glossary.get("entries", []):
        preferred = ", ".join(f"{v} ({k})" for k, v in (e.get("preferred") or {}).items())
        for rule in e.get("disallowed") or []:
            term = str(rule.get("term", ""))
            ctxs = [str(c) for c in (rule.get("when_near") or [])]
            if not term:
                continue
            for n, line in enumerate(lines, 1):
                clean = _unquoted(line)
                i = _contains(clean, term)
                if i < 0:
                    continue
                near = [c for c in ctxs if _contains(clean, c) >= 0] if ctxs else ["(no context required)"]
                if not near:
                    continue
                snippet = clean[max(0, i - 12): i + len(term) + 12].strip()
                findings.append(R.finding("terminology.concept_substitution", "warning", f"{did} line {n}",
                                          f"{snippet!r} uses {term!r} near {near[0]!r}: {rule.get('reason', '')}",
                                          f"use {preferred} if the concept is {e.get('concept')!r}; keep {term!r} if that is what is meant",
                                          rule=e.get("id"), source="terminology"))
        for lang, aliases in (e.get("aliases") or {}).items():
            for alias in aliases or []:
                hits = [n for n, line in enumerate(lines, 1) if _contains(_unquoted(line), str(alias)) >= 0]
                if hits:
                    notes.append({"code": "terminology.alias_used", "message": f"{did}: alias {alias!r} ({lang}) of {e.get('id')} at lines {hits[:5]}; equivalent, not flagged"})


def _abbreviations(did, lines, glossary, findings):
    for e in glossary.get("entries", []):
        for abbr in e.get("abbreviations") or []:
            rx = re.compile(ABBR_DEF_HEAD + re.escape(str(abbr)) + ABBR_DEF_TAIL)
            defs = []
            n_words = max(1, sum(ch.isalpha() for ch in str(abbr)))
            for n, line in enumerate(lines, 1):
                for m in rx.finditer(_unquoted(line)):
                    raw = m.group(1).strip()
                    spans = [w.start() for w in re.finditer(r"[^\s\-]+", raw)]
                    expansion = raw[spans[-n_words]:] if len(spans) >= n_words else raw  # the last len(abbr) words before the parenthesis
                    defs.append((n, normalize(expansion).lower(), expansion))
            distinct = {}
            for n, key, shown in defs:
                if CJK_RE.search(shown):
                    continue  # a CJK expansion has no word boundary to cut at: it counts as a definition, not for redefinition
                distinct.setdefault(key, (n, shown))
            if len(distinct) > 1:
                where = "; ".join(f"line {n}" for n, _ in distinct.values())
                findings.append(R.finding("terminology.abbreviation_redefined", "error", f"{did} {where}",
                                          f"{abbr} is defined as " + " and as ".join(f"{s!r} (line {n})" for n, s in distinct.values()),
                                          "use one expansion per abbreviation, or two abbreviations", rule=e.get("id"), source="terminology"))
            first_def = min((n for n, _, _ in defs), default=None)
            use_rx = re.compile(r"(?<![A-Za-z])" + re.escape(str(abbr)) + r"(?![A-Za-z])")
            for n, line in enumerate(lines, 1):
                if first_def is not None and n >= first_def:
                    break
                if use_rx.search(_unquoted(line)):
                    findings.append(R.finding("terminology.abbreviation_undefined", "warning", f"{did} line {n}",
                                              f"{abbr} is used before it is defined" + (f" (definition at line {first_def})" if first_def else " (never defined)"),
                                              "define the abbreviation at first use", rule=e.get("id"), source="terminology"))
                    break


def _notation(did, lines, sections, glossary, findings):
    declared: dict[str, list] = {}
    for n in glossary.get("notation", []) or []:
        declared.setdefault(str(n["symbol"]), []).append(n)
    for sym, entries in declared.items():
        rx = re.compile(r"(?<![A-Za-z\\])" + re.escape(sym) + r"(?![A-Za-z])(?:\s+(?:denotes|is defined as|stands for|is the|be the|denote)\s+"
                        r"|\s*(?:表示|定義為|記為|代表)\s*)(.+?)(?:[.;。；]|$)")
        found = []
        for ln, line in enumerate(lines, 1):
            for m in rx.finditer(_unquoted(line)):
                found.append((ln, _section_at(sections, ln), normalize(m.group(1)).lower()))
        by_section: dict = {}
        for ln, sec, text in found:
            by_section.setdefault(sec, []).append((ln, text))
        for sec, items in by_section.items():
            distinct = {}
            for ln, text in items:
                distinct.setdefault(text, ln)
            if len(distinct) > 1:
                where = "; ".join(f"line {ln}" for ln in distinct.values())
                findings.append(R.finding("terminology.conflicting_definitions", "error", f"{did} {where}",
                                          f"{sym} is defined in section {sec!r} as " + " and as ".join(f"{t!r} (line {ln})" for t, ln in distinct.items()),
                                          "keep one definition per symbol and section, or declare the reuse in the glossary with its scope",
                                          source="terminology"))
            scopes = [str(e.get("scope")) for e in entries]
            ok = any(s == f"section:{sec}".lower() or s.lower() == f"document:{did}".lower() for s in (x.lower() for x in scopes)) if sec else False
            ok = ok or any(s.lower() == f"document:{did}".lower() for s in scopes)
            if not ok:
                findings.append(R.finding("terminology.definition_undeclared", "warning", f"{did} line {items[0][0]}",
                                          f"{sym} is defined in section:{sec} ({items[0][1]!r}), a scope the glossary does not declare for it (declared: {scopes})",
                                          "add the scope to the glossary if the reuse is intended, or rename the symbol", source="terminology"))
