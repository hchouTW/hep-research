#!/usr/bin/env python3
"""Lint a generated Task Markdown document against the task-authoring contract.

Purpose: catch the mechanical defects in a finished task before it is handed over
- wrong or missing sections, empty sections, leftover template placeholders, a cited
repository path that does not exist, and an agentic loop with no stated limits. It
cannot judge whether the content is good; `references/task-quality-checklist.md`
still applies.

What it does: reads one task file and reports ERRORS (exit 1) and WARNINGS (exit 0).
Errors: the 12-section contract is broken (same check as `validate_skill_bundle.py`),
a section body is empty, a `{{...}}`, `<!-- ... -->` or `FIXME` placeholder is left, "Open Questions" has no item, a backtick path that looks like a repository file
does not exist under `--repo`, or the task describes an agent/retry loop but never
mentions a maximum-iteration limit. A path is found if it exists under `--repo` or inside this skill bundle (a task may
cite the authoring references it used), or if some
file under `--repo` ends with it after dropping leading segments (so skill-relative
and repo-name-prefixed paths resolve). A path that resolves outside `--repo` (through `..` or a symbolic link) is an
error ("path leaves the repository"); one that starts with `../` is a warning (not checked). A path mentioned within one line of text saying it will be created
or proposed (create, add, new, propose, write, introduce) or is absent (does not
exist, not found, missing, e.g.), or anywhere in the Deliverables section, is a warning, not an error; so is any path when `--repo` is
not given.

Usage: `python3 <plugin root>/skills/hep-computing/scripts/lint_task.py TASK.md [--repo REPO_ROOT] [--json]`
(--json: one JSON object with "status" "ok", "errors" or "error" instead of text.)
Exit codes: 0 no errors, 1 errors found, 2 unreadable input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill_bundle import check_template_sections  # noqa: E402

PATH_RE = re.compile(r"`((?:[\w.-]+/)+[\w.-]+\.\w{1,8})`")
CREATE_RE = re.compile(r"\b(creat\w*|add\w*|new|propos\w*|writ\w*|introduc\w*|generat\w*)\b", re.I)
PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|<!--(?!\s*/?example\b).*?-->|\bFIXME\b", re.S)  # plugin example-block markers are not placeholders
LOOP_RE = re.compile(r"\b(retry|retries|retrying|self-heal\w*|iterative loop|agentic loop|ReAct|until (?:it )?(?:passes|succeeds|works|is green))\b", re.I)
LIMIT_RE = re.compile(r"\b(max(?:imum)?[- ](?:iteration|pass|attempt|retr|step|turn|number of)\w*|iteration (?:cap|limit|ceiling)|cap\b)", re.I)
ABSENT_RE = re.compile(r"\b(do(?:es)? not exist|not found|no such|absent|missing|hypothetical|does not have|e\.g\.)", re.I)
SKIP_PATH = re.compile(r"[*<>{}$]|^https?:|^~")
PARENT_PATH = re.compile(r"^\.\./")


def leaves(root: Path, rel: str) -> bool:
    """True if `rel`, resolved under `root` (symbolic links and '..' followed), lands outside `root`."""
    base = root.resolve()
    return not (base / rel).resolve().is_relative_to(base)


def path_exists(repo: Path, rel: str) -> bool:
    """True if `rel` exists under `repo` without leaving it, or a repo file ends with it minus leading segments."""
    rel = re.sub(r"^(?:\.claude|\.agents|\.codex|\.gemini)/skills/[^/]+/", "", rel)  # installed-skill prefix
    if leaves(repo, rel):
        return False
    if (repo / rel).exists():
        return True
    parts = rel.split("/")
    if ".." in parts:  # a suffix of a path with '..' means nothing; only the resolved path above counts
        return False
    hits = [
        hit.as_posix()
        for hit in repo.rglob(parts[-1])
        if not {".git", ".worktrees"} & set(hit.relative_to(repo).parts)
    ]
    return any(
        hit.endswith("/" + "/".join(parts[start:])) for hit in hits for start in range(len(parts) - 1)
    )


def split_sections(text: str) -> dict[str, str]:
    """Map each '## X' / '### X' heading line to the text up to the next heading."""
    sections: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        if re.match(r"^#{2,3} ", line):
            current = line.strip()
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"
    return sections


SKILL_ROOT = Path(__file__).resolve().parents[1]


def lint(text: str, repo: Path | None, skill_root: Path | None = SKILL_ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = list(check_template_sections(text))
    warnings: list[str] = []
    sections = split_sections(text)

    for heading, body in sections.items():
        if heading == "## Scope":
            continue  # holds only the two subsections
        stripped = PLACEHOLDER_RE.sub("", body).strip()
        if not stripped:
            errors.append(f"section {heading!r} is empty")

    for match in PLACEHOLDER_RE.finditer(text):
        errors.append(f"leftover placeholder: {match.group(0)[:40]!r}")

    open_q = sections.get("## Open Questions", "")
    if open_q.strip() and not re.search(r"^\s*(?:[-*]|\d+\.)\s+\S", open_q, re.M):
        errors.append("'## Open Questions' has text but no list item")

    proposed: dict[str, bool] = {}  # path -> proposed or named as absent at any mention
    heading = ""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#{1,3} ", line):
            heading = line.strip()
        window = " ".join(lines[max(0, i - 1): i + 2])
        here = bool(CREATE_RE.search(window) or ABSENT_RE.search(window)) or heading == "## Deliverables"
        for path in PATH_RE.findall(line):
            if not SKIP_PATH.search(path):
                proposed[path] = proposed.get(path, False) or here
    for path, is_proposed in proposed.items():
        if PARENT_PATH.match(path):
            warnings.append(f"path starts outside the task's folder and is not checked: {path}")
        elif repo is None:
            warnings.append(f"path not checked (no --repo): {path}")
        elif leaves(repo, path) and not (skill_root and not leaves(skill_root, path) and path_exists(skill_root, path)):
            errors.append(f"path leaves the repository {repo}: {path}")
        elif not path_exists(repo, path) and not (skill_root and path_exists(skill_root, path)):
            msg = f"cited path does not exist under {repo}: {path}"
            if is_proposed:
                warnings.append(msg + " (proposed, or named as absent, here)")
            else:
                errors.append(msg)

    if LOOP_RE.search(text) and not LIMIT_RE.search(text):
        errors.append("describes an agent/retry loop but never states a maximum-iteration limit or marks it TBD")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("task", type=Path)
    parser.add_argument("--repo", type=Path, help="repository root that cited paths are resolved against")
    parser.add_argument("--json", action="store_true", help="print one JSON object (status, errors, warnings)")
    args = parser.parse_args(argv)
    try:
        text = args.task.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": f"cannot read {args.task}: {exc}"}))
        else:
            print(f"error: cannot read {args.task}: {exc}", file=sys.stderr)
        return 2
    errors, warnings = lint(text, args.repo)
    if args.json:
        print(json.dumps({"status": "errors" if errors else "ok", "errors": errors, "warnings": warnings}, indent=1))
        return 1 if errors else 0
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
