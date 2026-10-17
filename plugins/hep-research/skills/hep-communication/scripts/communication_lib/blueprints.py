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
