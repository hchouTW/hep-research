# G1 independent review: hep-review I/O layer (T02) and skill/coordinator (T03)

- Frozen at commit 96f70b01 (branch hep-review-v9-impl). Review date: 2026-10-29.
- Read: `skills/hep-review/scripts/hep_review_support/{materials,store,continuity,export,coordinator,evaluation}.py`,
  `skills/hep-review/scripts/review.py`, `skills/hep-review/SKILL.md`, `skills/hep-review/references/*.md`,
  `skills/hep-review/assets/{host_profile,registry}.json`, `tests/skills/hep_review/*.py`, the relevant parts of
  `contracts/hep_review.py` (`_check_chain`, `check_plan`, `decide_summary`, `render_report`) as context,
  `docs/dev/hep-review/host-profile.md`, and spec v9 (English) §1.3, §4, §5, §9-§13, §15.4, §16, §17.2, §19.
- Ran: the six test modules (93 tests, all pass), plus three probe scripts of my own against temporary stores
  (outside the repository and outside `~/.local/state`). The probes call the public functions with the test fixtures
  in `tests/skills/hep_review/store_fixtures.py`; their results are quoted in the findings.
- No repository file was changed apart from this report.

Severity: blocker = a no-defect summary or a tier claim that the records or the host do not support, reachable on the
documented path; major = a spec rule not implemented as written, with a real effect; minor = local defect or gap.

### B1 blocker: rolling back the head over the coordinator's own last commits stays "verified" and can show a no-defect summary

