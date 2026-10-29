# Store, continuity, checkpoints, export and import

Spec v9 section 11. Code: `scripts/hep_review_support/store.py`, `continuity.py`, `export.py`.

## Store

SQLite on a single host's local disk, by default `~/.local/state/hep-research/hep-review` (`$XDG_STATE_HOME` when set),
never in the project under review. The location is checked first: NFS, SMB/CIFS, FUSE, 9p, virtiofs, synced folders
(iCloud Drive, `Library/CloudStorage`, Dropbox, OneDrive, Google Drive) and unknown filesystem types are refused, with
no fallback to a writable JSON file; then only R0 or a static review is possible.

Appends are atomic (`isolation_level=None`, `BEGIN IMMEDIATE`), check the expected head (CAS), refuse a reused
operation id with another payload (a retry with the same payload returns the original commit), check object rules,
schemas, blobs present, plan ancestry and the downgrade list, and never rewrite a committed object. Blobs are written
and verified before the commit that references them; an unreferenced blob is an orphan, not committed.

## Head continuity

| State | When |
|---|---|
| verified | anchored (a trusted checkpoint the user gave, matching the chain, or a genesis this session wrote) and every later commit is one this session wrote |
| unverified | no anchor (a new session without a checkpoint, or lost state); fixed for the whole session |
| broken | the anchor is not on the chain, or a commit after it was not written by this session |

The coordinator's written digests live in its state file (`--state`), compared from tool output, never retyped.
Broken stops appending; recovery is a fork segment from the last trusted head (`forked_from`, `excluded_commits`), the
old segment kept as evidence. The report distinguishes "foreign commits appended" from "a saved value is not on the
chain" (a transcription error). An incompatible schema change opens a migration segment (`migrated_from`); the old
segment is never touched.

## Checkpoints

After every report and before the session ends, hand the user the line from `review.py checkpoint`:
`hep-review checkpoint: context=<id> segment=<seg> seq=<n> digest=<sha256>`. The next session starts with
`review.py start --checkpoint "<line>"`. If the store does not persist (an ephemeral host), export to a location the
user keeps before the session ends; without an export the report states that the record cannot be continued.

## Export and import

`export` writes one strict-JSON file: the segment's commits ≤ N with their objects, the segment origin, the blob
inventory and bytes, and a partial flag. `verify-export` gives two conclusions: internal consistency (every digest and
the chain recomputed) and, with a checkpoint, whether the digest at its seq matches; later commits are listed as
"appended after the checkpoint, unconfirmed". Without a checkpoint only self-consistency is claimed. `import` verifies
first and refuses a failing export.
