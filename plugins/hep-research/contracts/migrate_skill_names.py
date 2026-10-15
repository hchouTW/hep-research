#!/usr/bin/env python3
"""Rewrite the deprecated skill names of an artifact to the names of hep-research 0.11.0 (contracts 2.9.0).

hep-research 0.11.0 renamed four skills (contracts.skill_names.DEPRECATED_SKILL_ALIASES). An artifact written before
the rename keeps validating, with the warning skill.deprecated_name (an error under --strict-versions and protected
use). This converter rewrites exactly two fields, each with a diagnostic:

- provenance.producer_skill;
- handoff.to_skill.

Nothing else changes: not contract_version, not the extension, not a sha256 another artifact records for this one (a
downstream input that pins the old file's hash must be updated by whoever owns it; contracts/dependencies.py reports
the mismatch). A deprecated name elsewhere (an extension handoff of an ml-artifact) is left as is and reported as
remaining. Findings the artifact had for other reasons are reported as remaining, never repaired.

Usage: python3 contracts/migrate_skill_names.py OLD.json [--out NEW.json]
Exit codes: 0 migrated (or nothing to rewrite), 2 unreadable input or not an artifact object.
Output: JSON report {status, diagnostics, remaining} on stdout; the migrated artifact goes to --out.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.skill_names import DEPRECATED_SKILL_ALIASES  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

FIELDS = (("provenance", "producer_skill"), ("handoff", "to_skill"))


def migrate(doc: dict) -> tuple[dict | None, dict]:
    """Return (migrated artifact or None, report)."""
    if not isinstance(doc, dict):
        return None, {"status": "refused", "diagnostics": [], "remaining": [],
                      "error": "an artifact is a JSON object"}
    new = copy.deepcopy(doc)
    diagnostics = []
    for block, key in FIELDS:
        sub = new.get(block)
        if not isinstance(sub, dict):
            continue
        old = sub.get(key)
        if isinstance(old, str) and old in DEPRECATED_SKILL_ALIASES:
            sub[key] = DEPRECATED_SKILL_ALIASES[old]
            diagnostics.append({"code": "migrate.skill_renamed", "path": f"$.{block}.{key}",
                                "message": f"{old} -> {sub[key]}"})
    remaining = [{"code": f.code, "severity": f.severity, "path": f.path, "message": f.message}
                 for f in validate_artifact(new).findings if f.severity != "info"]
    return new, {"status": "migrated" if diagnostics else "unchanged", "diagnostics": diagnostics,
                 "remaining": remaining}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "error": f"cannot read {args[0]}: {exc}"}))
        return 2
    new, report = migrate(doc)
    if new is None:
        print(json.dumps(report, indent=1))
        return 2
    if "--out" in args:
        i = args.index("--out") + 1
        if i >= len(args):
            print(json.dumps({"status": "refused", "error": "--out needs a path"}))
            return 2
        Path(args[i]).write_text(json.dumps(new, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
