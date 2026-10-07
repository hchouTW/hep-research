#!/usr/bin/env python3
"""Convert a ROOT TTree to Parquet with uproot and awkward, keeping jagged branches, with a manifest to check it by.

Reads the tree in steps (--step-size entries) and writes one Parquet file per step (`part-00000.parquet`, ...), so
memory stays bounded. Jagged branches (for example NanoAOD's `Jet_pt`) stay jagged lists in Parquet. uproot's
per-branch counters (`nJet_pt`, ...) are written only when asked for with --branches. `manifest.json` records the input
file's SHA-256, the tree, the branches, the entries per part and in total, the output files with their SHA-256, and the
uproot, awkward and pyarrow versions; the conversion fails (exit 1) if the parts do not add up to the tree's entries.

Usage: root_to_parquet.py --input FILE.root --out DIR [--tree Events] [--branches Jet_pt,Jet_eta,genWeight]
       [--step-size 100000]
Exit 0 written and checked, 1 entry count mismatch, 2 bad input or a missing package. Requires uproot (tested with 5.7),
awkward (2.14) and pyarrow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import awkward as ak
    import uproot
    import pyarrow
    MISSING = None
except ImportError as _exc:  # reported by main(), so --help works without the optional stack
    MISSING = _exc.name


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def convert(src: Path, out: Path, tree: str = "Events", branches: list[str] | None = None, step_size: int = 100_000) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with uproot.open(src) as f:
        t = f[tree]
        names = branches or [b for b in t.keys() if not (b.startswith("n") and b[1:] in t.keys())]
        unknown = [b for b in names if b not in t.keys()]
        if unknown:
            raise ValueError(f"branches not in {tree}: {unknown}")
        total = t.num_entries
    parts = []
    for k, arrays in enumerate(uproot.iterate(f"{src}:{tree}", names, step_size=step_size, library="ak")):
        path = out / f"part-{k:05d}.parquet"
        ak.to_parquet(arrays, path)
        parts.append({"file": path.name, "entries": len(arrays), "sha256": sha256(path)})
    manifest = {"input": str(src), "input_sha256": sha256(src), "tree": tree, "branches": names, "step_size": step_size,
                "entries_in_tree": total, "entries_written": sum(p["entries"] for p in parts), "parts": parts,
                "versions": {"uproot": uproot.__version__, "awkward": ak.__version__, "pyarrow": pyarrow.__version__}}
    manifest["complete"] = manifest["entries_written"] == total
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tree", default="Events")
    ap.add_argument("--branches", help="comma-separated (default: every branch except uproot's n<branch> counters)")
    ap.add_argument("--step-size", type=int, default=100_000)
    args = ap.parse_args(argv)
    if MISSING:
        print(f"root_to_parquet.py: error: {MISSING} is not installed: pip install uproot awkward pyarrow", file=sys.stderr)
        return 2
    if not args.input.is_file():
        print(f"root_to_parquet.py: error: no such file: {args.input}", file=sys.stderr)
        return 2
    try:
        m = convert(args.input, args.out, args.tree, args.branches.split(",") if args.branches else None, args.step_size)
    except (KeyError, ValueError, OSError) as exc:
        print(f"root_to_parquet.py: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: m[k] for k in ("tree", "entries_in_tree", "entries_written", "complete")} | {"parts": len(m["parts"])}))
    return 0 if m["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
