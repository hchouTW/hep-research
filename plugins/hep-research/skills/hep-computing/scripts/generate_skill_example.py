#!/usr/bin/env python3
"""Scaffold an empty canonical example for a skill's `examples/` directory.

Purpose: give every `<skill>/examples/*.md` file the right shape - frontmatter
plus the fixed section headers for its archetype - before an agent fills in the
actual domain content. Mirrors how `create_story_card.py` scaffolds a story card
without inventing the story.

What it does: prints (or writes) a markdown skeleton for one of eight archetypes
(`contrast`, `trajectory`, `gated-pipeline`, `decision-tree`, `elicitation`,
`adversarial-audit`, `test-first`, `postmortem`), each with its own frontmatter
scenario field and fixed section headers, one HTML-comment placeholder per
section, and (for `contrast` only) one placeholder bullet per requested
takeaway. It does not generate content - see references/example-authoring.md
for the eight generation prompts and format spec, and
`validate_skill_example.py` for checking a filled-in file.

Usage: `python3 <plugin root>/skills/hep-computing/scripts/generate_skill_example.py --archetype
{contrast,trajectory,gated-pipeline,decision-tree,elicitation,adversarial-audit,test-first,postmortem}
--skill hep-analysis --role "Senior Experimental Particle Physicist"
<scenario-flag> "..." [--output ../hep-analysis/examples/01-slug.md]`. The
scenario flag depends on the archetype: `--use-case` (contrast),
`--problem-input` (trajectory), `--high-stakes-task` (gated-pipeline),
`--scenario` (decision-tree), `--user-request` (elicitation),
`--candidate-artifact` (adversarial-audit), `--target` (test-first), or
`--incident` (postmortem). `--takeaways` (3-6, default 4) is valid only with
`--archetype contrast`. Prints to stdout when `--output` is omitted. Standard
library only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MIN_TAKEAWAYS = 3
MAX_TAKEAWAYS = 6

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

# Maps each archetype to its frontmatter scenario field name and the CLI flag
# that supplies it.
SCENARIO_FIELD = {
    "contrast": ("use_case", "--use-case"),
    "trajectory": ("problem_input", "--problem-input"),
    "gated-pipeline": ("high_stakes_task", "--high-stakes-task"),
    "decision-tree": ("scenario", "--scenario"),
    "elicitation": ("user_request", "--user-request"),
    "adversarial-audit": ("candidate_artifact", "--candidate-artifact"),
    "test-first": ("target", "--target"),
    "postmortem": ("incident", "--incident"),
}


def _frontmatter(args: argparse.Namespace) -> str:
    field, _ = SCENARIO_FIELD[args.archetype]
    scenario_value = getattr(args, field)
    return f"---\nrole: {args.role}\nskill: {args.skill}\narchetype: {args.archetype}\n{field}: {scenario_value}\n---\n"


def _build_contrast(args: argparse.Namespace) -> str:
    takeaway_lines = "\n".join(
        f"- <!-- Takeaway {i}: why the expert approach differs architecturally, not just what changed. -->"
        for i in range(1, args.takeaways + 1)
    )
    return f"""{_frontmatter(args)}
## Scenario

<!-- 2-4 sentences describing the realistic scenario: {args.use_case} -->

## Common Weak Approach

<!-- A complete, realistic artifact showing the failure mode - not a caricature. -->

## Expert-Level Best Practice

<!-- A complete artifact solving the same scenario correctly, with zero placeholders. -->

## Key Takeaways

{takeaway_lines}
"""


def _build_trajectory(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## 1. Task Input & Context

<!-- The realistic, raw input as received: {args.problem_input} -->

## 2. Root-Cause Triage & Action Plan

<!-- How the root cause was found and the plan to resolve it. -->

## 3. Surgical Execution

<!-- At least one literal command, diff, or code block - not a description of one. -->

## 4. Verification Evidence

<!-- A literal log excerpt or test-runner output proving the fix, not a description of one. -->

## 5. Final Deliverable Summary

<!-- What shipped and what changed, in a few sentences. -->
"""


