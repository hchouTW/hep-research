# Geant4 architecture: working base

This folder holds the architecture and implementation specs for the Geant4 work in hep-research. It lives on the branch
`worktree-geant4-architecture`, based on `main` at `9f08796` (0.23.0 plus unreleased changes, contracts 3.5.0).

**If you are an agent starting work here:** read this file, then the task card (§0) of the task you are working on.
Read `architecture.md` only for the reasons behind a rule; the task specs are the executable specs and win if the two
disagree (report the disagreement). Do task A first; task B starts only after task A is merged.

**Current state (2026-10-22):** `architecture.md` is the architecture, redesigned with reference to real experiments
(ATLAS, CMS, ALICE, Belle II, Key4hep, Allpix², geant-val; PAMELA and AMS-02 for J15). The task specs have been
rewritten from it. All of it awaits the user's and the maintainer's approval; do not start implementation before that.

## Architecture in one paragraph

Per-event processing (simulation, summary accumulation, digitization, reconstruction) is in C++; inference after
merging, decisions, records and contracts are in Python (standard library only). The study layer knows a backend only
through three boundary artifacts: the run summary (`simulation-summary/1`, per-block accumulators with merge rules),
the column map (`simulation-columns/1`) and the effective config (engine-independent envelope plus the actual geometry
tree). Each event is seeded from H(logical-run seed, event number). Reproducibility means the same decisions and labels
(numbers within 1e-9 relative on replay). Standard errors come from block batch means within one run (K ≥ 16), with
exact intervals for low counts, and the convergence gate is an intersection-union test that can report "unresolved"
(incomplete). Benchmarks have a validation class (verification, reference, setup-matched, regression, surrogate,
sanity, interface); only reference and setup-matched on an isolated target can upgrade a label. `layered_sim` is frozen;
J15 uses a new box-element backend, `element_sim`.

## Stages

| Stage | Task | Content | Version |
|---|---|---|---|
| A1 | A | Correctness fixes D1–D10: benchmark table, scope, configuration and isolation, statistics, Python summary producer; J14 regenerated | contracts C1 (minor, sci-fix) |
| A2 | A | `g4common`, per-event seeding, `layered_sim` writes the three boundary artifacts, study layer reads only them | adapter 0.2.0 |
| B1 | B | `element_sim` (box elements, field, plane crossings), per-event ROOT files, `simroot` | adapter 0.3.0 |
| B2 | B | `simreco`, J15 study, C2 (verification, regression, surrogate, transitive processing chains) | adapter 0.4.0, contracts C2 |

## Files

| File | Content |
|---|---|
| `architecture.md` | **Architecture** (Traditional Chinese original): design basis from real experiments, goals and principles, overview, data tiers and run summary, seeds and blocks, validation classes, contracts, code and CI, generality, stages, risks, decision record, superseded designs, sources |
| `architecture.en.md` | English translation of `architecture.md` |
| `gate_operating_characteristics.py` | Recomputes the convergence-gate operating characteristics, two-stage factors and Welch degrees of freedom (task A A1.8, A1.9, appendix A). Needs numpy and scipy; a design aid, not plugin code |
| `task-a-core.md` | **Task A** (Traditional Chinese original): A1 (A1.1–A1.15) and A2 (A2.1–A2.10) |
| `task-a-core.en.md` | English translation of `task-a-core.md` |
| `task-b-j15.md` | **Task B** (Traditional Chinese original): J15 design (§4), B1 (B1.1–B1.8) and B2 (B2.1–B2.11) |
| `task-b-j15.en.md` | English translation of `task-b-j15.md` |
| `j15_design_estimates.py` | Design numbers for J15 (task B appendix A). Standard library; scipy optional. Not a benchmark reference |
| `prototype/phase1-core.patch` | Reference prototype of A1.1, A1.2, the first half of A1.3 and the enum fix of A1.12, with tests. Applies to `9f08796` with `git apply`. Predates the current spec: it lacks `target_slabs`, validation classes, per-benchmark scope dimensions, `hash_scheme`, the `dependencies.py` re-derivation and C1 gating, and gates at a hard-coded 3.6.0. Not reviewed for merge |

## How the specs are organized

| Section | Task A | Task B |
|---|---|---|
| Task card: goal, stages, scope, deliverables, definition of done, before starting | §0 | §0 |
| Terms, notation, main file paths | §1 | §1 |
| Prerequisites from task A | — | §2 |
| Hard rules (block a merge) | §2 | §3 (adds to task A §2) |
| Background: defects D1–D10 | §3 | — |
| Design summary / J15 design | §4 | §4 |
| Stage work items | §5 (A1), §6 (A2) | §5 (B1), §6 (B2) |
| Acceptance checklists | A1.15, A2.10 | B1.8, B2.11 |
| Statistics summary | §7 | — |
| Contracts and versions | §8 | §7 |
| Checks at the end of every stage | §9 | task A §9 |
| Not done and deferred | §10 | §8 |
| Decisions for the maintainer, residual risks | §11 | §9 |
| Suggested order of work | §12 | §10 |
| Appendices: numbers, baseline values, sources, history | A–D | A–C |

Reference notation: "A1.6" is a work item of task A, "B1.3" of task B; "§8" is a section of the same document;
"task A §2" is a section of the other document; "architecture §6" is a section of `architecture.md`.

Editing rules: change the Chinese original and the English translation together, with the same sections, tables,
checkboxes and numbers. If they disagree, the Chinese wins until the English is corrected.

## Key decisions already made (by the user, 2026-10-22)

- **Language split:** per-event processing is C++; Python is the interface and judgement layer; they exchange JSON/CSV
  through separate executables (no Python bindings). One production implementation per quantity.
- **Per-event ROOT files:** detailed per-event information is written as ROOT files through `G4AnalysisManager`
  (g4tools, no ROOT installation), as flat ntuples keyed by `event_id`. In this design they come with `element_sim`
  (task B, B1.4); Python and `simreco` read them only through `simroot`. ROOT files are not committed.
- **Two tasks:** task A first; task B (J15) after task A is merged. If task B needs a change to task A's interfaces,
  make it first as an adapter patch release within task A.

## Working rules

1. Work only on this branch, inside the worktree. Do not push to `main` or open a pull request without the
   maintainer's approval.
2. Contract versions are written C1 and C2; fix the numbers only at merge time.
3. Follow `docs/maintenance.md`: the sci-fix process for A1, the adapter-change steps for A2, B1 and B2, and the release
   steps (VALIDATION entry, CHANGELOG, release manifest).
4. Before committing, run at least `tools/check_packaging.py` and `tools/check_layering.py`, and stop if either fails.

## Open decisions for the maintainer

Task A §11 and task B §9 list them in full; the main ones:

- C1 as a minor plus sci-fix; C2 as a minor;
- how to confirm the G5 statement that no Geant4 example code was copied;
- hep-computing's agreement to the optional `simulation` property (task A) and to transitive processing chains (task B);
- the two-stage factor F₀.₉₀ or F₀.₉₅;
- live re-recording of J14's scan and variation runs, and the cap on `recorded/` size;
- a required C++17 CI job for `simreco`;
- where ROOT files are stored and for how long.

## Independent review

The rewritten specs have not been independently reviewed. The plugin's `review.py`
(`skills/hep-authoring/references/independent-review.md`) can review `task-a-core.en.md` and `task-b-j15.en.md` on
the maintainer's machine: it needs fork subagents switched off and a host restart, and the document must exist nowhere
else on the host. Its record is advisory, not a human review record (O04/O14).
