#!/usr/bin/env python3
"""Naming extractor of hep-detector (semantic naming charter, hep-computing references/semantic-naming.md): write the
naming inventory of surface N11, calibrations, conditions tags and efficiency maps, for contracts/naming_check.py.

N11 reads:
  - response artifacts: the artifact id (project_output) and its matrix_ref (efficiency or response map);
  - conditions tags: the conditions field of response and dataset-record artifacts, the versions of
    measurement-spec eras, and configuration keys or Python assignments named global_tag, globaltag,
    conditions_tag, calibration_tag or GlobalTag in .json, .toml, .yaml, .cfg and .py files. A tag is decided by
    the experiment's conditions database: source external (C4, never renamed; propose a mapping instead).
References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N11 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports N11 unsupported). Standard library only.
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

import json
import re
import sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (Builder, TextIndex, artifact_status, artifacts, coverage, files_of,  # noqa: E402
                                 line_of, mark_changed_by_file, now, read_text)
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-detector/scripts/extract_names.py", "version": VERSION}
TAG_KEY = re.compile(r"""(?i)\b(global_?tag|conditions_tag|calibration_tag)\b["']?\s*[:=]\s*["']([^"'\s]+)["']""")
CONFIG_SUFFIXES = (".json", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".py")


def extract_n11(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder("N11", EXTRACTOR)
    scanned = 0
    for rel in paths:
        if not rel.endswith(CONFIG_SUFFIXES):
            continue
        text = read_text(root, rel)
        if text is None or not TAG_KEY.search(text):
            continue
        scanned += 1
        for n, ln in enumerate(text.splitlines(), 1):
            for m in TAG_KEY.finditer(ln):
                b.add("conditions_tag", m.group(2), rel, m.group(1), n, ln.strip(), source="external")
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")],
                                    ("response", "dataset-record", "measurement-spec")):
        scanned += 1
        ext = doc.get("extension") or {}
        meaning = {"status_label": artifact_status(doc)}
        if doc["artifact_type"] == "response":
            aid = doc.get("artifact_id")
            b.add("project_output", aid, rel, "response", line_of(text, f'"{aid}"'), json.dumps(ext.get("provenance")),
                  meaning=meaning)
            ref = ext.get("matrix_ref")
            if isinstance(ref, str) and ref:
                b.add("project_output", PurePosixPath(ref).name, rel, "matrix_ref", line_of(text, ref), ref,
                      meaning=meaning)
        cond = ext.get("conditions")
        if isinstance(cond, str) and cond and len(cond.split()) == 1:
            b.add("conditions_tag", cond, rel, "conditions", line_of(text, f'"{cond}"'), cond, source="external")
        for era in ext.get("eras") or []:
            for key, tag in ((era or {}).get("versions") or {}).items() if isinstance(era, dict) else []:
                if isinstance(tag, str) and len(tag.split()) == 1:
                    b.add("conditions_tag", tag, rel, f"eras.{era.get('id')}.{key}", line_of(text, f'"{tag}"'), tag,
                          source="external")
    entities = b.build(index, coverage(["N11"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N11", scopes, scanned, entities, now(), changed_since=changed)


EXTRACT = {"N11": extract_n11}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