def _build_gated_pipeline(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## Phase 1: Input Extraction & Gap Formulation

<!-- Extract the inputs and name the gaps for: {args.high_stakes_task} -->

**Gate:** <!-- explicit pass/fail criterion before moving to Phase 2 -->

## Phase 2: Draft Synthesis

<!-- Must name the specific regulatory/evaluation criteria this aligns to, e.g. a
cited references/...md section for this skill - not a vague "best practices". -->

**Gate:** <!-- explicit pass/fail criterion before moving to Phase 3 -->

## Phase 3: Red-Team Review & Final Artifact Packaging

<!-- Must list at least one assumption that was stress-tested and what changed
as a result. -->

**Gate:** <!-- the final release/merge criterion, not an intermediate one -->
"""


def _build_decision_tree(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## Triage Matrix

<!-- Given: {args.scenario} -->

| Trigger | Resolution Strategy |
|---|---|
| <!-- trigger 1 --> | <!-- resolution 1 --> |
| <!-- trigger 2 --> | <!-- resolution 2 --> |
| <!-- trigger 3 --> | <!-- resolution 3 --> |

## Selected Branch

<!-- Which row was chosen, and why, given the scenario. -->

## End-to-End Execution Script

<!-- The full walkthrough for that branch: exact actions, any communication
script verbatim (not summarized). -->

## Fallback Safeguards

<!-- What happens if the chosen branch's primary action fails, or the trigger
was misclassified. -->
"""


def _build_elicitation(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## 1. Raw Ambiguous Input

<!-- The verbatim, underspecified request as received: {args.user_request} -->

## 2. Missing Constraint Analysis

<!-- Enumerate the specific missing constraints (target, scope, threshold,
etc.) that make the request impossible to execute safely as stated. -->

## 3. Socratic Clarification Round

<!-- Exactly 3-4 high-impact, multiple-choice questions. Each question needs
lettered options, e.g.:
1. Question text?
   a) Option one
   b) Option two
   c) Option three
-->

## 4. User Feedback Integration

<!-- The user's answers to the clarification round, and how each answer
resolves one of the missing constraints from section 2. -->

## 5. Final Mutually-Agreed Specification Document

<!-- The complete, unambiguous specification derived from the answers, ready
to execute against. -->
"""


def _build_adversarial_audit(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## 1. Initial Candidate Artifact

<!-- The complete, seemingly sound artifact under audit: {args.candidate_artifact} -->

## 2. Attack Vectors & Stress-Tests

<!-- At least 2 distinct, separately-labeled attack vectors (e.g. "Attack
Vector 1: ..."), each identifying a specific mathematical, logical, or
security flaw - not one paragraph of general skepticism. -->

## 3. Concrete Counter-Example / Exploit Proof

<!-- A literal artifact proving the flaw: a failing input, an exploit
payload, or a disproof step - not a description of one. -->

## 4. Hardened Architectural Patch

<!-- A diff or an explicit corrected artifact - not prose describing a fix. -->

## 5. Proof of Robustness Post-Fix

<!-- Evidence the patch actually closes the attack vectors from section 2. -->
"""


