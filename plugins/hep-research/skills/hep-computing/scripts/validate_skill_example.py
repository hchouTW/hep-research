#!/usr/bin/env python3
"""Validate a filled-in canonical `<skill>/examples/*.md` file.

Purpose: mechanically reject structural defects and placeholder content in a
worked example before it ships - mirrors `validate_agile_notes.py`'s role for
delivery notes. See references/example-authoring.md for the four archetypes and
the format each checks against.

What it does: reads the frontmatter `archetype:` field (`contrast`, `trajectory`,
`gated-pipeline`, `decision-tree`, `elicitation`, `adversarial-audit`,
`test-first`, or `postmortem`) to pick that archetype's rule set - a file with
no `archetype:` field is treated as `contrast`, for backward compatibility
with examples written before this script became archetype-aware. It then checks
that `role`/`skill`/the archetype's scenario field are present and non-empty in
frontmatter, that the archetype's fixed sections are present in order, the
archetype-specific structural rules below, and that no placeholder markers
(TODO/TBD/XXX/FIXME, Lorem ipsum, bracketed stand-ins, leftover scaffold
comments, standalone ellipsis lines) remain anywhere in the file. It cannot judge
domain correctness - that is a review step, not something this script does.

Archetype-specific rules:
- `contrast`: Key Takeaways has 3-6 bullet items.
- `trajectory`: "3. Surgical Execution" and "4. Verification Evidence" each
  contain a fenced code block.
- `gated-pipeline`: each of the three phase sections contains a `**Gate:**`
  line; "Phase 3: ..." additionally mentions an "assumption" it stress-tested.
- `decision-tree`: "Triage Matrix" contains a markdown table with a
  Trigger/Resolution Strategy header and at least 3 data rows.
- `elicitation`: "3. Socratic Clarification Round" has exactly 3 or 4
  numbered questions, each with lettered multiple-choice options.
- `adversarial-audit`: "2. Attack Vectors & Stress-Tests" enumerates at least
  2 distinct, separately-labeled attack vectors; "4. Hardened Architectural
  Patch" contains a fenced code block (diff or corrected artifact).
- `test-first`: "2. Executable Failing Test (Red)" contains a fenced block
  with a failure marker (FAILED/AssertionError/Error/non-zero exit) inside the
  fence, not in the prose around it; "4. Verified Passing Execution (Green)"
  contains a fenced block with a numeric metric inside the fence.
- `postmortem`: "1. Incident Symptom & Alert Payload" contains a fenced
  block; "3. 5-Whys Root Cause Deep-Dive" has exactly 5 numbered Why steps and
  does not stop at "human error"; "4. Permanent Surgical Fix (Diff)" contains
  a fenced diff block; "5. Blameless Postmortem & Preventative Monitoring
  Rules" names a concrete metric+threshold monitoring rule.

Usage: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/validate_skill_example.py <file.md>`. Exits 0 and prints
"<file>: ok" on success; exits 1 with a description of every problem found;
exits 2 with a one-line message (no traceback) if the file cannot be read.
Standard library only.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ARCHETYPES = [
    "contrast",
    "trajectory",
    "gated-pipeline",
    "decision-tree",
    "elicitation",
    "adversarial-audit",
    "test-first",
    "postmortem",
]

SCENARIO_FIELD = {
    "contrast": "use_case",
    "trajectory": "problem_input",
    "gated-pipeline": "high_stakes_task",
    "decision-tree": "scenario",
    "elicitation": "user_request",
    "adversarial-audit": "candidate_artifact",
    "test-first": "target",
    "postmortem": "incident",
}

REQUIRED_SECTIONS = {
    "contrast": ["Scenario", "Common Weak Approach", "Expert-Level Best Practice", "Key Takeaways"],
    "trajectory": [
        "1. Task Input & Context",
        "2. Root-Cause Triage & Action Plan",
        "3. Surgical Execution",
        "4. Verification Evidence",
        "5. Final Deliverable Summary",
    ],
    "gated-pipeline": [
        "Phase 1: Input Extraction & Gap Formulation",
        "Phase 2: Draft Synthesis",
        "Phase 3: Red-Team Review & Final Artifact Packaging",
    ],
    "decision-tree": ["Triage Matrix", "Selected Branch", "End-to-End Execution Script", "Fallback Safeguards"],
    "elicitation": [
        "1. Raw Ambiguous Input",
        "2. Missing Constraint Analysis",
        "3. Socratic Clarification Round",
        "4. User Feedback Integration",
        "5. Final Mutually-Agreed Specification Document",
    ],
    "adversarial-audit": [
        "1. Initial Candidate Artifact",
        "2. Attack Vectors & Stress-Tests",
        "3. Concrete Counter-Example / Exploit Proof",
        "4. Hardened Architectural Patch",
        "5. Proof of Robustness Post-Fix",
    ],
    "test-first": [
        "1. Acceptance Invariants & Boundary Constraints",
        "2. Executable Failing Test (Red)",
        "3. Minimal Code Implementation",
        "4. Verified Passing Execution (Green)",
        "5. Regression Guard Summary",
    ],
    "postmortem": [
        "1. Incident Symptom & Alert Payload",
        "2. Immediate Triage & Blast-Radius Mitigation",
        "3. 5-Whys Root Cause Deep-Dive",
        "4. Permanent Surgical Fix (Diff)",
        "5. Blameless Postmortem & Preventative Monitoring Rules",
    ],
}

MIN_TAKEAWAYS = 3
MAX_TAKEAWAYS = 6

SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"^- \S")
CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)
GATE_RE = re.compile(r"\*\*Gate:\*\*\s*\S")
TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|\s*$")
QUESTION_LINE_RE = re.compile(r"^\s*\d+\.\s+\S")
MC_OPTION_RE = re.compile(r"^\s*[a-dA-D]\)\s*\S")
ATTACK_VECTOR_RE = re.compile(r"attack vector\s*#?\s*(\d+)", re.IGNORECASE)
FAILURE_MARKER_RE = re.compile(
    r"\bFAILED\b|AssertionError|Traceback|non-zero exit|exit code [1-9]|exit status [1-9]|\bError\b",
    re.IGNORECASE,
)
METRIC_RE = re.compile(
    r"\d+(\.\d+)?[\s-]*(%|percent\b|ms|milliseconds|s\b|seconds?|minutes?|req/s|rps|qps|samples/sec|steps?\b|MB|GB|x\b)",
    re.IGNORECASE,
)
ACTION_WORD_RE = re.compile(
    r"\b(alert\w*|page[sd]?|paging|trigger\w*|rollback\w*|block\w*|gate[sd]?|gating|notify\w*|notif\w*|escalat\w*)\b",
    re.IGNORECASE,
)
HUMAN_ERROR_RE = re.compile(r"human error", re.IGNORECASE)
WHY_STEP_RE = re.compile(r"^\s*\d+\.\s+\S")

PLACEHOLDER_PATTERNS = [
    (re.compile(r"\b(TODO|TBD|FIXME|XXX)\b"), "placeholder marker"),
    (re.compile(r"lorem ipsum", re.IGNORECASE), "Lorem ipsum filler text"),
    (re.compile(r"\[(?:your|insert|placeholder|todo|xxx|tbd)\b[^\]]*\]", re.IGNORECASE),
     "bracketed stand-in"),
    (re.compile(r"<!--.*?-->", re.DOTALL), "leftover scaffold comment"),
]
ELLIPSIS_LINE_RE = re.compile(r"^\s*\.\.\.\s*$", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Returns (fields, body). Fields is empty if there is no --- block."""
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fields = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, parts[2]


