#!/usr/bin/env python3
"""Check a communication record: structure, traceability and manuscript occurrences, with honest coverage.

Usage: python3 check_communication.py RECORD.json --project-root ROOT [--checks schema|traceability|manuscript]
                                      [--format json|markdown] [--out REPORT]

--checks is cumulative: schema validates the record alone (no project path is opened); traceability (default) also
resolves the declared inputs, evidence ledgers, source ids and documents inside the project root through the
dependency checker; manuscript also opens each declared document and compares every declared occurrence with the
current text at its locator. Project paths are relative to --project-root; --out never names an input of the run.
Exit codes: 0 the requested checks completed without error or unresolved required check (no certificate of scientific
truth); 1 a confirmed inconsistency; 2 invalid invocation or unreadable record; 3 a required check is incomplete,
unresolved or blocked (an unresolved source, a legacy record with limited traceability, a document that cannot be
read). The JSON report (report_version 1.0.0) is the stable interface; markdown renders the same report. Diagnostics
go to stderr. Read-only: manuscripts, artifacts, ledgers and the record are never modified.
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

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
for _p in (str(PLUGIN), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contracts import audit_report as R  # noqa: E402
from communication_lib.audit import CHECKS, audit_communication  # noqa: E402


def main(argv=None) -> int:
    def add_args(ap):
        ap.add_argument("--checks", choices=CHECKS, default="traceability", help="cumulative check level (default: traceability)")

    def build(args, record, ctx):
        rep = audit_communication(record, ctx, checks=args.checks)
        rep["scope"]["project_root"] = str(args.project_root)
        return rep
    return R.run("check_communication", __doc__, argv, build, add_args=add_args, all_checks=CHECKS,
                 needs_context=lambda args: args.checks != "schema")


if __name__ == "__main__":
    sys.exit(main())
