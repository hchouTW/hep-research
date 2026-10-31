#!/usr/bin/env python3
"""Naming extractor of hep-citations (semantic naming charter, hep-computing references/semantic-naming.md): write the
naming inventory of surface N17, literature record ids, for contracts/naming_check.py.

N17 reads:
  - literature-record artifacts: the identifiers of each source (doi, arxiv, inspire, ads; kinds doi, arxiv_id,
    inspire_id, ads_bibcode) and the source id the ledger gives it (record_id). Every one is decided outside the
    project (source external, C4, rename policy never): a wrong identifier is corrected in the ledger by the
    procedure that verified it, never renamed.
References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N17 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports N17 unsupported). Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (Builder, TextIndex, artifacts, coverage, files_of, line_of,  # noqa: E402
                                 mark_changed_by_file, now)
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-citations/scripts/extract_names.py", "version": VERSION}
KINDS = {"doi": "doi", "arxiv": "arxiv_id", "inspire": "inspire_id", "ads": "ads_bibcode"}


def extract_n17(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder("N17", EXTRACTOR)
    scanned = 0
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")], ("literature-record",)):
        scanned += 1
        sources = (doc.get("extension") or {}).get("sources") or {}
        for sid, src in sources.items() if isinstance(sources, dict) else []:
            if not isinstance(src, dict):
                continue
            b.add("record_id", src.get("id", sid), rel, "sources", line_of(text, f'"{sid}"'), src.get("title", ""),
                  source="external")
            for key, kind in KINDS.items():
                value = (src.get("identifiers") or {}).get(key)
                if isinstance(value, (str, int)) and str(value):
                    b.add(kind, str(value), rel, f"sources.{sid}", line_of(text, str(value)), f"{key}={value}",
                          source="external")
    entities = b.build(index, coverage(["N17"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N17", scopes, scanned, entities, now(), changed_since=changed)


EXTRACT = {"N17": extract_n17}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
