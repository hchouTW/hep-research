# Geant4 architecture: working base

This folder holds the plan, architecture and implementation specs for the Geant4 work in hep-research: correctness
fixes and boundary artifacts (task A), a second simulation backend with reconstruction and the J15 minimal
spectrometer (task B), and automated detector design search (task C). It lives on the branch
`worktree-geant4-architecture`, based on `main` at `9f08796` (0.23.0 plus unreleased changes, contracts 3.5.0).

**If you are an agent starting work here:** read `plan.md` §0 (stages), §10 (execution in an isolated worktree), §6
(gates) and §4 (interface ownership), then the task card (§0) of the task you are working on. Read `architecture.md`
only for the reasons behind a rule.

**Run every stage in its own isolated git worktree** (`plan.md` §10): worktree `.claude/worktrees/geant4-<stage>` on
branch `geant4-<stage>`, created from the latest `main` that contains the prerequisite stages (in Claude Code:
`EnterWorktree`, or `isolation: "worktree"` for subagents). Confirm the top-level path, branch and a clean status before
writing code; never change files in the main checkout or another worktree; never use bare `git stash` (the stash is
shared by all worktrees). These documents themselves are edited in worktree `.claude/worktrees/geant4-architecture` on
branch `worktree-geant4-architecture`.

**Current state (2026-10-23):** everything here awaits the user's and the maintainer's approval; do not start
implementation before that. The specs were rewritten on 2026-10-23 from `plan.md`, after an overall evaluation of the
earlier plan (`plan.md` §1).

## Which document decides what

| Document | Decides |
|---|---|
| `plan.md` | Stage order and dependencies, IDs and version placeholders (CV1–CV3), interface ownership, gates, the merged list of open decisions, cross-task risks, the execution environment (isolated worktree per stage, §10) |
| `task-a-core.md`, `task-b-j15.md`, `task-c-design-search.md` | Work items and acceptance of their stages; the J15 numbers (task B) |
| `architecture.md` | Design rationale, reference experiments, superseded designs; where it disagrees with a spec, the spec wins and the disagreement is reported |

Each document has a Traditional Chinese original and an English translation (`.en.md`) with the same sections,
tables, checkboxes and numbers. If they disagree, the Chinese wins until the English is corrected; change both
together.

## Stages

```
A1 ──▶ A2 ──▶ B1 ──▶ B2 ──▶ B3 ─────────┐
 │                    │                  ▼
 └──▶ C1 ─────────────┴──────▶ C2 ──▶ C3
```

| Stage | Content | Depends on | Version |
|---|---|---|---|
| A1 | Fix defects D1–D8, D10 (benchmark table, scope, isolation, statistics); shared `core/` modules; J14 regenerated | — | contracts CV1 (sci-fix) |
| A2 | `g4sim`, per-event seeding, `layered_sim` writes the three boundary artifacts, study layer reads only them (D9) | A1 | geant4 adapter 0.2.0 |
| B1 | `element_sim` (box elements, field, plane crossings, calorimeter leakage), per-event ROOT files, `simroot`, `check-spec` | A2 | geant4 adapter 0.3.0 |
| B2 | `simreco`, processing chains, verification / regression / surrogate classes | B1 | geant4 adapter 0.4.0, contracts CV2 |
| B3 | The J15 study | B2 | example and docs |
| C1 | Requirements, component catalogue, design grammar, F0 analytic search, closure tests | A1 | detector-design adapter 0.1.0 |
| C2 | F1/F2 simulation evaluation, confirmation runs, requirement decisions, paired comparison | B2, C1 | detector-design 0.2.0, geant4 adapter 0.5.0, contracts CV3 |
| C3 | J16 automated-design example, optional MOBO backend | B3, C2 | detector-design 0.3.0 |

## Files

| File | Content |
|---|---|
| `plan.md` / `plan.en.md` | **Program plan:** evaluation of the earlier plan, planning principles, stages, interface ownership, naming, gates, open decisions, risks, document map |
| `task-a-core.md` / `.en.md` | **Task A:** A1 (A1.1–A1.15), A2 (A2.1–A2.10) |
| `task-b-j15.md` / `.en.md` | **Task B:** J15 design (§4), B1 (B1.1–B1.9), B2 (B2.1–B2.6), B3 (B3.1–B3.8) |
| `task-c-design-search.md` / `.en.md` | **Task C:** design (§4), C1 (C1.1–C1.9), C2 (C2.1–C2.9), C3 (C3.1–C3.4) |
| `architecture.md` / `.en.md` | Design rationale with reference to real experiments (ATLAS, CMS, ALICE, Belle II, Key4hep, Allpix², geant-val; PAMELA and AMS-02 for J15) |
| `gate_operating_characteristics.py` | Convergence-gate operating characteristics, two-stage factors, Welch degrees of freedom (task A A1.8, A1.9, appendix B). Needs numpy and scipy; a design aid, not plugin code |
| `j15_design_estimates.py` | J15 design numbers (task B appendix A). Standard library; scipy optional |
| `design_search_closure.py` | Reference values of task C's plane-placement closure test (task C appendix A). Standard library |
| `prototype/phase1-core.patch` | Reference prototype of A1.1, A1.2, the first half of A1.3 and the enum fix of A1.12, with tests; applies to `9f08796`. Predates the current spec (see task A §0); not reviewed for merge |

## Spec layout

All three task specs share one layout: §0 task card, §1 terms and files, §2 prerequisites and provided interfaces,
§3 hard rules, §4 design summary, §5 onward one section per stage (work items and acceptance checklist), then
contracts and versions, checks (task A §8, used by every stage), not done and deferred, open decisions and risks,
suggested order of work, appendices.

Reference notation: "A1.6" is a work item of task A, "B1.3" of task B, "C2.1" of task C; "§8" is a section of the same
document; "task A §3", "plan §4", "architecture §6" are sections of other documents.

## Key decisions already made (by the user)

- **Language split:** per-event processing is C++; Python is the interface and judgement layer; they exchange JSON/CSV
  through separate executables (no Python bindings). One production implementation per quantity.
- **Per-event ROOT files:** detailed per-event information is written as ROOT files through `G4AnalysisManager`
  (g4tools, no ROOT installation), as flat ntuples keyed by `event_id`; read only through `simroot`; not committed.
- **Task order:** task A first; J15 (task B) after task A. Automated design (task C) as proposed on 2026-10-23.

## Working rules

1. Documentation changes: only on branch `worktree-geant4-architecture`, inside its worktree. Implementation: one
   isolated worktree and branch per stage (`plan.md` §10). Do not push to `main` or open a pull request without the
   maintainer's approval.
2. Contract versions are written CV1–CV3; fix the numbers only at merge time.
3. Follow `docs/maintenance.md`: the sci-fix process for A1, the adapter-change steps for A2, B1, B2, C1–C3, and the
   release steps (VALIDATION entry, CHANGELOG, release manifest).
4. Before committing, run at least `tools/check_packaging.py` and `tools/check_layering.py`, and stop if either fails.

## Open decisions

`plan.md` §7 lists all fourteen, each with a recommendation and the stage it blocks.

## Independent review

On 2026-10-23 two agents that did not write the specs reviewed tasks A and B against the code; the confirmed findings
were fixed (each spec's version history lists them), including the two-stage columns of the gate table, which have
been recomputed. The restructured specs and task C have not yet been independently reviewed. The plugin's `review.py`
(`skills/hep-authoring/references/independent-review.md`) can review the English specs on the maintainer's machine; it
needs fork subagents switched off and a host restart, and the document must exist nowhere else on the host. Its record
is advisory, not a human review record (O04/O14).
