# Authoring a Canonical Skill Example

How to produce a `<skill>/examples/` entry: a complete, production-ready worked
example for a realistic scenario in that skill's domain, in whichever of eight
**archetypes** fits the scenario. Use this when asked to "author," "generate,"
or "add a canonical example" (in any archetype) for `hep-computing` itself
or for another skill.

## Which archetype fits?

A quick triage before generating anything - itself formalized as this
package's own Decision-Tree archetype in miniature:

| Trigger | Archetype |
|---|---|
| Teaching one principle by contrasting a wrong way and a right way to do the same thing | **Contrast** |
| Walking a single raw input (a bug report, an incident page) start-to-finish through triage, execution, and verification | **[A] Execution Trajectory** |
| Building one complex artifact incrementally, where each stage must clear an explicit acceptance gate before the next starts | **[B] Gated Pipeline** |
| Choosing among several plausible responses to an ambiguous trigger, then committing to and executing one | **[C] Decision-Tree** |
| Starting from a vague, underspecified request and needing to demonstrate structured clarification before committing to a spec | **[E] Interactive Elicitation ("Grill-Me")** |
| Stress-testing a seemingly sound artifact to surface non-obvious failure modes before it ships | **[R] Adversarial Audit / Red-Teaming** |
| Demonstrating a strict test-first workflow for a demanding, checkable target | **[T] Test-First / Red-to-Green** |
| Reconstructing a high-severity incident from first alert to permanent fix | **[P] Incident Postmortem & RCA** |

If a scenario could fit two archetypes, prefer the one whose fixed sections
already match the scenario's natural shape (e.g. a scenario with real
pass/fail checkpoints is Gated Pipeline even if it could be flattened into a
Trajectory; a scenario driven by an ambiguous *request* is Elicitation, while
one driven by a finished *artifact* under attack is Adversarial Audit).

## The eight generation prompts

The reusable core - each archetype's literal template, with its blanks bound
to concrete values before running it. The first four share the same opening
clause and a seniority word that escalates with the archetype's scope and
authority (see "Role/seniority convention" below). The second four - [E], [R],
[T], [P] - instead attach a distinct actor *stance* per archetype rather than
scaling on seniority alone (see "Actor-stance convention" below).

**Contrast**
```
Act as a senior {role} to create a standard example for `{skill}/examples/` in the
`{skill}` skill. Using a realistic {domain_use_case}, draft a complete,
production-ready artifact with zero placeholders. Format the artifact as a direct
contrast between a "Common Weak Approach" and an "Expert-Level Best Practice",
followed by {n} key takeaways explaining the architectural difference.
```

**[A] Execution Trajectory**
```
Act as a senior {role} to create a task-oriented execution trajectory example for
`{skill}/examples/` in the `{skill}` skill. Starting from a realistic, raw
{problem_input}, demonstrate a step-by-step resolution workflow. Structure the
artifact as: 1. Task Input & Context, 2. Root-Cause Triage & Action Plan,
3. Surgical Execution (exact commands, tool usage, or code modifications),
4. Verification Evidence (log outputs or automated test pass), and 5. Final
Deliverable Summary.
```

**[B] Gated Pipeline / Multi-Phase**
```
Act as a principal {role} to create a multi-phase workflow example for
`{skill}/examples/` in the `{skill}` skill. For a complex {high_stakes_task}, show
how to incrementally construct the artifact through explicit quality gates.
Structure the artifact across 3 distinct phases: Phase 1: Input Extraction & Gap
Formulation (with acceptance gate), Phase 2: Draft Synthesis (aligning with
specific regulatory/evaluation criteria), and Phase 3: Red-Team Review & Final
Artifact Packaging (stress-testing assumptions and final polish).
```

**[C] Decision-Tree / Branching Response**
```
Act as a lead {role} to create a branching decision-tree example for
`{skill}/examples/` in the `{skill}` skill. Given a complex
{challenging_scenario_with_edge_cases}, define a clear triage matrix mapping
triggers to resolution strategies. Select the most critical branch and provide a
complete, end-to-end execution script showing exact actions, communication
scripts, and fallback safeguards.
```

**[E] Interactive Elicitation ("Grill-Me")**
```
Act as a principal {role} to create an interactive elicitation example for
`{skill}/examples/` in the `{skill}` skill. Starting from an underspecified, vague
{user_request}, demonstrate how the agent avoids hallucination and conducts a
structured inquiry. Structure the artifact as: 1. Raw Ambiguous Input, 2. Missing
Constraint Analysis, 3. Socratic Clarification Round (3-4 high-impact,
multiple-choice questions), 4. User Feedback Integration, and 5. Final
Mutually-Agreed Specification Document.
```

