#!/usr/bin/env python3
"""Naming extractor of hep-ml (semantic naming charter, hep-computing references/semantic-naming.md): write the
naming inventory of surface N12, models, checkpoints and features, for contracts/naming_check.py.

N12 reads:
  - ml-artifact artifacts: the artifact id (model_artifact) and its features (feature: a string or an object's name);
  - checkpoint and exported model files in scope (.pt, .pth, .ckpt, .onnx, .joblib, .ubj, .safetensors, and
    .json files that train_bdt.py or export_bdt.py wrote) by file name (checkpoint).
References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N12 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports N12 unsupported). Standard library only.
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
import sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (Builder, TextIndex, artifact_status, artifacts, coverage, files_of,  # noqa: E402
                                 line_of, mark_changed_by_file, now)
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-ml/scripts/extract_names.py", "version": VERSION}
CHECKPOINT_SUFFIXES = (".pt", ".pth", ".ckpt", ".onnx", ".joblib", ".ubj", ".safetensors")


def extract_n12(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder("N12", EXTRACTOR)
    scanned = 0
    for rel in paths:
        if rel.endswith(CHECKPOINT_SUFFIXES):
            scanned += 1
            name = PurePosixPath(rel).name
            b.add("checkpoint", name, rel, PurePosixPath(rel).parent.as_posix(), 0, rel)
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")], ("ml-artifact",)):
        scanned += 1
        ext = doc.get("extension") or {}
        meaning = {"status_label": artifact_status(doc)}
        aid = doc.get("artifact_id")
        b.add("model_artifact", aid, rel, "ml-artifact", line_of(text, f'"{aid}"'), str(ext.get("model_hash")),
              meaning=meaning)
        for feat in ext.get("features") or []:
            name = feat if isinstance(feat, str) else feat.get("name") if isinstance(feat, dict) else None
            if isinstance(name, str):
                b.add("feature", name, rel, f"artifact:{aid}", line_of(text, f'"{name}"'), json.dumps(feat),
                      meaning=meaning)
    entities = b.build(index, coverage(["N12"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N12", scopes, scanned, entities, now(), changed_since=changed)


EXTRACT = {"N12": extract_n12}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
