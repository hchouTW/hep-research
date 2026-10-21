"""Units, scope, the round-to-round mapping and deterministic sampling (spec sections 4.1-4.5).

A unit is a contiguous excerpt of the delivered document: units are cut from character offsets, never rebuilt, so
the excerpt property holds by construction (tests check it after whitespace normalisation, spec 4.1).
"""
from __future__ import annotations

import bisect
import hashlib
import os
import random
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[4]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"}

LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^(\s*)(?:(?:[-*+]|\d+[.)])\s+)?(`{3,}|~{3,})")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
TABLE_ROW = re.compile(r"^\s*\|")
ONLY_PUNCT = re.compile(r"^[\s\W_]*$", re.UNICODE)
CJK_END = "。？！；"
ASCII_END = ".?!;"
CLOSERS = "\"')]”’」』"
ABBREV = re.compile(r"(?:\be\.g|\bi\.e|\betc|\bvs|\bcf|\bFig|\bEq|\bNo|\bal)\.$", re.I)

NUMBER = re.compile(r"\d")
BACKTICK = re.compile(r"`[^`\n]+`")
PATH = re.compile(r"(?:<plugin root>/)?(?:[\w.~-]+/)+[\w.-]*|\b[\w-]+\.(?:py|json|jsonl|md|txt|toml|yaml|yml|tex|sh|cfg|csv|lock|C|cpp|h)\b")
QUOTED = re.compile(r"“[^”]+”|\"[^\"\n]+\"|「[^」]+」|『[^』]+』")
URL = re.compile(r"https?://[^\s)>\]]+")
FILE_LINE = re.compile(r"[\w./<>-]+\.[A-Za-z0-9]+:\d+(?:-\d+)?")
ZH_NORMATIVE = ("必須", "不得", "不能", "不會", "不包含", "從不", "只有", "應", "應該", "至少", "至多", "只能", "一律", "禁止")
EN_NORMATIVE = re.compile(r"\b(?:must|must not|should|shall|cannot|never|always|only)\b", re.I)
ATTRIBUTION = re.compile(r"寫著|依.{0,30}?文件|according to", re.I)
NAMED_SOURCE = re.compile(r"`[^`]+`|“[^”]+”|\"[^\"]+\"|「[^」]+」|\b(?:docs?|documentation|document|paper|spec|specification|section)\b|§", re.I)
RULE_CODE = re.compile(r"`[a-z]+(?:_[a-z]+)+`")
ROW_REF = re.compile(r"\brows? \d+|第\s*\d+\s*列")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# --- 4.1 splitting ---------------------------------------------------------------------------------------------------

def _line_spans(text: str):
    pos = 0
    for line in text.splitlines(keepends=True):
        yield pos, pos + len(line), line
        pos += len(line)


def _trim(text: str, a: int, b: int) -> tuple[int, int]:
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return a, b


def _sentences(text: str, a: int, b: int) -> list[tuple[int, int]]:
    """Sentence spans inside a paragraph block [a, b): split after 。？！； always, after .?!; when whitespace or the
    block end follows; never inside inline code, after an abbreviation, or after a leading list marker."""
    out, start, i, code = [], a, a, False
    while i < b:
        ch = text[i]
        if ch == "`":
            code = not code
        elif not code and (ch in CJK_END or ch in ASCII_END):
            j = i + 1
            while j < b and text[j] in CLOSERS:
                j += 1
            ok = ch in CJK_END or j >= b or text[j].isspace()
            head = text[start:i + 1]
            if ok and ch == "." and (ABBREV.search(head) or LIST_MARK.fullmatch(head + " ") or re.fullmatch(r"\s*\d+\.", head)):
                ok = False
            if ok:
                out.append((start, j))
                start = i = j
                continue
        i += 1
    if start < b:
        out.append((start, b))
    return out


def split_markdown(text: str) -> list[dict]:
    """Units of a Markdown document: headings, table rows and fenced code blocks (also indented ones inside list
    items) are one unit each; paragraphs and list items are split into sentences. A fragment of only punctuation,
    list markers or whitespace is merged into the previous unit."""
    spans = []  # (start, end, kind, section)
    section = ""
    lines = list(_line_spans(text))
    para = None  # [start, end]

    def flush():
        nonlocal para
        if para:
            for s, e in _sentences(text, para[0], para[1]):
                spans.append([s, e, "sentence", section])
        para = None

    i = 0
    while i < len(lines):
        s, e, line = lines[i]
        m = FENCE.match(line)
        if m:
            flush()
            mark = m.group(2)
            j = i + 1
            while j < len(lines) and not lines[j][2].strip().startswith(mark[0] * len(mark)):
                j += 1
            end = lines[min(j, len(lines) - 1)][1]
            spans.append([s, end, "code", section])
            i = j + 1
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        h = HEADING.match(line)
        if h:
            flush()
            section = h.group(2).strip()
            spans.append([s, e, "heading", section])
            i += 1
            continue
        if TABLE_ROW.match(line):
            flush()
            spans.append([s, e, "table-row", section])
            i += 1
            continue
        if LIST_MARK.match(line) or line.lstrip().startswith(">"):
            flush()
            para = [s, e]
        elif para:
            para[1] = e
        else:
            para = [s, e]
        i += 1
    flush()
    units = []
    for s, e, kind, sec in spans:
        a, b = _trim(text, s, e)
        if a >= b:
            continue
        frag = text[a:b]
        if kind != "code" and (ONLY_PUNCT.fullmatch(LIST_MARK.sub("", frag)) or LIST_MARK.fullmatch(frag + " ")):
            if units:
                units[-1]["end"] = b
            continue
        units.append({"start": a, "end": b, "kind": kind, "section": sec})
    out = []
    for n, u in enumerate(units, 1):
        t = text[u["start"]:u["end"]]
        out.append({"id": f"U{n:04d}", "section": u["section"] or "(preamble)", "kind": u["kind"], "text": t,
                    "text_sha256": sha256_text(t)})
    return out


# --- 4.3 substantive, 4.4 scope --------------------------------------------------------------------------------------

def substantive(unit: dict) -> bool:
    if unit["kind"] == "heading":
        return False
    t = LIST_MARK.sub("", unit["text"], count=1)
    if NUMBER.search(t) or BACKTICK.search(t) or URL.search(t) or QUOTED.search(t) or PATH.search(t):
        return True
    return any(w in t for w in ZH_NORMATIVE) or bool(EN_NORMATIVE.search(t))


def normative(text: str) -> bool:
    return any(w in text for w in ZH_NORMATIVE) or bool(EN_NORMATIVE.search(text))


_INDEX = {}


def plugin_index(root: Path = PLUGIN) -> tuple[frozenset, frozenset]:
    """(relative paths of files and folders, base names of files) of the baseline plugin."""
    root = Path(root)
    if root not in _INDEX:
        rel, names = set(), set()
        for parent, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            p = Path(parent).relative_to(root).as_posix()
            if p != ".":
                rel.add(p)
            for f in files:
                rel.add(f if p == "." else f"{p}/{f}")
                names.add(f)
        _INDEX[root] = (frozenset(rel), frozenset(names))
    return _INDEX[root]


def path_tokens(text: str) -> list[str]:
    """Path-like tokens with any '<plugin root>/' prefix, ':line' suffix and trailing punctuation removed."""
    out = []
    for m in list(PATH.finditer(text)) + list(re.finditer(r"`([^`\n]+)`", text)):
        tok = m.group(1) if m.re.pattern.startswith("`") else m.group(0)
        tok = re.sub(r"^<plugin root>/|^\./", "", tok.strip())
        tok = re.sub(r":\d+(?:-\d+)?$", "", tok).rstrip(".,;:)/")
        if tok:
            out.append(tok)
    return out


def plugin_paths_in(text: str, root: Path = PLUGIN) -> list[str]:
    rel, names = plugin_index(root)
    return [t for t in path_tokens(text) if t in rel or ("/" not in t and t in names)]


def in_scope(unit: dict, lens: str, hosts_terms=(), keywords=(), root: Path = PLUGIN) -> bool:
    if not unit["substantive"]:
        return False
    t = unit["text"]
    if lens == "design":
        return True
    if lens == "facts":
        return bool(plugin_paths_in(t, root)) or any(term in t for term in hosts_terms)
    if lens == "sources":
        return bool(FILE_LINE.search(t) or URL.search(t) or (ATTRIBUTION.search(t) and NAMED_SOURCE.search(t)))
    if lens == "bypass":
        return normative(t) or bool(NUMBER.search(LIST_MARK.sub("", t, count=1)) or RULE_CODE.search(t) or ROW_REF.search(t))
    return any(k.lower() in t.lower() for k in keywords)


def unit_table(text: str, lenses: list[str], lens_table: dict, hosts_terms=(), root: Path = PLUGIN) -> list[dict]:
    units = split_markdown(text)
    for u in units:
        u["substantive"] = substantive(u)
        u["in_scope"] = {lens: in_scope(u, lens, hosts_terms, lens_table.get(lens, {}).get("keywords", ()), root)
                         for lens in lenses}
    return units


def active_lenses(text: str, lens_table: dict, extra=()) -> list[str]:
    """The fixed lenses, domain lenses whose keywords occur in the document, then extra_lenses (A2: never fewer)."""
    out = [k for k, v in lens_table.items() if v.get("fixed")]
    for k, v in lens_table.items():
        if not v.get("fixed") and k not in out and any(w.lower() in text.lower() for w in v.get("keywords", ())):
            out.append(k)
    out += [x for x in extra if x not in out]
    return out


# --- 4.2 mapping -----------------------------------------------------------------------------------------------------

def lcs_pairs(a: list, b: list) -> list[tuple[int, int]]:
    """A longest common subsequence of a and b as index pairs; among several, the lexicographically smallest by old
    positions, then by new positions (old [x] against new [x, x] maps to new index 0)."""
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        Li, Li1, ai = L[i], L[i + 1], a[i]
        for j in range(m - 1, -1, -1):
            Li[j] = Li1[j + 1] + 1 if ai == b[j] else max(Li1[j], Li[j + 1])
    where = {}
    for j, x in enumerate(b):
        where.setdefault(x, []).append(j)
    out, i, j = [], 0, 0
    need = L[0][0]
    while need:
        done = False
        for ii in range(i, n):
            if L[ii][j] < need:
                break
            pos = where.get(a[ii], [])
            k = bisect.bisect_left(pos, j)
            while k < len(pos):
                jj = pos[k]
                if L[ii + 1][jj + 1] == need - 1:
                    out.append((ii, jj))
                    i, j, need, done = ii + 1, jj + 1, need - 1, True
                    break
                k += 1
            if done:
                break
        if not done:  # cannot happen for a consistent table
            raise AssertionError("LCS reconstruction failed")
    return out


def map_units(old: list[dict], new: list[dict]) -> dict:
    """Section 4.2: unchanged pairs on the LCS of text hashes; between alignment points, remaining units paired by
    position are changed, unpaired old units removed and unpaired new units added."""
    pairs = lcs_pairs([u["text_sha256"] for u in old], [u["text_sha256"] for u in new])
    out = {"unchanged": [], "changed": [], "added": [], "removed": []}
    pi, pj = 0, 0
    for i, j in pairs + [(len(old), len(new))]:
        ro, rn = old[pi:i], new[pj:j]
        for x, y in zip(ro, rn):
            out["changed"].append([x["id"], y["id"]])
        out["removed"] += [x["id"] for x in ro[len(rn):]]
        out["added"] += [y["id"] for y in rn[len(ro):]]
        if i < len(old):
            out["unchanged"].append([old[i]["id"], new[j]["id"]])
        pi, pj = i + 1, j + 1
    return out


# --- 4.5 sampling ----------------------------------------------------------------------------------------------------

def derive(seed: str, *parts) -> str:
    """A child seed (hex) of a seed and labels; the same inputs always give the same child."""
    return hashlib.sha256("\x1f".join([str(seed), *map(str, parts)]).encode("utf-8")).hexdigest()


def rng(seed_hex: str) -> random.Random:
    return random.Random(int(seed_hex, 16))


def sample_deep(units: list[dict], candidates: list[str], n: int, seed_hex: str) -> list[str]:
    """Section-stratified deep sample: sections in document order, shuffled with the seed, then one unit from each
    section in turn (chosen with the same seed) until n are drawn; all candidates when there are at most n."""
    order = [u["id"] for u in units]
    cand = [u for u in order if u in set(candidates)]
    if len(cand) <= n:
        return cand
    sec = {u["id"]: u["section"] for u in units}
    groups = {}
    for u in cand:
        groups.setdefault(sec[u], []).append(u)
    r = rng(seed_hex)
    names = list(groups)
    r.shuffle(names)
    picked = []
    while len(picked) < n:
        for s in names:
            if groups[s] and len(picked) < n:
                picked.append(groups[s].pop(r.randrange(len(groups[s]))))
    return [u for u in order if u in set(picked)]


def top_up(units: list[dict], base: list[str], candidates: list[str], n: int, seed_hex: str) -> list[str]:
    """base plus a seeded draw from candidates up to n units (re-review rounds, A4.1)."""
    have = list(dict.fromkeys(base))
    rest = [u for u in candidates if u not in set(have)]
    if len(have) < n and rest:
        have += sample_deep(units, rest, n - len(have), seed_hex)
    order = [u["id"] for u in units]
    return [u for u in order if u in set(have)]