**[R] Adversarial Audit / Red-Teaming**
```
Act as a ruthless {role} (e.g., Lead Auditor / Red-Teamer) to create an
adversarial stress-testing example for `{skill}/examples/` in the `{skill}`
skill. Given a seemingly sound {candidate_artifact}, actively attack it to
uncover non-obvious failure modes. Structure the artifact as: 1. Initial
Candidate Artifact, 2. Attack Vectors & Stress-Tests (identifying specific
mathematical, logical, or security flaws), 3. Concrete Counter-Example / Exploit
Proof, 4. Hardened Architectural Patch, and 5. Proof of Robustness Post-Fix.
```

**[T] Test-First / Red-to-Green**
```
Act as a test-driven {role} to create a Red-to-Green specification example for
`{skill}/examples/` in the `{skill}` skill. For a demanding {target}, demonstrate
a strict test-first implementation workflow. Structure the artifact as:
1. Acceptance Invariants & Boundary Constraints, 2. Executable Failing Test (Red)
with raw terminal failure output, 3. Minimal Code Implementation, 4. Verified
Passing Execution (Green) with performance metrics, and 5. Regression Guard
Summary.
```

**[P] Incident Postmortem & RCA**
```
Act as a Site Reliability / Principal {role} to create a postmortem
incident-response example for `{skill}/examples/` in the `{skill}` skill.
Reconstruct a high-severity {incident} from triage to permanent fix. Structure
the artifact as: 1. Incident Symptom & Alert Payload, 2. Immediate Triage &
Blast-Radius Mitigation (rollback or bypass), 3. 5-Whys Root Cause Deep-Dive,
4. Permanent Surgical Fix (Diff), and 5. Blameless Postmortem & Preventative
Monitoring Rules.
```

Common blanks:
- `{role}` - a specific seniority + specialty (e.g. "Staff Software Engineer",
  "Senior Experimental Particle Physicist"), not a generic "expert."
- `{skill}` - the target skill's folder name (e.g. `hep-analysis`).
- `{domain_use_case}` / `{problem_input}` / `{high_stakes_task}` /
  `{challenging_scenario_with_edge_cases}` / `{user_request}` /
  `{candidate_artifact}` / `{target}` / `{incident}` - a concrete, narrow
  scenario grounded in that skill's own reference material, not invented or
  generic.
- `{n}` (Contrast only) - the number of key takeaways; default 4, minimum 3,
  maximum 6.

### Role/seniority convention (keep this, don't flatten it)

Each archetype escalates the actor's seniority on purpose:

| Archetype | Seniority word | Why |
|---|---|---|
| Contrast | senior | Teaching a single principle by comparison - individual-contributor judgment call. |
| Execution Trajectory | senior | Hands-on resolution of one concrete input - still IC-level, but end-to-end. |
| Gated Pipeline | **principal** | High-stakes, multi-phase construction against external (regulatory/evaluation) criteria - needs the authority to define acceptance gates. |
| Decision-Tree | **lead** | Requires the standing to define a triage matrix and commit to a branch on others' behalf, including fallback/communication responsibility. |

### Actor-stance convention (second wave - not a plain seniority ladder)

[E]/[R]/[T]/[P] don't scale on seniority alone - each attaches a distinct
*stance* the generating agent must adopt. Keep this as an authoring rule:

| Archetype | Actor framing | Why that framing matters |
|---|---|---|
| [E] Elicitation | principal {role} | Needs standing to decide the specification is final, not just to ask questions. |
| [R] Adversarial Audit | **ruthless** {role} (Lead Auditor / Red-Teamer) | The example fails its purpose if the "attack" is polite or superficial - the stance word is load-bearing, not decorative. |
| [T] Test-First | **test-driven** {role} | The workflow only teaches the right lesson if Red genuinely comes before Green - a role note, reinforced by section order. |
| [P] Postmortem | Site Reliability / Principal {role} | Needs incident-command authority (can order a rollback) and blameless-postmortem authority (can write the final RCA). |

Running one of the eight prompts above is content generation, not something a
stdlib script can do correctly for physics or ML domain content - domain
correctness needs an agent actually reasoning through the example with the
target skill's own `references/` loaded, the way a person would. The scaffold
and validator scripts in the workflow below only produce and check structure;
they do not write or judge the domain content itself.

## Workflow

1. **Scaffold.** Run `<plugin root>/skills/hep-computing/scripts/generate_skill_example.py` with `--archetype`,
   `--skill`, `--role`, and that archetype's scenario flag (`--use-case` /
   `--problem-input` / `--high-stakes-task` / `--scenario` / `--user-request` /
   `--candidate-artifact` / `--target` / `--incident`; `--takeaways` is
   valid only with `--archetype contrast`) to emit an empty skeleton with the
   right frontmatter and section headers at the right path - mirrors how
   `hep-computing`'s `create_story_card.py` scaffolds a story card without
   inventing the story.
