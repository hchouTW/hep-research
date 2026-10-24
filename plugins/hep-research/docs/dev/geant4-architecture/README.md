# Geant4 architecture: working base

This folder holds one consolidated document for the Geant4 work in hep-research. It plugs into the detector system
design loop that `main` shipped in 0.37.0–0.38.0 (design-spec, design-candidate, design-evaluation; verdicts derived by
`contracts/design.py`; fidelity F0–F5 with F4 = a qualified Geant4 study):

- task A: correctness fixes and boundary artifacts that make Geant4 study labels trustworthy for F4;
- task B: a second simulation backend with reconstruction that serves as main's F4 evaluator, and J15 as a design
  project;
- task C: automated generation of design candidates inside the loop (`evaluate_design.py search`);

together with the program plan, the design rationale and the full revision and review history. It lives on the branch
`worktree-geant4-architecture`, planned against `main` at `5584927` (0.38.0, contracts 3.12.0), which is merged into
the branch.

**Status (2026-10-24):** spec approved by the maintainer; §P.7 items 2–15 decided as recommended. Decision D0 (how a
detector-level Geant4 study qualifies as F4, §P.7.1; issue #273) is still open, so B3 and C2's F4 confirmation do not
start (G-D0).

## Files

| File | Content |
|---|---|
| `geant4-program.md` | **The consolidated document** (Traditional Chinese original). Front matter: how to use, a reading index per stage, conventions and a global glossary. Part 1 plan (§P), Part 2 task A (§A), Part 3 task B (§B), Part 4 task C (§C), Part 5 design rationale (§R), Part 6 revisions, reviews and decisions (§H, history only) |
| `geant4-program.en.md` | English translation with the same parts, sections, tables, checkboxes and numbers, line by line; if they disagree, the Chinese wins until the English is corrected |
| `decision-d0-f4-qualification.md` | Decision record D0 for the maintainer (the form linked from issue #273): options, the qualification path, sub-decisions D0-a to D0-d; open |
| `gate_operating_characteristics.py` | Convergence-gate operating characteristics, two-stage factors, Welch degrees of freedom (§A.8, §A.9, §A Appendix B). Needs numpy and scipy; a design aid, not plugin code |
| `j15_design_estimates.py` | J15 design numbers (§B Appendix A). Standard library; scipy optional |
| `design_search_closure.py` | Reference values of task C's plane-placement closure test (§C Appendix A). Standard library |
| `prototype/phase1-core.patch` | Reference prototype of parts of A1.1–A1.3 and the enum fix of A1.12 (changes `contracts/validate.py`, `check_geant4_study.py`, `geant4_benchmarks.py`, the study-spec schema and two tests; nothing in `core/`); written for `9f08796` and still applies to `5584927` with small offsets; predates the current spec (§A.0 lists what it lacks); not reviewed for merge |

The review of 2026-10-24 against `main` 0.38.0 is folded into §H.2.1 of the document.

## If you are an agent starting work here

1. Open `geant4-program.md` and read the front matter: "How to use this document", then the **reading index for
   your stage**; it lists the sections to read in order. Read by section (search for `## §A.5` etc.), not the whole
   file at once.
2. **Run every stage in its own isolated git worktree** (§P.10): worktree `.claude/worktrees/geant4-<stage>` on branch
   `worktree-geant4-<stage>`, created from the latest `origin/main` that contains the prerequisite stages (in Claude
   Code: `EnterWorktree` with name `geant4-<stage>`, or `isolation: "worktree"` for subagents). Confirm the top-level
   path, branch, a clean status and that each prerequisite's merge commit is an ancestor of `HEAD` before writing code;
   never change files in the main checkout or another worktree; never use bare `git stash`.
3. Parts 1–5 are the current specification; Part 6 is history and binds nothing.

## Working rules for this folder

1. Documentation changes happen only on branch `worktree-geant4-architecture`, in worktree
   `.claude/worktrees/geant4-architecture`. Change the Chinese original and the English translation together.
2. Do not push to `main` or open a pull request without the maintainer's approval.
3. Before committing, run at least `tools/check_packaging.py` and `tools/check_layering.py`, and stop if either fails.