- Location: `skills/hep-review/scripts/hep_review_support/continuity.py:95-124` (`head_continuity`).
- Spec clause: §11.3 (broken when "a saved value is not on the chain"; verified needs an anchor and every commit after
  it in the coordinator's sequence), §1.3 invariant 5, case N32/N66 family.
- Evidence: `head_continuity` only checks that every commit *on the chain* after the anchor is in `st.written`. It never
  checks the converse (every digest in `st.written` is on the chain) or that the head equals `st.expected_head`, unless a
  foreign commit also exists. Probe: seed five commits in a genesis-anchored session, append an assignment and a
  `violated` record with a finding (seq 6, 7); report gives `output_summary=False`. Then, with plain sqlite3,
  `DELETE FROM commits WHERE digest=<seq 7>` and set `heads` back to seq 6. `K.report` now returns
  `head_continuity=verified` and `output_summary=True`: the negative record disappeared and the report shows the R2
  no-defect sentence. The CAS on the next append would fail, but reports do not append.
- Fix: in `head_continuity`, return `broken` (case `saved-value-not-on-chain` / `head-rolled-back`) whenever any digest in
  `st.written` is not at its position on the anchor segment, or the head is not `st.expected_head`. Add a test with
  exactly this rollback.

### B2 blocker: `fork` and `migrate` can drop the session's own verified negative records and yield a verified no-defect report

- Location: `continuity.py:131-163` (`_open_segment`, `fork`), `continuity.py:166-177` (`migrate`);
  `coordinator.py:258-281` (`report`).
- Spec clause: §11.3 (fork is the recovery *from broken*, "from the last trusted head"), §8.3 / §1.3 invariant 5 (old
  negative or unresolved results must not disappear), N66 (the report explains the fork case).
- Evidence: `fork` does not require `head_continuity == broken` and accepts any `last_trusted_seq`, including one before
  commits this session itself wrote and verified. Probe: session anchored on a checkpoint at seq 5 appends an
  assignment and a `violated` record with a finding (seq 6-7; report: verified, no summary). `C.fork(s, st, 5, ...)`
  then opens `seg-2` anchored on its genesis; the report reads `head_continuity verified`, `achieved R2`,
  "R2 (independent review under the recorded conditions): no still-valid defect was observed ...", with the
  checkpoint now `segment=seg-2 seq=1`. Nothing in the report text mentions the fork, `forked_from` or the excluded
  commits. `migrate` has the same hole: `transform` is an arbitrary callable whose output is admitted as the new
  verified segment, so a transform that omits a negative record is accepted.
- Fix: allow `fork` only when continuity is broken, and only from a position that is the anchor or a commit in
  `st.written` (the last trusted head), never earlier than the last own commit that is still on the chain. For
  `migrate`, check that every record and finding of the source segment maps to an object in the new genesis (or carry
  an explicit, admitted mapping). The report (layer 2) must state when the head segment is a fork or migration and list
  `excluded_commits` and the broken case (`foreign-commits-appended` vs `saved-value-not-on-chain`); today only
  `attestation.head_continuity.basis` holds the case and the text says "head continuity broken".

### B3 blocker: the store admits hand-authored assignment conditions that the host cannot provide; the CLI offers no other way to make an assignment

- Location: `store.py:258-304` (`_admit`, no check of assignment conditions), `review.py:135-140` (`append` takes any
  object list), `coordinator.py:77-111` (`make_assignment` exists but is not reachable from the CLI);
  `references/workflow-and-tiers.md:65` documents a `packets` command that does not exist (see M4).
- Spec clause: §1.3 invariants 6 and 8, §4.3 (third condition is advisory on a shared filesystem; the advisory sentence
  is mandatory), §12.2-12.3 (bases come from host observations; keep dispatch requests and host invocation IDs).
- Evidence: the host profile records `filesystem_isolation: false (observed)` and
  `no_other_evaluations_seen_basis: advisory`. Probe: commit an assignment (as `review.py append` would) whose
  `no-other-evaluations-seen` is `{"satisfied": true, "basis": "observed"}`, then a supported record. The report reaches
  `R2`, `output_summary=True`, and the advisory sentence "...neither observed nor enforced" is absent. The same path lets
  the coordinator model write `fresh-context: observed` for a same-context review. Even `make_assignment` derives
  `fresh-context: observed` solely from the caller's `dispatch["via"] == "agent-tool"`, records no host invocation id
  or dispatch request, and hard-codes `qualified: {satisfied: true, basis: declared}`.
- Fix: build assignments only in the I/O layer (`make_assignment` behind a CLI command such as `assign`, recording the
  host invocation id and dispatch request), and in `_admit` refuse an assignment whose condition bases exceed what the
  bound host profile allows (e.g. `no-other-evaluations-seen` may not be `observed` unless `filesystem_isolation` is
  observed true; `fresh-context: observed` needs a dispatch record). Record the host profile digest on the assignment.

### B4 blocker: a record's answers are not bound to its raw submission; the CLI makes the coordinator re-enter the parsed record

- Location: `review.py:145-149` (`ingest` prints the record, "not committed"), `review.py:135-140` (`append`),
  `store.py:258-304` (`_admit`), `coordinator.py:157-238`.
- Spec clause: §12.4 (file-transfer: the coordinator reads the bytes and stores them "without retyping"; transcription
  caps at R1), §1.3 invariant 7, §10.2 (raw saved first, then parsed into metadata keeping raw_submission_ref).
- Evidence: the documented CLI flow is `ingest` (prints JSON) then `append --objects FILE`, so the model has to put the
  record into a file itself. Nothing at admission re-derives the record from `raw_submission_ref`. Probe: the reviewer's
  drop file says `outcome: undetermined`, `missing_inputs: ["covariance"]`; `K.ingest` builds the record with fidelity
  `file-transfer`; changing the answer to `supported` and clearing `missing_inputs` before `C.append` is accepted, and
  the report gives `R2` with `output_summary=True`. The raw blob is kept, but the record says `file-transfer` while its
  content was in effect retyped.
- Fix: make `ingest` commit the record itself (parse and append in one tool call, with the state file), or have
  `_admit` re-run `parse_submission` on the stored raw blob for every `type: submission` record whose fidelity is
  `file-transfer`/`digest-bound` and refuse it unless the result is byte-identical.

### M1 major: non-author is "declared" and met when the manifest has no author list at all

- Location: `coordinator.py:91-94` (`make_assignment`), `materials.py:169-173` (`snapshot` writes `authors: []`,
  `authors_basis: "unknown"`).
- Spec clause: §4.3 (non-author: observed or declared), §12.3, case A13.
- Evidence: with `authors_declared=True` the condition is `actor not in authors`; `authors_basis` is never read. Probe:
  manifest material with `authors: []`, `authors_basis: "unknown"` (exactly what `snapshot` produces); assignment for
  actor `author-a` with `authors_declared=True` gives `{"satisfied": true, "basis": "declared"}` and the report reaches
  R2. The material's actual author therefore reviews their own work at R2.
- Fix: count non-author as declared only when every target material of the spec's obligations has
  `authors_basis` `declared` (or `observed`) and a non-empty author list; otherwise `unknown`. Add the case to the A13 test.

### M2 major: malformed submissions crash ingestion instead of being recorded as data

- Location: `coordinator.py:182` (`suggested_obligations`), `:196-203` (attempts), `:214-215` (locator), `:229`
  (`missing_inputs`); `review.py:170-176` (TypeError and AttributeError are not caught).
- Spec clause: §5.1 step 5-6 (invalid original kept, not lost), §10.2 (non-compliant input rejected, never
  auto-corrected), §12.1.
- Evidence: probe with otherwise valid submissions: `attempts: ["x"]` raises `AttributeError: 'str' object has no
  attribute 'get'`; `missing_inputs: 3` and `suggested_obligations: 5` raise `TypeError: 'int' object is not iterable`;
  a finding with `locator: {"material_id": ["x"]}` raises `TypeError: unhashable type: 'list'`. Through the CLI these end
  in an uncaught traceback; the raw blob is left as an orphan and no record exists. A string `missing_inputs` is split
  into one missing input per character.
- Fix: type-check every nested value (dict / list of str / str) before use; on a wrong type record a limitation and skip
  the item, as is already done for an unknown obligation id. Add a fuzz-style test over wrong-typed fields.

### M3 major: store location check is by path string only; a symlink into a synced or network folder passes

- Location: `store.py:104-128` (`filesystem_type`, `check_location`), `store.py:172-177`.
- Spec clause: §11.1 (detect filesystem type with statfs / mountinfo; synced folders unsupported), cases P12, N51.
- Evidence: neither the mount-point match nor `SYNC_MARKERS` resolves the path. Probe: `store-link -> .../Library/
  CloudStorage/Dropbox`; `check_location(store-link)["supported"]` is `True`, while the resolved target gives `False`.
  The same applies to a symlink onto an NFS/SMB mount point (the longest-prefix match falls back to `/`).
- Fix: resolve the path (`os.path.realpath` of the nearest existing ancestor) before matching mounts and sync markers,
  and preferably confirm the type with `os.stat(path).st_dev` against the mount entries (or `stat -f` on macOS). Add the
  symlink case to `test_n51_*`.

### M4 major: the CLI reference documents commands and arguments that do not exist

- Location: `skills/hep-review/references/workflow-and-tiers.md:58-69` versus `scripts/review.py:62-104`.
- Spec clause: §17.2 / §12.2 (do not claim a capability that is not there); SKILL.md routes every review to this table.
- Evidence: `packets --context ID --out DIR` is documented; `review.py packets` exits with "invalid choice: 'packets'".
  `snapshot ... --out FILE` is not accepted; `start`, `append` and `report` are listed without the required `--state`;
  `import FILE --checkpoint LINE` omits the required `--into` and `--state`. A coordinator following the reference
  falls back to hand-writing packets and assignments (feeds B3).
- Fix: implement `packets` (and an `assign` command, see B3) or remove them, and make the table match `--help`. A test
  that parses the table and runs `--help` for each listed command would keep them aligned.

### m1 minor: the packet's submission form and the parser disagree

- Location: `coordinator.py:41-50` (PACKET) versus `coordinator.py:192-194, 211-225`.
- Spec clause: §9.4 (locators bound to a snapshot ref), §15.5 C01 (a locatable defect).
- Evidence: the packet offers `not-applicable` as an outcome, but the parser always turns it into `not-examined`; the
  packet's finding form has no `locator` field, so every finding gets the fallback "no valid locator given; located at
  the obligation's target" (the reviewer's location is only in free text); the finding's `evidence` text is dropped.