2. **Fill.** Replace every skeleton placeholder with real content per that
   archetype's format spec below. Zero placeholders (see below).
3. **Validate.** Run `<plugin root>/skills/hep-computing/scripts/validate_skill_example.py <file>` - it reads the
   `archetype:` frontmatter field to pick the rule set, then mechanically
   rejects structural defects and placeholder content. It cannot judge domain
   correctness (see Correctness review below).
4. **Index.** Add or update `<skill>/examples/README.md`, a one-row-per-example
   table: `Example | Archetype | Scenario | One-line takeaway`.
5. **Wire it up.** If this is the first example for that skill, add
   `examples/README.md` and the new example file to that skill's own
   `scripts/validate_skill_bundle.py` `REQUIRED_PATHS` (or, for a skill whose
   validator checks orphaned files by scanning `references/`/`scripts/`/`assets/`
   only, no change is needed there - confirm which kind the target skill has
   before assuming). Log the pass in that skill's `VALIDATION.md`.

## Format specification

Shared conventions across all eight archetypes:

- **File location:** `<skill>/examples/<NN>-<archetype>-<slug>.md`, where
  `archetype` is one of `contrast`, `trajectory`, `gated-pipeline`,
  `decision-tree`, `elicitation`, `adversarial-audit`, `test-first`,
  `postmortem` - a two-digit prefix for stable ordering, plus one
  `<skill>/examples/README.md` index.
- **Frontmatter:** `role:`, `skill:`, `archetype:`, plus one archetype-specific
  scenario field (see below), so the validator and index generator can read it
  back without re-parsing prose. A file with no `archetype:` field is treated
  as `contrast` by the validator, for backward compatibility with examples
  written before this reference and its scripts became archetype-aware; new
  examples of any archetype, including Contrast, should set `archetype:`
  explicitly.
- **Zero-placeholder rule (all archetypes):** no `TODO`, `TBD`, `XXX`, `FIXME`,
  `Lorem ipsum`, bracketed stand-ins like `[Your ...]`, or trailing `...` where
  real content belongs; every command, log excerpt, or code fence must be
  complete and literal, not illustrative.
- **Language.** English, matching this repository's rule that all maintained
  instructions, templates, and metadata are in English.
- **Diversity rule (all archetypes, including [E]/[R]/[T]/[P]).** Every
  archetype ships 3 examples per skill, matching Contrast/Trajectory/
  Gated-Pipeline/Decision-Tree's original pattern - the 3 examples within one
  `<skill>/archetype` pair must target genuinely different scenarios, failure
  modes, or artifacts (never 3 variations on the same complaint or bug), so the
  differentiation reads as structural, not stylistic. This is a curation
  responsibility: nothing mechanically checks conceptual distinctness within a
  skill, the same way nothing has ever checked it for the four original
  archetypes.
  `<plugin root>/skills/hep-computing/scripts/check_example_diversity.py` is retained but historical: an earlier,
  narrower release of `[E]/[R]/[T]/[P]` shipped only 3 examples *total* per
  archetype (one per skill, no skill repeated), and that script enforced the
  no-repeated-skill constraint for that specific batch. It no longer reflects
  how these four archetypes are authored - every skill now carries all four -
  and should not be run as a gate on new example batches.

**Contrast** - `## Scenario`, `## Common Weak Approach`, `## Expert-Level Best
Practice`, `## Key Takeaways` (bulleted, default N = 4, min 3 / max 6).
Frontmatter scenario field: `use_case:`.

**[A] Trajectory** - five fixed sections, in this exact order: `## 1. Task
Input & Context`, `## 2. Root-Cause Triage & Action Plan`, `## 3. Surgical
Execution`, `## 4. Verification Evidence`, `## 5. Final Deliverable Summary`.
Section 3 must contain at least one literal command/diff/code block; section 4
must contain a literal log excerpt or test-runner output, not a description of
one - the validator checks for a fenced code block in both sections, not just
prose. Frontmatter scenario field: `problem_input:`.

**[B] Gated Pipeline** - three fixed phase headings, each containing a
`**Gate:**` sub-line stating the explicit pass/fail criterion before moving on
(Phase 3's gate is the final release/merge criterion, not an intermediate
one): `## Phase 1: Input Extraction & Gap Formulation` (ends with `**Gate:**
...`), `## Phase 2: Draft Synthesis` (must name the specific
regulatory/evaluation criteria it aligns to - e.g. a cited section of
`references/...md` for that skill, not a vague "best practices"), `## Phase 3:
Red-Team Review & Final Artifact Packaging` (must list at least one assumption
it stress-tested and what changed as a result). Frontmatter scenario field:
`high_stakes_task:`.

