# Investigate Whether the Report Scaffolding in `examples/*/run.py` Should Be Shared

> Verified against the repository (`plugins/hep-research/`) on 2026-10-07. Paths are relative to the plugin root.

## Background

The plugin ships twelve executed examples under `examples/`, each with its own
`run.py` (124 to 516 lines) and a committed `output/` that
`tests/examples/` compares with a fresh run. The scripts repeat the same
scaffolding in their own words: nine of them build a Markdown `report.md`
line by line (`lines += [...]`), six define a `write_report()` of their own,
five define `artifacts()` that assembles contract artifacts, three define
`_audit()`, and eight call `contracts.validate` on what they wrote. A
line-level `difflib` ratio between any two scripts stays below 0.3 (highest
0.28, `published-comparison` vs `qed-prediction`), so these are not copies of
one file; they are the same chores written twelve times, each drifting on its
own (column order, how a pass/fail row is phrased, where the created timestamp
comes from). This task investigates whether that scaffolding should become one
shared helper, before a fix to one report writer is silently missing from the
others.

## Objective

Produce a recommendation, not an implementation: should the repeated report,
artifact and audit scaffolding be consolidated, and by which mechanism, given
that each example is meant to be read on its own as a worked example. The
recommendation is backed by an inventory of what repeats, with the commands used.

## Scope

### In Scope

- Inventory the repeated functions and idioms across the twelve `run.py`
  files (report writing, artifact assembly, audit hooks, output-directory
  handling, figure saving), with a count and the method used.
- Classify each repeat as intentional (example-specific wording a reader
  should see in place) or accidental drift.
- Compare mechanisms that fit the layering rules in `tools/check_layering.py`
  (`examples/` may import anything): a helper module under `examples/`, a
  helper in `core/`, or keeping the copies plus a drift test.
- Recommend one, with tradeoffs.

### Out of Scope

- Doing the consolidation.
- The physics or statistics in any example, and the committed numbers in
  `output/` (changing them is governed by `docs/maintenance.md`, "Rerunning
  comparisons and examples").
- The per-example `README.md` files, which differ by design.

## Repository Context

Verified by inspection on 2026-10-07:

- `examples/` holds twelve folders with a `run.py` each: `ams-flux-ratio`
  (516 lines), `theory-comparison` (481), `collider-angular` (328),
  `recasting` (251), `detector-resolution` (229), `qed-prediction` (207),
  `end-to-end-sample` (193), `published-comparison` (178), `batch-partition`
  (177), `unfolding-coverage` (154), `local-partition` (145),
  `eic-profile-routing` (124).
- Function names defined in three or more scripts: `main` (12),
  `write_report` (6), `artifacts` (5), `figures` (3), `_audit` (3). Nine
  scripts write `report.md`; eight import `contracts.validate`.
- Pairwise `difflib.SequenceMatcher` ratios on the line lists: maximum 0.28;
  no two scripts are near copies.
- `tests/examples/test_<example>.py` runs each `run.py` as a subprocess into a
  temporary directory and compares with the committed `output/`
  (`tests/examples/test_qed_prediction.py` is the pattern).
- `tools/check_layering.py` allows `examples/`, `tests/` and `tools/` to import
  anything; `core/` may import only `core/` and the mandatory environment.
- Not checked: whether any `write_report()` has a defect the others lack; this
  task only inventories them.

## Technical Approach

1. Repeat and extend the survey: list every top-level function in each
   `run.py`, group by name and by role (a function that writes `report.md`
   counts as report writing whatever its name), and record the commands.
2. For the report writers, produce a side-by-side summary of the table header,
   the pass/fail wording and the timestamp source used by each.
3. For the artifact assemblers, list which contract fields each fills by hand
   that a shared helper could derive (plugin, contract and profile versions,
   `created`, artifact IDs).
4. Evaluate the mechanisms: a shared `examples/_common.py` (readable in place,
   but every example then has one hidden dependency), a `core/` helper (would
   make report rendering part of the shared code and bring it under
   `core/OWNERS.json`), or copies plus a test that diffs the shared idioms.
5. Recommend one mechanism and outline the follow-up task if it is "proceed",
   including how the committed `output/` files are regenerated and checked.

## Deliverables

- An inventory table: idiom, scripts holding it, count, method.
- A side-by-side summary of the six `write_report()` implementations.
- A mechanism comparison against the layering rules and the "read in place"
  purpose of the examples.
- A recommendation with a follow-up task outline if applicable.

## Acceptance Criteria

- The inventory covers all twelve scripts and states the command used for each
  count so it can be reproduced.
- Each repeated idiom is classified as intentional or drift, with one line of
  evidence.
- The recommendation states what a reader of one example sees after the change
  and whether `tests/examples/` still compares byte-identical outputs.
- Every Open Question below is answered or explicitly deferred with a reason.

## Validation

- Re-run the survey commands and confirm the numbers.
- Check the recommendation against `tools/check_layering.py` by running it on
  a scratch copy that contains the proposed helper.

## Open Questions

- Is an example allowed to import anything outside its own folder, or is
  "self-contained and readable in place" a requirement? **Requires
  Confirmation**; `docs/maintenance.md` describes how to rerun examples but
  not what they may depend on.
- Is the drift in report wording something to unify, or does each example's
  report deliberately mirror its own acceptance criteria? **TBD**; the
  side-by-side summary answers part of it.
- Would a `core/` helper need a steward entry in `core/OWNERS.json` and a
  layering whitelist change? **Requires Confirmation**; assumed yes.

## References

- `examples/` (twelve `run.py` scripts).
- `tests/examples/test_qed_prediction.py`: how an example is compared with its
  committed output.
- `tools/check_layering.py`: the import rules.
- `docs/maintenance.md`, "Rerunning comparisons and examples".
- `core/OWNERS.json`: stewards of shared code.
