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

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from communication_lib import report as R  # noqa: E402
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
