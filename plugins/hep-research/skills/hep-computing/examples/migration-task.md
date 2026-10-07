# Drop the Hand-Written Display Fields from the Evidence Source Ledgers Safely

<!-- example: experiment-specific illustration -->
> Verified against the repository (`plugins/hep-research/`) on 2026-10-07. Paths are relative to the plugin root. The data are JSON ledgers, not a database, but the shape of the task is the same: a destructive schema change to committed records with readers in several places.

## Background

Every source record in `profiles/experiments/eic/evidence/sources.json` (5
records), and in every other profile ledger that shares the schema,
carries three display strings next to the structured fields they mirror:
`year_text` beside `year`, `tier_text` beside `tier` and `tier_range`, and
`locator_text` beside `dois` and `url`. The requester wants the three text
fields gone so that the structured fields are the only truth. They are not
dead: `core/evidence/render_index.py` prints them in the source table with the
structured fields as fallback, and `core/evidence/ledger.py` reports
`source.tier_text_mismatch` when `tier_text` does not start with `tier`. Some of
their content is not derivable from the structured fields (a `tier_text` of
`5-6` for a source with `tier_range` `[5, 6]` is; a `year_text` naming two
years, or a `locator_text` that is a report number rather than a DOI, is not).
Deleting them loses that text unless it is exported first, and the rendered
`evidence/index.md` of both profiles changes.

## Objective

After this task, no source record carries `year_text`, `tier_text` or
`locator_text`, the renderer and validator read only the structured fields, the
regenerated indexes are committed, and every non-derivable text is preserved in
an exported file with a documented restore path.

## Scope

### In Scope

- Remove the three fields from the ledger and from the synthetic records in
  `tests/core/test_evidence_ledger.py`,
  `profiles/experiments/eic/tests/test_evidence_ledger.py`, and in the tests
  of any other installed profile that builds such records.
- Change `render_index.py` to render Year, DOI / URL and Tier from `year`,
  `dois`/`url` and `tier`/`tier_range`; remove the `tier_text` check from
  `ledger.py`.
- Export the non-derivable texts before deleting them, with a restore command.
- Regenerate `evidence/index.md` for both profiles with `render_index.py --write`.

### Out of Scope

- Any other ledger field, and the claim ledgers.
- `contracts/schemas/evidence_source.json`, which does not list the three
  fields (they are allowed as extra properties), so no contract version change
  is needed; confirm this rather than assume it (Open Questions).
- Changing how a tier range is stored (`tier_range` stays as it is).

## Repository Context

Verified by inspection on 2026-10-07:

- `profiles/experiments/eic/evidence/sources.json`: all 5 records have the
  three fields and `tier_range`; in each the text field equals the value it
  mirrors, so nothing is lost there. Ledgers of other profiles (installed
  separately) may hold hand-written text that differs from the structured
  value; the export step below records those cells before they are dropped.
- Readers in tests: `tests/core/test_evidence_ledger.py` builds a synthetic
  source with all three fields and updates `year_text` in two tests;
  `profiles/experiments/eic/tests/test_evidence_ledger.py` sets `tier_text` in
  one test; a profile shipped separately may build records with `year_text`
  and `locator_text` in its own tests.
- `grep` for the three names outside those files finds nothing else in `.py`,
  `.json` or `.md`.
- The `evidence/index.md` file is generated between markers by
  `render_index.py` and checked by the profile tests.

## Technical Approach

1. Re-run the search for the three field names across the whole plugin before
   editing and list every hit. This step is mandatory: the inventory above was
   taken today and the task must not assume it stays true.
2. Export: write one JSON file per profile listing, per source ID, the three
   texts and whether each is derivable from the structured fields (equal to
   `str(year)`, to the `tier`/`tier_range` rendering, to the DOI join or URL).
   Put the exact restore command (read the export, set the fields back) in the
   file's header comment. Commit the exports with the change.
3. Characterize first: render both indexes with the current code and keep the
   output; it is the before-state for step 6.
4. Change `render_index.py` to derive the three columns (`tier_range` renders
   as `lo-hi`); remove the `tier_text` check and its code from `ledger.py`.
5. Delete the fields from the ledger and from the synthetic test records;
   regenerate both indexes with `--write`.
6. Diff the regenerated indexes against the before-state. Every changed cell
   must correspond to a non-derivable text listed in the export; anything else
   is a rendering defect.
7. Run the restore command on a scratch copy of one ledger and confirm the
   fields and values come back.

## Deliverables

- Updated `core/evidence/render_index.py` and `core/evidence/ledger.py`.
- `sources.json` without the three fields; `evidence/index.md`
  regenerated.
- One export file per profile under its `evidence/` folder, with the restore
  command in its header.
- Updated synthetic records in the three test files, and one new test that a
  `tier_range` renders as `lo-hi`.

## Acceptance Criteria

- No file in the plugin references `year_text`, `tier_text` or `locator_text`
  except the two export files and the changelog.
- `core/evidence/ledger.py` passes on the ledger with the same counts as
  before (5 sources for eic).
- The regenerated indexes differ from the before-state only in cells whose
  text the export marks as non-derivable; the diff is attached to the change.
- The restore command, run once on a scratch copy, reproduces the deleted
  fields byte for byte.
- `python3 -m unittest discover -s tests -t .` from the plugin root and each
  profile's `python3 -m unittest discover -s tests -t tests` pass.

## Validation

- Run the plugin and profile test suites before step 4 (green), after step 5
  (red where the fields are still expected), and at the end (green).
- `python3 core/evidence/render_index.py --sources ... --claims ... --index ...`
  without `--write` for both profiles, expecting exit 0.
- Re-run the field-name search and confirm only the export files match.

## Open Questions

- Are the non-derivable texts content to keep in a structured form (for
  example a `report_number` field for locators that are not DOIs, or a
  `year_note`) or display noise to drop? **Requires Confirmation**; the export
  keeps them either way, but the answer decides whether a follow-up adds
  fields.
- Does the evidence contract treat unknown extra properties as allowed? The
  schema does not list the three fields and the ledgers validate today, so
  yes by observation; a negative fixture confirming it was not found.
  **Requires Confirmation.**
- Should `tier_range` be rendered as `5-6` (today's `tier_text` form) or as
  `5 to 6`? **TBD**; the before/after diff is cleaner with `5-6`.
- Do any consumers outside this plugin (project files, companion plugins) read
  the three fields from the ledgers? **Requires Confirmation**; nothing here
  can answer it.

## References

- `profiles/experiments/eic/evidence/sources.json`: the records.
- `core/evidence/render_index.py`, `core/evidence/ledger.py`: the readers.
- `tests/core/test_evidence_ledger.py`,
  `profiles/experiments/eic/tests/test_evidence_ledger.py`: synthetic
  records to update.
- `docs/maintenance.md`, "Evidence ledgers" and "Schema migration".
<!-- /example -->