**[C] Decision-Tree** - `## Triage Matrix` (a markdown table, columns `Trigger
| Resolution Strategy`, at least 3 rows so it's a real tree, not a single
if/else), `## Selected Branch` (states which row was chosen and why, given the
scenario), `## End-to-End Execution Script` (the full walkthrough for that
branch: actions, any communication script verbatim, not summarized), `##
Fallback Safeguards` (what happens if the chosen branch's primary action fails
or the trigger was misclassified). Frontmatter scenario field: `scenario:`.

**[E] Elicitation** - five fixed sections in order: `## 1. Raw Ambiguous
Input`, `## 2. Missing Constraint Analysis`, `## 3. Socratic Clarification
Round`, `## 4. User Feedback Integration`, `## 5. Final Mutually-Agreed
Specification Document`. Section 3 must contain exactly 3 or 4 questions,
each with lettered multiple-choice options (a numbered question line followed
by `a)`/`b)`/... option lines) - a question with no options fails.
Frontmatter scenario field: `user_request:`.

**[R] Adversarial Audit** - `## 1. Initial Candidate Artifact`, `## 2. Attack
Vectors & Stress-Tests`, `## 3. Concrete Counter-Example / Exploit Proof`,
`## 4. Hardened Architectural Patch`, `## 5. Proof of Robustness Post-Fix`.
Section 2 must enumerate at least 2 distinct, separately-labeled attack
vectors (not one paragraph of prose); section 3 must contain a literal
artifact (failing input, exploit payload, or a disproof step), not a
description of one; section 4 must be a diff or an explicit corrected
artifact, not prose describing a fix. Frontmatter scenario field:
`candidate_artifact:`.

**[T] Test-First** - `## 1. Acceptance Invariants & Boundary Constraints`,
`## 2. Executable Failing Test (Red)`, `## 3. Minimal Code Implementation`,
`## 4. Verified Passing Execution (Green)`, `## 5. Regression Guard Summary`.
Section 2 must contain a fenced block showing an actual failure (`FAILED`,
`AssertionError`, non-zero exit, or equivalent) - prose alone fails
validation; section 4 must contain a fenced block showing a pass plus at
least one concrete numeric metric (latency, throughput, tolerance, coverage
%). Frontmatter scenario field: `target:`.

**[P] Postmortem** - `## 1. Incident Symptom & Alert Payload`, `## 2.
Immediate Triage & Blast-Radius Mitigation`, `## 3. 5-Whys Root Cause
Deep-Dive`, `## 4. Permanent Surgical Fix (Diff)`, `## 5. Blameless
Postmortem & Preventative Monitoring Rules`. Section 1 must include a
literal fenced alert/log payload; section 3 must contain exactly 5 numbered
"Why" steps, each one cause-to-effect sentence, terminating in a genuine
root cause (not "human error" as a stopping point - that fails a
lightweight blamelessness check); section 4 must be a diff; section 5 must
name at least one concrete, checkable monitoring rule (a metric + threshold
+ action), not "add more monitoring". Frontmatter scenario field:
`incident:`.

Postmortem (and every archetype that tells a story) is an illustrative
scenario, not a real event: say so in the opening lines (for example a
`> Illustrative scenario` note under the title), and keep durations, counts
and timestamps identical wherever they recur (header, timeline, body, 5-Whys).

## Correctness review

The validator enforces structure, per-archetype rules (gate lines, table
shape, code-fence presence), and rejects placeholders; it cannot verify that a
`hep-analysis` systematics example is physically correct, that a
`physics-ml` example's code actually runs, or that Gated Pipeline's Phase 2
cites a genuinely specific regulatory/evaluation criterion rather than a vague
"industry best practices" - that specificity check is a review responsibility,
not a mechanical one. Treat all of this as a review step, not something to
automate away: before merging a new example, have it read (or, for runnable
code, executed) by someone - or an agent with that skill's own `references/`
loaded - able to judge that domain.

Postmortem's "5-Whys must reach a real root cause" check is only lightly
mechanical: the validator can grep for "human error" as a lazy stop, but it
cannot verify the causal chain is *actually* correct - that stays a
domain-review responsibility, same as for the other archetypes' technical
content. Likewise, nothing mechanically verifies that a skill's 3 examples in
one archetype are conceptually distinct scenarios rather than near-duplicates
of each other - that is a hand-curation responsibility for every archetype,
the same way it always has been for Contrast/Trajectory/Gated-Pipeline/
Decision-Tree. (`check_example_diversity.py` exists but checks a different,
now-historical constraint - see the Diversity rule above.)

## Cross-skill use

This reference lives only in `hep-computing` and is shared by cross-link
rather than copied into each skill - each rollout skill's own "When to Load
References"-equivalent section points back here. The plugin ships every skill
together, so the pointer always resolves.

Don't add `examples/` to a skill's `REQUIRED_PATHS` (or equivalent orphan
check) until that skill actually has a populated `examples/` directory - an
empty requirement would make the validator lie about coverage.
