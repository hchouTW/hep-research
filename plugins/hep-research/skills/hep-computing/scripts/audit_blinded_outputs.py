#!/usr/bin/env python3
"""Audit output files for blinded values (enforcement side of blinding; policy is hep-analysis and the project config).

Two steps, so the blinded numbers never sit inside the audited outputs:
  seal:  python3 audit_blinded_outputs.py seal --hist hist.json --low 120 --high 130 [--reference mc.json] --out /private/sealed.json
         hist.json / mc.json: {"edges": [...], "values": [...]}. Writes the numbers no output may contain.
  scan:  python3 audit_blinded_outputs.py scan --sealed /private/sealed.json OUTPUT_DIR_OR_FILES... [--rtol 1e-9]
         Scans text outputs (JSON, CSV, logs, Markdown, SVG, ...) at full and printed precision, and .npy/.npz caches.
         Binary images are listed as unscanned: check figures in code with core.blinding.check_figure.
Exit codes: 0 no leak found, 1 leak found, 2 usage or input error. A clean scan is not an authorization to unblind.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.blinding.blinding import scan_paths, seal  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--hist", type=Path, required=True)
    s.add_argument("--low", type=float, required=True)
    s.add_argument("--high", type=float, required=True)
    s.add_argument("--reference", type=Path, action="append", default=[])
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("scan")
    c.add_argument("--sealed", type=Path, required=True)
    c.add_argument("--rtol", type=float, default=1e-9)
    c.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "seal":
            h = json.loads(args.hist.read_text(encoding="utf-8"))
            refs = [json.loads(r.read_text(encoding="utf-8"))["values"] for r in args.reference]
            nums = seal(h["edges"], h["values"], {"low": args.low, "high": args.high}, refs)
            args.out.write_text(json.dumps({"sealed": nums, "region": {"low": args.low, "high": args.high}}) + "\n", encoding="utf-8")
            print(json.dumps({"sealed_count": len(nums), "out": str(args.out)}))
            return 0
        sealed = json.loads(args.sealed.read_text(encoding="utf-8"))["sealed"]
        sealed_path = args.sealed.resolve()
        if any(sealed_path == p.resolve() or p.resolve() in sealed_path.parents for p in args.paths):
            print(json.dumps({"error": "the sealed file lies inside the audited outputs"}))
            return 2
        rep = scan_paths(args.paths, sealed, args.rtol)
        print(json.dumps({k: rep[k] for k in ("ok", "leaks", "unscanned")} | {"scanned_files": len(rep["scanned"])}, indent=1))
        return 0 if rep["ok"] else 1
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
