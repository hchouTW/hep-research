#!/usr/bin/env python3
"""Check a computational-run artifact's recorded hashes against the files they name.

The schema validator accepts any string in extension.input_manifest[].sha256 and extension.output_hashes, so a run
record can carry placeholders or hashes of files that have since changed. This recomputes each digest:
  input_manifest [{"path", "sha256"}]   and   output_hashes {"<path>": "<sha256>"}
Paths are relative to --base (default: the artifact's folder) and must stay inside it; nothing outside is read.
Per entry: match, mismatch, missing, outside-base, not-a-hash (a placeholder or malformed digest) or not-a-file (an
output_hashes key that names no file, for example a hash of merged JSON content).
Status: error (any mismatch, missing or outside-base), unresolved (any not-a-hash or not-a-file), ok otherwise.
A match shows the files are the ones recorded. It does not show who produced them, that the recorded commands produced
them, or anything about physical validity.

Usage: python3 contracts/verify_run.py RUN.json [--base DIR]
Exit codes: 0 ok, 1 error, 3 unresolved only, 2 unreadable input or not a computational-run. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _entry(base: Path, rel: str, declared, kind: str) -> dict:
    row = {"kind": kind, "path": rel, "declared": declared}
    if not (isinstance(declared, str) and HEX64.match(declared)):
        return dict(row, result="not-a-hash")
    p = (base / rel).resolve()
    if not (p == base or base in p.parents):
        return dict(row, result="outside-base")
    if not p.is_file():
        return dict(row, result="not-a-file" if kind == "output" else "missing")
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(row, actual=actual, result="match" if actual == declared else "mismatch")


def verify_run(doc: dict, base) -> dict:
    base = Path(base).resolve()
    ext = doc.get("extension") or {}
    rows = [_entry(base, str(i.get("path")), i.get("sha256"), "input") for i in ext.get("input_manifest", []) if isinstance(i, dict)]
    outs = ext.get("output_hashes") or {}
    rows += [_entry(base, str(k), v, "output") for k, v in (outs.items() if isinstance(outs, dict) else [])]
    results = {r["result"] for r in rows}
    if results & {"mismatch", "missing", "outside-base"}:
        status = "error"
    elif results & {"not-a-hash", "not-a-file"} or not rows:
        status = "unresolved"
    else:
        status = "ok"
    return {"status": status, "entries": rows, "checked": len(rows),
            "note": "hash agreement only: not who ran what, and not physical validity"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--base", type=Path)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.artifact.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": f"cannot read {args.artifact}: {exc}"}))
        return 2
    if not isinstance(doc, dict) or doc.get("artifact_type") != "computational-run":
        print(json.dumps({"error": "not a computational-run artifact"}))
        return 2
    rep = verify_run(doc, args.base or args.artifact.resolve().parent)
    print(json.dumps(rep, indent=1))
    return {"ok": 0, "error": 1, "unresolved": 3}[rep["status"]]


if __name__ == "__main__":
    sys.exit(main())