- Fix: put a `locator` object (material id + snapshot digest + line range or JSON Pointer) into the packet form, drop
  `not-applicable` from it (or support a structured discharge), and keep finding evidence.

### m2 minor: `report` defaults to `store_persistence="persistent"` although the host profile says unknown

- Location: `coordinator.py:258-259, 270-272`; `review.py:150-153` never passes it; `assets/host_profile.json`
  (`store_persistence: null, unknown`).
- Spec clause: §11.4, case N27, §12.2 (a capability not observed is unknown).
- Evidence: every CLI report is produced as if persistence were observed; no disclosure says it is unknown (H5 pending).
- Fix: read `store_persistence` from the host profile; when it is not observed `persistent`, disclose that and that
  continuation needs an export or the checkpoint.

### m3 minor: export fields outside the commit headers are not bound; checkpoint context is not compared

- Location: `export.py:73-115` (`verify_export`), `export.py:135` (`import_export`), `store.py:365-395`.
- Spec clause: §11.6.
- Evidence: `context_id`, `segment_id` and `segment_origin` at the top of the export are not compared with the commit
  headers (`_check_chain` does not look at them), and the checkpoint's `context_id` is ignored. An export can be imported
  under a context or segment id that differs from its own headers, and `segment_origin` (stored in the `segments` table
  and re-exported) is whatever the file says.
- Fix: require every header's `context_id`/`segment_id` to equal the export's, derive `segment_origin` from the genesis
  header (`forked_from`/`migrated_from`/`excluded_commits`) instead of storing it separately, and compare the
  checkpoint's context.

### m4 minor: after importing a non-first segment, fork and migrate cannot open a new segment

- Location: `continuity.py:127-128` (`_next_segment`).
- Spec clause: §11.3-11.4 (recovery by fork, migration).
- Evidence: probe: fork in store A (`seg-2`), export, import into store B with the checkpoint (verified). B has one
  segment row (`seg-2`), so `_next_segment` returns `seg-2` again; `C.migrate` is refused with `object.id_reused` /
  `plan.ancestry` (it re-admits against the existing `seg-2`), and a fork would collide on the primary key.
