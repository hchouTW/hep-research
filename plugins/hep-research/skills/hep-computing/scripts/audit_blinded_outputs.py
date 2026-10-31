#!/usr/bin/env python3
"""Audit output files for blinded values: an advisory check, not enforcement and not authorization.

With real data, seal and scan only as the data custodian or a person outside the agent session; agents use synthetic
sentinels only. Enforcement is input blinding plus OS access control; policy is the collaboration's.

Two steps, so the blinded numbers never sit inside the audited outputs:
  seal:  python3 audit_blinded_outputs.py seal --hist hist.json --low 120 --high 130 [--reference mc.json] --out SEALED.json
                [--rtol 1e-9]
         hist.json / mc.json: {"edges": [...], "values": [...]}. Writes the numbers no output may contain, with the
         scan tolerance (at most 1e-6) and the list of quantities left unsealed. Prints only where it wrote them.
         Bin edges must be finite and strictly increasing (exit 2 otherwise). Exact zero and numbers the unblinded
         bins give alone (sideband sums) are not sealed; if nothing is left the file says nothing_sealable.
  scan:  python3 audit_blinded_outputs.py scan --sealed SEALED.json OUTPUT_DIR_OR_FILES... [--report REPORT.json]
                [--strict] [--exempt PATH=REASON ...] [--outputs MANIFEST.json]
         Prints a fixed status only: pass, fail or incomplete, the unreadable files, and the limits of the scan. It
         never prints a sealed value, a matching token, file, line or a count of hits; those go to --report, which is
         for the custodian or a person outside the agent session. The tolerance comes from the sealed file.
         Scans text outputs (JSON, CSV, logs, Markdown, SVG, ...) at full and printed precision, and .npy/.npz caches.
         Text in UTF-8, UTF-16 (with or without a byte-order mark) or another 8-bit encoding is read; a file that
         cannot be decoded, an array that is not real numeric, and a symlinked directory are unscanned. A sealed
         value with fewer than 3 significant digits (a low count) matches only a standalone number.
         Binary images are listed as unscanned (status "incomplete"): check figures in code with
         core.blinding.check_figure(fig, region) and name each such file with --exempt and the reason.
         --strict (publication): an incomplete scan fails, every exemption needs a reason, and with --outputs (a JSON
         list of the files to publish) every listed output needs a scan record or an exemption.
Exit codes: 0 pass (every output read, no leak found), 1 leak found or strict failure, 2 usage or input error,
3 incomplete (no leak found, but not every output was read), or protected use refused (then the JSON status is
"refused", core/protected/guard.py). A clean scan is not an authorization to unblind,
publish or share.
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

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.blinding.blinding import NOT_SEALED, agent_view, scan_paths, seal  # noqa: E402
from core.protected.guard import protected_main  # noqa: E402

MAX_RTOL = 1e-6


def load_sealed(path: Path) -> tuple[list[float], float]:
    """The sealed numbers and tolerance; ValueError unless the file holds a list of finite numbers (a malformed sealed
    file would make every scan pass). The list may be empty only when seal recorded nothing_sealable (every blinded
    number is zero or follows from the public bins alone)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    nums = doc.get("sealed") if isinstance(doc, dict) else None
    if isinstance(nums, list) and not nums and doc.get("nothing_sealable") is True:
        pass
    elif not isinstance(nums, list) or not nums or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in nums):
        raise ValueError("the sealed file must hold a non-empty list of finite numbers under 'sealed'")
    rtol = doc.get("rtol", 1e-9)
    if not isinstance(rtol, (int, float)) or not 0 < rtol <= MAX_RTOL:
        raise ValueError(f"the sealed file's rtol must be in (0, {MAX_RTOL:g}]")
    return [float(x) for x in nums], float(rtol)


def inside(path: Path, roots) -> bool:
    p = path.resolve()
    return any(p == r.resolve() or r.resolve() in p.parents for r in roots)


@protected_main("audit_blinded_outputs")
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--hist", type=Path, required=True)
    s.add_argument("--low", type=float, required=True)
    s.add_argument("--high", type=float, required=True)
    s.add_argument("--reference", type=Path, action="append", default=[])
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--rtol", type=float, default=1e-9, help=f"scan tolerance recorded in the sealed file (at most {MAX_RTOL:g})")
    c = sub.add_parser("scan")
    c.add_argument("--sealed", type=Path, required=True)
    c.add_argument("--report", type=Path, help="write the detailed report (values, tokens, files, lines) here; "
                                                "for the custodian or a person outside the agent session")
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
            if not 0 < args.rtol <= MAX_RTOL:
                raise ValueError(f"--rtol must be in (0, {MAX_RTOL:g}]")
            nums = seal(h["edges"], h["values"], {"low": args.low, "high": args.high}, refs)
            doc = {"sealed": nums, "rtol": args.rtol, "region": {"low": args.low, "high": args.high},
                   "not_sealed": list(NOT_SEALED)}
            if not nums:  # every blinded number is zero or public (NOT_SEALED): the scan still checks readability
                doc["nothing_sealable"] = True
            args.out.write_text(json.dumps(doc) + "\n", encoding="utf-8")
            print(json.dumps({"status": "sealed", "out": str(args.out)}))  # no count: it depends on the values (N10)
            return 0
        sealed, rtol = load_sealed(args.sealed)
        for label, path in (("sealed file", args.sealed), ("report", args.report)):
            if path is not None and inside(path, args.paths):
                print(json.dumps({"status": "error", "error": f"the {label} lies inside the audited outputs"}))
                return 2
        exemptions = {}
        for item in args.exempt:
            path, sep, reason = item.partition("=")
            if not sep:
                raise ValueError(f"--exempt needs PATH=REASON, got {item!r}")
            exemptions[path] = reason
        outputs = json.loads(args.outputs.read_text(encoding="utf-8")) if args.outputs else None
        rep = scan_paths(args.paths, sealed, rtol, strict=args.strict, exemptions=exemptions, outputs=outputs)
        if args.report:
            args.report.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        view = agent_view(rep) | {"scanned_files": len(rep["scanned"]), "exempted": rep["exempted"]}
        if "outputs_without_record" in rep:
            view["outputs_without_record"] = rep["outputs_without_record"]
        print(json.dumps(view, indent=1))
        return {"pass": 0, "fail": 1, "incomplete": 3}[rep["status"]]
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
