#!/usr/bin/env python3
"""Audit output files for blinded values (enforcement side of blinding; policy is hep-analysis and the project config).

Two steps, so the blinded numbers never sit inside the audited outputs:
  seal:  python3 audit_blinded_outputs.py seal --hist hist.json --low 120 --high 130 [--reference mc.json] --out /private/sealed.json
         hist.json / mc.json: {"edges": [...], "values": [...]}. Writes the numbers no output may contain.
  scan:  python3 audit_blinded_outputs.py scan --sealed /private/sealed.json OUTPUT_DIR_OR_FILES... [--rtol 1e-9]
                [--strict] [--exempt PATH=REASON ...] [--outputs MANIFEST.json]
         Scans text outputs (JSON, CSV, logs, Markdown, SVG, ...) at full and printed precision, and .npy/.npz caches.
         Text in UTF-8, UTF-16 (with or without a byte-order mark) or another 8-bit encoding is read; a file that
         cannot be decoded is unscanned. A sealed value with fewer than 3 significant digits (a low count) matches
         only a standalone number and its hits are marked "weak".
         Binary images are listed as unscanned (status "incomplete"): check figures in code with
         core.blinding.check_figure(fig, region, sealed) and name each such file with --exempt and the reason.
         --strict (publication): an incomplete scan fails, every exemption needs a reason, and with --outputs (a JSON
         list of the files to publish) every listed output needs a scan record or an exemption.
Exit codes: 0 pass (every output read, no leak found), 1 leak found or strict failure, 2 usage or input error,
3 incomplete (no leak found, but not every output was read). A clean scan is not an authorization to unblind.
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
    c.add_argument("--strict", action="store_true", help="publication mode: incomplete scans fail")
    c.add_argument("--exempt", action="append", default=[], metavar="PATH=REASON",
                   help="an output checked another way (for example a figure checked with check_figure), with the reason")
    c.add_argument("--outputs", type=Path, help="strict mode: JSON list of every output to publish")
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
        exemptions = {}
        for item in args.exempt:
            path, sep, reason = item.partition("=")
            if not sep:
                raise ValueError(f"--exempt needs PATH=REASON, got {item!r}")
            exemptions[path] = reason
        outputs = json.loads(args.outputs.read_text(encoding="utf-8")) if args.outputs else None
        rep = scan_paths(args.paths, sealed, args.rtol, strict=args.strict, exemptions=exemptions, outputs=outputs)
        keys = ("status", "ok", "reasons", "leaks", "unscanned", "exempted", "outputs_without_record", "limitation")
        print(json.dumps({k: rep[k] for k in keys if k in rep} | {"scanned_files": len(rep["scanned"])}, indent=1))
        return {"pass": 0, "fail": 1, "incomplete": 3}[rep["status"]]
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
