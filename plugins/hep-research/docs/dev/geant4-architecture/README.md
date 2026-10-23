# Geant4 architecture: working base

This folder holds one consolidated document for the Geant4 work in hep-research: correctness fixes and boundary
artifacts (task A), a second simulation backend with reconstruction and the J15 minimal spectrometer (task B), and
automated detector design search (task C), together with the program plan and the design rationale. It lives on the
branch `worktree-geant4-architecture`, based on `main` at `9f08796` (0.23.0 plus unreleased changes, contracts 3.5.0).

**Status (2026-10-23):** awaiting the user's and the maintainer's approval; do not start implementation before that.

## Files

| File | Content |
|---|---|
| `geant4-program.md` | **The consolidated document** (Traditional Chinese original): Part 1 plan (§P), Part 2 task A (§A), Part 3 task B (§B), Part 4 task C (§C), Part 5 design rationale (§R) |
| `geant4-program.en.md` | English translation with the same parts, sections, tables, checkboxes and numbers; if they disagree, the Chinese wins until the English is corrected |
| `gate_operating_characteristics.py` | Convergence-gate operating characteristics, two-stage factors, Welch degrees of freedom (§A.8, §A.9, §A Appendix B). Needs numpy and scipy; a design aid, not plugin code |
| `j15_design_estimates.py` | J15 design numbers (§B Appendix A). Standard library; scipy optional |
| `design_search_closure.py` | Reference values of task C's plane-placement closure test (§C Appendix A). Standard library |
| `prototype/phase1-core.patch` | Reference prototype of parts of A1.1–A1.3 and the enum fix of A1.12 (changes `contracts/validate.py`, `check_geant4_study.py`, `geant4_benchmarks.py`, the study-spec schema and two tests; nothing in `core/`); applies to `9f08796`; predates the current spec (§A.0 lists what it lacks); not reviewed for merge |

## If you are an agent starting work here

1. Open `geant4-program.md` and read "How to use this document" at the top, then §P.0, §P.10, §P.6 and §P.4.
2. **Run every stage in its own isolated git worktree** (§P.10): worktree `.claude/worktrees/geant4-<stage>` on branch
   `worktree-geant4-<stage>`, created from the latest `origin/main` that contains the prerequisite stages (in Claude
   Code: `EnterWorktree` with name `geant4-<stage>`, or `isolation: "worktree"` for subagents). Confirm the top-level
   path, branch, a clean status and that each prerequisite's merge commit is an ancestor of `HEAD` before writing code;
   never change files in the main checkout or another worktree; never use bare `git stash`.
3. Read the task card of your stage's part (§A.0, §B.0 or §C.0) and follow its work items and acceptance checklist.

## Working rules for this folder

1. Documentation changes happen only on branch `worktree-geant4-architecture`, in worktree
   `.claude/worktrees/geant4-architecture`. Change the Chinese original and the English translation together.
2. Do not push to `main` or open a pull request without the maintainer's approval.
3. Before committing, run at least `tools/check_packaging.py` and `tools/check_layering.py`, and stop if either fails.