def resolve_archetype(fields: dict[str, str]) -> tuple[str | None, list[str]]:
    """Returns (archetype, problems). Missing archetype defaults to 'contrast'."""
    raw = fields.get("archetype", "").strip()
    if not raw:
        return "contrast", []
    if raw not in ARCHETYPES:
        return None, [f"unknown archetype {raw!r} (expected one of {', '.join(ARCHETYPES)})"]
    return raw, []


def check_frontmatter(fields: dict[str, str], archetype: str) -> list[str]:
    problems = []
    if not fields:
        problems.append(
            "missing frontmatter block (expected a leading '---' section with "
            f"role/skill/{SCENARIO_FIELD[archetype]})"
        )
        return problems
    for field in ("role", "skill", SCENARIO_FIELD[archetype]):
        if not fields.get(field):
            problems.append(f"frontmatter is missing a non-empty '{field}' field")
    return problems


def check_sections(body: str, archetype: str) -> list[str]:
    required = REQUIRED_SECTIONS[archetype]
    headings = SECTION_HEADING_RE.findall(body)
    missing = [s for s in required if s not in headings]
    if missing:
        return [f"missing required section(s): {', '.join(missing)}"]

    positions = [headings.index(s) for s in required]
    if positions != sorted(positions):
        return [f"required sections are present but out of order: found {headings}, "
                f"expected order {required}"]
    return []


