"""Paper blueprints (Com6): advisory content lists per paper type, read from assets/paper-blueprints.json.

check(text, blueprint) returns the items found and missing in a manuscript's TeX (comments stripped). Detection is a
keyword heuristic per item: "text" searches the whole source, "table-caption" the captions of table environments. A
missing item is advice, never a failed check."""
from __future__ import annotations

import json
import re
from pathlib import Path

ASSET = Path(__file__).resolve().parents[2] / "assets" / "paper-blueprints.json"
_COMMENT = re.compile(r"(?<!\\)%.*")
_TABLE = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.S)
_CAPTION = re.compile(r"\\caption\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", re.S)


def load(path: Path = ASSET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strip_comments(text: str) -> str:
    return "\n".join(_COMMENT.sub("", line) for line in text.splitlines())


def check(text: str, blueprint: dict, sources: dict) -> dict:
    text = strip_comments(text)
    captions = " ".join(c for t in _TABLE.findall(text) for c in _CAPTION.findall(t))
    found, missing, items = [], [], []
    for item in blueprint["items"]:
        where = captions if item.get("where") == "table-caption" else text
        hit = any(re.search(p, where, re.I) for p in item["detect"])
        (found if hit else missing).append(item["id"])
        src = sources.get(item["source"], {})
        items.append({"id": item["id"], "present": hit, "description": item["description"],
                      "source": src.get("url", "to-verify (field practice; no author guideline read states it)")})
    return {"found": found, "missing": missing, "items": items,
            "note": "advisory keyword heuristic: an item may be present in other words; the exit code is unaffected"}


# ---------------------------------------------------------------- numbers (Com7, check_manuscript.py --numbers)

_NEWCOMMAND = re.compile(r"\\(?:re)?newcommand\*?\{(\\[A-Za-z]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}")
_WATERMARK = re.compile(r"\\hep(?:Synthetic|Preliminary)\{")
_QUANTITY = re.compile(r"(?P<sym>\\?[A-Za-z]+(?:_\{[^{}$=]*\}|_[A-Za-z0-9])?)\s*=\s*(?P<val>[-+]?\d+(?:\.\d+)?)\s*"
                       r"(?:\\pm|\u00b1|\+-)\s*(?P<unc>\d+(?:\.\d+)?)")
_REGIONS = (("abstract", re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)),
            ("tables", re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.S)),
            ("conclusions", re.compile(r"\\section\*?\{\s*(?:Conclusions?|Summary)[^}]*\}(.*?)(?=\\section|\\end\{document\}|$)", re.S)))


def expand_macros(text: str) -> str:
    """Replace simple argument-free \\newcommand macros by their bodies (two passes) and drop watermark wrappers."""
    macros = {m.group(1): m.group(2) for m in _NEWCOMMAND.finditer(text)}
    text = _NEWCOMMAND.sub("", text)
    for _ in range(2):
        for name in sorted(macros, key=len, reverse=True):
            text = re.sub(re.escape(name) + r"(?![A-Za-z])", lambda _m, b=macros[name]: b, text)
    return _WATERMARK.sub("", text)


def number_consistency(text: str) -> dict:
    """Every 'SYMBOL = VALUE +- UNC' per region (abstract, tables, conclusions, body); a symbol shown with different
    values or uncertainties is a mismatch."""
    text = expand_macros(strip_comments(text))
    spans, occ = [], {}
    for region, rx in _REGIONS:
        for m in rx.finditer(text):
            spans.append((m.start(1), m.end(1), region))

    def region_of(pos):
        return next((r for a, b, r in spans if a <= pos < b), "body")
    for m in _QUANTITY.finditer(text):
        occ.setdefault(m.group("sym"), []).append({"region": region_of(m.start()), "value": m.group("val"),
                                                   "uncertainty": m.group("unc"), "line": text.count("\n", 0, m.start()) + 1})
    mismatches = [{"quantity": sym, "occurrences": o} for sym, o in sorted(occ.items())
                  if len({(x["value"], x["uncertainty"]) for x in o}) > 1]
    return {"quantities": {k: len(v) for k, v in sorted(occ.items())}, "mismatches": mismatches,
            "note": "heuristic: quantities written as SYMBOL = VALUE \\pm UNC after expanding argument-free macros"}
