#!/usr/bin/env python3
"""Check a project's terminology and notation against its glossary over the record's documents.

Usage: python3 check_terminology.py RECORD.json --project-root ROOT --glossary GLOSSARY.json [--format json|markdown] [--out REPORT]

The glossary (template: assets/paper/glossary-template.json) declares concepts with preferred terms per language,
aliases, definitions, abbreviations, scope and disallowed substitutions with their context words; and notation
definitions by section scope. Findings are contextual: a disallowed term next to its context word (warning, with both
the location and the rule), an abbreviation redefined (error) or used before its definition (warning), a symbol defined
twice in one section with different wording (error, both locations), a definition in an undeclared scope (warning).
Aliases and declared scoped reuse are never flagged; quoted language is skipped. Exit codes: 0 no confirmed
inconsistency; 1 a confirmed one; 2 invalid invocation or unreadable record or glossary; 3 nothing to scan. Read-only;
nothing is replaced or translated.
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
from communication_lib.terminology import check_terminology, load_glossary  # noqa: E402

CHECKS = ("concept-substitutions", "aliases", "abbreviations", "notation-scopes")


def main(argv=None) -> int:
    def add_args(ap):
        ap.add_argument("--glossary", type=Path, required=True, help="project glossary JSON")

    def build(args, record, ctx):
        try:
            glossary = load_glossary(args.glossary)
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read glossary {args.glossary}: {exc}") from exc
        rep = check_terminology(record, ctx, glossary)
        rep["scope"].update(glossary=str(args.glossary), project_root=str(args.project_root))
        return rep
    return R.run("check_terminology", __doc__, argv, build, add_args=add_args, all_checks=CHECKS,
                 extra_protected=lambda args, ctx: [args.glossary])


if __name__ == "__main__":
    sys.exit(main())
