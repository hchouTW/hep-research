#!/usr/bin/env python3
"""Naming extractor of hep-theory (semantic naming charter, hep-computing references/semantic-naming.md): write the
naming inventory of surface N13, theory parameters and scheme labels, for contracts/naming_check.py.

N13 reads:
  - theory-spec artifacts: the keys of parameters (parameter) and the values of conventions and scales keys that
    name a scheme (renormalization_scheme, factorization_scheme, mass_scheme, flavour_scheme, ...; scheme_label);
  - prediction artifacts: the keys of parameter_point (parameter).
References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N13 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports N13 unsupported). Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (Builder, TextIndex, artifact_status, artifacts, coverage, files_of,  # noqa: E402
                                 line_of, mark_changed_by_file, now)
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-theory/scripts/extract_names.py", "version": VERSION}
SCHEME_KEY = re.compile(r"(?i)scheme$")


def extract_n13(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder("N13", EXTRACTOR)
    scanned = 0
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")], ("theory-spec", "prediction")):
        scanned += 1
        ext = doc.get("extension") or {}
        meaning = {"status_label": artifact_status(doc)}
        cont = f"artifact:{doc.get('artifact_id', rel)}"
        params = ext.get("parameters") if doc["artifact_type"] == "theory-spec" else ext.get("parameter_point")
        for key, value in (params or {}).items() if isinstance(params, dict) else []:
            b.add("parameter", key, rel, cont, line_of(text, f'"{key}"'), json.dumps(value, sort_keys=True),
                  meaning=meaning)
        for block in ("conventions", "scales"):
            conv = ext.get(block) if isinstance(ext.get(block), dict) else doc.get(block)
            for key, value in (conv or {}).items() if isinstance(conv, dict) else []:
                if SCHEME_KEY.search(key) and isinstance(value, str) and len(value.split()) == 1:
                    b.add("scheme_label", value, rel, f"{cont}.{key}", line_of(text, f'"{value}"'), f"{key}={value}",
                          meaning=meaning)
    entities = b.build(index, coverage(["N13"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N13", scopes, scanned, entities, now(), changed_since=changed)


EXTRACT = {"N13": extract_n13}


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers=EXTRACT, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
