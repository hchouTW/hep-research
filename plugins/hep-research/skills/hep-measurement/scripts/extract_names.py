#!/usr/bin/env python3
"""Naming extractor of hep-measurement (semantic naming charter, hep-computing references/semantic-naming.md): write
the naming inventory of one surface for contracts/naming_check.py.

Surfaces:
  N7  samples, datasets and run ranges: the sample column of yield tables (CSV with region,sample,yield), the eras of
      measurement-spec artifacts (run ranges) and the dataset_id of dataset-record artifacts. A name that is the
      dataset_id of a dataset record of a profile the project binds (hep-research.project.json) is official:
      source external (C4, never renamed; propose an alias instead).
  N8  selections, cutflows and regions: measurement-spec selections and background control regions, and the region
      column of yield tables.
  N9  systematic variations: measurement-spec systematics and the name column of systematics ledgers (the CSV of
      assets/systematics.csv: name, source, effect, applied_via, ...).
Names carry the status label of the artifact they come from (meaning.status_label), so status-honesty can judge a
synthetic or preliminary product named final. References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N7|N8|N9 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports the surface unsupported). Standard library only.
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

import csv
import io
import json
import sys
from pathlib import Path

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
EXTRACTOR = {"id": "skills/hep-measurement/scripts/extract_names.py", "version": VERSION}
LEDGER_COLUMNS = {"name", "source", "effect", "applied_via"}
YIELD_COLUMNS = {"region", "sample", "yield"}


def official_dataset_ids(root: Path) -> set[str]:
    """dataset_id of every dataset record of the profiles the project binds (profiles/registry.json)."""
    try:
        cfg = json.loads((root / "hep-research.project.json").read_text(encoding="utf-8"))
        registry = json.loads((PLUGIN / "profiles" / "registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    bound = set(cfg.get("experiments") or []) | set(cfg.get("theory") or [])
    out: set[str] = set()
    for prof in registry.get("profiles", []):
        if prof.get("id") not in bound:
            continue
        for rec in sorted((PLUGIN / "profiles" / prof["path"] / "datasets").glob("*.json")):
            try:
                doc = json.loads(rec.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            did = doc.get("dataset_id") or (doc.get("extension") or {}).get("dataset_id")
            if isinstance(did, str):
                out.add(did)
    return out


def _csv_rows(text: str):
    try:
        reader = csv.DictReader(io.StringIO(text))
        cols = {c.strip() for c in reader.fieldnames or []}
        return cols, [(n + 2, {(k or "").strip(): (v or "").strip() for k, v in row.items()}) for n, row in enumerate(reader)]
    except csv.Error:
        return set(), []


def _read(surface: str, root: Path, scopes, changed, args) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder(surface, EXTRACTOR)
    official = official_dataset_ids(root) if surface == "N7" else set()
    scanned = 0
    for rel in paths:
        if not rel.endswith((".csv", ".tsv")):
            continue
        text = read_text(root, rel)
        if text is None:
            continue
        cols, rows = _csv_rows(text)
        if surface in ("N7", "N8") and YIELD_COLUMNS <= cols:
            scanned += 1
            col, kind = ("sample", "internal_alias") if surface == "N7" else ("region", "region")
            seen = set()
            for n, row in rows:
                name = row.get(col)
                if name and name not in seen:
                    seen.add(name)
                    b.add(kind, name, rel, f"<{col}s>", n, f"{col} {name}",
                          source="external" if name in official else "project")
        elif surface == "N9" and LEDGER_COLUMNS <= cols:
            scanned += 1
            for n, row in rows:
                b.add("variation", row.get("name"), rel, "<ledger>", n, json.dumps(row, sort_keys=True))
    types = {"N7": ("measurement-spec", "dataset-record"), "N8": ("measurement-spec",), "N9": ("measurement-spec",)}
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")], types[surface]):
        scanned += 1
        ext = doc.get("extension") or {}
        cont = f"artifact:{doc.get('artifact_id', rel)}"
        meaning = {"status_label": artifact_status(doc)}

        def add(kind, name, item, source="project"):
            if isinstance(name, str):
                b.add(kind, name, rel, cont, line_of(text, f'"{name}"'), json.dumps(item, sort_keys=True), source=source,
                      meaning=meaning)
        if surface == "N7":
            if doc.get("artifact_type") == "dataset-record":
                did = ext.get("dataset_id")
                add("dataset", did, ext.get("data"), "external" if did in official else "project")
            for era in ext.get("eras") or []:
                if isinstance(era, dict):
                    add("run_range", era.get("id"), era)
        elif surface == "N8":
            for sel in ext.get("selections") or []:
                if isinstance(sel, dict):
                    add("selection", sel.get("name"), sel)
            for bg in ext.get("backgrounds") or []:
                if isinstance(bg, dict) and isinstance(bg.get("control_region"), str) and len(bg["control_region"].split()) == 1:
                    add("region", bg["control_region"], bg)
        else:
            for sy in ext.get("systematics") or []:
                if isinstance(sy, dict):
                    add("variation", sy.get("name"), sy)
    entities = b.build(index, coverage([surface], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory(surface, scopes, scanned, entities, now(), changed_since=changed)


def extract_n7(root, scopes, changed=None, args=None):
    return _read("N7", root, scopes, changed, args)


def extract_n8(root, scopes, changed=None, args=None):
    return _read("N8", root, scopes, changed, args)


def extract_n9(root, scopes, changed=None, args=None):
    return _read("N9", root, scopes, changed, args)


EXTRACT = {"N7": extract_n7, "N8": extract_n8, "N9": extract_n9}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
