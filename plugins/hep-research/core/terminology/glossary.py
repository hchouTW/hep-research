"""load_glossary: read and validate a project glossary (glossary_version, entries with id, concept, preferred per
language and definition; optional disallowed, aliases, abbreviations, notation). Moved unchanged from
skills/hep-authoring/scripts/communication_lib/terminology.py, which re-exports it. Standard library only."""
from __future__ import annotations

import json
from pathlib import Path


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
