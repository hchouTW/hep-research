#!/usr/bin/env python3
"""Check markdown notes for common Agile delivery sections and plan structure.

By default this checks only that the expected headings are present. Two opt-in checks
add structure requirements from references/implementation-discipline.md:
`--require-plan-verification` requires every numbered plan step to carry a verification,
and rejects placeholder verifications like "looks right"; `--require-assumptions` adds
an assumptions heading to whatever is already required. Both are off by default so
existing notes keep passing.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_SECTIONS = [
    "story",
    "acceptance criteria",
    "validation",
    "risks",
]

# A numbered plan step, optionally followed by a verification clause.
STEP_PATTERN = re.compile(r"^\s{0,3}(\d+)[.)]\s+(.*?)\s*$")
VERIFICATION_PATTERN = re.compile(r"(?:->|-->|\u2192)?\s*verif(?:y|ication)\s*:\s*(.+)$",
                                  re.IGNORECASE)
# Verifications that assert nothing checkable.
WEAK_VERIFICATIONS = (
    "looks right", "looks good", "looks fine", "seems right", "seems fine",
    "seems to work", "it works", "works", "should work", "make it work",
    "no errors", "done", "ok", "fine",
)


def normalize_heading(line: str) -> str | None:
    match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
    if not match:
        return None
    heading = re.sub(r"\s+#+$", "", match.group(1).strip())  # optional closing ###
    return re.sub(r"\s+", " ", heading.strip().lower())


def strip_fenced_code(text: str) -> list[str]:
    """Lines outside ``` / ~~~ fenced blocks, so example headings in code don't count."""
    kept, fence = [], None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence is None:
            kept.append(line)
    return kept


def check_file(path: Path, required: list[str]) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8-sig")  # utf-8-sig drops a leading BOM
    headings = {heading for line in strip_fenced_code(text) if (heading := normalize_heading(line))}
    missing = [section for section in required if section.lower() not in headings]
    return sorted(headings), missing


def find_plan_steps(text: str) -> list[tuple[int, str, str | None]]:
    """Numbered steps and their verification clause, if any.

    Returns (number, step text, verification or None) per numbered line.
    """
    steps = []
    for line in text.splitlines():
        match = STEP_PATTERN.match(line)
        if not match:
            continue
        number, body = int(match.group(1)), match.group(2)
        verification = VERIFICATION_PATTERN.search(body)
        if verification:
            step_text = body[: verification.start()].rstrip(" -\u2192")
            steps.append((number, step_text.strip(), verification.group(1).strip()))
        else:
            steps.append((number, body.strip(), None))
    return steps


def is_weak_verification(verification: str) -> bool:
    """True when a verification asserts nothing anyone could repeat."""
    stripped = verification.strip().strip(".!").strip().lower()
    return stripped in WEAK_VERIFICATIONS


def check_plan_verification(text: str) -> list[str]:
    """Problems with the note's numbered plan. Empty list means it passes."""
    steps = find_plan_steps(text)
    if not steps:
        return ["no numbered plan steps found (expected lines like "
                "'1. <step> -> verify: <check>')"]
    problems = []
    for number, step_text, verification in steps:
        label = step_text if len(step_text) <= 50 else step_text[:47] + "..."
        if verification is None:
            problems.append(f"step {number} has no verification: {label!r}")
        elif is_weak_verification(verification):
            problems.append(
                f"step {number} has a placeholder verification: {verification!r}")
    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate common sections in Agile markdown notes.")
    parser.add_argument("file", type=Path, help="Markdown file to inspect.")
    parser.add_argument(
        "--require",
        action="append",
        dest="required",
        help="Required heading. Repeat to override defaults.",
    )
    parser.add_argument(
        "--require-assumptions",
        action="store_true",
        help="Also require an 'assumptions' heading, in addition to the other "
             "requirements rather than replacing them.",
    )
    parser.add_argument(
        "--require-plan-verification",
        action="store_true",
        help="Require every numbered plan step to carry a verification, and reject "
             "placeholder verifications such as 'looks right'.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    required = [item.lower() for item in (args.required or DEFAULT_SECTIONS)]
    if args.require_assumptions and "assumptions" not in required:
        required.append("assumptions")
    try:
        headings, missing = check_file(args.file, required)
        plan_problems = (
            check_plan_verification(args.file.read_text(encoding="utf-8-sig"))
            if args.require_plan_verification else []
        )
    except FileNotFoundError:
        print(f"{args.file}: file not found")
        return 2
    except OSError as exc:
        print(f"{args.file}: could not read file ({exc})")
        return 2

    if missing:
        print(f"{args.file}: missing required headings: {', '.join(missing)}")
        print(f"found headings: {', '.join(headings) if headings else '(none)'}")
        return 1

    if plan_problems:
        print(f"{args.file}: plan verification problems:")
        for problem in plan_problems:
            print(f"  {problem}")
        return 1

    print(f"{args.file}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