- Fix: choose a segment id not already present (e.g. max numeric suffix + 1, or a random id).

### m5 minor: the drop root (and material root) itself is opened following symlinks

- Location: `materials.py:85`.
- Spec clause: §9.2, case N67.
- Evidence: `os.open(root, O_RDONLY | O_DIRECTORY)` follows a symlink at the root or any of its parent components. On
  this host reviewers can write in the shared filesystem (H1), so a reviewer can replace the drops folder with a
  symlink and redirect where `asg-N/submission.json` is read from. Material roots come from the intent and are less
  exposed.
- Fix: open the drop root with `O_NOFOLLOW` as well (and resolve it once at assignment time, recording its device and
  inode; refuse if they change).

### m6 minor: mid-review supplementary material cannot re-assess "no other evaluations seen"

- Location: `coordinator.py:95-101`; test `tests/skills/hep_review/test_coordinator.py:145`.
- Spec clause: §12.3 ("once contaminated, the condition must not still be marked met"), case A30.
- Evidence: contamination is only taken into account when supplementary material is passed to `make_assignment`
  before the assignment is committed. Material supplied to an already dispatched reviewer (the A30 situation, e.g.
  after a material request) has no code path, and the committed assignment keeps `satisfied: true`. The A30 test covers
  only the before-dispatch case.
- Fix: add a committed "supplied-material" object bound to the assignment (source, reason, contains_evaluation) that the
  projection uses to turn the condition unmet; test it after dispatch.

### m7 minor: P30 test does not test its case; a confirm-only second reviewer never "completes separation"

- Location: `coordinator.py:356-365` (`marginal_value`); `tests/skills/hep_review/test_coordinator.py:257`.
- Spec clause: §16, case P30 ("second reviewer only confirms the original finding: can complete separation; its value
  is not erased").
- Evidence: `separation_completed = independent and ...` with `independent` requiring non-empty `new_evidence`. Probe:
  `{"new_evidence": [], "same_source_as": None, "confirmed": ["F1"]}` gives `separation_completed: False`. The test
  passes only because it supplies `new_evidence: ["independent recomputation"]`, which is not "only confirms".
- Fix: let an independent (non-same-source) confirmation complete separation without new evidence; change the test
  input to a pure confirmation.

### m8 minor: smaller gaps

- `add_obligation` (`coordinator.py:331-345`) records any `authority` string; nothing checks it against the intent's
  change authority (A09 "within authority").
- `ingest_submission` / `parse_submission` (`materials.py:190-203`, `coordinator.py:241-247`): on `mismatch` the
  declared digest is not stored in the record, so "keep both copies" (§12.4) keeps only one value.
- SKILL.md (§17.2 host capability branches) does not state the store-unavailable branch (location refused: no live
  backend, only R0 or static review, ask the user for a local location) or that an ephemeral store must be exported
  before the session ends; both are only in `references/storage-continuity-and-export.md`.

## Checked and found correct

- Controlled reading: component-by-component `O_DIRECTORY|O_NOFOLLOW`, last component `O_NOFOLLOW|O_NONBLOCK` then
  `fstat`; symlinked last and parent components, FIFOs, directories, oversize and growing files are refused; `.`/`..`,
  empty and absolute components refused; hard links recorded as a limitation; unavailable platform raises (N26).
  Snapshots hash the saved bytes and list unstable captures and coherent-version requests as gaps (P32, P33).
- Store: `isolation_level=None` with explicit `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK`; CAS on expected head; replay by
  `operation_id` with same payload returns the original, different payload refused (N06); blobs verified before
  commit; orphans are not committed (P06); rollback leaves the head unchanged (P05); two-process CAS (P27); as-of reads
  in one read transaction (A28/P08); reports never move the head (N07); unapproved validator refused (N61).
- DB edits that change object bytes or commit headers are caught by the kernel's `_check_chain` in `validate` (the
  report then fails rather than showing a summary); a checkpoint not on the chain is broken.
- Export: internal consistency recomputes digests, chain, payload digests and blob bytes; a recomputed chain without
  the negative commit fails against the checkpoint (N08/P13); N+1..M are listed (N43); without a checkpoint only
  self-consistency is claimed (N09); a failing export is not imported.
- Submissions: unknown fields (role, authorization, rubric, instructions) are ignored and listed; a wrong
  `assignment_id` examines nothing; invalid JSON keeps the raw bytes (P09); transcribed caps at R1 (N31); a writable
  host transcript does not qualify (N62).
- Salted gold commitment uses a 256-bit nonce and constant-time compare (N41).
- SKILL.md contains the target-tier first step, three-axis routing, R2 floor, instruction/data boundary, extra
  material, stopping, two-layer report with tier qualifier, checkpoint handover and asking for it (N55), on-demand
  references; the skill is registered in skill names, routing cases and the capability map (N16).
