# Task Authoring (guide)

## When to read this file

This file holds the routing and rules for task authoring. Read it when writing an implementation-ready task/ticket/spec for another human or agent, authoring a canonical worked example, or designing a prompt or agentic loop.

Turn a short natural-language request into an implementation-ready Task
Markdown document by reading the applicable authoring reference, inspecting
the target repository, and classifying every claim as Confirmed, Inferred, or
Unresolved - never fabricating a project-specific detail to make the task
look complete.

## Core Workflow

This is the workflow for the task-document job. Authoring a canonical example or
designing a prompt has no target repository to inspect: for those, go straight
to the matching reference under "When to Load References".

1. **Understand the user intent.** Extract the primary objective, the
   requested feature/analysis/fix/investigation, explicit constraints, the
   requested output format, and known domain context. Do not expand the task
   yet.
2. **Identify the relevant authoring reference.** Locate the authoring
   reference that best matches the request - this skill's own
   [assets/task-template.md](../assets/task-template.md) and
   [references/](./) first, and any repository-defined authoring
   instructions the target repo itself carries (a `CONTRIBUTING.md`, an
   existing task-template file, a sibling skill's own conventions). Prefer
   repository-defined instructions over this skill's default style. If
   multiple references are relevant, use the smallest sufficient set.
3. **Read the authoring reference before drafting.** Extract the required
   sections, the expected level of detail, formatting conventions, the
   acceptance-criteria style, required technical context, and any examples of
   strong and weak tasks it carries. Do not assume the authoring format from
   memory when a reference is available - see
   [assets/task-template.md](../assets/task-template.md) and
   [references/acceptance-criteria.md](acceptance-criteria.md).
4. **Inspect the target repository.** Before introducing any project-specific
   implementation detail, look at READMEs, source code, configuration files,
   tests, CI configuration, documentation, existing tasks, directory
   structure, and naming conventions. Prefer repository facts over generic
   domain assumptions - including the fact that a directory, dataset, or
   pipeline you expected to exist does not.
5. **Build an evidence model.** Classify every piece of information in the
   draft into exactly one of:
   - **Confirmed** - directly supported by user input, repository content, or
     an authoring reference.
   - **Inferred** - a reasonable technical conclusion derived from confirmed
     information. Inferences must never be written as if they were
     repository facts.
   - **Unresolved** - cannot be determined from available context (dataset
     version, production campaign, performance target, reference baseline,
     required hardware, expected threshold, and similar). Write these as
     `TBD`, `Open Question`, or `Requires Confirmation` - never fabricate a
     value merely to make the task appear complete.

## Generic Agent Instruction

This 13-point instruction is the reusable contract every supported agent
follows, regardless of vendor. When asked to create or refine an engineering
task:

1. Read the relevant task-authoring guide or reference before drafting.
2. Inspect the target repository for relevant implementation details.
3. Prefer repository facts over generic assumptions.
4. Distinguish confirmed information from inference.
5. Do not invent project-specific details.
6. Mark unresolved information as TBD, Open Question, or Requires
   Confirmation.
7. Follow the repository's task-authoring structure and conventions.
8. Define clear scope and explicit non-goals.
9. Include concrete deliverables.
10. Write measurable and verifiable acceptance criteria.
11. Include validation instructions where appropriate.
12. Ensure the task contains enough context for another human or AI agent to
    implement it independently.
13. Validate the final task against the authoring reference before writing
    it - see
    [references/task-quality-checklist.md](task-quality-checklist.md).

## When to Load References

- **Output contract for the generated document** (exact section list, order,
  one-line placeholder guidance) ->
  [assets/task-template.md](../assets/task-template.md)
- **Acceptance-criteria style** (what makes a criterion verifiable vs. vague)
  -> [references/acceptance-criteria.md](acceptance-criteria.md)
- **Final quality gate before writing the task** ->
  [references/task-quality-checklist.md](task-quality-checklist.md);
  when a shell is available, also run
  `python3 <plugin root>/skills/hep-computing/scripts/lint_task.py TASK.md --repo <target repo>` (sections,
  empty sections, placeholders, cited paths that do not exist, loop limits)
- **How a specific agent environment discovers or loads this skill** (Claude
  Code, Codex, Antigravity, or an unlisted generic agent) ->
  [host-notes.md](host-notes.md) - discovery notes only, they do
  not restate any rule above.
- **Worked examples per task category** (bug, research, migration, agentic
  loop, data/ML) -> [examples/](../examples/)
- **Authoring a canonical worked example** in any of eight archetypes -
  Contrast (Weak vs. Expert), Execution Trajectory, Gated Pipeline,
  Decision-Tree, Interactive Elicitation ("Grill-Me"), Adversarial Audit /
  Red-Teaming, Test-First / Red-to-Green, or Incident Postmortem & RCA - for
  this or another skill's `examples/` directory ->
  [references/example-authoring.md](example-authoring.md)
- **Designing or budgeting a prompt for an LLM call** - agent skills, prompt
  templates, structured-output contracts, model-tier choice, token budgets ->
  [references/prompt-engineering-and-token-optimization.md](prompt-engineering-and-token-optimization.md)
- **Authoring a task for an agentic, autonomous, or iterative loop** - an
  agent that calls tools repeatedly, a self-correcting pipeline, a
  retry-until-valid process - closed-loop pattern (ReAct, Plan-and-Solve),
  self-healing error feedback, and mandatory guardrails (termination
  condition, maximum-iteration limit, early stopping) ->
  [references/loop-engineering.md](loop-engineering.md)

## Decision Rules

- Prefer repository evidence over assumptions, and prefer an explicit "not
  found" over silence when an expected file or module does not exist.
- Never represent an Inferred conclusion as a Confirmed repository fact.
- Never fabricate Unresolved information merely to make Open Questions look
  shorter or the task look more complete.
- A claim in the request about the repository or its history (an endpoint,
  signup flow, caller or column exists; code is "unused" or "slow"; why
  something was added) is Unresolved until you have checked it. Background
  states what the repository shows. When the repository does not show the
  premise or contradicts it, say so in Background and ask in Open Questions;
  do not write the premise as fact or invent its history. When the check
  confirms the premise, write it as Confirmed and do not turn it into a
  question.
- Only cite repository paths that were actually verified to exist.
- A user-supplied or repository-defined format changes the headings, not the
  evidence rules: still check the repository, still label Inferred items, and
  say so inside the format's own slots when the request assumes something the
  repository contradicts (for example a database table that does not exist).
  Add no sections the format does not have.
- When the request is "write the task, then implement it", deliver the task
  document and stop there. Say that implementation is a separate step for
  [agile-development-guide.md](agile-development-guide.md) (or a domain skill); do not write the implementation
  code in the same reply.
- When the change is destructive or hard to reverse (dropping a column or
  table, deleting data, a migration with no down path), say so in Technical
  Approach, require a backup or rollback path in Acceptance Criteria, and list
  the readers of the thing being removed that the repository shows.
- A canonical worked example that presents an incident, run, dataset or
  measurement (any archetype, Postmortem above all) is a constructed
  scenario: label it illustrative in its opening lines, keep every number and
  date in it consistent from header to body, and never present invented
  specifics (dates, counts, durations, customers) as a real event. For a
  skill example this applies to a request like "write a postmortem example
  for ..."; a real incident the user describes is still written up as given.
- Keep agent-specific adapters discovery-only; the Core Workflow and the
  template contract live in exactly one place each.
- When the work under authoring is an agentic, autonomous, or iterative loop,
  name its closed-loop pattern in Technical Approach and fix its termination
  condition, maximum-iteration limit, and early-stopping condition in
  Acceptance Criteria - see
  [references/loop-engineering.md](loop-engineering.md). Never
  leave an iteration ceiling unbounded or invent one the requester never
  gave; mark it Open Question / TBD instead.

## Caveats

- This skill decides *how to write the task*, not *how to implement it* -
  pair it with [agile-development-guide.md](agile-development-guide.md) (or a domain skill) once the generated
  task is handed off for implementation.
- Building a new LLM, a vendor-specific API integration, or a full autonomous
  development agent is out of scope; so is replacing human review for
  ambiguous product or domain decisions. Authoring the task specification for
  such a loop - its pattern, error handling, and guardrails - is in scope;
  see [references/loop-engineering.md](loop-engineering.md).
- If the user explicitly supplies their own task template or format, follow
  it instead of [assets/task-template.md](../assets/task-template.md) -
  user instructions take precedence over this skill's default structure.

## Example Prompts This Skill Handles Well

- "Create a task for RICH reconstruction performance analysis."
- "Write a task for adding a CSV export endpoint for admins."
- "Turn this bug report into an implementation-ready task doc."
- "Draft a research task investigating whether we can deduplicate the C++
  design guidelines shared between two skills."
- "Generate a canonical `examples/` entry for the `hep-analysis` skill contrasting a
  weak vs. expert systematics writeup." (Contrast archetype)
- "Walk the cart-total discount-code bug report through a full triage-to-verified-fix
  trajectory for `hep-computing/examples/`." (Execution Trajectory archetype)
- "Author a gated-pipeline example showing how to draft and red-team an RFC for a
  feature-flagged rollout." (Gated Pipeline archetype)
- "Author a decision-tree example for triaging an ambiguous production incident page."
  (Decision-Tree archetype)
- "Generate a Grill-Me elicitation example for `hep-analysis` starting from
  'can you check if there's a signal in this dataset?'" (Elicitation archetype)
- "Red-team this 'SOTA accuracy' training writeup for leakage or a cherry-picked
  seed." (Adversarial Audit archetype)
- "Write a test-first example for a DataLoader throughput invariant, red test
  through green with metrics." (Test-First archetype)
- "Author a postmortem example for a distributed training run that diverged at
  hour 30." (Postmortem archetype)
- "Design a prompt template for a classification pipeline and give me a token budget."
- "Create a task for an autonomous log-triage agent that retries against a
  flaky search API until it finds the root cause or hits an iteration limit."