def section_text(body: str, name: str) -> str:
    matches = list(SECTION_HEADING_RE.finditer(body))
    for i, match in enumerate(matches):
        if match.group(1) != name:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        return body[start:end]
    return ""


def fenced_blocks(text: str) -> list[str]:
    """Contents of each closed ``` fence in text."""
    parts = re.split(r"^```.*$", text, flags=re.MULTILINE)
    return parts[1::2] if len(parts) % 2 == 1 else parts[1:-1:2]


def fenced_text(text: str) -> str:
    return "\n".join(fenced_blocks(text))


def check_takeaway_count(body: str) -> list[str]:
    takeaways_text = section_text(body, "Key Takeaways")
    count = sum(1 for line in takeaways_text.splitlines() if BULLET_RE.match(line))
    if not MIN_TAKEAWAYS <= count <= MAX_TAKEAWAYS:
        return [f"Key Takeaways has {count} bullet item(s), expected "
                f"{MIN_TAKEAWAYS}-{MAX_TAKEAWAYS}"]
    return []


def check_trajectory(body: str) -> list[str]:
    problems = []
    for section in ("3. Surgical Execution", "4. Verification Evidence"):
        text = section_text(body, section)
        if len(CODE_FENCE_RE.findall(text)) < 2:
            problems.append(f'"{section}" must contain a fenced code block, not just prose')
    return problems


def check_gated_pipeline(body: str) -> list[str]:
    problems = []
    for section in REQUIRED_SECTIONS["gated-pipeline"]:
        text = section_text(body, section)
        if not GATE_RE.search(text):
            problems.append(f'"{section}" is missing a non-empty "**Gate:**" line')
    phase3_text = section_text(body, "Phase 3: Red-Team Review & Final Artifact Packaging")
    if "assumption" not in phase3_text.lower():
        problems.append(
            '"Phase 3: Red-Team Review & Final Artifact Packaging" must mention at least '
            'one stress-tested assumption'
        )
    return problems


def check_decision_tree(body: str) -> list[str]:
    problems = []
    matrix_text = section_text(body, "Triage Matrix")
    rows = [line for line in matrix_text.splitlines() if TABLE_ROW_RE.match(line)]
    if len(rows) < 2:
        problems.append('"Triage Matrix" is missing a markdown table')
        return problems
    header, rest = rows[0], rows[1:]
    if "Trigger" not in header or "Resolution Strategy" not in header:
        problems.append('"Triage Matrix" table header must have "Trigger" and "Resolution Strategy" columns')
    data_rows = [row for row in rest if not TABLE_SEPARATOR_RE.match(row)]
    if len(data_rows) < 3:
        problems.append(f'"Triage Matrix" table has {len(data_rows)} data row(s), expected at least 3')
    return problems


def check_elicitation(body: str) -> list[str]:
    problems = []
    section = "3. Socratic Clarification Round"
    text = section_text(body, section)
    lines = text.splitlines()
    question_starts = [i for i, line in enumerate(lines) if QUESTION_LINE_RE.match(line)]
    count = len(question_starts)
    if not 3 <= count <= 4:
        problems.append(f'"{section}" has {count} question(s), expected 3-4')
    for pos, start in enumerate(question_starts):
        end = question_starts[pos + 1] if pos + 1 < len(question_starts) else len(lines)
        options = [line for line in lines[start + 1 : end] if MC_OPTION_RE.match(line)]
        if not options:
            snippet = lines[start].strip()[:60]
            problems.append(f'"{section}" question {snippet!r} has no lettered multiple-choice options')
    return problems


def check_adversarial_audit(body: str) -> list[str]:
    problems = []
    attack_section = "2. Attack Vectors & Stress-Tests"
    attack_text = section_text(body, attack_section)
    vector_numbers = set(ATTACK_VECTOR_RE.findall(attack_text))
    if len(vector_numbers) < 2:
        problems.append(f'"{attack_section}" must enumerate at least 2 distinct, separately-labeled attack vectors')
    proof_section = "3. Concrete Counter-Example / Exploit Proof"
    proof_text = section_text(body, proof_section)
    if len(CODE_FENCE_RE.findall(proof_text)) < 2:
        problems.append(f'"{proof_section}" must contain a literal fenced artifact, not a description of one')
    patch_section = "4. Hardened Architectural Patch"
    patch_text = section_text(body, patch_section)
    if len(CODE_FENCE_RE.findall(patch_text)) < 2:
        problems.append(f'"{patch_section}" must contain a diff or explicit corrected artifact, not prose')
    return problems


