# Drop the `legacy_id` Column from `orders` Safely

> Verified against the repository on 2026-10-02. The target is the demo shop at `task-authoring/tests/fixtures/shop_repo/`, which `README.md` there calls "not real code"; it is used because it is the only repository fragment here with a database migration. A real project would replace every path below.

## Background

`task-authoring/tests/fixtures/shop_repo/migrations/001_orders.sql` creates
`orders (id INTEGER PRIMARY KEY, total REAL, legacy_id TEXT, created_at TEXT)`.
The requester wants `legacy_id` gone. The only reader found in the repository is
`app/billing.py`, whose `invoice()` selects `total, legacy_id` from `orders` but
returns only `{"order": ..., "amount": ...}`, so the value is read and not used.
Dropping a column is irreversible once the data is gone, and the repository
shows no backup tooling, no production data, and no deployment process.

## Objective

After this task, no code reads `legacy_id`, a new migration removes the column,
and the data can be restored from a documented backup path if the change must be
rolled back.

## Scope

### In Scope

- Remove `legacy_id` from the query in `app/billing.py`.
- Add a numbered migration that drops the column (`002_...sql`).
- Define the backup and rollback path before the drop is applied.
- A test that `invoice()` still returns the same dictionary.

### Out of Scope

- Any other schema change.
- Backfilling or archiving `legacy_id` values beyond the backup path.
- Changing the database engine. `app/db.py` uses `sqlite3` with a file named
  `shop.db`.

## Repository Context

Verified by inspection on 2026-10-02 (paths relative to
`task-authoring/tests/fixtures/shop_repo/`):

- `migrations/001_orders.sql` is the only migration; there is no migration runner
  in the tree (`app/` has `db.py` with a `query()` helper only).
- `grep` for `legacy_id` finds exactly two files: the migration and
  `app/billing.py`.
- `tests/test_cart.py` is the only test file; nothing tests `app/billing.py`.
- No CI configuration, no backup script, no row counts, no production database
  were found. Whether the column is used outside this repository is unknown.

## Technical Approach

1. Re-run the `legacy_id` search across the whole repository, including
   templates and `web/`, and list every hit before editing. This step is
   mandatory: the search found two files today, and the task must not assume that
   stays true.
2. Add a characterization test for `invoice()` first (it should pass before any
   change), using a scratch `shop.db` created from `001_orders.sql`.
3. Remove `legacy_id` from the `SELECT` in `app/billing.py` and rerun the test.
4. Record the backup step: copy `shop.db` (or export the column) to a named
   file, and write the exact restore command in the migration's header comment.
5. Add `migrations/002_drop_legacy_id.sql`. `ALTER TABLE ... DROP COLUMN` needs
   SQLite 3.35 or newer; check the version in use and, if it is older, use the
   copy-table-and-rename pattern instead. Mark which one was used.
6. Apply it to a scratch database first, then run the test again.

## Deliverables

- Updated `app/billing.py` and a new test for `invoice()`.
- `migrations/002_drop_legacy_id.sql` with the restore command in its header.
- A short note listing the search results from step 1 and the SQLite version
  found.

## Acceptance Criteria

- No file under `task-authoring/tests/fixtures/shop_repo/` references `legacy_id`
  except the two historical migrations (`001`, `002`); other copies of the fixture
  and notes elsewhere in the repository are out of scope.
- `invoice()` returns the same dictionary before and after, asserted by a test
  that ran green before step 3 and after step 5.
- The migration's header names the backup file and the exact command that
  restores the column and its data; the restore command was run once on a scratch
  database and the data matched.
- Applying `002` to a scratch database built from `001` leaves a table without
  `legacy_id` and with all other columns and rows intact.
- No production database or deployment was touched.

## Validation

- Run the new test before and after the code change (the fixture has no test
  runner configuration; run it from the fixture root so `app` imports, for example
  `PYTHONPATH=. python3 -m pytest tests`).
- Build a scratch `shop.db` from `001`, insert sample rows, apply `002`, query
  `PRAGMA table_info(orders)`, then run the restore command and compare rows.
- Re-run the `legacy_id` search and confirm only the migrations match.

## Open Questions

- Do any consumers outside this repository (reports, exports, other services)
  read `orders.legacy_id`? **Requires Confirmation**; nothing here can answer it.
- Is there a real production database and a deployment process the migration
  must follow? **TBD**; none exists in the repository.
- Is "restore from backup" sufficient rollback, or must the column be kept for
  a deprecation period first (expand/contract)? **Requires Confirmation**; the
  task assumes a backup is enough.
- Which SQLite version runs in production? **TBD**; decides the `DROP COLUMN`
  form.
- Does column order matter after a restore? **TBD**; `ADD COLUMN` puts `legacy_id`
  last, so the restored table's column order differs from `001`. The criteria
  above compare data, not order.

## References

- `task-authoring/tests/fixtures/shop_repo/migrations/001_orders.sql`
- `task-authoring/tests/fixtures/shop_repo/app/billing.py`
- `task-authoring/tests/fixtures/shop_repo/app/db.py`
- `task-authoring/tests/fixtures/shop_repo/README.md`
