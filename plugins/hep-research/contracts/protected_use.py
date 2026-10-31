#!/usr/bin/env python3
"""Protected-use mode at the formal-use entry points (task P1.1, C07, HC-09, K08): the public interface. The
implementation is core/protected/guard.py (standard library only, so that entry points in core call the same code);
see its docstring for the mode rule (DP-2), the protected inputs and their source checks (DP-4), and the refusal codes.

For entry points that return a report rather than raise, guard_report() adds every refusal as an error finding.
known_capabilities() is the capability set entry points give the guard (contracts.KNOWN_CAPABILITIES).

Usage: python3 contracts/protected_use.py status [--project DIR] [--protected] [--formal [--permit FILE]] [PATH ...]
Prints the context (protected or not, reasons, refusals, the verified revocation log and qualification id); it never
reports a use as allowed. Exit 0 when protected mode is off or nothing was refused, 3 when protected use is refused,
2 bad usage.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[1])
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
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import KNOWN_CAPABILITIES  # noqa: E402
from contracts.schema import Report  # noqa: E402
from core.protected.guard import (CONFIG_NAME, NOTE, Context, ProtectedUseRefused, detect, establish,  # noqa: E402,F401
                                  find_configs, guard, input_refusals, protected_main, qualification_problem,
                                  report_findings)


def known_capabilities() -> frozenset:
    return KNOWN_CAPABILITIES


def guard_report(entry: str, rep: Report, **kw) -> Context | None:
    """guard() for an entry point that returns a Report: refusals become error findings; None when refused."""
    try:
        return guard(entry, **kw)
    except ProtectedUseRefused as exc:
        for path, code, message in report_findings(exc):
            rep.add("error", path, code, message)
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status")
    p.add_argument("paths", nargs="*")
    p.add_argument("--project", type=Path)
    p.add_argument("--protected", action="store_true")
    p.add_argument("--formal", action="store_true", help="evaluate for formal use (needs --permit in protected mode)")
    p.add_argument("--permit", type=Path, help="the formal-use permit to check (contracts/permit.py)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    ctx = establish(args.paths, args.protected, args.project, "formal" if args.formal else "protected")
    refusals = list(ctx.refusals)
    if ctx.protected and not refusals:
        refusals = input_refusals(ctx, args.paths, capabilities=KNOWN_CAPABILITIES)
    if ctx.protected and not refusals and args.formal:
        from contracts.permit import verify as verify_permit
        refusals = verify_permit(args.permit, ctx, inputs=args.paths)
    out = dict(ctx.report(), refusals=refusals, refused=bool(refusals))
    print(json.dumps(out, indent=1))
    return 3 if refusals else 0


if __name__ == "__main__":
    sys.exit(main())
