# Investigate Whether the Per-Skill `behavior_eval.py` Harnesses Should Be Consolidated

> Verified against the repository on 2026-10-02. Replaces the 2026-09-12 version, which investigated a byte-identical reference file that was removed on 2026-09-15. A fresh survey found no byte-identical file across skills today; the duplication now sits in test harnesses.

## Background

Three skills each carry their own copy of a fresh-model behavior-eval harness:
`agile-development/tests/behavior_eval.py` (306 lines),
`deep-learning/tests/behavior_eval.py` (318) and
`task-authoring/tests/behavior_eval.py` (337). The `task-authoring` copy was
adapted from the `agile-development` one on 2026-10-02. A line-level
`difflib` ratio gives 0.95 (agile vs deep-learning), 0.86 (agile vs
task-authoring) and 0.83 (deep-learning vs task-authoring), so they are near
copies, not identical, and each has drifted in its own way (for example the
`task-authoring` copy has a resume mode, a higher turn cap and per-prompt
fixtures). `academic-papers/tests/run_prompts.py` and
`academic-diagrams/tests/run_prompts.py` are a separate pair, and
`hep-analysis/tests/routing_eval.py` is used by other skills' TODO notes by a
relative path (`../hep-analysis/tests/routing_eval.py`), which only works when
the whole repository is checked out. This task investigates whether the
copies should become one shared harness, before a bug fix in one copy is
silently missing from the others.

## Objective

Produce a recommendation, not an implementation: should the near-duplicate
harnesses be consolidated, and by which mechanism, given that skills are
installed as independent folders. The recommendation is backed by a diff-based
inventory and a comparison of mechanisms.

## Scope

### In Scope

- Inventory the duplicated or near-duplicated test and script files across
  the seven skills (harnesses, `validate_skill_bundle.py`, prompt files),
  with a similarity measure and the method used.
- List which differences between the three `behavior_eval.py` copies are
  deliberate (fixtures, prompt format, resume) and which are accidental drift.
- Compare mechanisms that fit the install model in the root `README.md`
  (`cp -r <skill folders> ~/.claude/skills/` and the equivalents for other
  agents): keep copies plus a drift check, a shared top-level folder copied in
  by a script, a symlink, or a single owner skill referenced by relative path.
- Recommend one, with tradeoffs.

### Out of Scope

- Doing the consolidation.
- Judging whether the harnesses' scoring is good (see each skill's
  `VALIDATION.md`).
- `SKILL.md` and `README.md` content, which differ by design.

## Repository Context

Verified by inspection on 2026-10-02:

- A content-hash scan of the seven skill folders (excluding `__pycache__`,
  `fixtures`, `.git`) found identical files only inside git-ignored
  `.pytest_cache/` directories; there is no byte-identical `references/`
  file. Same-named files with different content: `validate_skill_bundle.py`
  (7), `behavior_eval.py` (3), `run_prompts.py` (2), `prompts.md` (6),
  `test_end_to_end.py` (2).
- The three `behavior_eval.py` files share the same run / score / report
  structure and the same blind-redaction idea (see the module docstrings).
- Every skill is installed by a plain `cp -r` of its own folder
  (root `README.md`, install section), so a file outside the skill folder is
  not installed with it.
- No CI configuration exists (no `.github/`, no `*.yml` in the tree).
- Not checked: whether the seven `validate_skill_bundle.py` implementations
  (four different output wordings) are worth merging; this task only
  inventories them.

## Technical Approach

1. Repeat and extend the survey: hash and `difflib`-compare every same-named
   script and test file across the seven skills; record the commands.
2. For the three `behavior_eval.py` copies, produce a three-way diff
   summary: shared core, intentional per-skill parts, drift.
3. Check where the harnesses are meant to run: from inside one skill folder
   after a single-folder install, or only from the repository checkout. Read
   each skill's `README.md` and `TODO.md` for how it says to run them.
4. Evaluate the mechanisms against the `cp -r` install model, including what
   happens when one skill folder is copied out alone.
5. Recommend one mechanism and list the follow-up implementation task if it
   is "proceed".

## Deliverables

- An inventory table: file name, skills holding it, similarity, method.
- A three-way diff summary of the `behavior_eval.py` copies.
- A mechanism comparison against the install model.
- A recommendation with a follow-up task outline if applicable.

## Acceptance Criteria

- The inventory covers all seven skills and states the command used for each
  similarity figure so it can be reproduced.
- The three-way summary classifies each difference as intentional or drift,
  with one line of evidence each.
- The recommendation states what happens to a skill folder copied out on its
  own, and does not silently break the documented `cp -r` install.
- Every Open Question below is answered or explicitly deferred with a reason.

## Validation

- Re-run the survey commands and confirm the numbers.
- Check the recommendation against the root `README.md` install section.

## Open Questions

- Are the harnesses run only from a repository checkout (so a shared file
  outside the skill folder is acceptable) or also from an installed skill
  folder? **Requires Confirmation**; `README.md` documents installation but
  not where the tests are expected to run.
- Is the drift (resume mode, fixtures, turn cap) something to propagate to
  the other copies, or does each skill need its own variant? **TBD**; the
  three-way diff answers part of it.
- Should `validate_skill_bundle.py` (seven different implementations) be in
  scope? **Requires Confirmation**; assumed out of scope beyond the inventory.

## References

- `README.md` (repository root): install model.
- `agile-development/tests/behavior_eval.py`,
  `deep-learning/tests/behavior_eval.py`,
  `task-authoring/tests/behavior_eval.py`: the three copies.
- `hep-analysis/tests/routing_eval.py`: the harness other skills' notes point
  to by relative path.
- `task-authoring/VALIDATION.md`, "Round 3": where the adaptation was logged.
