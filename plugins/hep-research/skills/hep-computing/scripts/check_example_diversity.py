#!/usr/bin/env python3
"""Check that examples in the same archetype are drawn from different skills.

Purpose: enforce the diversity rule for a batch of canonical examples - no two
files sharing an `archetype:` frontmatter value should also share a `skill:`
value, so a 3-example batch is guaranteed to span 3 different skills. See
references/example-authoring.md's "Diversity rule" for what this does and does
not guarantee.

What it does: reads the `archetype:`/`skill:` frontmatter fields from each
given file (missing `archetype:` defaults to `contrast`, matching
`validate_skill_example.py`'s backward-compatibility rule), groups files by
archetype, and reports any archetype group where two or more files share a
`skill:` value. It cannot judge whether the *content* is conceptually
distinct across files - that is a curation responsibility, not a mechanical
one.

Usage: `python3 <plugin root>/skills/hep-computing/scripts/check_example_diversity.py <file1.md> <file2.md> ...`
(rely on shell globbing for a whole batch, e.g.
`python3 <plugin root>/skills/hep-computing/scripts/check_example_diversity.py ../*/examples/*.md`). Exits 0 and
prints "ok: no diversity violations across N file(s)" on success; exits 1 and
lists every violation (archetype, skill, and the offending files) on failure.
Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill_example import parse_frontmatter  # noqa: E402


def group_by_archetype_and_skill(paths: list[Path]) -> dict[str, dict[str, list[Path]]]:
    groups: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        fields, _ = parse_frontmatter(text)
        archetype = fields.get("archetype", "").strip() or "contrast"
        skill = fields.get("skill", "").strip() or "(unknown)"
        groups[archetype][skill].append(path)
    return groups


def find_violations(paths: list[Path]) -> list[str]:
    violations = []
    groups = group_by_archetype_and_skill(paths)
    for archetype, by_skill in groups.items():
        for skill, files in by_skill.items():
            if len(files) > 1:
                names = ", ".join(str(f) for f in files)
                violations.append(
                    f"archetype {archetype!r}: skill {skill!r} appears in {len(files)} files: {names}"
                )
    return violations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that no two examples in the same archetype share a skill."
    )
    parser.add_argument("files", nargs="+", type=Path, help="Example markdown files to check.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    violations = find_violations(args.files)
    if violations:
        print(f"{len(violations)} diversity violation(s) found:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    print(f"ok: no diversity violations across {len(args.files)} file(s)")
    return 0


if __name__ == "__main__":
    import sys as _sys
    try:
        raise SystemExit(main())
    except OSError as _exc:  # a missing or unreadable input: one line, no traceback
        print(f"check_example_diversity.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2)