def _build_test_first(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## 1. Acceptance Invariants & Boundary Constraints

<!-- The precise, checkable invariants and boundary conditions for: {args.target} -->

## 2. Executable Failing Test (Red)

<!-- A fenced block with the actual failing test code, plus a second fenced
block with the raw terminal failure output (FAILED/AssertionError/non-zero
exit) - not a description of a failure. -->

## 3. Minimal Code Implementation

<!-- The minimal code that makes the failing test pass - no speculative
extras. -->

## 4. Verified Passing Execution (Green)

<!-- A fenced block showing the passing run, including at least one concrete
numeric metric (latency, throughput, tolerance, coverage %). -->

## 5. Regression Guard Summary

<!-- What this test now guards against, and how it prevents the invariant
from silently regressing. -->
"""


def _build_postmortem(args: argparse.Namespace) -> str:
    return f"""{_frontmatter(args)}
## 1. Incident Symptom & Alert Payload

<!-- A literal fenced alert/log payload for: {args.incident} -->

## 2. Immediate Triage & Blast-Radius Mitigation

<!-- The rollback or bypass action taken to stop the bleeding, and why it was
the fastest safe option. -->

## 3. 5-Whys Root Cause Deep-Dive

<!-- Exactly 5 numbered "Why" steps, each one cause-to-effect sentence,
terminating in a genuine root cause - not "human error" as a stopping
point. -->

## 4. Permanent Surgical Fix (Diff)

<!-- A diff implementing the permanent fix for the root cause found above. -->

## 5. Blameless Postmortem & Preventative Monitoring Rules

<!-- A blameless narrative plus at least one concrete, checkable monitoring
rule: a metric + threshold + action - not "add more monitoring". -->
"""


BUILDERS = {
    "contrast": _build_contrast,
    "trajectory": _build_trajectory,
    "gated-pipeline": _build_gated_pipeline,
    "decision-tree": _build_decision_tree,
    "elicitation": _build_elicitation,
    "adversarial-audit": _build_adversarial_audit,
    "test-first": _build_test_first,
    "postmortem": _build_postmortem,
}


def build_skeleton(args: argparse.Namespace) -> str:
    return BUILDERS[args.archetype](args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold an empty canonical example skeleton for a skill's examples/ directory."
    )
    parser.add_argument("--archetype", required=True, choices=ARCHETYPES, help="Example archetype to scaffold.")
    parser.add_argument("--skill", required=True, help="Target skill folder name, e.g. hep-analysis.")
    parser.add_argument("--role", required=True, help="Role to author as, e.g. 'Staff Software Engineer'.")
    parser.add_argument("--use-case", dest="use_case", help="Contrast only: realistic, narrow domain scenario.")
    parser.add_argument("--problem-input", dest="problem_input", help="Trajectory only: realistic, raw problem input.")
    parser.add_argument(
        "--high-stakes-task", dest="high_stakes_task", help="Gated Pipeline only: complex, high-stakes task."
    )
    parser.add_argument(
        "--scenario", dest="scenario", help="Decision-Tree only: challenging scenario with edge cases."
    )
    parser.add_argument(
        "--user-request", dest="user_request", help="Elicitation only: the raw, underspecified user request."
    )
    parser.add_argument(
        "--candidate-artifact",
        dest="candidate_artifact",
        help="Adversarial Audit only: the seemingly sound artifact under audit.",
    )
    parser.add_argument("--target", dest="target", help="Test-First only: the demanding target to implement.")
    parser.add_argument("--incident", dest="incident", help="Postmortem only: the high-severity incident.")
    parser.add_argument(
        "--takeaways",
        type=int,
        default=None,
        help=f"Contrast only: number of key-takeaway placeholders ({MIN_TAKEAWAYS}-{MAX_TAKEAWAYS}, default 4).",
    )
    parser.add_argument("--output", type=Path, help="Optional output path. Prints to stdout when omitted.")
    args = parser.parse_args(argv)

    field, flag_name = SCENARIO_FIELD[args.archetype]
    if not getattr(args, field):
        parser.error(f"--archetype {args.archetype} requires {flag_name}")
    for other_archetype, (other_field, other_flag) in SCENARIO_FIELD.items():
        if other_archetype != args.archetype and getattr(args, other_field):
            parser.error(f"{other_flag} is only valid with --archetype {other_archetype}")

    if args.archetype == "contrast":
        if args.takeaways is None:
            args.takeaways = 4
        if not MIN_TAKEAWAYS <= args.takeaways <= MAX_TAKEAWAYS:
            parser.error(f"--takeaways must be between {MIN_TAKEAWAYS} and {MAX_TAKEAWAYS}")
    elif args.takeaways is not None:
        parser.error("--takeaways is only valid with --archetype contrast")

    return args


def main() -> int:
    args = parse_args()
    content = build_skeleton(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
