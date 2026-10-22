# Geant4 architecture: working base

This folder holds the implementation specs for the Geant4 architecture work in hep-research. It lives on the branch
`worktree-geant4-architecture`, based on `main` at `9f08796` (0.23.0 plus unreleased changes, contracts 3.5.0).

**If you are an agent starting work here:** read this file, then the task card (§0) of the task you are working on.
Do task A first; task B starts only after task A is merged.

**Current state (2026-10-22):** `architecture.md` is the architecture proposal, redesigned with reference to real
experiments (ATLAS, CMS, ALICE, Belle II, Key4hep, Allpix², geant-val; PAMELA and AMS-02 for J15). It sets a backend
interface at the output (run summary, column map, effective config with the actual geometry tree), per-event seeding,
"same decisions" as the meaning of reproducibility, block batch means within one run, five validation classes, a new
`element_sim` backend for J15 instead of reworking `layered_sim`, and four stages (A1, A2, B1, B2). Until the user and
the maintainer approve it, the task specs below describe an older architecture; once approved they are rewritten from
`architecture.md`. Do not start implementation from the task specs before that.

## Files

| File | Content |
|---|---|
| `architecture.md` | **Consolidated architecture** (Traditional Chinese original): problems found, two-plane design, interfaces (spec/2, run summary, effective config, column map, event files, backend interface), statistical methods, contracts, stages, generality, decision record. Section 11 lists what needs approval |
| `architecture.en.md` | English translation of `architecture.md` |
| `gate_operating_characteristics.py` | Recomputes the convergence-gate operating characteristics, two-stage factors and Welch degrees of freedom quoted in `architecture.md` §5.5–5.6. Needs numpy and scipy; a design aid, not plugin code |
| `task-a-core.md` | **Task A** (Traditional Chinese original): phase 1 fixes the `validated-in-scope` defects D1–D10 (sci-fix, contracts C1); phase 2 moves the compute core to C++ (`simcore`, `simroot`, per-event ROOT files; adapter 0.2.0). Work items A1.1–A1.12 and A2.1–A2.12 |
| `task-a-core.en.md` | English translation of `task-a-core.md` |
| `task-b-j15.md` | **Task B** (Traditional Chinese original): the J15 minimal spectrometer (field, plane crossings and the ROOT `crossings` level, `simreco`, `verification` grade, contracts C2; adapter 0.3.0). Work items B1.1–B1.5 and B2.1–B2.3 |
| `task-b-j15.en.md` | English translation of `task-b-j15.md` |
| `j15_design_estimates.py` | Design numbers for J15 (task B appendix A) and the statistics numbers of task A appendix A. Standard library; scipy optional. Not a benchmark reference |
| `prototype/phase1-core.patch` | Reference prototype of A1.1, A1.2, part of A1.3 and the enum fix of A1.10, with tests. Applies to `9f08796` with `git apply`. Written before the current spec: it lacks `target_slabs`, the `longitudinal-profile` target-hash match, the missing-dimension rule, `shower-maximum`, the `dependencies.py` re-derivation and C1 gating of the isolation rule, and gates at a hard-coded 3.6.0. Not reviewed for merge |

## How the specs are organized

Both task documents have the same layout:

| Section | Purpose |
|---|---|
| §0 Task card | goal, scope and out of scope, deliverables, definition of done, what to do before starting |
| §1 Terms | glossary, reference notation, main file paths |
| Hard rules | constraints that block a merge (task A §2; task B §3 adds to them) |
| Work items | numbered items (A1.x, A2.x, B1.x, B2.x), each with what to change and the rules to meet |
| Acceptance | checkbox lists (A1.12, A2.12, task B §10); every box must be ticked |
| Checks | the tools to run at the end of every phase (task A §10) |
| Not done / deferred, decisions, risks | what is deliberately left out, what the maintainer must decide, what may go wrong |
| Suggested order of work | a step-by-step sequence (task A §13, task B §13) |
| Appendices | numbers, baseline check records, sources, version history |

Reference notation: "A1.6" is a work item of task A, "B1.3" of task B; "§8" is a section of the same document;
"task A §2" is a section of the other document.

Editing rules: change the Chinese original and the English translation together, with the same sections, tables,
checkboxes and numbers. If they disagree, the Chinese wins until the English is corrected.

## Key decisions already made (by the user, 2026-10-22)

- **Language split:** the compute core is C++; Python is the interface and judgement layer; they exchange JSON/CSV
  through separate executables (no Python bindings). One production implementation per quantity (task A principle 11).
- **Per-event ROOT files:** detailed per-event information is written by `layered_sim` through `G4AnalysisManager`
  (g4tools, no ROOT installation); flat ntuples keyed by `event_id`; the CSV stays as the summary. Python and
  `simcore` never read ROOT; `simroot` converts to CSV or gives a content hash. ROOT files are not committed.
- **Two tasks:** task A (phases 1 and 2) first; task B (J15) after task A is merged. Task A reserves the spec/2
  `field` block (rejected until task B) and leaves the `crossings` level to task B, so task B needs no change to task
  A's interfaces. If it does, make the change first as an adapter patch release within task A.

## Working rules

1. Work only on this branch, inside the worktree. Do not push to `main` or open a pull request without the
   maintainer's approval.
2. Contract versions are written C1 and C2; fix the numbers only at merge time.
3. Follow `docs/maintenance.md`: the sci-fix process for phase 1, the adapter-change steps for phase 2 and task B,
   and the release steps (VALIDATION entry, CHANGELOG, release manifest).
4. Before committing, run at least `tools/check_packaging.py` and `tools/check_layering.py`, and stop if either fails.

## Open decisions for the maintainer

Task A §12 and task B §12 list them in full:

- phase 1 as a minor (C1) plus a sci-fix;
- whether a statistical comparison is acceptable if bit-identical output cannot be reached on the same host;
- how to confirm the G5 statement that no Geant4 example code was copied;
- hep-computing's agreement to the optional `simulation` property (task A) and the C2 "derived simulation" marker (task B);
- a new required CI job for `simcore` (needs a C++17 compiler);
- where ROOT files are stored and for how long.

## Independent review

The specs have not been independently reviewed. The plugin's `review.py`
(`skills/hep-authoring/references/independent-review.md`) can review `task-a-core.en.md` and `task-b-j15.en.md` on
the maintainer's machine: it needs fork subagents switched off and a host restart, and the document must exist nowhere
else on the host. Its record is advisory, not a human review record (O04/O14).
