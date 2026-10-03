#!/usr/bin/env python3
"""Validate the structural integrity of the task-authoring material in hep-computing.

Purpose: catch accidental deletions or truncations of files this skill's SKILL.md
depends on, and confirm the generated-task output contract
(assets/task-template.md) still carries exactly the sections the authoring
reference specifies - no more, no fewer.

What it does: checks that every task-authoring file inside the hep-research plugin's
hep-computing skill (SKILL.md, references, host notes, templates, examples, scripts) exists
and is non-empty, that SKILL.md has YAML frontmatter with name/description (description at
most 1024 characters), and that
assets/task-template.md's heading structure exactly matches the section
contract (one top-level title, then the fixed list of ## / ### sections in order).

Usage: run with no arguments from anywhere; it resolves paths relative to its own
location. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/validate_skill_bundle.py`. No third-party dependencies.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_PATHS = [
    "SKILL.md",
    "assets/task-template.md",
    "references/task-authoring-guide.md",
    "references/acceptance-criteria.md",
    "references/task-quality-checklist.md",
    "references/example-authoring.md",
    "references/prompt-engineering-and-token-optimization.md",
    "references/loop-engineering.md",
    "references/host-notes.md",
    "examples/README.md",
    "examples/feature-task.md",
    "examples/bug-task.md",
    "examples/performance-task.md",
    "examples/research-task.md",
    "examples/migration-task.md",
    "examples/agentic-loop-task.md",
    "examples/data-ml-task.md",
    "scripts/validate_skill_bundle.py",
    "scripts/generate_skill_example.py",
    "scripts/validate_skill_example.py",
    "scripts/check_example_diversity.py",
    "scripts/lint_task.py",
]

# The exact, ordered section contract from "Task Generation Requirements" in
# references/task-authoring-guide.md: Title (a single top-level
# heading, checked separately), then these ## / ### sections in order.
DESCRIPTION_LIMIT = 1024  # characters; the sibling skills stay under it

REQUIRED_TEMPLATE_SECTIONS = [
    "## Background",
    "## Objective",
    "## Scope",
    "### In Scope",
    "### Out of Scope",
    "## Repository Context",
    "## Technical Approach",
    "## Deliverables",
    "## Acceptance Criteria",
    "## Validation",
    "## Open Questions",
    "## References",
]

HEADING_RE = re.compile(r"^(#{1,3} .+)$", re.MULTILINE)


def extract_headings(text: str) -> list[str]:
    """Return every level-1/2/3 Markdown heading line in `text`, in order."""
    return HEADING_RE.findall(text)


def check_template_sections(text: str) -> list[str]:
    """Return a list of problems with the template's section contract; empty
    if the template has exactly one top-level title followed by exactly the
    required sections, in order."""
    headings = extract_headings(text)
    top_level = [h for h in headings if not h.startswith("## ") and not h.startswith("### ")]
    sections = [h for h in headings if h.startswith("## ") or h.startswith("### ")]

    problems = []
    if len(top_level) != 1:
        problems.append(f"expected exactly one top-level title heading, found {len(top_level)}")
    if sections != REQUIRED_TEMPLATE_SECTIONS:
        missing = [s for s in REQUIRED_TEMPLATE_SECTIONS if s not in sections]
        extra = [s for s in sections if s not in REQUIRED_TEMPLATE_SECTIONS]
        if missing:
            problems.append(f"missing sections: {missing}")
        if extra:
            problems.append(f"unexpected extra sections: {extra}")
        if not missing and not extra:
            problems.append(f"sections present but out of order: {sections}")
    return problems


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                            epilog="Takes no arguments; paths resolve relative to this script.").parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    empty = [
        path
        for path in REQUIRED_PATHS
        if (root / path).exists() and (root / path).stat().st_size == 0
    ]

    if missing or empty:
        if missing:
            print("missing files:")
            for path in missing:
                print(f"  {path}")
        if empty:
            print("empty files:")
            for path in empty:
                print(f"  {path}")
        raise SystemExit(1)

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        print("SKILL.md is missing YAML frontmatter")
        raise SystemExit(1)
    frontmatter = skill.split("---", 2)[1]
    for field in ("name:", "description:"):
        if field not in frontmatter:
            print(f"SKILL.md frontmatter is missing {field}")
            raise SystemExit(1)

    match = re.search(r'^description:\s*"?(.*?)"?\s*$', frontmatter, re.MULTILINE)
    if match and len(match.group(1)) > DESCRIPTION_LIMIT:
        print(f"SKILL.md description is {len(match.group(1))} characters; limit is {DESCRIPTION_LIMIT}")
        raise SystemExit(1)

    template = (root / "assets/task-template.md").read_text(encoding="utf-8")
    template_problems = check_template_sections(template)
    if template_problems:
        print("assets/task-template.md section contract violated:")
        for problem in template_problems:
            print(f"  {problem}")
        raise SystemExit(1)

    print(
        f"Bundle OK: {len(REQUIRED_PATHS)} files present and non-empty, "
        f"assets/task-template.md carries all {len(REQUIRED_TEMPLATE_SECTIONS)} "
        "required sections in order."
    )


if __name__ == "__main__":
    main()
