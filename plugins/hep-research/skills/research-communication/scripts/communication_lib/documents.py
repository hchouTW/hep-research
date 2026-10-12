"""Locate a recorded occurrence in the current text of a Markdown or literal-LaTeX document (plan T5, Section 4.7).

A manifest declaring an occurrence is not evidence that the text was checked: this module opens the document, resolves
the locator and compares the recorded passage with what is there now. Locators: `section:<heading>` (Markdown heading
or LaTeX sectioning command, by title), `env:<name>` (LaTeX environment), `label:<key>` (LaTeX: the enclosing
environment, else the text from the label to the next sectioning command), `anchor:<text>` (the paragraph containing
the text), `line:<n>`, `document`. An ambiguous locator, an unsupported form or an absent region is unresolved; a
located region without the passage is a mismatch, with the closest current sentence reported. Comparison is on
whitespace-normalized text; no number is interpreted here.
"""
from __future__ import annotations

import difflib
import re

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.M)
TEX_SECTION_RE = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\])?\{([^}]*)\}")
TEX_COMMENT_RE = re.compile(r"(?<!\\)%.*")
TEX_ENV_RE = r"\\begin\{%s\}(.*?)\\end\{%s\}"
INCLUDE_RE = re.compile(r"\\(?:input|include|subfile|import|subimport)\s*\{")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00b1", "+/-")).strip()


def strip_tex_comments(text: str) -> str:
    return "\n".join(TEX_COMMENT_RE.sub("", ln) for ln in text.split("\n"))


def prepare(text: str, fmt: str) -> str:
    return strip_tex_comments(text) if fmt == "latex" else text


def _regions(text: str, fmt: str, locator: str) -> tuple[str, list[str], str | None]:
    """(kind, candidate regions, reason when unsupported)."""
    kind, _, arg = locator.partition(":")
    arg = arg.strip()
    if kind == "document":
        return kind, [text], None
    if kind == "line":
        try:
            n = int(arg)
        except ValueError:
            return kind, [], f"line locator {arg!r} is not a number"
        lines = text.split("\n")
        return kind, [lines[n - 1]] if 1 <= n <= len(lines) else [], None
    if kind == "section":
        if fmt == "markdown":
            heads = [(m.start(), len(m.group(1)), m.group(2)) for m in HEADING_RE.finditer(text)]
            out = []
            for i, (pos, level, title) in enumerate(heads):
                if normalize(title).lower() == arg.lower():
                    end = next((p for p, lv, _ in heads[i + 1:] if lv <= level), len(text))
                    out.append(text[pos:end])
            return kind, out, None
        if fmt == "latex":
            secs = [(m.start(), m.group(1), m.group(2)) for m in TEX_SECTION_RE.finditer(text)]
            out = []
            for i, (pos, _cmd, title) in enumerate(secs):
                if normalize(title).lower() == arg.lower():
                    end = next((p for p, _, _ in secs[i + 1:]), len(text))
                    out.append(text[pos:end])
            return kind, out, None
        return kind, [], f"section locators are not supported for format {fmt!r}"
    if kind == "anchor":
        if not arg:
            return kind, [], "empty anchor"
        paras = re.split(r"\n\s*\n", text)
        return kind, [p for p in paras if arg.lower() in normalize(p).lower()], None
    if fmt != "latex":
        return kind, [], f"locator kind {kind!r} needs a LaTeX document"
    if kind == "env":
        return kind, [m.group(0) for m in re.finditer(TEX_ENV_RE % (re.escape(arg), re.escape(arg)), text, re.S)], None
    if kind == "label":
        hits = [m.start() for m in re.finditer(r"\\label\{" + re.escape(arg) + r"\}", text)]
        out = []
        for pos in hits:
            env = _enclosing_env(text, pos)
            if env is not None:
                out.append(env)
                continue
            nxt = [m.start() for m in TEX_SECTION_RE.finditer(text) if m.start() > pos]
            end = min(nxt + [text.find("\\end{document}") if "\\end{document}" in text else len(text)])
            out.append(text[pos:end if end > pos else len(text)])
        return kind, out, None
    return kind, [], f"unknown locator kind {kind!r}"


def _enclosing_env(text: str, pos: int) -> str | None:
    """The innermost \\begin{env}...\\end{env} containing pos, except document."""
    best = None
    for m in re.finditer(r"\\begin\{([A-Za-z*]+)\}", text):
        name = m.group(1)
        if name == "document" or m.start() > pos:
            continue
        close = text.find("\\end{" + name + "}", m.end())
        if close != -1 and close > pos and (best is None or m.start() > best[0]):
            best = (m.start(), close + len("\\end{" + name + "}"))
    return text[best[0]:best[1]] if best else None


def _sentences(region: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n\s*\n", normalize(region)) if s.strip()]


def check_occurrence(text: str, fmt: str, occ: dict) -> dict:
    """{"outcome": located|mismatch|ambiguous|unresolved, "reason", "current"} for one occurrence against the text."""
    fmt = fmt if fmt in ("markdown", "latex") else "text"
    text = prepare(text, fmt)
    locator = str(occ.get("locator", "document"))
    kind, regions, reason = _regions(text, fmt, locator)
    if reason:
        return {"outcome": "unresolved", "reason": reason, "current": None}
    if not regions:
        return {"outcome": "unresolved", "reason": f"locator {locator!r} was not found in the document", "current": None}
    if len(regions) > 1:
        return {"outcome": "ambiguous", "reason": f"locator {locator!r} matches {len(regions)} regions", "current": None}
    region = regions[0]
    passage = normalize(str(occ.get("passage", "")))
    if passage and passage in normalize(region):
        return {"outcome": "located", "reason": None, "current": passage}
    if fmt == "latex" and INCLUDE_RE.search(region):
        return {"outcome": "include", "current": None,
                "reason": f"the region at {locator!r} includes other files ({INCLUDE_RE.search(region).group(0)}), which this check does not follow; "
                          "the passage may live there"}
    sentences = _sentences(region)
    closest = max(sentences, key=lambda s: difflib.SequenceMatcher(None, s, passage).ratio(), default="")
    return {"outcome": "mismatch", "current": closest,
            "reason": f"the recorded passage is not at {locator!r}; closest current sentence: {closest[:200]!r}"}