def check_test_first(body: str) -> list[str]:
    problems = []
    red_section = "2. Executable Failing Test (Red)"
    red_text = section_text(body, red_section)
    if len(CODE_FENCE_RE.findall(red_text)) < 2:
        problems.append(f'"{red_section}" must contain a fenced code block, not just prose')
    elif not FAILURE_MARKER_RE.search(fenced_text(red_text)):
        problems.append(f'"{red_section}" must show a raw failure (FAILED/AssertionError/non-zero exit)')
    green_section = "4. Verified Passing Execution (Green)"
    green_text = section_text(body, green_section)
    if len(CODE_FENCE_RE.findall(green_text)) < 2:
        problems.append(f'"{green_section}" must contain a fenced code block, not just prose')
    if not METRIC_RE.search(fenced_text(green_text)):
        problems.append(f'"{green_section}" must include at least one concrete numeric metric')
    return problems


def check_postmortem(body: str) -> list[str]:
    problems = []
    symptom_section = "1. Incident Symptom & Alert Payload"
    symptom_text = section_text(body, symptom_section)
    if len(CODE_FENCE_RE.findall(symptom_text)) < 2:
        problems.append(f'"{symptom_section}" must contain a literal fenced alert/log payload')
    whys_section = "3. 5-Whys Root Cause Deep-Dive"
    whys_text = section_text(body, whys_section)
    why_steps = sum(1 for line in whys_text.splitlines() if WHY_STEP_RE.match(line))
    if why_steps != 5:
        problems.append(f'"{whys_section}" has {why_steps} numbered "Why" step(s), expected exactly 5')
    if HUMAN_ERROR_RE.search(whys_text):
        problems.append(f'"{whys_section}" stops at "human error" instead of a genuine root cause')
    fix_section = "4. Permanent Surgical Fix (Diff)"
    fix_text = section_text(body, fix_section)
    if len(CODE_FENCE_RE.findall(fix_text)) < 2:
        problems.append(f'"{fix_section}" must contain a fenced diff')
    monitoring_section = "5. Blameless Postmortem & Preventative Monitoring Rules"
    monitoring_text = section_text(body, monitoring_section)
    if not (METRIC_RE.search(monitoring_text) and ACTION_WORD_RE.search(monitoring_text)):
        problems.append(
            f'"{monitoring_section}" must name a concrete monitoring rule (a metric + threshold + action)'
        )
    return problems


ARCHETYPE_CHECKS = {
    "contrast": check_takeaway_count,
    "trajectory": check_trajectory,
    "gated-pipeline": check_gated_pipeline,
    "decision-tree": check_decision_tree,
    "elicitation": check_elicitation,
    "adversarial-audit": check_adversarial_audit,
    "test-first": check_test_first,
    "postmortem": check_postmortem,
}


def check_placeholders(text: str) -> list[str]:
    problems = []
    for pattern, label in PLACEHOLDER_PATTERNS:
        match = pattern.search(text)
        if match:
            snippet = match.group(0).strip().replace("\n", " ")
            if len(snippet) > 60:
                snippet = snippet[:57] + "..."
            problems.append(f"found {label}: {snippet!r}")
    if ELLIPSIS_LINE_RE.search(text):
        problems.append("found a standalone '...' line where real content belongs")
    return problems


def validate(text: str) -> list[str]:
    fields, body = parse_frontmatter(text)
    archetype, problems = resolve_archetype(fields)
    if archetype is None:
        return problems
    problems += check_frontmatter(fields, archetype)
    problems += check_sections(body, archetype)
    if not problems:
        problems += ARCHETYPE_CHECKS[archetype](body)
    problems += check_placeholders(text)
    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a filled-in canonical skill example.")
    parser.add_argument("file", type=Path, help="Markdown example file to check.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text = args.file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"{args.file}: file not found")
        return 2
    except OSError as exc:
        print(f"{args.file}: could not read file ({exc})")
        return 2

    problems = validate(text)
    if problems:
        print(f"{args.file}: {len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"{args.file}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
